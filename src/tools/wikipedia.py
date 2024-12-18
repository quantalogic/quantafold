import logging
import time
from difflib import SequenceMatcher
from functools import lru_cache
from typing import List, Optional, Tuple

import wikipedia
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


def similarity_score(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def clean_query(query: str, max_length: int = 300) -> str:
    """Clean and truncate query to acceptable length."""
    # Remove URLs and common markers
    import re
    query = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', query)
    query = re.sub(r'URL:|Description:|Summary:', '', query)
    # Remove line numbers and dots
    query = re.sub(r'^\d+\.\s*', '', query)
    # Clean up whitespace
    query = ' '.join(query.split())
    # Truncate if still too long
    return query[:max_length].strip()

@lru_cache(maxsize=1000)
def cached_wiki_search(query: str, lang: str) -> List[str]:
    """Cache Wikipedia search results."""
    cleaned_query = clean_query(query)
    if not cleaned_query:
        return []
    return wikipedia.search(cleaned_query, results=10)


class WikipediaAPIError(Exception):
    """Custom exception for Wikipedia API errors."""

    pass


class WikipediaTool(Tool):
    name: str = Field(
        "SEARCH_WIKIPEDIA_TOOL",
        description="A Wikipedia search tool, can used to fetch summaries of Wikipedia articles.",
    )
    description: str = Field(
        """Search Wikipedia for a given query and return a summary.
        It must be used when you assess you don't have enough context to answer the question.
        Only use one keyword by query.
        """,
    )

    arguments: List[ToolArgument] = [
        ToolArgument(
            name="query",
            type="string",
            description="The search term to query on Wikipedia, prefer simple concept. One keyword by query.",
        ),
        ToolArgument(
            name="lang",
            type="string",
            description="Wikipedia language code",
            default="en",
            required=False,
        ),
        ToolArgument(
            name="max_lines",
            type="int",
            description="Maximum number of lines to return, at least 100",
            default="100",
        ),
    ]

    def find_best_match(self, query: str, results: List[str]) -> Tuple[str, float]:
        """Find the best matching article from search results."""
        scores = [(result, similarity_score(query, result)) for result in results]
        return max(scores, key=lambda x: x[1])

    def try_alternate_languages(self, query: str, primary_lang: str) -> Optional[str]:
        """Try searching in alternate languages if primary search fails."""
        alternate_langs = (
            ["en", "es", "fr", "de"]
            if primary_lang not in ["en", "es", "fr", "de"]
            else []
        )
        for lang in alternate_langs:
            try:
                wikipedia.set_lang(lang)
                results = cached_wiki_search(query, lang)
                if results:
                    return results[0]
            except:
                continue
        return None

    def execute(self, query: str, lang: str = "en", max_lines: str = "500") -> str:
        """Enhanced Wikipedia search and fetch."""
        if not query.strip():
            logger.error("Query cannot be empty or whitespace.")
            return "Error: Query cannot be empty."

        cleaned_query = clean_query(query)
        if not cleaned_query:
            logger.error("Query is invalid after cleaning.")
            return "Error: Invalid query after cleaning. Please provide a simpler search term."

        wikipedia.set_lang(lang)

        try:
            search_results = cached_wiki_search(cleaned_query, lang)

            if not search_results:
                alt_result = self.try_alternate_languages(query, lang)
                if (alt_result):
                    return f"No results in {lang}, but found in another language:\n{self.fetch_summary(alt_result, max_lines)}"
                logger.warning(f"No Wikipedia articles found for '{query}'")
                return f"No Wikipedia articles found for '{query}'"

            # Enhanced confidence handling
            best_match, score = self.find_best_match(query, search_results)

            if score < 0.2:  # Very low confidence
                suggestions = "\n- ".join(search_results[:5])
                return f"Very low confidence match. Consider these alternatives:\n- {suggestions}"
            elif score < 0.4:  # Low confidence
                summary = self.fetch_summary(best_match, max_lines)
                suggestions = ", ".join(search_results[1:4])
                return f"Note: Low confidence match ({score:.2f}). Showing results for '{best_match}'\n\n{summary}\n\nAlternative topics: {suggestions}"
            elif score < 0.7:  # Medium confidence
                summary = self.fetch_summary(best_match, max_lines)
                return f"Note: Moderate match ({score:.2f}) for '{best_match}'\n\n{summary}"
            else:  # High confidence
                return self.fetch_summary(best_match, max_lines)

        except wikipedia.exceptions.DisambiguationError as e:
            # Improved disambiguation handling
            options_with_scores = [
                (option, similarity_score(query, option)) for option in e.options[:5]
            ]
            best_option = max(options_with_scores, key=lambda x: x[1])

            try:
                summary = self.fetch_summary(best_option[0], max_lines)
                other_options = [
                    opt[0] for opt in options_with_scores if opt != best_option
                ][:3]
                return f"{summary}\n\nRelated topics: {', '.join(other_options)}"
            except Exception as inner_e:
                raise WikipediaAPIError(
                    f"Multiple topics found for '{query}'. Options: {', '.join(e.options[:5])}"
                ) from inner_e

        except Exception as e:
            logger.error(f"Wikipedia API error for query '{query}': {e}")
            raise WikipediaAPIError(
                f"Failed to fetch Wikipedia content for '{query}'"
            ) from e

    def fetch_summary(self, title: str, max_lines: str) -> str:
        """Fetch and format article summary."""
        time.sleep(0.5)  # Rate limiting
        page = wikipedia.page(title, auto_suggest=False)
        summary = page.summary

        if len(summary.split(".")) > int(max_lines):
            first_n_lines = ". ".join(summary.split(".")[: int(max_lines)]) + "."
            remaining_lines = len(summary.split(".")) - int(max_lines)
            return f"{first_n_lines}\n\nNote: {remaining_lines} more lines available."

        return summary

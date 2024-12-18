import logging
import time
from functools import lru_cache
from typing import List

import wikipedia
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


def clean_query(query: str, max_length: int = 300) -> str:
    """Clean and truncate query to acceptable length."""
    import re

    query = re.sub(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        "",
        query,
    )
    query = re.sub(r"URL:|Description:|Summary:", "", query)
    query = re.sub(r"^\d+\.\s*", "", query)
    query = " ".join(query.split())
    return query[:max_length].strip()


@lru_cache(maxsize=1000)
def cached_wiki_search(query: str, lang: str) -> List[str]:
    """Cache Wikipedia search results."""
    cleaned_query = clean_query(query)
    if not cleaned_query:
        return []
    return wikipedia.search(cleaned_query, results=5)


def find_best_match(query: str, search_results: List[str]) -> str:
    """Find the best match for the query in the search results."""
    for result in search_results:
        if result.lower() == query.lower():
            return result
    return search_results[0] if search_results else None


class WikipediaAPIError(Exception):
    """Custom exception for Wikipedia API errors."""

    pass


class WikipediaTool(Tool):
    name: str = Field(
        "WIKIPEDIA_TOOL",
        description="A Wikipedia search tool for fetching article summaries.",
    )
    description: str = Field(
        """Search Wikipedia and return article summaries.
        Use simple, specific search terms for best results.""",
    )

    arguments: List[ToolArgument] = [
        ToolArgument(
            name="query",
            type="string",
            description="The search term to query on Wikipedia",
        ),
        ToolArgument(
            name="lang",
            type="string",
            description="Wikipedia language code",
            default="en",
            required=False,
        ),
        ToolArgument(
            name="number_of_articles",
            type="int",
            description="Number of articles to display in results",
            default="3",
            required=False,
        ),
        ToolArgument(
            name="max_lines_per_article",
            type="int",
            description="Maximum number of lines to show per article",
            default="100",
            required=False,
        ),
    ]

    def execute(
        self,
        query: str,
        lang: str = "en",
        number_of_articles: str = "5",
        max_lines_per_article: str = "100",
    ) -> str:
        """Search Wikipedia and fetch multiple article summaries."""
        if not query.strip():
            return "Error: Query cannot be empty."

        cleaned_query = clean_query(query)
        if not cleaned_query:
            return "Error: Invalid query after cleaning. Please provide a simpler search term."

        wikipedia.set_lang(lang)

        try:
            # Get search results
            search_results = cached_wiki_search(cleaned_query, lang)

            if not search_results:
                return f"No Wikipedia articles found for '{query}'"

            best_match = find_best_match(cleaned_query, search_results)
            if not best_match:
                return f"No relevant Wikipedia articles found for '{query}'"

            num_articles = min(int(number_of_articles), len(search_results))
            results = []

            for i, title in enumerate(search_results[:num_articles], 1):
                try:
                    summary = self.fetch_summary(title, max_lines_per_article)
                    page_url = wikipedia.page(title, auto_suggest=False).url
                    results.append(f"{i}. {title}\n{summary}\nLink: {page_url}\n")
                except wikipedia.exceptions.DisambiguationError:
                    return f"The term '{title}' is ambiguous. Please provide a more specific query."
                except wikipedia.exceptions.PageError:
                    continue  # Skip pages that do not exist
                except Exception as e:
                    logger.error(f"Error fetching article '{title}': {e}")
                    continue

            return (
                "\n".join(results)
                if results
                else f"No relevant Wikipedia articles found for '{query}'"
            )

        except Exception as e:
            logger.error(f"Wikipedia API error for query '{query}': {e}")
            return f"Failed to fetch Wikipedia content for '{query}'"

    def fetch_summary(self, title: str, max_lines: str) -> str:
        """Fetch and format article summary."""
        time.sleep(0.5)  # Rate limiting
        page = wikipedia.page(title, auto_suggest=False)
        summary = page.summary

        if len(summary.split(".")) > int(max_lines):
            return ". ".join(summary.split(".")[: int(max_lines)]) + "."

        return summary

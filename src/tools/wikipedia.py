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


class WikipediaAPIError(Exception):
    """Custom exception for Wikipedia API errors."""

    pass


class WikipediaTool(Tool):
    name: str = Field(
        "SEARCH_WIKIPEDIA_TOOL",
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
            name="max_lines",
            type="int",
            description="Maximum number of lines to return",
            default="100",
        ),
    ]

    def execute(self, query: str, lang: str = "en", max_lines: str = "100") -> str:
        """Simple Wikipedia search and fetch."""
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

            # Get first result's summary
            try:
                return self.fetch_summary(search_results[0], max_lines)
            except wikipedia.exceptions.DisambiguationError as e:
                # If disambiguation page, return first option's summary
                return self.fetch_summary(e.options[0], max_lines)

        except Exception as e:
            logger.error(f"Wikipedia API error for query '{query}': {e}")
            return f"Failed to fetch Wikipedia content for '{query}'"

    def fetch_summary(self, title: str, max_lines: str) -> str:
        """Fetch and format article summary."""
        time.sleep(0.5)  # Rate limiting
        page = wikipedia.page(title, auto_suggest=True)
        summary = page.summary

        if len(summary.split(".")) > int(max_lines):
            return ". ".join(summary.split(".")[: int(max_lines)]) + "."

        return summary

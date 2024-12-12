import logging
import time
from typing import List

import wikipedia
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class WikipediaAPIError(Exception):
    """Custom exception for Wikipedia API errors."""

    pass


class WikipediaTool(Tool):
    name: str = Field("SEARCH_WIKIPEDIA", description="A Wikipedia search tool, can used to fetch summaries of Wikipedia articles.")
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

    def execute(self, query: str, lang: str = "en", max_lines: str = "200") -> str:
        """Fetch summary from Wikipedia in a specified language."""
        if not query.strip():
            logger.error("Query cannot be empty or whitespace.")
            return "Error: Query cannot be empty."

        wikipedia.set_lang(lang)

        try:
            search_results = wikipedia.search(query, results=5)
            if not search_results:
                logger.warning(f"No Wikipedia articles found for '{query}'")
                return f"No Wikipedia articles found for '{query}'"

            time.sleep(0.5)  # Rate limiting
            page = wikipedia.page(search_results[0], auto_suggest=False)

            summary = page.summary
            if len(summary.split(".")) > int(max_lines):
                first_n_lines = ". ".join(summary.split(".")[:int(max_lines)]) + "."
                remaining_lines_count = len(summary.split(".")) - int(max_lines)
                summary = f"{first_n_lines}\n\nNote: This is the first {max_lines} lines of the article. There are {remaining_lines_count} remaining lines."

            logger.debug(f"Fetched summary for query '{query}'")
            return summary

        except wikipedia.exceptions.DisambiguationError as e:
            logger.warning(f"Disambiguation error for query '{query}': {e.options}")
            try:
                page = wikipedia.page(e.options[0], auto_suggest=False)
                summary = page.summary
                if len(summary.split(".")) > max_lines:
                    summary = ". ".join(summary.split(".")[:max_lines]) + "."
                return f"{summary}\n\nNote: This is about '{e.options[0]}'. Other related topics include: {', '.join(e.options[1:4])}"

            except Exception as inner_e:
                logger.error(
                    f"Error with disambiguation option '{e.options[0]}': {inner_e}"
                )
                raise WikipediaAPIError(
                    f"Multiple topics found for '{query}'. Try being more specific. Options include: {', '.join(e.options[:5])}"
                ) from inner_e

        except Exception as e:
            logger.error(f"Wikipedia API error for query '{query}': {e}")
            raise WikipediaAPIError(f"Failed to fetch Wikipedia content for '{query}'") from e

import logging
import time

import wikipedia  # Ensure this library is installed
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class WikipediaTool(Tool):
    name: str = Field("SEARCH_WIKIPEDIA", description="The unique name of the tool.")
    description: str = Field(
        "Search Wikipedia for a given query and return a summary.",
        description="A brief description of what the tool does."
    )
    arguments: list[ToolArgument] = Field(default=[
        ToolArgument(
            name="query",
            type="string",
            description="The search term to query on Wikipedia."
        )
    ])

    def execute(self, query: str, lang: str = "en", max_lines: int = 3) -> str:
        """Fetch summary from Wikipedia in a specified language."""
        if not query:
            return "Error: Query cannot be empty."

        wikipedia.set_lang(lang)

        try:
            search_results = wikipedia.search(query, results=5)

            if not search_results:
                return f"No Wikipedia articles found for '{query}'."

            try:
                time.sleep(0.5)
                page = wikipedia.page(search_results[0], auto_suggest=False)
                summary = page.summary
                if len(summary.split(".")) > max_lines:
                    summary = ". ".join(summary.split(".")[:max_lines]) + "."
                logger.info(f"Fetched summary for query '{query}'")
                return summary
            except wikipedia.exceptions.DisambiguationError as e:
                try:
                    page = wikipedia.page(e.options[0], auto_suggest=False)
                    summary = page.summary
                    if len(summary.split(".")) > max_lines:
                        summary = ". ".join(summary.split(".")[:max_lines]) + "."
                    return f"{summary}\n\nNote: This is about '{e.options[0]}'. Other related topics: {', '.join(e.options[1:4])}"
                except Exception as inner_e:
                    logger.error(f"Error with first disambiguation option: {inner_e}")
                    return f"Multiple topics found for '{query}'. Try being more specific. Options: {', '.join(e.options[:5])}"
        except wikipedia.exceptions.PageError as e:
            logger.error(f"Page error for query '{query}': {e}")
            return f"Error: Could not find a Wikipedia page for '{query}'. Please try a different search term."
        except Exception as e:
            logger.error(f"Wikipedia API error for query '{query}': {e}")
            return f"Error fetching data from Wikipedia: {str(e)}"
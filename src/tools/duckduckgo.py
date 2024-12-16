import logging
import time
from typing import List

try:
    from duckduckgo_search import DDGS
except ImportError:
    raise ImportError(
        "The 'duckduckgo-search' package is required. Please install it using:\n"
        "pip install duckduckgo-search"
    )

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class DuckDuckGoAPIError(Exception):
    """Custom exception for DuckDuckGo API errors."""

    pass


class DuckDuckGoSearchTool(Tool):
    name: str = Field(
        "SEARCH_DUCKDUCKGO",
        description="A DuckDuckGo search tool for finding current information on the web.",
    )
    description: str = Field(
        """Search DuckDuckGo for a given query and return relevant results.
        Use this tool when you need to find current information or web content.
        """
    )

    arguments: List[ToolArgument] = [
        ToolArgument(
            name="query",
            type="string",
            description="The search term to query on DuckDuckGo",
        ),
        ToolArgument(
            name="max_results",
            type="int",
            description="Maximum number of results to return",
            default="5",
            required=False,
        ),
    ]

    def execute(self, query: str, max_results: str = "5") -> str:
        """Execute a search query using DuckDuckGo and return results."""
        if not query.strip():
            logger.error("Query cannot be empty or whitespace.")
            return "Error: Query cannot be empty."

        try:
            max_results_int = int(max_results)
            time.sleep(0.5)  # Rate limiting

            with DDGS() as ddgs:
                # Using the generator to get search results
                results = list(ddgs.text(query, max_results=max_results_int))

            if not results:
                logger.warning(f"No results found for '{query}'")
                return f"No results found for '{query}'"

            formatted_results = []
            for idx, result in enumerate(results, 1):
                title = result.get("text", "").split(" - ")[
                    0
                ]  # First part before ' - ' is usually the title
                link = result.get("href", "No URL")
                description = result.get("text", "No description")

                formatted_results.append(
                    f"{idx}. {title}\n" f"   URL: {link}\n" f"   {description}\n"
                )

            return "\n".join(formatted_results)

        except Exception as e:
            logger.error(f"DuckDuckGo search error for query '{query}': {e}")
            raise DuckDuckGoAPIError(
                f"Failed to fetch search results for '{query}'"
            ) from e

import logging
import time
from functools import lru_cache
from typing import List

try:
    from duckduckgo_search import DDGS
except ImportError as err:
    raise ImportError(
        "The 'duckduckgo-search' package is required. Please install it using:\n"
        "pip install duckduckgo-search"
    ) from err

from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class DuckDuckGoAPIError(Exception):
    """Custom exception for DuckDuckGo API errors."""

    pass


class DuckDuckGoSearchTool(Tool):
    name: str = Field(
        "DuckDuckGoSearchTool",
        description="A DuckDuckGo search tool for finding current URL pages containing information about a query.",
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
            description="Maximum number of total results to fetch",
            default="30",
            required=False,
        ),
        ToolArgument(
            name="number_of_articles",
            type="int",
            description="Number of articles to display in results",
            default="5",
            required=False,
        ),
        ToolArgument(
            name="max_lines_per_article",
            type="int",
            description="Maximum number of lines to show per article",
            default="3",
            required=False,
        ),
    ]

    @staticmethod
    @lru_cache(maxsize=128)
    def cached_search(query: str, max_results: int) -> List[dict]:
        """Cache search results to reduce redundant API calls."""
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))

    def truncate_text(self, text: str, max_lines: int) -> str:
        """Truncate text to specified number of lines."""
        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text
        return '\n'.join(lines[:max_lines]) + '...'

    def execute(
        self, 
        query: str, 
        max_results: str = "30",
        number_of_articles: str = "5",
        max_lines_per_article: str = "3"
    ) -> str:
        """Execute a search query using DuckDuckGo and return results."""
        if not query.strip():
            logger.error("Query cannot be empty or whitespace.")
            return "Error: Query cannot be empty."

        try:
            max_results_int = int(max_results)
            num_articles = min(int(number_of_articles), max_results_int)
            max_lines = max(1, int(max_lines_per_article))

            if max_results_int <= 0:
                raise ValueError("max_results must be a positive integer.")
            
            time.sleep(0.5)  # Rate limiting

            results = self.cached_search(query, max_results_int)

            if not results:
                logger.warning(f"No results found for '{query}'")
                return f"No results found for '{query}'"

            formatted_results = []
            for idx, result in enumerate(results[:num_articles], 1):
                title = result.get("text", "").split(" - ")[0]
                link = result.get("href", "No URL")
                description = self.truncate_text(
                    result.get("text", "No description"),
                    max_lines
                )
                summary = self.truncate_text(
                    result.get("summary", "No summary"),
                    max_lines
                )

                formatted_results.append(
                    f"{idx}. {title}\n   URL: {link}\n   Description: {description}\n   Summary: {summary}\n"
                )

            logger.info(
                f"Search successful: {len(formatted_results)} articles from {len(results)} results for '{query}'"
            )
            return "\n".join(formatted_results)

        except ValueError as ve:
            logger.error(f"Value error for query '{query}': {ve}")
            return f"Error: {ve}"
        except DuckDuckGoAPIError as e:
            logger.error(f"DuckDuckGoAPIError for query '{query}': {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error for query '{query}': {e}")
            raise DuckDuckGoAPIError(
                f"Failed to fetch search results for '{query}'"
            ) from e

import logging
import time

import wikipedia  # Ensure this library is installed

logger = logging.getLogger(__name__)


logger.setLevel(logging.INFO)

def use_wikipedia(query: str, lang: str = "en",max_lines: int = 700) -> str:
    """Fetch summary from Wikipedia in a specified language."""
    if not query:
        return "Error: Query cannot be empty."

    # Set language for Wikipedia API
    wikipedia.set_lang(lang)

    try:
        # First try to search for the query to get possible matches
        search_results = wikipedia.search(query, results=5)

        if not search_results:
            return f"No Wikipedia articles found for '{query}'."

        # Try to get the most relevant page
        try:
            # Introduce a delay to respect rate limiting
            time.sleep(0.5)
            page = wikipedia.page(search_results[0], auto_suggest=False)
            summary = page.summary
            if len(summary.split(".")) > max_lines:
                # Limit to first 3 sentences if summary is long
                summary = ". ".join(summary.split(".")[:max_lines]) + "."
            logger.info(f"Fetched summary for query '{query}'")
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            # If disambiguation occurs, try the first option
            try:
                page = wikipedia.page(e.options[0], auto_suggest=False)
                summary = page.summary
                if len(summary.split(".")) > 3:
                    summary = ". ".join(summary.split(".")[:3]) + "."
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

import logging

logger = logging.getLogger(__name__)

def use_wikipedia(self, query: str) -> str:
    # Implementation for Wikipedia API call
    # Example: fetching summary from Wikipedia
    try:
        import wikipedia

        return wikipedia.summary(query, sentences=2)
    except Exception as e:
        logger.error(f"Wikipedia API error: {e}")
        return f"Error fetching data from Wikipedia: {e}"

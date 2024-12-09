from typing import Callable

from .enums import Name
from .models import Choice
from .tool import Tool


class Manager:
    """
    Manages tool registration, selection, and execution.
    """

    def __init__(self) -> None:
        self.tools: dict[Name, Tool] = {}

    def register_tool(self, name: Name, func: Callable[[str], str]) -> None:
        """
        Register a new tool.
        """
        self.tools[name] = Tool(name, func)

    def act(self, name: Name, query: str) -> str:
        """
        Retrieve and use a registered tool to process the given query.

        Parameters:
            name (Name): The name of the tool to use.
            query (str): The input query string.

        Returns:
            str: The result of the tool's execution or an error message.
        """
        if name not in self.tools:
            raise ValueError(f"Tool {name} not registered")

        processed_query = query.split(" ", 1)[1] if " " in query else query
        return self.tools[name].use(processed_query)

    def choose_tool(self, query: str) -> Choice:
        """
        Choose the appropriate tool based on the query prefix.

        Example:
            Queries starting with "/people" use Wikipedia.
            Queries starting with "/search" use SerpApi.
        """
        if query.startswith("/people"):
            return Choice(
                name=Name.WIKIPEDIA,
                reason="Query starts with /people, using Wikipedia for biographical information.",
            )
        if query.startswith("/search"):
            return Choice(
                name=Name.SERPAPI,
                reason="Query starts with /search, using SerpApi for web search results.",
            )
        if query.startswith("/location"):
            return Choice(
                name=Name.GOOGLE,
                reason="Query starts with /location, using Google for location-specific information.",
            )
        return Choice(
            name=Name.NONE,
            reason="Unsupported query prefix, unable to determine the appropriate tool.",
        )

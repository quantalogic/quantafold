from enum import Enum, auto


class Name(Enum):
    """Enumeration for tool names available to the agent."""

    WIKIPEDIA = auto()
    GOOGLE = auto()
    SERPAPI = auto()
    NONE = auto()

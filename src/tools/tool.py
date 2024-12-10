import logging
from typing import Callable

from models.observation import Observation

logger = logging.getLogger(__name__)


class Tool:
    def __init__(self, tool_model, func: Callable[[str], str]):
        self.tool_model = tool_model
        self.name = tool_model.name
        self.func = func

    def use(self, query: str) -> Observation:
        try:
            return self.func(query)
        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {e}")
            return str(e)

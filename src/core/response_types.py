from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Argument:
    name: str
    value: str

@dataclass
class Action:
    tool_name: str
    reason: str
    arguments: List[Argument]

@dataclass
class Step:
    name: str
    description: str
    reason: str
    result: Optional[str] = None
    depends_on_steps: Optional[List[str]] = None

@dataclass
class Thought:
    reasoning: str
    to_do: List[Step]
    done: List[Step]

@dataclass
class Response:
    thought: Thought
    action: Optional[Action] = None
    final_answer: Optional[str] = None

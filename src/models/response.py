import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra, Field, StringConstraints, validator
from typing_extensions import Annotated

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Step(BaseModel):
    """Represents a step in the process to achieve the goal."""

    name: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ..., description="The name of the step, must be in snake_case."
    )
    description: str = Field(..., description="A detailed description of the step.")
    reason: str = Field(..., description="The reasoning behind selecting this step.")
    result: Optional[str] = Field(
        None, description="Summary of the result from executing this step."
    )
    tool_name: Optional[str] = Field(
        None, description="The tool associated with this step"
    )

    arguments: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arguments needed for the tool, as key-value pairs.",
    )

    depends_on_steps: List[str] = Field(
        default_factory=list,
        description="List of step names that this step depends on.",
    )


class Thought(BaseModel):
    """Represents the reasoning and planned actions of the agent."""

    reasoning: str = ""  # Set default empty string
    to_do: List[Step] = Field(
        default_factory=list, description="List of planned steps to address the query."
    )
    done: List[Step] = Field(
        default_factory=list, description="List of completed steps with results."
    )


class Action(BaseModel):
    """Represents the action to be carried out by the agent."""

    step_name: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ..., description="The name of the step to be executed."
    )

    tool_name: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        default="no_tool", description="The name of the tool to be used."
    )
    reason: str = Field(
        default="", description="Reason for selecting this specific tool."
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments needed for the tool, as key-value pairs.",
    )
    result: Optional[str] = Field(
        None, description="Summary of the result from executing this action."
    )


class Response(BaseModel):
    """Response model representing the AI's response structure."""

    thought: Optional[Thought] = None
    action: Optional[Action] = None
    final_answer: Optional[str] = None

    @validator("*", pre=True)
    def validate_response(cls, v, values):
        if (
            "answer" in values
            and "action" in values
            and values["answer"] is None
            and values["action"] is None
        ):
            raise ValueError("Either answer or action must be present")
        return v

    class Config:
        extra = Extra.allow  # Allow additional fields not defined in the model


# Example usage with logging
if __name__ == "__main__":
    response_data = {
        "thought": {
            "reasoning": "Given the current context and previous steps, the following actions are required.",
            "to_do": [
                {
                    "name": "gather_data",
                    "description": "Collect relevant data from the database.",
                    "reason": "Data is necessary for the analysis.",
                }
            ],
            "done": [],
        },
        "action": {
            "tool_name": "data_collector",
            "reason": "Selected for its efficiency in gathering large data sets.",
            "arguments": {"database": "main_db", "limit": 100},
        },
    }

    try:
        valid_response = Response(**response_data)
        logger.info("Response validated successfully.")
        print(valid_response.model_dump_json(indent=2))
    except ValueError as e:
        logger.error(f"Validation Error: {e}")

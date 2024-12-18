from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ToolArgument(BaseModel):
    name: str = Field(..., description="The name of the argument.")
    type: Literal["string", "int"] = Field(
        ..., description="The type of the argument (e.g., string or integer)."
    )
    description: Optional[str] = Field(
        None, description="A brief description of the argument."
    )
    required: bool = Field(
        False, description="Indicates if the argument is required."
    )
    default: Optional[str] = Field(
        None, description="The default value for the argument."
    )


class Tool(BaseModel):
    model_config = ConfigDict(extra="forbid")  # V2 style configuration
    
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(
        ..., description="A brief description of what the tool does."
    )
    arguments: List[ToolArgument] = Field(
        default_factory=list, description="A list of arguments the tool accepts."
    )
    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation."
    )
    need_parent_context: bool = Field(
        False, description="Indicates if the tool needs the parent context.",
        exclude=True
    )

    @field_validator("arguments", mode="before")  # V2 style validator
    @classmethod
    def validate_arguments(cls, v: Any) -> List[ToolArgument]:
        """Validate the arguments list."""
        if isinstance(v, list):
            return [
                ToolArgument(**arg) if isinstance(arg, dict) else arg
                for arg in v
            ]
        return []

    def execute(self, **kwargs) -> str:
        """Execute the tool with provided arguments."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def to_json(self) -> str:
        """Convert the tool to a JSON string representation."""
        return self.model_dump_json()

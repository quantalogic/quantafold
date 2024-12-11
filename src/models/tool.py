from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


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
    model_config = {"extra": "forbid"}  # Disallow extra fields
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

    @validator("arguments", each_item=True)
    def validate_arguments(cls, arg):
        if not isinstance(arg, ToolArgument):
            raise ValueError("All items in arguments must be instances of ToolArgument")
        return arg

    def execute(self, **kwargs) -> str:
        """Execute the tool with provided arguments."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def to_json(self) -> str:
        """Convert the tool to a JSON string representation.

        Returns:
            str: A JSON string representing the tool
        """
        return self.model_dump_json()

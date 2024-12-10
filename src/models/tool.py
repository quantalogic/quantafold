from typing import Optional

from pydantic import BaseModel, Field


class ToolArgument(BaseModel):
    name: str = Field(..., description="The name of the argument.")
    type: str = Field(
        ..., description="The type of the argument (e.g., string, integer)."
    )
    description: Optional[str] = Field(
        None, description="A brief description of the argument."
    )


class Tool(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(
        ..., description="A brief description of what the tool does."
    )
    arguments: list[ToolArgument] = Field(
        [], description="A list of arguments the tool accepts."
    )

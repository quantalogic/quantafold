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
    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation."
    )

    def execute(self, **kwargs) -> str:
        """Execute the tool with the provided arguments."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def get_xml_example(self) -> str:
        """Generate an XML example for the tool."""
        # Start with the tool description as XML comment
        xml = f"<!-- {self.description} -->\n"

        # Add the tool name tag
        xml += f"<{self.name}>\n"

        # Add parameters as direct tags
        for arg in self.arguments:
            xml += f"  <{arg.name}>"
            if arg.description:
                xml += f"{arg.description}"
            else:
                xml += f"Example {arg.type} value"
            xml += f"</{arg.name}>\n"

        # Close the tool tag
        xml += f"</{self.name}>"

        return xml

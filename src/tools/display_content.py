import logging
from typing import List, Optional

from models.tool import Tool, ToolArgument
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

logger = logging.getLogger(__name__)


class DisplayStyle(BaseModel):
    """Configuration for display styling."""

    theme: str = "default"
    panel: bool = False
    panel_title: Optional[str] = None
    panel_border_style: str = "blue"
    syntax_theme: str = "monokai"


class DisplayContentError(Exception):
    """Custom exception for DisplayContent errors."""

    pass


class DisplayContentTool(Tool):
    name: str = Field("DisplayContentTool", description="Display content tool.")
    description: str = Field(
        "Display content to the user with rich formatting and styling options.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="content",
                type="string",
                description="The content to display to the user.",
            ),
            ToolArgument(
                name="content_type",
                type="string",
                description="Type of content (text, code, markdown)",
                optional=True,
            ),
            ToolArgument(
                name="style",
                type="string",
                description="Styling configuration for display (JSON-encoded string)",
                optional=True,
            ),
        ]
    )

    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation."
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._console = Console()

    def execute(
        self,
        content: str,
        content_type: Optional[str] = "text",
        style: Optional[str] = None,
    ) -> str:
        """
        Display content with rich formatting.

        Args:
            content (str): Content to display
            content_type (str, optional): Type of content. Defaults to "text".
            style (str, optional): JSON-encoded styling configuration. Defaults to None.

        Returns:
            str: The original content
        """
        try:
            # Parse style configuration
            import json
            style_dict = json.loads(style) if style else {}
            display_style = DisplayStyle(**style_dict)

            # Create a console with custom theme if specified
            console = Console(theme=Theme({display_style.theme: display_style.theme}))

            # Render content based on type
            if content_type == "code":
                rendered_content = Syntax(
                    content,
                    "python",  # Default to Python, can be extended
                    theme=display_style.syntax_theme,
                    line_numbers=True,
                )
            elif content_type == "markdown":
                rendered_content = Markdown(content)
            else:
                rendered_content = Text(content)

            # Optional panel wrapping
            if display_style.panel:
                rendered_content = Panel(
                    rendered_content,
                    title=display_style.panel_title or "Content",
                    border_style=display_style.panel_border_style,
                )

            # Display the content
            console.print(rendered_content)

            return content

        except Exception as e:
            error_msg = f"Display error: {str(e)}"
            logger.error(error_msg)
            raise DisplayContentError(error_msg) from e

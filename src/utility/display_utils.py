import json
import logging
from typing import Any, Dict, Optional, Union

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.theme import Theme

logger = logging.getLogger(__name__)


class DisplayConfig:
    """Configuration class for display settings."""

    def __init__(
        self,
        theme: str = "default",
        panel: bool = False,
        panel_title: Optional[str] = None,
        panel_border_style: str = "blue",
        syntax_theme: str = "monokai",
        language: str = "python",
    ):
        self.theme = theme
        self.panel = panel
        self.panel_title = panel_title
        self.panel_border_style = panel_border_style
        self.syntax_theme = syntax_theme
        self.language = language


def render_content(
    content: str,
    content_type: str = "text",
    config: Optional[Union[DisplayConfig, Dict[str, Any]]] = None,
) -> Any:
    """
    Render content with rich formatting.

    Args:
        content (str): Content to render
        content_type (str): Type of content (text, code, markdown)
        config (DisplayConfig, optional): Display configuration

    Returns:
        Rendered rich content
    """
    try:
        # Handle config initialization
        if config is None:
            config = DisplayConfig()
        elif isinstance(config, dict):
            config = DisplayConfig(**config)

        # Create console with theme
        console = Console(theme=Theme({config.theme: config.theme}))

        # Render content based on type
        if content_type == "code":
            rendered_content = Syntax(
                content,
                config.language,
                theme=config.syntax_theme,
                line_numbers=True,
            )
        elif content_type == "markdown":
            rendered_content = Markdown(content)
        else:
            rendered_content = Text(content)

        # Optional panel wrapping
        if config.panel:
            rendered_content = Panel(
                rendered_content,
                title=config.panel_title or "Content",
                border_style=config.panel_border_style,
            )

        return rendered_content

    except Exception as e:
        logger.error(f"Content rendering error: {e}")
        raise


def print_content(
    content: str,
    content_type: str = "text",
    config: Optional[Union[DisplayConfig, Dict[str, Any]]] = None,
) -> str:
    """
    Print content with rich formatting.

    Args:
        content (str): Content to print
        content_type (str): Type of content (text, code, markdown)
        config (DisplayConfig, optional): Display configuration

    Returns:
        Original content string
    """
    console = Console()
    rendered_content = render_content(content, content_type, config)
    console.print(rendered_content)
    return content


def format_content_from_json(content: str, style: Optional[str] = None) -> Any:
    """
    Format content using JSON-encoded style configuration.

    Args:
        content (str): Content to format
        style (str, optional): JSON-encoded style configuration

    Returns:
        Rendered rich content
    """
    try:
        style_dict = json.loads(style) if style else {}
        return render_content(content, config=style_dict)
    except json.JSONDecodeError:
        logger.error("Invalid JSON style configuration")
        raise

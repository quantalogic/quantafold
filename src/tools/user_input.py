import logging
from typing import List

from models.tool import Tool, ToolArgument
from pydantic import Field
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

logger = logging.getLogger(__name__)
console = Console()

class UserInputTool(Tool):
    name: str = Field("USER_INPUT", description="A tool to get input from the user.")
    description: str = Field(
        "Prompts the user for input and returns their response. Can handle multiline input.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="prompt",
                type="string",
                description="The prompt to show to the user when asking for input.",
            ),
            ToolArgument(
                name="multiline",
                type="string",
                description="Set to 'true' to accept multiline input. User can enter multiple lines until they enter an empty line.",
                default="false",
            ),
        ]
    )

    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation."
    )

    def _format_prompt(self, prompt: str, is_multiline: bool) -> None:
        """Format and display the input prompt with styling."""
        # Create a panel with the prompt
        prompt_panel = Panel(
            Markdown(prompt),
            title="[bold cyan]Input Required[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(prompt_panel)
        
        if is_multiline:
            console.print("✏️  Enter multiple lines of text (submit an empty line to finish)", style="italic grey70")

    def execute(self, prompt: str, multiline: str = "false") -> str:
        """Get input from the user with enhanced UI/UX."""
        try:
            is_multiline = multiline.lower() == "true"
            self._format_prompt(prompt, is_multiline)

            if not is_multiline:
                # Single line input with custom prompt
                console.print("[cyan]>[/cyan] ", end="")
                return input()
            else:
                # Multiline input with visual feedback
                lines = []
                line_number = 1
                
                while True:
                    # Show line numbers for better orientation
                    console.print(f"[dim]│ {line_number}[/dim] ", end="")
                    line = input()
                    if not line:
                        if not lines:  # Don't allow empty input
                            console.print("ℹ️  At least one line is required", style="italic grey70")
                            continue
                        break
                    lines.append(line)
                    line_number += 1

                # Show success message
                console.print("✨ Input captured successfully!", style="green")
                return "\n".join(lines)

        except Exception as e:
            error_msg = f"Error getting user input: {str(e)}"
            logger.error(error_msg)
            console.print(f"❌ {error_msg}", style="bold red")
            return f"Error: Failed to get user input - {str(e)}"

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme

from core.agent import Agent
from core.generative_model import GenerativeModel
from tools.file_reader import FileReaderTool
from tools.shell_command import ShellCommandTool
from tools.wikipedia import WikipediaTool

# Configure rich console
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
    }
)
console = Console(theme=custom_theme)

# Configure logging with rich handler
logging.basicConfig(
    level=logging.ERROR,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)

MODEL_NAME = "gpt-4o-mini"


def get_multiline_input() -> str:
    """Get multiline input from the user. Empty line (double Enter) to finish."""
    console.print("[info]Enter your question (press Enter twice to submit):[/]")
    lines = []
    while True:
        line = Prompt.ask("", show_default=False).rstrip()
        if not line and lines:  # Empty line and we have content
            break
        if line:  # Add non-empty lines
            lines.append(line)
    return "\n".join(lines)


def main() -> None:
    model = GenerativeModel(model=MODEL_NAME)
    agent = Agent(model=model)

    wikipedia_tool = WikipediaTool()
    shell_command_tool = ShellCommandTool()

    agent.register(wikipedia_tool)
    agent.register(shell_command_tool)
    agent.register(FileReaderTool())

    # Build tool descriptions for welcome message
    tool_descriptions = "".join(
        f"* {tool.name.upper()}: {tool.description.strip().split('.')[0].strip()}\n"
        for tool in agent.tools.values()
    )

    # Welcome message
    welcome_md = f"""
    # 🤖 AI Assistant

    Welcome to your AI Assistant! 
    
    This tool can help you with the following:

    {tool_descriptions}

    Type 'quit' or 'exit' to end the session.
    Enter your questions in multiple lines - press Enter twice to submit.
    """
    console.print(Panel(Markdown(welcome_md), border_style="cyan"))

    while True:
        try:
            query = get_multiline_input().strip()

            if query.lower() in ["quit", "exit"]:
                console.print("\n[success]👋 Goodbye! Have a great day![/]")
                break

            if not query:
                console.print("[warning]⚠️  Please enter a question.[/]")
                continue

            console.print("[bold cyan]Thinking...[/]")
            response = agent.execute(query)

            # Format the response as a panel with markdown
            console.print(
                Panel(
                    Markdown(response),
                    title="[bold green]Response[/]",
                    border_style="green",
                )
            )

        except KeyboardInterrupt:
            console.print("\n[warning]Operation cancelled by user[/]")
            break
        except Exception as e:
            console.print(f"\n[error]❌ Error: {str(e)}[/]")
            console.print("[info]Please try again with a different question.[/]")


if __name__ == "__main__":
    main()

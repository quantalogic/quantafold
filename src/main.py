import locale
import logging
import sys

from core.agent import Agent  # noqa: E402
from core.generative_model import GenerativeModel
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from tools.display_content import DisplayContentTool
from tools.file_reader import FileReaderTool
from tools.file_tree import FileTreeTool
from tools.file_writer import FileWriterTool
from tools.llm_agent import LLMAgentTool
from tools.shell_command import ShellCommandTool
from tools.user_input import UserInputTool
from tools.wikipedia import WikipediaTool

# Explicitly set UTF-8 encoding
sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")

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

# MODEL_NAME = "gpt-4o-mini"
# MODEL_NAME = "ollama/qwen2.5-coder:14b"
# MODEL_NAME = "ollama/exaone3.5:2.4b"
# MODEL_NAME = "bedrock/amazon.nova-micro-v1:0"
# MODEL_NAME = "bedrock/amazon.nova-lite-v1:0"
MODEL_NAME = "bedrock/amazon.nova-pro-v1:0"


def get_multiline_input() -> str:
    """Get multiline input from the user. Empty line (double Enter) to finish."""
    console.print("[info]Enter your question (press Enter twice to submit):[/]")
    lines = []
    while True:
        try:
            line = Prompt.ask("", show_default=False)
            if line is None:  # Handle potential None return
                break
            line = line.rstrip()
            if not line and lines:  # Empty line and we have content
                break
            if line:  # Add non-empty lines
                lines.append(line)
        except UnicodeEncodeError:
            console.print(
                "[error]Error: Invalid characters in input. Please try again.[/error]"
            )
            continue
    return "\n".join(lines)


def main() -> None:
    model = GenerativeModel(model=MODEL_NAME)
    agent = Agent(model=model)

    llm_agent_tool = LLMAgentTool(model=model)

    #    agent.register(WikipediaTool())
    agent.register(ShellCommandTool())
    agent.register(FileReaderTool())
    agent.register(FileWriterTool())
    agent.register(UserInputTool())
    agent.register(llm_agent_tool)
    agent.register(WikipediaTool())
    agent.register(DisplayContentTool())
    agent.register(FileTreeTool())

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

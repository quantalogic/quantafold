import logging
import os
import xml.etree.ElementTree as ET  # noqa: N817
from datetime import datetime
from typing import Any, Dict, Optional

from core.agent_template import load_template
from core.generative_model import GenerativeModel
from models.message import Message
from models.responsestats import ResponseStats
from models.tool import Tool
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

os.environ["LITELLM_LOG_LEVEL"] = "ERROR"
logging.getLogger().setLevel(logging.ERROR)


# Configure rich console with no logging
console = Console(
    theme=Theme(
        {"info": "cyan", "warning": "yellow", "error": "red", "success": "green"}
    )
)

# Remove all handlers from root logger
logging.getLogger().handlers = []

# Configure logging with rich, but only for our app
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True, show_time=False, show_path=False, markup=True)
    ],
)

# Set our logger to INFO while keeping others at ERROR
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure no logging propagation for any existing loggers
for name in logging.root.manager.loggerDict:
    if name != __name__:  # Don't affect our own logger
        logging.getLogger(name).setLevel(logging.ERROR)
        logging.getLogger(name).propagate = False


class Agent:
    def __init__(self, model: GenerativeModel) -> None:
        self.model = model
        self.tools: dict[str, Tool] = {}
        self.messages: list[Message] = []
        self.query = ""
        self.max_iterations = 20
        self.current_iteration = 0
        self.prompt_template = load_template()

    def register(self, tool: Tool) -> None:
        """Register a new tool with the agent."""
        self.tools[tool.name.upper()] = tool

    def add_to_session_memory(self, role: str, content: str) -> None:
        """Add a new message to the session history."""
        timestamp = datetime.utcnow().isoformat()
        self.messages.append(Message(role=role, content=content, timestamp=timestamp))
        # Display the message with rich formatting
        role_style = {
            "assistant": "cyan",
            "user": "green",
            "tool_execution": "yellow",
        }.get(role.lower(), "white")

        console.print(
            Panel(
                Text(content, style="white"),
                title=f"[{role_style}]{role.upper()}[/{role_style}]",
                subtitle=f"[dim]{timestamp}[/dim]",
                border_style=role_style,
            )
        )

    def get_history(self) -> str:
        """Get formatted session history."""
        history_list: list[str] = []
        current_sequence: int = 1
        current_role = ""

        # Create a table for history display
        table = Table(
            title="Session History", show_header=True, header_style="bold magenta"
        )
        table.add_column("Sequence", style="dim")
        table.add_column("Role", style="cyan")
        table.add_column("Content", style="white", overflow="fold")

        for msg in self.messages:
            current_role = msg.role.upper()
            if current_role == "TOOL_EXECUTION":
                current_sequence += 1

            table.add_row(
                str(current_sequence), Text(current_role, style="bold"), msg.content
            )

        console.print(table)

        # Still maintain the string version for the model
        history_list.append(
            f"------------------------- SEQUENCE: {current_sequence} -------------------------"
        )
        for msg in self.messages:
            current_role = msg.role.upper()
            history_list.append(f"{current_role}:\n{msg.content}\n")
            if current_role == "TOOL_EXECUTION":
                current_sequence += 1
                history_list.append(
                    f"------------------------- SEQUENCE: {current_sequence} -------------------------"
                )

        return "\n".join(history_list)

    def think(self) -> None:
        """Execute the thinking step of the agent."""
        self.current_iteration += 1
        if self.current_iteration > self.max_iterations:
            console.print("[warning]Reached maximum iterations. Stopping.[/warning]")
            return

        # Display current status
        status_panel = Panel(
            f"""[bold]Current Status[/bold]
Iteration: {self.current_iteration}/{self.max_iterations}
Active Tools: {len(self.tools)}
Messages in History: {len(self.messages)}""",
            title="Agent Status",
            border_style="blue",
        )
        console.print(status_panel)

        # Collect XML examples from all tools
        tool_examples = "\n".join([tool.to_json() for tool in self.tools.values()])

        prompt = self.prompt_template.format(
            query=self.query,
            history=self.get_history(),
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            remaining_iterations=self.max_iterations - self.current_iteration,
            tools=tool_examples,
        )

        response = self.ask_llm(prompt)
        self.add_to_session_memory("assistant", f"Thought: {response.content}")
        self.decide(response.content)

    def extract(self, response: str) -> ET.Element:
        """Extract and validate XML response."""
        try:
            response = response.strip()
            if response.startswith("```xml"):
                response = response[6:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            root = ET.fromstring(response)

            if root.tag != "response":
                raise ValueError("Root element must be 'response'.")

            thought = root.find("thought")
            if thought is None or not thought.text:
                raise ValueError(
                    "Response must contain a 'thought' element with content."
                )

            action = root.find("action")
            answer = root.find("answer")

            if action is not None:
                tool_name = action.find("tool_name")
                reason = action.find("reason")
                arguments = action.find("arguments")

                if tool_name is None or reason is None:
                    raise ValueError(
                        "Action element must contain 'tool_name' and 'reason' elements."
                    )

                if tool_name.text.upper() not in self.tools:
                    console.print(f"[error]Unknown tool name: {tool_name.text}[/error]")
                    raise ValueError(f"Unknown tool name: {tool_name.text}")

            elif answer is not None:
                if not answer.text:
                    raise ValueError("'answer' element must contain text.")
            else:
                raise ValueError(
                    "Response must contain either 'action' or 'answer' element."
                )

            return root

        except ET.ParseError as e:
            clean_response = response.replace("\n", "\\n")
            console.print("[error]Invalid XML format in response[/error]")
            console.print(
                Panel(clean_response, title="Invalid Response", border_style="red")
            )
            logger.error(f"XML parse error: {str(e)}")
            raise ValueError("Response is not valid XML. Please try again.") from e
        except ValueError as e:
            console.print(f"[error]Validation error: {str(e)}[/error]")
            raise
        except Exception as e:
            console.print(
                f"[error]Unexpected error while parsing response: {str(e)}[/error]"
            )
            raise ValueError("Failed to process the response. Please try again.") from e

    def decide(self, response: str) -> None:
        """Process the response and decide next action."""
        try:
            parsed_response = self.extract(response)

            if parsed_response.find("action") is not None:
                action = parsed_response.find("action")
                tool_name = action.find("tool_name")

                if tool_name is None or not tool_name.text:
                    raise ValueError("Tool name is missing or empty")

                tool_name_str = tool_name.text.upper()
                if tool_name_str not in self.tools:
                    raise ValueError(f"Unsupported tool: {tool_name_str}")

                # Extract arguments
                args = {}
                arguments_elem = action.find("arguments")
                if arguments_elem is not None:
                    for arg in arguments_elem.findall("arg"):
                        name = arg.find("name")
                        value = arg.find("value")
                        if (
                            name is not None
                            and value is not None
                            and name.text
                            and value.text
                        ):
                            args[name.text] = value.text

                self.act(tool_name_str, args)

            elif parsed_response.find("answer") is not None:
                answer = parsed_response.find("answer")
                if answer is None or not answer.text:
                    raise ValueError("Answer element is empty")

                answer_text = answer.text.strip()
                self.add_to_session_memory("assistant", f"{answer_text}")

            else:
                raise ValueError(
                    "Response must contain either 'action' or 'answer' element."
                )

        except Exception as e:
            error_msg = f"Error processing response: {str(e)}"
            console.print(f"[error]{error_msg}[/error]")
            logger.error(error_msg)
            self.add_to_session_memory("system", f"Error: {error_msg}")
            if self.current_iteration < self.max_iterations:
                self.think()

    def act(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Execute a tool with the given arguments."""
        tool = self.tools.get(tool_name)
        if tool:
            try:
                # Convert argument types based on tool argument definitions
                converted_args = self._convert_arguments(tool, arguments)

                # Check if the tool needs validation
                if tool.need_validation:
                    # Create a nicely formatted panel showing the command details
                    command_panel = Panel(
                        f"""[bold]Command Details[/bold]
Tool: {tool_name}
Arguments: {converted_args}

[italic]This command requires your permission to execute. Would you like to proceed?[/italic]
""",
                        title="🔒 Permission Required",
                        border_style="yellow",
                    )
                    console.print(command_panel)

                    # Ask for permission
                    response = (
                        input("\n[?] Please type 'y' to approve or 'n' to deny: ")
                        .lower()
                        .strip()
                    )
                    if response != "y":
                        self.add_to_session_memory(
                            "system",
                            "Command execution cancelled by user.",
                        )
                        self.think()
                        return

                # Execute tool with converted arguments
                result = tool.execute(**converted_args)
                observation = f"Observation from {tool_name}: {result}"
                self.add_to_session_memory(
                    "tool_execution",
                    f"Executed tool :\n'{tool_name}' with arguments:\n{converted_args}.\nResult:\n{observation}\n",
                )
                self.think()
            except Exception as e:
                error_msg = f"Error executing tool {tool_name}: {str(e)}"
                console.print(f"[error]{error_msg}[/error]")
                logger.error(error_msg)
                self.add_to_session_memory("system", f"Error: {error_msg}")
                self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.think()

    def _convert_arguments(
        self, tool: Tool, arguments: dict[str, str]
    ) -> dict[str, Any]:
        """Convert arguments to their appropriate types based on tool argument definitions."""
        converted = {}
        type_converters = {
            "string": str,
            "int": int,
            "float": float,
            "bool": lambda x: x.lower() == "true",
        }

        for arg in tool.arguments:
            if arg.name in arguments:
                value = arguments[arg.name]
                try:
                    if arg.type in type_converters:
                        converted[arg.name] = type_converters[arg.type](value)
                    else:
                        converted[arg.name] = value  # Keep as string if type unknown
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Failed to convert argument '{arg.name}' to {arg.type}: {str(e)}"
                    )
            elif arg.required:
                raise ValueError(f"Missing required argument: {arg.name}")
            elif arg.default is not None:
                converted[arg.name] = arg.default

        return converted

    def execute(self, query: str) -> str:
        """Execute the agent with a given query."""
        try:
            self.query = query
            self.current_iteration = 0
            self.messages = []
            self.add_to_session_memory("user", f"Query: {query}")
            self.think()

            # Return the last answer from the session history
            for msg in reversed(self.messages):
                if msg.role == "assistant":
                    return msg.content

            return "Unable to provide an answer after maximum iterations."

        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return f"An error occurred while processing your query: {str(e)}"

    def ask_llm(self, prompt: str) -> ResponseStats:
        """Get response from the language model."""
        return self.model.generate(prompt)

    def generate_xml_response(
        self,
        thought: str,
        action: Optional[dict[str, Any]] = None,
        answer: Optional[str] = None,
    ) -> str:
        """Generate a well-formed XML response."""
        root = ET.Element("response")

        thought_elem = ET.SubElement(root, "thought")
        thought_elem.text = thought

        if action:
            action_elem = ET.SubElement(root, "action")

            tool_name = ET.SubElement(action_elem, "tool_name")
            tool_name.text = action["tool_name"]

            reason = ET.SubElement(action_elem, "reason")
            reason.text = action["reason"]

            if "arguments" in action:
                args_elem = ET.SubElement(action_elem, "arguments")
                for arg_name, arg_value in action["arguments"].items():
                    arg_elem = ET.SubElement(args_elem, "arg")
                    name = ET.SubElement(arg_elem, "name")
                    name.text = arg_name
                    value = ET.SubElement(arg_elem, "value")
                    value.text = str(arg_value)

        if answer:
            answer_elem = ET.SubElement(root, "answer")
            answer_elem.text = answer

        return ET.tostring(root, encoding="unicode", method="xml")

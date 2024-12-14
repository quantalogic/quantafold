import logging
import re
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from core.agent_template import output_format, query_template
from core.generative_model import GenerativeModel
from models.message import Message
from models.pydantic_to_xml import PydanticToXMLSerializer
from models.response import Action, Response, ResponseWithActionResult
from models.response_parser import ResponseParser
from models.tool import Tool
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax


class AgentState(Enum):
    READY = "ready"
    THINKING = "thinking"
    DECIDING = "deciding"
    ERROR = "error"
    COMPLETE = "complete"


class StepResult(BaseModel):
    step: str = Field(description="The step name")
    result: str = Field(description="The result of the step")


class Agent:
    def __init__(self, model: GenerativeModel, max_iterations: int = 20):
        self.model = model
        self.tools: dict[str, Tool] = {}
        self.memory: list[ResponseWithActionResult] = []
        self.step_results: list[StepResult] = []
        self.query: str = ""
        self.max_iterations: int = max_iterations
        self.current_iteration: int = 0
        self.state: AgentState = AgentState.READY
        self.logger = logging.getLogger(__name__)
        # Configure root logger to filter LiteLLM messages
        self.console = Console()

    def register(self, tool: Tool) -> None:
        """Register a new tool with the agent."""
        self.tools[tool.name.upper()] = tool
        self.logger.info(f"Registered tool: {tool.name}")

    def execute(self, query: str) -> str:
        """Main execution entry point"""
        try:
            self._reset_state(query)
            return self._run_thinking_loop()
        except Exception as e:
            self.logger.error(f"Execution error: {traceback.format_exc()}")
            return f"Error during execution:\n{traceback.format_exc()}"

    def _reset_state(self, query: str) -> None:
        """Reset agent state for new execution"""
        self.query = query
        self.messages = []
        self.memory = []
        self.current_iteration = 0
        self.state = AgentState.READY

    def _run_thinking_loop(self) -> str:
        """Main thinking loop"""
        while self.current_iteration < self.max_iterations:
            try:
                if not self._think():
                    break
            except Exception as e:
                self.state = AgentState.ERROR
                error_trace = traceback.format_exc()
                self.console.print(f"[red]Error during thinking:[/red]\n{error_trace}")
                return f"Error during thinking:\n{error_trace}"

        return self._get_final_answer()

    def _think(self) -> bool:
        """Execute one thinking iteration"""
        self.state = AgentState.THINKING
        self.current_iteration += 1

        if self.current_iteration > self.max_iterations:
            return False

        self._display_status()
        response = self._get_llm_response()
        return self._decide(response)

    def _decide(self, response: Response) -> bool:
        """Process response and decide next action"""
        self.state = AgentState.DECIDING

        print("Decide:\n")
        print(response.model_dump_json(indent=2))

        if response.answer:
            self._add_to_memory(response)
            return False

        if response.action:
            result = self._handle_action(response.action)
            # Convert result to string to ensure type compatibility
            result_str = str(result) if result is not None else None
            response_with_memory = ResponseWithActionResult(
                thought=response.thought,
                action=response.action,
                action_result=result_str,
            )
            self._add_to_memory(response_with_memory)
            return True

        raise ValueError(
            f"No answer or action found in response: {response.model_dump_json(indent=2)}"
        )

    def _handle_action(self, action: Action) -> str:
        """Handle tool execution"""
        tool_name = action.tool_name.upper()
        tool = self.tools.get(tool_name)

        if not tool:
            return f"Tool not found: {tool_name}"

        if tool.need_validation and not self._get_user_approval(tool_name, action):
            return "Action not approved by user"

        try:
            self.console.print(
                Panel.fit(
                    f"[bold cyan]Executing tool:[/bold cyan] {tool_name}\n[yellow]Arguments:[/yellow] {action.arguments}",
                    title="Tool Execution",
                    border_style="cyan",
                )
            )
            result = tool.execute(**action.arguments)
            self.console.print(f"[green]Tool execution result:[/green] {result}")
            return result
        except Exception as e:
            error_trace = traceback.format_exc()
            self.console.print(
                f"[red]Error executing tool {tool_name}:[/red]\n{error_trace}"
            )
            return f"Error executing tool {tool_name}:\n{error_trace}"

    def _get_llm_response(self) -> Response:
        """Get response from the language model"""
        prompt = self._prepare_prompt()
        self.console.print("\n[bold blue]Generated Prompt[/bold blue]")
        self.console.print(Panel(prompt, border_style="blue"))

        with Progress(
            SpinnerColumn(),
            TextColumn("Generating response..."),
            console=self.console,
            transient=True,
            disable=False,
        ) as progress:
            task = progress.add_task("", total=None)
            llm_response = self.model.generate(prompt)

        self.console.print("\n[bold green]LLM Response[/bold green]")
        self.console.print(Panel(llm_response.content, border_style="green"))
        self.console.input("[yellow]Press Enter to continue...[/yellow]")
        return self._parse_response(llm_response.content)

    def _get_user_approval(self, tool_name: str, action: Dict[str, Any]) -> bool:
        """Get user approval for tool execution"""
        self.console.print(
            Panel.fit(
                f"[yellow]Tool:[/yellow] {tool_name}\n[yellow]Actions:[/yellow] {action}",
                title="Approval Required",
                border_style="yellow",
            )
        )
        return self.console.input("Approve (y/n)? ").lower().strip() == "y"

    def _get_final_answer(self) -> str:
        """Get the final answer from memory"""
        last_memory = self.memory[-1] if self.memory else None
        if last_memory and last_memory.answer:
            return last_memory.answer
        return "No answer found"

    def _display_status(self) -> None:
        """Display current agent status"""
        self.console.rule("[bold blue]Agent Status")
        self.console.print(
            f"[yellow]Iteration:[/yellow] {self.current_iteration}/{self.max_iterations}"
        )
        self.console.print(f"[yellow]State:[/yellow] {self.state.value}")
        self.console.rule()

    def _prepare_prompt(self) -> str:
        """Prepare prompt for LLM"""
        last_memory = self.memory[-1] if self.memory else None
        return query_template(
            query=self.query,
            history=last_memory.model_dump_json(indent=2)
            if last_memory
            else "No history",
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            remaining_iterations=self.max_iterations - self.current_iteration,
            tools=self._available_tools_description("json"),
            output_format=output_format(),
        )

    def _first_xml_code_block(self, input: str) -> str:
        """Extract the first XML code block from the input string formatted in markdown using RegEx.
        Args:
            input (str): The input string
        Returns:
            str: The first XML content within the code block, or None if not found
        """
        match = re.search(r"```xml\s*([\s\S]*?)\s*```", input)
        if not match:
            return None
        return match.group(1)

    def _parse_response(self, response: str) -> Response:
        """Parse response from LLM"""

        first_xml = self._first_xml_code_block(response)

        if first_xml:
            return ResponseParser.parse(first_xml)

        raise ValueError(f"No XML content found in response:\n {response}")

    def _available_tools_description(self, format: str) -> str:
        """Get the description of all available tools in XML format."""
        if format == "xml":
            descriptions = [
                PydanticToXMLSerializer.serialize(tool) for tool in self.tools.values()
            ]
            return "\n".join(descriptions)
        if format == "json":
            return {tool.name: tool.to_json() for tool in self.tools.values()}

        raise ValueError(f"Unsupported format: {format}")

    def _format_history(self) -> str:
        """Format message history"""
        return "\n".join(f"{msg.role}: {msg.content}" for msg in self.messages)

    def _add_to_memory(self, response_with_memory: ResponseWithActionResult) -> None:
        """Add thought to memory"""
        self.memory.append(response_with_memory)

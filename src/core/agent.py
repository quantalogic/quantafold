import logging
import re
import traceback
from enum import Enum
from typing import Any, Dict

from core.agent_template import output_format, query_template
from core.generative_model import GenerativeModel
from models.pydantic_to_xml import PydanticToXMLSerializer
from models.response import Action, Response, Step, Thought
from models.response_parser import ResponseParser
from models.tool import Tool
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn


class AgentState(Enum):
    READY = "ready"
    THINKING = "thinking"
    DECIDING = "deciding"
    ERROR = "error"
    COMPLETE = "complete"


class Agent:
    def __init__(self, model: GenerativeModel, max_iterations: int = 20):
        self.model = model
        self.tools: dict[str, Tool] = {}
        self.memory: list[Response] = []
        self.current_tought: Thought | None = None
        self.to_do_steps: list[Step] = []
        self.done_steps: list[Step] = []
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
        except Exception:
            self.logger.error(f"Execution error: {traceback.format_exc()}")
            return f"Error during execution:\n{traceback.format_exc()}"

    def _reset_state(self, query: str) -> None:
        """Reset agent state for new execution"""
        self.query = query
        self.messages = []
        self.memory = []
        self.toughts = []
        self.done_steps = []
        self.to_do_steps = []
        self.current_iteration = 0
        self.state = AgentState.READY

    def _run_thinking_loop(self) -> str:
        """Main thinking loop"""
        while self.current_iteration < self.max_iterations:
            try:
                if not self._think():
                    break
            except Exception:
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

        if not response.thought:
            raise ValueError("Response must contain a thought")

        if response.final_answer is not None:
            self._add_to_memory(response)
            return False

        if response.action is not None:
            result = self._handle_action(response.action)
            # Convert result to string to ensure type compatibility
            result_str = str(result) if result is not None else None
            response.action_result = result_str
            self._add_to_memory(response)
            return True

        self._add_to_memory(response)
        return True

    def _handle_action(self, action: Action) -> str:
        """Handle tool execution"""
        tool_name = action.tool_name.upper()
        tool = self.tools.get(tool_name)

        if not tool:
            return f"Tool not found: {tool_name}"

        if tool.need_validation and not self._get_user_approval(tool_name, action):
            return "Action not approved by user"

        # Initialize parent_context variable
        parent_context_list: list[str] = []

        arguments = action.arguments.copy()

        if tool.need_parent_context:
            for step_result in self.step_results:
                parent_context_list.append(step_result.model_dump_json(indent=2))
                arguments["parent_context"] = "\n".join(parent_context_list)

        try:
            self.console.print(
                Panel.fit(
                    f"[bold cyan]Executing tool:[/bold cyan] {tool_name}\n[yellow]Arguments:[/yellow] {arguments}",
                    title="Tool Execution",
                    border_style="cyan",
                )
            )
            result = tool.execute(**arguments)
            self.console.print(f"[green]Tool execution result:[/green] {result}")
            return result
        except Exception:
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
            _task = progress.add_task("", total=None)
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
        if last_memory and last_memory.final_answer:
            return last_memory.final_answer
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
        return query_template(
            query=self.query,
            history=self._format_history(),
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            remaining_iterations=self.max_iterations - self.current_iteration,
            tools=self._available_tools_description("json"),
            output_format=output_format(),
            done_steps=self._format_past_steps("xml"),
        )

    def _format_chain_of_thought(self) -> str:
        """Format chain of thought in JSON format with pretty printing"""
        if not self.current_tought:
            return ""

        # return last Thought as XML
        return PydanticToXMLSerializer.serialize(self.current_tought, pretty=True)

    def _format_history(self) -> str:
        """Format message history"""
        content: list[str] = []
        for i, step in enumerate(self.memory):
            content.append("-------------------")
            content.append(f"Iteration {i + 1}:")
            content.append(PydanticToXMLSerializer.serialize(step, pretty=True))
            content.append("-------------------")
        return "\n".join(content)

    def _format_past_steps(self, format: str) -> str:
        """Format past steps in XML or JSON format with pretty printing"""
        if not self.done_steps:
            return "No previous steps"

        if format == "xml":
            steps = [
                PydanticToXMLSerializer.serialize(step) for step in self.done_steps
            ]
            return "\n".join(f"  {step}" for step in steps)

        if format == "json":
            return [
                {
                    "name": step.name,
                    "description": step.description,
                    "reason": step.reason,
                    "result": step.result,
                }
                for step in self.done_steps
            ]

        raise ValueError(f"Unsupported format: {format}")

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

    def _add_to_memory(self, response: Response) -> None:
        """Add thought to memory"""
        current_step = (
            response.thought.to_do[0]
            if response.thought and response.thought.to_do
            else None
        )
        current_step_name = current_step.name if current_step else None
        if current_step_name:
            self.done_steps.append(
                Step(
                    name=current_step_name,
                    description=current_step.description,
                    reason=current_step.reason,
                )
            )

            self.done_steps.append(
                Step(
                    name=current_step_name,
                    description=current_step.description,
                    reason=current_step.reason,
                )
            )

            ## Remove the current_step_name from to_do_steps
            self.to_do_steps = [
                step for step in self.to_do_steps if step.name != current_step_name
            ]

            ## add in to_do_steps all the steps that are not done
            new_to_do_steps = [
                step
                for step in response.thought.to_do
                if step.name != current_step_name
            ]
            ## add the new to_do_steps
            self.to_do_steps.extend(new_to_do_steps)

        self.current_tought = Thought(
            reasoning=response.thought.reasoning,
            to_do=self.to_do_steps,
            done=self.done_steps,
        )

        self.memory.append(response)

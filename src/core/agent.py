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
from rich.text import Text


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
        self.step_results: dict[str, str] = {}
        self.final_answer: str | None = None
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
        self.memory = []
        self.final_answer = None
        self.done_steps = []
        self.step_results = {}  # Changed from dict[str, str] to {}
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

        self.console.print(
            Panel.fit(
                response.model_dump_json(indent=2),
                title="[bold magenta]Decision Response[/bold magenta]",
                border_style="magenta",
            )
        )

        if not response.thought:
            raise ValueError("Response must contain a thought")

        if response.final_answer is not None:
            self.state = AgentState.COMPLETE
            self.final_answer = response.final_answer
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

    def _find_interpolated_variables(self, text: str) -> list[str]:
        """Find all interpolated variables in a text string."""
        return re.findall(r"\$([a-zA-Z0-9_]+)\$", text)

    def _replace_interpolated_variables(
        self, text: str, variables: dict[str, str]
    ) -> str:
        """Replace all interpolated variables in a text string with their values."""
        for variable, value in variables.items():
            text = text.replace(f"${variable}$", value)
        return text

    def _handle_action(self, action: Action) -> str:
        """Handle tool execution"""
        tool_name = action.tool_name.upper()
        tool = self.tools.get(tool_name)

        if not tool:
            return f"Tool not found: {tool_name}"

        if tool.need_validation and not self._get_user_approval(tool_name, action):
            return "Action not approved by user"

        try:
            # Convert dictionary arguments to named arguments
            # and replace any interpolated variables
            named_args = {}
            for key, value in action.arguments.items():
                # Ensure the key is a valid Python identifier
                valid_key = key.replace("-", "_").replace(" ", "_")
                interpolated_value = self._replace_interpolated_variables(
                    value, self.step_results
                )
                named_args[valid_key] = interpolated_value

            self.console.print(
                Panel.fit(
                    f"[bold cyan]Executing tool:[/bold cyan] {tool_name}\n[yellow]Arguments:[/yellow] {named_args}",
                    title="Tool Execution",
                    border_style="cyan",
                )
            )

            result = tool.execute(**named_args)
            self.console.print(f"[green]🛠️ Tool execution result:[/green] {result}")
            input("Press Enter to continue...")
            return result
        except Exception:
            error_trace = traceback.format_exc()
            safe_error_trace = Text(error_trace).escape()  # Escape special characters
            self.console.print(
                f"[red]Error executing tool {tool_name}:[/red]\n{safe_error_trace}"
            )
            input("Press Enter to continue...")
            return f"Error executing tool {tool_name}:\n{safe_error_trace}"

    def _get_llm_response(self) -> Response:
        """Get response from the language model"""
        prompt = self._prepare_prompt()
        self.console.print("\n[bold blue]Generated Prompt[/bold blue]")
        prompt_for_display = prompt.replace(output_format(), "")
        ## Remove content <available_tools> from prompt
        prompt_for_display = prompt_for_display.replace(
            self._available_tools_description("xml"), ""
        )
        self.console.print(Panel(prompt_for_display, border_style="blue"))

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
        if self.final_answer:
            return self.final_answer
        return "No answer found"

    def _format_step_result_variables(self) -> str:
        """Format step result variables in XML format."""
        if not self.step_results:
            return "No step results available."

        content = []
        for step_name, result in self.step_results.items():
            content.append(f"   <{step_name}>{result}</{step_name}>")
        return "\n".join(content)

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
            history=self._format_tasks(),
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            remaining_iterations=self.max_iterations - self.current_iteration,
            tools=self._available_tools_description("xml"),
            output_format=output_format(),
            step_result_variables=self._format_step_result_variables(),
        )

    def _format_step_results(self) -> str:
        content: list[str] = []
        for step_name, result in self.step_results.items():
            content.append(f"Step: {step_name}")
            content.append("```")
            content.append(result)
            content.append("```")
        return "\n".join(content)

    def _format_tasks(self) -> str:
        """Format tasks in XML format."""
        content = []

        if self.final_answer is not None:
            content.append(f"<final_answer>{self.final_answer}</final_answer>")

        ## Done steps
        content.append("  <done>")
        for step in self.done_steps:
            content.append(
                "    " + PydanticToXMLSerializer.serialize(step, pretty=True)
            )
        content.append("  </done>")

        content.append("")

        ## To do steps
        content.append("  <to_do>")
        for step in self.to_do_steps:
            content.append("   " + PydanticToXMLSerializer.serialize(step, pretty=True))
        content.append("  </to_do>")

        content.append("")

        ## Available variables
        content.append("  <variables>")
        for step_name, _result in self.step_results.items():
            content.append(f"    <variable>${step_name}$</variable>")
        content.append("  </variables>")

        return "\n".join(content)

    def _format_history(self, last_n: int = 1) -> str:
        """Format message history
        Args:
            last_n (int, optional): Number of last iterations to return. Defaults to None (all iterations).
        Returns:
            str: Formatted history as XML string
        """
        content: list[str] = []
        memory_items = self.memory[-last_n:] if last_n else self.memory

        for i, memory_item in enumerate(memory_items):
            content.append(f"Iteration {len(self.memory) - len(memory_items) + i + 1}:")
            content.append(
                PydanticToXMLSerializer.serialize(
                    memory_item,
                    pretty=True,
                    indent=2,
                    list_item_names={"to_do": "step", "done": "step"},
                )
            )
            content.append("-------------------")
        return "\n".join(content)

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
        # Improved regex to capture XML within code blocks or standalone
        match = re.search(r"```xml\s*([\s\S]*?)\s*```", input)
        if not match:
            match = re.search(r"(<response>[\\s\S]*?</response>)", input)
            if not match:
                return None
            return match.group(1)
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
                PydanticToXMLSerializer.serialize(tool, pretty=True)
                for tool in self.tools.values()
            ]
            return "\n".join(descriptions)
        if format == "json":
            return {tool.name: tool.to_json() for tool in self.tools.values()}

        raise ValueError(f"Unsupported format: {format}")

    def _add_to_memory(self, response: Response) -> None:
        """Add thought to memory"""
        if response.final_answer is not None:
            self.memory.append(response)
        elif response.thought and response.thought.to_do:
            thought = response.thought
            if thought and thought.to_do:
                current_step = thought.to_do[0]
                current_step_name = current_step.name

                # Update current_step result
                current_step.result = f"Result saved in ${current_step_name}$ variable"
                current_step.tool_name = response.action.tool_name
                current_step.arguments = response.action.arguments

                # Add current_step to done_steps
                self.done_steps.append(current_step)

                # Remove the current_step from to_do_steps
                self.to_do_steps = [
                    step for step in self.to_do_steps if step.name != current_step_name
                ]

                self.to_do_steps = thought.to_do[1:]

                if response.action_result:
                    self.step_results[current_step_name] = response.action_result

                self.current_thought = Thought(
                    reasoning=thought.reasoning,
                    to_do=self.to_do_steps,
                    done=self.done_steps,
                )

                # Display current thought in a panel
                self.console.print(
                    Panel.fit(
                        PydanticToXMLSerializer.serialize(
                            self.current_thought,
                            pretty=True,
                            list_item_names={"to_do": "step", "done": "step"},
                        ),
                        title="[bold cyan]Current Thought[/bold cyan]",
                        border_style="cyan",
                    )
                )
                self.console.input("[yellow]Press Enter to continue...[/yellow]")
                self.memory.append(response)
        else:
            # Handle other cases
            self.memory.append(response)

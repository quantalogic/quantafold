import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from core.agent_template import output_format, query_template
from core.generative_model import GenerativeModel
from models.message import Message
from models.pydantic_to_xml import PydanticToXMLSerializer
from models.response import Response
from models.response_parser import ResponseParser
from models.tool import Tool
from models.response import Thought


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
        self.messages: list[Message] = []
        self.toughts: list[Thought] = []
        self.query: str = ""
        self.max_iterations: int = max_iterations
        self.current_iteration: int = 0
        self.state: AgentState = AgentState.READY
        self.logger = logging.getLogger(__name__)

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
            self.logger.error(f"Execution error: {e}")
            return f"Error during execution: {str(e)}"

    def _reset_state(self, query: str) -> None:
        """Reset agent state for new execution"""
        self.query = query
        self.messages = []
        self.current_iteration = 0
        self.state = AgentState.READY

    def _run_thinking_loop(self) -> str:
        """Main thinking loop"""
        while self.current_iteration < self.max_iterations:
            try:
                if not self._think():
                    break
            except Exception as e:
                self._handle_error(e)

        return self._get_final_answer()

    def _think(self) -> bool:
        """Execute one thinking iteration"""
        self.state = AgentState.THINKING
        self.current_iteration += 1

        if self.current_iteration > self.max_iterations:
            return False

        self._display_status()
        response = self._get_llm_response()
        parsed_response = self._parse_response(response)
        self._add_thought_to_memory(parsed_response)

        return self._decide(response)

    def _decide(self, response: Response) -> bool:
        """Process response and decide next action"""
        self.state = AgentState.DECIDING

        if not response.action:
            self._add_to_memory("assistant", response.thought)
            return False

        return self._handle_action(response.action)

    def _handle_action(self, action: Dict[str, Any]) -> bool:
        """Handle tool execution"""
        tool_name = action.get("tool_name", "").upper()
        tool = self.tools.get(tool_name)

        if not tool:
            self._add_to_memory("system", f"Tool not found: {tool_name}")
            return True

        if tool.need_validation and not self._get_user_approval(tool_name, action):
            return True

        try:
            print(f"🛠️ Execute tools {tool_name} with actions: {action}")
            result = tool.execute(**action.get("arguments", {}))
            self._add_to_memory("tool_execution", str(result))
            return True
        except Exception as e:
            self._handle_error(e)
            return True

    def _get_llm_response(self) -> Response:
        """Get response from the language model"""
        prompt = self._prepare_prompt()
        print("----------------------------------")
        print(f"🎅\nPrompt:\n {prompt}\n")
        input("Press Enter to continue...")
        llm_response = self.model.generate(prompt)
        print(f"\n🤖 Response:\n {llm_response}\n")
        # pause
        input("Press Enter to continue...")
        return self._parse_response(llm_response.content)

    def _add_to_memory(self, role: str, content: str) -> None:
        """Add message to memory"""
        self.messages.append(
            Message(role=role, content=content, timestamp=datetime.utcnow().isoformat())
        )

    def _handle_error(self, error: Exception) -> None:
        """Handle errors during execution"""
        self.state = AgentState.ERROR
        self.logger.error(f"Error: {error}")
        self._add_to_memory("system", f"Error: {str(error)}")

    def _get_user_approval(self, tool_name: str, action: Dict[str, Any]) -> bool:
        """Get user approval for tool execution"""
        print(f"Require approval for {tool_name} with actions: {action}")
        return input("Approve (y/n)? ").lower().strip() == "y"

    def _get_final_answer(self) -> str:
        """Get the final answer from memory"""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return "No answer generated."

    def _display_status(self) -> None:
        """Display current agent status"""
        print(f"Iteration: {self.current_iteration}/{self.max_iterations}")
        print(f"State: {self.state.value}")

    def _prepare_prompt(self) -> str:
        """Prepare prompt for LLM"""
        last_thought = self.last_tought()
        last_thought = last_thought or Thought(reasoning="No previous thoughts.")
        return query_template(
            query=self.query,
            history=last_thought.model_dump_json(indent=2),
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

    def _add_thought_to_memory(self, response: Response) -> None:
        """Add thought to memory"""
        self._tought.append(response.thought)
        print(f"Thought: {response.thought}")
        input("Press Enter to continue...")
        self._add_to_memory("assistant", f"Thought: {response.thought}")

    def last_tought(self) -> Thought:
        """Get the last thought from memory"""
        if len(self.toughts) == 0:
            return None
        return self.toughts[-1]

# src/react/agent.py
import json
import logging
from typing import Callable

from core.generative_model import GenerativeModel
from models.message import Message
from tools.tool import Tool

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, model: GenerativeModel) -> None:
        self.model = model
        self.tools: dict[str, Tool] = {}
        self.messages: list[Message] = []
        self.query = ""
        self.max_iterations = 5
        self.current_iteration = 0
        self.prompt_template = self.load_template()

    def load_template(self) -> str:
        return """
You are a ReAct (Reasoning and Acting) agent tasked with answering the following query:

Query: 

<query>
{query}
</query>

Your goal is to reason about the query and decide on the best course of action to answer it accurately.

Previous reasoning steps and observations:
<history>
{history}
</history>

Available tools: 
<tools>
{tools}
</tools>

Instructions:
1. Analyze the query, previous reasoning steps, and observations.
2. Decide on the next action: use a tool or provide a final answer.
3. You MUST respond with ONLY a valid JSON object in one of these two formats:

Format 1 - If you need to use a tool:
```json
{{
    "thought": "Your detailed reasoning about what to do next",
    "action": {{
        "name": "EXACT_TOOL_NAME",
        "reason": "Brief explanation of why you chose this tool",
        "input": "Specific input for the tool"
    }}
}}
```

Format 2 - If you have enough information to answer:
```json
{{
    "thought": "Your reasoning about why you can now answer the query",
    "answer": "Your final answer to the query"
}}
```

DO NOT include any text before or after the JSON object. The response must be parseable JSON.
        """

    def register(self, name: str, func: Callable[[str], str]) -> None:
        self.tools[name] = Tool(name.upper(), func)

    def trace(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))

    def get_history(self) -> str:
        return "\n".join([f"{msg.role}: {msg.content}" for msg in self.messages])

    def think(self) -> None:
        self.current_iteration += 1
        if self.current_iteration > self.max_iterations:
            logger.warning("Reached maximum iterations. Stopping.")
            return
        prompt = self.prompt_template.format(
            query=self.query,
            history=self.get_history(),
            tools=", ".join([str(tool.name) for tool in self.tools.values()]),
        )
        response = self.ask_llm(prompt)
        self.trace("assistant", f"Thought: {response}")
        self.decide(response)

    def decide(self, response: str) -> None:
        try:
            parsed_response = self.extract(response)

            if "action" in parsed_response:
                action = parsed_response["action"]
                tool_name_str = action["name"].upper()
                if tool_name_str not in self.tools:
                    raise ValueError(f"Unsupported tool: {tool_name_str}")
                print(f"Tool: {tool_name_str}")
                print(f"Input: {action.get('input', self.query)}")
                self.act(tool_name_str, action.get("input", self.query))
            else:
                print("Answering directly")
                self.trace("assistant", f"Final Answer: {parsed_response['answer']}")

        except ValueError as e:
            error_msg = f"Error processing response: {str(e)}"
            logging.error(error_msg)
            self.trace("system", error_msg)

    def _extract_first_code_block(self, input_string: str) -> str:
        """
        Extracts the first code block from the provided string.

        Args:
            input_string (str): The input string containing code blocks.

        Returns:
            str: The extracted code block, or an empty string if no code block is found.
        """
        import re

        # Use regular expression to find the first code block
        match = re.search(r"```(.*?)```", input_string, re.DOTALL)
        if match:
            # Return the first code block without the backticks
            return match.group(1).strip()
        return ""

    def extract(self, response: str) -> dict:
        """
        Extracts and validates structured information from the response string.

        Args:
            response (str): The response string to parse

        Returns:
            dict: Parsed and validated response dictionary

        Raises:
            ValueError: If the response format is invalid or cannot be parsed
        """
        try:
            # Extract the first JSON block if there's any extra text
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # Try to parse the JSON
            parsed_response = json.loads(response)

            # Validate required fields
            if not isinstance(parsed_response, dict):
                raise ValueError("Response must be a JSON object")
            
            if "thought" not in parsed_response:
                raise ValueError("Response must contain a 'thought' field")

            # Check for valid keys
            if not any(key in parsed_response for key in ["action", "answer"]):
                raise ValueError("Response must contain either 'action' or 'answer' key")

            # Validate action structure if present
            if "action" in parsed_response:
                action = parsed_response["action"]
                if not isinstance(action, dict):
                    raise ValueError("Action must be a JSON object")
                if not all(key in action for key in ["name", "reason", "input"]):
                    raise ValueError("Action must contain 'name', 'reason', and 'input' fields")
                if action["name"] not in self.tools:
                    raise ValueError(f"Unknown tool name: {action['name']}")

            return parsed_response

        except json.JSONDecodeError as e:
            # Clean the response for logging
            clean_response = response.replace('\n', '\\n')
            logger.error(f"Invalid JSON format in response: {clean_response}")
            logger.error(f"JSON parse error: {str(e)}")
            raise ValueError("Response is not valid JSON. Please try again.") from e
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while parsing response: {str(e)}")
            raise ValueError("Failed to process the response. Please try again.") from e

    def act(self, tool_name: str, query: str) -> None:
        tool = self.tools.get(tool_name)
        if tool:
            result = tool.use(query)
            observation = f"Observation from {tool_name}: {result}"
            self.trace("system", observation)
            self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.think()

    def execute(self, query: str) -> str:
        self.query = query
        self.think()
        final_answers = [
            msg.content
            for msg in self.messages
            if msg.role == "assistant" and "Final Answer" in msg.content
        ]
        return (
            final_answers[-1].split("Final Answer: ")[-1]
            if final_answers
            else "Unable to provide an answer."
        )

    def ask_llm(self, prompt: str) -> str:
        response = self.model.generate(prompt)
        return response.content

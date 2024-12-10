import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, Optional

from core.generative_model import GenerativeModel
from models.message import Message
from models.responsestats import ResponseStats
from models.tool import Tool

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, model: GenerativeModel) -> None:
        self.model = model
        self.tools: dict[str, Tool] = {}
        self.messages: list[Message] = []
        self.query = ""
        self.max_iterations = 20
        self.current_iteration = 0
        self.prompt_template = """
You are a ReAct (Reasoning and Acting) agent tasked with answering the following query:

## Query to solve:

<query>
{query}
</query>

## Goal:

Your goal is to reason about the query and decide on the best course of action to answer it accurately.

## Session History:
<history>
{history}
</history>

Current iteration: {current_iteration}
Max iterations: {max_iterations}

## Available tools:

Here are examples of how to use the available tools:

<available_tools>
{tools}
</available_tools>

## Instructions:
1. Analyze the query, previous reasoning steps, and observations in history and decide on the best course of action to answer it accurately.
2. Decide on the next action: use a tool or provide a final answer. 
3. You must answer in less than {max_iterations} iterations.
4. You MUST respond with ONLY a valid XML object in one of these two formats:

Format 1 - If you need to use a tool:
```xml
<response>
    <thought>Your detailed reasoning about what to do next</thought>
    <action>
        <tool_name>EXACT_TOOL_NAME</tool_name>
        <reason>Brief explanation of why you chose this tool</reason>
        <parameters>
            <param>
                <name>parameter_name</name>
                <value>parameter_value</value>
            </param>
            <!-- Additional parameters as needed -->
        </parameters>
    </action>
</response>
```

Format 2 - If you have enough information to answer:
```xml
<response>
    <thought>Your reasoning about why you can now answer the query</thought>
    <answer>Your final answer to the query</answer>
</response>
```

DO NOT include any text before or after the XML object. The response must be well-formed XML.
"""

    def register(self, tool: Tool) -> None:
        """Register a new tool with the agent."""
        self.tools[tool.name.upper()] = tool

    def add_to_session_memory(self, role: str, content: str) -> None:
        """Add a new message to the session history."""
        timestamp = datetime.utcnow().isoformat()
        self.messages.append(Message(role=role, content=content, timestamp=timestamp))

    def get_history(self) -> str:
        """Get formatted session history."""
        history = [msg.model_dump() for msg in self.messages]
        print("History:")
        return str(history)  # Return the formatted history

    def think(self) -> None:
        """Execute the thinking step of the agent."""
        self.current_iteration += 1
        if self.current_iteration > self.max_iterations:
            logger.warning("Reached maximum iterations. Stopping.")
            return

        # Collect XML examples from all tools
        tool_examples = "\n".join([tool.to_json() for tool in self.tools.values()])

        prompt = self.prompt_template.format(
            query=self.query,
            history=self.get_history(),
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
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
                parameters = action.find("parameters")

                if tool_name is None or reason is None:
                    raise ValueError(
                        "Action element must contain 'tool_name' and 'reason' elements."
                    )

                if tool_name.text.upper() not in self.tools:
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
            logger.error(f"Invalid XML format in response: {clean_response}")
            logger.error(f"XML parse error: {str(e)}")
            raise ValueError("Response is not valid XML. Please try again.") from e
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while parsing response: {str(e)}")
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

                # Extract parameters
                params = {}
                parameters_elem = action.find("parameters")
                if parameters_elem is not None:
                    for param in parameters_elem.findall("param"):
                        name = param.find("name")
                        value = param.find("value")
                        if (
                            name is not None
                            and value is not None
                            and name.text
                            and value.text
                        ):
                            params[name.text] = value.text

                print(f"Tool: {tool_name_str}")
                print(f"Parameters: {params}")
                self.act(tool_name_str, params)

            elif parsed_response.find("answer") is not None:
                answer = parsed_response.find("answer")
                if answer is None or not answer.text:
                    raise ValueError("Answer element is empty")

                print("Answering directly")
                answer_text = answer.text.strip()
                self.add_to_session_memory("assistant", f"Answer: {answer_text}")

            else:
                raise ValueError(
                    "Response must contain either 'action' or 'answer' element."
                )

        except Exception as e:
            error_msg = f"Error processing response: {str(e)}"
            logger.error(error_msg)
            self.add_to_session_memory("system", f"Error: {error_msg}")
            if self.current_iteration < self.max_iterations:
                self.think()

    def act(self, tool_name: str, parameters: Dict[str, Any]) -> None:
        """Execute a tool with the given parameters."""
        tool = self.tools.get(tool_name)
        if tool:
            try:
                # Convert parameter types based on tool parameter definitions
                converted_params = self._convert_parameters(tool, parameters)
                # Execute tool with converted parameters
                result = tool.execute(**converted_params)
                observation = f"Observation from {tool_name}: {result}"
                print(f"Observation: {observation}")
                self.add_to_session_memory("system", f"Observation: {observation}")
                self.think()
            except Exception as e:
                error_msg = f"Error executing tool {tool_name}: {str(e)}"
                logger.error(error_msg)
                self.add_to_session_memory("system", f"Error: {error_msg}")
                self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.think()

    def _convert_parameters(
        self, tool: Tool, parameters: dict[str, str]
    ) -> dict[str, Any]:
        """Convert parameters to their appropriate types based on tool parameter definitions."""
        converted = {}
        type_converters = {
            "string": str,
            "int": int,
            "float": float,
            "bool": lambda x: x.lower() == "true",
        }

        for param in tool.parameters:
            if param.name in parameters:
                value = parameters[param.name]
                try:
                    if param.type in type_converters:
                        converted[param.name] = type_converters[param.type](value)
                    else:
                        converted[param.name] = value  # Keep as string if type unknown
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Failed to convert parameter '{param.name}' to {param.type}: {str(e)}"
                    )
            elif param.required:
                raise ValueError(f"Missing required parameter: {param.name}")
            elif param.default is not None:
                converted[param.name] = param.default

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
                if msg.role == "assistant" and msg.content.startswith("Answer: "):
                    return msg.content.replace("Answer: ", "")

            return "Unable to provide an answer after maximum iterations."

        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return f"An error occurred while processing your query: {str(e)}"

    def ask_llm(self, prompt: str) -> ResponseStats:
        """Get response from the language model."""
        print(f"Prompt:\n{prompt}\n")
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

            if "parameters" in action:
                params_elem = ET.SubElement(action_elem, "parameters")
                for param_name, param_value in action["parameters"].items():
                    param_elem = ET.SubElement(params_elem, "param")
                    name = ET.SubElement(param_elem, "name")
                    name.text = param_name
                    value = ET.SubElement(param_elem, "value")
                    value.text = str(param_value)

        if answer:
            answer_elem = ET.SubElement(root, "answer")
            answer_elem.text = answer

        return ET.tostring(root, encoding="unicode", method="xml")

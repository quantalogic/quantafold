# Summary Section

- Enhanced the tooling system by introducing Pydantic models for tool definitions, enabling robust XML handling and tool registration within the agent.
- **src/models/tool.py**: Created to define Pydantic models representing tools and their arguments for structured XML representation.
- **src/tools/tool.py**: Updated to utilize the new Pydantic Tool model for tool operations.
- **src/core/agent.py**: Modified to register tools using Pydantic models, handle XML input/output with validation, and execute tasks using the enhanced tooling system.
- **src/models/__init__.py**: Updated to include the newly created Tool model for seamless integration.
- **src/main.py**: Updated tool registration process to align with the new Pydantic-based tooling system.

# XML Section

```xml
<code_changes>
  <changed_files>
    <file>
      <file_summary>Created Pydantic models for tools to enable structured XML representation and validation.</file_summary>
      <file_operation>CREATE</file_operation>
      <file_path>src/models/tool.py</file_path>
      <file_code><![CDATA[
from typing import List, Optional
from pydantic import BaseModel, Field

class ToolArgument(BaseModel):
    name: str = Field(..., description="The name of the argument.")
    type: str = Field(..., description="The type of the argument (e.g., string, integer).")
    description: Optional[str] = Field(None, description="A brief description of the argument.")

class Tool(BaseModel):
    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A brief description of what the tool does.")
    arguments: List[ToolArgument] = Field([], description="A list of arguments the tool accepts.")
]]
      </file_code>
    </file>
    <file>
      <file_summary>Updated the Tool class to use the new Pydantic Tool model for structured operations.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/tools/tool.py</file_path>
      <file_code><![CDATA[
import logging
from typing import Callable

from models.observation import Observation
from models.tool import Tool as ToolModel

logger = logging.getLogger(__name__)

class Tool:
    def __init__(self, tool_model: ToolModel, func: Callable[[str], str]):
        self.tool_model = tool_model
        self.name = tool_model.name
        self.func = func

    def use(self, query: str) -> Observation:
        try:
            return self.func(query)
        except Exception as e:
            logger.error(f"Error executing tool {self.name}: {e}")
            return str(e)
]]
      </file_code>
    </file>
    <file>
      <file_summary>Modified the Agent class to register tools using Pydantic models, handle XML input/output, and ensure validation.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/core/agent.py</file_path>
      <file_code><![CDATA[
# src/core/agent.py
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Callable

from core.generative_model import GenerativeModel
from models.message import Message
from models.responsestats import ResponseStats
from models.tool import Tool as ToolModel
from tools.tool import Tool

logger = logging.getLogger(__name__)

class Agent:
    def __init__(self, model: GenerativeModel) -> None:
        self.model = model
        self.tools: dict[str, Tool] = {}
        self.messages: list[Message] = []
        self.query = ""
        self.max_iterations = 20
        self.current_iteration = 0
        self.prompt_template = self.load_template()

    def load_template(self) -> str:
        return """
You are a ReAct (Reasoning and Acting) agent tasked with answering the following query:

## Query to solve:

<query>
{query}
</query>


## Goal:

Your goal is to reason about the query and decide on the best course of action to answer it accurately.

## Session History:
{history}

Current iteration: {current_iteration}
Max iterations: {max_iterations}

## Available tools:
<tools>
{tools}
</tools>

## Instructions:
1. Analyze the query, previous reasoning steps, and observations in history and decide on the best course of action to answer it accurately.
2. Decide on the next action: use a tool or provide a final answer. You can use a tool to perform an action and get an information where you are not sure how to answer the query.
3. You must answer in less than {max_iterations} iterations.
4. You MUST respond with ONLY a valid XML object in one of these two formats:

The current tools ONLY ACCEPT ONE PARAMETER.

## Output Format:
Format 1 - If you need to use a tool:
```xml
<response>
    <thought>Your detailed reasoning about what to do next</thought>
    <action>
        <tool_name>EXACT_TOOL_NAME</tool_name>
        <reason>Brief explanation of why you chose this tool</reason>
        <input>Specific input for the tool</input>
    </action>
</response>
```

Format 2 - If you have enough information to answer:
```xml
<response>
    <thought>Your reasoning about why you can now answer the query</thought>
    <answer><![CDATA[Your final answer to the query]]></answer>
</response>
```

DO NOT include any text before or after the XML object. The response must be well-formed XML.
        """

    def register(self, tool_model: ToolModel, func: Callable[[str], str]) -> None:
        self.tools[tool_model.name.upper()] = Tool(tool_model, func)

    def add_to_session_memory(self, role: str, content: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        self.messages.append(Message(role=role, content=content, timestamp=timestamp))

    def get_history(self) -> str:
        history = "\n".join(
            [f"step{str(i + 1).zfill(4)} - {msg.role}: {msg.content}" for i, msg in enumerate(self.messages)]
        )
        xml_output = ["<history>"]
        xml_output.append(history)
        xml_output.append("</history>")
        return "\n".join(xml_output)

    def think(self) -> None:
        self.current_iteration += 1
        if self.current_iteration > self.max_iterations:
            logger.warning("Reached maximum iterations. Stopping.")
            return
        prompt = self.prompt_template.format(
            query=self.query,
            history=self.get_history(),
            current_iteration=self.current_iteration,
            max_iterations=self.max_iterations,
            tools=", ".join([str(tool.tool_model.name) for tool in self.tools.values()]),
        )
        print("Thinking...")
        print("=" * 40)  # Add a separator for better visibility
        print(prompt)
        print("=" * 40)  # Add a separator for consistency
        response = self.ask_llm(prompt)
        self.add_to_session_memory("assistant", f"Thought: {response.content}")
        self.decide(response.content)

    def decide(self, response: str) -> None:
        """Process the response from the LLM and decide on next action."""
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

                action_input = action.find("input")
                if action_input is None or not action_input.text:
                    action_input_str = self.query
                else:
                    action_input_str = action_input.text

                print(f"Tool: {tool_name_str}")
                print(f"Input: {action_input_str}")
                self.act(tool_name_str, action_input_str)

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
            # Continue thinking if there's an error, unless we've hit the max iterations
            if self.current_iteration < self.max_iterations:
                self.think()

    def extract(self, response: str) -> ET.ElementTree:
        """
        Extracts and validates structured information from the response string.

        Args:
            response (str): The response string to parse

        Returns:
            ET.ElementTree: Parsed and validated XML element tree

        Raises:
            ValueError: If the response format is invalid or cannot be parsed
        """
        try:
            response = response.strip()
            if response.startswith("```xml"):
                response = response[6:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Parse the XML
            root = ET.fromstring(response)

            if root.tag != "response":
                raise ValueError("Root element must be 'response'.")

            thought = root.find("thought")
            if thought is None or not thought.text:
                raise ValueError(
                    "Response must contain a 'thought' element with content."
                )

            # Check for either 'action' or 'answer'
            action = root.find("action")
            answer = root.find("answer")

            if action is not None:
                name = action.find("tool_name")
                reason = action.find("reason")
                input_elem = action.find("input")

                if name is None or reason is None or input_elem is None:
                    raise ValueError(
                        "Action element must contain 'tool_name', 'reason', and 'input' elements."
                    )

                if name.text.upper() not in self.tools:
                    raise ValueError(f"Unknown tool name: {name.text}")

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

    def act(self, tool_name: str, query: str) -> None:
        tool = self.tools.get(tool_name)
        if tool:
            result = tool.use(query)
            observation = f"Observation from {tool_name}: {result}"
            self.add_to_session_memory("system", f"Observation: {observation}")
            self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.think()

    def execute(self, query: str) -> str:
        """Execute a query and return the final answer."""
        try:
            self.query = query
            self.current_iteration = 0
            self.messages = []  # Reset message history for new query
            self.add_to_session_memory("user", f"Query: {query}")
            self.think()

            # Look for the most recent answer in the message history
            for msg in reversed(self.messages):
                if msg.role == "assistant" and msg.content.startswith("Answer: "):
                    return msg.content.replace("Answer: ", "")

            return "Unable to provide an answer after maximum iterations."

        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return f"An error occurred while processing your query: {str(e)}"

    def ask_llm(self, prompt: str) -> ResponseStats:
        """Get response from the LLM model."""
        return self.model.generate(prompt)

    # Additional method to generate XML response if needed
    def generate_xml_response(
        self, thought: str, action: dict = None, answer: str = None
    ) -> str:
        response = ET.Element("response")
        thought_elem = ET.SubElement(response, "thought")
        thought_elem.text = thought
        if action:
            action_elem = ET.SubElement(response, "action")
            name_elem = ET.SubElement(action_elem, "tool_name")
            name_elem.text = action["name"]
            reason_elem = ET.SubElement(action_elem, "reason")
            reason_elem.text = action["reason"]
            input_elem = ET.SubElement(action_elem, "input")
            input_elem.text = action["input"]
        if answer:
            answer_elem = ET.SubElement(response, "answer")
            answer_elem.text = answer
        return ET.tostring(response, encoding="unicode")
]]
      </file_code>
    </file>
    <file>
      <file_summary>Updated models/__init__.py to include the new Tool model for easy import.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/models/__init__.py</file_path>
      <file_code><![CDATA[
from .tool import Tool, ToolArgument

from .observation import Observation
from .choice import Choice
from .responsestats import ResponseStats
from .message import Message
]]
      </file_code>
    </file>
    <file>
      <file_summary>Updated main.py to register tools using the new Pydantic-based tooling system.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/main.py</file_path>
      <file_code><![CDATA[
import logging

from core.agent import Agent
from core.generative_model import GenerativeModel
from models.tool import Tool as ToolModel
from tools.wikipedia import use_wikipedia

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s:%(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

MODEL_NAME= "gpt-4o-mini"

def main() -> None:
    model = GenerativeModel(model=MODEL_NAME)
    agent = Agent(model=model)
    
    wikipedia_tool = ToolModel(
        name="SEARCH_WIKIPEDIA",
        description="Searches Wikipedia for information based on a query.",
        arguments=[
            ToolArgument(
                name="query",
                type="string",
                description="The search term to query on Wikipedia."
            )
        ]
    )
    
    agent.register(wikipedia_tool, use_wikipedia)

    print("Welcome to the AI Assistant!")
    print(
        "You can ask questions about any topic, and I'll search Wikipedia for information."
    )
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        print("\nAsk a question:")
        query = input().strip()

        if query.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break

        if not query:
            print("Please enter a question.")
            continue

        try:
            response = agent.execute(query)
            print("\nResponse:", response)
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try again with a different question.")


if __name__ == "__main__":
    main()
]]
      </file_code>
    </file>
  </changed_files>
</code_changes>
```
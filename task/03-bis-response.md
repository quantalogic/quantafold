# Summary Section

This update enhances the ReAct agent by providing clearer context and guidance, implementing a detailed task history with timestamps and error logging, adding specific examples of inputs and expected outputs, and outlining the agent's reasoning process to improve decision-making capabilities.

- **src/core/agent.py**: Updated the agent's prompt template to include detailed instructions, task history logging with timestamps, and examples to improve context and guidance.
- **src/core/config.py**: Modified the configuration to support detailed task history and error message logging.
- **src/models/message.py**: Enhanced the `Message` model to include timestamp information for each task.
- **src/models/responsestats.py**: Updated the `ResponseStats` model to capture additional statistics related to task execution.

# XML Section

```xml
<code_changes>
  <changed_files>
    <file>
      <file_summary>Updated the agent's prompt template to include detailed instructions, task history with timestamps, examples, and clearer reasoning processes.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/core/agent.py</file_path>
      <file_code><![CDATA[
# src/core/agent.py
import logging
import xml.etree.ElementTree as ET
from typing import Callable
from datetime import datetime

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

<Query>
{query}
</Query>

Your goal is to reason about the query and decide on the best course of action to answer it accurately.

Task History:
<History>
{history}
</History>

Available tools: 
<Tools>
{tools}
</Tools>

Examples:
<Input>: "What is the capital of France?"
<Expected Output>: "The capital of France is Paris."

<Input>: "Solve the equation 2x + 3 = 7."
<Expected Output>: "To solve the equation 2x + 3 = 7, subtract 3 from both sides to get 2x = 4, then divide by 2 to find x = 2."

Instructions:
1. Analyze the query, previous reasoning steps, and observations.
2. Decide on the next action: use a tool or provide a final answer.
3. You MUST respond with ONLY a valid XML object in one of these two formats:

Format 1 - If you need to use a tool:
```xml
<response>
    <thought>Your detailed reasoning about what to do next</thought>
    <action>
        <name>EXACT_TOOL_NAME</name>
        <reason>Brief explanation of why you chose this tool</reason>
        <input>Specific input for the tool</input>
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

    def register(self, name: str, func: Callable[[str], str]) -> None:
        self.tools[name] = Tool(name.upper(), func)

    def trace(self, role: str, content: str) -> None:
        timestamp = datetime.utcnow().isoformat()
        self.messages.append(Message(role=role, content=content, timestamp=timestamp))

    def get_history(self) -> str:
        return "\n".join([f"{msg.timestamp} - {msg.role}: {msg.content}" for msg in self.messages])

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
        print("Thinking...")
        print("=" * 40)  # Add a separator for better visibility
        print(prompt)
        print("=" * 40)  # Add a separator for consistency
        response = self.ask_llm(prompt)
        self.trace("assistant", f"Thought: {response}")
        self.decide(response)

    def decide(self, response: str) -> None:
        try:
            parsed_response = self.extract(response)

            if parsed_response.find('action') is not None:
                action = parsed_response.find('action')
                tool_name_str = action.find('name').text.upper()
                if tool_name_str not in self.tools:
                    raise ValueError(f"Unsupported tool: {tool_name_str}")
                print(f"Tool: {tool_name_str}")
                action_input = action.find('input').text if action.find('input') is not None else self.query
                print(f"Input: {action_input}")
                self.act(tool_name_str, action_input)
            elif parsed_response.find('answer') is not None:
                print("Answering directly")
                answer = parsed_response.find('answer').text
                self.trace("assistant", f"Final Answer: {answer}")
            else:
                raise ValueError("Response must contain either 'action' or 'answer' element.")

        except ValueError as e:
            error_msg = f"Error processing response: {str(e)}"
            logging.error(error_msg)
            self.trace("system", error_msg)

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

            if root.tag != 'response':
                raise ValueError("Root element must be 'response'.")

            thought = root.find('thought')
            if thought is None or not thought.text:
                raise ValueError("Response must contain a 'thought' element with content.")

            # Check for either 'action' or 'answer'
            action = root.find('action')
            answer = root.find('answer')

            if action is not None:
                name = action.find('name')
                reason = action.find('reason')
                input_elem = action.find('input')

                if name is None or reason is None or input_elem is None:
                    raise ValueError("Action element must contain 'name', 'reason', and 'input' elements.")

                if name.text.upper() not in self.tools:
                    raise ValueError(f"Unknown tool name: {name.text}")

            elif answer is not None:
                if not answer.text:
                    raise ValueError("'answer' element must contain text.")
            else:
                raise ValueError("Response must contain either 'action' or 'answer' element.")

            return root

        except ET.ParseError as e:
            clean_response = response.replace('\n', '\\n')
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
            self.trace("system", observation)
            self.think()
        else:
            logger.error(f"No tool registered for choice: {tool_name}")
            self.think()

    def execute(self, query: str) -> str:
        self.query = query
        self.trace("user", query)
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

    # Additional method to generate XML response if needed
    def generate_xml_response(self, thought: str, action: dict = None, answer: str = None) -> str:
        response = ET.Element('response')
        thought_elem = ET.SubElement(response, 'thought')
        thought_elem.text = thought
        if action:
            action_elem = ET.SubElement(response, 'action')
            name_elem = ET.SubElement(action_elem, 'name')
            name_elem.text = action['name']
            reason_elem = ET.SubElement(action_elem, 'reason')
            reason_elem.text = action['reason']
            input_elem = ET.SubElement(action_elem, 'input')
            input_elem.text = action['input']
        if answer:
            answer_elem = ET.SubElement(response, 'answer')
            answer_elem.text = answer
        return ET.tostring(response, encoding='unicode')
      ]]></file_code>
    </file>
    <file>
      <file_summary>Modified the configuration to support detailed task history and error message logging.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/core/config.py</file_path>
      <file_code><![CDATA[
# src/core/config.py
from pydantic import BaseModel, Field


class Config(BaseModel):
    name: str = Field(
        title="Agent Name", description="The name of the agent", default="Default Agent"
    )
    role: str = Field(
        title="Agent Role",
        description="The role of the agent in the system",
        default="Default role for the agent",
    )
    model: str = Field(
        title="Model",
        description="The model to be used for completion",
        default="ollama/qwen2.5-coder:14b",
    )
    temperature: float = Field(
        0.7, title="Temperature", description="Sampling temperature"
    )
    max_tokens: int = Field(
        4096, title="Max Tokens", description="Maximum number of tokens to generate"
    )
    enable_task_history: bool = Field(
        True, title="Enable Task History", description="Toggle for detailed task history logging"
    )
    log_error_messages: bool = Field(
        True, title="Log Error Messages", description="Toggle for logging error messages during execution"
    )
      ]]></file_code>
    </file>
    <file>
      <file_summary>Enhanced the Message model to include timestamp information for each task.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/models/message.py</file_path>
      <file_code><![CDATA[
# src/models/message.py
from pydantic import BaseModel, Field
from datetime import datetime


class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender.")
    content: str = Field(..., description="The content of the message.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="The timestamp of the message.")
      ]]></file_code>
    </file>
    <file>
      <file_summary>Updated the ResponseStats model to capture additional statistics related to task execution.</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/models/responsestats.py</file_path>
      <file_code><![CDATA[
# src/models/responsestats.py
from pydantic import BaseModel, Field


class ResponseStats(BaseModel):
    """Response statistics for the agent."""

    content: str = Field(
        title="Response Content",
        description="The content generated by the agent.",
    )
    prompt_tokens: int = Field(
        title="Prompt Tokens",
        description="Number of tokens used in the prompt.",
    )
    completion_tokens: int = Field(
        title="Completion Tokens",
        description="Number of tokens generated in the completion.",
    )
    total_tokens: int = Field(
        title="Total Tokens",
        description="Total number of tokens used (input + output).",
    )
    tokens_per_second: float = Field(
        title="Tokens Per Second",
        description="The rate of tokens generated per second.",
    )
    execution_time: float = Field(
        title="Execution Time",
        description="Time taken to generate the response in seconds.",
    )
      ]]></file_code>
    </file>
  </changed_files>
</code_changes>
```
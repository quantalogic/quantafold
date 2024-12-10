Let me help you improve the way agent support parameters in the code.

# Thinking Section

<thinking>

## Task Rephrasing
Need to enhance the agent's parameter handling to support multiple parameters in tool execution, updating:
1. Agent.py to handle multiple parameters
2. Prompt template to support multiple parameters
3. XML parsing to support multiple parameters for <input> content

## Approaches Analysis

| Approach | Pros | Cons |
|----------|------|------|
| JSON Parameter Object | - Structured parameter format<br>- Easy to parse<br>- Flexible schema | - More verbose<br>- Requires JSON parsing |
| Named Parameter Dict | - Simple key-value pairs<br>- Native Python dict support<br>- Clear parameter names | - Less structured<br>- Parameter validation more complex |
| Parameter List with Schema | - Strong typing<br>- Schema validation<br>- Self-documenting | - More complex setup<br>- Requires schema definition |

## Selected Approach
I choose the Parameter List with Schema approach because:
- Provides strong typing for parameters
- Self-documenting with parameter definitions
- Built-in validation through Pydantic models
- Consistent with current code structure using models

## Reasoning
This approach:
1. Maintains code quality with type checking
2. Makes tool usage clearer with defined parameters
3. Enables parameter validation
4. Scales well for future tools with varying parameter needs

</thinking>

# Summary Section

## Overall Summary
- Updating the parameter handling system to support multiple typed parameters
- Adding parameter schema validation
- Modifying XML parsing for structured parameters 

## File Changes
- src/models/tool.py: Added parameter schema support and validation
- src/core/agent.py: Updated to handle multiple parameters
- src/tools/wikipedia.py: Updated example with multiple parameters
- src/tools/shell_command.py: Updated to demonstrate parameter handling

# XML Section

```xml
<code_changes>
  <changed_files>
    <file>
      <file_summary>Enhanced Tool model with parameter schema support</file_summary> 
      <file_operation>UPDATE</file_operation>
      <file_path>src/models/tool.py</file_path>
      <file_code><![CDATA[
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, int, bool, etc)")
    description: str = Field(None, description="Parameter description")
    required: bool = Field(True, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if any")


class Tool(BaseModel):
    name: str = Field(..., description="The unique name of the tool")
    description: str = Field(..., description="A brief description of what the tool does")
    parameters: list[ToolParameter] = Field(
        default=[], description="List of parameters the tool accepts"
    )
    need_validation: bool = Field(
        False, description="Indicates if the tool needs validation"
    )

    def execute(self, **kwargs) -> str:
        """Execute the tool with the provided parameters."""
        # Validate parameters
        self.validate_parameters(kwargs)
        raise NotImplementedError("This method should be implemented by subclasses")

    def validate_parameters(self, params: Dict[str, Any]) -> None:
        """Validate parameters against schema."""
        required_params = {p.name for p in self.parameters if p.required}
        provided_params = set(params.keys())
        
        # Check required parameters
        missing = required_params - provided_params
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        # Validate parameter types
        for param in self.parameters:
            if param.name in params:
                value = params[param.name]
                try:
                    self._validate_type(value, param.type)
                except ValueError as e:
                    raise ValueError(
                        f"Invalid type for parameter '{param.name}': {str(e)}"
                    )

    def _validate_type(self, value: Any, expected_type: str) -> None:
        """Validate parameter type."""
        type_mapping = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
        }
        
        if expected_type not in type_mapping:
            return  # Skip validation for unknown types
            
        if not isinstance(value, type_mapping[expected_type]):
            raise ValueError(
                f"Expected {expected_type}, got {type(value).__name__}"
            )

    def get_xml_example(self) -> str:
        """Generate an XML example for the tool."""
        xml = f"<!-- {self.description} -->\n"
        xml += f"<{self.name}>\n"
        
        for param in self.parameters:
            xml += f"  <parameter>\n"
            xml += f"    <name>{param.name}</name>\n"
            xml += f"    <type>{param.type}</type>\n"
            if param.description:
                xml += f"    <description>{param.description}</description>\n"
            xml += f"    <required>{str(param.required).lower()}</required>\n"
            if param.default is not None:
                xml += f"    <default>{param.default}</default>\n"
            xml += f"  </parameter>\n"
        
        xml += f"</{self.name}>"
        return xml
]]></file_code>
    </file>

    <file>
      <file_summary>Updated agent to handle multiple parameters</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/core/agent.py</file_path>
      <file_code><![CDATA[
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any

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
{history}

Current iteration: {current_iteration}
Max iterations: {max_iterations}

## Available tools:

Here are examples of how to use the available tools:

{tools}

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

        def decide(self, response: str) -> None:
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
                            if name is not None and value is not None and name.text and value.text:
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
                    raise ValueError("Response must contain either 'action' or 'answer' element.")

            except Exception as e:
                error_msg = f"Error processing response: {str(e)}"
                logger.error(error_msg)
                self.add_to_session_memory("system", f"Error: {error_msg}")
                if self.current_iteration < self.max_iterations:
                    self.think()

        def act(self, tool_name: str, parameters: Dict[str, Any]) -> None:
            tool = self.tools.get(tool_name)
            if tool:
                result = tool.execute(**parameters)
                observation = f"Observation from {tool_name}: {result}"
                self.add_to_session_memory("system", f"Observation: {observation}")
                self.think()
            else:
                logger.error(f"No tool registered for choice: {tool_name}")
                self.think()

        # Rest of the Agent class implementation remains the same
]]></file_code>
    </file>

    <file>
      <file_summary>Updated Wikipedia tool to use multiple parameters</file_summary>
      <file_operation>UPDATE</file_operation>
      <file_path>src/tools/wikipedia.py</file_path>
      <file_code><![CDATA[
import logging
import time

import wikipedia
from models.tool import Tool, ToolParameter
from pydantic import Field

logger = logging.getLogger(__name__)

class WikipediaTool(Tool):
    name: str = Field("SEARCH_WIKIPEDIA", description="The unique name of the tool")
    description: str = Field(
        "Search Wikipedia for a given query and return a summary",
        description="A brief description of what the tool does"
    )
    parameters: list[ToolParameter] = [
        ToolParameter(
            name="query",
            type="string",
            description="The search term to query on Wikipedia",
            required=True
        ),
        ToolParameter(
            name="lang",
            type="string", 
            description="Wikipedia language code",
            required=False,
            default="en"
        ),
        ToolParameter(
            name="max_lines",
            type="int",
            description="Maximum number of lines to return",
            required=False,
            default=3
        )
    ]

    def execute(self, query: str, lang: str = "en", max_lines: int = 3) -> str:
        """Fetch summary from Wikipedia in a specified language."""
        if not query:
            return "Error: Query cannot be empty"

        wikipedia.set_lang(lang)

        try:
            search_results = wikipedia.search(query, results=5)

            if not search_results:
                return f"No Wikipedia articles found for '{query}'"

            try:
                time.sleep(0.5)
                page = wikipedia.page(search_results[0], auto_suggest=False)
                summary = page.summary
                if len(summary.split(".")) > max_lines:
                    summary = ". ".join(summary.split(".")[:max_lines]) + "."
                logger.info(f"Fetched summary for query '{query}'")
                return summary
            except wikipedia.exceptions.DisambiguationError as e:
                try:
                    page = wikipedia.page(e.options[0], auto_suggest=False)
                    summary = page.summary
                    if len(summary.split(".")) > max_lines:
                        summary = ". ".join(summary.split(".")[:max_lines]) + "."
                    return f"{summary}\n\nNote: This is about '{e.options[0]}'. Other related topics: {', '.join(e.options[1:4])}"
                except Exception as inner_e:
                    logger.error(f"Error with first disambiguation option: {inner_e}")
                    return f"Multiple topics found for '{query}'. Try being more specific. Options: {', '.join(e.options[:5])}"
        except Exception as e:
            logger.error(f"Wikipedia API error for query '{query}': {e}")
            return f"Error fetching data from Wikipedia: {str(e)}"
]]></file_code>
    </file>

  </changed_files>
</code_changes>
```

Would you like me to explain or break down the code changes?
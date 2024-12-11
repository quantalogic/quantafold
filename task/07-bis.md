<code_changes>
  <changed_files>
    <file>
      <file_summary>Implements new LLM Agent tool for generating AI responses with specified personas</file_summary>
      <file_operation>CREATE</file_operation>
      <file_path>src/tools/llm_agent.py</file_path>
      <file_code><![CDATA[
import logging
from typing import List

from models.tool import Tool, ToolArgument
from core.generative_model import GenerativeModel
from pydantic import Field

logger = logging.getLogger(__name__)


class LLMAgentError(Exception):
    """Custom exception for LLM Agent errors."""
    pass


class LLMAgentTool(Tool):
    name: str = Field("LLM_AGENT", description="An LLM Agent tool.")
    description: str = Field(
        "Generate AI responses using a specified persona and prompt.",
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="persona",
                type="string",
                description="A detailed description of the persona for the LLM Agent.",
            ),
            ToolArgument(
                name="prompt",
                type="string",
                description="The prompt to send to the LLM Agent.",
            ),
            ToolArgument(
                name="temperature",
                type="float",
                description="The temperature for response generation (0.0 to 1.0).",
                default="0.7",
            ),
        ]
    )

    need_validation: bool = Field(
        True, description="Indicates if the tool needs validation."
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.model = GenerativeModel()

    def execute(self, persona: str, prompt: str, temperature: str = "0.7") -> str:
        """Generate a response using the LLM Agent with specified persona."""
        if not prompt.strip():
            logger.error("Prompt cannot be empty or whitespace.")
            return "Error: Prompt cannot be empty."

        if not persona.strip():
            logger.error("Persona cannot be empty or whitespace.")
            return "Error: Persona cannot be empty."

        try:
            # Convert temperature string to float
            temp_value = float(temperature)
            if not 0.0 <= temp_value <= 1.0:
                logger.error(f"Temperature {temp_value} out of valid range (0.0-1.0)")
                return "Error: Temperature must be between 0.0 and 1.0"

            # Update model temperature
            self.model.temperature = temp_value
            
            # Update model role with persona
            self.model.role = persona

            # Generate response
            response = self.model.generate(prompt)
            
            logger.info(f"Successfully generated response for prompt with persona")
            return response.content

        except ValueError as e:
            error_msg = f"Invalid temperature value: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            raise LLMAgentError(error_msg) from e
]]></file_code>
    </file>
  </changed_files>
</code_changes>
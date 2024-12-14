import logging
from typing import List

from core.generative_model import GenerativeModel
from models.tool import Tool, ToolArgument
from pydantic import Field

logger = logging.getLogger(__name__)


class LLMAgentError(Exception):
    """Custom exception for LLM Agent errors."""

    pass


class LLMAgentTool(Tool):
    name: str = Field("LLM_AGENT", description="An LLM Agent tool.")
    description: str = Field(
        """
        Generates AI responses based on a specified persona, prompt, and context.
        Note that the LLM Agent operates without prior conversation memory;
        therefore, it is essential to include all relevant information in the context parameter,
        as it is a mandatory requirement. The context must be up to 20000 tokens in length.
        Agent must be used for creative writing or to get information the knowledge of AI.
        YOU MUST BE SURE TO INCLUDE ALL RELEVANT INFORMATION IN THE context PARAMETER.
        IT IS A MANDATORY REQUIREMENT.
        """,
        description="A brief description of what the tool does.",
    )

    arguments: List[ToolArgument] = Field(
        default_factory=lambda: [
            ToolArgument(
                name="persona",
                type="string",
                description="A detailed description of the persona for the LLM Agent.",
                required=True,
            ),
            ToolArgument(
                name="prompt",
                type="string",
                description="""
                The prompt to send to the LLM Agent. It must include
                all necessary information for the LLM Agent to generate
                a response. As the agent as no access to prior conversation
                memory, it is important to include all relevant information
                in the context parameter.
                It must be up to 20000 tokens in length.
                """,
                required=True,
            ),
            ToolArgument(
                name="context",
                type="string",
                description="""
                The context to include in the prompt for the LLM Agent.
                This should include all relevant information for the LLM Agent
                to generate a response. This content can be used to contextualize
                the prompt. It can be up to 20000 tokens in length.
                """,
                required=False,
                default="",
            ),
            ToolArgument(
                name="temperature",
                type="string",  # Keep as string to allow string input
                description="""
                The temperature for response generation (0.0 to 1.0).
                0: no creavity
                1: creative, but high risk of hallicantion or invented facts
                """,
                default="0.7",
            ),
        ]
    )

    need_validation: bool = Field(
        True, description="Indicates if the tool needs validation."
    )

    def __init__(self, model: GenerativeModel, **data):
        # Use the base Tool's __init__ without passing the model
        super().__init__(**data)
        # Store the model as an instance attribute
        self._model = model

    def execute(
        self,
        persona: str,
        prompt: str,
        context: str = "",
        temperature: str = "0.7",
        parent_context: str = "",
    ) -> str:
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
            self._model.temperature = temp_value

            # Update model role with persona
            self._model.role = persona

            # Generate response
            full_prompt = (
                f"Parent Contex: {parent_context}\nContext:\n{context}\nQuery: {prompt}"
            )
            print("Agent Prompt:")
            print(full_prompt)
            response = self._model.generate(full_prompt)

            logger.info("Successfully generated response for prompt with persona")
            return response.content

        except ValueError as e:
            error_msg = f"Invalid temperature value: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            raise LLMAgentError(error_msg) from e

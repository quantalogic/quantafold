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
                description="Defines the personality, expertise, and tone the AI should adopt (e.g., 'expert physicist', 'creative writer').",
                required=True,
            ),
            ToolArgument(
                name="prompt",
                type="string", 
                description="""The main instruction or question for the AI agent.
                - Max length: 20,000 tokens
                - Must be clear and specific
                - Include all necessary context as there's no conversation memory
                - Variable interpolation: References outputs from previous workflow steps using $step_name$ 
                - Single interpolation: 'Analyze the text from $step_1$'
                - Multiple interpolations: 'Compare reports from $step_1$ and $step_2$'
                - Invalid references will be left as-is: '$invalid_step$'""",
                required=True,
            ),
            ToolArgument(
                name="context",
                type="string",
                description="""Additional background information or data for the AI.
                - Max length: 20,000 tokens
                - Optional but recommended for better responses
                - Supports all interpolation features described in prompt parameter
                - Example: 'Analysis: $step_1$\nMetadata: $step_2$'
                """,
                required=False,
                default="",
            ),
            ToolArgument(
                name="temperature",
                type="string",
                description="""Controls response creativity and randomness (0.0 to 1.0):
                - 0.0: Focused, deterministic, factual
                - 0.3: Balanced, mostly factual
                - 0.7: Creative but controlled (default)
                - 1.0: Maximum creativity, higher risk of inaccuracies""",
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
    ) -> str:
        """Generate a response using the LLM Agent with specified persona."""
        if not prompt.strip():
            logger.error("Prompt cannot be empty or whitespace.")
            raise ValueError("Error: Prompt cannot be empty.")

        if not persona.strip():
            logger.error("Persona cannot be empty or whitespace.")
            raise ValueError("Error: Persona cannot be empty.")

        try:
            # Convert temperature string to float
            temp_value = float(temperature)
            if not 0.0 <= temp_value <= 1.0:
                logger.error(f"Temperature {temp_value} out of valid range (0.0-1.0)")
                raise ValueError("Error: Temperature must be between 0.0 and 1.0")

            # Update model temperature
            self._model.temperature = temp_value

            # Update model role with persona
            self._model.role = persona

            # Generate response
            full_prompt = f"Context:\n{context}\nQuery: {prompt}"
            response = self._model.generate(full_prompt)

            logger.info("Successfully generated response for prompt with persona")
            return response.content

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            raise LLMAgentError(error_msg) from e

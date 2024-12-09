import time

from litellm import completion, token_counter
from pydantic import BaseModel, Field


class ResponseStats(BaseModel):
    """Reponse for the agent."""

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


class Agent(BaseModel):
    name: str = Field(title="Agent Name", description="The name of the agent")
    role: str = Field(
        title="Agent Role", description="The role of the agent in the system"
    )
    model: str = Field(
        default="ollama/qwen2.5-coder:14b",
        title="Agent Model", 
        description="The model used by the agent",
    )
    temperature: float = Field(
        default=0.7,
        title="Agent Temperature",
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=4096,
        title="Agent Max Tokens",
        description="Maximum number of tokens to generate",
    )

    @classmethod
    def from_config(cls, config: dict = None):
        default_config = {
            "model": "ollama/qwen2.5-coder:14b",
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        config = config or default_config
        return cls(**config)

    def get_response(self, message: str) -> ResponseStats:
        """Get response from the agent along with token statistics."""
        start_time = time.time()  # Start timing

        response = completion(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            system_prompt=self.role,
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": message}],
            get_token_count=True,  # Ensure token count is returned
        )

        end_time = time.time()  # End timing

        # Calculate the elapsed time and tokens per second
        elapsed_time = end_time - start_time
        token_usage = response.usage  # This contains token counts

        tokens_per_second = (
            (token_usage.total_tokens / elapsed_time) if elapsed_time > 0 else 0
        )

        return ResponseStats(
            content=response.choices[0].message.content,
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens,
            tokens_per_second=tokens_per_second,
        )

    def get_token_count(self, message: str) -> int:
        return token_counter(
            model=self.model, messages=[{"role": "user", "content": message}]
        )

from litellm import completion
from pydantic import BaseModel, Field


class Agent(BaseModel):
    name: str = Field(title="Agent Name", description="The name of the agent")
    role: str = Field(
        title="Agent Role", description="The role of the agent in the system"
    )
    model: str = Field(title="Agent Model", description="The model used by the agent")
    temperature: float = Field(
        0.7, title="Agent Temperature", description="Sampling temperature"
    )
    max_tokens: int = Field(
        4096,
        title="Agent Max Tokens",
        description="Maximum number of tokens to generate",
    )

    def __init__(self, config: dict = None):
        default_config = {
            "model": "ollama/qwen2.5-coder:14b",
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        config = config or default_config
        super().__init__(**config)

    def get_response(self, message: str) -> str:
        response = completion(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            messages=[{"role": self.role, "content": message}],
        )
        return response.choices[0].message.content

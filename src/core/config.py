from pydantic import BaseModel, Field


class Config(BaseModel):
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

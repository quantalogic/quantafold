# src/react/agent.py
# Disable all litellm logging before any imports
import logging
import os

# Configure litellm
import litellm
from litellm import completion

from models.message import Message
from models.responsestats import ResponseStats

os.environ["LITELLM_LOG_LEVEL"] = "ERROR"
logging.getLogger().setLevel(logging.ERROR)

litellm.set_verbose = False


# Ensure no logging propagation
for name in logging.root.manager.loggerDict:
    if name.startswith(("litellm", "openai", "httpx")):
        logging.getLogger(name).setLevel(logging.ERROR)
        logging.getLogger(name).propagate = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GenerativeModel:
    def __init__(
        self,
        role: str = "You are a helpful assistant.",
        model: str = "ollama/qwen2.5-coder:14b",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> None:
        self.role = role
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate_with_history(
        self, messages_history: list[Message], prompt: str
    ) -> ResponseStats:
        """Get response from the agent along with token statistics."""
        import time

        start_time = time.time()  # Start timing

        logger.debug(f"Prompt: {prompt}")

        response = completion(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            messages=[
                {"role": "system", "content": self.role},
                *messages_history,
                {"role": "user", "content": prompt},
            ],
        )

        end_time = time.time()  # End timing

        # Calculate the elapsed time and tokens per second
        elapsed_time = end_time - start_time
        token_usage = response.usage  # This contains token counts

        tokens_per_second = (
            (token_usage.total_tokens / elapsed_time) if elapsed_time > 0 else 0
        )

        logger.debug(f"Prompt tokens: {token_usage.prompt_tokens}")
        logger.debug(f"Completion tokens: {token_usage.completion_tokens}")
        logger.debug(f"Tokens per second: {tokens_per_second}")
        logger.debug(f"Content: {response.choices[0].message.content}")

        return ResponseStats(
            content=response.choices[0].message.content,
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            total_tokens=token_usage.total_tokens,
            tokens_per_second=tokens_per_second,
            execution_time=elapsed_time,
        )

    def generate(self, prompt: str) -> ResponseStats:
        """Get response from the agent along with token statistics."""

        return self.generate_with_history([], prompt)

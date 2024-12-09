# src/react/agent.py
import logging

from litellm import completion, token_counter

from models.responsestats import ResponseStats

logger = logging.getLogger(__name__)


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

    def generate(self, prompt: str) -> ResponseStats:
        """Get response from the agent along with token statistics."""
        import time

        start_time = time.time()  # Start timing

        response = completion(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model=self.model,
            system_prompt=self.role,
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": prompt},
            ],
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

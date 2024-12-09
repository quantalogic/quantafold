from pydantic import Field

from core.agent import Agent
from model.step import Step
from model.task import Task

REACT_AGENT_ROLE = """
Your an AI assistant that helps break down tasks into steps.
Your role is to reason, and decompose complex problems into simpler parts.
You will be given a task, and your job is to break it down into smaller parts.
"""


class ReactAgent(Agent):
    reason_agent: Agent = Field(
        None, title="Reason Agent", description="Agent for reasoning about tasks"
    )

    # init reason agent
    def __init__(self, config: dict = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if config is None:
            config = {}
        config["name"] = "Reason Agent"
        config["role"] = REACT_AGENT_ROLE
        self.reason_agent = Agent(**config)

    @classmethod
    def from_config(cls, config: dict = None):
        default_config = {
            "name": "React Agent",
            "role": REACT_AGENT_ROLE,
            "model": "ollama/qwen2.5-coder:14b",
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        if config:
            default_config.update(config)
        instance = cls(**default_config)
        reason_config = default_config.copy()
        reason_config["name"] = "Reason Agent"
        instance.reason_agent = Agent(**reason_config)
        return instance

    def reason_and_decompose(self, message: str) -> list[Step]:
        """Reason about a task and decompose it into steps."""
        prompt = f"""
You are an AI assistant that helps break down tasks into steps.
Your response must be in JSON format as specified below.

For this task: "{message}"

Respond ONLY with a JSON object in this exact format:
{{
    "thinking": "Your reasoning about the task",
    "task": "{message}",
    "steps": [
        {{
            "id": "Step 1",
            "description": "First step description"
        }},
        {{
            "id": "Step 2",
            "description": "Second step description"
        }}
    ]
}}
        """

        response = self.reason_agent.get_response(prompt)
        print(response)
        # Extract the task and steps from the response parse ```json
        steps: list[Step] = self._extract_steps(response.content)
        return steps

    def ask(self, message: str) -> str:
        self.task = Task(id="1", description=message, steps=[])
        self.steps = self.reason_and_decompose(message)

    def _extract_steps(self, response: str) -> list[Step]:
        import json

        print(response)

        # Split lines
        lines = response.split("\n")

        # Remove first and last line if they start with ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]

        # Join lines into a single string
        response = "\n".join(lines)

        # Parse the JSON content
        data = json.loads(response)

        # Extract the task and steps
        return [
            Step(
                id=step["id"],
                description=step["description"],
                step_result="",  # Default empty result
                done=False,  # Default to not done
            )
            for step in data.get("steps", [])
        ]

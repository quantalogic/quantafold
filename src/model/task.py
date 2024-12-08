from pydantic import BaseModel, Field

from model.step import Step


class Task(BaseModel):
    """Task model representing a task with its details."""

    id: str = Field(title="Task ID", description="Unique identifier for the task")
    description: str = Field(
        title="Task Description", description="Description of the task"
    )
    steps: list[Step] = Field(
        title="Task Steps", description="List of steps in the task",
    )

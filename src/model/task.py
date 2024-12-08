from pydantic import BaseModel, Field


class Task(BaseModel):
    """Task model representing a task with its details."""

    id: str = Field(title="Task ID", description="Unique identifier for the task")
    title: str = Field(title="Task Title", description="Title of the task")
    description: str = Field(
        title="Task Description", description="Detailed description of the task",
    )
    completed: bool = Field(
        False,
        title="Completion Status",
        description="Indicates if the task is completed",
    )
    subtasks: list[str] = Field(
        default_factory=list,
        title="Subtasks",
        description="List of subtasks associated with the task",
    )

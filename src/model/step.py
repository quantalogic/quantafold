from pydantic import BaseModel, Field


class Step(BaseModel):
    """Base class for all steps in the workflow."""

    id: str = Field(title="Step Id", description="The id of the step.")
    description: str = Field(
        title="Step Description", description="The description of the step."
    )
    step_result: str = Field(title="Step Result", description="The result of the step.")
    done: bool = Field(title="Step Done", description="Indicates if the step is done.")

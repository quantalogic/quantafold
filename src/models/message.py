from datetime import datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender.")
    content: str = Field(..., description="The content of the message.")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="The timestamp of the message."
    )

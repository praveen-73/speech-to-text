from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TranscriptionIn(BaseModel):
    title: str = Field(default="Untitled", max_length=200)
    text: str = ""
    language: str = "hi-en"
    duration_sec: float = 0.0


class TranscriptionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str | None = None


class TranscriptionOut(TranscriptionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime

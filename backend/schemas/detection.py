"""Detection task API schemas."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class DetectionStartRequest(BaseModel):
    video_id: str = Field(min_length=1)


class DetectionTaskRead(BaseModel):
    id: str
    video_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress: int = Field(ge=0, le=100)
    current_frame: int
    error: str | None = None
    result: dict[str, Any] | None = None
    output_path: Path | None = Field(default=None, exclude=True)
    video_url: str | None = None
    created_at: datetime
    updated_at: datetime

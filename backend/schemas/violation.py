"""Violation API schema."""

from datetime import datetime

from pydantic import BaseModel


class ViolationRead(BaseModel):
    id: int
    task_id: str
    video_id: str
    track_id: int
    source_lane: str
    destination_lane: str
    frame_index: int
    timestamp_seconds: float
    detected_at: datetime
    evidence_path: str | None

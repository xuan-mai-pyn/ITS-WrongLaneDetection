"""Wrong-lane violation domain and API model."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Violation(BaseModel):
    track_id: int
    source_lane: str
    destination_lane: str
    frame_index: int = Field(ge=0)
    timestamp_seconds: float = Field(ge=0)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_path: str | None = None

"""Video API schemas."""

from datetime import datetime

from pydantic import BaseModel


class VideoRead(BaseModel):
    id: str
    original_filename: str
    size_bytes: int
    uploaded_at: datetime
    status: str
    processing_seconds: float | None
    vehicle_type_counts: dict[str, int]
    processed_frames: int
    vehicle_count: int
    violation_count: int

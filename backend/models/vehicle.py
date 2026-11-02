"""Vehicle detection domain model."""

from pydantic import BaseModel, ConfigDict, Field


class Vehicle(BaseModel):
    model_config = ConfigDict(frozen=True)

    box: tuple[float, float, float, float] = Field(description="Bounding box in xyxy pixels.")
    confidence: float = Field(ge=0, le=1)
    class_id: int
    label: str
    track_id: int | None = None

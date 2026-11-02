"""Camera-specific polygon lane lookup; lane geometry is never inferred by YOLO."""

import json
from pathlib import Path

from backend.models.lane import Lane


class LaneDetector:
    """Assign image points to explicitly configured lane polygons."""

    def __init__(self, lanes: list[Lane] | None = None) -> None:
        self.lanes = lanes or []

    @classmethod
    def from_json(cls, path: Path | None) -> "LaneDetector":
        if path is None:
            return cls()
        if not path.is_file():
            raise FileNotFoundError(f"Lane configuration was not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_lanes = payload.get("lanes")
        if not isinstance(raw_lanes, list):
            raise ValueError("Lane configuration must contain a 'lanes' array.")
        return cls([Lane.model_validate(item) for item in raw_lanes])

    def lane_at(self, point: tuple[float, float]) -> str | None:
        """Return the first lane containing the image point, if any."""
        for lane in self.lanes:
            if lane.contains(point):
                return lane.id
        return None

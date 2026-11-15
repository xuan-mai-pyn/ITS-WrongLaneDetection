"""Validated data model for a camera-configured traffic lane."""

from math import isfinite
from numbers import Real
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


class Lane(BaseModel):
    """A lane represented by a manually configured polygon in video pixels.

    Attributes:
        lane_id: Stable identifier for this lane. The legacy input key ``id``
            is also accepted for compatibility with the lane configuration.
        name: Human-readable lane name. If omitted, it defaults to ``lane_id``.
        polygon: Polygon vertices as ``(x, y)`` pixel-coordinate pairs in
            source-video coordinates, ordered around the polygon.
        allowed_vehicle_types: Vehicle labels permitted in this lane. The
            project does not define a closed vocabulary, so non-empty strings
            are accepted without restricting the labels.
        direction: Optional free-form description of the valid travel
            direction. No direction vocabulary is imposed by the project.
    """

    lane_id: str = Field(
        validation_alias=AliasChoices("lane_id", "id"),
        min_length=1,
        description="Stable lane identifier.",
    )
    name: str = Field(min_length=1, description="Human-readable lane name.")
    polygon: list[tuple[float, float]] = Field(
        min_length=3,
        description="Polygon vertices as (x, y) pixels in source-video coordinates.",
    )
    allowed_vehicle_types: list[str] = Field(default_factory=list)
    direction: str | None = None

    @model_validator(mode="before")
    @classmethod
    def default_name_to_lane_id(cls, data: Any) -> Any:
        """Use the lane ID as a name for legacy configurations without one."""
        if isinstance(data, dict) and "name" not in data:
            lane_id = data.get("lane_id", data.get("id"))
            if lane_id is not None:
                return {**data, "name": lane_id}
        return data

    @field_validator("lane_id", "name", mode="before")
    @classmethod
    def require_nonempty_text(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must be a non-empty string.")
        return value.strip()

    @field_validator("polygon", mode="before")
    @classmethod
    def validate_polygon_coordinates(cls, value: Any) -> list[tuple[float, float]]:
        if not isinstance(value, (list, tuple)) or len(value) < 3:
            raise ValueError("polygon must contain at least three vertices.")

        vertices: list[tuple[float, float]] = []
        for index, point in enumerate(value):
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(f"polygon vertex {index} must contain exactly two coordinates.")

            coordinates: list[float] = []
            for coordinate in point:
                if isinstance(coordinate, bool) or not isinstance(coordinate, Real):
                    raise ValueError("polygon coordinates must be finite numbers.")
                try:
                    pixel_coordinate = float(coordinate)
                except (OverflowError, ValueError):
                    raise ValueError("polygon coordinates must be finite numbers.") from None
                if not isfinite(pixel_coordinate):
                    raise ValueError("polygon coordinates must be finite numbers.")
                coordinates.append(pixel_coordinate)

            vertices.append((coordinates[0], coordinates[1]))
        return vertices

    @field_validator("allowed_vehicle_types")
    @classmethod
    def validate_allowed_vehicle_types(cls, value: list[str]) -> list[str]:
        normalized_types = [vehicle_type.strip() for vehicle_type in value]
        if any(not vehicle_type for vehicle_type in normalized_types):
            raise ValueError("allowed vehicle types must be non-empty strings.")
        return normalized_types

    @field_validator("direction", mode="before")
    @classmethod
    def validate_direction(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("direction must be a non-empty string when provided.")
        return value.strip()

    @property
    def id(self) -> str:
        """Return the lane identifier using the legacy attribute name."""
        return self.lane_id

    def contains(self, point: tuple[float, float]) -> bool:
        """Return whether an image-coordinate point lies inside the polygon."""
        x, y = point
        inside = False
        previous_x, previous_y = self.polygon[-1]
        for current_x, current_y in self.polygon:
            crosses = (current_y > y) != (previous_y > y)
            if crosses:
                intersection_x = (
                    (previous_x - current_x) * (y - current_y)
                    / (previous_y - current_y)
                    + current_x
                )
                if x < intersection_x:
                    inside = not inside
            previous_x, previous_y = current_x, current_y
        return inside

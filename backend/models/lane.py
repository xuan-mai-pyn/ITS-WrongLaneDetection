"""Configured lane polygon model."""

from pydantic import BaseModel, Field


class Lane(BaseModel):
    id: str = Field(min_length=1)
    polygon: list[tuple[float, float]] = Field(min_length=3)

    def contains(self, point: tuple[float, float]) -> bool:
        """Use a ray-casting point-in-polygon test in image coordinates."""
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

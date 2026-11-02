"""Small image-coordinate helpers shared by the video pipeline."""

from backend.models.vehicle import Vehicle


def vehicle_foot_point(vehicle: Vehicle) -> tuple[float, float]:
    """Return the bottom-center point, commonly used for road-lane membership."""
    x1, _, x2, y2 = vehicle.box
    return (x1 + x2) / 2, y2

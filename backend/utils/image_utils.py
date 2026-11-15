"""Small image-coordinate helpers shared by the video pipeline."""

from math import isfinite

from backend.models.vehicle import Vehicle


def vehicle_foot_point(vehicle: Vehicle) -> tuple[float, float]:
    """Trả về điểm giữa cạnh đáy của bounding box theo tọa độ ảnh.

    Bounding box phải có tọa độ hữu hạn theo định dạng ``(x1, y1, x2, y2)``
    và không bị đảo chiều. Giá trị trả về là ``(x, y)`` dạng số thực, phù hợp
    để kiểm tra điểm thuộc polygon làn đường.

    Raises:
        ValueError: Nếu bounding box chứa tọa độ không hữu hạn hoặc bị đảo chiều.
    """
    x1, y1, x2, y2 = vehicle.box

    if not all(isfinite(coordinate) for coordinate in (x1, y1, x2, y2)):
        raise ValueError("Bounding box coordinates must be finite numbers.")

    if x2 < x1 or y2 < y1:
        raise ValueError(
            "Bounding box coordinates must be ordered as (x1, y1, x2, y2)."
        )

    return (x1 + x2) / 2, y2

"""
Mô hình miền (domain model) của phương tiện được phát hiện trong khung hình.

Một đối tượng `Vehicle` là kết quả nhận diện của YOLO trên một khung hình,
kèm mã theo dõi (track_id) do ByteTrack gán khi có bật tracking.
Mô hình ở dạng bất biến (frozen) để tránh bị sửa nhầm giữa các bước xử lý
detector -> tracker -> kiểm tra làn đường.
"""

from pydantic import BaseModel, ConfigDict, Field


class Vehicle(BaseModel):
    """Một phương tiện được phát hiện (và có thể được theo dõi) trong một khung hình."""

    model_config = ConfigDict(frozen=True)

    box: tuple[float, float, float, float] = Field(
        description="Khung bao (bounding box) theo định dạng xyxy, đơn vị pixel."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Độ tin cậy của lần phát hiện, trong khoảng từ 0 đến 1.",
    )
    class_id: int = Field(description="Mã lớp đối tượng do mô hình YOLO trả về.")
    label: str = Field(description="Tên lớp đối tượng, ví dụ: car, motorcycle, bus, truck.")
    track_id: int | None = Field(
        default=None,
        description="Mã theo dõi do ByteTrack gán; None nếu chưa bật hoặc chưa gán được.",
    )
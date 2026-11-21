"""
Định nghĩa cấu trúc dữ liệu (Schemas) liên quan đến Vi phạm (Violation) cho API.

Quy định cấu trúc dữ liệu API biểu diễn một hành vi vi phạm làn đường:
    - Phương tiện vi phạm (track_id)
    - Làn đường bắt đầu và làn đường vi phạm (source_lane -> destination_lane)
    - Vị trí thời gian trong video (frame_index, timestamp_seconds)
    - Đường dẫn hình ảnh bằng chứng (evidence snapshot)

"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ViolationBase(BaseModel):
    """
    Thông tin cốt lõi của một hành vi vi phạm đi sai làn.
    """
    model_config = ConfigDict(from_attributes=True)

    track_id: int = Field(
        ...,
        ge=0,
        description="Mã định danh theo dõi (Tracker ID) của phương tiện vi phạm",
        example=12,
    )
    vehicle_type: str = Field(
        default="unknown",
        description="Loại phương tiện do YOLO nhận diện",
        example="car",
    )
    source_lane: str = Field(
        ...,
        min_length=1,
        description="Mã làn đường hợp lệ ban đầu của phương tiện",
        example="lane_car",
    )
    destination_lane: str = Field(
        ...,
        min_length=1,
        description="Mã làn đường mà phương tiện chuyển sang trái phép",
        example="lane_motorcycle",
    )
    frame_index: int = Field(
        ...,
        ge=0,
        description="Số thứ tự khung hình tại thời điểm xác nhận vi phạm",
        example=145,
    )
    timestamp_seconds: float = Field(
        ...,
        ge=0,
        description="Thời điểm xảy ra vi phạm tính từ đầu video (giây)",
        example=5.8,
    )


class ViolationRead(ViolationBase):
    """
    Schema chi tiết của bản ghi vi phạm trả về cho Frontend hiển thị lịch sử.

    Bao gồm thông tin liên kết với video, tác vụ và ảnh chụp bằng chứng vi phạm.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "task_id": "task-uuid-1234",
                "video_id": "video-uuid-5678",
                "track_id": 12,
                "vehicle_type": "car",
                "source_lane": "lane_car",
                "destination_lane": "lane_motorcycle",
                "frame_index": 145,
                "timestamp_seconds": 5.8,
                "detected_at": "2026-11-15T09:00:10Z",
                "evidence_path": "storage/evidence/task-uuid-1234-track-12-frame-145.jpg",
            }
        },
    )

    id: int = Field(
        ...,
        description="Mã số định danh tự tăng của bản ghi vi phạm trong database",
    )
    task_id: str = Field(
        ...,
        description="Mã tác vụ nhận diện đã phát hiện vi phạm này",
    )
    video_id: str = Field(
        ...,
        description="Mã video nguồn chứa vi phạm",
    )
    detected_at: datetime | str = Field(
        ...,
        description="Thời điểm hệ thống ghi nhận vi phạm vào cơ sở dữ liệu (ISO 8601)",
    )
    evidence_path: str | None = Field(
        default=None,
        description="Đường dẫn lưu file ảnh trích xuất khung hình vi phạm làm bằng chứng",
    )

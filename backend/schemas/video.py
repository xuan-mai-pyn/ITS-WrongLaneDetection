"""
Định nghĩa cấu trúc dữ liệu (Schemas) liên quan đến Video cho API.

Quy định cấu trúc dữ liệu đầu vào và đầu ra khi trao đổi qua REST API:
    - Tiếp nhận thông tin tải lên video
    - Trả về danh sách và chi tiết metadata của video
    - Thống kê phương tiện và vi phạm theo từng video

"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class VideoBase(BaseModel):
    """
    Thông tin cơ bản của video được tải lên.
    """
    model_config = ConfigDict(from_attributes=True)

    original_filename: str = Field(
        ...,
        description="Tên file gốc khi người dùng tải lên",
        example="traffic_sample_01.mp4",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Dung lượng file tính theo byte",
        example=15485760,
    )


class VideoUploadResponse(BaseModel):
    """
    Dữ liệu trả về ngay sau khi upload video thành công lên server.
    """
    id: str = Field(
        ...,
        description="Mã định danh duy nhất (UUID) của video được sinh ra",
        example="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    )
    original_filename: str = Field(
        ...,
        description="Tên file gốc",
        example="traffic_crossroad.mp4",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Dung lượng file (byte)",
    )
    uploaded_at: datetime | str = Field(
        ...,
        description="Thời điểm upload (định dạng chuẩn ISO 8601)",
    )
    status: str = Field(
        default="uploaded",
        description="Trạng thái khởi tạo ban đầu: uploaded",
        example="uploaded",
    )


class VideoRead(BaseModel):
    """
    Schema chi tiết của video khi truy vấn danh sách hoặc chi tiết qua API.

    Bao gồm các trường metadata ban đầu và toàn bộ kết quả tổng hợp
    sau khi tác vụ nhận diện hoàn thành (processed).
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "original_filename": "traffic_crossroad.mp4",
                "size_bytes": 10485760,
                "uploaded_at": "2026-11-15T08:30:00Z",
                "status": "processed",
                "processing_seconds": 12.45,
                "vehicle_type_counts": {
                    "car": 15,
                    "motorcycle": 28,
                    "bus": 2,
                    "truck": 3,
                },
                "processed_frames": 450,
                "vehicle_count": 48,
                "violation_count": 3,
            }
        },
    )

    id: str = Field(
        ...,
        description="Mã định danh duy nhất (UUID) của video trong hệ thống",
    )
    original_filename: str = Field(
        ...,
        description="Tên file gốc khi người dùng tải lên",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Dung lượng file tính theo byte",
    )
    uploaded_at: datetime | str = Field(
        ...,
        description="Thời điểm tải video lên hệ thống",
    )
    status: str = Field(
        ...,
        description="Trạng thái xử lý của video: uploaded, processing, processed, failed",
        example="processed",
    )
    processing_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Tổng thời gian thực hiện nhận diện và theo dõi (giây)",
        example=12.45,
    )
    vehicle_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Số lượng phương tiện phân chia theo từng loại: car, motorcycle, bus, truck",
    )
    processed_frames: int = Field(
        default=0,
        ge=0,
        description="Tổng số khung hình video đã đọc và xử lý",
        example=450,
    )
    vehicle_count: int = Field(
        default=0,
        ge=0,
        description="Tổng số phương tiện duy nhất được gán ID và theo dõi (unique tracker IDs)",
        example=48,
    )
    violation_count: int = Field(
        default=0,
        ge=0,
        description="Tổng số trường hợp vi phạm đi sai làn đường ghi nhận được trong video",
        example=3,
    )

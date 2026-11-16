"""
Định nghĩa cấu trúc dữ liệu (Schemas) liên quan đến Nhận diện (Detection) cho API.

Quy định cấu trúc dữ liệu API cho luồng xử lý nhận diện video:
    - Yêu cầu bắt đầu tác vụ nhận diện (Start Task)
    - Trạng thái và tiến trình thực hiện tác vụ (Task Status & Progress)
    - Chi tiết kết quả tổng hợp sau khi xử lý xong (Task Result)

"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


# ── Định nghĩa các trạng thái hợp lệ của một tác vụ nhận diện ──
TaskStatus = Literal["queued", "running", "completed", "failed"]


class DetectionStartRequest(BaseModel):
    """
    Yêu cầu bắt đầu tiến trình nhận diện cho một video đã tải lên.
    """
    video_id: str = Field(
        ...,
        min_length=1,
        description="Mã định danh (ID) của video cần xử lý nhận diện",
        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    )


class DetectionResultSummary(BaseModel):
    """
    Cấu trúc chi tiết của trường `result` trả về khi tác vụ hoàn thành.
    """
    model_config = ConfigDict(extra="allow")

    processed_frames: int = Field(
        ...,
        ge=0,
        description="Số lượng khung hình đã xử lý",
    )
    unique_tracked_vehicles: int = Field(
        ...,
        ge=0,
        description="Tổng số phương tiện duy nhất theo dõi được",
    )
    vehicle_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Thống kê số lượng theo loại xe",
    )
    violation_count: int = Field(
        default=0,
        ge=0,
        description="Số lượng vi phạm phát hiện được",
    )
    processing_seconds: float = Field(
        ...,
        ge=0,
        description="Thời gian xử lý tính bằng giây",
    )
    analysis_scope: str = Field(
        ...,
        description="Phạm vi phân tích: configured_lane_rules hoặc detection_only",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Danh sách cảnh báo phát sinh trong quá trình xử lý",
    )
    violations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Danh sách thông tin chi tiết từng vụ vi phạm",
    )


class DetectionTaskRead(BaseModel):
    """
    Thông tin trạng thái và kết quả của tác vụ nhận diện.

    Được Frontend sử dụng để hiển thị thanh tiến trình (progress bar),
    số khung hình đang xử lý và nhận link video kết quả sau khi hoàn thành.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "task-uuid-1234",
                "video_id": "video-uuid-5678",
                "status": "completed",
                "progress": 100,
                "current_frame": 450,
                "error": None,
                "result": {
                    "processed_frames": 450,
                    "unique_tracked_vehicles": 48,
                    "violation_count": 3,
                    "analysis_scope": "configured_lane_rules",
                },
                "video_url": "/api/detection/task-uuid-1234/video",
                "created_at": "2026-11-15T09:00:00Z",
                "updated_at": "2026-11-15T09:00:15Z",
            }
        },
    )

    id: str = Field(
        ...,
        description="Mã định danh duy nhất (UUID) của tác vụ nhận diện",
    )
    video_id: str = Field(
        ...,
        description="Mã định danh của video nguồn đang được xử lý",
    )
    status: TaskStatus = Field(
        ...,
        description="Trạng thái hiện tại: queued (chờ), running (đang chạy), completed (hoàn thành), failed (thất bại)",
    )
    progress: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Tiến độ xử lý tính theo phần trăm (0 - 100%)",
    )
    current_frame: int = Field(
        default=0,
        ge=0,
        description="Số thứ tự khung hình hiện tại đang được xử lý",
    )
    error: str | None = Field(
        default=None,
        description="Thông báo lỗi chi tiết nếu tác vụ gặp sự cố (status = failed)",
    )
    result: dict[str, Any] | None = Field(
        default=None,
        description="Dữ liệu tổng hợp kết quả nhận diện sau khi tác vụ hoàn thành",
    )
    output_path: Path | None = Field(
        default=None,
        exclude=True,
        description="Đường dẫn file video đầu ra trên ổ cứng (ẩn khi serialize ra API)",
    )
    video_url: str | None = Field(
        default=None,
        description="Đường dẫn API để xem hoặc tải video đã vẽ bounding box và cảnh báo vi phạm",
    )
    created_at: datetime | str = Field(
        ...,
        description="Thời điểm khởi tạo tác vụ (chuẩn ISO 8601)",
    )
    updated_at: datetime | str = Field(
        ...,
        description="Thời điểm cập nhật trạng thái gần nhất (chuẩn ISO 8601)",
    )

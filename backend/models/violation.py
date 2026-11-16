"""
Mô hình miền và mô hình API của một vi phạm đi sai làn đường.

Một vi phạm được ghi nhận khi phương tiện thực hiện một lần chuyển làn bị cấm
(`source_lane` -> `destination_lane`) và việc chuyển làn này được duy trì đủ số
khung hình xác nhận. Mỗi phương tiện chỉ bị báo một lần cho mỗi cặp làn.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Violation(BaseModel):
    """Bản ghi một hành vi chuyển làn trái quy định của một phương tiện."""

    track_id: int = Field(description="Mã theo dõi (ByteTrack) của phương tiện vi phạm.")
    source_lane: str = Field(description="Mã làn đường mà phương tiện xuất phát.")
    destination_lane: str = Field(
        description="Mã làn đường mà phương tiện chuyển sang trái quy định."
    )
    frame_index: int = Field(
        ge=0, description="Số thứ tự khung hình tại thời điểm xác nhận vi phạm."
    )
    timestamp_seconds: float = Field(
        ge=0, description="Thời điểm vi phạm tính từ đầu video, đơn vị giây."
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Thời điểm hệ thống ghi nhận vi phạm (UTC).",
    )
    evidence_path: str | None = Field(
        default=None,
        description="Đường dẫn ảnh bằng chứng đã lưu; None nếu chưa lưu được ảnh.",
    )
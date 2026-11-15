"""
Package schemas: Định nghĩa toàn bộ cấu trúc dữ liệu đầu vào và đầu ra cho REST API.

Tập hợp và xuất khẩu các schemas dùng chung:
    - Video schemas: VideoRead, VideoUploadResponse
    - Detection schemas: DetectionStartRequest, DetectionTaskRead, TaskStatus
    - Violation schemas: ViolationRead
"""

from backend.schemas.detection import (
    DetectionResultSummary,
    DetectionStartRequest,
    DetectionTaskRead,
    TaskStatus,
)
from backend.schemas.video import VideoBase, VideoRead, VideoUploadResponse
from backend.schemas.violation import ViolationBase, ViolationRead

__all__ = [
    "VideoBase",
    "VideoRead",
    "VideoUploadResponse",
    "DetectionStartRequest",
    "DetectionTaskRead",
    "DetectionResultSummary",
    "TaskStatus",
    "ViolationBase",
    "ViolationRead",
]

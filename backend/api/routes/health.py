"""
Endpoint kiểm tra trạng thái hoạt động (Health Check) của Backend.

Cung cấp thông tin về trạng thái máy chủ, phiên bản ứng dụng,
tình trạng kết nối cơ sở dữ liệu SQLite và trạng thái cấu hình mô hình AI.

Mục đích:
    - Giúp Frontend hoặc người vận hành kiểm tra Backend có đang sống hay không.
    - Cảnh báo sớm nếu thiếu file trọng số YOLO hoặc cấu hình làn đường.
    - Hỗ trợ giám sát hệ thống (monitoring) trong thực tế.

"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.api.dependencies import get_repository, get_settings
from backend.config import Settings
from backend.database.repository import Repository

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """
    Cấu trúc dữ liệu phản hồi kiểm tra sức khỏe hệ thống.
    """
    status: str = Field(
        default="ok",
        description="Trạng thái tổng quát của hệ thống: ok hoặc degraded",
        example="ok",
    )
    service: str = Field(
        default="its-wrong-lane-detection",
        description="Tên định danh dịch vụ",
        example="its-wrong-lane-detection",
    )
    version: str = Field(
        default="0.1.0",
        description="Phiên bản API hiện tại",
        example="0.1.0",
    )
    database: str = Field(
        default="connected",
        description="Trạng thái kết nối cơ sở dữ liệu SQLite",
        example="connected",
    )
    model_ready: bool = Field(
        default=False,
        description="Đã tìm thấy file trọng số mô hình YOLO hay chưa",
        example=True,
    )
    lane_config_ready: bool = Field(
        default=False,
        description="Đã cấu hình file tọa độ làn đường (ITS_LANE_CONFIG) hay chưa",
        example=False,
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Danh sách các cảnh báo cấu hình cần lưu ý",
    )


@router.get("/health", response_model=HealthResponse)
def health_check(
    request: Request,
    settings: Settings = Depends(get_settings),
    repository: Repository = Depends(get_repository),
) -> dict[str, Any]:
    """
    Kiểm tra trạng thái sẵn sàng hoạt động của hệ thống.

    Quy trình kiểm tra:
    1. Xác nhận server API đang nhận và phản hồi request.
    2. Kiểm tra kết nối tới cơ sở dữ liệu SQLite (thử truy vấn dữ liệu).
    3. Kiểm tra sự tồn tại của file weights mô hình YOLO.
    4. Kiểm tra cấu hình làn đường để xác định phạm vi phân tích (detection-only hay full-violation).
    """
    # ── 1. Kiểm tra kết nối Database SQLite ──
    db_status = "connected"
    try:
        repository.list_videos()
    except Exception as exc:
        db_status = f"error: {exc}"

    # ── 2. Kiểm tra tính sẵn sàng của mô hình và cấu hình làn ──
    is_model_ready = settings.model_path.is_file()
    is_lane_ready = (
        settings.lane_config_path is not None
        and settings.lane_config_path.is_file()
    )

    # ── 3. Thu thập cảnh báo từ settings.validate() ──
    warnings = settings.validate() if hasattr(settings, "validate") else []

    return {
        "status": "ok",
        "service": "its-wrong-lane-detection",
        "version": "0.1.0",
        "database": db_status,
        "model_ready": is_model_ready,
        "lane_config_ready": is_lane_ready,
        "warnings": warnings,
    }

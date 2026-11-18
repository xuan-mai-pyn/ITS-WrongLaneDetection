"""
API endpoints quản lý Video: upload, danh sách và chi tiết.

Cung cấp các endpoint REST cho Frontend giao tiếp:
    - POST /api/videos/upload  : Tải video lên hệ thống.
    - GET  /api/videos         : Lấy danh sách tất cả video đã tải.
    - GET  /api/videos/{id}    : Xem chi tiết metadata của một video.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.api.dependencies import get_repository, get_settings
from backend.config import Settings
from backend.database.repository import Repository
from backend.schemas.video import VideoRead
from backend.services.video_service import VideoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post(
    "/upload",
    response_model=VideoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tải video lên hệ thống",
    description=(
        "Tiếp nhận file video từ người dùng, kiểm tra định dạng và dung lượng, "
        "lưu vào thư mục storage/uploads/ và tạo bản ghi metadata trong database."
    ),
)
async def upload_video(
    file: UploadFile = File(..., description="File video cần phân tích"),
    settings: Settings = Depends(get_settings),
    repository: Repository = Depends(get_repository),
) -> VideoRead:
    """
    Xử lý upload video từ Frontend.

    Quy trình:
        1. Kiểm tra định dạng file (mp4, avi, mov, mkv).
        2. Đọc dữ liệu theo từng chunk 1MB để tránh tràn bộ nhớ.
        3. Kiểm tra dung lượng không vượt quá giới hạn max_upload_bytes.
        4. Lưu file vào storage/uploads/ với tên UUID duy nhất.
        5. Tạo bản ghi video trong database SQLite.

    Returns:
        VideoRead: Thông tin metadata của video vừa tải lên.

    Raises:
        400: File rỗng, sai định dạng hoặc vượt giới hạn dung lượng.
    """
    try:
        result = await VideoService(settings, repository).save_upload(file)
        logger.info("Upload video thành công: %s", result.original_filename)
        return result
    except ValueError as exc:
        logger.warning("Upload video thất bại: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[VideoRead],
    summary="Lấy danh sách video",
    description="Trả về danh sách tất cả video đã tải lên, sắp xếp theo thời gian mới nhất.",
)
def list_videos(
    repository: Repository = Depends(get_repository),
) -> list[VideoRead]:
    """Truy vấn toàn bộ video từ database và trả về cho Frontend."""
    return repository.list_videos()


@router.get(
    "/{video_id}",
    response_model=VideoRead,
    summary="Xem chi tiết một video",
    description="Trả về thông tin metadata chi tiết của video theo mã định danh.",
)
def get_video(
    video_id: str,
    repository: Repository = Depends(get_repository),
) -> VideoRead:
    """
    Truy vấn thông tin chi tiết của một video theo ID.

    Raises:
        404: Không tìm thấy video với ID đã cho.
    """
    video = repository.get_video(video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy video với ID đã cho.",
        )
    return video

"""
API endpoints quản lý tác vụ Nhận diện (Detection Task).

Cung cấp các endpoint REST cho luồng xử lý nhận diện video:
    - POST /api/detection/start          : Khởi tạo tác vụ nhận diện cho video.
    - GET  /api/detection/{id}/status     : Theo dõi tiến trình xử lý (polling).
    - GET  /api/detection/{id}/result     : Lấy kết quả sau khi xử lý xong.
    - GET  /api/detection/{id}/video      : Tải/xem video đã vẽ bounding box.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.api.dependencies import get_repository, get_settings
from backend.config import Settings
from backend.database.repository import Repository
from backend.schemas.detection import DetectionStartRequest, DetectionTaskRead
from backend.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection", tags=["detection"])


@router.post(
    "/start",
    response_model=DetectionTaskRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bắt đầu tác vụ nhận diện",
    description=(
        "Tạo một tác vụ nhận diện mới cho video đã upload. "
        "Tác vụ được đưa vào hàng đợi xử lý nền (background task) và "
        "trả về ngay thông tin task để Frontend theo dõi tiến trình qua endpoint /status."
    ),
)
def start_detection(
    request: DetectionStartRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    repository: Repository = Depends(get_repository),
) -> DetectionTaskRead:
    """
    Khởi tạo tác vụ nhận diện phương tiện cho một video.

    Quy trình:
        1. Kiểm tra video_id có tồn tại trong database không.
        2. Tạo bản ghi detection_task mới với trạng thái "queued".
        3. Đẩy tác vụ xử lý vào background (không chặn response).
        4. Trả về thông tin task ngay lập tức (HTTP 202 Accepted).

    Raises:
        404: Không tìm thấy video với ID đã cho.
    """
    service = DetectionService(settings, repository)
    try:
        task = service.create_task(request.video_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # Đẩy tác vụ xử lý video vào hàng đợi nền của FastAPI
    background_tasks.add_task(service.process_task, task.id)
    logger.info(
        "Đã khởi tạo tác vụ nhận diện: task_id=%s, video_id=%s",
        task.id,
        request.video_id,
    )
    return task


@router.get(
    "/{task_id}/status",
    response_model=DetectionTaskRead,
    summary="Theo dõi tiến trình xử lý",
    description=(
        "Frontend gọi endpoint này định kỳ (polling) để cập nhật "
        "thanh tiến trình (progress bar) và số khung hình đang xử lý."
    ),
)
def get_task_status(
    task_id: str,
    repository: Repository = Depends(get_repository),
) -> DetectionTaskRead:
    """
    Truy vấn trạng thái hiện tại của tác vụ nhận diện.

    Raises:
        404: Không tìm thấy tác vụ với task_id đã cho.
    """
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tác vụ nhận diện.",
        )
    return task


@router.get(
    "/{task_id}/result",
    response_model=DetectionTaskRead,
    summary="Lấy kết quả nhận diện",
    description=(
        "Trả về kết quả tổng hợp sau khi tác vụ hoàn thành: "
        "số phương tiện, số vi phạm, thời gian xử lý và phạm vi phân tích."
    ),
)
def get_task_result(
    task_id: str,
    repository: Repository = Depends(get_repository),
) -> DetectionTaskRead:
    """
    Lấy kết quả chi tiết của tác vụ nhận diện đã hoàn thành.

    Raises:
        404: Không tìm thấy tác vụ.
        409: Tác vụ chưa hoàn thành (vẫn đang queued hoặc running).
    """
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tác vụ nhận diện.",
        )
    if task.status not in {"completed", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tác vụ nhận diện chưa hoàn thành, vui lòng đợi.",
        )
    return task


@router.get(
    "/{task_id}/video",
    response_class=FileResponse,
    summary="Tải video đã xử lý",
    description=(
        "Trả về file video đầu ra đã được vẽ bounding box, ID phương tiện "
        "và cảnh báo vi phạm làn đường lên từng khung hình."
    ),
)
def get_processed_video(
    task_id: str,
    repository: Repository = Depends(get_repository),
) -> FileResponse:
    """
    Phục vụ file video đã xử lý cho Frontend phát lại.

    Raises:
        404: Không tìm thấy tác vụ hoặc file video đầu ra không tồn tại.
    """
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tác vụ nhận diện.",
        )
    if task.output_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video đã xử lý chưa sẵn sàng.",
        )
    output_path = task.output_path
    if not output_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File video đã xử lý không tồn tại trên ổ đĩa.",
        )
    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=output_path.name,
    )

"""Detection task endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.api.dependencies import get_repository, get_settings
from backend.config import Settings
from backend.database.repository import Repository
from backend.schemas.detection import DetectionStartRequest, DetectionTaskRead
from backend.services.detection_service import DetectionService

router = APIRouter(prefix="/detection", tags=["detection"])


@router.post("/start", response_model=DetectionTaskRead, status_code=status.HTTP_202_ACCEPTED)
def start_detection(
    request: DetectionStartRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    repository: Repository = Depends(get_repository),
) -> DetectionTaskRead:
    service = DetectionService(settings, repository)
    try:
        task = service.create_task(request.video_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    background_tasks.add_task(service.process_task, task.id)
    return task


@router.get("/{task_id}/status", response_model=DetectionTaskRead)
def get_task_status(
    task_id: str,
    repository: Repository = Depends(get_repository),
) -> DetectionTaskRead:
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection task not found.")
    return task


@router.get("/{task_id}/result", response_model=DetectionTaskRead)
def get_task_result(
    task_id: str,
    repository: Repository = Depends(get_repository),
) -> DetectionTaskRead:
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection task not found.")
    if task.status not in {"completed", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Detection task is not finished.")
    return task


@router.get("/{task_id}/video", response_class=FileResponse)
def get_processed_video(
    task_id: str,
    repository: Repository = Depends(get_repository),
) -> FileResponse:
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection task not found.")
    if task.output_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed video is unavailable.")
    output_path = task.output_path
    if not output_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed video is unavailable.")
    return FileResponse(output_path, media_type="video/mp4", filename=output_path.name)

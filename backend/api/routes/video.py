"""Video upload and metadata endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.api.dependencies import get_repository, get_settings
from backend.config import Settings
from backend.database.repository import Repository
from backend.schemas.video import VideoRead
from backend.services.video_service import VideoService

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=VideoRead, status_code=status.HTTP_201_CREATED)
async def upload_video(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    repository: Repository = Depends(get_repository),
) -> VideoRead:
    try:
        return await VideoService(settings, repository).save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[VideoRead])
def list_videos(repository: Repository = Depends(get_repository)) -> list[VideoRead]:
    return repository.list_videos()


@router.get("/{video_id}", response_model=VideoRead)
def get_video(
    video_id: str,
    repository: Repository = Depends(get_repository),
) -> VideoRead:
    video = repository.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")
    return video

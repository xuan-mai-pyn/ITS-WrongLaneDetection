"""Video upload validation and persistence."""

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.config import Settings
from backend.database.repository import Repository
from backend.schemas.video import VideoRead

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


class VideoService:
    def __init__(self, settings: Settings, repository: Repository) -> None:
        self.settings = settings
        self.repository = repository

    async def save_upload(self, upload: UploadFile) -> VideoRead:
        original_name = Path(upload.filename or "").name
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported video extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.")

        video_id = uuid4().hex
        destination = self.settings.upload_dir / f"{video_id}{extension}"
        size_bytes = 0
        try:
            with destination.open("wb") as target:
                while chunk := await upload.read(1024 * 1024):
                    size_bytes += len(chunk)
                    if size_bytes > self.settings.max_upload_bytes:
                        raise ValueError(
                            f"Video exceeds the upload limit of {self.settings.max_upload_bytes} bytes."
                        )
                    target.write(chunk)
            if size_bytes == 0:
                raise ValueError("Uploaded video is empty.")
            return self.repository.create_video(
                video_id=video_id,
                original_filename=original_name,
                stored_path=destination,
                size_bytes=size_bytes,
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

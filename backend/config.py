"""Application settings loaded from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    """Paths and limits shared by the API and processing services."""

    project_root: Path = PROJECT_ROOT
    database_path: Path = _project_path(os.getenv("ITS_DATABASE_PATH", "storage/its_wrong_lane.db"))
    upload_dir: Path = _project_path(os.getenv("ITS_UPLOAD_DIR", "storage/uploads"))
    processed_dir: Path = _project_path(os.getenv("ITS_PROCESSED_DIR", "storage/processed"))
    evidence_dir: Path = _project_path(os.getenv("ITS_EVIDENCE_DIR", "storage/evidence"))
    model_path: Path = _project_path(os.getenv("ITS_MODEL_PATH", "models/weights/yolov8n.pt"))
    lane_config_path: Path | None = (
        _project_path(os.environ["ITS_LANE_CONFIG"])
        if os.getenv("ITS_LANE_CONFIG")
        else None
    )
    max_upload_bytes: int = int(os.getenv("ITS_MAX_UPLOAD_BYTES", "524288000"))
    violation_confirm_frames: int = int(os.getenv("ITS_VIOLATION_CONFIRM_FRAMES", "8"))
    host: str = os.getenv("ITS_HOST", "127.0.0.1")
    port: int = int(os.getenv("ITS_PORT", "8000"))

    def prepare_directories(self) -> None:
        """Create runtime directories without replacing existing data."""
        for directory in (
            self.database_path.parent,
            self.upload_dir,
            self.processed_dir,
            self.evidence_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

"""Asynchronous detection orchestration and task-state persistence."""

import json
import logging
from pathlib import Path
from uuid import uuid4

from backend.config import Settings
from backend.core.alert_manager import AlertManager
from backend.core.detector import YOLODetector
from backend.core.lane_detector import LaneDetector
from backend.core.video_processor import VideoProcessor
from backend.core.wrong_lane_detector import WrongLaneDetector
from backend.database.repository import Repository
from backend.models.violation import Violation
from backend.schemas.detection import DetectionTaskRead

logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self, settings: Settings, repository: Repository) -> None:
        self.settings = settings
        self.repository = repository

    def create_task(self, video_id: str) -> DetectionTaskRead:
        if self.repository.get_video(video_id) is None:
            raise LookupError("Video not found.")
        return self.repository.create_task(uuid4().hex, video_id)

    def process_task(self, task_id: str) -> None:
        """Run processing and persist explicit success or failure state."""
        task = self.repository.get_task(task_id)
        if task is None:
            raise LookupError(f"Detection task {task_id} no longer exists.")
        video = self.repository.get_video(task.video_id)
        if video is None:
            self.repository.update_task(task_id, status="failed", error="Source video was not found.")
            return

        output_path = self.settings.processed_dir / f"{task_id}.mp4"
        try:
            self.repository.update_task(task_id, status="running", progress=0)
            detector = YOLODetector(self.settings.model_path)
            lane_detector = LaneDetector.from_json(self.settings.lane_config_path)
            forbidden_transitions: set[tuple[str, str]] = set()
            if self.settings.lane_config_path is not None:
                config = json.loads(self.settings.lane_config_path.read_text(encoding="utf-8"))
                for transition in config.get("forbidden_transitions", []):
                    if not isinstance(transition, list) or len(transition) != 2:
                        raise ValueError("Each forbidden transition must be a [source_lane, destination_lane] pair.")
                    forbidden_transitions.add((str(transition[0]), str(transition[1])))
            processor = VideoProcessor(
                detector=detector,
                lane_detector=lane_detector,
                wrong_lane_detector=WrongLaneDetector(
                    forbidden_transitions,
                    confirm_frames=self.settings.violation_confirm_frames,
                ),
                alert_manager=AlertManager(self.settings.evidence_dir, task_id),
            )
            result = processor.process(
                input_path=Path(video.stored_path),
                output_path=output_path,
                progress_callback=lambda progress, frame: self.repository.update_task(
                    task_id,
                    progress=progress,
                    current_frame=frame,
                ),
            )
            self.repository.save_violations(
                task_id,
                task.video_id,
                [Violation.model_validate(item) for item in result["violations"]],
            )
            self.repository.update_video_metrics(
                task.video_id,
                processing_seconds=result["processing_seconds"],
                vehicle_type_counts=result["vehicle_type_counts"],
                processed_frames=result["processed_frames"],
                vehicle_count=result["unique_tracked_vehicles"],
                violation_count=result["violation_count"],
            )
            self.repository.update_task(
                task_id,
                status="completed",
                progress=100,
                current_frame=result["processed_frames"],
                result=result,
                output_path=output_path,
            )
        except Exception as exc:
            logger.exception("Detection task %s failed", task_id)
            output_path.unlink(missing_ok=True)
            self.repository.update_video_status(task.video_id, "failed")
            self.repository.update_task(task_id, status="failed", error=str(exc))

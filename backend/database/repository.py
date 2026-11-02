"""SQLite repository for videos, detection tasks, violations, and summaries."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.database.connection import connect, initialize_database
from backend.models.violation import Violation
from backend.schemas.detection import DetectionTaskRead
from backend.schemas.video import VideoRead
from backend.schemas.violation import ViolationRead


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        initialize_database(self.database_path)

    @staticmethod
    def _video(row: Any) -> VideoRead:
        return VideoRead(
            id=row["id"],
            original_filename=row["original_filename"],
            size_bytes=row["size_bytes"],
            uploaded_at=row["uploaded_at"],
            status=row["status"],
            processing_seconds=row["processing_seconds"],
            vehicle_type_counts=json.loads(row["vehicle_type_counts_json"]),
            processed_frames=row["processed_frames"],
            vehicle_count=row["vehicle_count"],
            violation_count=row["violation_count"],
        )

    @staticmethod
    def _task(row: Any) -> DetectionTaskRead:
        result = json.loads(row["result_json"]) if row["result_json"] else None
        return DetectionTaskRead(
            id=row["id"],
            video_id=row["video_id"],
            status=row["status"],
            progress=row["progress"],
            current_frame=row["current_frame"],
            error=row["error"],
            result=result,
            output_path=Path(row["output_path"]) if row["output_path"] else None,
            video_url=f"/api/detection/{row['id']}/video" if row["output_path"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_video(
        self,
        video_id: str,
        original_filename: str,
        stored_path: Path,
        size_bytes: int,
    ) -> VideoRead:
        with connect(self.database_path) as connection:
            connection.execute(
                """INSERT INTO videos (id, original_filename, stored_path, size_bytes, uploaded_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (video_id, original_filename, str(stored_path), size_bytes, _now()),
            )
            row = connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return self._video(row)

    def list_videos(self) -> list[VideoRead]:
        with connect(self.database_path) as connection:
            rows = connection.execute("SELECT * FROM videos ORDER BY uploaded_at DESC").fetchall()
        return [self._video(row) for row in rows]

    def get_video(self, video_id: str) -> VideoRead | None:
        with connect(self.database_path) as connection:
            row = connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return self._video(row) if row else None

    def get_video_path(self, video_id: str) -> Path | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT stored_path FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
        return Path(row["stored_path"]) if row else None

    def create_task(self, task_id: str, video_id: str) -> DetectionTaskRead:
        now = _now()
        with connect(self.database_path) as connection:
            connection.execute(
                """INSERT INTO detection_tasks (id, video_id, status, created_at, updated_at)
                   VALUES (?, ?, 'queued', ?, ?)""",
                (task_id, video_id, now, now),
            )
            connection.execute(
                "UPDATE videos SET status = 'processing' WHERE id = ?", (video_id,)
            )
            row = connection.execute(
                "SELECT * FROM detection_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._task(row)

    def get_task(self, task_id: str) -> DetectionTaskRead | None:
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM detection_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._task(row) if row else None

    def update_task(
        self,
        task_id: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        current_frame: int | None = None,
        error: str | None = None,
        result: dict[str, Any] | None = None,
        output_path: Path | None = None,
    ) -> None:
        updates: dict[str, Any] = {"updated_at": _now()}
        for key, value in (
            ("status", status),
            ("progress", progress),
            ("current_frame", current_frame),
            ("error", error),
        ):
            if value is not None:
                updates[key] = value
        if result is not None:
            updates["result_json"] = json.dumps(result)
        if output_path is not None:
            updates["output_path"] = str(output_path)
        assignments = ", ".join(f"{column} = ?" for column in updates)
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                f"UPDATE detection_tasks SET {assignments} WHERE id = ?",
                (*updates.values(), task_id),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"Detection task {task_id} not found.")

    def save_violations(
        self,
        task_id: str,
        video_id: str,
        violations: list[Violation],
    ) -> None:
        with connect(self.database_path) as connection:
            connection.executemany(
                """INSERT INTO violations (
                       task_id, video_id, track_id, source_lane, destination_lane,
                       frame_index, timestamp_seconds, detected_at, evidence_path
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        task_id,
                        video_id,
                        item.track_id,
                        item.source_lane,
                        item.destination_lane,
                        item.frame_index,
                        item.timestamp_seconds,
                        item.detected_at.isoformat(),
                        item.evidence_path,
                    )
                    for item in violations
                ],
            )

    def list_violations(self, limit: int = 100) -> list[ViolationRead]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM violations ORDER BY detected_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ViolationRead(**dict(row)) for row in rows]

    def update_video_metrics(
        self,
        video_id: str,
        *,
        processing_seconds: float,
        vehicle_type_counts: dict[str, int],
        processed_frames: int,
        vehicle_count: int,
        violation_count: int,
    ) -> None:
        with connect(self.database_path) as connection:
            connection.execute(
                """UPDATE videos
                   SET status = 'processed', processing_seconds = ?,
                       vehicle_type_counts_json = ?, processed_frames = ?,
                       vehicle_count = ?, violation_count = ?
                   WHERE id = ?""",
                (
                    processing_seconds,
                    json.dumps(vehicle_type_counts),
                    processed_frames,
                    vehicle_count,
                    violation_count,
                    video_id,
                ),
            )

    def update_video_status(self, video_id: str, status: str) -> None:
        with connect(self.database_path) as connection:
            connection.execute("UPDATE videos SET status = ? WHERE id = ?", (status, video_id))

    def get_statistics(self) -> dict[str, Any]:
        with connect(self.database_path) as connection:
            videos = connection.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN status = 'processed' THEN 1 ELSE 0 END) AS processed,
                          COALESCE(SUM(vehicle_count), 0) AS vehicles,
                          COALESCE(SUM(violation_count), 0) AS violations
                   FROM videos"""
            ).fetchone()
            with_violations = connection.execute(
                "SELECT COUNT(*) FROM videos WHERE status = 'processed' AND violation_count > 0"
            ).fetchone()[0]
            type_rows = connection.execute(
                """SELECT vehicle_type_counts_json FROM videos
                   WHERE status = 'processed'"""
            ).fetchall()
        vehicle_types: dict[str, int] = {}
        for row in type_rows:
            for label, count in json.loads(row["vehicle_type_counts_json"]).items():
                vehicle_types[label] = vehicle_types.get(label, 0) + count
        processed = videos["processed"] or 0
        return {
            "total_videos": videos["total"],
            "processed_videos": processed,
            "total_vehicles": videos["vehicles"],
            "total_violations": videos["violations"],
            "videos_with_violations": with_violations,
            "vehicle_types": vehicle_types,
        }

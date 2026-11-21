"""
Tầng Repository quản lý toàn bộ thao tác đọc và ghi cơ sở dữ liệu SQLite.

Module này áp dụng Repository Design Pattern:
    - Tách biệt hoàn toàn tầng nghiệp vụ (Services) khỏi các truy vấn SQL trực tiếp.
    - Đảm bảo tính nhất quán dữ liệu cho 4 nhóm đối tượng chính:
        1. Video: Tạo bản ghi, danh sách, chi tiết và cập nhật số liệu tổng hợp.
        2. Detection Task: Khởi tạo tác vụ, cập nhật trạng thái/tiến trình và lưu kết quả.
        3. Violation: Lưu trữ danh sách vi phạm hàng loạt (batch insert) và truy vấn lịch sử.
        4. Statistics: Tổng hợp số liệu toàn hệ thống phục vụ Dashboard và trang thống kê.
    - Tự động chuyển đổi giữa các dòng dữ liệu SQLite (Row) và các Pydantic Schemas.

"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.database.connection import connect, initialize_database
from backend.models.violation import Violation
from backend.schemas.detection import DetectionTaskRead
from backend.schemas.video import VideoRead
from backend.schemas.violation import ViolationRead

logger = logging.getLogger(__name__)


def _now() -> str:
    """Trả về mốc thời gian hiện tại chuẩn định dạng ISO 8601 (UTC)."""
    return datetime.now(timezone.utc).isoformat()


class Repository:
    """
    Kho lưu trữ trung tâm điều phối tất cả các thao tác với cơ sở dữ liệu SQLite.

    Attributes:
        database_path: Đường dẫn tới file SQLite database trên ổ đĩa.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        """Khởi tạo cấu trúc các bảng và chỉ mục trong cơ sở dữ liệu."""
        initialize_database(self.database_path)

    # ── HÀM CHUYỂN ĐỔI ROW SQL THÀNH PYDANTIC SCHEMAS ──

    @staticmethod
    def _video(row: Any) -> VideoRead:
        """Chuyển đổi một bản ghi bảng videos thành schema VideoRead."""
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
        """Chuyển đổi một bản ghi bảng detection_tasks thành schema DetectionTaskRead."""
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

    # ── QUẢN LÝ DỮ LIỆU VIDEO (VIDEOS) ──

    def create_video(
        self,
        video_id: str,
        original_filename: str,
        stored_path: Path,
        size_bytes: int,
    ) -> VideoRead:
        """Tạo bản ghi mới cho video vừa tải lên hệ thống."""
        now_str = _now()
        with connect(self.database_path) as connection:
            connection.execute(
                """INSERT INTO videos (id, original_filename, stored_path, size_bytes, uploaded_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (video_id, original_filename, str(stored_path), size_bytes, now_str),
            )
            row = connection.execute(
                "SELECT * FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
        logger.info("Đã tạo bản ghi video mới: %s (%s)", original_filename, video_id)
        return self._video(row)

    def list_videos(self) -> list[VideoRead]:
        """Truy vấn danh sách tất cả video, sắp xếp theo thời gian tải lên mới nhất."""
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM videos ORDER BY uploaded_at DESC"
            ).fetchall()
        return [self._video(row) for row in rows]

    def get_video(self, video_id: str) -> VideoRead | None:
        """Truy vấn chi tiết một video theo mã định danh (UUID)."""
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
        return self._video(row) if row else None

    def get_video_path(self, video_id: str) -> Path | None:
        """Lấy đường dẫn lưu trữ tệp video trên ổ đĩa."""
        with connect(self.database_path) as connection:
            row = connection.execute(
                "SELECT stored_path FROM videos WHERE id = ?", (video_id,)
            ).fetchone()
        return Path(row["stored_path"]) if row else None

    def update_video_status(self, video_id: str, status: str) -> None:
        """Cập nhật trạng thái xử lý của video (ví dụ: processing, failed)."""
        with connect(self.database_path) as connection:
            connection.execute(
                "UPDATE videos SET status = ? WHERE id = ?", (status, video_id)
            )

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
        """Cập nhật các số liệu thống kê sau khi tác vụ nhận diện video hoàn thành."""
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
        logger.info("Đã cập nhật số liệu cho video: %s (Xe: %d, Lỗi: %d)", video_id, vehicle_count, violation_count)

    # ── QUẢN LÝ TÁC VỤ NHẬN DIỆN (DETECTION TASKS) ──

    def create_task(self, task_id: str, video_id: str) -> DetectionTaskRead:
        """Khởi tạo một tác vụ nhận diện mới với trạng thái ban đầu là 'queued'."""
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
        logger.info("Đã tạo tác vụ nhận diện mới: task_id=%s, video_id=%s", task_id, video_id)
        return self._task(row)

    def get_task(self, task_id: str) -> DetectionTaskRead | None:
        """Truy vấn thông tin chi tiết và tiến trình của một tác vụ nhận diện."""
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
        """Cập nhật động các trường trạng thái, tiến độ phần trăm, số khung hình hoặc lỗi của task."""
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
                raise LookupError(f"Không tìm thấy tác vụ nhận diện với ID: {task_id}")

    # ── QUẢN LÝ HỒ SƠ VI PHẠM (VIOLATIONS) ──

    def save_violations(
        self,
        task_id: str,
        video_id: str,
        violations: list[Violation],
    ) -> None:
        """
        Lưu danh sách vi phạm hàng loạt vào cơ sở dữ liệu (Batch Insert).

        Sử dụng executemany giúp tối ưu hóa số lượng giao dịch I/O với đĩa,
        ghi hàng trăm bản ghi vi phạm chỉ trong một chu kỳ kết nối duy nhất.
        """
        if not violations:
            return

        with connect(self.database_path) as connection:
            connection.executemany(
                """INSERT INTO violations (
                       task_id, video_id, track_id, source_lane, destination_lane,
                       vehicle_type, frame_index, timestamp_seconds, detected_at, evidence_path
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        task_id,
                        video_id,
                        item.track_id,
                        item.source_lane,
                        item.destination_lane,
                        item.vehicle_type,
                        item.frame_index,
                        item.timestamp_seconds,
                        item.detected_at.isoformat(),
                        item.evidence_path,
                    )
                    for item in violations
                ],
            )
        logger.info("Đã lưu %d bản ghi vi phạm cho task: %s", len(violations), task_id)

    def list_violations(self, limit: int = 100) -> list[ViolationRead]:
        """Truy vấn danh sách vi phạm gần nhất phục vụ trang Lịch sử (History)."""
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM violations ORDER BY detected_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ViolationRead(**dict(row)) for row in rows]

    # ── TỔNG HỢP SỐ LIỆU THỐNG KÊ (STATISTICS) ──

    def get_statistics(self) -> dict[str, Any]:
        """
        Tính toán và tổng hợp số liệu thực tế từ cơ sở dữ liệu SQLite.

        Returns:
            dict chứa:
                - total_videos: Tổng số video đã tải lên.
                - processed_videos: Số video đã phân tích hoàn tất.
                - total_vehicles: Tổng số phương tiện duy nhất theo dõi được.
                - total_violations: Tổng số lượt phương tiện đi sai làn.
                - videos_with_violations: Số lượng video có ghi nhận vi phạm.
                - vehicle_types: Thống kê số lượng xe phân chia theo từng loại.
        """
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
            try:
                counts = json.loads(row["vehicle_type_counts_json"])
                for label, count in counts.items():
                    vehicle_types[label] = vehicle_types.get(label, 0) + count
            except (json.JSONDecodeError, TypeError):
                continue

        processed = videos["processed"] or 0
        return {
            "total_videos": videos["total"] or 0,
            "processed_videos": processed,
            "total_vehicles": videos["vehicles"] or 0,
            "total_violations": videos["violations"] or 0,
            "videos_with_violations": with_violations,
            "vehicle_types": vehicle_types,
        }

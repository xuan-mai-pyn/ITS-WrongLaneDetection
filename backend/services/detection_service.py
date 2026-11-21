"""
Dịch vụ điều phối tác vụ Nhận diện (Detection Service).

Chức năng chính:
    - Tạo tác vụ nhận diện mới và lưu vào database.
    - Điều phối toàn bộ pipeline xử lý video chạy ở background:
        YOLO Detector → ByteTrack Tracker → Lane Detector → Wrong Lane Detector
    - Cập nhật tiến trình xử lý (progress) liên tục vào database
      để Frontend có thể polling và hiển thị thanh tiến trình.
    - Lưu kết quả tổng hợp và danh sách vi phạm vào database.
    - Ghi nhận rõ ràng trạng thái thành công (completed) hoặc thất bại (failed).
"""

from __future__ import annotations

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
    """
    Dịch vụ quản lý nghiệp vụ tạo và xử lý tác vụ nhận diện.

    Attributes:
        settings: Cấu hình hệ thống.
        repository: Đối tượng thao tác cơ sở dữ liệu.
    """

    def __init__(self, settings: Settings, repository: Repository) -> None:
        self.settings = settings
        self.repository = repository

    def create_task(self, video_id: str) -> DetectionTaskRead:
        """
        Tạo một tác vụ nhận diện mới cho video đã upload.

        Args:
            video_id: Mã định danh của video cần xử lý.

        Returns:
            DetectionTaskRead: Thông tin tác vụ vừa tạo (trạng thái: queued).

        Raises:
            LookupError: Video không tồn tại trong database.
        """
        if self.repository.get_video(video_id) is None:
            raise LookupError("Không tìm thấy video trong hệ thống.")
        task_id = uuid4().hex
        logger.info("Tạo tác vụ nhận diện: task_id=%s, video_id=%s", task_id, video_id)
        return self.repository.create_task(task_id, video_id)

    def process_task(self, task_id: str) -> None:
        """
        Thực thi toàn bộ pipeline xử lý video cho một tác vụ nhận diện.

        Đây là hàm chạy trong background (FastAPI BackgroundTasks).
        Mọi trạng thái (running, completed, failed) đều được ghi nhận
        rõ ràng vào database để Frontend hiển thị chính xác.

        Quy trình:
            1. Truy xuất thông tin task và video từ database.
            2. Cập nhật trạng thái task thành "running".
            3. Khởi tạo các module xử lý: YOLO Detector, Lane Detector,
               Wrong Lane Detector, Alert Manager.
            4. Gọi VideoProcessor.process() để xử lý toàn bộ video.
            5. Lưu danh sách vi phạm phát hiện được vào database.
            6. Cập nhật số liệu tổng hợp vào bản ghi video.
            7. Đánh dấu task hoàn thành (completed) với kết quả chi tiết.
            8. Nếu có lỗi: ghi log, xóa file video dở, đánh dấu task thất bại (failed).

        Args:
            task_id: Mã định danh của tác vụ cần xử lý.
        """
        # ── 1. Truy xuất thông tin task và video ──
        task = self.repository.get_task(task_id)
        if task is None:
            raise LookupError(f"Tác vụ nhận diện {task_id} không còn tồn tại.")

        video = self.repository.get_video(task.video_id)
        if video is None:
            self.repository.update_task(
                task_id, status="failed",
                error="Video nguồn không tìm thấy trong hệ thống.",
            )
            return
        input_path = self.repository.get_video_path(task.video_id)
        if input_path is None or not input_path.is_file():
            self.repository.update_task(
                task_id,
                status="failed",
                error="Tệp video nguồn không tồn tại trên ổ đĩa.",
            )
            self.repository.update_video_status(task.video_id, "failed")
            return

        output_path = self.settings.processed_dir / f"{task_id}.mp4"

        try:
            # ── 2. Cập nhật trạng thái "running" ──
            self.repository.update_task(task_id, status="running", progress=0)
            logger.info("Bắt đầu xử lý tác vụ: %s", task_id)

            # ── 3. Khởi tạo các module xử lý ──
            detector = YOLODetector(self.settings.model_path)
            lane_detector = LaneDetector.from_json(self.settings.lane_config_path)

            # Đọc danh sách các chuyển làn bị cấm từ file cấu hình
            forbidden_transitions: set[tuple[str, str]] = set()
            if self.settings.lane_config_path is not None:
                config = json.loads(
                    self.settings.lane_config_path.read_text(encoding="utf-8")
                )
                for transition in config.get("forbidden_transitions", []):
                    if not isinstance(transition, list) or len(transition) != 2:
                        raise ValueError(
                            "Mỗi phần tử trong forbidden_transitions phải là "
                            "một cặp [source_lane, destination_lane]."
                        )
                    forbidden_transitions.add(
                        (str(transition[0]), str(transition[1]))
                    )

            # Ghép nối toàn bộ pipeline
            processor = VideoProcessor(
                detector=detector,
                lane_detector=lane_detector,
                wrong_lane_detector=WrongLaneDetector(
                    forbidden_transitions,
                    confirm_frames=self.settings.violation_confirm_frames,
                ),
                alert_manager=AlertManager(self.settings.evidence_dir, task_id),
            )

            # ── 4. Chạy pipeline xử lý video ──
            result = processor.process(
                input_path=input_path,
                output_path=output_path,
                progress_callback=lambda progress, frame: (
                    self.repository.update_task(
                        task_id,
                        progress=progress,
                        current_frame=frame,
                    )
                ),
            )

            # ── 5. Lưu danh sách vi phạm vào database ──
            self.repository.save_violations(
                task_id,
                task.video_id,
                [Violation.model_validate(item) for item in result["violations"]],
            )

            # ── 6. Cập nhật số liệu tổng hợp vào bản ghi video ──
            self.repository.update_video_metrics(
                task.video_id,
                processing_seconds=result["processing_seconds"],
                vehicle_type_counts=result["vehicle_type_counts"],
                processed_frames=result["processed_frames"],
                vehicle_count=result["unique_tracked_vehicles"],
                violation_count=result["violation_count"],
            )

            # ── 7. Đánh dấu task hoàn thành ──
            self.repository.update_task(
                task_id,
                status="completed",
                progress=100,
                current_frame=result["processed_frames"],
                result=result,
                output_path=output_path,
            )
            logger.info(
                "Tác vụ %s hoàn thành: %d phương tiện, %d vi phạm",
                task_id,
                result["unique_tracked_vehicles"],
                result["violation_count"],
            )

        except Exception as exc:
            # ── 8. Xử lý lỗi: ghi log, dọn dẹp và đánh dấu thất bại ──
            logger.exception("Tác vụ nhận diện %s thất bại", task_id)
            output_path.unlink(missing_ok=True)
            self.repository.update_video_status(task.video_id, "failed")
            self.repository.update_task(
                task_id, status="failed", error=str(exc)
            )

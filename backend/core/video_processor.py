"""
Điều phối toàn bộ quá trình phân tích video theo từng khung hình.

Đây là module trung tâm của pipeline xử lý, kết nối tất cả các thành phần:
    YOLODetector → VehicleTracker → LaneDetector → WrongLaneDetector → AlertManager

Quy trình xử lý mỗi khung hình (frame):
    1. Đọc frame từ video nguồn.
    2. Phát hiện phương tiện bằng YOLO (detector).
    3. Gán và theo dõi ID phương tiện qua ByteTrack (tracker).
    4. Xác định phương tiện thuộc làn nào bằng Polygon (lane_detector).
    5. Kiểm tra vi phạm chuyển làn trái phép (wrong_lane_detector).
    6. Lưu ảnh bằng chứng nếu có vi phạm (alert_manager).
    7. Vẽ bounding box, ID, nhãn lên frame và ghi vào video đầu ra.

"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np

from backend.core.alert_manager import AlertManager
from backend.core.detector import YOLODetector
from backend.core.lane_detector import LaneDetector
from backend.core.tracker import VehicleTracker
from backend.core.wrong_lane_detector import WrongLaneDetector
from backend.models.violation import Violation
from backend.utils.file_handler import ensure_parent
from backend.utils.image_utils import vehicle_foot_point

logger = logging.getLogger(__name__)

# ── Màu sắc hiển thị trên video (BGR) ──
COLOR_NORMAL = (0, 180, 0)       # Xanh lá: phương tiện bình thường
COLOR_VIOLATION = (0, 0, 255)    # Đỏ: phương tiện vi phạm
COLOR_LANE_BORDER = (255, 180, 0)  # Vàng cam: viền làn đường


class VideoProcessor:
    """
    Điều phối toàn bộ quá trình xử lý video.

    Ghép nối các module phát hiện, theo dõi, xác định làn và nhận diện vi phạm
    thành một pipeline xử lý hoàn chỉnh. Không viết lại thuật toán YOLO,
    tracker hay thuật toán xác định làn trong file này.

    Attributes:
        detector: Module phát hiện phương tiện bằng YOLO.
        tracker: Module theo dõi phương tiện qua ByteTrack.
        lane_detector: Module xác định làn đường bằng Polygon.
        wrong_lane_detector: Module kiểm tra vi phạm chuyển làn.
        alert_manager: Module quản lý cảnh báo và lưu ảnh bằng chứng.
    """

    def __init__(
        self,
        detector: YOLODetector,
        lane_detector: LaneDetector,
        wrong_lane_detector: WrongLaneDetector,
        alert_manager: AlertManager,
    ) -> None:
        self.detector = detector
        self.tracker = VehicleTracker(detector)
        self.lane_detector = lane_detector
        self.wrong_lane_detector = wrong_lane_detector
        self.alert_manager = alert_manager

    def process(
        self,
        input_path: Path,
        output_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """
        Xử lý toàn bộ video từ đầu đến cuối.

        Args:
            input_path: Đường dẫn file video nguồn cần phân tích.
            output_path: Đường dẫn file video đầu ra (đã vẽ bounding box).
            progress_callback: Hàm callback nhận (phần_trăm, số_frame) để
                               cập nhật thanh tiến trình trên Frontend.

        Returns:
            dict: Kết quả tổng hợp bao gồm:
                - processed_frames: Tổng số khung hình đã xử lý.
                - unique_tracked_vehicles: Số phương tiện duy nhất.
                - vehicle_type_counts: Thống kê theo loại xe.
                - violation_count: Số vi phạm phát hiện được.
                - processing_seconds: Thời gian xử lý (giây).
                - analysis_scope: Phạm vi phân tích (detection_only hoặc configured_lane_rules).
                - warnings: Danh sách cảnh báo.
                - violations: Chi tiết từng vụ vi phạm.

        Raises:
            ValueError: Video không mở được hoặc không có khung hình hợp lệ.
            OSError: Không thể tạo file video đầu ra.
        """
        import cv2

        # ── Bước 1: Mở video nguồn và đọc thông số kỹ thuật ──
        capture = cv2.VideoCapture(str(input_path))
        if not capture.isOpened():
            raise ValueError(
                f"OpenCV không thể mở video: {input_path.name}"
            )

        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if width <= 0 or height <= 0:
            capture.release()
            raise ValueError("Video có kích thước khung hình không hợp lệ.")

        logger.info(
            "Bắt đầu xử lý video: %s (%dx%d, %.1f FPS, ~%d frames)",
            input_path.name, width, height, fps, total_frames,
        )

        # ── Bước 2: Khởi tạo VideoWriter để ghi video đầu ra ──
        ensure_parent(output_path)
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            capture.release()
            raise OSError(
                f"OpenCV không thể tạo video đầu ra: {output_path}"
            )

        # ── Bước 3: Vòng lặp xử lý từng khung hình ──
        started = perf_counter()
        frame_index = 0
        last_progress = -1
        vehicle_ids: set[int] = set()
        vehicle_classes: dict[int, str] = {}
        violations: list[Violation] = []

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_index += 1
                timestamp = (frame_index - 1) / fps

                # ── 3a. Phát hiện và theo dõi phương tiện ──
                tracks = self.tracker.update(frame)

                # ── 3b. Vẽ viền các làn đường lên khung hình ──
                for lane in self.lane_detector.lanes:
                    polygon = np.asarray(lane.polygon, dtype=np.int32)
                    cv2.polylines(frame, [polygon], True, COLOR_LANE_BORDER, 2)
                    cv2.putText(
                        frame,
                        lane.id,
                        tuple(polygon[0]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        COLOR_LANE_BORDER,
                        2,
                    )

                # ── 3c. Xử lý từng phương tiện được phát hiện ──
                for vehicle in tracks:
                    x1, y1, x2, y2 = (int(v) for v in vehicle.box)
                    color = COLOR_NORMAL
                    label = f"{vehicle.label} {vehicle.confidence:.2f}"

                    if vehicle.track_id is not None:
                        vehicle_ids.add(vehicle.track_id)
                        vehicle_classes.setdefault(vehicle.track_id, vehicle.label)
                        label = f"ID {vehicle.track_id} | {label}"

                        # Xác định làn hiện tại bằng điểm bottom-center
                        lane_id = self.lane_detector.lane_at(
                            vehicle_foot_point(vehicle)
                        )

                        # Kiểm tra vi phạm chuyển làn trái phép
                        violation = self.wrong_lane_detector.update(
                            vehicle.track_id,
                            lane_id,
                            frame_index,
                            timestamp,
                            vehicle.label,
                        )

                        # Nếu phát hiện vi phạm: đổi màu đỏ và lưu bằng chứng
                        if violation is not None:
                            violations.append(violation)
                            color = COLOR_VIOLATION
                            label = f"WRONG LANE | ID {vehicle.track_id}"
                            evidence_path = self.alert_manager.save_evidence(
                                violation, frame
                            )
                            if evidence_path is not None:
                                violation.evidence_path = str(evidence_path)

                    # Vẽ bounding box và nhãn lên khung hình
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame,
                        label,
                        (x1, max(y1 - 8, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2,
                    )

                # ── 3d. Ghi khung hình đã xử lý vào video đầu ra ──
                writer.write(frame)

                # ── 3e. Cập nhật tiến trình cho Frontend ──
                if progress_callback and total_frames > 0:
                    progress = min(int(frame_index * 100 / total_frames), 99)
                    if progress > last_progress:
                        progress_callback(progress, frame_index)
                        last_progress = progress

        finally:
            capture.release()
            writer.release()

        # ── Bước 4: Kiểm tra kết quả và tổng hợp báo cáo ──
        if frame_index == 0:
            raise ValueError("Video không chứa khung hình nào có thể đọc được.")

        elapsed = perf_counter() - started
        logger.info(
            "Hoàn thành xử lý: %d frames, %d phương tiện, %d vi phạm (%.2fs)",
            frame_index, len(vehicle_ids), len(violations), elapsed,
        )

        # Thu thập cảnh báo về cấu hình
        warnings: list[str] = []
        if not self.lane_detector.lanes:
            warnings.append(
                "Chưa cấu hình polygon làn đường; không thể đánh giá vi phạm sai làn."
            )
        elif not self.wrong_lane_detector.forbidden_transitions:
            warnings.append(
                "Chưa cấu hình quy tắc chuyển làn cấm; không thể đánh giá vi phạm sai làn."
            )

        return {
            "processed_frames": frame_index,
            "unique_tracked_vehicles": len(vehicle_ids),
            "vehicle_type_counts": dict(Counter(vehicle_classes.values())),
            "violation_count": len(violations),
            "processing_seconds": round(elapsed, 3),
            "analysis_scope": (
                "configured_lane_rules"
                if self.lane_detector.lanes and self.wrong_lane_detector.forbidden_transitions
                else "detection_only"
            ),
            "warnings": warnings,
            "violations": [
                violation.model_dump(mode="json") for violation in violations
            ],
        }

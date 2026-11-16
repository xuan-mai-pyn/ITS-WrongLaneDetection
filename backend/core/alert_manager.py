"""
Quản lý cảnh báo và lưu trữ ảnh minh chứng (Evidence) cho vi phạm làn đường.

Chức năng chính:
    - Tiếp nhận sự kiện vi phạm từ WrongLaneDetector.
    - Lọc trùng lặp cảnh báo (Deduplication): Mỗi phương tiện (track_id)
      khi thực hiện cùng một hành vi chuyển làn trái phép (source -> destination)
      chỉ bị kích hoạt cảnh báo và lưu ảnh bằng chứng đúng 1 lần.
    - Vẽ thông tin giám sát (Watermark/Overlay: Track ID, Làn vi phạm, Thời điểm)
      lên ảnh bằng chứng để tăng tính xác thực như camera giám sát thực tế.
    - Xuất file ảnh JPEG chất lượng cao vào thư mục storage/evidence/.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from backend.models.violation import Violation

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Điều phối việc tạo cảnh báo và lưu ảnh bằng chứng cho các vụ vi phạm.

    Attributes:
        evidence_dir: Thư mục lưu trữ các file ảnh JPEG bằng chứng.
        task_id: Mã định danh của tác vụ nhận diện hiện tại.
    """

    def __init__(self, evidence_dir: Path, task_id: str) -> None:
        self.evidence_dir = evidence_dir
        self.task_id = task_id
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        # Tập hợp lưu các bộ khóa (track_id, source_lane, destination_lane) đã ghi nhận
        self._seen: set[tuple[int, str, str]] = set()

    def is_recorded(self, violation: Violation) -> bool:
        """
        Kiểm tra xem trường hợp vi phạm này đã được ghi nhận trước đó chưa.
        """
        key = (violation.track_id, violation.source_lane, violation.destination_lane)
        return key in self._seen

    def save_evidence(self, violation: Violation, frame: np.ndarray) -> Path | None:
        """
        Lưu ảnh bằng chứng khi phát hiện một trường hợp vi phạm mới.

        Quy trình xử lý:
            1. Kiểm tra chống trùng lặp qua bộ khóa (track_id, source_lane, destination_lane).
            2. Nếu đã tồn tại -> bỏ qua (trả về None).
            3. Nếu là vi phạm mới:
               - Tạo bản sao khung hình (tránh can thiệp khung hình gốc).
               - Vẽ thông tin vi phạm (banner cảnh báo đỏ) lên đầu ảnh.
               - Ghi file JPEG vào thư mục evidence với tên chuẩn hóa.
               - Đánh dấu đã ghi nhận vào tập _seen.

        Args:
            violation: Đối tượng Violation chứa thông tin xe và làn đường vi phạm.
            frame: Khung hình hiện tại (mảng NumPy BGR từ OpenCV).

        Returns:
            Path: Đường dẫn tới file ảnh bằng chứng đã lưu thành công.
            None: Nếu vi phạm này đã được lưu trước đó (trùng lặp).
        """
        key = (violation.track_id, violation.source_lane, violation.destination_lane)
        if key in self._seen:
            return None

        try:
            import cv2
        except ImportError as exc:
            logger.error("Không thể lưu ảnh bằng chứng vì thiếu OpenCV: %s", exc)
            return None

        # ── 1. Tạo bản sao khung hình để vẽ nhãn minh chứng ──
        evidence_frame = frame.copy()

        # ── 2. Vẽ dải banner cảnh báo ở góc trên cùng của ảnh ──
        banner_text = (
            f"[CANH BAO SAI LAN] ID: {violation.track_id} | "
            f"Lan: {violation.source_lane} -> {violation.destination_lane} | "
            f"F: {violation.frame_index} ({violation.timestamp_seconds:.1f}s)"
        )
        # Nền đỏ cho banner
        cv2.rectangle(evidence_frame, (10, 10), (len(banner_text) * 11 + 20, 42), (0, 0, 200), -1)
        # Chữ trắng rõ nét
        cv2.putText(
            evidence_frame,
            banner_text,
            (15, 33),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # ── 3. Đặt tên file theo chuẩn và lưu ra ổ đĩa ──
        filename = (
            f"{self.task_id}-track-{violation.track_id}-frame-{violation.frame_index}.jpg"
        )
        output_path = self.evidence_dir / filename

        success = cv2.imwrite(str(output_path), evidence_frame)
        if not success:
            logger.error("Ghi file ảnh bằng chứng thất bại: %s", output_path)
            raise OSError(f"Could not write evidence image: {output_path}")

        self._seen.add(key)
        logger.info(
            "Đã lưu ảnh bằng chứng vi phạm: %s (Track ID: %d)",
            filename,
            violation.track_id,
        )
        return output_path

    @property
    def total_alerts(self) -> int:
        """Tổng số cảnh báo vi phạm duy nhất đã được ghi nhận."""
        return len(self._seen)

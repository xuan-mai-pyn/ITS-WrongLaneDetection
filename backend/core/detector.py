"""
Bộ nhận diện phương tiện bằng YOLO (Ultralytics), nạp trọng số theo kiểu lazy.

Module này bọc mô hình YOLO để các thành phần khác (tracker, video_processor)
chỉ cần gọi `detect()` hoặc `track()` và nhận về danh sách `Vehicle`:
    - `detect()`: nhận diện phương tiện trên một khung hình, chưa gán track ID.
    - `track()`: nhận diện kèm theo dõi bằng ByteTrack để giữ ID giữa các khung hình.

Trọng số YOLO không được tải tự động và không được commit lên repo; file `.pt`
phải được đặt sẵn ở máy (mặc định `models/weights/yolov8n.pt`, hoặc cấu hình
qua biến môi trường `ITS_MODEL_PATH`).
"""

from pathlib import Path

import numpy as np

from backend.models.vehicle import Vehicle

# Mã lớp COCO của các phương tiện cần nhận diện: 2=car, 3=motorcycle, 5=bus, 7=truck.
VEHICLE_CLASS_IDS = {2, 3, 5, 7}


class YOLODetector:
    """Nạp trọng số YOLO cục bộ chỉ khi thật sự cần xử lý video."""

    def __init__(self, weights_path: Path, confidence: float = 0.35) -> None:
        """
        Khởi tạo bộ nhận diện.

        Args:
            weights_path: Đường dẫn file trọng số YOLO (.pt) có sẵn trên máy.
            confidence: Ngưỡng độ tin cậy tối thiểu để giữ lại một phát hiện (0-1).

        Raises:
            FileNotFoundError: Khi file trọng số không tồn tại.
            RuntimeError: Khi chưa cài thư viện ultralytics.
        """
        if not weights_path.is_file():
            raise FileNotFoundError(
                f"YOLO weights were not found at {weights_path}. "
                "Place a compatible local weights file there or set ITS_MODEL_PATH."
            )
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install the project dependencies to use YOLO detection.") from exc

        self._model = YOLO(str(weights_path))
        self.confidence = confidence

    def detect(self, frame: np.ndarray) -> list[Vehicle]:
        """Nhận diện phương tiện trên một khung hình, không gán mã theo dõi (track_id)."""
        results = self._model.predict(
            source=frame,
            conf=self.confidence,
            classes=sorted(VEHICLE_CLASS_IDS),
            verbose=False,
        )
        return self._parse_results(results, include_track_ids=False)

    def track(self, frame: np.ndarray) -> list[Vehicle]:
        """Nhận diện phương tiện và dùng ByteTrack của Ultralytics để duy trì track_id."""
        results = self._model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.confidence,
            classes=sorted(VEHICLE_CLASS_IDS),
            verbose=False,
        )
        return self._parse_results(results, include_track_ids=True)

    @staticmethod
    def _parse_results(results: object, include_track_ids: bool) -> list[Vehicle]:
        """
        Chuyển kết quả thô của Ultralytics thành danh sách `Vehicle`.

        Args:
            results: Kết quả trả về từ `predict()` hoặc `track()` của YOLO.
            include_track_ids: True nếu cần lấy track_id từ kết quả (chế độ tracking).

        Returns:
            Danh sách phương tiện; bỏ qua các lớp không thuộc `VEHICLE_CLASS_IDS`.
        """
        vehicles: list[Vehicle] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            xyxy = boxes.xyxy.cpu().tolist()
            confidences = boxes.conf.cpu().tolist()
            class_ids = boxes.cls.int().cpu().tolist()
            track_ids = None
            if include_track_ids and boxes.id is not None:
                track_ids = boxes.id.int().cpu().tolist()
            for index, (coordinates, confidence, class_id) in enumerate(
                zip(xyxy, confidences, class_ids)
            ):
                if class_id not in VEHICLE_CLASS_IDS:
                    continue
                label = str(result.names.get(class_id, class_id))
                track_id = track_ids[index] if track_ids is not None else None
                vehicles.append(
                    Vehicle(
                        box=tuple(float(value) for value in coordinates),
                        confidence=float(confidence),
                        class_id=int(class_id),
                        label=label,
                        track_id=int(track_id) if track_id is not None else None,
                    )
                )
        return vehicles
"""Lazy Ultralytics YOLO vehicle detector."""

from pathlib import Path

import numpy as np

from backend.models.vehicle import Vehicle

VEHICLE_CLASS_IDS = {2, 3, 5, 7}


class YOLODetector:
    """Load local YOLO weights only when processing is explicitly requested."""

    def __init__(self, weights_path: Path, confidence: float = 0.35) -> None:
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
        """Return vehicle boxes for a single frame without assigning track IDs."""
        results = self._model.predict(
            source=frame,
            conf=self.confidence,
            classes=sorted(VEHICLE_CLASS_IDS),
            verbose=False,
        )
        return self._parse_results(results, include_track_ids=False)

    def track(self, frame: np.ndarray) -> list[Vehicle]:
        """Detect vehicles and ask Ultralytics to maintain ByteTrack identities."""
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

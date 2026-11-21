"""Vehicle tracking: YOLO detection + ByteTrack IDs + per-track position history."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from backend.models.vehicle import Vehicle

Point = Tuple[float, float]

# COCO class ids for vehicles
VEHICLE_CLASSES: Dict[int, str] = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@dataclass
class TrackedObject:
    """One tracked vehicle in the current frame."""

    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    frame_index: int
    history: List[Point] = field(default_factory=list)  # oldest -> newest

    @property
    def anchor(self) -> Point:
        """Bottom-center of the box: the point closest to the road surface."""
        x1, _, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, y2)

    def direction(
        self, window: int = 10, min_distance: float = 5.0
    ) -> Optional[Point]:
        """Unit movement vector (dx, dy) over the last `window` points.

        Returns None if the vehicle barely moved or has too little history.
        """
        points = self.history[-window:]
        if len(points) < 2:
            return None
        dx = points[-1][0] - points[0][0]
        dy = points[-1][1] - points[0][1]
        distance = math.hypot(dx, dy)
        if distance < min_distance:
            return None
        return (dx / distance, dy / distance)


class VehicleTracker:
    """Wraps an Ultralytics YOLO model with ByteTrack and keeps track history."""

    def __init__(
        self,
        model: Any = None,
        model_path: str = "yolov8n.pt",
        tracker_config: str = "bytetrack.yaml",
        conf: float = 0.3,
        iou: float = 0.5,
        vehicle_classes: Optional[Dict[int, str]] = None,
        history_length: int = 30,
        max_missing_frames: int = 60,
        device: Optional[str] = None,
    ) -> None:
        self._model = model
        self._model_was_provided = model is not None
        self.model_path = model_path
        self.tracker_config = tracker_config
        self.conf = conf
        self.iou = iou
        self.vehicle_classes = vehicle_classes or VEHICLE_CLASSES
        self.history_length = history_length
        self.max_missing_frames = max_missing_frames
        self.device = device

        self._histories: Dict[int, Deque[Point]] = {}
        self._last_seen: Dict[int, int] = {}
        self._frame_index = -1

    def _load_model(self) -> Any:
        if self._model is None:
            from ultralytics import YOLO  # lazy import: tests don't need weights

            self._model = YOLO(self.model_path)
        return self._model

    def update(self, frame: Any) -> List[TrackedObject] | List[Vehicle]:
        """Run detection + tracking on one frame (BGR numpy array)."""
        model = self._load_model()
        if self._model_was_provided:
            tracked = model.track(frame)
            if isinstance(tracked, list) and all(
                isinstance(item, Vehicle) for item in tracked
            ):
                self._sync_vehicle_history(tracked)
            return tracked

        kwargs: Dict[str, Any] = dict(
            persist=True,
            tracker=self.tracker_config,
            conf=self.conf,
            iou=self.iou,
            classes=list(self.vehicle_classes.keys()),
            verbose=False,
        )
        if self.device:
            kwargs["device"] = self.device
        results = model.track(frame, **kwargs)
        return self.process_result(results[0])

    def process_result(self, result: Any) -> List[TrackedObject]:
        """Convert one Ultralytics result into TrackedObject list.

        Kept separate from `update` so it can be tested with fake results.
        """
        self._frame_index += 1
        boxes = getattr(result, "boxes", None)
        if boxes is None or boxes.id is None:
            self._prune()
            return []

        xyxy = boxes.xyxy.cpu().tolist()
        ids = boxes.id.int().cpu().tolist()
        classes = boxes.cls.int().cpu().tolist()
        confs = boxes.conf.cpu().tolist()

        tracked: List[TrackedObject] = []
        for bbox, track_id, class_id, confidence in zip(xyxy, ids, classes, confs):
            obj = TrackedObject(
                track_id=int(track_id),
                class_id=int(class_id),
                class_name=self.vehicle_classes.get(int(class_id), str(class_id)),
                confidence=float(confidence),
                bbox=tuple(float(v) for v in bbox),  # type: ignore[arg-type]
                frame_index=self._frame_index,
            )
            history = self._histories.setdefault(
                obj.track_id, deque(maxlen=self.history_length)
            )
            history.append(obj.anchor)
            self._last_seen[obj.track_id] = self._frame_index
            obj.history = list(history)
            tracked.append(obj)

        self._prune()
        return tracked

    def _sync_vehicle_history(self, tracked: List[Vehicle]) -> None:
        """Keep persistent position history for detector-adapter Vehicle objects."""
        self._frame_index += 1
        for vehicle in tracked:
            if vehicle.track_id is None:
                continue
            x1, _, x2, y2 = vehicle.box
            anchor = ((x1 + x2) / 2.0, y2)
            history = self._histories.setdefault(
                vehicle.track_id, deque(maxlen=self.history_length)
            )
            history.append(anchor)
            self._last_seen[vehicle.track_id] = self._frame_index
        self._prune()

    def get_history(self, track_id: int) -> List[Point]:
        return list(self._histories.get(track_id, []))

    def active_ids(self) -> List[int]:
        return list(self._histories.keys())

    def reset(self) -> None:
        """Clear all state. Call this when starting a new video."""
        self._histories.clear()
        self._last_seen.clear()
        self._frame_index = -1
        if self._model is not None and hasattr(self._model, "predictor"):
            self._model.predictor = None  # forces ByteTrack to restart

    def _prune(self) -> None:
        """Drop histories of vehicles not seen for a long time."""
        stale = [
            tid
            for tid, last in self._last_seen.items()
            if self._frame_index - last > self.max_missing_frames
        ]
        for tid in stale:
            self._histories.pop(tid, None)
            self._last_seen.pop(tid, None)
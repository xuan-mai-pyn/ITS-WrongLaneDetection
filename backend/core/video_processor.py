"""Frame-by-frame video analysis and annotated-video export."""

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


class VideoProcessor:
    """Compose the detection, tracking, lane, and violation components."""

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
        """Process a video; progress_callback receives (percent, frame index)."""
        import cv2

        capture = cv2.VideoCapture(str(input_path))
        if not capture.isOpened():
            raise ValueError(f"OpenCV could not open the uploaded video: {input_path.name}")

        fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width <= 0 or height <= 0:
            capture.release()
            raise ValueError("The uploaded video has invalid frame dimensions.")

        ensure_parent(output_path)
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            capture.release()
            raise OSError(f"OpenCV could not create the processed video: {output_path}")

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
                tracks = self.tracker.update(frame)

                for lane in self.lane_detector.lanes:
                    polygon = np.asarray(lane.polygon, dtype=np.int32)
                    cv2.polylines(frame, [polygon], True, (255, 180, 0), 2)
                    cv2.putText(
                        frame,
                        lane.id,
                        tuple(polygon[0]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 180, 0),
                        2,
                    )

                for vehicle in tracks:
                    x1, y1, x2, y2 = (int(value) for value in vehicle.box)
                    color = (0, 180, 0)
                    label = f"{vehicle.label} {vehicle.confidence:.2f}"
                    if vehicle.track_id is not None:
                        vehicle_ids.add(vehicle.track_id)
                        vehicle_classes.setdefault(vehicle.track_id, vehicle.label)
                        label = f"ID {vehicle.track_id} | {label}"
                        lane_id = self.lane_detector.lane_at(vehicle_foot_point(vehicle))
                        violation = self.wrong_lane_detector.update(
                            vehicle.track_id,
                            lane_id,
                            frame_index,
                            timestamp,
                        )
                        if violation is not None:
                            violations.append(violation)
                            color = (0, 0, 255)
                            label = f"WRONG LANE | ID {vehicle.track_id}"
                            evidence_path = self.alert_manager.save_evidence(violation, frame)
                            if evidence_path is not None:
                                violation.evidence_path = str(evidence_path)
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

                writer.write(frame)
                if progress_callback and total_frames > 0:
                    progress = min(int(frame_index * 100 / total_frames), 99)
                    if progress > last_progress:
                        progress_callback(progress, frame_index)
                        last_progress = progress
        finally:
            capture.release()
            writer.release()

        if frame_index == 0:
            raise ValueError("The uploaded video contains no readable frames.")

        elapsed = perf_counter() - started
        warnings: list[str] = []
        if not self.lane_detector.lanes:
            warnings.append("No lane polygons were configured; wrong-lane behavior was not evaluated.")
        elif not self.wrong_lane_detector.forbidden_transitions:
            warnings.append("No forbidden lane transitions were configured; wrong-lane behavior was not evaluated.")
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
            "violations": [violation.model_dump(mode="json") for violation in violations],
        }

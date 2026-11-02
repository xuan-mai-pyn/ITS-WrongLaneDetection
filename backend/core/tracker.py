"""Vehicle tracking adapter backed by Ultralytics' ByteTrack implementation."""

import numpy as np

from backend.core.detector import YOLODetector
from backend.models.vehicle import Vehicle


class VehicleTracker:
    """Keep tracker state in the detector's persistent ByteTrack model."""

    def __init__(self, detector: YOLODetector) -> None:
        self.detector = detector

    def update(self, frame: np.ndarray) -> list[Vehicle]:
        return self.detector.track(frame)

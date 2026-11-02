"""Deduplicate violation alerts and save optional JPEG evidence."""

from pathlib import Path

import numpy as np

from backend.models.violation import Violation


class AlertManager:
    """Write one evidence image per confirmed track/lane transition."""

    def __init__(self, evidence_dir: Path, task_id: str) -> None:
        self.evidence_dir = evidence_dir
        self.task_id = task_id
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self._seen: set[tuple[int, str, str]] = set()

    def save_evidence(self, violation: Violation, frame: np.ndarray) -> Path | None:
        key = (violation.track_id, violation.source_lane, violation.destination_lane)
        if key in self._seen:
            return None
        import cv2

        filename = f"{self.task_id}-track-{violation.track_id}-frame-{violation.frame_index}.jpg"
        output_path = self.evidence_dir / filename
        if not cv2.imwrite(str(output_path), frame):
            raise OSError(f"Could not write evidence image: {output_path}")
        self._seen.add(key)
        return output_path

"""Detector prerequisite tests; no model weights are downloaded."""

import tempfile
import unittest
from pathlib import Path

from backend.core.detector import YOLODetector


class DetectorTests(unittest.TestCase):
    def test_missing_local_weights_fail_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.pt"
            with self.assertRaisesRegex(FileNotFoundError, "YOLO weights were not found"):
                YOLODetector(path)


if __name__ == "__main__":
    unittest.main()

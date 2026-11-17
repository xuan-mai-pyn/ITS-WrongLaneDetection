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


    def test_prediction_and_tracking_with_local_model_stub(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        def tensor(values):
            value = Mock()
            value.cpu.return_value = value
            value.int.return_value = value
            value.tolist.return_value = values
            return value
        result = SimpleNamespace(boxes=SimpleNamespace(
            xyxy=tensor([[1, 2, 11, 22], [3, 4, 13, 24]]),
            conf=tensor([0.9, 0.8]), cls=tensor([2, 0]), id=tensor([42, 43])),
            names={2: "car", 0: "person"})
        model = Mock()
        factory = Mock(return_value=model)
        with tempfile.TemporaryDirectory() as directory:
            weights = Path(directory) / "local.pt"
            weights.touch()
            with patch.dict("sys.modules", {"ultralytics": SimpleNamespace(YOLO=factory)}):
                detector = YOLODetector(weights, confidence=0.6)
            factory.assert_called_once_with(str(weights))
            model.predict.return_value = [result]
            frame = object()
            vehicles = detector.detect(frame)
            model.predict.assert_called_once_with(source=frame, conf=0.6,
                classes=[2, 3, 5, 7], verbose=False)
            self.assertEqual(len(vehicles), 1)
            self.assertEqual(vehicles[0].box, (1.0, 2.0, 11.0, 22.0))
            self.assertEqual(vehicles[0].label, "car")
            self.assertAlmostEqual(vehicles[0].confidence, 0.9)
            self.assertIsNone(vehicles[0].track_id)
            model.track.return_value = [result]
            self.assertEqual(detector.track(frame)[0].track_id, 42)
            model.track.assert_called_once_with(source=frame, persist=True,
                tracker="bytetrack.yaml", conf=0.6, classes=[2, 3, 5, 7], verbose=False)
            result.boxes.id = None
            self.assertIsNone(detector.track(frame)[0].track_id)
            for results in ([], [SimpleNamespace(boxes=None)]):
                with self.subTest(results=results):
                    model.predict.return_value = results
                    self.assertEqual(detector.detect(frame), [])


if __name__ == "__main__":
    unittest.main()

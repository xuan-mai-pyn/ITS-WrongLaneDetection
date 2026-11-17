"""Tracker adapter behavior tests."""

import unittest
from unittest.mock import Mock

from backend.core.tracker import VehicleTracker


class TrackerTests(unittest.TestCase):
    def test_update_delegates_to_persistent_detector_tracking(self) -> None:
        detector = Mock()
        expected = [object()]
        detector.track.return_value = expected
        frame = object()
        self.assertIs(VehicleTracker(detector).update(frame), expected)
        detector.track.assert_called_once_with(frame)


    def test_multiple_frames_reuse_detector_and_preserve_identity(self):
        from backend.models.vehicle import Vehicle
        from unittest.mock import call
        detector = Mock()
        frame1, frame2 = object(), object()
        vehicle = Vehicle(box=(0, 0, 10, 10), confidence=0.9,
                          class_id=2, label="car", track_id=17)
        detector.track.side_effect = [[vehicle], [], [vehicle]]
        tracker = VehicleTracker(detector)
        self.assertEqual(tracker.update(frame1)[0].track_id, 17)
        self.assertEqual(tracker.update(frame2), [])
        self.assertEqual(tracker.update(frame1)[0].track_id, 17)
        self.assertEqual(detector.track.call_args_list,
                         [call(frame1), call(frame2), call(frame1)])

    def test_detector_errors_propagate(self):
        detector = Mock()
        detector.track.side_effect = RuntimeError("tracking failed")
        with self.assertRaisesRegex(RuntimeError, "tracking failed"):
            VehicleTracker(detector).update(object())


if __name__ == "__main__":
    unittest.main()

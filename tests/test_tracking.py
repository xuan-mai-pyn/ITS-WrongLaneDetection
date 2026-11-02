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


if __name__ == "__main__":
    unittest.main()

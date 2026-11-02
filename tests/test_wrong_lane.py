"""Lane membership and multi-frame forbidden-transition tests."""

import unittest

from backend.core.wrong_lane_detector import WrongLaneDetector
from backend.models.lane import Lane


class WrongLaneTests(unittest.TestCase):
    def test_polygon_contains_interior_but_not_exterior_point(self) -> None:
        lane = Lane(id="lane_a", polygon=[(0, 0), (10, 0), (10, 10), (0, 10)])
        self.assertTrue(lane.contains((5, 5)))
        self.assertFalse(lane.contains((15, 5)))

    def test_forbidden_transition_requires_confirmation(self) -> None:
        detector = WrongLaneDetector({("lane_a", "lane_b")}, confirm_frames=3)
        self.assertIsNone(detector.update(9, "lane_a", 1, 0.1))
        self.assertIsNone(detector.update(9, "lane_b", 2, 0.2))
        self.assertIsNone(detector.update(9, "lane_b", 3, 0.3))
        violation = detector.update(9, "lane_b", 4, 0.4)
        self.assertIsNotNone(violation)
        self.assertEqual(violation.track_id, 9)
        self.assertEqual((violation.source_lane, violation.destination_lane), ("lane_a", "lane_b"))
        self.assertIsNone(detector.update(9, "lane_b", 5, 0.5))

    def test_unconfigured_transition_does_not_report_violation(self) -> None:
        detector = WrongLaneDetector(set(), confirm_frames=1)
        detector.update(2, "lane_a", 1, 0.1)
        self.assertIsNone(detector.update(2, "lane_b", 2, 0.2))


if __name__ == "__main__":
    unittest.main()

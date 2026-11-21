"""Lane configuration and forbidden-transition tests."""

import json
import tempfile
import unittest
from pathlib import Path

from backend.core.lane_detector import LaneDetector
from backend.core.wrong_lane_detector import WrongLaneDetector
from backend.models.lane import Lane


class WrongLaneTests(unittest.TestCase):
    def test_polygon_contains_interior_but_not_exterior_point(self):
        lane = Lane(
            id="lane_a",
            polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
        )

        self.assertTrue(lane.contains((5, 5)))
        self.assertFalse(lane.contains((15, 5)))

    def test_forbidden_transition_requires_confirmation(self):
        detector = WrongLaneDetector(
            {("lane_a", "lane_b")},
            confirm_frames=3,
        )

        self.assertIsNone(detector.update(9, "lane_a", 1, 0.1))
        self.assertIsNone(detector.update(9, "lane_b", 2, 0.2))
        self.assertIsNone(detector.update(9, "lane_b", 3, 0.3))

        violation = detector.update(9, "lane_b", 4, 0.4)

        self.assertIsNotNone(violation)
        self.assertEqual(violation.track_id, 9)
        self.assertEqual(
            (violation.source_lane, violation.destination_lane),
            ("lane_a", "lane_b"),
        )
        self.assertIsNone(detector.update(9, "lane_b", 5, 0.5))

    def test_unconfigured_transition_does_not_report_violation(self):
        detector = WrongLaneDetector(set(), confirm_frames=1)
        detector.update(2, "lane_a", 1, 0.1)

        self.assertIsNone(detector.update(2, "lane_b", 2, 0.2))

    def test_confirmation_threshold_must_be_positive(self):
        for value in (0, -1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    WrongLaneDetector(set(), confirm_frames=value)

    def test_immediate_confirmation_has_frame_timestamp_and_no_duplicates(self):
        detector = WrongLaneDetector(
            {("a", "b")},
            confirm_frames=1,
        )
        detector.update(1, "a", 0, 0)

        violation = detector.update(1, "b", 15, 0.5, "bus")

        self.assertIsNotNone(violation)
        self.assertEqual(violation.vehicle_type, "bus")
        self.assertEqual(violation.frame_index, 15)
        self.assertEqual(violation.timestamp_seconds, 0.5)
        self.assertIsNone(detector.update(1, "b", 16, 0.6))

    def test_missing_lane_cancels_pending_confirmation(self):
        detector = WrongLaneDetector(
            {("a", "b")},
            confirm_frames=2,
        )

        for frame, lane in enumerate(["a", "b", None, "b", "b"]):
            self.assertIsNone(
                detector.update(1, lane, frame, frame / 10)
            )

    def test_return_to_source_cancels_pending_transition(self):
        detector = WrongLaneDetector(
            {("a", "b")},
            confirm_frames=2,
        )

        for frame, lane in enumerate(["a", "b", "a", "a"]):
            self.assertIsNone(
                detector.update(1, lane, frame, frame / 10)
            )

        self.assertIsNone(detector.update(1, "b", 4, 0.4))
        self.assertIsNotNone(detector.update(1, "b", 5, 0.5))

    def test_tracks_have_independent_confirmation_and_deduplication(self):
        detector = WrongLaneDetector(
            {("a", "b")},
            confirm_frames=2,
        )

        for track in (1, 2):
            detector.update(track, "a", 0, 0)
            self.assertIsNone(detector.update(track, "b", 1, 0.1))

        for track in (1, 2):
            violation = detector.update(track, "b", 2, 0.2)
            self.assertIsNotNone(violation)
            self.assertEqual(violation.track_id, track)

            detector.update(track, "a", 3, 0.3)

            # The same transition for the same track is not reported twice.
            self.assertIsNone(detector.update(track, "b", 4, 0.4))
            self.assertIsNone(detector.update(track, "b", 5, 0.5))

    def test_reverse_direction_is_allowed_without_rule(self):
        detector = WrongLaneDetector(
            {("a", "b")},
            confirm_frames=1,
        )
        detector.update(1, "b", 0, 0)

        self.assertIsNone(detector.update(1, "a", 1, 0.1))

    def test_lane_configuration_and_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lanes.json"

            configuration = {
                "lanes": [
                    {
                        "id": "a",
                        "polygon": [
                            [0, 0],
                            [10, 0],
                            [10, 10],
                            [0, 10],
                        ],
                    }
                ]
            }
            path.write_text(
                json.dumps(configuration),
                encoding="utf-8",
            )

            detector = LaneDetector.from_json(path)

            self.assertEqual(detector.lane_at((5, 5)), "a")
            self.assertIsNone(detector.lane_at((15, 5)))
            self.assertIsNone(
                LaneDetector.from_json(None).lane_at((5, 5))
            )

            invalid_configurations = [
                {},
                {"lanes": "invalid"},
                {"lanes": [{"id": "a", "polygon": [[0, 0]]}]},
            ]

            for payload in invalid_configurations:
                with self.subTest(payload=payload):
                    path.write_text(
                        json.dumps(payload),
                        encoding="utf-8",
                    )
                    with self.assertRaises(ValueError):
                        LaneDetector.from_json(path)

            path.unlink()

            with self.assertRaises(FileNotFoundError):
                LaneDetector.from_json(path)


if __name__ == "__main__":
    unittest.main()
"""VehicleTracker adapter and position-history tests."""

import unittest
from unittest.mock import Mock, call

from backend.core.tracker import VehicleTracker
from backend.models.vehicle import Vehicle


class TrackerTests(unittest.TestCase):

    @staticmethod
    def make_vehicle(
        track_id=17,
        box=(0, 0, 10, 10),
        label="car",
    ):
        return Vehicle(
            box=box,
            confidence=0.9,
            class_id=2,
            label=label,
            track_id=track_id,
        )

    def test_update_delegates_to_detector(self):
        detector = Mock()
        expected = [self.make_vehicle()]
        detector.track.return_value = expected
        frame = object()

        result = VehicleTracker(detector).update(frame)

        self.assertIs(result, expected)
        detector.track.assert_called_once_with(frame)

    def test_multiple_frames_preserve_vehicle_identity(self):
        detector = Mock()
        frame1, frame2 = object(), object()

        vehicle = self.make_vehicle()

        detector.track.side_effect = [
            [vehicle],
            [],
            [vehicle],
        ]

        tracker = VehicleTracker(detector)

        self.assertEqual(tracker.update(frame1)[0].track_id, 17)
        self.assertEqual(tracker.update(frame2), [])
        self.assertEqual(tracker.update(frame1)[0].track_id, 17)

        self.assertEqual(
            detector.track.call_args_list,
            [call(frame1), call(frame2), call(frame1)],
        )

        self.assertEqual(len(tracker.get_history(17)), 2)

    def test_position_history_uses_bottom_center(self):
        detector = Mock()
        detector.track.side_effect = [
            [self.make_vehicle(box=(10, 20, 30, 60))],
            [self.make_vehicle(box=(20, 25, 40, 70))],
        ]

        tracker = VehicleTracker(detector)

        tracker.update(object())
        tracker.update(object())

        self.assertEqual(
            tracker.get_history(17),
            [(20.0, 60.0), (30.0, 70.0)],
        )

    def test_vehicle_without_track_id_is_ignored(self):
        detector = Mock()
        vehicle = self.make_vehicle(track_id=None)
        detector.track.return_value = [vehicle]

        tracker = VehicleTracker(detector)

        result = tracker.update(object())

        self.assertEqual(result, [vehicle])
        self.assertEqual(tracker.get_history(17), [])
        self.assertEqual(tracker.active_ids(), [])

    def test_history_respects_maximum_length(self):
        detector = Mock()
        detector.track.side_effect = [
            [self.make_vehicle(box=(0, 0, 10, 10))],
            [self.make_vehicle(box=(10, 0, 20, 20))],
            [self.make_vehicle(box=(20, 0, 30, 30))],
        ]

        tracker = VehicleTracker(detector, history_length=2)

        for _ in range(3):
            tracker.update(object())

        self.assertEqual(
            tracker.get_history(17),
            [(15.0, 20.0), (25.0, 30.0)],
        )

    def test_stale_track_history_is_pruned(self):
        detector = Mock()
        vehicle = self.make_vehicle()

        detector.track.side_effect = [
            [vehicle],
            [],
            [],
            [],
        ]

        tracker = VehicleTracker(
            detector,
            max_missing_frames=2,
        )

        tracker.update(object())
        self.assertEqual(tracker.active_ids(), [17])

        tracker.update(object())
        tracker.update(object())

        self.assertEqual(tracker.active_ids(), [17])

        tracker.update(object())

        self.assertEqual(tracker.active_ids(), [])
        self.assertEqual(tracker.get_history(17), [])

    def test_reset_clears_tracking_history(self):
        detector = Mock()
        detector.track.return_value = [self.make_vehicle()]

        tracker = VehicleTracker(detector)

        tracker.update(object())
        self.assertEqual(tracker.active_ids(), [17])

        tracker.reset()

        self.assertEqual(tracker.active_ids(), [])
        self.assertEqual(tracker.get_history(17), [])
        self.assertEqual(tracker._frame_index, -1)

    def test_detector_errors_propagate(self):
        detector = Mock()
        detector.track.side_effect = RuntimeError("tracking failed")

        with self.assertRaisesRegex(RuntimeError, "tracking failed"):
            VehicleTracker(detector).update(object())


if __name__ == "__main__":
    unittest.main()

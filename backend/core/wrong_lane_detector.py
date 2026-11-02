"""Rule-based, multi-frame confirmation for configured forbidden lane transitions."""

from backend.models.violation import Violation


class WrongLaneDetector:
    """Confirm configured lane transitions; an empty rule set reports no violations."""

    def __init__(
        self,
        forbidden_transitions: set[tuple[str, str]],
        confirm_frames: int = 8,
    ) -> None:
        if confirm_frames < 1:
            raise ValueError("confirm_frames must be at least 1.")
        self.forbidden_transitions = forbidden_transitions
        self.confirm_frames = confirm_frames
        self._states: dict[int, tuple[str, str | None, int]] = {}
        self._reported: set[tuple[int, str, str]] = set()

    def update(
        self,
        track_id: int,
        lane_id: str | None,
        frame_index: int,
        timestamp_seconds: float,
    ) -> Violation | None:
        """Return one violation after the same forbidden transition persists."""
        if lane_id is None:
            if track_id in self._states:
                previous_lane, _, _ = self._states[track_id]
                self._states[track_id] = (previous_lane, None, 0)
            return None

        previous = self._states.get(track_id)
        if previous is None:
            self._states[track_id] = (lane_id, None, 0)
            return None

        previous_lane, transition_origin, count = previous
        if lane_id == previous_lane:
            if transition_origin is not None:
                count += 1
                self._states[track_id] = (previous_lane, transition_origin, count)
                key = (track_id, transition_origin, previous_lane)
                if count >= self.confirm_frames and key not in self._reported:
                    self._reported.add(key)
                    return Violation(
                        track_id=track_id,
                        source_lane=transition_origin,
                        destination_lane=previous_lane,
                        frame_index=frame_index,
                        timestamp_seconds=timestamp_seconds,
                    )
            return None

        if (previous_lane, lane_id) in self.forbidden_transitions:
            self._states[track_id] = (lane_id, previous_lane, 1)
            key = (track_id, previous_lane, lane_id)
            if self.confirm_frames == 1 and key not in self._reported:
                self._reported.add(key)
                return Violation(
                    track_id=track_id,
                    source_lane=previous_lane,
                    destination_lane=lane_id,
                    frame_index=frame_index,
                    timestamp_seconds=timestamp_seconds,
                )
            return None

        self._states[track_id] = (lane_id, None, 0)
        return None

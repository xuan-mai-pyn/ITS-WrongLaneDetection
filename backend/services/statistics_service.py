"""Statistics derived from persisted database records."""

from typing import Annotated

from pydantic import Field
from typing_extensions import TypedDict

from backend.database.repository import Repository


class StatisticsSummary(TypedDict):
    """Aggregate processing metrics consumed by the dashboard."""

    total_videos: int
    processed_videos: int
    total_vehicles: int
    total_violations: int
    videos_with_violations: int
    vehicle_types: dict[str, int]
    detection_rate: Annotated[
        float,
        Field(
            description=(
                "Fraction of processed videos with at least one recorded violation, "
                "rounded to four decimal places. Zero when no video is processed."
            ),
        ),
    ]


class StatisticsService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def get_summary(self) -> StatisticsSummary:
        """Read stored counts and calculate the video violation rate."""
        totals = self.repository.get_statistics()
        processed_videos = totals["processed_videos"]
        videos_with_violations = totals["videos_with_violations"]
        detection_rate = (
            round(videos_with_violations / processed_videos, 4)
            if processed_videos
            else 0.0
        )
        return StatisticsSummary(
            total_videos=totals["total_videos"],
            processed_videos=processed_videos,
            total_vehicles=totals["total_vehicles"],
            total_violations=totals["total_violations"],
            videos_with_violations=videos_with_violations,
            vehicle_types=totals["vehicle_types"],
            detection_rate=detection_rate,
        )
"""Statistics derived only from persisted database records."""

from typing import Any

from backend.database.repository import Repository


class StatisticsService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def get_summary(self) -> dict[str, Any]:
        totals = self.repository.get_statistics()
        detection_rate = (
            totals["videos_with_violations"] / totals["processed_videos"]
            if totals["processed_videos"]
            else 0.0
        )
        return {**totals, "detection_rate": round(detection_rate, 4)}

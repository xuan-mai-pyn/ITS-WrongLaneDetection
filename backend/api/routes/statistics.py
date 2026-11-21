"""Persisted processing statistics endpoint."""

"""Persisted processing statistics endpoint."""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_repository
from backend.database.repository import Repository
from backend.services.statistics_service import StatisticsService, StatisticsSummary

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsSummary)
def get_statistics(
    repository: Repository = Depends(get_repository),
) -> StatisticsSummary:
    """Return aggregate video, vehicle, and violation counts from SQLite."""
    return StatisticsService(repository).get_summary()
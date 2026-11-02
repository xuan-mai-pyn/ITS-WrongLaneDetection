"""Persisted processing statistics endpoint."""

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_repository
from backend.database.repository import Repository
from backend.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("")
def get_statistics(repository: Repository = Depends(get_repository)) -> dict[str, Any]:
    return StatisticsService(repository).get_summary()

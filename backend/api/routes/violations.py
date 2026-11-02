"""Persisted traffic-violation endpoint."""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_repository
from backend.database.repository import Repository
from backend.schemas.violation import ViolationRead

router = APIRouter(prefix="/violations", tags=["violations"])


@router.get("", response_model=list[ViolationRead])
def list_violations(
    limit: int = Query(default=100, ge=1, le=500),
    repository: Repository = Depends(get_repository),
) -> list[ViolationRead]:
    return repository.list_violations(limit=limit)

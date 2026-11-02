"""FastAPI dependencies for shared application services."""

from fastapi import Request

from backend.config import Settings
from backend.database.repository import Repository


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_repository(request: Request) -> Repository:
    return request.app.state.repository

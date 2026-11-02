"""FastAPI application factory and browser entry points."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import detection, health, statistics, video, violations
from backend.config import Settings
from backend.database.repository import Repository

FRONTEND_DIR = Settings.project_root / "frontend"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API app and initialize only its local SQLite schema."""
    app_settings = settings or Settings()
    app_settings.prepare_directories()
    app = FastAPI(
        title="ITS Wrong-Lane Detection API",
        description="A configurable starter API for traffic video analysis.",
        version="0.1.0",
    )
    app.state.settings = app_settings
    app.state.repository = Repository(app_settings.database_path)
    app.state.repository.initialize()

    app.include_router(health.router, prefix="/api")
    app.include_router(video.router, prefix="/api")
    app.include_router(detection.router, prefix="/api")
    app.include_router(violations.router, prefix="/api")
    app.include_router(statistics.router, prefix="/api")

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "pages" / "dashboard.html")

    @app.get("/{page_name}", include_in_schema=False)
    def frontend_page(page_name: str) -> FileResponse:
        page = FRONTEND_DIR / "pages" / f"{page_name}.html"
        if page_name not in {"dashboard", "detection", "history", "statistics"}:
            page = FRONTEND_DIR / "index.html"
        return FileResponse(page)

    return app


app = create_app()

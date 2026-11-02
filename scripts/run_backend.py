"""Run the development API server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from backend.config import Settings

if __name__ == "__main__":
    settings = Settings()
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=False)

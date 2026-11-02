"""Initialize the local SQLite schema."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import Settings
from backend.database.repository import Repository

if __name__ == "__main__":
    settings = Settings()
    settings.prepare_directories()
    Repository(settings.database_path).initialize()
    print(f"SQLite database initialized at {settings.database_path}")

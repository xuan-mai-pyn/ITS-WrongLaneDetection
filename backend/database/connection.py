"""SQLite connection factory and schema initialization."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    processing_seconds REAL,
    vehicle_type_counts_json TEXT NOT NULL DEFAULT '{}',
    processed_frames INTEGER NOT NULL DEFAULT 0,
    vehicle_count INTEGER NOT NULL DEFAULT 0,
    violation_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS detection_tasks (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    current_frame INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    result_json TEXT,
    output_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES detection_tasks(id),
    video_id TEXT NOT NULL REFERENCES videos(id),
    track_id INTEGER NOT NULL,
    source_lane TEXT NOT NULL,
    destination_lane TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    timestamp_seconds REAL NOT NULL,
    detected_at TEXT NOT NULL,
    evidence_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_video_id ON detection_tasks(video_id);
CREATE INDEX IF NOT EXISTS idx_violations_video_id ON violations(video_id);
"""


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Open and reliably close a short-lived SQLite connection."""
    connection = sqlite3.connect(database_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        video_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(videos)").fetchall()
        }
        if "processing_seconds" not in video_columns:
            connection.execute("ALTER TABLE videos ADD COLUMN processing_seconds REAL")
        if "vehicle_type_counts_json" not in video_columns:
            connection.execute(
                "ALTER TABLE videos ADD COLUMN vehicle_type_counts_json TEXT NOT NULL DEFAULT '{}'"
            )

"""File helpers for generated runtime artifacts."""

from pathlib import Path

def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

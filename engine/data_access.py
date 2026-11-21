"""Data access layer: serves static files from mocks/ (mock mode) or
data/processed/ (real mode), with a graceful fallback to mocks/ when
real-mode files are not yet produced by A1's pipeline.

Every load returns the parsed JSON document and a ``source`` string so
callers (notably /confidence) can report where data actually came from.
"""
import json
from pathlib import Path
from typing import Tuple

from config import DATA_MODE, MOCKS_DIR, PROCESSED_DIR, RESPONSES_DIR


def _resolve(filename: str) -> Tuple[Path, str]:
    """Return (path, source_label) for a data file.

    In real mode, prefer data/processed/<filename>; fall back to mocks/
    if it does not exist. In mock mode, always read mocks/.
    """
    if DATA_MODE == "real":
        real_path = PROCESSED_DIR / filename
        if real_path.exists():
            return real_path, "real"
    mock_path = MOCKS_DIR / filename
    if mock_path.exists():
        return mock_path, "mock"
    # Last resort: try real even in mock mode (should not happen).
    real_path = PROCESSED_DIR / filename
    if real_path.exists():
        return real_path, "real"
    raise FileNotFoundError(f"Data file not found in mocks/ or data/processed/: {filename}")


def load_json(filename: str) -> Tuple[dict, str]:
    """Load a JSON file. Returns (data, source_label)."""
    path, source = _resolve(filename)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f), source


def load_geojson(filename: str) -> Tuple[dict, str]:
    """Load a GeoJSON file. Returns (data, source_label)."""
    return load_json(filename)


def load_response(filename: str) -> dict:
    """Load a static canned response from mocks/responses/."""
    path = RESPONSES_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
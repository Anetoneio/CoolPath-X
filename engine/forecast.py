"""Forecast fetch + cache for COOLPATH X.

Prefers reading the committed cache at engine/cache/forecast.json so the engine
never depends on network or server disk writes at runtime. If missing or stale,
falls back to a live Open-Meteo fetch in memory only with a short timeout.
If the cache is stale and live fetch fails, falls back to using the stale cache
with source label "stale-cache" to degrade confidence. On total failure,
returns a safe default forecast.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import httpx

from config import APP_DIR, FORECAST_CACHE

# Ahmedabad, India (used for the Open-Meteo request).
AHMEDABAD_LAT = 23.0225
AHMEDABAD_LON = 72.5714
FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={AHMEDABAD_LAT}&longitude={AHMEDABAD_LON}"
    "&hourly=temperature_2m,relative_humidity_2m,apparent_temperature"
    "&timezone=Asia/Kolkata"
)

DEFAULT_TEMP_C = 35.0  # PLACEHOLDER - pending A1 verification (conservative hot default)
FETCH_TIMEOUT_SEC = 5.0
STALE_THRESHOLD_HOURS = 24.0
MEMORY_TTL_HOURS = 3.0

# Process-local only. Never written to disk. Keyed by the cache path so a
# test that patches FORECAST_CACHE does not reuse another path's entry.
_memory_cache: dict | None = None


def clear_memory_cache() -> None:
    """Drop the in-memory forecast entry. Tests reset this between cases."""
    global _memory_cache
    _memory_cache = None


def _memory_get(path: Path) -> Tuple[dict, str] | None:
    entry = _memory_cache
    if not entry or entry.get("path") != str(path):
        return None
    stored_at = entry.get("stored_at")
    if not isinstance(stored_at, datetime):
        return None
    age_hours = (datetime.now(timezone.utc) - stored_at).total_seconds() / 3600
    if age_hours > MEMORY_TTL_HOURS:
        return None
    return entry["data"], entry["source"]


def _memory_put(path: Path, data: dict, source: str) -> None:
    global _memory_cache
    _memory_cache = {
        "path": str(path),
        "stored_at": datetime.now(timezone.utc),
        "data": data,
        "source": source,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_forecast() -> dict:
    """Fetch forecast from Open-Meteo using httpx with short timeout. Returns raw JSON or raises."""
    resp = httpx.get(FORECAST_URL, timeout=FETCH_TIMEOUT_SEC)
    resp.raise_for_status()
    data = resp.json()
    data["_cached_at"] = _now_iso()
    data["_source"] = "open-meteo"
    return data


def _default_forecast() -> dict:
    """Safe default when Open-Meteo is unreachable."""
    now = datetime.now(timezone.utc)
    hourly = {
        "time": [now.isoformat()],
        "temperature_2m": [DEFAULT_TEMP_C],
        "relative_humidity_2m": [50],
        "apparent_temperature": [DEFAULT_TEMP_C + 3],
    }
    return {
        "hourly": hourly,
        "_cached_at": _now_iso(),
        "_source": "default-fallback",
        "_error": "Open-Meteo unavailable; using safe default",
    }


def _is_stale(data: dict) -> bool:
    cached_at = data.get("_cached_at")
    if not cached_at:
        return True
    try:
        cached_dt = datetime.fromisoformat(cached_at)
        age_hours = (datetime.now(timezone.utc) - cached_dt).total_seconds() / 3600
        return age_hours > STALE_THRESHOLD_HOURS
    except (ValueError, TypeError):
        return True


def load_forecast() -> Tuple[dict, str]:
    """Return (forecast_dict, source_label).

    Checks a 3-hour in-memory cache first, then the on-disk cache at
    engine/cache/forecast.json. Neither path writes a file at runtime.
    If the disk cache is missing or stale, attempts a live in-memory fetch
    with a short timeout. Internal source labels stay "cache", "open-meteo",
    "stale-cache", and "default-fallback". Public names such as "live" are
    applied only when building the /confidence response.
    If the cache is stale and the live fetch fails, uses the stale file and
    returns "stale-cache" so confidence scoring can lower the score.
    On total failure, returns a safe default forecast.
    """
    cached_data = None
    memory_hit = _memory_get(FORECAST_CACHE)
    if memory_hit is not None:
        return memory_hit

    if FORECAST_CACHE.exists():
        try:
            with FORECAST_CACHE.open("r", encoding="utf-8") as f:
                cached_data = json.load(f)
            if not _is_stale(cached_data):
                _memory_put(FORECAST_CACHE, cached_data, "cache")
                return cached_data, "cache"
        except (json.JSONDecodeError, OSError):
            cached_data = None

    # Missing or stale: try short in-memory network fetch (no disk write)
    try:
        data = fetch_forecast()
        _memory_put(FORECAST_CACHE, data, "open-meteo")
        return data, "open-meteo"
    except Exception:
        if cached_data is not None:
            _memory_put(FORECAST_CACHE, cached_data, "stale-cache")
            return cached_data, "stale-cache"
        data = _default_forecast()
        _memory_put(FORECAST_CACHE, data, "default-fallback")
        return data, "default-fallback"


def temperature_at(forecast: dict, hour: int) -> float | None:
    """Return the forecast temperature (C) for a given hour of the day,
    or None if unavailable."""
    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    if not times or not temps:
        return None
    # Match by hour-of-day from the first matching ISO timestamp.
    for t, temp in zip(times, temps):
        try:
            if int(t[11:13]) == hour:
                return float(temp)
        except (ValueError, IndexError, TypeError):
            continue
    return temps[0] if temps else None

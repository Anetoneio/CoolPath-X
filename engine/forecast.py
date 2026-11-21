"""Forecast fetch + cache for COOLPATH X.

Fetches hourly temperature from Open-Meteo once and caches to
engine/cache/forecast.json so the demo never depends on the network at
request time. On any failure (no network, bad response), returns a safe
default forecast and records that the source was unavailable so
/confidence can downgrade the forecast_age component.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import requests

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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_forecast() -> dict:
    """Fetch forecast from Open-Meteo. Returns the raw JSON or raises."""
    import time

    resp = requests.get(FORECAST_URL, timeout=15)
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


def load_forecast() -> Tuple[dict, str]:
    """Return (forecast_dict, source_label).

    Prefers the on-disk cache at engine/cache/forecast.json. If the cache
    is missing or stale, attempts a one-time Open-Meteo fetch and writes
    the cache. On any failure, returns a safe default forecast with
    source_label "default-fallback".
    """
    if FORECAST_CACHE.exists():
        try:
            with FORECAST_CACHE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data, "cache"
        except (json.JSONDecodeError, OSError):
            pass  # fall through to fetch

    # Try a one-time network fetch to (re)populate the cache.
    try:
        data = fetch_forecast()
        FORECAST_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with FORECAST_CACHE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data, "open-meteo"
    except Exception:
        data = _default_forecast()
        # Persist the default so subsequent reads don't hammer the network.
        try:
            FORECAST_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with FORECAST_CACHE.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass
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
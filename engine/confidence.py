"""Confidence scoring for GET /confidence.

Computes overall_0_100 from five components:
  - data_age: how old the heat-grid satellite pass is
  - cloud: cloud cover % (lower = more confident)
  - resolution: spatial resolution of the grid cells
  - forecast_age: age of the cached forecast
  - source_agreement: agreement between satellite heat and forecast

Includes notes explaining data sources (mock vs real, forecast source).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from config import DATA_MODE, PROCESSED_DIR
from data_access import load_json
from forecast import load_forecast

# Manifest city for the Ahmedabad AOI. The optional /health commit field is
# intentionally not populated.
CITY_ID = "ahmedabad"
_PUBLIC_FORECAST_SOURCE = {
    "open-meteo": "live",
    "default-fallback": "default",
    "cache": "cache",
    "stale-cache": "stale-cache",
}


# ---------------------------------------------------------------------------
# Documented placeholders (pending A1 verification of confidence thresholds).
# ---------------------------------------------------------------------------
DATAAGE_NEW_DAYS = 1      # PLACEHOLDER - pending A1 verification
DATAAGE_RECENT_DAYS = 7   # PLACEHOLDER - pending A1 verification
DATAAGE_STALE_DAYS = 30   # PLACEHOLDER - pending A1 verification
DATAAGE_SCORE_NEW = 95    # PLACEHOLDER - pending A1 verification
DATAAGE_SCORE_RECENT = 80 # PLACEHOLDER - pending A1 verification
DATAAGE_SCORE_STALE = 60  # PLACEHOLDER - pending A1 verification
DATAAGE_SCORE_OLD = 40    # PLACEHOLDER - pending A1 verification

CLOUD_LOW_PCT = 5     # PLACEHOLDER - pending A1 verification
CLOUD_MOD_PCT = 15    # PLACEHOLDER - pending A1 verification
CLOUD_HIGH_PCT = 30   # PLACEHOLDER - pending A1 verification
CLOUD_SCORE_LOW = 95  # PLACEHOLDER - pending A1 verification
CLOUD_SCORE_MOD = 80  # PLACEHOLDER - pending A1 verification
CLOUD_SCORE_HIGH = 60 # PLACEHOLDER - pending A1 verification
CLOUD_SCORE_VHIGH = 40# PLACEHOLDER - pending A1 verification

RESOLUTION_MANY_CELLS = 20  # PLACEHOLDER - pending A1 verification
RESOLUTION_SOME_CELLS = 10  # PLACEHOLDER - pending A1 verification
RESOLUTION_SCORE_MANY = 70  # PLACEHOLDER - pending A1 verification
RESOLUTION_SCORE_SOME = 60  # PLACEHOLDER - pending A1 verification
RESOLUTION_SCORE_FEW = 50   # PLACEHOLDER - pending A1 verification

FORECAGE_FRESH_HOURS = 6    # PLACEHOLDER - pending A1 verification
FORECAGE_RECENT_HOURS = 24  # PLACEHOLDER - pending A1 verification
FORECAGE_STALE_HOURS = 48   # PLACEHOLDER - pending A1 verification
FORECAGE_SCORE_FRESH = 90   # PLACEHOLDER - pending A1 verification
FORECAGE_SCORE_RECENT = 70  # PLACEHOLDER - pending A1 verification
FORECAGE_SCORE_STALE = 50   # PLACEHOLDER - pending A1 verification
FORECAGE_SCORE_OLD = 30     # PLACEHOLDER - pending A1 verification

TEMP_NORM_MIN_C = 30.0  # PLACEHOLDER - pending A1 verification
TEMP_NORM_RANGE_C = 15.0  # PLACEHOLDER - pending A1 verification
AGREE_DIFF_CLOSE = 10   # PLACEHOLDER - pending A1 verification
AGREE_DIFF_MODERATE = 25  # PLACEHOLDER - pending A1 verification
AGREE_SCORE_CLOSE = 85  # PLACEHOLDER - pending A1 verification
AGREE_SCORE_MODERATE = 65 # PLACEHOLDER - pending A1 verification
AGREE_SCORE_FAR = 45    # PLACEHOLDER - pending A1 verification


def _parse_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _data_age_score(heat_grid: dict) -> int:
    features = heat_grid.get("features", [])
    dates = []
    for f in features:
        acquired = f.get("properties", {}).get("acquired_on")
        if acquired:
            dt = _parse_date(acquired)
            if dt:
                dates.append(dt)
    if not dates:
        return DATAAGE_SCORE_OLD
    newest = max(dates)
    age_days = (datetime.now(timezone.utc) - newest).days
    if age_days <= DATAAGE_NEW_DAYS:
        return DATAAGE_SCORE_NEW
    if age_days <= DATAAGE_RECENT_DAYS:
        return DATAAGE_SCORE_RECENT
    if age_days <= DATAAGE_STALE_DAYS:
        return DATAAGE_SCORE_STALE
    return DATAAGE_SCORE_OLD


def _cloud_score(heat_grid: dict) -> int:
    features = heat_grid.get("features", [])
    clouds = [f.get("properties", {}).get("cloud_pct") for f in features]
    clouds = [c for c in clouds if c is not None]
    if not clouds:
        return CLOUD_SCORE_VHIGH
    avg_cloud = sum(clouds) / len(clouds)
    if avg_cloud <= CLOUD_LOW_PCT:
        return CLOUD_SCORE_LOW
    if avg_cloud <= CLOUD_MOD_PCT:
        return CLOUD_SCORE_MOD
    if avg_cloud <= CLOUD_HIGH_PCT:
        return CLOUD_SCORE_HIGH
    return CLOUD_SCORE_VHIGH


def _resolution_score(heat_grid: dict) -> int:
    features = heat_grid.get("features", [])
    count = len(features)
    if count >= RESOLUTION_MANY_CELLS:
        return RESOLUTION_SCORE_MANY
    if count >= RESOLUTION_SOME_CELLS:
        return RESOLUTION_SCORE_SOME
    return RESOLUTION_SCORE_FEW


def _forecast_age_score(forecast: dict, source_label: str) -> int:
    cached_at = forecast.get("_cached_at")
    if source_label in ("default-fallback", "stale-cache"):
        return FORECAGE_SCORE_OLD
    if not cached_at:
        return FORECAGE_SCORE_STALE
    try:
        cached = datetime.fromisoformat(cached_at)
    except (ValueError, TypeError):
        return FORECAGE_SCORE_STALE
    age_hours = (datetime.now(timezone.utc) - cached).total_seconds() / 3600
    if age_hours <= FORECAGE_FRESH_HOURS:
        return FORECAGE_SCORE_FRESH
    if age_hours <= FORECAGE_RECENT_HOURS:
        return FORECAGE_SCORE_RECENT
    if age_hours <= FORECAGE_STALE_HOURS:
        return FORECAGE_SCORE_STALE
    return FORECAGE_SCORE_OLD
def _source_agreement_score(heat_grid: dict, forecast: dict) -> int:
    features = heat_grid.get("features", [])
    heat_indices = [
        f.get("properties", {}).get("heat_index_0_100")
        for f in features
        if f.get("properties", {}).get("heat_index_0_100") is not None
    ]
    if not heat_indices:
        return AGREE_SCORE_FAR
    mean_hi = sum(heat_indices) / len(heat_indices)

    hourly = forecast.get("hourly", {})
    temps = hourly.get("temperature_2m", [])
    if not temps:
        return AGREE_SCORE_FAR
    max_temp = max(temps)
    temp_norm = max(0, min(100, (max_temp - TEMP_NORM_MIN_C) / TEMP_NORM_RANGE_C * 100.0))
    diff = abs(mean_hi - temp_norm)
    if diff <= AGREE_DIFF_CLOSE:
        return AGREE_SCORE_CLOSE
    if diff <= AGREE_DIFF_MODERATE:
        return AGREE_SCORE_MODERATE
    return AGREE_SCORE_FAR


def confidence(heat_grid_source: str, forecast_source: str) -> dict:
    heat_grid, _ = load_json("heat_grid.geojson")
    forecast, _ = load_forecast()
    features = heat_grid.get("features", [])

    components = {
        "data_age": _data_age_score(heat_grid),
        "cloud": _cloud_score(heat_grid),
        "resolution": _resolution_score(heat_grid),
        "forecast_age": _forecast_age_score(forecast, forecast_source),
        "source_agreement": _source_agreement_score(heat_grid, forecast),
    }
    overall = round(sum(components.values()) / len(components))

    notes: list[str] = []
    hg_label = "mock data" if heat_grid_source == "mock" else "A1 processed data"
    notes.append(f"Heat grid from {hg_label}; latest satellite pass used.")
    clouds = [f.get("properties", {}).get("cloud_pct") for f in features if f.get("properties", {}).get("cloud_pct") is not None]
    if clouds:
        avg_cloud = round(sum(clouds) / len(clouds))
        notes.append(f"Average cloud cover {avg_cloud}% across grid cells.")
    if forecast_source == "default-fallback":
        notes.append("Forecast from safe default (Open-Meteo unavailable); forecast_age reduced.")
    elif forecast_source == "stale-cache":
        notes.append("Forecast served from stale cache (live fetch failed); forecast_age reduced.")
    elif forecast_source == "open-meteo":
        notes.append("Forecast freshly fetched from Open-Meteo and cached.")
    elif forecast_source == "cache":
        notes.append("Forecast served from local cache (engine/cache/forecast.json).")
    # Report the ACTUAL source used (falls back to mocks when real data missing).
    if DATA_MODE == "real":
        if heat_grid_source == "mock":
            notes.append("DATA_MODE=real requested but data/processed/ missing; serving mocks (source labeled 'mock').")
        else:
            notes.append("DATA_MODE=real: serving A1 processed pipeline data.")
    else:
        notes.append("DATA_MODE=mock: all values are estimates from static mocks.")

    return {
        "overall_0_100": overall,
        "components": components,
        "notes": notes,
    }


def data_as_of(heat_grid: dict | None = None) -> str | None:
    """Satellite date: manifest acquired_on if that file exists, else the
    loaded heat grid's acquired_on, else null.

    A present manifest is authoritative even when acquired_on is null.
    """
    manifest_path = PROCESSED_DIR / CITY_ID / "manifest.json"
    if manifest_path.is_file():
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError):
            manifest = None
        if isinstance(manifest, dict):
            acquired = manifest.get("acquired_on")
            return acquired if isinstance(acquired, str) and acquired else None

    if heat_grid is None:
        try:
            heat_grid, _ = load_json("heat_grid.geojson")
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            return None
    for feature in heat_grid.get("features", []):
        acquired = feature.get("properties", {}).get("acquired_on")
        if isinstance(acquired, str) and acquired:
            return acquired
    return None


def public_forecast_source(source_label: str) -> str | None:
    """Map internal forecast labels to the /confidence enum.

    open-meteo -> live and default-fallback -> default. Other labels pass
    through. This is not applied inside load_forecast.
    """
    return _PUBLIC_FORECAST_SOURCE.get(source_label)


def forecast_as_of(forecast: dict, source_label: str) -> str | None:
    """UTC time the forecast was originally fetched, or null if unknown.

    Uses the stored _cached_at value. Does not stamp the current time.
    The synthetic default forecast was never fetched, so its time is null.
    """
    if source_label == "default-fallback":
        return None
    raw = forecast.get("_cached_at")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc).replace(microsecond=0)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
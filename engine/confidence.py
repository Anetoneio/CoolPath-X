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

from datetime import datetime, timezone
from typing import Tuple

import yaml

from config import DATA_MODE, POLICY_FILE
from data_access import load_json
from forecast import load_forecast


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
        return 40
    newest = max(dates)
    age_days = (datetime.now(timezone.utc) - newest).days
    if age_days <= 1:
        return 95
    if age_days <= 7:
        return 80
    if age_days <= 30:
        return 60
    return 40


def _cloud_score(heat_grid: dict) -> int:
    features = heat_grid.get("features", [])
    clouds = [f.get("properties", {}).get("cloud_pct") for f in features]
    clouds = [c for c in clouds if c is not None]
    if not clouds:
        return 50
    avg_cloud = sum(clouds) / len(clouds)
    if avg_cloud <= 5:
        return 95
    if avg_cloud <= 15:
        return 80
    if avg_cloud <= 30:
        return 60
    return 40


def _resolution_score(heat_grid: dict) -> int:
    features = heat_grid.get("features", [])
    count = len(features)
    if count >= 20:
        return 70
    if count >= 10:
        return 60
    return 50


def _forecast_age_score(forecast: dict, source_label: str) -> int:
    cached_at = forecast.get("_cached_at")
    if source_label == "default-fallback":
        return 30
    if not cached_at:
        return 50
    try:
        cached = datetime.fromisoformat(cached_at)
    except (ValueError, TypeError):
        return 50
    age_hours = (datetime.now(timezone.utc) - cached).total_seconds() / 3600
    if age_hours <= 6:
        return 90
    if age_hours <= 24:
        return 70
    if age_hours <= 48:
        return 50
    return 30
def _source_agreement_score(heat_grid: dict, forecast: dict) -> int:
    features = heat_grid.get("features", [])
    heat_indices = [
        f.get("properties", {}).get("heat_index_0_100")
        for f in features
        if f.get("properties", {}).get("heat_index_0_100") is not None
    ]
    if not heat_indices:
        return 50
    mean_hi = sum(heat_indices) / len(heat_indices)

    hourly = forecast.get("hourly", {})
    temps = hourly.get("temperature_2m", [])
    if not temps:
        return 50
    max_temp = max(temps)
    temp_norm = max(0, min(100, (max_temp - 30) / 15.0 * 100.0))
    diff = abs(mean_hi - temp_norm)
    if diff <= 10:
        return 85
    if diff <= 25:
        return 65
    return 45


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
    elif forecast_source == "open-meteo":
        notes.append("Forecast freshly fetched from Open-Meteo and cached.")
    elif forecast_source == "cache":
        notes.append("Forecast served from local cache (engine/cache/forecast.json).")
    if DATA_MODE == "mock":
        notes.append("DATA_MODE=mock: all values are estimates from static mocks.")
    else:
        notes.append("DATA_MODE=real: values from A1 processed data where available.")

    return {
        "overall_0_100": overall,
        "components": components,
        "notes": notes,
    }
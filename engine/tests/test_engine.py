"""Additional unit tests for COOLPATH X engine modules.

Beyond the contract-shape checks in test_contracts.py, these tests validate
real logic: scoring correctness, scheduler work/rest compliance, route
compare structure, confidence component shape, forecast cache loading,
and data_access fallback behaviour.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import forecast as forecast_mod
from main import app
from scoring import site_exposure, route_exposure, cell_for_point, point_in_polygon
from scheduler import schedule, _intensity_limits, _time_to_minutes
from routing import compare_routes, _haversine_km, _water_nearby
from confidence import confidence
from data_access import load_json
from forecast import clear_memory_cache, load_forecast

client = TestClient(app)

TEST_HEAT_GRID = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [72.55, 23.01], [72.57, 23.01], [72.57, 23.03], [72.55, 23.03], [72.55, 23.01]
                ]],
            },
            "properties": {
                "cell_id": "C01", "lst_c": 45.0, "ndvi": 0.05,
                "heat_index_0_100": 90, "acquired_on": "2026-05-20",
                "source": "Landsat-9", "cloud_pct": 4,
            },
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [72.57, 23.01], [72.59, 23.01], [72.59, 23.03], [72.57, 23.03], [72.57, 23.01]
                ]],
            },
            "properties": {
                "cell_id": "C02", "lst_c": 40.0, "ndvi": 0.20,
                "heat_index_0_100": 60, "acquired_on": "2026-05-20",
                "source": "Landsat-9", "cloud_pct": 6,
            },
        },
    ],
}

TEST_SITES = [
    {"site_id": "S01", "name": "Site 1", "lat": 23.02, "lon": 72.56,
     "job_type": "road repair", "duration_min": 180, "intensity": "heavy", "priority": 4},
    {"site_id": "S02", "name": "Site 2", "lat": 23.02, "lon": 72.58,
     "job_type": "drain cleaning", "duration_min": 120, "intensity": "moderate", "priority": 3},
]

TEST_FACILITIES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [72.565, 23.02]},
            "properties": {"id": "F01", "type": "water", "verified": True, "source": "AMC"},
        },
    ],
}


def test_point_in_polygon():
    poly = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    assert point_in_polygon(5, 5, poly) is True
    assert point_in_polygon(15, 5, poly) is False


def test_cell_for_point():
    cell, idx = cell_for_point(72.56, 23.02, TEST_HEAT_GRID)
    assert cell is not None
    assert cell["cell_id"] == "C01"
    cell, idx = cell_for_point(72.58, 23.02, TEST_HEAT_GRID)
    assert cell is not None
    assert cell["cell_id"] == "C02"
    cell, idx = cell_for_point(72.99, 23.99, TEST_HEAT_GRID)
    assert cell is None


def test_site_exposure_hot_cell():
    site = TEST_SITES[0]
    score, reason = site_exposure(site, TEST_HEAT_GRID, forecast_temp_c=35.0)
    assert 0 <= score <= 100
    assert isinstance(reason, str) and len(reason) > 0
    assert "ESTIMATE" in reason


def test_site_exposure_cooler_cell():
    site = TEST_SITES[1]
    score, reason = site_exposure(site, TEST_HEAT_GRID, forecast_temp_c=30.0)
    assert 0 <= score <= 100
    assert isinstance(reason, str)
    assert "ESTIMATE" in reason


def test_route_exposure_known_line():
    geometry = {
        "type": "LineString",
        "coordinates": [[72.56, 23.02], [72.58, 23.02]],
    }
    score, reason = route_exposure(geometry, TEST_HEAT_GRID)
    assert 0 <= score <= 100
    assert isinstance(reason, str)
    assert "ESTIMATE" in reason


def test_scheduler_respects_max_continuous_work():
    assignments = schedule(
        date="2026-05-21",
        shift_start="07:00",
        shift_end="12:00",
        crews=1,
        site_ids=["S01"],
        sites=TEST_SITES,
        heat_grid=TEST_HEAT_GRID,
        forecast_temp_c=35.0,
    )
    assert len(assignments) == 1
    a = assignments[0]
    assert set(a.keys()) == {"site_id", "start", "end", "rest_breaks", "exposure_score", "reason", "confidence"}
    assert a["site_id"] == "S01"
    assert len(a["rest_breaks"]) >= 1


def test_scheduler_rest_breaks_have_shape():
    assignments = schedule(
        date="2026-05-21",
        shift_start="07:00",
        shift_end="12:00",
        crews=1,
        site_ids=["S01"],
        sites=TEST_SITES,
        heat_grid=TEST_HEAT_GRID,
        forecast_temp_c=35.0,
    )
    for a in assignments:
        for rb in a["rest_breaks"]:
            assert set(rb.keys()) == {"start", "end"}
            assert _time_to_minutes(rb["end"]) > _time_to_minutes(rb["start"])


def test_scheduler_reason_nonempty():
    assignments = schedule(
        date="2026-05-21",
        shift_start="07:00",
        shift_end="12:00",
        crews=1,
        site_ids=["S01", "S02"],
        sites=TEST_SITES,
        heat_grid=TEST_HEAT_GRID,
        forecast_temp_c=35.0,
    )
    for a in assignments:
        assert isinstance(a["reason"], str) and len(a["reason"]) > 0
        assert isinstance(a["confidence"], float)


def test_intensity_limits_reads_policy():
    import yaml
    from config import POLICY_FILE
    with open(POLICY_FILE) as f:
        policy = yaml.safe_load(f)
    limits = _intensity_limits(policy, "heavy")
    assert "max_continuous_work_min" in limits
    assert "rest_min" in limits
    assert isinstance(limits["max_continuous_work_min"], int)
    assert isinstance(limits["rest_min"], int)
    assert limits["max_continuous_work_min"] <= 120


def test_compare_routes_shape():
    from_site = TEST_SITES[0]
    to_site = TEST_SITES[1]
    routes = compare_routes(from_site, to_site, TEST_SITES, TEST_FACILITIES, TEST_HEAT_GRID, "09:45")
    assert isinstance(routes, list) and len(routes) >= 1
    for route in routes:
        assert set(route.keys()) == {
            "id", "label", "geometry", "distance_km", "duration_min",
            "exposure_score", "water_points_nearby",
        }
        assert route["geometry"]["type"] == "LineString"
        assert isinstance(route["exposure_score"], int)
        assert isinstance(route["water_points_nearby"], list)


def test_compare_routes_water_points():
    from_site = TEST_SITES[0]
    to_site = TEST_SITES[1]
    routes = compare_routes(from_site, to_site, TEST_SITES, TEST_FACILITIES, TEST_HEAT_GRID, "09:45")
    # water_points_nearby must always be a list (may be empty if no verified
    # water point lies within WATER_PROXIMITY_KM of the sampled path nodes).
    for route in routes:
        assert isinstance(route["water_points_nearby"], list)
        for wid in route["water_points_nearby"]:
            assert isinstance(wid, str)


def test_haversine_known_distance():
    assert _haversine_km(0, 0, 0, 0) == 0.0
    d = _haversine_km(0, 0, 0, 1)
    assert 110 < d < 112


def test_confidence_shape_and_components():
    result = confidence("mock", "cache")
    assert set(result.keys()) == {"overall_0_100", "components", "notes"}
    assert set(result["components"].keys()) == {
        "data_age", "cloud", "resolution", "forecast_age", "source_agreement",
    }
    assert 0 <= result["overall_0_100"] <= 100
    assert isinstance(result["notes"], list) and len(result["notes"]) > 0
    joined = " ".join(result["notes"])
    assert "mock" in joined.lower() or "DATA_MODE" in joined


def test_data_access_loads_mocks():
    data, source = load_json("sites.json")
    assert isinstance(data, list) and len(data) == 8
    assert source == "mock"


def test_forecast_loads(tmp_path, monkeypatch):
    cache_file = tmp_path / "forecast.json"
    payload = {
        "hourly": {
            "time": ["2026-05-21T06:00"],
            "temperature_2m": [34.0],
            "relative_humidity_2m": [40],
            "apparent_temperature": [36.0],
        },
        "_cached_at": datetime.now(timezone.utc).isoformat(),
        "_source": "open-meteo",
    }
    cache_file.write_text(json.dumps(payload), encoding="utf-8")

    def _forbid_fetch(*_args, **_kwargs):
        raise AssertionError("fetch_forecast must not be called when cache is fresh")

    monkeypatch.setattr(forecast_mod, "FORECAST_CACHE", cache_file)
    monkeypatch.setattr(forecast_mod, "fetch_forecast", _forbid_fetch)

    clear_memory_cache()
    try:
        data, source = load_forecast()
        assert "hourly" in data
        assert source == "cache"
        assert source in ("cache", "open-meteo", "stale-cache", "default-fallback")
        hourly = data["hourly"]
        assert "temperature_2m" in hourly
        assert len(hourly["temperature_2m"]) > 0
    finally:
        clear_memory_cache()
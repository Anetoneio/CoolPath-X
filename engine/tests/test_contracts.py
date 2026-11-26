"""Contract validation tests for the COOLPATH X engine.

Hits each endpoint via TestClient and asserts the response keys/shape match
contracts/api.md (and the matching JSON Schema files in /contracts).
"""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

SITE_KEYS = {"site_id", "name", "lat", "lon", "job_type", "duration_min", "intensity", "priority"}
FACILITY_PROP_KEYS = {"id", "type", "verified", "source"}
HEAT_PROP_KEYS = {"cell_id", "lst_c", "ndvi", "heat_index_0_100", "acquired_on", "source", "cloud_pct"}
ASSIGNMENT_KEYS = {"site_id", "start", "end", "rest_breaks", "exposure_score", "reason", "confidence"}
ROUTE_KEYS = {"id", "label", "geometry", "distance_km", "duration_min", "exposure_score", "water_points_nearby"}


def test_get_sites():
    r = client.get("/sites")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 8
    for s in data:
        assert set(s.keys()) == SITE_KEYS, s.keys()
        assert s["intensity"] in ("light", "moderate", "heavy")
        assert 1 <= s["priority"] <= 5


def test_get_facilities():
    r = client.get("/facilities")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 10
    for f in data["features"]:
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "Point"
        assert set(f["properties"].keys()) == FACILITY_PROP_KEYS
        assert f["properties"]["type"] in ("water", "shade")


def test_get_heat_grid():
    r = client.get("/heat-grid")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 20
    for f in data["features"]:
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "Polygon"
        assert set(f["properties"].keys()) == HEAT_PROP_KEYS
        assert 0 <= f["properties"]["heat_index_0_100"] <= 100


def test_get_confidence():
    r = client.get("/confidence")
    assert r.status_code == 200
    data = r.json()
    required = {"overall_0_100", "components", "notes"}
    optional = {"data_as_of", "forecast_source", "forecast_as_of"}
    assert required.issubset(data.keys())
    assert set(data.keys()) <= required | optional
    assert data.get("data_as_of") is None or isinstance(data.get("data_as_of"), str)
    assert data.get("forecast_source") in (None, "live", "cache", "stale-cache", "default")
    assert data.get("forecast_as_of") is None or isinstance(data.get("forecast_as_of"), str)
    assert set(data["components"].keys()) == {"data_age", "cloud", "resolution", "forecast_age", "source_agreement"}
    assert isinstance(data["notes"], list)


def test_post_schedule():
    r = client.post("/schedule", json={
        "date": "2026-05-21", "shift_start": "07:00", "shift_end": "12:00",
        "crews": 2, "site_ids": ["S01", "S02"],
    })
    assert r.status_code == 200
    data = r.json()
    assert "assignments" in data and isinstance(data["assignments"], list)
    for a in data["assignments"]:
        assert set(a.keys()) == ASSIGNMENT_KEYS, a.keys()
        assert isinstance(a["reason"], str) and len(a["reason"]) > 0


def test_post_route_compare():
    r = client.post("/route/compare", json={
        "from_site": "S01", "to_site": "S02", "depart_time": "09:45",
    })
    assert r.status_code == 200
    data = r.json()
    assert "routes" in data and isinstance(data["routes"], list)
    for route in data["routes"]:
        assert set(route.keys()) == ROUTE_KEYS, route.keys()
        assert route["geometry"]["type"] == "LineString"


def test_post_simulate():
    r = client.post("/simulate", json={
        "config_a": {"date": "2026-05-21", "shift_start": "07:00", "shift_end": "12:00", "crews": 2, "site_ids": ["S01"]},
        "config_b": {"date": "2026-05-21", "shift_start": "06:00", "shift_end": "11:00", "crews": 2, "site_ids": ["S01"]},
    })
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"a", "b", "summary"}
    for cfg in ("a", "b"):
        assert set(data[cfg].keys()) == {"total_exposure", "finish_time", "rest_compliant"}
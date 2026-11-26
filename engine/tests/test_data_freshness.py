"""Data freshness: in-memory forecast TTL, fallbacks, manifest, /confidence fields."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import forecast
from confidence import data_as_of, forecast_as_of, public_forecast_source
from forecast import clear_memory_cache, load_forecast
from main import app

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _reset_forecast_memory():
    clear_memory_cache()
    yield
    clear_memory_cache()


def _hourly(temp: float, cached_at: str) -> dict:
    return {
        "hourly": {
            "time": ["2026-05-21T06:00"],
            "temperature_2m": [temp],
            "relative_humidity_2m": [40],
            "apparent_temperature": [temp],
        },
        "_cached_at": cached_at,
        "_source": "open-meteo",
    }


def test_memory_cache_hit_within_ttl(monkeypatch):
    sentinel = _hourly(11.0, "2026-05-21T01:00:00+00:00")
    forecast._memory_cache = {
        "path": str(forecast.FORECAST_CACHE),
        "stored_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "data": sentinel,
        "source": "cache",
    }

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("disk and live fetch must not run inside the TTL")

    monkeypatch.setattr(forecast, "fetch_forecast", _forbidden)
    data, source = load_forecast()
    assert data is sentinel
    assert source == "cache"


def test_memory_cache_expires_after_three_hours(tmp_path, monkeypatch):
    cache_file = tmp_path / "forecast.json"
    fresh_at = datetime.now(timezone.utc).isoformat()
    disk = _hourly(22.0, fresh_at)
    cache_file.write_text(json.dumps(disk), encoding="utf-8")
    monkeypatch.setattr(forecast, "FORECAST_CACHE", cache_file)
    forecast._memory_cache = {
        "path": str(cache_file),
        "stored_at": datetime.now(timezone.utc) - timedelta(hours=3, minutes=1),
        "data": _hourly(1.0, "2020-01-01T00:00:00+00:00"),
        "source": "open-meteo",
    }
    monkeypatch.setattr(
        forecast, "fetch_forecast", lambda: (_ for _ in ()).throw(AssertionError("live"))
    )

    data, source = load_forecast()
    assert source == "cache"
    assert data["hourly"]["temperature_2m"] == [22.0]


def test_live_failure_falls_back_to_disk_cache(tmp_path, monkeypatch):
    stale_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    disk = _hourly(33.0, stale_at)
    cache_file = tmp_path / "forecast.json"
    cache_file.write_text(json.dumps(disk), encoding="utf-8")
    monkeypatch.setattr(forecast, "FORECAST_CACHE", cache_file)
    monkeypatch.setattr(
        forecast, "fetch_forecast", lambda: (_ for _ in ()).throw(RuntimeError("down"))
    )

    data, source = load_forecast()
    assert source == "stale-cache"
    assert data["hourly"]["temperature_2m"] == [33.0]
    assert cache_file.is_file()


def test_stale_cache_label_stays_internal(tmp_path, monkeypatch):
    stale_at = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    cache_file = tmp_path / "forecast.json"
    cache_file.write_text(json.dumps(_hourly(31.0, stale_at)), encoding="utf-8")
    monkeypatch.setattr(forecast, "FORECAST_CACHE", cache_file)
    monkeypatch.setattr(
        forecast, "fetch_forecast", lambda: (_ for _ in ()).throw(RuntimeError("down"))
    )
    _data, source = load_forecast()
    assert source == "stale-cache"
    assert public_forecast_source(source) == "stale-cache"


def test_default_when_disk_and_live_fail(tmp_path, monkeypatch):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(forecast, "FORECAST_CACHE", missing)
    monkeypatch.setattr(
        forecast, "fetch_forecast", lambda: (_ for _ in ()).throw(RuntimeError("down"))
    )
    data, source = load_forecast()
    assert source == "default-fallback"
    assert public_forecast_source(source) == "default"
    assert data["_source"] == "default-fallback"
    assert forecast_as_of(data, source) is None
    assert not missing.exists()


def test_live_fetch_keeps_open_meteo_label_and_does_not_write(tmp_path, monkeypatch):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(forecast, "FORECAST_CACHE", missing)
    calls = {"n": 0}

    def _fetch():
        calls["n"] += 1
        return _hourly(28.0, "2026-05-21T01:00:00+00:00")

    monkeypatch.setattr(forecast, "fetch_forecast", _fetch)
    _data, source = load_forecast()
    again, source_again = load_forecast()
    assert source == "open-meteo"
    assert source_again == "open-meteo"
    assert public_forecast_source(source) == "live"
    assert calls["n"] == 1
    assert again["hourly"]["temperature_2m"] == [28.0]
    assert not missing.exists()


def test_manifest_matches_heat_grid_including_nulls():
    manifest = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "ahmedabad" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    grid = json.loads(
        (PROJECT_ROOT / "data" / "processed" / "heat_grid.geojson").read_text(encoding="utf-8")
    )
    props = [feature["properties"] for feature in grid["features"]]
    assert len(props) == 528
    assert manifest["city"] == "ahmedabad"
    assert manifest["source"] == "Landsat-8"
    assert manifest["acquired_on"] == "2026-05-15"
    assert manifest["cloud_pct"] == 0
    assert manifest["scene_id"] is None
    assert all(item["source"] == manifest["source"] for item in props)
    assert all(item["acquired_on"] == manifest["acquired_on"] for item in props)
    assert all(item["cloud_pct"] == manifest["cloud_pct"] for item in props)
    assert all("scene_id" not in item for item in props)


def test_manifest_null_acquired_on_does_not_fall_through(tmp_path, monkeypatch):
    city = tmp_path / "ahmedabad"
    city.mkdir()
    (city / "manifest.json").write_text(
        json.dumps({"city": "ahmedabad", "acquired_on": None, "scene_id": None}),
        encoding="utf-8",
    )
    monkeypatch.setattr("confidence.PROCESSED_DIR", tmp_path)
    grid = {"features": [{"properties": {"acquired_on": "2026-05-20"}}]}
    assert data_as_of(grid) is None


def test_data_as_of_uses_heat_grid_when_manifest_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("confidence.PROCESSED_DIR", tmp_path)
    grid = {"features": [{"properties": {"acquired_on": "2026-05-20"}}]}
    assert data_as_of(grid) == "2026-05-20"
    assert data_as_of({"features": []}) is None


def test_confidence_response_fields_are_str_or_null(monkeypatch):
    payload = _hourly(30.0, "2026-05-21T06:00:00+00:00")
    monkeypatch.setattr("main.load_forecast", lambda: (payload, "open-meteo"))
    body = client.get("/confidence").json()
    assert isinstance(body["data_as_of"], str) or body["data_as_of"] is None
    assert body["forecast_source"] == "live"
    assert body["forecast_as_of"] == "2026-05-21T06:00:00Z"
    assert set(body["components"].keys()) == {
        "data_age", "cloud", "resolution", "forecast_age", "source_agreement",
    }


def test_confidence_default_forecast_as_of_is_null(monkeypatch):
    payload = _hourly(35.0, datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr("main.load_forecast", lambda: (payload, "default-fallback"))
    body = client.get("/confidence").json()
    assert body["forecast_source"] == "default"
    assert body["forecast_as_of"] is None
    assert isinstance(body["data_as_of"], str) or body["data_as_of"] is None


def test_health_data_as_of_without_commit():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "commit" not in body
    assert body["data_as_of"] == {"ahmedabad": "2026-05-15"}

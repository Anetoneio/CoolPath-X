"""Test stale forecast fallback and confidence degradation."""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from confidence import confidence, FORECAGE_SCORE_OLD, FORECAGE_SCORE_FRESH
from forecast import load_forecast


def test_stale_cache_fallback_and_confidence_penalty(tmp_path):
    stale_file = tmp_path / "forecast.json"
    stale_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    stale_data = {
        "hourly": {
            "time": [stale_time],
            "temperature_2m": [38.0],
            "relative_humidity_2m": [45],
            "apparent_temperature": [42.0],
        },
        "_cached_at": stale_time,
        "_source": "open-meteo",
    }
    with stale_file.open("w", encoding="utf-8") as f:
        json.dump(stale_data, f)

    # 1. When cache is stale and live fetch raises, load_forecast returns ("stale-cache")
    with patch("forecast.FORECAST_CACHE", stale_file), \
         patch("forecast.fetch_forecast", side_effect=Exception("Network down")):

        data, source_label = load_forecast()
        assert source_label == "stale-cache"
        assert data == stale_data

    # 2. Test confidence degradation
    res_stale = confidence(heat_grid_source="mock", forecast_source="stale-cache")
    assert res_stale["components"]["forecast_age"] == FORECAGE_SCORE_OLD
    assert any("Forecast served from stale cache" in note for note in res_stale["notes"])

    # Verify that fresh cache produces higher forecast_age score
    fresh_time = datetime.now(timezone.utc).isoformat()
    fresh_data = dict(stale_data, _cached_at=fresh_time)
    with patch("confidence.load_forecast", return_value=(fresh_data, "cache")):
        res_fresh = confidence(heat_grid_source="mock", forecast_source="cache")
        assert res_fresh["components"]["forecast_age"] == FORECAGE_SCORE_FRESH
        assert res_stale["components"]["forecast_age"] < res_fresh["components"]["forecast_age"]
        assert res_stale["overall_0_100"] < res_fresh["overall_0_100"]

"""ASTRA COOLPATH X engine — FastAPI.

DATA_MODE (env var, default "mock") controls data source:
  - mock  -> read from /mocks (demo-safe, always available)
  - real  -> read from /data/processed (A1 pipeline output)

Every endpoint matches its contract in contracts/api.md. All exposure
values are ESTIMATES and carry a plain-language reason string.

NUMERIC PLACEHOLDERS (pending A1 verification).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import DATA_MODE
from data_access import load_json, load_response
from forecast import load_forecast
from scheduler import schedule as compute_schedule, _time_to_minutes, _add_minutes
from routing import compare_routes
from confidence import confidence, data_as_of, forecast_as_of, public_forecast_source

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="COOLPATH X engine", version="0.2.0")

ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in ALLOWED_ORIGINS_ENV.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def get_health():
    # data_as_of is optional per contracts/api.md. The optional commit field
    # is left out on purpose.
    acquired = data_as_of()
    return JSONResponse(content={
        "status": "ok",
        "data_mode": DATA_MODE,
        "data_as_of": { "ahmedabad": acquired } if acquired else None,
    })


SUMMARY_EXPOSURE_DIFF_PCT = 20  # PLACEHOLDER - pending A1 verification


def _simulate_summary(a: dict, b: dict) -> str:
    ea, eb = a["total_exposure"], b["total_exposure"]
    hi = max(ea, eb)
    if hi <= 0 or ea == eb:
        return "Both options have the same estimated exposure."
    diff_pct = round(abs(ea - eb) / hi * 100)
    if diff_pct < SUMMARY_EXPOSURE_DIFF_PCT:
        return (f"Estimated exposure differs by only {diff_pct}% between "
                f"A and B (below the {SUMMARY_EXPOSURE_DIFF_PCT}% threshold).")
    lower = "A" if ea < eb else "B"
    return f"Option {lower} has about {diff_pct}% lower estimated exposure (estimate)."


def _load(filename: str):
    with (APP_DIR.parent / "mocks" / filename).open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Static data endpoints (DATA_MODE aware).
# ---------------------------------------------------------------------------

@app.get("/sites")
def get_sites():
    data, source = load_json("sites.json")
    return JSONResponse(content=data)


@app.get("/facilities")
def get_facilities():
    data, source = load_json("facilities.geojson")
    return JSONResponse(content=data)


@app.get("/heat-grid")
def get_heat_grid():
    data, source = load_json("heat_grid.geojson")
    return JSONResponse(content=data)


# ---------------------------------------------------------------------------
# GET /confidence — data age, cloud, resolution, forecast age, agreement.
# ---------------------------------------------------------------------------

@app.get("/confidence")
def get_confidence():
    heat_grid, hg_source = load_json("heat_grid.geojson")
    forecast, fc_source = load_forecast()
    result = confidence(hg_source, fc_source)
    # Public labels only. load_forecast still returns open-meteo / default-fallback.
    result["data_as_of"] = data_as_of(heat_grid)
    result["forecast_source"] = public_forecast_source(fc_source)
    result["forecast_as_of"] = forecast_as_of(forecast, fc_source)
    return JSONResponse(content=result)


def _get_forecast_temp_at_hour(forecast: dict, shift_start: str) -> float | None:
    try:
        sh = int(shift_start.split(":")[0])
    except (ValueError, AttributeError):
        sh = 7
    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    for t, temp in zip(times, temps):
        try:
            if int(t[11:13]) == sh:
                return float(temp)
        except (ValueError, IndexError, TypeError):
            continue
    return None


# ---------------------------------------------------------------------------
# POST /schedule — greedy rule-based scheduler.
# ---------------------------------------------------------------------------

@app.post("/schedule")
def post_schedule(payload: dict):
    sites, _ = load_json("sites.json")
    heat_grid, _ = load_json("heat_grid.geojson")
    forecast, _ = load_forecast()

    date = payload.get("date", "")
    shift_start = payload.get("shift_start", "07:00")
    shift_end = payload.get("shift_end", "12:00")
    crews = int(payload.get("crews", 1))
    site_ids = payload.get("site_ids", [])

    forecast_temp_c = _get_forecast_temp_at_hour(forecast, shift_start)

    assignments = compute_schedule(
        date=date,
        shift_start=shift_start,
        shift_end=shift_end,
        crews=crews,
        site_ids=site_ids,
        sites=sites,
        heat_grid=heat_grid,
        forecast_temp_c=forecast_temp_c,
    )
    return JSONResponse(content={"assignments": assignments})


# ---------------------------------------------------------------------------
# POST /route/compare — fastest vs lower-exposure via networkx.
# ---------------------------------------------------------------------------

@app.post("/route/compare")
def post_route_compare(payload: dict):
    sites, _ = load_json("sites.json")
    facilities, _ = load_json("facilities.geojson")
    heat_grid, _ = load_json("heat_grid.geojson")

    from_site_id = payload.get("from_site", "")
    to_site_id = payload.get("to_site", "")
    depart_time = payload.get("depart_time", "09:00")

    site_by_id = {s["site_id"]: s for s in sites}
    from_site = site_by_id.get(from_site_id)
    to_site = site_by_id.get(to_site_id)

    if from_site is None or to_site is None:
        return JSONResponse(content={"routes": []})

    routes = compare_routes(from_site, to_site, sites, facilities, heat_grid, depart_time)
    return JSONResponse(content={"routes": routes})


# ---------------------------------------------------------------------------
# POST /simulate — stretch (mock-served until Hour 6 checkpoint).
# ---------------------------------------------------------------------------

@app.post("/simulate")
def post_simulate(payload: dict):
    sites, _ = load_json("sites.json")
    heat_grid, _ = load_json("heat_grid.geojson")
    forecast, _ = load_forecast()

    def simulate_one(config):
        shift_start = config.get("shift_start", "07:00")
        forecast_temp_c = _get_forecast_temp_at_hour(forecast, shift_start)
        assignments = compute_schedule(
            date=config.get("date", ""),
            shift_start=shift_start,
            shift_end=config.get("shift_end", "12:00"),
            crews=int(config.get("crews", 1)),
            site_ids=config.get("site_ids", []),
            sites=sites,
            heat_grid=heat_grid,
            forecast_temp_c=forecast_temp_c,
        )
        total_exposure = sum(a["exposure_score"] for a in assignments)
        # finish_time: last assignment end time, or shift_end if no assignments
        if assignments:
            all_ends = []
            for a in assignments:
                all_ends.append(_time_to_minutes(a["end"]))
            finish_min = max(all_ends)
        else:
            finish_min = _time_to_minutes("12:00")
        finish_time = _add_minutes("00:00", finish_min)
        rest_compliant = all(
            _time_to_minutes(rb["end"]) <= _time_to_minutes(a["end"])
            for a in assignments
            for rb in a.get("rest_breaks", [])
        )
        return {
            "total_exposure": total_exposure,
            "finish_time": finish_time,
            "rest_compliant": rest_compliant,
        }

    config_a = payload.get("config_a", {})
    config_b = payload.get("config_b", {})
    a = simulate_one(config_a)
    b = simulate_one(config_b)
    summary = _simulate_summary(a, b)
    return JSONResponse(content={"a": a, "b": b, "summary": summary})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
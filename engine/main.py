"""ASTRA COOLPATH X engine — FastAPI.

DATA_MODE (env var, default "mock") controls data source:
  - mock  -> read from /mocks (demo-safe, always available)
  - real  -> read from /data/processed (A1 pipeline output)

Every endpoint matches its contract in contracts/api.md. All exposure
values are ESTIMATES and carry a plain-language reason string.
"""
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import DATA_MODE
from data_access import load_json, load_response
from forecast import load_forecast
from scheduler import schedule as compute_schedule
from routing import compare_routes
from confidence import confidence
from scheduler import schedule as compute_schedule
from routing import compare_routes
from confidence import confidence

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="COOLPATH X engine", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return JSONResponse(content=result)


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

    # Forecast temperature at shift start hour for exposure adjustment.
    try:
        sh = int(shift_start.split(":")[0])
    except (ValueError, AttributeError):
        sh = 7
    forecast_temp_c = None
    hourly = forecast.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    for t, temp in zip(times, temps):
        try:
            if int(t[11:13]) == sh:
                forecast_temp_c = float(temp)
                break
        except (ValueError, IndexError, TypeError):
            continue

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
def post_simulate():
    return JSONResponse(content=load_response("simulate.json"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
"""ASTRA COOLPATH X engine — FastAPI scaffold.

Every endpoint returns its mock response loaded from /mocks. Contract-first:
responses must match contracts/*.json (verified by tests/test_contracts.py).

Exposure values are estimates (see .clinerules rule 5).
"""
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

APP_DIR = Path(__file__).resolve().parent
MOCKS_DIR = APP_DIR.parent / "mocks"
RESPONSES_DIR = MOCKS_DIR / "responses"

app = FastAPI(title="COOLPATH X engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/sites")
def get_sites():
    return JSONResponse(content=_load(MOCKS_DIR / "sites.json"))


@app.get("/facilities")
def get_facilities():
    return JSONResponse(content=_load(MOCKS_DIR / "facilities.geojson"))


@app.get("/heat-grid")
def get_heat_grid():
    return JSONResponse(content=_load(MOCKS_DIR / "heat_grid.geojson"))


@app.get("/confidence")
def get_confidence():
    return JSONResponse(content=_load(RESPONSES_DIR / "confidence.json"))


@app.post("/schedule")
def post_schedule():
    # Request body (date, shift_start, shift_end, crews, site_ids) is accepted
    # but the scaffold returns the static mock response.
    return JSONResponse(content=_load(RESPONSES_DIR / "schedule.json"))


@app.post("/route/compare")
def post_route_compare():
    return JSONResponse(content=_load(RESPONSES_DIR / "route_compare.json"))


@app.post("/simulate")
def post_simulate():
    return JSONResponse(content=_load(RESPONSES_DIR / "simulate.json"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
#!/usr/bin/env python3
"""QA Check: Validate local engine endpoints against API contracts and schemas."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root and engine to path
QA_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = QA_DIR.parent.parent
ENGINE_DIR = PROJECT_ROOT / "engine"
CONTRACTS_DIR = PROJECT_ROOT / "contracts"

sys.path.insert(0, str(ENGINE_DIR))

import httpx

# Try jsonschema if installed
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SITE_REQ_KEYS = {"site_id", "name", "lat", "lon", "job_type", "duration_min", "intensity", "priority"}
FACILITY_REQ_PROPS = {"id", "type", "verified", "source"}
HEAT_REQ_PROPS = {"cell_id", "lst_c", "ndvi", "heat_index_0_100", "acquired_on", "source", "cloud_pct"}
ASSIGNMENT_REQ_KEYS = {"site_id", "start", "end", "rest_breaks", "exposure_score", "reason", "confidence"}
ROUTE_REQ_KEYS = {"id", "label", "geometry", "distance_km", "duration_min", "exposure_score", "water_points_nearby"}


def run_checks(base_url: str | None = None) -> bool:
    data_mode = os.getenv("DATA_MODE", "mock")
    print(f"\n=======================================================")
    print(f" QA CONTRACT CHECK (DATA_MODE={data_mode})")
    print(f"=======================================================")

    client = None
    if base_url:
        print(f"Targeting live server: {base_url}")
        client = httpx.Client(base_url=base_url, timeout=10.0)
    else:
        print("Targeting in-process FastAPI TestClient...")
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app, raise_server_exceptions=False)

    failures = 0

    def check(name, success, msg=""):
        nonlocal failures
        if success:
            print(f" [PASS] {name}{' - ' + msg if msg else ''}")
        else:
            print(f" [FAIL] {name}{' - ' + msg if msg else ''}")
            failures += 1

    # Load schemas
    with open(CONTRACTS_DIR / "sites.schema.json", "r", encoding="utf-8") as f:
        sites_schema = json.load(f)
    with open(CONTRACTS_DIR / "facilities.schema.json", "r", encoding="utf-8") as f:
        fac_schema = json.load(f)
    with open(CONTRACTS_DIR / "heat_grid.schema.json", "r", encoding="utf-8") as f:
        heat_schema = json.load(f)

    # 1. GET /health
    try:
        r = client.get("/health")
        check(
            "GET /health",
            r.status_code == 200 and r.json().get("status") == "ok",
            f"status={r.status_code}, data_mode={r.json().get('data_mode')}"
        )
    except Exception as e:
        check("GET /health", False, f"Exception: {e}")

    # 2. GET /sites
    try:
        r = client.get("/sites")
        data = r.json() if r.status_code == 200 else []
        schema_ok = False
        if r.status_code == 200 and isinstance(data, list) and len(data) > 0:
            if HAS_JSONSCHEMA:
                try:
                    jsonschema.validate(instance=data, schema=sites_schema)
                    schema_ok = True
                except Exception as e:
                    schema_ok = False
            else:
                schema_ok = all(isinstance(s, dict) and SITE_REQ_KEYS.issubset(s.keys()) for s in data)
        check("GET /sites", schema_ok, f"{len(data)} sites")
    except Exception as e:
        check("GET /sites", False, f"Exception: {e}")

    # 3. GET /facilities
    try:
        r = client.get("/facilities")
        fac_data = r.json() if r.status_code == 200 else {}
        fac_ok = r.status_code == 200 and fac_data.get("type") == "FeatureCollection"
        if fac_ok:
            if HAS_JSONSCHEMA:
                try:
                    jsonschema.validate(instance=fac_data, schema=fac_schema)
                except Exception:
                    fac_ok = False
            else:
                features = fac_data.get("features", [])
                fac_ok = len(features) > 0 and all(
                    f.get("type") == "Feature" and FACILITY_REQ_PROPS.issubset((f.get("properties") or {}).keys())
                    for f in features
                )
        check("GET /facilities", fac_ok, f"{len(fac_data.get('features', []))} features")
    except Exception as e:
        check("GET /facilities", False, f"Exception: {e}")

    # 4. GET /heat-grid
    try:
        r = client.get("/heat-grid")
        hg_data = r.json() if r.status_code == 200 else {}
        hg_ok = r.status_code == 200 and hg_data.get("type") == "FeatureCollection"
        if hg_ok:
            if HAS_JSONSCHEMA:
                try:
                    jsonschema.validate(instance=hg_data, schema=heat_schema)
                except Exception:
                    hg_ok = False
            else:
                features = hg_data.get("features", [])
                hg_ok = len(features) > 0 and all(
                    f.get("type") == "Feature" and HEAT_REQ_PROPS.issubset((f.get("properties") or {}).keys())
                    for f in features
                )
        check("GET /heat-grid", hg_ok, f"{len(hg_data.get('features', []))} features")
    except Exception as e:
        check("GET /heat-grid", False, f"Exception: {e}")

    # 5. GET /confidence
    try:
        r = client.get("/confidence")
        conf_data = r.json() if r.status_code == 200 else {}
        conf_ok = r.status_code == 200 and {"overall_0_100", "components", "notes"}.issubset(conf_data.keys())
        check("GET /confidence", conf_ok, f"score={conf_data.get('overall_0_100')}")
    except Exception as e:
        check("GET /confidence", False, f"Exception: {e}")

    # 6. POST /schedule
    try:
        sched_payload = {
            "date": "2026-05-21",
            "shift_start": "07:00",
            "shift_end": "12:00",
            "crews": 2,
            "site_ids": ["S01", "S02"]
        }
        r = client.post("/schedule", json=sched_payload)
        sched_data = r.json() if r.status_code == 200 else {}
        assignments = sched_data.get("assignments", [])
        sched_ok = r.status_code == 200 and isinstance(assignments, list) and len(assignments) > 0
        if sched_ok:
            first = assignments[0]
            sched_ok = ASSIGNMENT_REQ_KEYS.issubset(first.keys())
        check("POST /schedule", sched_ok, f"{len(assignments)} assignments")
    except Exception as e:
        check("POST /schedule", False, f"Exception: {e}")

    # 7. POST /route/compare
    try:
        route_payload = {
            "from_site": "S01",
            "to_site": "S02",
            "depart_time": "09:45"
        }
        r = client.post("/route/compare", json=route_payload)
        route_data = r.json() if r.status_code == 200 else {}
        routes = route_data.get("routes", [])
        route_ok = r.status_code == 200 and isinstance(routes, list) and len(routes) >= 2
        if route_ok:
            route_ok = all(isinstance(rt, dict) and ROUTE_REQ_KEYS.issubset(rt.keys()) for rt in routes)
        check("POST /route/compare", route_ok, f"{len(routes)} routes returned")
    except Exception as e:
        check("POST /route/compare", False, f"Exception: {e}")

    # 8. POST /simulate
    try:
        sim_payload = {
            "config_a": {"shift_start": "07:00", "shift_end": "12:00", "crews": 2, "site_ids": ["S01", "S02"]},
            "config_b": {"shift_start": "06:00", "shift_end": "11:00", "crews": 2, "site_ids": ["S01", "S02"]}
        }
        r = client.post("/simulate", json=sim_payload)
        sim_data = r.json() if r.status_code == 200 else {}
        sim_ok = r.status_code == 200 and "a" in sim_data and "b" in sim_data and "summary" in sim_data
        check("POST /simulate", sim_ok, f"summary={sim_data.get('summary', '')[:40]}...")
    except Exception as e:
        check("POST /simulate", False, f"Exception: {e}")

    if failures > 0:
        print(f"\n[FAIL] {failures} check(s) failed.")
        return False
    print("\n[SUCCESS] All contract checks passed.")
    return True


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_checks(url)
    sys.exit(0 if success else 1)

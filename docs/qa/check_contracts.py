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


def run_checks(base_url: str | None = None):
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
        client = TestClient(app)

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
    r = client.get("/health")
    check(
        "GET /health",
        r.status_code == 200 and r.json().get("status") == "ok",
        f"status={r.status_code}, data_mode={r.json().get('data_mode')}"
    )

    # 2. GET /sites
    r = client.get("/sites")
    sites_ok = r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) > 0
    if HAS_JSONSCHEMA and sites_ok:
        try:
            jsonschema.validate(instance=r.json(), schema=sites_schema)
            schema_ok = True
        except Exception as e:
            schema_ok = False
            print(f"   Schema error: {e}")
    else:
        schema_ok = sites_ok
    check("GET /sites", sites_ok and schema_ok, f"{len(r.json()) if sites_ok else 0} sites")

    # 3. GET /facilities
    r = client.get("/facilities")
    fac_data = r.json() if r.status_code == 200 else {}
    fac_ok = r.status_code == 200 and fac_data.get("type") == "FeatureCollection"
    if HAS_JSONSCHEMA and fac_ok:
        try:
            jsonschema.validate(instance=fac_data, schema=fac_schema)
            fac_schema_ok = True
        except Exception as e:
            fac_schema_ok = False
            print(f"   Schema error: {e}")
    else:
        fac_schema_ok = fac_ok
    check("GET /facilities", fac_ok and fac_schema_ok, f"{len(fac_data.get('features', []))} features")

    # 4. GET /heat-grid
    r = client.get("/heat-grid")
    hg_data = r.json() if r.status_code == 200 else {}
    hg_ok = r.status_code == 200 and hg_data.get("type") == "FeatureCollection"
    if HAS_JSONSCHEMA and hg_ok:
        try:
            jsonschema.validate(instance=hg_data, schema=heat_schema)
            hg_schema_ok = True
        except Exception as e:
            hg_schema_ok = False
            print(f"   Schema error: {e}")
    else:
        hg_schema_ok = hg_ok
    check("GET /heat-grid", hg_ok and hg_schema_ok, f"{len(hg_data.get('features', []))} features")

    # 5. GET /confidence
    r = client.get("/confidence")
    conf_data = r.json() if r.status_code == 200 else {}
    conf_ok = r.status_code == 200 and {"overall_0_100", "components", "notes"}.issubset(conf_data.keys())
    check("GET /confidence", conf_ok, f"score={conf_data.get('overall_0_100')}")

    # 6. POST /schedule
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
        req_keys = {"site_id", "start", "end", "rest_breaks", "exposure_score", "reason", "confidence"}
        sched_ok = req_keys.issubset(first.keys())
    check("POST /schedule", sched_ok, f"{len(assignments)} assignments")

    # 7. POST /route/compare
    route_payload = {
        "from_site": "S01",
        "to_site": "S02",
        "depart_time": "09:45"
    }
    r = client.post("/route/compare", json=route_payload)
    route_data = r.json() if r.status_code == 200 else {}
    routes = route_data.get("routes", [])
    route_ok = r.status_code == 200 and isinstance(routes, list) and len(routes) >= 2
    check("POST /route/compare", route_ok, f"{len(routes)} routes returned")

    # 8. POST /simulate
    sim_payload = {
        "config_a": {"shift_start": "07:00", "shift_end": "12:00", "crews": 2, "site_ids": ["S01", "S02"]},
        "config_b": {"shift_start": "06:00", "shift_end": "11:00", "crews": 2, "site_ids": ["S01", "S02"]}
    }
    r = client.post("/simulate", json=sim_payload)
    sim_data = r.json() if r.status_code == 200 else {}
    sim_ok = r.status_code == 200 and "a" in sim_data and "b" in sim_data and "summary" in sim_data
    check("POST /simulate", sim_ok, f"summary={sim_data.get('summary', '')[:40]}...")

    if failures > 0:
        print(f"\n[FAIL] {failures} check(s) failed.")
        return False
    print("\n[SUCCESS] All contract checks passed.")
    return True


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_checks(url)
    sys.exit(0 if success else 1)

"""Standalone pre-push verification gate for COOLPATH X engine.

Run from engine/:
    python verify.py

Behavior:
  - Parent process runs `python verify.py --child` twice (DATA_MODE=mock and DATA_MODE=real).
  - Then runs `python -m pytest -q`.
  - Prints "READY TO PUSH" (exit 0) or "NOT READY: N failing stage(s)" (exit 1).
"""
from __future__ import annotations

import os
import sys
import subprocess


def run_check(label: str, fn) -> bool:
    try:
        ok, msg = fn()
    except Exception as exc:
        ok, msg = False, f"Exception: {exc}"
    status = "PASS" if ok else "FAIL"
    detail = f" - {msg}" if msg else ""
    print(f"[{status}] {label}{detail}")
    return ok


def run_child():
    from fastapi.testclient import TestClient
    from main import app

    data_mode = os.getenv("DATA_MODE", "mock")
    print(f"\n--- Running child verification (DATA_MODE={data_mode}) ---")
    client = TestClient(app)
    checks: list[bool] = []

    # Check 1: GET /sites returns 200 and non-empty
    def check_sites():
        r = client.get("/sites")
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return False, "empty or invalid list"
        return True, f"{len(data)} sites returned"

    checks.append(run_check("GET /sites returns 200 and non-empty", check_sites))

    # Check 2: GET /facilities returns 200 and non-empty
    def check_facilities():
        r = client.get("/facilities")
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        features = data.get("features", [])
        if not features:
            return False, "features empty"
        return True, f"{len(features)} facilities returned"

    checks.append(run_check("GET /facilities returns 200 and non-empty", check_facilities))

    # Check 3: GET /heat-grid returns 200 and non-empty
    def check_heat_grid():
        r = client.get("/heat-grid")
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        features = data.get("features", [])
        if not features:
            return False, "features empty"
        return True, f"{len(features)} heat grid cells returned"

    checks.append(run_check("GET /heat-grid returns 200 and non-empty", check_heat_grid))

    # Check 4: GET /confidence returns 200 and non-empty
    def check_confidence():
        r = client.get("/confidence")
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        if not data:
            return False, "empty response"
        return True, f"overall_0_100={data.get('overall_0_100')}"

    checks.append(run_check("GET /confidence returns 200 and non-empty", check_confidence))

    # Check 5: /confidence has overall_0_100 and notes that mention the data source (mock/real) and forecast source
    def check_confidence_notes():
        r = client.get("/confidence")
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        if "overall_0_100" not in data:
            return False, "missing overall_0_100 key"
        notes = data.get("notes", [])
        if not isinstance(notes, list) or not notes:
            return False, "missing or empty notes list"
        joined = " ".join(notes).lower()
        has_data_source = ("mock" in joined) or ("real" in joined)
        has_forecast = ("forecast" in joined) or ("open-meteo" in joined) or ("cache" in joined)
        if not has_data_source:
            return False, "notes do not mention data source (mock/real)"
        if not has_forecast:
            return False, "notes do not mention forecast source"
        return True, "overall_0_100 present and notes detail data & forecast source"

    checks.append(run_check("/confidence has overall_0_100 and source notes", check_confidence_notes))

    # Check 6: POST /schedule returns 200 with assignments, each with a non-empty reason and a rest_breaks key
    def check_schedule():
        payload = {
            "date": "2026-05-21",
            "shift_start": "07:00",
            "shift_end": "12:00",
            "crews": 2,
            "site_ids": ["S01", "S02"],
        }
        r = client.post("/schedule", json=payload)
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        assignments = data.get("assignments")
        if not isinstance(assignments, list) or not assignments:
            return False, "assignments empty or missing"
        for a in assignments:
            if not a.get("reason"):
                return False, f"assignment {a.get('site_id')} missing reason"
            if "rest_breaks" not in a:
                return False, f"assignment {a.get('site_id')} missing rest_breaks key"
        return True, f"{len(assignments)} assignments compliant"

    checks.append(run_check("POST /schedule returns 200 with assignments (reason & rest_breaks)", check_schedule))

    # Check 7: POST /schedule with an unknown site id returns no 500
    def check_schedule_unknown_site():
        payload = {
            "date": "2026-05-21",
            "shift_start": "07:00",
            "shift_end": "12:00",
            "crews": 2,
            "site_ids": ["S999_UNKNOWN_SITE"],
        }
        r = client.post("/schedule", json=payload)
        if r.status_code == 500:
            return False, "got 500 internal server error"
        return True, f"status {r.status_code} (no 500)"

    checks.append(run_check("POST /schedule with unknown site id returns no 500", check_schedule_unknown_site))

    # Check 8: POST /route/compare returns 200 with two routes and Route B exposure_score <= Route A exposure_score
    def check_route_compare():
        payload = {
            "from_site": "S01",
            "to_site": "S02",
            "depart_time": "09:45",
        }
        r = client.post("/route/compare", json=payload)
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        routes = data.get("routes")
        if not isinstance(routes, list) or len(routes) != 2:
            return False, f"expected 2 routes, got {len(routes) if isinstance(routes, list) else type(routes)}"
        ra, rb = routes[0], routes[1]
        score_a = ra.get("exposure_score")
        score_b = rb.get("exposure_score")
        if score_a is None or score_b is None:
            return False, "route missing exposure_score"
        if score_b > score_a:
            return False, f"Route B exposure ({score_b}) > Route A exposure ({score_a})"
        return True, f"2 routes returned; Route B ({score_b}) <= Route A ({score_a})"

    checks.append(run_check("POST /route/compare returns 2 routes (Route B <= Route A)", check_route_compare))

    # Check 9: POST /simulate returns 200 with a non-empty string summary
    def check_simulate():
        payload = {
            "config_a": {"date": "2026-05-21", "shift_start": "07:00", "shift_end": "12:00", "crews": 2, "site_ids": ["S01"]},
            "config_b": {"date": "2026-05-21", "shift_start": "06:00", "shift_end": "11:00", "crews": 2, "site_ids": ["S01"]},
        }
        r = client.post("/simulate", json=payload)
        if r.status_code != 200:
            return False, f"status {r.status_code}"
        data = r.json()
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return False, "summary is missing or empty"
        return True, f"summary: {summary}"

    checks.append(run_check("POST /simulate returns 200 with non-empty summary", check_simulate))

    if all(checks):
        print(f"Child checks (DATA_MODE={data_mode}): ALL {len(checks)} PASSED\n")
        sys.exit(0)
    else:
        failed = sum(1 for c in checks if not c)
        print(f"Child checks (DATA_MODE={data_mode}): {failed} FAILED\n")
        sys.exit(1)


def main():
    if "--child" in sys.argv:
        run_child()
        return

    print("========================================")
    print("COOLPATH X Engine Pre-Push Verification")
    print("========================================")
    sys.stdout.flush()

    failing_stages = 0

    # Stage 1: DATA_MODE=mock child run
    env_mock = os.environ.copy()
    env_mock["DATA_MODE"] = "mock"
    res_mock = subprocess.run([sys.executable, "verify.py", "--child"], env=env_mock)
    if res_mock.returncode != 0:
        failing_stages += 1

    # Stage 2: DATA_MODE=real child run
    env_real = os.environ.copy()
    env_real["DATA_MODE"] = "real"
    res_real = subprocess.run([sys.executable, "verify.py", "--child"], env=env_real)
    if res_real.returncode != 0:
        failing_stages += 1

    # Stage 3: pytest suite
    print("--- Running pytest suite ---")
    res_pytest = subprocess.run([sys.executable, "-m", "pytest", "-q"])
    if res_pytest.returncode != 0:
        failing_stages += 1

    print("\n========================================")
    if failing_stages == 0:
        print("READY TO PUSH")
        sys.exit(0)
    else:
        print(f"NOT READY: {failing_stages} failing stage(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()

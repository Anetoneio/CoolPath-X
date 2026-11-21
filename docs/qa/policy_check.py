#!/usr/bin/env python3
"""QA Policy Check: Validate policy.yaml structure and engine adherence to policy rules."""
import os
import sys
from pathlib import Path
import yaml

QA_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = QA_DIR.parent.parent
ENGINE_DIR = PROJECT_ROOT / "engine"
CONTRACTS_DIR = PROJECT_ROOT / "contracts"

sys.path.insert(0, str(ENGINE_DIR))


def run_policy_check():
    data_mode = os.getenv("DATA_MODE", "mock")
    print(f"\n=======================================================")
    print(f" QA POLICY CHECK (DATA_MODE={data_mode})")
    print(f"=======================================================")

    policy_file = CONTRACTS_DIR / "policy.yaml"
    failures = 0

    def check(name, success, msg=""):
        nonlocal failures
        if success:
            print(f" [PASS] {name}{' - ' + msg if msg else ''}")
        else:
            print(f" [FAIL] {name}{' - ' + msg if msg else ''}")
            failures += 1

    # 1. Read policy.yaml
    with open(policy_file, "r", encoding="utf-8") as f:
        policy = yaml.safe_load(f)

    check("policy.yaml exists and parses", isinstance(policy, dict))
    check("policy.yaml contains wbgt_bands", "wbgt_bands" in policy and len(policy["wbgt_bands"]) == 4)
    check("policy.yaml contains intensity_limits", "intensity_limits" in policy and {"light", "moderate", "heavy"}.issubset(policy["intensity_limits"].keys()))

    # 2. Check engine scheduler adherence
    from scheduler import FALLBACK_MAX_WORK_MIN, FALLBACK_REST_MIN
    check(
        "Engine defines fallback work/rest limits",
        {"light", "moderate", "heavy"}.issubset(FALLBACK_MAX_WORK_MIN.keys()) and {"light", "moderate", "heavy"}.issubset(FALLBACK_REST_MIN.keys()),
        f"work={FALLBACK_MAX_WORK_MIN}, rest={FALLBACK_REST_MIN}"
    )

    # 3. Check scheduler reasons & rest compliance
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    r = client.post("/schedule", json={
        "date": "2026-05-21",
        "shift_start": "07:00",
        "shift_end": "12:00",
        "crews": 2,
        "site_ids": ["S01", "S02"]
    })
    sched_ok = r.status_code == 200
    if sched_ok:
        data = r.json()
        assignments = data.get("assignments", [])
        has_reasons = all(len(a.get("reason", "")) > 5 for a in assignments)
        has_rest = all("rest_breaks" in a for a in assignments)
        check("Schedule assignments have plain-language reason strings", has_reasons)
        check("Schedule assignments include rest breaks", has_rest)
    else:
        check("Schedule API response", False, f"status={r.status_code}")

    if failures > 0:
        print(f"\n[FAIL] {failures} policy check(s) failed.")
        return False
    print("\n[SUCCESS] All policy checks passed.")
    return True


if __name__ == "__main__":
    success = run_policy_check()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""QA Policy Check: Validate policy.yaml completeness and engine adherence to policy rules."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
import yaml

QA_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = QA_DIR.parent.parent
ENGINE_DIR = PROJECT_ROOT / "engine"
CONTRACTS_DIR = PROJECT_ROOT / "contracts"

sys.path.insert(0, str(ENGINE_DIR))


def run_policy_check() -> bool:
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

    # 1. Read policy.yaml structure
    with open(policy_file, "r", encoding="utf-8") as f:
        policy_raw = f.read()
        policy = yaml.safe_load(policy_raw)

    check("policy.yaml exists and parses", isinstance(policy, dict))
    check("policy.yaml contains wbgt_bands", "wbgt_bands" in policy and len(policy["wbgt_bands"]) == 4)
    check(
        "policy.yaml contains intensity_limits",
        "intensity_limits" in policy and {"light", "moderate", "heavy"}.issubset(policy["intensity_limits"].keys())
    )

    # 2. Strict check: policy.yaml must NOT contain TODO_VERIFY or TODO
    todo_matches = re.findall(r"\bTODO(?:_VERIFY)?\b", policy_raw)
    if todo_matches:
        check(
            "policy.yaml verified (no TODO/TODO_VERIFY)",
            False,
            f"Found {len(todo_matches)} unverified placeholders: {set(todo_matches)}"
        )
    else:
        check("policy.yaml verified (no TODO/TODO_VERIFY)", True, "All thresholds verified")

    # 3. Check for hardcoded work-rest minutes in engine source code
    hardcoded_findings = []
    for py_file in sorted(ENGINE_DIR.glob("*.py")):
        if py_file.name in ("verify.py", "conftest.py"):
            continue
        code = py_file.read_text(encoding="utf-8")
        # Check for FALLBACK_MAX_WORK_MIN and FALLBACK_REST_MIN
        matches = re.findall(r"(FALLBACK_(?:MAX_WORK|REST)_MIN\s*=\s*\{[^}]+\})", code)
        if matches:
            for m in matches:
                hardcoded_findings.append(f"{py_file.name}: {m.strip()}")
        # Check for default literal numbers in fallback gets
        lit_matches = re.findall(r"FALLBACK_(?:MAX_WORK|REST)_MIN\.get\([^)]+,\s*(\d+)\)", code)
        if lit_matches:
            hardcoded_findings.append(f"{py_file.name}: default literal gets {lit_matches}")

    if hardcoded_findings:
        print("\n[FINDINGS] Hardcoded work-rest values detected in engine source:")
        for finding in hardcoded_findings:
            print(f"  - {finding}")
        check(
            "Engine contains no hardcoded work-rest minutes (Rule 3)",
            False,
            f"{len(hardcoded_findings)} hardcoded work/rest definitions found"
        )
    else:
        check("Engine contains no hardcoded work-rest minutes (Rule 3)", True)

    # 4. Schedule assignments check
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app, raise_server_exceptions=False)
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

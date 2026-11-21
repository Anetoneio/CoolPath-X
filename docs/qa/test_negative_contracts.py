#!/usr/bin/env python3
"""Negative test for contract verification: confirms that broken mocks/responses fail check_contracts."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

QA_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = QA_DIR.parent.parent
ENGINE_DIR = PROJECT_ROOT / "engine"
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(QA_DIR))

from check_contracts import run_checks


def test_negative_broken_mock():
    print("\n--- Running negative contract check test ---")

    # Deliberately corrupt sites response (missing required site_id, negative priority, wrong keys)
    broken_sites = [
        {"invalid_key": "broken", "name": "Broken Site", "priority": -99}
    ]

    # Patch data_access.load_json so that "sites.json" returns the broken data
    import data_access
    original_load_json = data_access.load_json

    def mock_load_json(filename):
        if filename == "sites.json":
            return broken_sites, "broken-mock"
        return original_load_json(filename)

    with patch.object(data_access, "load_json", side_effect=mock_load_json):
        # run_checks should detect schema violation and return False
        success = run_checks()
        assert not success, "Expected check_contracts.run_checks() to FAIL on broken mock data, but it passed!"

    print("\n[PASS] Negative test confirmed: deliberately broken mock correctly failed contract checks.")
    return True


if __name__ == "__main__":
    ok = test_negative_broken_mock()
    sys.exit(0 if ok else 1)

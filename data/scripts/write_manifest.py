#!/usr/bin/env python3
"""write_manifest.py — Seat A1: write data/processed/<city>/manifest.json.

Derives provenance metadata from the actual processed output files:
  - source, acquired_on, cloud_pct from heat grid feature properties
  - scene_id: null if not recorded in feature properties
  - build_time: runtime UTC ISO-8601 timestamp
  - git_commit: runtime Git commit SHA (null if unavailable)
  - files: SHA-256 digests of processed output files

Existing file locations (data/processed/*.geojson, data/processed/roads.graphml)
are preserved. The manifest is written alongside them at:
  data/processed/<city>/manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

TRACKED_FILES = [
    "heat_grid.geojson",
    "facilities.geojson",
    "roads.graphml",
]


def _git_commit() -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=5,
        )
        if res.returncode == 0:
            commit = res.stdout.strip()
            return commit if commit else None
    except Exception:
        pass
    return None


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def derive_manifest(city: str = "ahmedabad", processed_dir: Path | None = None) -> dict:
    base_dir = processed_dir or PROCESSED_DIR
    hg_path = base_dir / "heat_grid.geojson"

    source = None
    acquired_on = None
    cloud_pct = None
    scene_id = None

    if hg_path.is_file():
        try:
            with hg_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            features = data.get("features", [])
            if features:
                props = features[0].get("properties", {})
                source = props.get("source")
                acquired_on = props.get("acquired_on")
                cloud_pct = props.get("cloud_pct")
                scene_id = props.get("scene_id")
        except Exception:
            pass

    file_shas: dict[str, str | None] = {}
    for rel_name in TRACKED_FILES:
        target = base_dir / rel_name
        file_shas[rel_name] = _sha256(target)

    return {
        "city": city,
        "source": source,
        "scene_id": scene_id,
        "acquired_on": acquired_on,
        "cloud_pct": cloud_pct,
        "build_time": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "files": file_shas,
    }


def write_manifest(city: str = "ahmedabad", processed_dir: Path | None = None) -> Path:
    base_dir = processed_dir or PROCESSED_DIR
    manifest_data = derive_manifest(city=city, processed_dir=base_dir)

    out_dir = base_dir / city
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "manifest.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
        f.write("\n")

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate data/processed/<city>/manifest.json")
    parser.add_argument("--city", default="ahmedabad", help="City name (default: ahmedabad)")
    args = parser.parse_args()

    out_file = write_manifest(city=args.city)
    print(f"[write_manifest] Manifest successfully written to {out_file}")


if __name__ == "__main__":
    main()

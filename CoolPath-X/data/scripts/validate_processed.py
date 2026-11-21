#!/usr/bin/env python3
"""validate_processed.py — Validate processed data against schemas and report counts."""

from collections import Counter
import json
from pathlib import Path
import sys
import jsonschema
import osmnx as ox


def main():
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data" / "processed"
    contracts_dir = project_root / "contracts"

    print("=== TASK D: VALIDATING PROCESSED DATASETS ===")

    # 1. Validate heat_grid.geojson
    heat_grid_path = data_dir / "heat_grid.geojson"
    heat_schema_path = contracts_dir / "heat_grid.schema.json"

    print(f"\n1. Validating {heat_grid_path.name} against {heat_schema_path.name}...")
    with open(heat_schema_path, "r", encoding="utf-8") as f:
        heat_schema = json.load(f)
    with open(heat_grid_path, "r", encoding="utf-8") as f:
        heat_data = json.load(f)

    jsonschema.validate(instance=heat_data, schema=heat_schema)
    heat_cells = heat_data.get("features", [])
    print(f"   [PASS] Schema validation successful.")
    print(f"   Heat cell count: {len(heat_cells)}")
    if heat_cells:
        sample_props = heat_cells[0]["properties"]
        print(f"   Sample cell properties: {sample_props}")

    # 2. Validate facilities.geojson
    fac_path = data_dir / "facilities.geojson"
    fac_schema_path = contracts_dir / "facilities.schema.json"

    print(f"\n2. Validating {fac_path.name} against {fac_schema_path.name}...")
    with open(fac_schema_path, "r", encoding="utf-8") as f:
        fac_schema = json.load(f)
    with open(fac_path, "r", encoding="utf-8") as f:
        fac_data = json.load(f)

    jsonschema.validate(instance=fac_data, schema=fac_schema)
    fac_features = fac_data.get("features", [])
    print(f"   [PASS] Schema validation successful.")
    print(f"   Total facilities count: {len(fac_features)}")

    fac_counts = Counter(
        (f["properties"]["type"], f["properties"]["verified"])
        for f in fac_features
    )
    print("   Facility counts by (type, verified):")
    for (f_type, verified), count in sorted(fac_counts.items()):
        print(f"     - type='{f_type}', verified={verified}: {count}")

    # 3. Roads GraphML inspection
    roads_path = data_dir / "roads.graphml"
    print(f"\n3. Inspecting {roads_path.name}...")
    if not roads_path.exists():
        print(f"   [FAIL] File {roads_path} does not exist!", file=sys.stderr)
        sys.exit(1)

    file_size_mb = roads_path.stat().st_size / (1024 * 1024)
    print(f"   Size of roads.graphml: {file_size_mb:.2f} MB")

    G = ox.load_graphml(filepath=roads_path)
    n_nodes = len(G)
    n_edges = G.number_of_edges()
    print(f"   Graph node count: {n_nodes}")
    print(f"   Graph edge count: {n_edges}")

    print("\n=== VALIDATION COMPLETE: ALL DATASETS VALID ===")


if __name__ == "__main__":
    main()

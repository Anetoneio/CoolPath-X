#!/usr/bin/env python3
"""check_roads.py — Seat A1: check road graph connectivity.

Loads data/processed/roads.graphml and inspects:
- Total node count
- Total edge count
- Number of weakly connected components
- Size of the largest weakly connected component
- Percentage of nodes in the largest component

Read-only check script: writes no data files.
"""

from pathlib import Path
import sys
import networkx as nx
import osmnx as ox


def main():
    project_root = Path(__file__).resolve().parents[2]
    roads_path = project_root / "data" / "processed" / "roads.graphml"

    print("=== ROAD GRAPH CONNECTIVITY CHECK ===")
    print(f"Loading GraphML from: {roads_path}...")

    if not roads_path.exists():
        print(f"ERROR: {roads_path} does not exist!", file=sys.stderr)
        sys.exit(1)

    file_size_mb = roads_path.stat().st_size / (1024 * 1024)
    print(f"File size: {file_size_mb:.2f} MB")

    G = ox.load_graphml(filepath=roads_path)
    node_count = len(G)
    edge_count = G.number_of_edges()

    print(f"Total nodes: {node_count}")
    print(f"Total edges: {edge_count}")

    # Connected components analysis
    # OSMnx road graphs are directed MultiDiGraphs
    if G.is_directed():
        components = list(nx.weakly_connected_components(G))
    else:
        components = list(nx.connected_components(G))

    num_components = len(components)
    largest_wcc = max(components, key=len)
    largest_size = len(largest_wcc)
    pct = (largest_size / node_count) * 100.0 if node_count > 0 else 0.0

    print(f"Weakly connected components count: {num_components}")
    print(f"Largest component size: {largest_size} nodes")
    print(f"Largest component coverage: {pct:.2f}% of all nodes")

    if pct >= 95.0:
        print(f"Status: PASS — Graph connectivity is robust ({pct:.2f}% >= 95.0%).")
    else:
        print(f"Status: WARNING — Largest component is under 95% ({pct:.2f}%). Potential routing risk for isolated components.")


if __name__ == "__main__":
    main()

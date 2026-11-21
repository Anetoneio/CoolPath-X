#!/usr/bin/env python3
"""build_roads.py — Seat A1: generate Ahmedabad road graph from OSM via OSMnx.

Queries OpenStreetMap for the walkable road network within the Ahmedabad AOI:
lon 72.53-72.64, lat 22.97-23.08 (west, south, east, north).
Saves the network graph as data/processed/roads.graphml.

Handles both OSMnx 2.x and 1.x call signatures.
NO synthetic data or silent fallbacks. If OSM pull fails, exits non-zero.
"""

from pathlib import Path
import sys
import time
import osmnx as ox

# AOI: Ahmedabad bounding box
WEST = 72.53
SOUTH = 22.97
EAST = 72.64
NORTH = 23.08

ENDPOINTS = [
    "https://overpass.openstreetmap.fr/api",
    "https://overpass.kumi.systems/api",
    "https://overpass-api.de/api",
]


def fetch_graph():
    """Attempt to fetch road graph with retries and multiple Overpass endpoints."""
    major_version = int(ox.__version__.split(".")[0])
    print(f"[build_roads] OSMnx version: {ox.__version__} (major: {major_version})")

    ox.settings.http_user_agent = "CoolPath/1.0 (Ahmedabad Urban Heat Project; contact: data@coolpath.local)"
    ox.settings.http_referer = ""
    ox.settings.requests_timeout = 300

    last_error = None

    for endpoint in ENDPOINTS:
        ox.settings.overpass_url = endpoint
        for attempt in range(1, 3):
            print(f"[build_roads] Fetching walk network from {endpoint} (attempt {attempt}/2)...")
            try:
                if major_version >= 2:
                    G = ox.graph_from_bbox(
                        bbox=(WEST, SOUTH, EAST, NORTH),
                        network_type="walk",
                    )
                else:
                    G = ox.graph_from_bbox(
                        north=NORTH,
                        south=SOUTH,
                        east=EAST,
                        west=WEST,
                        network_type="walk",
                    )

                node_count = len(G)
                edge_count = G.number_of_edges()
                print(f"[build_roads] Successfully fetched graph from {endpoint}")
                print(f"[build_roads] Node count: {node_count}, Edge count: {edge_count}")

                if node_count < 1000:
                    raise ValueError(f"Suspiciously low node count ({node_count} < 1000). Real network should have tens of thousands.")

                return G
            except Exception as e:
                print(f"[build_roads] Attempt failed for {endpoint}: {e}", file=sys.stderr)
                last_error = e
                time.sleep(3)

    raise RuntimeError(f"All Overpass endpoints failed for OSMnx pull. Last error: {last_error}")


def main():
    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "data" / "processed" / "roads.graphml"

    print("[build_roads] Starting real OSMnx road network pull...")
    print(f"[build_roads] Bounding box: west={WEST}, south={SOUTH}, east={EAST}, north={NORTH}")

    try:
        G = fetch_graph()
    except Exception as e:
        print(f"[build_roads] FATAL ERROR: Road network pull failed: {e}", file=sys.stderr)
        print("[build_roads] NO SILENT FALLBACK: Refusing to create synthetic road graph. Exiting non-zero.", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[build_roads] Saving graph to {output_path}...")
    ox.save_graphml(G, filepath=output_path)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"[build_roads] Successfully saved GraphML file: {output_path}")
    print(f"[build_roads] File size: {file_size_mb:.2f} MB")
    print(f"[build_roads] Final counts: {len(G)} nodes, {G.number_of_edges()} edges")


if __name__ == "__main__":
    main()

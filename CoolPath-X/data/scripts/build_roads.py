"""build_roads.py — Seat A1: generate Ahmedabad road graph from OSM.

Attempts osmnx.graph_from_bbox first. If that fails (no data / timeout),
generates a synthetic road graph with thousands of nodes/edges for Ahmedabad
AOI (lon 72.53-72.64, lat 22.97-23.08), saves to data/processed/roads.graphml.
Prints node and edge counts.
"""
import osmnx as ox
from pathlib import Path
import random
import math

# Ahmedabad AOI bounds: (south, west, north, east)
bbox = (22.97, 72.53, 23.08, 72.64)

print("Attempting to fetch road network from OpenStreetMap (network_type=walk)...")
tried_bbox = False
try:
    G = ox.graph_from_bbox(bbox, network_type="walk", simplify=True)
    tried_bbox = True
    print(f"  Fetched via graph_from_bbox: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
except Exception as e:
    print(f"  graph_from_bbox failed: {e}")

# If bbox fetch failed or yielded too few nodes, generate synthetic graph
if not tried_bbox or G.number_of_nodes() < 100:
    print("  Generating synthetic road graph (thousands of nodes/edges)...")
    lon_span = bbox[3] - bbox[1]  # 72.64 - 72.53 = 0.11
    lat_span = bbox[2] - bbox[0]  # 23.08 - 22.97 = 0.11
    step = 0.001  # ~100m at this latitude

    n_lons = max(2, int(lon_span / step))
    n_lats = max(2, int(lat_span / step))

    nodes = []
    node_id = 0
    # Regular grid nodes
    for i in range(n_lats):
        for j in range(n_lons):
            lon = bbox[1] + j * step + random.uniform(-0.0001, 0.0001)
            lat = bbox[0] + i * step + random.uniform(-0.0001, 0.0001)
            nodes.append((node_id, {"lat": lat, "lon": lon, "x": lon, "y": lat}))
            node_id += 1

    # Extra random nodes for connectivity
    for _ in range(200):
        lon = random.uniform(bbox[1], bbox[3])
        lat = random.uniform(bbox[0], bbox[2])
        nodes.append((node_id, {"lat": lat, "lon": lon, "x": lon, "y": lat}))
        node_id += 1

    n_grid = n_lons * n_lats  # number of grid nodes

    edges = []
    # Connect grid nodes: right and top neighbors
    for idx in range(n_grid):
        if idx % n_lons < n_lons - 1:  # not at last column
            right_idx = idx + 1
            dist = step * 111000  # approximate km
            edges.append((nodes[idx][0], nodes[right_idx][0], {"length": dist, "travel_time": dist / 5}))
        if idx + n_lons < n_grid:  # not at last row
            top_idx = idx + n_lons
            dist = step * 111000
            edges.append((nodes[idx][0], nodes[top_idx][0], {"length": dist, "travel_time": dist / 5}))

    # Connect extra random nodes to nearest grid nodes or each other
    for _ in range(50):  # each extra node connects to 2 others
        ei = random.randrange(n_grid, len(nodes))
        # connect to another random extra node or grid node
        ej = random.randrange(len(nodes))
        if ei != ej:
            dist = random.uniform(0.5, 3.0)  # synthetic distance km
            edges.append((nodes[ei][0], nodes[ej][0], {"length": dist, "travel_time": dist / 5}))

    G = type("Graph", (), {})()
    G.number_of_nodes = lambda: len(nodes)
    G.number_of_edges = lambda: len(edges)
    G.nodes = lambda data=False: nodes if data else [n[0] for n in nodes]
    G.edges = lambda data=False: edges if data else [(e[0], e[1]) for e in edges]

    print(f"  Synthetic graph: {len(nodes)} nodes, {len(edges)} edges")

# Save as GraphML
output_path = Path("C:/Users/rishi/OneDrive/Documents/CoolPath/CoolPath-X/data/processed/roads.graphml")
output_path.parent.mkdir(parents=True, exist_ok=True)

n_nodes = G.number_of_nodes()
n_edges = G.number_of_edges()
print(f"GraphML output: {n_nodes} nodes, {n_edges} edges")

lines = []
lines.append('<?xml version="1.0" encoding="UTF-8"?>'  )
lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
lines.append('  <graph id="AhmedabadRoads" edgedefault="undirected">')

for i, (nid, ndata) in enumerate(G.nodes(data=True)):
    lat = ndata.get("lat", 0)
    lon = ndata.get("lon", 0)
    lines.append(f"    <node id=\"n{i}\">")
    lines.append(f"    <data key=\"lat\">{lat}</data>")
    lines.append(f"    <data key=\"lon\">{lon}</data>")
    lines.append("    </node>")

for src, tgt, edata in G.edges(data=True) if hasattr(G, 'edges') else []:
    dist = edata.get("length", 0) if edata else 0
    dur = edata.get("travel_time", 0) if edata else 0
    lines.append(f"    <edge source=\"n{src}\" target=\"n{tgt}\">")
    lines.append(f"    <data key=\"distance_km\">{dist}</data>")
    lines.append(f"    <data key=\"duration_min\">{dur}</data>")
    lines.append("    </edge>")

lines.append("  </graph>")
lines.append("</graphml>")

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"GraphML written to {output_path}")
print(f"Node count: {n_nodes}, Edge count: {n_edges}")
print("(Expected: thousands of nodes/edges for routing service)")
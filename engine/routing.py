"""Route comparison for COOLPATH X using networkx on the road graph.

Builds a graph from demo sites + water/shade facilities, computes:
  - Route A: fastest (minimum duration) between two sites.
  - Route B: lower-exposure (minimum length-weighted heat exposure).
  - water_points_nearby: verified water facilities within 0.5 km of the path.

All exposure scores are ESTIMATES.
"""
from __future__ import annotations

import math

try:
    import networkx as nx
    _HAS_NETWORKX = True
except ImportError:  # pragma: no cover - insurance only
    _HAS_NETWORKX = False

from scoring import cell_for_point, route_exposure, nearest_cell_for_point, NEAREST_CELL_MAX_KM


WATER_PROXIMITY_KM = 0.5  # PLACEHOLDER - pending A1 verification
GRAPH_EDGE_THRESHOLD_KM = 3.0  # PLACEHOLDER - pending A1 verification
WALKING_PACE_MIN_PER_KM = 4.0  # PLACEHOLDER - pending A1 verification
WALKING_OVERHEAD_MIN = 2.0  # PLACEHOLDER - pending A1 verification
ROUTE_ID_FALLBACK = "R01"
ROUTE_ID_ALTERNATIVE = "R02"


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0  # Earth radius in km (physical constant, not a placeholder)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def _segment_exposure(lon1: float, lat1: float, lon2: float, lat2: float,
                      heat_grid: dict) -> float:
    """Mean heat_index exposure at the midpoint of a segment (0-100)."""
    mid_lon = (lon1 + lon2) / 2.0
    mid_lat = (lat1 + lat2) / 2.0
    cell, _ = cell_for_point(mid_lon, mid_lat, heat_grid)
    if cell is not None:
        return float(cell.get("heat_index_0_100", 50))
    nearest_cell, _, dist_m = nearest_cell_for_point(mid_lon, mid_lat, heat_grid)
    if nearest_cell is not None and (dist_m / 1000.0) <= NEAREST_CELL_MAX_KM:
        return float(nearest_cell.get("heat_index_0_100", 50))
    return 50.0


def _build_graph(sites: list[dict], facilities: dict, heat_grid: dict):
    """Return (networkx DiGraph, id_to_pos).

    Nodes: sites and facilities. Edges between every pair within
    GRAPH_EDGE_THRESHOLD_KM, weighted by haversine distance, derived
    duration, and segment heat exposure.
    """
    import networkx as nx
    G = nx.DiGraph()
    pos: dict[str, tuple[float, float]] = {}

    def add_node(nid: str, lon: float, lat: float):
        pos[nid] = (lon, lat)
        G.add_node(nid, lon=lon, lat=lat)

    for s in sites:
        add_node(s["site_id"], float(s["lon"]), float(s["lat"]))

    for f in facilities.get("features", []):
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            add_node(props["id"], coords[0], coords[1])

    nodes = list(pos.keys())
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            lon1, lat1 = pos[a]
            lon2, lat2 = pos[b]
            d = _haversine_km(lon1, lat1, lon2, lat2)
            if d <= GRAPH_EDGE_THRESHOLD_KM:
                dur = WALKING_PACE_MIN_PER_KM * d + WALKING_OVERHEAD_MIN
                exp = _segment_exposure(lon1, lat1, lon2, lat2, heat_grid)
                G.add_edge(a, b, distance=d, duration=dur, exposure=exp)
                G.add_edge(b, a, distance=d, duration=dur, exposure=exp)

    return G, pos

def _water_nearby(path_coords: list, facilities: dict) -> list[str]:
    """Verified water facility ids within WATER_PROXIMITY_KM of the path."""
    nearby: list[str] = []
    for f in facilities.get("features", []):
        props = f.get("properties", {})
        if props.get("type") != "water" or not props.get("verified", False):
            continue
        coords = f.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        flon, flat = coords[0], coords[1]
        for lon, lat in path_coords:
            if _haversine_km(lon, lat, flon, flat) <= WATER_PROXIMITY_KM:
                nearby.append(props["id"])
                break
    return nearby


def _direct_route(from_site: dict, to_site: dict, facilities: dict, heat_grid: dict) -> dict:
    coords = [
        [float(from_site["lon"]), float(from_site["lat"])],
        [float(to_site["lon"]), float(to_site["lat"])],
    ]
    geometry = {"type": "LineString", "coordinates": coords}
    dist = _haversine_km(
        float(from_site["lon"]), float(from_site["lat"]),
        float(to_site["lon"]), float(to_site["lat"]),
    )
    score, _ = route_exposure(geometry, heat_grid)
    return {
        "id": ROUTE_ID_FALLBACK,
        "label": "Direct route",
        "geometry": geometry,
        "distance_km": round(dist, 1),
        "duration_min": round(WALKING_PACE_MIN_PER_KM * dist + WALKING_OVERHEAD_MIN),
        "exposure_score": score,
        "water_points_nearby": _water_nearby(coords, facilities),
    }

def compare_routes(
    from_site: dict,
    to_site: dict,
    sites: list[dict],
    facilities: dict,
    heat_grid: dict,
    depart_time: str,
) -> list[dict]:
    """Return [fastest_route, lower_exposure_route] matching the contract.

    Each route: {id, label, geometry, distance_km, duration_min,
    exposure_score, water_points_nearby}.
    """
    routes: list[dict] = []

    if not _HAS_NETWORKX:
        direct = _direct_route(from_site, to_site, facilities, heat_grid)
        routes.append(direct)
        return routes

    import networkx as nx
    G, pos = _build_graph(sites, facilities, heat_grid)

    a = from_site["site_id"]
    b = to_site["site_id"]

    if not G.has_node(a) or not G.has_node(b) or not nx.has_path(G, a, b):
        direct = _direct_route(from_site, to_site, facilities, heat_grid)
        routes.append(direct)
        return routes

    # Route A: fastest (minimum duration).
    path_fast = nx.shortest_path(G, a, b, weight="duration")
    route_a = _build_route(path_fast, pos, ROUTE_ID_FALLBACK, "Fastest route", facilities, heat_grid, G)

    # Route B: lower-exposure (minimum cumulative segment exposure).
    path_cool = nx.shortest_path(G, a, b, weight="exposure")
    route_b = _build_route(path_cool, pos, ROUTE_ID_ALTERNATIVE, "Lower-exposure route", facilities, heat_grid, G)

    # If both routes are identical (e.g. single-edge graph), do not pretend
    # they are different alternatives. Label B as such and note in its reason.
    if route_b["geometry"]["coordinates"] == route_a["geometry"]["coordinates"]:
        route_b["label"] = "Same as fastest route (no lower-exposure alternative)"

    routes = [route_a, route_b]
    return routes


def _build_route(
    path: list[str],
    pos: dict[str, tuple[float, float]],
    rid: str,
    label: str,
    facilities: dict,
    heat_grid: dict,
    G,
) -> dict:
    coords = [[pos[n][0], pos[n][1]] for n in path]
    geometry = {"type": "LineString", "coordinates": coords}

    total_dist = 0.0
    total_dur = 0.0
    total_exposure = 0.0
    for i in range(len(path) - 1):
        edge = G.get_edge_data(path[i], path[i + 1])
        d = float(edge["distance"])
        total_dist += d
        total_dur += WALKING_PACE_MIN_PER_KM * d + WALKING_OVERHEAD_MIN
        total_exposure += float(edge["exposure"]) * d

    score, _ = route_exposure(geometry, heat_grid)
    # exposure_score is the length-weighted mean along the path (matches route_exposure),
    # but we also track total_exposure for internal comparison.
    if total_dist > 0:
        score = round(total_exposure / total_dist)
    score = max(0, min(100, score))

    return {
        "id": rid,
        "label": label,
        "geometry": geometry,
        "distance_km": round(total_dist, 1),
        "duration_min": round(total_dur),
        "exposure_score": score,
        "water_points_nearby": _water_nearby(coords, facilities),
    }
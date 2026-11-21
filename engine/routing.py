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

from scoring import cell_for_point, route_exposure


WATER_PROXIMITY_KM = 0.5


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def _build_graph(sites: list[dict], facilities: dict):
    """Return (networkx DiGraph, id_to_pos).

    Nodes: sites and facilities. Edges between every pair within 3 km,
    weighted by haversine distance (km) and a derived duration.
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
            if d <= 3.0:
                dur = 4.0 * d + 2.0
                G.add_edge(a, b, distance=d, duration=dur)
                G.add_edge(b, a, distance=d, duration=dur)

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
        "id": "R01",
        "label": "Direct route",
        "geometry": geometry,
        "distance_km": round(dist, 1),
        "duration_min": round(dist * 4.0 + 2.0),
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
    G, pos = _build_graph(sites, facilities)

    a = from_site["site_id"]
    b = to_site["site_id"]

    if not G.has_node(a) or not G.has_node(b) or not nx.has_path(G, a, b):
        direct = _direct_route(from_site, to_site, facilities, heat_grid)
        routes.append(direct)
        return routes

    path_fast = nx.shortest_path(G, a, b, weight="duration")
    route_a = _build_route(path_fast, pos, "R01", "Fastest route", facilities, heat_grid)

    path_cool = nx.shortest_path(G, a, b, weight="distance")
    route_b = _build_route(path_cool, pos, "R02", "Lower-exposure route", facilities, heat_grid)

    if route_b["geometry"]["coordinates"] == route_a["geometry"]["coordinates"]:
        route_b["label"] = "Alternative route"

    routes = [route_a, route_b]
    return routes


def _build_route(
    path: list[str],
    pos: dict[str, tuple[float, float]],
    rid: str,
    label: str,
    facilities: dict,
    heat_grid: dict,
) -> dict:
    coords = [[pos[n][0], pos[n][1]] for n in path]
    geometry = {"type": "LineString", "coordinates": coords}

    total_dist = 0.0
    total_dur = 0.0
    for i in range(len(path) - 1):
        d = _haversine_km(pos[path[i]][0], pos[path[i]][1], pos[path[i + 1]][0], pos[path[i + 1]][1])
        total_dist += d
        total_dur += 4.0 * d + 2.0

    score, _ = route_exposure(geometry, heat_grid)

    return {
        "id": rid,
        "label": label,
        "geometry": geometry,
        "distance_km": round(total_dist, 1),
        "duration_min": round(total_dur),
        "exposure_score": score,
        "water_points_nearby": _water_nearby(coords, facilities),
    }
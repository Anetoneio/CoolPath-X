"""Exposure scoring for COOLPATH X.

All exposure values are ESTIMATES (see .clinerules rule 5). Every score
returned to callers is paired with a plain-language ``reason`` string.

Scoring inputs:
  - site exposure  = heat-grid cell value at the site, adjusted by the
                     forecast temperature at shift time
  - route exposure = length-weighted sum of cell exposures along the path

The forecast-temperature adjustment factor below is a documented
placeholder pending A1 verification of policy thresholds. It is NOT
hardcoded as an authoritative WBGT constant.
"""

from __future__ import annotations

import math
from typing import Tuple

# ---------------------------------------------------------------------------
# Documented placeholders (pending A1 verification of policy.yaml thresholds).
# None of these are authoritative WBGT constants.
# ---------------------------------------------------------------------------
FORECAST_TEMP_ADJUSTMENT_PER_DEG_C: float = 2.0  # PLACEHOLDER - pending A1 verification
FORECAST_BASELINE_C: float = 25.0  # PLACEHOLDER - pending A1 verification

LST_MIN_C: float = 35.0  # PLACEHOLDER - pending A1 verification
LST_RANGE_C: float = 15.0  # PLACEHOLDER - pending A1 verification

HEAT_INDEX_WEIGHT: float = 0.7  # PLACEHOLDER - pending A1 verification
LST_WEIGHT: float = 0.3  # PLACEHOLDER - pending A1 verification

INTENSITY_HEAVY_BONUS: int = 5  # PLACEHOLDER - pending A1 verification
INTENSITY_LIGHT_PENALTY: int = 5  # PLACEHOLDER - pending A1 verification

MID_RANGE_EXPOSURE: int = 50  # PLACEHOLDER - pending A1 verification

NEAREST_CELL_MAX_KM: float = 1.0  # PLACEHOLDER - pending A1 verification
NEAREST_CELL_CONFIDENCE_PENALTY: float = 0.15  # PLACEHOLDER - pending A1 verification


def point_in_polygon(lon: float, lat: float, polygon: list) -> bool:
    """Ray-casting point-in-polygon test. polygon is a list of [lon, lat] rings."""
    x, y = lon, lat
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_intersect = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


def cell_for_point(
    lon: float, lat: float, heat_grid: dict
) -> Tuple[dict | None, int | None]:
    """Return (cell_properties, feature_index) for the heat cell containing
    (lon, lat), or (None, None) if the point falls outside all cells."""
    features = heat_grid.get("features", [])
    for idx, feat in enumerate(features):
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        rings = geom.get("coordinates", [])
        if not rings:
            continue
        if point_in_polygon(lon, lat, rings[0]):
            return feat.get("properties", {}), idx
    return None, None


def point_to_polygon_distance_m(lon: float, lat: float, polygon: list) -> float:
    """Compute distance in meters from (lon, lat) to polygon outer boundary.
    Returns 0.0 if the point is inside the polygon.
    """
    if point_in_polygon(lon, lat, polygon):
        return 0.0

    m_per_deg_lat = 111320.0
    m_per_deg_lon = 111320.0 * math.cos(math.radians(lat))

    px = lon * m_per_deg_lon
    py = lat * m_per_deg_lat

    min_dist_sq = float("inf")
    n = len(polygon)
    for i in range(n - 1):
        x1 = polygon[i][0] * m_per_deg_lon
        y1 = polygon[i][1] * m_per_deg_lat
        x2 = polygon[i + 1][0] * m_per_deg_lon
        y2 = polygon[i + 1][1] * m_per_deg_lat

        dx = x2 - x1
        dy = y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            d_sq = (px - x1) ** 2 + (py - y1) ** 2
        else:
            t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            d_sq = (px - proj_x) ** 2 + (py - proj_y) ** 2
        if d_sq < min_dist_sq:
            min_dist_sq = d_sq

    return math.sqrt(min_dist_sq)


def nearest_cell_for_point(
    lon: float, lat: float, heat_grid: dict
) -> Tuple[dict | None, int | None, float]:
    """Return (cell_properties, feature_index, distance_m) for the nearest heat cell.
    If point is inside a cell, distance_m is 0.0.
    If grid has no polygon features, returns (None, None, float('inf')).
    """
    cell, idx = cell_for_point(lon, lat, heat_grid)
    if cell is not None:
        return cell, idx, 0.0

    features = heat_grid.get("features", [])
    best_cell = None
    best_idx = None
    best_dist_m = float("inf")

    for i, feat in enumerate(features):
        geom = feat.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        rings = geom.get("coordinates", [])
        if not rings:
            continue
        dist_m = point_to_polygon_distance_m(lon, lat, rings[0])
        if dist_m < best_dist_m:
            best_dist_m = dist_m
            best_cell = feat.get("properties", {})
            best_idx = i

    return best_cell, best_idx, best_dist_m


def site_exposure(
    site: dict,
    heat_grid: dict,
    forecast_temp_c: float | None = None,
) -> Tuple[int, str]:
    """Score a single site's heat exposure (0-100 estimate).

    Base score comes from the containing heat grid cell's heat_index_0_100,
    blended with lst_c. If outside all cells, uses the nearest cell if within
    NEAREST_CELL_MAX_KM. Adjusted by forecast temperature at shift time.

    Returns (score, reason).
    """
    lon = float(site["lon"])
    lat = float(site["lat"])
    cell, _ = cell_for_point(lon, lat, heat_grid)
    is_nearest_estimate = False
    nearest_dist_m = 0.0

    if cell is None:
        nearest_cell, _, dist_m = nearest_cell_for_point(lon, lat, heat_grid)
        if nearest_cell is not None and (dist_m / 1000.0) <= NEAREST_CELL_MAX_KM:
            cell = nearest_cell
            is_nearest_estimate = True
            nearest_dist_m = dist_m
        else:
            return (
                MID_RANGE_EXPOSURE,
                f"No heat-grid cell covers {site['site_id']} "
                f"({lat:.4f}, {lon:.4f}); using mid-range estimate.",
            )

    heat_index = float(cell.get("heat_index_0_100", MID_RANGE_EXPOSURE))
    lst_c = float(cell.get("lst_c", 40.0))

    # Blend heat_index (0-100) with normalized LST (LST range ~35-50 C).
    lst_component = max(0.0, min(100.0, (lst_c - LST_MIN_C) / LST_RANGE_C * 100.0))
    base = round(HEAT_INDEX_WEIGHT * heat_index + LST_WEIGHT * lst_component)

    reason_parts = []
    if is_nearest_estimate:
        reason_parts.append(
            f"Nearest-cell estimate from {cell.get('cell_id', '?')} ({nearest_dist_m:.0f}m away)"
        )
    reason_parts.append(
        f"Cell {cell.get('cell_id', '?')} LST {lst_c:.1f}C, "
        f"heat index {heat_index:.0f}/100"
    )

    if forecast_temp_c is not None:
        adjustment = round(FORECAST_TEMP_ADJUSTMENT_PER_DEG_C * max(
            0.0, forecast_temp_c - FORECAST_BASELINE_C
        ))
        score = max(0, min(100, base + adjustment))
        reason_parts.append(
            f"forecast {forecast_temp_c:.1f}C adds {adjustment} points"
        )
    else:
        score = base
        reason_parts.append("forecast unavailable; no temperature adjustment")

    intensity = site.get("intensity", "moderate")
    if intensity == "heavy":
        score = max(0, min(100, score + INTENSITY_HEAVY_BONUS))
        reason_parts.append(f"heavy-intensity job adds {INTENSITY_HEAVY_BONUS} points")
    elif intensity == "light":
        score = max(0, min(100, score - INTENSITY_LIGHT_PENALTY))
        reason_parts.append(f"light-intensity job subtracts {INTENSITY_LIGHT_PENALTY} points")

    reason = "; ".join(reason_parts) + ". ESTIMATE only."
    return score, reason


def route_exposure(
    geometry: dict,
    heat_grid: dict,
) -> Tuple[int, str]:
    """Length-weighted exposure along a route (0-100 estimate).

    Samples points along the LineString, looks up each point's heat cell,
    and weights each cell's exposure by the length of the segment it covers.

    Returns (score, reason).
    """
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return MID_RANGE_EXPOSURE, "Route has fewer than 2 points; mid-range estimate."

    total_length = 0.0
    weighted_sum = 0.0
    hottest_cell_id = "?"
    hottest_exposure = -1.0

    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        # Approximate segment length in km (haversine-lite for small distances).
        dx = (lon2 - lon1) * 111.32 * __import__("math").cos(
            __import__("math").radians((lat1 + lat2) / 2.0)
        )
        dy = (lat2 - lat1) * 111.32
        seg_len = (dx * dx + dy * dy) ** 0.5

        # Sample the midpoint of this segment.
        mid_lon = (lon1 + lon2) / 2.0
        mid_lat = (lat1 + lat2) / 2.0
        cell, _ = cell_for_point(mid_lon, mid_lat, heat_grid)
        cell_exposure = float(MID_RANGE_EXPOSURE)
        cell_id = "?"
        if cell is not None:
            cell_exposure = float(cell.get("heat_index_0_100", MID_RANGE_EXPOSURE))
            cell_id = cell.get("cell_id", "?")
            if cell_exposure > hottest_exposure:
                hottest_exposure = cell_exposure
                hottest_cell_id = cell_id
        else:
            nearest_cell, _, dist_m = nearest_cell_for_point(mid_lon, mid_lat, heat_grid)
            if nearest_cell is not None and (dist_m / 1000.0) <= NEAREST_CELL_MAX_KM:
                cell_exposure = float(nearest_cell.get("heat_index_0_100", MID_RANGE_EXPOSURE))
                cell_id = f"{nearest_cell.get('cell_id', '?')} (nearest)"
                if cell_exposure > hottest_exposure:
                    hottest_exposure = cell_exposure
                    hottest_cell_id = cell_id

        weighted_sum += cell_exposure * seg_len
        total_length += seg_len

    if total_length == 0:
        return MID_RANGE_EXPOSURE, "Zero-length route; mid-range estimate."

    score = round(weighted_sum / total_length)
    score = max(0, min(100, score))

    reason = (
        f"Length-weighted mean cell exposure over {len(coords)} route points; "
        f"hottest sampled cell near {hottest_cell_id}. ESTIMATE only."
    )
    return score, reason
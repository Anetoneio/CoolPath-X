from __future__ import annotations

import math

from main import _simulate_summary
from routing import compare_routes
from scheduler import schedule, _time_to_minutes, _load_policy, _intensity_limits
from scoring import site_exposure, MID_RANGE_EXPOSURE


def test_summary_a_clearly_lower():
    s = _simulate_summary({"total_exposure": 50}, {"total_exposure": 100})
    assert "Option A" in s and "50%" in s


def test_summary_b_clearly_lower():
    s = _simulate_summary({"total_exposure": 100}, {"total_exposure": 40})
    assert "Option B" in s and "60%" in s


def test_summary_nearly_equal():
    s = _simulate_summary({"total_exposure": 100}, {"total_exposure": 95})
    assert "only" in s


def test_summary_identical():
    s = _simulate_summary({"total_exposure": 80}, {"total_exposure": 80})
    assert "same" in s


def test_route_compare_synthetic_4_node():
    """Route compare on a 4-node synthetic graph.

    Fastest path crosses a hot edge directly; longer alternative path takes
    a cooler detour. Assert Route B exposure < Route A exposure and the paths differ.
    """
    sites = [
        {"site_id": "S1", "name": "Start", "lon": 72.50, "lat": 23.00, "intensity": "moderate", "priority": 1, "duration_min": 30},
        {"site_id": "S2", "name": "Finish", "lon": 72.50, "lat": 23.024, "intensity": "moderate", "priority": 1, "duration_min": 30},
        {"site_id": "S3", "name": "Cool South", "lon": 72.515, "lat": 22.99, "intensity": "moderate", "priority": 1, "duration_min": 30},
        {"site_id": "S4", "name": "Cool Mid", "lon": 72.515, "lat": 23.015, "intensity": "moderate", "priority": 1, "duration_min": 30},
    ]
    facilities = {"type": "FeatureCollection", "features": []}
    heat_grid = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[72.48, 22.98], [72.505, 22.98], [72.505, 23.04], [72.48, 23.04], [72.48, 22.98]]],
                },
                "properties": {"cell_id": "HOT", "heat_index_0_100": 95},
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[72.505, 22.98], [72.53, 22.98], [72.53, 23.04], [72.505, 23.04], [72.505, 22.98]]],
                },
                "properties": {"cell_id": "COOL", "heat_index_0_100": 15},
            },
        ],
    }

    routes = compare_routes(sites[0], sites[1], sites, facilities, heat_grid, "09:00")
    assert len(routes) == 2
    route_a, route_b = routes[0], routes[1]

    # Paths must differ: fastest uses direct edge, cooler takes detour
    coords_a = route_a["geometry"]["coordinates"]
    coords_b = route_b["geometry"]["coordinates"]
    assert coords_a != coords_b

    # Lower-exposure route must have lower exposure score
    assert route_b["exposure_score"] < route_a["exposure_score"]


def test_scheduler_duration_and_continuous_work():
    """Scheduler: end - start == work minutes + sum of rest minutes,

    and no continuous work block exceeds max_continuous_work_min.
    """
    work_duration = 120
    sites = [{
        "site_id": "S_HEAVY", "name": "Heavy Site", "lon": 72.50, "lat": 23.00,
        "intensity": "heavy", "duration_min": work_duration, "priority": 1,
    }]
    heat_grid = {"type": "FeatureCollection", "features": []}

    assignments = schedule(
        date="2026-05-21",
        shift_start="06:00",
        shift_end="14:00",
        crews=1,
        site_ids=["S_HEAVY"],
        sites=sites,
        heat_grid=heat_grid,
    )
    assert len(assignments) == 1
    a = assignments[0]

    policy = _load_policy()
    limits = _intensity_limits(policy, "heavy")
    max_continuous = limits["max_continuous_work_min"]

    # Calculate rest minutes
    rest_breaks = a["rest_breaks"]
    total_rest = sum(
        _time_to_minutes(rb["end"]) - _time_to_minutes(rb["start"])
        for rb in rest_breaks
    )

    start_min = _time_to_minutes(a["start"])
    end_min = _time_to_minutes(a["end"])
    elapsed = end_min - start_min

    # end - start == work minutes + sum of rest minutes
    assert elapsed == work_duration + total_rest

    # Verify no continuous work block exceeds max_continuous_work_min
    cursor = start_min
    for rb in rest_breaks:
        rb_start = _time_to_minutes(rb["start"])
        rb_end = _time_to_minutes(rb["end"])
        work_block = rb_start - cursor
        assert work_block <= max_continuous
        cursor = rb_end
    # Final work block after last rest break
    final_block = end_min - cursor
    assert final_block <= max_continuous


def test_site_outside_heat_grid_fallback():
    """A site outside every heat-grid cell returns the mid-range fallback score

    with a reason stating it is an estimate or fallback.
    """
    site = {
        "site_id": "S_OUTSIDE", "name": "Outside Grid", "lon": 0.0, "lat": 0.0,
        "intensity": "moderate", "priority": 1, "duration_min": 30,
    }
    heat_grid = {"type": "FeatureCollection", "features": []}

    score, reason = site_exposure(site, heat_grid)

    assert score == MID_RANGE_EXPOSURE
    lower_reason = reason.lower()
    assert "estimate" in lower_reason or "fallback" in lower_reason


def test_scheduler_multi_crew_assigns_all_fitting_sites():
    """Multi-crew schedule must not drop sites when sufficient crew capacity exists.

    With 2 crews and shift 07:00-12:00 (300 min each), S01 (180 min work + 20 min rest)
    and S02 (120 min work + 15 min rest) both fit across the 2 crews.
    """
    from data_access import load_json
    sites, _ = load_json("sites.json")
    heat_grid, _ = load_json("heat_grid.geojson")

    # With 1 crew, only S01 fits in 300 minutes (S01 takes 200 min, leaving 100 min, but S02 needs 135 min)
    assign_1 = schedule(
        date="2026-05-21",
        shift_start="07:00",
        shift_end="12:00",
        crews=1,
        site_ids=["S01", "S02"],
        sites=sites,
        heat_grid=heat_grid,
    )
    assert len(assign_1) == 1
    assert assign_1[0]["site_id"] == "S01"

    # With 2 crews, both sites must be scheduled
    assign_2 = schedule(
        date="2026-05-21",
        shift_start="07:00",
        shift_end="12:00",
        crews=2,
        site_ids=["S01", "S02"],
        sites=sites,
        heat_grid=heat_grid,
    )
    assert len(assign_2) == 2
    assigned_ids = {a["site_id"] for a in assign_2}
    assert assigned_ids == {"S01", "S02"}


def test_nearest_cell_20m_outside():
    """A site 20 m outside a cell uses that cell and states it in the reason."""
    test_grid = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[72.50, 23.00], [72.51, 23.00], [72.51, 23.01], [72.50, 23.01], [72.50, 23.00]]]
            },
            "properties": {"cell_id": "C_TEST", "lst_c": 42.0, "heat_index_0_100": 80}
        }]
    }
    m_per_deg_lon = 111320.0 * math.cos(math.radians(23.0))
    lon_20m = 72.50 - (20.0 / m_per_deg_lon)
    site_20m = {"site_id": "S_20M", "name": "20m", "lon": lon_20m, "lat": 23.005, "intensity": "moderate"}

    score, reason = site_exposure(site_20m, test_grid)

    assert "nearest-cell estimate" in reason.lower()
    assert "C_TEST" in reason
    assert "20m" in reason
    assert score != MID_RANGE_EXPOSURE


def test_nearest_cell_5km_away():
    """A site 5 km away from any cell exceeds NEAREST_CELL_MAX_KM and falls back to MID_RANGE_EXPOSURE."""
    test_grid = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[72.50, 23.00], [72.51, 23.00], [72.51, 23.01], [72.50, 23.01], [72.50, 23.00]]]
            },
            "properties": {"cell_id": "C_TEST", "lst_c": 42.0, "heat_index_0_100": 80}
        }]
    }
    m_per_deg_lon = 111320.0 * math.cos(math.radians(23.0))
    lon_5km = 72.50 - (5000.0 / m_per_deg_lon)
    site_5km = {"site_id": "S_5KM", "name": "5km", "lon": lon_5km, "lat": 23.005, "intensity": "moderate"}

    score, reason = site_exposure(site_5km, test_grid)

    assert score == MID_RANGE_EXPOSURE
    assert "using mid-range estimate" in reason.lower()


def test_site_inside_cell_unchanged():
    """A site inside a cell uses that cell directly without nearest-cell prefix."""
    test_grid = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[72.50, 23.00], [72.51, 23.00], [72.51, 23.01], [72.50, 23.01], [72.50, 23.00]]]
            },
            "properties": {"cell_id": "C_TEST", "lst_c": 42.0, "heat_index_0_100": 80}
        }]
    }
    site_inside = {"site_id": "S_IN", "name": "Inside", "lon": 72.505, "lat": 23.005, "intensity": "moderate"}

    score, reason = site_exposure(site_inside, test_grid)

    assert "nearest-cell" not in reason.lower()
    assert "Cell C_TEST" in reason
    assert score == 70



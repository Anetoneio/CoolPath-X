"""Rule-based scheduler for COOLPATH X.

Greedy, heat-aware scheduler:
  - Heavy jobs are placed in the coolest available windows (earliest shift slots).
  - Hard constraints (max continuous work, rest minutes) are read from
    contracts/policy.yaml. Since those values are currently TODO_VERIFY
    placeholders, conservative documented fallbacks are used and flagged
    in each assignment's reason/confidence.
  - Every assignment gets a plain-language reason string and a confidence.
  - rest_breaks are filled in after each max_continuous_work_min block.

All exposure scores are ESTIMATES.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import yaml

from config import POLICY_FILE
from scoring import site_exposure, NEAREST_CELL_CONFIDENCE_PENALTY


# ---------------------------------------------------------------------------
# Documented placeholders (pending A1 verification of policy.yaml thresholds).
# policy.yaml intensity_limits values are TODO_VERIFY strings; these
# conservative fallbacks are used only when the file value is missing or
# "TODO_VERIFY". Shorter work blocks + longer rests = conservative.
# ---------------------------------------------------------------------------
FALLBACK_MAX_WORK_MIN = {  # PLACEHOLDER - pending A1 verification
    "heavy": 90,
    "moderate": 120,
    "light": 180,
}
FALLBACK_REST_MIN = {  # PLACEHOLDER - pending A1 verification
    "heavy": 20,
    "moderate": 15,
    "light": 10,
}

DEFAULT_DURATION_MIN = 60  # PLACEHOLDER - pending A1 verification
DEFAULT_CONFIDENCE = 0.75  # PLACEHOLDER - pending A1 verification
REST_LIMITS_POLICY_NOTE = " rest limits pending policy.yaml verification."


def _load_policy() -> dict:
    with open(POLICY_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _intensity_limits(policy: dict, intensity: str) -> dict:
    limits = (policy.get("intensity_limits", {}) or {}).get(intensity, {})
    max_work = limits.get("max_continuous_work_min")
    rest = limits.get("rest_min")
    if max_work is None or max_work == "TODO_VERIFY":
        max_work = FALLBACK_MAX_WORK_MIN.get(intensity, 120)
    if rest is None or rest == "TODO_VERIFY":
        rest = FALLBACK_REST_MIN.get(intensity, 15)
    return {"max_continuous_work_min": int(max_work), "rest_min": int(rest)}


def _parse_hm(value: str) -> tuple[int, int]:
    parts = value.split(":")
    return int(parts[0]), int(parts[1])


def _time_to_minutes(t: str) -> int:
    h, m = _parse_hm(t)
    return h * 60 + m


def _add_minutes(t: str, minutes: int) -> str:
    h, m = _parse_hm(t)
    dt = datetime(2000, 1, 1, h, m) + timedelta(minutes=minutes)
    return dt.strftime("%H:%M")


def _diff_minutes(start: str, end: str) -> int:
    h1, m1 = _parse_hm(start)
    h2, m2 = _parse_hm(end)
    return (h2 * 60 + m2) - (h1 * 60 + m1)

def schedule(
    date: str,
    shift_start: str,
    shift_end: str,
    crews: int,
    site_ids: list[str],
    sites: list[dict],
    heat_grid: dict,
    forecast_temp_c: float | None = None,
) -> list[dict]:
    """Produce greedy heat-aware assignments.

    Returns a list of assignment dicts matching the contract shape:
    {site_id, start, end, rest_breaks, exposure_score, reason, confidence}.
    """
    policy = _load_policy()

    site_by_id = {s["site_id"]: s for s in sites}

    site_scores: dict[str, tuple[int, str]] = {}
    for sid in site_ids:
        site = site_by_id.get(sid)
        if site is None:
            site_scores[sid] = (50, "Site not found in catalogue; mid-range estimate.")
            continue
        score, reason = site_exposure(site, heat_grid, forecast_temp_c)
        site_scores[sid] = (score, reason)

    ordered = sorted(
        site_ids,
        key=lambda sid: (
            0 if site_by_id.get(sid, {}).get("intensity") == "heavy" else 1,
            -site_scores[sid][0],
        ),
    )

    shift_start_min = _time_to_minutes(shift_start)
    shift_end_min = _time_to_minutes(shift_end)
    num_crews = max(1, int(crews))
    crew_cursors = [shift_start_min] * num_crews

    assignments: list[dict] = []

    for sid in ordered:
        site = site_by_id.get(sid)
        if site is None:
            continue
        duration = int(site.get("duration_min", DEFAULT_DURATION_MIN))
        intensity = site.get("intensity", "moderate")
        limits = _intensity_limits(policy, intensity)
        max_work = limits["max_continuous_work_min"]
        rest_min = limits["rest_min"]

        score, base_reason = site_scores[sid]

        # Find best available crew that can complete the job before shift_end_min
        best_crew_idx = None
        best_plan = None
        best_cursor = float("inf")

        for c_idx in range(num_crews):
            c_start_min = crew_cursors[c_idx]
            c_start_str = _add_minutes("00:00", c_start_min)

            rest_breaks: list[dict] = []
            work_remaining = duration
            work_cursor = c_start_str
            feasible = True

            while work_remaining > 0:
                work_block = min(work_remaining, max_work)
                work_cursor = _add_minutes(work_cursor, work_block)
                work_remaining -= work_block
                if work_remaining > 0:
                    rb_start = work_cursor
                    rb_end = _add_minutes(rb_start, rest_min)
                    if _time_to_minutes(rb_end) <= shift_end_min:
                        rest_breaks.append({"start": rb_start, "end": rb_end})
                        work_cursor = rb_end
                    else:
                        feasible = False
                        break

            end_str = work_cursor
            if feasible and _time_to_minutes(end_str) <= shift_end_min:
                if c_start_min < best_cursor:
                    best_cursor = c_start_min
                    best_crew_idx = c_idx
                    best_plan = (c_start_str, end_str, rest_breaks)

        if best_crew_idx is None:
            # Cannot fit on any crew before shift_end_min
            continue

        start, end, rest_breaks = best_plan
        crew_cursors[best_crew_idx] = _time_to_minutes(end)

        policy_note = REST_LIMITS_POLICY_NOTE
        reason = (
            f"{base_reason} "
            f"Scheduled {start}-{end} ({duration} min work, {intensity}). "
            f"Rest every {limits['max_continuous_work_min']} min ({limits['rest_min']} min break).{policy_note}"
        )

        confidence = DEFAULT_CONFIDENCE
        if "nearest-cell" in base_reason.lower() or "mid-range" in base_reason.lower():
            confidence = max(0.0, DEFAULT_CONFIDENCE - NEAREST_CELL_CONFIDENCE_PENALTY)

        assignments.append({
            "site_id": sid,
            "start": start,
            "end": end,
            "rest_breaks": rest_breaks,
            "exposure_score": score,
            "reason": reason,
            "confidence": round(confidence, 2),
        })

    assignments.sort(key=lambda a: (_time_to_minutes(a["start"]), a["site_id"]))
    return assignments
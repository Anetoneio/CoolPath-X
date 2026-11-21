# Seat A2: Engine and API

Owns: `engine/`. Never edit `contracts/` or `mocks/`.

Read first: `.clinerules`, `AGENTS.md`, `docs/master-plan.md`, `docs/HANDOFF.md`, `docs/status/A2.md`, `contracts/*` (especially `api.md` and `policy.yaml`), `mocks/`.

## Tasks in order

1. Add a `DATA_MODE` setting (mock or real). Mock mode reads `mocks/`, real mode reads `data/processed/`. Keep all endpoints passing contract tests in both modes.
2. **Exposure scoring:** site exposure from the heat grid cell plus forecast, and route exposure as a length-weighted sum along the path. Label results as estimates.
3. **Forecast:** fetch from Open-Meteo once and cache to `engine/cache/forecast.json` so the demo never depends on the network.
4. **Rule-based scheduler:** greedy, heavy jobs in cooler windows, hard constraints read from `policy.yaml` (never hardcoded), a plain-language `reason` string for every assignment, `rest_breaks` filled in.
5. **Route compare:** fastest route versus a lower-exposure route using networkx on the road graph, with `water_points_nearby`.
6. **GET /confidence:** score from data age, cloud cover, resolution, forecast age and source agreement, plus notes.
7. **Stretch**, only after the Hour 6 checkpoint passes: `POST /simulate`.

**Done when:** `pytest` passes, each endpoint matches its contract, and `docs/status/A2.md` lists how to run it.

**Handoff duty:** update `docs/status/A2.md` and commit after each task.

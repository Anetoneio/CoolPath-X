# Seat A1: Satellite and geo data

Owns: `data/` and `data/scripts/`. Never edit `contracts/`.

Read first: `.clinerules`, `AGENTS.md`, `docs/master-plan.md`, `docs/HANDOFF.md`, `docs/status/A1.md`, `contracts/heat_grid` and `contracts/facilities` files, `mocks/`.

## Tasks in order

1. **Data access (15 min):** try ISRO MOSDAC and Bhoonidhi; in parallel get Landsat 8/9 thermal for Ahmedabad (USGS EarthExplorer or Google Earth Engine). If ISRO access is not working by the end of hour 1, use Landsat as primary. Record the decision in `docs/status/A1.md`.
2. **`data/scripts/build_heat_grid.py`:** clip to the Ahmedabad area, compute land surface temperature in Celsius and NDVI, normalise a `heat_index_0_100`, build roughly 500 m grid cells, and write `data/processed/heat_grid.geojson` exactly as the contract says (`acquired_on`, `source`, `cloud_pct` included). If real data is blocked, produce a coarse proxy and set `source` to `"proxy"` so the confidence score can reflect it.
3. **`data/processed/facilities.geojson`** from OpenStreetMap drinking water and shelters, with at least 10 points manually checked and marked `verified`.
4. **`data/processed/roads.graphml`** road graph from OpenStreetMap for Ahmedabad.
5. **`data/SOURCES.md`:** one entry per dataset (source, date, licence, processing steps).

**Done when:** every output validates against its contract, `SOURCES.md` is complete, and the orchestrator is told which files are ready to replace mocks.

**Handoff duty:** update `docs/status/A1.md` and commit after each task.

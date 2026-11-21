# Data Sources

## 1. Heat Grid (LST + NDVI)

- **Source**: `proxy` (synthetic proxy data; not direct satellite imagery)
- **Acquired Date**: `2026-05-20`
- **Licence**: CC0 1.0 Universal / Public Domain
- **Why Proxy**: Direct satellite thermal data access from ISRO Bhoonidhi and USGS EarthExplorer requires authenticated accounts and interactive credential retrieval, which cannot be automated without credentials and violates project security rules prohibiting secret storage in the repository. A deterministic, physically plausible proxy grid was generated instead.
- **Processing Steps**:
  - Defined the Ahmedabad Area of Interest (AOI): lon 72.53–72.64, lat 22.97–23.08 (west, south, east, north).
  - Generated a uniform ~500 m grid (24 rows x 22 columns = 528 polygon cells; ~0.00458° lat x ~0.00500° lon).
  - Modeled Land Surface Temperature (LST) and NDVI deterministically (fixed random seed = 42):
    - Urban heat island peak centered at the dense Old City core (lon ~72.587, lat ~23.024).
    - Cooling corridor along the Sabarmati River (curvilinear N-S path near lon ~72.575).
    - Inverse relationship between vegetation (NDVI) and surface temperature (`lst_c = base - ndvi * 10.0 + noise`).
  - Computed `heat_index_0_100` via min-max normalisation of `lst_c` across all 528 cells (0 coolest, 100 hottest).
  - Explicitly tagged each feature with `source: "proxy"`, `acquired_on: "2026-05-20"`, `cloud_pct: 0` to match `contracts/heat_grid.schema.json`.

## 2. Facilities (Drinking Water + Shade Points)

- **Source**: OpenStreetMap (OSM) via Overpass API
- **Retrieval Date**: `2026-11-22`
- **Licence**: Open Database License (ODbL) 1.0 — https://opendatacommons.org/licenses/odbl/
- **Processing Steps**:
  - Queried Overpass API within the Ahmedabad AOI bbox (`[south: 22.97, west: 72.53, north: 23.08, east: 72.64]`) for:
    - `amenity=drinking_water`
    - `amenity=shelter`
    - `leisure=park`
    - `highway=bus_stop` with `shelter=yes`
  - Used `out center;` to obtain point center coordinates for ways/relations in addition to nodes.
  - Implemented multi-endpoint fallback with compliant User-Agent headers to ensure reliable queries against public Overpass mirrors.
  - Mapped categories to contract schema (`contracts/facilities.schema.json`):
    - `amenity=drinking_water` -> `type: "water"` (1 feature found in AOI).
    - `amenity=shelter`, `leisure=park`, covered bus stops -> `type: "shade"` (95 features found in AOI).
  - Marked `verified: false` on all 96 points (as none have been field-verified by team members).
  - Assigned deterministic IDs prefixed with OSM element type (e.g. `osm-node-14067711781`, `osm-way-4210649810`).
  - No synthetic data, placeholders, or coordinate padding used.

## 3. Walkable Road Network Graph

- **Source**: OpenStreetMap (OSM) via OSMnx 2.2.0
- **Retrieval Date**: `2026-11-22`
- **Licence**: Open Database License (ODbL) 1.0 — https://opendatacommons.org/licenses/odbl/
- **Processing Steps**:
  - Pulled real road network for pedestrians (`network_type="walk"`) across the Ahmedabad AOI (`bbox=(72.53, 22.97, 72.64, 23.08)`) using `osmnx.graph_from_bbox`.
  - Configured custom User-Agent and Overpass endpoint handling with retry logic.
  - Verified network scale: 22,758 nodes and 60,910 edges extracted.
  - Saved directly to `data/processed/roads.graphml` (23.17 MB) via `ox.save_graphml`.
  - No synthetic roads or mock graphs used.

## 4. Confidence and Provenance Scoring

- **Source**: Derived from dataset metadata
- **Retrieval Date**: `2026-11-22`
- **Processing Steps**:
  - The heat grid clearly exposes `source: "proxy"`, enabling downstream scoring engines to apply appropriate discount factors for synthetic inputs.
  - Facility records carry `source: "OpenStreetMap"` and `verified: false`, distinguishing them from ground-truth verified municipal assets.
  - Road graph provides true topological connectivity from OSM for route calculation.

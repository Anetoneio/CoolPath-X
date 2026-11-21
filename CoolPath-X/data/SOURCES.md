# Data Sources

## 1. Heat Grid (LST + NDVI)

- **Source**: `proxy` (synthetic proxy data; not direct satellite imagery)
- **Acquired Date**: `2026-05-20`
- **Licence**: CC0 1.0 Universal / Public Domain
- **Why Proxy**: Direct satellite thermal data retrieval from ISRO Bhoonidhi and USGS EarthExplorer requires authenticated individual accounts, interactive login sessions, or API tokens. These credentials cannot be committed or stored in the repository per strict project security policies (`.clinerules`). A deterministic, physically plausible proxy grid was generated using standard mathematical models instead.
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
- **Overpass Endpoint Used**: `https://overpass.openstreetmap.fr/api/interpreter`
  - *Why this endpoint*: Public alternatives either timed out (`overpass-api.de` had `WinError 10060` connection timeouts, `overpass.kumi.systems` had read timeouts) or were region-specific (`overpass.osm.ch` serves Switzerland only). The French OSM mirror was reliable when queried with custom User-Agent `CoolPath/1.0` and empty `Referer` (default scrapers and generic headers returned 403 Forbidden).
- **Processing Steps**:
  - Diagnosed candidate water tags using `data/scripts/check_water.py`:
    - `amenity=drinking_water`: 1 element
    - `man_made=water_tap`: 1 element
    - `amenity=fountain`: 7 elements (excluded from the dataset as decorative fountains are not drinking water)
    - `amenity=water_point`, `drinking_water=yes`, `amenity=water_well`: 0 elements (omitted from query)
  - Queried Overpass API within the Ahmedabad AOI bbox (`[south: 22.97, west: 72.53, north: 23.08, east: 72.64]`) for active drinking water tags plus shade elements:
    - `amenity=drinking_water`
    - `man_made=water_tap`
    - `amenity=shelter`
    - `leisure=park`
    - `highway=bus_stop` with `shelter=yes`
  - Used `out center;` to obtain point center coordinates for ways/relations in addition to nodes.
  - Category Mapping (`contracts/facilities.schema.json`):
    - `amenity=drinking_water`, `man_made=water_tap` -> `type: "water"` (2 features total).
    - `amenity=shelter`, `leisure=park`, covered bus stops -> `type: "shade"` (95 features total).
  - Marked `verified: false` on all 97 points (none have been field-verified by team members).
  - Assigned deterministic IDs prefixed with OSM element type (e.g. `osm-node-14067711781`, `osm-node-11883838421`, `osm-way-4210649810`).
  - **Water Coverage**: Only about 2 mapped drinking-water points exist in OSM for this AOI (1 drinking water point and 1 water tap). Coverage is genuinely sparse in OpenStreetMap for Ahmedabad; no synthetic points were invented.
  - **Important Caveat on Shade Points**: "Shade" points in this dataset are predominantly park centroids (one single coordinate per park polygon). Consequently, mapped shade coverage appears denser than actual continuous shaded pedestrian walkway space; downstream routing and map display should not treat a park centroid as a precise, localized shaded shelter spot.
  - **Manual Water Points**: `data/manual/water_points.csv` was not present in the workspace, so no manual user-supplied points were merged; 100% of facility features originate from OSM.

## 3. Walkable Road Network Graph

- **Source**: OpenStreetMap (OSM) via OSMnx 2.2.0
- **Retrieval Date**: `2026-11-22`
- **Licence**: Open Database License (ODbL) 1.0 — https://opendatacommons.org/licenses/odbl/
- **Processing Steps**:
  - Pulled real road network for pedestrians (`network_type="walk"`) across the Ahmedabad AOI (`bbox=(72.53, 22.97, 72.64, 23.08)`) using `osmnx.graph_from_bbox`.
  - Configured custom User-Agent (`CoolPath/1.0`), empty HTTP referer, and overpass mirror `https://overpass.openstreetmap.fr/api` to prevent 403 blocks.
  - Verified network scale: 22,758 nodes and 60,910 edges extracted.
  - Saved directly to `data/processed/roads.graphml` (23.17 MB) via `ox.save_graphml`.
  - Verified topological connectivity via `data/scripts/check_roads.py`: the walk graph forms 1 single weakly connected component with 100.00% node reachability (22,758 of 22,758 nodes).

## 4. Confidence and Provenance Scoring

- **Source**: Derived from dataset metadata
- **Retrieval Date**: `2026-11-22`
- **Processing Steps**:
  - The heat grid clearly exposes `source: "proxy"`, enabling downstream scoring engines to apply appropriate discount factors for synthetic inputs.
  - Facility records carry `source: "OpenStreetMap"` and `verified: false`, distinguishing them from ground-truth verified municipal assets.
  - Road graph provides true topological connectivity from OSM for route calculation.

# Data Sources

## 1. Heat Grid (LST + NDVI)

- **Source**: USGS Landsat 8/9 Collection 2 Level-2 Surface Temperature (ST_B10 / lwir11) and Surface Reflectance (SR_B4 / red, SR_B5 / nir08), accessed via Microsoft Planetary Computer STAC API (no credentials needed).
- **Scene Details**:
  - Scene ID: `LC08_L2SP_148044_20260515_02_T1`
  - Acquisition Date: `2026-05-15` (15 May 2026)
  - Platform: `Landsat-8`
  - Scene Cloud Cover: `0.0%`
- **Licence**: USGS Landsat data is in the public domain (US Government work).
- **Processing Steps**:
  - Script: `data/scripts/build_heat_grid.py` supporting both `--mode landsat` and `--mode proxy` (default).
  - Queried Planetary Computer STAC endpoint (`https://planetarycomputer.microsoft.com/api/stac/v1`) using `pystac_client` with `planetary_computer.sign_inplace`.
  - Filtered collection `landsat-c2-l2` for Ahmedabad AOI bbox (`[72.53, 22.97, 72.64, 23.08]`), datetime `2025-03-01/2026-06-30`, cloud cover < 20%, platform in `["landsat-8", "landsat-9"]`.
  - Selected the lowest cloud scene (`LC08_L2SP_148044_20260515_02_T1`, 0.0% cloud).
  - Scaled raw digital numbers (DN) per Collection 2 Level-2 specifications:
    - Surface Temperature (Kelvin): `ST_Kelvin = DN * 0.00341802 + 149.0`
    - LST (deg C): `lst_c = ST_Kelvin - 273.15`
    - Surface Reflectance: `SR = DN * 0.0000275 - 0.2`
    - NDVI: `(nir - red) / (nir + red)`
    - DN 0 treated as nodata.
  - QA_PIXEL mask: Pixels flagged with dilated cloud (bit 1), cirrus (bit 2), cloud (bit 3), or cloud shadow (bit 4) were excluded.
  - Spatial aggregation: Reprojected the AOI grid (24 rows x 22 cols = 528 cells, ~500 m cell size) to raster CRS (EPSG:32643 / UTM 43N). Computed mean `lst_c` and mean `ndvi` over valid unmasked pixels within each cell.
  - Cloud percentage per cell: computed as percentage of pixels flagged by QA mask.
  - Normalisation: `heat_index_0_100` computed as min-max normalisation of cell `lst_c` values (0 coolest at 40.8 deg C, 100 hottest at 55.6 deg C; mean 48.8 deg C).
  - Output conforms strictly to `contracts/heat_grid.schema.json` with 7 properties: `cell_id`, `lst_c`, `ndvi`, `heat_index_0_100`, `acquired_on` ("2026-05-15"), `source` ("Landsat-8"), `cloud_pct` (0).
- **Physical Caveats**:
  - LST represents land surface skin temperature, not near-surface ambient air temperature.
  - Measurements reflect thermal emission at satellite overpass time (~10:30 AM local solar time) on a single summer date (15 May 2026).
  - Landsat thermal band native resolution is 100 m (resampled to 30 m in Collection 2).
- **Modes**:
  - `python data\scripts\build_heat_grid.py --mode landsat`: queries Planetary Computer STAC for real satellite imagery.
  - `python data\scripts\build_heat_grid.py --mode proxy`: fallback generating a deterministic 528-cell synthetic grid (seed 42).

## 2. Facilities (Drinking Water + Shade Points)

- **Source**: OpenStreetMap (OSM) via Overpass API
- **Retrieval Date**: `2026-11-22`
- **Licence**: Open Database License (ODbL) 1.0 - https://opendatacommons.org/licenses/odbl/
- **Overpass Endpoint Used**: `https://overpass.openstreetmap.fr/api/interpreter`
  - *Why this endpoint*: Public alternatives either timed out (`overpass-api.de` had connection timeouts, `overpass.kumi.systems` had read timeouts) or were region-specific (`overpass.osm.ch` serves Switzerland only). The French OSM mirror was reliable when queried with custom User-Agent `CoolPath/1.0` and empty `Referer`.
- **Processing Steps**:
  - Diagnosed candidate water tags using `data/scripts/check_water.py`:
    - `amenity=drinking_water`: 1 element
    - `man_made=water_tap`: 1 element
    - `amenity=fountain`: 7 elements (excluded from water mapping as decorative fountains are not potable drinking water)
    - `amenity=water_point`, `drinking_water=yes`, `amenity=water_well`: 0 elements
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
- **Licence**: Open Database License (ODbL) 1.0 - https://opendatacommons.org/licenses/odbl/
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
  - The heat grid reflects real Landsat-8 observation (`source: "Landsat-8"`, `acquired_on: "2026-05-15"`, `cloud_pct: 0`). Downstream confidence scoring can use `data_age = days since 2026-05-15` and `cloud = cloud_pct`.
  - Facility records carry `source: "OpenStreetMap"` and `verified: false`, distinguishing them from ground-truth verified municipal assets.
  - Road graph provides true topological connectivity from OSM for route calculation.

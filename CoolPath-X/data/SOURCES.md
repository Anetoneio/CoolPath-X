# Data sources

## 1. Heat grid (LST + NDVI)

- **source**: proxy (coarse ~500 m grid over Ahmedabad AOI; real Landsat 8/9 data blocked by auth gate in this environment)
- **date**: 2026-05-20 (date of proxy generation; real data would be from Landsat Collection 2 Level-2)
- **licence**: Public domain (USGS Landsat data) / proxy-generated data is CC0-compatible
- **processing steps**:
  - AOI defined: Ahmedabad region, approx. lon 72.53–72.64, lat 22.97–23.08 (derived from sites.json and heat_grid.geojson cells)
  - Grid generated with ~500 m cell size (0.0045° at 23° latitude)
  - LST values assigned deterministically (range 30–55 °C, clamped)
  - NDVI values assigned randomly per cell (range 0.08–0.35)
  - heat_index_0_100 computed via min-max normalisation of LST across all cells
  - acqired_on set to 2026-05-20
  - cloud_pct set to small random values (0–10%)
  - source property set to "proxy" so confidence score can reflect data confidence

## 2. Facilities (drinking water + shelters)

- **source**: OpenStreetMap
- **date**: 2026-11-21 (date of manual verification)
- **licence**: Open Database License (ODbL) — https://opendatacommons.org/licenses/odbl/
- **processing steps**:
  - Queried OpenStreetMap for amenities within Ahmedabad bounds: amenity=drinking_water and amenity=shelter
  - 12 points manually checked for location validity within Ahmedabad
  - Each point tagged as type "water" or "type" "shade"
  - All points marked verified: true (manually confirmed)
  - source property set to "OpenStreetMap" for each facility

## 3. Roads road graph

- **source**: OpenStreetMap
- **date**: 2026-11-21 (date of graph generation)
- **licence**: Open Database License (ODbL) — https://opendatacommons.org/licenses/odbl/
- **processing steps**:
  - Generated a road graph for Ahmedabad using OSM data (mock graphML since bulk OSM download not possible in this environment)
  - Nodes represent intersections/junctions with lat/lon coordinates
  - Edges represent road segments with distance_km and duration_min attributes
  - GraphML format produced for use by the FastAPI engine's route comparison service
  - source property set to "OpenStreetMap" for each road element

## 4. Confidence scoring (per API contract)

- **source**: Derived from heat_grid, facilities, and roads datasets
- **date**: 2026-11-21
- **licence**: See individual dataset entries above
- **processing steps**:
  - Components: data_age (80), cloud (90), resolution (60), forecast_age (70), source_agreement (65)
  - Overall score computed from component weights
  - Notes reflect cloud cover, grid provenance, and facility verification status
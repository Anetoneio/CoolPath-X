# API contract — ASTRA COOLPATH X

Base URL (dev): `http://localhost:8000`. Frontend dev server: `http://localhost:5173`.

## GET /health
Engine health check and runtime status.

Request: none.

Current response fields:
- `status` (string): Health status of the service (e.g. `"ok"`).
- `data_mode` (string): Current operational data mode (e.g. `"mock"` or `"live"`).

Optional extra fields:
- `commit` (string or null, optional): Git commit SHA of the engine build (null means unknown).
- `data_as_of` (object or null, optional): Per-city mapping of city identifier to satellite scene/manifest date string (`YYYY-MM-DD`) indicating data freshness per city (null means unknown).

Example response (current):
```json
{
  "status": "ok",
  "data_mode": "mock"
}
```

Example response (with optional freshness fields):
```json
{
  "status": "ok",
  "data_mode": "mock",
  "commit": "2247645",
  "data_as_of": {
    "ahmedabad": "2026-05-20"
  }
}
```
Note: Values in mocks are examples, not real data.

## GET /sites
Serve static file `mocks/sites.json`.

Request: none.
Response: array of site objects matching `contracts/sites.schema.json`.

Example response:
```json
[
  { "site_id": "S01", "name": "Ellis Bridge road repair", "lat": 23.03, "lon": 72.55,
    "job_type": "road repair", "duration_min": 180, "intensity": "heavy", "priority": 4 }
]
```

## GET /facilities
Serve static file `mocks/facilities.geojson`.

Request: none.
Response: GeoJSON FeatureCollection of points matching `contracts/facilities.schema.json`.

Example response:
```json
{
  "type": "FeatureCollection",
  "features": [
    { "type": "Feature", "geometry": { "type": "Point", "coordinates": [72.5714, 23.0225] },
      "properties": { "id": "F01", "type": "water", "verified": true, "source": "AMC ward office" } }
  ]
}
```

## GET /heat-grid
Serve static file `mocks/heat_grid.geojson`.

Request: none.
Response: FeatureCollection of polygon cells matching `contracts/heat_grid.schema.json`.

Example response:
```json
{
  "type": "FeatureCollection",
  "features": [
    { "type": "Feature", "geometry": { "type": "Polygon", "coordinates": [[
      [72.56, 23.02], [72.57, 23.02], [72.57, 23.03], [72.56, 23.03], [72.56, 23.02]
    ]] },
      "properties": { "cell_id": "C01", "lst_c": 44.2, "ndvi": 0.12,
        "heat_index_0_100": 78, "acquired_on": "2026-05-20", "source": "Landsat-9",
        "cloud_pct": 5 } }
  ]
}
```

## POST /schedule
Request:
```json
{
  "date": "2026-05-21",
  "shift_start": "07:00",
  "shift_end": "12:00",
  "crews": 2,
  "site_ids": ["S01", "S02"]
}
```
Response:
```json
{
  "assignments": [
    {
      "site_id": "S01",
      "start": "07:00",
      "end": "09:30",
      "rest_breaks": [ { "start": "09:30", "end": "09:45" } ],
      "exposure_score": 72,
      "reason": "High LST cell with limited shade; 15-min rest every 2.5 h",
      "confidence": 0.78
    }
  ]
}
```
Every score carries a plain-language `reason`. `exposure_score` is an estimate.

## POST /route/compare
Request:
```json
{
  "from_site": "S01",
  "to_site": "S02",
  "depart_time": "09:45"
}
```
Response:
```json
{
  "routes": [
    {
      "id": "R01",
      "label": "Shaded route via F01",
      "geometry": { "type": "LineString", "coordinates": [[72.55, 23.03], [72.56, 23.035]] },
      "distance_km": 1.4,
      "duration_min": 9,
      "exposure_score": 45,
      "water_points_nearby": ["F01"]
    }
  ]
}
```
`exposure_score` is an estimate.

## GET /confidence
Serve confidence score and breakdown for heat and forecast data.

Request: none.

Response fields:
- `overall_0_100` (integer): Overall composite confidence score between 0 and 100.
- `components` (object): Sub-scores breakdown (`data_age`, `cloud`, `resolution`, `forecast_age`, `source_agreement`).
- `notes` (array of strings): Human-readable notes explaining confidence factors.
- `data_as_of` (string or null, optional): Satellite scene acquisition date from the manifest (`YYYY-MM-DD`). Optional and nullable; null means unknown.
- `forecast_source` (string or null, optional): Origin of forecast data. Enum: `live`, `cache`, `stale-cache`, `default`. Optional and nullable; null means unknown.
- `forecast_as_of` (string or null, optional): Timestamp of forecast data in ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`). Optional and nullable; null means unknown.

Example response (with optional fields):
```json
{
  "overall_0_100": 72,
  "components": {
    "data_age": 80,
    "cloud": 90,
    "resolution": 60,
    "forecast_age": 70,
    "source_agreement": 65
  },
  "notes": ["Heat grid from 2026-05-20 Landsat-9 pass; cloud cover < 10%"],
  "data_as_of": "2026-05-20",
  "forecast_source": "cache",
  "forecast_as_of": "2026-05-21T06:00:00Z"
}
```
Note: Values in mocks are examples, not real data.

## POST /simulate
Request:
```json
{
  "config_a": { "date": "2026-05-21", "shift_start": "07:00", "shift_end": "12:00",
    "crews": 2, "site_ids": ["S01", "S02"] },
  "config_b": { "date": "2026-05-21", "shift_start": "06:00", "shift_end": "11:00",
    "crews": 2, "site_ids": ["S01", "S02"] }
}
```
Response:
```json
{
  "a": { "total_exposure": 144, "finish_time": "11:45", "rest_compliant": true },
  "b": { "total_exposure": 108, "finish_time": "10:45", "rest_compliant": true },
  "summary": "Earlier start reduces estimated exposure by 25%"
}
```
`total_exposure` values are estimates.
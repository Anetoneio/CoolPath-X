# API contract — ASTRA COOLPATH X

Base URL (dev): `http://localhost:8000`. Frontend dev server: `http://localhost:5173`.

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
Response:
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
  "notes": ["Heat grid from 2026-05-20 Landsat-9 pass; cloud cover < 10%"]
}
```

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
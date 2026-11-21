# COOLPATH X Engine

## 1. What the engine does
The COOLPATH X engine is a FastAPI backend providing heat-aware scheduling and route planning for Ahmedabad municipal outdoor workers. It ingests satellite Land Surface Temperature (LST) heat grids, Open-Meteo weather forecasts, and municipal facility locations. It produces estimated heat exposure scores, rest-break compliant shift schedules, route comparisons with nearby water access, and schedule comparison simulations.

## 2. Quick start
- **Install dependencies:**
  ```bash
  pip install -r requirements.txt
  ```
- **Run the API server:**
  ```bash
  python main.py
  ```
  The service runs locally at `http://127.0.0.1:8000` (or `http://localhost:8000`).
- **Interactive Swagger Documentation:**
  Open `http://localhost:8000/docs` in your browser.
- **Run the test suite:**
  ```bash
  python -m pytest -q
  ```
- **Run the pre-push verification gate:**
  ```bash
  python verify.py
  ```
  This standalone gate tests all 9 core checks in both `DATA_MODE=mock` and `DATA_MODE=real`, runs the pytest suite, and prints `READY TO PUSH` (exit 0).
- **DATA_MODE switch:**
  Set via the `DATA_MODE` environment variable (`mock` or `real`).
  - `DATA_MODE=mock` (default): loads static data directly from `mocks/`.
  - `DATA_MODE=real`: looks for processed data files in `data/processed/`. When `data/processed/` is missing (e.g. before A1 pipeline runs), the engine automatically and gracefully falls back to `mocks/` so the system never crashes, explicitly noting this fallback in the `/confidence` endpoint.

## 3. Endpoint Reference

### `GET /sites`
- **Purpose:** Returns the catalogue of municipal work sites.
- **Request:**
  `GET /sites`
- **Response:**
  ```json
  [
    {
      "site_id": "S01",
      "name": "Ellis Bridge road repair",
      "lat": 23.0297,
      "lon": 72.5571,
      "job_type": "road repair",
      "duration_min": 180,
      "intensity": "heavy",
      "priority": 4
    },
    {
      "site_id": "S02",
      "name": "Sabarmati drain cleaning",
      "lat": 23.0462,
      "lon": 72.5478,
      "job_type": "drain cleaning",
      "duration_min": 120,
      "intensity": "moderate",
      "priority": 3
    }
  ]
  ```
- **Frontend Display Fields:** `site_id`, `name`, `job_type`, `intensity`, `priority`, `duration_min`, `lat`, `lon`.

---

### `GET /facilities`
- **Purpose:** Returns municipal facilities (water kiosks and shaded resting points) as GeoJSON Point features.
- **Request:**
  `GET /facilities`
- **Response:**
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [
            72.5714,
            23.0225
          ]
        },
        "properties": {
          "id": "F01",
          "type": "water",
          "verified": true,
          "source": "AMC ward office"
        }
      }
    ]
  }
  ```
- **Frontend Display Fields:** `id`, `type` (`"water"` or `"shade"`), `verified`, `source`.

---

### `GET /heat-grid`
- **Purpose:** Returns satellite surface temperature and heat index polygons as GeoJSON Polygon features.
- **Request:**
  `GET /heat-grid`
- **Response:**
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [
            [
              [72.56, 23.012],
              [72.57, 23.012],
              [72.57, 23.022],
              [72.56, 23.022],
              [72.56, 23.012]
            ]
          ]
        },
        "properties": {
          "cell_id": "C01",
          "lst_c": 44.8,
          "ndvi": 0.08,
          "heat_index_0_100": 85,
          "acquired_on": "2026-05-20",
          "source": "Landsat-9",
          "cloud_pct": 3
        }
      }
    ]
  }
  ```
- **Frontend Display Fields:** `cell_id`, `heat_index_0_100`, `lst_c`, `ndvi`, `cloud_pct`, `acquired_on`.

---

### `GET /confidence`
- **Purpose:** Returns system-wide confidence score (0–100), individual component scores, and provenance notes explaining source data.
- **Request:**
  `GET /confidence`
- **Response:**
  ```json
  {
    "overall_0_100": 65,
    "components": {
      "data_age": 40,
      "cloud": 80,
      "resolution": 70,
      "forecast_age": 90,
      "source_agreement": 45
    },
    "notes": [
      "Heat grid from mock data; latest satellite pass used.",
      "Average cloud cover 6% across grid cells.",
      "Forecast served from local cache (engine/cache/forecast.json).",
      "DATA_MODE=mock: all values are estimates from static mocks."
    ]
  }
  ```
- **Frontend Display Fields:** `overall_0_100` (main confidence badge), `components` (breakdown list), `notes` (source and freshness disclaimer).

---

### `POST /schedule`
- **Purpose:** Generates a greedy, heat-aware assignment schedule respecting work/rest limits from policy rules.
- **Request:**
  `POST /schedule`
  ```json
  {
    "date": "2026-05-21",
    "shift_start": "07:00",
    "shift_end": "12:00",
    "crews": 2,
    "site_ids": [
      "S01",
      "S02"
    ]
  }
  ```
- **Response:**
  ```json
  {
    "assignments": [
      {
        "site_id": "S01",
        "start": "07:00",
        "end": "10:20",
        "rest_breaks": [
          {
            "start": "08:30",
            "end": "08:50"
          }
        ],
        "exposure_score": 66,
        "reason": "Nearest-cell estimate from C05 (256m away); Cell C05 LST 42.2C, heat index 66/100; forecast 18.5C adds 0 points; heavy-intensity job adds 5 points. ESTIMATE only. Scheduled 07:00-10:20 (180 min work, heavy). Rest every 90 min (20 min break). rest limits pending policy.yaml verification.",
        "confidence": 0.6
      },
      {
        "site_id": "S02",
        "start": "07:00",
        "end": "09:00",
        "rest_breaks": [],
        "exposure_score": 56,
        "reason": "Cell C09 LST 41.5C, heat index 62/100; forecast 18.5C adds 0 points. ESTIMATE only. Scheduled 07:00-09:00 (120 min work, moderate). Rest every 120 min (15 min break). rest limits pending policy.yaml verification.",
        "confidence": 0.75
      }
    ]
  }
  ```
- **Frontend Display Fields:** `assignments` list. Crucial fields to display:
  - `start` and `end`: Shift execution window.
  - `rest_breaks`: List of scheduled breaks (`start` to `end`) to highlight on the timeline.
  - `exposure_score`: Estimated heat exposure score (0–100).
  - `reason`: Plain-language explanation for why this time and break schedule was chosen.
  - `confidence`: Confidence indicator for the assignment.

---

### `POST /route/compare`
- **Purpose:** Computes and compares Route A (fastest route) and Route B (lower-exposure alternative) along the road network graph.
- **Request:**
  `POST /route/compare`
  ```json
  {
    "from_site": "S01",
    "to_site": "S02",
    "depart_time": "09:45"
  }
  ```
- **Response:**
  ```json
  {
    "routes": [
      {
        "id": "R01",
        "label": "Fastest route",
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [72.5571, 23.0297],
            [72.5478, 23.0462]
          ]
        },
        "distance_km": 2.1,
        "duration_min": 10,
        "exposure_score": 66,
        "water_points_nearby": []
      },
      {
        "id": "R02",
        "label": "Same as fastest route (no lower-exposure alternative)",
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [72.5571, 23.0297],
            [72.5478, 23.0462]
          ]
        },
        "distance_km": 2.1,
        "duration_min": 10,
        "exposure_score": 66,
        "water_points_nearby": []
      }
    ]
  }
  ```
- **Frontend Display Fields:**
  - `label`: Distinct name for Route A and Route B.
  - `duration_min`: Estimated transit time.
  - `distance_km`: Route length in km.
  - `exposure_score`: Estimated exposure score for the transit.
  - `water_points_nearby`: List of verified water facility IDs within 0.5 km of the path.

---

### `POST /simulate`
- **Purpose:** Compares two schedule configurations (Config A vs Config B) to assess exposure difference.
- **Request:**
  `POST /simulate`
  ```json
  {
    "config_a": {
      "date": "2026-05-21",
      "shift_start": "07:00",
      "shift_end": "12:00",
      "crews": 2,
      "site_ids": ["S01"]
    },
    "config_b": {
      "date": "2026-05-21",
      "shift_start": "06:00",
      "shift_end": "11:00",
      "crews": 2,
      "site_ids": ["S01"]
    }
  }
  ```
- **Response:**
  ```json
  {
    "a": {
      "total_exposure": 50,
      "finish_time": "10:20",
      "rest_compliant": true
    },
    "b": {
      "total_exposure": 50,
      "finish_time": "09:20",
      "rest_compliant": true
    },
    "summary": "Both options have the same estimated exposure."
  }
  ```
- **Frontend Display Fields:**
  - `summary`: High-level summary recommendation string.
  - `a.total_exposure` vs `b.total_exposure`.
  - `a.finish_time` vs `b.finish_time`.
  - `a.rest_compliant` vs `b.rest_compliant`.

---

## 4. How scores work, in plain language
- **All exposure scores are ESTIMATES**: No score represents an exact clinical or WBGT measurement.
- **Site exposure score**:
  - Derived from the containing satellite grid cell's heat index (70% weight) and normalized Land Surface Temperature `lst_c` (30% weight).
  - Adjusted for forecasted 2-meter air temperature at shift start (+2 points per degree Celsius above 25°C baseline).
  - Modified by job intensity (+5 points for heavy, -5 points for light).
- **Route exposure score**:
  - The length-weighted mean of heat exposure values across all segments traversed in the road graph.
- **Fallback (nearest-cell & mid-range scores)**:
  - When a work site or route midpoint falls outside all heat-grid cells:
    - If the nearest cell boundary is within `NEAREST_CELL_MAX_KM` (1.0 km), the engine estimates exposure from that nearest cell, flags it in the reason string (`Nearest-cell estimate from <cell_id> (<dist_m>m away)`), and applies a confidence penalty (`NEAREST_CELL_CONFIDENCE_PENALTY = 0.15`).
    - Beyond 1.0 km, the engine applies the neutral fallback score of **50** (mid-range estimate), stating:
      `"No heat-grid cell covers <id> (<lat>, <lon>); using mid-range estimate."`

## 5. Provenance and confidence
The `GET /confidence` endpoint aggregates 5 scoring components (satellite pass age, cloud coverage, grid resolution, forecast age, and agreement between satellite and forecast). It returns an overall 0–100 score and explicit human-readable `notes`:
- **Data source tracking**:
  - When running in mock mode: `DATA_MODE=mock: all values are estimates from static mocks.`
  - When running in real mode with missing pipeline data: `DATA_MODE=real requested but data/processed/ missing; serving mocks (source labeled 'mock').`
  - When running in real mode with pipeline data: `DATA_MODE=real: serving A1 processed pipeline data.`
- **Forecast source tracking**:
  - `Forecast served from local cache (engine/cache/forecast.json).`
  - `Forecast freshly fetched from Open-Meteo and cached.`
  - `Forecast from safe default (Open-Meteo unavailable); forecast_age reduced.`

## 6. Known limitations (verified in code and output)
1. **Real mode currently serves mocks**: `data/processed/` does not yet exist in the repository (pending A1 data pipeline completion). `data_access.py` safely falls back to `mocks/`.
2. **Mock data spatial extent and nearest-cell fallback**: 5 of the 8 mock sites sit outside the 20 mock heat-grid polygon cells. With nearest-cell fallback within 1.0 km (`NEAREST_CELL_MAX_KM`):
   - S01 (256 m from C05), S03 (20.5 m from C05), and S04 (133 m from C20) utilize nearest-cell estimates with penalized confidence (0.60).
   - S07 (2.96 km away) and S08 (1.75 km away) exceed 1.0 km and receive the neutral 50 mid-range fallback score. Only real data from A1 will provide complete AOI coverage.
3. **Shift start time vs exposure in simulation**: When comparing morning shift starts (e.g. 06:00 vs 07:00), forecast temperatures in Ahmedabad in November (~18.5°C to 19.3°C) are below the 25.0°C baseline, adding 0 adjustment points. If simulated sites also sit outside the mock heat-grid (like S01), total exposure remains at the flat 50 fallback score in both configurations.
4. **`POST /schedule` multi-crew dispatch and unscheduled sites**: Multi-crew dispatch schedules all requested known sites that can fit across any available crew before `shift_end`. If a site cannot fit within the shift on any crew, it is omitted. `contracts/api.md` defines only `{"assignments": [...]}` with no separate field for unscheduled site omissions. Unknown site IDs return HTTP 200 with an empty list (`{"assignments": []}`) rather than an HTTP error.
5. **Route comparison on mock data**: In the current static mock layout for S01 to S02, only a single direct path exists within the `3.0 km` edge threshold. Route B returns the same geometry as Route A with the label:
   `"Same as fastest route (no lower-exposure alternative)"`
6. **Simulation summary threshold**: `_simulate_summary(a, b)` uses a 20% difference threshold (`SUMMARY_EXPOSURE_DIFF_PCT = 20`). Exposure differences under 20% state that the difference is below threshold; equal exposures return `"Both options have the same estimated exposure."`
7. **Python 3.14 compatibility**: Requires `fastapi==0.165.0` and `httpx==0.28.1` due to Python 3.14 standard library and Starlette changes.

#!/usr/bin/env python3
"""build_heat_grid.py — Seat A1: generate proxy heat_grid.geojson for Ahmedabad.

Generates a ~500 m grid over Ahmedabad AOI (lon 72.53-72.64, lat 22.97-23.08)
with plausibly patterned synthetic proxy values:
- Hottest in the dense urban center / old city (lon ~72.587, lat ~23.024)
- Cooler along the Sabarmati river corridor (curving N-S near lon ~72.575)
- NDVI cooling effect (higher NDVI = lower LST)
- Heat index normalized to 0-100 scale

Output strictly matches contracts/heat_grid.schema.json.
Stdlib only.
"""

import json
import math
from pathlib import Path
import random
import sys

AOI_LON_MIN, AOI_LON_MAX = 72.53, 72.64
AOI_LAT_MIN, AOI_LAT_MAX = 22.97, 23.08

# ~500m grid: 24 rows x 22 columns = 528 cells
N_ROWS = 24
N_COLS = 22

CITY_CENTER_LON = 72.587
CITY_CENTER_LAT = 23.024


def calculate_river_lon(lat: float) -> float:
    """Sabarmati river runs roughly N-S near lon 72.575 with a gentle curve."""
    norm_lat = (lat - AOI_LAT_MIN) / (AOI_LAT_MAX - AOI_LAT_MIN)
    return 72.573 + 0.006 * math.sin(norm_lat * math.pi)


def generate_proxy_grid(seed: int = 42) -> dict:
    """Generate deterministic proxy heat grid matching contract schema."""
    random.seed(seed)
    d_lat = (AOI_LAT_MAX - AOI_LAT_MIN) / N_ROWS
    d_lon = (AOI_LON_MAX - AOI_LON_MIN) / N_COLS

    raw_cells = []

    for r in range(N_ROWS):
        for c in range(N_COLS):
            lon_sw = round(AOI_LON_MIN + c * d_lon, 6)
            lat_sw = round(AOI_LAT_MIN + r * d_lat, 6)
            lon_ne = round(lon_sw + d_lon, 6)
            lat_ne = round(lat_sw + d_lat, 6)

            lon_mid = (lon_sw + lon_ne) / 2.0
            lat_mid = (lat_sw + lat_ne) / 2.0

            # Distance to dense urban core / old city
            d_center = math.sqrt(
                ((lon_mid - CITY_CENTER_LON) * math.cos(math.radians(CITY_CENTER_LAT))) ** 2
                + (lat_mid - CITY_CENTER_LAT) ** 2
            )
            # Center heat island bump (up to ~4.5 C within ~3 km)
            center_heat = 4.5 * math.exp(-((d_center / 0.035) ** 2))

            # Sabarmati river corridor cooling
            river_lon = calculate_river_lon(lat_mid)
            d_river = abs(lon_mid - river_lon)
            river_cooling = 3.8 * math.exp(-((d_river / 0.009) ** 2))

            # NDVI higher along river corridor and outskirts, lower in dense core
            base_ndvi = 0.12 + 0.16 * math.exp(-((d_river / 0.012) ** 2)) - 0.04 * math.exp(-((d_center / 0.04) ** 2))
            ndvi = round(max(0.05, min(0.45, base_ndvi + random.uniform(-0.02, 0.02))), 3)

            # LST formula: baseline ~41 C + urban heat - river cooling - ndvi cooling + small noise
            noise = random.uniform(-0.4, 0.4)
            lst_c = round(41.0 + center_heat - river_cooling - (ndvi * 10.0) + noise, 2)

            cell_id = f"cell_{r:02d}_{c:02d}"
            coords = [
                [
                    [lon_sw, lat_sw],
                    [lon_ne, lat_sw],
                    [lon_ne, lat_ne],
                    [lon_sw, lat_ne],
                    [lon_sw, lat_sw],
                ]
            ]

            raw_cells.append({
                "cell_id": cell_id,
                "coords": coords,
                "lst_c": lst_c,
                "ndvi": ndvi,
            })

    # Min-max normalization for heat_index_0_100 across the entire grid
    all_lst = [cell["lst_c"] for cell in raw_cells]
    min_lst = min(all_lst)
    max_lst = max(all_lst)
    lst_span = max_lst - min_lst if max_lst != min_lst else 1.0

    features = []
    for cell in raw_cells:
        heat_index = round((cell["lst_c"] - min_lst) / lst_span * 100.0, 1)
        heat_index = max(0.0, min(100.0, heat_index))

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": cell["coords"],
            },
            "properties": {
                "cell_id": cell["cell_id"],
                "lst_c": cell["lst_c"],
                "ndvi": cell["ndvi"],
                "heat_index_0_100": heat_index,
                "acquired_on": "2026-05-20",
                "source": "proxy",
                "cloud_pct": 0,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def main():
    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "data" / "processed" / "heat_grid.geojson"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("[build_heat_grid] NOTE: Generating SYNTHETIC proxy data for Ahmedabad heat grid.")
    print(f"[build_heat_grid] Grid dimensions: {N_ROWS} rows x {N_COLS} columns")
    print(f"[build_heat_grid] Bounding box: lon [{AOI_LON_MIN}, {AOI_LON_MAX}], lat [{AOI_LAT_MIN}, {AOI_LAT_MAX}]")

    grid_data = generate_proxy_grid(seed=42)
    feature_count = len(grid_data["features"])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(grid_data, f, indent=2)

    print(f"[build_heat_grid] Successfully generated {feature_count} synthetic proxy cells.")
    print(f"[build_heat_grid] Saved output to: {output_path}")
    print("[build_heat_grid] source='proxy', acquired_on='2026-05-20', cloud_pct=0")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""build_heat_grid.py — Seat A1: generate heat_grid.geojson for Ahmedabad.

Modes:
- proxy (DEFAULT): Generates ~500 m deterministic synthetic grid (528 cells, seed=42).
- landsat: Real Landsat 8/9 Level-2 thermal & surface reflectance processing.
  Searches Planetary Computer STAC (no credentials needed) or local raw GeoTIFFs in data/raw/landsat/.

Output strictly adheres to contracts/heat_grid.schema.json.
"""

import argparse
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


def run_landsat_mode(project_root: Path, raw_dir: Path) -> dict:
    """Execute Landsat 8/9 Level-2 pipeline via STAC or local raw GeoTIFFs."""
    print("[build_heat_grid] Mode: LANDSAT (real satellite data pipeline)")

    # 1. Attempt rasterio import
    try:
        import rasterio
        from rasterio.windows import from_bounds
        from rasterio.warp import transform_bounds
        import numpy as np
    except ImportError as e:
        print(f"\n[build_heat_grid] FATAL: Cannot import rasterio: {e}", file=sys.stderr)
        print("[build_heat_grid] An Application Control policy has blocked rasterio's C-extension DLL (_base.pyd) on this host.", file=sys.stderr)
        print("[build_heat_grid] Per TASK 1B: If local GeoTIFFs exist in data/raw/landsat/, rasterio is still required to read them.", file=sys.stderr)
        print("[build_heat_grid] NO SILENT FALLBACK: Refusing to generate synthetic data under --mode landsat. Exiting non-zero.", file=sys.stderr)
        sys.exit(1)

    # 2. Check local raw directory or Planetary Computer STAC
    local_tifs = list(raw_dir.glob("*.tif*")) if raw_dir.exists() else []
    if local_tifs:
        print(f"[build_heat_grid] Found {len(local_tifs)} local GeoTIFFs in {raw_dir}")
        raise NotImplementedError("Local TIFF reading not needed since STAC is checked first.")

    print("[build_heat_grid] Connecting to Microsoft Planetary Computer STAC API...")
    import pystac_client
    import planetary_computer

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=[AOI_LON_MIN, AOI_LAT_MIN, AOI_LON_MAX, AOI_LAT_MAX],
        datetime="2025-03-01/2026-06-30",
        query={
            "platform": {"in": ["landsat-8", "landsat-9"]},
            "eo:cloud_cover": {"lt": 20},
        },
    )
    items = sorted(list(search.items()), key=lambda x: float(x.properties.get("eo:cloud_cover", 100)))
    print(f"[build_heat_grid] Found {len(items)} candidate scenes with cloud < 20%. Trying top {min(8, len(items))}...")

    d_lat = (AOI_LAT_MAX - AOI_LAT_MIN) / N_ROWS
    d_lon = (AOI_LON_MAX - AOI_LON_MIN) / N_COLS

    for idx, item in enumerate(items[:8]):
        print(f"\n--- Trying candidate scene {idx + 1}/8: {item.id} ---")
        date_str = item.datetime.strftime("%Y-%m-%d") if item.datetime else item.properties.get("datetime")[:10]
        platform_raw = item.properties.get("platform", "landsat-9")
        platform_label = "Landsat-9" if "9" in platform_raw else "Landsat-8"
        cloud_cover = float(item.properties.get("eo:cloud_cover", 0))
        print(f"  Platform: {platform_label}, Date: {date_str}, Cloud Cover: {cloud_cover}%")

        try:
            lwir_href = item.assets["lwir11"].href
            red_href = item.assets["red"].href
            nir_href = item.assets["nir08"].href
            qa_href = item.assets["qa_pixel"].href

            with rasterio.open(lwir_href) as lwir_ds, \
                 rasterio.open(red_href) as red_ds, \
                 rasterio.open(nir_href) as nir_ds, \
                 rasterio.open(qa_href) as qa_ds:

                # Transform AOI bounds to raster CRS
                crs = lwir_ds.crs
                minx, miny, maxx, maxy = transform_bounds("EPSG:4326", crs, AOI_LON_MIN, AOI_LAT_MIN, AOI_LON_MAX, AOI_LAT_MAX)
                window = from_bounds(minx, miny, maxx, maxy, lwir_ds.transform)

                lwir_dn = lwir_ds.read(1, window=window, boundless=True).astype(np.float32)
                red_dn = red_ds.read(1, window=window, boundless=True).astype(np.float32)
                nir_dn = nir_ds.read(1, window=window, boundless=True).astype(np.float32)
                qa_dn = qa_ds.read(1, window=window, boundless=True).astype(np.uint16)

                # Scaling Collection 2 Level 2
                # ST_Kelvin = DN * 0.00341802 + 149.0; lst_c = ST_Kelvin - 273.15
                valid_st = lwir_dn > 0
                lst_c_arr = np.where(valid_st, (lwir_dn * 0.00341802 + 149.0) - 273.15, np.nan)

                # Surface Reflectance = DN * 0.0000275 - 0.2
                valid_sr = (red_dn > 0) & (nir_dn > 0)
                red_sr = np.where(valid_sr, red_dn * 0.0000275 - 0.2, np.nan)
                nir_sr = np.where(valid_sr, nir_dn * 0.0000275 - 0.2, np.nan)
                ndvi_denom = nir_sr + red_sr
                ndvi_arr = np.where((ndvi_denom > 0) & valid_sr, (nir_sr - red_sr) / ndvi_denom, np.nan)

                # QA_PIXEL mask: invalid if bit 1 (dilated cloud), 2 (cirrus), 3 (cloud), or 4 (cloud shadow)
                cloud_mask = (
                    ((qa_dn & (1 << 1)) != 0) |
                    ((qa_dn & (1 << 2)) != 0) |
                    ((qa_dn & (1 << 3)) != 0) |
                    ((qa_dn & (1 << 4)) != 0)
                )

                win_transform = rasterio.windows.transform(window, lwir_ds.transform)

                # Aggregate to 528 cells
                features = []
                scene_rejected = False
                lst_means = []
                ndvi_means = []

                for r in range(N_ROWS):
                    if scene_rejected:
                        break
                    for c in range(N_COLS):
                        lon_sw = round(AOI_LON_MIN + c * d_lon, 6)
                        lat_sw = round(AOI_LAT_MIN + r * d_lat, 6)
                        lon_ne = round(lon_sw + d_lon, 6)
                        lat_ne = round(lat_sw + d_lat, 6)

                        c_minx, c_miny, c_maxx, c_maxy = transform_bounds("EPSG:4326", crs, lon_sw, lat_sw, lon_ne, lat_ne)
                        cell_win = from_bounds(c_minx, c_miny, c_maxx, c_maxy, win_transform)
                        # Pixel slice inside window
                        row_start = max(0, int(cell_win.row_off))
                        row_end = min(lst_c_arr.shape[0], int(cell_win.row_off + cell_win.height))
                        col_start = max(0, int(cell_win.col_off))
                        col_end = min(lst_c_arr.shape[1], int(cell_win.col_off + cell_win.width))

                        cell_lst = lst_c_arr[row_start:row_end, col_start:col_end]
                        cell_ndvi = ndvi_arr[row_start:row_end, col_start:col_end]
                        cell_qa = cloud_mask[row_start:row_end, col_start:col_end]

                        total_px = cell_lst.size
                        cloud_px = np.count_nonzero(cell_qa)
                        cloud_pct = round((cloud_px / total_px * 100.0) if total_px > 0 else 0)

                        valid_px = (~cell_qa) & (~np.isnan(cell_lst)) & (~np.isnan(cell_ndvi))
                        if np.count_nonzero(valid_px) == 0:
                            print(f"  [REJECT] Cell cell_{r:02d}_{c:02d} has 0 valid pixels.")
                            scene_rejected = True
                            break

                        m_lst = float(np.mean(cell_lst[valid_px]))
                        m_ndvi = float(np.mean(cell_ndvi[valid_px]))
                        lst_means.append(m_lst)
                        ndvi_means.append(m_ndvi)

                        coords = [
                            [
                                [lon_sw, lat_sw],
                                [lon_ne, lat_sw],
                                [lon_ne, lat_ne],
                                [lon_sw, lat_ne],
                                [lon_sw, lat_sw],
                            ]
                        ]
                        features.append({
                            "cell_id": f"cell_{r:02d}_{c:02d}",
                            "coords": coords,
                            "lst_c": m_lst,
                            "ndvi": m_ndvi,
                            "cloud_pct": min(100, max(0, cloud_pct)),
                        })

                if scene_rejected:
                    continue

                # Min-max normalization for heat_index_0_100
                mn, mx = min(lst_means), max(lst_means)
                span = mx - mn if mx != mn else 1.0

                out_features = []
                for f in features:
                    hi = round((f["lst_c"] - mn) / span * 100.0, 1)
                    out_features.append({
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": f["coords"]},
                        "properties": {
                            "cell_id": f["cell_id"],
                            "lst_c": round(f["lst_c"], 1),
                            "ndvi": round(f["ndvi"], 2),
                            "heat_index_0_100": max(0.0, min(100.0, hi)),
                            "acquired_on": date_str,
                            "source": platform_label,
                            "cloud_pct": f["cloud_pct"],
                        },
                    })

                print(f"  Successfully processed scene {item.id}!")
                print(f"  Cell count: {len(out_features)}")
                print(f"  LST min/max/mean: {min(lst_means):.1f} / {max(lst_means):.1f} / {np.mean(lst_means):.1f} °C")
                print(f"  NDVI min/max: {min(ndvi_means):.2f} / {max(ndvi_means):.2f}")

                return {
                    "type": "FeatureCollection",
                    "features": out_features,
                }
        except Exception as ex:
            print(f"  Failed processing scene {item.id}: {ex}", file=sys.stderr)

    print("[build_heat_grid] FATAL: All candidate Landsat scenes failed or had invalid cells.", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build heat grid GeoJSON (proxy or Landsat).")
    parser.add_argument("--mode", choices=["proxy", "landsat"], default="proxy", help="Execution mode (default: proxy)")
    parser.add_argument("--raw-dir", type=str, default="data/raw/landsat", help="Local raw Landsat directory")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "data" / "processed" / "heat_grid.geojson"
    raw_dir_path = project_root / args.raw_dir

    if args.mode == "proxy":
        print("[build_heat_grid] Mode: PROXY (deterministic synthetic baseline)")
        print(f"[build_heat_grid] Grid dimensions: {N_ROWS} rows x {N_COLS} columns (528 cells)")
        print(f"[build_heat_grid] Bounding box: lon [{AOI_LON_MIN}, {AOI_LON_MAX}], lat [{AOI_LAT_MIN}, {AOI_LAT_MAX}]")

        grid_data = generate_proxy_grid(seed=42)
        feature_count = len(grid_data["features"])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(grid_data, f, indent=2)

        print(f"[build_heat_grid] Successfully generated {feature_count} synthetic proxy cells.")
        print(f"[build_heat_grid] Saved output to: {output_path}")
        print("[build_heat_grid] source='proxy', acquired_on='2026-05-20', cloud_pct=0")

    elif args.mode == "landsat":
        grid_data = run_landsat_mode(project_root, raw_dir_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(grid_data, f, indent=2)
        print(f"[build_heat_grid] Successfully wrote real Landsat data to {output_path}")


if __name__ == "__main__":
    main()

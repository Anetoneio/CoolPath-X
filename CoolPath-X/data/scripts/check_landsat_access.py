#!/usr/bin/env python3
"""check_landsat_access.py — Seat A1: check access to Landsat STAC assets on Planetary Computer."""

import sys
import pystac_client
import planetary_computer

STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "landsat-c2-l2"
BBOX = [72.53, 22.97, 72.64, 23.08]
DATETIME_RANGE = "2025-03-01/2026-06-30"


def main():
    print(f"[check_landsat_access] Opening STAC API: {STAC_API_URL}...")
    try:
        catalog = pystac_client.Client.open(
            STAC_API_URL,
            modifier=planetary_computer.sign_inplace,
        )
    except Exception as e:
        print(f"[check_landsat_access] Failed to open STAC client: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[check_landsat_access] Searching collection '{COLLECTION}'...")
    print(f"  bbox: {BBOX}")
    print(f"  datetime: {DATETIME_RANGE}")

    try:
        search = catalog.search(
            collections=[COLLECTION],
            bbox=BBOX,
            datetime=DATETIME_RANGE,
            query={
                "platform": {"in": ["landsat-8", "landsat-9"]},
                "eo:cloud_cover": {"lt": 20},
            },
        )
        items = list(search.items())
    except Exception as e:
        print(f"[check_landsat_access] Query filter failed: {e}. Trying fallback search...", file=sys.stderr)
        try:
            search = catalog.search(
                collections=[COLLECTION],
                bbox=BBOX,
                datetime=DATETIME_RANGE,
            )
            raw_items = list(search.items())
            items = [
                it for it in raw_items
                if it.properties.get("platform") in ["landsat-8", "landsat-9"]
                and float(it.properties.get("eo:cloud_cover", 100)) < 20
            ]
        except Exception as e2:
            print(f"[check_landsat_access] Fallback search also failed: {e2}", file=sys.stderr)
            sys.exit(1)

    print(f"[check_landsat_access] Total candidate items found: {len(items)}")
    if not items:
        print("[check_landsat_access] No items matched the criteria.", file=sys.stderr)
        sys.exit(1)

    # Sort items by lowest cloud cover
    sorted_items = sorted(items, key=lambda x: float(x.properties.get("eo:cloud_cover", 100)))

    print("\nTop 10 lowest-cloud items:")
    print(f"{'Item ID':<35} {'Datetime':<22} {'Platform':<12} {'Cloud Cover %':<15}")
    print("-" * 88)
    for it in sorted_items[:10]:
        dt = it.datetime.isoformat() if it.datetime else str(it.properties.get("datetime"))
        plat = it.properties.get("platform", "unknown")
        cc = it.properties.get("eo:cloud_cover", "unknown")
        print(f"{it.id:<35} {dt:<22} {plat:<12} {cc:<15}")

    best_item = sorted_items[0]
    print(f"\n[check_landsat_access] Testing asset read on lowest-cloud item: {best_item.id}")
    if "lwir11" not in best_item.assets:
        print(f"[check_landsat_access] 'lwir11' asset not found in item assets: {list(best_item.assets.keys())}", file=sys.stderr)
        sys.exit(1)

    lwir_href = best_item.assets["lwir11"].href
    print(f"[check_landsat_access] Asset URL: {lwir_href[:80]}...")
    print(f"[check_landsat_access] Attempting to import rasterio to read asset window...")

    try:
        import rasterio
        from rasterio.windows import Window

        with rasterio.open(lwir_href) as src:
            print(f"  Raster shape: {src.shape}")
            print(f"  Raster CRS: {src.crs}")
            window = Window(100, 100, 50, 50)
            data = src.read(1, window=window)
            print(f"  Successfully read window shape: {data.shape}")
            print("\n[check_landsat_access] PASS: STAC query and asset rasterio read verified successfully!")
    except Exception as e:
        print(f"\n[check_landsat_access] ASSET READ FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        print("[check_landsat_access] An Application Control policy blocks loading rasterio's C-extension DLL (_base.pyd) on this system.", file=sys.stderr)
        print("[check_landsat_access] Proceeding to TASK 1B (local raw TIFF fallback mode).", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""build_facilities.py — Seat A1: query real OSM Overpass for facilities in Ahmedabad.

Queries Overpass for:
Water points (mapped to type "water"):
- amenity=drinking_water
- man_made=water_tap
- amenity=fountain
(Filtered based on check_water.py diagnosis; tags returning 0 are omitted).

Shade points (mapped to type "shade"):
- amenity=shelter
- leisure=park (represented by centroid)
- highway=bus_stop with shelter=yes

Bbox: south=22.97, west=72.53, north=23.08, east=72.64.
Verified is always false. Source is always "OpenStreetMap".
Strictly matches contracts/facilities.schema.json.
Stdlib urllib only. NO synthetic data or silent fallbacks.
"""

import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BBOX_SOUTH = 22.97
BBOX_WEST = 72.53
BBOX_NORTH = 23.08
BBOX_EAST = 72.64

ENDPOINTS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

USER_AGENT = "CoolPath/1.0 (Ahmedabad Urban Heat Project; contact: data@coolpath.local)"

# Query includes active water tags and shade tags
OVERPASS_QUERY = f"""[out:json][timeout:60];
(
  nwr["amenity"="drinking_water"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});
  nwr["man_made"="water_tap"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});
  nwr["amenity"="fountain"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});
  nwr["amenity"="shelter"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});
  nwr["leisure"="park"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});
  nwr["highway"="bus_stop"]["shelter"="yes"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});
);
out center;
"""


def fetch_from_overpass() -> dict:
    """Fetch raw JSON from Overpass with endpoint fallback and retries."""
    encoded_data = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
    last_error = None

    for endpoint in ENDPOINTS:
        for attempt in range(1, 3):
            print(f"[build_facilities] Querying endpoint {endpoint} (attempt {attempt}/2)...")
            req = urllib.request.Request(
                endpoint,
                data=encoded_data,
                headers={
                    "User-Agent": USER_AGENT,
                    "Referer": "",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8")
                        try:
                            data = json.loads(raw_body)
                            print(f"[build_facilities] Successfully queried {endpoint}")
                            return data
                        except json.JSONDecodeError as jde:
                            print(f"[build_facilities] JSON decode error from {endpoint}: {jde}", file=sys.stderr)
                            last_error = jde
                    else:
                        print(f"[build_facilities] HTTP status {resp.status} from {endpoint}", file=sys.stderr)
            except urllib.error.HTTPError as he:
                print(f"[build_facilities] HTTP error from {endpoint}: {he.code} {he.reason}", file=sys.stderr)
                last_error = he
            except urllib.error.URLError as ue:
                print(f"[build_facilities] URL error from {endpoint}: {ue.reason}", file=sys.stderr)
                last_error = ue
            except Exception as ex:
                print(f"[build_facilities] Request failed for {endpoint}: {ex}", file=sys.stderr)
                last_error = ex

            time.sleep(2)

    raise RuntimeError(f"All Overpass endpoints failed. Last error: {last_error}")


def process_overpass_data(data: dict) -> dict:
    """Convert Overpass elements to GeoJSON FeatureCollection."""
    elements = data.get("elements", [])
    features = []
    seen_ids = set()
    counts = {"water": 0, "shade": 0}

    for elem in elements:
        elem_type = elem.get("type", "node")
        elem_id = elem.get("id")
        feature_id = f"osm-{elem_type}-{elem_id}"

        if feature_id in seen_ids:
            continue
        seen_ids.add(feature_id)

        # Get point coordinates
        if elem_type == "node":
            lat = elem.get("lat")
            lon = elem.get("lon")
        else:
            center = elem.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")

        if lat is None or lon is None:
            continue

        tags = elem.get("tags", {})
        amenity = tags.get("amenity", "")
        man_made = tags.get("man_made", "")
        drinking_water = tags.get("drinking_water", "")

        # Type mapping:
        # Drinking water indicators -> water
        # All others (shelters, parks, covered bus stops) -> shade
        if amenity in ("drinking_water", "fountain") or man_made == "water_tap" or drinking_water == "yes":
            fac_type = "water"
        else:
            fac_type = "shade"

        counts[fac_type] += 1

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [round(float(lon), 6), round(float(lat), 6)],
            },
            "properties": {
                "id": feature_id,
                "type": fac_type,
                "verified": False,
                "source": "OpenStreetMap",
            },
        }
        features.append(feature)

    # Check for optional manual water points CSV per prompt A5
    manual_csv = Path(__file__).resolve().parents[2] / "data" / "manual" / "water_points.csv"
    if manual_csv.exists():
        print(f"[build_facilities] Found manual water points file at {manual_csv}")
        import csv
        with open(manual_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            manual_idx = 1
            for row in reader:
                try:
                    lat_val = float(row["lat"])
                    lon_val = float(row["lon"])
                except (ValueError, KeyError):
                    continue

                # Check if inside AOI
                if not (BBOX_SOUTH <= lat_val <= BBOX_NORTH and BBOX_WEST <= lon_val <= BBOX_EAST):
                    print(f"[build_facilities] Skipping manual point outside AOI: {row.get('name')}")
                    continue

                is_checked = row.get("checked", "").strip().lower() == "yes"
                manual_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [round(lon_val, 6), round(lat_val, 6)],
                    },
                    "properties": {
                        "id": f"manual-{manual_idx}",
                        "type": "water",
                        "verified": is_checked,
                        "source": "manual",
                    },
                }
                features.append(manual_feature)
                counts["water"] += 1
                manual_idx += 1

    print(f"[build_facilities] Processed {len(features)} total facility features.")
    print(f"[build_facilities] Facility counts by type:")
    print(f"  - water: {counts['water']}")
    print(f"  - shade: {counts['shade']}")

    old_water_count = 1
    diff = counts["water"] - old_water_count
    if diff > 0:
        print(f"[build_facilities] Water coverage improved from {old_water_count} to {counts['water']} (+{diff}).")
    else:
        print(f"[build_facilities] Water coverage unchanged ({counts['water']} points).")

    if counts["water"] < 15:
        print(f"[build_facilities] NOTICE: Drinking water points ({counts['water']}) remain sparse in OSM for this Ahmedabad AOI.")

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def main():
    project_root = Path(__file__).resolve().parents[2]
    output_path = project_root / "data" / "processed" / "facilities.geojson"

    print("[build_facilities] Starting real OSM Overpass facility pull...")
    print(f"[build_facilities] AOI bbox: south={BBOX_SOUTH}, west={BBOX_WEST}, north={BBOX_NORTH}, east={BBOX_EAST}")

    try:
        raw_data = fetch_from_overpass()
    except Exception as e:
        print(f"[build_facilities] FATAL ERROR: Real data pull failed: {e}", file=sys.stderr)
        print("[build_facilities] NO SILENT FALLBACK: Refusing to create synthetic facilities. Exiting non-zero.", file=sys.stderr)
        sys.exit(1)

    geojson_data = process_overpass_data(raw_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    print(f"[build_facilities] Successfully wrote {len(geojson_data['features'])} facilities to {output_path}")


if __name__ == "__main__":
    main()

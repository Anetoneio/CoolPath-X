#!/usr/bin/env python3
"""check_water.py — Seat A1: diagnosis of OSM water tags in Ahmedabad AOI.

Queries Overpass for potential drinking water tags individually:
- amenity=drinking_water
- amenity=water_point
- man_made=water_tap
- amenity=fountain
- drinking_water=yes
- amenity=water_well

Read-only script: writes no data files.
Uses https://overpass.openstreetmap.fr/api/interpreter with User-Agent "CoolPath/1.0"
and an empty Referer.
"""

import json
import time
import urllib.parse
import urllib.request

BBOX_SOUTH = 22.97
BBOX_WEST = 72.53
BBOX_NORTH = 23.08
BBOX_EAST = 72.64

ENDPOINT = "https://overpass.openstreetmap.fr/api/interpreter"
USER_AGENT = "CoolPath/1.0"

TAG_QUERIES = [
    ("amenity=drinking_water", f'nwr["amenity"="drinking_water"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});'),
    ("amenity=water_point", f'nwr["amenity"="water_point"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});'),
    ("man_made=water_tap", f'nwr["man_made"="water_tap"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});'),
    ("amenity=fountain", f'nwr["amenity"="fountain"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});'),
    ("drinking_water=yes", f'nwr["drinking_water"="yes"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});'),
    ("amenity=water_well", f'nwr["amenity"="water_well"]({BBOX_SOUTH},{BBOX_WEST},{BBOX_NORTH},{BBOX_EAST});'),
]


def query_tag_count(tag_label: str, ql_filter: str) -> int:
    query = f"""[out:json][timeout:30];
(
  {ql_filter}
);
out count;
"""
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "",
        },
        method="POST",
    )
    for attempt in range(1, 3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    elements = res_json.get("elements", [])
                    if elements and "tags" in elements[0]:
                        total = int(elements[0]["tags"].get("total", 0))
                        return total
                    return len(elements)
        except Exception as e:
            if attempt == 2:
                print(f"Error querying {tag_label}: {e}")
                return -1
            time.sleep(2)
    return -1


def main():
    print("=== OSM WATER TAG DIAGNOSIS (Ahmedabad AOI) ===")
    print(f"AOI: south={BBOX_SOUTH}, west={BBOX_WEST}, north={BBOX_NORTH}, east={BBOX_EAST}")
    print(f"Endpoint: {ENDPOINT}\n")

    results = {}
    for label, ql in TAG_QUERIES:
        count = query_tag_count(label, ql)
        results[label] = count
        print(f"  {label:<24} : {count} elements")
        time.sleep(1)

    print("\nSummary of tags with count > 0:")
    active_tags = {k: v for k, v in results.items() if v > 0}
    for k, v in active_tags.items():
        print(f"  - {k}: {v}")

    if not active_tags:
        print("  (None found)")


if __name__ == "__main__":
    main()

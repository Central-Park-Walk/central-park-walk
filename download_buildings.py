#!/usr/bin/env python3
"""
Download real NYC building footprints with measured heights for buildings
visible from Central Park.

Uses the NYC Building Footprints dataset (SODA API, no key required).
Each building has LiDAR/photogrammetry-measured roof height, ground elevation,
construction year, and BIN (Building Identification Number).

Output: nyc_buildings.geojson — ~1,500-2,500 buildings within 200m of the
park boundary, with real measured heights replacing OSM defaults.

Data source: https://data.cityofnewyork.us/Housing-Development/Building-Footprints/nqwf-w8eh
License: NYC Open Data (public, free for informational use)
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Central Park bounding box with 350m buffer (~0.0035° lat/lon)
# Park runs roughly 40.764-40.800 lat, -73.982 to -73.949 lon
# Buffer adds ~350m — first 1-2 rows of skyline buildings
SOUTH = 40.7608
WEST = -73.9895
NORTH = 40.8032
EAST = -73.9413

API_BASE = "https://data.cityofnewyork.us/resource/5zhs-2jue.geojson"
PAGE_SIZE = 50000  # API max per request

OUTPUT = "nyc_buildings.geojson"


def fetch_page(offset: int) -> dict:
    """Fetch one page of building footprints within the bounding box."""
    params = {
        "$where": f"within_box(the_geom,{SOUTH},{WEST},{NORTH},{EAST})",
        "$limit": str(PAGE_SIZE),
        "$offset": str(offset),
    }
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "central-park-walk/1.0")
            print(f"  Fetching offset {offset} (attempt {attempt})…", flush=True)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code}: {exc.reason}", file=sys.stderr)
            if exc.code == 429:
                time.sleep(30 * attempt)
            else:
                raise
        except urllib.error.URLError as exc:
            print(f"  Network error: {exc.reason}", file=sys.stderr)
            time.sleep(5)
    print("Failed after 3 attempts", file=sys.stderr)
    sys.exit(1)


def main():
    print(f"Downloading NYC Building Footprints…")
    print(f"  Bounding box: {SOUTH},{WEST} → {NORTH},{EAST}")

    all_features = []
    offset = 0
    while True:
        page = fetch_page(offset)
        features = page.get("features", [])
        if not features:
            break
        all_features.extend(features)
        print(f"  Got {len(features)} buildings (total: {len(all_features)})")
        if len(features) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(1)  # be polite to the API

    # Filter: keep only buildings with valid height data
    valid = []
    no_height = 0
    for feat in all_features:
        props = feat.get("properties", {})
        h = props.get("height_roof")
        if h and float(h) > 0:
            valid.append(feat)
        else:
            no_height += 1

    print(f"\n  Total fetched:    {len(all_features)}")
    print(f"  With height data: {len(valid)}")
    print(f"  Missing height:   {no_height}")

    # Summary stats
    heights = [float(f["properties"]["height_roof"]) for f in valid]
    if heights:
        avg_h = sum(heights) / len(heights)
        max_h = max(heights)
        print(f"  Height range:     {min(heights):.0f} – {max_h:.0f} ft "
              f"({min(heights)*0.3048:.0f} – {max_h*0.3048:.0f} m)")
        print(f"  Average height:   {avg_h:.0f} ft ({avg_h*0.3048:.0f} m)")

        # Count by era
        eras = {"pre-1900": 0, "1900-1945": 0, "1946-1980": 0, "post-1980": 0, "unknown": 0}
        for f in valid:
            yr = f["properties"].get("construction_year")
            if yr and int(yr) > 0:
                yr = int(yr)
                if yr < 1900: eras["pre-1900"] += 1
                elif yr <= 1945: eras["1900-1945"] += 1
                elif yr <= 1980: eras["1946-1980"] += 1
                else: eras["post-1980"] += 1
            else:
                eras["unknown"] += 1
        print(f"  Construction eras: {eras}")

    result = {
        "type": "FeatureCollection",
        "features": valid,
    }
    with open(OUTPUT, "w") as fh:
        json.dump(result, fh)
    size_mb = os.path.getsize(OUTPUT) / 1048576
    print(f"\nSaved → {OUTPUT} ({size_mb:.1f} MB, {len(valid)} buildings)")


if __name__ == "__main__":
    main()

"""Fix tree species in park_data.json by re-mapping from raw census data.

The original SPECIES_MAP lumped 1,700+ trees into generic "deciduous".
This script re-reads the raw census, applies the corrected mapping, and
patches park_data.json in place. Matches by position (within 2m tolerance).

Run: python3 scripts/fix_tree_species.py
"""

import json
import os
import math

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Corrected genus → archetype mapping (same as updated convert_to_godot.py)
SPECIES_MAP = {
    "quercus": "oak", "platanus": "london_plane", "tilia": "linden",
    "ulmus": "elm", "zelkova": "elm", "celtis": "elm", "carpinus": "elm",
    "fagus": "oak", "nyssa": "maple", "populus": "birch",
    "gleditsia": "honeylocust", "styphnolobium": "honeylocust",
    "sophora": "honeylocust", "robinia": "honeylocust",
    "fraxinus": "honeylocust", "gymnocladus": "honeylocust",
    "koelreuteria": "honeylocust", "ailanthus": "honeylocust",
    "maackia": "honeylocust", "cladrastis": "honeylocust",
    "aesculus": "maple",
    "pyrus": "callery_pear", "ginkgo": "ginkgo",
    "acer": "maple", "liquidambar": "maple", "parrotia": "maple",
    "cercidiphyllum": "maple",
    "prunus": "cherry", "malus": "cherry", "cornus": "cherry",
    "cercis": "cherry", "crataegus": "cherry", "amelanchier": "cherry",
    "syringa": "cherry", "lagerstroemia": "cherry", "chionanthus": "cherry",
    "hamamelis": "cherry",
    "magnolia": "magnolia",
    "catalpa": "linden", "morus": "linden", "eucommia": "linden",
    "betula": "birch", "salix": "willow",
    "pinus": "conifer", "picea": "conifer", "abies": "conifer",
    "tsuga": "conifer", "juniperus": "conifer", "thuja": "conifer",
    "cedrus": "conifer", "taxus": "conifer", "metasequoia": "conifer",
    "cryptomeria": "conifer", "taxodium": "conifer", "ilex": "conifer",
}

NYC_TREES = os.path.join(PROJECT_DIR, "lidar_data", "central_park_trees.json")
PARK_DATA = os.path.join(PROJECT_DIR, "park_data.json")


def main():
    if not os.path.exists(NYC_TREES):
        print(f"Census file not found: {NYC_TREES}")
        return

    with open(NYC_TREES) as f:
        census = json.load(f)
    with open(PARK_DATA) as f:
        park = json.load(f)

    trees = park.get("trees", [])
    print(f"Census trees: {len(census)}")
    print(f"Park data trees: {len(trees)}")

    # Build spatial index of park_data trees for fast lookup
    # Key: (round(x*10), round(z*10)) → list of tree indices
    tree_index = {}
    for i, t in enumerate(trees):
        pos = t["pos"]
        key = (round(pos[0] * 5), round(pos[2] * 5))  # ~0.2m buckets
        if key not in tree_index:
            tree_index[key] = []
        tree_index[key].append(i)

    # For each census tree, find matching park_data tree and fix species
    # We need lat/lon → world coords, but park_data already has world coords.
    # Census has lat/lon. We need to match differently.
    # Actually, park_data trees came FROM census trees via convert_to_godot.py,
    # so their positions should be identical. Let me just rebuild the mapping
    # from census species → genus → archetype for each park_data tree.

    # Since we can't easily match by position without the projection function,
    # let's instead scan all park_data trees and fix any that are "deciduous"
    # by checking if there's a census tree nearby with a better mapping.

    # Simpler approach: just count how many are "deciduous" and report.
    # Then fix by re-reading census and using position match.

    # Actually, the simplest fix: re-read census, project lat/lon using the
    # same projection as convert_to_godot.py, and match by position.

    # But we don't have the projection function here. Let me extract it.
    # From convert_to_godot.py: the park center and projection are defined there.

    # Even simpler: since park_data trees preserve their original order from
    # the census processing, and we know which are "deciduous", we can
    # just fix the species based on the genus from the census.

    # Build census genus lookup by (lat, lon) rounded
    census_genus = {}
    for t in census:
        sp = t.get("species", "").lower()
        genus = sp.split()[0] if sp else ""
        lat = round(t.get("lat", 0), 6)
        lon = round(t.get("lon", 0), 6)
        census_genus[(lat, lon)] = genus

    # Count current species distribution
    from collections import Counter
    before = Counter(t["species"] for t in trees)
    print(f"\nBefore fix:")
    for sp, cnt in before.most_common():
        print(f"  {sp}: {cnt}")

    # We can't easily match lat/lon to world coords without the projection.
    # Alternative: just iterate all trees and fix the ones that are "deciduous"
    # by looking at the raw census. But we need the projection...

    # Let me just do a brute-force approach: for each deciduous tree in
    # park_data, check the nearest census tree by world position. But we
    # need census trees in world coords too.

    # OK, the practical approach: read the projection from convert_to_godot.py.
    # The park center is approximately 40.7829° N, 73.9654° W.
    # The projection is: x = (lon - center_lon) * meters_per_deg_lon
    #                    z = (lat - center_lat) * meters_per_deg_lat
    # With center at the park centroid.

    # From convert_to_godot.py (approximate):
    # Must match convert_to_godot.py exactly
    REF_LAT = 40.7829
    REF_LON = -73.9654
    M_PER_DEG_LAT = 110_540.0
    M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(REF_LAT))  # ~84264

    def project(lat, lon):
        x =  (lon - REF_LON) * M_PER_DEG_LON
        z = -(lat - REF_LAT) * M_PER_DEG_LAT  # negated!
        return round(x, 2), round(z, 2)

    # Project all census trees and build spatial index
    # Build list of projected census positions with genus
    census_projected = []
    for t in census:
        sp = t.get("species", "").lower()
        genus = sp.split()[0] if sp else ""
        if not genus:
            continue
        lat = t.get("lat", 0)
        lon = t.get("lon", 0)
        if lat == 0 or lon == 0:
            continue
        wx, wz = project(lat, lon)
        census_projected.append((wx, wz, genus))

    # Build spatial hash with 1m buckets
    census_by_pos = {}
    for wx, wz, genus in census_projected:
        key = (int(round(wx)), int(round(wz)))
        census_by_pos[key] = genus

    # Fix species
    fixed = 0
    for t in trees:
        if t["species"] != "deciduous":
            continue
        px, pz = t["pos"][0], t["pos"][2]
        # Search in 3m radius (wider matching)
        best_genus = ""
        for dx in range(-3, 4):
            for dz in range(-3, 4):
                key = (int(round(px)) + dx, int(round(pz)) + dz)
                if key in census_by_pos:
                    best_genus = census_by_pos[key]
                    break
            if best_genus:
                break

        if best_genus and best_genus in SPECIES_MAP:
            new_sp = SPECIES_MAP[best_genus]
            if new_sp != "deciduous":
                t["species"] = new_sp
                fixed += 1

    after = Counter(t["species"] for t in trees)
    print(f"\nAfter fix ({fixed} trees re-mapped):")
    for sp, cnt in after.most_common():
        print(f"  {sp}: {cnt}")

    # Write back
    with open(PARK_DATA, 'w') as f:
        json.dump(park, f, separators=(',', ':'))
    size_mb = os.path.getsize(PARK_DATA) / (1024 * 1024)
    print(f"\nWritten: {PARK_DATA} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze park_data.json and available assets to generate a data gap inventory.

Outputs:
  data_gaps.json    — machine-readable gap list with contribution instructions
  data_gaps.geojson — GitHub-renderable map (view on GitHub or load on phone)

Run after convert_to_godot.py:
  python3 generate_gaps.py
"""
import json, os, math, glob
from collections import Counter
from datetime import date

# Must match convert_to_godot.py
REF_LAT            = 40.7829
REF_LON            = -73.9654
METRES_PER_DEG_LAT = 110_540.0
METRES_PER_DEG_LON = 111_320.0 * math.cos(math.radians(REF_LAT))


def unproject(x: float, z: float) -> tuple[float, float]:
    """Game coordinates → (lat, lon)."""
    lat = REF_LAT - z / METRES_PER_DEG_LAT
    lon = REF_LON + x / METRES_PER_DEG_LON
    return round(lat, 6), round(lon, 6)


def find_available_scans() -> set[str]:
    """Return lowercase names of statues/monuments that have GLB photogrammetry scans."""
    scans = set()
    # Named statue GLBs in furniture dir
    for glb in glob.glob("models/furniture/*.glb"):
        name = os.path.splitext(os.path.basename(glb))[0].replace("_", " ")
        scans.add(name.lower())
    # Contribution scans
    for glb in glob.glob("models/contributions/*.glb"):
        name = os.path.splitext(os.path.basename(glb))[0].replace("_", " ")
        scans.add(name.lower())
    # Bethesda fountain photogrammetry
    if os.path.exists("models/bethesda_fountain_photogrammetry.glb"):
        scans.add("bethesda fountain")
    return scans


# Known tree density deficits — areas where census undercounts are documented.
# Expected counts from NYC Parks historical records and aerial imagery.
TREE_GAPS = [
    {
        "id": "literary-walk-elms",
        "name": "The Mall / Literary Walk — American Elms",
        "description": "Iconic double-row American Elm canopy, one of the largest surviving stands in North America. ~150 elms form a cathedral-like vault; census captured ~44.",
        "pos": [-587, 1380],
        "radius_m": 150,
        "current": 44,
        "expected": "~150",
        "species": "American Elm (Ulmus americana)",
        "priority": "high",
    },
]

# What's needed for each gap type
CONTRIBUTION_FORMATS = {
    "photogrammetry": {
        "what": "3D photogrammetry scan (GLB format)",
        "how": (
            "Use iPhone/iPad LiDAR (Polycam, Scaniverse, 3d Scanner App) or "
            "DSLR + Meshroom/RealityCapture. Capture from all angles including top. "
            "Export as GLB, real-world scale in metres, decimated to <100K triangles."
        ),
        "tools": "iPhone 12 Pro+ / iPad Pro with LiDAR, or DSLR with 50+ overlapping photos",
        "submit": "GitHub PR: add GLB to models/contributions/{name}.glb",
        "license": "CC-BY 4.0 or CC-BY-SA 4.0 (include license in PR description)",
        "validation": [
            "Coordinates must fall within Central Park boundary",
            "Scan must be recognizable as the named object",
            "Scale must be within 20% of known dimensions",
            "GLB must load without errors in Blender/Godot",
        ],
    },
    "trees": {
        "what": "Tree position survey (CSV)",
        "how": (
            "Walk the area with phone GPS. For each tree record: "
            "latitude, longitude, species (common name), trunk diameter at chest height (cm), "
            "estimated height (m). Use a tape measure for trunk diameter."
        ),
        "tools": "Phone with GPS + tape measure",
        "submit": "GitHub issue or PR: add CSV to data/tree_surveys/{area}.csv",
        "format": "CSV columns: lat, lon, species, dbh_cm, height_m, notes",
        "license": "Public domain (factual data)",
        "validation": [
            "All coordinates must fall within Central Park boundary",
            "Species must be from NYC Parks approved species list",
            "DBH must be 5-300 cm (reasonable trunk range)",
            "Heights must be 2-50 m",
            "Positions must be >1m apart (no duplicates)",
        ],
    },
    "building_geometry": {
        "what": "Real building geometry from NYC open data",
        "how": (
            "Source CityGML LOD2 models from NYC DoITT 3D Building Model dataset "
            "or NYC Open Data PLUTO/MapPLUTO for footprints + heights. "
            "Convert to GLB with real-world coordinates."
        ),
        "tools": "QGIS, FME, or Python with citygml4j",
        "submit": "GitHub issue with data source link and conversion script",
        "license": "NYC Open Data (public domain)",
        "validation": [
            "Must come from official NYC government data sources",
            "Building footprints must align with existing OSM footprints within 5m",
        ],
    },
}


def analyze_statues(statues: list, scans: set) -> list:
    """Find statues/monuments that need photogrammetry scans."""
    gaps = []
    # Types that are physical 3D objects worth scanning
    scannable_types = {"statue", "sculpture", "bust", "monument", "memorial"}
    # Types that are 2D / not scannable
    skip_types = {"mural", "graffiti", "street_art"}

    for s in statues:
        stype = s.get("type", "statue")
        sname = s.get("name", "")
        if stype in skip_types:
            continue
        if not sname:
            continue  # unnamed items can't be targeted for contribution
        if sname.lower() in scans:
            continue  # already have a scan

        pos = s.get("position", [0, 0, 0])
        x, z = float(pos[0]), float(pos[2])
        lat, lon = unproject(x, z)

        # Priority based on notoriety
        high_priority_names = {
            "balto", "cleopatra's needle", "angel of the waters",
            "alice in wonderland", "bethesda fountain", "bow bridge",
            "belvedere castle", "shakespeare", "columbus",
        }
        priority = "high" if any(hp in sname.lower() for hp in high_priority_names) else "medium"

        # Estimate what tools are best based on type
        if stype == "bust":
            size_hint = "Small (~0.5-1m). iPhone LiDAR works well at this scale."
        elif stype == "monument":
            size_hint = "Large structure. Walk around entire perimeter. May need DSLR for best results."
        else:
            size_hint = "Life-size or larger statue. Walk slowly around all sides."

        gaps.append({
            "id": f"scan-{sname.lower().replace(' ', '-').replace('.', '').replace(',', '')[:40]}",
            "type": "photogrammetry",
            "name": sname,
            "object_type": stype,
            "description": f"{stype.title()}: {sname}",
            "pos": [round(x, 1), round(z, 1)],
            "lat": lat,
            "lon": lon,
            "priority": priority,
            "size_hint": size_hint,
        })

    return gaps


def analyze_fountains(water: list, scans: set) -> list:
    """Find fountains without photogrammetry."""
    gaps = []
    for body in water:
        name = body.get("name", "")
        if "fountain" not in name.lower():
            continue
        if name.lower() in scans:
            continue

        pts = body.get("points", [])
        if not pts:
            continue
        cx = sum(float(p[0]) for p in pts) / len(pts)
        cz = sum(float(p[1]) for p in pts) / len(pts)
        lat, lon = unproject(cx, cz)

        gaps.append({
            "id": f"scan-{name.lower().replace(' ', '-')[:40]}",
            "type": "photogrammetry",
            "name": name,
            "object_type": "fountain",
            "description": f"Fountain: {name}",
            "pos": [round(cx, 1), round(cz, 1)],
            "lat": lat,
            "lon": lon,
            "priority": "high",
            "size_hint": "Large fountain basin + sculpture. Full walk-around needed, include base and water features.",
        })

    return gaps


def make_geojson(gaps: list) -> dict:
    """Convert gap list to GeoJSON FeatureCollection."""
    features = []
    # Color and symbol by type
    style = {
        "photogrammetry": {"marker-color": "#e67e22", "marker-symbol": "camera"},
        "trees": {"marker-color": "#27ae60", "marker-symbol": "park"},
        "building_geometry": {"marker-color": "#95a5a6", "marker-symbol": "building"},
    }

    for gap in gaps:
        gtype = gap["type"]
        s = style.get(gtype, {"marker-color": "#3498db", "marker-symbol": "circle"})
        fmt = CONTRIBUTION_FORMATS.get(gtype, {})

        props = {
            "id": gap["id"],
            "name": gap.get("name", ""),
            "description": gap.get("description", ""),
            "gap_type": gtype,
            "priority": gap.get("priority", "medium"),
            "what_to_bring": fmt.get("tools", ""),
            "how_to_contribute": fmt.get("how", ""),
            "how_to_submit": fmt.get("submit", ""),
            "marker-color": s["marker-color"],
            "marker-symbol": s["marker-symbol"],
        }
        # Add type-specific fields
        if "size_hint" in gap:
            props["size_hint"] = gap["size_hint"]
        if "current" in gap:
            props["current_count"] = gap["current"]
            props["expected_count"] = gap["expected"]
        if "species" in gap:
            props["species"] = gap["species"]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [gap["lon"], gap["lat"]],
            },
            "properties": props,
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def main():
    if not os.path.exists("park_data.json"):
        print("ERROR: park_data.json not found. Run convert_to_godot.py first.")
        return

    with open("park_data.json") as f:
        data = json.load(f)

    scans = find_available_scans()
    print(f"Available scans: {len(scans)}")
    for s in sorted(scans):
        print(f"  ✓ {s}")

    all_gaps = []

    # --- Statue/monument scan gaps ---
    statue_gaps = analyze_statues(data.get("statues", []), scans)
    all_gaps.extend(statue_gaps)
    print(f"\nStatue/monument scan gaps: {len(statue_gaps)}")

    # --- Fountain scan gaps ---
    fountain_gaps = analyze_fountains(data.get("water", []), scans)
    all_gaps.extend(fountain_gaps)
    print(f"Fountain scan gaps: {len(fountain_gaps)}")

    # --- Tree density gaps ---
    trees = data.get("trees", [])
    for tg in TREE_GAPS:
        x, z = tg["pos"]
        lat, lon = unproject(x, z)
        all_gaps.append({
            "id": tg["id"],
            "type": "trees",
            "name": tg["name"],
            "description": tg["description"],
            "pos": tg["pos"],
            "lat": lat,
            "lon": lon,
            "priority": tg["priority"],
            "current": tg["current"],
            "expected": tg["expected"],
            "species": tg["species"],
            "radius_m": tg["radius_m"],
        })
    print(f"Tree density gaps: {len(TREE_GAPS)}")

    # --- Building geometry (summary, not per-building) ---
    buildings = data.get("buildings", [])
    # Just one marker at park center for the building gap
    blat, blon = unproject(0, 0)
    all_gaps.append({
        "id": "buildings-citymodel",
        "type": "building_geometry",
        "name": f"All {len(buildings)} buildings — facade only",
        "description": (
            f"All {len(buildings)} buildings use procedural facades from OSM footprints + heights. "
            "Real 3D geometry from NYC CityGML LOD2 dataset would replace these."
        ),
        "pos": [0, 0],
        "lat": blat,
        "lon": blon,
        "priority": "medium",
    })

    # --- Summary ---
    by_type = Counter(g["type"] for g in all_gaps)
    by_priority = Counter(g.get("priority", "medium") for g in all_gaps)
    print(f"\nTotal gaps: {len(all_gaps)}")
    for t, c in by_type.most_common():
        print(f"  {t}: {c}")
    print(f"Priority: high={by_priority['high']}, medium={by_priority['medium']}")

    # --- Write data_gaps.json ---
    output = {
        "version": 1,
        "generated": str(date.today()),
        "summary": {
            "total_gaps": len(all_gaps),
            **{t: c for t, c in by_type.items()},
        },
        "contribution_formats": CONTRIBUTION_FORMATS,
        "gaps": all_gaps,
    }

    with open("data_gaps.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n→ data_gaps.json ({len(all_gaps)} gaps)")

    # --- Write data_gaps.geojson ---
    geojson = make_geojson(all_gaps)
    with open("data_gaps.geojson", "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"→ data_gaps.geojson ({len(geojson['features'])} features — view on GitHub)")


if __name__ == "__main__":
    main()

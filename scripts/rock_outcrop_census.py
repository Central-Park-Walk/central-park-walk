#!/usr/bin/env python3
"""Rock outcrop census (walk-around 2026-06-12 cpw_000: "green mounds in
the distance ... we should try to get more data on what these features
are supposed to be").

The mounds are real geometry: convert_to_godot.py's targeted rock
outcrop restoration blends canopy-masked DSM domes (>=19 m^2 footprint,
grass/tagged-rock areas only) into the heightmap and marks their cells
as world-atlas surface type 7. They render green because the Terrain3D
control bake never maps type 7 to the rock texture (autoshader only
rocks steep slopes, and these domes are smooth).

This script inventories every type-7 cluster so we know what we're
texturing before we texture it:
  - connected components of atlas R==7 (8-connectivity)
  - footprint area (m^2), centroid + bbox in world XZ
  - relief: max heightmap value inside the cluster minus the median of a
    boundary ring ~2 m outside it (how far the dome pokes out)
  - OSM natural=rock cross-ref (park_data.json "rocks" — sparse: OSM has
    almost no rock mapping in the park, so absence is NOT evidence
    against; presence is confirmation)

Classification heuristic (reported, not enforced):
  confirmed  — overlaps/near an OSM rock feature
  outcrop    — area >= 100 m^2 (broad schist sheets; DSM contamination
               from shrub clumps rarely sustains that footprint)
  suspect    — small AND tall (area < 60 m^2, relief > 2.5 m): the
               profile of a shrub/object that survived canopy masking
  unverified — everything else

Outputs notes/rock_outcrop_census.json (full) and prints a summary.
Usage: scripts/rock_outcrop_census.py [--near X,Z] (report clusters near
a world position, e.g. a screenshot mound)
"""
import argparse
import json
import struct
import sys

import numpy as np
from scipy import ndimage

ATLAS = "world_atlas.bin"
HEIGHTMAP = "heightmap.bin"
PARK_DATA = "park_data.json"
OUT_JSON = "notes/rock_outcrop_census.json"


def load_atlas():
    with open(ATLAS, "rb") as f:
        w, h = struct.unpack("<II", f.read(8))
        data = np.frombuffer(f.read(w * h * 2), dtype=np.uint8).reshape(h, w, 2)
    return data[..., 0], w  # R channel = surface type; row=z, col=x


def load_heightmap():
    with open(HEIGHTMAP, "rb") as f:
        w, h = struct.unpack("<II", f.read(8))
        world_size, origin_h = struct.unpack("<ff", f.read(8))
        grid = np.frombuffer(f.read(), dtype=np.float32).reshape(h, w)
    return grid, w, world_size


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--near", help="world X,Z — list clusters within 200 m")
    args = ap.parse_args()

    surface, ares = load_atlas()
    hm, hres, world = load_heightmap()
    cell = world / ares          # atlas cell size, m
    cell_area = cell * cell

    rock = surface == 7
    labels, n = ndimage.label(rock, structure=np.ones((3, 3), dtype=int))
    print(f"type-7 cells: {int(rock.sum())} ({rock.sum() * cell_area:.0f} m^2) "
          f"in {n} clusters")

    # OSM rock features (world XZ)
    osm_pts = []
    try:
        pd = json.load(open(PARK_DATA))
        for r in pd.get("rocks", []):
            for p in r["points"]:
                osm_pts.append((p[0], p[1], r.get("name", "")))
    except FileNotFoundError:
        pass
    print(f"OSM natural=rock features: {len(osm_pts)} points "
          "(sparse — absence is not evidence against)")

    half = world / 2.0
    hm_scale = hres / ares  # heightmap px per atlas px (same world span)

    objs = ndimage.find_objects(labels)
    clusters = []
    for i, sl in enumerate(objs, start=1):
        m = labels[sl] == i
        area = float(m.sum() * cell_area)
        zi, xi = np.nonzero(m)
        # centroid + bbox in world coords (atlas col -> X, row -> Z)
        cx = (sl[1].start + xi.mean()) * cell - half
        cz = (sl[0].start + zi.mean()) * cell - half
        bx0, bx1 = sl[1].start * cell - half, sl[1].stop * cell - half
        bz0, bz1 = sl[0].start * cell - half, sl[0].stop * cell - half

        # Relief from the heightmap: cluster max vs boundary-ring median.
        # Work on the cluster's padded bbox in heightmap pixels.
        pad = max(int(round(3 * hm_scale)), 2)
        hz0 = max(int(sl[0].start * hm_scale) - pad, 0)
        hz1 = min(int(sl[0].stop * hm_scale) + pad, hres)
        hx0 = max(int(sl[1].start * hm_scale) - pad, 0)
        hx1 = min(int(sl[1].stop * hm_scale) + pad, hres)
        hwin = hm[hz0:hz1, hx0:hx1]
        # Cluster mask resampled into the heightmap window
        mwin = np.zeros(hwin.shape, dtype=bool)
        hzi = np.clip(((sl[0].start + zi) * hm_scale).astype(int) - hz0, 0, hwin.shape[0] - 1)
        hxi = np.clip(((sl[1].start + xi) * hm_scale).astype(int) - hx0, 0, hwin.shape[1] - 1)
        mwin[hzi, hxi] = True
        mfill = ndimage.binary_dilation(mwin, iterations=max(int(hm_scale), 1))
        ring = ndimage.binary_dilation(mfill, iterations=pad // 2) & ~mfill
        if ring.sum() >= 4 and mfill.sum() >= 1:
            relief = float(hwin[mfill].max() - np.median(hwin[ring]))
        else:
            relief = 0.0

        # OSM cross-ref: nearest feature point
        osm_d = min((((cx - px) ** 2 + (cz - pz) ** 2) ** 0.5
                     for px, pz, _ in osm_pts), default=float("inf"))

        if osm_d < 30.0:
            klass = "confirmed"
        elif area >= 100.0:
            klass = "outcrop"
        elif area < 60.0 and relief > 2.5:
            klass = "suspect"
        else:
            klass = "unverified"

        clusters.append({
            "id": i, "area_m2": round(area, 1), "relief_m": round(relief, 2),
            "x": round(cx, 1), "z": round(cz, 1),
            "bbox": [round(bx0, 1), round(bz0, 1), round(bx1, 1), round(bz1, 1)],
            "osm_dist_m": None if osm_d == float("inf") else round(osm_d, 1),
            "class": klass,
        })

    clusters.sort(key=lambda c: -c["area_m2"])
    by_class = {}
    for c in clusters:
        by_class[c["class"]] = by_class.get(c["class"], 0) + 1
    print("classes:", ", ".join(f"{k}={v}" for k, v in sorted(by_class.items())))
    areas = np.array([c["area_m2"] for c in clusters])
    print(f"area m^2: median={np.median(areas):.0f} p90={np.percentile(areas, 90):.0f} "
          f"max={areas.max():.0f}")
    reliefs = np.array([c["relief_m"] for c in clusters])
    print(f"relief m: median={np.median(reliefs):.1f} p90={np.percentile(reliefs, 90):.1f} "
          f"max={reliefs.max():.1f}")

    print("\nlargest 15:")
    for c in clusters[:15]:
        print(f"  #{c['id']:4d} {c['class']:10s} {c['area_m2']:8.0f} m^2  "
              f"relief {c['relief_m']:5.2f} m  at X={c['x']:7.1f} Z={c['z']:7.1f}")

    if args.near:
        nx, nz = (float(v) for v in args.near.split(","))
        near = [c for c in clusters
                if ((c["x"] - nx) ** 2 + (c["z"] - nz) ** 2) ** 0.5 < 200.0]
        print(f"\nwithin 200 m of ({nx:.0f}, {nz:.0f}): {len(near)}")
        for c in sorted(near, key=lambda c: (c["x"] - nx) ** 2 + (c["z"] - nz) ** 2)[:10]:
            d = ((c["x"] - nx) ** 2 + (c["z"] - nz) ** 2) ** 0.5
            print(f"  #{c['id']:4d} {c['class']:10s} {c['area_m2']:8.0f} m^2  "
                  f"relief {c['relief_m']:5.2f} m  at X={c['x']:7.1f} Z={c['z']:7.1f}  ({d:.0f} m away)")

    with open(OUT_JSON, "w") as f:
        json.dump({"cell_m": cell, "clusters": clusters}, f, indent=1)
    print(f"\nwrote {OUT_JSON} ({len(clusters)} clusters)")


if __name__ == "__main__":
    main()

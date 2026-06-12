#!/usr/bin/env python3
"""Lawn mound audit (walk-around 2026-06-12 cpw_000/cpw_002: green mounds).

Two families of "green mounds" exist:
  1. World-atlas type-7 cells — DSM-restored schist outcrops. Real, now
     baked as rock (scripts/rock_outcrop_census.py inventories them).
  2. Smooth domes in the bare-earth DEM inside open lawn, with NO atlas
     marking. The Great Lawn examples sit on what NYC aerial imagery
     shows as flat mowed lawn between ball diamonds — LiDAR processing
     artifacts (temporary objects in the ground return), not landforms.

This script finds family 2 and classifies every candidate against ESRI
World Imagery (the data the user asked for: "what are these features
supposed to be"):

  detect : top-hat residual (height - grayscale opening, ~24 m disk) on
           the heightmap, masked to atlas grass (1) cells that are not
           type 7; blobs with residual >= 1.2 m and 19..3000 m^2.
  classify: mean RGB of the aerial at the dome footprint —
           green (G dominant)            -> "artifact" (flat lawn there)
           gray/low-saturation bright    -> "rock" (real outcrop the
                                            atlas missed; should become
                                            type 7, not be flattened)
           else                          -> "review"

Output: lidar_data/lawn_mound_verdicts.json plus lidar_data/
lawn_mound_mask.png, a 16-bit label image of every candidate's EXACT
detected footprint (mound["label_id"] indexes into it). convert_to_
godot.py flattens/marks exactly those cells — footprints re-derived
from area-equivalent circles failed on elongated blobs (ring landed on
the dome, poisoning the plane fit).

--inherit carries verdicts (incl. manual overrides) from the existing
verdicts file to re-detected mounds within 15 m, so the audit can be
re-run after partial flattening without losing classification work;
only unmatched mounds fetch fresh aerial imagery.

Usage: scripts/lawn_mound_audit.py [--no-fetch] [--inherit] [--limit N]
"""
import argparse
import io
import json
import math
import os
import struct
import time
import urllib.request

import numpy as np
from PIL import Image
from scipy import ndimage

ATLAS = "world_atlas.bin"
# Detect against the RAW bare-earth DEM (written by convert_to_godot.py's
# terrain stage), NOT the shipping heightmap — that one mutates as domes
# get flattened, which made re-audits lose previously-found mounds and
# broke the converter's exclusion bookkeeping. Fallback for first runs.
HEIGHTMAP = ("lidar_data/dem_raw.bin" if os.path.exists("lidar_data/dem_raw.bin")
             else "heightmap.bin")
PARK_DATA = "park_data.json"
OUT = "lidar_data/lawn_mound_verdicts.json"
MASK_OUT = "lidar_data/lawn_mound_mask.png"
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ZOOM = 19

OPEN_RADIUS_M = 24.0     # opening disk radius — wider than any artifact dome
MIN_RESIDUAL_M = 1.2     # dome must poke this far above the opened surface
MIN_AREA_M2 = 19.0       # converter's own outcrop breadth floor
MAX_AREA_M2 = 3000.0


def load_atlas():
    with open(ATLAS, "rb") as f:
        w, h = struct.unpack("<II", f.read(8))
        data = np.frombuffer(f.read(w * h * 2), dtype=np.uint8).reshape(h, w, 2)
    return data[..., 0], w


def load_heightmap():
    with open(HEIGHTMAP, "rb") as f:
        w, h = struct.unpack("<II", f.read(8))
        world, _origin = struct.unpack("<ff", f.read(8))
    grid = np.fromfile(HEIGHTMAP, dtype=np.float32, offset=16).reshape(h, w)
    return grid, w, world


_tile_cache = {}


def fetch_tile(tx, ty):
    key = (tx, ty)
    if key not in _tile_cache:
        req = urllib.request.Request(TILE_URL.format(z=ZOOM, x=tx, y=ty),
                                     headers={"User-Agent": "central-park-walk-audit"})
        with urllib.request.urlopen(req, timeout=20) as r:
            _tile_cache[key] = np.asarray(
                Image.open(io.BytesIO(r.read())).convert("RGB"), dtype=np.float32)
        time.sleep(0.1)
    return _tile_cache[key]


def aerial_rgb(lat, lon, half_px=6):
    """Mean RGB of a small window around (lat, lon) at ZOOM."""
    n = 2 ** ZOOM
    fx = (lon + 180.0) / 360.0 * n
    lr = math.radians(lat)
    fy = (1.0 - math.log(math.tan(lr) + 1.0 / math.cos(lr)) / math.pi) / 2.0 * n
    tx, ty = int(fx), int(fy)
    px, py = int((fx - tx) * 256), int((fy - ty) * 256)
    tile = fetch_tile(tx, ty)
    x0, x1 = max(px - half_px, 0), min(px + half_px + 1, 256)
    y0, y1 = max(py - half_px, 0), min(py + half_px + 1, 256)
    return tile[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)


def classify_rgb(rgb):
    # Thresholds tuned 2026-06-12 against the ESRI leaf-off capture:
    # summer-mowed lawn reads dark olive (G/R only ~1.03-1.08), so the
    # green test keys on the low blue of vegetation instead of strong G/R.
    r, g, b = rgb
    mx, mn = max(rgb), min(rgb)
    if g > r * 1.02 and g > b * 1.15:
        return "artifact"            # vegetation hue — nothing real at the dome
    if (mx - mn) / max(mx, 1e-3) < 0.15 and mx > 70:
        return "rock"                # flat gray — exposed schist
    return "review"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip aerial classification (verdict='review')")
    ap.add_argument("--inherit", action="store_true",
                    help="carry verdicts from the existing verdicts file "
                         "(centroid match within 15 m) before fetching")
    ap.add_argument("--limit", type=int, default=0, help="cap candidates (debug)")
    args = ap.parse_args()

    prior = []
    if args.inherit:
        try:
            prior = [m for m in json.load(open(OUT))["mounds"]
                     if m.get("verdict") in ("artifact", "rock")]
        except (FileNotFoundError, KeyError, ValueError):
            pass

    surface, ares = load_atlas()
    hm, hres, world = load_heightmap()
    cell = world / hres
    cell_area = cell * cell

    pd = json.load(open(PARK_DATA))
    ref_lat, ref_lon = pd["ref_lat"], pd["ref_lon"]
    mlat, mlon = pd["metres_per_deg_lat"], pd["metres_per_deg_lon"]

    # Atlas and heightmap share world span; resample atlas to heightmap res
    # if needed (both 8192 today).
    if ares != hres:
        raise SystemExit(f"atlas {ares} != heightmap {hres} — add resampling")
    # Same candidacy mask as the restoration's natural_mask: grass OR
    # already-marked rock. Type-7 derives from the restoration each run —
    # excluding it here made every already-marked cluster invisible to the
    # audit (the Great Lawn twin domes hid behind their own rock marks).
    grass = (surface == 1) | (surface == 7)

    print(f"opening heightmap ({hres}^2, disk r={OPEN_RADIUS_M} m)...")
    r_px = int(round(OPEN_RADIUS_M / cell))
    yy, xx = np.ogrid[-r_px:r_px + 1, -r_px:r_px + 1]
    disk = (yy * yy + xx * xx) <= r_px * r_px
    opened = ndimage.grey_opening(hm, footprint=disk, mode="nearest")
    residual = hm - opened

    cand = (residual >= MIN_RESIDUAL_M) & grass

    # Third family: DSM-restoration candidates (convert_to_godot.py blends
    # canopy-masked DSM features back into the heightmap as "rock"). DSM
    # contamination in open lawn — leftover objects, missed vegetation —
    # passes every geometric filter the restoration applies; only imagery
    # rules it out. Same thresholds as the restoration itself.
    dsm_diff_path = "lidar_data/dsm_diff.bin"
    if os.path.exists(dsm_diff_path):
        dsm_diff = np.fromfile(dsm_diff_path, dtype=np.float32,
                               offset=16).reshape(hres, hres)
        cand_dsm = (dsm_diff > 0.2) & (dsm_diff < 4.0) & grass
        cand_dsm = ndimage.binary_opening(cand_dsm, iterations=3)
        print(f"DSM-restoration candidates in lawn: {int(cand_dsm.sum())} cells")
        cand |= cand_dsm
    else:
        print("lidar_data/dsm_diff.bin missing — DSM candidates not audited "
              "(run convert_to_godot.py once to generate)")

    # Canopy guard: ESRI imagery can't see the ground under tree crowns,
    # and its capture date differs from the LiDAR — never auto-classify a
    # cluster that sits under canopy.
    canopy = None
    chm_path = "lidar_data/canopy_height_model.png"
    if os.path.exists(chm_path):
        chm_img = Image.open(chm_path)
        if chm_img.size == (hres, hres):
            canopy = np.asarray(chm_img, dtype=np.uint8)

    labels, n = ndimage.label(cand, structure=np.ones((3, 3), dtype=int))
    print(f"raw candidate blobs in lawn: {n}")

    # Map prior verdicts onto new blobs by footprint containment: which new
    # label sits at each prior mound's centroid?
    prior_by_label = {}
    for p_rec in prior:
        ppx = int((p_rec["x"] + world / 2) / cell)
        ppz = int((p_rec["z"] + world / 2) / cell)
        if 0 <= ppx < hres and 0 <= ppz < hres:
            lab_here = int(labels[ppz, ppx])
            if lab_here and lab_here not in prior_by_label:
                prior_by_label[lab_here] = p_rec

    objs = ndimage.find_objects(labels)
    moundlist = []
    for i, sl in enumerate(objs, start=1):
        m = labels[sl] == i
        area = float(m.sum() * cell_area)
        if not (MIN_AREA_M2 <= area <= MAX_AREA_M2):
            continue
        zi, xi = np.nonzero(m)
        cx = (sl[1].start + xi.mean()) * cell - world / 2
        cz = (sl[0].start + zi.mean()) * cell - world / 2
        peak = float(residual[sl][m].max())
        lat = ref_lat - cz / mlat
        lon = ref_lon + cx / mlon
        rec = {"label_id": i, "x": round(cx, 1), "z": round(cz, 1),
               "lat": round(lat, 6), "lon": round(lon, 6),
               "area_m2": round(area, 1), "peak_m": round(peak, 2)}
        if canopy is not None:
            rec["under_canopy"] = bool(canopy[sl][m].mean() > 20)
        moundlist.append(rec)
    moundlist.sort(key=lambda c: -c["area_m2"])
    if args.limit:
        moundlist = moundlist[:args.limit]
    print(f"candidate lawn domes ({MIN_AREA_M2}-{MAX_AREA_M2} m^2): {len(moundlist)}")

    # Exact footprint mask: keep only surviving candidates' labels
    keep = np.zeros(n + 1, dtype=np.uint16)
    for c in moundlist:
        keep[c["label_id"]] = c["label_id"]
    Image.fromarray(keep[labels].astype(np.uint16)).save(MASK_OUT)
    print(f"wrote {MASK_OUT}")

    counts = {}
    inherited = 0
    for c in moundlist:
        # Footprint containment first (blob shapes/centroids shift when
        # candidate sources merge), centroid distance as fallback.
        old = prior_by_label.get(c["label_id"]) or next(
            (p for p in prior
             if (p["x"] - c["x"]) ** 2 + (p["z"] - c["z"]) ** 2 < 15.0 ** 2), None)
        if old is not None:
            c["verdict"] = old["verdict"]
            c["aerial_rgb"] = old.get("aerial_rgb")
            if old.get("verdict_source"):
                c["verdict_source"] = old["verdict_source"]
            inherited += 1
        elif args.no_fetch or c.get("under_canopy"):
            # under_canopy: imagery can't see the ground — leave for the
            # restoration's geometric filters (status quo), never classify
            c["verdict"], c["aerial_rgb"] = "review", None
        else:
            try:
                rgb = aerial_rgb(c["lat"], c["lon"])
                c["aerial_rgb"] = [round(float(v), 1) for v in rgb]
                c["verdict"] = classify_rgb(rgb)
            except Exception as e:  # network hiccup — keep going
                c["verdict"], c["aerial_rgb"] = "review", None
                print(f"  fetch failed at ({c['x']},{c['z']}): {e}")
        counts[c["verdict"]] = counts.get(c["verdict"], 0) + 1
    print(f"verdicts: {counts} ({inherited} inherited)")

    print("\nlargest 15:")
    for c in moundlist[:15]:
        print(f"  {c['verdict']:8s} {c['area_m2']:7.0f} m^2  peak {c['peak_m']:4.1f} m  "
              f"X={c['x']:7.1f} Z={c['z']:7.1f}  rgb={c['aerial_rgb']}")

    with open(OUT, "w") as f:
        json.dump({"open_radius_m": OPEN_RADIUS_M, "min_residual_m": MIN_RESIDUAL_M,
                   "zoom": ZOOM, "mounds": moundlist}, f, indent=1)
    print(f"\nwrote {OUT} ({len(moundlist)} mounds, {len(_tile_cache)} tiles fetched)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate wear_map.png — turf wear from real park geometry (docs/grass.md §4).

Reads world_atlas.bin (surface types + occupancy from OSM via convert_to_godot.py)
and writes an L8 4096² map of foot-traffic wear intensity:

  - unpaved paths: wear 1.0 within 1 m, linear falloff to 0 at 6 m
    (dirt paths bleed into their shoulders)
  - paved paths:   wear 0.55 max, falloff 0.7 m -> 3.5 m
    (desire lines hug pavement edges)
  - benches:       wear 0.70 max, radial falloff to 2.5 m
    (trampled spots in front of seating)

Combined as max(). Canopy compaction and ambient mottle are runtime terms
(shader-side) — this map is only the data-driven component. Output is
gitignored like landuse_map.png; consumers sample it with the same
splat_uv = (world_xz + world_size/2) / world_size convention as the
landuse/canopy maps.

Usage: python3 scripts/gen_wear_map.py [--atlas world_atlas.bin] [--out wear_map.png]
"""
import argparse
import os
import struct
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

WORLD_SIZE = 5000.0  # meters (matches convert_to_godot.py)
OUT_RES = 4096       # 1.22 m/px — wear gradients are >= 2 m wide


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas", default="world_atlas.bin")
    ap.add_argument("--out", default="wear_map.png")
    args = ap.parse_args()

    with open(args.atlas, "rb") as fh:
        w, h = struct.unpack("<II", fh.read(8))
        data = np.frombuffer(fh.read(w * h * 2), dtype=np.uint8).reshape(h, w, 2)
    print(f"world_atlas: {w}x{h}")

    surface = data[:, :, 0]
    occupancy = data[:, :, 1]

    paved = surface == 2
    unpaved = surface == 3
    bench = (occupancy & 0x02) != 0
    print(f"paved px: {paved.sum():,}  unpaved px: {unpaved.sum():,}  bench px: {bench.sum():,}")

    # Downsample masks to OUT_RES with 2x2 max-pool so 1-px-wide paths survive.
    f = w // OUT_RES
    if f > 1:
        def pool(m):
            return m.reshape(OUT_RES, f, OUT_RES, f).any(axis=(1, 3))
        paved, unpaved, bench = pool(paved), pool(unpaved), pool(bench)

    px_m = WORLD_SIZE / OUT_RES  # meters per pixel

    def falloff(mask, full_m, zero_m, peak):
        """peak inside full_m, linear to 0 at zero_m (meters from mask)."""
        if not mask.any():
            return np.zeros((OUT_RES, OUT_RES), dtype=np.float32)
        d = distance_transform_edt(~mask) * px_m
        return (peak * np.clip(1.0 - (d - full_m) / (zero_m - full_m), 0.0, 1.0)).astype(np.float32)

    wear = falloff(unpaved, 1.0, 6.0, 1.0)
    wear = np.maximum(wear, falloff(paved, 0.7, 3.5, 0.55))
    wear = np.maximum(wear, falloff(bench, 0.0, 2.5, 0.70))

    img = (wear * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img, mode="L").save(args.out, optimize=True)
    nz = (img > 0).mean() * 100.0
    print(f"wrote {args.out} ({OUT_RES}x{OUT_RES}, {os.path.getsize(args.out):,} bytes, "
          f"{nz:.1f}% nonzero, max {img.max()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

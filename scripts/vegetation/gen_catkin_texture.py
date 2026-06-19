#!/usr/bin/env python3
"""Generate the cattail catkin (female spike) albedo texture.

The catkin reads plastic when it's a flat-coloured tube (user 2026-06-19: "catkins and
stems aren't quite organic yet"). A real Typha female spike is a VELVETY cylinder of
densely packed florets — fine vertical columns + offset horizontal rows (a brick lattice),
warm cinnamon brown, with tonal mottle and a fuzzy grain. This bakes that as an ABSOLUTE
albedo wrapped around the cylinder (UV.x = circumference, tiles; UV.y = along length).

Mapped via the circumferential UVs make_tube now emits; sampled in undergrowth.gdshader's
catkin path (gated by stem_use_vtx). Output: models/vegetation/tex_catkin_Wetland_Cattail.png
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "models", "vegetation",
                                    "tex_catkin_Wetland_Cattail.png"))
W = H = 256
N_COL = 22          # floret columns around the circumference
N_ROW = 34          # floret rows along the visible length
BASE = np.array([142.0, 97.0, 59.0])   # warm cinnamon brown — MEASURED mature-spike refs
                                       # (serene/GKg9 ~(140,95,64)); was too dark/muddy before.

xs = np.linspace(0.0, 1.0, W, endpoint=False)
ys = np.linspace(0.0, 1.0, H, endpoint=False)
U, V = np.meshgrid(xs, ys)

# ORGANIC VELVET from tileable spectral noise (sum of sines at INTEGER frequencies → seamless
# tile, no seam). A regular floret lattice read as a mechanical diagonal WEAVE / stripes
# (user 2026-06-19). Random-phase multi-octave noise gives the irregular packed-velvet look
# with NO grid. Frequencies span broad mottle → fine floret-scale lumps (V denser than U so
# the spike reads as faint horizontal floret rows, not vertical columns).
rng = np.random.default_rng(11)
field = np.zeros((H, W))
for _ in range(22):
    fx = int(rng.integers(1, 22))           # around circumference
    fy = int(rng.integers(2, 30))           # along length (finer)
    ph = rng.uniform(0.0, 2.0 * np.pi)
    amp = 1.0 / (1.0 + 0.30 * (fx + fy))     # 1/f falloff — low freqs broad, high freqs subtle
    field += amp * np.sin(2.0 * np.pi * (fx * U + fy * V) + ph)
field /= np.abs(field).max()                 # -> ~[-1, 1]

# Fine velvety grain (low amplitude; any U-seam is invisible at this level).
grain = rng.normal(0.0, 1.0, (H, W))

val = 0.92 + field * 0.24 + grain * 0.045
val = np.clip(val, 0.60, 1.24)

img = val[..., None] * BASE
# Raised lumps read slightly warmer/lighter; recesses cooler/darker.
img += np.clip(field, 0.0, 1.0)[..., None] * np.array([16.0, 6.0, -6.0])
img = np.clip(img, 0, 255).astype(np.uint8)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
Image.fromarray(img, "RGB").save(OUT)
print(f"  Saved {OUT} ({W}x{H})")

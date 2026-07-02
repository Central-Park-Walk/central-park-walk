#!/usr/bin/env python3
"""Derive the turf normal map from the baked height field.

Part 3 of the turf bake (after bake_turf.gd's albedo + height passes):
    python3 scripts/height_to_normal.py
    "$GODOT" --path . --import --headless

The tile mesh bakes all vertex NORMALs straight up (a lighting choice for the
blades), so a shader normal pass would produce nothing — the real relief lives
in the height pass. Sobel the height field into a tangent-space normal map so
the sward responds to light (raking-light micro-shadowing, ambient relief in
shadow — albedo-only texture goes flat the moment direct sun leaves it).
Deriving from the same height PNG keeps normals and POM depth exactly agreed.

The height field wraps (periodic bake), so the Sobel wraps too — seamless.
"""
import numpy as np
from PIL import Image

HEIGHT = "textures/grass_turf_height.png"
OUT = "textures/grass_turf_normal.png"
TILE_M = 2.0     # bake period (m)
H_MAX = 0.12     # height normalizer used by turf_bake_height.gdshader (m)
STRENGTH = 0.35  # slope scale: true blade slopes are near-vertical walls;
                 # full-strength normals read as noise, this keeps readable
                 # relief (lever: rebake cheap, or scale again in-shader)

h = np.asarray(Image.open(HEIGHT).convert("L"), dtype=np.float64) / 255.0 * H_MAX
n = h.shape[0]
texel = TILE_M / n

# wrap-around central differences (periodic tile -> seamless normal map)
dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2.0 * texel)
dz = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) / (2.0 * texel)

nx = -dx * STRENGTH
nz = -dz * STRENGTH
ny = np.ones_like(h)
ln = np.sqrt(nx * nx + ny * ny + nz * nz)
nx, ny, nz = nx / ln, ny / ln, nz / ln

# tangent-space convention: x -> R, z(green up in uv-space) -> G, up -> B
rgb = np.stack([(nx * 0.5 + 0.5), (nz * 0.5 + 0.5), (ny * 0.5 + 0.5)], axis=-1)
Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8)).save(OUT)
print(f"saved {OUT} ({n}x{n}), slope strength {STRENGTH}")

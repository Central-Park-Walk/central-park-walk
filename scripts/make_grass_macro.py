"""Generate a COARSE grass macro texture for distance/altitude coherence.

The fine terrain grass texture (make_turf_texture.py) tiles at ~1.25 m, so from
any real distance or flying altitude its blade detail AND its normal relief mip
below one pixel and average to flat green — the "flat quilt" look. Real grass (see
reference_photos/grass/91suSCsHsdL...) never does this because it has resolved
structure at EVERY scale: blades -> clumps -> tufts -> tonal undulation.

This texture supplies the scale the fine one lacks: clump/tuft/tonal structure at
the ~0.3-4 m WORLD scale (when tiled at grass_macro_scale ~12 m). That scale is
still several pixels wide from altitude, so it keeps the lawn reading as lit,
textured, 3D grass instead of a flat plane. The terrain shader blends this in with
a weight that rises with distance (and altitude, since the camera distance to the
ground below IS the height), so the near field keeps its fine blades.

Outputs (seamless / tileable):
  textures/terrain3d/grass_macro.png     RGB coarse VALUE tone (mean ~0.5), A height
  textures/terrain3d/grass_macro_n.png   RGB tangent normal (relief for lighting)

Colour/character calibrated to the sod reference (mean G/R 1.27, soft isotropic
tonal patches, NO mowing stripes). The shader still recolours to the sward palette;
this carries the multi-scale VALUE + RELIEF, which is what survives distance.
Run: python3 scripts/make_grass_macro.py
"""

import os
import numpy as np
from PIL import Image

SIZE = 1024
SEED = 23
# World metres represented by one tile (must match grass_macro_scale in the shader).
TILE_M = 12.0
PX_PER_M = SIZE / TILE_M   # ~85 px/m

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "textures", "terrain3d")


def value_noise(size, scale_px, seed):
    """Tileable smooth value noise in [0,1] at the given cell size (pixels)."""
    cells = max(2, int(round(size / scale_px)))
    g = np.random.default_rng(seed).random((cells, cells))
    g = np.pad(g, ((0, 1), (0, 1)), mode="wrap")   # wrap for seamless bilinear
    ys = np.linspace(0, cells, size, endpoint=False)
    xs = np.linspace(0, cells, size, endpoint=False)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    g00 = g[np.ix_(y0, x0)]; g10 = g[np.ix_(y0 + 1, x0)]
    g01 = g[np.ix_(y0, x0 + 1)]; g11 = g[np.ix_(y0 + 1, x0 + 1)]
    top = g00 * (1 - fx) + g01 * fx
    bot = g10 * (1 - fx) + g11 * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def octaves(specs):
    """Sum tileable octaves: specs = [(scale_m, weight, seed), ...] -> [0,1]."""
    acc = np.zeros((SIZE, SIZE), np.float32)
    wsum = 0.0
    for scale_m, w, sd in specs:
        acc += w * value_noise(SIZE, scale_m * PX_PER_M, sd)
        wsum += w
    acc /= wsum
    # normalise to full 0..1 so the swing is predictable
    acc -= acc.min(); acc /= max(1e-6, acc.max())
    return acc


def build():
    # --- HEIGHT field: TUFT/CLUMP relief (5-40 cm) is the star — that's the scale that
    # resolves from altitude (at 60 m, ~4 cm/px, so 5-40 cm clumps read as 1-10 px of lit/
    # shadowed grass texture). A gentle 2.5 m mound underneath for broad undulation. This
    # normal is what makes the lawn read as textured 3D grass from above, not a flat plane.
    height = octaves([
        (2.5, 0.22, SEED + 1),    # broad undulation (subtle)
        (0.40, 0.34, SEED + 2),   # clumps
        (0.16, 0.30, SEED + 3),   # tufts
        (0.07, 0.14, SEED + 4),   # fine tuft grain
    ])

    # --- TONE (albedo value): SUBTLE. Real lawn tonal variation is gentle; big pale
    # blobs read as discolouration/cloud, not grass. Broad drift + fine clump value,
    # compressed hard so tone_mult stays ~0.85..1.06 (the NORMAL carries the texture).
    tone = octaves([
        (3.0, 0.55, SEED + 11),
        (0.30, 0.45, SEED + 12),
    ])
    tone = 0.5 + (tone - 0.5) * 0.22        # -> ~0.39..0.61, mean 0.5 (subtle)
    tone_rgb = np.clip(np.dstack([tone, tone, tone]), 0, 1)

    # --- NORMAL from height (wrap-aware Sobel), tangent space +Z up.
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    strength = 3.4 * PX_PER_M / 85.0        # keep slope consistent if SIZE/TILE change
    nx = -gx * strength; ny = -gy * strength; nz = np.ones_like(height)
    nl = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= nl; ny /= nl; nz /= nl
    normal = np.dstack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5])

    os.makedirs(OUT_DIR, exist_ok=True)
    macro_rgba = np.dstack([tone_rgb, height]).astype(np.float32)
    Image.fromarray((macro_rgba * 255).astype(np.uint8), "RGBA").save(
        os.path.join(OUT_DIR, "grass_macro.png"))
    Image.fromarray((normal * 255).astype(np.uint8), "RGB").save(
        os.path.join(OUT_DIR, "grass_macro_n.png"))
    print("grass macro written to", OUT_DIR)
    print("  tile = %.1f m   tone mean=%.3f (min %.3f max %.3f)   height relief baked"
          % (TILE_M, float(tone.mean()), float(tone.min()), float(tone.max())))


if __name__ == "__main__":
    build()

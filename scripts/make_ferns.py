"""Generate fern models with individual pinnae along curved rachis.

The comb-like silhouette of individual pinnae IS what reads as "fern" —
flat strips with alpha can never achieve this. Each pinna is a diamond
card, alternating along the rachis, tilted for depth.

Run: blender --background --python scripts/make_ferns.py

Outputs:
  models/vegetation/Fern_Ostrich.glb   — 1.3m vase-shaped, bright green
  models/vegetation/Fern_Christmas.glb — 0.5m rosette, deep glossy green
"""

import sys
import os
import math
import random

# Add scripts dir to path for shared helpers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vegetation_helpers import *


def make_ostrich_fern():
    """Ostrich fern (Matteuccia struthiopteris) — 1-1.8m.
    Vase-shaped clump of 7 bright green fronds + brown fertile frond."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(801)

    n_fronds = 7
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.15, 0.15)
        # Vase shape: fronds arch outward at 30-45°
        make_fern_frond(bm, Vector((0, 0, 0.05)),
                        length=1.6, n_pinnae=14,
                        pinna_len=0.10, pinna_width=0.06,
                        arch=0.50, droop=0.28, angle_y=angle,
                        color_base=(0.10, 0.32, 0.04),
                        color_tip=(0.30, 0.52, 0.15),
                        uv_layer=uv, col_layer=co)

    # Brown fertile frond in center
    make_fern_frond(bm, Vector((0, 0, 0.05)),
                    length=0.9, n_pinnae=8,
                    pinna_len=0.03, pinna_width=0.02,
                    arch=0.12, droop=0.1,
                    angle_y=rng.uniform(0, math.tau),
                    color_base=(0.35, 0.22, 0.10),
                    color_tip=(0.40, 0.28, 0.14),
                    uv_layer=uv, col_layer=co)

    return bm


def make_christmas_fern():
    """Christmas fern (Polystichum acrostichoides) — 0.3-0.6m.
    EVERGREEN. Low rosette of glossy deep green fronds."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(802)

    n_fronds = 8
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.1, 0.1)
        # Low rosette: more horizontal spread
        make_fern_frond(bm, Vector((0, 0, 0.02)),
                        length=0.50, n_pinnae=10,
                        pinna_len=0.05, pinna_width=0.035,
                        arch=0.85, droop=0.15, angle_y=angle,
                        color_base=(0.03, 0.16, 0.02),
                        color_tip=(0.06, 0.24, 0.04),
                        uv_layer=uv, col_layer=co)

    return bm


FERNS = [
    (make_ostrich_fern, "Fern_Ostrich"),
    (make_christmas_fern, "Fern_Christmas"),
]

if __name__ == "__main__":
    print("=" * 60)
    print(f"Building {len(FERNS)} fern models with individual pinnae")
    print("=" * 60)

    for func, name in FERNS:
        clear_scene()
        bm = func()
        finalize_and_export(bm, name)

    print(f"\nDone — {len(FERNS)} fern GLBs exported")

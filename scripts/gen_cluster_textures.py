#!/usr/bin/env python3
"""Generate blade-silhouette alpha textures for grass cluster LOD tier.

Each texture depicts 4-6 thin individual blade shapes on a transparent
background. When applied to crossed-card geometry, the alpha cutout makes
the cards read as "a few blades" rather than "a flat card" — bridging the
visual character between particle blades (Tier 1) and dense tuft cards (Tier 3).

Color is neutral gray — the shader applies zone palette color via
grass_base_color(), so the texture only provides luminance variation + alpha.
"""
import numpy as np
from PIL import Image
import os

TEX_W, TEX_H = 128, 256

def make_blade_texture(n_blades: int, blade_w_frac: float, heights: list[float],
                       offsets: list[float], curve: list[float]) -> Image.Image:
    """Generate a blade silhouette texture.

    Args:
        n_blades: number of blade silhouettes
        blade_w_frac: blade width as fraction of texture width (at base)
        heights: list of blade heights as fraction of texture height (per blade)
        offsets: list of horizontal center offsets (0=left, 1=right, per blade)
        curve: list of horizontal lean at tip (pixels, per blade)
    """
    img = np.zeros((TEX_H, TEX_W, 4), dtype=np.uint8)

    for i in range(n_blades):
        h_frac = heights[i]
        cx = offsets[i] * TEX_W  # center x
        base_hw = blade_w_frac * TEX_W * 0.5  # half-width at base
        lean = curve[i]

        blade_top = int(TEX_H * (1.0 - h_frac))  # top pixel row
        blade_bot = TEX_H - 1  # bottom pixel row

        for y in range(blade_top, blade_bot + 1):
            # t=0 at base, t=1 at tip
            t = 1.0 - (y - blade_top) / max(blade_bot - blade_top, 1)
            # Taper: tip is 15% of base width
            hw = base_hw * (1.0 - t * 0.85)
            # Horizontal lean
            cx_at_y = cx + lean * t

            x_lo = max(0, int(cx_at_y - hw))
            x_hi = min(TEX_W - 1, int(cx_at_y + hw))

            if x_lo > x_hi:
                continue

            # Luminance: slight root-to-tip gradient (darker at base)
            lum_base = 100 + int(40 * t)  # 100 at root, 140 at tip
            # Slight variation across blade width
            for x in range(x_lo, x_hi + 1):
                dx = abs(x - cx_at_y) / max(hw, 0.5)
                edge_darken = 1.0 - dx * 0.15  # edges slightly darker
                lum = int(lum_base * edge_darken)
                img[y, x] = [lum, lum + 8, lum - 5, 255]  # slight green tint

    return Image.fromarray(img, 'RGBA')


# Biome definitions: sparse blade silhouettes
biomes = {
    "Cluster_Lawn": {
        "n_blades": 5,
        "blade_w": 0.06,  # thin maintained blades
        "heights": [0.75, 0.85, 0.80, 0.70, 0.78],
        "offsets": [0.15, 0.32, 0.50, 0.68, 0.85],
        "curve":   [-2, 1, 0, -1, 3],
    },
    "Cluster_Shade": {
        "n_blades": 4,
        "blade_w": 0.055,  # fine fescue — thinner
        "heights": [0.82, 0.90, 0.78, 0.85],
        "offsets": [0.18, 0.40, 0.62, 0.82],
        "curve":   [-3, 2, -1, 4],
    },
    "Cluster_Wild": {
        "n_blades": 4,
        "blade_w": 0.08,  # switchgrass — wider, taller
        "heights": [0.88, 0.95, 0.80, 0.92],
        "offsets": [0.15, 0.38, 0.62, 0.85],
        "curve":   [-5, 3, -2, 6],
    },
    "Cluster_Sedge": {
        "n_blades": 4,
        "blade_w": 0.065,
        "heights": [0.80, 0.88, 0.75, 0.84],
        "offsets": [0.17, 0.39, 0.61, 0.83],
        "curve":   [-4, 2, -1, 5],
    },
}

out_dir = os.path.join(os.path.dirname(__file__), '..', 'textures', 'grass')
os.makedirs(out_dir, exist_ok=True)

for name, cfg in biomes.items():
    tex = make_blade_texture(
        cfg["n_blades"], cfg["blade_w"],
        cfg["heights"], cfg["offsets"], cfg["curve"])
    path = os.path.join(out_dir, f"{name}_card.png")
    tex.save(path)
    print(f"  {name}: {TEX_W}x{TEX_H} → {path}")

print("Done — 4 cluster blade textures generated")

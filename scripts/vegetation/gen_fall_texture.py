"""Make the DRAB FALL albedo for the London plane leaf by recoloring the summer
real-leaf texture (same leaf, seasonal color). Palette measured from
reference_photos/london planetree/london-plane-tree-leaves-autumn-color-...jpg:
russet (0.58,0.32,0.15) -> ochre (0.73,0.49,0.15) -> gold (0.91,0.74,0.32), with
heavy brown MOTTLING and edge browning (the plane's autumn signature; warm yellow-
brown, never maple-red). Luminance drives the gradient so veins/teeth structure
survives. Keeps the alpha. Output: textures/leaves/london_plane_real_albedo_fall.png

Run: python3 scripts/vegetation/gen_fall_texture.py
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(PROJ, "textures/leaves/london_plane_real_albedo.png")
OUT = os.path.join(PROJ, "textures/leaves/london_plane_real_albedo_fall.png")

a = np.asarray(Image.open(SRC)).astype(np.float32) / 255.0
rgb, alpha = a[..., :3], a[..., 3]
leaf = alpha > 0.3
lum = rgb @ np.array([0.3, 0.59, 0.11], np.float32)

lo, hi = np.percentile(lum[leaf], 5), np.percentile(lum[leaf], 95)
t = np.clip((lum - lo) / ((hi - lo) or 1), 0, 1)            # 0 dark .. 1 bright

brown = np.array([0.50, 0.30, 0.14], np.float32)
ochre = np.array([0.73, 0.49, 0.15], np.float32)
gold = np.array([0.92, 0.77, 0.36], np.float32)
dark = np.array([0.36, 0.21, 0.10], np.float32)            # mottle/edge brown

tt = t[..., None]
col = np.where(tt < 0.5, brown + (ochre - brown) * (tt / 0.5),
               ochre + (gold - ochre) * ((tt - 0.5) / 0.5))

# brown MOTTLING in low-frequency patches (matches the real blotchy fall leaf)
rng = np.random.default_rng(7)
noise = ndimage.gaussian_filter(rng.random(lum.shape).astype(np.float32), sigma=16)
noise = (noise - noise.min()) / (noise.ptp() or 1)
blotch = np.clip((noise - 0.45) * 2.2, 0, 1)[..., None]
col = col * (1 - blotch * 0.6) + dark * (blotch * 0.6)

# EDGE browning: near the leaf margin browns first
edt = ndimage.distance_transform_edt(leaf).astype(np.float32)
edt /= (edt.max() or 1)
edge = np.clip(1 - edt * 3.0, 0, 1)[..., None]
col = col * (1 - edge * 0.45) + dark * (edge * 0.45)

col = np.clip(col, 0, 1) * leaf[..., None]                 # background stays black
out = (np.dstack([col, alpha]) * 255).astype(np.uint8)
Image.fromarray(out, "RGBA").save(OUT)

# preview over gray
bg = Image.new("RGBA", (out.shape[1], out.shape[0]), (130, 132, 135, 255))
bg.alpha_composite(Image.fromarray(out, "RGBA"))
bg.convert("RGB").save(OUT.replace(".png", "_preview.png"))
print("wrote", OUT)

"""Make an alpha-cutout leaf TEXTURE from a real leaf photo on white.

This is the research-backed path (docs/research-game-ready-leaves.md S1-S2): realistic
game leaves are alpha cards textured from a photographed/scanned real leaf. IMG_4070 is
a real London plane leaf on near-white paper -> cut the green leaf out to RGBA.

Output: textures/leaves/london_plane_real_albedo.png (RGBA, premultiplied-safe),
and a preview composited over neutral gray so the cutout can be eyeballed.

Run: python3 scripts/vegetation/cut_leaf_texture.py
"""
import os
import numpy as np
from PIL import Image, ImageFilter

SRC = "reference_photos/london planetree/IMG_4070-scaled-e1603199840808.jpg"
OUTDIR = "textures/leaves"
os.makedirs(OUTDIR, exist_ok=True)

im = Image.open(SRC).convert("RGB")
a = np.asarray(im).astype(np.float32) / 255.0
R, G, B = a[..., 0], a[..., 1], a[..., 2]

# Leaf is green: G clearly exceeds R and B. Paper (white) and shadow (gray) have
# R~=G~=B, so greenness ~ 0 there. Petiole is brown/tan (low greenness) -> recovered
# below via a darkness term so we don't drop the stalk.
greenness = G - 0.5 * (R + B)
brightness = (R + G + B) / 3.0
# leaf = sufficiently green OR (dark enough AND not bright paper)
leaf = (greenness > 0.045) | ((brightness < 0.45) & (greenness > -0.02))
alpha = (leaf.astype(np.uint8) * 255)

# Clean: median filter to remove speckle, then keep the largest blob region only.
amask = Image.fromarray(alpha, "L").filter(ImageFilter.MedianFilter(size=5))
alpha = np.asarray(amask)

# Keep largest connected component (drops stray text/specks on the paper)
try:
    from scipy import ndimage
    lbl, n = ndimage.label(alpha > 127)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n + 1))
        biggest = int(np.argmax(sizes)) + 1
        alpha = np.where(lbl == biggest, 255, 0).astype(np.uint8)
except Exception as e:
    print("scipy unavailable, skipping component filter:", e)

# Feather edge by 1px so the alpha-scissor edge isn't jagged
alpha_img = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.8))
alpha = np.asarray(alpha_img)

rgba = np.dstack([np.asarray(im), alpha]).astype(np.uint8)
out = Image.fromarray(rgba, "RGBA")

# crop to leaf bbox + small margin
ys, xs = np.where(alpha > 20)
if len(xs):
    m = 12
    x0, x1 = max(0, xs.min() - m), min(out.width, xs.max() + m)
    y0, y1 = max(0, ys.min() - m), min(out.height, ys.max() + m)
    out = out.crop((x0, y0, x1, y1))

albedo_path = os.path.join(OUTDIR, "london_plane_real_albedo.png")
out.save(albedo_path)

# preview over neutral gray
bg = Image.new("RGBA", out.size, (130, 132, 135, 255))
bg.alpha_composite(out)
prev = os.path.join(OUTDIR, "london_plane_real_preview.png")
bg.convert("RGB").save(prev)
cov = (np.asarray(out)[..., 3] > 127).mean()
print(f"wrote {albedo_path}  size={out.size}  coverage={cov:.1%}")
print(f"wrote {prev}")

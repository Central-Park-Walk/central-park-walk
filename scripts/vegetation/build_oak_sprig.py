"""Composite the Lobatae oak leaf SPRIG (Chris's london-plane method, run by Claude).

Process (per Chris, 2026-06-24): take one good red-oak leaf already cut out (RGBA),
make 4 copies, flip/rotate each for aesthetic, lay them on a forking twig so each
leaf's petiole overlaps the twig at the join, flatten onto the solid dark-green
background (~RGB 15,80,50) so make_oak_cluster_from_photo.py keys it like the LP sprig.

Source leaf: reference_photos/oak/_sources/bysa3_leaf.png  (Quercus rubra, cut to alpha;
Wikimedia, heavily transformed → generic silhouette in the final card).
Out: reference_photos/oak/red_oak_sprig.jpg   (+ _rgba.png preview on transparency)
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(PROJ, "reference_photos", "oak", "_sources", "bysa3_leaf.png")
OUTDIR = os.path.join(PROJ, "reference_photos", "oak")

BG = (15, 80, 50)            # the LP chroma-key background
CANVAS = 1500
TWIG = (118, 96, 52)         # olive-brown twig (LP-like yellow-brown)
TWIG_DK = (86, 68, 34)

# Each leaf: anchor (petiole lands here), rot (PIL CCW deg; blade points DOWN at 0,
# so 180=tip-up, 90=tip-right, 270=tip-left), scale, mirror. Airy fan like the LP sprig:
# apex up, two upper sides radiating OUT, one low — clear gaps, twig visible between.
LEAVES = [
    dict(anchor=(752, 802),  rot=184, scale=0.70, mirror=False),  # apex  (tip up)
    dict(anchor=(892, 848),  rot=120, scale=0.66, mirror=False),  # right (tip up-right)
    dict(anchor=(636, 856),  rot=240, scale=0.63, mirror=True),   # left  (tip up-left)
    dict(anchor=(792, 928),  rot=352, scale=0.62, mirror=True),   # low   (tip down)
]
# Twig: main stem base → junction, with branchlets to each side/low petiole.
TWIG_BASE = (772, 1140)
MAIN_TOP = (756, 805)


def deglare(im):
    """Roll off the source leaf's specular sun-glints so it reads as matte foliage."""
    arr = np.asarray(im).astype(np.float32)
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    hi = np.clip((lum - 150.0) / 70.0, 0.0, 1.0)[..., None]   # 0 below 150 → 1 at 220
    tint = np.array([58.0, 98.0, 52.0])                       # pull glints toward leaf-green
    rgb = arr[..., :3]
    rgb = rgb * (1 - 0.72 * hi) + tint * (0.72 * hi)
    return Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA")


def load_leaf():
    im = Image.open(SRC).convert("RGBA")
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > 24)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return deglare(im)


def place(leaf, anchor, rot, scale, mirror):
    """Return a CANVAS-sized RGBA layer with the leaf's petiole(top-centre) at anchor,
    rotated by `rot` (blade down at 0)."""
    lf = leaf
    if mirror:
        lf = lf.transpose(Image.FLIP_LEFT_RIGHT)
    w, h = int(lf.width * scale), int(lf.height * scale)
    lf = lf.resize((w, h), Image.LANCZOS)
    # pad to a square big enough to rotate, petiole(top-centre) at pad centre
    pad = int(np.hypot(w, h)) + 8
    sq = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
    sq.alpha_composite(lf, ((pad - w) // 2, pad // 2))      # petiole at (pad/2, pad/2)
    sq = sq.rotate(rot, resample=Image.BICUBIC, expand=False, center=(pad / 2, pad / 2))
    layer = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    layer.alpha_composite(sq, (int(anchor[0] - pad / 2), int(anchor[1] - pad / 2)))
    return layer


def draw_twig(canvas):
    d = ImageDraw.Draw(canvas)
    # main stem (tapered: dark wide underlay, lighter narrower on top)
    def seg(p0, p1, w0):
        for col, wd in ((TWIG_DK, w0 + 4), (TWIG, w0)):
            d.line([p0, p1], fill=col + (255,), width=wd)
    seg(TWIG_BASE, (766, 880), 14)
    seg((766, 880), MAIN_TOP, 9)
    # branchlets run slightly PAST each petiole so the twig tucks under the leaf
    seg((768, 905), LEAVES[3]["anchor"], 9)     # low
    seg((760, 852), LEAVES[2]["anchor"], 8)     # left
    seg((760, 846), LEAVES[1]["anchor"], 8)     # right
    return canvas


def main():
    leaf = load_leaf()
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw_twig(canvas)                                   # twig first (under leaves)
    for L in LEAVES:
        canvas.alpha_composite(place(leaf, **L))        # leaves overlap twig at joins
    # trim to content
    a = np.asarray(canvas)[..., 3]
    ys, xs = np.where(a > 16)
    canvas = canvas.crop((xs.min() - 12, ys.min() - 12, xs.max() + 12, ys.max() + 12))
    canvas.save(os.path.join(OUTDIR, "red_oak_sprig_rgba.png"))
    # flatten onto the LP key-green
    flat = Image.new("RGBA", canvas.size, BG + (255,))
    flat.alpha_composite(canvas)
    flat.convert("RGB").save(os.path.join(OUTDIR, "red_oak_sprig.jpg"), quality=95)
    cov = (a > 16).mean()
    print(f"sprig {canvas.size}  leaf-coverage {cov*100:.1f}%  → reference_photos/oak/red_oak_sprig.jpg")


if __name__ == "__main__":
    main()

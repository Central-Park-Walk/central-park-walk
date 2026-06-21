#!/usr/bin/env python3
"""Single-leaf OPAQUE surface texture for the true-3D Mtree-distributed leaf.

The true-3D leaf IS its own silhouette (geometry defines the outline), so it must
NOT be an alpha-cutout cluster card — that punches the card's transparent gaps as
holes through solid leaves and shows white shards (user 2026-06-20). It needs a
FULLY-OPAQUE single-leaf SURFACE map: blade value + palmate veins, alpha=1.

The runtime leaf shader (tree_leaf.gdshader) uses the texture mainly for LUMINANCE
modulation (`col = v_leaf_color * (0.5 + lum*0.5)`) and tints with the per-species
green — so this map carries the vein/blade light STRUCTURE; hue is secondary.

Vein endpoints come from leaf_outline.palmate_outline() — the SAME outline the
geometry uses — so the palmate main veins always point at the actual lobe tips
(no shape/texture drift). Surface modelled from real flat-leaf refs: paler
yellow-green veins, gentle inter-vein quilting, slightly darker margins/sinuses.

Usage:
    python3 scripts/vegetation/gen_single_leaf_tex.py --species london_plane \
        --out models/trees/leaf_textures/london_plane_leaf.png
"""
import argparse
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from leaf_outline import palmate_outline  # same dir; sys.path[0] = script dir

# Luminance-bearing palette (shader tints hue; relative VALUE is what matters).
# Mid-green blade, distinctly PALER veins (real plane veins are yellow-green and
# read lighter), slightly darker margin/sinus.
BLADE = np.array([70, 110, 50], np.float32)
VEIN = np.array([150, 176, 120], np.float32)


def _line(draw, p0, p1, w, col):
    draw.line([p0, p1], fill=tuple(int(c) for c in col) + (255,), width=max(1, int(w)))


def _tapered(draw, p0, p1, w0, w1, col, steps=14):
    """Draw p0->p1 with width tapering w0 (start) -> w1 (end) — real veins are
    thick at the stem and taper to the margin, which reads the flow direction."""
    c = tuple(int(v) for v in col) + (255,)
    for s in range(steps):
        t0, t1 = s / steps, (s + 1) / steps
        a = (p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0)
        b = (p0[0] + (p1[0] - p0[0]) * t1, p0[1] + (p1[1] - p0[1]) * t1)
        w = max(1, int(round(w0 + (w1 - w0) * t0)))
        draw.line([a, b], fill=c, width=w)


def make_leaf_tex(size=512, cfg=None):
    _, _, tip_uv, base_uv = palmate_outline(cfg)

    img = Image.new("RGBA", (size, size), tuple(int(c) for c in BLADE) + (255,))
    arr = np.asarray(img).astype(np.float32)

    # Gentle inter-vein quilting: low-frequency value variation (areoles) so the
    # blade isn't a dead flat fill. Built at low res + upscaled = soft blobs.
    rng = np.random.default_rng(7)
    low = rng.normal(0.0, 1.0, (16, 16)).astype(np.float32)
    quilt = np.asarray(Image.fromarray((low * 18 + 128).astype(np.uint8)).resize(
        (size, size), Image.BICUBIC), np.float32) - 128.0
    arr[..., :3] += quilt[..., None] * 0.5

    # Slightly darker toward the margins/sinuses (radial falloff from leaf centre).
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.sqrt(((xx - size * 0.5) / (size * 0.5)) ** 2 +
                ((yy - size * 0.46) / (size * 0.54)) ** 2)
    vig = np.clip(1.0 - 0.14 * np.clip(r - 0.45, 0.0, 1.0), 0.82, 1.0)
    arr[..., :3] *= vig[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    draw = ImageDraw.Draw(img)
    wbase = max(3, size // 70)   # thick at the stem
    wtip = max(1, size // 360)   # thin at the lobe tip
    wsec = max(1, size // 300)

    def px(uv):
        return (uv[0] * size, uv[1] * size)

    bpx = px(base_uv)
    # tip_uv order from palmate_outline: [central, +lat, -lat, +basal, -basal].
    for idx, tip in enumerate(tip_uv):
        tpx = px(tip)
        _tapered(draw, bpx, tpx, wbase, wtip, VEIN)
        # No herringbone on the low BASAL veins (idx 3,4) — secondaries down there
        # cluster at the petiole and read as anatomically wrong (user 2026-06-20,
        # ringed the base herringbone). Only central + upper-laterals carry rungs.
        if idx >= 3:
            continue
        # Secondaries branch off the main vein toward the margin, angled FORWARD
        # toward the lobe tip (toward the marginal teeth) — real plane venation.
        dx, dy = tpx[0] - bpx[0], tpx[1] - bpx[1]
        L = math.hypot(dx, dy) or 1.0
        perp = (-dy / L, dx / L)
        fwd = (dx / L, dy / L)
        # Herringbone starts a bit above the stem (t~0.34, clear of the petiole)
        # and rungs up to the tip; rungs nearest the stem are longest.
        for t in (0.34, 0.48, 0.61, 0.73, 0.84):
            mx, my = bpx[0] + dx * t, bpx[1] + dy * t
            slen = size * 0.11 * (1.0 - t * 0.45)
            # Forward (toward-tip) lean DOMINATES the sideways spread, so every
            # secondary sweeps tipward regardless of which main vein it's on —
            # real plane venation feathers toward the lobe tips, never back to
            # the stem. (Old 0.55 forward let perp dominate on the lateral/basal
            # veins and they swept backward — user 2026-06-20.)
            for sgn in (-1, 1):
                ex = mx + sgn * perp[0] * slen * 0.55 + fwd[0] * slen * 1.15
                ey = my + sgn * perp[1] * slen * 0.55 + fwd[1] * slen * 1.15
                _line(draw, (mx, my), (ex, ey), wsec, VEIN * 0.96)

    img = img.filter(ImageFilter.GaussianBlur(radius=size / 480.0))

    # V-AXIS CONVENTION FIX (user 2026-06-20): palmate_outline puts the apex at
    # v=0 and the petiole/base at v=1, and we author here in PIL space (row 0 =
    # TOP of file). But the geometry's apex vertex (v=0) samples the OPPOSITE end
    # of the file once rendered (Blender viewport == glTF/Godot after the export
    # V-flip), so the venation came out upside-down — convergence at the apex
    # instead of the petiole. Flipping the finished image top↔bottom aligns the
    # authored apex pixels with where the apex vertex actually samples; veins now
    # radiate from the base. This is the single canonical place to resolve the
    # PIL-top vs UV-v mismatch (was the source of the repeated orientation flips).
    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    out = np.asarray(img).astype(np.float32)
    out[..., 3] = 255  # fully opaque — geometry is the silhouette
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--species", default="london_plane")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=512)
    args = ap.parse_args()
    im = make_leaf_tex(args.size)
    im.save(args.out)
    print(f"wrote {args.out}  ({im.size}, opaque single-leaf surface, veins aligned to lobe tips)")

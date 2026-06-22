"""Composite the REAL London-plane leaf cutout into a CLUSTER CARD texture.

This is the real-photo replacement for leaf_card_utils._leaf_edge_plane_lobes
(the crude procedural polar-painted cluster). It scatters N rotated/scaled copies
of the real single-leaf cutout (textures/leaves/london_plane_real_albedo.png —
real veins/teeth/silhouette/color) into a square RGBA cluster, overlapping toward
a continuous foliage mass with clean alpha for alpha-scissor. Runs in plain
CPython (PIL) OUTSIDE Blender, per the architecture note in generate_trees_mtree
(PIL is not in Blender's bundled Python). Output PNGs are loaded as the leaf
material image by create_leaf_material(real_texture=...).

Run: python3 scripts/vegetation/make_leaf_cluster_texture.py
Outputs: textures/leaves/london_plane_cluster.png  (summer)
         textures/leaves/london_plane_cluster_fall.png  (fall)
"""
import os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
TEXDIR = os.path.join(PROJ, "textures", "leaves")

TEX = 1024          # matches london_plane leaf_tex_size
# TWIG SPRIG (user 2026-06-21 PM: "the cluster should only have 3 leaves, and twigs
# should separate them, 2-4 leaves per cluster"). NOT a packed rosette/ball — a real
# twig with a few leaves attached at spaced nodes, the twig segments visibly between
# them, blades fanning out, tips OUTWARD. Shape guide: 2SA8J91 (a watermarked Alamy
# stock photo — INSPIRATION ONLY, never shippable). Built from the clean single-leaf
# cutout (london_plane_real_albedo.png).
N_LEAVES = 3        # leaves per sprig card (2-4 range; 3 = canonical)
SEED = 447          # london_plane leaf_seed
TWIG_COL = (96, 84, 52)     # olive-brown london-plane twig
PETIOLE_COL = (120, 116, 70)  # greener petiole


def trim_to_alpha(im):
    """Crop an RGBA image to its alpha bounding box."""
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > 20)
    if len(xs) == 0:
        return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def _bezier(p0, p1, p2, t):
    u = 1.0 - t
    x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
    y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
    return x, y


def _draw_taper(draw, p0, p1, p2, w0, w1, color, n=180):
    """Draw a tapered (w0→w1) quadratic-bezier twig as overlapping discs."""
    for i in range(n + 1):
        t = i / n
        x, y = _bezier(p0, p1, p2, t)
        w = w0 + (w1 - w0) * t
        draw.ellipse([x - w, y - w, x + w, y + w], fill=color)


def build_cluster(src_png, out_png):
    leaf = trim_to_alpha(Image.open(src_png).convert("RGBA"))
    rng = np.random.default_rng(SEED)
    canvas = Image.new("RGBA", (TEX, TEX), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # --- Main twig: a gently curved, tapering stem rising from the base ---
    # Image +y is DOWN. Base (thick) at bottom-center, tip (thin) upper area.
    p0 = (TEX * 0.50, TEX * 0.95)            # base — attaches to the branch
    p1 = (TEX * 0.40, TEX * 0.55)            # control → gentle S
    p2 = (TEX * 0.57, TEX * 0.18)            # apex (thin)
    _draw_taper(draw, p0, p1, p2, w0=11, w1=3, color=TWIG_COL)

    # --- Leaf nodes spaced ALONG the twig (so twig segments separate the leaves) ---
    # Each: (t along twig, outward petiole angle [screen coords, -y is up], leaf
    # height frac, petiole length frac). Alternating sides → natural fan; lower leaf
    # largest. Angles fan up-and-out.
    nodes = [
        (0.34, np.radians(168), 0.42, 0.11),   # lower — out to the LEFT, big
        (0.60, np.radians(-22), 0.39, 0.10),   # mid   — out to the RIGHT
        (0.82, np.radians(-92), 0.33, 0.09),   # upper — UP, smaller
    ][:N_LEAVES]

    for t, phi, hfrac, pet in nodes:
        nx, ny = _bezier(p0, p1, p2, t)
        dx, dy = np.cos(phi), np.sin(phi)
        # Petiole: short stem from the twig node outward to the leaf base.
        pet_len = pet * TEX
        bx, by = nx + dx * pet_len, ny + dy * pet_len
        draw.line([(nx, ny), (bx, by)], fill=PETIOLE_COL, width=6)

        # Leaf: base (petiole end, top of source image) sits at (bx,by); blade and
        # TIP extend further outward along phi. Rotate the source leaf (petiole up,
        # tip down = +y) so its tip points along phi.
        h = hfrac * TEX
        scale = h / leaf.height
        w = max(8, int(leaf.width * scale))
        hh = max(8, int(leaf.height * scale))
        lf = leaf.resize((w, hh), Image.LANCZOS)
        ang = -np.degrees(phi) + 90 + rng.uniform(-8, 8)   # tip → outward along phi
        lf = lf.rotate(ang, expand=True, resample=Image.BICUBIC)
        # subtle per-leaf tint variation
        arr = np.asarray(lf).astype(np.float32)
        arr[..., :3] *= rng.uniform(0.88, 1.08)
        arr[..., 1] *= rng.uniform(0.97, 1.03)
        lf = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
        # Place leaf CENTER a bit beyond the base along phi (blade reaches outward).
        cx = bx + dx * (0.42 * h)
        cy = by + dy * (0.42 * h)
        canvas.alpha_composite(lf, (int(cx - lf.width / 2), int(cy - lf.height / 2)))

    canvas.save(out_png)
    cov = (np.asarray(canvas)[..., 3] > 30).mean()
    print(f"wrote {out_png}  ({TEX}x{TEX}, coverage {cov*100:.1f}%, {N_LEAVES}-leaf sprig)")

    # preview over neutral gray
    bg = Image.new("RGBA", (TEX, TEX), (130, 132, 135, 255))
    bg.alpha_composite(canvas)
    bg.convert("RGB").save(out_png.replace(".png", "_preview.png"))


if __name__ == "__main__":
    build_cluster(os.path.join(TEXDIR, "london_plane_real_albedo.png"),
                  os.path.join(TEXDIR, "london_plane_cluster.png"))
    build_cluster(os.path.join(TEXDIR, "london_plane_real_albedo_fall.png"),
                  os.path.join(TEXDIR, "london_plane_cluster_fall.png"))

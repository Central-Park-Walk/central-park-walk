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
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
TEXDIR = os.path.join(PROJ, "textures", "leaves")

TEX = 1024          # matches london_plane leaf_tex_size
N_LEAVES = 18       # overlapping leaves per cluster card
SEED = 447          # london_plane leaf_seed


def trim_to_alpha(im):
    """Crop an RGBA image to its alpha bounding box."""
    a = np.asarray(im)[..., 3]
    ys, xs = np.where(a > 20)
    if len(xs) == 0:
        return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def build_cluster(src_png, out_png):
    leaf = trim_to_alpha(Image.open(src_png).convert("RGBA"))
    rng = np.random.default_rng(SEED)
    canvas = Image.new("RGBA", (TEX, TEX), (0, 0, 0, 0))

    # base leaf size so several leaves overlap into a mass (~38% of canvas tall)
    base_h = 0.38 * TEX
    # spheroidal placement: center-weighted radius, full-circle angle
    placements = []
    for _ in range(N_LEAVES):
        r = (rng.random() ** 0.65) * 0.40 * TEX          # center-dense
        th = rng.random() * 2 * np.pi
        cx = TEX / 2 + r * np.cos(th)
        cy = TEX / 2 + r * np.sin(th) * 0.85             # slightly flattened
        placements.append((r, cx, cy, th))
    # paint far leaves first so near/central ones sit on top
    placements.sort(key=lambda p: -p[0])

    for r, cx, cy, th in placements:
        scale = base_h * rng.uniform(0.80, 1.20) / leaf.height
        w = max(8, int(leaf.width * scale))
        h = max(8, int(leaf.height * scale))
        lf = leaf.resize((w, h), Image.LANCZOS)
        # rotate: petiole roughly points back toward cluster center + jitter
        ang = -np.degrees(th) + 90 + rng.uniform(-55, 55)
        lf = lf.rotate(ang, expand=True, resample=Image.BICUBIC)
        # gentle per-leaf brightness/tint jitter for natural variation
        arr = np.asarray(lf).astype(np.float32)
        bright = rng.uniform(0.82, 1.10)
        arr[..., :3] *= bright
        arr[..., 1] *= rng.uniform(0.97, 1.04)           # green wobble
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        lf = Image.fromarray(arr, "RGBA")
        px = int(cx - lf.width / 2)
        py = int(cy - lf.height / 2)
        canvas.alpha_composite(lf, (px, py))

    canvas.save(out_png)
    cov = (np.asarray(canvas)[..., 3] > 30).mean()
    print(f"wrote {out_png}  ({TEX}x{TEX}, coverage {cov*100:.1f}%, {N_LEAVES} leaves)")

    # preview over neutral gray
    bg = Image.new("RGBA", (TEX, TEX), (130, 132, 135, 255))
    bg.alpha_composite(canvas)
    bg.convert("RGB").save(out_png.replace(".png", "_preview.png"))


if __name__ == "__main__":
    build_cluster(os.path.join(TEXDIR, "london_plane_real_albedo.png"),
                  os.path.join(TEXDIR, "london_plane_cluster.png"))
    build_cluster(os.path.join(TEXDIR, "london_plane_real_albedo_fall.png"),
                  os.path.join(TEXDIR, "london_plane_cluster_fall.png"))

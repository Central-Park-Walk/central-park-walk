"""
Post-bake alpha premultiplication for impostor atlases.

Replaces the older dilation pass. Premultiplied alpha solves the mipmap
halo problem by construction: when the GPU averages an opaque tree pixel
(0.4, 0.6, 0.2, 1.0) with a transparent pixel (0.4, 0.6, 0.2, 0.0) under
straight alpha, the averaged color is full-strength (0.4, 0.6, 0.2) at
alpha 0.5 — a bright halo extending the silhouette.

Premultiplied alpha stores (color * alpha, alpha). The same averaging
yields (0.2, 0.3, 0.1, 0.5) — half-bright at half-alpha, which renders
correctly as a clean alpha-50% pixel. No halo.

Requires the impostor shader to use `render_mode blend_premul_alpha`
(equivalent: BLEND_PREMUL_ALPHA in Godot StandardMaterial3D).

Also neutral-fills the transparent background of the normal and depth
atlases (normal -> (128,128,255) = facing camera, depth -> 128 = the
shader's 0.5 parallax reference). The impostor shader's parallax pass
samples depth BEFORE the alpha discard, so background texels bleed into
silhouette edges through bilinear/mip filtering — neutral values make
that bleed a no-op instead of a UV warp.

Usage:
    python3 scripts/premultiply_impostors.py

Runs in <1 second per atlas. Idempotent (re-running on an already-
premultiplied atlas produces the same output: color * alpha is a no-op
once the dilated/non-dilated transparent regions have been zeroed).
"""
import os
import sys
import glob
import numpy as np
from PIL import Image

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPOSTOR_DIR = os.path.join(PROJ, "textures", "impostors")


def premultiply(path):
    im = np.array(Image.open(path).convert("RGBA"), dtype=np.float32)
    rgb = im[..., :3]
    alpha = im[..., 3:4] / 255.0
    out_rgb = np.clip(rgb * alpha, 0.0, 255.0).astype(np.uint8)
    out_alpha = im[..., 3:4].astype(np.uint8)
    out = np.concatenate([out_rgb, out_alpha], axis=-1)
    Image.fromarray(out).save(path)


def neutral_fill(path, fill_rgb):
    """Replace the RGB of fully transparent texels with a neutral value."""
    im = np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)
    bg = im[..., 3] < 8
    im[bg, 0] = fill_rgb[0]
    im[bg, 1] = fill_rgb[1]
    im[bg, 2] = fill_rgb[2]
    Image.fromarray(im).save(path)


def main():
    paths = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_albedo*.png")))
    if not paths:
        print(f"premultiply_impostors: no atlases found in {IMPOSTOR_DIR}", file=sys.stderr)
        sys.exit(1)
    for i, p in enumerate(paths):
        premultiply(p)
        if (i + 1) % 10 == 0 or i == len(paths) - 1:
            print(f"  {i+1}/{len(paths)} {os.path.basename(p)}")
    print(f"premultiply_impostors: done — {len(paths)} atlases premultiplied")

    nrm_paths = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_normal.png")))
    for p in nrm_paths:
        neutral_fill(p, (128, 128, 255))   # encoded (0,0,1): facing camera
    dep_paths = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_depth.png")))
    for p in dep_paths:
        neutral_fill(p, (128, 128, 128))   # 0.5: zero parallax shift
    print(f"premultiply_impostors: neutral-filled {len(nrm_paths)} normal + "
          f"{len(dep_paths)} depth atlases")


if __name__ == "__main__":
    main()

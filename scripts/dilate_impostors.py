"""
Post-bake dilation for impostor atlases.

Each atlas has transparent regions outside the tree silhouette and between
leaves. When the atlas is mipmapped by the GPU, texels at the silhouette
edge average opaque tree color with transparent black, producing a dark
halo around distant canopies.

This script fills the transparent regions with the nearest opaque pixel's
color (alpha stays 0). Mipmap averaging then pulls from tree-colored
neighbors instead of black, eliminating the halo. This is the standard
texture-island dilation technique used in every alpha-tested atlas
pipeline.

Usage:
    python3 scripts/dilate_impostors.py

Runs in ~1-2 seconds per atlas. No visual change close-up (alpha==0
pixels remain invisible); only distant-mipmap samples benefit.
"""
import os
import sys
import glob
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPOSTOR_DIR = os.path.join(PROJ, "textures", "impostors")


def dilate(path):
    im = np.array(Image.open(path).convert("RGBA"))
    rgb = im[..., :3]
    alpha = im[..., 3]
    mask_opaque = alpha > 0
    if mask_opaque.all():
        return False  # no transparent region to fill
    # Find nearest opaque pixel for every transparent pixel
    _, (iy, ix) = distance_transform_edt(~mask_opaque, return_indices=True)
    filled = rgb[iy, ix]
    out_rgb = np.where(mask_opaque[..., None], rgb, filled).astype(np.uint8)
    out = np.concatenate([out_rgb, alpha[..., None]], axis=-1)
    Image.fromarray(out).save(path)
    return True


def main():
    paths = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_albedo*.png")))
    if not paths:
        print(f"dilate_impostors: no atlases found in {IMPOSTOR_DIR}", file=sys.stderr)
        sys.exit(1)
    n_dilated = 0
    for i, p in enumerate(paths):
        changed = dilate(p)
        n_dilated += int(changed)
        if (i + 1) % 10 == 0 or i == len(paths) - 1:
            print(f"  {i+1}/{len(paths)} {os.path.basename(p)}")
    print(f"dilate_impostors: done — {n_dilated}/{len(paths)} atlases dilated")


if __name__ == "__main__":
    main()

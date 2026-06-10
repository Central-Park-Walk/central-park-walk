"""
Post-bake finalization for impostor atlases (scripts/impostor_baker.gd).

ALBEDO atlases are left untouched: the baker renders with MSAA
alpha-to-coverage over a transparent black background, so the resolved
RGB is already scaled by coverage — the atlas is *born premultiplied*,
exactly what `render_mode blend_premul_alpha` expects. (The old chain
multiplied by alpha again here, which double-darkened edge texels.)

NORMAL and DEPTH atlases store data, not color, so the coverage scaling
is contamination: edge texels are dragged toward encoded black, which
decodes to garbage normals / near-plane depth. Fix per 256x256 frame:
  1. trust texels with alpha >= 0.9 as-is (attenuation <= 10%, below
     visual relevance for fringe data; dividing by stored alpha instead
     over-corrects — under alpha-to-coverage the stored alpha is not the
     rgb attenuation factor — and breaks idempotency),
  2. dilate those texels' values into every weaker/empty texel
     (nearest-solid via distance transform, frame-local so values
     never bleed across atlas frame boundaries),
  3. frames with no solid texels get a neutral fill
     (normal -> (128,128,255) facing camera, depth -> 128 = the
     impostor shader's 0.5 parallax reference).
The impostor shader's parallax pass samples depth BEFORE the alpha
discard, so edge/background texels do get sampled — dilated values make
bilinear/mip bleed a no-op instead of a UV warp or lighting artifact.

Usage:
    python3 scripts/premultiply_impostors.py

Runs in a few seconds for all atlases. Idempotent.
"""
import os
import sys
import glob
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPOSTOR_DIR = os.path.join(PROJ, "textures", "impostors")

FRAME_GRID = 8          # 8x8 octahedral frames per atlas
SOLID_ALPHA = 230       # >= this (~0.9): trust rgb as-is; below: dilate over


def finalize_data_atlas(path, neutral_rgb):
    """Dilate high-confidence texels' values into weak/empty ones."""
    im = np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)
    h, w = im.shape[:2]
    fh, fw = h // FRAME_GRID, w // FRAME_GRID
    rgb = im[..., :3]
    solid = im[..., 3] >= SOLID_ALPHA

    out_rgb = np.empty_like(rgb)
    for fy in range(FRAME_GRID):
        for fx in range(FRAME_GRID):
            ys, xs = slice(fy * fh, (fy + 1) * fh), slice(fx * fw, (fx + 1) * fw)
            s = solid[ys, xs]
            if not s.any():
                out_rgb[ys, xs] = np.array(neutral_rgb, dtype=np.uint8)
                continue
            # Nearest-solid index map (frame-local), then copy values.
            _, (iy, ix) = distance_transform_edt(~s, return_indices=True)
            out_rgb[ys, xs] = rgb[ys, xs][iy, ix]

    im[..., :3] = out_rgb
    Image.fromarray(im).save(path)


def main():
    albedo = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_albedo*.png")))
    if not albedo:
        print(f"premultiply_impostors: no atlases found in {IMPOSTOR_DIR}", file=sys.stderr)
        sys.exit(1)
    print(f"premultiply_impostors: {len(albedo)} albedo atlases left as baked "
          f"(born premultiplied by coverage resolve)")

    nrm_paths = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_normal.png")))
    for p in nrm_paths:
        finalize_data_atlas(p, (128, 128, 255))
    dep_paths = sorted(glob.glob(os.path.join(IMPOSTOR_DIR, "*_impostor_depth.png")))
    for p in dep_paths:
        finalize_data_atlas(p, (128, 128, 128))
    print(f"premultiply_impostors: finalized {len(nrm_paths)} normal + "
          f"{len(dep_paths)} depth atlases (frame-local dilate from solid texels)")


if __name__ == "__main__":
    main()

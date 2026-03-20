#!/usr/bin/env python3
"""Pack raw ambientCG textures into Terrain3D format.

Terrain3D requires two RGBA files per surface:
  albedo:  RGB = color,     A = height (luminance of color if no explicit height)
  normal:  RGB = normal map (OpenGL +Y), A = roughness

All output textures are 1024x1024 to match Terrain3D array requirements.
"""
import sys, os
from pathlib import Path
from PIL import Image
import numpy as np

TEX_DIR = Path(__file__).resolve().parent.parent / "textures"
OUT_DIR = TEX_DIR / "terrain3d"
SIZE = 1024

# Texture sets: name → (color_file, normal_file, roughness_file)
# All paths relative to TEX_DIR
TEXTURE_SETS = {
    "grass": (
        "grass_albedo.jpg",
        "grass_normal.jpg",
        "grass_rough.jpg",
    ),
    "meadow": (
        "forrest_ground_01_Color.jpg",
        "forrest_ground_01_NormalGL.jpg",
        "forrest_ground_01_Roughness.jpg",
    ),
    "rock": (
        "schist_rock_Color.jpg",
        "schist_rock_NormalGL.jpg",
        "schist_rock_Roughness.jpg",
    ),
    "dirt": (
        "park_dirt_Color.jpg",
        "park_dirt_NormalGL.jpg",
        "park_dirt_Roughness.jpg",
    ),
    "shore": (
        "shore_mud_Color.jpg",
        "shore_mud_NormalGL.jpg",
        "shore_mud_Roughness.jpg",
    ),
    "asphalt": (
        "Asphalt012_1K-JPG_Color.jpg",
        "Asphalt012_1K-JPG_NormalGL.jpg",
        "Asphalt012_1K-JPG_Roughness.jpg",
    ),
    "concrete": (
        "Concrete034_1K-JPG_Color.jpg",
        "Concrete034_1K-JPG_NormalGL.jpg",
        "Concrete034_1K-JPG_Roughness.jpg",
    ),
    "paving": (
        "PavingStones130_1K-JPG_Color.jpg",
        "PavingStones130_1K-JPG_NormalGL.jpg",
        "PavingStones130_1K-JPG_Roughness.jpg",
    ),
    "gravel": (
        "Gravel021_1K-JPG_Color.jpg",
        "Gravel021_1K-JPG_NormalGL.jpg",
        "Gravel021_1K-JPG_Roughness.jpg",
    ),
    "wood": (
        "WoodFloor041_1K-JPG_Color.jpg",
        "WoodFloor041_1K-JPG_NormalGL.jpg",
        "WoodFloor041_1K-JPG_Roughness.jpg",
    ),
}


def load_and_resize(path: Path) -> np.ndarray:
    """Load image, convert to RGB/L, resize to SIZE×SIZE."""
    img = Image.open(path)
    if img.size != (SIZE, SIZE):
        img = img.resize((SIZE, SIZE), Image.LANCZOS)
    return np.array(img)


def pack_set(name: str, color_file: str, normal_file: str, rough_file: str):
    """Pack one texture set into two Terrain3D RGBA PNGs."""
    color_path = TEX_DIR / color_file
    normal_path = TEX_DIR / normal_file
    rough_path = TEX_DIR / rough_file

    for p in (color_path, normal_path, rough_path):
        if not p.exists():
            print(f"  SKIP {name}: missing {p.name}")
            return

    # Load channels
    color = load_and_resize(color_path)
    normal = load_and_resize(normal_path)
    rough = load_and_resize(rough_path)

    # Ensure 3-channel
    if color.ndim == 2:
        color = np.stack([color] * 3, axis=-1)
    if normal.ndim == 2:
        normal = np.stack([normal] * 3, axis=-1)
    if rough.ndim == 2:
        pass  # keep as grayscale
    elif rough.ndim == 3:
        rough = rough[:, :, 0]  # take R channel

    # Height = luminance of color (Terrain3D default when no explicit height map)
    height = (0.299 * color[:, :, 0] + 0.587 * color[:, :, 1] + 0.114 * color[:, :, 2]).astype(np.uint8)

    # Pack albedo + height
    albedo_height = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    albedo_height[:, :, :3] = color[:, :, :3]
    albedo_height[:, :, 3] = height

    # Pack normal + roughness
    normal_rough = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    normal_rough[:, :, :3] = normal[:, :, :3]
    normal_rough[:, :, 3] = rough

    # Save
    out_alb = OUT_DIR / f"{name}_albedo_height.png"
    out_nrm = OUT_DIR / f"{name}_normal_rough.png"
    Image.fromarray(albedo_height, 'RGBA').save(out_alb)
    Image.fromarray(normal_rough, 'RGBA').save(out_nrm)
    print(f"  {name}: {out_alb.name} + {out_nrm.name}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Packing {len(TEXTURE_SETS)} texture sets → {OUT_DIR}/")
    for name, (c, n, r) in TEXTURE_SETS.items():
        pack_set(name, c, n, r)
    print("Done.")


if __name__ == "__main__":
    main()

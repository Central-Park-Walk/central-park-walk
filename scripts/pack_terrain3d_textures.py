#!/usr/bin/env python3
"""Pack textures for Terrain3D: albedo+height → RGBA, normal+roughness → RGBA.

Terrain3D requires:
  - Albedo file: RGB = albedo, A = height (used for blending)
  - Normal file: RGB = normal (OpenGL +Y), A = roughness

We generate a flat height (0.5) when no height map is available.
"""
import os
import numpy as np
from PIL import Image

TEX_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "textures")
OUT_DIR = os.path.join(TEX_DIR, "terrain3d")


def load_or_gray(path, size, default_val=128):
    """Load an image or create a solid gray if missing."""
    if os.path.exists(path):
        img = Image.open(path).resize(size, Image.LANCZOS)
        return np.array(img)
    return np.full((*size[::-1], 3 if default_val != 128 else 1), default_val, dtype=np.uint8)


def pack_texture_set(name, albedo_path, normal_path, roughness_path, height_path=None):
    """Pack a texture set into Terrain3D format (two RGBA PNGs)."""
    # Load albedo
    alb = Image.open(albedo_path).convert("RGB")
    size = alb.size
    alb_arr = np.array(alb)

    # Height: use provided or generate from albedo luminance (flat 0.5 default)
    if height_path and os.path.exists(height_path):
        h_arr = np.array(Image.open(height_path).convert("L").resize(size, Image.LANCZOS))
    else:
        # Use albedo value as rough height proxy (darker = lower, lighter = higher)
        h_arr = np.array(alb.convert("L"))

    # Pack albedo + height → RGBA
    alb_rgba = np.zeros((*alb_arr.shape[:2], 4), dtype=np.uint8)
    alb_rgba[:, :, :3] = alb_arr
    alb_rgba[:, :, 3] = h_arr
    alb_out = os.path.join(OUT_DIR, f"{name}_albedo_height.png")
    Image.fromarray(alb_rgba, "RGBA").save(alb_out)
    print(f"  {name}_albedo_height.png ({size[0]}x{size[1]})")

    # Load normal
    nrm = Image.open(normal_path).convert("RGB").resize(size, Image.LANCZOS)
    nrm_arr = np.array(nrm)

    # Load roughness
    rgh = Image.open(roughness_path).convert("L").resize(size, Image.LANCZOS)
    rgh_arr = np.array(rgh)

    # Pack normal + roughness → RGBA
    nrm_rgba = np.zeros((*nrm_arr.shape[:2], 4), dtype=np.uint8)
    nrm_rgba[:, :, :3] = nrm_arr
    nrm_rgba[:, :, 3] = rgh_arr
    nrm_out = os.path.join(OUT_DIR, f"{name}_normal_rough.png")
    Image.fromarray(nrm_rgba, "RGBA").save(nrm_out)
    print(f"  {name}_normal_rough.png ({size[0]}x{size[1]})")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Packing textures for Terrain3D:")

    # Grass
    pack_texture_set("grass",
        os.path.join(TEX_DIR, "grass_albedo.jpg"),
        os.path.join(TEX_DIR, "grass_normal.jpg"),
        os.path.join(TEX_DIR, "grass_rough.jpg"))

    # Leaf litter / meadow ground
    litter_alb = os.path.join(TEX_DIR, "leaf_litter_Color.jpg")
    if not os.path.exists(litter_alb):
        litter_alb = os.path.join(TEX_DIR, "forrest_ground_01_Color.jpg")
    litter_nrm = os.path.join(TEX_DIR, "leaf_litter_NormalGL.jpg")
    if not os.path.exists(litter_nrm):
        litter_nrm = os.path.join(TEX_DIR, "forrest_ground_01_NormalGL.jpg")
    litter_rgh = os.path.join(TEX_DIR, "leaf_litter_Roughness.jpg")
    if not os.path.exists(litter_rgh):
        litter_rgh = os.path.join(TEX_DIR, "forrest_ground_01_Roughness.jpg")
    if os.path.exists(litter_alb):
        pack_texture_set("meadow", litter_alb, litter_nrm, litter_rgh)

    # Rock (Manhattan schist)
    rock_alb = os.path.join(TEX_DIR, "schist_rock_Color.jpg")
    if not os.path.exists(rock_alb):
        rock_alb = os.path.join(TEX_DIR, "rock_wall_diff.jpg")
    rock_nrm = os.path.join(TEX_DIR, "schist_rock_NormalGL.jpg")
    if not os.path.exists(rock_nrm):
        rock_nrm = os.path.join(TEX_DIR, "rock_wall_nrm.jpg")
    rock_rgh = os.path.join(TEX_DIR, "schist_rock_Roughness.jpg")
    if not os.path.exists(rock_rgh):
        rock_rgh = os.path.join(TEX_DIR, "rock_wall_rgh.jpg")
    if os.path.exists(rock_alb):
        pack_texture_set("rock", rock_alb, rock_nrm, rock_rgh)

    # Dirt
    dirt_alb = os.path.join(TEX_DIR, "park_dirt_Color.jpg")
    dirt_nrm = os.path.join(TEX_DIR, "park_dirt_NormalGL.jpg")
    dirt_rgh = os.path.join(TEX_DIR, "park_dirt_Roughness.jpg")
    if os.path.exists(dirt_alb):
        pack_texture_set("dirt", dirt_alb, dirt_nrm, dirt_rgh)

    # Path textures (asphalt)
    path_alb = os.path.join(TEX_DIR, "pbr", "Asphalt_Color.jpg")
    if not os.path.exists(path_alb):
        path_alb = os.path.join(TEX_DIR, "asphalt_Color.jpg")
    path_nrm = os.path.join(TEX_DIR, "pbr", "Asphalt_NormalGL.jpg")
    if not os.path.exists(path_nrm):
        path_nrm = os.path.join(TEX_DIR, "asphalt_NormalGL.jpg")
    path_rgh = os.path.join(TEX_DIR, "pbr", "Asphalt_Roughness.jpg")
    if not os.path.exists(path_rgh):
        path_rgh = os.path.join(TEX_DIR, "asphalt_Roughness.jpg")
    if os.path.exists(path_alb):
        pack_texture_set("asphalt", path_alb, path_nrm, path_rgh)

    print("Done!")


if __name__ == "__main__":
    main()

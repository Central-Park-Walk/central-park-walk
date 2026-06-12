"""Shared PBR material creation utilities for model generation scripts.

Loads ambientCG textures from textures/pbr/ and creates Blender Principled BSDF
materials with Color, Normal, Roughness, and Metalness maps.

Usage:
    from pbr_utils import make_pbr_material
    iron = make_pbr_material("Iron", "cast_iron", tint=(0.04, 0.04, 0.035), tint_strength=0.7)
"""

import bpy
import os

_PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEX_DIR = os.path.join(_PROJ, "textures", "pbr")

# Map folder name -> (file prefix, has metalness)
_TEXTURE_MAP = {
    "cast_iron":      ("Metal027_1K-JPG", True),
    "weathered_wood":  ("Wood035_1K-JPG", False),
    "brownstone":      ("Bricks084_1K-JPG", False),
    "granite":         ("Granite002A_1K-JPG", False),
    "schist":          ("Rock058_1K-JPG", False),
    "brick":           ("Bricks097_1K-JPG", False),
    "concrete":        ("PavingStones150_1K-JPG", False),
    "bronze":          ("Metal017_1K-JPG", True),
}


def _load_tex(path):
    if os.path.isfile(path):
        return bpy.data.images.load(path)
    return None


def make_pbr_material(name, texture_set, tint=None, tint_strength=0.5,
                       roughness_fallback=0.65, metallic_fallback=0.0,
                       normal_strength=0.8, metallic_override=None):
    """Create a PBR material using ambientCG textures.

    Args:
        name: Material name
        texture_set: Folder name in textures/pbr/ (e.g., "cast_iron", "granite")
        tint: Optional (r, g, b) color to mix with the texture
        tint_strength: How much tint to apply (0=texture only, 1=tint only)
        roughness_fallback: Roughness if no texture found
        metallic_fallback: Metallic if no texture found
        normal_strength: Normal map intensity
        metallic_override: Scalar metallic that REPLACES the metalness map.
            Use for painted metal: full metalness renders near-black
            outdoors in Godot without reflection probes, and paint is a
            dielectric anyway.
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    tex_info = _TEXTURE_MAP.get(texture_set)
    if not tex_info:
        # Fallback: flat color
        if tint:
            bsdf.inputs['Base Color'].default_value = (*tint, 1.0)
        bsdf.inputs['Roughness'].default_value = roughness_fallback
        bsdf.inputs['Metallic'].default_value = metallic_fallback
        return mat

    prefix, has_metal = tex_info
    tex_dir = os.path.join(_TEX_DIR, texture_set)

    # Color
    color_img = _load_tex(os.path.join(tex_dir, f"{prefix}_Color.jpg"))
    if color_img and tint:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = color_img
        mix = nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = tint_strength
        mix.inputs['B'].default_value = (*tint, 1.0)
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    elif color_img:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = color_img
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    elif tint:
        bsdf.inputs['Base Color'].default_value = (*tint, 1.0)

    # Normal
    norm_img = _load_tex(os.path.join(tex_dir, f"{prefix}_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = normal_strength
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    # Roughness
    rough_img = _load_tex(os.path.join(tex_dir, f"{prefix}_Roughness.jpg"))
    if rough_img:
        rough_img.colorspace_settings.name = 'Non-Color'
        rough_tex = nodes.new('ShaderNodeTexImage')
        rough_tex.image = rough_img
        links.new(rough_tex.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = roughness_fallback

    # Metalness
    if metallic_override is not None:
        bsdf.inputs['Metallic'].default_value = metallic_override
    elif has_metal:
        metal_img = _load_tex(os.path.join(tex_dir, f"{prefix}_Metalness.jpg"))
        if metal_img:
            metal_img.colorspace_settings.name = 'Non-Color'
            metal_tex = nodes.new('ShaderNodeTexImage')
            metal_tex.image = metal_img
            links.new(metal_tex.outputs['Color'], bsdf.inputs['Metallic'])
        else:
            bsdf.inputs['Metallic'].default_value = metallic_fallback
    else:
        bsdf.inputs['Metallic'].default_value = metallic_fallback

    return mat

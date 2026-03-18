"""
Generate Central Park iron fence panel model for Central Park Walk.

The standard NYC Parks Department low iron fence used throughout Central Park:
- ~1.0m (40") tall
- Black painted cast iron
- Pointed pickets (spear-tip finials) at ~100mm (4") spacing
- Top rail with a slight outward curve
- Bottom rail sits ~50mm above ground

This model creates a single 2m fence panel (one repeating unit between posts).
The game tiles these along OSM fence polylines via the existing _build_fence_segments.

Upgraded: Blender 4.5 + ambientCG PBR textures, UV-mapped.
Generates: models/furniture/fence_panel.glb
Run: blender4 --background --python scripts/make_fence_panel.py
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX_DIR = os.path.join(PROJ, "textures", "pbr")
OUT_PATH = os.path.join(PROJ, "models", "furniture", "fence_panel.glb")

PANEL_WIDTH = 2.0
FENCE_HEIGHT = 1.0
POST_SIZE = 0.04
PICKET_SIZE = 0.012
PICKET_SPACING = 0.10
RAIL_HEIGHT = 0.025
RAIL_DEPTH = 0.015
FINIAL_HEIGHT = 0.035
BOTTOM_GAP = 0.05

# Scene cleanup
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)
for block in bpy.data.images:
    if block.users == 0:
        bpy.data.images.remove(block)

# ---------------------------------------------------------------------------
# PBR Material
# ---------------------------------------------------------------------------

def _load_tex(path):
    if os.path.isfile(path):
        return bpy.data.images.load(path)
    return None


def make_fence_iron_material():
    """Black painted cast iron PBR from ambientCG Metal027."""
    mat = bpy.data.materials.new(name="FenceIron")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    tex_dir = os.path.join(TEX_DIR, "cast_iron")
    color_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Color.jpg"))
    if color_img:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = color_img
        mix = nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = 0.75
        mix.inputs['B'].default_value = (0.05, 0.05, 0.06, 1.0)
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.06, 1.0)

    norm_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = 0.6
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    rough_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Roughness.jpg"))
    if rough_img:
        rough_img.colorspace_settings.name = 'Non-Color'
        rough_tex = nodes.new('ShaderNodeTexImage')
        rough_tex.image = rough_img
        links.new(rough_tex.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.65

    metal_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Metalness.jpg"))
    if metal_img:
        metal_img.colorspace_settings.name = 'Non-Color'
        metal_tex = nodes.new('ShaderNodeTexImage')
        metal_tex.image = metal_img
        links.new(metal_tex.outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = 0.85

    return mat


iron_mat = make_fence_iron_material()


# ---------------------------------------------------------------------------
# Geometry helpers with UVs
# ---------------------------------------------------------------------------

def make_box(bm, uv_layer, cx, cy, cz, sx, sy, sz):
    """Add a UV-mapped axis-aligned box to bmesh."""
    verts = []
    for dz in (-1, 1):
        for dy in (-1, 1):
            for dx in (-1, 1):
                verts.append(bm.verts.new((cx + dx*sx, cy + dy*sy, cz + dz*sz)))
    idx = [(0,1,3,2), (4,6,7,5), (0,4,5,1), (2,3,7,6), (0,2,6,4), (1,5,7,3)]
    for face_idx in idx:
        face = bm.faces.new([verts[i] for i in face_idx])
        # Box projection UVs
        for loop in face.loops:
            co = loop.vert.co
            # Project based on face normal direction
            loop[uv_layer].uv = (co.x * 2.0 + co.y * 2.0, co.z * 2.0)


def make_picket(bm, uv_layer, x, y):
    """One pointed picket with spear-tip finial, UV-mapped."""
    bottom_z = BOTTOM_GAP
    top_z = FENCE_HEIGHT - RAIL_HEIGHT
    hs = PICKET_SIZE * 0.5

    make_box(bm, uv_layer, x, y, (bottom_z + top_z) / 2, hs, hs, (top_z - bottom_z) / 2)

    # Spear-tip finial
    tip_base_z = top_z
    tip_top_z = top_z + FINIAL_HEIGHT
    v_base = [
        bm.verts.new((x - hs * 1.2, y - hs * 1.2, tip_base_z)),
        bm.verts.new((x + hs * 1.2, y - hs * 1.2, tip_base_z)),
        bm.verts.new((x + hs * 1.2, y + hs * 1.2, tip_base_z)),
        bm.verts.new((x - hs * 1.2, y + hs * 1.2, tip_base_z)),
    ]
    v_tip = bm.verts.new((x, y, tip_top_z))
    for i in range(4):
        j = (i + 1) % 4
        face = bm.faces.new([v_base[i], v_base[j], v_tip])
        for loop in face.loops:
            co = loop.vert.co
            loop[uv_layer].uv = (co.x * 5.0, co.z * 5.0)
    bm.faces.new(list(reversed(v_base)))


def make_post(bm, uv_layer, x, y):
    """Fence post with ball finial, UV-mapped."""
    hs = POST_SIZE * 0.5
    make_box(bm, uv_layer, x, y, FENCE_HEIGHT * 0.5, hs, hs, FENCE_HEIGHT * 0.5)

    # Ball finial — higher segment count for smoother sphere
    ball_r = POST_SIZE * 0.6
    ball_z = FENCE_HEIGHT + ball_r * 0.7
    n_ring = 8   # was 6
    n_slices = 7  # was 5
    rings = []
    for si in range(n_slices + 1):
        phi = math.pi * si / n_slices
        rr = ball_r * math.sin(phi)
        zz = ball_z + ball_r * math.cos(phi)
        ring = []
        for ri in range(n_ring):
            theta = 2 * math.pi * ri / n_ring
            ring.append(bm.verts.new((x + rr * math.cos(theta),
                                       y + rr * math.sin(theta),
                                       zz)))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for si in range(n_slices):
        v_lo = si / n_slices
        v_hi = (si + 1) / n_slices
        for ri in range(n_ring):
            ri2 = (ri + 1) % n_ring
            u_lo = ri / n_ring
            u_hi = (ri + 1) / n_ring
            face = bm.faces.new([rings[si][ri], rings[si][ri2],
                                  rings[si+1][ri2], rings[si+1][ri]])
            face.smooth = True
            for loop in face.loops:
                v_idx = loop.vert
                if v_idx == rings[si][ri]:
                    loop[uv_layer].uv = (u_lo, v_lo)
                elif v_idx == rings[si][ri2]:
                    loop[uv_layer].uv = (u_hi, v_lo)
                elif v_idx == rings[si+1][ri2]:
                    loop[uv_layer].uv = (u_hi, v_hi)
                elif v_idx == rings[si+1][ri]:
                    loop[uv_layer].uv = (u_lo, v_hi)


# ---------------------------------------------------------------------------
# Build the fence panel
# ---------------------------------------------------------------------------
bm = bmesh.new()
uv_layer = bm.loops.layers.uv.new("UVMap")

make_post(bm, uv_layer, -PANEL_WIDTH / 2, 0)
make_post(bm, uv_layer, PANEL_WIDTH / 2, 0)

# Rails
top_rail_z = FENCE_HEIGHT - RAIL_HEIGHT / 2
make_box(bm, uv_layer, 0, 0, top_rail_z, PANEL_WIDTH / 2, RAIL_DEPTH / 2, RAIL_HEIGHT / 2)
bot_rail_z = BOTTOM_GAP + RAIL_HEIGHT / 2
make_box(bm, uv_layer, 0, 0, bot_rail_z, PANEL_WIDTH / 2, RAIL_DEPTH / 2, RAIL_HEIGHT / 2)
mid_rail_z = BOTTOM_GAP + (FENCE_HEIGHT - BOTTOM_GAP) * 0.40
make_box(bm, uv_layer, 0, 0, mid_rail_z, PANEL_WIDTH / 2, RAIL_DEPTH / 2, RAIL_HEIGHT * 0.4)

# Pickets
half_w = PANEL_WIDTH / 2 - POST_SIZE
n_pickets = int(half_w * 2 / PICKET_SPACING)
for i in range(n_pickets):
    px = -half_w + (i + 0.5) * PICKET_SPACING
    if abs(px) > half_w - PICKET_SIZE:
        continue
    make_picket(bm, uv_layer, px, 0)

mesh = bpy.data.meshes.new("FencePanel")
bm.to_mesh(mesh)
bm.free()

obj = bpy.data.objects.new("FencePanel", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(iron_mat)

# Smooth shading on ball finials only
for poly in obj.data.polygons:
    center_z = sum(obj.data.vertices[vi].co.z for vi in poly.vertices) / len(poly.vertices)
    if center_z > FENCE_HEIGHT:
        poly.use_smooth = True

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

n_faces = len(obj.data.polygons)
n_verts = len(obj.data.vertices)
print(f"\nFence panel: {n_verts} verts, {n_faces} faces")
print(f"  Panel width: {PANEL_WIDTH}m, height: {FENCE_HEIGHT}m")
print(f"  ~{n_pickets} pickets at {PICKET_SPACING*1000:.0f}mm spacing")

# Export
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT_PATH,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_image_format='JPEG',
    export_image_quality=85,
)
sz_kb = os.path.getsize(OUT_PATH) / 1024
print(f"Exported to {OUT_PATH} ({sz_kb:.0f} KB)")

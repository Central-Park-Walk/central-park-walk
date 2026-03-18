"""Generate Central Park drinking fountain for Central Park Walk.

Classic NYC Parks cast-iron pedestal drinking fountain:
- Fluted cylindrical pedestal (~90cm tall, 15cm diameter)
- Basin bowl at top (~30cm diameter, shallow)
- Square base plate (25cm x 25cm)
- Small spout nub at top center
- Decorative ring at pedestal/basin junction

Upgraded: Blender 4.5 + ambientCG PBR cast iron, UV-mapped.
Exports to models/furniture/cp_drinking_fountain.glb
Run: blender4 --background --python scripts/make_drinking_fountain.py
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX_DIR = os.path.join(PROJ, "textures", "pbr")

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


def make_cast_iron_material():
    mat = bpy.data.materials.new(name="CastIron")
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
        mix.inputs['Factor'].default_value = 0.5
        mix.inputs['B'].default_value = (0.15, 0.17, 0.14, 1.0)
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.15, 0.17, 0.14, 1.0)

    norm_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = 0.9
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


iron_mat = make_cast_iron_material()

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------
BASE_W = 0.125       # base plate half-width
BASE_H = 0.03        # base plate height
PED_R = 0.075        # pedestal radius
PED_H = 0.90         # pedestal height
BASIN_R = 0.15       # basin radius
BASIN_H = 0.08       # basin depth
RIM_MAJOR_R = 0.14   # rim torus major radius
RIM_MINOR_R = 0.02   # rim torus minor radius
RING_R = 0.095       # decorative ring at pedestal top
RING_H = 0.04        # ring height
SPOUT_R = 0.015
SPOUT_H = 0.05
CIRC_SEGS = 20       # higher for smoother curves

objects = []

# ---------------------------------------------------------------------------
# Build components (Z-up)
# ---------------------------------------------------------------------------

# Base plate
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, BASE_H / 2))
base = bpy.context.active_object
base.name = "Base"
base.scale = (BASE_W, BASE_W, BASE_H / 2)
bpy.ops.object.transform_apply(location=True, scale=True)
base.data.materials.append(iron_mat)
objects.append(base)

# Fluted pedestal — alternating radii for fluting
bm = bmesh.new()
uv_layer = bm.loops.layers.uv.new("UVMap")
n_height = 16
flute_count = 10
circ = flute_count * 2
rings = []
for i in range(n_height):
    t = i / (n_height - 1)
    z = BASE_H + t * PED_H
    # Slight taper (wider at base)
    base_r = PED_R + (1 - t) * 0.008
    ring = []
    for j in range(circ):
        angle = 2 * math.pi * j / circ
        r = base_r if j % 2 == 0 else base_r * 0.88
        ring.append(bm.verts.new(Vector((math.cos(angle) * r, math.sin(angle) * r, z))))
    rings.append(ring)

bm.verts.ensure_lookup_table()
for i in range(len(rings) - 1):
    v_lo = i / (n_height - 1)
    v_hi = (i + 1) / (n_height - 1)
    for j in range(circ):
        j2 = (j + 1) % circ
        u_lo = j / circ
        u_hi = (j + 1) / circ
        face = bm.faces.new([rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]])
        face.smooth = True
        for loop in face.loops:
            v_idx = loop.vert
            if v_idx == rings[i][j]:
                loop[uv_layer].uv = (u_lo, v_lo)
            elif v_idx == rings[i][j2]:
                loop[uv_layer].uv = (u_hi, v_lo)
            elif v_idx == rings[i + 1][j2]:
                loop[uv_layer].uv = (u_hi, v_hi)
            elif v_idx == rings[i + 1][j]:
                loop[uv_layer].uv = (u_lo, v_hi)

mesh = bpy.data.meshes.new("Pedestal")
bm.to_mesh(mesh)
bm.free()
ped = bpy.data.objects.new("Pedestal", mesh)
bpy.context.collection.objects.link(ped)
ped.data.materials.append(iron_mat)
objects.append(ped)

# Decorative ring
ped_top_z = BASE_H + PED_H
bpy.ops.mesh.primitive_torus_add(
    major_radius=RING_R, minor_radius=0.015,
    major_segments=CIRC_SEGS, minor_segments=8,
    location=(0, 0, ped_top_z - 0.02)
)
ring_obj = bpy.context.active_object
ring_obj.name = "Ring"
ring_obj.data.materials.append(iron_mat)
objects.append(ring_obj)

# Basin bowl
basin_z = ped_top_z
bpy.ops.mesh.primitive_cylinder_add(
    radius=BASIN_R, depth=BASIN_H, vertices=CIRC_SEGS,
    location=(0, 0, basin_z + BASIN_H / 2)
)
basin = bpy.context.active_object
basin.name = "Basin"
basin.data.materials.append(iron_mat)
objects.append(basin)

# Rim
bpy.ops.mesh.primitive_torus_add(
    major_radius=RIM_MAJOR_R, minor_radius=RIM_MINOR_R,
    major_segments=CIRC_SEGS, minor_segments=10,
    location=(0, 0, basin_z + BASIN_H)
)
rim = bpy.context.active_object
rim.name = "Rim"
rim.data.materials.append(iron_mat)
objects.append(rim)

# Spout
bpy.ops.mesh.primitive_cylinder_add(
    radius=SPOUT_R, depth=SPOUT_H, vertices=10,
    location=(0, 0, basin_z + BASIN_H + SPOUT_H / 2)
)
spout = bpy.context.active_object
spout.name = "Spout"
spout.data.materials.append(iron_mat)
objects.append(spout)

# ---------------------------------------------------------------------------
# Join and export
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
fountain = bpy.context.active_object
fountain.name = "DrinkingFountain"

out_path = os.path.join(PROJ, "models", "furniture", "cp_drinking_fountain.glb")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_image_format='JPEG',
    export_image_quality=85,
)

verts = len(fountain.data.vertices)
faces = len(fountain.data.polygons)
sz_kb = os.path.getsize(out_path) / 1024
bb = [fountain.matrix_world @ Vector(c) for c in fountain.bound_box]
h = max(v.z for v in bb) - min(v.z for v in bb)
print(f"Exported Drinking Fountain to {out_path}")
print(f"  Height: {h:.2f}m ({h * 39.37:.1f}in)")
print(f"  Verts: {verts:,}, Faces: {faces:,}")
print(f"  File: {sz_kb:.0f} KB")

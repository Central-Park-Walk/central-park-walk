"""Generate a Central Park Conservancy recycling receptacle.

The actual trash cans in Central Park are the Landor/Landscape Forms aluminum
recycling system (2013). Cylindrical body with vertical slats inspired by the
1939 World's Fair bench, domed lid with circular aperture, cast aluminum base.
Triple powder-coat finish. ~30 gallon capacity.

NOT the old wire mesh basket — that was replaced throughout the park.

Dimensions: ~0.61m diameter, ~0.91m tall.
One material: 'Aluminum' (dark charcoal powder coat, PBR).
Exports to models/furniture/cp_trash_can.glb

Upgraded: Blender 4.5 + ambientCG PBR textures, UV-mapped.
Run: blender4 --background --python scripts/make_trash_can.py
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX_DIR = os.path.join(PROJ, "textures", "pbr")

# Clear scene
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


def make_aluminum_material():
    """Dark charcoal powder-coated aluminum with PBR from ambientCG Metal027."""
    mat = bpy.data.materials.new(name="Aluminum")
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
        mix.inputs['Factor'].default_value = 0.6
        mix.inputs['B'].default_value = (0.18, 0.19, 0.17, 1.0)  # charcoal
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.18, 0.19, 0.17, 1.0)

    norm_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = 0.5  # Subtle — powder coat is smooth
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    rough_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Roughness.jpg"))
    if rough_img:
        rough_img.colorspace_settings.name = 'Non-Color'
        rough_tex = nodes.new('ShaderNodeTexImage')
        rough_tex.image = rough_img
        # Blend toward smoother (powder coat is smoother than raw iron)
        mix_r = nodes.new('ShaderNodeMix')
        mix_r.data_type = 'FLOAT'
        mix_r.inputs['Factor'].default_value = 0.5
        mix_r.inputs['B'].default_value = 0.45
        links.new(rough_tex.outputs['Color'], mix_r.inputs['A'])
        links.new(mix_r.outputs['Result'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.55

    bsdf.inputs['Metallic'].default_value = 0.4
    return mat


alum_mat = make_aluminum_material()

# ---------------------------------------------------------------------------
# Dimensions (metres) — unchanged
# ---------------------------------------------------------------------------
CAN_R = 0.305
CAN_H = 0.70
BASE_H = 0.08
LID_H = 0.06
LID_DOME_H = 0.07
APERTURE_R = 0.15
SLAT_COUNT = 24
SLAT_W = 0.030
SLAT_T = 0.004
TOTAL_H = BASE_H + CAN_H + LID_H + LID_DOME_H

CIRC_SEGS = 24


# ---------------------------------------------------------------------------
# UV-mapped geometry helpers
# ---------------------------------------------------------------------------

def make_uv_cylinder(name, radius, depth, location, segments=CIRC_SEGS, mat=None):
    """Cylinder with basic cylindrical UV projection."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=segments, location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    # Auto UV unwrap
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cylinder_project(scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def make_base():
    objs = []
    objs.append(make_uv_cylinder("base_foot", CAN_R + 0.02, 0.02, (0, 0, 0.01), CIRC_SEGS, alum_mat))

    bpy.ops.mesh.primitive_cone_add(
        radius1=CAN_R + 0.01, radius2=CAN_R - 0.005,
        depth=BASE_H - 0.02, vertices=CIRC_SEGS,
        location=(0, 0, 0.02 + (BASE_H - 0.02) / 2)
    )
    base = bpy.context.active_object
    base.name = "base_body"
    base.data.materials.append(alum_mat)
    objs.append(base)

    return objs


def make_slat_body():
    objs = []

    for i in range(SLAT_COUNT):
        angle = 2 * math.pi * i / SLAT_COUNT
        twist = math.radians(5)

        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        n_segs = 8  # More segments for smoother twist (was 6)
        rings = []
        for j in range(n_segs + 1):
            t = j / n_segs
            z = BASE_H + t * CAN_H
            a = angle + t * twist
            cx = math.cos(a) * CAN_R
            cy = math.sin(a) * CAN_R
            tx_d = -math.sin(a)
            ty_d = math.cos(a)
            nx_d = math.cos(a)
            ny_d = math.sin(a)
            hw = SLAT_W / 2
            ht = SLAT_T / 2
            corners = [
                Vector((cx - tx_d * hw - nx_d * ht, cy - ty_d * hw - ny_d * ht, z)),
                Vector((cx + tx_d * hw - nx_d * ht, cy + ty_d * hw - ny_d * ht, z)),
                Vector((cx + tx_d * hw + nx_d * ht, cy + ty_d * hw + ny_d * ht, z)),
                Vector((cx - tx_d * hw + nx_d * ht, cy - ty_d * hw + ny_d * ht, z)),
            ]
            ring = [bm.verts.new(c) for c in corners]
            rings.append(ring)

        bm.verts.ensure_lookup_table()
        for j in range(n_segs):
            v_lo = j / n_segs
            v_hi = (j + 1) / n_segs
            for k in range(4):
                k2 = (k + 1) % 4
                u_lo = k / 4
                u_hi = (k + 1) / 4
                face = bm.faces.new([rings[j][k], rings[j][k2], rings[j+1][k2], rings[j+1][k]])
                face.smooth = True
                for loop in face.loops:
                    v_idx = loop.vert
                    if v_idx == rings[j][k]:
                        loop[uv_layer].uv = (u_lo, v_lo)
                    elif v_idx == rings[j][k2]:
                        loop[uv_layer].uv = (u_hi, v_lo)
                    elif v_idx == rings[j+1][k2]:
                        loop[uv_layer].uv = (u_hi, v_hi)
                    elif v_idx == rings[j+1][k]:
                        loop[uv_layer].uv = (u_lo, v_hi)

        # Caps
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])

        mesh = bpy.data.meshes.new(f"slat_{i}")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"slat_{i}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(alum_mat)
        objs.append(obj)

    # Inner liner
    objs.append(make_uv_cylinder("liner", CAN_R - 0.01, CAN_H, (0, 0, BASE_H + CAN_H / 2), CIRC_SEGS, alum_mat))

    # Reinforcement rings
    for z in [BASE_H, BASE_H + CAN_H]:
        bpy.ops.mesh.primitive_torus_add(
            major_radius=CAN_R, minor_radius=0.008,
            major_segments=CIRC_SEGS, minor_segments=8,
            location=(0, 0, z)
        )
        ring = bpy.context.active_object
        ring.name = f"ring_{z:.2f}"
        ring.data.materials.append(alum_mat)
        objs.append(ring)

    return objs


def make_lid():
    objs = []
    lid_z = BASE_H + CAN_H

    # Lid rim
    objs.append(make_uv_cylinder("lid_rim", CAN_R + 0.005, LID_H, (0, 0, lid_z + LID_H / 2), CIRC_SEGS, alum_mat))

    # Domed top with aperture
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    dome_z = lid_z + LID_H
    n_rings = 10  # More rings for smoother dome (was 8)
    n_segs = CIRC_SEGS

    rings = []
    for i in range(n_rings + 1):
        t = i / n_rings
        phi = t * math.pi / 2
        r = CAN_R * math.cos(phi)
        z = dome_z + LID_DOME_H * math.sin(phi)
        if r < APERTURE_R and i > 0:
            break
        ring = []
        for j in range(n_segs):
            theta = 2 * math.pi * j / n_segs
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            ring.append(bm.verts.new(Vector((x, y, z))))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        v_lo = i / max(len(rings) - 1, 1)
        v_hi = (i + 1) / max(len(rings) - 1, 1)
        for j in range(n_segs):
            j2 = (j + 1) % n_segs
            u_lo = j / n_segs
            u_hi = (j + 1) / n_segs
            face = bm.faces.new([rings[i][j], rings[i][j2], rings[i+1][j2], rings[i+1][j]])
            face.smooth = True
            for loop in face.loops:
                v_idx = loop.vert
                if v_idx == rings[i][j]:
                    loop[uv_layer].uv = (u_lo, v_lo)
                elif v_idx == rings[i][j2]:
                    loop[uv_layer].uv = (u_hi, v_lo)
                elif v_idx == rings[i+1][j2]:
                    loop[uv_layer].uv = (u_hi, v_hi)
                elif v_idx == rings[i+1][j]:
                    loop[uv_layer].uv = (u_lo, v_hi)

    mesh = bpy.data.meshes.new("lid_dome")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("lid_dome", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(alum_mat)
    objs.append(obj)

    # Aperture rim ring
    bpy.ops.mesh.primitive_torus_add(
        major_radius=APERTURE_R + 0.01, minor_radius=0.01,
        major_segments=20, minor_segments=8,
        location=(0, 0, dome_z + LID_DOME_H * 0.85)
    )
    ap_ring = bpy.context.active_object
    ap_ring.name = "aperture_ring"
    ap_ring.data.materials.append(alum_mat)
    objs.append(ap_ring)

    return objs


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
all_parts = []
all_parts.extend(make_base())
all_parts.extend(make_slat_body())
all_parts.extend(make_lid())

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

can = bpy.context.active_object
can.name = "CP_TrashCan"

bbox = [can.matrix_world @ Vector(corner) for corner in can.bound_box]
min_z = min(v.z for v in bbox)
can.location.z -= min_z
bpy.ops.object.transform_apply(location=True)

# Export
out_path = os.path.join(PROJ, "models", "furniture", "cp_trash_can.glb")
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

bbox2 = [can.matrix_world @ Vector(corner) for corner in can.bound_box]
height = max(v.z for v in bbox2) - min(v.z for v in bbox2)
sz_kb = os.path.getsize(out_path) / 1024
print(f"Exported CP trash receptacle to {out_path}")
print(f"  Height: {height:.2f}m ({height * 39.37:.1f}in)")
print(f"  Verts: {len(can.data.vertices):,}")
print(f"  Faces: {len(can.data.polygons):,}")
print(f"  File: {sz_kb:.0f} KB")

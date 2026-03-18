"""Generate a Central Park lamppost: Henry Bacon Type B pole + Kent Bloomer luminaire.

The Type B was designed 1910-1912 by Henry Bacon for NYC parks. The Kent Bloomer
luminaire (1982, with architect Gerald Allen) replaced the original electric lamp.
~1,800 identical units throughout Central Park.

Reference: NYC Street Design Manual, Forgotten NY, Elizabeth Barlow Rogers,
WikiCommons photos of actual Central Park lampposts.

Design: straight black iron pole with fluted lower section, decorative Beaux Arts
base, and the Bloomer luminaire — a glass globe encased in 4 curved metal ribs
with abstracted leaf ornament, topped by an acorn finial.

Total height: ~4.1m (13.5 ft). Two objects: 'CP_Lamppost' (iron) and 'CP_Lamppost_Globe' (glass).
Exports to models/furniture/cp_lamppost.glb

Upgraded: Blender 4.5 + ambientCG PBR textures, UV-mapped, higher-poly.
Run: blender4 --background --python scripts/make_lamppost.py
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector, Matrix

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX_DIR = os.path.join(PROJ, "textures", "pbr")

# ---------------------------------------------------------------------------
# Scene cleanup
# ---------------------------------------------------------------------------
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
# PBR Materials
# ---------------------------------------------------------------------------

def _load_tex(path):
    if os.path.isfile(path):
        return bpy.data.images.load(path)
    return None


def make_iron_material():
    """Cast iron PBR from ambientCG Metal027 — dark powder coat."""
    mat = bpy.data.materials.new(name="Iron")
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
        mix.inputs['Factor'].default_value = 0.7
        mix.inputs['B'].default_value = (0.04, 0.04, 0.035, 1.0)
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.04, 0.04, 0.035, 1.0)

    norm_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = 0.8
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    rough_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Roughness.jpg"))
    if rough_img:
        rough_img.colorspace_settings.name = 'Non-Color'
        rough_tex = nodes.new('ShaderNodeTexImage')
        rough_tex.image = rough_img
        links.new(rough_tex.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.7

    metal_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Metalness.jpg"))
    if metal_img:
        metal_img.colorspace_settings.name = 'Non-Color'
        metal_tex = nodes.new('ShaderNodeTexImage')
        metal_tex.image = metal_img
        links.new(metal_tex.outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = 0.6

    return mat


def make_globe_material():
    """Frosted glass globe material."""
    mat = bpy.data.materials.new(name="Globe")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    bsdf.inputs['Base Color'].default_value = (0.95, 0.88, 0.75, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.25
    bsdf.inputs['Alpha'].default_value = 0.8
    bsdf.inputs['Specular IOR Level'].default_value = 0.5

    mat.surface_render_method = 'DITHERED'

    return mat


iron_mat = make_iron_material()
globe_mat = make_globe_material()

# ---------------------------------------------------------------------------
# Dimensions (metres, matching real Type B) — unchanged from original
# ---------------------------------------------------------------------------
BASE_FOOT_W = 0.12
BASE_FOOT_H = 0.03
BASE_H = 0.30
BASE_R_BOT = 0.09
BASE_R_TOP = 0.055

SHAFT_R = 0.05
SHAFT_UPPER_R = 0.04
FLUTE_H = 1.60
PLAIN_H = 1.80
SHAFT_START = BASE_H
FLUTE_TOP = SHAFT_START + FLUTE_H
PLAIN_TOP = FLUTE_TOP + PLAIN_H

LUM_NECK_Z = PLAIN_TOP
LUM_GLOBE_R = 0.13
LUM_GLOBE_H = 0.28
LUM_RIB_COUNT = 4
LUM_FINIAL_R = 0.018
LUM_FINIAL_H = 0.04
LUM_CALYX_R = 0.07
LUM_TOTAL_H = LUM_GLOBE_H + 0.12

TOTAL_H = PLAIN_TOP + LUM_TOTAL_H

CIRC_SEGS = 16


# ---------------------------------------------------------------------------
# Geometry helpers — UV-mapped
# ---------------------------------------------------------------------------

def make_tube(name, points, radii, segments=CIRC_SEGS, mat=None):
    """Create a UV-mapped tube mesh following a path with varying radii."""
    if isinstance(radii, (int, float)):
        radii = [radii] * len(points)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    rings = []

    # Arc lengths for V coordinate
    total_len = 0.0
    arc_lengths = [0.0]
    for i in range(1, len(points)):
        total_len += (points[i] - points[i - 1]).length
        arc_lengths.append(total_len)

    for i, pt in enumerate(points):
        if i < len(points) - 1:
            direction = (points[i + 1] - pt).normalized()
        elif i > 0:
            direction = (pt - points[i - 1]).normalized()
        else:
            direction = Vector((0, 0, 1))
        if abs(direction.z) < 0.99:
            side = direction.cross(Vector((0, 0, 1))).normalized()
        else:
            side = direction.cross(Vector((1, 0, 0))).normalized()
        up = side.cross(direction).normalized()
        r = radii[i]
        ring = []
        for j in range(segments):
            angle = 2 * math.pi * j / segments
            offset = side * math.cos(angle) * r + up * math.sin(angle) * r
            ring.append(bm.verts.new(pt + offset))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        v_lo = arc_lengths[i] / max(total_len, 0.001)
        v_hi = arc_lengths[i + 1] / max(total_len, 0.001)
        for j in range(segments):
            j2 = (j + 1) % segments
            u_lo = j / segments
            u_hi = (j + 1) / segments
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

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------------------
# Components — same design, higher quality
# ---------------------------------------------------------------------------

def make_base():
    objs = []
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, BASE_FOOT_H / 2))
    foot = bpy.context.active_object
    foot.name = "base_foot"
    foot.scale = (BASE_FOOT_W, BASE_FOOT_W, BASE_FOOT_H / 2)
    bpy.ops.object.transform_apply(scale=True)
    foot.data.materials.append(iron_mat)
    objs.append(foot)

    n_steps = 14  # Smoother base taper (was 10)
    pts = []
    radii = []
    for i in range(n_steps):
        t = i / (n_steps - 1)
        z = BASE_FOOT_H + t * (BASE_H - BASE_FOOT_H)
        r = BASE_R_BOT + (BASE_R_TOP - BASE_R_BOT) * (t ** 0.4)
        pts.append(Vector((0, 0, z)))
        radii.append(r)
    objs.append(make_tube("base_body", pts, radii, CIRC_SEGS, iron_mat))
    return objs


def make_shaft():
    objs = []

    # Fluted lower section
    n_pts = 16  # More height segments (was 12)
    flute_segs = 10
    circ = flute_segs * 2

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    rings = []
    for i in range(n_pts):
        t = i / (n_pts - 1)
        z = SHAFT_START + t * FLUTE_H
        base_r = SHAFT_R - t * 0.005
        ring = []
        for j in range(circ):
            angle = 2 * math.pi * j / circ
            r = base_r if j % 2 == 0 else base_r * 0.88
            x = math.cos(angle) * r
            y = math.sin(angle) * r
            ring.append(bm.verts.new(Vector((x, y, z))))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        v_lo = i / (n_pts - 1)
        v_hi = (i + 1) / (n_pts - 1)
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

    mesh = bpy.data.meshes.new("shaft_fluted")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("shaft_fluted", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(iron_mat)
    objs.append(obj)

    # Transition collar
    bpy.ops.mesh.primitive_torus_add(
        major_radius=SHAFT_R + 0.005, minor_radius=0.008,
        major_segments=CIRC_SEGS, minor_segments=8,
        location=(0, 0, FLUTE_TOP)
    )
    trans = bpy.context.active_object
    trans.name = "shaft_collar"
    trans.data.materials.append(iron_mat)
    objs.append(trans)

    # Upper plain pipe
    n_pts = 10  # More segments (was 8)
    pts = []
    radii = []
    for i in range(n_pts):
        t = i / (n_pts - 1)
        z = FLUTE_TOP + t * PLAIN_H
        pts.append(Vector((0, 0, z)))
        radii.append(SHAFT_UPPER_R)
    objs.append(make_tube("shaft_plain", pts, radii, CIRC_SEGS, iron_mat))

    return objs


def make_number_plate():
    plate_z = SHAFT_START + FLUTE_H * 0.5
    plate_w = 0.06
    plate_h = 0.04
    plate_depth = 0.005
    offset = SHAFT_R + 0.005

    bpy.ops.mesh.primitive_cube_add(size=1, location=(offset + plate_depth / 2, 0, plate_z))
    plate = bpy.context.active_object
    plate.name = "number_plate"
    plate.scale = (plate_depth, plate_w / 2, plate_h / 2)
    bpy.ops.object.transform_apply(scale=True)
    plate.data.materials.append(iron_mat)
    return [plate]


def make_luminaire():
    objs = []
    globe_center_z = LUM_NECK_Z + 0.04 + LUM_GLOBE_H * 0.45

    # Glass globe
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=LUM_GLOBE_R, segments=24, ring_count=16,
        location=(0, 0, globe_center_z)
    )
    globe = bpy.context.active_object
    globe.name = "CP_Lamppost_Globe"
    globe.scale = (1.0, 1.0, LUM_GLOBE_H / (LUM_GLOBE_R * 2))
    bpy.ops.object.transform_apply(scale=True)
    globe.data.materials.append(globe_mat)

    # Four curved ribs
    rib_r = 0.008
    globe_bot_z = globe_center_z - LUM_GLOBE_H * 0.5
    globe_top_z = globe_center_z + LUM_GLOBE_H * 0.5

    for rib_i in range(LUM_RIB_COUNT):
        base_angle = 2 * math.pi * rib_i / LUM_RIB_COUNT
        pts = []
        n_rib_pts = 20  # Smoother ribs (was 16)
        for j in range(n_rib_pts):
            t = j / (n_rib_pts - 1)
            z = globe_bot_z - 0.01 + t * (LUM_GLOBE_H + 0.04)
            bulge = math.sin(t * math.pi) * (LUM_GLOBE_R + 0.015)
            twist = base_angle + t * 0.15
            x = math.cos(twist) * bulge
            y = math.sin(twist) * bulge
            pts.append(Vector((x, y, z)))
        objs.append(make_tube(f"rib_{rib_i}", pts, rib_r, 8, iron_mat))

        # Leaf ornaments (3 per rib)
        for leaf_i in range(3):
            lt = 0.25 + leaf_i * 0.25
            lz = globe_bot_z - 0.01 + lt * (LUM_GLOBE_H + 0.04)
            bulge = math.sin(lt * math.pi) * (LUM_GLOBE_R + 0.015)
            twist = base_angle + lt * 0.15
            lx = math.cos(twist) * bulge
            ly = math.sin(twist) * bulge
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=0.012, segments=8, ring_count=6,
                location=(lx, ly, lz)
            )
            leaf = bpy.context.active_object
            leaf.name = f"leaf_{rib_i}_{leaf_i}"
            leaf_angle = twist + math.pi / 2
            leaf.rotation_euler = (0, 0, leaf_angle)
            leaf.scale = (0.6, 1.2, 1.0)
            bpy.ops.object.transform_apply(rotation=True, scale=True)
            leaf.data.materials.append(iron_mat)
            objs.append(leaf)

    # Neck collar
    bpy.ops.mesh.primitive_torus_add(
        major_radius=SHAFT_UPPER_R + 0.02, minor_radius=0.01,
        major_segments=CIRC_SEGS, minor_segments=8,
        location=(0, 0, LUM_NECK_Z + 0.01)
    )
    neck = bpy.context.active_object
    neck.name = "lum_neck"
    neck.data.materials.append(iron_mat)
    objs.append(neck)

    # Top calyx
    bpy.ops.mesh.primitive_torus_add(
        major_radius=LUM_CALYX_R, minor_radius=0.012,
        major_segments=CIRC_SEGS, minor_segments=8,
        location=(0, 0, globe_top_z + 0.01)
    )
    calyx = bpy.context.active_object
    calyx.name = "lum_calyx"
    calyx.data.materials.append(iron_mat)
    objs.append(calyx)

    # Acorn finial
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=LUM_FINIAL_R, segments=12, ring_count=8,
        location=(0, 0, globe_top_z + 0.03)
    )
    acorn = bpy.context.active_object
    acorn.name = "finial_acorn"
    acorn.scale = (1.0, 1.0, LUM_FINIAL_H / (LUM_FINIAL_R * 2))
    bpy.ops.object.transform_apply(scale=True)
    acorn.data.materials.append(iron_mat)
    objs.append(acorn)

    # Acorn cap
    bpy.ops.mesh.primitive_cylinder_add(
        radius=LUM_FINIAL_R * 1.2, depth=0.01, vertices=12,
        location=(0, 0, globe_top_z + 0.03 + LUM_FINIAL_H * 0.3)
    )
    acap = bpy.context.active_object
    acap.name = "finial_cap"
    acap.data.materials.append(iron_mat)
    objs.append(acap)

    # Finial stem
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.006, depth=0.025, vertices=8,
        location=(0, 0, globe_top_z + 0.03 + LUM_FINIAL_H * 0.6)
    )
    fstem = bpy.context.active_object
    fstem.name = "finial_stem"
    fstem.data.materials.append(iron_mat)
    objs.append(fstem)

    return objs, globe


# ---------------------------------------------------------------------------
# Build the lamppost
# ---------------------------------------------------------------------------
iron_parts = []
iron_parts.extend(make_base())
iron_parts.extend(make_shaft())
iron_parts.extend(make_number_plate())
lum_iron, globe_obj = make_luminaire()
iron_parts.extend(lum_iron)

# Apply all transforms
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Join all iron parts
bpy.ops.object.select_all(action='DESELECT')
for obj in iron_parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = iron_parts[0]
bpy.ops.object.join()

lamp = bpy.context.active_object
lamp.name = "CP_Lamppost"

# Set origin so bottom at Z=0
bbox = [lamp.matrix_world @ Vector(corner) for corner in lamp.bound_box]
min_z = min(v.z for v in bbox)
lamp.location.z -= min_z
globe_obj.location.z -= min_z
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True)

# Export GLB
out_dir = os.path.join(PROJ, "models", "furniture")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "cp_lamppost.glb")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_image_format='JPEG',
    export_image_quality=85,
)

# Report
bbox2 = [lamp.matrix_world @ Vector(corner) for corner in lamp.bound_box]
height = max(v.z for v in bbox2) - min(v.z for v in bbox2)
iron_faces = len(lamp.data.polygons)
iron_verts = len(lamp.data.vertices)
globe_faces = len(globe_obj.data.polygons)
globe_verts = len(globe_obj.data.vertices)
sz_kb = os.path.getsize(out_path) / 1024
print(f"Exported Central Park Type B lamppost to {out_path}")
print(f"  Height: {height:.2f}m ({height * 3.281:.1f} ft)")
print(f"  Iron: {iron_verts:,} verts, {iron_faces:,} faces")
print(f"  Globe: {globe_verts:,} verts, {globe_faces:,} faces")
print(f"  File: {sz_kb:.0f} KB")
print(f"  Objects: CP_Lamppost (iron) + CP_Lamppost_Globe (glass)")

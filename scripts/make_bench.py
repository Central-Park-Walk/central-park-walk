"""Generate the 1939 World's Fair bench (Kenneth Lynch & Sons).

THE iconic Central Park bench. Art Deco + Victorian hybrid designed by Kenneth Lynch
in collaboration with Parks Commissioner Robert Moses. Debuted at the 1939 NY World's Fair.
~8,000 originally produced; the dominant bench type among Central Park's 10,000 benches.

Key features: circular hoop armrests with ornate scroll inserts, splayed legs,
9 horizontal wood slats (5 seat + 4 back), cross-brace stretcher bars.

Dimensions (6' model — most common in park):
  Length: 6' (1.83m)
  Height: 34" (0.86m)
  Depth:  27" (0.69m)

3 side frames for 6' bench (2 ends + 1 center divider).
Two materials: 'Iron' (PBR cast iron) and 'Wood' (PBR weathered wood).
Exports to models/furniture/cp_bench.glb

Upgraded: Blender 4.5 + ambientCG PBR textures, higher-poly tubes, UV-mapped, beveled slats.
Run: blender4 --background --python scripts/make_bench.py
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
# PBR Materials — ambientCG textures
# ---------------------------------------------------------------------------

def _load_tex(path):
    """Load an image texture, return bpy.types.Image or None."""
    if os.path.isfile(path):
        return bpy.data.images.load(path)
    return None


def make_iron_material():
    """Cast iron with PBR textures from ambientCG Metal027."""
    mat = bpy.data.materials.new(name="Iron")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # Base color: tint the texture toward black powder coat
    tex_dir = os.path.join(TEX_DIR, "cast_iron")
    color_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Color.jpg"))
    if color_img:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = color_img
        # Darken to match powder-coat black (mix with dark color)
        mix = nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = 0.7  # 70% dark tint
        mix.inputs['B'].default_value = (0.04, 0.04, 0.035, 1.0)  # powder coat black
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.04, 0.04, 0.035, 1.0)

    # Normal map
    norm_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = 0.8
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    # Roughness map
    rough_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Roughness.jpg"))
    if rough_img:
        rough_img.colorspace_settings.name = 'Non-Color'
        rough_tex = nodes.new('ShaderNodeTexImage')
        rough_tex.image = rough_img
        links.new(rough_tex.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.65

    # Metalness
    metal_img = _load_tex(os.path.join(tex_dir, "Metal027_1K-JPG_Metalness.jpg"))
    if metal_img:
        metal_img.colorspace_settings.name = 'Non-Color'
        metal_tex = nodes.new('ShaderNodeTexImage')
        metal_tex.image = metal_img
        links.new(metal_tex.outputs['Color'], bsdf.inputs['Metallic'])
    else:
        bsdf.inputs['Metallic'].default_value = 0.6

    return mat


def make_wood_material():
    """Weathered wood with PBR textures from ambientCG Wood035."""
    mat = bpy.data.materials.new(name="Wood")
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    tex_dir = os.path.join(TEX_DIR, "weathered_wood")
    color_img = _load_tex(os.path.join(tex_dir, "Wood035_1K-JPG_Color.jpg"))
    if color_img:
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = color_img
        # Warm tint toward Cumaru/Ipe brown
        mix = nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.inputs['Factor'].default_value = 0.35
        mix.inputs['B'].default_value = (0.45, 0.30, 0.18, 1.0)
        links.new(tex_node.outputs['Color'], mix.inputs['A'])
        links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.45, 0.30, 0.18, 1.0)

    norm_img = _load_tex(os.path.join(tex_dir, "Wood035_1K-JPG_NormalGL.jpg"))
    if norm_img:
        norm_img.colorspace_settings.name = 'Non-Color'
        norm_tex = nodes.new('ShaderNodeTexImage')
        norm_tex.image = norm_img
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.inputs['Strength'].default_value = 1.0
        links.new(norm_tex.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    rough_img = _load_tex(os.path.join(tex_dir, "Wood035_1K-JPG_Roughness.jpg"))
    if rough_img:
        rough_img.colorspace_settings.name = 'Non-Color'
        rough_tex = nodes.new('ShaderNodeTexImage')
        rough_tex.image = rough_img
        links.new(rough_tex.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.75

    bsdf.inputs['Metallic'].default_value = 0.0

    return mat


iron_mat = make_iron_material()
wood_mat = make_wood_material()

# ---------------------------------------------------------------------------
# Dimensions (metres) — identical to original
# ---------------------------------------------------------------------------
BENCH_LEN = 1.83
BENCH_H = 0.86
BENCH_DEPTH = 0.69
SEAT_H = 0.44
SEAT_DEPTH = 0.44

IRON_R = 0.019
HOOP_R = 0.15
CIRC_SEGS = 12       # Upgraded from 8 for smoother tubes

SLAT_W = 0.089
SLAT_T = 0.025
SLAT_GAP = 0.013

BACK_ANGLE = math.radians(15)
FRONT_SPLAY = math.radians(18)
REAR_SPLAY = math.radians(12)
STRETCHER_H = 0.15
FOOT_R = 0.038
FOOT_H = 0.012

BOLT_R = 0.006       # Bolt head radius (~12mm diameter)
BOLT_H = 0.004       # Bolt head height


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def make_tube(name, points, radii, segments=CIRC_SEGS, mat=None, cap_ends=False):
    """Create a tube mesh following a path with varying radii. UV-mapped."""
    if isinstance(radii, (int, float)):
        radii = [radii] * len(points)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    rings = []
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

    # Side faces with UVs
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

    if cap_ends and len(rings) >= 2:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def make_slat(name, length, width, thickness, location, rotation_euler=None, mat=None):
    """Create a wood slat with beveled edges and proper UVs."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Create a box with beveled long edges
    hw, hd, ht = length / 2, width / 2, thickness / 2
    bevel = min(thickness * 0.15, 0.003)  # Subtle edge bevel

    # 8 corners of beveled box (bevel on Z edges only for simplicity)
    verts = []
    # Bottom face (4 corners)
    verts.append(bm.verts.new((-hw, -hd, -ht + bevel)))
    verts.append(bm.verts.new((hw, -hd, -ht + bevel)))
    verts.append(bm.verts.new((hw, hd, -ht + bevel)))
    verts.append(bm.verts.new((-hw, hd, -ht + bevel)))
    # Bevel strip bottom
    verts.append(bm.verts.new((-hw, -hd + bevel, -ht)))
    verts.append(bm.verts.new((hw, -hd + bevel, -ht)))
    verts.append(bm.verts.new((hw, hd - bevel, -ht)))
    verts.append(bm.verts.new((-hw, hd - bevel, -ht)))
    # Bevel strip top
    verts.append(bm.verts.new((-hw, -hd + bevel, ht)))
    verts.append(bm.verts.new((hw, -hd + bevel, ht)))
    verts.append(bm.verts.new((hw, hd - bevel, ht)))
    verts.append(bm.verts.new((-hw, hd - bevel, ht)))
    # Top face (4 corners)
    verts.append(bm.verts.new((-hw, -hd, ht - bevel)))
    verts.append(bm.verts.new((hw, -hd, ht - bevel)))
    verts.append(bm.verts.new((hw, hd, ht - bevel)))
    verts.append(bm.verts.new((-hw, hd, ht - bevel)))

    # Faces — front, back, top, bottom, bevel strips, ends
    def quad(a, b, c, d):
        f = bm.faces.new([verts[a], verts[b], verts[c], verts[d]])
        # Simple box projection UVs
        for loop in f.loops:
            co = loop.vert.co
            loop[uv_layer].uv = (co.x / length + 0.5, co.y / width + 0.5)
        return f

    # Front side (Y = -hd region)
    quad(4, 5, 1, 0)    # lower bevel
    quad(0, 1, 13, 12)   # main front face
    quad(12, 13, 9, 8)   # upper bevel

    # Back side (Y = +hd region)
    quad(3, 2, 6, 7)     # lower bevel
    quad(15, 14, 2, 3)   # main back face
    quad(11, 10, 14, 15)  # upper bevel

    # Bottom (Z = -ht)
    quad(7, 6, 5, 4)

    # Top (Z = +ht)
    quad(8, 9, 10, 11)

    # Left end (X = -hw)
    f = bm.faces.new([verts[0], verts[4], verts[8], verts[12], verts[15], verts[11], verts[7], verts[3]])
    for loop in f.loops:
        co = loop.vert.co
        loop[uv_layer].uv = (co.y / width + 0.5, co.z / thickness + 0.5)

    # Right end (X = +hw)
    f = bm.faces.new([verts[1], verts[2], verts[14], verts[13], verts[9], verts[5], verts[6], verts[10]])
    for loop in f.loops:
        co = loop.vert.co
        loop[uv_layer].uv = (co.y / width + 0.5, co.z / thickness + 0.5)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    if rotation_euler:
        obj.rotation_euler = rotation_euler
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def make_bolt(location, mat=None):
    """Small hex bolt head detail at slat-frame connection points."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=BOLT_R, depth=BOLT_H, vertices=6,
        location=location
    )
    bolt = bpy.context.active_object
    bolt.name = "bolt"
    if mat:
        bolt.data.materials.append(mat)
    return bolt


# ---------------------------------------------------------------------------
# Bench components — same design as original, higher quality
# ---------------------------------------------------------------------------

def make_hoop_armrest(x_pos):
    hoop_cy = SEAT_DEPTH * 0.42
    hoop_cz = SEAT_H + 0.06
    n_hoop_pts = 32  # Smoother hoop circle (was 24)
    pts = []
    for i in range(n_hoop_pts + 1):
        angle = 2 * math.pi * i / n_hoop_pts
        py = hoop_cy + HOOP_R * math.cos(angle)
        pz = hoop_cz + HOOP_R * math.sin(angle)
        pts.append(Vector((x_pos, py, pz)))
    hoop = make_tube("hoop", pts, IRON_R, CIRC_SEGS, iron_mat)
    return [hoop], (x_pos, hoop_cy, hoop_cz)


def make_scroll_insert(x_pos, hoop_center):
    _, cy, cz = hoop_center
    objs = []
    scroll_r = IRON_R * 0.70

    # Central vertical bar
    bar_bot_z = cz - HOOP_R * 0.75
    bar_top_z = cz + HOOP_R * 0.50
    pts = [Vector((x_pos, cy, bar_bot_z)), Vector((x_pos, cy, bar_top_z))]
    objs.append(make_tube("scroll_vert", pts, scroll_r, CIRC_SEGS, iron_mat))

    # Two S-curves with volutes
    for side in [-1, 1]:
        n_pts = 16  # More points for smoother S-curve (was 12)
        s_pts = []
        for i in range(n_pts):
            t = i / (n_pts - 1)
            sz = cz - HOOP_R * 0.30 + t * HOOP_R * 1.10
            sy = cy + side * HOOP_R * 0.50 * math.sin(t * math.pi * 1.5) * (0.4 + 0.6 * t)
            s_pts.append(Vector((x_pos, sy, sz)))
        objs.append(make_tube(f"scroll_s_{side}", s_pts, scroll_r, 8, iron_mat))

        # Top volute spiral
        vol_cy = s_pts[-1].y
        vol_cz = s_pts[-1].z
        n_vol = 12  # Smoother spiral (was 8)
        vol_r_start = HOOP_R * 0.10
        vol_pts = []
        for i in range(n_vol):
            t = i / (n_vol - 1)
            angle = t * math.pi * 1.5
            r = vol_r_start * (1 - t * 0.7)
            vy = vol_cy + side * r * math.cos(angle)
            vz = vol_cz + r * math.sin(angle)
            vol_pts.append(Vector((x_pos, vy, vz)))
        objs.append(make_tube(f"scroll_vol_top_{side}", vol_pts, scroll_r * 0.8, 8, iron_mat))

        # Bottom volute
        low_cy = cy + side * HOOP_R * 0.25
        low_cz = cz - HOOP_R * 0.55
        vol_pts2 = []
        for i in range(n_vol):
            t = i / (n_vol - 1)
            angle = t * math.pi * 1.3 + math.pi
            r = vol_r_start * 0.7 * (1 - t * 0.7)
            vy = low_cy + side * r * math.cos(angle)
            vz = low_cz + r * math.sin(angle)
            vol_pts2.append(Vector((x_pos, vy, vz)))
        objs.append(make_tube(f"scroll_vol_bot_{side}", vol_pts2, scroll_r * 0.8, 8, iron_mat))

    return objs


def make_end_frame(x_pos, is_end=True):
    objs = []
    hoop_cy = SEAT_DEPTH * 0.42
    hoop_cz = SEAT_H + 0.06

    if is_end:
        hoop_objs, hoop_center = make_hoop_armrest(x_pos)
        objs.extend(hoop_objs)
        objs.extend(make_scroll_insert(x_pos, hoop_center))

    # Front leg
    front_top_y = 0.04
    front_top_z = SEAT_H - 0.02
    front_bot_y = front_top_y - math.sin(FRONT_SPLAY) * front_top_z
    front_bot_z = 0.0

    n_leg = 10  # More segments for smoother leg curves (was 8)
    front_pts = []
    for i in range(n_leg):
        t = i / (n_leg - 1)
        curve = math.sin(t * math.pi) * 0.015
        py = front_bot_y + t * (front_top_y - front_bot_y) - curve
        pz = front_bot_z + t * (front_top_z - front_bot_z)
        front_pts.append(Vector((x_pos, py, pz)))
    objs.append(make_tube("front_leg", front_pts, IRON_R, CIRC_SEGS, iron_mat))

    # Rear leg
    rear_top_y = SEAT_DEPTH - 0.04
    rear_top_z = SEAT_H - 0.02
    rear_bot_y = rear_top_y + math.sin(REAR_SPLAY) * rear_top_z

    rear_pts = []
    for i in range(n_leg):
        t = i / (n_leg - 1)
        curve = math.sin(t * math.pi) * 0.015
        py = rear_bot_y + t * (rear_top_y - rear_bot_y) + curve
        pz = t * rear_top_z
        rear_pts.append(Vector((x_pos, py, pz)))
    objs.append(make_tube("rear_leg", rear_pts, IRON_R, CIRC_SEGS, iron_mat))

    # Back upright
    back_bot_y = rear_top_y
    back_bot_z = rear_top_z
    back_height = BENCH_H - SEAT_H + 0.02
    back_top_y = back_bot_y + math.sin(BACK_ANGLE) * back_height
    back_top_z = back_bot_z + math.cos(BACK_ANGLE) * back_height
    back_pts = [
        Vector((x_pos, back_bot_y, back_bot_z)),
        Vector((x_pos, back_top_y, back_top_z))
    ]
    objs.append(make_tube("back_upright", back_pts, IRON_R, CIRC_SEGS, iron_mat))

    # Cross-brace stretcher
    front_stretch_y = front_bot_y + (front_top_y - front_bot_y) * (STRETCHER_H / front_top_z)
    rear_stretch_y = rear_bot_y + (rear_top_y - rear_bot_y) * (STRETCHER_H / rear_top_z)
    stretch_pts = [
        Vector((x_pos, front_stretch_y, STRETCHER_H)),
        Vector((x_pos, rear_stretch_y, STRETCHER_H))
    ]
    objs.append(make_tube("stretcher", stretch_pts, IRON_R * 0.85, CIRC_SEGS, iron_mat))

    # Foot pads
    for foot_y in [front_bot_y, rear_bot_y]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=FOOT_R, depth=FOOT_H, vertices=CIRC_SEGS,
            location=(x_pos, foot_y, FOOT_H / 2)
        )
        pad = bpy.context.active_object
        pad.name = "foot_pad"
        pad.data.materials.append(iron_mat)
        objs.append(pad)

    return objs


def make_seat_slats():
    objs = []
    slat_len = BENCH_LEN - 0.06
    n_slats = 5
    total_slat_width = n_slats * SLAT_W + (n_slats - 1) * SLAT_GAP
    start_y = (SEAT_DEPTH - total_slat_width) / 2 + SLAT_W / 2
    seat_tilt = math.radians(5)

    for i in range(n_slats):
        y = start_y + i * (SLAT_W + SLAT_GAP)
        z_offset = (y - SEAT_DEPTH / 2) * math.sin(seat_tilt)
        loc = (0, y, SEAT_H + SLAT_T / 2 - z_offset)
        slat = make_slat(
            f"seat_slat_{i}", slat_len, SLAT_W, SLAT_T,
            loc, rotation_euler=(seat_tilt, 0, 0), mat=wood_mat
        )
        objs.append(slat)

    return objs


def make_back_slats():
    objs = []
    slat_len = BENCH_LEN - 0.06
    n_slats = 4
    back_start_z = SEAT_H + 0.04
    back_end_z = BENCH_H - 0.03
    back_base_y = SEAT_DEPTH - 0.04

    for i in range(n_slats):
        frac = (i + 0.5) / n_slats
        z = back_start_z + frac * (back_end_z - back_start_z)
        height_above_seat = z - SEAT_H
        y = back_base_y + math.sin(BACK_ANGLE) * height_above_seat
        loc = (0, y, z)
        slat = make_slat(
            f"back_slat_{i}", slat_len, SLAT_W, SLAT_T,
            loc, rotation_euler=(BACK_ANGLE, 0, 0), mat=wood_mat
        )
        objs.append(slat)

    return objs


def make_longitudinal_rails():
    objs = []
    rail_len = BENCH_LEN - 0.04
    rail_r = IRON_R * 0.80
    pts_front = [
        Vector((-rail_len / 2, 0.06, SEAT_H - 0.02)),
        Vector((rail_len / 2, 0.06, SEAT_H - 0.02))
    ]
    objs.append(make_tube("rail_seat_front", pts_front, rail_r, CIRC_SEGS, iron_mat))

    pts_rear = [
        Vector((-rail_len / 2, SEAT_DEPTH - 0.06, SEAT_H - 0.02)),
        Vector((rail_len / 2, SEAT_DEPTH - 0.06, SEAT_H - 0.02))
    ]
    objs.append(make_tube("rail_seat_rear", pts_rear, rail_r, CIRC_SEGS, iron_mat))

    back_top_y = SEAT_DEPTH - 0.04 + math.sin(BACK_ANGLE) * (BENCH_H - SEAT_H - 0.02)
    pts_back = [
        Vector((-rail_len / 2, back_top_y + 0.02, BENCH_H - 0.01)),
        Vector((rail_len / 2, back_top_y + 0.02, BENCH_H - 0.01))
    ]
    objs.append(make_tube("rail_back_top", pts_back, rail_r, CIRC_SEGS, iron_mat))

    mid_z = (SEAT_H + BENCH_H) / 2
    mid_y = SEAT_DEPTH - 0.04 + math.sin(BACK_ANGLE) * (mid_z - SEAT_H)
    pts_mid = [
        Vector((-rail_len / 2, mid_y + 0.02, mid_z)),
        Vector((rail_len / 2, mid_y + 0.02, mid_z))
    ]
    objs.append(make_tube("rail_back_mid", pts_mid, rail_r, CIRC_SEGS, iron_mat))

    return objs


def add_bolt_details():
    """Add small hex bolt heads where slats meet the side frames."""
    objs = []
    half_len = BENCH_LEN / 2
    frame_xs = [-half_len + 0.03, 0.0, half_len - 0.03]

    # Seat slat bolts
    n_seat = 5
    total_sw = n_seat * SLAT_W + (n_seat - 1) * SLAT_GAP
    start_y = (SEAT_DEPTH - total_sw) / 2 + SLAT_W / 2
    seat_tilt = math.radians(5)

    for fx in frame_xs:
        for i in range(n_seat):
            y = start_y + i * (SLAT_W + SLAT_GAP)
            z_offset = (y - SEAT_DEPTH / 2) * math.sin(seat_tilt)
            bz = SEAT_H + SLAT_T + 0.001 - z_offset
            objs.append(make_bolt((fx, y, bz), iron_mat))

    # Back slat bolts
    n_back = 4
    back_start_z = SEAT_H + 0.04
    back_end_z = BENCH_H - 0.03
    back_base_y = SEAT_DEPTH - 0.04

    for fx in frame_xs:
        for i in range(n_back):
            frac = (i + 0.5) / n_back
            z = back_start_z + frac * (back_end_z - back_start_z)
            h_above = z - SEAT_H
            y = back_base_y + math.sin(BACK_ANGLE) * h_above
            # Bolt on the front face of back slats
            bolt_y = y - SLAT_T * 0.5 * math.cos(BACK_ANGLE) - 0.001
            bolt_z = z - SLAT_T * 0.5 * math.sin(BACK_ANGLE)
            bolt = make_bolt((fx, bolt_y, bolt_z), iron_mat)
            bolt.rotation_euler = (BACK_ANGLE, 0, 0)
            objs.append(bolt)

    return objs


# ---------------------------------------------------------------------------
# Build the bench
# ---------------------------------------------------------------------------
all_parts = []

half_len = BENCH_LEN / 2
frame_positions = [
    (-half_len + 0.03, True),
    (0.0, False),
    (half_len - 0.03, True),
]

for x_pos, is_end in frame_positions:
    all_parts.extend(make_end_frame(x_pos, is_end=is_end))

all_parts.extend(make_seat_slats())
all_parts.extend(make_back_slats())
all_parts.extend(make_longitudinal_rails())
all_parts.extend(add_bolt_details())

# Apply transforms
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Join all parts
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

bench = bpy.context.active_object
bench.name = "ParkFurn_Bench_CP"

# Set origin so bottom is at Z=0
bbox = [bench.matrix_world @ Vector(corner) for corner in bench.bound_box]
min_z = min(v.z for v in bbox)
bench.location.z -= min_z
bpy.ops.object.transform_apply(location=True)

# Export GLB
out_dir = os.path.join(PROJ, "models", "furniture")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "cp_bench.glb")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_image_format='JPEG',  # Compress textures in GLB
    export_image_quality=85,
)

# Report
bbox2 = [bench.matrix_world @ Vector(corner) for corner in bench.bound_box]
dims = Vector((
    max(v.x for v in bbox2) - min(v.x for v in bbox2),
    max(v.y for v in bbox2) - min(v.y for v in bbox2),
    max(v.z for v in bbox2) - min(v.z for v in bbox2),
))
faces = len(bench.data.polygons)
verts = len(bench.data.vertices)
mats = len(bench.data.materials)
sz_kb = os.path.getsize(out_path) / 1024
print(f"Exported 1939 World's Fair bench to {out_path}")
print(f"  Length: {dims.x:.2f}m ({dims.x * 39.37:.1f}in)")
print(f"  Depth:  {dims.y:.2f}m ({dims.y * 39.37:.1f}in)")
print(f"  Height: {dims.z:.2f}m ({dims.z * 39.37:.1f}in)")
print(f"  Verts:  {verts:,}")
print(f"  Faces:  {faces:,}")
print(f"  Materials: {mats}")
print(f"  File:   {sz_kb:.0f} KB")

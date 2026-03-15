"""Bethesda Terrace — built directly from LiDAR heightmap data.

The model replicates the EXACT terrain shape inside the hole polygon,
sampled from heightmap.bin. The surface mesh matches the terrain at
the edges seamlessly. Below the surface, arcade vault geometry provides
the walkable tunnel interior.

This is the AAA approach: terrain has a hole, model fills it with
complete geometry that matches the terrain edges precisely.

Exports to models/furniture/cp_bethesda_terrace.glb
"""

import bpy
import bmesh
import math
import os
import struct
import numpy as np

# ── Clear scene ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ── Materials ──
def make_mat(name, color, roughness=0.80):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    return m

sandstone  = make_mat("Sandstone",  (0.72, 0.65, 0.52), 0.85)
vault_tile = make_mat("VaultTile",  (0.82, 0.72, 0.55), 0.55)
stair_mat  = make_mat("StairStone", (0.60, 0.56, 0.48), 0.82)
brownstone = make_mat("Brownstone", (0.42, 0.32, 0.24), 0.80)

# ══════════════════════════════════════════════════════════════════
# LOAD HEIGHTMAP — DEM bare earth for edge matching
# Structure dimensions from LiDAR DSM measurements (session 34):
#   Upper terrace: 23.6m    Lower terrace: 17.6m    Drop: 6.0m
#   West wall peak: (-484, 997)    East wall peak: (-462, 1004)
# ══════════════════════════════════════════════════════════════════
HM_PATH = "/home/chris/central-park-walk/heightmap.bin"
with open(HM_PATH, 'rb') as f:
    hm_w = struct.unpack('<I', f.read(4))[0]
    hm_d = struct.unpack('<I', f.read(4))[0]
    hm_ws = struct.unpack('<f', f.read(4))[0]
    _ = f.read(4)
    hm_data = np.frombuffer(f.read(hm_w * hm_d * 4), dtype=np.float32).reshape(hm_d, hm_w)

hm_half = hm_ws / 2.0
print(f"Heightmap: {hm_w}x{hm_d}, ws={hm_ws}")

def terrain_h(wx, wz):
    """Sample heightmap (DEM) at world coordinates."""
    xi = (wx + hm_half) / hm_ws * (hm_w - 1)
    zi = (wz + hm_half) / hm_ws * (hm_d - 1)
    xi0 = max(0, min(int(xi), hm_w - 2))
    zi0 = max(0, min(int(zi), hm_d - 2))
    fx = xi - xi0
    fz = zi - zi0
    h00 = float(hm_data[zi0, xi0])
    h10 = float(hm_data[zi0, xi0+1])
    h01 = float(hm_data[zi0+1, xi0])
    h11 = float(hm_data[zi0+1, xi0+1])
    return h00*(1-fx)*(1-fz) + h10*fx*(1-fz) + h01*(1-fx)*fz + h11*fx*fz

def terrain_h(wx, wz):
    """Sample heightmap at world coordinates."""
    xi = (wx + hm_half) / hm_ws * (hm_w - 1)
    zi = (wz + hm_half) / hm_ws * (hm_d - 1)
    xi0 = max(0, min(int(xi), hm_w - 2))
    zi0 = max(0, min(int(zi), hm_d - 2))
    fx = xi - xi0
    fz = zi - zi0
    h00 = float(hm_data[zi0, xi0])
    h10 = float(hm_data[zi0, xi0 + 1])
    h01 = float(hm_data[zi0 + 1, xi0])
    h11 = float(hm_data[zi0 + 1, xi0 + 1])
    return h00 * (1-fx)*(1-fz) + h10 * fx*(1-fz) + h01 * (1-fx)*fz + h11 * fx*fz

# ══════════════════════════════════════════════════════════════════
# MODEL PLACEMENT — verified from wall peak positions
# ══════════════════════════════════════════════════════════════════
# Model origin in world: (-473, 17.6, 1000.5)
# rotation_y = 2.834 (PI - 0.308)
MODEL_X = -473.0
MODEL_Z = 1000.5
# Model origin matches GDScript placement: ty = terrain_y(tx, 1010) - 6.0
# Sample terrain at the upper terrace (outside any carve zone) and subtract drop
upper_terrace_h = terrain_h(MODEL_X, 1010.0)
MODEL_Y = upper_terrace_h - 6.0  # arcade floor = upper level - measured drop
print(f"Upper terrace DEM: {upper_terrace_h:.1f}m → MODEL_Y: {MODEL_Y:.1f}m")
ROTATION = 2.834
ct = math.cos(ROTATION)
st = math.sin(ROTATION)

print(f"Model origin: ({MODEL_X}, {MODEL_Y:.1f}, {MODEL_Z})")

def world_to_blender(wx, wz):
    """Convert world XZ to Blender XY (accounting for rotation)."""
    dx = wx - MODEL_X
    dz = wz - MODEL_Z
    # Inverse of the Godot rotation transform
    # bx = ct*dx - st*dz (but also need GLTF→Blender: bx=gx, by=-gz)
    gx = ct * dx - st * dz
    gz = st * dx + ct * dz  # note: this gives GLTF Z, not world Z
    # GLTF to Blender: bx = gx, by = -gz
    bx = gx
    by = -gz
    return bx, by

def blender_to_world(bx, by):
    """Convert Blender XY to world XZ."""
    gx = bx
    gz = -by
    wx = MODEL_X + gx * ct + gz * st
    wz = MODEL_Z + (-gx * st + gz * ct)
    return wx, wz

# ══════════════════════════════════════════════════════════════════
# GENERATE SURFACE MESH FROM HEIGHTMAP
# ══════════════════════════════════════════════════════════════════
# Sample a grid of points inside the terrace footprint
# Grid spacing ~1m in world coordinates
GRID_STEP = 1.0  # meters

# Bounding box in world coordinates (from hole polygon)
WX_MIN, WX_MAX = -500, -450
WZ_MIN, WZ_MAX = 994, 1021

# Generate grid in world coords, convert to Blender, sample heights
print("Generating surface mesh from heightmap...")
grid_points = []  # (bx, by, bz) in Blender coords
for wz_i in np.arange(WZ_MIN, WZ_MAX + GRID_STEP, GRID_STEP):
    for wx_i in np.arange(WX_MIN, WX_MAX + GRID_STEP, GRID_STEP):
        bx, by = world_to_blender(float(wx_i), float(wz_i))
        wh = terrain_h(float(wx_i), float(wz_i))
        bz = wh - MODEL_Y  # height relative to model origin
        grid_points.append((bx, by, bz))

nx = len(np.arange(WX_MIN, WX_MAX + GRID_STEP, GRID_STEP))
nz = len(np.arange(WZ_MIN, WZ_MAX + GRID_STEP, GRID_STEP))
print(f"  Grid: {nx} x {nz} = {len(grid_points)} vertices")

# Build mesh
surface_verts = grid_points
surface_faces = []
for zi in range(nz - 1):
    for xi in range(nx - 1):
        i00 = zi * nx + xi
        i10 = zi * nx + xi + 1
        i01 = (zi + 1) * nx + xi
        i11 = (zi + 1) * nx + xi + 1
        surface_faces.append((i00, i10, i11, i01))

surface_mesh = bpy.data.meshes.new("terrace_surface")
surface_mesh.from_pydata(surface_verts, [], surface_faces)
surface_mesh.update()
surface_obj = bpy.data.objects.new("TerraceSurface", surface_mesh)
bpy.context.collection.objects.link(surface_obj)
surface_obj.data.materials.append(sandstone)

print(f"  Surface: {len(surface_verts)} verts, {len(surface_faces)} faces")

# ══════════════════════════════════════════════════════════════════
# ARCADE INTERIOR — vault ceiling, columns, floor
# ══════════════════════════════════════════════════════════════════
# Arcade dimensions from heightmap wall peaks
# West wall peak: (-484, 997), East wall peak: (-462, 1004)
# In Blender coords:
arcade_w_bx, arcade_w_by = world_to_blender(-484, 997)
arcade_e_bx, arcade_e_by = world_to_blender(-462, 1004)
arcade_cx = (arcade_w_bx + arcade_e_bx) / 2
arcade_cy = (arcade_w_by + arcade_e_by) / 2
arcade_width = math.sqrt((arcade_e_bx - arcade_w_bx)**2 + (arcade_e_by - arcade_w_by)**2)

print(f"  Arcade center (Blender): ({arcade_cx:.1f}, {arcade_cy:.1f})")
print(f"  Arcade width: {arcade_width:.1f}m")

# Arcade runs perpendicular to the line between wall peaks
# Tunnel depth estimated at 12m
TUNNEL_DEPTH = 12.0
VAULT_H = 5.2  # vault crown height (level_drop - road_slab)
VAULT_T = 0.45

all_parts = [surface_obj]

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx, hy, hz)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# Floor slab at model Y=0 (lower terrace level)
half_aw = arcade_width / 2
box("arcade_floor", arcade_cx, arcade_cy, -0.15,
    half_aw + 0.8, TUNNEL_DEPTH / 2, 0.15, stair_mat)

# Side walls
wall_h = VAULT_H
for side in (-1, 1):
    wx = arcade_cx + side * (half_aw + 0.4)
    box(f"wall_{side}", wx, arcade_cy, wall_h / 2,
        0.4, TUNNEL_DEPTH / 2, wall_h / 2, sandstone)

# Three-bay barrel vault
CENTER_W = arcade_width * 0.45
SIDE_VW = (arcade_width - CENTER_W) / 2 - 0.4
COL_R = 0.20
center_r = CENTER_W / 2
side_vr = SIDE_VW / 2
col_row_bx = [arcade_cx - (center_r + COL_R), arcade_cx + (center_r + COL_R)]
side_bx = [arcade_cx - (center_r + COL_R*2 + side_vr),
           arcade_cx + (center_r + COL_R*2 + side_vr)]
center_spring = max(VAULT_H - center_r, 0)
side_crown = VAULT_H - 0.6
side_spring = max(side_crown - side_vr, 0)

vault_segs = 16
hl = TUNNEL_DEPTH / 2

def make_vault(name, cx, radius, v_spring, mat):
    verts = []
    faces = []
    for j in range(2):
        y = arcade_cy + (-hl if j == 0 else hl)
        for i in range(vault_segs + 1):
            a = math.pi * i / vault_segs
            ca, sa = math.cos(a), math.sin(a)
            verts.append((cx + ca * radius, y, sa * radius + v_spring))
            verts.append((cx + ca * (radius + VAULT_T), y,
                          sa * (radius + VAULT_T) + v_spring))
    stride = (vault_segs + 1) * 2
    for i in range(vault_segs):
        a = i*2; b = i*2+2; c = stride+i*2+2; d = stride+i*2
        faces.append((a,d,c,b))
        faces.append((a+1,b+1,c+1,d+1))
    for j in range(2):
        base = j * stride
        for i in range(vault_segs):
            a = base+i*2; b = a+1; c = b+2; d = a+2
            faces.append((a,b,c,d) if j==0 else (a,d,c,b))
    m = bpy.data.meshes.new(name)
    m.from_pydata(verts, [], faces)
    m.update()
    obj = bpy.data.objects.new(name, m)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    all_parts.append(obj)

make_vault("vault_center", arcade_cx, center_r, center_spring, vault_tile)
for si, sbx in enumerate(side_bx):
    make_vault(f"vault_side_{si}", sbx, side_vr, side_spring, vault_tile)

# Interior columns
col_spacing = TUNNEL_DEPTH / 5
for crx in col_row_bx:
    for ci in range(5):
        cy = arcade_cy - hl + col_spacing * 0.5 + ci * col_spacing
        col_h = min(center_spring, side_spring)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=COL_R, depth=col_h, vertices=10,
            location=(crx, cy, col_h / 2))
        col = bpy.context.active_object
        col.name = f"col_{ci}"
        col.data.materials.append(brownstone)
        all_parts.append(col)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=COL_R * 1.4, depth=0.15, vertices=10,
            location=(crx, cy, col_h + 0.075))
        cap = bpy.context.active_object
        cap.name = f"cap_{ci}"
        cap.data.materials.append(brownstone)
        all_parts.append(cap)

# Road slab above vault (seals ceiling)
slab_bot = VAULT_H + VAULT_T
slab_top = 6.0  # level drop
if slab_top > slab_bot:
    box("road_slab", arcade_cx, arcade_cy, (slab_bot + slab_top) / 2,
        half_aw + 0.8, hl, (slab_top - slab_bot) / 2, sandstone)

# ══════════════════════════════════════════════════════════════════
# FINALIZE
# ══════════════════════════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

terrace = bpy.context.active_object
terrace.name = "BethesdaTerrace"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_bethesda_terrace.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Bethesda Terrace to {out_path}")
print(f"  Parts: {len(all_parts)}")
print(f"  Vertices: {len(terrace.data.vertices)}")
print(f"  Faces: {len(terrace.data.polygons)}")

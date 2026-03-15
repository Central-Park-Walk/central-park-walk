"""Bethesda Terrace INTERIOR — vault ceiling, columns, floor for the arcade tunnel.

The terrain mesh (from LiDAR DSM) already shows the correct EXTERIOR shape:
upper platform, staircase slopes, retaining walls, parapets — all captured
at 0.61m resolution. The 3D model only adds what the terrain CAN'T show:
the interior arcade space (barrel vault ceiling, columns, floor slab).

The player walks on the terrain everywhere except inside the tunnel,
where collision is lowered to arcade floor level and this model provides
the ceiling and floor surfaces.

Dimensions from LiDAR heightmap.bin measurements:
  Arcade opening wall-to-wall: 23.1m (peaks at (-484,997) and (-462,1004))
  Level drop: 6.0m (23.6m upper - 17.6m lower)
  Arcade tunnel depth: ~12m (road width estimate)

Orientation (Blender Z-up):
  +Y = south (from The Mall)
  -Y = north (toward fountain)
  Origin = arcade floor center

Exports to models/furniture/cp_bethesda_terrace.glb
"""

import bpy
import math
import os

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
def make_mat(name, color, roughness=0.80, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

sandstone  = make_mat("Sandstone",  (0.72, 0.65, 0.52), 0.85)
vault_tile = make_mat("VaultTile",  (0.82, 0.72, 0.55), 0.55)
stair_mat  = make_mat("StairStone", (0.60, 0.56, 0.48), 0.82)
brownstone = make_mat("Brownstone", (0.42, 0.32, 0.24), 0.80)

# ══════════════════════════════════════════════════════════════════
# DIMENSIONS FROM LIDAR HEIGHTMAP
# ══════════════════════════════════════════════════════════════════
LEVEL_DROP    = 6.0     # 23.6m - 17.6m
ARCADE_W      = 22.0    # wall-to-wall from peak positions
ARCADE_L      = 12.0    # tunnel depth (road width)
ARCADE_H      = LEVEL_DROP - 0.8  # vault crown (5.2m)
VAULT_T       = 0.45    # vault shell thickness
WALL_T        = 0.8     # side walls

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Axis-aligned box at center (cx,cy,cz) with half-extents (hx,hy,hz)."""
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx, hy, hz)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Derived ──
arcade_floor_z = 0.0
half_arc = ARCADE_W / 2.0
hl = ARCADE_L / 2.0

# Three-bay vault
CENTER_W = ARCADE_W * 0.45
SIDE_VW  = (ARCADE_W - CENTER_W) / 2.0 - 0.4
COL_R    = 0.20
center_r = CENTER_W / 2.0
side_vr  = SIDE_VW / 2.0
col_row_x = [-(center_r + COL_R), +(center_r + COL_R)]
side_cx = [-(center_r + COL_R * 2 + side_vr), +(center_r + COL_R * 2 + side_vr)]
center_crown = ARCADE_H
center_spring = max(center_crown - center_r, 0)
side_crown = ARCADE_H - 0.6
side_spring_z = max(side_crown - side_vr, 0)

print(f"Arcade interior: {ARCADE_W:.0f}m wide × {ARCADE_L:.0f}m deep, vault crown {ARCADE_H:.1f}m")

# ════════════════════════════════════════════
# FLOOR SLAB (the only horizontal surface the terrain can't provide)
# ════════════════════════════════════════════
box("arcade_floor", 0, 0, arcade_floor_z - 0.15,
    half_arc + WALL_T, hl, 0.15, stair_mat)

# ════════════════════════════════════════════
# BARREL VAULTS (ceiling the player sees from below)
# ════════════════════════════════════════════
vault_segs = 16

def make_vault(name, cx, radius, v_spring, v_crown, mat):
    verts = []
    faces = []
    for j in range(2):
        y = -hl if j == 0 else hl
        for i in range(vault_segs + 1):
            a = math.pi * i / vault_segs
            cos_a, sin_a = math.cos(a), math.sin(a)
            verts.append((cx + cos_a * radius, y, sin_a * radius + v_spring))
            verts.append((cx + cos_a * (radius + VAULT_T), y,
                          sin_a * (radius + VAULT_T) + v_spring))
    stride = (vault_segs + 1) * 2
    for i in range(vault_segs):
        a = i * 2; b = i * 2 + 2
        c = stride + i * 2 + 2; d = stride + i * 2
        faces.append((a, d, c, b))
        faces.append((a+1, b+1, c+1, d+1))
    for j in range(2):
        base = j * stride
        for i in range(vault_segs):
            a = base + i * 2; b = a + 1; c = b + 2; d = a + 2
            if j == 0:
                faces.append((a, b, c, d))
            else:
                faces.append((a, d, c, b))
    m = bpy.data.meshes.new(name)
    m.from_pydata(verts, [], faces)
    m.update()
    obj = bpy.data.objects.new(name, m)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    all_parts.append(obj)

make_vault("vault_center", 0.0, center_r, center_spring, center_crown, vault_tile)
for si, scx in enumerate(side_cx):
    make_vault(f"vault_side_{si}", scx, side_vr, side_spring_z, side_crown, vault_tile)

# ════════════════════════════════════════════
# INTERIOR COLUMNS (structural supports between the three bays)
# ════════════════════════════════════════════
col_spacing = ARCADE_L / 5.0
for crx in col_row_x:
    for ci in range(5):
        cy = -hl + col_spacing * 0.5 + ci * col_spacing
        col_h = min(center_spring, side_spring_z)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=COL_R, depth=col_h, vertices=10,
            location=(crx, cy, arcade_floor_z + col_h / 2.0))
        col = bpy.context.active_object
        col.name = f"col_{crx:.0f}_{ci}"
        col.data.materials.append(brownstone)
        all_parts.append(col)
        # Capital
        bpy.ops.mesh.primitive_cylinder_add(
            radius=COL_R * 1.4, depth=0.15, vertices=10,
            location=(crx, cy, arcade_floor_z + col_h + 0.075))
        cap = bpy.context.active_object
        cap.name = f"cap_{crx:.0f}_{ci}"
        cap.data.materials.append(brownstone)
        all_parts.append(cap)

# ════════════════════════════════════════════
# SIDE WALLS (arcade interior walls — not visible from outside)
# ════════════════════════════════════════════
wall_h = ARCADE_H
for side in (-1, 1):
    wx = side * (half_arc + WALL_T / 2.0)
    box(f"arcade_wall_{side}", wx, 0, arcade_floor_z + wall_h / 2.0,
        WALL_T / 2.0, hl, wall_h / 2.0, sandstone)

# Road slab above vaults (closes the ceiling)
slab_bot = center_crown + VAULT_T
slab_top = LEVEL_DROP
if slab_top > slab_bot:
    box("road_slab", 0, 0, (slab_bot + slab_top) / 2.0,
        half_arc + WALL_T, hl, (slab_top - slab_bot) / 2.0, sandstone)

# Fill above side vaults
for scx in side_cx:
    fill_bot = side_crown + VAULT_T
    fill_h = slab_bot - fill_bot
    if fill_h > 0.01:
        box(f"vault_fill_{scx:.0f}", scx, 0, fill_bot + fill_h / 2.0,
            side_vr + VAULT_T, hl, fill_h / 2.0, sandstone)

# Facade piers at arcade entrances (decorative, visible from inside)
pier_h = min(center_spring, side_spring_z)
PIER_W = 0.55
for face in (-1, 1):
    py = face * hl
    for crx in col_row_x:
        box(f"pier_{face}_{crx:.0f}", crx, py, arcade_floor_z + pier_h / 2.0,
            PIER_W / 2.0, 0.25, pier_h / 2.0, brownstone)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
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
print(f"Exported Bethesda Terrace (interior only) to {out_path}")
print(f"  Parts: {len(all_parts)}, Verts: {len(terrace.data.vertices)}, Faces: {len(terrace.data.polygons)}")

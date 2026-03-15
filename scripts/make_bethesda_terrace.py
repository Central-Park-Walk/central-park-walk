"""Bethesda Terrace model — ALL dimensions from LiDAR heightmap measurements.

Measured from heightmap.bin at 0.61m resolution:
  Upper terrace:  23.6m elevation, 63m E-W (X:-510 to -447), 35m N-S (Z:999-1034)
  Lower terrace:  17.6m elevation, ~30m E-W (X:-480 to -450)
  Level drop:     6.0m
  Arcade opening: 19m wide at north face (Z=996), narrows to 8m at Z=999
  Arcade center:  X ≈ -469
  West staircase: X ≈ -490, Z=986-1000 (14m run, gradual slope)
  East staircase: X ≈ -460, Z=990-1004 (14m run, gradual slope)
  Arcade tunnel:  ~12m N-S depth (road width, estimated from upper terrace profile)

Orientation (Blender Z-up):
  +Y = south (from The Mall, upper approach)
  -Y = north (toward fountain / lake, stairs descend this way)
  Origin = arcade floor center

Materials: Sandstone, Brownstone trim, VaultTile, StairStone
Exports to models/furniture/cp_bethesda_terrace.glb
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

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
brownstone = make_mat("Brownstone", (0.42, 0.32, 0.24), 0.80)
vault_tile = make_mat("VaultTile",  (0.82, 0.72, 0.55), 0.55)
stair_mat  = make_mat("StairStone", (0.60, 0.56, 0.48), 0.82)

# ══════════════════════════════════════════════════════════════════
# ALL DIMENSIONS FROM LIDAR HEIGHTMAP (0.61m resolution)
# ══════════════════════════════════════════════════════════════════
LEVEL_DROP    = 6.0     # 23.6m - 17.6m, measured from heightmap
TERRACE_W     = 63.0    # upper terrace E-W extent (X:-510 to -447)
UPPER_D       = 35.0    # upper terrace N-S (Z:999 to 1034)

# Arcade tunnel (under the 72nd St road)
ARCADE_W      = 22.0    # wall-to-wall from stalagmite peaks: (-484,997) to (-462,1004)
ARCADE_L      = 12.0    # road width / tunnel depth (estimated from profile)
ARCADE_H      = LEVEL_DROP - 0.8  # vault crown height (level drop minus road slab)
VAULT_T       = 0.45    # vault shell thickness
WALL_T        = 0.8     # arcade side walls
ROAD_SLAB_T   = 0.8     # road slab above vault crown

# Staircases — measured positions relative to arcade center
# West stair: world X ≈ -490, arcade center X = -469, offset = -21m in world
# East stair: world X ≈ -460, arcade center X = -469, offset = +9m in world
# PI rotation MIRRORS X: world -X = Blender +X, world +X = Blender -X
WEST_STAIR_CX = +21.0   # +X in Blender = west in world (PI mirrors X)
EAST_STAIR_CX = -9.0    # -X in Blender = east in world (PI mirrors X)
STAIR_W       = 6.0     # staircase width
STAIR_RUN     = 14.0    # N-S run of each staircase (measured from heightmap)

# Lower terrace
LOWER_W       = 30.0    # E-W extent of lower terrace (X:-480 to -450)
LOWER_D       = 6.0     # landing depth north of staircase bottom

# Balustrades
BALUSTRADE_H  = 0.90
BAL_POST_W    = 0.20
BAL_POST_D    = 0.16
BAL_RAIL_H    = 0.10
BAL_RAIL_D    = 0.12
BAL_SPACING   = 1.8
BALUSTER_W    = 0.07
PIER_W        = 0.55

STEP_RISE     = 0.17
n_steps       = round(LEVEL_DROP / STEP_RISE)
STEP_RISE     = LEVEL_DROP / n_steps
STEP_RUN      = STAIR_RUN / n_steps

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


# ── Derived geometry ──
arcade_floor_z = 0.0
vault_r = ARCADE_W / 2.0
spring_z = arcade_floor_z + (ARCADE_H - vault_r)
if spring_z < arcade_floor_z:
    spring_z = arcade_floor_z  # vault radius > height, use full semicircle
    vault_r = ARCADE_H
vault_crown_z = arcade_floor_z + ARCADE_H
upper_z = LEVEL_DROP
lower_z = arcade_floor_z

# Y extents — stairs descend toward -Y (north/fountain side)
stair_top_y = -ARCADE_L / 2.0
stair_bot_y = stair_top_y - STAIR_RUN

# South wing depth (upper terrace extends south past arcade)
south_wing_d = UPPER_D - ARCADE_L / 2.0  # total upper depth minus half arcade

print(f"Terrace rebuild: upper_z={upper_z:.2f} lower_z={lower_z:.2f} drop={LEVEL_DROP:.2f}")
print(f"  steps={n_steps} step_rise={STEP_RISE:.3f} step_run={STEP_RUN:.3f}")
print(f"  arcade: {ARCADE_W:.0f}m wide × {ARCADE_L:.0f}m deep, vault_r={vault_r:.1f}")
print(f"  stair_run={STAIR_RUN:.0f}m, stair_bot_y={stair_bot_y:.1f}")


# ════════════════════════════════════════════
# 1. ARCADE — walls, floor, three-bay vault
# ════════════════════════════════════════════
half_arc = ARCADE_W / 2.0
hl = ARCADE_L / 2.0

# East and west walls of arcade passage
for side in (-1, 1):
    wx = side * (half_arc + WALL_T / 2.0)
    wall_h = upper_z - arcade_floor_z
    box(f"arcade_wall_{side}", wx, 0, arcade_floor_z + wall_h / 2.0,
        WALL_T / 2.0, hl, wall_h / 2.0, sandstone)

# Arcade floor slab
box("arcade_floor", 0, 0, arcade_floor_z - 0.15,
    half_arc + WALL_T, hl, 0.15, stair_mat)

# Three-bay barrel vault
CENTER_W = ARCADE_W * 0.45   # center bay = 45% of width
SIDE_VW  = (ARCADE_W - CENTER_W) / 2.0 - 0.4  # remaining split for sides minus columns
COL_R    = 0.20
center_r = CENTER_W / 2.0
side_vr  = SIDE_VW / 2.0
col_row_x = [-(center_r + COL_R), +(center_r + COL_R)]
side_cx = [-(center_r + COL_R * 2 + side_vr), +(center_r + COL_R * 2 + side_vr)]
center_crown = ARCADE_H
center_spring = max(center_crown - center_r, 0)
side_crown = ARCADE_H - 0.6
side_spring_z = max(side_crown - side_vr, 0)

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

# Interior columns
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
        bpy.ops.mesh.primitive_cylinder_add(
            radius=COL_R * 1.4, depth=0.15, vertices=10,
            location=(crx, cy, arcade_floor_z + col_h + 0.075))
        cap = bpy.context.active_object
        cap.name = f"cap_{crx:.0f}_{ci}"
        cap.data.materials.append(brownstone)
        all_parts.append(cap)

# Road slab above vaults
slab_bot = center_crown + VAULT_T
box("road_slab", 0, 0, (slab_bot + upper_z) / 2.0,
    half_arc + WALL_T, hl, (upper_z - slab_bot) / 2.0, sandstone)
for scx in side_cx:
    fill_bot = side_crown + VAULT_T
    fill_h = slab_bot - fill_bot
    if fill_h > 0.01:
        box(f"vault_fill_{scx:.0f}", scx, 0, fill_bot + fill_h / 2.0,
            side_vr + VAULT_T, hl, fill_h / 2.0, sandstone)

# Facade pilasters
pier_h = min(center_spring, side_spring_z)
for face in (-1, 1):
    py = face * hl
    for crx in col_row_x:
        box(f"pier_{face}_{crx:.0f}", crx, py, arcade_floor_z + pier_h / 2.0,
            PIER_W / 2.0, 0.25, pier_h / 2.0, brownstone)
        box(f"pier_cap_{face}_{crx:.0f}", crx, py, arcade_floor_z + pier_h + 0.08,
            PIER_W / 2.0 + 0.06, 0.30, 0.08, brownstone)
    for side in (-1, 1):
        px = side * (half_arc - 0.05)
        box(f"pier_outer_{face}_{side}", px, py, arcade_floor_z + pier_h / 2.0,
            0.30, 0.25, pier_h / 2.0, brownstone)

# Cornice at springing line
for face in (-1, 1):
    py = face * (hl + 0.01)
    box(f"impost_{face}", 0, py, center_spring + 0.06,
        half_arc + WALL_T + 0.12, 0.12, 0.06, brownstone)


# ════════════════════════════════════════════
# 2. UPPER TERRACE PLATFORM
# ════════════════════════════════════════════
plat_h = 0.35
# Full-width upper platform — offset 9.5m west (+X in Blender = west in world)
# because the arcade is east of the platform center
# Heightmap: platform X[-510,-447] center=-478.5, arcade center=-469, offset=9.5m
PLAT_OFFSET_X = 9.5
box("upper_platform", PLAT_OFFSET_X, 0, upper_z - plat_h / 2.0,
    TERRACE_W / 2.0, hl, plat_h / 2.0, sandstone)
# South wing extending toward Mall (same offset)
box("upper_wing_s", PLAT_OFFSET_X, hl + south_wing_d / 2.0, upper_z - plat_h / 2.0,
    TERRACE_W / 2.0, south_wing_d / 2.0, plat_h / 2.0, sandstone)


# ════════════════════════════════════════════
# 3. GRAND STAIRCASES (asymmetric: west wider approach, east narrower)
# ════════════════════════════════════════════
for stair_cx in [WEST_STAIR_CX, EAST_STAIR_CX]:
    x_lo = stair_cx - STAIR_W / 2.0
    x_hi = stair_cx + STAIR_W / 2.0

    profile_verts = []
    for si in range(n_steps):
        sy = stair_top_y - si * STEP_RUN
        sz = upper_z - si * STEP_RISE
        profile_verts.append((sy, sz))
        profile_verts.append((sy - STEP_RUN, sz))
        profile_verts.append((sy - STEP_RUN, sz - STEP_RISE))

    profile_verts.append((stair_bot_y, lower_z))
    profile_verts.append((stair_bot_y, lower_z - 0.5))
    profile_verts.append((stair_top_y, lower_z - 0.5))
    profile_verts.append((stair_top_y, upper_z))

    n_pv = len(profile_verts)
    mverts = []
    mfaces = []

    for xi, xv in enumerate([x_lo, x_hi]):
        for pv in profile_verts:
            mverts.append((xv, pv[0], pv[1]))

    for xi in range(2):
        base = xi * n_pv
        face = list(range(base, base + n_pv))
        if xi == 1:
            face.reverse()
        mfaces.append(face)

    for i in range(n_pv):
        i_next = (i + 1) % n_pv
        a = i; b = i_next; c = n_pv + i_next; d = n_pv + i
        mfaces.append((a, b, c, d))

    label = "west" if stair_cx < 0 else "east"
    smesh = bpy.data.meshes.new(f"stair_mesh_{label}")
    smesh.from_pydata(mverts, [], mfaces)
    smesh.update()
    sobj = bpy.data.objects.new(f"staircase_{label}", smesh)
    bpy.context.collection.objects.link(sobj)
    sobj.data.materials.append(stair_mat)
    all_parts.append(sobj)


# ════════════════════════════════════════════
# 4. RETAINING / CHEEK WALLS alongside stairs
# ════════════════════════════════════════════
for stair_cx in [WEST_STAIR_CX, EAST_STAIR_CX]:
    label = "w" if stair_cx < 0 else "e"
    inner_x = stair_cx - STAIR_W / 2.0 if stair_cx > 0 else stair_cx + STAIR_W / 2.0
    outer_x = stair_cx + STAIR_W / 2.0 if stair_cx > 0 else stair_cx - STAIR_W / 2.0

    ow_h = LEVEL_DROP + 0.5
    ow_cy = (stair_top_y + stair_bot_y) / 2.0
    ow_hl = abs(stair_top_y - stair_bot_y) / 2.0

    # Outer cheek wall
    box(f"cheek_outer_{label}", outer_x + (0.35 if stair_cx > 0 else -0.35),
        ow_cy, lower_z + ow_h / 2.0,
        WALL_T / 2.0, ow_hl, ow_h / 2.0, sandstone)
    # Inner cheek wall
    box(f"cheek_inner_{label}", inner_x + (-0.35 if stair_cx > 0 else 0.35),
        ow_cy, lower_z + ow_h / 2.0,
        WALL_T / 2.0, ow_hl, ow_h / 2.0, sandstone)


# ════════════════════════════════════════════
# 5. LOWER TERRACE PLATFORM
# ════════════════════════════════════════════
landing_cy = stair_bot_y - LOWER_D / 2.0
box("lower_platform", 0, landing_cy, lower_z - 0.15,
    LOWER_W / 2.0, LOWER_D / 2.0, 0.15, stair_mat)


# ════════════════════════════════════════════
# 6. BALUSTRADES (upper terrace edges)
# ════════════════════════════════════════════
def add_balustrade_run(x_start, x_end, y_pos, z_base, prefix):
    length = abs(x_end - x_start)
    if length < 0.5:
        return
    n_posts = max(2, round(length / BAL_SPACING) + 1)
    spacing = length / (n_posts - 1)
    dx = 1 if x_end > x_start else -1
    for i in range(n_posts):
        px = x_start + i * spacing * dx
        box(f"{prefix}_p{i}", px, y_pos, z_base + BALUSTRADE_H / 2.0,
            BAL_POST_W / 2.0, BAL_POST_D / 2.0, BALUSTRADE_H / 2.0, brownstone)
    mid_x = (x_start + x_end) / 2.0
    box(f"{prefix}_tr", mid_x, y_pos, z_base + BALUSTRADE_H - BAL_RAIL_H / 2.0,
        length / 2.0, BAL_RAIL_D / 2.0, BAL_RAIL_H / 2.0, sandstone)

# South edge
south_y = hl + south_wing_d
add_balustrade_run(-TERRACE_W / 2.0, TERRACE_W / 2.0, south_y, upper_z, "bal_s")
# North edge — west wing
add_balustrade_run(-TERRACE_W / 2.0, WEST_STAIR_CX - STAIR_W / 2.0 - WALL_T,
                   stair_top_y, upper_z, "bal_nw")
# North edge — east wing
add_balustrade_run(EAST_STAIR_CX + STAIR_W / 2.0 + WALL_T, TERRACE_W / 2.0,
                   stair_top_y, upper_z, "bal_ne")
# East and west edges
for side_x in [-TERRACE_W / 2.0, TERRACE_W / 2.0]:
    label = "w" if side_x < 0 else "e"
    # Simple top rail along the edge
    edge_len = abs(south_y - stair_top_y)
    mid_y = (south_y + stair_top_y) / 2.0
    box(f"bal_{label}_edge_tr", side_x, mid_y, upper_z + BALUSTRADE_H - BAL_RAIL_H / 2.0,
        BAL_RAIL_D / 2.0, edge_len / 2.0, BAL_RAIL_H / 2.0, sandstone)


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
print(f"Exported Bethesda Terrace to {out_path}")
print(f"  Parts joined: {len(all_parts)}")
print(f"  Vertices: {len(terrace.data.vertices)}")
print(f"  Faces: {len(terrace.data.polygons)}")

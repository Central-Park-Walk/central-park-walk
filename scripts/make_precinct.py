"""Generate the Central Park Police Precinct (22nd Precinct) for Central Park Walk.

The Central Park Precinct (1871, Calvert Vaux design) is a Victorian Gothic
structure near the 86th Street Transverse Road. Built of Manhattan schist with
brownstone trim, steep slate gable roof, central dormer, and Gothic pointed-arch
windows in six bays on the long sides.

Key features:
  - Rectangular building ~20m × 12m
  - 2.5 stories, ~9m to eave
  - Dark Manhattan schist construction
  - Corner quoins in lighter stone
  - Steep gable slate roof with central dormer
  - Gothic pointed-arch windows (6 bays per long side, 3 per short side)
  - Main entrance with brownstone pointed arch surround
  - Stone water table course at base
  - Ridge iron cresting

Origin at ground center.
Exports to models/furniture/cp_precinct.glb
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
def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

schist     = make_mat("Schist",     (0.35, 0.33, 0.30), 0.90)  # dark Manhattan schist
brownstone = make_mat("Brownstone", (0.50, 0.38, 0.28), 0.85)  # brownstone trim
quoin      = make_mat("Quoin",      (0.52, 0.50, 0.46), 0.88)  # lighter corner quoins
slate      = make_mat("Slate",      (0.30, 0.30, 0.32), 0.80)  # slate roof
iron_mat   = make_mat("Iron",       (0.14, 0.13, 0.12), 0.60, 0.3)  # iron cresting
window_mat = make_mat("Window",     (0.20, 0.18, 0.16), 0.95)  # dark recessed windows

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Building dimensions ──
W = 20.0     # length (X)
D = 12.0     # depth (Y)
H = 9.0      # wall height to eave
WALL_T = 0.55
RIDGE_H = 4.5  # ridge above eave (steep Victorian Gothic pitch)
OVERHANG = 0.45

hw = W / 2.0
hd = D / 2.0

# ════════════════════════════════════════════
# 1. FOUNDATION / WATER TABLE
# ════════════════════════════════════════════
# Stepped stone base — slightly proud of main walls
box("foundation", 0, 0, 0.20, hw + 0.30, hd + 0.30, 0.40, schist)
# Water table course (projecting stone belt at base of wall)
box("water_table", 0, 0, 0.55, hw + 0.12, hd + 0.12, 0.10, brownstone)

# ════════════════════════════════════════════
# 2. MAIN WALLS — Manhattan schist
# ════════════════════════════════════════════
WALL_BASE = 0.65   # Z where walls begin (top of foundation)
WALL_TOP  = WALL_BASE + H

# Front wall (south, +Y) — main entrance side
# Left section (west of door)
door_w = 2.0
door_h = 3.8
door_cx = 0.0  # centred
left_w  = (W - door_w) / 2.0
right_w = (W - door_w) / 2.0

box("wall_front_l", -(door_w/2 + left_w/2), hd - WALL_T/2, WALL_BASE + H/2,
    left_w/2, WALL_T/2, H/2, schist)
box("wall_front_r",  (door_w/2 + right_w/2), hd - WALL_T/2, WALL_BASE + H/2,
    right_w/2, WALL_T/2, H/2, schist)
# Solid section above door
box("wall_front_top", door_cx, hd - WALL_T/2,
    WALL_BASE + door_h + (H - door_h)/2,
    door_w/2, WALL_T/2, (H - door_h)/2, schist)

# Back wall (north, -Y) — solid
box("wall_back", 0, -hd + WALL_T/2, WALL_BASE + H/2, hw, WALL_T/2, H/2, schist)

# Side walls (east -X, west +X) — full depth
box("wall_east", -hw + WALL_T/2, 0, WALL_BASE + H/2, WALL_T/2, hd, H/2, schist)
box("wall_west",  hw - WALL_T/2, 0, WALL_BASE + H/2, WALL_T/2, hd, H/2, schist)

# ════════════════════════════════════════════
# 3. CORNER QUOINS — alternating lighter stone blocks
# ════════════════════════════════════════════
QUOIN_W = 0.45
QUOIN_H = 0.50
QUOIN_D = 0.08  # how far they project beyond wall face

for corner_x, corner_y in [(-hw, -hd), (-hw, hd), (hw, -hd), (hw, hd)]:
    n_quoins = int(H / QUOIN_H)
    for i in range(n_quoins):
        z = WALL_BASE + i * QUOIN_H + QUOIN_H / 2
        # One quoin proud on X face, next on Y face (alternating)
        if i % 2 == 0:
            # Proud on X face
            sx = math.copysign(1, corner_x)
            box(f"quoin_x_{corner_x:.0f}_{corner_y:.0f}_{i}",
                corner_x + sx * QUOIN_D/2,
                corner_y - math.copysign(QUOIN_W/2, corner_y),
                z,
                WALL_T/2 + QUOIN_D, QUOIN_W/2, QUOIN_H/2 - 0.02,
                quoin)
        else:
            # Proud on Y face
            sy = math.copysign(1, corner_y)
            box(f"quoin_y_{corner_x:.0f}_{corner_y:.0f}_{i}",
                corner_x - math.copysign(QUOIN_W/2, corner_x),
                corner_y + sy * QUOIN_D/2,
                z,
                QUOIN_W/2, WALL_T/2 + QUOIN_D, QUOIN_H/2 - 0.02,
                quoin)

# ════════════════════════════════════════════
# 4. GOTHIC POINTED-ARCH WINDOWS
# ════════════════════════════════════════════
WIN_W   = 0.90    # window opening width
WIN_H   = 1.80    # rectangular body height
POINT_H = 0.55    # extra height of the pointed arch above the rect body
WIN_Z   = WALL_BASE + H * 0.40   # window centre (rect body centre)
WIN_INSET = 0.08  # how far dark panel is recessed

# Helper: place a window (dark recess + brownstone surround + pointed arch piece)
def gothic_window(name, cx, cy, cz, face_axis):
    """face_axis: 'X' wall normal along X, 'Y' wall normal along Y"""
    if face_axis == 'Y':
        # dark recess
        box(f"{name}_glass", cx, cy, cz, WIN_W/2 - 0.04, WIN_INSET, WIN_H/2, window_mat)
        # surround
        box(f"{name}_surr", cx, cy, cz, WIN_W/2 + 0.07, WIN_INSET + 0.02, WIN_H/2 + 0.07, brownstone)
        # pointed arch keystone block
        arch_z = cz + WIN_H/2 + POINT_H/2
        box(f"{name}_arch", cx, cy, arch_z, WIN_W/2 * 0.55, WIN_INSET + 0.02, POINT_H/2 + 0.04, brownstone)
        # narrow peak tip
        box(f"{name}_tip", cx, cy, arch_z + POINT_H/2 + 0.05,
            WIN_W * 0.12, WIN_INSET + 0.02, 0.08, brownstone)
    else:  # face_axis == 'X'
        box(f"{name}_glass", cx, cy, cz, WIN_INSET, WIN_W/2 - 0.04, WIN_H/2, window_mat)
        box(f"{name}_surr", cx, cy, cz, WIN_INSET + 0.02, WIN_W/2 + 0.07, WIN_H/2 + 0.07, brownstone)
        arch_z = cz + WIN_H/2 + POINT_H/2
        box(f"{name}_arch", cx, cy, arch_z, WIN_INSET + 0.02, WIN_W/2 * 0.55, POINT_H/2 + 0.04, brownstone)
        box(f"{name}_tip", cx, cy, arch_z + POINT_H/2 + 0.05,
            WIN_INSET + 0.02, WIN_W * 0.12, 0.08, brownstone)

# Long sides — 6 bays each, spaced evenly
N_LONG = 6
bay_long = (W - 2 * WALL_T - 1.0) / (N_LONG - 1)   # -1.0 margin from quoins

# Front face (south, +Y): bays skip the doorway centre, split 3+3
win_xs_front = []
for i in range(N_LONG // 2):
    win_xs_front.append(-(door_w/2 + 1.0 + i * bay_long))
    win_xs_front.append( (door_w/2 + 1.0 + i * bay_long))

for i, wx in enumerate(win_xs_front):
    gothic_window(f"win_front_{i}", wx, hd, WIN_Z, 'Y')

# Back face (north, -Y): 6 evenly spaced bays
for i in range(N_LONG):
    wx = -hw + WALL_T + 1.0 + i * bay_long
    gothic_window(f"win_back_{i}", wx, -hd, WIN_Z, 'Y')

# Short sides — 3 bays each
N_SHORT = 3
bay_short = (D - 2 * WALL_T - 1.0) / (N_SHORT - 1)
for i in range(N_SHORT):
    wy = -hd + WALL_T + 1.0 + i * bay_short
    # East wall (-X)
    gothic_window(f"win_east_{i}", -hw, wy, WIN_Z, 'X')
    # West wall (+X)
    gothic_window(f"win_west_{i}",  hw, wy, WIN_Z, 'X')

# Upper storey windows (half-height, in the wall above the belt course)
# 4 on long sides, 2 on short sides
WIN2_W   = 0.65
WIN2_H   = 1.00
WIN2_Z   = WALL_BASE + H * 0.76

def small_gothic_window(name, cx, cy, cz, face_axis):
    if face_axis == 'Y':
        box(f"{name}_glass", cx, cy, cz, WIN2_W/2 - 0.04, WIN_INSET, WIN2_H/2, window_mat)
        box(f"{name}_surr",  cx, cy, cz, WIN2_W/2 + 0.06, WIN_INSET + 0.02, WIN2_H/2 + 0.06, brownstone)
        box(f"{name}_arch",  cx, cy, cz + WIN2_H/2 + 0.20,
            WIN2_W/2 * 0.50, WIN_INSET + 0.02, 0.25, brownstone)
    else:
        box(f"{name}_glass", cx, cy, cz, WIN_INSET, WIN2_W/2 - 0.04, WIN2_H/2, window_mat)
        box(f"{name}_surr",  cx, cy, cz, WIN_INSET + 0.02, WIN2_W/2 + 0.06, WIN2_H/2 + 0.06, brownstone)
        box(f"{name}_arch",  cx, cy, cz + WIN2_H/2 + 0.20,
            WIN_INSET + 0.02, WIN2_W/2 * 0.50, 0.25, brownstone)

N_LONG2 = 4
bay_long2 = (W - 2 * WALL_T - 2.0) / (N_LONG2 - 1)
for i in range(N_LONG2):
    wx = -hw + WALL_T + 2.0 + i * bay_long2
    small_gothic_window(f"win2_front_{i}", wx,  hd, WIN2_Z, 'Y')
    small_gothic_window(f"win2_back_{i}",  wx, -hd, WIN2_Z, 'Y')

N_SHORT2 = 2
bay_short2 = (D - 2 * WALL_T - 2.0) / (N_SHORT2 - 1)
for i in range(N_SHORT2):
    wy = -hd + WALL_T + 2.0 + i * bay_short2
    small_gothic_window(f"win2_east_{i}", -hw, wy, WIN2_Z, 'X')
    small_gothic_window(f"win2_west_{i}",  hw, wy, WIN2_Z, 'X')

# ════════════════════════════════════════════
# 5. MAIN ENTRANCE — brownstone pointed arch surround
# ════════════════════════════════════════════
DOOR_DEPTH = 0.25   # how far the arch projects forward

# Deep brownstone door frame
box("door_frame", door_cx, hd + DOOR_DEPTH/2, WALL_BASE + door_h/2,
    door_w/2 + 0.18, DOOR_DEPTH/2 + WALL_T/2, door_h/2, brownstone)
# Dark door fill
box("door_fill", door_cx, hd + DOOR_DEPTH/2 + 0.02, WALL_BASE + door_h/2,
    door_w/2 - 0.12, DOOR_DEPTH/4, door_h/2 - 0.12, window_mat)
# Pointed arch over door — two angled brownstone blocks
arch_w  = door_w/2 + 0.18
arch_tip_h = 0.90
box("door_arch_l", door_cx - arch_w * 0.30, hd + DOOR_DEPTH/2,
    WALL_BASE + door_h + arch_tip_h * 0.40,
    arch_w * 0.38, DOOR_DEPTH/2 + WALL_T/2, arch_tip_h * 0.55, brownstone)
box("door_arch_r", door_cx + arch_w * 0.30, hd + DOOR_DEPTH/2,
    WALL_BASE + door_h + arch_tip_h * 0.40,
    arch_w * 0.38, DOOR_DEPTH/2 + WALL_T/2, arch_tip_h * 0.55, brownstone)
# Keystone tip
box("door_arch_key", door_cx, hd + DOOR_DEPTH/2,
    WALL_BASE + door_h + arch_tip_h * 0.82,
    arch_w * 0.14, DOOR_DEPTH/2 + WALL_T/2, arch_tip_h * 0.18 + 0.04, brownstone)

# Stone steps (3 wide steps up to entrance)
for step in range(3):
    sw = door_w/2 + 0.5 + step * 0.25
    sz = 0.15 + step * 0.18
    box(f"step_{step}", door_cx, hd + 0.80 + step * 0.35, sz, sw, 0.35, 0.12, brownstone)

# ════════════════════════════════════════════
# 6. BELT COURSE — horizontal brownstone band mid-wall
# ════════════════════════════════════════════
BELT_Z = WALL_BASE + H * 0.58
box("belt_front", 0,  hd, BELT_Z, hw, WALL_T/2 + 0.06, 0.09, brownstone)
box("belt_back",  0, -hd, BELT_Z, hw, WALL_T/2 + 0.06, 0.09, brownstone)
box("belt_east", -hw, 0, BELT_Z, WALL_T/2 + 0.06, hd, 0.09, brownstone)
box("belt_west",  hw, 0, BELT_Z, WALL_T/2 + 0.06, hd, 0.09, brownstone)

# ════════════════════════════════════════════
# 7. CORNICE — projecting stone eave course
# ════════════════════════════════════════════
CORNICE_Z = WALL_TOP
box("cornice_front", 0,  hd + 0.05, CORNICE_Z + 0.10, hw + 0.08, WALL_T/2 + 0.10, 0.14, brownstone)
box("cornice_back",  0, -hd - 0.05, CORNICE_Z + 0.10, hw + 0.08, WALL_T/2 + 0.10, 0.14, brownstone)
box("cornice_east", -hw - 0.05, 0, CORNICE_Z + 0.10, WALL_T/2 + 0.10, hd + 0.10, 0.14, brownstone)
box("cornice_west",  hw + 0.05, 0, CORNICE_Z + 0.10, WALL_T/2 + 0.10, hd + 0.10, 0.14, brownstone)

# ════════════════════════════════════════════
# 8. MAIN GABLE ROOF — steep slate, ridge runs E–W (along X)
# ════════════════════════════════════════════
eave_z = WALL_TOP + 0.24   # above cornice

rv = [
    (-hw - OVERHANG, -hd - OVERHANG, eave_z),   # 0 NW eave
    ( hw + OVERHANG, -hd - OVERHANG, eave_z),   # 1 NE eave
    ( hw + OVERHANG,  hd + OVERHANG, eave_z),   # 2 SE eave
    (-hw - OVERHANG,  hd + OVERHANG, eave_z),   # 3 SW eave
    (-hw - OVERHANG,  0,             eave_z + RIDGE_H),  # 4 ridge west
    ( hw + OVERHANG,  0,             eave_z + RIDGE_H),  # 5 ridge east
]
rf = [
    (3, 0, 4),      # west gable (south slope left)
    (0, 1, 5, 4),   # north slope
    (1, 2, 5),      # east gable (not right — Blender winding fix below)
    (2, 3, 4, 5),   # south slope
    (0, 3, 2, 1),   # soffit (underside)
]
# Note: west gable winding (3,0,4) and east (1,2,5) give outward normals for
# gable ends whose ridge runs in X direction.
rmesh = bpy.data.meshes.new("roof_mesh")
rmesh.from_pydata(rv, [], rf)
rmesh.update()
robj = bpy.data.objects.new("MainRoof", rmesh)
bpy.context.collection.objects.link(robj)
robj.data.materials.append(slate)
all_parts.append(robj)

# Gable wall fill — schist triangles above eave level at each end
for side_x, winding in [(-1, (0, 1, 2)), (1, (0, 2, 1))]:
    gx = side_x * (hw + OVERHANG - 0.05)
    gv = [
        (gx, -hd, eave_z),
        (gx,  hd, eave_z),
        (gx,   0, eave_z + RIDGE_H - 0.10),
    ]
    gm = bpy.data.meshes.new(f"gable_fill_{side_x}")
    gm.from_pydata(gv, [], [winding])
    gm.update()
    go = bpy.data.objects.new(f"GableFill_{side_x}", gm)
    bpy.context.collection.objects.link(go)
    go.data.materials.append(schist)
    all_parts.append(go)

# Ridge board
box("ridge", 0, 0, eave_z + RIDGE_H + 0.05, hw + OVERHANG, 0.05, 0.07, brownstone)

# ════════════════════════════════════════════
# 9. CENTRAL DORMER — projects from south slope
# ════════════════════════════════════════════
# Dormer sits on the south roof slope centred in X, centred on the slope in Y
DORM_W   = 3.0    # dormer width (X)
DORM_H   = 2.2    # dormer wall height above roof intersection
DORM_D   = 1.60   # dormer depth (projects south from ridge line)
DORM_RIDGE = 1.40 # dormer roof ridge above dormer wall

# Roof slope intercept: south slope goes from (_, hd+OVERHANG, eave_z) to (_, 0, eave_z+RIDGE_H)
# At Y offset from ridge (dormer base Y = -DORM_D/2 toward south):
# slope ratio = (hd + OVERHANG) / RIDGE_H
dorm_roof_y = -DORM_D * 0.4    # centre of dormer along slope (roughly), Y < 0 = toward south slope
slope_frac = (hd + OVERHANG - abs(dorm_roof_y)) / (hd + OVERHANG)  # 0=eave, 1=ridge
dorm_base_z = eave_z + slope_frac * RIDGE_H - 0.15

dorm_cx = 0.0
dorm_cy = dorm_roof_y
dorm_wall_top_z = dorm_base_z + DORM_H

# Dormer front wall (south face of dormer)
dorm_front_y = dorm_cy + DORM_D/2
box("dorm_wall_front", dorm_cx, dorm_front_y, dorm_base_z + DORM_H/2,
    DORM_W/2, WALL_T/2 * 0.7, DORM_H/2, schist)
# Dormer side walls
for sx in (-1, 1):
    box(f"dorm_wall_side_{sx}", dorm_cx + sx * (DORM_W/2 - WALL_T*0.35),
        dorm_cy, dorm_base_z + DORM_H/2,
        WALL_T/2 * 0.7, DORM_D/2, DORM_H/2, schist)

# Dormer window — single tall Gothic arch window
gothic_window("dorm_win", dorm_cx, dorm_front_y, dorm_base_z + DORM_H * 0.48, 'Y')

# Dormer gable roof (mini gable, ridge runs E–W)
drv = [
    (-DORM_W/2 - 0.15, dorm_cy - DORM_D/2 - 0.10, dorm_wall_top_z),   # 0 NW
    ( DORM_W/2 + 0.15, dorm_cy - DORM_D/2 - 0.10, dorm_wall_top_z),   # 1 NE
    ( DORM_W/2 + 0.15, dorm_front_y + 0.15,        dorm_wall_top_z),   # 2 SE
    (-DORM_W/2 - 0.15, dorm_front_y + 0.15,        dorm_wall_top_z),   # 3 SW
    (-DORM_W/2 - 0.15,  dorm_cy,                   dorm_wall_top_z + DORM_RIDGE),  # 4 ridge W
    ( DORM_W/2 + 0.15,  dorm_cy,                   dorm_wall_top_z + DORM_RIDGE),  # 5 ridge E
]
drf = [
    (3, 0, 4),
    (0, 1, 5, 4),
    (1, 2, 5),
    (2, 3, 4, 5),
    (0, 3, 2, 1),
]
drm = bpy.data.meshes.new("dormer_roof")
drm.from_pydata(drv, [], drf)
drm.update()
dro = bpy.data.objects.new("DormerRoof", drm)
bpy.context.collection.objects.link(dro)
dro.data.materials.append(slate)
all_parts.append(dro)

# Dormer cornice
box("dorm_cornice_f", dorm_cx, dorm_front_y + 0.08, dorm_wall_top_z + 0.06,
    DORM_W/2 + 0.18, 0.06, 0.09, brownstone)

# ════════════════════════════════════════════
# 10. RIDGE IRON CRESTING
# ════════════════════════════════════════════
ridge_z = eave_z + RIDGE_H
n_crests = 14
crest_sp = (W + 2 * OVERHANG) / n_crests
for i in range(n_crests + 1):
    cx = -hw - OVERHANG + i * crest_sp
    box(f"crest_{i}", cx, 0, ridge_z + 0.18, 0.025, 0.025, 0.20, iron_mat)
    # Fleur-de-lis style horizontal arm
    box(f"crest_arm_{i}", cx, 0, ridge_z + 0.28, 0.10, 0.025, 0.025, iron_mat)

# ════════════════════════════════════════════
# 11. CHIMNEY STACKS — two on roof (Victorian heating)
# ════════════════════════════════════════════
for chx, chy in [(-hw * 0.30, -hd * 0.30), (hw * 0.30, hd * 0.30)]:
    # Chimney rises from roof slope; compute approximate Z at that point
    slope_frac_ch = (hd - abs(chy)) / (hd + OVERHANG)
    ch_base_z = eave_z + slope_frac_ch * RIDGE_H + 0.10
    ch_h = (ridge_z + 1.0) - ch_base_z   # extends above ridge
    box(f"chimney_{chx:.0f}", chx, chy, ch_base_z + ch_h/2, 0.55, 0.55, ch_h/2, schist)
    # Chimney cap (brownstone)
    box(f"chimney_cap_{chx:.0f}", chx, chy, ch_base_z + ch_h + 0.08, 0.65, 0.65, 0.10, brownstone)
    # Chimney pots (two per stack)
    for pot_x in (-0.15, 0.15):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.45, vertices=8,
            location=(chx + pot_x, chy, ch_base_z + ch_h + 0.38))
        pot = bpy.context.active_object
        pot.name = f"chimney_pot_{chx:.0f}_{pot_x}"
        pot.data.materials.append(brownstone)
        all_parts.append(pot)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "CPPrecinct"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_precinct.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported CP Precinct to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

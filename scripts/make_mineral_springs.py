"""Generate Mineral Springs Pavilion for Central Park Walk.

The Mineral Springs Pavilion (1868, restored 1990s) is a Victorian
Italianate building near the western edge of the Sheep Meadow. Now
houses Le Pain Quotidien bakery/cafe.

Key features:
  - Rectangular building ~18m × 10m, walls ~5m, total ~7m
  - Elegant Italianate style with front loggia (covered porch)
  - Front loggia: 6 arched bays supported by slender iron columns
  - Low-pitch hip roof with decorative cornice and brackets
  - Painted wood/iron construction (cream/warm white body)
  - Stone foundation (brownish gray)
  - Red-brown trim accents

The building faces south (+Y direction), with the loggia projecting
forward on the south face. Origin at ground center.

Exports to models/furniture/cp_mineral_springs.glb
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

cream      = make_mat("Cream",     (0.82, 0.78, 0.70), 0.75)
stone_base = make_mat("StoneBase", (0.48, 0.44, 0.40), 0.88)
trim       = make_mat("Trim",      (0.50, 0.32, 0.22), 0.80)
roof       = make_mat("Roof",      (0.35, 0.30, 0.25), 0.82)
iron_col   = make_mat("IronCol",   (0.15, 0.15, 0.14), 0.55, 0.4)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cylinder(name, cx, cy, cz, r, h, mat, segs=12):
    """Add a cylinder with base at cz, top at cz+h."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=h, vertices=segs,
        location=(cx, cy, cz + h / 2))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Dimensions ──
W = 18.0       # building width (X)
D = 10.0       # building depth (Y) — main body only
H = 5.0        # wall height to eave
WALL_T = 0.35  # wall thickness
BASE_H = 0.50  # stone foundation height
LOGGIA_D = 3.2 # loggia depth (how far it projects south)
LOGGIA_N = 6   # number of arched bays
ARCH_H = 3.6   # height of arch opening in loggia
COL_R = 0.10   # iron column radius
CORNICE_H = 0.30  # decorative cornice band height
BRACKET_W = 0.12  # bracket width
BRACKET_D = 0.28  # bracket depth (projection from wall)
BRACKET_H = 0.35  # bracket height
OVERHANG = 0.55   # roof overhang past cornice

hw = W / 2.0
hd = D / 2.0

# South face of main building (inside face of front wall)
front_y = hd

# ════════════════════════════════════════════
# 1. STONE FOUNDATION
# ════════════════════════════════════════════
# Main building footprint base + loggia base
box("foundation_main", 0, 0, BASE_H / 2,
    hw + 0.15, hd + 0.15, BASE_H / 2, stone_base)
box("foundation_loggia", 0, hd + LOGGIA_D / 2, BASE_H / 2,
    hw + 0.15, LOGGIA_D / 2 + 0.15, BASE_H / 2, stone_base)

# Low step at loggia entry (south edge)
box("entry_step", 0, hd + LOGGIA_D + 0.30, BASE_H / 4,
    hw * 0.6, 0.30, BASE_H / 4, stone_base)

# ════════════════════════════════════════════
# 2. MAIN BUILDING WALLS (cream painted wood/stucco)
# ════════════════════════════════════════════
wall_base = BASE_H  # walls sit on top of foundation

# Back wall (north face, solid)
box("wall_north", 0, -hd + WALL_T / 2, wall_base + H / 2,
    hw, WALL_T / 2, H / 2, cream)

# East side wall
box("wall_east", -hw + WALL_T / 2, 0, wall_base + H / 2,
    WALL_T / 2, hd, H / 2, cream)

# West side wall
box("wall_west", hw - WALL_T / 2, 0, wall_base + H / 2,
    WALL_T / 2, hd, H / 2, cream)

# Front wall (south face) — solid above the loggia beam height,
# plus narrow piers between bays at ground level
# Upper portion (above arch height)
upper_wall_h = H - ARCH_H
box("wall_south_upper", 0, hd - WALL_T / 2,
    wall_base + ARCH_H + upper_wall_h / 2,
    hw, WALL_T / 2, upper_wall_h / 2, cream)

# ── Side-wall windows (2 per long side) ──
win_w = 1.00
win_h = 1.80
win_surr = 0.07
win_z = wall_base + H * 0.45

for side in (-1, 1):  # -1=east, +1=west
    wx = side * hw
    for wy_off in (-hd * 0.50, hd * 0.15):
        # Window surround (cream with trim-colored reveal)
        box(f"win_surr_{side}_{wy_off}", wx, wy_off, win_z,
            win_surr, win_w / 2 + win_surr, win_h / 2 + win_surr, trim)
        # Window opening fill (slightly recessed, darker)
        box(f"win_fill_{side}_{wy_off}", wx - side * 0.01, wy_off, win_z,
            win_surr * 0.5, win_w / 2, win_h / 2, stone_base)
        # Semicircular arch head above window (represented as flat lunette)
        box(f"win_arch_{side}_{wy_off}", wx, wy_off,
            win_z + win_h / 2 + 0.18,
            win_surr, win_w * 0.42, 0.20, trim)

# Back wall windows (3 evenly spaced)
for wx_off in (-hw * 0.52, 0.0, hw * 0.52):
    box(f"win_n_surr_{wx_off}", wx_off, -hd, win_z,
        win_w / 2 + win_surr, win_surr, win_h / 2 + win_surr, trim)
    box(f"win_n_fill_{wx_off}", wx_off, -hd + 0.01, win_z,
        win_w / 2, win_surr * 0.5, win_h / 2, stone_base)
    box(f"win_n_arch_{wx_off}", wx_off, -hd,
        win_z + win_h / 2 + 0.18,
        win_w * 0.42, win_surr, 0.20, trim)

# ════════════════════════════════════════════
# 3. FRONT LOGGIA — 6 arched bays with iron columns
# ════════════════════════════════════════════
loggia_floor_y = hd + LOGGIA_D / 2

# Loggia floor slab
box("loggia_floor", 0, loggia_floor_y, wall_base - 0.04,
    hw + 0.10, LOGGIA_D / 2 + 0.10, 0.08, stone_base)

# Columns: 7 columns (N+1) at bay intervals along the south loggia edge
# Plus 2 at the building wall corners (north end of loggia)
bay_w = W / LOGGIA_N
col_z = wall_base  # base of column

# Front row — 7 columns at loggia face (south edge)
loggia_face_y = hd + LOGGIA_D
for i in range(LOGGIA_N + 1):
    cx = -hw + i * bay_w
    # Base plinth (square stone block)
    box(f"col_plinth_f_{i}", cx, loggia_face_y,
        col_z + 0.10, 0.16, 0.16, 0.10, stone_base)
    # Iron shaft
    cylinder(f"col_shaft_f_{i}", cx, loggia_face_y,
             col_z + 0.20, COL_R, ARCH_H - 0.40, iron_col, 12)
    # Capital block
    box(f"col_cap_f_{i}", cx, loggia_face_y,
        col_z + ARCH_H - 0.12, 0.18, 0.18, 0.08, cream)

# Back row of loggia — 7 columns at the main building face (south wall line)
# These align with the piers embedded in the front wall
for i in range(LOGGIA_N + 1):
    cx = -hw + i * bay_w
    box(f"col_plinth_b_{i}", cx, front_y,
        col_z + 0.10, 0.16, 0.16, 0.10, stone_base)
    cylinder(f"col_shaft_b_{i}", cx, front_y,
             col_z + 0.20, COL_R, ARCH_H - 0.40, iron_col, 12)
    box(f"col_cap_b_{i}", cx, front_y,
        col_z + ARCH_H - 0.12, 0.18, 0.18, 0.08, cream)

# Arch keystones and spandrel fill for each bay (front row)
# Arch represented as a flat lintel band + raised keystone above it
for i in range(LOGGIA_N):
    ax = -hw + (i + 0.5) * bay_w
    arch_top_z = col_z + ARCH_H

    # Flat arch lintel (spanning between column caps)
    box(f"arch_lintel_f_{i}", ax, loggia_face_y,
        arch_top_z + 0.05,
        bay_w / 2 - COL_R - 0.02, 0.12, 0.07, cream)

    # Keystone (slightly proud of lintel)
    box(f"keystone_f_{i}", ax, loggia_face_y,
        arch_top_z + 0.14,
        0.14, 0.12, 0.10, trim)

    # Spandrel panel (wall fill between arch and loggia ceiling beam)
    # Between back columns
    box(f"arch_lintel_b_{i}", ax, front_y,
        arch_top_z + 0.05,
        bay_w / 2 - COL_R - 0.02, 0.12, 0.07, cream)
    box(f"keystone_b_{i}", ax, front_y,
        arch_top_z + 0.14,
        0.14, 0.12, 0.10, trim)

# Loggia ceiling beam (connects front and back column rows at arch height)
# East and west end beams
for side in (-1, 1):
    bx = side * hw
    box(f"loggia_end_beam_{side}", bx, loggia_floor_y,
        col_z + ARCH_H + 0.10,
        0.15, LOGGIA_D / 2, 0.12, cream)

# Loggia roof slab (flat, connecting front to back)
box("loggia_roof_slab", 0, loggia_floor_y,
    wall_base + ARCH_H + 0.22,
    hw + 0.10, LOGGIA_D / 2 + 0.10, 0.14, cream)

# ════════════════════════════════════════════
# 4. DECORATIVE CORNICE + BRACKETS
# ════════════════════════════════════════════
cornice_z = wall_base + H

# Main cornice band (runs around all 4 sides of main building)
# North
box("cornice_north", 0, -hd, cornice_z + CORNICE_H / 2,
    hw + OVERHANG, WALL_T / 2 + 0.12, CORNICE_H / 2, cream)
# East
box("cornice_east", -hw, 0, cornice_z + CORNICE_H / 2,
    WALL_T / 2 + 0.12, hd, CORNICE_H / 2, cream)
# West
box("cornice_west", hw, 0, cornice_z + CORNICE_H / 2,
    WALL_T / 2 + 0.12, hd, CORNICE_H / 2, cream)
# South (above main front wall, not loggia)
box("cornice_south", 0, hd, cornice_z + CORNICE_H / 2,
    hw + OVERHANG, WALL_T / 2 + 0.12, CORNICE_H / 2, cream)

# Trim accent line just below cornice (thin trim band)
trim_band_h = 0.08
for (name, cy, ly) in [
    ("trim_n", -hd, hd + LOGGIA_D),
]:
    pass  # all sides below
for (bname, bcx, bcy, bhx, bhy) in [
    ("trim_n",  0,    -hd,  hw + 0.05, hd * 0),
    ("trim_e", -hw,    0,   0,         hd),
    ("trim_w",  hw,    0,   0,         hd),
    ("trim_s",  0,     hd,  hw + 0.05, 0),
]:
    pass  # handled inline below

# Continuous trim band under cornice on all walls
box("trim_band_north", 0, -hd, cornice_z - trim_band_h / 2,
    hw + 0.02, WALL_T / 2 + 0.04, trim_band_h / 2, trim)
box("trim_band_east", -hw, 0, cornice_z - trim_band_h / 2,
    WALL_T / 2 + 0.04, hd + 0.02, trim_band_h / 2, trim)
box("trim_band_west", hw, 0, cornice_z - trim_band_h / 2,
    WALL_T / 2 + 0.04, hd + 0.02, trim_band_h / 2, trim)
box("trim_band_south", 0, hd, cornice_z - trim_band_h / 2,
    hw + 0.02, WALL_T / 2 + 0.04, trim_band_h / 2, trim)

# Cornice brackets — Italianate feature: decorative paired brackets
# under the eave cornice, spaced ~1.5m apart on all four sides
bracket_spacing = 1.8

# North side brackets
n_brack_n = int(W / bracket_spacing)
for i in range(n_brack_n):
    bx = -hw + (i + 0.5) * (W / n_brack_n)
    box(f"brack_n_{i}", bx, -hd - BRACKET_D / 2,
        cornice_z - BRACKET_H / 2,
        BRACKET_W / 2, BRACKET_D / 2, BRACKET_H / 2, trim)

# South side brackets
for i in range(n_brack_n):
    bx = -hw + (i + 0.5) * (W / n_brack_n)
    box(f"brack_s_{i}", bx, hd + BRACKET_D / 2,
        cornice_z - BRACKET_H / 2,
        BRACKET_W / 2, BRACKET_D / 2, BRACKET_H / 2, trim)

# East side brackets
n_brack_e = int(D / bracket_spacing)
for i in range(n_brack_e):
    by = -hd + (i + 0.5) * (D / n_brack_e)
    box(f"brack_e_{i}", -hw - BRACKET_D / 2, by,
        cornice_z - BRACKET_H / 2,
        BRACKET_D / 2, BRACKET_W / 2, BRACKET_H / 2, trim)

# West side brackets
for i in range(n_brack_e):
    by = -hd + (i + 0.5) * (D / n_brack_e)
    box(f"brack_w_{i}", hw + BRACKET_D / 2, by,
        cornice_z - BRACKET_H / 2,
        BRACKET_D / 2, BRACKET_W / 2, BRACKET_H / 2, trim)

# ════════════════════════════════════════════
# 5. LOW-PITCH HIP ROOF
# ════════════════════════════════════════════
eave_z = cornice_z + CORNICE_H
ROOF_RISE = 2.0  # low Italian pitch — ~11 degrees on 18m span

# Hip roof mesh: 4 eave corners + 2 ridge endpoints
# The loggia is under the main roof overhang (front face extends to cover it)
ovh = OVERHANG
# Eave outline includes slight projection over loggia on south side
rv = [
    (-hw - ovh, -hd - ovh,           eave_z),       # 0 NE corner
    ( hw + ovh, -hd - ovh,           eave_z),       # 1 NW corner
    ( hw + ovh,  hd + LOGGIA_D + ovh, eave_z),      # 2 SW corner
    (-hw - ovh,  hd + LOGGIA_D + ovh, eave_z),      # 3 SE corner
    # Ridge (shortened for hip, centered over building + half loggia)
    (-hw * 0.45,  hd * 0.10 + LOGGIA_D * 0.5, eave_z + ROOF_RISE),  # 4 ridge east
    ( hw * 0.45,  hd * 0.10 + LOGGIA_D * 0.5, eave_z + ROOF_RISE),  # 5 ridge west
]
rf = [
    (0, 1, 5, 4),   # north slope
    (2, 3, 4, 5),   # south slope
    (3, 0, 4),      # east hip
    (1, 2, 5),      # west hip
    (0, 3, 2, 1),   # soffit
]
rm = bpy.data.meshes.new("hip_roof")
rm.from_pydata(rv, [], rf)
rm.update()
ro = bpy.data.objects.new("HipRoof", rm)
bpy.context.collection.objects.link(ro)
ro.data.materials.append(roof)
all_parts.append(ro)

# Ridge cap (flat band along ridge line)
ridge_cx = 0
ridge_cy = hd * 0.10 + LOGGIA_D * 0.5
ridge_len = hw * 0.90  # half-length of ridge
box("ridge_cap", ridge_cx, ridge_cy, eave_z + ROOF_RISE + 0.08,
    ridge_len, 0.12, 0.08, trim)

# Decorative finial at each hip end (small turned wood ornament)
for side in (-1, 1):
    for cx_s in (-hw * 0.45, hw * 0.45):
        pass  # finials below
# Apex finials — small vertical accent at each hip peak junction
for cx_s in (-hw * 0.45, hw * 0.45):
    cylinder(f"finial_{cx_s}", cx_s, ridge_cy,
             eave_z + ROOF_RISE + 0.16, 0.05, 0.25, trim, 8)

# ════════════════════════════════════════════
# 6. DOOR — main entry in loggia (center bay)
# ════════════════════════════════════════════
door_w = 1.10
door_h = 2.60
door_z = wall_base + door_h / 2

# Door surround in center of front wall
box("door_surround", 0, front_y,
    door_z,
    door_w / 2 + 0.10, WALL_T / 2 + 0.04, door_h / 2 + 0.10, trim)
# Door panel (dark interior fill)
box("door_panel", 0, front_y + 0.01,
    door_z,
    door_w / 2, 0.04, door_h / 2, stone_base)
# Semicircular transom arch above door
box("door_transom", 0, front_y,
    wall_base + door_h + 0.22,
    door_w / 2, WALL_T / 2 + 0.04, 0.24, trim)

# ════════════════════════════════════════════
# 7. CHIMNEY — one modest chimney on north slope
# ════════════════════════════════════════════
chimney_x = hw * 0.38
chimney_y = -hd * 0.30
chimney_base_z = eave_z - 0.50
chimney_h = 1.80

box("chimney_shaft", chimney_x, chimney_y,
    chimney_base_z + chimney_h / 2,
    0.30, 0.30, chimney_h / 2, stone_base)
# Chimney cap
box("chimney_cap", chimney_x, chimney_y,
    chimney_base_z + chimney_h + 0.08,
    0.36, 0.36, 0.08, trim)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "MineralSpringsPavilion"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_mineral_springs.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Mineral Springs Pavilion to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

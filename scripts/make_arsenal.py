"""Generate the Arsenal building for Central Park Walk.

The Arsenal (1848) is a Gothic Revival red brick landmark at the southeast
corner of Central Park at 64th Street and 5th Avenue. Originally an actual
arsenal, it now houses NYC Parks headquarters and a gallery.

Key features:
  - Large rectangular main body (~40m × 15m, H≈16m to parapet)
  - Central projecting octagonal tower (~5m across, 25m total height)
  - Crenellated battlements along roofline and tower
  - Gothic pointed-arch windows (3 rows, ground floor larger)
  - Central entrance with brownstone pointed-arch surround
  - Brownstone quoin corners and belt courses
  - Two smaller flanking projections at east facade corners

Origin at ground center of main body footprint.
Exports to models/furniture/cp_arsenal.glb
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

brick      = make_mat("Brick",      (0.55, 0.25, 0.18), 0.88)
brownstone = make_mat("Brownstone", (0.50, 0.38, 0.28), 0.85)
slate_roof = make_mat("SlateRoof",  (0.30, 0.30, 0.32), 0.80)
window_mat = make_mat("Window",     (0.12, 0.14, 0.18), 0.30, 0.05)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Box centered at (cx, cy, cz) with half-extents (hx, hy, hz)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cylinder(name, cx, cy, cz_bottom, radius, height, mat, segments=16):
    """Upright cylinder, bottom at cz_bottom."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, vertices=segments,
        location=(cx, cy, cz_bottom + height / 2.0))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ════════════════════════════════════════════
# DIMENSIONS
# ════════════════════════════════════════════
# Main body
BW = 40.0     # building width (X)
BD = 15.0     # building depth (Y, east–west)
BH = 16.0     # wall height to parapet base
T  = 0.6      # wall thickness

HBW = BW / 2.0
HBD = BD / 2.0

# Tower (central, projects slightly from east/front face)
TW = 5.0      # tower footprint width (X)
TD = 5.5      # tower footprint depth (Y) — projects ~1m in front of facade
TH_WALL = 22.0  # tower wall height (above ground)
TH_BATT = 1.8   # battlement height on tower
TOWER_CX = 0.0  # centered on building
TOWER_CY = -HBD  # flush with front (east) face, projects outward

# Battlements
MERLON_W = 0.60
MERLON_H = 1.20
CRENEL_W = 0.50

# Belt courses (horizontal brownstone bands)
BELT1_Z = 5.8   # top of ground-floor window zone
BELT2_Z = 11.2  # top of first-upper-floor window zone

# ════════════════════════════════════════════
# 1. MAIN BODY — brick walls
# ════════════════════════════════════════════

# Full solid box for body, then brownstone details layered on top
box("body", 0, 0, BH / 2, HBW, HBD, BH / 2, brick)

# ════════════════════════════════════════════
# 2. BROWNSTONE QUOIN CORNERS
# ════════════════════════════════════════════
QUOIN_W = 0.55
QUOIN_D = 0.55

for (sx, sy) in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
    cx = sx * (HBW - QUOIN_W / 2)
    cy = sy * (HBD - QUOIN_D / 2)
    box(f"quoin_{sx}_{sy}", cx, cy, BH / 2,
        QUOIN_W / 2, QUOIN_D / 2, BH / 2, brownstone)

# ════════════════════════════════════════════
# 3. BROWNSTONE BELT COURSES
# ════════════════════════════════════════════
BELT_H = 0.30
BELT_PROJ = 0.08  # projection beyond wall face

for belt_z in (BELT1_Z, BELT2_Z):
    # Front + back
    for sy in (-1, 1):
        box(f"belt_fb_{belt_z}_{sy}", 0, sy * (HBD + BELT_PROJ / 2), belt_z,
            HBW + BELT_PROJ, BELT_H / 2 + BELT_PROJ / 2, BELT_H / 2, brownstone)
    # Side walls
    for sx in (-1, 1):
        box(f"belt_side_{belt_z}_{sx}", sx * (HBW + BELT_PROJ / 2), 0, belt_z,
            BELT_H / 2 + BELT_PROJ / 2, HBD + BELT_PROJ, BELT_H / 2, brownstone)

# ════════════════════════════════════════════
# 4. WINDOW INDICATIONS — recessed darker strips
# ════════════════════════════════════════════
# Gothic pointed-arch windows approximated as dark recessed strips.
# Three rows: ground (taller), 1st upper (narrower), 2nd upper (narrowest).
# Only the front (east, Y-negative) and rear (Y-positive) faces shown.

WIN_ROWS = [
    # (row_z_center, win_h, win_w, label)
    (3.2,  4.0, 1.4, "gnd"),
    (8.5,  3.2, 1.1, "up1"),
    (13.5, 2.6, 0.9, "up2"),
]
WIN_DEPTH = 0.12   # recess depth
WIN_SPACING_X = 4.0  # bay spacing along facade

num_bays = 9   # windows across 40m facade

for row_z, wh, ww, lbl in WIN_ROWS:
    for i in range(num_bays):
        wx = -HBW + WIN_SPACING_X * (i + 0.5) + 0.5
        if wx > HBW - 0.5:
            continue
        # Front face windows
        box(f"win_front_{lbl}_{i}", wx, -(HBD + WIN_DEPTH / 2), row_z,
            ww / 2, WIN_DEPTH / 2, wh / 2, window_mat)
        # Rear face windows (fewer, same pattern)
        box(f"win_rear_{lbl}_{i}", wx, (HBD + WIN_DEPTH / 2), row_z,
            ww / 2, WIN_DEPTH / 2, wh / 2, window_mat)

# Side wall windows (fewer — 3 bays on 15m depth)
SIDE_WIN_ROWS = [
    (3.2, 4.0, 1.4, "gnd"),
    (8.5, 3.2, 1.1, "up1"),
    (13.5, 2.6, 0.9, "up2"),
]
SIDE_WIN_X = [-5.0, 0.0, 5.0]

for row_z, wh, ww, lbl in SIDE_WIN_ROWS:
    for j, wy_off in enumerate(SIDE_WIN_X):
        for sx in (-1, 1):
            box(f"win_side_{lbl}_{j}_{sx}",
                sx * (HBW + WIN_DEPTH / 2), wy_off, row_z,
                WIN_DEPTH / 2, ww / 2, wh / 2, window_mat)

# ════════════════════════════════════════════
# 5. MAIN ENTRANCE — brownstone pointed-arch surround
# ════════════════════════════════════════════
# Entrance centered on front face, between tower legs
DOOR_W   = 3.0
DOOR_H   = 5.5
ARCH_T   = 0.45   # arch surround thickness
ENTRY_Y  = -(HBD + ARCH_T / 2)

# Arch left + right jambs
for sx in (-1, 1):
    box(f"arch_jamb_{sx}", sx * (DOOR_W / 2 + ARCH_T / 2), ENTRY_Y, DOOR_H / 2,
        ARCH_T / 2, ARCH_T / 2, DOOR_H / 2, brownstone)

# Arch head (horizontal lintel portion)
box("arch_head", 0, ENTRY_Y, DOOR_H + ARCH_T / 2,
    DOOR_W / 2 + ARCH_T, ARCH_T / 2, ARCH_T / 2, brownstone)

# Arch pointed-top triangle (brownstone keystone block)
box("arch_apex", 0, ENTRY_Y, DOOR_H + ARCH_T + 0.6,
    ARCH_T * 0.8, ARCH_T / 2, 0.65, brownstone)

# Entrance door recess (dark)
box("door_recess", 0, -(HBD + 0.08), DOOR_H / 2,
    DOOR_W / 2, 0.10, DOOR_H / 2, window_mat)

# Entry stoop — brownstone steps (3 steps)
for s in range(3):
    sw = DOOR_W / 2 + 1.2 - s * 0.35
    sy = -(HBD + 0.25 + s * 0.45)
    sz = s * 0.18 + 0.09
    box(f"stoop_{s}", 0, sy, sz, sw, 0.22, 0.09, brownstone)

# ════════════════════════════════════════════
# 6. CORNER TURRET PROJECTIONS
# ════════════════════════════════════════════
# Small flanking square buttress projections at front corners
BUTT_W = 2.5
BUTT_D = 1.5
BUTT_H = BH + 0.5   # slightly above main parapet

for sx in (-1, 1):
    cx = sx * (HBW - BUTT_W / 2)
    cy = -(HBD - BUTT_D / 2)
    box(f"buttress_{sx}", cx, cy, BUTT_H / 2,
        BUTT_W / 2, BUTT_D / 2, BUTT_H / 2, brick)
    # Brownstone cap
    box(f"butt_cap_{sx}", cx, cy, BUTT_H + 0.15,
        BUTT_W / 2 + 0.08, BUTT_D / 2 + 0.08, 0.18, brownstone)
    # Two small battlements on buttress
    for bm in (-1, 1):
        box(f"butt_mlon_{sx}_{bm}",
            cx + bm * BUTT_W * 0.3, cy, BUTT_H + 0.15 + MERLON_H / 2,
            MERLON_W / 2, BUTT_D / 2 + 0.05, MERLON_H / 2, brick)

# ════════════════════════════════════════════
# 7. MAIN PARAPET BATTLEMENTS
# ════════════════════════════════════════════
# Front parapet (east face, Y-negative)
front_merlon_step = MERLON_W + CRENEL_W
n_front = int(BW / front_merlon_step)
front_step_actual = BW / n_front

for i in range(n_front):
    mx = -HBW + (i + 0.5) * front_step_actual
    box(f"par_front_{i}", mx, -(HBD - MERLON_W / 2), BH + MERLON_H / 2,
        MERLON_W / 2, MERLON_W / 2, MERLON_H / 2, brick)

# Rear parapet (west face, Y-positive)
for i in range(n_front):
    mx = -HBW + (i + 0.5) * front_step_actual
    box(f"par_rear_{i}", mx, (HBD - MERLON_W / 2), BH + MERLON_H / 2,
        MERLON_W / 2, MERLON_W / 2, MERLON_H / 2, brick)

# Side parapets
n_side = int(BD / front_merlon_step)
side_step_actual = BD / max(n_side, 1)

for i in range(n_side):
    my = -HBD + (i + 0.5) * side_step_actual
    for sx in (-1, 1):
        box(f"par_side_{sx}_{i}", sx * (HBW - MERLON_W / 2), my, BH + MERLON_H / 2,
            MERLON_W / 2, MERLON_W / 2, MERLON_H / 2, brick)

# Parapet base course (thin brownstone rail)
PBASE_H = 0.25
for sy in (-1, 1):
    box(f"par_base_fb_{sy}", 0, sy * (HBD - 0.08), BH + PBASE_H / 2,
        HBW, 0.14, PBASE_H / 2, brownstone)
for sx in (-1, 1):
    box(f"par_base_side_{sx}", sx * (HBW - 0.08), 0, BH + PBASE_H / 2,
        0.14, HBD, PBASE_H / 2, brownstone)

# ════════════════════════════════════════════
# 8. CENTRAL OCTAGONAL TOWER
# ════════════════════════════════════════════
# The tower sits centered on the front (east) face, projecting ~1m out.
# Approximated as an octagonal prism using cylinder with 8 vertices.

TOWER_PROJ = 1.0   # how far tower projects south of main wall
tower_cy = -(HBD + TOWER_PROJ / 2)   # center Y of tower footprint

# Tower body — octagonal cylinder
cylinder("tower_body", TOWER_CX, tower_cy, 0, TW / 2, TH_WALL, brick, 8)

# Tower brownstone belt courses at same heights as main building
for belt_z in (BELT1_Z, BELT2_Z):
    cylinder(f"tower_belt_{belt_z}", TOWER_CX, tower_cy, belt_z - BELT_H / 2,
             TW / 2 + BELT_PROJ + 0.05, BELT_H, brownstone, 8)

# Tower windows — narrow Gothic slits on 3 faces (front + flanking 45° faces)
# Approximated as thin dark recessed strips on the outer octagon surface
TWin_ANGLES = [0, math.pi / 4, -math.pi / 4]  # front and diagonals facing east
TWin_R = TW / 2 + 0.05

for row_z, wh, ww, lbl in WIN_ROWS:
    for ai, ang in enumerate(TWin_ANGLES):
        wx = TOWER_CX + math.sin(ang) * TWin_R
        wy = tower_cy - math.cos(ang) * TWin_R
        # window strip faces outward — use a thin box oriented outward
        nx = math.sin(ang)
        ny = -math.cos(ang)
        box(f"tower_win_{lbl}_{ai}",
            wx + nx * WIN_DEPTH / 2,
            wy + ny * WIN_DEPTH / 2,
            row_z,
            max(abs(ny) * ww / 2 + abs(nx) * WIN_DEPTH / 2, 0.05),
            max(abs(nx) * ww / 2 + abs(ny) * WIN_DEPTH / 2, 0.05),
            wh / 2,
            window_mat)

# Tower parapet base ring
cylinder("tower_par_base", TOWER_CX, tower_cy, TH_WALL,
         TW / 2 + 0.12, 0.28, brownstone, 8)

# Tower battlements — 8 merlons (one per octagon face)
N_OCT = 8
for i in range(N_OCT):
    ang = 2.0 * math.pi * i / N_OCT
    mx = TOWER_CX + math.sin(ang) * (TW / 2 + 0.05)
    my = tower_cy - math.cos(ang) * (TW / 2 + 0.05)
    box(f"tower_merlon_{i}", mx, my, TH_WALL + TH_BATT / 2,
        MERLON_W / 2, MERLON_W / 2, TH_BATT / 2, brick)

# Tower conical cap (slate)
cone_base_r = TW / 2 + 0.20
cone_h = 3.0
cone_z = TH_WALL + TH_BATT * 0.4   # rises from inside battlements
cone_verts = []
cone_faces = []
N_CONE = 8
for i in range(N_CONE):
    ang = 2.0 * math.pi * i / N_CONE
    cone_verts.append((
        TOWER_CX + math.cos(ang) * cone_base_r,
        tower_cy + math.sin(ang) * cone_base_r,
        cone_z
    ))
cone_verts.append((TOWER_CX, tower_cy, cone_z + cone_h))
apex_i = len(cone_verts) - 1
for i in range(N_CONE):
    cone_faces.append((i, (i + 1) % N_CONE, apex_i))
cone_faces.append(list(range(N_CONE)))

cmesh = bpy.data.meshes.new("tower_cone_mesh")
cmesh.from_pydata(cone_verts, [], cone_faces)
cmesh.update()
cobj = bpy.data.objects.new("TowerCone", cmesh)
bpy.context.collection.objects.link(cobj)
cobj.data.materials.append(slate_roof)
all_parts.append(cobj)

# ════════════════════════════════════════════
# 9. MAIN ROOF — low pitch gable (barely visible behind parapet)
# ════════════════════════════════════════════
ROOF_RISE = 1.8
OVH = 0.0   # no overhang (hidden behind parapet)
roof_z = BH

roof_verts = [
    (-HBW, -HBD, roof_z),          # 0 front-left
    ( HBW, -HBD, roof_z),          # 1 front-right
    ( HBW,  HBD, roof_z),          # 2 rear-right
    (-HBW,  HBD, roof_z),          # 3 rear-left
    (-HBW,  0,   roof_z + ROOF_RISE),  # 4 left ridge
    ( HBW,  0,   roof_z + ROOF_RISE),  # 5 right ridge
]
roof_faces = [
    (0, 1, 5, 4),   # front slope
    (3, 2, 5, 4),   # rear slope (note winding)
    (0, 3, 4),      # west gable
    (1, 2, 5),      # east gable
    (0, 1, 2, 3),   # soffit
]
rmesh = bpy.data.meshes.new("roof_mesh")
rmesh.from_pydata(roof_verts, [], roof_faces)
rmesh.update()
robj = bpy.data.objects.new("MainRoof", rmesh)
bpy.context.collection.objects.link(robj)
robj.data.materials.append(slate_roof)
all_parts.append(robj)

# ════════════════════════════════════════════
# 10. FOUNDATION COURSE
# ════════════════════════════════════════════
box("foundation", 0, 0, -0.25,
    HBW + 0.15, HBD + 0.15, 0.30, brownstone)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

arsenal = bpy.context.active_object
arsenal.name = "Arsenal"

# Origin at ground center
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_arsenal.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Arsenal to {out_path}")
print(f"  Vertices: {len(arsenal.data.vertices)}")
print(f"  Faces: {len(arsenal.data.polygons)}")

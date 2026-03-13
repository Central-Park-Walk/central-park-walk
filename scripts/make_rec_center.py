"""Generate the North Meadow Recreation Center for Central Park Walk.

The North Meadow Recreation Center (c. 1990s) sits at 97th Street in the
park's northern section, serving as a recreational facility with equipment
storage, restrooms, and staff offices. A modest, functional single-story
brick building characteristic of late-20th-century NYC Parks design.

Key features:
  - Rectangular building ~25m × 12m
  - Single story, H=4.5m to parapet top
  - Red brick with concrete base course and parapet cap
  - Flat roof with low parapet
  - South face: 5 glazed bays (large windows + glass entrance doors)
  - Main entrance: central bay with projecting concrete canopy
  - North face: utility door + single window
  - Concrete band course at lintel level
  - Concrete pilasters between window bays

Origin at ground center.
Exports to models/furniture/cp_rec_center.glb
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

brick    = make_mat("Brick",    (0.52, 0.28, 0.20), 0.88)
concrete = make_mat("Concrete", (0.60, 0.58, 0.55), 0.85)
glass    = make_mat("Glass",    (0.30, 0.35, 0.40), 0.20, 0.1)

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
W      = 25.0    # length (X)
D      = 12.0    # depth (Y)
H_WALL = 3.80    # brick wall height (to top of wall, below parapet)
H_PAR  = 4.50    # total height including parapet cap
WALL_T = 0.35    # wall thickness
PAR_T  = 0.45    # parapet thickness (slightly thicker than wall)
PAR_H  = H_PAR - H_WALL   # parapet height (0.70m)
BASE_H = 0.35    # concrete base course height
BAND_H = 0.18    # concrete lintel band height

hw = W / 2.0
hd = D / 2.0

# ════════════════════════════════════════════
# 1. CONCRETE BASE COURSE
# Runs around full perimeter, slightly proud of wall face
# ════════════════════════════════════════════
box("base_front", 0,  hd, BASE_H / 2, hw + 0.06, WALL_T/2 + 0.06, BASE_H/2, concrete)
box("base_back",  0, -hd, BASE_H / 2, hw + 0.06, WALL_T/2 + 0.06, BASE_H/2, concrete)
box("base_east", -hw, 0,  BASE_H / 2, WALL_T/2 + 0.06, hd + 0.06, BASE_H/2, concrete)
box("base_west",  hw, 0,  BASE_H / 2, WALL_T/2 + 0.06, hd + 0.06, BASE_H/2, concrete)

# ════════════════════════════════════════════
# 2. MAIN BRICK WALLS
# Four walls, full height from base course to wall top
# ════════════════════════════════════════════
WALL_Z0 = BASE_H
WALL_MID = WALL_Z0 + (H_WALL - WALL_Z0) / 2.0
WALL_HH  = (H_WALL - WALL_Z0) / 2.0   # half-height of brick wall above base

# South wall (front, +Y) — will be subdivided by window bays below
box("wall_south", 0, hd - WALL_T/2, WALL_MID, hw, WALL_T/2, WALL_HH, brick)

# North wall (back, -Y)
box("wall_north", 0, -hd + WALL_T/2, WALL_MID, hw, WALL_T/2, WALL_HH, brick)

# East wall (-X)
box("wall_east", -hw + WALL_T/2, 0, WALL_MID, WALL_T/2, hd, WALL_HH, brick)

# West wall (+X)
box("wall_west",  hw - WALL_T/2, 0, WALL_MID, WALL_T/2, hd, WALL_HH, brick)

# ════════════════════════════════════════════
# 3. FLAT ROOF DECK (concrete slab)
# ════════════════════════════════════════════
box("roof_deck", 0, 0, H_WALL + 0.08, hw, hd, 0.10, concrete)

# ════════════════════════════════════════════
# 4. PARAPET — runs around all four sides, proud of roof
# Low wall above the main wall, capped with thicker concrete cap
# ════════════════════════════════════════════
PAR_BASE = H_WALL
PAR_MID  = PAR_BASE + PAR_H / 2.0

# Parapet walls (same footprint as main walls)
box("par_south", 0,  hd - PAR_T/2, PAR_MID, hw + PAR_T, PAR_T/2, PAR_H/2, brick)
box("par_north", 0, -hd + PAR_T/2, PAR_MID, hw + PAR_T, PAR_T/2, PAR_H/2, brick)
box("par_east", -hw + PAR_T/2, 0,  PAR_MID, PAR_T/2, hd, PAR_H/2, brick)
box("par_west",  hw - PAR_T/2, 0,  PAR_MID, PAR_T/2, hd, PAR_H/2, brick)

# Parapet cap (concrete coping, overhangs parapet on both sides by 50mm)
CAP_Z = H_PAR + 0.05
box("cap_south", 0,  hd, CAP_Z, hw + PAR_T + 0.05, PAR_T/2 + 0.05, 0.07, concrete)
box("cap_north", 0, -hd, CAP_Z, hw + PAR_T + 0.05, PAR_T/2 + 0.05, 0.07, concrete)
box("cap_east", -hw, 0,  CAP_Z, PAR_T/2 + 0.05, hd + PAR_T/2 + 0.05, 0.07, concrete)
box("cap_west",  hw, 0,  CAP_Z, PAR_T/2 + 0.05, hd + PAR_T/2 + 0.05, 0.07, concrete)

# ════════════════════════════════════════════
# 5. SOUTH FACADE — 5 glazed bays
#
# Bay layout (25m wide, 5 bays):
#   bay 0 (west end): fixed window
#   bay 1: fixed window
#   bay 2 (centre): entrance double-door + sidelight panels
#   bay 3: fixed window
#   bay 4 (east end): fixed window
#
# Each bay ~4.0m wide with 0.5m concrete pilasters between bays
# ════════════════════════════════════════════

N_BAYS    = 5
PILASTER_W = 0.50   # concrete pilasters between bays (X width)
PILASTER_D = 0.12   # projection depth beyond wall face
CORNER_W   = 0.60   # wider corner pilasters
DOOR_W     = 1.80   # entrance double-door width (used by bay loop + canopy step)

# Available span for glazing after corners and pilasters
# Corners: 2 × 0.60 = 1.20m
# Pilasters: 4 × 0.50 = 2.00m
# Remaining for 5 bays: 25.0 - 1.20 - 2.00 = 21.80m → 21.80 / 5 = 4.36m per bay
INNER_SPAN = W - 2 * CORNER_W - (N_BAYS - 1) * PILASTER_W
BAY_W = INNER_SPAN / N_BAYS   # ~4.36m per bay

WIN_H     = 2.20   # window/door height (from base course top to lintel band)
WIN_INSET = 0.06   # glass set back from wall face
WIN_Z     = WALL_Z0 + WIN_H / 2.0   # window centre height

LINTEL_Z  = WALL_Z0 + WIN_H          # underside of lintel band
LINTEL_MID = LINTEL_Z + BAND_H / 2.0

# Lintel/band course across full south face — concrete strip at head height
box("lintel_band_s", 0, hd, LINTEL_MID,
    hw, WALL_T/2 + PILASTER_D + 0.02, BAND_H/2, concrete)

# Corner pilasters (south face, full height from base to parapet)
FULL_H_MID = (H_WALL + BASE_H) / 2.0
FULL_HH    = (H_WALL - BASE_H) / 2.0
for sx, name in [(-1, "sw"), (1, "se")]:
    px = sx * (hw - CORNER_W / 2.0)
    box(f"pilaster_corner_{name}", px, hd, FULL_H_MID,
        CORNER_W/2, WALL_T/2 + PILASTER_D, FULL_HH, concrete)

# Bay pilasters (between bays)
for i in range(N_BAYS - 1):
    px = -hw + CORNER_W + BAY_W + i * (BAY_W + PILASTER_W) + PILASTER_W / 2.0
    box(f"pilaster_bay_{i}", px, hd, FULL_H_MID,
        PILASTER_W/2, WALL_T/2 + PILASTER_D, FULL_HH, concrete)

# Bay centres
bay_centers = []
for i in range(N_BAYS):
    cx = -hw + CORNER_W + BAY_W/2.0 + i * (BAY_W + PILASTER_W)
    bay_centers.append(cx)

# Glass panels and brick spandrels for each bay
for i, bx in enumerate(bay_centers):
    is_entrance = (i == 2)   # centre bay is entrance

    if is_entrance:
        # Entrance: two narrow sidelight panels + central door opening
        SIDE_W  = (BAY_W - DOOR_W) / 2.0 - 0.04

        # Sidelight glass (left and right of door)
        for side, sign in [("l", -1), ("r", 1)]:
            sx = bx + sign * (DOOR_W/2.0 + SIDE_W/2.0 + 0.02)
            box(f"sidelight_{side}", sx, hd - WIN_INSET, WIN_Z,
                SIDE_W/2, 0.04, WIN_H/2, glass)
            # Thin concrete mullion framing each sidelight
            box(f"sidelight_frame_{side}", sx, hd, WIN_Z,
                SIDE_W/2 + 0.04, WALL_T/2 + 0.02, WIN_H/2 + 0.02, concrete)

        # Door opening glass (two panels)
        for side, sign in [("dl", -1), ("dr", 1)]:
            sx = bx + sign * DOOR_W / 4.0
            box(f"door_glass_{side}", sx, hd - WIN_INSET, WIN_Z,
                DOOR_W/4.0 - 0.04, 0.04, WIN_H/2, glass)

        # Door frame surround
        box("door_frame", bx, hd, WIN_Z,
            DOOR_W/2 + 0.06, WALL_T/2 + 0.04, WIN_H/2 + 0.04, concrete)

    else:
        # Standard fixed window — full bay width, recessed glass
        WIN_W_BAY = BAY_W - 0.20   # slight margin inside pilasters
        box(f"win_glass_{i}", bx, hd - WIN_INSET, WIN_Z,
            WIN_W_BAY/2, 0.04, WIN_H/2, glass)
        # Window frame (concrete surround, flush with pilasters)
        box(f"win_frame_{i}", bx, hd, WIN_Z,
            WIN_W_BAY/2 + 0.06, WALL_T/2 + 0.02, WIN_H/2 + 0.04, concrete)

    # Brick spandrel above each bay (from lintel band to parapet)
    SPAN_H = PAR_BASE - LINTEL_Z - BAND_H
    if SPAN_H > 0.01:
        box(f"spandrel_{i}", bx, hd - WALL_T/2,
            LINTEL_Z + BAND_H + SPAN_H/2,
            BAY_W/2, WALL_T/2, SPAN_H/2, brick)

# ════════════════════════════════════════════
# 6. MAIN ENTRANCE CANOPY
# Projecting flat concrete slab on two square posts
# Centred on bay 2 (entrance bay), projects 1.8m south
# ════════════════════════════════════════════
CANOPY_W    = BAY_W + 1.0   # 1.0m wider than door bay on each side
CANOPY_D    = 1.80          # projection depth (Y)
CANOPY_Z    = WIN_H + WALL_Z0 + 0.12   # underside at ~head height + clearance
CANOPY_SLAB = 0.18          # slab thickness
CANOPY_Y    = hd + CANOPY_D / 2.0
POST_H      = CANOPY_Z      # post height from grade to underside of slab

# Slab
box("canopy_slab", bay_centers[2], CANOPY_Y,
    CANOPY_Z + CANOPY_SLAB/2,
    CANOPY_W/2, CANOPY_D/2, CANOPY_SLAB/2, concrete)

# Two square posts (0.25m × 0.25m)
for side, sign in [("l", -1), ("r", 1)]:
    px = bay_centers[2] + sign * (CANOPY_W/2 - 0.20)
    box(f"canopy_post_{side}", px, hd + CANOPY_D - 0.20,
        POST_H / 2,
        0.125, 0.125, POST_H/2, concrete)

# Canopy soffit edge beam (forward face of slab, slightly thicker look)
box("canopy_fascia", bay_centers[2], hd + CANOPY_D,
    CANOPY_Z + CANOPY_SLAB/2,
    CANOPY_W/2, 0.06, CANOPY_SLAB/2 + 0.04, concrete)

# Small concrete step at entrance
box("entrance_step", bay_centers[2], hd + 0.55, 0.10,
    DOOR_W/2 + 0.30, 0.50, 0.12, concrete)

# ════════════════════════════════════════════
# 7. NORTH FACE — utility door + single window
# ════════════════════════════════════════════
UTIL_DOOR_W  = 1.10
UTIL_DOOR_H  = 2.20
UTIL_DOOR_Z  = WALL_Z0 + UTIL_DOOR_H / 2.0
UTIL_DOOR_CX = -hw * 0.40   # offset west of centre

UTIL_WIN_W  = 0.90
UTIL_WIN_H  = 1.20
UTIL_WIN_Z  = WALL_Z0 + UTIL_WIN_H / 2.0 + 0.60   # higher sill
UTIL_WIN_CX =  hw * 0.30   # offset east of centre

# Lintel band on north face
box("lintel_band_n", 0, -hd, LINTEL_MID,
    hw, WALL_T/2 + 0.02, BAND_H/2, concrete)

# Utility door: dark recessed fill to suggest a solid panel door
box("util_door_fill", UTIL_DOOR_CX, -hd, UTIL_DOOR_Z,
    UTIL_DOOR_W/2, WIN_INSET, UTIL_DOOR_H/2, glass)
# Door frame
box("util_door_frame", UTIL_DOOR_CX, -hd, UTIL_DOOR_Z,
    UTIL_DOOR_W/2 + 0.06, WALL_T/2 + 0.04, UTIL_DOOR_H/2 + 0.04, concrete)

# Utility window
box("util_win_glass", UTIL_WIN_CX, -hd + WIN_INSET, UTIL_WIN_Z,
    UTIL_WIN_W/2, 0.04, UTIL_WIN_H/2, glass)
box("util_win_frame", UTIL_WIN_CX, -hd, UTIL_WIN_Z,
    UTIL_WIN_W/2 + 0.06, WALL_T/2 + 0.02, UTIL_WIN_H/2 + 0.04, concrete)

# ════════════════════════════════════════════
# 8. EAST AND WEST END WALLS
# Solid brick, no openings — with concrete corner pilasters
# ════════════════════════════════════════════
END_CORNER_W = 0.55
for sx, name in [(-1, "east"), (1, "west")]:
    px = sx * hw
    for sy, cy_off in [(-1, -hd), (1, hd)]:
        # Corner column running full height
        box(f"end_col_{name}_{sy}", px, cy_off, FULL_H_MID,
            WALL_T/2 + PILASTER_D, END_CORNER_W/2, FULL_HH, concrete)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "NorthMeadowRecCenter"

# Origin at ground center
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_rec_center.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported North Meadow Recreation Center to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

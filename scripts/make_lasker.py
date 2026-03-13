"""Generate Lasker Rink/Pool for Central Park Walk.

Lasker Rink (1966, demolished 2021, rebuilding as Lasker Pool) stood at the
north end of Central Park between 106th and 108th Streets.  The classic 1966
Kahn & Jacobs modernist concrete facility is modelled here for the historical
period.

Key features:
  - Large rectangular concrete enclosure ~60m × 30m, wall height ~4m
  - Low-profile modernist design with flat roof and expressed concrete block
  - Mechanical/plant housing on roof (north end), ~20m × 6m × 2m
  - Entry/skate-rental building on east side, ~15m × 8m × 5m (slightly taller)
  - Open spectator terrace on south side with low parapet + guardrail posts
  - Dark trim bands at top of walls
  - Chain-link perimeter fence represented as thin metal posts + top rail

Origin at ground center of the main enclosure.
Exports to models/furniture/cp_lasker.glb
"""

import bpy
import math
import os

# ── Clear scene ──────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ── Materials ─────────────────────────────────────────────────────────────────
def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

concrete  = make_mat("Concrete",  (0.60, 0.58, 0.55), 0.90)
dark_trim = make_mat("DarkTrim",  (0.25, 0.25, 0.24), 0.75)
metal     = make_mat("Metal",     (0.40, 0.40, 0.38), 0.65, 0.3)
floor_mat = make_mat("Floor",     (0.50, 0.50, 0.48), 0.92)   # interior floor slab

all_parts = []

# ── Helpers ───────────────────────────────────────────────────────────────────
def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Place a box centred at (cx,cy,cz) with half-extents (hx,hy,hz)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cyl(name, cx, cy, cz, radius, depth, verts=12, mat=None):
    """Place an upright cylinder centred at (cx,cy,cz)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=verts,
        location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Dimensions ────────────────────────────────────────────────────────────────
ENC_X = 30.0     # half-length (60 m total, E-W)
ENC_Y = 15.0     # half-width  (30 m total, N-S)
WALL_H = 4.0     # main enclosure wall height
WALL_T = 0.40    # wall thickness

# Trim band at top of walls
TRIM_H = 0.30

# ════════════════════════════════════════════════════════════════════════════
# 1. MAIN ENCLOSURE — four concrete walls
# ════════════════════════════════════════════════════════════════════════════

# South wall (open spectator side — full wall with lower section to terrace)
box("wall_south", 0, -ENC_Y + WALL_T/2, WALL_H/2,
    ENC_X, WALL_T/2, WALL_H/2, concrete)
# North wall
box("wall_north", 0,  ENC_Y - WALL_T/2, WALL_H/2,
    ENC_X, WALL_T/2, WALL_H/2, concrete)
# West wall
box("wall_west", -ENC_X + WALL_T/2, 0, WALL_H/2,
    WALL_T/2, ENC_Y, WALL_H/2, concrete)
# East wall — interrupted by entry building; keep full wall, entry building sits outside
box("wall_east",  ENC_X - WALL_T/2, 0, WALL_H/2,
    WALL_T/2, ENC_Y, WALL_H/2, concrete)

# ── Dark trim band at top of all four walls ───────────────────────────────────
box("trim_south", 0, -ENC_Y + WALL_T/2, WALL_H + TRIM_H/2,
    ENC_X + WALL_T, WALL_T/2 + 0.02, TRIM_H/2, dark_trim)
box("trim_north", 0,  ENC_Y - WALL_T/2, WALL_H + TRIM_H/2,
    ENC_X + WALL_T, WALL_T/2 + 0.02, TRIM_H/2, dark_trim)
box("trim_west", -ENC_X + WALL_T/2, 0, WALL_H + TRIM_H/2,
    WALL_T/2 + 0.02, ENC_Y, TRIM_H/2, dark_trim)
box("trim_east",  ENC_X - WALL_T/2, 0, WALL_H + TRIM_H/2,
    WALL_T/2 + 0.02, ENC_Y, TRIM_H/2, dark_trim)

# ── Flat roof slab over main enclosure ───────────────────────────────────────
ROOF_Z = WALL_H + TRIM_H
box("roof_slab", 0, 0, ROOF_Z + 0.15,
    ENC_X, ENC_Y, 0.18, concrete)

# ── Interior floor slab ───────────────────────────────────────────────────────
box("floor_slab", 0, 0, 0.06,
    ENC_X - WALL_T, ENC_Y - WALL_T, 0.08, floor_mat)

# ── Horizontal mid-band (modernist concrete block coursing) ───────────────────
# A single recessed band halfway up the exterior of all walls
MID_Z = WALL_H * 0.45
MID_H = 0.12
box("band_south", 0, -ENC_Y - 0.01, MID_Z,
    ENC_X, 0.06, MID_H/2, dark_trim)
box("band_north", 0,  ENC_Y + 0.01, MID_Z,
    ENC_X, 0.06, MID_H/2, dark_trim)
box("band_west", -ENC_X - 0.01, 0, MID_Z,
    0.06, ENC_Y, MID_H/2, dark_trim)
box("band_east",  ENC_X + 0.01, 0, MID_Z,
    0.06, ENC_Y, MID_H/2, dark_trim)

# ════════════════════════════════════════════════════════════════════════════
# 2. MECHANICAL HOUSING — plant room on roof, north end
# ════════════════════════════════════════════════════════════════════════════
MECH_W = 10.0   # half-length
MECH_D = 3.0    # half-depth
MECH_H = 2.0    # full height above roof
mech_y = ENC_Y - MECH_D - 1.0    # north end of roof, setback 1 m from edge

box("mech_body",   0, mech_y, ROOF_Z + 0.30 + MECH_H/2,
    MECH_W, MECH_D, MECH_H/2, concrete)
box("mech_roof",   0, mech_y, ROOF_Z + 0.30 + MECH_H + 0.10,
    MECH_W + 0.15, MECH_D + 0.15, 0.12, dark_trim)

# Ventilation louvres (thin dark strips on face)
for i in range(4):
    lx = -MECH_W + 2.0 + i * (MECH_W * 2 - 3.0) / 3
    box(f"louvre_{i}", lx, mech_y - MECH_D - 0.01,
        ROOF_Z + 0.30 + MECH_H * 0.55,
        0.60, 0.04, MECH_H * 0.20, dark_trim)

# HVAC equipment on roof — two box units
box("hvac_unit_a", -5.0, mech_y + 0.5,
    ROOF_Z + 0.30 + MECH_H + 0.50,
    1.5, 1.0, 0.40, metal)
box("hvac_unit_b",  4.0, mech_y + 0.5,
    ROOF_Z + 0.30 + MECH_H + 0.50,
    1.0, 0.80, 0.35, metal)

# ════════════════════════════════════════════════════════════════════════════
# 3. ENTRY BUILDING — east side, slightly taller at 5 m
# ════════════════════════════════════════════════════════════════════════════
EB_W = 7.5    # half-width along E-W (outside enclosure)
EB_D = 4.0    # half-depth along N-S
EB_H = 5.0    # taller than main enclosure

eb_cx = ENC_X + EB_W + 0.10    # butts up against east wall

# Entry building body
box("entry_body", eb_cx, 0, EB_H/2,
    EB_W, EB_D, EB_H/2, concrete)

# Slightly raised flat roof with overhang
box("entry_roof", eb_cx, 0, EB_H + 0.20,
    EB_W + 0.50, EB_D + 0.50, 0.22, concrete)

# Dark trim band at top
box("entry_trim", eb_cx, 0, EB_H + 0.40 + TRIM_H/2,
    EB_W + 0.50, EB_D + 0.50, TRIM_H/2, dark_trim)

# Entrance canopy on east face — projecting slab
CANOPY_Z = 2.8
box("entry_canopy", eb_cx + EB_W, 0, CANOPY_Z + 0.12,
    1.20, 2.0, 0.14, concrete)

# Door opening — represented as a dark inset panel
box("entry_door_l", eb_cx + EB_W - 0.05, -1.0, 1.3,
    0.06, 0.50, 1.25, dark_trim)
box("entry_door_r", eb_cx + EB_W - 0.05,  1.0, 1.3,
    0.06, 0.50, 1.25, dark_trim)

# Horizontal window strip below trim band on east face
box("entry_windows", eb_cx + EB_W - 0.05, 0, EB_H * 0.68,
    0.06, EB_D - 0.60, EB_H * 0.10, dark_trim)

# Step at entry (east face of entry building)
box("entry_step", eb_cx + EB_W + 0.70, 0, 0.12,
    0.70, 1.80, 0.12, concrete)

# ════════════════════════════════════════════════════════════════════════════
# 4. SPECTATOR TERRACE — south side open area
# ════════════════════════════════════════════════════════════════════════════
TER_D = 5.0     # terrace depth (S of main enclosure)
TER_H = 0.60    # raised terrace slab

ter_y = -ENC_Y - TER_D/2

# Terrace slab
box("terrace_slab", 0, ter_y, TER_H/2,
    ENC_X - 2.0, TER_D/2, TER_H/2, concrete)

# Low parapet around three free edges of terrace
PAR_H = 1.10   # parapet height above terrace
PAR_T = 0.20

# Front parapet (south edge)
box("parapet_front", 0, ter_y - TER_D/2 + PAR_T/2, TER_H + PAR_H/2,
    ENC_X - 2.0, PAR_T/2, PAR_H/2, concrete)
# Left parapet (west edge)
box("parapet_left", -(ENC_X - 2.0) + PAR_T/2, ter_y, TER_H + PAR_H/2,
    PAR_T/2, TER_D/2, PAR_H/2, concrete)
# Right parapet (east edge — stops at entry building)
box("parapet_right",  (ENC_X - 2.0) - PAR_T/2, ter_y, TER_H + PAR_H/2,
    PAR_T/2, TER_D/2, PAR_H/2, concrete)

# Parapet dark cap
box("parapet_front_cap", 0, ter_y - TER_D/2 + PAR_T/2,
    TER_H + PAR_H + 0.08,
    ENC_X - 2.0 + PAR_T, PAR_T/2 + 0.02, 0.08, dark_trim)

# Terrace step down to grade (south face)
box("terrace_step", 0, ter_y - TER_D/2 - 0.25, 0.18,
    ENC_X - 2.0, 0.25, 0.18, concrete)

# ════════════════════════════════════════════════════════════════════════════
# 5. GUARDRAIL POSTS on terrace parapet top
# ════════════════════════════════════════════════════════════════════════════
# Thin metal posts every 2.5 m along front parapet
POST_H  = 0.90
POST_R  = 0.04
post_z  = TER_H + PAR_H + POST_H/2

n_posts = int((ENC_X - 2.0) / 2.5)
for i in range(-n_posts, n_posts + 1):
    px = i * 2.5
    cyl(f"post_front_{i}", px, ter_y - TER_D/2 + PAR_T/2,
        post_z, POST_R, POST_H, verts=6, mat=metal)

# Top rail connecting posts (front face)
box("rail_front", 0, ter_y - TER_D/2 + PAR_T/2, TER_H + PAR_H + POST_H - 0.04,
    ENC_X - 2.0, 0.03, 0.04, metal)

# ════════════════════════════════════════════════════════════════════════════
# 6. CHAIN-LINK FENCE — perimeter posts + top rail
#    Surrounds main enclosure on north/west/east sides; south replaced by terrace
# ════════════════════════════════════════════════════════════════════════════
FENCE_H  = 2.40
FENCE_R  = 0.04
FENCE_OFF = 2.0   # setback from building edge

# Post spacing
FENCE_STEP = 3.0

def fence_posts_line(x0, y0, x1, y1, prefix):
    """Place fence posts from (x0,y0) to (x1,y1)."""
    dx, dy = x1 - x0, y1 - y0
    length = math.sqrt(dx*dx + dy*dy)
    n = max(2, int(length / FENCE_STEP) + 1)
    for i in range(n):
        t = i / max(1, n - 1)
        px, py = x0 + t*dx, y0 + t*dy
        cyl(f"{prefix}_{i}", px, py, FENCE_H/2,
            FENCE_R, FENCE_H, verts=6, mat=metal)

fence_wx = -(ENC_X + FENCE_OFF)
fence_ex =  (ENC_X + FENCE_OFF)
fence_ny =  (ENC_Y + FENCE_OFF)
fence_sy = -(ENC_Y + FENCE_OFF)

# North fence
fence_posts_line(fence_wx, fence_ny, fence_ex, fence_ny, "fn")
box("rail_north", 0, fence_ny, FENCE_H + 0.04,
    ENC_X + FENCE_OFF, 0.04, 0.04, metal)

# West fence
fence_posts_line(fence_wx, fence_sy, fence_wx, fence_ny, "fw")
box("rail_west", fence_wx, 0, FENCE_H + 0.04,
    0.04, ENC_Y + FENCE_OFF, 0.04, metal)

# East fence (stops short where entry building is)
fence_posts_line(fence_ex, fence_sy, fence_ex, fence_ny, "fe")
box("rail_east", fence_ex, 0, FENCE_H + 0.04,
    0.04, ENC_Y + FENCE_OFF, 0.04, metal)

# South partial fence (corners only — terrace is the main element here)
fence_posts_line(fence_wx, fence_sy, -(ENC_X - 3.0), fence_sy, "fsl")
fence_posts_line( (ENC_X - 3.0), fence_sy, fence_ex, fence_sy, "fsr")

# ════════════════════════════════════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "LaskerRink"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_lasker.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB',
    use_selection=True, export_apply=True)
print(f"Exported Lasker Rink to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

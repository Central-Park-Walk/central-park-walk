"""Generate Vanderbilt Gate model for Central Park Walk.

The Vanderbilt Gate (1894, originally from the Cornelius Vanderbilt II
mansion at 5th Avenue & 58th Street) is the monumental wrought iron
entrance gate to the Conservatory Garden at East 105th Street.  It was
donated to the park in 1939.

Key features:
  - Two massive central piers (~1.2m × 1.2m × 5m tall) with decorative caps
  - Central double-gate opening (~4m wide × 4.5m tall)
  - Ornate wrought iron gate panels filling the central opening
  - Semicircular arched overthrow / transom spanning the two central piers
  - Two smaller flanking piers (~0.8m × 0.8m × 3.5m) on each side
  - Short ashlar walls connecting each flanking pier to the central piers
  - Total assembled width ~10m

Orientation: gate faces the +Y direction (south / street side).
Origin at ground centre of the full gate assembly.
Exports to models/furniture/cp_vanderbilt_gate.glb
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

granite   = make_mat("Granite",  (0.58, 0.55, 0.50), roughness=0.82)
iron      = make_mat("Iron",     (0.10, 0.10, 0.09), roughness=0.55, metallic=0.6)
cap_stone = make_mat("CapStone", (0.62, 0.58, 0.52), roughness=0.80)

# ── Helpers ───────────────────────────────────────────────────────────────────
all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Place a box centred at (cx,cy,cz) with half-extents (hx,hy,hz)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cyl(name, cx, cy, cz, radius, depth, verts, mat, rx=0.0, ry=0.0, rz=0.0):
    """Place a cylinder (Z-axis default) optionally rotated."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=verts,
        location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = (rx, ry, rz)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Dimensions ────────────────────────────────────────────────────────────────
# Central piers
CP_W  = 1.2    # pier width/depth (square)
CP_H  = 5.0    # pier height
# Central gate opening
GATE_W = 4.0   # clear opening width (X)
GATE_H = 4.5   # clear opening height (Z)
# Flanking piers
FP_W  = 0.8    # flanking pier width/depth
FP_H  = 3.5    # flanking pier height
# Connecting wall
WALL_L = 2.0   # wall length (X) between central and flanking piers
WALL_H = 2.8   # wall height
WALL_T = 0.35  # wall thickness (Y)
# Pier cap overhang
CAP_OVER = 0.08  # how much cap overhangs each side
# Arch overthrow
ARCH_R    = GATE_W / 2.0   # inner radius = half gate opening
ARCH_T    = 0.15           # arch bar thickness (cross-section half-extent)
ARCH_N    = 20             # number of arc segments (semicircle)
ARCH_DEPTH = 0.10          # depth of arch bars (Y half-extent)

# X positions of pier centres
# Gate opening spans -GATE_W/2 to +GATE_W/2
# Central piers sit immediately outside the opening
CX_INNER = GATE_W / 2.0 + CP_W / 2.0   # ±2.0 + 0.6 = ±2.6
# Flanking piers: wall connects to flanking, then flanking pier
FX_FLANK = CX_INNER + CP_W / 2.0 + WALL_L + FP_W / 2.0  # ±(2.6+0.6+2.0+0.4)=±5.6

# ════════════════════════════════════════════
# 1. CENTRAL PIERS (two)
# ════════════════════════════════════════════
for side in (-1, 1):
    px = side * CX_INNER
    box(f"central_pier_{side}", px, 0, CP_H / 2,
        CP_W / 2, CP_W / 2, CP_H / 2, granite)

# ════════════════════════════════════════════
# 2. CENTRAL PIER CAPS — wider slab + upper finial block
# ════════════════════════════════════════════
for side in (-1, 1):
    px = side * CX_INNER
    hw = CP_W / 2 + CAP_OVER
    # Lower cap slab
    box(f"cap_slab_{side}", px, 0, CP_H + 0.10,
        hw + 0.04, hw + 0.04, 0.10, cap_stone)
    # Upper decorative block (slightly smaller, bevelled feel via step)
    box(f"cap_block_{side}", px, 0, CP_H + 0.30,
        hw, hw, 0.10, cap_stone)
    # Top finial cube
    box(f"cap_finial_{side}", px, 0, CP_H + 0.55,
        0.14, 0.14, 0.15, cap_stone)

# ════════════════════════════════════════════
# 3. FLANKING PIERS (two, one each side)
# ════════════════════════════════════════════
for side in (-1, 1):
    fx = side * FX_FLANK
    box(f"flank_pier_{side}", fx, 0, FP_H / 2,
        FP_W / 2, FP_W / 2, FP_H / 2, granite)
    # Flanking pier cap
    fhw = FP_W / 2 + CAP_OVER
    box(f"flank_cap_slab_{side}", fx, 0, FP_H + 0.08,
        fhw + 0.03, fhw + 0.03, 0.08, cap_stone)
    box(f"flank_cap_block_{side}", fx, 0, FP_H + 0.22,
        fhw, fhw, 0.08, cap_stone)
    box(f"flank_cap_finial_{side}", fx, 0, FP_H + 0.38,
        0.10, 0.10, 0.10, cap_stone)

# ════════════════════════════════════════════
# 4. CONNECTING WALLS (ashlar, one each side)
# ════════════════════════════════════════════
# Wall spans from outer face of central pier to inner face of flanking pier
# Central pier outer face X: CX_INNER + CP_W/2
# Flanking pier inner face X: FX_FLANK - FP_W/2
# Wall centre X: midpoint of those two
for side in (-1, 1):
    inner_x = side * (CX_INNER + CP_W / 2)
    outer_x = side * (FX_FLANK - FP_W / 2)
    wall_cx = (inner_x + outer_x) / 2.0
    wall_hx = abs(outer_x - inner_x) / 2.0
    box(f"wall_{side}", wall_cx, 0, WALL_H / 2,
        wall_hx, WALL_T / 2, WALL_H / 2, granite)
    # Small coping on top of wall
    box(f"wall_coping_{side}", wall_cx, 0, WALL_H + 0.06,
        wall_hx + 0.05, WALL_T / 2 + 0.04, 0.06, cap_stone)

# ════════════════════════════════════════════
# 5. IRON GATE PANELS (two leaves filling central opening)
# ════════════════════════════════════════════
# Each leaf fills one half of the gate opening
panel_w  = GATE_W / 2.0  # half the opening
panel_h  = GATE_H
panel_t  = 0.06          # gate leaf thickness (thin iron)

for side in (-1, 1):
    px = side * panel_w / 2.0
    box(f"gate_panel_{side}", px, 0, panel_h / 2,
        panel_w / 2, panel_t / 2, panel_h / 2, iron)

# Vertical bars on each leaf (decorative representation)
BAR_W = 0.025   # bar half-width
BAR_SPACING = 0.18
N_BARS = int(panel_w / BAR_SPACING)
for side in (-1, 1):
    for i in range(N_BARS):
        bx = side * (BAR_SPACING * 0.5 + i * BAR_SPACING)
        if abs(bx) > GATE_W / 2 - BAR_W:
            continue
        box(f"bar_{side}_{i}", bx, 0.065, panel_h / 2,
            BAR_W, BAR_W, panel_h / 2, iron)

# Horizontal rails at top, middle, and bottom of each gate leaf
RAIL_H = 0.04
for side in (-1, 1):
    px = side * panel_w / 2.0
    for rail_z in (RAIL_H, panel_h * 0.45, panel_h - RAIL_H):
        box(f"rail_{side}_{int(rail_z*100)}", px, 0.065,
            rail_z, panel_w / 2, RAIL_H / 2, RAIL_H / 2, iron)

# ════════════════════════════════════════════
# 6. SEMICIRCULAR ARCH OVERTHROW
#    Built as a series of short rectangular segments following a
#    semicircle centred at (0, 0, GATE_H) with radius ARCH_R.
#    Each segment is a box positioned and rotated to follow the arc.
# ════════════════════════════════════════════
# The arch spans from angle 0 (right pier top) to pi (left pier top)
# Centre of the arch circle: (0, 0, GATE_H)
arch_cx_y  = 0.0          # Y position of arch (same plane as gate)
arch_cz    = GATE_H       # Z of arch circle centre

for i in range(ARCH_N):
    t0 = math.pi * i / ARCH_N
    t1 = math.pi * (i + 1) / ARCH_N
    tm = (t0 + t1) / 2.0

    # Midpoint position on the arc (inner surface radius)
    arc_x  = math.cos(tm) * ARCH_R
    arc_z  = arch_cz + math.sin(tm) * ARCH_R
    # Radial outward offset so the segment centre is at mid-thickness
    arc_x  = math.cos(tm) * (ARCH_R + ARCH_T)
    arc_z  = arch_cz + math.sin(tm) * (ARCH_R + ARCH_T)

    # Arc length for one segment (chord length)
    x0 = math.cos(t0) * ARCH_R
    z0 = arch_cz + math.sin(t0) * ARCH_R
    x1 = math.cos(t1) * ARCH_R
    z1 = arch_cz + math.sin(t1) * ARCH_R
    seg_len = math.sqrt((x1 - x0) ** 2 + (z1 - z0) ** 2)

    # Rotation around Y axis: tangent to arc in XZ plane
    # tangent direction angle (from +X axis, in XZ plane)
    tang_angle = tm + math.pi / 2.0   # perpendicular to radial
    # Blender: rotation_euler.y rotates in XZ plane (right-hand, CCW from +X toward -Z)
    # We want the segment's local X axis to follow the tangent.
    # rotation_euler = (0, -tm, 0) aligns local X along the tangent at angle tm
    rot_y = -(math.pi / 2.0 - tm)

    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(arc_x, arch_cx_y, arc_z))
    seg = bpy.context.active_object
    seg.name = f"arch_seg_{i}"
    seg.rotation_euler = (0, rot_y, 0)
    seg.scale = (seg_len / 2.0 + 0.02,   # slightly overlap to avoid gaps
                 ARCH_DEPTH,
                 ARCH_T)
    seg.data.materials.append(iron)
    all_parts.append(seg)

# Arch end collars — short horizontal bars connecting arch feet to pier tops
arch_foot_z  = GATE_H            # where the arch starts (at gate top height)
arch_foot_r  = ARCH_R + ARCH_T  # outer radius of arch at springing

for side in (-1, 1):
    collar_x = side * arch_foot_r
    # Collar bridges gap between arch foot and pier top edge
    collar_len = abs(collar_x) - (CX_INNER + CP_W / 2.0)
    if collar_len > 0.01:
        collar_cx = side * (CX_INNER + CP_W / 2.0 + collar_len / 2.0)
        box(f"arch_collar_{side}", collar_cx, 0, arch_foot_z,
            collar_len / 2.0, ARCH_DEPTH, ARCH_T, iron)

# ════════════════════════════════════════════
# 7. DECORATIVE SCROLLWORK — small acanthus-like volutes at arch
#    springing points (approximated as thin curved wedge boxes)
# ════════════════════════════════════════════
for side in (-1, 1):
    sx = side * CX_INNER
    # Volute base — small flat scroll at pier top
    box(f"volute_base_{side}", sx, 0, GATE_H + ARCH_T * 0.5,
        0.18, ARCH_DEPTH * 0.8, 0.12, iron)
    # Volute curl up
    box(f"volute_up_{side}", sx, 0, GATE_H + 0.30,
        0.10, ARCH_DEPTH * 0.6, 0.16, iron)

# ════════════════════════════════════════════
# 8. TOP RAIL above gate panels (iron cross-bar at gate top)
# ════════════════════════════════════════════
box("gate_top_rail", 0, 0, GATE_H,
    GATE_W / 2, ARCH_DEPTH, ARCH_T, iron)

# Small spike finials along the top rail
SPIKE_SPACING = 0.36
N_SPIKES = int(GATE_W / SPIKE_SPACING) - 1
for i in range(N_SPIKES):
    sx = -GATE_W / 2 + SPIKE_SPACING + i * SPIKE_SPACING
    cyl(f"spike_{i}", sx, 0, GATE_H + ARCH_T + 0.14,
        0.025, 0.28, 6, iron)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "VanderbiltGate"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_vanderbilt_gate.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Vanderbilt Gate to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces:    {len(obj.data.polygons)}")

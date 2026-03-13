"""Generate the Wisteria Pergola model for Central Park Walk.

The Wisteria Pergola is a long classical garden structure in the
North Garden (Italian Garden) of the Conservatory Garden, located
along the east side of the formal garden.  It supports wisteria
vines on its overhead beams and is a beloved feature of the garden.

Key features:
  - Long rectangular structure ~25m × 4m
  - Height ~3.5m (column tops at 3.0m, overhead beams add ~0.5m)
  - 12 paired Tuscan-style stone columns (24 total, two rows of 12)
  - Column diameter ~0.25m, height ~3.0m
  - Column base plinths and capital slabs
  - Stone cross-beams connecting each column pair across the 4m span
  - Longitudinal stone beams along the top connecting all cross-beams
  - Stone base/footing strips running the full length under each row
  - Open sides — classical garden pergola, not enclosed

Axis convention:
  - X runs along the long axis (25m), centred at 0
  - Y runs across the short axis (4m), centred at 0
  - Z is vertical, origin at ground level

Exports to models/furniture/cp_pergola.glb
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

stone = make_mat("Stone", (0.68, 0.64, 0.58), roughness=0.82)
beam  = make_mat("Beam",  (0.45, 0.38, 0.30), roughness=0.85)

# ── Helpers ───────────────────────────────────────────────────────────────────
all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Place a box centred at (cx, cy, cz) with half-extents (hx, hy, hz)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cyl(name, cx, cy, cz, radius, depth, verts, mat):
    """Place a vertical cylinder centred at (cx, cy, cz)."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, vertices=verts,
        location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# ── Dimensions ────────────────────────────────────────────────────────────────
LENGTH      = 25.0    # overall length along X
SPAN        = 4.0     # column-row separation along Y
N_COLS      = 12      # columns per row (12 each side = 24 total)
COL_R       = 0.125   # column radius (0.25m diameter)
COL_H       = 3.0     # column shaft height
COL_VERTS   = 16      # polygon count for column cylinders

# Column spacing along the long axis
# 12 columns span from one end to the other, so 11 gaps
COL_SPACING = LENGTH / (N_COLS - 1)   # ~2.27m spacing

# Footing strip
FOOT_H      = 0.15   # footing strip height
FOOT_W      = 0.55   # footing strip width (slightly wider than column base)

# Plinth (square base under each column)
PLINTH_W    = 0.30   # plinth half-width
PLINTH_H    = 0.20   # plinth height

# Capital slab (square top of each column)
CAP_W       = 0.28   # capital half-width
CAP_H       = 0.12   # capital slab height

# Cross-beams (connect paired columns across the 4m span)
XBEAM_W     = 0.18   # cross-beam width (Y direction, half-extent along X)
XBEAM_H     = 0.25   # cross-beam height (half-extent in Z)
XBEAM_OVER  = 0.20   # overhang beyond column centre on each end

# Longitudinal beams (run the full length along the top, two of them)
LBEAM_H     = 0.20   # longitudinal beam height (half-extent in Z)
LBEAM_W     = 0.12   # longitudinal beam width (half-extent in Y direction)

# Top of column shaft (Z)
COL_TOP_Z   = FOOT_H + PLINTH_H + COL_H   # = 3.35m

# Top of capital (Z at top face of capital slab, resting on column)
CAP_TOP_Z   = COL_TOP_Z + CAP_H           # = 3.47m

# Cross-beams sit on top of capitals
XBEAM_BOT_Z = CAP_TOP_Z
XBEAM_CZ    = XBEAM_BOT_Z + XBEAM_H      # centre Z of cross-beam

# Longitudinal beams sit on top of cross-beams
LBEAM_BOT_Z = XBEAM_BOT_Z + XBEAM_H * 2
LBEAM_CZ    = LBEAM_BOT_Z + LBEAM_H

# Y positions of the two column rows (centred at Y=0)
ROW_Y = [-SPAN / 2.0, SPAN / 2.0]    # -2.0 and +2.0

# X positions of the 12 columns in each row
col_xs = [-LENGTH / 2.0 + i * COL_SPACING for i in range(N_COLS)]

# ════════════════════════════════════════════
# 1. FOOTING STRIPS — stone base along each row
# ════════════════════════════════════════════
for ri, ry in enumerate(ROW_Y):
    box(f"footing_{ri}",
        0, ry, FOOT_H / 2,
        LENGTH / 2, FOOT_W / 2, FOOT_H / 2,
        stone)

# ════════════════════════════════════════════
# 2. COLUMNS — Tuscan style: plinth + shaft + capital
# ════════════════════════════════════════════
for ri, ry in enumerate(ROW_Y):
    for ci, cx in enumerate(col_xs):
        # Plinth (square base)
        box(f"plinth_{ri}_{ci}",
            cx, ry, FOOT_H + PLINTH_H / 2,
            PLINTH_W, PLINTH_W, PLINTH_H / 2,
            stone)

        # Column shaft (cylinder)
        shaft_bot_z = FOOT_H + PLINTH_H
        shaft_cz    = shaft_bot_z + COL_H / 2
        cyl(f"col_{ri}_{ci}",
            cx, ry, shaft_cz,
            COL_R, COL_H, COL_VERTS,
            stone)

        # Capital slab (square block on top of shaft)
        box(f"capital_{ri}_{ci}",
            cx, ry, COL_TOP_Z + CAP_H / 2,
            CAP_W, CAP_W, CAP_H / 2,
            stone)

# ════════════════════════════════════════════
# 3. CROSS-BEAMS — connect paired columns across the 4m span
#    One per column position (12 total)
# ════════════════════════════════════════════
for ci, cx in enumerate(col_xs):
    # Cross-beam runs from ROW_Y[0] - XBEAM_OVER to ROW_Y[1] + XBEAM_OVER
    xbeam_y_len = SPAN + 2.0 * XBEAM_OVER   # total Y extent = 4.0 + 0.4 = 4.4m
    box(f"xbeam_{ci}",
        cx, 0, XBEAM_CZ,
        XBEAM_W / 2, xbeam_y_len / 2, XBEAM_H,
        stone)

# ════════════════════════════════════════════
# 4. LONGITUDINAL BEAMS — run the full length along each row at the top
#    Two beams, one above each column row
# ════════════════════════════════════════════
for ri, ry in enumerate(ROW_Y):
    box(f"longbeam_{ri}",
        0, ry, LBEAM_CZ,
        LENGTH / 2, LBEAM_W, LBEAM_H,
        beam)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "WisteriaPergola"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_pergola.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Wisteria Pergola to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces:    {len(obj.data.polygons)}")

"""Generate the "Imagine" mosaic at Strawberry Fields, Central Park Walk.

The Imagine mosaic (1985, designed by Italian craftsmen from Naples) is a
circular black-and-white tile mosaic set flush in the ground, serving as
the memorial to John Lennon at Strawberry Fields.

Key features:
  - Circular disc ~4.5m diameter, ~0.05m thick (flush with ground)
  - Outer border ring in dark border stone
  - 16 alternating black/white wedge segments radiating from center
  - Central disc (black tile) representing the "IMAGINE" inscription area
  - All geometry sits at Z=0 (top surface) to Z=-0.05 (bottom)

Origin at ground center (top face at Z=0).
Exports to models/furniture/cp_imagine_mosaic.glb
"""

import bpy
import math
import os

# ── Scene cleanup ────────────────────────────────────────────────────────────
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

white_tile  = make_mat("WhiteTile",  (0.85, 0.83, 0.80), roughness=0.40)
black_tile  = make_mat("BlackTile",  (0.12, 0.12, 0.11), roughness=0.45)
border_mat  = make_mat("Border",     (0.30, 0.28, 0.25), roughness=0.50)

# ── Geometry constants ────────────────────────────────────────────────────────
DISC_THICK   = 0.05     # how far the mosaic slab sits below grade
R_OUTER      = 2.25     # full mosaic radius (4.5m diameter)
R_BORDER_IN  = 2.05     # inner edge of the border ring
R_CENTER     = 0.42     # radius of the central "IMAGINE" disc
N_SEGS       = 16       # alternating wedge count (must be even)
N_RING       = 64       # polygon resolution for circular rings
TOP_Z        = 0.0      # top surface at ground level
BOT_Z        = -DISC_THICK

all_parts = []

# ── Helper: build a flat annular sector from from_pydata ─────────────────────
def make_annular_sector(name, r_inner, r_outer, a_start, a_end,
                         n_steps, top_z, bot_z, mat):
    """
    Build a single wedge-annulus prism (pie-slice ring segment).
    n_steps controls arc smoothness within the sector.
    """
    verts = []
    faces = []

    def ring_pts(r, z, n, a0, a1):
        pts = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((math.cos(a) * r, math.sin(a) * r, z))
        return pts

    # 4 rings of vertices: inner-top, outer-top, outer-bot, inner-bot
    it = ring_pts(r_inner, top_z, n_steps, a_start, a_end)   # inner top
    ot = ring_pts(r_outer, top_z, n_steps, a_start, a_end)   # outer top
    ob = ring_pts(r_outer, bot_z, n_steps, a_start, a_end)   # outer bot
    ib = ring_pts(r_inner, bot_z, n_steps, a_start, a_end)   # inner bot

    # Flatten into single vertex list with index base
    base = len(verts)
    n_v = n_steps + 1
    for row in (it, ot, ob, ib):
        verts.extend(row)

    IT = base + 0 * n_v
    OT = base + 1 * n_v
    OB = base + 2 * n_v
    IB = base + 3 * n_v

    # Top face quads (it → ot)
    for i in range(n_steps):
        faces.append((IT+i, OT+i, OT+i+1, IT+i+1))

    # Bottom face quads (ob → ib, reversed winding)
    for i in range(n_steps):
        faces.append((OB+i, IB+i, IB+i+1, OB+i+1))

    # Outer side quads
    for i in range(n_steps):
        faces.append((OT+i, OB+i, OB+i+1, OT+i+1))

    # Inner side quads (reversed)
    for i in range(n_steps):
        faces.append((IB+i, IT+i, IT+i+1, IB+i+1))

    # End-cap at a_start (left edge)
    faces.append((IT, IB, OB, OT))

    # End-cap at a_end (right edge)
    e = n_steps
    faces.append((OT+e, OB+e, IB+e, IT+e))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    all_parts.append(obj)
    return obj


# ── Helper: full disc or annulus ring (N_RING-gon prism) ─────────────────────
def make_ring(name, r_inner, r_outer, top_z, bot_z, n, mat):
    """Solid annular prism — used for the border ring and central disc."""
    verts = []
    faces = []

    def circle(r, z):
        return [(math.cos(2*math.pi*i/n)*r,
                 math.sin(2*math.pi*i/n)*r,
                 z) for i in range(n)]

    is_full_disc = (r_inner < 1e-6)

    if is_full_disc:
        # Top fan
        top_verts = circle(r_outer, top_z)
        bot_verts = circle(r_outer, bot_z)
        verts = [(0, 0, top_z)] + top_verts + [(0, 0, bot_z)] + bot_verts
        ct = 0
        bot_c = n + 1
        for i in range(n):
            j = (i + 1) % n
            faces.append((ct, i+1, j+1))           # top fan
            faces.append((bot_c, bot_c+j+1, bot_c+i+1))  # bot fan
        for i in range(n):
            j = (i + 1) % n
            faces.append((i+1, bot_c+i+1, bot_c+j+1, j+1))  # side
    else:
        it = circle(r_inner, top_z)
        ot = circle(r_outer, top_z)
        ib = circle(r_inner, bot_z)
        ob = circle(r_outer, bot_z)
        verts = it + ot + ib + ob
        IT, OT, IB, OB = 0, n, 2*n, 3*n
        for i in range(n):
            j = (i + 1) % n
            faces.append((IT+i, OT+i, OT+j, IT+j))     # top
            faces.append((OB+i, IB+i, IB+j, OB+j))     # bot
            faces.append((OT+i, OB+i, OB+j, OT+j))     # outer side
            faces.append((IB+i, IT+i, IT+j, IB+j))     # inner side

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    all_parts.append(obj)
    return obj


# ════════════════════════════════════════════
# 1. OUTER BORDER RING
# ════════════════════════════════════════════
make_ring("border_ring", R_BORDER_IN, R_OUTER, TOP_Z, BOT_Z, N_RING, border_mat)

# ════════════════════════════════════════════
# 2. ALTERNATING WEDGE SEGMENTS
#    16 pie-slice annuli from R_CENTER to R_BORDER_IN
#    Odd  → white_tile, Even → black_tile
# ════════════════════════════════════════════
# Use 4 arc-steps per wedge (each wedge spans 22.5°, smooth enough at this scale)
STEPS_PER_WEDGE = 4

for i in range(N_SEGS):
    a0 = 2 * math.pi * i / N_SEGS
    a1 = 2 * math.pi * (i + 1) / N_SEGS
    mat = white_tile if (i % 2 == 0) else black_tile
    make_annular_sector(
        f"wedge_{i:02d}",
        R_CENTER, R_BORDER_IN,
        a0, a1,
        STEPS_PER_WEDGE,
        TOP_Z, BOT_Z,
        mat
    )

# ════════════════════════════════════════════
# 3. CENTRAL "IMAGINE" DISC
#    Solid black disc — represents the inscription area
# ════════════════════════════════════════════
make_ring("center_disc", 0.0, R_CENTER, TOP_Z, BOT_Z, 32, black_tile)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "ImagineМosaic"

# Origin at ground center (0, 0, 0) — top surface is flush with Z=0
bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_imagine_mosaic.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB',
    use_selection=True, export_apply=True)
print(f"Exported Imagine mosaic to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces:    {len(obj.data.polygons)}")
print(f"  Diameter: {R_OUTER*2:.1f}m  Thickness: {DISC_THICK*100:.0f}mm")
print(f"  Segments: {N_SEGS} alternating wedges + border ring + central disc")

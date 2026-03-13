"""Generate Delacorte Theater for Central Park Walk.

The Delacorte Theater is an open-air amphitheater in Central Park,
home to Shakespeare in the Park since 1962. Sits between Belvedere
Castle and the Great Lawn with Turtle Pond behind the stage.

Key features:
  - Semicircular seating bowl (~1,800 seats)
  - Open-air — no roof over seating
  - Raised stage with backstage structure
  - Concrete and stone construction
  - Approximate diameter: 45m
  - Stage width: ~18m

Origin at center of stage/seating.
Exports to models/furniture/cp_delacorte.glb
"""

import bpy
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

def make_mat(name, color, roughness=0.85, metallic=0.0):
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m

concrete  = make_mat("Concrete", (0.60, 0.58, 0.54), 0.90)
stone     = make_mat("Stone",    (0.50, 0.48, 0.44), 0.88)
stage_mat = make_mat("Stage",    (0.35, 0.30, 0.25), 0.82)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# Dimensions
RADIUS = 22.0      # seating bowl radius
STAGE_W = 18.0     # stage width
STAGE_D = 10.0     # stage depth
STAGE_H = 1.2      # stage elevation
N_TIERS = 8        # concentric seating tiers
TIER_H = 0.35      # height per tier step
TIER_D = 2.2       # depth per tier
BACKSTAGE_H = 5.0  # backstage wall height

# ════════════════════════════════════════════
# 1. ORCHESTRA PIT / STAGE FLOOR
# ════════════════════════════════════════════
# Stage platform (rectangular, north side)
box("stage", 0, -RADIUS * 0.15, STAGE_H / 2,
    STAGE_W / 2, STAGE_D / 2, STAGE_H / 2, stage_mat)

# ════════════════════════════════════════════
# 2. SEMICIRCULAR SEATING TIERS
# ════════════════════════════════════════════
# Seating rises in concentric arcs from the stage
# The open end faces north (toward stage at -Y)
for tier in range(N_TIERS):
    inner_r = 8.0 + tier * TIER_D
    outer_r = inner_r + TIER_D - 0.15
    tier_z = tier * TIER_H
    n_segs = 24

    verts = []
    faces = []
    # Generate arc from -120° to +120° (240° semicircle facing -Y)
    arc_start = math.radians(30)
    arc_end = math.radians(150)

    for i in range(n_segs + 1):
        a = arc_start + (arc_end - arc_start) * i / n_segs
        # Inner ring bottom
        verts.append((math.cos(a) * inner_r, math.sin(a) * inner_r, tier_z))
        # Inner ring top
        verts.append((math.cos(a) * inner_r, math.sin(a) * inner_r, tier_z + TIER_H))
        # Outer ring bottom
        verts.append((math.cos(a) * outer_r, math.sin(a) * outer_r, tier_z))
        # Outer ring top
        verts.append((math.cos(a) * outer_r, math.sin(a) * outer_r, tier_z + TIER_H))

    for i in range(n_segs):
        b = i * 4
        # Top face (seat surface)
        faces.append((b+1, b+3, b+7, b+5))
        # Front face (riser)
        faces.append((b, b+1, b+5, b+4))
        # Back face
        faces.append((b+2, b+6, b+7, b+3))

    mesh = bpy.data.meshes.new(f"tier_{tier}")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"Tier_{tier}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(concrete)
    all_parts.append(obj)

# ════════════════════════════════════════════
# 3. BACKSTAGE WALL
# ════════════════════════════════════════════
# Wall behind the stage
box("backstage_wall", 0, -RADIUS * 0.15 - STAGE_D / 2 - 0.3, BACKSTAGE_H / 2,
    STAGE_W / 2 + 2.0, 0.40, BACKSTAGE_H / 2, stone)

# Side wing walls
for side in (-1, 1):
    box(f"wing_wall_{side}", side * (STAGE_W / 2 + 1.5),
        -RADIUS * 0.15 - STAGE_D * 0.3, BACKSTAGE_H * 0.6 / 2,
        0.35, STAGE_D * 0.4, BACKSTAGE_H * 0.6 / 2, stone)


# ════════════════════════════════════════════
# 4. PERIMETER WALL — low wall around the seating area
# ════════════════════════════════════════════
wall_r = RADIUS + 1.0
wall_h = 1.5
n_wall_segs = 20
arc_s = math.radians(25)
arc_e = math.radians(155)

for i in range(n_wall_segs):
    a1 = arc_s + (arc_e - arc_s) * i / n_wall_segs
    a2 = arc_s + (arc_e - arc_s) * (i + 1) / n_wall_segs
    x1, y1 = math.cos(a1) * wall_r, math.sin(a1) * wall_r
    x2, y2 = math.cos(a2) * wall_r, math.sin(a2) * wall_r
    mx, my = (x1+x2)/2, (y1+y2)/2
    dx, dy = x2-x1, y2-y1
    seg_len = math.sqrt(dx*dx + dy*dy)
    ang = math.atan2(dy, dx)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(mx, my, wall_h/2))
    w = bpy.context.active_object
    w.name = f"perim_wall_{i}"
    w.scale = (seg_len/2, 0.20, wall_h/2)
    w.rotation_euler = (0, 0, ang)
    w.data.materials.append(stone)
    all_parts.append(w)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "DelacorteTheater"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_delacorte.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Delacorte Theater to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

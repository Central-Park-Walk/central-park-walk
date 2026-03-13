"""Generate Chess & Checkers House for Central Park Walk.

The Chess & Checkers House is a small rustic open-air pavilion on a
rocky knoll south of the Dairy. Originally the Kinderberg (children's
shelter) designed by Calvert Vaux in 1952 renovation. Has a distinctive
umbrella-style hip roof supported by timber posts over an open stone
platform — more of a shelter/gazebo than a full building.

Key features:
  - Open timber-and-stone pavilion (no solid walls)
  - Octagonal hip roof with broad eaves
  - Thick timber posts on stone base
  - Stone floor platform on rock outcrop
  - Approximate footprint: 8m diameter

Origin at ground center.
Exports to models/furniture/cp_chess_house.glb
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

stone   = make_mat("Stone",  (0.52, 0.50, 0.45), 0.88)
timber  = make_mat("Timber", (0.32, 0.22, 0.15), 0.85)
shingle = make_mat("Shingle",(0.25, 0.20, 0.16), 0.80)

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
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=h, vertices=segs,
        location=(cx, cy, cz + h/2))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# Dimensions
R = 4.0       # pavilion radius
POST_H = 3.5  # post height
ROOF_H = 2.0  # roof cone rise
N_SIDES = 8
N_POSTS = 8

# ════════════════════════════════════════════
# 1. STONE PLATFORM
# ════════════════════════════════════════════
cylinder("platform", 0, 0, -0.05, R + 0.8, 0.35, stone, N_SIDES)

# ════════════════════════════════════════════
# 2. TIMBER POSTS
# ════════════════════════════════════════════
for i in range(N_POSTS):
    a = 2.0 * math.pi * i / N_POSTS
    px = math.cos(a) * (R - 0.3)
    py = math.sin(a) * (R - 0.3)
    # Post
    box(f"post_{i}", px, py, POST_H/2 + 0.30, 0.12, 0.12, POST_H/2, timber)
    # Stone base for each post
    box(f"post_base_{i}", px, py, 0.22, 0.22, 0.22, 0.18, stone)
    # Bracket (angled timber support under eave)
    # Inner bracket arm
    bracket_len = 0.6
    bx = px * 0.85
    by = py * 0.85
    box(f"bracket_{i}", bx, by, POST_H + 0.10,
        0.06, 0.06, 0.30, timber)

# ════════════════════════════════════════════
# 3. OCTAGONAL HIP ROOF
# ════════════════════════════════════════════
eave_z = POST_H + 0.30
roof_r = R + 0.8  # broad eave overhang

rv = []
rf = []
for i in range(N_SIDES):
    a = 2.0 * math.pi * i / N_SIDES
    rv.append((math.cos(a) * roof_r, math.sin(a) * roof_r, eave_z))
# Apex
rv.append((0, 0, eave_z + ROOF_H))
apex = len(rv) - 1

# Roof triangular faces
for i in range(N_SIDES):
    rf.append((i, (i+1) % N_SIDES, apex))
# Soffit (underside)
rf.append(list(range(N_SIDES)))

rmesh = bpy.data.meshes.new("roof_mesh")
rmesh.from_pydata(rv, [], rf)
rmesh.update()
robj = bpy.data.objects.new("Roof", rmesh)
bpy.context.collection.objects.link(robj)
robj.data.materials.append(shingle)
all_parts.append(robj)

# Ridge cap at apex
cylinder("apex_cap", 0, 0, eave_z + ROOF_H, 0.15, 0.25, timber, 8)

# ════════════════════════════════════════════
# 4. BEAM RING — connecting timber ring at post tops
# ════════════════════════════════════════════
for i in range(N_SIDES):
    a1 = 2.0 * math.pi * i / N_SIDES
    a2 = 2.0 * math.pi * ((i+1) % N_SIDES) / N_SIDES
    x1 = math.cos(a1) * (R - 0.3)
    y1 = math.sin(a1) * (R - 0.3)
    x2 = math.cos(a2) * (R - 0.3)
    y2 = math.sin(a2) * (R - 0.3)
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    seg_len = math.sqrt(dx*dx + dy*dy)
    ang = math.atan2(dy, dx)
    # Horizontal beam
    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(mx, my, POST_H + 0.30))
    beam = bpy.context.active_object
    beam.name = f"beam_{i}"
    beam.scale = (seg_len / 2, 0.08, 0.10)
    beam.rotation_euler = (0, 0, ang)
    beam.data.materials.append(timber)
    all_parts.append(beam)

# Low stone wall segments (knee wall between posts — waist height)
KNEE_H = 0.9
for i in range(0, N_SIDES, 2):  # every other bay has a knee wall
    a1 = 2.0 * math.pi * i / N_SIDES
    a2 = 2.0 * math.pi * ((i+1) % N_SIDES) / N_SIDES
    x1 = math.cos(a1) * (R - 0.3)
    y1 = math.sin(a1) * (R - 0.3)
    x2 = math.cos(a2) * (R - 0.3)
    y2 = math.sin(a2) * (R - 0.3)
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    seg_len = math.sqrt(dx*dx + dy*dy)
    ang = math.atan2(dy, dx)
    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(mx, my, 0.30 + KNEE_H/2))
    wall = bpy.context.active_object
    wall.name = f"knee_wall_{i}"
    wall.scale = (seg_len / 2, 0.18, KNEE_H / 2)
    wall.rotation_euler = (0, 0, ang)
    wall.data.materials.append(stone)
    all_parts.append(wall)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "ChessHouse"

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_chess_house.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Chess & Checkers House to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

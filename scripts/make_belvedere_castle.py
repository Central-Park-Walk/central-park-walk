"""Generate Belvedere Castle for Central Park Walk.

Belvedere Castle is a Victorian folly on Vista Rock, the second-highest
natural elevation in Central Park. Built 1869 by Calvert Vaux and
Jacob Wrey Mould in a mix of Gothic and Romanesque styles.

Key features:
  - Main tower (octagonal lookout, ~15.5m to parapet)
  - Lower wing with loggia/open arches
  - Manhattan schist and granite construction
  - Crenellated parapet (castle battlements)
  - Stone terrace/viewing platform

Approximate real dimensions:
  - Tower: ~6m diameter, ~15.5m tall
  - Wing: ~18m long × 8m deep × 8m tall
  - Loggia arches: 5 open bays on south face

Origin at ground center of the main structure footprint.
Exports to models/furniture/cp_belvedere_castle.glb
"""

import bpy
import math
import os
from mathutils import Vector, Matrix

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

schist   = make_mat("Schist",   (0.38, 0.36, 0.33), 0.90)   # dark Manhattan schist
granite  = make_mat("Granite",  (0.52, 0.50, 0.46), 0.85)   # lighter granite trim
slate    = make_mat("Slate",    (0.30, 0.28, 0.26), 0.78)    # dark slate roof
iron_mat = make_mat("Iron",     (0.15, 0.14, 0.13), 0.65, 0.3)  # railing iron

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    """Box at center with half-extents."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def cylinder(name, cx, cy, cz, radius, height, mat, segments=16):
    """Upright cylinder, bottom at cz."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, vertices=segments,
        location=(cx, cy, cz + height / 2.0))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    all_parts.append(o)
    return o


# ════════════════════════════════════════════
# LAYOUT
# ════════════════════════════════════════════
# Tower at X=0, Y=+4 (north side)
# Wing extends from tower southward: Y=-4 to Y=+4 (centered at Y=0 roughly)
# The wing is wider in X

TOWER_R     = 3.0      # tower radius (octagonal approximated as cylinder)
TOWER_H     = 13.0     # tower wall height
PARAPET_H   = 2.5      # crenellated parapet above tower wall
TOWER_CY    = 5.0      # tower center Y offset (north of wing center)

WING_W      = 18.0     # wing X extent
WING_D      = 8.0      # wing Y extent
WING_H      = 7.5      # wing wall height
WING_CY     = -1.0     # wing center Y

LOGGIA_H    = 5.5      # arch opening height
LOGGIA_N    = 5         # number of arched bays
PIER_W      = 0.6       # width of piers between arches

MERLON_W    = 0.55
MERLON_H    = 1.2
MERLON_D    = 0.50
CRENEL_W    = 0.45


# ════════════════════════════════════════════
# 1. MAIN TOWER — octagonal lookout tower
# ════════════════════════════════════════════
cylinder("tower_body", 0, TOWER_CY, 0, TOWER_R, TOWER_H, schist, 8)

# Tower floor slab
cylinder("tower_floor", 0, TOWER_CY, 0, TOWER_R + 0.15, 0.3, granite, 8)

# Tower parapet wall (thin ring above tower body)
# Build as difference between outer and inner cylinders → approximate with ring of boxes
n_sides = 8
parapet_base = TOWER_H
for i in range(n_sides):
    a1 = 2.0 * math.pi * i / n_sides
    a2 = 2.0 * math.pi * (i + 0.5) / n_sides
    mx = math.cos(a1) * (TOWER_R + 0.1)
    my = math.sin(a1) * (TOWER_R + 0.1) + TOWER_CY
    mx2 = math.cos(a2) * (TOWER_R + 0.1)
    my2 = math.sin(a2) * (TOWER_R + 0.1) + TOWER_CY
    # Merlon (raised part of battlement)
    box(f"tower_merlon_{i}", mx, my, parapet_base + MERLON_H/2,
        MERLON_W/2, MERLON_D/2, MERLON_H/2, schist)

# Tower conical roof hint (flattened cone)
ROOF_H = 2.5
roof_verts = []
roof_faces = []
n_roof = 8
for i in range(n_roof):
    a = 2.0 * math.pi * i / n_roof
    roof_verts.append((math.cos(a) * (TOWER_R + 0.2), math.sin(a) * (TOWER_R + 0.2) + TOWER_CY, TOWER_H + MERLON_H * 0.5))
# Apex
roof_verts.append((0, TOWER_CY, TOWER_H + MERLON_H * 0.5 + ROOF_H))
apex_i = len(roof_verts) - 1
for i in range(n_roof):
    roof_faces.append((i, (i + 1) % n_roof, apex_i))
# Base cap
roof_faces.append(list(range(n_roof)))

rmesh = bpy.data.meshes.new("tower_roof_mesh")
rmesh.from_pydata(roof_verts, [], roof_faces)
rmesh.update()
robj = bpy.data.objects.new("TowerRoof", rmesh)
bpy.context.collection.objects.link(robj)
robj.data.materials.append(slate)
all_parts.append(robj)


# ════════════════════════════════════════════
# 2. MAIN WING — lower building with loggia
# ════════════════════════════════════════════
hww = WING_W / 2.0
hwd = WING_D / 2.0
wcy = WING_CY

# Back wall (north, toward tower) — solid
box("wing_back", 0, wcy + hwd - 0.3, WING_H/2,
    hww, 0.30, WING_H/2, schist)

# Side walls (east and west)
for side in (-1, 1):
    box(f"wing_side_{side}", side * hww, wcy, WING_H/2,
        0.35, hwd, WING_H/2, schist)

# Front wall (south) — loggia with arched openings
# Build piers between arches and wall above arches
total_bay_w = WING_W - 0.7  # minus side wall thickness
bay_w = total_bay_w / LOGGIA_N
arch_w = bay_w - PIER_W
front_y = wcy - hwd

# Wall above arches
above_arch_h = WING_H - LOGGIA_H
box("loggia_top", 0, front_y, LOGGIA_H + above_arch_h/2,
    hww, 0.30, above_arch_h/2, schist)

# Piers between arches
for i in range(LOGGIA_N + 1):
    px = -total_bay_w/2 + i * bay_w
    if i == 0 or i == LOGGIA_N:
        pw = PIER_W * 0.75  # end piers are thinner
    else:
        pw = PIER_W
    box(f"loggia_pier_{i}", px, front_y, LOGGIA_H/2,
        pw/2, 0.30, LOGGIA_H/2, granite)

# Arch tops (semicircular keystones above each opening)
for i in range(LOGGIA_N):
    ax = -total_bay_w/2 + (i + 0.5) * bay_w
    # Simple arch keystone block
    box(f"arch_key_{i}", ax, front_y, LOGGIA_H + 0.15,
        arch_w/2 * 0.6, 0.32, 0.20, granite)


# ════════════════════════════════════════════
# 3. WING ROOF — gable/hip roof
# ════════════════════════════════════════════
wing_eave = WING_H
wing_ridge_h = 2.5
overhang = 0.4

wrv = [
    (-hww - overhang, wcy - hwd - overhang, wing_eave),   # 0
    ( hww + overhang, wcy - hwd - overhang, wing_eave),   # 1
    ( hww + overhang, wcy + hwd + overhang, wing_eave),   # 2
    (-hww - overhang, wcy + hwd + overhang, wing_eave),   # 3
    (-hww - overhang, wcy, wing_eave + wing_ridge_h),     # 4 left ridge
    ( hww + overhang, wcy, wing_eave + wing_ridge_h),     # 5 right ridge
]
wrf = [
    (0, 1, 5, 4),  # front slope
    (2, 3, 4, 5),  # back slope
    (3, 0, 4),     # left gable
    (1, 2, 5),     # right gable
    (0, 3, 2, 1),  # soffit
]
wrmesh = bpy.data.meshes.new("wing_roof_mesh")
wrmesh.from_pydata(wrv, [], wrf)
wrmesh.update()
wrobj = bpy.data.objects.new("WingRoof", wrmesh)
bpy.context.collection.objects.link(wrobj)
wrobj.data.materials.append(slate)
all_parts.append(wrobj)


# ════════════════════════════════════════════
# 4. BATTLEMENTS — crenellated parapet on wing
# ════════════════════════════════════════════
# Front parapet (south face)
n_front_merlons = int(WING_W / (MERLON_W + CRENEL_W))
merlon_step = WING_W / n_front_merlons
for i in range(n_front_merlons):
    mx = -hww + (i + 0.5) * merlon_step
    mz = WING_H
    box(f"wing_merlon_f_{i}", mx, front_y, mz + MERLON_H/2,
        MERLON_W/2, 0.25, MERLON_H/2, schist)

# Side parapets
for side in (-1, 1):
    n_side = int(WING_D / (MERLON_W + CRENEL_W))
    side_step = WING_D / max(n_side, 1)
    sx = side * (hww + 0.05)
    for i in range(n_side):
        my = wcy - hwd + (i + 0.5) * side_step
        box(f"wing_merlon_s_{side}_{i}", sx, my, WING_H + MERLON_H/2,
            0.25, MERLON_W/2, MERLON_H/2, schist)


# ════════════════════════════════════════════
# 5. VIEWING TERRACE — stone platform in front of loggia
# ════════════════════════════════════════════
terrace_d = 3.5  # depth extending south from front wall
terrace_y = front_y - terrace_d / 2
box("terrace_slab", 0, terrace_y, -0.15,
    hww + 1.0, terrace_d/2, 0.20, granite)

# Low wall / railing around terrace
box("terrace_wall_s", 0, front_y - terrace_d, 0.45,
    hww + 1.0, 0.20, 0.50, schist)
for side in (-1, 1):
    box(f"terrace_wall_{side}", side * (hww + 1.0), terrace_y, 0.45,
        0.20, terrace_d/2 + 0.20, 0.50, schist)


# ════════════════════════════════════════════
# 6. CONNECTING ELEMENTS — tower-to-wing transition
# ════════════════════════════════════════════
# Fill between tower cylinder and wing back wall
box("tower_wing_fill", 0, TOWER_CY - TOWER_R + 0.5, WING_H/2,
    TOWER_R * 0.8, 1.5, WING_H/2, schist)


# ════════════════════════════════════════════
# 7. FOUNDATION / ROCK BASE
# ════════════════════════════════════════════
# Visible stone foundation course
box("foundation", 0, (wcy + TOWER_CY) / 2, -0.25,
    hww + 0.5, (WING_D + TOWER_R * 2 + abs(TOWER_CY - wcy)) / 2 + 0.5, 0.30, granite)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

castle = bpy.context.active_object
castle.name = "BelvedereCastle"

# Origin at ground center
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_belvedere_castle.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported Belvedere Castle to {out_path}")
print(f"  Vertices: {len(castle.data.vertices)}")
print(f"  Faces: {len(castle.data.polygons)}")

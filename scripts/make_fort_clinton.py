"""Generate Fort Clinton (Nutter's Battery) for Central Park Walk.

Fort Clinton (also called Nutter's Battery, War of 1812) is a small
stone fortification ruin in the northwest section of Central Park,
near the Blockhouse. Simpler than the Blockhouse — a low semicircular
stone battery emplacement facing north/west.

Key features:
  - Semicircular stone parapet wall, ~10m diameter
  - Thick rubble walls (~0.8m) about 1.5m high (ruined)
  - Open to the south (gun battery faces north/west)
  - Rough Manhattan schist construction
  - Irregular top (ruins)
  - Sits on exposed rock outcrop

Origin at ground center.
Exports to models/furniture/cp_fort_clinton.glb
"""

import bpy
import math
import os

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

schist = make_mat("Schist", (0.38, 0.36, 0.33), 0.92)
mortar = make_mat("Mortar", (0.52, 0.50, 0.46), 0.88)

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

# Geometry constants
R_MID   = 5.0   # radius to wall centreline
T       = 0.8   # wall thickness (half = 0.4)
H       = 1.5   # parapet height
N_SEGS  = 14    # box segments spanning the half-circle (north 180°)

# The arc runs from angle=0 (east/right) to angle=pi (west/left), i.e.
# the flat/open side faces south (+Y in Blender).  Each segment is a box
# tangent to the arc at its midpoint.

# ════════════════════════════════════════════
# 1. EXPOSED ROCK OUTCROP BASE
# ════════════════════════════════════════════
# Irregular schist platform — two overlapping slabs suggest real outcrop
box("rock_base_main",   0.0,  -1.0, -0.35,  6.5, 5.5, 0.50, schist)
box("rock_base_north",  0.3,  -3.8, -0.50,  5.0, 2.0, 0.35, schist)
box("rock_base_east",   3.2,  -0.5, -0.42,  2.0, 3.5, 0.28, schist)
box("rock_base_west",  -3.4,  -0.8, -0.38,  2.2, 3.2, 0.22, schist)

# ════════════════════════════════════════════
# 2. SEMICIRCULAR PARAPET WALL
#    14 box segments, angles 0 → π (east → north → west)
#    open side = south (+Y axis)
# ════════════════════════════════════════════
seg_arc = math.pi / N_SEGS          # angular width per segment
seg_chord = 2.0 * R_MID * math.sin(seg_arc / 2.0)  # chord length

for i in range(N_SEGS):
    # midpoint angle of this segment (0=east, pi/2=north, pi=west)
    angle = seg_arc * (i + 0.5)

    # wall centre position
    cx = math.cos(angle) * R_MID
    cy = -math.sin(angle) * R_MID   # negative Y so arc opens toward +Y

    # wall segment is oriented tangent to circle at this angle
    tangent_angle = angle + math.pi / 2.0

    # slight height variation for ruin effect
    ruin_dh = math.sin(i * 1.31 + 0.7) * 0.18
    wall_h = H + ruin_dh

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, wall_h / 2.0))
    seg = bpy.context.active_object
    seg.name = f"wall_seg_{i:02d}"
    # scale: X = half-chord (length along arc), Y = half-thickness, Z = half-height
    seg.scale = (seg_chord / 2.0 + 0.05, T / 2.0, wall_h / 2.0)
    seg.rotation_euler = (0, 0, tangent_angle)
    seg.data.materials.append(schist)
    all_parts.append(seg)

# ════════════════════════════════════════════
# 3. END CHEEKS — short straight wall stubs at east and west terminations
#    These are the open mouth of the battery, facing south
# ════════════════════════════════════════════
cheek_len = 1.8   # how far south the end walls extend
cheek_h   = H * 0.85   # slightly lower (more ruined)

# East cheek: at angle=0, wall runs south (+Y direction)
box("cheek_east",  R_MID,  -cheek_len / 2.0,  cheek_h / 2.0,
    T / 2.0, cheek_len / 2.0, cheek_h / 2.0, schist)

# West cheek: at angle=pi
box("cheek_west", -R_MID,  -cheek_len / 2.0,  cheek_h / 2.0,
    T / 2.0, cheek_len / 2.0, cheek_h / 2.0, schist)

# ════════════════════════════════════════════
# 4. MORTAR COURSE LINES
#    Thin horizontal slabs at mid-height on outer face to suggest
#    rubble coursing joints
# ════════════════════════════════════════════
R_OUTER = R_MID + T / 2.0 + 0.02   # just outside the outer wall face
course_z = H * 0.5

for i in range(N_SEGS):
    angle = seg_arc * (i + 0.5)
    cx = math.cos(angle) * R_OUTER
    cy = -math.sin(angle) * R_OUTER
    tangent_angle = angle + math.pi / 2.0

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, course_z))
    seg = bpy.context.active_object
    seg.name = f"mortar_course_{i:02d}"
    seg.scale = (seg_chord / 2.0 + 0.05, 0.04, 0.04)
    seg.rotation_euler = (0, 0, tangent_angle)
    seg.data.materials.append(mortar)
    all_parts.append(seg)

# ════════════════════════════════════════════
# 5. IRREGULAR WALL CAP STONES
#    Broken stone slabs along the top — height varies per segment
# ════════════════════════════════════════════
for i in range(N_SEGS):
    angle = seg_arc * (i + 0.5)
    cx = math.cos(angle) * R_MID
    cy = -math.sin(angle) * R_MID

    ruin_dh = math.sin(i * 1.31 + 0.7) * 0.18
    top_z = H + ruin_dh

    # Cap slab slightly wider and thicker than the wall segment
    cap_extra_w = 0.08 * (1.0 + math.sin(i * 2.7) * 0.3)
    cap_h = 0.12 + abs(math.sin(i * 0.9)) * 0.06

    tangent_angle = angle + math.pi / 2.0

    bpy.ops.mesh.primitive_cube_add(size=1.0,
        location=(cx, cy, top_z + cap_h / 2.0))
    cap = bpy.context.active_object
    cap.name = f"cap_{i:02d}"
    cap.scale = (seg_chord / 2.0 + cap_extra_w,
                 T / 2.0 + 0.06,
                 cap_h / 2.0)
    cap.rotation_euler = (0, 0, tangent_angle)
    cap.data.materials.append(schist)
    all_parts.append(cap)

# End cheek caps
for side, cx in (("east", R_MID), ("west", -R_MID)):
    cap_h = 0.13
    top_z = cheek_h
    box(f"cheek_cap_{side}", cx, -cheek_len / 2.0, top_z + cap_h / 2.0,
        T / 2.0 + 0.06, cheek_len / 2.0 + 0.04, cap_h / 2.0, schist)

# ════════════════════════════════════════════
# 6. EARTH FILL — interior packed earth / soil inside the battery
#    Low flat fill visible inside the arc
# ════════════════════════════════════════════
# Use a simple half-disc approximation: a cylinder clipped by position.
# With box primitives we lay a grid of fill slabs that fit within the arc.
fill_step = 2.2
fill_z    = 0.12   # height of fill above rock base top (~0.0)
fill_half_h = 0.10

for row in range(3):
    y_off = -row * fill_step - 1.0   # Y negative = inside arc (north)
    row_r = math.sqrt(max(0, (R_MID - T / 2.0 - 0.1) ** 2 - y_off ** 2))
    if row_r < 0.2:
        continue
    # lay a single slab spanning the row width
    box(f"fill_row_{row}", 0.0, y_off, fill_z,
        row_r * 0.88, fill_step / 2.0 * 0.85, fill_half_h, mortar)

# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "FortClinton"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_fort_clinton.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB',
    use_selection=True, export_apply=True)
print(f"Exported Fort Clinton to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

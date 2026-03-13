"""Generate Cop Cot (rustic shelter) for Central Park Walk.

Cop Cot is a rustic timber shelter/gazebo on a rocky knoll
overlooking the southwest corner of the Lake. One of the
original Olmsted & Vaux rustic structures (rebuilt 2001).
"Cop" = summit/hilltop, "Cot" = cottage.

Key features:
  - Open-sided rustic timber shelter
  - Natural branch/log construction with bark intact
  - Peaked cedar-shake roof
  - Stone seat and floor base
  - Sits on exposed Manhattan schist outcrop
  - Approximate footprint: 5m × 4m

Origin at ground center.
Exports to models/furniture/cp_cop_cot.glb
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

log_bark = make_mat("LogBark",  (0.30, 0.22, 0.14), 0.92)   # bark-on log
cedar    = make_mat("Cedar",    (0.35, 0.28, 0.18), 0.85)   # cedar shake
stone    = make_mat("Stone",    (0.45, 0.43, 0.40), 0.90)   # Manhattan schist
branch   = make_mat("Branch",   (0.28, 0.20, 0.12), 0.88)   # thinner branch

all_parts = []

def box(name, cx, cy, cz, hx, hy, hz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.name = name
    o.scale = (hx * 2, hy * 2, hz * 2)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

def log_post(name, cx, cy, cz, radius, height, mat):
    """Slightly irregular cylinder to suggest natural log."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=height, vertices=8,
        location=(cx, cy, cz + height/2))
    o = bpy.context.active_object
    o.name = name
    # Slight random tilt for natural look
    tilt = (hash(name) % 100) / 5000.0
    o.rotation_euler = (tilt, -tilt * 0.7, 0)
    o.data.materials.append(mat)
    all_parts.append(o)
    return o

W = 5.0   # length
D = 4.0   # depth
H = 3.2   # eave height
RIDGE_H = 1.5

hw = W / 2.0
hd = D / 2.0

# ════════════════════════════════════════════
# 1. STONE BASE — rough rock floor platform
# ════════════════════════════════════════════
box("rock_base", 0, 0, 0.10, hw + 0.5, hd + 0.5, 0.25, stone)
box("rock_step", 0, hd + 0.3, 0.05, 1.0, 0.35, 0.15, stone)

# ════════════════════════════════════════════
# 2. LOG POSTS — 6 natural branch posts
# ════════════════════════════════════════════
# Corners + midpoints of long sides
post_positions = [
    (-hw + 0.15, -hd + 0.15),
    (-hw + 0.15,  hd - 0.15),
    ( hw - 0.15, -hd + 0.15),
    ( hw - 0.15,  hd - 0.15),
    (0, -hd + 0.15),
    (0,  hd - 0.15),
]
for i, (px, py) in enumerate(post_positions):
    r = 0.08 + (hash(str(i)) % 20) / 400.0  # 0.08-0.13 radius
    log_post(f"post_{i}", px, py, 0.25, r, H, log_bark)

# ════════════════════════════════════════════
# 3. BRANCH CROSS-BEAMS
# ════════════════════════════════════════════
beam_z = H + 0.25

# Ridge beam (long axis)
log_post("ridge_beam", 0, 0, beam_z + RIDGE_H * 0.5, 0.08, W + 0.3, log_bark)
bpy.context.active_object.rotation_euler = (0, math.pi/2, 0)

# Cross beams at each post pair
for py in (-hd + 0.15, 0, hd - 0.15):
    log_post(f"cross_{py}", 0, py, beam_z - 0.1, 0.06, W * 0.9, branch)
    bpy.context.active_object.rotation_euler = (0, math.pi/2, 0)

# ════════════════════════════════════════════
# 4. CEDAR SHAKE ROOF — steep gable
# ════════════════════════════════════════════
overhang = 0.6
rv = [
    (-hw - overhang, -hd - overhang, beam_z),
    ( hw + overhang, -hd - overhang, beam_z),
    ( hw + overhang,  hd + overhang, beam_z),
    (-hw - overhang,  hd + overhang, beam_z),
    (-hw - overhang, 0, beam_z + RIDGE_H),
    ( hw + overhang, 0, beam_z + RIDGE_H),
]
rf = [
    (0, 1, 5, 4),
    (2, 3, 4, 5),
    (3, 0, 4),
    (1, 2, 5),
    (0, 3, 2, 1),
]
rm = bpy.data.meshes.new("roof_mesh")
rm.from_pydata(rv, [], rf)
rm.update()
ro = bpy.data.objects.new("CedarRoof", rm)
bpy.context.collection.objects.link(ro)
ro.data.materials.append(cedar)
all_parts.append(ro)

# ════════════════════════════════════════════
# 5. BRANCH RAILINGS — decorative branch infill between posts
# ════════════════════════════════════════════
rail_h = 0.85
for i in range(len(post_positions) - 1):
    px1, py1 = post_positions[i]
    px2, py2 = post_positions[i + 1]
    # Only connect adjacent posts on same side
    if abs(py1 - py2) < 0.5 or abs(px1 - px2) < 0.5:
        mx = (px1 + px2) / 2
        my = (py1 + py2) / 2
        dx = px2 - px1
        dy = py2 - py1
        length = math.sqrt(dx*dx + dy*dy)
        ang = math.atan2(dy, dx)
        # Top rail
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=length,
            vertices=6, location=(mx, my, 0.25 + rail_h))
        r = bpy.context.active_object
        r.name = f"rail_top_{i}"
        r.rotation_euler = (0, math.pi/2, ang)
        r.data.materials.append(branch)
        all_parts.append(r)
        # Bottom rail
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=length,
            vertices=6, location=(mx, my, 0.25 + rail_h * 0.35))
        r2 = bpy.context.active_object
        r2.name = f"rail_bot_{i}"
        r2.rotation_euler = (0, math.pi/2, ang)
        r2.data.materials.append(branch)
        all_parts.append(r2)

# ════════════════════════════════════════════
# 6. STONE BENCH — built into back wall
# ════════════════════════════════════════════
box("bench_seat", 0, -hd + 0.40, 0.55, hw * 0.7, 0.25, 0.08, stone)
box("bench_back", 0, -hd + 0.20, 0.80, hw * 0.7, 0.08, 0.30, stone)


# ════════════════════════════════════════════
# FINALIZE
# ════════════════════════════════════════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obj = bpy.context.active_object
obj.name = "CopCot"
bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

out_path = "/home/chris/central-park-walk/models/furniture/cp_cop_cot.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB',
    use_selection=True, export_apply=True)
print(f"Exported Cop Cot to {out_path}")
print(f"  Vertices: {len(obj.data.vertices)}")
print(f"  Faces: {len(obj.data.polygons)}")

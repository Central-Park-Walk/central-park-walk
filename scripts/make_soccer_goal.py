"""Generate soccer goal for Central Park Walk.

Full-size regulation soccer goal:
- 7.32m × 2.44m (24ft × 8ft)
- White aluminum posts and crossbar
- Net support frame (depth ~2m)
- No mesh net (too fine for real-time)

Exports to models/furniture/cp_soccer_goal.glb
"""

import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

GOAL_W = 7.32
GOAL_H = 2.44
GOAL_D = 2.0     # net depth
POST_R = 0.05    # 10cm diameter posts
BAR_R = 0.04     # crossbar slightly thinner

# --- Two uprights ---
for sx in [-GOAL_W/2, GOAL_W/2]:
    bpy.ops.mesh.primitive_cylinder_add(radius=POST_R, depth=GOAL_H, vertices=8)
    post = bpy.context.active_object
    post.name = f"Upright_{sx}"
    post.location = (sx, GOAL_H/2, 0)
    bpy.ops.object.transform_apply(location=True)
    objects.append(post)

# --- Crossbar ---
bpy.ops.mesh.primitive_cylinder_add(radius=BAR_R, depth=GOAL_W, vertices=8)
bar = bpy.context.active_object
bar.name = "Crossbar"
bar.rotation_euler = (0, 0, math.pi/2)
bar.location = (0, GOAL_H, 0)
bpy.ops.object.transform_apply(location=True, rotation=True)
objects.append(bar)

# --- Net frame: two rear posts + rear crossbar + top bars ---
for sx in [-GOAL_W/2, GOAL_W/2]:
    bpy.ops.mesh.primitive_cylinder_add(radius=BAR_R * 0.7, depth=GOAL_H * 0.6, vertices=6)
    rpost = bpy.context.active_object
    rpost.name = f"RearPost_{sx}"
    rpost.location = (sx, GOAL_H * 0.3, -GOAL_D)
    bpy.ops.object.transform_apply(location=True)
    objects.append(rpost)

# Rear crossbar (lower)
bpy.ops.mesh.primitive_cylinder_add(radius=BAR_R * 0.6, depth=GOAL_W, vertices=6)
rbar = bpy.context.active_object
rbar.name = "RearBar"
rbar.rotation_euler = (0, 0, math.pi/2)
rbar.location = (0, GOAL_H * 0.6, -GOAL_D)
bpy.ops.object.transform_apply(location=True, rotation=True)
objects.append(rbar)

# Top depth bars (connect crossbar to rear)
for sx in [-GOAL_W/2, GOAL_W/2]:
    length = math.sqrt(GOAL_D**2 + (GOAL_H * 0.4)**2)
    angle = math.atan2(GOAL_H * 0.4, GOAL_D)
    bpy.ops.mesh.primitive_cylinder_add(radius=BAR_R * 0.6, depth=length, vertices=6)
    tbar = bpy.context.active_object
    tbar.name = f"TopBar_{sx}"
    tbar.location = (sx, GOAL_H - GOAL_H*0.2, -GOAL_D/2)
    tbar.rotation_euler = (angle, 0, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    objects.append(tbar)

# --- Material: white aluminum ---
mat = bpy.data.materials.new("WhiteAluminum")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.90, 0.90, 0.88, 1.0)
bsdf.inputs["Metallic"].default_value = 0.6
bsdf.inputs["Roughness"].default_value = 0.4

for obj in objects:
    obj.data.materials.clear()
    obj.data.materials.append(mat)

# Join
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.active_object
obj.name = "SoccerGoal"

out_path = "/home/chris/central-park-walk/models/furniture/cp_soccer_goal.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Soccer Goal to {out_path} ({vcount} verts, {fcount} faces)")

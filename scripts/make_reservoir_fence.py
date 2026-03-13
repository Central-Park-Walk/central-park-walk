"""Generate Reservoir perimeter fence for Central Park Walk.

The JKO Reservoir has a tall chain-link security fence (2.4m/8ft)
with black vinyl coating. This generates a 3m fence section
for MultiMesh placement around the 2575m perimeter.

Exports to models/furniture/cp_reservoir_fence.glb
"""

import bpy
import bmesh
import math

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

FENCE_H = 2.4   # 8 feet
SECTION_W = 3.0  # 3m sections
POST_R = 0.025   # 2.5cm radius posts
POST_H = FENCE_H + 0.1  # posts slightly taller than mesh
WIRE_R = 0.005   # thin wire
N_VERT_WIRES = 16  # vertical wires per section
N_HORIZ_WIRES = 8  # horizontal wires

objects = []

# --- Two end posts ---
for sx in [-SECTION_W/2, SECTION_W/2]:
    bpy.ops.mesh.primitive_cylinder_add(radius=POST_R, depth=POST_H, vertices=8)
    post = bpy.context.active_object
    post.name = f"Post_{sx}"
    post.location = (sx, POST_H/2, 0)
    bpy.ops.object.transform_apply(location=True)
    objects.append(post)

# --- Top rail ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=SECTION_W, vertices=8)
rail = bpy.context.active_object
rail.name = "TopRail"
rail.rotation_euler = (0, 0, math.pi/2)
rail.location = (0, FENCE_H, 0)
bpy.ops.object.transform_apply(location=True, rotation=True)
objects.append(rail)

# --- Bottom rail ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=SECTION_W, vertices=8)
brail = bpy.context.active_object
brail.name = "BotRail"
brail.rotation_euler = (0, 0, math.pi/2)
brail.location = (0, 0.05, 0)
bpy.ops.object.transform_apply(location=True, rotation=True)
objects.append(brail)

# --- Vertical wires ---
for i in range(N_VERT_WIRES):
    t = (i + 0.5) / N_VERT_WIRES
    x = -SECTION_W/2 + SECTION_W * t
    bpy.ops.mesh.primitive_cylinder_add(radius=WIRE_R, depth=FENCE_H - 0.1, vertices=4)
    wire = bpy.context.active_object
    wire.name = f"VWire_{i}"
    wire.location = (x, FENCE_H/2, 0)
    bpy.ops.object.transform_apply(location=True)
    objects.append(wire)

# --- Horizontal wires ---
for i in range(N_HORIZ_WIRES):
    t = (i + 1.0) / (N_HORIZ_WIRES + 1)
    y = 0.05 + (FENCE_H - 0.05) * t
    bpy.ops.mesh.primitive_cylinder_add(radius=WIRE_R, depth=SECTION_W, vertices=4)
    wire = bpy.context.active_object
    wire.name = f"HWire_{i}"
    wire.rotation_euler = (0, 0, math.pi/2)
    wire.location = (0, y, 0)
    bpy.ops.object.transform_apply(location=True, rotation=True)
    objects.append(wire)

# --- Material: black vinyl-coated chain link ---
mat = bpy.data.materials.new("BlackFence")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1.0)
bsdf.inputs["Roughness"].default_value = 0.5
bsdf.inputs["Metallic"].default_value = 0.7

for obj in objects:
    obj.data.materials.clear()
    obj.data.materials.append(mat)

# Join all
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
obj = bpy.context.active_object
obj.name = "ReservoirFence"

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_reservoir_fence.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Reservoir Fence to {out_path} ({vcount} verts, {fcount} faces)")

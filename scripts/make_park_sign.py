"""Generate Central Park wayfinding sign for Central Park Walk.

The Central Park Conservancy uses distinctive brown wooden signs:
- Brown-stained wooden post (10cm square, 2.4m tall)
- Brown wooden sign board at top (60cm wide × 30cm tall × 3cm thick)
- Angled cap on top of post
- Placed at major path intersections

Exports to models/furniture/cp_park_sign.glb
"""

import bpy
import math

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

# --- Post (square, 10cm × 10cm, 2.4m tall) ---
bpy.ops.mesh.primitive_cube_add(size=1)
post = bpy.context.active_object
post.name = "Post"
post.scale = (0.05, 1.2, 0.05)  # 10cm × 2.4m × 10cm
post.location = (0, 1.2, 0)
bpy.ops.object.transform_apply(location=True, scale=True)
objects.append(post)

# --- Sign board (60cm wide × 30cm tall × 3cm thick) ---
bpy.ops.mesh.primitive_cube_add(size=1)
board = bpy.context.active_object
board.name = "Board"
board.scale = (0.30, 0.15, 0.015)  # 60cm × 30cm × 3cm
board.location = (0, 2.25, 0.04)  # slightly forward of post
bpy.ops.object.transform_apply(location=True, scale=True)
objects.append(board)

# --- Cap (angled top piece) ---
bpy.ops.mesh.primitive_cone_add(radius1=0.07, radius2=0.0, depth=0.08, vertices=4)
cap = bpy.context.active_object
cap.name = "Cap"
cap.location = (0, 2.44, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(cap)

# --- Material: brown-stained wood ---
mat = bpy.data.materials.new("BrownWood")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.25, 0.15, 0.08, 1.0)  # warm brown
bsdf.inputs["Roughness"].default_value = 0.75
bsdf.inputs["Metallic"].default_value = 0.0

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
obj.name = "ParkSign"

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_park_sign.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Park Sign to {out_path} ({vcount} verts, {fcount} faces)")

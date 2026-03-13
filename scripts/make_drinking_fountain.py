"""Generate Central Park drinking fountain for Central Park Walk.

Classic NYC Parks cast-iron pedestal drinking fountain:
- Fluted cylindrical pedestal (~90cm tall, 15cm diameter)
- Basin bowl at top (~30cm diameter, shallow)
- Square base plate (25cm x 25cm)
- Small spout nub at top center

Exports to models/furniture/cp_drinking_fountain.glb
"""

import bpy
import math

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

objects = []

# --- Base plate (square, 25cm x 25cm, 3cm thick) ---
bpy.ops.mesh.primitive_cube_add(size=1)
base = bpy.context.active_object
base.name = "Base"
base.scale = (0.125, 0.015, 0.125)
base.location = (0, 0.015, 0)
bpy.ops.object.transform_apply(location=True, scale=True)
objects.append(base)

# --- Pedestal (cylinder, 90cm tall, 7.5cm radius) ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.075, depth=0.90, vertices=12)
ped = bpy.context.active_object
ped.name = "Pedestal"
ped.location = (0, 0.03 + 0.45, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(ped)

# --- Ring detail at top of pedestal ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.095, depth=0.04, vertices=16)
ring = bpy.context.active_object
ring.name = "Ring"
ring.location = (0, 0.03 + 0.88, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(ring)

# --- Basin bowl (30cm diameter, 8cm deep) ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.08, vertices=16)
basin = bpy.context.active_object
basin.name = "Basin"
basin.location = (0, 0.03 + 0.90 + 0.04, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(basin)

# --- Lip/rim at top of basin ---
bpy.ops.mesh.primitive_torus_add(
    major_radius=0.14, minor_radius=0.02,
    major_segments=16, minor_segments=8
)
rim = bpy.context.active_object
rim.name = "Rim"
rim.location = (0, 0.03 + 0.90 + 0.08, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(rim)

# --- Spout nub ---
bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.05, vertices=8)
spout = bpy.context.active_object
spout.name = "Spout"
spout.location = (0, 0.03 + 0.90 + 0.10, 0)
bpy.ops.object.transform_apply(location=True)
objects.append(spout)

# --- Material: dark cast iron ---
mat = bpy.data.materials.new("CastIron")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.15, 0.17, 0.14, 1.0)
bsdf.inputs["Metallic"].default_value = 0.85
bsdf.inputs["Roughness"].default_value = 0.65

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
obj.name = "DrinkingFountain"

# Export
out_path = "/home/chris/central-park-walk/models/furniture/cp_drinking_fountain.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
vcount = len(obj.data.vertices)
fcount = len(obj.data.polygons)
print(f"Exported Drinking Fountain to {out_path} ({vcount} verts, {fcount} faces)")

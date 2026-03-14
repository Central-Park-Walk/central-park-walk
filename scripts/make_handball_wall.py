"""Generate handball wall for Central Park Walk.

American handball court front wall:
- Concrete wall 6.1m (20ft) wide × 4.9m (16ft) tall × 0.3m thick
- Gray concrete material

Exports to models/furniture/cp_handball_wall.glb
"""

import bpy
import math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

WALL_W = 6.1   # 20ft
WALL_H = 4.9   # 16ft
WALL_T = 0.3   # thickness

bpy.ops.mesh.primitive_cube_add(size=1)
wall = bpy.context.active_object
wall.name = "HandballWall"
wall.scale = (WALL_W/2, WALL_H/2, WALL_T/2)
wall.location = (0, WALL_H/2, 0)
bpy.ops.object.transform_apply(location=True, scale=True)

# Material: concrete
mat = bpy.data.materials.new("Concrete")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.55, 0.53, 0.50, 1.0)
bsdf.inputs["Roughness"].default_value = 0.85

wall.data.materials.clear()
wall.data.materials.append(mat)

out_path = "/home/chris/central-park-walk/models/furniture/cp_handball_wall.glb"
bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB')
print(f"Exported Handball Wall to {out_path}")

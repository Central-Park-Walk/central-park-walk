"""Generate Central Park wayfinding sign for Central Park Walk.

The Central Park Conservancy uses distinctive brown wooden signs:
- Brown-stained wooden post (10cm square, 2.4m tall)
- Brown wooden sign board at top (60cm wide x 30cm tall x 3cm thick)
- Angled cap on top of post
- Placed at major path intersections

Upgraded: Blender 4.5 + PBR weathered wood, UV-mapped.
Run: blender4 --background --python scripts/make_park_sign.py
"""

import bpy
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from pbr_utils import make_pbr_material

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

wood = make_pbr_material("BrownWood", "weathered_wood", tint=(0.25, 0.15, 0.08),
                           tint_strength=0.45, normal_strength=1.0)

objects = []

# Post (10cm x 10cm x 2.4m, Z-up)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.2))
post = bpy.context.active_object
post.name = "Post"
post.scale = (0.05, 0.05, 1.2)
bpy.ops.object.transform_apply(location=True, scale=True)
post.data.materials.append(wood)
objects.append(post)

# Sign board (60cm x 30cm x 3cm)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.04, 2.25))
board = bpy.context.active_object
board.name = "Board"
board.scale = (0.30, 0.015, 0.15)
bpy.ops.object.transform_apply(location=True, scale=True)
board.data.materials.append(wood)
objects.append(board)

# Angled cap
bpy.ops.mesh.primitive_cone_add(radius1=0.07, radius2=0.0, depth=0.08, vertices=4, location=(0, 0, 2.44))
cap = bpy.context.active_object
cap.name = "Cap"
bpy.ops.object.transform_apply(location=True)
cap.data.materials.append(wood)
objects.append(cap)

# Join
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.object.join()
bpy.context.active_object.name = "ParkSign"

out = os.path.join(PROJ, "models", "furniture", "cp_park_sign.glb")
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True,
                            export_apply=True, export_image_format='JPEG', export_image_quality=85)
print(f"Exported: {out} ({os.path.getsize(out)//1024} KB)")

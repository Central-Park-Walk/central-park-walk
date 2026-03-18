"""Generate park entrance bollard for Central Park Walk.

Short cast-iron bollards at vehicle-restricted park entrances.
Classic NYC Parks design: tapered cylinder with rounded cap.
~0.85m tall, 0.15m diameter.

Upgraded: Blender 4.5 + PBR cast iron, UV-mapped.
Run: blender4 --background --python scripts/make_bollard.py
"""

import bpy
import math
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from pbr_utils import make_pbr_material

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

iron = make_pbr_material("Iron", "cast_iron", tint=(0.08, 0.08, 0.09), tint_strength=0.6,
                          metallic_fallback=0.85)
SEGS = 16

# Base flange
bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.04, vertices=SEGS, location=(0, 0, 0.02))
bpy.context.active_object.name = "base"
bpy.context.active_object.data.materials.append(iron)

# Lower taper
bpy.ops.mesh.primitive_cone_add(radius1=0.10, radius2=0.075, depth=0.30, vertices=SEGS, location=(0, 0, 0.19))
bpy.context.active_object.name = "lower_taper"
bpy.context.active_object.data.materials.append(iron)

# Main shaft
bpy.ops.mesh.primitive_cylinder_add(radius=0.075, depth=0.40, vertices=SEGS, location=(0, 0, 0.54))
bpy.context.active_object.name = "shaft"
bpy.context.active_object.data.materials.append(iron)

# Rounded cap (higher segments)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.085, segments=16, ring_count=10, location=(0, 0, 0.76))
bpy.context.active_object.name = "cap"
bpy.context.active_object.scale = (1.0, 1.0, 0.6)
bpy.ops.object.transform_apply(scale=True)
bpy.context.active_object.data.materials.append(iron)

# Join and export
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
bpy.context.active_object.name = "Bollard"

out = os.path.join(PROJ, "models", "furniture", "cp_bollard.glb")
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True,
                            export_apply=True, export_image_format='JPEG', export_image_quality=85)
print(f"Exported: {out} ({os.path.getsize(out)//1024} KB)")

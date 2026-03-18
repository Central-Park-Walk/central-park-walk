"""Generate park info/wayfinding kiosk for Central Park Walk.

Freestanding map/information display panels at major intersections.
Two-sided panel on steel frame, ~2m tall, park green color.
"""

import bpy
import math
import os

import sys as _sys
_sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "scripts"))
from pbr_utils import make_pbr_material


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

green = make_pbr_material("ParkGreen", "cast_iron", tint=(0.06, 0.06, 0.07), tint_strength=0.6)

panel_mat = make_pbr_material("MapPanel", "cast_iron", tint=(0.06, 0.06, 0.07), tint_strength=0.6)

steel = make_pbr_material("Steel", "cast_iron", tint=(0.06, 0.06, 0.07), tint_strength=0.6)


def box(name, x, y, z, sx, sy, sz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + sy, z))
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx * 2, sy * 2, sz * 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    return o


def cylinder(name, x, y, z, r, h, segs, mat):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=h, vertices=segs,
        location=(x, y + h / 2, z))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


# ── Base plate ──
box("base", 0, 0, 0, 0.40, 0.03, 0.20, steel)

# ── Two support posts ──
cylinder("left_post", -0.30, 0.03, 0, 0.03, 1.70, 8, green)
cylinder("right_post", 0.30, 0.03, 0, 0.03, 1.70, 8, green)

# ── Top bar connecting posts ──
box("top_bar", 0, 1.73, 0, 0.32, 0.025, 0.025, green)

# ── Map panel (large, slightly tilted) ──
box("map_panel", 0, 0.70, 0, 0.38, 0.50, 0.015, panel_mat)

# ── Header bar (dark green with "CENTRAL PARK" text area) ──
box("header", 0, 1.55, 0, 0.38, 0.08, 0.018, green)

# ── "You Are Here" marker dot ──
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=0.015, segments=8, ring_count=6,
    location=(0, 0.90, 0.018))
o = bpy.context.active_object
o.name = "marker_dot"
# Red dot
red = make_pbr_material("Red", "cast_iron", tint=(0.06, 0.06, 0.07), tint_strength=0.6)
o.data.materials.append(red)

# ── Join and export ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
bpy.context.active_object.name = "InfoKiosk"

# Fix orientation: scripts use Y-up, Blender is Z-up
bpy.context.active_object.rotation_euler = (math.pi/2, 0, 0)
bpy.ops.object.transform_apply(rotation=True)

outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "models", "furniture")
os.makedirs(outdir, exist_ok=True)
outpath = os.path.join(outdir, "cp_info_kiosk.glb")
bpy.ops.export_scene.gltf(filepath=outpath, export_format='GLB', export_image_format='JPEG', export_image_quality=85)
print(f"Exported: {outpath} ({os.path.getsize(outpath)} bytes)")

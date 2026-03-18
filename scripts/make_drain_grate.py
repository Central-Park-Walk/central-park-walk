"""Generate storm drain grate for Central Park Walk.

Cast iron grate at road/path intersections for drainage.
Rectangular frame with parallel bars. Sits flush with pavement.
~0.6m × 0.3m.
"""

import bpy
import math
import os

import sys as _sys
_sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "scripts"))
from pbr_utils import make_pbr_material


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

iron = make_pbr_material("Iron", "cast_iron", tint=(0.1, 0.1, 0.1), tint_strength=0.7)

W = 0.60   # grate width
D = 0.30   # grate depth
H = 0.02   # grate height
BAR_W = 0.015  # bar width
N_BARS = 8  # parallel bars


def box(name, x, y, z, sx, sy, sz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + sy, z))
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx * 2, sy * 2, sz * 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    return o


# ── Frame ──
# Front and back rails
box("frame_front", 0, 0, D / 2 - BAR_W / 2, W / 2, H / 2, BAR_W / 2, iron)
box("frame_back", 0, 0, -D / 2 + BAR_W / 2, W / 2, H / 2, BAR_W / 2, iron)
# Left and right rails
box("frame_left", -W / 2 + BAR_W / 2, 0, 0, BAR_W / 2, H / 2, D / 2, iron)
box("frame_right", W / 2 - BAR_W / 2, 0, 0, BAR_W / 2, H / 2, D / 2, iron)

# ── Parallel bars ──
inner_w = W - BAR_W * 2
spacing = inner_w / (N_BARS + 1)
for i in range(N_BARS):
    bx = -W / 2 + BAR_W + spacing * (i + 1)
    box(f"bar_{i}", bx, 0, 0, BAR_W / 2, H / 2, D / 2 - BAR_W, iron)

# ── Join and export ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
bpy.context.active_object.name = "DrainGrate"

# Fix orientation: scripts use Y-up, Blender is Z-up
bpy.context.active_object.rotation_euler = (math.pi/2, 0, 0)
bpy.ops.object.transform_apply(rotation=True)

outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "models", "furniture")
os.makedirs(outdir, exist_ok=True)
outpath = os.path.join(outdir, "cp_drain_grate.glb")
bpy.ops.export_scene.gltf(filepath=outpath, export_format='GLB', export_image_format='JPEG', export_image_quality=85)
print(f"Exported: {outpath} ({os.path.getsize(outpath)} bytes)")

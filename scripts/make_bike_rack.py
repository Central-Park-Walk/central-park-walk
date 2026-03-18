"""Generate bicycle rack for Central Park Walk.

NYC Parks standard inverted-U bike rack (aka "staple" rack).
Single galvanized steel tube bent into an inverted U shape.
~0.85m tall, 0.70m wide.

Upgraded: Blender 4.5 + PBR cast iron (galvanized), UV-mapped.
Run: blender4 --background --python scripts/make_bike_rack.py
"""

import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from pbr_utils import make_pbr_material

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

steel = make_pbr_material("Steel", "cast_iron", tint=(0.45, 0.44, 0.42), tint_strength=0.4,
                            metallic_fallback=0.90, normal_strength=0.5)

TUBE_R = 0.025
HEIGHT = 0.85
WIDTH = 0.70
SEGS = 12

# Build as a single continuous tube path (inverted U shape)
def make_tube_path(name, points, radius, segments, mat):
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    rings = []
    total_len = 0.0
    arc_lengths = [0.0]
    for i in range(1, len(points)):
        total_len += (points[i] - points[i - 1]).length
        arc_lengths.append(total_len)

    for i, pt in enumerate(points):
        if i < len(points) - 1:
            d = (points[i + 1] - pt).normalized()
        elif i > 0:
            d = (pt - points[i - 1]).normalized()
        else:
            d = Vector((0, 0, 1))
        if abs(d.z) < 0.99:
            side = d.cross(Vector((0, 0, 1))).normalized()
        else:
            side = d.cross(Vector((1, 0, 0))).normalized()
        up = side.cross(d).normalized()
        ring = []
        for j in range(segments):
            angle = 2 * math.pi * j / segments
            offset = side * math.cos(angle) * radius + up * math.sin(angle) * radius
            ring.append(bm.verts.new(pt + offset))
        rings.append(ring)

    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        v_lo = arc_lengths[i] / max(total_len, 0.001)
        v_hi = arc_lengths[i + 1] / max(total_len, 0.001)
        for j in range(segments):
            j2 = (j + 1) % segments
            face = bm.faces.new([rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]])
            face.smooth = True
            u_lo = j / segments
            u_hi = (j + 1) / segments
            for loop in face.loops:
                v_idx = loop.vert
                if v_idx == rings[i][j]: loop[uv_layer].uv = (u_lo, v_lo)
                elif v_idx == rings[i][j2]: loop[uv_layer].uv = (u_hi, v_lo)
                elif v_idx == rings[i + 1][j2]: loop[uv_layer].uv = (u_hi, v_hi)
                elif v_idx == rings[i + 1][j]: loop[uv_layer].uv = (u_lo, v_hi)

    # Cap ends
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

# Path: left leg up, semicircle across top, right leg down
pts = []
n_leg = 6
n_curve = 16
hw = WIDTH / 2

# Left leg (bottom to top)
for i in range(n_leg):
    t = i / (n_leg - 1)
    pts.append(Vector((-hw, 0, t * (HEIGHT - hw))))

# Semicircle at top
for i in range(1, n_curve):
    angle = math.pi * i / n_curve
    pts.append(Vector((-hw * math.cos(angle), 0, HEIGHT - hw + hw * math.sin(angle))))

# Right leg (top to bottom)
for i in range(n_leg):
    t = i / (n_leg - 1)
    pts.append(Vector((hw, 0, (HEIGHT - hw) * (1 - t))))

tube = make_tube_path("BikeRack_Tube", pts, TUBE_R, SEGS, steel)

# Ground anchor flanges
for side in [-1, 1]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.01, vertices=SEGS, location=(side * hw, 0, 0.005))
    bpy.context.active_object.name = f"anchor_{side}"
    bpy.context.active_object.data.materials.append(steel)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
bpy.context.active_object.name = "BikeRack"

out = os.path.join(PROJ, "models", "furniture", "cp_bike_rack.glb")
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True,
                            export_apply=True, export_image_format='JPEG', export_image_quality=85)
print(f"Exported: {out} ({os.path.getsize(out)//1024} KB)")

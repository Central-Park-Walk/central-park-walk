"""Generate NYC Parks wire mesh trash can for Central Park Walk.

The distinctive green wire-frame waste baskets used throughout NYC parks.
Cylindrical wire cage on a central post with peaked lid.
~0.9m tall, 0.45m diameter.
"""

import bpy
import math
import os

import sys as _sys
_sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))), "scripts"))
from pbr_utils import make_pbr_material


bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Painted dark "Central Park green" steel. The old near-black tint
# (0.08, 0.08, 0.09) + full metalness map rendered as a pure-black
# silhouette outdoors (no reflection probes; walk-around 2026-06-12
# cpw_009). Paint is dielectric: scalar low metallic, green-dominant tint.
green = make_pbr_material("ParkGreen", "cast_iron", tint=(0.043, 0.114, 0.057),
                          tint_strength=0.85, metallic_override=0.1)

steel = make_pbr_material("Steel", "cast_iron", tint=(0.043, 0.114, 0.057),
                          tint_strength=0.85, metallic_override=0.1)

CAN_R = 0.225    # radius
CAN_H = 0.75     # can height
POST_H = 0.90    # total height including post
POST_R = 0.025   # central post radius


def cylinder(name, x, y, z, r, h, segs, mat):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=h, vertices=segs,
        location=(x, y + h / 2, z))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


# ── Central post ──
cylinder("post", 0, 0, 0, POST_R, POST_H, 8, steel)

# ── Base plate ──
cylinder("base_plate", 0, 0, 0, CAN_R * 0.6, 0.015, 12, green)

# ── Wire cage (simplified as semi-transparent cylinder) ──
# Bottom ring
bpy.ops.mesh.primitive_torus_add(
    major_radius=CAN_R, minor_radius=0.008,
    major_segments=20, minor_segments=4,
    location=(0, 0.10, 0))
o = bpy.context.active_object
o.name = "bottom_ring"
o.data.materials.append(green)

# Middle ring
bpy.ops.mesh.primitive_torus_add(
    major_radius=CAN_R, minor_radius=0.008,
    major_segments=20, minor_segments=4,
    location=(0, 0.40, 0))
o = bpy.context.active_object
o.name = "mid_ring"
o.data.materials.append(green)

# Top ring
bpy.ops.mesh.primitive_torus_add(
    major_radius=CAN_R, minor_radius=0.008,
    major_segments=20, minor_segments=4,
    location=(0, CAN_H, 0))
o = bpy.context.active_object
o.name = "top_ring"
o.data.materials.append(green)

# Vertical wire bars (12 around the circumference)
for i in range(12):
    angle = math.pi * 2 * i / 12
    bx = math.cos(angle) * CAN_R
    bz = math.sin(angle) * CAN_R
    cylinder(f"bar_{i}", bx, 0.10, bz, 0.005, CAN_H - 0.10, 4, green)

# ── Peaked lid ──
bpy.ops.mesh.primitive_cone_add(
    radius1=CAN_R + 0.02, radius2=0.03,
    depth=0.12, vertices=12,
    location=(0, CAN_H + 0.06, 0))
lid = bpy.context.active_object
lid.name = "lid"
lid.data.materials.append(green)

# ── Join and export ──
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.join()
bpy.context.active_object.name = "WireTrashCan"

# Fix orientation: scripts use Y-up, Blender is Z-up
bpy.context.active_object.rotation_euler = (math.pi/2, 0, 0)
bpy.ops.object.transform_apply(rotation=True)

outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "models", "furniture")
os.makedirs(outdir, exist_ok=True)
outpath = os.path.join(outdir, "cp_wire_trash_can.glb")
bpy.ops.export_scene.gltf(filepath=outpath, export_format='GLB', export_image_format='JPEG', export_image_quality=85)
print(f"Exported: {outpath} ({os.path.getsize(outpath)} bytes)")

# The glTF exporter cannot express the ShaderNodeMix tint, so the baked
# GLB ships the raw gray Metal027 albedo. Patch baseColorFactor (glTF
# multiplies it with the texture) to get the painted CP-green basket.
import json
import struct
with open(outpath, 'rb') as f:
    data = f.read()
magic, ver, _total = struct.unpack_from('<III', data, 0)
clen, ctype = struct.unpack_from('<II', data, 12)
gltf = json.loads(data[20:20 + clen])
for m in gltf.get('materials', []):
    m.setdefault('pbrMetallicRoughness', {})['baseColorFactor'] = [0.11, 0.27, 0.15, 1.0]
payload = json.dumps(gltf, separators=(',', ':')).encode()
payload += b' ' * ((4 - len(payload) % 4) % 4)
rest = data[20 + clen:]
with open(outpath, 'wb') as f:
    f.write(struct.pack('<III', magic, ver, 12 + 8 + len(payload) + len(rest)))
    f.write(struct.pack('<II', len(payload), ctype))
    f.write(payload)
    f.write(rest)
print(f"Patched baseColorFactor (park green) — {os.path.getsize(outpath)} bytes")

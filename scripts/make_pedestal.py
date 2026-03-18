"""Generate stone pedestals for Central Park statues and monuments.

Central Park's 106+ statues sit on a variety of stone bases. Most are
gray granite (Westerly or Barre granite) with classical molding profiles.
Three variants cover the main pedestal types:

  Variant 0 — Standard rectangular pedestal (statues, sculptures)
    ~1.2m tall, 0.8m x 0.8m shaft, stepped base + cornice with molding
  Variant 1 — Column pedestal (busts)
    ~1.5m tall, 0.45m x 0.45m shaft, chamfered cap for bust mounting
  Variant 2 — Wide memorial base (memorials, monuments)
    ~0.8m tall, 1.4m x 0.9m, low stepped profile with wide inscription face

Materials: PBR granite and brownstone from ambientCG.
Exports: models/furniture/cp_pedestal.glb (3 variants as separate objects)

Upgraded: Blender 4.5 + PBR textures, UV-mapped.
Run: blender4 --background --python scripts/make_pedestal.py
"""

import bpy
import bmesh
import os
import sys
from mathutils import Vector

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "scripts"))
from pbr_utils import make_pbr_material

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)
for block in bpy.data.images:
    if block.users == 0:
        bpy.data.images.remove(block)

granite = make_pbr_material("GrayGranite", "granite", tint=(0.52, 0.50, 0.47),
                              tint_strength=0.35, normal_strength=1.0)
limestone = make_pbr_material("Limestone", "brownstone", tint=(0.65, 0.60, 0.52),
                                tint_strength=0.4, normal_strength=0.8)


def make_box(bm, uv_layer, cx, cz, sx, sy, sz):
    """UV-mapped box centered at (cx, 0, cz), half-extents sx/sz, full height sy starting at cz."""
    verts = []
    for dz in [-sz, sz]:
        for dy in [0, sy]:
            for dx in [-sx, sx]:
                verts.append(bm.verts.new((cx + dx, cz + dy, dz)))
    bm.verts.ensure_lookup_table()
    idx = [
        (0, 2, 6, 4), (1, 5, 7, 3),  # front/back
        (0, 1, 3, 2), (4, 6, 7, 5),  # bottom/top
        (0, 4, 5, 1), (2, 3, 7, 6),  # left/right
    ]
    base = len(bm.verts) - 8
    for f_idx in idx:
        face = bm.faces.new([bm.verts[base + i] for i in f_idx])
        for loop in face.loops:
            co = loop.vert.co
            loop[uv_layer].uv = (co.x * 1.5 + co.z * 1.5, co.y * 1.5)


def build_variant(name, tiers, mat):
    """Build a pedestal from a list of (cx, cz, sx, sy, sz) tier tuples."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for cx, cz, sx, sy, sz in tiers:
        make_box(bm, uv_layer, cx, cz, sx, sy, sz)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


# Standard rectangular pedestal
standard = build_variant("Pedestal_Standard", [
    (0, 0.00, 0.55, 0.10, 0.55),   # bottom step
    (0, 0.10, 0.48, 0.08, 0.48),   # middle step
    (0, 0.18, 0.43, 0.06, 0.43),   # top step
    (0, 0.24, 0.38, 0.72, 0.38),   # main shaft
    (0, 0.96, 0.42, 0.04, 0.42),   # cornice
    (0, 1.00, 0.44, 0.05, 0.44),   # cap plate
    (0, 1.05, 0.40, 0.03, 0.40),   # crown
], granite)

# Column pedestal (busts)
column = build_variant("Pedestal_Column", [
    (0, 0.00, 0.40, 0.08, 0.40),   # base
    (0, 0.08, 0.35, 0.05, 0.35),   # base step
    (0, 0.13, 0.25, 1.10, 0.25),   # shaft
    (0, 1.23, 0.30, 0.04, 0.30),   # capital
    (0, 1.27, 0.33, 0.06, 0.33),   # capital top
    (0, 1.33, 0.28, 0.03, 0.28),   # mount plate
], granite)
column.location = (2, 0, 0)

# Wide memorial base
memorial = build_variant("Pedestal_Memorial", [
    (0, 0.00, 0.80, 0.08, 0.55),   # base
    (0, 0.08, 0.72, 0.06, 0.48),   # step
    (0, 0.14, 0.65, 0.45, 0.42),   # inscription body
    (0, 0.59, 0.68, 0.04, 0.45),   # top ledge
    (0, 0.63, 0.62, 0.05, 0.40),   # cap
], limestone)
memorial.location = (4, 0, 0)

# Export
bpy.ops.object.select_all(action='SELECT')
out = os.path.join(PROJ, "models", "furniture", "cp_pedestal.glb")
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True,
                            export_apply=True, export_image_format='JPEG', export_image_quality=85)
sz_kb = os.path.getsize(out) / 1024
print(f"Exported pedestal variants to {out} ({sz_kb:.0f} KB)")
print(f"  Standard: ~1.08m tall (granite)")
print(f"  Column:   ~1.36m tall (granite)")
print(f"  Memorial: ~0.68m tall (limestone)")

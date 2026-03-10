"""Generate Cleopatra's Needle (Central Park obelisk).

The oldest man-made object in Central Park: a 3,500-year-old Egyptian
obelisk of red Syene granite, erected ~1461 BC by Thutmose III.
Moved to Central Park in 1881 by Lt. Cmdr. Henry Gorringe.

Dimensions (from NYC Parks / Central Park Conservancy):
  Shaft: 21.08m (69'2") tall, tapers from 2.34m (7'8.5") base to 1.60m (5'3") top
  Pyramidion: ~1.8m tall pointed cap
  Pedestal: stepped granite base ~3.0m tall, 3.0m × 3.0m
  Bronze crabs: 4 replicas of Roman-era supports at pedestal corners

Materials:
  'RedGranite' — weathered Syene granite (reddish-gray, heavily eroded on west face)
  'Bronze' — patinated bronze for decorative crabs
  'GrayGranite' — pedestal stone (gray Westerly granite)

Exports: models/furniture/cp_obelisk.glb
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# --- Materials ---
granite_mat = bpy.data.materials.new(name="RedGranite")
granite_mat.use_nodes = True
bsdf = granite_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.52, 0.38, 0.32, 1.0)  # weathered red granite
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 0.82

pedestal_mat = bpy.data.materials.new(name="GrayGranite")
pedestal_mat.use_nodes = True
bsdf_p = pedestal_mat.node_tree.nodes["Principled BSDF"]
bsdf_p.inputs["Base Color"].default_value = (0.55, 0.53, 0.50, 1.0)  # gray Westerly granite
bsdf_p.inputs["Metallic"].default_value = 0.0
bsdf_p.inputs["Roughness"].default_value = 0.78

bronze_mat = bpy.data.materials.new(name="Bronze")
bronze_mat.use_nodes = True
bsdf_b = bronze_mat.node_tree.nodes["Principled BSDF"]
bsdf_b.inputs["Base Color"].default_value = (0.22, 0.30, 0.20, 1.0)  # patinated bronze
bsdf_b.inputs["Metallic"].default_value = 0.6
bsdf_b.inputs["Roughness"].default_value = 0.55

# --- Dimensions (metres) ---
# Pedestal
PED_BASE_W = 3.00     # bottom step width
PED_H = 3.00          # total pedestal height
PED_STEPS = 3         # number of stepped tiers

# Obelisk shaft
SHAFT_H = 21.08       # shaft height (69'2")
BASE_HW = 2.34 / 2    # half-width at base (7'8.5")
TOP_HW = 1.60 / 2     # half-width at top (5'3")

# Pyramidion (pointed cap)
PYRAM_H = 1.80        # pyramidion height

# Bronze crab supports
CRAB_SIZE = 0.35      # approximate crab body size
CRAB_H = 0.15         # crab height

all_parts = []


def make_pedestal():
    """Stepped granite pedestal — 3 tiers."""
    objs = []
    step_h = PED_H / PED_STEPS
    for i in range(PED_STEPS):
        t = i / PED_STEPS
        # Each tier narrows toward the top
        w = PED_BASE_W * (1.0 - t * 0.15)
        hw = w / 2
        z = i * step_h + step_h / 2

        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0, 0, z)
        )
        step = bpy.context.active_object
        step.scale = (hw, hw, step_h / 2)
        step.name = f"pedestal_step_{i}"
        step.data.materials.append(pedestal_mat)
        objs.append(step)

    return objs


def make_shaft():
    """Tapered rectangular shaft with slight entasis."""
    bm = bmesh.new()

    # Build shaft as series of quads tapering from base to top
    n_segs = 8  # vertical segments
    rings = []

    for i in range(n_segs + 1):
        t = i / n_segs
        z = PED_H + t * SHAFT_H
        # Linear taper
        hw = BASE_HW + t * (TOP_HW - BASE_HW)
        corners = [
            bm.verts.new(Vector((-hw, -hw, z))),
            bm.verts.new(Vector(( hw, -hw, z))),
            bm.verts.new(Vector(( hw,  hw, z))),
            bm.verts.new(Vector((-hw,  hw, z))),
        ]
        rings.append(corners)

    bm.verts.ensure_lookup_table()

    # Side faces
    for i in range(n_segs):
        for j in range(4):
            j2 = (j + 1) % 4
            bm.faces.new([rings[i][j], rings[i][j2], rings[i+1][j2], rings[i+1][j]])

    # Bottom and top caps
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])

    mesh = bpy.data.meshes.new("shaft")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("shaft", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(granite_mat)
    return [obj]


def make_pyramidion():
    """Pointed pyramidal cap."""
    bm = bmesh.new()

    z_base = PED_H + SHAFT_H
    z_top = z_base + PYRAM_H
    hw = TOP_HW

    # Base corners
    base = [
        bm.verts.new(Vector((-hw, -hw, z_base))),
        bm.verts.new(Vector(( hw, -hw, z_base))),
        bm.verts.new(Vector(( hw,  hw, z_base))),
        bm.verts.new(Vector((-hw,  hw, z_base))),
    ]

    # Apex
    apex = bm.verts.new(Vector((0, 0, z_top)))

    bm.verts.ensure_lookup_table()

    # Four triangular faces
    for j in range(4):
        j2 = (j + 1) % 4
        bm.faces.new([base[j], base[j2], apex])

    # Base cap
    bm.faces.new(base[::-1])

    mesh = bpy.data.meshes.new("pyramidion")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("pyramidion", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(granite_mat)
    return [obj]


def make_crabs():
    """Four bronze crab supports at pedestal corners."""
    objs = []
    # Crabs sit at the top of the pedestal, at the four corners
    crab_offset = PED_BASE_W * 0.85 * 0.5  # near corners of top step
    crab_z = PED_H - 0.05  # sitting on top of pedestal

    for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        cx = sx * crab_offset
        cy = sy * crab_offset

        # Simplified crab body — flattened ellipsoid
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=CRAB_SIZE / 2, segments=8, ring_count=6,
            location=(cx, cy, crab_z + CRAB_H / 2)
        )
        crab = bpy.context.active_object
        crab.scale = (1.0, 0.8, 0.4)  # flatten
        crab.name = f"crab_{sx}_{sy}"
        crab.data.materials.append(bronze_mat)
        for poly in crab.data.polygons:
            poly.use_smooth = True
        objs.append(crab)

    return objs


# --- Build ---
all_parts.extend(make_pedestal())
all_parts.extend(make_shaft())
all_parts.extend(make_pyramidion())
all_parts.extend(make_crabs())

# Apply all transforms
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Join all parts
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = all_parts[0]
bpy.ops.object.join()

obelisk = bpy.context.active_object
obelisk.name = "CP_Obelisk"

# Set origin so bottom at Z=0
bbox = [obelisk.matrix_world @ Vector(c) for c in obelisk.bound_box]
min_z = min(v.z for v in bbox)
obelisk.location.z -= min_z
bpy.ops.object.transform_apply(location=True)

# Export GLB
out_path = "/home/chris/central-park-walk/models/furniture/cp_obelisk.glb"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)

bbox2 = [obelisk.matrix_world @ Vector(c) for c in obelisk.bound_box]
height = max(v.z for v in bbox2) - min(v.z for v in bbox2)
print(f"Exported Cleopatra's Needle to {out_path}")
print(f"  Height: {height:.2f}m  ({height * 3.281:.1f} ft)")
print(f"  Faces: {len(obelisk.data.polygons)}")

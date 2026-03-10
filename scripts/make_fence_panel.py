"""
Generate Central Park iron fence panel model for Central Park Walk.

The standard NYC Parks Department low iron fence used throughout Central Park:
- ~1.0m (40") tall
- Black painted cast iron
- Pointed pickets (spear-tip finials) at ~100mm (4") spacing
- Top rail with a slight outward curve
- Bottom rail sits ~50mm above ground

This model creates a single 2m fence panel (one repeating unit between posts).
The game tiles these along OSM fence polylines via the existing _build_fence_segments.

Generates: models/furniture/fence_panel.glb
Run: blender --background --python scripts/make_fence_panel.py
"""

import bpy
import bmesh
import math
from mathutils import Vector

OUT_PATH = "/home/chris/central-park-walk/models/furniture/fence_panel.glb"

PANEL_WIDTH = 2.0        # distance between posts
FENCE_HEIGHT = 1.0       # total height
POST_SIZE = 0.04         # post cross-section (square)
PICKET_SIZE = 0.012      # picket cross-section
PICKET_SPACING = 0.10    # center-to-center
RAIL_HEIGHT = 0.025      # rail cross-section height
RAIL_DEPTH = 0.015       # rail cross-section depth
FINIAL_HEIGHT = 0.035    # spear tip above top rail
BOTTOM_GAP = 0.05        # gap below bottom rail

# ---- Scene cleanup ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ---- Material: black cast iron ----
iron_mat = bpy.data.materials.new(name="FenceIron")
iron_mat.use_nodes = True
bsdf = iron_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1.0)  # near-black
bsdf.inputs["Roughness"].default_value = 0.65
bsdf.inputs["Metallic"].default_value = 0.85


def make_box(bm, cx, cy, cz, sx, sy, sz):
    """Add an axis-aligned box to bmesh. cx/cy/cz = center, sx/sy/sz = half-extents."""
    verts = []
    for dz in (-1, 1):
        for dy in (-1, 1):
            for dx in (-1, 1):
                verts.append(bm.verts.new((cx + dx*sx, cy + dy*sy, cz + dz*sz)))
    # 6 faces (right-hand winding)
    idx = [(0,1,3,2), (4,6,7,5), (0,4,5,1), (2,3,7,6), (0,2,6,4), (1,5,7,3)]
    for face_idx in idx:
        bm.faces.new([verts[i] for i in face_idx])


def make_picket(bm, x, y):
    """Create one pointed picket at position (x, y) in the XY plane, Z-up."""
    bottom_z = BOTTOM_GAP
    top_z = FENCE_HEIGHT - RAIL_HEIGHT
    hs = PICKET_SIZE * 0.5

    # Main shaft (box)
    make_box(bm, x, y, (bottom_z + top_z) / 2, hs, hs, (top_z - bottom_z) / 2)

    # Spear-tip finial (pyramid)
    tip_base_z = top_z
    tip_top_z = top_z + FINIAL_HEIGHT
    # 4 base vertices + 1 tip
    v_base = [
        bm.verts.new((x - hs * 1.2, y - hs * 1.2, tip_base_z)),
        bm.verts.new((x + hs * 1.2, y - hs * 1.2, tip_base_z)),
        bm.verts.new((x + hs * 1.2, y + hs * 1.2, tip_base_z)),
        bm.verts.new((x - hs * 1.2, y + hs * 1.2, tip_base_z)),
    ]
    v_tip = bm.verts.new((x, y, tip_top_z))
    # 4 triangular faces
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([v_base[i], v_base[j], v_tip])
    # Bottom face
    bm.faces.new(list(reversed(v_base)))


def make_post(bm, x, y):
    """Create a fence post (thicker square post with ball finial)."""
    hs = POST_SIZE * 0.5
    # Main post shaft
    make_box(bm, x, y, FENCE_HEIGHT * 0.5, hs, hs, FENCE_HEIGHT * 0.5)

    # Ball finial on top
    ball_r = POST_SIZE * 0.6
    ball_z = FENCE_HEIGHT + ball_r * 0.7
    # Approximate sphere with 3 stacked rings
    n_ring = 6
    rings = []
    n_slices = 5
    for si in range(n_slices + 1):
        phi = math.pi * si / n_slices
        rr = ball_r * math.sin(phi)
        zz = ball_z + ball_r * math.cos(phi)
        ring = []
        for ri in range(n_ring):
            theta = 2 * math.pi * ri / n_ring
            ring.append(bm.verts.new((x + rr * math.cos(theta),
                                       y + rr * math.sin(theta),
                                       zz)))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for si in range(n_slices):
        for ri in range(n_ring):
            ri2 = (ri + 1) % n_ring
            bm.faces.new([rings[si][ri], rings[si][ri2],
                          rings[si+1][ri2], rings[si+1][ri]])


# ---- Build the fence panel ----
bm = bmesh.new()

# Two end posts
make_post(bm, -PANEL_WIDTH / 2, 0)
make_post(bm, PANEL_WIDTH / 2, 0)

# Top rail
top_rail_z = FENCE_HEIGHT - RAIL_HEIGHT / 2
make_box(bm, 0, 0, top_rail_z, PANEL_WIDTH / 2, RAIL_DEPTH / 2, RAIL_HEIGHT / 2)

# Bottom rail
bot_rail_z = BOTTOM_GAP + RAIL_HEIGHT / 2
make_box(bm, 0, 0, bot_rail_z, PANEL_WIDTH / 2, RAIL_DEPTH / 2, RAIL_HEIGHT / 2)

# Middle rail (decorative, at ~40% height)
mid_rail_z = BOTTOM_GAP + (FENCE_HEIGHT - BOTTOM_GAP) * 0.40
make_box(bm, 0, 0, mid_rail_z, PANEL_WIDTH / 2, RAIL_DEPTH / 2, RAIL_HEIGHT * 0.4)

# Pickets between posts
half_w = PANEL_WIDTH / 2 - POST_SIZE
n_pickets = int(half_w * 2 / PICKET_SPACING)
for i in range(n_pickets):
    px = -half_w + (i + 0.5) * PICKET_SPACING
    # Skip if too close to posts
    if abs(px) > half_w - PICKET_SIZE:
        continue
    make_picket(bm, px, 0)

# Create mesh object
mesh = bpy.data.meshes.new("FencePanel")
bm.to_mesh(mesh)
bm.free()

obj = bpy.data.objects.new("FencePanel", mesh)
bpy.context.collection.objects.link(obj)
obj.data.materials.append(iron_mat)

# Smooth shading on post ball finials, flat on everything else
for poly in obj.data.polygons:
    # Smooth the ball finial faces (high-z center)
    center_z = sum(obj.data.vertices[vi].co.z for vi in poly.vertices) / len(poly.vertices)
    if center_z > FENCE_HEIGHT:
        poly.use_smooth = True

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

n_faces = len(obj.data.polygons)
n_verts = len(obj.data.vertices)
print(f"\nFence panel: {n_verts} verts, {n_faces} faces")
print(f"  Panel width: {PANEL_WIDTH}m, height: {FENCE_HEIGHT}m")
print(f"  ~{n_pickets} pickets at {PICKET_SPACING*1000:.0f}mm spacing")

# ---- Export GLB ----
bpy.ops.export_scene.gltf(
    filepath=OUT_PATH,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"Exported to {OUT_PATH}")

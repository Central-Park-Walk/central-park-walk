"""Generate vine models for Central Park.

Two invasive species that dominate woodland edges:
  - Porcelain Berry (Ampelopsis brevipedunculata): 5 hanging strand variants
  - Oriental Bittersweet (Celastrus orbiculatus): 5 hanging strand variants
  - Trunk wraps: 3 variants (thick woody vine spiraling up trunks)

Each strand: thin stem ribbon + leaf quads, origin at top (attachment point).
Strands hang downward from canopy edges. Trunk wraps spiral upward from base.

Exports to models/vegetation/cp_vines.glb
"""

import bpy
import bmesh
import math
import random
import os
from mathutils import Vector


# --- Clear scene ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# --- Materials (overridden by custom shader in Godot, but needed for export) ---
stem_mat = bpy.data.materials.new(name="VineStem")
stem_mat.use_nodes = True
bsdf = stem_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.28, 0.22, 0.14, 1.0)
bsdf.inputs["Roughness"].default_value = 0.80

leaf_mat = bpy.data.materials.new(name="VineLeaf")
leaf_mat.use_nodes = True
bsdf = leaf_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.18, 0.35, 0.12, 1.0)
bsdf.inputs["Roughness"].default_value = 0.55


def make_vine_strand(name, seed, length, n_leaves, stem_radius=0.008):
    """Create a vine strand hanging from origin downward (-Z in Blender = -Y in Godot).

    Stem is a thin ribbon of connected quads. Leaves are individual quads
    sprouting outward from the stem at random intervals.
    UV convention: UV.x near 0.5 = stem, UV.x near 0 or 1 = leaf.
    """
    rng = random.Random(seed)

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # --- Path: gentle hanging curve from origin ---
    n_segs = 8
    path = []
    drift_angle = rng.uniform(0, math.tau)
    drift_mag = length * 0.06

    for i in range(n_segs + 1):
        t = i / n_segs
        z = -length * t
        # Slight lateral sway (sine curve + noise)
        sway = math.sin(t * math.pi) * drift_mag
        x = math.cos(drift_angle) * sway + rng.gauss(0, 0.015) * (t + 0.2)
        y = math.sin(drift_angle) * sway + rng.gauss(0, 0.015) * (t + 0.2)
        path.append(Vector((x, y, z)))

    # --- Stem ribbon: two verts per path point ---
    stem_verts = []
    for i, pt in enumerate(path):
        t = i / n_segs
        r = stem_radius * (1.0 - t * 0.5)
        # Ribbon perpendicular to drift direction
        perp = Vector((-math.sin(drift_angle), math.cos(drift_angle), 0.0))
        v1 = bm.verts.new(pt - perp * r)
        v2 = bm.verts.new(pt + perp * r)
        stem_verts.append((v1, v2))

    bm.verts.ensure_lookup_table()

    for i in range(n_segs):
        v1, v2 = stem_verts[i]
        v3, v4 = stem_verts[i + 1]
        t0 = i / n_segs
        t1 = (i + 1) / n_segs
        face = bm.faces.new([v1, v2, v4, v3])
        face.smooth = True
        face.material_index = 0
        loops = list(face.loops)
        loops[0][uv_layer].uv = (0.45, t0)
        loops[1][uv_layer].uv = (0.55, t0)
        loops[2][uv_layer].uv = (0.55, t1)
        loops[3][uv_layer].uv = (0.45, t1)

    # --- Leaf quads along the stem ---
    for j in range(n_leaves):
        t = rng.uniform(0.10, 0.92)
        seg_f = t * n_segs
        seg_i = min(int(seg_f), n_segs - 1)
        seg_frac = seg_f - seg_i
        pos = path[seg_i].lerp(path[min(seg_i + 1, n_segs)], seg_frac)

        # Leaf sprouts outward at random angle
        angle = rng.uniform(0, math.tau)
        leaf_size = rng.uniform(0.06, 0.14)

        right = Vector((math.cos(angle), math.sin(angle), 0.0)) * leaf_size * 0.5
        up = Vector((0, 0, 1)) * leaf_size * 0.75
        # Small tilt for natural look
        tilt = Vector((0, 0, -leaf_size * 0.15 * rng.random()))
        center = pos + right.normalized() * (stem_radius + 0.01 + rng.uniform(0, 0.02))

        v1 = bm.verts.new(center - right + tilt)
        v2 = bm.verts.new(center + right + tilt)
        v3 = bm.verts.new(center + right + up)
        v4 = bm.verts.new(center - right + up)
        face = bm.faces.new([v1, v2, v3, v4])
        face.smooth = True
        face.material_index = 1
        loops = list(face.loops)
        loops[0][uv_layer].uv = (0.0, 0.0)
        loops[1][uv_layer].uv = (1.0, 0.0)
        loops[2][uv_layer].uv = (1.0, 1.0)
        loops[3][uv_layer].uv = (0.0, 1.0)

    # --- Berry clusters (small quads at some leaf positions) ---
    n_berries = max(1, n_leaves // 3)
    for j in range(n_berries):
        t = rng.uniform(0.25, 0.85)
        seg_f = t * n_segs
        seg_i = min(int(seg_f), n_segs - 1)
        seg_frac = seg_f - seg_i
        pos = path[seg_i].lerp(path[min(seg_i + 1, n_segs)], seg_frac)

        angle = rng.uniform(0, math.tau)
        berry_size = rng.uniform(0.02, 0.04)

        right = Vector((math.cos(angle), math.sin(angle), 0.0)) * berry_size
        up = Vector((0, 0, 1)) * berry_size
        center = pos + right.normalized() * (stem_radius + 0.03)
        center.z -= berry_size * 0.5  # hang slightly below stem

        v1 = bm.verts.new(center - right)
        v2 = bm.verts.new(center + right)
        v3 = bm.verts.new(center + right + up)
        v4 = bm.verts.new(center - right + up)
        face = bm.faces.new([v1, v2, v3, v4])
        face.smooth = True
        face.material_index = 1
        # UV: berry uses specific region (UV.y > 0.9) for shader detection
        loops = list(face.loops)
        loops[0][uv_layer].uv = (0.0, 0.90)
        loops[1][uv_layer].uv = (1.0, 0.90)
        loops[2][uv_layer].uv = (1.0, 1.00)
        loops[3][uv_layer].uv = (0.0, 1.00)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(stem_mat)
    mesh.materials.append(leaf_mat)
    return obj


def make_trunk_wrap(name, seed, height=3.0, wrap_radius=0.15, n_turns=2.5, n_leaves=6):
    """Create a vine spiraling around an imaginary trunk, origin at base."""
    rng = random.Random(seed)

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    n_pts = int(n_turns * 12)
    path = []
    vine_r = 0.014

    for i in range(n_pts + 1):
        t = i / n_pts
        angle = t * n_turns * math.tau
        z = height * t
        r = wrap_radius + rng.gauss(0, 0.008)
        x = math.cos(angle) * r
        y = math.sin(angle) * r
        path.append(Vector((x, y, z)))

    # Stem ribbon along spiral
    stem_verts = []
    for i, pt in enumerate(path):
        t = i / n_pts
        r = vine_r * (1.0 - t * 0.3)
        # Face outward from center
        outward = Vector((pt.x, pt.y, 0.0))
        if outward.length > 0.001:
            outward = outward.normalized() * r
        else:
            outward = Vector((r, 0, 0))
        v1 = bm.verts.new(pt - outward)
        v2 = bm.verts.new(pt + outward)
        stem_verts.append((v1, v2))

    bm.verts.ensure_lookup_table()

    for i in range(n_pts):
        v1, v2 = stem_verts[i]
        v3, v4 = stem_verts[i + 1]
        t0 = i / n_pts
        t1 = (i + 1) / n_pts
        face = bm.faces.new([v1, v2, v4, v3])
        face.smooth = True
        face.material_index = 0
        loops = list(face.loops)
        loops[0][uv_layer].uv = (0.45, t0)
        loops[1][uv_layer].uv = (0.55, t0)
        loops[2][uv_layer].uv = (0.55, t1)
        loops[3][uv_layer].uv = (0.45, t1)

    # Leaf quads sprouting outward from spiral
    for j in range(n_leaves):
        t = rng.uniform(0.15, 0.85)
        seg_f = t * n_pts
        seg_i = min(int(seg_f), n_pts - 1)
        seg_frac = seg_f - seg_i
        pos = path[seg_i].lerp(path[min(seg_i + 1, n_pts)], seg_frac)

        angle = rng.uniform(0, math.tau)
        leaf_size = rng.uniform(0.05, 0.09)
        right = Vector((math.cos(angle), math.sin(angle), 0.0)) * leaf_size * 0.5
        up = Vector((0, 0, 1)) * leaf_size * 0.7
        outward_dir = Vector((pos.x, pos.y, 0.0))
        if outward_dir.length > 0.001:
            outward_dir = outward_dir.normalized()
        else:
            outward_dir = Vector((1, 0, 0))
        center = pos + outward_dir * (vine_r + 0.01)

        v1 = bm.verts.new(center - right)
        v2 = bm.verts.new(center + right)
        v3 = bm.verts.new(center + right + up)
        v4 = bm.verts.new(center - right + up)
        face = bm.faces.new([v1, v2, v3, v4])
        face.smooth = True
        face.material_index = 1
        loops = list(face.loops)
        loops[0][uv_layer].uv = (0.0, 0.0)
        loops[1][uv_layer].uv = (1.0, 0.0)
        loops[2][uv_layer].uv = (1.0, 1.0)
        loops[3][uv_layer].uv = (0.0, 1.0)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(stem_mat)
    mesh.materials.append(leaf_mat)
    return obj


# --- Create all variants ---
objs = []
spacing = 2.0

# Porcelain Berry: 5 strand variants (2-4m, many leaves)
for i in range(5):
    rng_v = random.Random(100 + i)
    length = rng_v.uniform(2.0, 4.0)
    n_leaves = rng_v.randint(8, 14)
    obj = make_vine_strand(
        "Vine_PorcelainBerry_%s" % chr(65 + i),
        seed=100 + i, length=length, n_leaves=n_leaves,
        stem_radius=0.007
    )
    obj.location = (i * spacing, 0, 0)
    objs.append(obj)

# Oriental Bittersweet: 5 strand variants (3-6m, thicker stem, more leaves)
for i in range(5):
    rng_v = random.Random(200 + i)
    length = rng_v.uniform(3.0, 6.0)
    n_leaves = rng_v.randint(10, 18)
    obj = make_vine_strand(
        "Vine_Bittersweet_%s" % chr(65 + i),
        seed=200 + i, length=length, n_leaves=n_leaves,
        stem_radius=0.012
    )
    obj.location = ((5 + i) * spacing, 0, 0)
    objs.append(obj)

# Trunk wraps: 3 variants (spiral around imaginary trunk)
for i in range(3):
    rng_v = random.Random(300 + i)
    height = rng_v.uniform(2.0, 4.0)
    n_leaves = rng_v.randint(4, 8)
    n_turns = rng_v.uniform(2.0, 3.5)
    obj = make_trunk_wrap(
        "Vine_TrunkWrap_%s" % chr(65 + i),
        seed=300 + i, height=height, n_leaves=n_leaves,
        n_turns=n_turns
    )
    obj.location = ((10 + i) * spacing, 0, 0)
    objs.append(obj)

# Apply transforms and export
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_path = os.path.join(out_dir, "models", "vegetation", "cp_vines.glb")
bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print("Exported %d vine models to %s" % (len(objs), out_path))

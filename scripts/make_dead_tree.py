"""
Generate standing dead tree (snag) model for Central Park Walk.

Standing dead trees are natural features of mature woodland areas like
the North Woods and the Ramble. They provide dramatic silhouettes,
especially in winter. Character: broken top, missing branches, bark
sloughing off, sometimes leaning.

Key characteristics:
  - Broken/snapped crown (top 20-40% missing)
  - 1-3 remaining dead branch stubs (no leaves)
  - Irregular bark, some sections bare wood showing
  - Slight lean (wind/decay)
  - Thinner than live trees of same species

Generates 5 variants → models/trees/dead.glb
Run: blender --background --python scripts/make_dead_tree.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ---- Configuration ----
TREE_H = 4.0              # shorter than live trees (top broken off)
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/dead.glb"

TRUNK_SEGS = 7
BRANCH_SEGS = 5
SUB_SEGS = 4

# ---- Scene cleanup ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ---- Material: weathered dead wood (gray, cracked) ----
dead_mat = bpy.data.materials.new(name="DeadWood")
dead_mat.use_nodes = True
bsdf = dead_mat.node_tree.nodes["Principled BSDF"]
# Silver-gray weathered wood — sun-bleached, no bark
bsdf.inputs["Base Color"].default_value = (0.42, 0.38, 0.34, 1.0)
bsdf.inputs["Roughness"].default_value = 0.92  # very rough, splintered


# ---- Geometry helpers ----

def make_tube(name, points, r_start, r_end, segments, mat):
    bm = bmesh.new()
    rings = []
    n = len(points)
    for i, pt in enumerate(points):
        t = i / max(n - 1, 1)
        r = r_start + (r_end - r_start) * t
        if i < n - 1:
            fwd = (points[i + 1] - pt).normalized()
        else:
            fwd = (pt - points[i - 1]).normalized()
        if abs(fwd.dot(Vector((0, 0, 1)))) < 0.95:
            side = fwd.cross(Vector((0, 0, 1))).normalized()
        else:
            side = fwd.cross(Vector((1, 0, 0))).normalized()
        up = side.cross(fwd).normalized()
        ring = []
        for j in range(segments):
            a = 2.0 * math.pi * j / segments
            offset = side * math.cos(a) * r + up * math.sin(a) * r
            ring.append(bm.verts.new(pt + offset))
        rings.append(ring)
    bm.verts.ensure_lookup_table()
    for i in range(len(rings) - 1):
        for j in range(segments):
            j2 = (j + 1) % segments
            bm.faces.new([rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]])
    if len(rings) > 0 and len(rings[0]) >= 3:
        bm.faces.new(list(reversed(rings[0])))
    if len(rings) > 0 and len(rings[-1]) >= 3:
        bm.faces.new(rings[-1])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def bezier_point(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (p0 * u * u * u +
            p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t +
            p3 * t * t * t)


def make_dead_variant(vi, seed):
    """Generate one standing dead tree (snag) variant."""
    rng = random.Random(seed)
    parts = []

    trunk_r_base = rng.uniform(0.10, 0.16)
    trunk_r_top = rng.uniform(0.04, 0.08)

    # Lean angle (dead trees often lean)
    lean_angle = rng.uniform(0, 2.0 * math.pi)
    lean_amount = rng.uniform(0.05, 0.20)
    lean_x = math.cos(lean_angle) * lean_amount
    lean_y = math.sin(lean_angle) * lean_amount

    # Broken top: tree doesn't reach full height
    break_frac = rng.uniform(0.55, 0.85)
    actual_h = TREE_H * break_frac

    # ---- Trunk: leaning, broken top ----
    n_trunk = 8
    trunk_pts = []
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * actual_h
        # Increasing lean with height
        trunk_pts.append(Vector((
            lean_x * t * t + rng.uniform(-0.02, 0.02),
            lean_y * t * t + rng.uniform(-0.02, 0.02),
            z)))
    parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                            trunk_r_base, trunk_r_top, TRUNK_SEGS, dead_mat))

    # ---- Root flare: more pronounced on dead trees ----
    n_roots = rng.randint(3, 5)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.4, 0.4)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.15, 0.30)
        root_pts = [
            Vector((0, 0, 0.08)),
            Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.03)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                trunk_r_base * 0.50, 0.015, SUB_SEGS, dead_mat))

    # ---- Dead branch stubs: broken off, only 1-3 remaining ----
    n_stubs = rng.randint(1, 3)
    for b in range(n_stubs):
        # Stubs emerge from lower-middle trunk
        t_start = rng.uniform(0.25, 0.70)
        idx = int(t_start * (len(trunk_pts) - 1))
        origin = trunk_pts[idx].copy()

        stub_angle = rng.uniform(0, 2.0 * math.pi)
        dx = math.cos(stub_angle)
        dy = math.sin(stub_angle)
        stub_len = rng.uniform(0.3, 1.0)
        # Dead branches angle downward (gravity + decay)
        droop = rng.uniform(-0.20, 0.05)

        stub_pts = []
        for sp in range(4):
            st = sp / 3.0
            stub_pts.append(Vector((
                origin.x + dx * stub_len * st,
                origin.y + dy * stub_len * st,
                origin.z + stub_len * st * 0.08 + st * droop)))

        r_start = rng.uniform(0.020, 0.040)
        parts.append(make_tube(f"stub_{vi}_{b}", stub_pts,
                                r_start, r_start * 0.4, BRANCH_SEGS, dead_mat))

        # Some stubs have a secondary fork
        if rng.random() > 0.5:
            fork_origin = stub_pts[2].copy()
            fork_angle = stub_angle + rng.uniform(-0.8, 0.8)
            fork_dx = math.cos(fork_angle)
            fork_dy = math.sin(fork_angle)
            fork_len = rng.uniform(0.15, 0.45)
            fork_pts = []
            for fp in range(3):
                ft = fp / 2.0
                fork_pts.append(Vector((
                    fork_origin.x + fork_dx * fork_len * ft,
                    fork_origin.y + fork_dy * fork_len * ft,
                    fork_origin.z + fork_len * ft * 0.03 - ft * 0.08)))
            parts.append(make_tube(f"fork_{vi}_{b}", fork_pts,
                                    r_start * 0.5, r_start * 0.15, SUB_SEGS, dead_mat))

    # ---- Broken top: jagged splintered end ----
    # Add a few short splintered stubs at the break point
    top_pt = trunk_pts[-1].copy()
    n_splinters = rng.randint(2, 4)
    for s in range(n_splinters):
        spl_angle = rng.uniform(0, 2.0 * math.pi)
        spl_dx = math.cos(spl_angle) * rng.uniform(0.01, 0.03)
        spl_dy = math.sin(spl_angle) * rng.uniform(0.01, 0.03)
        spl_len = rng.uniform(0.05, 0.20)
        spl_pts = [
            top_pt.copy(),
            Vector((top_pt.x + spl_dx, top_pt.y + spl_dy,
                     top_pt.z + spl_len))
        ]
        parts.append(make_tube(f"splinter_{vi}_{s}", spl_pts,
                                trunk_r_top * 0.6, 0.005, SUB_SEGS, dead_mat))

    # ---- Finalize ----
    for obj in parts:
        for poly in obj.data.polygons:
            poly.use_smooth = True

    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()

    final = bpy.context.active_object
    final.name = f"DeadTree_{vi + 1}"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bbox = [final.matrix_world @ Vector(corner) for corner in final.bound_box]
    min_z = min(v.z for v in bbox)
    final.location.z -= min_z
    bpy.ops.object.transform_apply(location=True)

    bpy.ops.object.select_all(action='DESELECT')
    return final


# ---- Generate 5 variants ----
print("\n" + "=" * 60)
print("Building 5 standing dead tree (snag) variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_dead_variant(i, seed=600 + i * 37)
    n_faces = len(v.data.polygons)
    d = v.dimensions
    print(f"  Variant {i+1}: {n_faces} faces, "
          f"size={d.x:.1f}x{d.y:.1f}x{d.z:.1f}")
    variants.append(v)

# ---- Export GLB ----
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=OUT_PATH,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
)
print(f"\nExported {len(variants)} standing dead tree variants to {OUT_PATH}")

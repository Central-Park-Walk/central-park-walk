"""
Generate Ginkgo (Ginkgo biloba) tree model for Central Park Walk.

The ginkgo is a distinctive columnar-to-pyramidal tree with fan-shaped leaves.
Male trees dominate Central Park's 284 ginkgos (females produce smelly fruit).
Open, irregular branching with short spur shoots; bark is gray, deeply furrowed.
In autumn, ginkgos turn vivid gold all at once and drop leaves in 1-2 days.

Generates 5 variants → models/trees/ginkgo.glb
Run: blender --background --python scripts/make_ginkgo.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from leaf_card_utils import create_leaf_material, make_leaf_cards

# ---- Configuration ----
TREE_H = 5.0              # game scales to 12-20m
TRUNK_FRAC = 0.30         # relatively tall straight trunk
CANOPY_SPREAD = 2.0       # narrow, columnar profile
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/ginkgo.glb"

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
for block in bpy.data.images:
    if block.users == 0:
        bpy.data.images.remove(block)

# ---- Materials ----
bark_mat = bpy.data.materials.new(name="GinkgoBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf_bark.inputs["Base Color"].default_value = (0.38, 0.34, 0.28, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.90

# Leaves — crossed-quad leaf cards with fan-shaped ginkgo leaves
leaf_mat = create_leaf_material("GinkgoLeaf", leaf_shape="fan",
                                n_leaves=12, tex_size=512, seed=557)


# ---- Geometry helpers (same as oak/elm) ----

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
    return (p0 * u * u * u + p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t + p3 * t * t * t)


def make_ginkgo_variant(vi, seed):
    """Generate one Ginkgo tree variant.

    Key characteristics:
    - Tall, straight trunk (longer before branching)
    - Columnar to pyramidal crown (narrow, upright)
    - Irregular branching — some long, some short spur shoots
    - Open canopy with distinct clusters (not dense dome)
    - Bark: gray, deeply furrowed
    """
    rng = random.Random(seed)
    bark_parts = []
    leaf_parts = []

    split_h = TREE_H * TRUNK_FRAC
    trunk_r_base = 0.072    # census DBH-derived (was 0.14)
    trunk_r_top = 0.043
    lean_x = rng.uniform(-0.03, 0.03)
    lean_y = rng.uniform(-0.03, 0.03)

    # ---- Trunk: straight, tall ----
    n_trunk = 8
    trunk_pts = []
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * split_h
        trunk_pts.append(Vector((
            lean_x * t + math.sin(t * math.pi * 0.8) * 0.02,
            lean_y * t + math.cos(t * math.pi * 0.6) * 0.015,
            z)))
    bark_parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                                trunk_r_base, trunk_r_top, TRUNK_SEGS, bark_mat))

    # ---- Central leader extends above fork (ginkgo often keeps a central leader) ----
    leader_h = TREE_H * rng.uniform(0.90, 1.0)
    n_leader = 6
    leader_pts = []
    for i in range(n_leader):
        t = i / (n_leader - 1)
        z = split_h + t * (leader_h - split_h)
        leader_pts.append(Vector((
            lean_x + math.sin(t * math.pi * 0.5) * 0.015,
            lean_y + math.cos(t * math.pi * 0.4) * 0.01,
            z)))
    bark_parts.append(make_tube(f"leader_{vi}", leader_pts,
                                trunk_r_top * 0.85, 0.015, BRANCH_SEGS, bark_mat))

    # ---- Root flare ----
    n_roots = rng.randint(3, 4)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.12, 0.25)
        root_pts = [
            Vector((0, 0, 0.08)),
            Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.02)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        bark_parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                    trunk_r_base * 0.50, 0.012, SUB_SEGS, bark_mat))

    # ---- Branches: irregular, ascending at various angles ----
    n_limbs = rng.randint(5, 8)
    limb_data = []

    for b in range(n_limbs):
        # Branch emerges from central leader at various heights
        t_emerge = rng.uniform(0.1, 0.85)
        emerge_h = split_h + t_emerge * (leader_h - split_h)
        base_angle = rng.uniform(0, 2.0 * math.pi)
        dx = math.cos(base_angle)
        dy = math.sin(base_angle)

        # Ginkgo branches angle upward (30-60°) but spread less than oak
        end_spread = CANOPY_SPREAD * rng.uniform(0.40, 0.85)
        end_h = emerge_h + rng.uniform(0.3, 1.2)

        p0 = Vector((lean_x, lean_y, emerge_h))
        p1 = Vector((lean_x + dx * end_spread * 0.2,
                      lean_y + dy * end_spread * 0.2,
                      emerge_h + (end_h - emerge_h) * 0.4))
        p2 = Vector((dx * end_spread * 0.6,
                      dy * end_spread * 0.6,
                      emerge_h + (end_h - emerge_h) * 0.7))
        p3 = Vector((dx * end_spread, dy * end_spread, end_h))

        n_pts = 7
        limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                    for t in range(n_pts)]

        r_start = trunk_r_top * rng.uniform(0.35, 0.55)
        bark_parts.append(make_tube(f"limb_{vi}_{b}", limb_pts,
                                    r_start, 0.010, BRANCH_SEGS, bark_mat))
        limb_data.append((limb_pts, base_angle, end_spread))

        # Spur shoots (short, stubby — ginkgo characteristic)
        n_spurs = rng.randint(3, 6)
        for s in range(n_spurs):
            t_start = rng.uniform(0.30, 0.90)
            idx = int(t_start * (len(limb_pts) - 1))
            origin = limb_pts[idx].copy()
            spur_angle = base_angle + rng.uniform(-1.0, 1.0)
            spur_dx = math.cos(spur_angle)
            spur_dy = math.sin(spur_angle)
            spur_len = rng.uniform(0.15, 0.40)  # short spurs
            spur_pts = [
                origin.copy(),
                Vector((origin.x + spur_dx * spur_len * 0.5,
                        origin.y + spur_dy * spur_len * 0.5,
                        origin.z + spur_len * 0.2)),
                Vector((origin.x + spur_dx * spur_len,
                        origin.y + spur_dy * spur_len,
                        origin.z + spur_len * 0.35)),
            ]
            bark_parts.append(make_tube(f"spur_{vi}_{b}_{s}", spur_pts,
                                        0.017, 0.006, SUB_SEGS, bark_mat))

    # ---- Canopy: open, clustered along branches ----
    # Ginkgo has an open, airy canopy — clusters of fan leaves on spur shoots

    # Along branches
    for b, (limb_pts, angle, spread) in enumerate(limb_data):
        n_cl = rng.randint(6, 12)
        for c in range(n_cl):
            t = rng.uniform(0.30, 1.0)
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.35, 0.35)
            pos.y += rng.uniform(-0.35, 0.35)
            pos.z += rng.uniform(-0.15, 0.25)
            r = rng.uniform(0.18, 0.40)  # smaller clusters = open canopy
            leaf_parts += make_leaf_cards(
                f"lc_{b}_{c}", vi, pos, r, n_cards=3,
                rng=rng, mat=leaf_mat, flatten=rng.uniform(0.50, 0.70))

    # Central leader clusters (pyramidal top)
    n_top = rng.randint(8, 14)
    for f in range(n_top):
        angle_f = rng.uniform(0, 2.0 * math.pi)
        # Narrow distribution = columnar
        dist = rng.uniform(0, CANOPY_SPREAD * 0.45)
        z = TREE_H * rng.uniform(0.50, 0.95)
        x = math.cos(angle_f) * dist + rng.uniform(-0.2, 0.2)
        y = math.sin(angle_f) * dist + rng.uniform(-0.2, 0.2)
        r = rng.uniform(0.20, 0.45)
        leaf_parts += make_leaf_cards(
            f"top_{f}", vi, Vector((x, y, z)), r, n_cards=3,
            rng=rng, mat=leaf_mat, flatten=rng.uniform(0.45, 0.65))

    # ---- Finalize ----
    all_parts = bark_parts + leaf_parts
    for obj in all_parts:
        for poly in obj.data.polygons:
            poly.use_smooth = True

    bpy.ops.object.select_all(action='DESELECT')
    for obj in all_parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = all_parts[0]
    bpy.ops.object.join()

    final = bpy.context.active_object
    final.name = f"GinkgoTree_{vi + 1}"
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
print("Building 5 Ginkgo variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_ginkgo_variant(i, seed=300 + i * 31)
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
print(f"\nExported {len(variants)} Ginkgo variants to {OUT_PATH}")

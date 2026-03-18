"""
Generate Honeylocust (Gleditsia triacanthos) tree model for Central Park Walk.

The thornless honeylocust is extremely common in NYC — 241 in the park census.
Distinctive for its open, airy crown that lets dappled light through (hence
popular as a street tree). Compound pinnate leaves create a fine-textured,
feathery canopy. Trunk has flat-topped bark ridges. Crown is broadly oval.

Generates 5 variants → models/trees/honeylocust.glb
Run: blender --background --python scripts/make_honeylocust.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from leaf_card_utils import create_leaf_material, make_leaf_cards

# ---- Configuration ----
TREE_H = 5.0              # game scales to 12-22m
TRUNK_FRAC = 0.25
CANOPY_SPREAD = 3.2       # broad but airy
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/honeylocust.glb"

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
bark_mat = bpy.data.materials.new(name="HoneylocustBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf_bark.inputs["Base Color"].default_value = (0.35, 0.28, 0.20, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.88

# Leaves — crossed-quad leaf cards with compound honeylocust leaflets
leaf_mat = create_leaf_material("HoneylocustLeaf", leaf_shape="compound",
                                n_leaves=12, tex_size=512, seed=661)


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
    return (p0 * u * u * u + p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t + p3 * t * t * t)


def make_honeylocust_variant(vi, seed):
    """Generate one Honeylocust tree variant.

    Key characteristics:
    - Open, airy crown that casts dappled shade
    - Broadly oval crown shape
    - Ascending branches with graceful secondary drooping
    - Fewer, smaller leaf clusters = visible sky through canopy
    """
    rng = random.Random(seed)
    bark_parts = []
    leaf_parts = []

    split_h = TREE_H * TRUNK_FRAC
    trunk_r_base = 0.14
    trunk_r_top = 0.08
    lean_x = rng.uniform(-0.05, 0.05)
    lean_y = rng.uniform(-0.05, 0.05)

    # ---- Trunk ----
    n_trunk = 7
    trunk_pts = []
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * split_h
        trunk_pts.append(Vector((
            lean_x * t + math.sin(t * math.pi * 1.1) * 0.03,
            lean_y * t + math.cos(t * math.pi * 0.8) * 0.02,
            z)))
    bark_parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                                trunk_r_base, trunk_r_top, TRUNK_SEGS, bark_mat))

    # Root flare
    n_roots = rng.randint(3, 5)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.12, 0.22)
        root_pts = [
            Vector((0, 0, 0.07)),
            Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.02)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        bark_parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                    trunk_r_base * 0.50, 0.012, SUB_SEGS, bark_mat))

    # ---- Major limbs: ascending, broadly oval ----
    n_limbs = rng.randint(4, 7)
    limb_data = []

    for b in range(n_limbs):
        base_angle = (b / n_limbs) * 2.0 * math.pi + rng.uniform(-0.25, 0.25)
        dx = math.cos(base_angle)
        dy = math.sin(base_angle)

        end_spread = CANOPY_SPREAD * rng.uniform(0.55, 1.0)
        end_h = TREE_H * rng.uniform(0.70, 0.95)

        p0 = trunk_pts[-1].copy()
        p1 = Vector((lean_x + dx * end_spread * 0.15,
                      lean_y + dy * end_spread * 0.15,
                      split_h + (end_h - split_h) * 0.40))
        p2 = Vector((dx * end_spread * 0.55,
                      dy * end_spread * 0.55,
                      split_h + (end_h - split_h) * 0.75))
        p3 = Vector((dx * end_spread, dy * end_spread, end_h))

        n_pts = 8
        limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                    for t in range(n_pts)]

        r_start = trunk_r_top * rng.uniform(0.45, 0.65)
        bark_parts.append(make_tube(f"limb_{vi}_{b}", limb_pts,
                                    r_start, 0.012, BRANCH_SEGS, bark_mat))
        limb_data.append((limb_pts, base_angle, end_spread))

        # Fine secondary branches (many, thin — creates airy look)
        n_subs = rng.randint(5, 8)
        for s in range(n_subs):
            t_start = rng.uniform(0.25, 0.85)
            idx = int(t_start * (len(limb_pts) - 1))
            origin = limb_pts[idx].copy()
            sub_angle = base_angle + rng.uniform(-1.0, 1.0)
            sub_dx = math.cos(sub_angle)
            sub_dy = math.sin(sub_angle)
            sub_len = rng.uniform(0.5, 1.2)
            sub_pts = []
            for sp in range(5):
                st = sp / 4.0
                # Slightly drooping sub-branches
                sub_pts.append(Vector((
                    origin.x + sub_dx * sub_len * st,
                    origin.y + sub_dy * sub_len * st,
                    origin.z + sub_len * st * 0.10 + rng.uniform(-0.08, 0.05))))
            bark_parts.append(make_tube(f"sub_{vi}_{b}_{s}", sub_pts,
                                        0.030, 0.008, SUB_SEGS, bark_mat))

    # ---- Canopy: airy, dappled — hallmark of honeylocust ----
    # Fewer, smaller clusters with more gaps = visible sky through canopy

    # Along branches (sparser than oak)
    for b, (limb_pts, angle, spread) in enumerate(limb_data):
        n_cl = rng.randint(5, 9)
        for c in range(n_cl):
            t = rng.uniform(0.35, 1.0)
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.5, 0.5)
            pos.y += rng.uniform(-0.5, 0.5)
            pos.z += rng.uniform(-0.15, 0.35)
            r = rng.uniform(0.20, 0.42)  # smaller = airier
            leaf_parts += make_leaf_cards(
                f"lc_{b}_{c}", vi, pos, r, n_cards=3,
                rng=rng, mat=leaf_mat, flatten=rng.uniform(0.45, 0.65))

    # Light fill (much less dense than oak)
    n_dome = rng.randint(5, 10)
    for f in range(n_dome):
        angle_f = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0, CANOPY_SPREAD * 0.6)
        z = TREE_H * rng.uniform(0.55, 0.90)
        x = math.cos(angle_f) * dist + rng.uniform(-0.3, 0.3)
        y = math.sin(angle_f) * dist + rng.uniform(-0.3, 0.3)
        r = rng.uniform(0.22, 0.45)
        leaf_parts += make_leaf_cards(
            f"dome_{f}", vi, Vector((x, y, z)), r, n_cards=3,
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
    final.name = f"HoneylocustTree_{vi + 1}"
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
print("Building 5 Honeylocust variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_honeylocust_variant(i, seed=400 + i * 29)
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
print(f"\nExported {len(variants)} Honeylocust variants to {OUT_PATH}")

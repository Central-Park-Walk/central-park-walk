"""
Generate Cathedral American Elm for Central Park Walk's Literary Walk.

The Literary Walk's double row of mature American Elms is one of Central
Park's most iconic features. These elms have been trained and grown over
150+ years to form a cathedral tunnel: the canopy extends far laterally
(7-8m reach) so that opposing rows planted ~15m apart interlock overhead,
creating a vaulted green ceiling.

Key differences from the standard elm:
 - Taller (5.5 vs 5.0) — mature specimens
 - Lower fork (18% vs 25%) — splits early, maximizing lateral growth
 - Much wider spread (7.5 vs 4.5) — extreme lateral reach
 - More major limbs (5-7) angled OUT at 55-70° from vertical
 - Heavier sub-branching (6-9 per limb) with draping tips
 - Bezier control points emphasize LATERAL movement over vertical

Generates 5 variants → models/trees/cathedral_elm.glb
Run: blender --background --python scripts/make_cathedral_elm.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from leaf_card_utils import create_leaf_material, make_leaf_cards

# ---- Configuration ----
TREE_H = 5.5             # taller — mature Literary Walk specimens
TRUNK_FRAC = 0.18        # low fork — mature trees split early
CANOPY_SPREAD = 7.5      # extreme lateral reach for cathedral tunnel effect
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/cathedral_elm.glb"

TRUNK_SEGS = 8
BRANCH_SEGS = 6
SUB_SEGS = 4
LEAF_TEX_SIZE = 128      # leaf texture resolution

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
# Bark: gray-brown (mature American Elm — deeper furrowed bark)
bark_mat = bpy.data.materials.new(name="CathedralElmBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf_bark.inputs["Base Color"].default_value = (0.28, 0.23, 0.16, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.90

# Leaves: crossed-quad leaf cards with elliptic elm leaf atlas
leaf_mat = create_leaf_material("CathedralElmLeaf", leaf_shape="elliptic", n_leaves=14, tex_size=512, seed=888)


# ---- Geometry helpers ----

def make_tube(name, points, r_start, r_end, segments, mat):
    """Create a tapered tube following a path of 3D points."""
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
    """Evaluate cubic bezier at parameter t."""
    u = 1.0 - t
    return (p0 * u * u * u +
            p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t +
            p3 * t * t * t)


def make_cathedral_elm_variant(vi, seed):
    """Generate one complete Cathedral American Elm tree variant.

    Key architectural differences from standard elm:
    - Lower fork point (18% of height) — mature specimens split early
    - 5-7 major limbs angled 55-70° from vertical (more lateral)
    - Bezier control points push branches OUT before UP
    - Heavier sub-branching (6-9 per limb) and more twigs (3-6 per sub)
    - Draping foliage concentrated at canopy edges
    """
    rng = random.Random(seed)
    bark_parts = []
    leaf_parts = []

    split_h = TREE_H * TRUNK_FRAC  # ~0.99m — low fork
    trunk_r_base = 0.18             # slightly thicker — mature tree
    trunk_r_top = 0.10

    lean_x = rng.uniform(-0.04, 0.04)  # less lean — well-maintained park tree
    lean_y = rng.uniform(-0.04, 0.04)

    # ---- Trunk ----
    n_trunk = 8
    trunk_pts = []
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * split_h
        trunk_pts.append(Vector((
            lean_x * t + math.sin(t * math.pi) * 0.03,
            lean_y * t + math.cos(t * math.pi * 0.7) * 0.02,
            z)))
    bark_parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                                trunk_r_base, trunk_r_top, TRUNK_SEGS, bark_mat))

    # ---- Root flare ----
    n_roots = rng.randint(4, 6)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.18, 0.35)
        root_pts = [
            Vector((0, 0, 0.10)),
            Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.02)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        bark_parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                    trunk_r_base * 0.55, 0.015, SUB_SEGS, bark_mat))

    # ---- Major limbs (cathedral vase) ----
    # 5-7 limbs angled 55-70° from vertical = 20-35° from horizontal
    # Bezier control points emphasize LATERAL spread: go OUT first, then arch UP
    n_limbs = rng.randint(5, 7)
    limb_data = []

    for b in range(n_limbs):
        base_angle = (b / n_limbs) * 2.0 * math.pi + rng.uniform(-0.2, 0.2)
        dx = math.cos(base_angle)
        dy = math.sin(base_angle)

        # Lateral reach: 80-115% of CANOPY_SPREAD
        end_spread = CANOPY_SPREAD * rng.uniform(0.80, 1.15)
        # Final height: branches arch up to 75-92% of tree height
        end_h = TREE_H * rng.uniform(0.75, 0.92)
        # Droop at tips — elm's signature weeping tips
        tip_droop = rng.uniform(0.15, 0.45)

        p0 = trunk_pts[-1].copy()

        # Control points push branches OUT aggressively before arching UP
        # p1: branches go mostly lateral with moderate rise
        #     (55-70° from vertical means cos(55-70°) = 0.34-0.57 lateral fraction)
        p1 = Vector((lean_x + dx * end_spread * 0.30,
                      lean_y + dy * end_spread * 0.30,
                      split_h + (end_h - split_h) * 0.30))   # strong lateral push

        # p2: continue outward, now rising more — the arch
        p2 = Vector((dx * end_spread * 0.75,
                      dy * end_spread * 0.75,
                      end_h + 0.20))                           # peak above final height

        # p3: full lateral extent, drooping tip
        p3 = Vector((dx * end_spread, dy * end_spread,
                      end_h - tip_droop))

        n_pts = 14  # more points for smoother curve
        limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                    for t in range(n_pts)]

        r_start = trunk_r_top * rng.uniform(0.60, 0.80)
        bark_parts.append(make_tube(f"limb_{vi}_{b}", limb_pts,
                                    r_start, 0.010, BRANCH_SEGS, bark_mat))
        limb_data.append((limb_pts, base_angle, end_spread))

        # ---- Secondary branches (6-9 per limb — heavy branching) ----
        n_subs = rng.randint(6, 9)
        for s in range(n_subs):
            t_start = rng.uniform(0.20, 0.92)
            idx = int(t_start * (len(limb_pts) - 1))
            origin = limb_pts[idx].copy()

            # Sub-branches fan outward, biased away from trunk
            sub_angle = base_angle + rng.uniform(-1.0, 1.0)
            sub_dx = math.cos(sub_angle)
            sub_dy = math.sin(sub_angle)
            sub_len = rng.uniform(1.0, 2.5)  # longer subs for cathedral spread
            sub_pts = []
            for sp in range(7):
                st = sp / 6.0
                # Sub-branches arch outward and droop at tips
                sub_pts.append(Vector((
                    origin.x + sub_dx * sub_len * st,
                    origin.y + sub_dy * sub_len * st,
                    origin.z + sub_len * st * 0.20 - st * st * sub_len * 0.18)))
            bark_parts.append(make_tube(f"sub_{vi}_{b}_{s}", sub_pts,
                                        0.035, 0.007, SUB_SEGS, bark_mat))

            # ---- Tertiary twigs (3-6 per sub — heavier than standard elm) ----
            for tw in range(rng.randint(3, 6)):
                tw_t = rng.uniform(0.20, 0.90)
                tw_idx = int(tw_t * (len(sub_pts) - 1))
                tw_origin = sub_pts[tw_idx].copy()
                tw_angle = sub_angle + rng.uniform(-1.3, 1.3)
                tw_len = rng.uniform(0.35, 0.95)
                tw_pts = [
                    tw_origin,
                    tw_origin + Vector((math.cos(tw_angle) * tw_len * 0.5,
                                        math.sin(tw_angle) * tw_len * 0.5,
                                        tw_len * 0.10)),
                    tw_origin + Vector((math.cos(tw_angle) * tw_len,
                                        math.sin(tw_angle) * tw_len,
                                        -tw_len * 0.10)),  # drooping tips
                ]
                bark_parts.append(make_tube(f"twig_{vi}_{b}_{s}_{tw}", tw_pts,
                                            0.010, 0.003, 3, bark_mat))

    # ---- Canopy: leaf clusters along branches and at draping edges ----
    # ~60-80 total clusters per variant, distributed for cathedral effect:
    # concentrated along lateral reach and at drooping edges.

    # Along each major limb — clusters follow branch architecture
    for b, (limb_pts, angle, spread) in enumerate(limb_data):
        n_cl = rng.randint(7, 11)
        for c in range(n_cl):
            t = rng.uniform(0.40, 1.0)
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.8, 0.8)
            pos.y += rng.uniform(-0.8, 0.8)
            pos.z += rng.uniform(-0.3, 0.4)
            r = rng.uniform(0.50, 0.95)  # slightly larger clusters
            leaf_parts += make_leaf_cards("lc", vi, pos, r, n_cards=3, rng=rng, mat=leaf_mat, flatten=rng.uniform(0.40, 0.60))

    # Upper dome — sparser to let light through (cathedral light effect)
    n_dome = rng.randint(8, 14)
    for f in range(n_dome):
        angle_f = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0.8, CANOPY_SPREAD * 0.65)
        z = TREE_H * rng.uniform(0.75, 1.0)
        x = math.cos(angle_f) * dist + rng.uniform(-0.4, 0.4)
        y = math.sin(angle_f) * dist + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.55, 0.90)
        leaf_parts += make_leaf_cards("dome", vi, Vector((x, y, z)), r, n_cards=3, rng=rng, mat=leaf_mat, flatten=rng.uniform(0.40, 0.55))

    # Draping edges — elm's signature weeping tips, heavier for cathedral effect
    n_drape = rng.randint(12, 20)
    for d in range(n_drape):
        angle_d = rng.uniform(0, 2.0 * math.pi)
        dist = CANOPY_SPREAD * rng.uniform(0.70, 1.12)
        z = TREE_H * rng.uniform(0.38, 0.70)  # lower — hanging curtain effect
        x = math.cos(angle_d) * dist + rng.uniform(-0.4, 0.4)
        y = math.sin(angle_d) * dist + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.40, 0.75)
        leaf_parts += make_leaf_cards("drape", vi, Vector((x, y, z)), r, n_cards=3, rng=rng, mat=leaf_mat, flatten=rng.uniform(0.50, 0.70))

    # ---- Finalize variant ----
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
    final.name = f"CathedralElm_{vi + 1}"

    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Origin to bottom center
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bbox = [final.matrix_world @ Vector(corner) for corner in final.bound_box]
    min_z = min(v.z for v in bbox)
    final.location.z -= min_z
    bpy.ops.object.transform_apply(location=True)

    bpy.ops.object.select_all(action='DESELECT')
    return final


# ---- Generate 5 variants ----
variants = []
for i in range(N_VARIANTS):
    v = make_cathedral_elm_variant(i, seed=101 + i * 23)
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
print(f"\nExported {len(variants)} Cathedral Elm variants to {OUT_PATH}")

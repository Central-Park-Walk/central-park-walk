"""
Generate magnolia tree model for Central Park Walk.

Saucer magnolia (Magnolia × soulangeana) is common in Central Park,
especially in the Conservatory Garden's "Wedding Garden" and along
5th Avenue paths. One of the most spectacular spring-flowering trees.

Key characteristics:
  - Multi-stemmed or low-branching habit
  - Wide, spreading, rounded crown
  - Large thick leaves (dark glossy green)
  - Spectacular pink/white cup-shaped spring flowers (before leaf-out)
  - Smooth gray bark
  - Medium height: 6-10m in Central Park
  - Crown wider than tall (broad spreading habit)

Generates 5 variants → models/trees/magnolia.glb
Run: blender --background --python scripts/make_magnolia.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ---- Configuration ----
TREE_H = 4.0              # model scale height (shorter, wider tree)
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/magnolia.glb"

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

# ---- Materials ----
# Bark: smooth gray
bark_mat = bpy.data.materials.new(name="MagnoliaBark")
bark_mat.use_nodes = True
bsdf = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.52, 0.48, 0.44, 1.0)
bsdf.inputs["Roughness"].default_value = 0.75  # smooth gray bark

# Leaves: dark glossy green, large and thick
leaf_mat = bpy.data.materials.new(name="MagnoliaLeaf")
leaf_mat.use_nodes = True
bsdf_l = leaf_mat.node_tree.nodes["Principled BSDF"]
bsdf_l.inputs["Base Color"].default_value = (0.18, 0.35, 0.12, 1.0)
bsdf_l.inputs["Roughness"].default_value = 0.65  # glossy leaves


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


def make_leaf_cluster(name, center, radius, n_quads, rng, mat):
    """Create a cluster of large magnolia leaf billboard quads."""
    bm = bmesh.new()
    for _ in range(n_quads):
        dx = rng.gauss(0, radius * 0.45)
        dy = rng.gauss(0, radius * 0.45)
        dz = rng.gauss(0, radius * 0.35)
        qc = Vector((center.x + dx, center.y + dy, center.z + dz))
        # Large, broad magnolia leaves — oval shape
        w = rng.uniform(0.10, 0.18)  # wider than typical leaves
        h = rng.uniform(0.12, 0.20)
        angle = rng.uniform(0, math.pi)
        ax = math.cos(angle) * w
        az = math.sin(angle) * w
        v0 = bm.verts.new((qc.x - ax, qc.y - h * 0.5, qc.z - az))
        v1 = bm.verts.new((qc.x + ax, qc.y - h * 0.5, qc.z + az))
        v2 = bm.verts.new((qc.x + ax, qc.y + h * 0.5, qc.z + az))
        v3 = bm.verts.new((qc.x - ax, qc.y + h * 0.5, qc.z - az))
        try:
            bm.faces.new([v0, v1, v2, v3])
        except ValueError:
            pass
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


def make_magnolia_variant(vi, seed):
    """Generate one magnolia variant — wide, low-branching, spreading crown."""
    rng = random.Random(seed)
    parts = []

    # Magnolias often multi-stemmed or branch very low
    n_stems = rng.randint(1, 3)
    trunk_r_base = rng.uniform(0.08, 0.14)

    all_branch_tips = []

    for stem_idx in range(n_stems):
        stem_angle = (stem_idx / max(n_stems, 1)) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        stem_spread = rng.uniform(0.0, 0.12) if n_stems > 1 else 0.0
        stem_dx = math.cos(stem_angle) * stem_spread
        stem_dy = math.sin(stem_angle) * stem_spread

        trunk_r = trunk_r_base * (0.7 if n_stems > 1 else 1.0)
        trunk_frac = rng.uniform(0.20, 0.35)
        trunk_h = TREE_H * trunk_frac

        # Trunk
        n_trunk = 6
        trunk_pts = []
        for i in range(n_trunk):
            t = i / (n_trunk - 1)
            z = t * trunk_h
            trunk_pts.append(Vector((
                stem_dx * t + rng.uniform(-0.01, 0.01),
                stem_dy * t + rng.uniform(-0.01, 0.01),
                z)))
        parts.append(make_tube(f"trunk_{vi}_{stem_idx}", trunk_pts,
                               trunk_r, trunk_r * 0.5, TRUNK_SEGS, bark_mat))

        top_pt = trunk_pts[-1].copy()

        # Root flare (only on main stem)
        if stem_idx == 0:
            n_roots = rng.randint(3, 5)
            for r_idx in range(n_roots):
                angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
                dx = math.cos(angle)
                dy = math.sin(angle)
                root_len = rng.uniform(0.12, 0.25)
                root_pts = [
                    Vector((0, 0, 0.06)),
                    Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.02)),
                    Vector((dx * root_len, dy * root_len, 0.0)),
                ]
                parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                       trunk_r_base * 0.45, 0.015, SUB_SEGS, bark_mat))

        # Main branches: spread wide and arch upward
        # Magnolia crown is wider than tall — branches go horizontal then curve up
        n_branches = rng.randint(3, 5)
        for b in range(n_branches):
            br_angle = (b / n_branches) * 2.0 * math.pi + rng.uniform(-0.4, 0.4)
            if n_stems > 1:
                # Multi-stem: branches bias outward from stem angle
                br_angle = stem_angle + rng.uniform(-1.0, 1.0)
            dx = math.cos(br_angle)
            dy = math.sin(br_angle)

            br_len = rng.uniform(1.2, 2.2)  # long horizontal reach
            br_rise = rng.uniform(0.5, 1.2)  # moderate upward curve

            p0 = top_pt.copy()
            p1 = Vector((
                top_pt.x + dx * br_len * 0.3,
                top_pt.y + dy * br_len * 0.3,
                top_pt.z + br_rise * 0.3))
            p2 = Vector((
                top_pt.x + dx * br_len * 0.7,
                top_pt.y + dy * br_len * 0.7,
                top_pt.z + br_rise * 0.7))
            p3 = Vector((
                top_pt.x + dx * br_len,
                top_pt.y + dy * br_len,
                top_pt.z + br_rise))

            br_pts = []
            n_br = 6
            for i in range(n_br):
                t = i / (n_br - 1)
                pt = bezier_point(p0, p1, p2, p3, t)
                pt.x += rng.uniform(-0.02, 0.02)
                pt.y += rng.uniform(-0.02, 0.02)
                br_pts.append(pt)

            br_r = rng.uniform(0.025, 0.045)
            parts.append(make_tube(f"branch_{vi}_{stem_idx}_{b}", br_pts,
                                   br_r, br_r * 0.25, BRANCH_SEGS, bark_mat))

            # Store branch tips for leaf clusters
            for frac in [0.4, 0.6, 0.8, 1.0]:
                idx = min(int(frac * (n_br - 1)), n_br - 1)
                all_branch_tips.append(br_pts[idx].copy())

            # Sub-branches
            n_sub = rng.randint(2, 4)
            for s in range(n_sub):
                sub_t = rng.uniform(0.3, 0.8)
                sub_idx = min(int(sub_t * (n_br - 1)), n_br - 1)
                sub_origin = br_pts[sub_idx].copy()
                sub_angle = br_angle + rng.uniform(-1.0, 1.0)
                sub_dx = math.cos(sub_angle)
                sub_dy = math.sin(sub_angle)
                sub_len = rng.uniform(0.3, 0.8)

                sub_pts = []
                for sp in range(4):
                    st = sp / 3.0
                    sub_pts.append(Vector((
                        sub_origin.x + sub_dx * sub_len * st,
                        sub_origin.y + sub_dy * sub_len * st,
                        sub_origin.z + sub_len * st * 0.25)))
                sub_r = rng.uniform(0.012, 0.025)
                parts.append(make_tube(f"sub_{vi}_{stem_idx}_{b}_{s}", sub_pts,
                                       sub_r, sub_r * 0.25, SUB_SEGS, bark_mat))
                all_branch_tips.append(sub_pts[-1].copy())

    # ---- Dense leaf canopy ----
    # Magnolias have thick, dense foliage — large glossy leaves
    for tip_idx, tip in enumerate(all_branch_tips):
        n_clusters = rng.randint(1, 3)
        for cl in range(n_clusters):
            offset = Vector((
                rng.uniform(-0.15, 0.15),
                rng.uniform(-0.15, 0.15),
                rng.uniform(-0.10, 0.10)))
            center = tip + offset
            cluster_r = rng.uniform(0.25, 0.45)
            n_quads = rng.randint(10, 18)
            parts.append(make_leaf_cluster(
                f"leaf_{vi}_{tip_idx}_{cl}",
                center, cluster_r, n_quads, rng, leaf_mat))

    # Extra canopy fill at crown center
    if all_branch_tips:
        avg_x = sum(t.x for t in all_branch_tips) / len(all_branch_tips)
        avg_y = sum(t.y for t in all_branch_tips) / len(all_branch_tips)
        avg_z = sum(t.z for t in all_branch_tips) / len(all_branch_tips)
        n_fill = rng.randint(6, 12)
        for f in range(n_fill):
            center = Vector((
                avg_x + rng.uniform(-0.8, 0.8),
                avg_y + rng.uniform(-0.8, 0.8),
                avg_z + rng.uniform(-0.4, 0.4)))
            cluster_r = rng.uniform(0.3, 0.50)
            n_quads = rng.randint(12, 20)
            parts.append(make_leaf_cluster(
                f"fill_{vi}_{f}", center, cluster_r, n_quads, rng, leaf_mat))

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
    final.name = f"Magnolia_{vi + 1}"
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
print("Building 5 magnolia variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_magnolia_variant(i, seed=900 + i * 43)
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
print(f"\nExported {len(variants)} magnolia variants to {OUT_PATH}")

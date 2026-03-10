"""
Generate Gray Birch (Betula populifolia) tree model for Central Park Walk.

Gray birch is the common native birch in Central Park — slender, often
multi-stemmed, with chalky white bark marked by dark triangular patches
below each branch.  Smaller than paper birch (6-10m in the park), found
in woodland edges and naturalistic plantings.

Key characteristics:
  - White/chalky bark with dark chevron marks
  - Often multi-stemmed (clump form)
  - Slender, somewhat drooping branchlets
  - Small triangular-ovate leaves (doubly serrate)
  - Open, airy crown — light passes through

Generates 5 variants → models/trees/birch.glb
Run: blender --background --python scripts/make_birch.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ---- Configuration ----
TREE_H = 4.5              # game-scale (engine scales to real ~6-10m)
TRUNK_FRAC = 0.30          # taller clear trunk before branching
CANOPY_SPREAD = 1.8        # narrow, open crown
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/birch.glb"

TRUNK_SEGS = 6
BRANCH_SEGS = 5
SUB_SEGS = 4
LEAF_TEX_SIZE = 128

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

# ---- Leaf texture ----
TEX = LEAF_TEX_SIZE
leaf_img = bpy.data.images.new("BirchLeafTex", width=TEX, height=TEX, alpha=True)
pixels = [0.0] * (TEX * TEX * 4)

leaf_rng = random.Random(551)
for _ in range(90):  # many small triangular leaves
    cx = leaf_rng.randint(4, TEX - 4)
    cy = leaf_rng.randint(4, TEX - 4)
    leaf_w = leaf_rng.randint(3, 5)   # small leaves
    leaf_h = leaf_rng.randint(4, 8)   # slightly elongated triangular
    angle = leaf_rng.uniform(0, math.pi)
    # Birch leaf: bright yellow-green, lighter than most species
    r = leaf_rng.uniform(0.55, 0.72)
    g = leaf_rng.uniform(0.78, 0.95)
    b = leaf_rng.uniform(0.38, 0.55)
    for dy in range(-leaf_h, leaf_h + 1):
        for dx in range(-leaf_w, leaf_w + 1):
            rx = dx * math.cos(angle) + dy * math.sin(angle)
            ry = -dx * math.sin(angle) + dy * math.cos(angle)
            # Triangular shape: narrower at tip (positive ry)
            width_at_y = max(1 - abs(ry) / max(leaf_h, 1), 0.0)
            if ry > 0:
                width_at_y *= 0.6  # narrower toward tip
            if abs(rx) / max(leaf_w, 1) <= width_at_y:
                px = (cx + dx) % TEX
                py = (cy + dy) % TEX
                idx = (py * TEX + px) * 4
                pixels[idx + 0] = r
                pixels[idx + 1] = g
                pixels[idx + 2] = b
                pixels[idx + 3] = 1.0

leaf_img.pixels[:] = pixels
leaf_img.pack()

# ---- Materials ----
# Bark: white/chalky — birch's most distinctive feature
bark_mat = bpy.data.materials.new(name="BirchBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
# White bark with slight warm undertone
bsdf_bark.inputs["Base Color"].default_value = (0.82, 0.78, 0.72, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.65  # papery texture

# Leaves
leaf_mat = bpy.data.materials.new(name="BirchLeaf")
leaf_mat.use_nodes = True
leaf_mat.blend_method = 'CLIP'
leaf_mat.alpha_threshold = 0.5
tree = leaf_mat.node_tree
bsdf_leaf = tree.nodes["Principled BSDF"]
bsdf_leaf.inputs["Roughness"].default_value = 0.68

tex_node = tree.nodes.new('ShaderNodeTexImage')
tex_node.image = leaf_img
tree.links.new(tex_node.outputs['Color'], bsdf_leaf.inputs['Base Color'])
tree.links.new(tex_node.outputs['Alpha'], bsdf_leaf.inputs['Alpha'])


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


def make_leaf_cluster(name, center, radius, flatten, rng_local):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=radius, location=tuple(center))
    obj = bpy.context.active_object
    obj.name = name
    for v in obj.data.vertices:
        v.co.z *= flatten
        noise = (math.sin(v.co.x * 7.1 + v.co.z * 3.3) *
                 math.cos(v.co.y * 5.7 + v.co.x * 2.1) * 0.15 * radius)
        v.co.x += noise
        v.co.y += noise * 0.7
        v.co.z += noise * 0.5
    obj.data.materials.append(leaf_mat)
    return obj


def bezier_point(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (p0 * u * u * u +
            p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t +
            p3 * t * t * t)


def make_birch_variant(vi, seed):
    """Generate one Gray Birch tree variant.

    Key characteristics:
    - Multi-stemmed clump (2-4 trunks from base)
    - White chalky bark
    - Slender, open crown with drooping branchlets
    - Small triangular leaves on fine twigs
    """
    rng = random.Random(seed)
    bark_parts = []
    leaf_parts = []

    # ---- Multi-stem habit: 1-3 stems from near ground ----
    n_stems = rng.randint(1, 3)
    stem_data = []

    for si in range(n_stems):
        if n_stems == 1:
            stem_angle = 0
            stem_lean = 0.02
        else:
            stem_angle = (si / n_stems) * 2.0 * math.pi + rng.uniform(-0.3, 0.3)
            stem_lean = rng.uniform(0.08, 0.18)

        trunk_r_base = 0.08 if n_stems == 1 else 0.06
        trunk_r_top = 0.035

        # Stem curves outward slightly from clump center
        lean_x = math.cos(stem_angle) * stem_lean
        lean_y = math.sin(stem_angle) * stem_lean

        split_h = TREE_H * TRUNK_FRAC

        # ---- Trunk: slender, white ----
        n_trunk = 7
        trunk_pts = []
        for i in range(n_trunk):
            t = i / (n_trunk - 1)
            z = t * split_h
            # Gentle curve outward
            trunk_pts.append(Vector((
                lean_x * t * t + math.sin(t * math.pi * 2.0) * 0.015,
                lean_y * t * t + math.cos(t * math.pi * 1.5) * 0.010,
                z)))
        bark_parts.append(make_tube(f"trunk_{vi}_{si}", trunk_pts,
                                    trunk_r_base, trunk_r_top, TRUNK_SEGS, bark_mat))
        stem_data.append((trunk_pts, stem_angle, lean_x, lean_y))

    # ---- Branches from each stem ----
    all_limb_data = []

    for si, (trunk_pts, stem_angle, lean_x, lean_y) in enumerate(stem_data):
        split_h = trunk_pts[-1].z

        n_limbs = rng.randint(3, 5)
        for b in range(n_limbs):
            base_angle = stem_angle + (b / n_limbs) * 2.0 * math.pi + rng.uniform(-0.4, 0.4)
            dx = math.cos(base_angle)
            dy = math.sin(base_angle)

            end_spread = CANOPY_SPREAD * rng.uniform(0.50, 0.95)
            end_h = TREE_H * rng.uniform(0.65, 0.95)

            p0 = trunk_pts[-1].copy()
            # Upward then outward arc
            p1 = Vector((lean_x + dx * end_spread * 0.10,
                          lean_y + dy * end_spread * 0.10,
                          split_h + (end_h - split_h) * 0.50))
            p2 = Vector((lean_x + dx * end_spread * 0.55,
                          lean_y + dy * end_spread * 0.55,
                          end_h + rng.uniform(-0.05, 0.05)))
            # Tips droop slightly (birch characteristic)
            droop = rng.uniform(-0.20, -0.02)
            p3 = Vector((lean_x + dx * end_spread,
                          lean_y + dy * end_spread,
                          end_h + droop))

            n_pts = 7
            limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                        for t in range(n_pts)]

            r_start = trunk_r_top * rng.uniform(0.50, 0.70)
            bark_parts.append(make_tube(f"limb_{vi}_{si}_{b}", limb_pts,
                                        r_start, 0.008, BRANCH_SEGS, bark_mat))
            all_limb_data.append((limb_pts, base_angle, end_spread))

            # ---- Fine drooping branchlets ----
            n_subs = rng.randint(3, 6)
            for s in range(n_subs):
                t_start = rng.uniform(0.35, 0.90)
                idx = int(t_start * (len(limb_pts) - 1))
                origin = limb_pts[idx].copy()
                sub_angle = base_angle + rng.uniform(-1.2, 1.2)
                sub_dx = math.cos(sub_angle)
                sub_dy = math.sin(sub_angle)
                sub_len = rng.uniform(0.30, 0.75)
                sub_pts = []
                for sp in range(4):
                    st = sp / 3.0
                    # Drooping: z decreases along branch
                    sub_pts.append(Vector((
                        origin.x + sub_dx * sub_len * st,
                        origin.y + sub_dy * sub_len * st,
                        origin.z + sub_len * st * 0.05 - st * st * 0.15)))
                bark_parts.append(make_tube(f"sub_{vi}_{si}_{b}_{s}", sub_pts,
                                            0.010, 0.003, SUB_SEGS, bark_mat))

    # ---- Canopy: open, airy — light filters through ----

    # Along branches
    for b, (limb_pts, angle, spread) in enumerate(all_limb_data):
        n_cl = rng.randint(8, 14)  # fewer = airier
        for c in range(n_cl):
            t = rng.uniform(0.40, 1.0)
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.35, 0.35)
            pos.y += rng.uniform(-0.35, 0.35)
            pos.z += rng.uniform(-0.15, 0.20)
            r = rng.uniform(0.18, 0.38)  # small clusters = airy
            leaf_parts.append(make_leaf_cluster(
                f"lc_{vi}_{b}_{c}", pos, r, rng.uniform(0.45, 0.65), rng))

    # Sparse dome fill (birch crown is NOT dense)
    n_dome = rng.randint(6, 12)
    for f in range(n_dome):
        angle_f = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0, CANOPY_SPREAD * 0.5)
        z = TREE_H * rng.uniform(0.55, 0.90)
        # Offset from clump center
        x = math.cos(angle_f) * dist + rng.uniform(-0.2, 0.2)
        y = math.sin(angle_f) * dist + rng.uniform(-0.2, 0.2)
        r = rng.uniform(0.18, 0.40)
        leaf_parts.append(make_leaf_cluster(
            f"dome_{vi}_{f}", Vector((x, y, z)), r,
            rng.uniform(0.40, 0.60), rng))

    # Drooping edge clusters (birch hallmark — pendulous tips)
    n_drape = rng.randint(5, 9)
    for d in range(n_drape):
        angle_d = rng.uniform(0, 2.0 * math.pi)
        dist = CANOPY_SPREAD * rng.uniform(0.60, 0.95)
        z = TREE_H * rng.uniform(0.35, 0.55)  # low = drooping
        x = math.cos(angle_d) * dist + rng.uniform(-0.15, 0.15)
        y = math.sin(angle_d) * dist + rng.uniform(-0.15, 0.15)
        r = rng.uniform(0.15, 0.32)
        leaf_parts.append(make_leaf_cluster(
            f"drape_{vi}_{d}", Vector((x, y, z)), r,
            rng.uniform(0.50, 0.70), rng))

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
    final.name = f"BirchTree_{vi + 1}"
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
print("Building 5 Gray Birch variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_birch_variant(i, seed=300 + i * 23)
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
print(f"\nExported {len(variants)} Gray Birch variants to {OUT_PATH}")

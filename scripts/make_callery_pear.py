"""
Generate Callery Pear (Pyrus calleryana / Bradford Pear) tree model for Central Park Walk.

Callery pear (Bradford pear) is one of NYC's most common street trees — distinctive
for its tight pyramidal/teardrop crown, upright branch angles, and dense white spring
blossoms.  Central Park has ~150 callery pears.

Key characteristics vs cherry:
- Pyramidal crown (NOT spreading) — branches angle sharply upward
- Dense canopy, less airy than cherry
- Short trunk, branches emerge low
- Gray-brown bark with shallow furrows (not smooth reddish like cherry)
- Deep red-purple fall color (spectacular)
- White spring blossoms (before leaf-out, captured in leaf shader)

Generates 5 variants → models/trees/callery_pear.glb
Run: blender --background --python scripts/make_callery_pear.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ---- Configuration ----
TREE_H = 5.2              # medium-large tree
TRUNK_FRAC = 0.20         # short trunk — branches emerge low
CANOPY_SPREAD = 2.0       # narrow relative to height (pyramidal)
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/callery_pear.glb"

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
leaf_img = bpy.data.images.new("CalleryPearLeafTex", width=TEX, height=TEX, alpha=True)
pixels = [0.0] * (TEX * TEX * 4)

leaf_rng = random.Random(557)
for _ in range(95):  # dense glossy leaves
    cx = leaf_rng.randint(4, TEX - 4)
    cy = leaf_rng.randint(4, TEX - 4)
    leaf_w = leaf_rng.randint(4, 8)   # broadly ovate
    leaf_h = leaf_rng.randint(6, 12)
    angle = leaf_rng.uniform(0, math.pi)
    # Glossy dark green
    r = leaf_rng.uniform(0.50, 0.65)
    g = leaf_rng.uniform(0.75, 0.90)
    b = leaf_rng.uniform(0.45, 0.58)
    for dy in range(-leaf_h, leaf_h + 1):
        for dx in range(-leaf_w, leaf_w + 1):
            rx = dx * math.cos(angle) + dy * math.sin(angle)
            ry = -dx * math.sin(angle) + dy * math.cos(angle)
            if (rx / max(leaf_w, 1)) ** 2 + (ry / max(leaf_h, 1)) ** 2 <= 1.0:
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
# Bark: gray-brown with shallow furrows
bark_mat = bpy.data.materials.new(name="CalleryPearBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf_bark.inputs["Base Color"].default_value = (0.42, 0.36, 0.28, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.82

# Leaves
leaf_mat = bpy.data.materials.new(name="CalleryPearLeaf")
leaf_mat.use_nodes = True
leaf_mat.blend_method = 'CLIP'
leaf_mat.alpha_threshold = 0.5
tree = leaf_mat.node_tree
bsdf_leaf = tree.nodes["Principled BSDF"]
bsdf_leaf.inputs["Roughness"].default_value = 0.65  # glossy leaves

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


def make_callery_pear_variant(vi, seed):
    """Generate one Callery Pear tree variant.

    Key characteristics:
    - Short trunk, tight pyramidal crown
    - Branches angle sharply upward (acute angles — Bradford pear trait)
    - Dense canopy, teardrop silhouette
    - Broader at base, tapering to pointed top
    """
    rng = random.Random(seed)
    bark_parts = []
    leaf_parts = []

    split_h = TREE_H * TRUNK_FRAC
    trunk_r_base = 0.12
    trunk_r_top = 0.08
    lean_x = rng.uniform(-0.03, 0.03)
    lean_y = rng.uniform(-0.03, 0.03)

    # ---- Trunk: short, thick ----
    n_trunk = 5
    trunk_pts = []
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * split_h
        trunk_pts.append(Vector((
            lean_x * t + math.sin(t * math.pi) * 0.015,
            lean_y * t,
            z)))
    bark_parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                                trunk_r_base, trunk_r_top, TRUNK_SEGS, bark_mat))

    # ---- Root flare ----
    n_roots = rng.randint(3, 5)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.12, 0.25)
        root_pts = [
            Vector((0, 0, 0.08)),
            Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.03)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        bark_parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                    trunk_r_base * 0.5, 0.012, SUB_SEGS, bark_mat))

    # ---- Central leader: Bradford pear keeps a strong central leader (mostly) ----
    leader_h = TREE_H * rng.uniform(0.90, 1.0)
    leader_pts = []
    n_leader = 7
    for i in range(n_leader):
        t = i / (n_leader - 1)
        z = split_h + t * (leader_h - split_h)
        leader_pts.append(Vector((
            lean_x + math.sin(t * math.pi * 2) * 0.03,
            lean_y + math.cos(t * math.pi * 1.5) * 0.02,
            z)))
    bark_parts.append(make_tube(f"leader_{vi}", leader_pts,
                                trunk_r_top * 0.85, 0.015, BRANCH_SEGS, bark_mat))

    # ---- Major branches: sharply upward (30-50° from vertical) ----
    # Bradford pear is notorious for tight branch angles
    n_limbs = rng.randint(5, 8)
    limb_data = []

    for b in range(n_limbs):
        base_angle = (b / n_limbs) * 2.0 * math.pi + rng.uniform(-0.25, 0.25)
        dx = math.cos(base_angle)
        dy = math.sin(base_angle)

        # Height where branch departs the leader
        branch_start_t = rng.uniform(0.1, 0.75)
        start_z = split_h + branch_start_t * (leader_h - split_h)

        # Pyramidal: lower branches spread wider, upper branches stay tight
        spread_factor = 1.0 - branch_start_t * 0.6  # lower=wider
        end_spread = CANOPY_SPREAD * spread_factor * rng.uniform(0.7, 1.1)
        # Branches angle UP sharply (acute angle from trunk)
        end_h = start_z + (TREE_H - start_z) * rng.uniform(0.55, 0.80)

        start_pos = leader_pts[int(branch_start_t * (n_leader - 1))].copy()
        p0 = start_pos
        # Control points: branch goes UP and OUT
        p1 = Vector((start_pos.x + dx * end_spread * 0.15,
                      start_pos.y + dy * end_spread * 0.15,
                      start_z + (end_h - start_z) * 0.40))
        p2 = Vector((dx * end_spread * 0.55,
                      dy * end_spread * 0.55,
                      start_z + (end_h - start_z) * 0.75))
        p3 = Vector((dx * end_spread,
                      dy * end_spread,
                      end_h))

        n_pts = 7
        limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                    for t in range(n_pts)]

        r_start = trunk_r_top * rng.uniform(0.40, 0.60)
        bark_parts.append(make_tube(f"limb_{vi}_{b}", limb_pts,
                                    r_start, 0.010, BRANCH_SEGS, bark_mat))
        limb_data.append((limb_pts, base_angle, end_spread, branch_start_t))

        # ---- Secondary branches ----
        n_subs = rng.randint(2, 5)
        for s in range(n_subs):
            t_start = rng.uniform(0.35, 0.90)
            idx = int(t_start * (len(limb_pts) - 1))
            origin = limb_pts[idx].copy()
            sub_angle = base_angle + rng.uniform(-0.8, 0.8)
            sub_dx = math.cos(sub_angle)
            sub_dy = math.sin(sub_angle)
            sub_len = rng.uniform(0.3, 0.8)
            sub_pts = []
            for sp in range(4):
                st = sp / 3.0
                sub_pts.append(Vector((
                    origin.x + sub_dx * sub_len * st,
                    origin.y + sub_dy * sub_len * st,
                    origin.z + sub_len * st * 0.35)))  # upward bias
            bark_parts.append(make_tube(f"sub_{vi}_{b}_{s}", sub_pts,
                                        0.014, 0.004, SUB_SEGS, bark_mat))

    # ---- Canopy: DENSE, PYRAMIDAL ----
    # The key to Bradford pear's look is the tight pyramidal silhouette

    # Along branches: dense clusters
    for b, (limb_pts, angle, spread, start_t) in enumerate(limb_data):
        n_cl = rng.randint(12, 20)  # denser than cherry
        for c in range(n_cl):
            t = rng.uniform(0.30, 1.0)
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.35, 0.35)
            pos.y += rng.uniform(-0.35, 0.35)
            pos.z += rng.uniform(-0.15, 0.25)
            r = rng.uniform(0.28, 0.55)
            leaf_parts.append(make_leaf_cluster(
                f"lc_{vi}_{b}_{c}", pos, r, rng.uniform(0.50, 0.70), rng))

    # Pyramidal fill: constrain clusters within tapered cone
    n_fill = rng.randint(25, 40)  # very dense fill
    for f in range(n_fill):
        # Height within crown
        z_t = rng.uniform(0.0, 1.0)
        z = split_h + z_t * (leader_h - split_h)
        # Pyramidal constraint: wider at bottom, narrow at top
        max_r = CANOPY_SPREAD * (1.0 - z_t * 0.75) * rng.uniform(0.5, 1.0)
        angle_f = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0, max_r)
        x = math.cos(angle_f) * dist + rng.uniform(-0.2, 0.2)
        y = math.sin(angle_f) * dist + rng.uniform(-0.2, 0.2)
        r = rng.uniform(0.25, 0.50)
        # Flatten clusters more at edges
        flatten = rng.uniform(0.45, 0.65)
        leaf_parts.append(make_leaf_cluster(
            f"fill_{vi}_{f}", Vector((x, y, z)), r, flatten, rng))

    # Top cap: pointed crown tip (hallmark of Bradford pear)
    n_top = rng.randint(4, 8)
    for tc in range(n_top):
        z = leader_h * rng.uniform(0.85, 1.0)
        angle_tc = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0, 0.5)
        x = math.cos(angle_tc) * dist
        y = math.sin(angle_tc) * dist
        r = rng.uniform(0.22, 0.40)
        leaf_parts.append(make_leaf_cluster(
            f"top_{vi}_{tc}", Vector((x, y, z)), r,
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
    final.name = f"CalleryPear_{vi + 1}"
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
print("Building 5 Callery Pear (Bradford Pear) variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_callery_pear_variant(i, seed=350 + i * 23)
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
print(f"\nExported {len(variants)} Callery Pear variants to {OUT_PATH}")

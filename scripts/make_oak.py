"""
Generate Red Oak (Quercus rubra) tree model for Central Park Walk.

The Red Oak is the most common oak species in Central Park — heavy-limbed,
with a broad rounded dome canopy that spreads as wide or wider than the tree
is tall.  Unlike the vase-shaped elm, oak branches emerge at wide angles
(45-70°) and are thick, gnarled, and horizontal.  The trunk is short before
the first major fork, with deeply furrowed dark gray-brown bark.

Central Park Conservancy foliage zones: North Woods (oak-dominant), Ramble
(oak/cherry), Great Hill, and scattered throughout.  1,377 instances in census.

Generates 5 variants → models/trees/oak.glb
Run: blender --background --python scripts/make_oak.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ---- Configuration ----
TREE_H = 5.0              # total model height (game engine scales to ~20-28m)
TRUNK_FRAC = 0.22         # shorter trunk before fork than elm
CANOPY_SPREAD = 3.5       # broader spread than elm (3.0)
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/oak.glb"

TRUNK_SEGS = 8
BRANCH_SEGS = 6
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

# ---- Generate leaf texture ----
# Oak leaves are lobed — wider individual leaf shapes with pointed tips
TEX = LEAF_TEX_SIZE
leaf_img = bpy.data.images.new("OakLeafTex", width=TEX, height=TEX, alpha=True)
pixels = [0.0] * (TEX * TEX * 4)

leaf_rng = random.Random(881)
for _ in range(70):  # oak has denser, larger leaves
    cx = leaf_rng.randint(6, TEX - 6)
    cy = leaf_rng.randint(6, TEX - 6)
    leaf_w = leaf_rng.randint(5, 10)   # wider lobed leaves
    leaf_h = leaf_rng.randint(8, 16)
    angle = leaf_rng.uniform(0, math.pi)
    # Oak leaf colors: darker green than elm
    r = leaf_rng.uniform(0.55, 0.70)
    g = leaf_rng.uniform(0.75, 0.90)
    b = leaf_rng.uniform(0.45, 0.60)
    for dy in range(-leaf_h, leaf_h + 1):
        for dx in range(-leaf_w, leaf_w + 1):
            rx = dx * math.cos(angle) + dy * math.sin(angle)
            ry = -dx * math.sin(angle) + dy * math.cos(angle)
            # Lobed shape: modulated ellipse
            lobe = 1.0 + 0.3 * math.sin(ry * 0.8)  # wavy edge for lobes
            if (rx / max(leaf_w * lobe, 1)) ** 2 + (ry / max(leaf_h, 1)) ** 2 <= 1.0:
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
# Bark: dark gray-brown — deeply furrowed, darker than elm
bark_mat = bpy.data.materials.new(name="OakBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf_bark.inputs["Base Color"].default_value = (0.22, 0.18, 0.12, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.92

# Leaves: alpha-clipped with oak leaf texture
leaf_mat = bpy.data.materials.new(name="OakLeaf")
leaf_mat.use_nodes = True
leaf_mat.blend_method = 'CLIP'
leaf_mat.alpha_threshold = 0.5
tree = leaf_mat.node_tree
bsdf_leaf = tree.nodes["Principled BSDF"]
bsdf_leaf.inputs["Roughness"].default_value = 0.78

tex_node = tree.nodes.new('ShaderNodeTexImage')
tex_node.image = leaf_img
tree.links.new(tex_node.outputs['Color'], bsdf_leaf.inputs['Base Color'])
tree.links.new(tex_node.outputs['Alpha'], bsdf_leaf.inputs['Alpha'])


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


def make_leaf_cluster(name, center, radius, flatten, rng_local):
    """Icosphere canopy cluster with leaf texture material."""
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=radius, location=tuple(center))
    obj = bpy.context.active_object
    obj.name = name
    for v in obj.data.vertices:
        v.co.z *= flatten
        noise = (math.sin(v.co.x * 5.3 + v.co.z * 4.1) *
                 math.cos(v.co.y * 4.7 + v.co.x * 3.2) * 0.18 * radius)
        v.co.x += noise
        v.co.y += noise * 0.8
        v.co.z += noise * 0.4
    obj.data.materials.append(leaf_mat)
    return obj


def bezier_point(p0, p1, p2, p3, t):
    """Evaluate cubic bezier at parameter t."""
    u = 1.0 - t
    return (p0 * u * u * u +
            p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t +
            p3 * t * t * t)


def make_oak_variant(vi, seed):
    """Generate one Red Oak tree variant.

    Key differences from elm:
    - Shorter trunk (22% vs 28%) before main fork
    - Wider branching angle (45-70° vs 20-40°)
    - More horizontal heavy limbs
    - Rounded dome canopy (not vase/drape)
    - Thicker trunk with more prominent buttress roots
    """
    rng = random.Random(seed)
    bark_parts = []
    leaf_parts = []

    split_h = TREE_H * TRUNK_FRAC
    trunk_r_base = 0.20     # thicker trunk than elm (0.16)
    trunk_r_top = 0.12
    lean_x = rng.uniform(-0.04, 0.04)
    lean_y = rng.uniform(-0.04, 0.04)

    # ---- Trunk: short, stout ----
    n_trunk = 8
    trunk_pts = []
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * split_h
        # Slight lean and organic wobble
        trunk_pts.append(Vector((
            lean_x * t + math.sin(t * math.pi * 1.3) * 0.04,
            lean_y * t + math.cos(t * math.pi * 0.9) * 0.03,
            z)))
    bark_parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                                trunk_r_base, trunk_r_top, TRUNK_SEGS, bark_mat))

    # ---- Buttress root flare: larger than elm ----
    n_roots = rng.randint(4, 6)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.20, 0.40)
        root_pts = [
            Vector((0, 0, 0.10)),
            Vector((dx * root_len * 0.4, dy * root_len * 0.4, 0.03)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        bark_parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                    trunk_r_base * 0.60, 0.018, SUB_SEGS, bark_mat))

    # ---- Major limbs: wide-angle, heavy, more horizontal than elm ----
    n_limbs = rng.randint(4, 6)
    limb_data = []

    for b in range(n_limbs):
        base_angle = (b / n_limbs) * 2.0 * math.pi + rng.uniform(-0.30, 0.30)
        dx = math.cos(base_angle)
        dy = math.sin(base_angle)

        # Oak limbs spread wider and more horizontally
        end_spread = CANOPY_SPREAD * rng.uniform(0.70, 1.10)
        end_h = TREE_H * rng.uniform(0.65, 0.88)  # lower canopy ceiling than elm

        p0 = trunk_pts[-1].copy()
        # Control points push more outward than upward (horizontal spread)
        p1 = Vector((lean_x + dx * end_spread * 0.25,
                      lean_y + dy * end_spread * 0.25,
                      split_h + (end_h - split_h) * 0.30))
        p2 = Vector((dx * end_spread * 0.70,
                      dy * end_spread * 0.70,
                      split_h + (end_h - split_h) * 0.60))
        p3 = Vector((dx * end_spread, dy * end_spread, end_h))

        n_pts = 10
        limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                    for t in range(n_pts)]

        # Thicker limbs than elm
        r_start = trunk_r_top * rng.uniform(0.55, 0.80)
        bark_parts.append(make_tube(f"limb_{vi}_{b}", limb_pts,
                                    r_start, 0.020, BRANCH_SEGS, bark_mat))
        limb_data.append((limb_pts, base_angle, end_spread))

        # ---- Secondary branches: more gnarled, irregular ----
        n_subs = rng.randint(3, 5)
        for s in range(n_subs):
            t_start = rng.uniform(0.20, 0.80)
            idx = int(t_start * (len(limb_pts) - 1))
            origin = limb_pts[idx].copy()
            sub_angle = base_angle + rng.uniform(-1.0, 1.0)
            sub_dx = math.cos(sub_angle)
            sub_dy = math.sin(sub_angle)
            sub_len = rng.uniform(0.6, 1.5)
            sub_pts = []
            for sp in range(5):
                st = sp / 4.0
                # More horizontal sub-branches
                sub_pts.append(Vector((
                    origin.x + sub_dx * sub_len * st,
                    origin.y + sub_dy * sub_len * st,
                    origin.z + sub_len * st * 0.20 + rng.uniform(-0.10, 0.10))))
            bark_parts.append(make_tube(f"sub_{vi}_{b}_{s}", sub_pts,
                                        0.028, 0.008, SUB_SEGS, bark_mat))

            # Tertiary twigs from sub-branches
            if rng.random() < 0.6:
                ti_origin = sub_pts[rng.randint(1, 3)]
                tw_angle = sub_angle + rng.uniform(-1.2, 1.2)
                tw_dx = math.cos(tw_angle)
                tw_dy = math.sin(tw_angle)
                tw_len = rng.uniform(0.3, 0.7)
                tw_pts = [
                    ti_origin.copy(),
                    Vector((ti_origin.x + tw_dx * tw_len * 0.5,
                            ti_origin.y + tw_dy * tw_len * 0.5,
                            ti_origin.z + tw_len * 0.15)),
                    Vector((ti_origin.x + tw_dx * tw_len,
                            ti_origin.y + tw_dy * tw_len,
                            ti_origin.z + tw_len * 0.25)),
                ]
                bark_parts.append(make_tube(f"twig_{vi}_{b}_{s}", tw_pts,
                                            0.012, 0.003, SUB_SEGS, bark_mat))

    # ---- Canopy: dense rounded dome ----
    # Oak canopy is rounder and denser than elm, less drooping

    # Along each major limb (upper 40-100%)
    for b, (limb_pts, angle, spread) in enumerate(limb_data):
        n_cl = rng.randint(14, 22)
        for c in range(n_cl):
            t = rng.uniform(0.35, 1.0)
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.7, 0.7)
            pos.y += rng.uniform(-0.7, 0.7)
            pos.z += rng.uniform(-0.2, 0.5)
            r = rng.uniform(0.30, 0.65)
            leaf_parts.append(make_leaf_cluster(
                f"lc_{vi}_{b}_{c}", pos, r, rng.uniform(0.45, 0.65), rng))

    # Dense dome fill — oak has rounded top, not pointed
    n_dome = rng.randint(20, 35)
    for f in range(n_dome):
        angle_f = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0, CANOPY_SPREAD * 0.7)
        z = TREE_H * rng.uniform(0.60, 0.95)
        x = math.cos(angle_f) * dist + rng.uniform(-0.4, 0.4)
        y = math.sin(angle_f) * dist + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.35, 0.70)
        leaf_parts.append(make_leaf_cluster(
            f"dome_{vi}_{f}", Vector((x, y, z)), r,
            rng.uniform(0.40, 0.60), rng))

    # Crown edge: rounded perimeter (not drooping like elm)
    n_edge = rng.randint(12, 18)
    for d in range(n_edge):
        angle_d = rng.uniform(0, 2.0 * math.pi)
        dist = CANOPY_SPREAD * rng.uniform(0.75, 1.05)
        z = TREE_H * rng.uniform(0.45, 0.75)
        x = math.cos(angle_d) * dist + rng.uniform(-0.3, 0.3)
        y = math.sin(angle_d) * dist + rng.uniform(-0.3, 0.3)
        r = rng.uniform(0.30, 0.55)
        leaf_parts.append(make_leaf_cluster(
            f"edge_{vi}_{d}", Vector((x, y, z)), r,
            rng.uniform(0.50, 0.70), rng))

    # Inner canopy fill (creates depth and density)
    n_inner = rng.randint(10, 16)
    for i_c in range(n_inner):
        angle_i = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0.4, CANOPY_SPREAD * 0.55)
        z = split_h + (TREE_H - split_h) * rng.uniform(0.25, 0.65)
        x = math.cos(angle_i) * dist
        y = math.sin(angle_i) * dist
        r = rng.uniform(0.25, 0.50)
        leaf_parts.append(make_leaf_cluster(
            f"inner_{vi}_{i_c}", Vector((x, y, z)), r,
            rng.uniform(0.45, 0.65), rng))

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
    final.name = f"OakTree_{vi + 1}"
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
print("\n" + "=" * 60)
print("Building 5 Red Oak variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_oak_variant(i, seed=100 + i * 23)
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
print(f"\nExported {len(variants)} Red Oak variants to {OUT_PATH}")

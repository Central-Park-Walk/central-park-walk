"""
Generate Austrian Pine (Pinus nigra) tree model for Central Park Walk.

Austrian Pine is the predominant conifer in Central Park — planted
extensively by Olmsted & Vaux. Stocky, pyramidal when young becoming
broad and flat-topped with age. Dark green needles, thick furrowed
gray-brown bark, strong horizontal branching.

Key characteristics:
  - Dense, dark green foliage (year-round evergreen)
  - Pyramidal when young, broad dome/flat-top when mature
  - Thick trunk with deeply furrowed dark bark
  - Strong horizontal to slightly drooping branches
  - Whorled branching pattern (branches emerge in tiers)

Generates 5 variants → models/trees/pine.glb
Run: blender --background --python scripts/make_pine.py
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector

# ---- Configuration ----
TREE_H = 5.5              # game-scale (engine scales to real ~12-18m)
TRUNK_FRAC = 0.15          # short clear trunk (low branches on mature pines)
CANOPY_SPREAD = 2.2        # broad spread
N_VARIANTS = 5
OUT_PATH = "/home/chris/central-park-walk/models/trees/pine.glb"

TRUNK_SEGS = 7
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

# ---- Needle texture ----
TEX = LEAF_TEX_SIZE
needle_img = bpy.data.images.new("PineNeedleTex", width=TEX, height=TEX, alpha=True)
pixels = [0.0] * (TEX * TEX * 4)

needle_rng = random.Random(601)
for _ in range(120):  # many needle clusters
    cx = needle_rng.randint(3, TEX - 3)
    cy = needle_rng.randint(3, TEX - 3)
    # Needle bundles: elongated thin strokes
    n_len = needle_rng.randint(5, 12)
    angle = needle_rng.uniform(0, math.pi)
    # Austrian pine: dark green, sometimes blue-green
    r = needle_rng.uniform(0.18, 0.32)
    g = needle_rng.uniform(0.35, 0.55)
    b = needle_rng.uniform(0.16, 0.30)
    for di in range(-n_len, n_len + 1):
        # Needle is 1-2 pixels wide
        for dw in range(-1, 2):
            px_x = cx + int(di * math.cos(angle) + dw * math.sin(angle))
            px_y = cy + int(di * math.sin(angle) - dw * math.cos(angle))
            px_x = px_x % TEX
            px_y = px_y % TEX
            idx = (px_y * TEX + px_x) * 4
            pixels[idx + 0] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b
            pixels[idx + 3] = 1.0

needle_img.pixels[:] = pixels
needle_img.pack()

# ---- Materials ----
# Bark: deeply furrowed dark gray-brown (Austrian pine characteristic)
bark_mat = bpy.data.materials.new(name="PineBark")
bark_mat.use_nodes = True
bsdf_bark = bark_mat.node_tree.nodes["Principled BSDF"]
bsdf_bark.inputs["Base Color"].default_value = (0.28, 0.22, 0.18, 1.0)
bsdf_bark.inputs["Roughness"].default_value = 0.92  # deeply furrowed

# Needles
needle_mat = bpy.data.materials.new(name="PineNeedle")
needle_mat.use_nodes = True
needle_mat.blend_method = 'CLIP'
needle_mat.alpha_threshold = 0.5
tree = needle_mat.node_tree
bsdf_needle = tree.nodes["Principled BSDF"]
bsdf_needle.inputs["Roughness"].default_value = 0.60

tex_node = tree.nodes.new('ShaderNodeTexImage')
tex_node.image = needle_img
tree.links.new(tex_node.outputs['Color'], bsdf_needle.inputs['Base Color'])
tree.links.new(tex_node.outputs['Alpha'], bsdf_needle.inputs['Alpha'])


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


def make_needle_cluster(name, center, radius, flatten, rng_local):
    """Create a dense needle foliage blob — flatter and more irregular than leaf clusters."""
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=1, radius=radius, location=tuple(center))
    obj = bpy.context.active_object
    obj.name = name
    for v in obj.data.vertices:
        v.co.z *= flatten
        # More angular distortion for conifer silhouette
        noise = (math.sin(v.co.x * 5.5 + v.co.z * 4.2) *
                 math.cos(v.co.y * 6.3 + v.co.x * 3.1) * 0.20 * radius)
        v.co.x += noise
        v.co.y += noise * 0.8
        v.co.z += noise * 0.4
    obj.data.materials.append(needle_mat)
    return obj


def bezier_point(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (p0 * u * u * u +
            p1 * 3.0 * u * u * t +
            p2 * 3.0 * u * t * t +
            p3 * t * t * t)


def make_pine_variant(vi, seed):
    """Generate one Austrian Pine tree variant.

    Key characteristics:
    - Thick straight trunk with deeply furrowed bark
    - Whorled branching (branches in distinct tiers)
    - Dense dark green needle masses
    - Pyramidal when young → broad/flat-topped when mature
    """
    rng = random.Random(seed)
    bark_parts = []
    needle_parts = []

    trunk_r_base = 0.14      # thick trunk
    trunk_r_top = 0.06
    lean_x = rng.uniform(-0.03, 0.03)
    lean_y = rng.uniform(-0.03, 0.03)

    # ---- Trunk: straight, thick ----
    n_trunk = 8
    trunk_pts = []
    # Trunk extends most of tree height (pines have a central leader)
    trunk_h = TREE_H * 0.85
    for i in range(n_trunk):
        t = i / (n_trunk - 1)
        z = t * trunk_h
        trunk_pts.append(Vector((
            lean_x * t + math.sin(t * math.pi) * 0.02,
            lean_y * t + math.cos(t * math.pi * 0.8) * 0.015,
            z)))
    bark_parts.append(make_tube(f"trunk_{vi}", trunk_pts,
                                trunk_r_base, trunk_r_top * 0.5, TRUNK_SEGS, bark_mat))

    # ---- Root buttress ----
    n_roots = rng.randint(3, 5)
    for r_idx in range(n_roots):
        angle = (r_idx / n_roots) * 2 * math.pi + rng.uniform(-0.3, 0.3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        root_len = rng.uniform(0.15, 0.28)
        root_pts = [
            Vector((0, 0, 0.08)),
            Vector((dx * root_len * 0.5, dy * root_len * 0.5, 0.03)),
            Vector((dx * root_len, dy * root_len, 0.0)),
        ]
        bark_parts.append(make_tube(f"root_{vi}_{r_idx}", root_pts,
                                    trunk_r_base * 0.50, 0.012, SUB_SEGS, bark_mat))

    # ---- Whorled branching: branches in distinct tiers ----
    # Mature Austrian pine: lower branches horizontal/drooping, upper ascending
    branch_start_h = TREE_H * TRUNK_FRAC
    n_whorls = rng.randint(4, 6)
    all_limb_data = []

    for w in range(n_whorls):
        whorl_t = (w + 0.5) / n_whorls
        whorl_h = branch_start_h + (trunk_h - branch_start_h) * whorl_t
        # Spread decreases toward top (pyramidal/dome shape)
        tier_spread = CANOPY_SPREAD * (1.0 - whorl_t * 0.55)
        # Branch angle: lower=horizontal/drooping, upper=ascending
        base_uplift = rng.uniform(-0.10, 0.05) + whorl_t * 0.25

        n_branches = rng.randint(3, 5)
        for b in range(n_branches):
            base_angle = (b / n_branches) * 2.0 * math.pi + rng.uniform(-0.25, 0.25)
            # Rotate each whorl slightly for natural look
            base_angle += w * 0.4
            dx = math.cos(base_angle)
            dy = math.sin(base_angle)

            end_spread = tier_spread * rng.uniform(0.70, 1.10)
            end_h = whorl_h + end_spread * base_uplift

            # Branch origin on trunk at whorl height
            trunk_idx = int(whorl_t * (len(trunk_pts) - 1))
            p0 = trunk_pts[trunk_idx].copy()
            p0.z = whorl_h  # exact whorl height

            p1 = Vector((p0.x + dx * end_spread * 0.25,
                          p0.y + dy * end_spread * 0.25,
                          whorl_h + (end_h - whorl_h) * 0.3))
            p2 = Vector((dx * end_spread * 0.65,
                          dy * end_spread * 0.65,
                          end_h + rng.uniform(-0.08, 0.08)))
            # Lower branches droop at tips
            droop = rng.uniform(-0.15, 0.0) if whorl_t < 0.5 else rng.uniform(-0.05, 0.10)
            p3 = Vector((dx * end_spread,
                          dy * end_spread,
                          end_h + droop))

            n_pts = 6
            limb_pts = [bezier_point(p0, p1, p2, p3, t / (n_pts - 1))
                        for t in range(n_pts)]

            r_start = 0.025 + (1.0 - whorl_t) * 0.02  # lower branches thicker
            bark_parts.append(make_tube(f"limb_{vi}_{w}_{b}", limb_pts,
                                        r_start, 0.008, BRANCH_SEGS, bark_mat))
            all_limb_data.append((limb_pts, base_angle, end_spread, whorl_t))

    # ---- Needle masses: dense, dark, concentrated at branch ends ----
    # Pines concentrate needles at branch tips, not along entire length

    for b, (limb_pts, angle, spread, whorl_t) in enumerate(all_limb_data):
        # More needles on outer portion of branch
        n_cl = rng.randint(8, 15)
        for c in range(n_cl):
            t = rng.uniform(0.50, 1.0)  # concentrated at tips
            idx = int(t * (len(limb_pts) - 1))
            idx2 = min(idx + 1, len(limb_pts) - 1)
            frac = t * (len(limb_pts) - 1) - idx
            pos = limb_pts[idx].lerp(limb_pts[idx2], frac)
            pos.x += rng.uniform(-0.25, 0.25)
            pos.y += rng.uniform(-0.25, 0.25)
            pos.z += rng.uniform(-0.15, 0.20)
            # Larger clusters than deciduous — dense needle masses
            r = rng.uniform(0.28, 0.55) * (0.7 + whorl_t * 0.3)
            needle_parts.append(make_needle_cluster(
                f"nc_{vi}_{b}_{c}", pos, r, rng.uniform(0.40, 0.60), rng))

    # Top crown: leader tip gets dense needle cap
    top_z = TREE_H * rng.uniform(0.88, 0.98)
    n_top = rng.randint(5, 9)
    for f in range(n_top):
        angle_f = rng.uniform(0, 2.0 * math.pi)
        dist = rng.uniform(0, CANOPY_SPREAD * 0.25)
        z = top_z + rng.uniform(-0.3, 0.15)
        x = lean_x + math.cos(angle_f) * dist
        y = lean_y + math.sin(angle_f) * dist
        r = rng.uniform(0.25, 0.50)
        needle_parts.append(make_needle_cluster(
            f"top_{vi}_{f}", Vector((x, y, z)), r,
            rng.uniform(0.45, 0.60), rng))

    # ---- Finalize ----
    all_parts = bark_parts + needle_parts
    for obj in all_parts:
        for poly in obj.data.polygons:
            poly.use_smooth = True

    bpy.ops.object.select_all(action='DESELECT')
    for obj in all_parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = all_parts[0]
    bpy.ops.object.join()

    final = bpy.context.active_object
    final.name = f"PineTree_{vi + 1}"
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
print("Building 5 Austrian Pine variants")
print("=" * 60 + "\n")

variants = []
for i in range(N_VARIANTS):
    v = make_pine_variant(i, seed=400 + i * 29)
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
print(f"\nExported {len(variants)} Austrian Pine variants to {OUT_PATH}")

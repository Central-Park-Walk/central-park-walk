"""Generate per-species vine models for Central Park Walk.

7 vine species with climbing-mechanism-specific geometry:
  Virginia Creeper — adhesive pad climbing, 5-palmate leaves
  English Ivy      — aerial rootlet climbing, one-sided, 3-5 lobed leaves
  Bittersweet      — twining spiral, simple leaves, berry clusters
  Porcelain Berry  — forked tendrils, maple-like leaves, multi-color berries
  Wild Grape       — forked tendrils, large leaves, grape clusters
  Honeysuckle      — twining spiral (small diameter), oval leaves, tubular flowers
  Wisteria         — heavy twining, compound leaves, pendant flower racemes

UV convention (matches vine.gdshader):
  UV.x near 0.5 = stem/vine body
  UV.x near 0/1 = leaf
  UV.y > 0.88   = berry/fruit
  UV.y > 0.92 with leaf UV.x = flower

Run: blender --background --python scripts/make_vine.py
Outputs: models/vegetation/Vine_*.glb (7 files, each with 3-4 named variants)
"""

import sys
import os
import math
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vegetation_helpers import *


# =========================================================================
# Core geometry builders
# =========================================================================

def make_vine_strand(bm, uv, co, seed, length, n_leaves, stem_radius=0.008,
                     leaf_size_range=(0.06, 0.14), add_berries=True,
                     add_tendrils=False):
    """Hanging vine strand from origin downward. Stem ribbon + leaf quads."""
    rng = random.Random(seed)
    n_segs = 8
    drift_angle = rng.uniform(0, math.tau)
    drift_mag = length * 0.06
    path = []
    for i in range(n_segs + 1):
        t = i / n_segs
        z = -length * t
        sway = math.sin(t * math.pi) * drift_mag
        x = math.cos(drift_angle) * sway + rng.gauss(0, 0.015) * (t + 0.2)
        y = math.sin(drift_angle) * sway + rng.gauss(0, 0.015) * (t + 0.2)
        path.append(Vector((x, y, z)))

    # Stem ribbon
    perp = Vector((-math.sin(drift_angle), math.cos(drift_angle), 0.0))
    prev_pair = None
    for i, pt in enumerate(path):
        t = i / n_segs
        r = stem_radius * (1.0 - t * 0.5)
        stem_col = [0.28 - t*0.06, 0.22 - t*0.04, 0.14 - t*0.02, 1.0]
        v1 = bm.verts.new(pt - perp * r)
        v2 = bm.verts.new(pt + perp * r)
        if prev_pair:
            pv1, pv2, pt0 = prev_pair
            try:
                f = bm.faces.new([pv1, pv2, v2, v1])
                for loop in f.loops:
                    loop[uv].uv = (0.5, t)
                    loop[co] = stem_col
            except ValueError:
                pass
        prev_pair = (v1, v2, t)

    # Leaves
    for j in range(n_leaves):
        t = rng.uniform(0.10, 0.92)
        seg_f = t * n_segs
        seg_i = min(int(seg_f), n_segs - 1)
        seg_frac = seg_f - seg_i
        pos = path[seg_i].lerp(path[min(seg_i + 1, n_segs)], seg_frac)
        angle = rng.uniform(0, math.tau)
        ls = rng.uniform(*leaf_size_range)
        green = (0.12 + rng.uniform(-0.03, 0.03),
                 0.30 + rng.uniform(-0.06, 0.06),
                 0.08 + rng.uniform(-0.02, 0.02))
        make_leaf_card(bm, pos + Vector((math.cos(angle), math.sin(angle), 0)) * 0.02,
                       ls, ls * 1.2, angle, rng.uniform(-0.4, 0.4), green, uv, co)

    # Berries
    if add_berries:
        for j in range(max(1, n_leaves // 3)):
            t = rng.uniform(0.25, 0.85)
            seg_f = t * n_segs
            seg_i = min(int(seg_f), n_segs - 1)
            pos = path[seg_i].lerp(path[min(seg_i + 1, n_segs)], seg_f - seg_i)
            angle = rng.uniform(0, math.tau)
            bs = rng.uniform(0.02, 0.04)
            right = Vector((math.cos(angle), math.sin(angle), 0.0)) * bs
            up_v = Vector((0, 0, 1)) * bs
            center = pos + right.normalized() * 0.03
            col_rgba = [0.25, 0.40, 0.30, 1.0]
            v1 = bm.verts.new(center - right)
            v2 = bm.verts.new(center + right)
            v3 = bm.verts.new(center + right + up_v)
            v4 = bm.verts.new(center - right + up_v)
            try:
                f = bm.faces.new([v1, v2, v3, v4])
                for loop in f.loops:
                    if loop.vert in (v1, v2):
                        loop[uv].uv = (0.0, 0.90)
                    else:
                        loop[uv].uv = (1.0, 1.00)
                    loop[co] = col_rgba
            except ValueError:
                pass

    # Tendrils
    if add_tendrils:
        for j in range(max(1, n_leaves // 4)):
            t = rng.uniform(0.15, 0.80)
            seg_f = t * n_segs
            seg_i = min(int(seg_f), n_segs - 1)
            pos = path[seg_i].lerp(path[min(seg_i + 1, n_segs)], seg_f - seg_i)
            ta = rng.uniform(0, math.tau)
            tl = rng.uniform(0.04, 0.10)
            tpts = [pos]
            for k in range(1, 4):
                kt = k / 3
                curl = math.sin(kt * math.pi * 2) * 0.015
                tpts.append(Vector((
                    pos.x + math.cos(ta) * tl * kt + curl,
                    pos.y + math.sin(ta) * tl * kt,
                    pos.z - 0.02 * kt)))
            make_tube(bm, tpts, 0.002, 0.0005, 3,
                      (0.22, 0.18, 0.08), (0.18, 0.14, 0.06), uv, co)


def make_spiral_wrap(bm, uv, co, seed, height=3.0, wrap_radius=0.15,
                     n_turns=2.5, n_leaves=6, leaf_size_range=(0.05, 0.09),
                     vine_r=0.014, add_flowers=False, flower_uv_y=0.94):
    """Vine spiraling around imaginary trunk, origin at base."""
    rng = random.Random(seed)
    n_pts = int(n_turns * 12)
    path = []
    for i in range(n_pts + 1):
        t = i / n_pts
        angle = t * n_turns * math.tau
        z = height * t
        r = wrap_radius + rng.gauss(0, 0.008)
        path.append(Vector((math.cos(angle) * r, math.sin(angle) * r, z)))

    # Stem ribbon
    prev_pair = None
    for i, pt in enumerate(path):
        t = i / n_pts
        r = vine_r * (1.0 - t * 0.3)
        outward = Vector((pt.x, pt.y, 0.0))
        if outward.length > 0.001:
            outward = outward.normalized() * r
        else:
            outward = Vector((r, 0, 0))
        stem_col = [0.28, 0.22, 0.14, 1.0]
        v1 = bm.verts.new(pt - outward)
        v2 = bm.verts.new(pt + outward)
        if prev_pair:
            pv1, pv2 = prev_pair
            try:
                f = bm.faces.new([pv1, pv2, v2, v1])
                for loop in f.loops:
                    loop[uv].uv = (0.5, t)
                    loop[co] = stem_col
            except ValueError:
                pass
        prev_pair = (v1, v2)

    # Leaves sprouting outward
    for j in range(n_leaves):
        t = rng.uniform(0.15, 0.85)
        seg_f = t * n_pts
        seg_i = min(int(seg_f), n_pts - 1)
        pos = path[seg_i].lerp(path[min(seg_i + 1, n_pts)], seg_f - seg_i)
        outward_dir = Vector((pos.x, pos.y, 0.0))
        if outward_dir.length > 0.001:
            outward_dir = outward_dir.normalized()
        else:
            outward_dir = Vector((1, 0, 0))
        center = pos + outward_dir * (vine_r + 0.01)
        la = math.atan2(outward_dir.y, outward_dir.x) + rng.uniform(-0.5, 0.5)
        ls = rng.uniform(*leaf_size_range)
        green = (0.12 + rng.uniform(-0.03, 0.03),
                 0.30 + rng.uniform(-0.05, 0.05),
                 0.08 + rng.uniform(-0.02, 0.02))
        make_leaf_card(bm, center, ls, ls * 1.2, la, rng.uniform(-0.3, 0.3), green, uv, co)

    # Flowers (wisteria racemes, honeysuckle tubular)
    if add_flowers:
        for j in range(max(1, n_leaves // 3)):
            t = rng.uniform(0.30, 0.80)
            seg_f = t * n_pts
            seg_i = min(int(seg_f), n_pts - 1)
            pos = path[seg_i].lerp(path[min(seg_i + 1, n_pts)], seg_f - seg_i)
            outward_dir = Vector((pos.x, pos.y, 0.0))
            if outward_dir.length > 0.001:
                outward_dir = outward_dir.normalized()
            else:
                outward_dir = Vector((1, 0, 0))
            center = pos + outward_dir * (vine_r + 0.02)
            fs = rng.uniform(0.04, 0.08)
            right = Vector((outward_dir.y, -outward_dir.x, 0)) * fs * 0.5
            up_v = Vector((0, 0, -1)) * fs * 1.5  # hanging down
            fc = [0.55, 0.30, 0.65, 1.0]  # purple for wisteria
            v1 = bm.verts.new(center - right)
            v2 = bm.verts.new(center + right)
            v3 = bm.verts.new(center + right + up_v)
            v4 = bm.verts.new(center - right + up_v)
            try:
                f = bm.faces.new([v1, v2, v3, v4])
                for loop in f.loops:
                    if loop.vert in (v1, v2):
                        loop[uv].uv = (0.0, flower_uv_y)
                    else:
                        loop[uv].uv = (1.0, 1.0)
                    loop[co] = fc
            except ValueError:
                pass


def make_climbing_pad(bm, uv, co, seed, height=2.0, width=0.6,
                      n_leaves=12, leaf_size_range=(0.05, 0.10)):
    """Flat climbing pad — planar mesh hugging an imaginary trunk surface.
    Leaves sprout outward. Used for adhesive-pad and rootlet climbers."""
    rng = random.Random(seed)
    # Flat panel at slight distance from trunk center
    trunk_r = 0.20  # imaginary trunk radius
    face_angle = rng.uniform(0, math.tau)
    n_segs = 6
    hw = width * 0.5

    # Stem path climbing up
    path = []
    for i in range(n_segs + 1):
        t = i / n_segs
        z = height * t
        # Slight meandering
        offset = rng.gauss(0, 0.02)
        x = math.cos(face_angle) * trunk_r + offset
        y = math.sin(face_angle) * trunk_r + offset
        path.append(Vector((x, y, z)))

    stem_col = (0.25, 0.19, 0.10)
    make_tube(bm, path, 0.006, 0.003, 4, stem_col, stem_col, uv, co)

    # Leaves sprouting outward from stem
    for j in range(n_leaves):
        t = rng.uniform(0.05, 0.95)
        idx = min(int(t * n_segs), n_segs - 1)
        frac = t * n_segs - idx
        pos = path[idx].lerp(path[min(idx + 1, n_segs)], frac)
        # Outward from trunk
        outward = Vector((math.cos(face_angle), math.sin(face_angle), 0))
        spread = rng.uniform(-0.6, 0.6)
        la = face_angle + spread
        center = pos + outward * 0.02
        ls = rng.uniform(*leaf_size_range)
        green = (0.12 + rng.uniform(-0.03, 0.03),
                 0.30 + rng.uniform(-0.05, 0.05),
                 0.08 + rng.uniform(-0.02, 0.02))
        make_leaf_card(bm, center, ls, ls * 1.3, la, rng.uniform(-0.3, 0.3), green, uv, co)


def make_ground_runner(bm, uv, co, seed, radius=1.5, n_leaves=15,
                       leaf_size_range=(0.04, 0.08)):
    """Ground-running vine patch — flat mat radiating from center."""
    rng = random.Random(seed)
    n_arms = rng.randint(3, 5)
    for arm in range(n_arms):
        angle = (arm / n_arms) * math.tau + rng.uniform(-0.3, 0.3)
        arm_len = radius * rng.uniform(0.5, 1.0)
        n_seg = 4
        pts = []
        for i in range(n_seg + 1):
            t = i / n_seg
            pts.append(Vector((
                math.cos(angle) * arm_len * t + rng.gauss(0, 0.03),
                math.sin(angle) * arm_len * t + rng.gauss(0, 0.03),
                0.01 + rng.uniform(0, 0.01)
            )))
        stem_col = (0.22, 0.18, 0.10)
        make_tube(bm, pts, 0.004, 0.002, 3, stem_col, stem_col, uv, co)

        # Leaves along arm
        leaves_per_arm = n_leaves // n_arms
        for j in range(leaves_per_arm):
            t = rng.uniform(0.1, 0.95)
            idx = min(int(t * n_seg), n_seg - 1)
            pos = pts[idx].lerp(pts[min(idx + 1, n_seg)], t * n_seg - idx)
            la = angle + rng.uniform(-1.0, 1.0)
            ls = rng.uniform(*leaf_size_range)
            green = (0.10, 0.28 + rng.uniform(-0.05, 0.05), 0.06)
            make_leaf_card(bm, pos, ls, ls * 1.2, la, rng.uniform(-0.2, 0.2), green, uv, co)


# =========================================================================
# Per-species builders
# =========================================================================

def build_virginia_creeper(seed_base):
    """Adhesive pad climber — 5-palmate leaves, brilliant fall red."""
    variants = []
    for i in range(4):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        # Mix of climbing pads and ground runner
        if i < 3:
            make_climbing_pad(bm, uv, co, s, height=rng.uniform(1.5, 3.0),
                              n_leaves=rng.randint(10, 18),
                              leaf_size_range=(0.06, 0.12))
        else:
            make_ground_runner(bm, uv, co, s, radius=rng.uniform(1.0, 2.0),
                               n_leaves=rng.randint(12, 20),
                               leaf_size_range=(0.05, 0.10))
        variants.append((bm, "VCreeper_%s" % chr(65 + i)))
    return variants


def build_english_ivy(seed_base):
    """Aerial rootlet climber — one-sided, evergreen, dark 3-5 lobed leaves."""
    variants = []
    for i in range(4):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        if i < 3:
            make_climbing_pad(bm, uv, co, s, height=rng.uniform(1.5, 4.0),
                              n_leaves=rng.randint(15, 25),
                              leaf_size_range=(0.04, 0.08))
        else:
            make_ground_runner(bm, uv, co, s, radius=rng.uniform(1.5, 2.5),
                               n_leaves=rng.randint(20, 30),
                               leaf_size_range=(0.03, 0.06))
        variants.append((bm, "Ivy_%s" % chr(65 + i)))
    return variants


def build_bittersweet(seed_base):
    """Twining spiral — tight wraps, orange/red berries."""
    variants = []
    for i in range(4):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        make_spiral_wrap(bm, uv, co, s,
                         height=rng.uniform(2.0, 4.0),
                         wrap_radius=rng.uniform(0.12, 0.18),
                         n_turns=rng.uniform(2.5, 4.0),
                         n_leaves=rng.randint(6, 12),
                         leaf_size_range=(0.05, 0.09),
                         vine_r=rng.uniform(0.012, 0.020))
        variants.append((bm, "Bitter_%s" % chr(65 + i)))
    return variants


def build_porcelain_berry(seed_base):
    """Forked tendrils — maple-like leaves, multi-color berries."""
    variants = []
    for i in range(4):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        make_vine_strand(bm, uv, co, s,
                         length=rng.uniform(2.0, 4.0),
                         n_leaves=rng.randint(8, 14),
                         stem_radius=0.007,
                         leaf_size_range=(0.06, 0.12),
                         add_berries=True, add_tendrils=True)
        variants.append((bm, "Porcelain_%s" % chr(65 + i)))
    return variants


def build_wild_grape(seed_base):
    """Forked tendrils — large leaves, small grape clusters, shredding bark."""
    variants = []
    for i in range(4):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        make_vine_strand(bm, uv, co, s,
                         length=rng.uniform(3.0, 6.0),
                         n_leaves=rng.randint(6, 12),
                         stem_radius=0.012,
                         leaf_size_range=(0.08, 0.16),
                         add_berries=True, add_tendrils=True)
        variants.append((bm, "Grape_%s" % chr(65 + i)))
    return variants


def build_honeysuckle(seed_base):
    """Twining — smaller spiral, oval leaves, tubular white-yellow flowers."""
    variants = []
    for i in range(4):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        make_spiral_wrap(bm, uv, co, s,
                         height=rng.uniform(1.5, 3.0),
                         wrap_radius=rng.uniform(0.06, 0.12),
                         n_turns=rng.uniform(3.0, 5.0),
                         n_leaves=rng.randint(8, 14),
                         leaf_size_range=(0.03, 0.06),
                         vine_r=0.006,
                         add_flowers=True, flower_uv_y=0.94)
        variants.append((bm, "Honey_%s" % chr(65 + i)))
    return variants


def build_wisteria(seed_base):
    """Heavy twining — compound leaves, pendant purple flower racemes."""
    variants = []
    for i in range(3):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        co = bm.loops.layers.color.new("Col")
        s = seed_base + i
        rng = random.Random(s)
        make_spiral_wrap(bm, uv, co, s,
                         height=rng.uniform(2.5, 4.5),
                         wrap_radius=rng.uniform(0.08, 0.15),
                         n_turns=rng.uniform(2.0, 3.0),
                         n_leaves=rng.randint(8, 14),
                         leaf_size_range=(0.05, 0.10),
                         vine_r=rng.uniform(0.018, 0.030),
                         add_flowers=True, flower_uv_y=0.94)
        variants.append((bm, "Wisteria_%s" % chr(65 + i)))
    return variants


# =========================================================================
# Export
# =========================================================================

VINE_SPECIES = [
    ("Vine_VirginiaCreeper", build_virginia_creeper, 4000),
    ("Vine_EnglishIvy",      build_english_ivy,      4100),
    ("Vine_Bittersweet",     build_bittersweet,       4200),
    ("Vine_PorcelainBerry",  build_porcelain_berry,   4300),
    ("Vine_WildGrape",       build_wild_grape,        4400),
    ("Vine_Honeysuckle",     build_honeysuckle,       4500),
    ("Vine_Wisteria",        build_wisteria,          4600),
]

if __name__ == "__main__":
    print("=" * 60)
    print(f"Building {len(VINE_SPECIES)} vine species")
    print("=" * 60)

    for glb_name, builder, seed_base in VINE_SPECIES:
        print(f"\n  Building {glb_name}...")
        clear_scene()

        variants = builder(seed_base)
        spacing = 3.0
        for vi, (bm, mesh_name) in enumerate(variants):
            mesh = bpy.data.meshes.new(mesh_name)
            bm.to_mesh(mesh)
            # Hemisphere-biased normals for natural soft shading
            normals = [(0, 0, 0)] * len(mesh.loops)
            for poly in mesh.polygons:
                fn = Vector(poly.normal)
                up = Vector((0, 0, 1))
                n = fn.lerp(up, 0.35).normalized()
                for li in poly.loop_indices:
                    normals[li] = tuple(n)
            mesh.normals_split_custom_set(normals)

            obj = bpy.data.objects.new(mesh_name, mesh)
            bpy.context.collection.objects.link(obj)
            mat = make_material(mesh_name + "_Mat")
            obj.data.materials.append(mat)
            for poly in obj.data.polygons:
                poly.use_smooth = True
            obj.location = (vi * spacing, 0, 0)
            bm.free()

        # Apply transforms
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        path = os.path.join(VEG_DIR, f"{glb_name}.glb")
        bpy.ops.export_scene.gltf(
            filepath=path, export_format='GLB', use_selection=True,
            export_normals=True, export_vertex_color='ACTIVE', export_apply=True)
        total_verts = sum(len(bpy.data.objects[v[1]].data.vertices)
                          for v in variants if v[1] in bpy.data.objects)
        print(f"  {glb_name}: {len(variants)} variants, ~{total_verts} total verts -> {path}")

    print(f"\n{'=' * 60}")
    print(f"Done — {len(VINE_SPECIES)} vine species exported")
    print("=" * 60)

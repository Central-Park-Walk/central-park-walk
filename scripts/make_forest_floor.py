"""Generate procedural forest floor models for Central Park Walk.

Leaf litter, moss patches, fallen branches, and seedlings — the ground
cover layer that makes woodland areas feel complete. All models are
procedural with vertex colors, no external textures required.

Run: blender --background --python scripts/make_forest_floor.py

Outputs to models/vegetation/:
  GroundCover_DeadLeaves_01.glb  — cluster of fallen autumn leaves
  GroundCover_DeadLeaves_02.glb  — variant
  GroundCover_ForestLeaves_01.glb — decomposing year-round litter
  GroundCover_ForestLeaves_02.glb — variant
  GroundCover_Moss_01.glb        — low green moss patch ~15cm
  GroundCover_Moss_02.glb        — variant
  GroundCover_Branch_01.glb      — fallen twig + offshoots ~50cm
  GroundCover_Branch_02.glb      — variant
  GroundCover_Seedling_01.glb    — tiny deciduous seedling ~6cm
  GroundCover_Seedling_02.glb    — tiny conifer seedling ~5cm
"""

import sys
import os
import math
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vegetation_helpers import *


def _dead_leaf_quad(bm, uv, co, cx, cy, cz, angle, hw, hh, color, curl=0.0):
    """One fallen leaf as a tilted quad."""
    ca, sa = math.cos(angle), math.sin(angle)
    col_rgba = list(color) + [1.0]
    v0 = bm.verts.new((cx - ca*hw + sa*hh, cy - sa*hw - ca*hh, cz))
    v1 = bm.verts.new((cx + ca*hw + sa*hh, cy + sa*hw - ca*hh, cz))
    v2 = bm.verts.new((cx + ca*hw - sa*hh, cy + sa*hw + ca*hh, cz + curl))
    v3 = bm.verts.new((cx - ca*hw - sa*hh, cy - sa*hw + ca*hh, cz + curl))
    try:
        f = bm.faces.new([v0, v1, v2, v3])
        uv_map = {id(v0): (0.0, 0.0), id(v1): (1.0, 0.0),
                  id(v2): (1.0, 1.0), id(v3): (0.0, 1.0)}
        for loop in f.loops:
            loop[uv].uv = uv_map[id(loop.vert)]
            loop[co] = col_rgba
    except ValueError:
        pass


def make_dead_leaves(seed, n_leaves=6):
    """Cluster of fallen autumn leaves lying flat with slight curl."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)
    palette = [
        (0.55, 0.32, 0.08), (0.72, 0.45, 0.10), (0.65, 0.25, 0.05),
        (0.80, 0.55, 0.12), (0.50, 0.28, 0.06), (0.60, 0.35, 0.08),
    ]
    for _ in range(n_leaves):
        size = rng.uniform(0.04, 0.10)
        _dead_leaf_quad(bm, uv, co,
            rng.gauss(0, 0.12), rng.gauss(0, 0.12),
            rng.uniform(0.005, 0.025),
            rng.uniform(0, math.tau),
            size * 0.4, size * 0.6,
            palette[rng.randint(0, len(palette)-1)],
            rng.uniform(0.01, 0.03))
    return bm


def make_forest_leaves(seed, n_leaves=8):
    """Decomposing leaf litter — darker, year-round."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)
    palette = [
        (0.22, 0.15, 0.06), (0.30, 0.20, 0.08), (0.25, 0.18, 0.07),
        (0.18, 0.12, 0.05), (0.28, 0.16, 0.06),
    ]
    for _ in range(n_leaves):
        size = rng.uniform(0.03, 0.08)
        _dead_leaf_quad(bm, uv, co,
            rng.gauss(0, 0.15), rng.gauss(0, 0.15),
            rng.uniform(0.002, 0.015),
            rng.uniform(0, math.tau),
            size * 0.35, size * 0.55,
            palette[rng.randint(0, len(palette)-1)])
    return bm


def make_moss(seed):
    """Low-profile moss patch — irregular green mound ~15cm across."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)
    radius = 0.10
    for _ in range(12):
        a = rng.uniform(0, math.tau)
        dist = (rng.uniform(0, 1) ** 0.5) * radius
        cx = math.cos(a) * dist
        cy = math.sin(a) * dist
        r_frac = dist / radius
        cz = max(0.002, 0.025 * (1.0 - r_frac * r_frac))
        size = rng.uniform(0.02, 0.05)
        g = rng.uniform(0.20, 0.35)
        color = (0.05 + rng.uniform(-0.02, 0.02), g, 0.03 + rng.uniform(-0.01, 0.01))
        col_rgba = list(color) + [1.0]
        qa = rng.uniform(0, math.tau)
        hw = size * 0.5
        qc, qs = math.cos(qa), math.sin(qa)
        v0 = bm.verts.new((cx - hw*qc, cy - hw*qs, cz))
        v1 = bm.verts.new((cx + hw*qc, cy + hw*qs, cz))
        v2 = bm.verts.new((cx + hw*qs, cy - hw*qc, cz + 0.008))
        v3 = bm.verts.new((cx - hw*qs, cy + hw*qc, cz + 0.008))
        try:
            f = bm.faces.new([v0, v1, v2, v3])
            uv_map = {id(v0): (0.0, 0.0), id(v1): (1.0, 0.0),
                      id(v2): (1.0, 1.0), id(v3): (0.0, 1.0)}
            for loop in f.loops:
                loop[uv].uv = uv_map[id(loop.vert)]
                loop[co] = col_rgba
        except ValueError:
            pass
    return bm


def make_branch(seed):
    """Small fallen branch ~40-70cm with 2-3 twig offshoots."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)
    length = rng.uniform(0.35, 0.70)
    angle = rng.uniform(0, math.tau)
    ca, sa = math.cos(angle), math.sin(angle)
    n_seg = 6
    pts = []
    for i in range(n_seg + 1):
        t = i / n_seg
        pts.append(Vector((
            ca * length * t + rng.gauss(0, 0.01),
            sa * length * t + rng.gauss(0, 0.01),
            0.008 + 0.005 * math.sin(t * math.pi)
        )))
    bark_base = (0.30, 0.22, 0.12)
    bark_tip = (0.25, 0.18, 0.10)
    make_tube(bm, pts, 0.008, 0.004, 4, bark_base, bark_tip, uv, co)
    for _ in range(rng.randint(2, 3)):
        ai = rng.randint(1, n_seg - 1)
        origin = pts[ai]
        ta = angle + rng.uniform(-1.2, 1.2)
        tl = rng.uniform(0.08, 0.18)
        tpts = [Vector((
            origin.x + math.cos(ta) * tl * (i/3),
            origin.y + math.sin(ta) * tl * (i/3),
            origin.z + 0.003 * (i/3)
        )) for i in range(4)]
        make_tube(bm, tpts, 0.003, 0.001, 3, bark_base, bark_tip, uv, co)
    return bm


def make_seedling_deciduous(seed):
    """Tiny deciduous seedling — thin stem + 2-4 leaves, ~6cm tall."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)
    h = rng.uniform(0.04, 0.08)
    stem_col = (0.22, 0.18, 0.08)
    make_tube(bm, [Vector((0,0,0)), Vector((0,0,h))], 0.0015, 0.001, 3,
              stem_col, stem_col, uv, co)
    for i in range(rng.randint(2, 4)):
        la = (i / 3) * math.tau + rng.uniform(-0.3, 0.3)
        lh = h * rng.uniform(0.5, 0.95)
        ls = rng.uniform(0.012, 0.025)
        green = (0.10 + rng.uniform(-0.03, 0.03),
                 0.28 + rng.uniform(-0.06, 0.06),
                 0.04 + rng.uniform(-0.02, 0.02))
        make_leaf_card(bm, Vector((0, 0, lh)), ls, ls * 1.4,
                       la, rng.uniform(-0.3, 0.3), green, uv, co)
    return bm


def make_seedling_conifer(seed):
    """Tiny conifer seedling — thin stem + needle tufts, ~5cm tall."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)
    h = rng.uniform(0.03, 0.06)
    stem_col = (0.20, 0.14, 0.06)
    make_tube(bm, [Vector((0,0,0)), Vector((0,0,h))], 0.001, 0.0008, 3,
              stem_col, stem_col, uv, co)
    for i in range(rng.randint(3, 5)):
        th = h * (0.3 + 0.7 * i / 4)
        ts = 0.008 + 0.006 * (1.0 - i / 4)
        green = (0.04, 0.18 + rng.uniform(-0.03, 0.03), 0.03)
        col_rgba = list(green) + [1.0]
        for p in range(2):
            a = (p / 2) * math.pi + rng.uniform(-0.3, 0.3)
            ca, sa = math.cos(a), math.sin(a)
            hw = ts * 0.5
            v0 = bm.verts.new((-ca*hw, -sa*hw, th - 0.003))
            v1 = bm.verts.new((ca*hw, sa*hw, th - 0.003))
            v2 = bm.verts.new((ca*hw*0.3, sa*hw*0.3, th + ts))
            try:
                f = bm.faces.new([v0, v1, v2])
                for loop in f.loops:
                    loop[uv].uv = (0.5, 0.5)
                    loop[co] = col_rgba
            except ValueError:
                pass
    return bm


# =========================================================================
# Build all
# =========================================================================

MODELS = [
    (lambda: make_dead_leaves(3001, 6),      "GroundCover_DeadLeaves_01"),
    (lambda: make_dead_leaves(3002, 7),      "GroundCover_DeadLeaves_02"),
    (lambda: make_forest_leaves(3003, 8),    "GroundCover_ForestLeaves_01"),
    (lambda: make_forest_leaves(3004, 7),    "GroundCover_ForestLeaves_02"),
    (lambda: make_moss(3005),                "GroundCover_Moss_01"),
    (lambda: make_moss(3006),                "GroundCover_Moss_02"),
    (lambda: make_branch(3007),              "GroundCover_Branch_01"),
    (lambda: make_branch(3008),              "GroundCover_Branch_02"),
    (lambda: make_seedling_deciduous(3009),  "GroundCover_Seedling_01"),
    (lambda: make_seedling_conifer(3010),    "GroundCover_Seedling_02"),
]

if __name__ == "__main__":
    print("=" * 60)
    print(f"Building {len(MODELS)} ground cover models")
    print("=" * 60)

    for func, name in MODELS:
        print(f"\n  Building {name}...")
        clear_scene()
        bm = func()

        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        # Upward-biased normals for ground-lying objects
        normals = [(0, 0, 0)] * len(mesh.loops)
        for poly in mesh.polygons:
            fn = Vector(poly.normal)
            up = Vector((0, 0, 1))
            n = fn.lerp(up, 0.5).normalized()
            for li in poly.loop_indices:
                normals[li] = tuple(n)
        mesh.normals_split_custom_set(normals)

        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        mat = make_material(name + "_Mat")
        obj.data.materials.append(mat)
        for poly in obj.data.polygons:
            poly.use_smooth = True
        bm.free()

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        path = os.path.join(VEG_DIR, f"{name}.glb")
        bpy.ops.export_scene.gltf(
            filepath=path, export_format='GLB', use_selection=True,
            export_normals=True, export_vertex_color='ACTIVE', export_apply=True)
        nv = len(mesh.vertices)
        nf = len(mesh.polygons)
        print(f"  {name}: {nv} verts, {nf} faces -> {path}")

    print(f"\n{'=' * 60}")
    print(f"Done — {len(MODELS)} ground cover models exported")
    print("=" * 60)

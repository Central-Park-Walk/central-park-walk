"""Create seasonal wildflower meshes for Central Park.

Run in Blender: blender --background --python scripts/make_seasonal_flowers.py

Spring flowers (appear season_t 0.0-1.2):
  Flower_Crocus.glb    — purple/white crocus (first spring bulb)
  Flower_Daffodil.glb  — yellow daffodil with trumpet

Fall flowers (appear season_t 1.8-2.8):
  Flower_Goldenrod.glb — tall golden spike
  Flower_Aster.glb     — purple/white daisy-like
"""

import bpy
import bmesh
import math
import os
import mathutils

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def export_glb(obj, name):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT_DIR, f"{name}.glb")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_normals=True,
        export_vertex_color='ACTIVE',
        export_apply=True,
    )
    print(f"  Exported {path}")


def add_quad(bm, v0, v1, v2, v3, color, uv_y, uv_layer, col_layer):
    """Add a quad (2 tris) with color and UV."""
    f1 = bm.faces.new([v0, v1, v2])
    f2 = bm.faces.new([v0, v2, v3])
    col_rgba = [color[0], color[1], color[2], 1.0]
    for f in [f1, f2]:
        for loop in f.loops:
            loop[uv_layer].uv = (0.5, uv_y)
            loop[col_layer] = col_rgba


def make_stem_verts(bm, height, segments, width, color_base, color_tip, uv_layer, col_layer):
    """Create stem geometry, return top Z position."""
    verts = []
    for i in range(segments + 1):
        t = i / segments
        z = height * t
        hw = width * (1.0 - t * 0.3)
        col = [color_base[j] + (color_tip[j] - color_base[j]) * t for j in range(3)] + [1.0]
        v_l = bm.verts.new((-hw, 0, z))
        v_r = bm.verts.new((hw, 0, z))
        verts.append((v_l, v_r, t * 0.4, col))  # UV.y 0-0.4 for stem

    for i in range(segments):
        bl, br, uv_b, col_b = verts[i]
        tl, tr, uv_t, col_t = verts[i + 1]
        f = bm.faces.new([bl, br, tr, tl])
        for loop in f.loops:
            v = loop.vert
            if v in (bl, br):
                loop[uv_layer].uv = (0.5, uv_b)
                loop[col_layer] = col_b
            else:
                loop[uv_layer].uv = (0.5, uv_t)
                loop[col_layer] = col_t
    return height


def make_petal_ring(bm, cz, radius, n, petal_len, petal_w, color, cup, uv_layer, col_layer):
    """Ring of petals at height cz."""
    for i in range(n):
        a = (i / n) * math.tau + (i * 0.3)  # slight offset for natural look
        dx, dy = math.cos(a), math.sin(a)
        base = mathutils.Vector((dx * radius * 0.3, dy * radius * 0.3, cz))
        tip_z = cz + math.sin(cup) * petal_len
        tip_r = math.cos(cup) * petal_len if cup != 0 else petal_len
        tip = mathutils.Vector((dx * (radius * 0.3 + tip_r), dy * (radius * 0.3 + tip_r), tip_z))
        px, py = -dy * petal_w * 0.5, dx * petal_w * 0.5
        mid = base.lerp(tip, 0.5)
        left = mathutils.Vector((mid.x + px, mid.y + py, mid.z))
        right = mathutils.Vector((mid.x - px, mid.y - py, mid.z))
        vb = bm.verts.new(base)
        vl = bm.verts.new(left)
        vt = bm.verts.new(tip)
        vr = bm.verts.new(right)
        col_rgba = [color[0], color[1], color[2], 1.0]
        for verts in [[vb, vl, vt], [vb, vt, vr]]:
            f = bm.faces.new(verts)
            for loop in f.loops:
                loop[uv_layer].uv = (0.5, 0.8)
                loop[col_layer] = col_rgba


def finalize(bm, name):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    normals = [(0, 0, 0)] * len(mesh.loops)
    for poly in mesh.polygons:
        fn = mathutils.Vector(poly.normal)
        up = mathutils.Vector((0, 0, 1))
        n = fn.lerp(up, 0.4).normalized()
        for li in poly.loop_indices:
            normals[li] = tuple(n)
    mesh.normals_split_custom_set(normals)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.rotation_euler = (math.pi / 2, 0, 0)
    bm.free()
    return obj


def make_crocus():
    """Purple crocus: 6 pointed petals in a cup, 5cm stem. First spring flower."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    top = make_stem_verts(bm, 0.05, 2, 0.002, (0.15, 0.30, 0.08), (0.20, 0.36, 0.10), uv, co)
    # 6 cupped petals — mix of purple and white (real crocuses vary)
    make_petal_ring(bm, top, 0.006, 6, 0.018, 0.008,
                    (0.55, 0.30, 0.70), 0.5, uv, co)
    # Yellow stamens in center
    make_petal_ring(bm, top + 0.005, 0.002, 3, 0.005, 0.002,
                    (0.90, 0.80, 0.15), 0.7, uv, co)
    return finalize(bm, "Flower_Crocus")


def make_daffodil():
    """Yellow daffodil: 6 petals + central trumpet, 15cm stem."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    top = make_stem_verts(bm, 0.15, 3, 0.003, (0.12, 0.28, 0.06), (0.18, 0.35, 0.08), uv, co)
    # 6 yellow petals radiating outward
    make_petal_ring(bm, top, 0.008, 6, 0.020, 0.010,
                    (0.95, 0.88, 0.20), 0.15, uv, co)
    # Central trumpet (deeper yellow/orange)
    make_petal_ring(bm, top + 0.003, 0.004, 6, 0.010, 0.005,
                    (0.95, 0.72, 0.12), 0.6, uv, co)
    return finalize(bm, "Flower_Daffodil")


def make_goldenrod():
    """Goldenrod: tall spike of tiny yellow flowers, 25cm stem."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    top = make_stem_verts(bm, 0.25, 4, 0.003, (0.14, 0.30, 0.06), (0.20, 0.38, 0.08), uv, co)
    # Spike of tiny yellow florets along the top 8cm
    for j in range(4):
        h = top - 0.02 * j
        r = 0.012 - j * 0.002
        make_petal_ring(bm, h, r, 5, 0.006, 0.004,
                        (0.92, 0.82, 0.15), 0.3, uv, co)
    return finalize(bm, "Flower_Goldenrod")


def make_aster():
    """New England aster: purple daisy-like, 20cm stem. Fall bloomer."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    top = make_stem_verts(bm, 0.20, 3, 0.002, (0.12, 0.26, 0.06), (0.16, 0.32, 0.08), uv, co)
    # Purple ray petals
    make_petal_ring(bm, top, 0.005, 10, 0.012, 0.004,
                    (0.58, 0.28, 0.68), 0.1, uv, co)
    # Yellow disc center
    make_petal_ring(bm, top + 0.002, 0.003, 5, 0.004, 0.003,
                    (0.90, 0.80, 0.20), 0.3, uv, co)
    return finalize(bm, "Flower_Aster")


if __name__ == "__main__":
    print("Creating seasonal flower meshes...")
    for func, name in [(make_crocus, "Flower_Crocus"),
                       (make_daffodil, "Flower_Daffodil"),
                       (make_goldenrod, "Flower_Goldenrod"),
                       (make_aster, "Flower_Aster")]:
        clear_scene()
        obj = func()
        export_glb(obj, name)
    print("Done — 4 seasonal flower GLBs exported")

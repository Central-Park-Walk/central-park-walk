"""Create low-poly wildflower meshes for Central Park grass.

Run in Blender: blender --background --python scripts/make_flower_mesh.py

Exports 4 flower GLBs to models/vegetation/:
  Flower_Clover.glb   — white clover (Trifolium repens): dome of tiny florets
  Flower_Dandelion.glb — dandelion (Taraxacum): flat yellow disc
  Flower_Violet.glb   — common blue violet (Viola sororia): 5 petals
  Flower_Buttercup.glb — buttercup (Ranunculus): 5 cupped petals

All flowers are small (2-4cm diameter) on a short green stem.
Geometry is minimal (10-20 triangles) for MultiMesh instancing.
UV.y = 0 at base, 1 at tip (matching blade convention).
Custom split normals for soft shading.
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


def make_stem(bm, height, color_base, color_tip):
    """Create a thin green stem from origin upward."""
    w = 0.002  # 2mm wide stem
    segs = 2
    verts = []
    for i in range(segs + 1):
        t = i / segs
        z = height * t
        hw = w * (1.0 - t * 0.5)  # slight taper
        uv_y = t * 0.5  # stem is bottom half of UV range
        col = [
            color_base[0] + (color_tip[0] - color_base[0]) * t,
            color_base[1] + (color_tip[1] - color_base[1]) * t,
            color_base[2] + (color_tip[2] - color_base[2]) * t,
            1.0
        ]
        v_l = bm.verts.new((-hw, 0, z))
        v_r = bm.verts.new((hw, 0, z))
        verts.append((v_l, v_r, uv_y, col))

    uv_layer = bm.loops.layers.uv.verify()
    col_layer = bm.loops.layers.color.verify()

    for i in range(segs):
        bl, br, uv_b, col_b = verts[i]
        tl, tr, uv_t, col_t = verts[i + 1]
        f1 = bm.faces.new([bl, br, tr, tl])
        for loop in f1.loops:
            v = loop.vert
            if v in (bl, br):
                loop[uv_layer].uv = (0.5, uv_b)
                loop[col_layer] = col_b
            else:
                loop[uv_layer].uv = (0.5, uv_t)
                loop[col_layer] = col_t

    return height  # return top Z for flower head placement


def make_petal_ring(bm, center_z, radius, n_petals, petal_len, petal_w,
                    color, cup_angle=0.0, uv_layer=None, col_layer=None):
    """Create a ring of petals at height center_z."""
    if uv_layer is None:
        uv_layer = bm.loops.layers.uv.verify()
    if col_layer is None:
        col_layer = bm.loops.layers.color.verify()

    for i in range(n_petals):
        angle = (i / n_petals) * math.tau
        # Petal center direction
        dx = math.cos(angle)
        dy = math.sin(angle)

        # Base of petal (at flower center)
        base = mathutils.Vector((dx * radius * 0.3, dy * radius * 0.3, center_z))
        # Tip of petal (extends outward and slightly up/down based on cup)
        tip_z = center_z + math.sin(cup_angle) * petal_len
        tip_xy = math.cos(cup_angle) * petal_len if cup_angle != 0 else petal_len
        tip = mathutils.Vector((dx * (radius * 0.3 + tip_xy), dy * (radius * 0.3 + tip_xy), tip_z))
        # Side vertices (perpendicular to petal direction)
        perp_x = -dy * petal_w * 0.5
        perp_y = dx * petal_w * 0.5
        mid_frac = 0.5
        mid = base.lerp(tip, mid_frac)
        left = mathutils.Vector((mid.x + perp_x, mid.y + perp_y, mid.z))
        right = mathutils.Vector((mid.x - perp_x, mid.y - perp_y, mid.z))

        v_base = bm.verts.new(base)
        v_left = bm.verts.new(left)
        v_tip = bm.verts.new(tip)
        v_right = bm.verts.new(right)

        # Two triangles: base-left-tip, base-tip-right
        f1 = bm.faces.new([v_base, v_left, v_tip])
        f2 = bm.faces.new([v_base, v_tip, v_right])

        col_rgba = [color[0], color[1], color[2], 1.0]
        for f in [f1, f2]:
            for loop in f.loops:
                loop[uv_layer].uv = (0.5, 0.85)  # flower head = top of UV
                loop[col_layer] = col_rgba


def finalize_mesh(bm, name):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)

    # Apply custom normals: all face normals pointing outward+up
    # Custom normals: blend polygon normal toward up for soft shading
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

    # Rotate for Blender Z-up → GLTF Y-up export
    obj.rotation_euler = (math.pi / 2, 0, 0)

    bm.free()
    return obj


def make_clover():
    """White clover: dome of tiny white florets, 2cm diameter, on 8cm stem."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    col_layer = bm.loops.layers.color.new("Col")

    stem_top = make_stem(bm, 0.08, (0.12, 0.30, 0.08), (0.18, 0.38, 0.10))

    # Clover head: dome of 8 tiny petals pointing upward/outward
    make_petal_ring(bm, stem_top, 0.01, 8, 0.010, 0.006,
                    (0.90, 0.92, 0.88), cup_angle=0.6,
                    uv_layer=uv_layer, col_layer=col_layer)
    # Second ring slightly higher for dome effect
    make_petal_ring(bm, stem_top + 0.005, 0.005, 5, 0.007, 0.005,
                    (0.95, 0.95, 0.92), cup_angle=0.8,
                    uv_layer=uv_layer, col_layer=col_layer)

    return finalize_mesh(bm, "Flower_Clover")


def make_dandelion():
    """Dandelion: flat yellow disc, 3cm diameter, on 10cm stem."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    col_layer = bm.loops.layers.color.new("Col")

    stem_top = make_stem(bm, 0.10, (0.15, 0.32, 0.06), (0.22, 0.40, 0.10))

    # Flat disc of narrow yellow petals
    make_petal_ring(bm, stem_top, 0.005, 12, 0.015, 0.004,
                    (0.92, 0.82, 0.12), cup_angle=0.1,
                    uv_layer=uv_layer, col_layer=col_layer)
    # Inner petals (shorter, slightly darker)
    make_petal_ring(bm, stem_top + 0.002, 0.003, 8, 0.008, 0.003,
                    (0.85, 0.72, 0.10), cup_angle=0.2,
                    uv_layer=uv_layer, col_layer=col_layer)

    return finalize_mesh(bm, "Flower_Dandelion")


def make_violet():
    """Common blue violet: 5 petals, 2cm diameter, on 6cm stem."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    col_layer = bm.loops.layers.color.new("Col")

    stem_top = make_stem(bm, 0.06, (0.10, 0.25, 0.06), (0.14, 0.32, 0.08))

    # 5 violet petals — the lower petal is slightly larger (real violet anatomy)
    make_petal_ring(bm, stem_top, 0.004, 5, 0.010, 0.008,
                    (0.42, 0.22, 0.62), cup_angle=0.15,
                    uv_layer=uv_layer, col_layer=col_layer)
    # White center spot
    make_petal_ring(bm, stem_top + 0.001, 0.002, 3, 0.003, 0.003,
                    (0.90, 0.90, 0.85), cup_angle=0.0,
                    uv_layer=uv_layer, col_layer=col_layer)

    return finalize_mesh(bm, "Flower_Violet")


def make_buttercup():
    """Buttercup: 5 glossy golden cup-shaped petals, 2cm, on 12cm stem."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    col_layer = bm.loops.layers.color.new("Col")

    stem_top = make_stem(bm, 0.12, (0.12, 0.28, 0.06), (0.16, 0.35, 0.08))

    # 5 cupped golden petals
    make_petal_ring(bm, stem_top, 0.005, 5, 0.010, 0.008,
                    (0.95, 0.85, 0.10), cup_angle=0.4,
                    uv_layer=uv_layer, col_layer=col_layer)
    # Green center (pistil/stamen area)
    make_petal_ring(bm, stem_top + 0.003, 0.002, 4, 0.003, 0.002,
                    (0.45, 0.55, 0.15), cup_angle=0.6,
                    uv_layer=uv_layer, col_layer=col_layer)

    return finalize_mesh(bm, "Flower_Buttercup")


if __name__ == "__main__":
    print("Creating wildflower meshes...")
    clear_scene()

    clover = make_clover()
    export_glb(clover, "Flower_Clover")

    clear_scene()
    dandelion = make_dandelion()
    export_glb(dandelion, "Flower_Dandelion")

    clear_scene()
    violet = make_violet()
    export_glb(violet, "Flower_Violet")

    clear_scene()
    buttercup = make_buttercup()
    export_glb(buttercup, "Flower_Buttercup")

    print("Done — 4 flower GLBs exported to models/vegetation/")

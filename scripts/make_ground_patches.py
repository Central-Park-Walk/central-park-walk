"""
Generate ground cover patch meshes for dense vegetation layer.

Each patch is a 2x2m pre-assembled cluster of crossed-plane stems/leaves
baked into a single mesh. Scattered via MultiMesh for dense ground cover
with minimal draw calls.

Patch types:
  1. Bramble — thorny tangles, horizontal spread, dark green
  2. FernCluster — overlapping frond rosettes
  3. MixedWeeds — varied stems, broad leaves, ragwort/dock-like
  4. TallGrass — waist-high tussock grasses, upright
  5. FallenLeaves — autumn/winter leaf litter carpet
  6. TwigLitter — bare winter twigs + dead leaf fragments

Run in Blender:  blender --background --python scripts/make_ground_patches.py

Each type gets 4 variants for visual variety when scattered.
"""

import bpy
import bmesh
import math
import random
import os
import sys
from mathutils import Vector, Euler

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "models", "vegetation")

PATCH_SIZE = 2.0   # metres
N_VARIANTS = 4


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for img in list(bpy.data.images):
        bpy.data.images.remove(img)


def make_crossed_planes(name, center, width, height, n_planes=2, rng=None,
                        mat=None, tilt_range=0.15):
    """Create intersecting vertical planes at position with random tilt."""
    if rng is None:
        rng = random.Random()
    parts = []
    for i in range(n_planes):
        bm = bmesh.new()
        hw, hh = width / 2.0, height / 2.0
        v0 = bm.verts.new(Vector((-hw, 0, 0)))
        v1 = bm.verts.new(Vector(( hw, 0, 0)))
        v2 = bm.verts.new(Vector(( hw, hh, 0)))
        v3 = bm.verts.new(Vector((-hw, hh, 0)))
        face = bm.faces.new([v0, v1, v2, v3])
        uv_layer = bm.loops.layers.uv.new()
        uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
        for loop, uv in zip(face.loops, uvs):
            loop[uv_layer].uv = uv
        mesh_data = bpy.data.meshes.new(f"{name}_p{i}")
        bm.to_mesh(mesh_data)
        bm.free()
        obj = bpy.data.objects.new(f"{name}_p{i}", mesh_data)
        bpy.context.collection.objects.link(obj)
        # Rotate around Y to create crossed pattern
        base_angle = i * math.pi / n_planes + rng.uniform(-0.2, 0.2)
        tilt_x = rng.uniform(-tilt_range, tilt_range)
        tilt_z = rng.uniform(-tilt_range, tilt_range)
        obj.rotation_euler = Euler((tilt_x, base_angle, tilt_z))
        obj.location = tuple(center)
        if mat:
            obj.data.materials.append(mat)
        parts.append(obj)
    return parts


def generate_patch_texture(name, tex_size, patch_type, rng):
    """Generate a texture for a ground cover patch type.
    Returns a bpy.types.Image.
    """
    TEX = tex_size
    img = bpy.data.images.new(name, width=TEX, height=TEX, alpha=True)
    pixels = [0.0] * (TEX * TEX * 4)

    if patch_type == "bramble":
        _paint_bramble(pixels, TEX, rng)
    elif patch_type == "fern_cluster":
        _paint_fern(pixels, TEX, rng)
    elif patch_type == "mixed_weeds":
        _paint_weeds(pixels, TEX, rng)
    elif patch_type == "tall_grass":
        _paint_tall_grass(pixels, TEX, rng)
    elif patch_type == "fallen_leaves":
        _paint_fallen_leaves(pixels, TEX, rng)
    elif patch_type == "twig_litter":
        _paint_twig_litter(pixels, TEX, rng)

    img.pixels[:] = pixels
    img.pack()
    return img


def _set_pixel(pixels, tex, x, y, r, g, b, a=1.0):
    """Set pixel with bounds check."""
    if 0 <= x < tex and 0 <= y < tex:
        idx = (y * tex + x) * 4
        if pixels[idx + 3] < 0.5:  # don't overwrite existing
            pixels[idx] = r
            pixels[idx + 1] = g
            pixels[idx + 2] = b
            pixels[idx + 3] = a


def _paint_leaf(pixels, tex, cx, cy, size, angle, r, g, b, rng, shape="elliptic"):
    """Paint a single leaf shape."""
    aspect = 0.45 if shape == "elliptic" else 0.65 if shape == "broad" else 0.30
    leaf_h = int(size)
    leaf_w = int(size * aspect)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    radius = max(leaf_w, leaf_h)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            lx = dx * cos_a + dy * sin_a
            ly = -dx * sin_a + dy * cos_a
            nx = lx / max(leaf_w, 1)
            ny = ly / max(leaf_h, 1)
            dist = math.sqrt(nx * nx + ny * ny)
            if dist <= 1.0:
                edge_dark = 1.0 - 0.25 * dist
                vein = 1.0 - 0.06 * math.exp(-abs(nx) * 6.0)
                px = int(cx + dx) % tex
                py = int(cy + dy) % tex
                _set_pixel(pixels, tex, px, py,
                           r * edge_dark * vein, g * edge_dark * vein,
                           b * edge_dark * vein)


def _paint_bramble(pixels, tex, rng):
    """Dense thorny leaves — small, dark green, many overlapping."""
    n_leaves = rng.randint(20, 30)
    for _ in range(n_leaves):
        cx = rng.randint(tex // 6, tex * 5 // 6)
        cy = rng.randint(tex // 6, tex * 5 // 6)
        size = tex * rng.uniform(0.06, 0.12)
        angle = rng.uniform(0, math.pi * 2)
        r = rng.uniform(0.30, 0.45)
        g = rng.uniform(0.50, 0.70)
        b = rng.uniform(0.20, 0.35)
        _paint_leaf(pixels, tex, cx, cy, size, angle, r, g, b, rng, "broad")
    # Add some thin stem lines
    for _ in range(rng.randint(3, 6)):
        sx = rng.randint(tex // 4, tex * 3 // 4)
        sy = rng.randint(0, tex // 4)
        angle = rng.uniform(-0.4, 0.4)
        length = rng.randint(tex // 3, tex * 2 // 3)
        for t in range(length):
            px = int(sx + math.sin(angle) * t + math.sin(t * 0.05) * 3)
            py = int(sy + math.cos(angle) * t)
            for w in range(-1, 2):
                _set_pixel(pixels, tex, px + w, py, 0.25, 0.20, 0.12)


def _paint_fern(pixels, tex, rng):
    """Fern fronds radiating from center — feathery compound leaves."""
    n_fronds = rng.randint(5, 8)
    center_x = tex // 2 + rng.randint(-tex // 8, tex // 8)
    center_y = tex // 4 + rng.randint(-tex // 8, tex // 8)
    for f in range(n_fronds):
        angle = f * math.pi * 2 / n_fronds + rng.uniform(-0.3, 0.3)
        frond_len = rng.randint(tex // 4, tex * 3 // 8)
        # Draw central rachis
        for t in range(frond_len):
            px = int(center_x + math.sin(angle) * t)
            py = int(center_y + math.cos(angle) * t * 0.7 + t * 0.3)
            r_col = rng.uniform(0.20, 0.30)
            g_col = rng.uniform(0.45, 0.60)
            b_col = rng.uniform(0.15, 0.25)
            # Pinnae (leaflets) along the rachis
            if t > 5 and t % 4 < 3:
                pinna_len = int((frond_len - t) * 0.3)
                for p in range(pinna_len):
                    side = 1 if (t % 8 < 4) else -1
                    perp_angle = angle + side * math.pi / 2
                    ppx = int(px + math.sin(perp_angle) * p)
                    ppy = int(py + math.cos(perp_angle) * p * 0.7)
                    fade = 1.0 - p / max(pinna_len, 1) * 0.3
                    _set_pixel(pixels, tex, ppx, ppy,
                               r_col * fade, g_col * fade, b_col * fade)
            _set_pixel(pixels, tex, px, py, 0.18, 0.28, 0.12)


def _paint_weeds(pixels, tex, rng):
    """Mixed broad-leaf weeds — dock, plantain, dandelion-like rosettes."""
    n_plants = rng.randint(8, 14)
    for _ in range(n_plants):
        cx = rng.randint(tex // 6, tex * 5 // 6)
        cy = rng.randint(tex // 6, tex * 5 // 6)
        n_leaves = rng.randint(4, 8)
        for l in range(n_leaves):
            angle = l * math.pi * 2 / n_leaves + rng.uniform(-0.3, 0.3)
            size = tex * rng.uniform(0.05, 0.10)
            dist = rng.uniform(0.3, 0.8) * size
            lx = cx + math.cos(angle) * dist
            ly = cy + math.sin(angle) * dist
            r = rng.uniform(0.35, 0.55)
            g = rng.uniform(0.55, 0.80)
            b = rng.uniform(0.20, 0.40)
            shape = rng.choice(["elliptic", "broad"])
            _paint_leaf(pixels, tex, lx, ly, size, angle, r, g, b, rng, shape)


def _paint_tall_grass(pixels, tex, rng):
    """Tall tussock grasses — vertical blades radiating from base."""
    n_blades = rng.randint(15, 25)
    base_x = tex // 2 + rng.randint(-tex // 6, tex // 6)
    base_y = tex // 8
    for _ in range(n_blades):
        bx = base_x + rng.randint(-tex // 6, tex // 6)
        angle = rng.uniform(-0.4, 0.4)
        length = rng.randint(tex // 3, tex * 3 // 4)
        width = rng.randint(2, max(3, tex // 80))
        r = rng.uniform(0.35, 0.55)
        g = rng.uniform(0.55, 0.78)
        b = rng.uniform(0.18, 0.32)
        for t in range(length):
            curve = math.sin(t * 0.02 + rng.uniform(0, 3)) * t * 0.003
            px = int(bx + math.sin(angle + curve) * t * 0.3)
            py = int(base_y + t)
            fade = 1.0 - (t / length) * 0.25
            for w in range(-width, width + 1):
                _set_pixel(pixels, tex, px + w, py,
                           r * fade, g * fade, b * fade)


def _paint_fallen_leaves(pixels, tex, rng):
    """Scattered fallen leaves — brown/orange/yellow, various sizes and rotations."""
    n_leaves = rng.randint(20, 35)
    for _ in range(n_leaves):
        cx = rng.randint(tex // 8, tex * 7 // 8)
        cy = rng.randint(tex // 8, tex * 7 // 8)
        size = tex * rng.uniform(0.04, 0.10)
        angle = rng.uniform(0, math.pi * 2)
        # Autumn palette: browns, oranges, yellows, some red
        palette = rng.choice([
            (0.60, 0.40, 0.15),  # brown
            (0.70, 0.45, 0.10),  # orange-brown
            (0.75, 0.60, 0.15),  # yellow-brown
            (0.55, 0.20, 0.10),  # dark red-brown
            (0.65, 0.55, 0.20),  # pale yellow
            (0.45, 0.30, 0.12),  # dark brown
        ])
        r, g, b = palette
        r += rng.uniform(-0.05, 0.05)
        g += rng.uniform(-0.05, 0.05)
        b += rng.uniform(-0.03, 0.03)
        shape = rng.choice(["elliptic", "broad"])
        _paint_leaf(pixels, tex, cx, cy, size, angle, r, g, b, rng, shape)


def _paint_twig_litter(pixels, tex, rng):
    """Winter ground litter — dead twigs + shriveled leaf fragments."""
    # Twigs
    for _ in range(rng.randint(6, 12)):
        sx = rng.randint(tex // 6, tex * 5 // 6)
        sy = rng.randint(tex // 6, tex * 5 // 6)
        angle = rng.uniform(0, math.pi * 2)
        length = rng.randint(tex // 8, tex // 3)
        for t in range(length):
            px = int(sx + math.cos(angle) * t)
            py = int(sy + math.sin(angle) * t)
            r = rng.uniform(0.25, 0.38)
            g = rng.uniform(0.18, 0.28)
            b = rng.uniform(0.10, 0.18)
            for w in range(-1, 2):
                _set_pixel(pixels, tex, px + w, py, r, g, b)
    # Dead leaf fragments
    for _ in range(rng.randint(8, 15)):
        cx = rng.randint(tex // 6, tex * 5 // 6)
        cy = rng.randint(tex // 6, tex * 5 // 6)
        size = tex * rng.uniform(0.03, 0.06)
        angle = rng.uniform(0, math.pi * 2)
        r = rng.uniform(0.30, 0.45)
        g = rng.uniform(0.22, 0.32)
        b = rng.uniform(0.10, 0.18)
        _paint_leaf(pixels, tex, cx, cy, size, angle, r, g, b, rng, "elliptic")


def create_patch_material(name, patch_type, rng, tex_size=512):
    """Create a material with generated patch texture."""
    img = generate_patch_texture(f"{name}_tex", tex_size, patch_type, rng)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.blend_method = 'CLIP'
    mat.alpha_threshold = 0.5
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.80
    tex_node = tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = img
    tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
    return mat


def build_patch(patch_type, variant_idx, rng):
    """Build a single ground cover patch mesh.

    Returns a list of blender objects composing the patch.
    """
    half = PATCH_SIZE / 2.0
    parts = []
    mat = create_patch_material(
        f"{patch_type}_v{variant_idx}", patch_type, rng, tex_size=512)

    if patch_type in ("bramble", "mixed_weeds"):
        # Dense horizontal spread — many small crossed-plane clusters
        n_clusters = rng.randint(12, 20)
        for c in range(n_clusters):
            cx = rng.uniform(-half, half)
            cz = rng.uniform(-half, half)
            h = rng.uniform(0.15, 0.40) if patch_type == "bramble" else rng.uniform(0.10, 0.30)
            w = rng.uniform(0.20, 0.40)
            center = Vector((cx, 0, cz))
            new_parts = make_crossed_planes(
                f"{patch_type}_v{variant_idx}_c{c}", center, w, h,
                n_planes=2, rng=rng, mat=mat, tilt_range=0.25)
            parts.extend(new_parts)

    elif patch_type == "fern_cluster":
        # Radial rosette — fronds splaying outward
        n_fronds = rng.randint(6, 10)
        for f in range(n_fronds):
            angle = f * math.pi * 2 / n_fronds + rng.uniform(-0.2, 0.2)
            dist = rng.uniform(0.15, 0.50)
            cx = math.cos(angle) * dist
            cz = math.sin(angle) * dist
            h = rng.uniform(0.25, 0.50)
            w = rng.uniform(0.20, 0.35)
            center = Vector((cx, 0, cz))
            new_parts = make_crossed_planes(
                f"fern_v{variant_idx}_f{f}", center, w, h,
                n_planes=2, rng=rng, mat=mat, tilt_range=0.35)
            parts.extend(new_parts)

    elif patch_type == "tall_grass":
        # Upright tussock — tall narrow planes
        n_blades = rng.randint(8, 14)
        for b in range(n_blades):
            cx = rng.uniform(-half * 0.5, half * 0.5)
            cz = rng.uniform(-half * 0.5, half * 0.5)
            h = rng.uniform(0.40, 0.80)
            w = rng.uniform(0.12, 0.25)
            center = Vector((cx, 0, cz))
            new_parts = make_crossed_planes(
                f"tgrass_v{variant_idx}_b{b}", center, w, h,
                n_planes=2, rng=rng, mat=mat, tilt_range=0.10)
            parts.extend(new_parts)

    elif patch_type in ("fallen_leaves", "twig_litter"):
        # Flat ground-hugging cards — nearly horizontal
        n_cards = rng.randint(10, 18)
        for c in range(n_cards):
            cx = rng.uniform(-half, half)
            cz = rng.uniform(-half, half)
            w = rng.uniform(0.30, 0.55)
            h = rng.uniform(0.25, 0.45)
            center = Vector((cx, 0.01, cz))  # just above ground
            # Nearly horizontal planes with slight tilt
            bm = bmesh.new()
            hw, hh = w / 2.0, h / 2.0
            # Horizontal quad (XZ plane, slightly above Y=0)
            v0 = bm.verts.new(Vector((-hw, 0, -hh)))
            v1 = bm.verts.new(Vector(( hw, 0, -hh)))
            v2 = bm.verts.new(Vector(( hw, 0,  hh)))
            v3 = bm.verts.new(Vector((-hw, 0,  hh)))
            face = bm.faces.new([v0, v1, v2, v3])
            uv_layer = bm.loops.layers.uv.new()
            uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
            for loop, uv in zip(face.loops, uvs):
                loop[uv_layer].uv = uv
            mesh_data = bpy.data.meshes.new(f"{patch_type}_v{variant_idx}_c{c}")
            bm.to_mesh(mesh_data)
            bm.free()
            obj = bpy.data.objects.new(f"{patch_type}_v{variant_idx}_c{c}", mesh_data)
            bpy.context.collection.objects.link(obj)
            yaw = rng.uniform(0, math.pi * 2)
            tilt = rng.uniform(-0.08, 0.08)
            obj.rotation_euler = Euler((tilt, yaw, tilt))
            obj.location = tuple(center)
            obj.data.materials.append(mat)
            parts.append(obj)

    return parts


def export_patch(patch_type, variant_idx, parts):
    """Join all parts and export as GLB."""
    if not parts:
        return

    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()

    obj = bpy.context.active_object
    obj.name = f"Patch_{patch_type}_v{variant_idx}"

    # Apply transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Set origin to base center
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

    # Export
    out_path = os.path.join(OUT_DIR, f"Patch_{patch_type}_v{variant_idx}.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
    )
    print(f"Exported: {out_path}")


def main():
    patch_types = [
        "bramble",
        "fern_cluster",
        "mixed_weeds",
        "tall_grass",
        "fallen_leaves",
        "twig_litter",
    ]

    for pt in patch_types:
        for vi in range(N_VARIANTS):
            clear_scene()
            rng = random.Random(hash((pt, vi)))
            parts = build_patch(pt, vi, rng)
            export_patch(pt, vi, parts)

    print(f"\nGenerated {len(patch_types) * N_VARIANTS} ground cover patches.")


if __name__ == "__main__":
    main()

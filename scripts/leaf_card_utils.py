"""
Shared leaf card utilities for tree model generation.

AAA leaf rendering: instead of icosphere clusters (80 faces, looks like
puffy balls), use CROSSED QUADS — 2-3 intersecting planes that each show
a cluster of ~12 overlapping leaves via alpha-tested texture. This gives
volume from every viewing angle with just 4-6 faces per cluster.

Usage in make_*.py scripts:
    from leaf_card_utils import create_leaf_material, make_leaf_cards

    leaf_mat = create_leaf_material("OakLeaf", leaf_shape="lobed",
                                     n_leaves=12, tex_size=512)
    leaf_parts += make_leaf_cards("lc", vi, center, radius, n_cards=3,
                                   rng=rng, mat=leaf_mat)
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector, Euler


# ---------------------------------------------------------------------------
# Leaf texture generation — species-specific leaf clusters
# ---------------------------------------------------------------------------

LEAF_SHAPES = {
    # name: (aspect_ratio, edge_fn_name)
    # aspect_ratio: width/height of individual leaf
    # edge_fn: function name for edge shape
    "elliptic":   (0.40, "smooth"),       # elm, linden, birch, cherry
    "lobed":      (0.75, "oak_lobes"),     # oak
    "palmate":    (0.85, "maple_lobes"),   # maple
    "fan":        (0.90, "ginkgo_fan"),    # ginkgo
    "compound":   (0.20, "narrow"),        # honeylocust leaflets
    "ovate":      (0.50, "smooth"),        # magnolia, callery pear
    "lanceolate": (0.25, "narrow"),        # willow
    "needle":     (0.08, "narrow"),        # pine needles
}


def _leaf_edge_smooth(angle, phase):
    """Smooth elliptic edge — elm, linden, birch."""
    return 1.0 + 0.08 * math.sin(angle * 6 + phase)


def _leaf_edge_oak_lobes(angle, phase):
    """Deep-lobed oak leaf."""
    lobe = math.sin(angle * 3.5 + phase)
    return 0.65 + 0.35 * max(lobe, 0.0) ** 0.6


def _leaf_edge_maple_lobes(angle, phase):
    """5-pointed maple leaf."""
    lobe = math.sin(angle * 2.5 + phase)
    return 0.55 + 0.45 * max(lobe, 0.0) ** 0.5


def _leaf_edge_ginkgo_fan(angle, phase):
    """Fan-shaped ginkgo with notch."""
    fan = max(0.0, math.cos(angle * 0.5 + phase))
    notch = 1.0 - 0.2 * max(0.0, math.cos(angle * 4 + phase)) ** 4
    return fan * notch * 0.9 + 0.1


def _leaf_edge_narrow(angle, phase):
    """Narrow lanceolate / compound leaflet."""
    return 0.85 + 0.15 * math.sin(angle * 2 + phase)


EDGE_FNS = {
    "smooth":      _leaf_edge_smooth,
    "oak_lobes":   _leaf_edge_oak_lobes,
    "maple_lobes": _leaf_edge_maple_lobes,
    "ginkgo_fan":  _leaf_edge_ginkgo_fan,
    "narrow":      _leaf_edge_narrow,
}


def _pixel_hash(x, y):
    """Fast deterministic per-pixel hash → float in [-1, 1]."""
    n = x * 374761393 + y * 668265263
    n = (n ^ (n >> 13)) * 1274126177
    return ((n & 0xFFFFFF) / 8388608.0) - 1.0


def generate_leaf_texture(name, tex_size=512, n_leaves=12, leaf_shape="elliptic",
                          seed=42):
    """Generate a leaf cluster texture with proper alpha for alpha-to-coverage.

    Returns a bpy.types.Image with scattered overlapping leaves.
    The texture is designed for crossed-quad leaf cards.
    """
    rng = random.Random(seed)
    aspect, edge_name = LEAF_SHAPES.get(leaf_shape, LEAF_SHAPES["elliptic"])
    edge_fn = EDGE_FNS[edge_name]
    TEX = tex_size

    img = bpy.data.images.new(name, width=TEX, height=TEX, alpha=True)
    pixels = [0.0] * (TEX * TEX * 4)

    for leaf_i in range(n_leaves):
        # Leaf center (clustered toward texture center)
        cx = TEX // 2 + rng.randint(-TEX // 4, TEX // 4)
        cy = TEX // 2 + rng.randint(-TEX // 4, TEX // 4)

        # Leaf size (variable)
        base_size = TEX * rng.uniform(0.10, 0.22)
        leaf_w = int(base_size * aspect)
        leaf_h = int(base_size)

        # Random rotation
        rot = rng.uniform(0, math.pi * 2)
        cos_r, sin_r = math.cos(rot), math.sin(rot)

        # Color variation — light values, shader provides final tint
        r = rng.uniform(0.65, 0.85)
        g = rng.uniform(0.80, 0.98)
        b = rng.uniform(0.55, 0.75)

        # Per-leaf unique traits
        tip_yellow = rng.uniform(0.0, 0.06)
        base_dark = rng.uniform(0.0, 0.04)
        side_warm = rng.uniform(-0.015, 0.015)

        # Subtle vein darkening along midrib
        phase = rng.uniform(0, math.pi * 2)

        # Draw leaf
        radius = max(leaf_w, leaf_h)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                # Rotate to leaf-local coordinates
                lx = dx * cos_r + dy * sin_r
                ly = -dx * sin_r + dy * cos_r

                # Normalized leaf coordinates
                nx = lx / max(leaf_w, 1)
                ny = ly / max(leaf_h, 1)

                # Radial distance for edge function
                dist = math.sqrt(nx * nx + ny * ny)
                angle = math.atan2(ny, nx)

                edge_r = edge_fn(angle, phase)

                if dist <= edge_r:
                    px = (cx + dx) % TEX
                    py = (cy + dy) % TEX
                    idx = (py * TEX + px) * 4

                    # Darken toward edges (natural AO)
                    edge_dark = 1.0 - 0.2 * (dist / max(edge_r, 0.01))
                    # Midrib vein (slight darkening along center line)
                    vein = 1.0 - 0.08 * math.exp(-abs(nx) * 8.0)

                    # Tip-to-base gradient
                    tip_t = (ny + 1.0) * 0.5
                    lr = r * edge_dark * vein + tip_yellow * tip_t - base_dark * (1.0 - tip_t)
                    lg = g * edge_dark * vein + tip_yellow * tip_t * 0.4 - base_dark * (1.0 - tip_t) * 0.4
                    lb = b * edge_dark * vein - tip_yellow * tip_t * 0.2
                    lr += side_warm * nx

                    # Per-pixel micro-noise: chlorophyll patches, dust, cell texture
                    n1 = _pixel_hash(px, py) * 0.05
                    n2 = _pixel_hash(px + 7919, py) * 0.025
                    n3 = _pixel_hash(px, py + 6271) * 0.025
                    lr = max(0.0, min(1.0, lr + n1 + n2))
                    lg = max(0.0, min(1.0, lg + n1))
                    lb = max(0.0, min(1.0, lb + n1 + n3))

                    # Alpha blend (later leaves overlap earlier)
                    old_a = pixels[idx + 3]
                    if old_a < 0.9:
                        pixels[idx + 0] = lr
                        pixels[idx + 1] = lg
                        pixels[idx + 2] = lb
                        pixels[idx + 3] = 1.0

    img.pixels[:] = pixels
    img.pack()
    return img


# ---------------------------------------------------------------------------
# Leaf card material
# ---------------------------------------------------------------------------

def create_leaf_material(name, leaf_shape="elliptic", n_leaves=12,
                         tex_size=512, seed=42):
    """Create a leaf material with a multi-leaf cluster texture."""
    leaf_img = generate_leaf_texture(
        f"{name}Tex", tex_size=tex_size, n_leaves=n_leaves,
        leaf_shape=leaf_shape, seed=seed)

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.blend_method = 'CLIP'
    mat.alpha_threshold = 0.5
    tree = mat.node_tree
    bsdf = tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.75

    tex_node = tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = leaf_img
    tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])

    return mat


# ---------------------------------------------------------------------------
# Crossed-quad leaf card geometry
# ---------------------------------------------------------------------------

def _make_single_quad(name, center, width, height, rotation, mat):
    """Create a single textured quad at the given position and rotation."""
    bm = bmesh.new()
    hw, hh = width / 2.0, height / 2.0

    v0 = bm.verts.new(Vector((-hw, -hh, 0)))
    v1 = bm.verts.new(Vector(( hw, -hh, 0)))
    v2 = bm.verts.new(Vector(( hw,  hh, 0)))
    v3 = bm.verts.new(Vector((-hw,  hh, 0)))

    face = bm.faces.new([v0, v1, v2, v3])

    # UV mapping (full texture)
    uv_layer = bm.loops.layers.uv.new()
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for loop, uv in zip(face.loops, uvs):
        loop[uv_layer].uv = uv

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    obj.location = tuple(center)
    obj.rotation_euler = rotation
    obj.data.materials.append(mat)
    return obj


def make_leaf_cards(prefix, variant_idx, center, size, n_cards=3,
                    rng=None, mat=None, flatten=0.7):
    """Create a crossed-quad leaf cluster at the given position.

    Args:
        prefix: name prefix for objects
        variant_idx: tree variant index
        center: Vector position
        size: approximate radius of the cluster
        n_cards: number of intersecting quads (2-3, default 3)
        rng: random.Random instance
        mat: leaf material
        flatten: vertical squish (0.5 = pancake, 1.0 = sphere)

    Returns:
        list of bpy objects (the quads)
    """
    if rng is None:
        rng = random.Random()
    if mat is None:
        return []

    parts = []
    card_w = size * 2.0 * rng.uniform(0.85, 1.15)
    card_h = card_w * flatten * rng.uniform(0.8, 1.2)

    for c in range(n_cards):
        # Evenly space rotations around Y axis, with some random offset
        base_angle = c * math.pi / n_cards + rng.uniform(-0.2, 0.2)
        # Slight tilt for organic look
        tilt_x = rng.uniform(-0.15, 0.15)
        tilt_z = rng.uniform(-0.15, 0.15)

        rotation = Euler((tilt_x, base_angle, tilt_z), 'XYZ')

        obj = _make_single_quad(
            f"{prefix}_{variant_idx}_{c}",
            center, card_w, card_h, rotation, mat)
        parts.append(obj)

    return parts

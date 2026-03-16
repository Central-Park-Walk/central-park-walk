"""Build ground cover (turf carpet) tiles for Central Park Walk.

Dense grass tiles with 3000+ blades, 5 variants per type for variety.
Heights follow CPC data — mow height is minimum, blades grow to species
maximum. Wider blades (10-18mm) for visual coverage from oblique angles.

5 variants per type: same parameters, different random seeds. Adjacent
tiles get randomly different variants but all have identical statistics
(density, height distribution, color), so boundaries are invisible.

Types match Central Park zone categories:
  0. Turf_Lawn   — mowed KBG/ryegrass, 6.5-10cm
  1. Turf_Wild   — unmowed meadow, 8-40cm
  2. Turf_Shade  — woodland floor fescue, 5-18cm
  3. Turf_Sedge  — waterside rushes/sedges, 8-25cm

Exports to models/vegetation/Turf_*_v{0-4}.glb (20 files total)
"""

import bpy
import bmesh
import math
import random
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)

VARIANTS = 5


def make_blade(bm, color_layer, uv_layer,
               bx, bz, height, width, rot, lean,
               base_rgb, tip_rgb):
    """Create one grass blade as a single quad."""
    dx = math.cos(rot)
    dz = math.sin(rot)
    px = -math.sin(rot)
    pz = math.cos(rot)

    hw = width * 0.5
    tip_x = bx + dx * lean
    tip_z = bz + dz * lean
    thw = hw * 0.3

    # Blender is Z-up. Height along Z, horizontal plane is XY.
    v0 = bm.verts.new((bx + px * hw, bz + pz * hw, 0.0))
    v1 = bm.verts.new((bx - px * hw, bz - pz * hw, 0.0))
    v2 = bm.verts.new((tip_x - px * thw, tip_z - pz * thw, height))
    v3 = bm.verts.new((tip_x + px * thw, tip_z + pz * thw, height))

    try:
        face = bm.faces.new([v0, v1, v2, v3])
    except ValueError:
        return

    base_col = (base_rgb[0], base_rgb[1], base_rgb[2], 1.0)
    tip_col = (tip_rgb[0], tip_rgb[1], tip_rgb[2], 1.0)
    for loop in face.loops:
        if loop.vert in (v0, v1):
            loop[color_layer] = base_col
            loop[uv_layer].uv = (0.5, 0.0)
        else:
            loop[color_layer] = tip_col
            loop[uv_layer].uv = (0.5, 1.0)


def sample_height(rng, h_min, h_max, distribution="lawn"):
    """Sample a blade height with realistic non-uniform distribution."""
    t = rng.random()
    if distribution == "lawn":
        t = t ** 2.0
    elif distribution == "wild":
        t = (rng.random() + rng.random()) * 0.5
    elif distribution == "shade":
        t = t ** 2.5
    elif distribution == "sedge":
        t = 1.0 - (1.0 - t) ** 1.8
    return h_min + t * (h_max - h_min)


def build_turf_tile(cfg, seed):
    """Build a dense ground cover tile with blades at varied heights."""
    rng = random.Random(seed)
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    radius = cfg["radius"]
    blade_count = cfg["blade_count"]
    h_min, h_max = cfg["height_range"]
    w_lo, w_hi = cfg["width_range"]
    lean_lo, lean_hi = cfg["lean_range"]
    base_rgb = cfg["base_rgb"]
    tip_rgb = cfg["tip_rgb"]
    color_var = cfg.get("color_var", 0.04)
    distribution = cfg.get("distribution", "lawn")

    # Edge bleed distance — blades near edges get copies on opposite side
    # so the tile wraps seamlessly (like a tileable texture).
    bleed = 0.04  # 4cm — slightly larger than average blade spacing
    tile_w = radius * 2.0  # full tile width

    for _ in range(blade_count):
        bx = rng.uniform(-radius, radius)
        bz = rng.uniform(-radius, radius)
        rot = rng.random() * 2 * math.pi

        h = sample_height(rng, h_min, h_max, distribution)
        w = rng.uniform(w_lo, w_hi)
        h_frac = (h - h_min) / max(h_max - h_min, 0.01)
        lean = rng.uniform(lean_lo, lean_hi) * (0.5 + h_frac * 0.5)

        cv = rng.uniform(-color_var, color_var)
        dark_factor = 0.85 + 0.15 * h_frac
        b_rgb = (
            max(0.01, (base_rgb[0] + cv * 0.8) * dark_factor),
            max(0.01, (base_rgb[1] + cv * 0.6) * dark_factor),
            max(0.01, (base_rgb[2] + cv * 0.4) * dark_factor),
        )
        t_rgb = (
            min(0.95, tip_rgb[0] + cv * 0.6),
            min(0.95, tip_rgb[1] + cv * 0.5),
            min(0.95, tip_rgb[2] + cv * 0.3),
        )

        # Crossed quads: 2 quads at 90° per blade position.
        # Guarantees a visible face from every viewing angle.
        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, lean, b_rgb, t_rgb)
        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot + math.pi * 0.5, lean, b_rgb, t_rgb)

    return bm


TURF_TYPES = [
    # 0: Lawn — mowed 2x/week at 3 inches (7.6cm)
    {
        "name": "Turf_Lawn",
        "blade_count": 3000,
        "radius": 0.61,
        "height_range": (0.065, 0.10),
        "width_range": (0.010, 0.018),      # wider for oblique coverage
        "lean_range": (0.01, 0.03),
        "base_rgb": (0.15, 0.35, 0.06),
        "tip_rgb": (0.35, 0.55, 0.18),
        "color_var": 0.03,
        "distribution": "lawn",
        "seed": 501,
    },
    # 1: Wild — nature reserve, never mowed
    {
        "name": "Turf_Wild",
        "blade_count": 2200,
        "radius": 0.61,
        "height_range": (0.08, 0.40),
        "width_range": (0.010, 0.020),
        "lean_range": (0.03, 0.12),
        "base_rgb": (0.12, 0.28, 0.04),
        "tip_rgb": (0.40, 0.42, 0.16),
        "color_var": 0.06,
        "distribution": "wild",
        "seed": 503,
    },
    # 2: Shade — woodland floor fescue
    {
        "name": "Turf_Shade",
        "blade_count": 1800,
        "radius": 0.61,
        "height_range": (0.05, 0.18),
        "width_range": (0.008, 0.016),
        "lean_range": (0.02, 0.06),
        "base_rgb": (0.06, 0.18, 0.03),
        "tip_rgb": (0.16, 0.30, 0.10),
        "color_var": 0.04,
        "distribution": "shade",
        "seed": 507,
    },
    # 3: Sedge — waterside Carex and Juncus
    {
        "name": "Turf_Sedge",
        "blade_count": 2000,
        "radius": 0.61,
        "height_range": (0.08, 0.25),
        "width_range": (0.008, 0.016),
        "lean_range": (0.02, 0.05),
        "base_rgb": (0.10, 0.26, 0.05),
        "tip_rgb": (0.24, 0.40, 0.14),
        "color_var": 0.04,
        "distribution": "sedge",
        "seed": 509,
    },
]


def make_turf_material(name):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    for n in nodes:
        nodes.remove(n)
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular'].default_value = 0.06
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def export_tile(bm, name, material, cfg):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    filepath = os.path.join(OUT_DIR, name + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_colors=True,
        export_normals=True,
        export_apply=True,
    )

    vc = len(mesh.vertices)
    fc = len(mesh.polygons)
    print(f"  {name}: {vc} verts, {fc} faces")
    bpy.ops.object.delete(use_global=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

total_files = len(TURF_TYPES) * VARIANTS
print("=" * 60)
print(f"Building {len(TURF_TYPES)} types × {VARIANTS} variants = {total_files} tiles")
print("=" * 60)

mat = make_turf_material("TurfBlade")
count = 0

for cfg in TURF_TYPES:
    for v in range(VARIANTS):
        name = f"{cfg['name']}_v{v}"
        seed = cfg["seed"] + v * 1000
        count += 1
        print(f"\n[{count}/{total_files}] {name} ({cfg['blade_count']} blades)...")
        bm = build_turf_tile(cfg, seed)
        export_tile(bm, name, mat, cfg)

print(f"\nDone. {count} ground cover tiles exported.")

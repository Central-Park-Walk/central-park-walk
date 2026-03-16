"""Build ground cover turf tiles for Central Park Walk.

Curved multi-segment grass blades (like hexaquo's approach). Blade
curvature depends on height — short mowed grass is straight, tall
meadow grass arcs dramatically. Fewer blades than before (~600/tile)
but each blade has 2-5 segments for natural shape.

Types match Central Park zone categories:
  0. Turf_Lawn   — mowed KBG/ryegrass, 7.6cm, 2 segments (straight)
  1. Turf_Wild   — unmowed meadow, 8-40cm, 4 segments (dramatic arc)
  2. Turf_Shade  — woodland fescue, 5-18cm, 3 segments (gentle curve)
  3. Turf_Sedge  — waterside rushes, 8-25cm, 3 segments (lean, not curve)

Exports to models/vegetation/Turf_*_v{0-4}.glb (20 files)
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
               bx, bz, height, width, rot, arch, segments,
               base_rgb, tip_rgb):
    """Create a curved grass blade with N segments.

    Segments=1: single quad (flat). Segments=2+: curved strip.
    The curvature comes from 'arch' — horizontal extension in the
    facing direction, applied quadratically so the tip arcs over.
    Blender Z-up: XY is horizontal, Z is height.
    """
    dx = math.cos(rot)
    dz = math.sin(rot)
    px = -math.sin(rot)
    pz = math.cos(rot)

    # Build vertex pairs from base to tip
    vert_pairs = []
    for si in range(segments + 1):
        t = si / segments
        # Height with slight deceleration at top
        seg_z = height * (t - 0.12 * t * t)
        # Arch: quadratic — tip extends more than middle
        extend = arch * t * t
        # Width tapers toward tip
        seg_w = width * (1.0 - t * 0.65) * 0.5

        cx = bx + dx * extend
        cy = bz + dz * extend

        # Color interpolation
        r = base_rgb[0] + (tip_rgb[0] - base_rgb[0]) * t
        g = base_rgb[1] + (tip_rgb[1] - base_rgb[1]) * t
        b = base_rgb[2] + (tip_rgb[2] - base_rgb[2]) * t

        vl = bm.verts.new((cx + px * seg_w, cy + pz * seg_w, seg_z))
        vr = bm.verts.new((cx - px * seg_w, cy - pz * seg_w, seg_z))
        vert_pairs.append((vl, vr, (r, g, b, 1.0), t))

    for si in range(segments):
        vl0, vr0, c0, t0 = vert_pairs[si]
        vl1, vr1, c1, t1 = vert_pairs[si + 1]
        try:
            face = bm.faces.new([vl0, vr0, vr1, vl1])
        except ValueError:
            continue
        for loop in face.loops:
            if loop.vert == vl0:
                loop[color_layer] = c0
                loop[uv_layer].uv = (0.0, t0)
            elif loop.vert == vr0:
                loop[color_layer] = c0
                loop[uv_layer].uv = (1.0, t0)
            elif loop.vert == vr1:
                loop[color_layer] = c1
                loop[uv_layer].uv = (1.0, t1)
            elif loop.vert == vl1:
                loop[color_layer] = c1
                loop[uv_layer].uv = (0.0, t1)


def sample_height(rng, h_min, h_max, distribution="lawn"):
    """Sample blade height — mowed lawns are uniform, others vary."""
    if distribution == "lawn":
        return h_min  # CPC mows to uniform 3 inches
    t = rng.random()
    if distribution == "wild":
        t = (rng.random() + rng.random()) * 0.5
    elif distribution == "shade":
        t = t ** 2.5
    elif distribution == "sedge":
        t = 1.0 - (1.0 - t) ** 1.8
    return h_min + t * (h_max - h_min)


def build_turf_tile(cfg, seed):
    """Build a turf tile with curved multi-segment blades."""
    rng = random.Random(seed)
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    radius = cfg["radius"]
    blade_count = cfg["blade_count"]
    h_min, h_max = cfg["height_range"]
    w_lo, w_hi = cfg["width_range"]
    arch_lo, arch_hi = cfg["arch_range"]
    segments = cfg["segments"]
    base_rgb = cfg["base_rgb"]
    tip_rgb = cfg["tip_rgb"]
    color_var = cfg.get("color_var", 0.04)
    distribution = cfg.get("distribution", "lawn")

    for _ in range(blade_count):
        bx = rng.uniform(-radius, radius)
        bz = rng.uniform(-radius, radius)
        rot = rng.random() * 2 * math.pi

        h = sample_height(rng, h_min, h_max, distribution)
        w = rng.uniform(w_lo, w_hi)
        # Arch proportional to height — short blades don't curve
        h_frac = (h - h_min) / max(h_max - h_min, 0.01)
        arch = rng.uniform(arch_lo, arch_hi) * (0.3 + h_frac * 0.7)

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

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, arch, segments, b_rgb, t_rgb)

    return bm


TURF_TYPES = [
    # 0: Lawn — mowed 2x/week, 3 inches. Straight, stiff blades.
    {
        "name": "Turf_Lawn",
        "blade_count": 600,
        "radius": 0.61,
        "height_range": (0.076, 0.076),    # uniform mow height
        "width_range": (0.008, 0.016),
        "arch_range": (0.002, 0.008),       # nearly straight
        "segments": 2,
        "base_rgb": (0.15, 0.35, 0.06),
        "tip_rgb": (0.35, 0.55, 0.18),
        "color_var": 0.03,
        "distribution": "lawn",
        "seed": 501,
    },
    # 1: Wild — unmowed meadow, dramatic arcing blades
    {
        "name": "Turf_Wild",
        "blade_count": 500,
        "radius": 0.61,
        "height_range": (0.08, 0.40),
        "width_range": (0.010, 0.020),
        "arch_range": (0.04, 0.15),         # strong arc on tall blades
        "segments": 4,
        "base_rgb": (0.12, 0.28, 0.04),
        "tip_rgb": (0.40, 0.42, 0.16),
        "color_var": 0.06,
        "distribution": "wild",
        "seed": 503,
    },
    # 2: Shade — woodland fescue, gentle curve
    {
        "name": "Turf_Shade",
        "blade_count": 500,
        "radius": 0.61,
        "height_range": (0.05, 0.18),
        "width_range": (0.007, 0.014),
        "arch_range": (0.01, 0.05),         # gentle arc
        "segments": 3,
        "base_rgb": (0.06, 0.18, 0.03),
        "tip_rgb": (0.16, 0.30, 0.10),
        "color_var": 0.04,
        "distribution": "shade",
        "seed": 507,
    },
    # 3: Sedge — rigid triangular stems, lean not curve
    {
        "name": "Turf_Sedge",
        "blade_count": 550,
        "radius": 0.61,
        "height_range": (0.08, 0.25),
        "width_range": (0.006, 0.012),
        "arch_range": (0.02, 0.06),         # lean, not dramatic arc
        "segments": 3,
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
    print(f"  {name}: {vc} verts, {fc} faces ({cfg['segments']} seg/blade)")
    bpy.ops.object.delete(use_global=False)


# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

total_files = len(TURF_TYPES) * VARIANTS
print("=" * 60)
print(f"Building {len(TURF_TYPES)} types × {VARIANTS} variants = {total_files} tiles")
print(f"Curved multi-segment blades — fewer blades, better shape")
print("=" * 60)

mat = make_turf_material("TurfBlade")
count = 0

for cfg in TURF_TYPES:
    for v in range(VARIANTS):
        name = f"{cfg['name']}_v{v}"
        seed = cfg["seed"] + v * 1000
        count += 1
        print(f"\n[{count}/{total_files}] {name} ({cfg['blade_count']} blades, "
              f"{cfg['segments']} segments)...")
        bm = build_turf_tile(cfg, seed)
        export_tile(bm, name, mat, cfg)

print(f"\nDone. {count} tiles exported.")

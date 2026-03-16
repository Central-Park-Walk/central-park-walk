"""Build ground cover (turf carpet) tiles for Central Park Walk — 4 zone types.

Dense grass tiles with 1000-2000 blades each, all at different heights.
Mow height is the MINIMUM blade height for mowed lawns — blades range
from mow height up to max growth since last cut. Unmowed areas have
full height distribution from ground level to species maximum.

This is the AAA approach: each tile is a dense carpet of varied-height
blades that reads as continuous grass from the player's perspective.
The terrain shader carries the color at distance; these tiles provide
3D parallax depth within 12-15m.

Types match Central Park zone categories:
  0. Turf_Lawn   — mowed KBG/ryegrass, 7.5-10cm (CPC 3-inch mow + regrowth)
  1. Turf_Wild   — unmowed meadow, 8-40cm (full species range)
  2. Turf_Shade  — woodland floor fescue, 5-18cm (shade-tolerant)
  3. Turf_Sedge  — waterside rushes/sedges, 8-25cm (moisture-loving)

Exports to models/vegetation/Turf_*.glb
"""

import bpy
import bmesh
import math
import random
import os

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Grass blade — single quad, optionally leaning outward
# ---------------------------------------------------------------------------
def make_blade(bm, color_layer, uv_layer,
               bx, bz, height, width, rot, lean,
               base_rgb, tip_rgb):
    """Create one grass blade as a single quad at position (bx, bz)."""
    dx = math.cos(rot)
    dz = math.sin(rot)
    px = -math.sin(rot)
    pz = math.cos(rot)

    hw = width * 0.5
    tip_x = bx + dx * lean
    tip_z = bz + dz * lean
    thw = hw * 0.3  # tip tapers to 30% of base width

    # Blender is Z-up. Height goes along Z, horizontal plane is XY.
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


# ---------------------------------------------------------------------------
# Height distribution — not uniform. Biased toward typical for that zone.
# ---------------------------------------------------------------------------
def sample_height(rng, h_min, h_max, distribution="lawn"):
    """Sample a blade height with realistic distribution.

    lawn:  most blades near mow height (h_min), tapering off toward h_max
    wild:  full range, slight bias toward mid-height
    shade: most blades short, occasional tall
    sedge: biased toward tall
    """
    t = rng.random()
    if distribution == "lawn":
        # Most blades near mow height, few taller (exponential decay above mow)
        # 70% within first 30% of range, rest spread across upper 70%
        t = t ** 2.0  # squares bunch toward 0 = near h_min
    elif distribution == "wild":
        # Full range, slight bias toward mid-height (bell-ish)
        t = (rng.random() + rng.random()) * 0.5  # triangle distribution
    elif distribution == "shade":
        # Mostly short with occasional tall outlier
        t = t ** 2.5
    elif distribution == "sedge":
        # Biased toward taller — sedges grow upright
        t = 1.0 - (1.0 - t) ** 1.8
    return h_min + t * (h_max - h_min)


# ---------------------------------------------------------------------------
# Turf tile builder
# ---------------------------------------------------------------------------
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
    outward_pct = cfg.get("outward_pct", 0.7)
    distribution = cfg.get("distribution", "lawn")

    for _ in range(blade_count):
        # Distribute blades uniformly in square — matches the grid placement.
        # Square tiles on a square grid tile perfectly with no gaps.
        bx = rng.uniform(-radius, radius)
        bz = rng.uniform(-radius, radius)

        # Fully random blade direction — with 1000+ blades, density
        # provides coverage without needing outward-lean patterns.
        rot = rng.random() * 2 * math.pi

        h = sample_height(rng, h_min, h_max, distribution)
        w = rng.uniform(w_lo, w_hi)
        # Lean proportional to height — taller blades lean more
        h_frac = (h - h_min) / max(h_max - h_min, 0.01)
        lean = rng.uniform(lean_lo, lean_hi) * (0.5 + h_frac * 0.5)

        # Per-blade color variation
        cv = rng.uniform(-color_var, color_var)
        # Shorter blades slightly darker (closer to base/soil)
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
                   bx, bz, h, w, rot, lean, b_rgb, t_rgb)

    return bm


# ---------------------------------------------------------------------------
# 4 turf types — CPC data-driven
# ---------------------------------------------------------------------------
TURF_TYPES = [
    # 0: Lawn — mowed 2x/week at 3 inches (7.6cm). Blades range from mow
    #    height to ~10cm (3-5 days regrowth). Kentucky bluegrass / perennial
    #    ryegrass blend. Dense, uniform, narrow blades.
    {
        "name": "Turf_Lawn",
        "blade_count": 2500,                    # dense carpet — ~1680 blades/m²
        "radius": 0.61,                      # half grid spacing (stride 2 × 0.61m)
        "height_range": (0.065, 0.10),     # 6.5cm (fresh cut) to 10cm (regrowth)
        "width_range": (0.007, 0.014),      # 7-14mm — KBG/ryegrass blades
        "lean_range": (0.01, 0.03),         # minimal lean — upright mowed grass
        "base_rgb": (0.15, 0.35, 0.06),
        "tip_rgb": (0.35, 0.55, 0.18),
        "color_var": 0.03,
        "outward_pct": 0.40,               # less outward — mowed grass is upright
        "distribution": "lawn",
        "seed": 501,
    },
    # 1: Wild — nature reserve, never mowed. Big bluestem, switchgrass,
    #    goldenrod. Full height range from seedlings to mature.
    {
        "name": "Turf_Wild",
        "blade_count": 1800,
        "radius": 0.61,
        "height_range": (0.08, 0.40),       # 8cm seedlings to 40cm mature
        "width_range": (0.008, 0.018),       # wider, more varied
        "lean_range": (0.03, 0.12),          # dramatic lean on tall blades
        "base_rgb": (0.12, 0.28, 0.04),
        "tip_rgb": (0.40, 0.42, 0.16),      # warm golden-green tips
        "color_var": 0.06,
        "outward_pct": 0.55,
        "distribution": "wild",
        "seed": 503,
    },
    # 2: Shade — woodland floor, shade fescue (Festuca rubra). Sparse
    #    clumps in dappled light. Some taller stems reaching for light.
    {
        "name": "Turf_Shade",
        "blade_count": 1400,
        "radius": 0.61,
        "height_range": (0.05, 0.18),        # 5-18cm — reaching for light
        "width_range": (0.006, 0.014),
        "lean_range": (0.02, 0.06),
        "base_rgb": (0.06, 0.18, 0.03),     # very dark shade green
        "tip_rgb": (0.16, 0.30, 0.10),
        "color_var": 0.04,
        "outward_pct": 0.45,
        "distribution": "shade",
        "seed": 507,
    },
    # 3: Sedge — waterside Carex and Juncus. Upright growth habit,
    #    triangular stems, taller than lawn grass.
    {
        "name": "Turf_Sedge",
        "blade_count": 1600,
        "radius": 0.61,
        "height_range": (0.08, 0.25),        # 8-25cm — upright sedges
        "width_range": (0.006, 0.014),
        "lean_range": (0.02, 0.05),
        "base_rgb": (0.10, 0.26, 0.05),
        "tip_rgb": (0.24, 0.40, 0.14),
        "color_var": 0.04,
        "outward_pct": 0.35,                 # more upright — sedge growth habit
        "distribution": "sedge",
        "seed": 509,
    },
]


# ---------------------------------------------------------------------------
# Material & export
# ---------------------------------------------------------------------------
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
    h_lo, h_hi = cfg["height_range"]
    print(f"  {name}: {vc} verts, {fc} faces ({cfg['blade_count']} blades, "
          f"h={h_lo*100:.1f}-{h_hi*100:.1f}cm, dist={cfg.get('distribution','lawn')})")
    bpy.ops.object.delete(use_global=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

VARIANTS = 3  # different blade arrangements per type — breaks repetition

print("=" * 60)
print(f"Building {len(TURF_TYPES)} × {VARIANTS} ground cover tiles")
print("=" * 60)

mat = make_turf_material("TurfBlade")
total = 0

for i, cfg in enumerate(TURF_TYPES):
    base_name = cfg["name"]
    base_seed = cfg["seed"]
    blades = cfg["blade_count"]
    h_lo, h_hi = cfg["height_range"]

    for v in range(VARIANTS):
        name = f"{base_name}_v{v}"
        seed = base_seed + v * 1000  # different seed per variant
        print(f"\n[{total+1}/{len(TURF_TYPES)*VARIANTS}] {name} ({blades} blades)...")

        bm = build_turf_tile(cfg, seed)
        export_tile(bm, name, mat, cfg)
        total += 1

print(f"\nDone. {total} ground cover tiles exported.")

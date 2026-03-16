"""Build ground cover (turf carpet) tiles for Central Park Walk — 4 zone types.

Ground cover provides dense, low, ground-hugging vegetation that fills
the space between taller detail grass blades. Combined with the green
terrain shader base, this creates seamless grass coverage at all distances.

Blades lean OUTWARD from tile center to maximize ground coverage from above.
This is the key difference from detail blades (which are mostly vertical).

Types match Central Park zone categories:
  0. Turf_Lawn   — mowed lawn carpet (A/B/C lawns), 2.5-4.5cm
  1. Turf_Wild   — wild meadow ground cover (nature reserves), 4-10cm
  2. Turf_Shade  — woodland floor cover (Ramble, North Woods), 3-7cm
  3. Turf_Sedge  — waterside ground cover (shorelines), 4-9cm

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
# Grass blade — single quad, leaning outward from tile center
# ---------------------------------------------------------------------------
def make_blade(bm, color_layer, uv_layer,
               bx, bz, height, width, rot, lean,
               base_rgb, tip_rgb):
    """Create one grass blade as a single quad at position (bx, bz).

    Unlike detail blades which are mostly vertical, ground cover blades
    lean outward (controlled by 'lean' = horizontal extension in facing
    direction), covering ground area when viewed from above.
    """
    dx = math.cos(rot)
    dz = math.sin(rot)
    px = -math.sin(rot)
    pz = math.cos(rot)

    hw = width * 0.5
    # Tip position: extends outward (lean) and upward (height)
    tip_x = bx + dx * lean
    tip_z = bz + dz * lean
    # Width tapers at tip (30% of base width)
    thw = hw * 0.3

    v0 = bm.verts.new((bx + px * hw, 0.0, bz + pz * hw))
    v1 = bm.verts.new((bx - px * hw, 0.0, bz - pz * hw))
    v2 = bm.verts.new((tip_x - px * thw, height, tip_z - pz * thw))
    v3 = bm.verts.new((tip_x + px * thw, height, tip_z + pz * thw))

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
# Turf tile builder — blades fan outward from center
# ---------------------------------------------------------------------------
def build_turf_tile(cfg, seed):
    """Build a ground cover tile with blades leaning outward from center."""
    rng = random.Random(seed)
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    radius = cfg["radius"]
    blade_count = cfg["blade_count"]
    h_lo, h_hi = cfg["height_range"]
    w_lo, w_hi = cfg["width_range"]
    lean_lo, lean_hi = cfg["lean_range"]
    base_rgb = cfg["base_rgb"]
    tip_rgb = cfg["tip_rgb"]
    color_var = cfg.get("color_var", 0.04)
    outward_pct = cfg.get("outward_pct", 0.7)

    for _ in range(blade_count):
        # Distribute blades uniformly in circle (sqrt for even area density)
        r = radius * math.sqrt(rng.random())
        theta = rng.random() * 2 * math.pi
        bx = r * math.cos(theta)
        bz = r * math.sin(theta)

        # Direction: mostly outward from center, some random for natural look
        if rng.random() < outward_pct and r > 0.05:
            outward_angle = math.atan2(bz, bx)
            rot = outward_angle + rng.gauss(0, 0.3)  # ±17° scatter
        else:
            rot = rng.random() * 2 * math.pi

        h = rng.uniform(h_lo, h_hi)
        w = rng.uniform(w_lo, w_hi)
        lean = rng.uniform(lean_lo, lean_hi)

        # Per-blade color variation
        cv = rng.uniform(-color_var, color_var)
        b_rgb = (
            max(0.01, base_rgb[0] + cv * 0.8),
            max(0.01, base_rgb[1] + cv * 0.6),
            max(0.01, base_rgb[2] + cv * 0.4),
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
# 4 turf types — ground cover for each Central Park zone category
# ---------------------------------------------------------------------------
TURF_TYPES = [
    # 0: Lawn — mowed KBG/ryegrass carpet, dense and uniform
    {
        "name": "Turf_Lawn",
        "blade_count": 100,
        "radius": 0.45,
        "height_range": (0.025, 0.045),    # 2.5-4.5cm — below mow height
        "width_range": (0.015, 0.025),      # 15-25mm — wider than detail for coverage
        "lean_range": (0.02, 0.05),         # 2-5cm outward lean
        "base_rgb": (0.18, 0.38, 0.07),
        "tip_rgb": (0.40, 0.58, 0.22),
        "color_var": 0.04,
        "outward_pct": 0.75,
        "seed": 501,
    },
    # 1: Wild — unmowed meadow ground cover, taller and looser
    {
        "name": "Turf_Wild",
        "blade_count": 70,
        "radius": 0.50,
        "height_range": (0.04, 0.10),       # 4-10cm — unmowed understory
        "width_range": (0.015, 0.028),
        "lean_range": (0.03, 0.08),          # more dramatic lean
        "base_rgb": (0.14, 0.30, 0.05),
        "tip_rgb": (0.38, 0.42, 0.18),      # warm golden tips
        "color_var": 0.06,
        "outward_pct": 0.60,                 # more random, less manicured
        "seed": 503,
    },
    # 2: Shade — woodland floor fescue, sparse and dark
    {
        "name": "Turf_Shade",
        "blade_count": 50,
        "radius": 0.40,
        "height_range": (0.03, 0.07),        # 3-7cm
        "width_range": (0.012, 0.020),
        "lean_range": (0.02, 0.04),
        "base_rgb": (0.08, 0.22, 0.04),     # deep shade green
        "tip_rgb": (0.20, 0.36, 0.12),
        "color_var": 0.05,
        "outward_pct": 0.50,                 # more random under canopy
        "seed": 507,
    },
    # 3: Sedge — waterside ground cover, reedy
    {
        "name": "Turf_Sedge",
        "blade_count": 60,
        "radius": 0.45,
        "height_range": (0.04, 0.09),        # 4-9cm
        "width_range": (0.012, 0.022),
        "lean_range": (0.03, 0.06),
        "base_rgb": (0.12, 0.30, 0.06),
        "tip_rgb": (0.28, 0.45, 0.16),
        "color_var": 0.05,
        "outward_pct": 0.65,
        "seed": 509,
    },
]


# ---------------------------------------------------------------------------
# Material & export (same pattern as make_grass_patch.py)
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


def export_tile(bm, name, material):
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
    print(f"  {name}: {vc} verts, {fc} faces ({cfg['blade_count']} blades)")
    bpy.ops.object.delete(use_global=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

print("=" * 60)
print("Building 4 ground cover (turf) tiles — outward-lean blades")
print("=" * 60)

mat = make_turf_material("TurfBlade")

for i, cfg in enumerate(TURF_TYPES):
    name = cfg["name"]
    seed = cfg["seed"]
    blades = cfg["blade_count"]
    print(f"\n[{i+1}/{len(TURF_TYPES)}] {name} ({blades} blades, "
          f"r={cfg['radius']}m, h={cfg['height_range'][0]*100:.1f}-"
          f"{cfg['height_range'][1]*100:.1f}cm)...")

    bm = build_turf_tile(cfg, seed)
    export_tile(bm, name, mat)

print(f"\nDone. {len(TURF_TYPES)} ground cover tiles exported.")

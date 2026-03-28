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
    """Create a curved grass blade with N segments and cylinder-derived normals.

    Normals are computed as if the blade were a cylinder (Data Transfer
    technique from hexaquo). Left-edge normals point left, right-edge
    point right, implying roundness. Tips blend toward straight up.
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
        seg_z = height * (t - 0.12 * t * t)
        extend = arch * t * t
        seg_w = width * (1.0 - t * 0.65) * 0.5

        cx = bx + dx * extend
        cy = bz + dz * extend

        r = base_rgb[0] + (tip_rgb[0] - base_rgb[0]) * t
        g = base_rgb[1] + (tip_rgb[1] - base_rgb[1]) * t
        b = base_rgb[2] + (tip_rgb[2] - base_rgb[2]) * t

        vl = bm.verts.new((cx + px * seg_w, cy + pz * seg_w, seg_z))
        vr = bm.verts.new((cx - px * seg_w, cy - pz * seg_w, seg_z))
        vert_pairs.append((vl, vr, (r, g, b, 1.0), t))

    # Store normal data per loop for later application as custom split normals.
    # Cylinder-derived: left edge points (+px,+pz), right edge points (-px,-pz).
    # Blend toward up (0,0,1) at blade tip (t→1).
    loop_normals = []

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
                # Left edge, base-side: normal points left + slight up
                up_blend = t0
                nx = px * (1.0 - up_blend * 0.8)
                ny = pz * (1.0 - up_blend * 0.8)
                nz = up_blend * 0.8
                ln = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
                loop_normals.append((loop, (nx/ln, ny/ln, nz/ln)))
            elif loop.vert == vr0:
                loop[color_layer] = c0
                loop[uv_layer].uv = (1.0, t0)
                up_blend = t0
                nx = -px * (1.0 - up_blend * 0.8)
                ny = -pz * (1.0 - up_blend * 0.8)
                nz = up_blend * 0.8
                ln = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
                loop_normals.append((loop, (nx/ln, ny/ln, nz/ln)))
            elif loop.vert == vr1:
                loop[color_layer] = c1
                loop[uv_layer].uv = (1.0, t1)
                up_blend = t1
                nx = -px * (1.0 - up_blend * 0.8)
                ny = -pz * (1.0 - up_blend * 0.8)
                nz = up_blend * 0.8
                ln = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
                loop_normals.append((loop, (nx/ln, ny/ln, nz/ln)))
            elif loop.vert == vl1:
                loop[color_layer] = c1
                loop[uv_layer].uv = (0.0, t1)
                up_blend = t1
                nx = px * (1.0 - up_blend * 0.8)
                ny = pz * (1.0 - up_blend * 0.8)
                nz = up_blend * 0.8
                ln = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
                loop_normals.append((loop, (nx/ln, ny/ln, nz/ln)))

    return loop_normals


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
    all_normals = []

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

        blade_normals = make_blade(bm, color_layer, uv_layer,
                                    bx, bz, h, w, rot, arch, segments, b_rgb, t_rgb)
        all_normals.extend(blade_normals)

    return bm, all_normals


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
        "base_rgb": (0.37, 0.44, 0.38),  # spectral: KBG etiolated sheath
        "tip_rgb": (0.23, 0.40, 0.24),   # spectral: KBG healthy leaf
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
        "base_rgb": (0.41, 0.46, 0.41),  # spectral: switchgrass base
        "tip_rgb": (0.28, 0.41, 0.24),   # spectral: switchgrass leaf
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
        "base_rgb": (0.36, 0.42, 0.36),  # spectral: fine fescue base
        "tip_rgb": (0.22, 0.37, 0.22),   # spectral: fine fescue leaf
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
        "base_rgb": (0.35, 0.41, 0.35),  # spectral: tussock sedge base
        "tip_rgb": (0.22, 0.36, 0.21),   # spectral: tussock sedge leaf
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
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.06
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.06
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def export_tile(bm, all_normals, name, material, cfg):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)

    # Apply cylinder-derived custom split normals (hexaquo Data Transfer technique).
    # Build a mapping from bmesh loop index to normal vector.
    # bmesh loops and mesh loops are in the same order after to_mesh().
    normals_by_loop_idx = {}
    for loop, nrm in all_normals:
        normals_by_loop_idx[loop.index] = nrm

    # Enable custom split normals on the mesh
    if hasattr(mesh, 'use_auto_smooth'):
        mesh.use_auto_smooth = True
        mesh.auto_smooth_angle = math.pi  # accept all angles

    # Build the normals list in mesh loop order
    custom_normals = []
    for li in range(len(mesh.loops)):
        if li in normals_by_loop_idx:
            custom_normals.append(normals_by_loop_idx[li])
        else:
            custom_normals.append((0.0, 0.0, 1.0))  # fallback: up
    mesh.normals_split_custom_set(custom_normals)

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

# Turf tile generation (Turf_*_v{0-4}.glb) removed — superseded by
# per-blade GPU particles (Blade_*.glb). TURF_TYPES kept as reference data.

mat = make_turf_material("TurfBlade")


# ---------------------------------------------------------------------------
# Tier 0 blade variants — individual blades for near-field GPU particles
# ---------------------------------------------------------------------------
# Single-blade meshes with cylinder-derived normals. Used at 0-6m distance
# for botanical close-up detail alongside Tier 1 blades (Blade_Lawn.glb etc).
# 3 variants per biome (thin/wide/curved) × 4 biomes = 12 blade GLBs.
#
# Thin: narrower blade representing finer-textured species in the mix
# Wide: broader blade representing coarser species (ryegrass, bluestem)
# Curved: more dramatic arch for organic wind-blown variety

BLADE_VARIANTS = [
    # -- Lawn: spectral KBG (thin), ryegrass (wide), KBG avg (curved) --
    {"name": "Blade_Lawn_Thin", "segments": 2, "height": 0.076,
     "width": 0.015, "arch": 0.003,
     "base_rgb": (0.37, 0.44, 0.38), "tip_rgb": (0.23, 0.40, 0.24)},
    {"name": "Blade_Lawn_Wide", "segments": 2, "height": 0.055,
     "width": 0.045, "arch": 0.006,
     "base_rgb": (0.40, 0.47, 0.40), "tip_rgb": (0.25, 0.43, 0.26)},
    {"name": "Blade_Lawn_Curved", "segments": 3, "height": 0.065,
     "width": 0.025, "arch": 0.015,
     "base_rgb": (0.38, 0.45, 0.39), "tip_rgb": (0.24, 0.41, 0.25)},
    # -- Wild: spectral switchgrass (thin), bluestem (wide), avg (curved) --
    {"name": "Blade_Wild_Thin", "segments": 5, "height": 0.35,
     "width": 0.018, "arch": 0.10,
     "base_rgb": (0.41, 0.46, 0.41), "tip_rgb": (0.28, 0.41, 0.24)},
    {"name": "Blade_Wild_Wide", "segments": 3, "height": 0.18,
     "width": 0.050, "arch": 0.06,
     "base_rgb": (0.39, 0.45, 0.40), "tip_rgb": (0.23, 0.40, 0.26)},
    {"name": "Blade_Wild_Curved", "segments": 5, "height": 0.28,
     "width": 0.030, "arch": 0.14,
     "base_rgb": (0.40, 0.46, 0.40), "tip_rgb": (0.26, 0.41, 0.25)},
    # -- Shade: spectral fine fescue --
    {"name": "Blade_Shade_Thin", "segments": 3, "height": 0.10,
     "width": 0.012, "arch": 0.02,
     "base_rgb": (0.36, 0.42, 0.36), "tip_rgb": (0.22, 0.37, 0.22)},
    {"name": "Blade_Shade_Wide", "segments": 3, "height": 0.08,
     "width": 0.035, "arch": 0.04,
     "base_rgb": (0.36, 0.42, 0.36), "tip_rgb": (0.22, 0.37, 0.22)},
    {"name": "Blade_Shade_Curved", "segments": 4, "height": 0.14,
     "width": 0.020, "arch": 0.06,
     "base_rgb": (0.36, 0.42, 0.36), "tip_rgb": (0.22, 0.37, 0.22)},
    # -- Sedge: spectral tussock sedge (thin/curved), soft rush (wide) --
    {"name": "Blade_Sedge_Thin", "segments": 3, "height": 0.20,
     "width": 0.010, "arch": 0.03,
     "base_rgb": (0.35, 0.41, 0.35), "tip_rgb": (0.22, 0.36, 0.21)},
    {"name": "Blade_Sedge_Wide", "segments": 3, "height": 0.14,
     "width": 0.035, "arch": 0.05,
     "base_rgb": (0.37, 0.43, 0.37), "tip_rgb": (0.23, 0.38, 0.23)},
    {"name": "Blade_Sedge_Curved", "segments": 4, "height": 0.18,
     "width": 0.020, "arch": 0.08,
     "base_rgb": (0.36, 0.42, 0.36), "tip_rgb": (0.22, 0.37, 0.22)},
]

print("\n" + "=" * 60)
print(f"Building {len(BLADE_VARIANTS)} Tier 0 blade variants")
print(f"Single blades with cylinder normals for near-field particles")
print("=" * 60)

blade_n = 0
for bv in BLADE_VARIANTS:
    name = bv["name"]
    blade_n += 1
    print(f"\n[{blade_n}/{len(BLADE_VARIANTS)}] {name} "
          f"(h={bv['height']*100:.1f}cm w={bv['width']*1000:.0f}mm "
          f"arch={bv['arch']*100:.1f}cm {bv['segments']}seg)...")

    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    normals = make_blade(bm, color_layer, uv_layer,
                         0.0, 0.0, bv["height"], bv["width"],
                         0.0, bv["arch"], bv["segments"],
                         bv["base_rgb"], bv["tip_rgb"])

    export_tile(bm, normals, name, mat, bv)

print(f"\nDone. {blade_n} blade variants exported.")

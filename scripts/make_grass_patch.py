"""Build grass patch models for Central Park Walk.

Data-driven grass based on real Central Park vegetation zones:
  1. Maintained lawn (Kentucky bluegrass) — Sheep Meadow, Great Lawn, etc.
     Short (6-10cm), dense, bright green. Largest footprint (~0.85m radius)
     so patches overlap at 1.83m spacing to carpet the ground.
  2. Woodland floor — North Woods, Ramble, Hallett understory.
     Sparse, shade-adapted, darker green. Smaller footprint (~0.45m radius).
  3. Wild meadow — Nature reserve edges, unmowed areas.
     Tall (20-35cm), flowing, varied green with golden tips.

Colors from PIL analysis of Wikimedia Commons Central Park reference photos:
  - Sheep Meadow: bright green Kentucky bluegrass
  - North Woods/Ramble: darker shade-adapted understory
  - Grass texture close-up: blade color gradients

Each blade is a wide curved mesh strip radiating outward from clump center.
Vertex colors provide albedo (no texture needed — shader uses COLOR.rgb).

Exports to models/vegetation/Grass_Patch_Lawn.glb
                              Grass_Patch_Woodland.glb
                              Grass_Patch_Meadow.glb
"""

import bpy
import bmesh
import math
import random
import os

# ---------------------------------------------------------------------------
# Clear scene
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)
for block in bpy.data.materials:
    if block.users == 0:
        bpy.data.materials.remove(block)

# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Grass blade builder — wide arching blade
# ---------------------------------------------------------------------------
def make_blade(bm, color_layer, uv_layer,
               bx, bz, height, width, rot, arch_strength,
               segments, base_rgb, tip_rgb):
    """Create one wide arching grass blade as a curved mesh strip.

    Blades arch outward from center — arch_strength controls horizontal reach.
    Height follows parabolic arc: rises then droops toward tip.
    """
    out_dx = math.cos(rot)
    out_dz = math.sin(rot)
    perp_dx = -math.sin(rot)
    perp_dz = math.cos(rot)

    vert_pairs = []
    for si in range(segments + 1):
        t = si / segments
        # Parabolic arc: rises then curves over
        seg_h = height * (t - 0.3 * t * t)
        # Horizontal extension: blade arches outward
        extend = arch_strength * t * t
        # Width tapers from base to tip
        seg_w = width * (1.0 - t * 0.7)
        hw = seg_w * 0.5

        cx = bx + out_dx * extend
        cz = bz + out_dz * extend

        lx = cx + perp_dx * hw
        lz = cz + perp_dz * hw
        rx = cx - perp_dx * hw
        rz = cz - perp_dz * hw

        r = base_rgb[0] + (tip_rgb[0] - base_rgb[0]) * t
        g = base_rgb[1] + (tip_rgb[1] - base_rgb[1]) * t
        b = base_rgb[2] + (tip_rgb[2] - base_rgb[2]) * t

        vl = bm.verts.new((lx, seg_h, lz))
        vr = bm.verts.new((rx, seg_h, rz))
        vert_pairs.append((vl, vr, (r, g, b, 1.0), t))

    for si in range(segments):
        vl0, vr0, col0, t0 = vert_pairs[si]
        vl1, vr1, col1, t1 = vert_pairs[si + 1]

        try:
            face = bm.faces.new([vl0, vr0, vr1, vl1])
        except ValueError:
            continue

        for loop in face.loops:
            if loop.vert == vl0:
                loop[color_layer] = col0
                loop[uv_layer].uv = (0.0, t0)
            elif loop.vert == vr0:
                loop[color_layer] = col0
                loop[uv_layer].uv = (1.0, t0)
            elif loop.vert == vr1:
                loop[color_layer] = col1
                loop[uv_layer].uv = (1.0, t1)
            elif loop.vert == vl1:
                loop[color_layer] = col1
                loop[uv_layer].uv = (0.0, t1)


# ---------------------------------------------------------------------------
# Lawn patch — Kentucky bluegrass (Sheep Meadow, Great Lawn, etc.)
# ---------------------------------------------------------------------------
def build_lawn_patch(seed=42):
    """Maintained lawn — Kentucky bluegrass, mowed 5-10cm.

    Large footprint (~0.85m radius) so patches overlap at 1.83m spacing.
    Two rings of blades:
      Inner ring (12 blades): moderate arch, taller
      Outer ring (22 blades): strong arch, ground-hugging, fills carpet
    Total: 34 blades.

    Colors from Sheep Meadow reference photos:
      Base: dark rich green (0.12, 0.28, 0.04)
      Tips: bright yellow-green (0.38, 0.55, 0.22)
    """
    rng = random.Random(seed)
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    # --- Inner ring: 12 taller blades near center ---
    INNER_COUNT = 12
    for i in range(INNER_COUNT):
        base_angle = (i / INNER_COUNT) * 2 * math.pi
        rot = base_angle + rng.uniform(-0.35, 0.35)

        offset_r = rng.uniform(0.0, 0.10)
        bx = math.cos(rot) * offset_r
        bz = math.sin(rot) * offset_r

        h = rng.uniform(0.07, 0.12)       # 7-12cm
        w = rng.uniform(0.025, 0.040)     # 2.5-4cm wide
        arch = rng.uniform(0.20, 0.38)    # moderate outward reach

        cv = rng.uniform(-0.03, 0.03)
        base_rgb = (
            max(0.06, 0.12 + cv),
            max(0.15, 0.28 + cv * 0.7),
            max(0.02, 0.04 + cv * 0.4),
        )
        tip_rgb = (
            min(0.55, 0.38 + cv),
            min(0.70, 0.55 + cv * 0.6),
            min(0.35, 0.22 + cv * 0.3),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, arch,
                   segments=3, base_rgb=base_rgb, tip_rgb=tip_rgb)

    # --- Outer ring: 22 ground-hugging blades for carpet coverage ---
    OUTER_COUNT = 22
    for i in range(OUTER_COUNT):
        base_angle = (i / OUTER_COUNT) * 2 * math.pi
        rot = base_angle + rng.uniform(-0.25, 0.25)

        offset_r = rng.uniform(0.15, 0.35)
        bx = math.cos(rot) * offset_r
        bz = math.sin(rot) * offset_r

        h = rng.uniform(0.05, 0.09)       # shorter, ground-hugging
        w = rng.uniform(0.030, 0.050)     # wider blades for coverage
        arch = rng.uniform(0.30, 0.55)    # strong outward arch → tips at 0.65-0.90m

        cv = rng.uniform(-0.04, 0.04)
        base_rgb = (
            max(0.06, 0.14 + cv),
            max(0.15, 0.30 + cv * 0.7),
            max(0.02, 0.05 + cv * 0.4),
        )
        tip_rgb = (
            min(0.60, 0.42 + cv),
            min(0.72, 0.58 + cv * 0.6),
            min(0.38, 0.25 + cv * 0.3),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, arch,
                   segments=3, base_rgb=base_rgb, tip_rgb=tip_rgb)

    return bm


# ---------------------------------------------------------------------------
# Woodland floor patch — shade-adapted understory
# ---------------------------------------------------------------------------
def build_woodland_patch(seed=137):
    """Woodland understory — North Woods, Ramble, Hallett.

    Sparse, shade-adapted, darker green. Smaller footprint (~0.45m radius).
    Under heavy canopy (density_mult 1.0-1.4), grass is thin and patchy.
    12 blades total — sparse is correct for woodland floor.

    Colors darker than lawn — reduced light under canopy:
      Base: very dark green (0.06, 0.18, 0.02)
      Tips: muted green (0.20, 0.35, 0.12)
    """
    rng = random.Random(seed)
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    BLADE_COUNT = 12

    for i in range(BLADE_COUNT):
        base_angle = (i / BLADE_COUNT) * 2 * math.pi
        rot = base_angle + rng.uniform(-0.5, 0.5)

        offset_r = rng.uniform(0.0, 0.12)
        bx = math.cos(rot) * offset_r
        bz = math.sin(rot) * offset_r

        h = rng.uniform(0.04, 0.10)       # 4-10cm
        w = rng.uniform(0.020, 0.035)     # 2-3.5cm wide
        arch = rng.uniform(0.12, 0.30)    # moderate reach

        cv = rng.uniform(-0.04, 0.04)
        # Darker colors — reduced light under canopy
        base_rgb = (
            max(0.03, 0.06 + cv),
            max(0.10, 0.18 + cv * 0.6),
            max(0.01, 0.02 + cv * 0.3),
        )
        tip_rgb = (
            min(0.35, 0.20 + cv),
            min(0.48, 0.35 + cv * 0.5),
            min(0.22, 0.12 + cv * 0.3),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, arch,
                   segments=3, base_rgb=base_rgb, tip_rgb=tip_rgb)

    return bm


# ---------------------------------------------------------------------------
# Wild meadow patch — nature reserve / unmowed areas
# ---------------------------------------------------------------------------
def build_meadow_patch(seed=271):
    """Wild meadow — nature reserves, unmowed edges.

    Tall flowing grass (20-35cm), dramatic arch, darker green with golden tips.
    Two rings for coverage (~0.7m radius).

    Colors from North Meadow / grass texture reference photos:
      Base: deep green (0.08, 0.22, 0.02)
      Tips: golden-green (0.40, 0.45, 0.15) — seed heads
    """
    rng = random.Random(seed)
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    # Inner ring: 10 tall blades
    INNER_COUNT = 10
    for i in range(INNER_COUNT):
        base_angle = (i / INNER_COUNT) * 2 * math.pi
        rot = base_angle + rng.uniform(-0.40, 0.40)

        offset_r = rng.uniform(0.0, 0.08)
        bx = math.cos(rot) * offset_r
        bz = math.sin(rot) * offset_r

        h = rng.uniform(0.22, 0.38)       # tall
        w = rng.uniform(0.022, 0.035)     # moderate width
        arch = rng.uniform(0.20, 0.40)    # strong arch

        cv = rng.uniform(-0.05, 0.05)
        base_rgb = (
            max(0.04, 0.08 + cv),
            max(0.12, 0.22 + cv * 0.6),
            max(0.01, 0.02 + cv * 0.3),
        )
        # Golden-green tips (seed heads)
        tip_rgb = (
            min(0.55, 0.40 + cv),
            min(0.58, 0.45 + cv * 0.5),
            min(0.25, 0.15 + cv * 0.3),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, arch,
                   segments=4, base_rgb=base_rgb, tip_rgb=tip_rgb)

    # Outer ring: 14 medium blades
    OUTER_COUNT = 14
    for i in range(OUTER_COUNT):
        base_angle = (i / OUTER_COUNT) * 2 * math.pi
        rot = base_angle + rng.uniform(-0.30, 0.30)

        offset_r = rng.uniform(0.10, 0.25)
        bx = math.cos(rot) * offset_r
        bz = math.sin(rot) * offset_r

        h = rng.uniform(0.15, 0.30)
        w = rng.uniform(0.025, 0.042)     # wider for coverage
        arch = rng.uniform(0.25, 0.50)

        cv = rng.uniform(-0.05, 0.05)
        base_rgb = (
            max(0.04, 0.10 + cv),
            max(0.12, 0.24 + cv * 0.6),
            max(0.01, 0.03 + cv * 0.3),
        )
        tip_rgb = (
            min(0.55, 0.38 + cv),
            min(0.58, 0.42 + cv * 0.5),
            min(0.25, 0.14 + cv * 0.3),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, arch,
                   segments=4, base_rgb=base_rgb, tip_rgb=tip_rgb)

    return bm


# ---------------------------------------------------------------------------
# Material (vertex-color based for GLTF export)
# ---------------------------------------------------------------------------
def make_grass_material(name):
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
    bsdf.inputs['Metallic'].default_value = 0.0
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])

    return mat


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_patch(bm, name, material):
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
    print(f"  Exported {name}: {vc} verts, {fc} faces -> {filepath}")

    bpy.ops.object.delete(use_global=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 60)
print("Building data-driven grass patch models")
print("=" * 60)

mat = make_grass_material("GrassBlade")

print("\n[1/3] Maintained lawn (34 blades, 5-12cm, ~0.85m radius)...")
bm_lawn = build_lawn_patch(seed=42)
export_patch(bm_lawn, "Grass_Patch_Lawn", mat)

print("\n[2/3] Woodland floor (12 blades, 4-10cm, ~0.45m radius)...")
bm_woodland = build_woodland_patch(seed=137)
export_patch(bm_woodland, "Grass_Patch_Woodland", mat)

print("\n[3/3] Wild meadow (24 blades, 15-38cm, ~0.7m radius)...")
bm_meadow = build_meadow_patch(seed=271)
export_patch(bm_meadow, "Grass_Patch_Meadow", mat)

print("\nDone.")

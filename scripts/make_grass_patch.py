"""Build grass patch models for Central Park Walk.

Reference photos (Wikimedia Commons, all CC0/CC-BY-SA):
  - Sheep Meadow: dense bright-green mowed lawn, 3" (7.6cm) blades
  - Green grass texture: close-up flowing blades in wind
  - Grass and clovers: mowed lawn with clover patches

Two patch types modeled from reference:
  1. Mowed lawn (Sheep Meadow, Great Lawn, North Meadow)
     - Short upright blades (5-8cm), dense, bright green
     - Some clover leaves mixed in
  2. Wild meadow (North Woods, Ramble, Hallett Sanctuary)
     - Tall flowing blades (15-40cm), varied heights
     - More curve and lean, color variation

Each blade is a 3D mesh strip with 3-4 segments (curved, tapered).
Vertex colors encode green variation for the wind shader.
No textures — shader uses vertex color as albedo.

Exports to models/vegetation/Grass_Patch_Mowed.glb
                              Grass_Patch_Meadow.glb
"""

import bpy
import bmesh
import math
import random
import os
import sys

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
# Grass blade builder
# ---------------------------------------------------------------------------
def make_blade(bm, color_layer, uv_layer,
               bx, bz, height, width, rot, lean_angle, lean_strength,
               segments, base_rgb, tip_rgb):
    """Create one curved grass blade as a tapered mesh strip.

    bx, bz:         position on the patch ground plane (Y-up)
    height:          blade height in metres
    width:           blade width at base in metres
    rot:             Y-axis rotation (facing direction) in radians
    lean_angle:      direction the blade leans toward (radians)
    lean_strength:   how far the tip leans (fraction of height)
    segments:        number of vertical segments (3 = 6 verts)
    base_rgb:        (r, g, b) colour at blade base
    tip_rgb:         (r, g, b) colour at blade tip
    """
    dx = math.cos(rot)
    dz = math.sin(rot)
    lean_dx = math.cos(lean_angle) * lean_strength
    lean_dz = math.sin(lean_angle) * lean_strength

    vert_pairs = []
    for si in range(segments + 1):
        t = si / segments
        seg_h = height * t
        # Taper: full width at base, ~12% at tip
        seg_w = width * (1.0 - t * 0.88)
        hw = seg_w * 0.5

        # Quadratic curve toward lean direction
        cx = bx + lean_dx * t * t * height
        cz = bz + lean_dz * t * t * height

        # Perpendicular to blade facing for width offset
        lx = cx - dz * hw
        lz = cz + dx * hw
        rx = cx + dz * hw
        rz = cz - dx * hw

        # Colour interpolation
        r = base_rgb[0] + (tip_rgb[0] - base_rgb[0]) * t
        g = base_rgb[1] + (tip_rgb[1] - base_rgb[1]) * t
        b = base_rgb[2] + (tip_rgb[2] - base_rgb[2]) * t

        vl = bm.verts.new((lx, seg_h, lz))
        vr = bm.verts.new((rx, seg_h, rz))
        vert_pairs.append((vl, vr, (r, g, b, 1.0), t))

    # Create quad faces between segment pairs
    for si in range(segments):
        vl0, vr0, col0, t0 = vert_pairs[si]
        vl1, vr1, col1, t1 = vert_pairs[si + 1]

        try:
            face = bm.faces.new([vl0, vr0, vr1, vl1])
        except ValueError:
            continue  # degenerate face

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


def make_clover_leaf(bm, color_layer, uv_layer, bx, bz, radius, rot):
    """Create a simple clover leaf cluster (3 rounded lobes) as flat quads."""
    green = (0.18, 0.38, 0.08, 1.0)
    light = (0.22, 0.42, 0.10, 1.0)
    leaf_h = radius * 0.6  # slight elevation
    lobe_r = radius * 0.45

    for i in range(3):
        angle = rot + i * (2.0 * math.pi / 3.0)
        cx = bx + math.cos(angle) * lobe_r
        cz = bz + math.sin(angle) * lobe_r

        # Each lobe is a small diamond (4 verts, 2 tris)
        lr = lobe_r * 0.5
        v0 = bm.verts.new((cx, leaf_h, cz + lr))
        v1 = bm.verts.new((cx + lr, leaf_h, cz))
        v2 = bm.verts.new((cx, leaf_h, cz - lr))
        v3 = bm.verts.new((cx - lr, leaf_h, cz))

        try:
            face = bm.faces.new([v0, v1, v2, v3])
            for loop in face.loops:
                loop[color_layer] = green if loop.vert in (v0, v2) else light
                loop[uv_layer].uv = (0.5, 0.5)
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Patch builders
# ---------------------------------------------------------------------------
def build_mowed_patch(seed=42):
    """Mowed lawn patch — Sheep Meadow / Great Lawn style.

    Reference: 3" (7.6cm) maintained height, dense Kentucky bluegrass mix.
    Bright green, mostly upright, slight lean. Some clover mixed in.
    """
    rng = random.Random(seed)

    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    BLADE_COUNT = 64
    CLOVER_COUNT = 6
    PATCH_RADIUS = 0.90  # metres

    for _ in range(BLADE_COUNT):
        # Position: uniform distribution across circular patch
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.random()) * PATCH_RADIUS
        bx = math.cos(a) * d
        bz = math.sin(a) * d

        # Blade properties (from Sheep Meadow reference)
        h = rng.uniform(0.05, 0.08)    # 5-8cm mowed height
        w = rng.uniform(0.003, 0.005)   # 3-5mm blade width
        rot = rng.uniform(0, 2 * math.pi)
        lean_a = rng.uniform(0, 2 * math.pi)
        lean_s = rng.uniform(0.05, 0.20)  # slight lean

        # Colour from reference photos (green grass texture + sheep meadow)
        cv = rng.uniform(-0.03, 0.03)
        base_rgb = (
            max(0.10, 0.22 + cv),
            max(0.20, 0.38 + cv * 0.7),
            max(0.04, 0.08 + cv * 0.4),
        )
        tip_rgb = (
            min(0.50, base_rgb[0] * 1.35),
            min(0.60, base_rgb[1] * 1.20),
            min(0.30, base_rgb[2] * 0.75),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, lean_a, lean_s,
                   segments=3, base_rgb=base_rgb, tip_rgb=tip_rgb)

    # A few clover patches (from grass_and_clovers.jpg reference)
    for _ in range(CLOVER_COUNT):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.random()) * PATCH_RADIUS * 0.8
        cx = math.cos(a) * d
        cz = math.sin(a) * d
        make_clover_leaf(bm, color_layer, uv_layer,
                         cx, cz, radius=0.025, rot=rng.uniform(0, math.pi))

    return bm


def build_meadow_patch(seed=137):
    """Wild meadow patch — North Woods / Ramble / Hallett style.

    Reference: tall flowing grass, varied heights, more lean and curve.
    Darker green with yellow-green variation. No clover.
    """
    rng = random.Random(seed)

    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    BLADE_COUNT = 48
    PATCH_RADIUS = 0.90

    for _ in range(BLADE_COUNT):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.random()) * PATCH_RADIUS
        bx = math.cos(a) * d
        bz = math.sin(a) * d

        # Taller, more varied (from green grass texture reference)
        h = rng.uniform(0.15, 0.38)
        w = rng.uniform(0.004, 0.007)
        rot = rng.uniform(0, 2 * math.pi)
        lean_a = rng.uniform(0, 2 * math.pi)
        lean_s = rng.uniform(0.15, 0.45)  # more curve

        # Darker, more varied greens
        cv = rng.uniform(-0.05, 0.05)
        base_rgb = (
            max(0.08, 0.16 + cv),
            max(0.18, 0.34 + cv * 0.6),
            max(0.03, 0.06 + cv * 0.3),
        )
        tip_rgb = (
            min(0.55, base_rgb[0] * 1.50),
            min(0.65, base_rgb[1] * 1.30),
            min(0.25, base_rgb[2] * 0.60),
        )

        make_blade(bm, color_layer, uv_layer,
                   bx, bz, h, w, rot, lean_a, lean_s,
                   segments=4, base_rgb=base_rgb, tip_rgb=tip_rgb)

    return bm


# ---------------------------------------------------------------------------
# Material (vertex-color based for GLTF export)
# ---------------------------------------------------------------------------
def make_grass_material(name):
    """Create a Principled BSDF material driven by vertex colors."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False

    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links

    # Clear default nodes
    for n in nodes:
        nodes.remove(n)

    # Output
    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)

    # Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular'].default_value = 0.06
    bsdf.inputs['Metallic'].default_value = 0.0
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # Vertex Color attribute
    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])

    return mat


# ---------------------------------------------------------------------------
# Export helper
# ---------------------------------------------------------------------------
def export_patch(bm, name, material):
    """Convert bmesh to object, assign material, export as GLB."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    # Select only this object
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

    # Clean up for next export
    bpy.ops.object.delete(use_global=False)
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 60)
print("Building grass patch models from Central Park references")
print("=" * 60)

mat = make_grass_material("GrassBlade")

print("\n[1/2] Mowed lawn (Sheep Meadow / Great Lawn style)...")
bm_mowed = build_mowed_patch(seed=42)
export_patch(bm_mowed, "Grass_Patch_Mowed", mat)

print("\n[2/2] Wild meadow (North Woods / Ramble style)...")
bm_meadow = build_meadow_patch(seed=137)
export_patch(bm_meadow, "Grass_Patch_Meadow", mat)

print("\nDone.")

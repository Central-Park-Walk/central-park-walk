"""Build botanical accent meshes for Central Park Walk Tier 0 close-up.

Small ground-level details scattered among grass blades via GPU particles.
Each accent is a simple low-poly mesh with vertex colors, designed to add
biome-specific character at meditation-pace viewing distances (0-6m).

  Accent_Clover.glb     — White clover rosette (Trifolium repens), lawn zones
  Accent_Dandelion.glb  — Dandelion rosette + flower (Taraxacum), lawn/open
  Accent_Plantain.glb   — Broadleaf plantain rosette (Plantago major), lawns
  Accent_DriedLeaf.glb  — Curled fallen deciduous leaf, shade/woodland floor
  Accent_SeedHead.glb   — Dried grass seed head on stem, wild meadow

Run: blender4 --background --python scripts/make_accent_meshes.py
"""

import bpy
import bmesh
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)


def make_accent_material(name):
    """Simple vertex-color material matching turf blade PBR."""
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
    bsdf.inputs['Roughness'].default_value = 0.82
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.05
    elif 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = 0.05
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def export_accent(bm, name, material):
    """Export a bmesh as a GLB file."""
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
        export_normals=True,
        export_apply=True,
    )

    vc = len(mesh.vertices)
    fc = len(mesh.polygons)
    print(f"  {name}: {vc} verts, {fc} faces -> {filepath}")
    bpy.ops.object.delete(use_global=False)


# ---------------------------------------------------------------------------
# Accent geometry builders
# ---------------------------------------------------------------------------

def build_clover():
    """White clover (Trifolium repens) — 3 heart-shaped leaflets.

    ~15mm across, sits 2-4mm above ground. Common lawn weed visible at
    close range as dark-green rosettes among lighter grass blades.
    """
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Color")
    uv = bm.loops.layers.uv.new("UV")

    leaf_col = (0.12, 0.36, 0.06, 1.0)
    mark_col = (0.18, 0.42, 0.10, 1.0)  # lighter chevron center

    for i in range(3):
        angle = i * 2.094 + 0.3  # 120 deg apart
        ca, sa = math.cos(angle), math.sin(angle)
        cx = ca * 0.007  # 7mm from center
        cy = sa * 0.007
        hs = 0.005  # 5mm half-size per leaflet

        # Leaflet quad, tilted slightly outward from center
        v0 = bm.verts.new((cx - sa * hs, cy + ca * hs, 0.003))
        v1 = bm.verts.new((cx + sa * hs, cy - ca * hs, 0.003))
        v2 = bm.verts.new((cx + ca * hs * 1.2 + sa * hs * 0.3,
                           cy + sa * hs * 1.2 - ca * hs * 0.3, 0.004))
        v3 = bm.verts.new((cx + ca * hs * 1.2 - sa * hs * 0.3,
                           cy + sa * hs * 1.2 + ca * hs * 0.3, 0.004))
        try:
            face = bm.faces.new([v0, v1, v2, v3])
        except ValueError:
            continue
        for j, loop in enumerate(face.loops):
            loop[cl] = mark_col if j < 2 else leaf_col
            loop[uv].uv = (0.5, float(j >= 2))

    return bm


def build_dandelion():
    """Dandelion (Taraxacum officinale) — radiating jagged leaves + flower.

    5 narrow leaves radiating ~35-45mm from center, flat on ground.
    Small yellow flower head on a 6cm stem. Unmistakable lawn character.
    """
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Color")
    uv = bm.loops.layers.uv.new("UV")

    leaf_base = (0.14, 0.32, 0.05, 1.0)
    leaf_tip = (0.18, 0.36, 0.08, 1.0)
    flower_col = (0.72, 0.65, 0.12, 1.0)

    # 5 radiating jagged leaves
    for i in range(5):
        angle = i * 1.2566 + 0.2  # ~72 deg apart
        ca, sa = math.cos(angle), math.sin(angle)
        length = 0.035 + (i % 2) * 0.010  # alternate 35/45mm
        hw = 0.004  # 4mm half-width — narrow jagged leaf

        v0 = bm.verts.new((-sa * hw, ca * hw, 0.002))
        v1 = bm.verts.new((sa * hw, -ca * hw, 0.002))
        v2 = bm.verts.new((ca * length + sa * hw * 0.3,
                           sa * length - ca * hw * 0.3, 0.003))
        v3 = bm.verts.new((ca * length - sa * hw * 0.3,
                           sa * length + ca * hw * 0.3, 0.003))
        try:
            face = bm.faces.new([v0, v1, v2, v3])
        except ValueError:
            continue
        for j, loop in enumerate(face.loops):
            loop[cl] = leaf_base if j < 2 else leaf_tip
            loop[uv].uv = (0.5, float(j >= 2))

    # Yellow flower head on 6cm stem
    fh = 0.060
    fr = 0.008
    v0 = bm.verts.new((-fr, -fr, fh))
    v1 = bm.verts.new((fr, -fr, fh))
    v2 = bm.verts.new((fr, fr, fh + 0.003))
    v3 = bm.verts.new((-fr, fr, fh + 0.003))
    try:
        face = bm.faces.new([v0, v1, v2, v3])
        for loop in face.loops:
            loop[cl] = flower_col
            loop[uv].uv = (0.5, 1.0)
    except ValueError:
        pass

    return bm


def build_plantain():
    """Broadleaf plantain (Plantago major) — oval leaves flat on ground.

    4 broad oval leaves radiating from center, 30-38mm long. Darker,
    coarser texture than grass — visible as flat dark rosettes in lawns.
    """
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Color")
    uv = bm.loops.layers.uv.new("UV")

    leaf_col = (0.10, 0.28, 0.04, 1.0)
    vein_col = (0.12, 0.30, 0.06, 1.0)

    for i in range(4):
        angle = i * 1.5708 + 0.4  # 90 deg apart
        ca, sa = math.cos(angle), math.sin(angle)
        length = 0.030 + (i % 2) * 0.008  # 30-38mm
        hw = 0.010 + (i % 2) * 0.003  # 10-13mm half-width (broad oval)

        # Narrow base, broad tip — characteristic plantain shape
        v0 = bm.verts.new((-sa * hw * 0.4, ca * hw * 0.4, 0.001))
        v1 = bm.verts.new((sa * hw * 0.4, -ca * hw * 0.4, 0.001))
        v2 = bm.verts.new((ca * length + sa * hw,
                           sa * length - ca * hw, 0.003))
        v3 = bm.verts.new((ca * length - sa * hw,
                           sa * length + ca * hw, 0.003))
        try:
            face = bm.faces.new([v0, v1, v2, v3])
        except ValueError:
            continue
        for j, loop in enumerate(face.loops):
            loop[cl] = vein_col if j < 2 else leaf_col
            loop[uv].uv = (0.5, float(j >= 2))

    return bm


def build_dried_leaf():
    """Fallen deciduous leaf — curled single leaf on woodland floor.

    2-segment quad strip: base flat, tip curled up. ~40mm long.
    Warm autumn brown tones. Creates woodland floor litter character.
    """
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Color")
    uv = bm.loops.layers.uv.new("UV")

    stem_col = (0.35, 0.22, 0.08, 1.0)
    edge_col = (0.45, 0.30, 0.10, 1.0)
    tip_col = (0.50, 0.35, 0.12, 1.0)

    length = 0.040
    hw = 0.0125  # 25mm wide

    # Segment 1: base, flat on ground
    v0 = bm.verts.new((-hw, 0, 0.001))
    v1 = bm.verts.new((hw, 0, 0.001))
    v2 = bm.verts.new((hw * 0.9, length * 0.5, 0.004))
    v3 = bm.verts.new((-hw * 0.9, length * 0.5, 0.004))
    try:
        face = bm.faces.new([v0, v1, v2, v3])
        for j, loop in enumerate(face.loops):
            loop[cl] = stem_col if j < 2 else edge_col
            loop[uv].uv = (float(j in (1, 2)), float(j >= 2) * 0.5)
    except ValueError:
        pass

    # Segment 2: tip curled upward
    v4 = bm.verts.new((hw * 0.6, length, 0.012))
    v5 = bm.verts.new((-hw * 0.6, length, 0.012))
    try:
        face = bm.faces.new([v3, v2, v4, v5])
        for j, loop in enumerate(face.loops):
            loop[cl] = edge_col if j < 2 else tip_col
            loop[uv].uv = (float(j in (1, 2)), 0.5 + float(j >= 2) * 0.5)
    except ValueError:
        pass

    return bm


def build_seed_head():
    """Dried grass seed head — thin stem topped with seed cluster.

    2-segment stem ~12cm tall with a small seed cluster quad at top.
    Straw/tan tones. Adds vertical interest to wild meadow biome.
    """
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Color")
    uv = bm.loops.layers.uv.new("UV")

    stem_col = (0.42, 0.35, 0.15, 1.0)
    seed_col = (0.50, 0.40, 0.18, 1.0)

    stem_h = 0.12  # 12cm
    hw = 0.0015  # 3mm wide stem

    # Stem segment 1: base to mid
    v0 = bm.verts.new((-hw, 0, 0.0))
    v1 = bm.verts.new((hw, 0, 0.0))
    v2 = bm.verts.new((hw + 0.001, 0, stem_h * 0.6))
    v3 = bm.verts.new((-hw + 0.001, 0, stem_h * 0.6))
    try:
        face = bm.faces.new([v0, v1, v2, v3])
        for loop in face.loops:
            loop[cl] = stem_col
            loop[uv].uv = (0.5, 0.3)
    except ValueError:
        pass

    # Stem segment 2: mid to top (slight lean)
    v4 = bm.verts.new((hw + 0.002, 0, stem_h))
    v5 = bm.verts.new((-hw + 0.002, 0, stem_h))
    try:
        face = bm.faces.new([v3, v2, v4, v5])
        for loop in face.loops:
            loop[cl] = stem_col
            loop[uv].uv = (0.5, 0.7)
    except ValueError:
        pass

    # Seed head — small cluster quad at top
    sh = 0.006  # 12mm across
    v6 = bm.verts.new((-sh + 0.002, -sh, stem_h - 0.005))
    v7 = bm.verts.new((sh + 0.002, -sh, stem_h - 0.005))
    v8 = bm.verts.new((sh + 0.002, sh, stem_h + 0.005))
    v9 = bm.verts.new((-sh + 0.002, sh, stem_h + 0.005))
    try:
        face = bm.faces.new([v6, v7, v8, v9])
        for loop in face.loops:
            loop[cl] = seed_col
            loop[uv].uv = (0.5, 1.0)
    except ValueError:
        pass

    return bm


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

ACCENTS = [
    ("Accent_Clover", build_clover),
    ("Accent_Dandelion", build_dandelion),
    ("Accent_Plantain", build_plantain),
    ("Accent_DriedLeaf", build_dried_leaf),
    ("Accent_SeedHead", build_seed_head),
]

print("=" * 60)
print(f"Building {len(ACCENTS)} botanical accent meshes")
print("=" * 60)

mat = make_accent_material("AccentMat")

for name, builder in ACCENTS:
    print(f"\n  Building {name}...")
    bm = builder()
    export_accent(bm, name, mat)

print(f"\nDone. {len(ACCENTS)} accent meshes exported.")

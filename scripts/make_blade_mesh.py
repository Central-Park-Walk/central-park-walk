"""Build single grass blade meshes — one per zone type.

Each blade is a curved quad strip. Used as the shared mesh in GPU particles,
with each blade placed as an individual instance.

  Blade_Lawn.glb  — 2 segments, nearly straight (7.6cm)
  Blade_Wild.glb  — 4 segments, dramatic arc (25cm)
  Blade_Shade.glb — 3 segments, gentle curve (12cm)
  Blade_Sedge.glb — 3 segments, lean (16cm)

Run: blender4 --background --python scripts/make_blade_mesh.py
"""

import bpy
import bmesh
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)

BLADE_TYPES = [
    {   # Spectral: Kentucky Bluegrass (Poa pratensis)
        "name": "Blade_Lawn",
        "segments": 2,
        "height": 0.076,
        "width": 0.030,
        "arch": 0.004,
        "base_rgb": (0.37, 0.44, 0.38),
        "tip_rgb": (0.23, 0.40, 0.24),
    },
    {   # Spectral: Switchgrass (Panicum virgatum)
        "name": "Blade_Wild",
        "segments": 4,
        "height": 0.25,
        "width": 0.035,
        "arch": 0.08,
        "base_rgb": (0.41, 0.46, 0.41),
        "tip_rgb": (0.28, 0.41, 0.24),
    },
    {   # Spectral: Fine Fescue (Festuca rubra)
        "name": "Blade_Shade",
        "segments": 3,
        "height": 0.12,
        "width": 0.025,
        "arch": 0.03,
        "base_rgb": (0.36, 0.42, 0.36),
        "tip_rgb": (0.22, 0.37, 0.22),
    },
    {   # Spectral: Tussock Sedge (Carex stricta)
        "name": "Blade_Sedge",
        "segments": 3,
        "height": 0.16,
        "width": 0.025,
        "arch": 0.04,
        "base_rgb": (0.35, 0.41, 0.35),
        "tip_rgb": (0.22, 0.36, 0.21),
    },
]


def make_blade(cfg):
    """Create one curved grass blade centered at origin."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UV")
    color_layer = bm.loops.layers.color.new("Color")

    segments = cfg["segments"]
    height = cfg["height"]
    width = cfg["width"]
    arch = cfg["arch"]
    base_rgb = cfg["base_rgb"]
    tip_rgb = cfg["tip_rgb"]

    vert_pairs = []
    for si in range(segments + 1):
        t = si / segments
        z = height * (t - 0.12 * t * t)
        x = arch * t * t
        w = width * (1.0 - t * 0.65) * 0.5

        vl = bm.verts.new((x, w, z))
        vr = bm.verts.new((x, -w, z))

        r = base_rgb[0] + (tip_rgb[0] - base_rgb[0]) * t
        g = base_rgb[1] + (tip_rgb[1] - base_rgb[1]) * t
        b = base_rgb[2] + (tip_rgb[2] - base_rgb[2]) * t
        vert_pairs.append((vl, vr, (r, g, b, 1.0), t))

    for si in range(segments):
        vl0, vr0, c0, t0 = vert_pairs[si]
        vl1, vr1, c1, t1 = vert_pairs[si + 1]
        try:
            face = bm.faces.new([vl0, vr0, vr1, vl1])
        except ValueError:
            continue
        face.smooth = True
        for loop in face.loops:
            is_left = loop.vert in (vl0, vl1)
            t_val = t0 if loop.vert in (vl0, vr0) else t1
            col = c0 if loop.vert in (vl0, vr0) else c1
            loop[color_layer] = col
            loop[uv_layer].uv = (0.0 if is_left else 1.0, t_val)

    name = cfg["name"]
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    # Simple material with vertex colors
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        nodes.remove(n)
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.4
    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.append(mat)

    return obj


# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print(f"Building {len(BLADE_TYPES)} blade meshes...")

for cfg in BLADE_TYPES:
    obj = make_blade(cfg)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    filepath = os.path.join(OUT_DIR, cfg["name"] + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_normals=True,
        export_apply=True,
    )
    vc = len(obj.data.vertices)
    fc = len(obj.data.polygons)
    print(f"  {cfg['name']}: {vc} verts, {fc} faces -> {filepath}")
    bpy.ops.object.delete(use_global=False)

print("Done.")

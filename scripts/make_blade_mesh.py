"""Build single grass blade meshes — one per zone type.

Each blade is a curved strip with cylinder-derived normals (hexaquo
Data Transfer technique). These are used as the shared mesh in
MultiMesh, with each blade placed as an individual instance.

  Blade_Lawn.glb  — 2 segments, nearly straight (mowed 7.6cm)
  Blade_Wild.glb  — 4 segments, dramatic arc (8-40cm)
  Blade_Shade.glb — 3 segments, gentle curve (5-18cm)
  Blade_Sedge.glb — 3 segments, lean (8-25cm)

Exports to models/vegetation/Blade_*.glb
"""

import bpy
import bmesh
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)


def make_single_blade(segments, height, width, arch, base_rgb, tip_rgb):
    """Create one curved grass blade centered at origin with cylinder normals.

    The blade is a vertical strip along Z (Blender Z-up).
    UV.y goes from 0 at base to 1 at tip.
    Normals imply roundness: left edge points left, right edge points right.
    """
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")
    uv_layer = bm.loops.layers.uv.new("UV")

    # Blade faces along +X, width along +Y
    vert_pairs = []
    for si in range(segments + 1):
        t = si / segments
        seg_z = height * (t - 0.12 * t * t)
        extend = arch * t * t
        seg_w = width * (1.0 - t * 0.65) * 0.5

        cx = extend  # arch extends along +X
        vl = bm.verts.new((cx, seg_w, seg_z))
        vr = bm.verts.new((cx, -seg_w, seg_z))

        r = base_rgb[0] + (tip_rgb[0] - base_rgb[0]) * t
        g = base_rgb[1] + (tip_rgb[1] - base_rgb[1]) * t
        b = base_rgb[2] + (tip_rgb[2] - base_rgb[2]) * t
        vert_pairs.append((vl, vr, (r, g, b, 1.0), t))

    loop_normals = []
    for si in range(segments):
        vl0, vr0, c0, t0 = vert_pairs[si]
        vl1, vr1, c1, t1 = vert_pairs[si + 1]
        try:
            face = bm.faces.new([vl0, vr0, vr1, vl1])
        except ValueError:
            continue
        for loop in face.loops:
            # Determine left/right and height fraction
            is_left = loop.vert in (vl0, vl1)
            t_val = t0 if loop.vert in (vl0, vr0) else t1
            col = c0 if loop.vert in (vl0, vr0) else c1

            loop[color_layer] = col
            loop[uv_layer].uv = (0.0 if is_left else 1.0, t_val)

            # Cylinder-derived normal: left points +Y, right points -Y
            # Blend toward up (0,0,1) at blade tip
            side = 1.0 if is_left else -1.0
            up_blend = t_val
            ny = side * (1.0 - up_blend * 0.8)
            nz = up_blend * 0.8
            ln = math.sqrt(ny * ny + nz * nz) or 1.0
            loop_normals.append((loop, (0.0, ny / ln, nz / ln)))

    return bm, loop_normals


BLADE_TYPES = [
    {
        "name": "Blade_Lawn",
        "segments": 2,
        "height": 0.076,       # 3 inches — CPC mow height
        "width": 0.012,        # 12mm KBG blade
        "arch": 0.004,         # nearly straight
        "base_rgb": (0.15, 0.35, 0.06),
        "tip_rgb": (0.35, 0.55, 0.18),
    },
    {
        "name": "Blade_Wild",
        "segments": 4,
        "height": 0.25,        # mid-range meadow height
        "width": 0.015,
        "arch": 0.08,          # dramatic arc
        "base_rgb": (0.12, 0.28, 0.04),
        "tip_rgb": (0.40, 0.42, 0.16),
    },
    {
        "name": "Blade_Shade",
        "segments": 3,
        "height": 0.12,        # mid-range shade fescue
        "width": 0.010,
        "arch": 0.03,          # gentle curve
        "base_rgb": (0.06, 0.18, 0.03),
        "tip_rgb": (0.16, 0.30, 0.10),
    },
    {
        "name": "Blade_Sedge",
        "segments": 3,
        "height": 0.16,        # mid-range sedge
        "width": 0.009,
        "arch": 0.04,          # lean
        "base_rgb": (0.10, 0.26, 0.05),
        "tip_rgb": (0.24, 0.40, 0.14),
    },
]


def make_material(name):
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
    bsdf.inputs['Roughness'].default_value = 0.4
    bsdf.inputs['Specular'].default_value = 0.2
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    vcol = nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Color"
    links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    if block.users == 0:
        bpy.data.meshes.remove(block)

print("=" * 60)
print(f"Building {len(BLADE_TYPES)} single blade meshes")
print("=" * 60)

mat = make_material("GrassBlade")

for cfg in BLADE_TYPES:
    name = cfg["name"]
    print(f"\n  {name} ({cfg['segments']} segments, h={cfg['height']*100:.1f}cm)...")

    bm, loop_normals = make_single_blade(
        cfg["segments"], cfg["height"], cfg["width"], cfg["arch"],
        cfg["base_rgb"], cfg["tip_rgb"])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)

    # Apply cylinder-derived custom split normals
    normals_by_idx = {loop.index: nrm for loop, nrm in loop_normals}
    mesh.use_auto_smooth = True
    mesh.auto_smooth_angle = math.pi
    custom_normals = [normals_by_idx.get(i, (0.0, 0.0, 1.0)) for i in range(len(mesh.loops))]
    mesh.normals_split_custom_set(custom_normals)

    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)

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
    print(f"  {name}: {vc} verts, {fc} faces ({cfg['segments']*2} tris)")
    bpy.ops.object.delete(use_global=False)

print(f"\nDone. {len(BLADE_TYPES)} blade meshes exported.")

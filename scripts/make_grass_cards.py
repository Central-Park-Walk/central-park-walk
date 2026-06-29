"""Build AAA-style grass CLUSTER CARDS — the Witcher 3 / GTA V method.

Instead of drawing each tuft as hundreds of polygon blades (the dated, flat-lit
approach), we:
  1. Build a rich "hero" clump of many fine blades (rendered once, off-line).
  2. Render it orthographically, side-on, UNLIT (emission = a luminance ramp:
     dark shadowed base -> bright tips) with a TRANSPARENT background, to an
     RGBA card texture. Alpha = the blade silhouette; RGB = luminance/AO detail.
  3. Build a tiny card mesh — 3 crossed quads (~12 tris) wearing that texture —
     and export it as Blade_<biome>.glb (same filenames the grass system already
     loads). main.gd auto-enables `use_texture` when the GLB carries an albedo.

In-game the render shader uses the card ALPHA for the cutout and the card
LUMINANCE to modulate ONE data-driven green palette (so colour stays unified and
seasonal), while wind bends the whole card from its base (UV.y). Result: the
visual density of 100+ blades for ~12 triangles per tuft — the triangle budget
that lets the field run dense at 60 fps.

Run: blender4 --background --python scripts/make_grass_cards.py
"""

import bpy
import bmesh
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
GLB_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
TEX_DIR = os.path.join(PROJECT_DIR, "textures", "grass")
os.makedirs(GLB_DIR, exist_ok=True)
os.makedirs(TEX_DIR, exist_ok=True)

# Rich hero clumps — rendered once to a card, so blade count is "free".
CARDS = [
    {   # Kentucky Bluegrass — lush tended lawn (dense, near-even)
        "name": "Blade_Lawn",
        "segments": 4, "height": 0.20, "width": 0.010, "arch": 0.035,
        "blades": 190, "clump_radius": 0.11, "dome": 0.32, "splay": 0.42,
        "height_var": 0.34, "flag_frac": 0.08, "res": 512,
    },
    {   # Switchgrass — tall meadow bunch grass
        "name": "Blade_Wild",
        "segments": 5, "height": 0.34, "width": 0.013, "arch": 0.13,
        "blades": 150, "clump_radius": 0.085, "dome": 0.55, "splay": 0.65,
        "height_var": 0.42, "flag_frac": 0.16, "res": 512,
    },
    {   # Fine Fescue — soft woodland
        "name": "Blade_Shade",
        "segments": 4, "height": 0.21, "width": 0.008, "arch": 0.08,
        "blades": 160, "clump_radius": 0.09, "dome": 0.40, "splay": 0.52,
        "height_var": 0.38, "flag_frac": 0.12, "res": 512,
    },
    {   # Tussock Sedge — waterside upright fan
        "name": "Blade_Sedge",
        "segments": 4, "height": 0.21, "width": 0.010, "arch": 0.05,
        "blades": 140, "clump_radius": 0.07, "dome": 0.42, "splay": 0.32,
        "height_var": 0.36, "flag_frac": 0.12, "res": 512,
    },
]

GOLDEN = math.pi * (3.0 - math.sqrt(5.0))


def _frac(n):
    return (math.sin(n * 12.9898) * 43758.5453) % 1.0


def build_clump(cfg):
    """Hero clump geometry. Vertex colour is a grayscale LUMINANCE ramp
    (base ~shadowed, tip ~bright) so the rendered card bakes soft AO depth."""
    bm = bmesh.new()
    color_layer = bm.loops.layers.color.new("Color")

    seg = cfg["segments"]; H = cfg["height"]; W = cfg["width"]; arch = cfg["arch"]
    n = cfg["blades"]; cr = cfg["clump_radius"]
    dome = cfg["dome"]; splay = cfg["splay"]; hv = cfg["height_var"]; ff = cfg["flag_frac"]

    for bi in range(n):
        ang = bi * GOLDEN
        frac = (bi + 0.5) / n
        rad = cr * math.sqrt(frac)
        bx, by = rad * math.cos(ang), rad * math.sin(ang)
        n1 = _frac(bi * 7 + 3); n2 = _frac(bi * 13 + 11)
        dome_h = 1.0 - dome * frac
        jitter = 1.0 + (n1 - 0.5) * 2.0 * hv
        flag = 1.0 + (0.6 if n2 < ff else 0.0)
        hvar = max(0.3, dome_h * jitter * flag)
        out_yaw = math.atan2(by, bx) if rad > 1e-5 else ang
        yaw = out_yaw + (n1 - 0.5) * 1.5
        lean = splay * frac
        fwd = (math.cos(yaw), math.sin(yaw)); side = (-math.sin(yaw), math.cos(yaw))
        # slight per-blade brightness so blades read individually
        shade = 0.82 + 0.18 * n2

        pairs = []
        for si in range(seg + 1):
            t = si / seg
            along = (arch * t * t + H * lean * t) * hvar
            up = H * hvar * (t - 0.10 * t * t)
            hw = W * (1.0 - t) ** 0.65 * 0.5 + W * 0.05
            cx = bx + fwd[0] * along; cy = by + fwd[1] * along
            vl = bm.verts.new((cx + side[0] * hw, cy + side[1] * hw, up))
            vr = bm.verts.new((cx - side[0] * hw, cy - side[1] * hw, up))
            lum = (0.40 + 0.60 * t) * shade   # dark base -> bright tip (AO)
            pairs.append((vl, vr, (lum, lum, lum, 1.0), t))
        for si in range(seg):
            vl0, vr0, c0, _ = pairs[si]
            vl1, vr1, c1, _ = pairs[si + 1]
            try:
                f = bm.faces.new([vl0, vr0, vr1, vl1])
            except ValueError:
                continue
            for loop in f.loops:
                loop[color_layer] = c0 if loop.vert in (vl0, vr0) else c1

    mesh = bpy.data.meshes.new(cfg["name"] + "_hero")
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(cfg["name"] + "_hero", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def emission_vcol_material():
    mat = bpy.data.materials.new("card_emit")
    mat.use_nodes = True
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    emi = nt.nodes.new('ShaderNodeEmission')
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = "Color"
    nt.links.new(vc.outputs['Color'], emi.inputs['Color'])
    nt.links.new(emi.outputs['Emission'], out.inputs['Surface'])
    return mat


def render_card(obj, cfg, png_path):
    """Ortho side-on render of the hero clump to an RGBA card (transparent bg)."""
    scene = bpy.context.scene
    # frame the geometry bbox: X width, Z height (base at Z=0)
    xs = [v.co.x for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    half_w = max(max(xs), -min(xs)) * 1.06
    top = max(zs) * 1.04
    Wc = half_w * 2.0
    Hc = top
    res = cfg["res"]
    res_y = max(8, int(round(res * Hc / Wc)))

    # camera: ortho, looking +Y, centred on (0, Hc/2)
    cam_data = bpy.data.cameras.new("card_cam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = Wc
    cam_data.sensor_fit = 'HORIZONTAL'
    cam = bpy.data.objects.new("card_cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, -5.0, Hc * 0.5)
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)  # look +Y, Z stays up
    scene.camera = cam

    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    try:
        scene.eevee.taa_render_samples = 64
    except Exception:
        pass
    scene.render.film_transparent = True
    scene.render.resolution_x = res
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = png_path
    bpy.ops.render.render(write_still=True)

    bpy.data.objects.remove(cam, do_unlink=True)
    return Wc, Hc


def build_card_glb(cfg, png_path, Wc, Hc, glb_path):
    """3 crossed quads wearing the rendered card texture, exported as GLB."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UV")
    hw = Wc * 0.5
    for a_deg in (0.0, 60.0, 120.0):
        a = math.radians(a_deg)
        dx, dy = math.cos(a), math.sin(a)
        p0 = bm.verts.new((-dx * hw, -dy * hw, 0.0))
        p1 = bm.verts.new(( dx * hw,  dy * hw, 0.0))
        p2 = bm.verts.new(( dx * hw,  dy * hw, Hc))
        p3 = bm.verts.new((-dx * hw, -dy * hw, Hc))
        f = bm.faces.new([p0, p1, p2, p3])
        uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        for loop, c in zip(f.loops, uvs):
            loop[uv].uv = c

    mesh = bpy.data.meshes.new(cfg["name"])
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(cfg["name"], mesh)
    bpy.context.collection.objects.link(obj)

    # material with the rendered card as base colour + alpha
    img = bpy.data.images.load(png_path)
    mat = bpy.data.materials.new(cfg["name"] + "_mat")
    mat.use_nodes = True
    mat.use_backface_culling = False
    # blend_method / shadow_method were removed from Material in Blender 4.2+
    # (EEVEE-Next). They don't affect the GLB→Godot path anyway (the game uses
    # its own render shader; Godot keeps the RGBA texture's alpha regardless),
    # so set them only if the running Blender still exposes them.
    for _attr, _val in (("blend_method", 'HASHED'), ("shadow_method", 'HASHED')):
        if hasattr(mat, _attr):
            setattr(mat, _attr, _val)
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.5
    texn = nt.nodes.new('ShaderNodeTexImage'); texn.image = img
    nt.links.new(texn.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(texn.outputs['Alpha'], bsdf.inputs['Alpha'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    obj.data.materials.append(mat)

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=glb_path, export_format='GLB', use_selection=True,
        export_normals=True, export_apply=True,
    )
    return len(mesh.polygons)


# --- clear scene ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

print("Building %d grass cluster cards..." % len(CARDS))
for cfg in CARDS:
    # clean slate each card
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    hero = build_clump(cfg)
    hero.data.materials.append(emission_vcol_material())

    png_path = os.path.join(TEX_DIR, cfg["name"] + "_card.png")
    Wc, Hc = render_card(hero, cfg, png_path)

    # remove hero before building the card mesh
    bpy.data.objects.remove(hero, do_unlink=True)

    glb_path = os.path.join(GLB_DIR, cfg["name"] + ".glb")
    tris = build_card_glb(cfg, png_path, Wc, Hc, glb_path)
    print("  %s: %d blades -> card %.2fx%.2fm, %d quads tris -> %s + %s" % (
        cfg["name"], cfg["blades"], Wc, Hc, tris, glb_path, png_path))

print("Done.")

"""Build grass CLUMP meshes — one per zone type.

Each mesh is a DENSE tuft of many fine, sharp-tipped blades fanned into a
rounded dome, modelled on the reference tuft pucks in
`reference_photos/fantasy grass/` (Everybody's Gone to the Rapture / Witcher 3
look). One clump = one GPU particle, so a lawn of overlapping clumps reads as a
continuous lush sward — NOT the isolated single-blade "spikes" (Mario-64) Chris
rejected. Sharp tips are fine here precisely BECAUSE the blades are dense;
spikiness was a symptom of sparsity, not of pointed blades.

Per-biome character:
  Blade_Lawn  — dense, short, near-even height (mown turf), low dome
  Blade_Wild  — tall clumpy bunch grass, strong dome + outward splay
  Blade_Shade — soft medium fescue, gentle
  Blade_Sedge — upright dense fan, waterside

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

# Hundreds-of-blades dense tufts (2026-06-28, rev 3). blades-per-clump is up
# ~5-8x from rev 2; the GRASS_BIOMES `spacing` in main.gd is widened to match so
# the per-m² triangle budget stays roughly flat (fewer, far denser tufts).
# base/tip_rgb are doc-only — render colour comes from the zone/fantasy palette.
BLADE_TYPES = [
    {   # Kentucky Bluegrass (Poa pratensis) — lush tended lawn
        "name": "Blade_Lawn",
        "segments": 3,
        "height": 0.11,
        "width": 0.022,
        "arch": 0.018,
        "blades": 44,
        "clump_radius": 0.085,
        "dome": 0.28,          # how much taller the centre is than the rim
        "splay": 0.35,         # outward lean of rim blades (fountain)
        "height_var": 0.30,    # per-blade height jitter
        "flag_frac": 0.08,     # fraction of blades that shoot up tall
        "base_rgb": (0.37, 0.44, 0.38),
        "tip_rgb": (0.23, 0.40, 0.24),
    },
    {   # Switchgrass (Panicum virgatum) — tall meadow bunch grass
        "name": "Blade_Wild",
        "segments": 4,
        "height": 0.30,
        "width": 0.026,
        "arch": 0.11,
        "blades": 40,
        "clump_radius": 0.075,
        "dome": 0.55,
        "splay": 0.60,
        "height_var": 0.40,
        "flag_frac": 0.16,
        "base_rgb": (0.41, 0.46, 0.41),
        "tip_rgb": (0.28, 0.41, 0.24),
    },
    {   # Fine Fescue (Festuca rubra) — soft woodland
        "name": "Blade_Shade",
        "segments": 3,
        "height": 0.15,
        "width": 0.018,
        "arch": 0.06,
        "blades": 40,
        "clump_radius": 0.075,
        "dome": 0.35,
        "splay": 0.45,
        "height_var": 0.35,
        "flag_frac": 0.10,
        "base_rgb": (0.36, 0.42, 0.36),
        "tip_rgb": (0.22, 0.37, 0.22),
    },
    {   # Tussock Sedge (Carex stricta) — waterside upright fan
        "name": "Blade_Sedge",
        "segments": 3,
        "height": 0.19,
        "width": 0.020,
        "arch": 0.05,
        "blades": 38,
        "clump_radius": 0.065,
        "dome": 0.40,
        "splay": 0.30,
        "height_var": 0.35,
        "flag_frac": 0.12,
        "base_rgb": (0.35, 0.41, 0.35),
        "tip_rgb": (0.22, 0.36, 0.21),
    },
]

GOLDEN = math.pi * (3.0 - math.sqrt(5.0))  # 2.39996 rad — even disk fill


def _frac(n):
    """Deterministic [0,1) pseudo-noise from an int (no RNG → reproducible)."""
    return (math.sin(n * 12.9898) * 43758.5453) % 1.0


def make_blade(cfg):
    """One dense grass CLUMP. N fine sharp-tipped blades fanned into a dome:
    even disk fill (golden spiral), height falls off toward the rim (dome) with
    per-blade jitter, blades lean+arc outward (fountain splay), a few 'flag'
    blades shoot up tall. UV.y stays 0=base→1=tip per blade so the render
    shader's wind bend + root→tip gradient still work."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UV")
    color_layer = bm.loops.layers.color.new("Color")

    segments = cfg["segments"]
    height = cfg["height"]
    width = cfg["width"]
    arch = cfg["arch"]
    base_rgb = cfg["base_rgb"]
    tip_rgb = cfg["tip_rgb"]
    n_blades = cfg["blades"]
    clump_radius = cfg["clump_radius"]
    dome = cfg.get("dome", 0.3)
    splay = cfg.get("splay", 0.4)
    height_var = cfg.get("height_var", 0.3)
    flag_frac = cfg.get("flag_frac", 0.1)

    for bi in range(n_blades):
        ang = bi * GOLDEN
        frac = (bi + 0.5) / n_blades          # 0=centre → ~1=rim
        rad = clump_radius * math.sqrt(frac)
        bx, by = rad * math.cos(ang), rad * math.sin(ang)

        # Dome: centre blades tallest, rim shortest; plus per-blade jitter and a
        # few tall "flag" blades poking out of the canopy.
        n1 = _frac(bi * 7 + 3)
        n2 = _frac(bi * 13 + 11)
        dome_h = 1.0 - dome * frac
        jitter = 1.0 + (n1 - 0.5) * 2.0 * height_var
        flag = 1.0 + (0.55 if n2 < flag_frac else 0.0)
        hvar = max(0.35, dome_h * jitter * flag)

        # Blades lean OUTWARD from the clump centre (fountain), more at the rim.
        out_yaw = math.atan2(by, bx) if rad > 1e-5 else ang
        twist = (n1 - 0.5) * 1.4            # per-blade yaw scatter
        yaw = out_yaw + twist
        lean = splay * frac                  # rim blades splay more
        fwd = (math.cos(yaw), math.sin(yaw))
        side = (-math.sin(yaw), math.cos(yaw))

        vert_pairs = []
        for si in range(segments + 1):
            t = si / segments
            # outward travel: arch curve + linear splay lean
            along = (arch * t * t + height * lean * t) * hvar
            up = height * hvar * (t - 0.10 * t * t)
            # taper toward a fine tip but keep body width through the mid-blade
            # so each blade covers ground (razor-thin blades vanish into terrain
            # at grazing angles no matter how many there are).
            hw = width * (1.0 - t) ** 0.7 * 0.5 + width * 0.06
            cx = bx + fwd[0] * along
            cy = by + fwd[1] * along
            vl = bm.verts.new((cx + side[0] * hw, cy + side[1] * hw, up))
            vr = bm.verts.new((cx - side[0] * hw, cy - side[1] * hw, up))
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

print(f"Building {len(BLADE_TYPES)} grass clump meshes...")

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
    print(f"  {cfg['name']}: {cfg['blades']} blades, {vc} verts, {fc} faces -> {filepath}")
    bpy.ops.object.delete(use_global=False)

print("Done.")

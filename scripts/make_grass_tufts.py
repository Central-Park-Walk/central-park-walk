"""Generate grass tuft meshes for Central Park Walk GPU particle system.

Run: python3 scripts/make_grass_tufts.py

Standard game grass technique: 3-4 crossed quad cards per tuft, each card
textured with multiple blade silhouettes via alpha mask. Cards arranged in
star/X pattern so the tuft reads from any viewing angle. This is the same
approach used by EGTTR, Unreal Engine foliage, and Unity grass.

Phase 1 (system Python + PIL): Generate blade-cluster textures.
Phase 2 (Blender): Generate crossed-card meshes with embedded textures.

All models MIT-licensed, generated from scratch.
"""

import math
import os
import random
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(PROJ, "models", "vegetation")
TEX_DIR = os.path.join(PROJ, "textures", "grass")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TEX_DIR, exist_ok=True)

# EGTTR-inspired palette, ~3x scale for visual legibility at eye height.
# Each zone has a distinct color identity.
TUFTS = {
    "Tuft_Tiny": {
        # Maintained lawn: warm yellow-green, sunlit English lawn
        "h": 0.15, "card_w": 0.18, "n_cards": 3,
        "n_blades_per_card": 7, "segs": 3,
        "curve": 0.15, "droop": 0.06,
        "color": (88, 120, 52), "tip_color": (115, 142, 65),
        "dark_color": (62, 88, 38),
        "blade_shape": "broad",
    },
    "Tuft_Woodland": {
        # Shade floor: deep muted olive, cool under canopy
        "h": 0.22, "card_w": 0.16, "n_cards": 3,
        "n_blades_per_card": 5, "segs": 4,
        "curve": 0.25, "droop": 0.12,
        "color": (48, 72, 38), "tip_color": (62, 88, 45),
        "dark_color": (35, 55, 28),
        "blade_shape": "needle",
    },
    "Tuft_Wild": {
        # Wild meadow: golden-green, hay undertones, sun-bleached tips
        "h": 0.45, "card_w": 0.22, "n_cards": 4,
        "n_blades_per_card": 5, "segs": 5,
        "curve": 0.35, "droop": 0.18,
        "color": (95, 110, 48), "tip_color": (130, 135, 68),
        "dark_color": (70, 82, 35),
        "blade_shape": "broad",
    },
    "Tuft_Meadow": {
        # Waterside sedge: cool grey-green, damp wetland
        "h": 0.32, "card_w": 0.18, "n_cards": 4,
        "n_blades_per_card": 6, "segs": 5,
        "curve": 0.40, "droop": 0.22,
        "color": (55, 85, 48), "tip_color": (72, 105, 58),
        "dark_color": (40, 62, 35),
        "blade_shape": "arch",
    },
}

TEX_W, TEX_H = 256, 512


# ─── Phase 1: Texture generation ─────────────────────────────────────────

def make_blade_cluster_texture(name, spec):
    """Generate a texture showing multiple grass blade silhouettes.

    Each card texture shows N blades side-by-side with slight variation
    in height, width, lean, and color. Alpha mask creates the silhouette.
    """
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np

    rng = np.random.RandomState(abs(hash(name)) % (2**31))
    img = Image.new('RGBA', (TEX_W, TEX_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    n_blades = spec["n_blades_per_card"]
    r0, g0, b0 = spec["color"]
    r1, g1, b1 = spec["tip_color"]
    rd, gd, bd = spec["dark_color"]
    shape = spec["blade_shape"]

    for bi in range(n_blades):
        # Distribute blades across card width
        cx = int(TEX_W * (0.08 + 0.84 * bi / max(1, n_blades - 1)))
        # Random offset
        cx += rng.randint(-8, 9)

        # Blade dimensions (in pixels)
        blade_h = int(TEX_H * rng.uniform(0.55, 0.95))
        if shape == "needle":
            blade_w = int(TEX_W * rng.uniform(0.04, 0.07))
        elif shape == "arch":
            blade_w = int(TEX_W * rng.uniform(0.06, 0.10))
        else:  # broad
            blade_w = int(TEX_W * rng.uniform(0.07, 0.12))

        # Lean direction
        lean_px = int(rng.uniform(-15, 15))

        # Draw blade as a series of horizontal slices (bottom to top)
        base_y = TEX_H - 1
        for y_off in range(blade_h):
            t = y_off / blade_h  # 0=base, 1=tip
            y = base_y - y_off

            # Width tapers toward tip
            w = blade_w * (1.0 - t * 0.85)
            # Lean accumulates toward tip
            lean = int(lean_px * t * t)
            # Slight wave
            wave = int(3 * math.sin(t * 8 + bi * 1.7))

            x_center = cx + lean + wave
            x0 = max(0, int(x_center - w / 2))
            x1 = min(TEX_W - 1, int(x_center + w / 2))

            if x1 <= x0:
                continue

            # Color: gradient base->tip with per-blade variation
            color_var = rng.uniform(-0.08, 0.08)
            # Mix in dark color near base, bright toward tip
            base_mix = max(0, 1.0 - t * 2)  # dark near base
            r = int(rd * base_mix + (r0 + (r1 - r0) * t) * (1 - base_mix))
            g = int(gd * base_mix + (g0 + (g1 - g0) * t) * (1 - base_mix))
            b = int(bd * base_mix + (b0 + (b1 - b0) * t) * (1 - base_mix))

            # Per-blade hue shift
            r = max(0, min(255, int(r * (1 + color_var))))
            g = max(0, min(255, int(g * (1 + color_var * 0.5))))
            b = max(0, min(255, int(b * (1 + color_var))))

            # Midrib (slightly darker center line)
            for x in range(x0, x1 + 1):
                dx = abs(x - x_center)
                # Edge softness
                edge_dist = dx / max(1, w / 2)
                if edge_dist > 0.8:
                    alpha = int(255 * (1.0 - (edge_dist - 0.8) / 0.2))
                else:
                    alpha = 255

                if dx < 1.5:
                    # Midrib
                    pr = max(0, r - 18)
                    pg = max(0, g - 12)
                    pb = max(0, b - 10)
                else:
                    pr, pg, pb = r, g, b

                img.putpixel((x, y), (pr, pg, pb, alpha))

    # Slight blur for anti-aliasing
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
    img.save(tex_path)
    print(f"  Texture: {tex_path} ({TEX_W}x{TEX_H}, {n_blades} blades)")
    return tex_path


def generate_all_textures():
    print("=== Generating grass blade cluster textures ===")
    for name, spec in TUFTS.items():
        make_blade_cluster_texture(name, spec)
    print("=== Textures done ===\n")


# ─── Phase 2: Mesh generation (Blender) ──────────────────────────────────

def clear_scene():
    import bpy
    bpy.ops.wm.read_homefile(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def make_crossed_cards(name, spec, tex_path):
    """Create a tuft as crossed quad cards — the standard game grass approach.

    N_CARDS quads arranged in a star pattern (evenly rotated around Y axis).
    Each quad is a vertical strip that bows outward slightly, showing the
    blade cluster texture with alpha. From any viewing angle, at least one
    card faces the camera.
    """
    import bpy, bmesh

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.verify()

    h = spec["h"]
    card_w = spec["card_w"]
    n_cards = spec["n_cards"]
    segs = spec["segs"]
    curve = spec["curve"]
    droop = spec["droop"]
    rng = random.Random(hash(name))

    for ci in range(n_cards):
        # Rotate each card evenly around Y
        angle = math.pi * ci / n_cards  # 0, 60, 120 for 3 cards; 0, 45, 90, 135 for 4
        # Slight random offset to break symmetry
        angle += rng.uniform(-0.15, 0.15)

        dx = math.cos(angle)
        dz = math.sin(angle)
        # Perpendicular for card width
        px = -dz * card_w * 0.5
        pz = dx * card_w * 0.5

        # Per-card height/curve variation
        ch = h * rng.uniform(0.85, 1.15)
        cc = curve * rng.uniform(0.7, 1.3)
        cd = droop * rng.uniform(0.7, 1.3)
        seg_h = ch / segs

        left_verts = []
        right_verts = []

        for si in range(segs + 1):
            t = si / segs  # 0=base, 1=tip
            y = seg_h * si - cd * t * t * ch
            # Slight outward bow at mid-height
            bow = cc * math.sin(t * math.pi) * 0.03

            vl = bm.verts.new((px + dx * bow, y, pz + dz * bow))
            vr = bm.verts.new((-px + dx * bow, y, -pz + dz * bow))
            left_verts.append((vl, t))
            right_verts.append((vr, t))

        # Create faces
        for si in range(segs):
            vl0, t0 = left_verts[si]
            vr0, _ = right_verts[si]
            vl1, t1 = left_verts[si + 1]
            vr1, _ = right_verts[si + 1]

            try:
                f1 = bm.faces.new([vl0, vr0, vr1, vl1])
                for loop in f1.loops:
                    v = loop.vert
                    for vv, vt in left_verts:
                        if v == vv:
                            loop[uv_layer].uv = (0.0, vt)
                            break
                    else:
                        for vv, vt in right_verts:
                            if v == vv:
                                loop[uv_layer].uv = (1.0, vt)
                                break
            except ValueError:
                pass

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Material with alpha-scissor texture
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_backface_culling = False
    mat.blend_method = 'CLIP'
    mat.alpha_threshold = 0.4
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        nodes.remove(n)

    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex_node = nodes.new("ShaderNodeTexImage")

    tex_img = bpy.data.images.load(tex_path)
    tex_img.pack()
    tex_node.image = tex_img

    bsdf.inputs["Roughness"].default_value = 0.82
    bsdf.inputs["Specular IOR Level"].default_value = 0.12

    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    obj.data.materials.append(mat)
    return obj


def export_glb(obj, filepath):
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_image_format='AUTO',
        export_draco_mesh_compression_enable=False,
    )


def generate_all_meshes():
    print("=== Generating crossed-card grass tuft meshes ===")
    for name, spec in TUFTS.items():
        clear_scene()
        tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
        if not os.path.exists(tex_path):
            print(f"  SKIP {name}: texture not found")
            continue

        print(f"  {name}: {spec['h']*100:.0f}cm, {spec['n_cards']} cards × {spec['segs']} segs")
        obj = make_crossed_cards(name, spec, tex_path)
        vcount = len(obj.data.vertices)
        fcount = len(obj.data.polygons)
        print(f"    {vcount} verts, {fcount} faces")

        path = os.path.join(OUT_DIR, f"{name}.glb")
        export_glb(obj, path)
        size_kb = os.path.getsize(path) / 1024
        print(f"    -> {path} ({size_kb:.0f} KB)")

    print("\n=== All grass tufts generated ===")


# ─── Entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "bpy" in sys.modules:
        generate_all_meshes()
    else:
        generate_all_textures()
        import subprocess
        print("Launching Blender for mesh generation...")
        proc = subprocess.Popen(
            ["blender4", "--background", "--python", __file__],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout:
            line = line.rstrip()
            if any(k in line for k in ["===", "Tuft_", "verts", "->", "SKIP", "Error", "Traceback"]):
                print(line)
        proc.wait()
        try:
            proc.kill()
        except:
            pass
        print("\nDone.")

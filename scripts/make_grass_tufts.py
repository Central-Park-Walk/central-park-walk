"""Generate grass tuft meshes for Central Park Walk GPU particle system.

Run: python3 scripts/make_grass_tufts.py

Standard game grass technique: crossed quad cards per tuft, each card
textured with multiple blade silhouettes via alpha mask. Cards arranged in
star/X pattern so the tuft reads from any viewing angle.

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

# EGTTR-inspired palette. Each zone has a distinct color identity.
TUFTS = {
    "Tuft_Tiny": {
        # Maintained lawn: warm yellow-green, sunlit English lawn
        "h": 0.15, "card_w": 0.20, "n_cards": 4,
        "n_blades": 75, "n_stubs": 30, "segs": 3,
        "curve": 0.15, "droop": 0.06,
        "color": (88, 120, 52), "tip_color": (115, 142, 65),
        "dark_color": (62, 88, 38),
        "dead_color": (140, 120, 55), "dead_tip_color": (170, 148, 72),
        "blade_shape": "broad",
        "lean_range": 15,  # mostly upright — 3D comes from crossed cards, not blade angles
    },
    "Tuft_Woodland": {
        # Shade floor: deep muted olive, cool under canopy
        "h": 0.22, "card_w": 0.18, "n_cards": 4,
        "n_blades": 50, "n_stubs": 20, "segs": 4,
        "curve": 0.25, "droop": 0.12,
        "color": (48, 72, 38), "tip_color": (62, 88, 45),
        "dark_color": (35, 55, 28),
        "dead_color": (105, 92, 48), "dead_tip_color": (128, 112, 60),
        "blade_shape": "needle",
        "lean_range": 12,
    },
    "Tuft_Wild": {
        # Wild meadow: golden-green, hay undertones, sun-bleached tips
        "h": 0.45, "card_w": 0.24, "n_cards": 5,
        "n_blades": 55, "n_stubs": 20, "segs": 5,
        "curve": 0.35, "droop": 0.18,
        "color": (95, 110, 48), "tip_color": (130, 135, 68),
        "dark_color": (70, 82, 35),
        "dead_color": (148, 128, 58), "dead_tip_color": (175, 155, 78),
        "blade_shape": "broad",
        "lean_range": 20,  # wild grass leans a bit more
    },
    "Tuft_Meadow": {
        # Waterside sedge: cool grey-green, damp wetland
        "h": 0.32, "card_w": 0.20, "n_cards": 5,
        "n_blades": 52, "n_stubs": 20, "segs": 5,
        "curve": 0.40, "droop": 0.22,
        "color": (55, 85, 48), "tip_color": (72, 105, 58),
        "dark_color": (40, 62, 35),
        "dead_color": (112, 100, 52), "dead_tip_color": (138, 122, 65),
        "blade_shape": "arch",
        "lean_range": 18,
    },
}

TEX_W, TEX_H = 512, 1024


# ─── Phase 1: Texture generation ─────────────────────────────────────────

def draw_blade(img_arr, cx, base_y, blade_h, blade_w, lean_deg, curve_str,
               color_base, color_tip, color_dark, color_var, rng):
    """Draw a single thin grass blade as an anti-aliased curved strip.

    Blades are drawn into a numpy RGBA array for speed. Each blade is thin
    (2-6px), curves via sine, and leans at a random angle. The base-to-tip
    gradient runs along the blade's arc, not just vertically.
    """
    import numpy as np

    h, w = img_arr.shape[:2]
    lean_rad = math.radians(lean_deg)

    # Blade curvature: mostly straight with gentle arc, not wildly wavy
    curve_freq = rng.uniform(0.5, 1.5)
    curve_phase = rng.uniform(0, math.pi * 2)
    curve_amp = curve_str * blade_h * 0.06

    for step in range(blade_h):
        t = step / max(1, blade_h - 1)  # 0=base, 1=tip
        y = base_y - step

        if y < 0 or y >= h:
            continue

        # Width tapers: full at base, thin at tip
        tw = blade_w * (1.0 - t ** 1.5 * 0.85)
        tw = max(0.5, tw)

        # Position: lean + curve
        lean_offset = math.sin(lean_rad) * step
        curve_offset = math.sin(t * curve_freq * math.pi + curve_phase) * curve_amp * t
        x_center = cx + lean_offset + curve_offset

        # Color gradient base->tip
        base_mix = max(0, 1.0 - t * 3.0)
        r = int(color_dark[0] * base_mix + (color_base[0] + (color_tip[0] - color_base[0]) * t) * (1 - base_mix))
        g = int(color_dark[1] * base_mix + (color_base[1] + (color_tip[1] - color_base[1]) * t) * (1 - base_mix))
        b = int(color_dark[2] * base_mix + (color_base[2] + (color_tip[2] - color_base[2]) * t) * (1 - base_mix))

        # Per-blade color variation
        r = max(0, min(255, int(r * (1 + color_var))))
        g = max(0, min(255, int(g * (1 + color_var * 0.6))))
        b = max(0, min(255, int(b * (1 + color_var * 1.2))))

        # Midrib highlight at center
        half_w = max(0.5, tw / 2)

        x_start = max(0, int(x_center - half_w))
        x_end = min(w - 1, int(x_center + half_w))

        for x in range(x_start, x_end + 1):
            dx = abs(x - x_center)
            edge_t = dx / half_w

            # Anti-aliased edge: soft falloff
            if edge_t > 0.5:
                alpha = int(255 * max(0, 1.0 - (edge_t - 0.5) / 0.5))
            else:
                alpha = 255

            # Midrib: lighter center line
            if dx < 1.0:
                pr = min(255, r + 15)
                pg = min(255, g + 10)
                pb = min(255, b + 6)
            else:
                pr, pg, pb = r, g, b

            if alpha <= 0:
                continue

            # Alpha-composite onto existing
            ea = img_arr[y, x, 3] / 255.0
            na = alpha / 255.0
            out_a = na + ea * (1 - na)
            if out_a > 0.001:
                out_r = int((pr * na + img_arr[y, x, 0] * ea * (1 - na)) / out_a)
                out_g = int((pg * na + img_arr[y, x, 1] * ea * (1 - na)) / out_a)
                out_b = int((pb * na + img_arr[y, x, 2] * ea * (1 - na)) / out_a)
                img_arr[y, x] = [out_r, out_g, out_b, int(out_a * 255)]


def make_blade_cluster_texture(name, spec):
    """Generate a dense grass blade cluster texture.

    Key design: many thin, overlapping blades at varied angles — NOT a few
    wide leaf shapes. The base is a dense thatch mass; individual blades only
    become distinct at their tips. Mimics the style of proven game grass
    card textures (GrassCard_Lawn, etc).
    """
    from PIL import Image, ImageFilter
    import numpy as np

    rng = np.random.RandomState(abs(hash(name)) % (2**31))
    img_arr = np.zeros((TEX_H, TEX_W, 4), dtype=np.uint8)

    n_blades = spec["n_blades"]
    r0, g0, b0 = spec["color"]
    r1, g1, b1 = spec["tip_color"]
    rd, gd, bd = spec["dark_color"]
    dr0, dg0, db0 = spec["dead_color"]
    dr1, dg1, db1 = spec["dead_tip_color"]
    shape = spec["blade_shape"]
    lean_range = spec["lean_range"]

    # Draw short stub blades at the base for thatch density
    n_stubs = spec.get("n_stubs", 15)
    for si in range(n_stubs):
        cx = int(TEX_W * 0.5 + rng.normal(0, TEX_W * 0.28))
        cx = max(5, min(TEX_W - 5, cx))
        stub_h = int(TEX_H * rng.uniform(0.05, 0.25))
        stub_w = rng.uniform(4.0, 9.0)
        stub_lean = rng.uniform(-20, 20)  # stubs lean a bit more (thatch)
        stub_var = rng.uniform(-0.15, 0.15)
        # Stubs are darker — thatch layer
        stub_dark = (int(rd * 0.8), int(gd * 0.8), int(bd * 0.7))
        stub_base = (int(r0 * 0.7), int(g0 * 0.7), int(b0 * 0.6))
        draw_blade(img_arr, cx, TEX_H - 1, stub_h, stub_w, stub_lean, 0.3,
                   stub_base, stub_base, stub_dark, stub_var, rng)

    # Sort blades: draw back-leaning first, front-leaning last (depth order)
    blade_params = []
    for bi in range(n_blades):
        is_dead = rng.random() < 0.12  # 12% dead blades

        # Spread blades across the full card width
        cx = int(TEX_W * 0.5 + rng.normal(0, TEX_W * 0.25))
        cx = max(8, min(TEX_W - 8, cx))

        # Height: varies widely, some blades reach nearly full card height
        blade_h = int(TEX_H * rng.uniform(0.30, 0.92))

        # Width: moderate — visible leaf surface, but not fat leaf shapes.
        # At 512px canvas, 6-12px ≈ 2-4mm real blade width on an 18cm card.
        if shape == "needle":
            blade_w = rng.uniform(5.0, 9.0)
        elif shape == "arch":
            blade_w = rng.uniform(6.0, 11.0)
        else:  # broad
            blade_w = rng.uniform(7.0, 12.0)

        # Lean: wide range, creating the crossing pattern that reads as grass
        lean_deg = rng.uniform(-lean_range, lean_range)

        # Curve strength
        curve_str = rng.uniform(0.3, 2.0)

        # Color variation per blade (±18%)
        color_var = rng.uniform(-0.18, 0.18)

        if is_dead:
            c_base = (dr0, dg0, db0)
            c_tip = (dr1, dg1, db1)
            c_dark = (int(dr0 * 0.65), int(dg0 * 0.6), int(db0 * 0.5))
        else:
            c_base = (r0, g0, b0)
            c_tip = (r1, g1, b1)
            c_dark = (rd, gd, bd)

        blade_params.append((cx, blade_h, blade_w, lean_deg, curve_str,
                             c_base, c_tip, c_dark, color_var))

    # Sort by absolute lean (upright blades drawn first = behind)
    blade_params.sort(key=lambda p: abs(p[3]))

    base_y = TEX_H - 1
    for cx, blade_h, blade_w, lean_deg, curve_str, c_base, c_tip, c_dark, color_var in blade_params:
        draw_blade(img_arr, cx, base_y, blade_h, blade_w, lean_deg, curve_str,
                   c_base, c_tip, c_dark, color_var, rng)

    # Convert to PIL and apply light blur for AA
    img = Image.fromarray(img_arr, 'RGBA')
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
    img.save(tex_path)

    # Report fill percentage
    arr = np.array(img)
    fill_pct = (arr[:, :, 3] > 10).sum() / (TEX_W * TEX_H) * 100
    print(f"  Texture: {tex_path} ({TEX_W}x{TEX_H}, {n_blades} blades, {fill_pct:.1f}% fill)")
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
    blade cluster texture with alpha. Cards tilt off-vertical for organic feel.
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
        angle = math.pi * ci / n_cards
        # Slight random offset to break symmetry
        angle += rng.uniform(-0.18, 0.18)

        dx = math.cos(angle)
        dz = math.sin(angle)
        # Perpendicular for card width
        px = -dz * card_w * 0.5
        pz = dx * card_w * 0.5

        # Per-card height/curve variation — wider range
        ch = h * rng.uniform(0.75, 1.25)
        cc = curve * rng.uniform(0.6, 1.4)
        cd = droop * rng.uniform(0.6, 1.4)
        seg_h = ch / segs

        # Per-card tilt off vertical: lean outward 3-13 degrees
        tilt_angle = rng.uniform(0.05, 0.22)  # radians
        tilt_dx = dx * math.sin(tilt_angle)
        tilt_dz = dz * math.sin(tilt_angle)
        tilt_cos = math.cos(tilt_angle)

        left_verts = []
        right_verts = []

        for si in range(segs + 1):
            t = si / segs  # 0=base, 1=tip
            y = seg_h * si - cd * t * t * ch
            # Outward bow at mid-height
            bow = cc * math.sin(t * math.pi) * 0.07

            # Apply tilt
            tilt_x = tilt_dx * t * ch * 0.3
            tilt_z = tilt_dz * t * ch * 0.3
            y *= (tilt_cos + (1.0 - tilt_cos) * (1.0 - t))

            vl = bm.verts.new((px + dx * bow + tilt_x, y, pz + dz * bow + tilt_z))
            vr = bm.verts.new((-px + dx * bow + tilt_x, y, -pz + dz * bow + tilt_z))
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

        print(f"  {name}: {spec['h']*100:.0f}cm, {spec['n_cards']} cards x {spec['segs']} segs")
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

"""Generate grass tuft meshes for Central Park Walk GPU particle system.

Run: python3 scripts/make_grass_tufts.py

Standard game grass technique: 3 crossed quad cards per tuft, each card
textured with blade silhouettes via alpha mask. Cards arranged in star
pattern so the tuft reads from any viewing angle.

KEY DESIGN PRINCIPLE: Blades must be THIN. The crossed-card geometry
creates a visible rosette when card surfaces are filled. Keeping blades
thin (high transparency) hides the cards — you only see the grass
silhouettes. Variety comes from blade count, height, color, and dead
accents, NOT from making blades wider.

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

TUFTS = {
    "Tuft_Tiny": {
        # Maintained lawn: spectral KBG (Poa pratensis)
        "h": 0.12, "card_w": 0.40, "n_cards": 3,
        "n_blades": 24, "segs": 3,
        "curve": 0.15, "droop": 0.06,
        "color": (58, 102, 61), "tip_color": (76, 112, 78),
        "dark_color": (45, 80, 48),
        "dead_color": (111, 110, 77), "dead_tip_color": (123, 122, 85),
        "blade_shape": "broad",
    },
    "Tuft_Woodland": {
        # Shade floor: spectral Fine Fescue (Festuca rubra)
        "h": 0.18, "card_w": 0.55, "n_cards": 3,
        "n_blades": 18, "segs": 4,
        "curve": 0.25, "droop": 0.12,
        "color": (56, 94, 56), "tip_color": (74, 106, 74),
        "dark_color": (42, 72, 42),
        "dead_color": (100, 98, 70), "dead_tip_color": (111, 110, 77),
        "blade_shape": "needle",
    },
    "Tuft_Wild": {
        # Wild meadow: spectral Switchgrass (Panicum virgatum)
        "h": 0.40, "card_w": 0.60, "n_cards": 4,
        "n_blades": 18, "segs": 5,
        "curve": 0.35, "droop": 0.18,
        "color": (70, 105, 62), "tip_color": (88, 118, 82),
        "dark_color": (52, 82, 48),
        "dead_color": (123, 122, 85), "dead_tip_color": (140, 138, 95),
        "blade_shape": "broad",
    },
    "Tuft_Meadow": {
        # Waterside sedge: spectral Tussock Sedge (Carex stricta)
        "h": 0.28, "card_w": 0.55, "n_cards": 4,
        "n_blades": 20, "segs": 5,
        "curve": 0.40, "droop": 0.22,
        "color": (55, 92, 54), "tip_color": (72, 105, 72),
        "dark_color": (40, 70, 40),
        "dead_color": (100, 98, 68), "dead_tip_color": (111, 110, 77),
        "blade_shape": "arch",
    },
}

TEX_W, TEX_H = 256, 512


# ─── Phase 1: Texture generation ─────────────────────────────────────────

def make_blade_cluster_texture(name, spec):
    """Generate a blade cluster texture with thin, varied blades.

    Blades are thin enough that the crossed-card geometry remains invisible.
    Variety comes from blade count, height, lean, color shifts, and dead
    blade accents — NOT from blade width.
    """
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np

    rng = np.random.RandomState(abs(hash(name)) % (2**31))
    img = Image.new('RGBA', (TEX_W, TEX_H), (0, 0, 0, 0))

    n_blades = spec["n_blades"]
    r0, g0, b0 = spec["color"]
    r1, g1, b1 = spec["tip_color"]
    rd, gd, bd = spec["dark_color"]
    dr0, dg0, db0 = spec["dead_color"]
    dr1, dg1, db1 = spec["dead_tip_color"]
    shape = spec["blade_shape"]

    # Convert to numpy array for fast pixel access
    img_arr = np.array(img)

    for bi in range(n_blades):
        is_dead = rng.random() < 0.12

        # Distribute blades across card width with jitter
        cx = int(TEX_W * (0.08 + 0.84 * bi / max(1, n_blades - 1)))
        cx += rng.randint(-10, 11)

        # Blade height: wide variation
        blade_h = int(TEX_H * rng.uniform(0.40, 0.92))

        # Blade width: THIN — this is critical for hiding card geometry.
        # At 256px canvas, 8-16px creates a blade that's just barely visible
        # as a silhouette, not as a filled surface.
        if shape == "needle":
            blade_w_base = rng.uniform(6, 12)
        elif shape == "arch":
            blade_w_base = rng.uniform(8, 14)
        else:  # broad
            blade_w_base = rng.uniform(9, 16)

        # Lean: subtle, mostly vertical (±10-15 degrees)
        lean_px = int(rng.uniform(-18, 18))

        # Gentle curve
        curve_amp = rng.uniform(1, 4)
        curve_freq = rng.uniform(5, 10)
        curve_phase = rng.uniform(0, math.pi * 2)

        # Per-blade color variation (±15%)
        color_var = rng.uniform(-0.15, 0.15)

        if is_dead:
            cr0, cg0, cb0 = dr0, dg0, db0
            cr1, cg1, cb1 = dr1, dg1, db1
            crd, cgd, cbd = int(dr0 * 0.65), int(dg0 * 0.6), int(db0 * 0.5)
        else:
            cr0, cg0, cb0 = r0, g0, b0
            cr1, cg1, cb1 = r1, g1, b1
            crd, cgd, cbd = rd, gd, bd

        base_y = TEX_H - 1
        for y_off in range(blade_h):
            t = y_off / blade_h  # 0=base, 1=tip
            y = base_y - y_off

            if y < 0 or y >= TEX_H:
                continue

            # Taper: narrows toward tip
            w = blade_w_base * (1.0 - t * 0.85)

            # Lean + gentle wave
            lean = int(lean_px * t * t)
            wave = int(curve_amp * math.sin(t * curve_freq + curve_phase))
            x_center = cx + lean + wave

            # Color gradient base→tip
            base_mix = max(0, 1.0 - t * 2.5)
            r = int(crd * base_mix + (cr0 + (cr1 - cr0) * t) * (1 - base_mix))
            g = int(cgd * base_mix + (cg0 + (cg1 - cg0) * t) * (1 - base_mix))
            b = int(cbd * base_mix + (cb0 + (cb1 - cb0) * t) * (1 - base_mix))

            r = max(0, min(255, int(r * (1 + color_var))))
            g = max(0, min(255, int(g * (1 + color_var * 0.5))))
            b = max(0, min(255, int(b * (1 + color_var))))

            half_w = max(0.5, w / 2)
            x0 = max(0, int(x_center - half_w))
            x1 = min(TEX_W - 1, int(x_center + half_w))

            for x in range(x0, x1 + 1):
                dx = abs(x - x_center)
                edge_dist = dx / half_w

                # Soft edges
                if edge_dist > 0.6:
                    alpha = int(255 * max(0, (1.0 - (edge_dist - 0.6) / 0.4)))
                else:
                    alpha = 255

                # Midrib: slightly darker center
                if dx < 1.5:
                    pr = max(0, r - 12)
                    pg = max(0, g - 8)
                    pb = max(0, b - 6)
                else:
                    pr, pg, pb = r, g, b

                if alpha > 0:
                    # Alpha composite
                    ea = img_arr[y, x, 3] / 255.0
                    na = alpha / 255.0
                    out_a = na + ea * (1 - na)
                    if out_a > 0.001:
                        out_r = int((pr * na + img_arr[y, x, 0] * ea * (1 - na)) / out_a)
                        out_g = int((pg * na + img_arr[y, x, 1] * ea * (1 - na)) / out_a)
                        out_b = int((pb * na + img_arr[y, x, 2] * ea * (1 - na)) / out_a)
                        img_arr[y, x] = [out_r, out_g, out_b, int(out_a * 255)]

    img = Image.fromarray(img_arr, 'RGBA')
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
    img.save(tex_path)

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
    """Create a tuft as crossed quad cards."""
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
        angle = math.pi * ci / n_cards
        angle += rng.uniform(-0.15, 0.15)

        dx = math.cos(angle)
        dz = math.sin(angle)
        px = -dz * card_w * 0.5
        pz = dx * card_w * 0.5

        # Offset each card's center so blades don't all radiate from one point.
        # This breaks the rosette/cluster pattern that makes tufts individually
        # identifiable. Each card is shifted 3-8cm from the tuft origin.
        card_offset_dist = rng.uniform(0.03, 0.08)
        card_offset_angle = rng.uniform(0, math.pi * 2)
        card_ox = math.cos(card_offset_angle) * card_offset_dist
        card_oz = math.sin(card_offset_angle) * card_offset_dist

        ch = h * rng.uniform(0.85, 1.15)
        cc = curve * rng.uniform(0.7, 1.3)
        cd = droop * rng.uniform(0.7, 1.3)
        seg_h = ch / segs

        # Subtle per-card tilt: 3-8 degrees
        tilt_angle = rng.uniform(0.04, 0.14)
        tilt_dx = dx * math.sin(tilt_angle)
        tilt_dz = dz * math.sin(tilt_angle)
        tilt_cos = math.cos(tilt_angle)

        left_verts = []
        right_verts = []

        for si in range(segs + 1):
            t = si / segs
            y = seg_h * si - cd * t * t * ch
            bow = cc * math.sin(t * math.pi) * 0.03

            tilt_x = tilt_dx * t * ch * 0.2
            tilt_z = tilt_dz * t * ch * 0.2
            y *= (tilt_cos + (1.0 - tilt_cos) * (1.0 - t))

            vl = bm.verts.new((px + dx * bow + tilt_x + card_ox, y, pz + dz * bow + tilt_z + card_oz))
            vr = bm.verts.new((-px + dx * bow + tilt_x + card_ox, y, -pz + dz * bow + tilt_z + card_oz))
            left_verts.append((vl, t))
            right_verts.append((vr, t))

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

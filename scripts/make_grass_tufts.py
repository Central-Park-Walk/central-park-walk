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
        "h": 0.15, "card_w": 0.18, "n_cards": 4,
        "n_blades_per_card": 12, "segs": 3,
        "curve": 0.15, "droop": 0.06,
        "color": (88, 120, 52), "tip_color": (115, 142, 65),
        "dark_color": (62, 88, 38),
        "dead_color": (140, 120, 55), "dead_tip_color": (170, 148, 72),
        "blade_shape": "broad",
    },
    "Tuft_Woodland": {
        # Shade floor: deep muted olive, cool under canopy
        "h": 0.22, "card_w": 0.16, "n_cards": 4,
        "n_blades_per_card": 10, "segs": 4,
        "curve": 0.25, "droop": 0.12,
        "color": (48, 72, 38), "tip_color": (62, 88, 45),
        "dark_color": (35, 55, 28),
        "dead_color": (105, 92, 48), "dead_tip_color": (128, 112, 60),
        "blade_shape": "needle",
    },
    "Tuft_Wild": {
        # Wild meadow: golden-green, hay undertones, sun-bleached tips
        "h": 0.45, "card_w": 0.22, "n_cards": 5,
        "n_blades_per_card": 10, "segs": 5,
        "curve": 0.35, "droop": 0.18,
        "color": (95, 110, 48), "tip_color": (130, 135, 68),
        "dark_color": (70, 82, 35),
        "dead_color": (148, 128, 58), "dead_tip_color": (175, 155, 78),
        "blade_shape": "broad",
    },
    "Tuft_Meadow": {
        # Waterside sedge: cool grey-green, damp wetland
        "h": 0.32, "card_w": 0.18, "n_cards": 5,
        "n_blades_per_card": 11, "segs": 5,
        "curve": 0.40, "droop": 0.22,
        "color": (55, 85, 48), "tip_color": (72, 105, 58),
        "dark_color": (40, 62, 35),
        "dead_color": (112, 100, 52), "dead_tip_color": (138, 122, 65),
        "blade_shape": "arch",
    },
}

TEX_W, TEX_H = 512, 1024


# ─── Phase 1: Texture generation ─────────────────────────────────────────

def make_blade_cluster_texture(name, spec):
    """Generate a texture showing multiple grass blade silhouettes.

    Each card texture shows N blades side-by-side with variation in height,
    width, lean, color, and shape. Includes dead/dry blade accents and
    ground-level stub blades for density. Alpha mask creates the silhouette.
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
    dr0, dg0, db0 = spec["dead_color"]
    dr1, dg1, db1 = spec["dead_tip_color"]
    shape = spec["blade_shape"]

    # --- Draw ground-level stub blades first (behind main blades) ---
    n_stubs = 4
    for si in range(n_stubs):
        cx = int(TEX_W * (0.1 + 0.8 * si / max(1, n_stubs - 1)))
        cx += rng.randint(-20, 21)
        stub_h = int(TEX_H * rng.uniform(0.08, 0.20))
        stub_w = int(TEX_W * rng.uniform(0.04, 0.08))
        lean_px = int(rng.uniform(-25, 25))
        # Stubs are darker, brownish — thatch layer
        base_y = TEX_H - 1
        for y_off in range(stub_h):
            t = y_off / stub_h
            y = base_y - y_off
            w = stub_w * (1.0 - t * 0.7)
            lean = int(lean_px * t)
            x_center = cx + lean
            x0 = max(0, int(x_center - w / 2))
            x1 = min(TEX_W - 1, int(x_center + w / 2))
            if x1 <= x0:
                continue
            sr = int(rd * 0.7 + (r0 * 0.5) * t)
            sg = int(gd * 0.6 + (g0 * 0.4) * t)
            sb = int(bd * 0.5 + (b0 * 0.3) * t)
            alpha = int(255 * (1.0 - t * 0.3))
            for x in range(x0, x1 + 1):
                edge_dist = abs(x - x_center) / max(1, w / 2)
                a = alpha if edge_dist < 0.7 else int(alpha * (1.0 - (edge_dist - 0.7) / 0.3))
                a = max(0, min(255, a))
                img.putpixel((x, y), (sr, sg, sb, a))

    # --- Draw main blades ---
    for bi in range(n_blades):
        # Determine if this blade is dead/dry (15% chance)
        is_dead = rng.random() < 0.15

        # Distribute blades across card width with jitter
        cx = int(TEX_W * (0.06 + 0.88 * bi / max(1, n_blades - 1)))
        cx += rng.randint(-18, 19)

        # Blade dimensions — much wider than before
        blade_h = int(TEX_H * rng.uniform(0.50, 0.92))
        if shape == "needle":
            blade_w = int(TEX_W * rng.uniform(0.08, 0.14))
        elif shape == "arch":
            blade_w = int(TEX_W * rng.uniform(0.10, 0.17))
        else:  # broad
            blade_w = int(TEX_W * rng.uniform(0.12, 0.20))

        # Lean direction — more dramatic
        lean_px = int(rng.uniform(-35, 35))

        # Per-blade curve parameters for organic shape
        curve_freq = rng.uniform(4.0, 10.0)
        curve_amp = rng.uniform(2.0, 6.0)
        curve_phase = rng.uniform(0, math.pi * 2)

        # Tip curl: some blades curl over at the tip
        tip_curl = rng.uniform(0, 1.0)
        has_tip_curl = tip_curl > 0.6  # 40% of blades

        # Edge irregularity
        edge_wave_freq = rng.uniform(8.0, 18.0)
        edge_wave_amp = rng.uniform(0.5, 2.5)

        # Color selection
        if is_dead:
            br0, bg0, bb0 = dr0, dg0, db0
            br1, bg1, bb1 = dr1, dg1, db1
            brd, bgd, bbd = int(dr0 * 0.7), int(dg0 * 0.65), int(db0 * 0.5)
        else:
            br0, bg0, bb0 = r0, g0, b0
            br1, bg1, bb1 = r1, g1, b1
            brd, bgd, bbd = rd, gd, bd

        # Per-blade hue shift (wider range: ±15%)
        color_var = rng.uniform(-0.15, 0.15)

        # Draw blade as horizontal slices (bottom to top)
        base_y = TEX_H - 1
        for y_off in range(blade_h):
            t = y_off / blade_h  # 0=base, 1=tip
            y = base_y - y_off

            # Width tapers with organic curve (not linear)
            # Grass blades taper slowly then quickly at tip
            taper = 1.0 - (t ** 1.8) * 0.90
            w = blade_w * taper

            # Edge waviness for organic feel
            edge_var = math.sin(t * edge_wave_freq + curve_phase) * edge_wave_amp
            w += edge_var

            # Lean accumulates quadratically toward tip
            lean = int(lean_px * t * t)

            # Organic curve (S-curve or C-curve)
            wave = int(curve_amp * math.sin(t * curve_freq + curve_phase))

            # Tip curl: blade bends sideways sharply at top
            if has_tip_curl and t > 0.75:
                curl_t = (t - 0.75) / 0.25
                curl_dir = 1 if lean_px > 0 else -1
                wave += int(curl_dir * curl_t * curl_t * 12)

            x_center = cx + lean + wave
            x0 = max(0, int(x_center - w / 2))
            x1 = min(TEX_W - 1, int(x_center + w / 2))

            if x1 <= x0:
                continue

            # Color: gradient base->tip with dark base mix
            base_mix = max(0, 1.0 - t * 2.5)  # dark color near base
            cr = int(brd * base_mix + (br0 + (br1 - br0) * t) * (1 - base_mix))
            cg = int(bgd * base_mix + (bg0 + (bg1 - bg0) * t) * (1 - base_mix))
            cb = int(bbd * base_mix + (bb0 + (bb1 - bb0) * t) * (1 - base_mix))

            # Per-blade hue shift
            cr = max(0, min(255, int(cr * (1 + color_var))))
            cg = max(0, min(255, int(cg * (1 + color_var * 0.5))))
            cb = max(0, min(255, int(cb * (1 + color_var))))

            # Tip yellowing for living blades
            if not is_dead and t > 0.7:
                yellow_t = (t - 0.7) / 0.3
                cr = min(255, int(cr * (1 + yellow_t * 0.08)))
                cg = min(255, int(cg * (1 + yellow_t * 0.04)))

            for x in range(x0, x1 + 1):
                dx = abs(x - x_center)
                half_w = max(1, w / 2)

                # Soft alpha edges
                edge_dist = dx / half_w
                if edge_dist > 0.65:
                    alpha = int(255 * max(0, (1.0 - (edge_dist - 0.65) / 0.35)))
                else:
                    alpha = 255

                # Midrib: lighter highlight along center
                if dx < 2.0:
                    # Midrib highlight (lighter, slightly glossy)
                    pr = min(255, cr + 12)
                    pg = min(255, cg + 8)
                    pb = min(255, cb + 5)
                elif dx < 4.0:
                    # Near midrib: slightly darker (vein shadow)
                    pr = max(0, cr - 8)
                    pg = max(0, cg - 5)
                    pb = max(0, cb - 4)
                else:
                    pr, pg, pb = cr, cg, cb

                # Leaf surface micro-variation (subtle)
                surf_var = math.sin(x * 0.8 + y * 0.3) * 4
                pr = max(0, min(255, int(pr + surf_var)))
                pg = max(0, min(255, int(pg + surf_var * 0.7)))

                if alpha > 0:
                    # Alpha-composite over existing pixels
                    existing = img.getpixel((x, y))
                    if existing[3] > 0 and alpha < 255:
                        # Blend with existing
                        ea = existing[3] / 255.0
                        na = alpha / 255.0
                        out_a = na + ea * (1 - na)
                        if out_a > 0:
                            out_r = int((pr * na + existing[0] * ea * (1 - na)) / out_a)
                            out_g = int((pg * na + existing[1] * ea * (1 - na)) / out_a)
                            out_b = int((pb * na + existing[2] * ea * (1 - na)) / out_a)
                            img.putpixel((x, y), (out_r, out_g, out_b, int(out_a * 255)))
                    else:
                        img.putpixel((x, y), (pr, pg, pb, alpha))

    # Slight blur for anti-aliasing
    img = img.filter(ImageFilter.GaussianBlur(radius=0.7))

    tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
    img.save(tex_path)

    # Calculate alpha fill percentage
    import numpy as np
    arr = np.array(img)
    fill_pct = (arr[:, :, 3] > 10).sum() / (TEX_W * TEX_H) * 100
    print(f"  Texture: {tex_path} ({TEX_W}x{TEX_H}, {n_blades} blades + {n_stubs} stubs, {fill_pct:.1f}% fill)")
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

        # Per-card tilt off vertical: lean outward 5-15 degrees
        tilt_angle = rng.uniform(0.06, 0.22)  # radians (~3-13 degrees)
        # Tilt direction: outward from center (along card's facing direction)
        tilt_dx = dx * math.sin(tilt_angle)
        tilt_dz = dz * math.sin(tilt_angle)
        tilt_cos = math.cos(tilt_angle)

        left_verts = []
        right_verts = []

        for si in range(segs + 1):
            t = si / segs  # 0=base, 1=tip
            y = seg_h * si - cd * t * t * ch
            # Stronger outward bow at mid-height
            bow = cc * math.sin(t * math.pi) * 0.07

            # Apply tilt: shift position outward as height increases
            tilt_x = tilt_dx * t * ch * 0.3
            tilt_z = tilt_dz * t * ch * 0.3
            # Reduce height slightly due to tilt
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

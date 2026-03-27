"""Generate grass tuft meshes for Central Park Walk GPU particle system.

Run: python3 scripts/make_grass_tufts.py  (generates textures)
     blender4 --background --python scripts/make_grass_tufts.py  (generates GLBs)

If run with system Python, generates blade textures in textures/grass/.
If run inside Blender, generates GLB meshes using those textures.

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
        "h": 0.058, "bw": 0.007, "n_blades": 24, "spread": 0.17,
        "curve": 0.15, "droop": 0.05, "segs": 3,
        "color": (75, 140, 50), "tip_color": (90, 155, 55),
        "blade_shape": "broad",
    },
    "Tuft_Woodland": {
        "h": 0.10, "bw": 0.005, "n_blades": 18, "spread": 0.12,
        "curve": 0.25, "droop": 0.12, "segs": 4,
        "color": (55, 110, 40), "tip_color": (65, 120, 45),
        "blade_shape": "needle",
    },
    "Tuft_Wild": {
        "h": 0.26, "bw": 0.012, "n_blades": 14, "spread": 0.34,
        "curve": 0.35, "droop": 0.18, "segs": 5,
        "color": (70, 115, 45), "tip_color": (85, 130, 50),
        "blade_shape": "broad",
    },
    "Tuft_Meadow": {
        "h": 0.17, "bw": 0.010, "n_blades": 20, "spread": 0.14,
        "curve": 0.40, "droop": 0.22, "segs": 5,
        "color": (60, 110, 40), "tip_color": (72, 122, 45),
        "blade_shape": "arch",
    },
}

TEX_W, TEX_H = 128, 256


# ─── Phase 1: Texture generation (PIL, system Python) ────────────────────

def make_blade_texture(name, spec):
    """Generate a procedural grass blade albedo+alpha PNG."""
    from PIL import Image
    import numpy as np

    rng = np.random.RandomState(abs(hash(name)) % (2**31))
    img = np.zeros((TEX_H, TEX_W, 4), dtype=np.uint8)

    r0, g0, b0 = spec["color"]
    r1, g1, b1 = spec["tip_color"]
    shape = spec["blade_shape"]

    for y in range(TEX_H):
        ct = 1.0 - y / TEX_H  # 0=base(bottom), 1=tip(top)

        r = int(r0 + (r1 - r0) * ct)
        g = int(g0 + (g1 - g0) * ct)
        b = int(b0 + (b1 - b0) * ct)
        noise = rng.randint(-8, 9)
        r = max(0, min(255, r + noise))
        g = max(0, min(255, g + noise))
        b = max(0, min(255, b + noise))

        if shape == "needle":
            blade_half_w = 0.12 + 0.18 * (1.0 - ct)
        elif shape == "arch":
            mid = max(0, 1.0 - 4.0 * (ct - 0.4)**2) if 0.1 < ct < 0.7 else 0.0
            blade_half_w = 0.10 + 0.20 * (1.0 - ct) + 0.08 * mid
        else:
            blade_half_w = 0.15 + 0.25 * (1.0 - ct)

        wave = 0.03 * math.sin(ct * 12.0 + rng.uniform(0, 3.14))
        center = TEX_W / 2.0

        for x in range(TEX_W):
            dx = abs(x - center + wave * TEX_W) / TEX_W
            if dx < blade_half_w:
                edge_t = dx / blade_half_w
                alpha = int(255 * (1.0 - (edge_t - 0.85) / 0.15)) if edge_t > 0.85 else 255
                if dx < 0.02:
                    img[y, x] = [max(0, r-15), max(0, g-10), max(0, b-8), alpha]
                else:
                    img[y, x] = [r, g, b, alpha]

    pil_img = Image.fromarray(img, 'RGBA')
    tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
    pil_img.save(tex_path)
    print(f"  Texture: {tex_path}")
    return tex_path


def generate_all_textures():
    print("=== Generating grass blade textures ===")
    for name, spec in TUFTS.items():
        make_blade_texture(name, spec)
    print("=== Textures done ===\n")


# ─── Phase 2: Mesh generation (Blender) ──────────────────────────────────

def clear_scene():
    import bpy
    bpy.ops.wm.read_homefile(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def make_blade_card(bm, spec, rng, uv_layer):
    import bmesh
    h = spec["h"] * rng.uniform(0.7, 1.3)
    bw = spec["bw"] * rng.uniform(0.8, 1.2)
    segs = spec["segs"]
    curve = spec["curve"] * rng.uniform(0.5, 1.5)
    droop = spec["droop"] * rng.uniform(0.5, 1.5)
    spread = spec["spread"]

    dx = rng.gauss(0, spread * 0.25)
    dz = rng.gauss(0, spread * 0.25)
    rot = rng.uniform(0, 2 * math.pi)
    lean = rng.uniform(0.05, 0.30)

    seg_h = h / segs
    left_verts = []
    right_verts = []

    for i in range(segs + 1):
        t = i / segs
        w = bw * (1.0 - t * 0.9) * 0.5
        y = seg_h * i - droop * t * t * h
        outward = curve * t * t * h

        cx = dx + outward * math.cos(rot) + lean * math.cos(rot) * y * 0.3
        cz = dz + outward * math.sin(rot) + lean * math.sin(rot) * y * 0.3
        px = -math.sin(rot) * w
        pz = math.cos(rot) * w

        vl = bm.verts.new((cx + px, y, cz + pz))
        vr = bm.verts.new((cx - px, y, cz - pz))
        left_verts.append((vl, t))
        right_verts.append((vr, t))

    for i in range(segs):
        vl0, t0 = left_verts[i]
        vr0, _ = right_verts[i]
        vl1, t1 = left_verts[i + 1]
        vr1, _ = right_verts[i + 1]
        try:
            f1 = bm.faces.new([vl0, vr0, vr1])
            f2 = bm.faces.new([vl0, vr1, vl1])
            for f in [f1, f2]:
                for loop in f.loops:
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


def make_tuft(name, spec, tex_path):
    import bpy, bmesh
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.verify()
    rng = random.Random(hash(name))

    for _ in range(spec["n_blades"]):
        make_blade_card(bm, spec, rng, uv_layer)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Material with albedo texture + alpha
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_backface_culling = False
    mat.blend_method = 'CLIP'
    mat.alpha_threshold = 0.5
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

    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.15

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
    print("=== Generating grass tuft meshes ===")
    for name, spec in TUFTS.items():
        clear_scene()
        tex_path = os.path.join(TEX_DIR, f"{name}_blade.png")
        if not os.path.exists(tex_path):
            print(f"  SKIP {name}: texture not found at {tex_path}")
            print(f"  Run: python3 scripts/make_grass_tufts.py  (to generate textures first)")
            continue

        print(f"\n  {name}: {spec['h']*100:.1f}cm, {spec['n_blades']} blades, {spec['spread']*100:.0f}cm spread")
        obj = make_tuft(name, spec, tex_path)
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
        # Running inside Blender — generate meshes (textures must exist)
        generate_all_meshes()
    else:
        # Running with system Python — generate textures, then call Blender
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
        if proc.returncode not in (0, None):
            print(f"Blender exited with code {proc.returncode}")
        # Kill any hanging Blender
        try:
            proc.kill()
        except:
            pass
        print("\nDone. GLBs in models/vegetation/, textures in textures/grass/")

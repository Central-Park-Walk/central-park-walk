"""Generate grass tuft meshes for Central Park Walk GPU particle system.

Run: blender4 --background --python scripts/make_grass_tufts.py

Creates 4 tuft GLBs in models/vegetation/:
  Tuft_Tiny.glb     — Maintained lawn (KBG, 7.6cm, 2-3mm blades)
  Tuft_Woodland.glb  — Shade floor (Fine Fescue, 12cm, 1-1.5mm blades)
  Tuft_Wild.glb      — Wild meadow (Little Bluestem, 26cm, 3-5mm blades)
  Tuft_Meadow.glb    — Waterside sedge (Tussock Sedge, 17cm, 3-5mm blades)

Each tuft is a cluster of 3D triangular grass blades (NOT billboards).
Blades are thin tri strips with natural curve, random rotation/tilt.
Vertex color GREEN channel = normalized height (0=base, 1=tip) for wind.
UV.y = normalized height for shader effects.

Botanical reference:
  Kentucky Bluegrass (Poa pratensis): mowed 7.6cm, blade 2-3mm, dense carpet
  Fine Fescue (Festuca spp.): shade, 10-15cm unmowed, blade 1-1.5mm, needle-like
  Little Bluestem (Schizachyrium scoparium): bunchgrass 60-120cm, blade 3-5mm
  Tussock Sedge (Carex stricta): arching 30-100cm, blade 3-5mm, forms tussocks

All models MIT-licensed, generated from scratch.
"""

import bpy
import bmesh
import math
import os
import random

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)

# ─── Tuft specifications ───────────────────────────────────────────────────
# h = total height (m), bw = blade width (m), n_blades = count per tuft,
# spread = footprint radius (m), curve = blade curvature (0=straight, 1=full arc),
# droop = gravity droop factor, segs = segments per blade, color = summer RGB
TUFTS = {
    "Tuft_Tiny": {
        "h": 0.058, "bw": 0.0025, "n_blades": 14, "spread": 0.17,
        "curve": 0.15, "droop": 0.05, "segs": 3,
        "color": (0.29, 0.55, 0.20),  # vivid emerald (75, 140, 50)/255
        "tip_color": (0.35, 0.60, 0.22),  # slightly lighter tips
    },
    "Tuft_Woodland": {
        "h": 0.10, "bw": 0.0012, "n_blades": 10, "spread": 0.12,
        "curve": 0.20, "droop": 0.10, "segs": 4,
        "color": (0.22, 0.43, 0.16),  # darker shade green (55, 110, 40)/255
        "tip_color": (0.26, 0.48, 0.18),
    },
    "Tuft_Wild": {
        "h": 0.26, "bw": 0.004, "n_blades": 8, "spread": 0.34,
        "curve": 0.35, "droop": 0.15, "segs": 5,
        "color": (0.27, 0.45, 0.18),  # blue-green (70, 115, 45)/255
        "tip_color": (0.35, 0.50, 0.20),
    },
    "Tuft_Meadow": {
        "h": 0.17, "bw": 0.004, "n_blades": 12, "spread": 0.14,
        "curve": 0.40, "droop": 0.20, "segs": 5,
        "color": (0.24, 0.43, 0.16),  # medium green (60, 110, 40)/255
        "tip_color": (0.30, 0.48, 0.18),
    },
}


def clear_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def make_blade(bm, spec, rng):
    """Create a single grass blade as a tri strip in the bmesh.

    Each blade is a thin 3D strip with `segs` segments, curving outward
    and slightly drooping. Width tapers from base to tip.
    """
    h = spec["h"] * rng.uniform(0.7, 1.3)
    bw = spec["bw"] * rng.uniform(0.8, 1.2)
    segs = spec["segs"]
    curve = spec["curve"] * rng.uniform(0.5, 1.5)
    droop = spec["droop"] * rng.uniform(0.5, 1.5)

    # Random placement within tuft spread
    spread = spec["spread"]
    dx = rng.gauss(0, spread * 0.25)
    dz = rng.gauss(0, spread * 0.25)

    # Random outward lean angle and rotation
    lean = rng.uniform(0.05, 0.35)  # radians, outward lean
    rot = rng.uniform(0, 2 * math.pi)  # rotation around Y

    # Build vertices along the blade
    verts = []
    seg_h = h / segs
    color_base = spec["color"]
    color_tip = spec["tip_color"]

    uv_layer = bm.loops.layers.uv.verify()
    color_layer = bm.loops.layers.color.verify()

    blade_verts = []
    for i in range(segs + 1):
        t = i / segs  # 0 at base, 1 at tip
        # Width tapers: full at base, zero at tip
        w = bw * (1.0 - t * 0.85)
        # Height
        y = seg_h * i
        # Curvature: blade bends outward more as it goes up
        outward = curve * t * t * h
        # Droop: gravity pulls tip down
        y_droop = -droop * t * t * h

        # Apply lean direction
        local_x = outward * math.cos(rot) + dx
        local_z = outward * math.sin(rot) + dz
        local_y = y + y_droop

        # Two vertices per segment (left and right of blade center)
        perp_x = -math.sin(rot) * w * 0.5
        perp_z = math.cos(rot) * w * 0.5

        # Apply lean
        lean_offset_x = math.sin(lean) * math.cos(rot) * y * 0.3
        lean_offset_z = math.sin(lean) * math.sin(rot) * y * 0.3

        v_left = bm.verts.new((
            local_x + perp_x + lean_offset_x,
            local_y,
            local_z + perp_z + lean_offset_z
        ))
        v_right = bm.verts.new((
            local_x - perp_x + lean_offset_x,
            local_y,
            local_z - perp_z + lean_offset_z
        ))

        blade_verts.append((v_left, v_right, t))

    # Create faces between segments
    for i in range(segs):
        bl, br, t0 = blade_verts[i]
        tl, tr, t1 = blade_verts[i + 1]

        # Two triangles per quad segment
        try:
            f1 = bm.faces.new([bl, br, tr])
            f2 = bm.faces.new([bl, tr, tl])

            # Set UV and vertex color for each loop
            for f in [f1, f2]:
                for loop in f.loops:
                    v = loop.vert
                    # Find which blade_vert this is
                    for bv_l, bv_r, bv_t in blade_verts:
                        if v == bv_l or v == bv_r:
                            # UV: x=0 or 1 (left/right), y=t (height)
                            u = 0.0 if v == bv_l else 1.0
                            loop[uv_layer].uv = (u, bv_t)
                            # Vertex color: interpolate base->tip
                            r = color_base[0] + (color_tip[0] - color_base[0]) * bv_t
                            g = color_base[1] + (color_tip[1] - color_base[1]) * bv_t
                            b = color_base[2] + (color_tip[2] - color_base[2]) * bv_t
                            loop[color_layer] = (r, g, b, 1.0)
                            break
        except ValueError:
            pass  # Skip degenerate faces


def make_tuft(name, spec):
    """Create a complete grass tuft mesh."""
    bm = bmesh.new()
    rng = random.Random(hash(name))

    for _ in range(spec["n_blades"]):
        make_blade(bm, spec, rng)

    # Create mesh object
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    # Smooth shading
    for poly in mesh.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # Create material with vertex colors
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default
    for n in nodes:
        nodes.remove(n)

    # Simple vertex color material with alpha cutout
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    vcol = nodes.new("ShaderNodeVertexColor")
    vcol.layer_name = "Col"

    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Specular IOR Level"].default_value = 0.1

    links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    output.location = (300, 0)
    bsdf.location = (0, 0)
    vcol.location = (-300, 0)

    obj.data.materials.append(mat)

    return obj


def export_glb(obj, filepath):
    """Export single object as GLB."""
    # Select only this object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_draco_mesh_compression_enable=False,
    )


def main():
    for name, spec in TUFTS.items():
        clear_scene()
        print(f"\n=== Generating {name} ===")
        print(f"  Height: {spec['h']*100:.1f}cm, Blade width: {spec['bw']*1000:.1f}mm, "
              f"Blades: {spec['n_blades']}, Spread: {spec['spread']*100:.0f}cm")

        obj = make_tuft(name, spec)

        vcount = len(obj.data.vertices)
        fcount = len(obj.data.polygons)
        print(f"  Geometry: {vcount} verts, {fcount} faces")

        path = os.path.join(OUT_DIR, f"{name}.glb")
        export_glb(obj, path)
        size_kb = os.path.getsize(path) / 1024
        print(f"  Exported: {path} ({size_kb:.0f} KB)")

    print("\n=== All grass tufts generated ===")


if __name__ == "__main__":
    main()

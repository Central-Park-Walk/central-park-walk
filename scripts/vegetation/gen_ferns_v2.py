"""Generate high-detail fern models with species-accurate morphology.

Each fern is built from botanical research data:
- Correct frond count, length, arch, and droop
- Species-specific pinna shape via alpha-textured cards
- Proper rachis curvature and taper
- Vertex colors for wind animation (Y-based sway in shader)

Run: blender --background --python scripts/vegetation/gen_ferns_v2.py

Outputs:
  models/vegetation/Fern_Christmas.glb
  models/vegetation/Fern_Ostrich.glb
  models/vegetation/Fern_Cinnamon.glb
  models/vegetation/Fern_Sensitive.glb
"""

import sys
import os
import math
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
VEG_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def make_textured_material(name, tex_path):
    """Material with image texture + alpha clip for vegetation."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.blend_method = 'CLIP'  # alpha clip for Eevee preview
    mat.alpha_threshold = 0.4

    tree = mat.node_tree
    for n in tree.nodes:
        tree.nodes.remove(n)

    out = tree.nodes.new('ShaderNodeOutputMaterial')
    out.location = (600, 0)

    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    bsdf.inputs['Roughness'].default_value = 0.55
    bsdf.inputs['Specular IOR Level'].default_value = 0.12
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.location = (0, 0)
    if os.path.exists(tex_path):
        tex.image = bpy.data.images.load(tex_path)
        tex.image.alpha_mode = 'STRAIGHT'
    tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])

    return mat


def lerp(a, b, t):
    return a + (b - a) * t


def build_rachis_curve(origin, length, arch, droop, angle_y, n_pts=12):
    """Build a curved rachis path for a fern frond.

    arch: how far outward the frond extends (0-1, fraction of length)
    droop: how much the tip droops (0-1)
    angle_y: rotation around vertical axis
    """
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    pts = []
    for i in range(n_pts):
        t = i / (n_pts - 1)

        # Vertical rise: starts steep, levels off, droops at tip
        rise = length * (t * 0.85 - t * t * droop * 0.6)

        # Horizontal outward spread: increases along frond
        outward = length * t * arch

        # Slight S-curve for natural look
        s_curve = math.sin(t * math.pi) * length * 0.03

        x = origin.x + ca * outward + sa * s_curve
        y = origin.y + sa * outward - ca * s_curve
        z = origin.z + rise

        pts.append(Vector((x, y, z)))

    return pts


def add_rachis_tube(bm, points, r_start, r_end, n_sides, color, uv_layer, col_layer):
    """Add a tapered tube for the rachis stem."""
    rings = []
    n = len(points)
    for i, pt in enumerate(points):
        t = i / max(n - 1, 1)
        r = lerp(r_start, r_end, t)
        col_rgba = list(color) + [1.0]

        if i < n - 1:
            fwd = (points[i + 1] - pt).normalized()
        else:
            fwd = (pt - points[i - 1]).normalized()

        if abs(fwd.dot(Vector((0, 0, 1)))) < 0.95:
            side = fwd.cross(Vector((0, 0, 1))).normalized()
        else:
            side = fwd.cross(Vector((1, 0, 0))).normalized()
        up = side.cross(fwd).normalized()

        ring = []
        for j in range(n_sides):
            a = 2.0 * math.pi * j / n_sides
            offset = side * math.cos(a) * r + up * math.sin(a) * r
            v = bm.verts.new(pt + offset)
            ring.append(v)
        rings.append((ring, col_rgba, t))

    for i in range(len(rings) - 1):
        for j in range(n_sides):
            j2 = (j + 1) % n_sides
            v0 = rings[i][0][j]
            v1 = rings[i][0][j2]
            v2 = rings[i + 1][0][j2]
            v3 = rings[i + 1][0][j]
            try:
                f = bm.faces.new([v0, v1, v2, v3])
                for loop in f.loops:
                    # Rachis UV: x=0.5 (stem center), y=height fraction
                    vert_t = rings[i][2] if loop.vert in rings[i][0] else rings[i + 1][2]
                    loop[uv_layer].uv = (0.5, vert_t)
                    loop[col_layer] = rings[i][1] if loop.vert in rings[i][0] else rings[i + 1][1]
            except ValueError:
                pass


def add_pinna_card(bm, center, pinna_len, pinna_width,
                   direction, up_vec, tilt_angle,
                   height_frac, uv_layer, col_layer, mirror=False):
    """Add a single pinna as a textured quad card.

    The card is oriented perpendicular to the rachis, tilted slightly.
    UV maps to the full pinna texture (0-1 range).
    Vertex color stores height info for wind animation.
    """
    # Build local coordinate frame
    fwd = direction.normalized()
    right = fwd.cross(up_vec).normalized()
    if right.length < 0.01:
        right = fwd.cross(Vector((0, 0, 1))).normalized()
    local_up = right.cross(fwd).normalized()

    # Apply tilt
    tilt_mat = Matrix.Rotation(tilt_angle, 3, fwd)
    right = tilt_mat @ right
    local_up = tilt_mat @ local_up

    hw = pinna_width * 0.5
    hl = pinna_len * 0.5

    if mirror:
        right = -right

    # Quad corners: base-left, base-right, tip-right, tip-left
    # Pinna extends outward from rachis (fwd direction) and has length along it
    v_bl = bm.verts.new(center - fwd * hl - right * hw * 0.3)
    v_br = bm.verts.new(center - fwd * hl + right * hw * 0.3)
    v_tr = bm.verts.new(center + fwd * hl + right * hw)
    v_tl = bm.verts.new(center + fwd * hl - right * hw)

    # Mid vertices for better shape (6 verts, 4 tris)
    v_ml = bm.verts.new(center - right * hw * 0.1)
    v_mr = bm.verts.new(center + right * hw * 1.1)  # auricle side slightly wider

    # Height-based color for wind: darker at base, brighter at tip
    # The shader uses VERTEX.y for wind sway, so we encode height in color
    # for any additional effects
    col = [0.08 + height_frac * 0.15,
           0.25 + height_frac * 0.20,
           0.05 + height_frac * 0.08,
           1.0]

    # UV coordinates map to pinna texture
    uv_map = {
        id(v_bl): (0.35, 0.0),   # base left
        id(v_br): (0.65, 0.0),   # base right
        id(v_ml): (0.0, 0.45),   # mid left
        id(v_mr): (1.0, 0.45),   # mid right
        id(v_tl): (0.25, 1.0),   # tip left
        id(v_tr): (0.75, 1.0),   # tip right (doesn't exist, use tip center)
    }

    # Create faces (4 triangles from 6 vertices)
    faces = [
        [v_bl, v_br, v_mr],
        [v_bl, v_mr, v_ml],
        [v_ml, v_mr, v_tr],
        [v_ml, v_tr, v_tl],
    ]

    for verts in faces:
        try:
            f = bm.faces.new(verts)
            for loop in f.loops:
                uv = uv_map.get(id(loop.vert), (0.5, 0.5))
                loop[uv_layer].uv = uv
                loop[col_layer] = col
        except ValueError:
            pass


def add_pinna_simple(bm, center, pinna_len, pinna_width,
                     outward_dir, rachis_fwd, tilt,
                     height_frac, uv_layer, col_layer):
    """Pinna card with 3 quad strips for curvature and better silhouette.

    Creates 6 triangles per pinna (3 quads) with a gentle droop curve
    and proper UV mapping to the pinna texture.
    """
    out = outward_dir.normalized()

    # Pinna card lies FLAT (face up) and extends outward from rachis.
    # The card surface normal points roughly upward so it catches light
    # and is visible from above and at walking-height camera angles.

    # "right" = outward from rachis (pinna extends this way)
    # "fwd" = along rachis direction (pinna width spans this way)
    # "up" = vertical (card face normal, modified by tilt)

    fwd = rachis_fwd.normalized()
    up = Vector((0, 0, 1))

    # Apply tilt — rotates the pinna around the outward axis
    tilt_mat = Matrix.Rotation(tilt, 3, out)
    up = tilt_mat @ up
    fwd = tilt_mat @ fwd

    # 4 rows of 2 vertices = 3 quad strips
    # Rows go from base (rachis attachment) to tip of pinna
    n_rows = 4
    verts_grid = []
    for row in range(n_rows):
        t = row / (n_rows - 1)  # 0=base, 1=tip

        # Width tapers: lanceolate shape, widest in lower-middle
        if t < 0.3:
            w_scale = 0.4 + t * 2.0
        else:
            w_scale = 1.0 - (t - 0.3) / 0.7 * 0.65

        hw = pinna_width * 0.5 * w_scale

        # Position along pinna length (outward from rachis)
        along = out * (pinna_len * t)

        # Natural droop: tip bends slightly downward
        droop_vec = Vector((0, 0, -0.015 * pinna_len * t * t))

        # Slight upward curl at edges for 3D volume
        curl = up * (0.003 * pinna_len * math.sin(t * math.pi))

        pos_base = center + along + droop_vec + curl

        # Width spans along the rachis direction (fwd), so the card
        # face is roughly horizontal/upward-facing
        v_left = bm.verts.new(pos_base - fwd * hw)
        v_right = bm.verts.new(pos_base + fwd * hw)
        verts_grid.append((v_left, v_right, t))

    # Vertex color — the shader reads albedo from the texture when
    # use_texture=1, so COLOR is mostly used for per-instance variation.
    # Keep it neutral/bright so the texture colors come through.
    col = [0.75 + height_frac * 0.15,
           0.80 + height_frac * 0.15,
           0.70 + height_frac * 0.10,
           1.0]

    # Create quad faces between consecutive rows
    for i in range(n_rows - 1):
        vb0, vt0, t0 = verts_grid[i]
        vb1, vt1, t1 = verts_grid[i + 1]

        uv_map = {
            id(vb0): (0.0, t0),
            id(vt0): (1.0, t0),
            id(vb1): (0.0, t1),
            id(vt1): (1.0, t1),
        }

        try:
            f = bm.faces.new([vb0, vt0, vt1, vb1])
            for loop in f.loops:
                loop[uv_layer].uv = uv_map[id(loop.vert)]
                loop[col_layer] = col
        except ValueError:
            pass


def build_fern(species_cfg, rng):
    """Build a complete fern plant from species configuration."""
    cfg = species_cfg
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    n_fronds = cfg['n_fronds']
    crown_origin = Vector((0, 0, cfg.get('crown_height', 0.02)))

    for fi in range(n_fronds):
        # Distribute fronds around the crown
        base_angle = (fi / n_fronds) * math.tau
        angle = base_angle + rng.uniform(-0.2, 0.2)

        # Vary frond parameters significantly for natural 3D volume
        frond_len = cfg['frond_length'] * rng.uniform(0.75, 1.20)
        arch = cfg['arch'] * rng.uniform(0.7, 1.3)
        droop = cfg['droop'] * rng.uniform(0.6, 1.4)

        # Frond origin offset from crown center with HEIGHT variation
        # Real ferns have fronds at different heights — outer ones droop,
        # inner ones rise, creating a 3D mound not a flat disc
        offset_r = cfg.get('crown_radius', 0.03)
        height_var = rng.uniform(-0.02, 0.04)  # vertical stagger
        frond_origin = crown_origin + Vector((
            math.cos(angle) * offset_r,
            math.sin(angle) * offset_r,
            height_var
        ))

        # Build rachis curve
        rachis_pts = build_rachis_curve(
            frond_origin, frond_len, arch, droop, angle,
            n_pts=cfg.get('rachis_segments', 12)
        )

        # Add rachis tube
        rachis_color = cfg.get('rachis_color', (0.25, 0.18, 0.08))
        add_rachis_tube(bm, rachis_pts,
                       cfg.get('rachis_r_base', 0.004),
                       cfg.get('rachis_r_tip', 0.001),
                       cfg.get('rachis_sides', 4),
                       rachis_color, uv, co)

        # Add pinnae along rachis
        n_pinnae = cfg['n_pinnae'] + rng.randint(-2, 2)
        for pi in range(n_pinnae):
            # Position along rachis (skip very base and very tip)
            t = (pi + 1.0) / (n_pinnae + 1.0)

            # Skip if in the reduced zone at base or tip
            if t < cfg.get('pinna_start_t', 0.08):
                continue
            if t > cfg.get('pinna_end_t', 0.95):
                continue

            # Interpolate position on rachis
            seg_t = t * (len(rachis_pts) - 1)
            idx = min(int(seg_t), len(rachis_pts) - 2)
            frac = seg_t - idx
            pos = rachis_pts[idx].lerp(rachis_pts[idx + 1], frac)

            # Rachis direction at this point
            if idx < len(rachis_pts) - 1:
                rachis_dir = (rachis_pts[idx + 1] - rachis_pts[idx]).normalized()
            else:
                rachis_dir = (rachis_pts[-1] - rachis_pts[-2]).normalized()

            # Pinna size: taper toward base and tip
            # Christmas fern: largest in lower-middle, reduced at base
            base_taper = min(1.0, (t - cfg.get('pinna_start_t', 0.08)) / 0.15)
            tip_taper = 1.0 - max(0, (t - 0.65) / 0.35) ** 0.7
            scale = base_taper * tip_taper

            pl = cfg['pinna_length'] * scale * rng.uniform(0.9, 1.1)
            pw = cfg['pinna_width'] * scale * rng.uniform(0.9, 1.1)

            if pl < 0.005 or pw < 0.004:
                continue

            # Alternate sides
            side = 1.0 if pi % 2 == 0 else -1.0

            # Outward direction (perpendicular to rachis, alternating sides)
            up = Vector((0, 0, 1))
            outward = rachis_dir.cross(up).normalized() * side
            if outward.length < 0.01:
                outward = rachis_dir.cross(Vector((1, 0, 0))).normalized() * side

            # Slight tilt for depth
            tilt = side * rng.uniform(0.1, 0.35)

            # Height fraction for wind animation
            height_frac = pos.z / max(0.01, frond_len * 0.8)

            add_pinna_simple(bm, pos, pl, pw,
                           outward, rachis_dir, tilt,
                           height_frac, uv, co)

    return bm


def export_fern(bm, name, mat, out_path):
    """Convert bmesh to object and export as GLB."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)

    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
        export_image_format='AUTO',
    )
    print(f"  Exported {out_path}")
    print(f"  Vertices: {len(mesh.vertices)}, Triangles: {len(mesh.polygons)}")

    # Cleanup
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)


# ===================================================================
# Species configurations — from botanical research
# ===================================================================

CHRISTMAS_FERN = {
    'name': 'Fern_Christmas',
    'texture': 'tex_pinna_christmas.png',
    'n_fronds': 16,          # 10-20 fronds per rosette
    'frond_length': 0.45,    # 30-60cm, typically 45cm
    'arch': 0.75,            # arches outward significantly
    'droop': 0.55,           # fronds arch toward ground
    'crown_height': 0.02,
    'crown_radius': 0.025,
    'rachis_segments': 16,
    'rachis_r_base': 0.004,
    'rachis_r_tip': 0.001,
    'rachis_sides': 4,
    'rachis_color': (0.30, 0.22, 0.10),  # golden-brown scales
    'n_pinnae': 32,          # 20-35 pinnae per frond
    'pinna_length': 0.040,   # 2-5cm, boosted for visual presence
    'pinna_width': 0.028,    # doubled for visible leaf surface
    'pinna_start_t': 0.06,
    'pinna_end_t': 0.92,
    'seed': 802,
    # Target: ~3,500 tris (16 fronds × 32 pinnae × 6 tris + rachis)
}

OSTRICH_FERN = {
    'name': 'Fern_Ostrich',
    'texture': 'tex_pinna_ostrich.png',
    'n_fronds': 10,          # 7-12 sterile fronds
    'frond_length': 1.30,    # 80-170cm, typically 130cm
    'arch': 0.38,            # vase shape
    'droop': 0.30,           # graceful droop at tips
    'crown_height': 0.05,
    'crown_radius': 0.04,
    'rachis_segments': 18,
    'rachis_r_base': 0.006,
    'rachis_r_tip': 0.0015,
    'rachis_sides': 4,
    'rachis_color': (0.22, 0.28, 0.08),  # green rachis
    'n_pinnae': 40,          # 20-40+ pinnae per frond
    'pinna_length': 0.14,    # 10-18cm at widest
    'pinna_width': 0.050,    # wider for visual fill
    'pinna_start_t': 0.15,   # REDUCED at base (key ID feature)
    'pinna_end_t': 0.95,
    'seed': 801,
    # Target: ~3,000 tris (10 fronds × 40 pinnae × 6 tris + rachis)
}

CINNAMON_FERN = {
    'name': 'Fern_Cinnamon',
    'texture': 'tex_pinna_cinnamon.png',
    'n_fronds': 12,          # 8-15 sterile fronds
    'frond_length': 0.95,    # 60-150cm, typically 95cm
    'arch': 0.48,            # moderate arch
    'droop': 0.38,           # graceful droop
    'crown_height': 0.04,
    'crown_radius': 0.035,
    'rachis_segments': 16,
    'rachis_r_base': 0.005,
    'rachis_r_tip': 0.0012,
    'rachis_sides': 4,
    'rachis_color': (0.35, 0.20, 0.08),  # cinnamon-woolly
    'n_pinnae': 34,          # 20-35 pinnae per frond
    'pinna_length': 0.12,    # 8-15cm
    'pinna_width': 0.050,    # wider for visual fill
    'pinna_start_t': 0.05,   # full-sized at base (unlike ostrich!)
    'pinna_end_t': 0.93,
    'seed': 803,
    # Target: ~3,200 tris (12 fronds × 34 pinnae × 6 tris + rachis)
}

SENSITIVE_FERN = {
    'name': 'Fern_Sensitive',
    'texture': 'tex_pinna_sensitive.png',
    'n_fronds': 10,          # more fronds to fill the carpet-like colony
    'frond_length': 0.45,    # 30-60cm
    'arch': 0.25,            # more upright
    'droop': 0.15,           # minimal droop
    'crown_height': 0.01,
    'crown_radius': 0.08,    # wider spacing (rhizome spread)
    'rachis_segments': 10,
    'rachis_r_base': 0.003,
    'rachis_r_tip': 0.001,
    'rachis_sides': 3,
    'rachis_color': (0.30, 0.35, 0.10),  # yellow-green stipe
    'n_pinnae': 10,          # 5-11 pairs (few LARGE pinnae)
    'pinna_length': 0.12,    # 6-12cm (large, broad)
    'pinna_width': 0.070,    # 3-5cm (very wide — un-fern-like)
    'pinna_start_t': 0.10,
    'pinna_end_t': 0.92,
    'seed': 804,
    # Target: ~1,500 tris (10 fronds × 10 pinnae × 6 tris + rachis)
    # Lower count is correct — sensitive fern has few large pinnae
}

ALL_FERNS = [CHRISTMAS_FERN, OSTRICH_FERN, CINNAMON_FERN, SENSITIVE_FERN]


def main():
    for cfg in ALL_FERNS:
        clear_scene()

        name = cfg['name']
        tex_path = os.path.join(VEG_DIR, cfg['texture'])
        out_path = os.path.join(VEG_DIR, f"{name}.glb")

        print(f"\n=== Generating {name} ===")

        mat = make_textured_material(f"{name}_Mat", tex_path)
        rng = random.Random(cfg['seed'])
        bm = build_fern(cfg, rng)

        export_fern(bm, name, mat, out_path)

    print("\nAll ferns generated.")


if __name__ == "__main__":
    main()

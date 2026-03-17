"""Create undergrowth vegetation models for Central Park Walk.

16 species across 5 vertical layers — the missing vegetation between
ankle height and tree canopy that makes wild areas feel real.

Run: blender --background --python scripts/make_undergrowth.py

Outputs to models/vegetation/:
  Shrub_Spicebush.glb          — 3m, dominant understory shrub
  Shrub_WitchHazel.glb         — 4m, large zigzag understory
  Shrub_Viburnum.glb           — 2.5m, dense screening shrub
  Shrub_Sumac.glb              — 4m, flat-topped colony shrub
  Shrub_Elderberry.glb         — 3m, arching woodland edge
  Herb_Pokeweed.glb            — 2m, magenta stems (signature)
  Herb_JapaneseKnotweed.glb    — 3m, invasive bamboo-like thicket
  Herb_JoePyeWeed.glb          — 2m, tall pink wetland flower
  Herb_Coneflower.glb          — 2m, yellow drooping petals
  Herb_CardinalFlower.glb      — 0.8m, scarlet spike
  Herb_Mugwort.glb             — 1m, silvery invasive
  Herb_WhiteWoodAster.glb      — 0.4m, woodland floor carpet
  Herb_Jewelweed.glb           — 0.8m, stream bank
  Fern_Ostrich.glb             — 1.3m, tall vase-shaped
  Fern_Christmas.glb           — 0.4m, evergreen rosette
  Wetland_Cattail.glb          — 2m, iconic pond edge
"""

import bpy
import bmesh
import math
import random
import os
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)


# ==========================================================================
# Utilities
# ==========================================================================

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def make_material(name):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    tree = mat.node_tree
    for n in tree.nodes:
        tree.nodes.remove(n)
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Roughness'].default_value = 0.6
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    vcol = tree.nodes.new('ShaderNodeVertexColor')
    vcol.location = (-200, 0)
    vcol.layer_name = "Col"
    tree.links.new(vcol.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def finalize_and_export(bm, name, mat=None):
    """Convert bmesh to object, export as GLB."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)

    # Custom normals: blend face normal toward up for softer shading
    normals = [(0, 0, 0)] * len(mesh.loops)
    for poly in mesh.polygons:
        fn = Vector(poly.normal)
        up = Vector((0, 0, 1))
        n = fn.lerp(up, 0.35).normalized()
        for li in poly.loop_indices:
            normals[li] = tuple(n)
    mesh.normals_split_custom_set(normals)

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    m = make_material(name + "_Mat")
    obj.data.materials.append(m)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    bm.free()

    # Export
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT_DIR, f"{name}.glb")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_normals=True,
        export_colors=True,
        export_apply=True,
    )
    nv = len(mesh.vertices)
    nf = len(mesh.polygons)
    print(f"  {name}: {nv} verts, {nf} faces → {path}")
    return obj


# ==========================================================================
# Geometry helpers
# ==========================================================================

def _lerp_color(c0, c1, t):
    return [c0[i] + (c1[i] - c0[i]) * t for i in range(3)] + [1.0]


def make_tube(bm, points, r_start, r_end, n_sides, color_start, color_end,
              uv_layer, col_layer, uv_y_start=0.0, uv_y_end=1.0):
    """Create a tube mesh along a list of points. Returns list of vertex rings."""
    rings = []
    n = len(points)
    for i, pt in enumerate(points):
        t = i / max(n - 1, 1)
        r = r_start + (r_end - r_start) * t
        uv_y = uv_y_start + (uv_y_end - uv_y_start) * t
        col = _lerp_color(color_start, color_end, t)

        # Compute local frame
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
            ring.append((v, uv_y, col))
        rings.append(ring)

    # Connect rings
    for i in range(len(rings) - 1):
        for j in range(n_sides):
            j2 = (j + 1) % n_sides
            v0, uv0, c0 = rings[i][j]
            v1, uv1, c1 = rings[i][j2]
            v2, uv2, c2 = rings[i + 1][j2]
            v3, uv3, c3 = rings[i + 1][j]
            try:
                f = bm.faces.new([v0, v1, v2, v3])
                for loop in f.loops:
                    if loop.vert in (v0, v1):
                        loop[uv_layer].uv = (0.5, uv0)
                        loop[col_layer] = c0
                    else:
                        loop[uv_layer].uv = (0.5, uv3)
                        loop[col_layer] = c3
            except ValueError:
                pass
    return rings


def make_leaf_card(bm, center, width, height, angle_y, tilt, color,
                   _uv_y, uv_layer, col_layer):
    """Diamond-shaped leaf card with UV mapped for procedural alpha cutout.
    UV.x spans 0-1 across leaf width, UV.y spans 0-1 base to tip.
    Shader uses these UVs to generate a natural leaf silhouette.
    _uv_y is accepted for call-site compatibility but ignored."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    ct, st = math.cos(tilt), math.sin(tilt)
    hw, hh = width * 0.5, height * 0.5

    dx = Vector((ca, sa, 0))
    dz = Vector((-sa * st, ca * st, ct))

    # Diamond: 4 verts — base, right, tip, left (same tri count as rectangle)
    vb = bm.verts.new(center - dz * hh)                   # base
    vr = bm.verts.new(center + dx * hw - dz * hh * 0.1)   # right (at 40% height)
    vt = bm.verts.new(center + dz * hh)                   # tip
    vl = bm.verts.new(center - dx * hw - dz * hh * 0.1)   # left (at 40% height)

    col_rgba = list(color[:3]) + [1.0] if len(color) == 3 else list(color)
    # Two triangles: base-right-tip, base-tip-left
    uv_map = {id(vb): (0.5, 0.0), id(vr): (1.0, 0.4),
              id(vt): (0.5, 1.0), id(vl): (0.0, 0.4)}
    for verts in [[vb, vr, vt], [vb, vt, vl]]:
        try:
            f = bm.faces.new(verts)
            for loop in f.loops:
                loop[uv_layer].uv = uv_map[id(loop.vert)]
                loop[col_layer] = col_rgba
        except ValueError:
            pass


def make_crossed_planes(bm, height, width_base, width_top, n_planes, segments,
                        color_func, uv_layer, col_layer):
    """Create n_planes vertical billboard planes crossing at center.
    UV.x spans 0-1 across each plane width (for shader leaf alpha cutout).
    UV.y spans 0-1 from base to tip. color_func(t) returns (r,g,b)."""
    for p in range(n_planes):
        angle = (p / n_planes) * math.pi
        ca, sa = math.cos(angle), math.sin(angle)

        for s in range(segments):
            t0 = s / segments
            t1 = (s + 1) / segments
            z0 = height * t0
            z1 = height * t1
            w0 = (width_base + (width_top - width_base) * t0) * 0.5
            w1 = (width_base + (width_top - width_base) * t1) * 0.5
            c0 = list(color_func(t0)) + [1.0]
            c1 = list(color_func(t1)) + [1.0]

            v0 = bm.verts.new((-ca * w0, -sa * w0, z0))  # left-bottom
            v1 = bm.verts.new((ca * w0, sa * w0, z0))     # right-bottom
            v2 = bm.verts.new((ca * w1, sa * w1, z1))     # right-top
            v3 = bm.verts.new((-ca * w1, -sa * w1, z1))   # left-top
            try:
                f = bm.faces.new([v0, v1, v2, v3])
                uv_map = {id(v0): (0.0, t0), id(v1): (1.0, t0),
                          id(v2): (1.0, t1), id(v3): (0.0, t1)}
                for loop in f.loops:
                    loop[uv_layer].uv = uv_map[id(loop.vert)]
                    if loop.vert in (v0, v1):
                        loop[col_layer] = c0
                    else:
                        loop[col_layer] = c1
            except ValueError:
                pass


def make_frond(bm, origin, length, width, segments, arch, droop, angle_y,
               color_base, color_tip, uv_layer, col_layer):
    """Create one fern frond as a curved tapered strip.
    UV.x spans 0-1 across width (for shader leaf alpha cutout).
    UV.y spans 0-1 from base to tip."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    verts = []
    for i in range(segments + 1):
        t = i / segments
        rise = length * 0.7 * t * (1.0 - t * droop)
        out = length * t * arch
        fw = width * (1.0 - t * 0.7) * 0.5

        cx = origin.x + ca * out
        cy = origin.y + sa * out
        cz = origin.z + rise

        px, py = -sa * fw, ca * fw

        col = _lerp_color(color_base, color_tip, t)
        vl = bm.verts.new((cx + px, cy + py, cz))
        vr = bm.verts.new((cx - px, cy - py, cz))
        verts.append((vl, vr, t, col))

    for i in range(segments):
        vl0, vr0, uv0, c0 = verts[i]
        vl1, vr1, uv1, c1 = verts[i + 1]
        try:
            f = bm.faces.new([vl0, vr0, vr1, vl1])
            uv_map = {id(vl0): (0.0, uv0), id(vr0): (1.0, uv0),
                      id(vr1): (1.0, uv1), id(vl1): (0.0, uv1)}
            for loop in f.loops:
                loop[uv_layer].uv = uv_map[id(loop.vert)]
                if loop.vert in (vl0, vr0):
                    loop[col_layer] = c0
                else:
                    loop[col_layer] = c1
        except ValueError:
            pass


def bezier_pt(p0, p1, p2, t):
    """Quadratic bezier."""
    u = 1.0 - t
    return p0 * u * u + p1 * 2.0 * u * t + p2 * t * t


# ==========================================================================
# Species: SHRUBS (multi-stem + leaf clusters)
# ==========================================================================

def _make_shrub(bm, rng, n_stems, height, spread, stem_r, leaf_size,
                stem_color, leaf_color, zigzag, leaf_density,
                uv_layer, col_layer):
    """Generic multi-stem shrub with dense leaf coverage.
    Stems are thin and green-tinted to blend with foliage.
    Leaves start low (20% height) and spread wide to fill the crown."""
    # Stems: lighter, greener — blend toward leaf color so they disappear
    stem_blend = [stem_color[i] * 0.6 + leaf_color[i] * 0.4 for i in range(3)]
    stem_color_tip = [min(c + 0.06, 1.0) for c in stem_blend]

    for s in range(n_stems):
        angle = (s / n_stems) * math.tau + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.15, 0.45) * spread
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean

        pts = []
        n_seg = 6
        for i in range(n_seg):
            t = i / (n_seg - 1)
            zz = 0.0
            if zigzag and i > 0 and i < n_seg - 1:
                zz = rng.uniform(-0.06, 0.06) * height
            pts.append(Vector((
                dx * t + rng.uniform(-0.02, 0.02) + zz * math.cos(angle + 1.5),
                dy * t + rng.uniform(-0.02, 0.02) + zz * math.sin(angle + 1.5),
                height * t * (1.0 - 0.1 * t)
            )))

        # Thinner stems — less visible
        r_base = stem_r * rng.uniform(0.6, 0.9)
        make_tube(bm, pts, r_base, r_base * 0.2, 3,
                  stem_blend, stem_color_tip, uv_layer, col_layer,
                  uv_y_start=0.0, uv_y_end=0.5)

        # Sub-branches (also thinner)
        n_sub = rng.randint(1, 3)
        for sb in range(n_sub):
            branch_t = rng.uniform(0.3, 0.7)
            branch_idx = min(int(branch_t * (n_seg - 1)), n_seg - 1)
            origin = pts[branch_idx].copy()
            sub_angle = angle + rng.uniform(-1.2, 1.2)
            sub_len = height * rng.uniform(0.2, 0.4)
            sub_dx = math.cos(sub_angle)
            sub_dy = math.sin(sub_angle)
            sub_pts = [
                origin,
                Vector((origin.x + sub_dx * sub_len * 0.5,
                        origin.y + sub_dy * sub_len * 0.5,
                        origin.z + sub_len * 0.4)),
                Vector((origin.x + sub_dx * sub_len,
                        origin.y + sub_dy * sub_len,
                        origin.z + sub_len * 0.2)),
            ]
            make_tube(bm, sub_pts, r_base * 0.25, r_base * 0.08, 3,
                      stem_blend, stem_color_tip, uv_layer, col_layer,
                      uv_y_start=0.3, uv_y_end=0.6)

        # Dense leaf cards — start LOW (20% height), spread WIDE to fill crown
        for i in range(leaf_density):
            lt = rng.uniform(0.20, 1.0)  # leaves start at 20%, not 40%
            idx = min(int(lt * (n_seg - 1)), n_seg - 1)
            lc = pts[idx].copy()
            # Wider spread — leaves fill the air around the stems
            lc.x += rng.uniform(-0.25, 0.25) * spread
            lc.y += rng.uniform(-0.25, 0.25) * spread
            lc.z += rng.uniform(-0.08, 0.12) * height
            la = rng.uniform(0, math.tau)
            lt_angle = rng.uniform(-0.3, 0.5)
            lw = leaf_size * rng.uniform(0.7, 1.3)
            lh = leaf_size * rng.uniform(0.8, 1.4)
            make_leaf_card(bm, lc, lw, lh, la, lt_angle, leaf_color,
                          lt * 0.5 + 0.3, uv_layer, col_layer)


def make_spicebush():
    """Spicebush (Lindera benzoin) — THE dominant Central Park understory shrub.
    2-4m, multi-stemmed, open spreading form, zigzag branching."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(101)

    # Glossy aromatic leaves — warmer yellow-green, dense understory
    _make_shrub(bm, rng, n_stems=5, height=3.0, spread=1.8,
                stem_r=0.020, leaf_size=0.10,
                stem_color=(0.30, 0.25, 0.14),
                leaf_color=(0.30, 0.48, 0.12),  # warm glossy yellow-green
                zigzag=True, leaf_density=40,
                uv_layer=uv, col_layer=co)

    return bm


def make_witch_hazel():
    """Witch hazel (Hamamelis virginiana) — 3-5m, open irregular crown,
    larger than spicebush, distinctive zigzag architecture."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(202)

    _make_shrub(bm, rng, n_stems=4, height=4.0, spread=2.2,
                stem_r=0.025, leaf_size=0.13,
                stem_color=(0.34, 0.30, 0.20),
                leaf_color=(0.20, 0.38, 0.10),
                zigzag=True, leaf_density=35,
                uv_layer=uv, col_layer=co)

    return bm


def make_viburnum():
    """Arrowwood viburnum (Viburnum dentatum) — 2-3m, dense rounded form.
    Creates solid visual screens in understory."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(303)

    # Glossy dark green toothed leaves — dense visual screen
    _make_shrub(bm, rng, n_stems=6, height=2.5, spread=1.5,
                stem_r=0.015, leaf_size=0.08,
                stem_color=(0.22, 0.28, 0.12),
                leaf_color=(0.10, 0.32, 0.05),  # glossy dark green
                zigzag=False, leaf_density=45,
                uv_layer=uv, col_layer=co)

    # Add white flower cluster at top
    for _ in range(3):
        fc = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3),
                      rng.uniform(1.8, 2.3)))
        for _ in range(5):
            make_leaf_card(bm, fc + Vector((rng.uniform(-0.06, 0.06),
                                            rng.uniform(-0.06, 0.06), 0)),
                          0.04, 0.04, rng.uniform(0, math.tau), 0.1,
                          (0.92, 0.94, 0.88), 0.9, uv, co)

    return bm


def make_sumac():
    """Staghorn sumac (Rhus typhina) — 3-5m, flat-topped, colony-forming.
    Feathery compound leaves, red fruit clusters, velvety stems."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(404)

    # Thick velvety stems
    for s in range(3):
        angle = (s / 3) * math.tau + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.3, 0.8)
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean
        h = rng.uniform(3.5, 4.5)

        pts = []
        for i in range(6):
            t = i / 5
            pts.append(Vector((dx * t, dy * t, h * t * (1.0 - 0.05 * t))))
        make_tube(bm, pts, 0.04, 0.015, 5,
                  (0.45, 0.30, 0.18), (0.50, 0.35, 0.22),
                  uv, co, 0.0, 0.4)

        # Flat-topped canopy: feathery compound leaf quads (pinnate, vivid green)
        top = pts[-1]
        for _ in range(10):
            lc = top + Vector((rng.uniform(-0.6, 0.6),
                               rng.uniform(-0.6, 0.6),
                               rng.uniform(-0.2, 0.3)))
            make_leaf_card(bm, lc, 0.25, 0.08, rng.uniform(0, math.tau),
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.42, 0.06), 0.8, uv, co)

        # Fuzzy crimson-red fruit cluster at top — vivid upright cone
        fruit_c = top + Vector((0, 0, 0.15))
        for _ in range(4):
            fc = fruit_c + Vector((rng.uniform(-0.03, 0.03),
                                   rng.uniform(-0.03, 0.03),
                                   rng.uniform(-0.05, 0.05)))
            make_leaf_card(bm, fc, 0.04, 0.06, rng.uniform(0, math.tau),
                          0.1, (0.82, 0.10, 0.06), 0.95, uv, co)  # vivid crimson

    return bm


def make_elderberry():
    """Elderberry (Sambucus canadensis) — 2-3.5m, arching multi-stemmed.
    Compound leaves, large white flower clusters."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(505)

    for s in range(4):
        angle = (s / 4) * math.tau + rng.uniform(-0.4, 0.4)
        lean = rng.uniform(0.4, 1.0)
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean
        h = rng.uniform(2.5, 3.2)

        # Arching stem path
        pts = []
        for i in range(7):
            t = i / 6
            arch_drop = -0.4 * t * t  # arch over
            pts.append(Vector((
                dx * t * 1.2, dy * t * 1.2,
                h * t * (1.0 - 0.15 * t) + arch_drop
            )))
        make_tube(bm, pts, 0.022, 0.008, 4,
                  (0.38, 0.30, 0.20), (0.42, 0.36, 0.24),
                  uv, co, 0.0, 0.5)

        # Compound leaf quads along upper stem
        for lf in range(6):
            lt = rng.uniform(0.4, 0.95)
            idx = min(int(lt * 6), 5)
            lc = pts[idx] + Vector((rng.uniform(-0.15, 0.15),
                                    rng.uniform(-0.15, 0.15),
                                    rng.uniform(-0.05, 0.1)))
            # Light green compound leaves (5-7 leaflets per leaf)
            make_leaf_card(bm, lc, 0.14, 0.08, rng.uniform(0, math.tau),
                          rng.uniform(-0.2, 0.3),
                          (0.22, 0.44, 0.10), lt * 0.4 + 0.3, uv, co)

        # White flower cluster near top
        fc = pts[-2] + Vector((0, 0, 0.1))
        for _ in range(6):
            fv = fc + Vector((rng.uniform(-0.08, 0.08),
                              rng.uniform(-0.08, 0.08),
                              rng.uniform(-0.02, 0.04)))
            make_leaf_card(bm, fv, 0.03, 0.03, rng.uniform(0, math.tau),
                          0.1, (0.92, 0.94, 0.86), 0.92, uv, co)

    return bm


# ==========================================================================
# Species: TALL HERBACEOUS (stem + leaves + flowers)
# ==========================================================================

def make_pokeweed():
    """Pokeweed (Phytolacca americana) — 1.2-3m, MAGENTA/PURPLE stems.
    The signature color. Large leaves, drooping purple berry clusters."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(601)

    h = 2.0
    # Main stem — MAGENTA is the signature
    main_pts = []
    for i in range(8):
        t = i / 7
        main_pts.append(Vector((
            rng.uniform(-0.02, 0.02),
            rng.uniform(-0.02, 0.02),
            h * t
        )))
    make_tube(bm, main_pts, 0.025, 0.010, 5,
              (0.72, 0.08, 0.35), (0.80, 0.12, 0.42),  # vivid magenta!
              uv, co, 0.0, 0.6)

    # Side branches with leaves
    for b in range(4):
        bt = 0.3 + b * 0.15
        idx = min(int(bt * 7), 6)
        origin = main_pts[idx].copy()
        ba = rng.uniform(0, math.tau)
        bl = rng.uniform(0.3, 0.6)
        bdx, bdy = math.cos(ba) * bl, math.sin(ba) * bl

        # Large elliptical leaf
        leaf_c = origin + Vector((bdx * 0.5, bdy * 0.5, 0.05))
        make_leaf_card(bm, leaf_c, 0.18, 0.28, ba,
                      rng.uniform(-0.1, 0.2),
                      (0.15, 0.35, 0.06), bt * 0.5 + 0.2, uv, co)

    # Drooping berry raceme at top
    top = main_pts[-1]
    for b in range(5):
        bt = b / 4
        bc = top + Vector((rng.uniform(-0.02, 0.02),
                           rng.uniform(-0.02, 0.02),
                           -bt * 0.15 + 0.05))
        make_leaf_card(bm, bc, 0.03, 0.03, rng.uniform(0, math.tau),
                      0.0, (0.15, 0.02, 0.15), 0.95, uv, co)  # deep purple-black

    return bm


def make_japanese_knotweed():
    """Japanese knotweed (Fallopia japonica) — 2-4.5m, bamboo-like thicket.
    THE invasive that defines disturbed areas. Dense walls of vegetation."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(602)

    for s in range(4):
        h = rng.uniform(2.5, 3.5)
        ox = rng.uniform(-0.25, 0.25)
        oy = rng.uniform(-0.25, 0.25)

        # Thick bamboo-like stem with nodes
        pts = []
        for i in range(8):
            t = i / 7
            pts.append(Vector((
                ox + rng.uniform(-0.01, 0.01),
                oy + rng.uniform(-0.01, 0.01),
                h * t
            )))

        # Green stem with purple speckle character — olive-green with red undertone
        make_tube(bm, pts, 0.018, 0.012, 5,
                  (0.32, 0.35, 0.14), (0.38, 0.38, 0.18),  # purple-tinged green
                  uv, co, 0.0, 0.5)

        # Large heart-shaped leaves at nodes
        for node in range(3, 7):
            t = node / 7
            lc = pts[node].copy()
            for side in range(2):
                la = (s / 4) * math.tau + side * math.pi + rng.uniform(-0.3, 0.3)
                leaf_off = Vector((math.cos(la) * 0.2, math.sin(la) * 0.2, 0.02))
                make_leaf_card(bm, lc + leaf_off, 0.18, 0.14, la,
                              rng.uniform(-0.2, 0.1),
                              (0.20, 0.46, 0.08), t * 0.4 + 0.3, uv, co)  # bright green

    return bm


def make_joe_pye_weed():
    """Joe Pye weed (Eutrochium spp.) — 1.2-3m, tall wetland wildflower.
    Large domed pink-purple flower heads. Whorled leaves."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(603)

    h = 2.0
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.015, 0.015),
                           rng.uniform(-0.015, 0.015), h * t)))

    # Purple-tinged stem
    make_tube(bm, pts, 0.015, 0.008, 5,
              (0.30, 0.22, 0.28), (0.35, 0.25, 0.32),
              uv, co, 0.0, 0.5)

    # Whorled leaves at nodes
    for node in range(2, 6):
        t = node / 6
        lc = pts[node].copy()
        n_whorl = 4
        for w in range(n_whorl):
            la = (w / n_whorl) * math.tau + rng.uniform(-0.2, 0.2)
            leaf_off = Vector((math.cos(la) * 0.12, math.sin(la) * 0.12, 0))
            make_leaf_card(bm, lc + leaf_off, 0.08, 0.18, la,
                          rng.uniform(-0.1, 0.2),
                          (0.16, 0.34, 0.06), t * 0.4 + 0.2, uv, co)

    # Domed pink-purple flower head at top
    top = pts[-1]
    for _ in range(8):
        fc = top + Vector((rng.uniform(-0.08, 0.08),
                           rng.uniform(-0.08, 0.08),
                           rng.uniform(-0.02, 0.06)))
        make_leaf_card(bm, fc, 0.04, 0.04, rng.uniform(0, math.tau),
                      rng.uniform(-0.2, 0.3),
                      (0.75, 0.30, 0.58), 0.9, uv, co)  # vivid mauve-rose

    return bm


def make_coneflower():
    """Green-headed coneflower (Rudbeckia laciniata) — 1.5-3m.
    Yellow drooping ray petals around green cone center."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(604)

    h = 2.0
    # Main stem
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.01, 0.01),
                           rng.uniform(-0.01, 0.01), h * t)))
    make_tube(bm, pts, 0.008, 0.004, 4,
              (0.20, 0.32, 0.08), (0.24, 0.36, 0.10),
              uv, co, 0.0, 0.5)

    # Deeply lobed leaves
    for node in range(2, 5):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.2 + rng.uniform(-0.3, 0.3)
            leaf_off = Vector((math.cos(la) * 0.1, math.sin(la) * 0.1, 0))
            make_leaf_card(bm, lc + leaf_off, 0.10, 0.14, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.36, 0.06), t * 0.4 + 0.2, uv, co)

    # Flower heads — branching top with 2-3 flowers
    for fl in range(2):
        ft = rng.uniform(0.7, 0.95)
        idx = min(int(ft * 6), 5)
        fc = pts[idx] + Vector((rng.uniform(-0.15, 0.15),
                                rng.uniform(-0.15, 0.15), 0.1))

        # Green cone center
        make_leaf_card(bm, fc, 0.03, 0.04, 0, 0.1,
                      (0.35, 0.50, 0.15), 0.95, uv, co)

        # Yellow drooping petals
        for p in range(6):
            pa = (p / 6) * math.tau
            pdx = math.cos(pa) * 0.04
            pdy = math.sin(pa) * 0.04
            pv = fc + Vector((pdx, pdy, -0.02))
            make_leaf_card(bm, pv, 0.02, 0.05, pa, -0.4,
                          (0.90, 0.80, 0.15), 0.92, uv, co)

    return bm


def make_cardinal_flower():
    """Cardinal flower (Lobelia cardinalis) — 0.6-1m.
    BRILLIANT SCARLET flower spike. The most intensely red native wildflower."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(605)

    h = 0.8
    pts = []
    for i in range(6):
        t = i / 5
        pts.append(Vector((0, 0, h * t)))
    make_tube(bm, pts, 0.005, 0.003, 4,
              (0.18, 0.28, 0.06), (0.22, 0.32, 0.08),
              uv, co, 0.0, 0.4)

    # Lance leaves
    for node in range(1, 4):
        t = node / 5
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.3 + rng.uniform(-0.2, 0.2)
            make_leaf_card(bm, lc + Vector((math.cos(la) * 0.04,
                                            math.sin(la) * 0.04, 0)),
                          0.04, 0.10, la, 0.1,
                          (0.14, 0.30, 0.05), t * 0.3 + 0.2, uv, co)

    # SCARLET flower spike — top 30% of stem
    for fi in range(6):
        ft = 0.55 + fi * 0.07
        fz = h * ft
        for fa in range(3):
            a = (fa / 3) * math.tau + fi * 0.5
            fx = math.cos(a) * 0.015
            fy = math.sin(a) * 0.015
            make_leaf_card(bm, Vector((fx, fy, fz)),
                          0.015, 0.02, a, 0.2,
                          (0.88, 0.08, 0.06), ft, uv, co)

    return bm


# ==========================================================================
# Species: BILLBOARD HERBS (crossed planes for viewing from any angle)
# ==========================================================================

def make_white_wood_aster():
    """White wood aster (Eurybia divaricata) — 0.3-0.6m.
    THE woodland floor wildflower. White carpet in autumn."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.3:
            return (0.22, 0.15, 0.10)  # dark zigzag stems
        elif t < 0.65:
            return (0.18, 0.38, 0.10)  # heart-shaped leaves
        else:
            return (0.90, 0.92, 0.85)  # white flower clusters

    make_crossed_planes(bm, 0.55, 0.30, 0.40, 3, 4, color_func, uv, co)
    return bm


def make_jewelweed():
    """Jewelweed (Impatiens capensis) — 0.6-1.5m.
    Translucent pale green, dense stream bank walls. Orange spotted flowers."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.15:
            return (0.25, 0.35, 0.15)  # stem base
        elif t < 0.75:
            # Translucent pale green — distinctive light color
            return (0.40, 0.58, 0.25)
        else:
            # Small orange flowers at tips
            g = 0.58 - (t - 0.75) * 2.0 * 0.30
            r = 0.40 + (t - 0.75) * 2.0 * 0.45
            return (min(r, 0.85), max(g, 0.40), 0.12)

    make_crossed_planes(bm, 1.0, 0.35, 0.45, 3, 4, color_func, uv, co)
    return bm


def make_mugwort():
    """Mugwort (Artemisia vulgaris) — 0.6-1.5m.
    SILVERY-WHITE leaf undersides flash in wind. Dark green upper."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.15:
            return (0.30, 0.24, 0.16)  # woody ridged stems
        elif t < 0.5:
            # Dark green upper surface — deeply lobed leaves
            return (0.22, 0.34, 0.16)
        else:
            # SILVERY-WHITE undersides — the key identifier, flashes in wind
            return (0.62, 0.66, 0.56)  # distinctly silvery-grey

    make_crossed_planes(bm, 1.0, 0.30, 0.45, 3, 4, color_func, uv, co)
    return bm


# ==========================================================================
# Species: FERNS (radial frond arrangements)
# ==========================================================================

def make_ostrich_fern():
    """Ostrich fern (Matteuccia struthiopteris) — 1-1.8m.
    TALLEST fern. Elegant vase-shaped clump of bright green fronds."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(801)

    n_fronds = 7
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.15, 0.15)
        # Vase shape: 30-45° outward lean, tips droop slightly
        make_frond(bm, Vector((0, 0, 0.05)),
                   length=1.6, width=0.14, segments=6,
                   arch=0.50, droop=0.28, angle_y=angle,
                   color_base=(0.10, 0.32, 0.04),
                   color_tip=(0.30, 0.52, 0.15),
                   uv_layer=uv, col_layer=co)

    # Brown fertile frond in center (shorter, darker)
    make_frond(bm, Vector((0, 0, 0.05)),
               length=0.9, width=0.04, segments=3,
               arch=0.12, droop=0.1, angle_y=rng.uniform(0, math.tau),
               color_base=(0.35, 0.22, 0.10),
               color_tip=(0.40, 0.28, 0.14),
               uv_layer=uv, col_layer=co)

    return bm


def make_christmas_fern():
    """Christmas fern (Polystichum acrostichoides) — 0.3-0.6m.
    EVERGREEN. Glossy deep green rosette on rocky slopes."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(802)

    n_fronds = 8
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.1, 0.1)
        # Low rosette: fronds more horizontal, shorter
        # Deep glossy leathery green — EVERGREEN, stays green through winter
        make_frond(bm, Vector((0, 0, 0.02)),
                   length=0.50, width=0.08, segments=4,
                   arch=0.85, droop=0.15, angle_y=angle,
                   color_base=(0.03, 0.16, 0.02),   # very deep green base
                   color_tip=(0.06, 0.24, 0.04),     # dark glossy green tip
                   uv_layer=uv, col_layer=co)

    return bm


# ==========================================================================
# Species: WETLAND
# ==========================================================================

def make_cattail():
    """Cattail (Typha latifolia) — 1.5-3m.
    THE wetland plant. Sword-like leaves + iconic brown spike."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(901)

    h = 2.0

    # 4-5 tall sword-like leaves
    for i in range(5):
        angle = (i / 5) * math.tau + rng.uniform(-0.2, 0.2)
        leaf_h = rng.uniform(1.4, 1.8)
        # Each leaf is a tall narrow strip, slight arch
        make_frond(bm, Vector((0, 0, 0.0)),
                   length=leaf_h, width=0.04, segments=4,
                   arch=0.25, droop=0.15, angle_y=angle,
                   color_base=(0.15, 0.35, 0.08),
                   color_tip=(0.28, 0.45, 0.15),
                   uv_layer=uv, col_layer=co)

    # Central stalk — taller than leaves
    stalk_pts = []
    for i in range(6):
        t = i / 5
        stalk_pts.append(Vector((0, 0, h * t)))
    make_tube(bm, stalk_pts, 0.008, 0.005, 4,
              (0.20, 0.32, 0.10), (0.25, 0.38, 0.14),
              uv, co, 0.0, 0.5)

    # Brown spike ("hot dog") near top — a thicker tube segment
    spike_base = h * 0.65
    spike_top = h * 0.80
    spike_pts = []
    for i in range(4):
        t = i / 3
        spike_pts.append(Vector((0, 0, spike_base + (spike_top - spike_base) * t)))
    # Brown "hot dog" spike — dark chocolate brown, iconic shape
    make_tube(bm, spike_pts, 0.022, 0.020, 6,
              (0.28, 0.14, 0.05), (0.32, 0.16, 0.06),  # dark chocolate brown
              uv, co, 0.7, 0.85)

    return bm


# ==========================================================================
# Species: TIER 3 — SHRUBS
# ==========================================================================

def make_sweet_pepperbush():
    """Sweet pepperbush (Clethra alnifolia) — 1-2.5m, upright suckering shrub.
    White bottlebrush flower spikes. Wetland edge."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1001)

    # Narrow upright form — suckering stems close together
    _make_shrub(bm, rng, n_stems=5, height=2.2, spread=0.9,
                stem_r=0.015, leaf_size=0.09,
                stem_color=(0.35, 0.28, 0.18),
                leaf_color=(0.22, 0.44, 0.10),
                zigzag=False, leaf_density=35,
                uv_layer=uv, col_layer=co)

    # White bottlebrush flower spikes at stem tips
    for _ in range(4):
        fc = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3),
                      rng.uniform(1.6, 2.1)))
        for fi in range(6):
            fv = fc + Vector((rng.uniform(-0.02, 0.02),
                              rng.uniform(-0.02, 0.02),
                              fi * 0.025 - 0.05))
            make_leaf_card(bm, fv, 0.025, 0.015, rng.uniform(0, math.tau),
                          0.1, (0.94, 0.96, 0.90), 0.92, uv, co)

    return bm


def make_flowering_raspberry():
    """Purple flowering raspberry (Rubus odoratus) — 1-2m, spreading.
    Large maple-like leaves (to 25cm), rose-purple flowers 5cm across."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1002)

    # Spreading shrub with large leaves — fewer stems, bigger leaves
    _make_shrub(bm, rng, n_stems=4, height=1.8, spread=1.6,
                stem_r=0.015, leaf_size=0.18,  # LARGE maple-like leaves
                stem_color=(0.38, 0.30, 0.20),
                leaf_color=(0.22, 0.42, 0.10),
                zigzag=False, leaf_density=24,
                uv_layer=uv, col_layer=co)

    # Rose-purple flowers (5cm across, scattered)
    for _ in range(5):
        fc = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6),
                      rng.uniform(1.0, 1.6)))
        # 5-petal flower
        for p in range(5):
            pa = (p / 5) * math.tau + rng.uniform(-0.1, 0.1)
            pv = fc + Vector((math.cos(pa) * 0.02, math.sin(pa) * 0.02, 0))
            make_leaf_card(bm, pv, 0.025, 0.025, pa, 0.1,
                          (0.72, 0.28, 0.55), 0.9, uv, co)

    return bm


# ==========================================================================
# Species: TIER 3 — TALL HERBS
# ==========================================================================

def make_white_snakeroot():
    """White snakeroot (Ageratina altissima) — 0.5-1.5m.
    Erect branching, white fluffy flower clusters at woodland edges."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1101)

    h = 1.2
    # Main stem
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.01, 0.01),
                           rng.uniform(-0.01, 0.01), h * t)))
    make_tube(bm, pts, 0.006, 0.003, 4,
              (0.22, 0.30, 0.10), (0.26, 0.34, 0.12),
              uv, co, 0.0, 0.5)

    # Heart-shaped toothed leaves along stem
    for node in range(2, 6):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.2 + rng.uniform(-0.3, 0.3)
            leaf_off = Vector((math.cos(la) * 0.08, math.sin(la) * 0.08, 0))
            make_leaf_card(bm, lc + leaf_off, 0.10, 0.08, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.36, 0.08), t * 0.4 + 0.2, uv, co)

    # Branching top with white flower corymbs
    for b in range(3):
        ba = rng.uniform(0, math.tau)
        bx = math.cos(ba) * 0.12
        by = math.sin(ba) * 0.12
        fc = pts[-1] + Vector((bx, by, rng.uniform(-0.05, 0.1)))
        for _ in range(8):
            fv = fc + Vector((rng.uniform(-0.06, 0.06),
                              rng.uniform(-0.06, 0.06),
                              rng.uniform(-0.02, 0.04)))
            make_leaf_card(bm, fv, 0.02, 0.02, rng.uniform(0, math.tau),
                          0.1, (0.94, 0.96, 0.92), 0.92, uv, co)

    return bm


def make_ironweed():
    """New York ironweed (Vernonia noveboracensis) — 1.2-2.4m.
    Stiff erect stems, deep purple fluffy disc flowers."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1102)

    h = 2.0
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.008, 0.008),
                           rng.uniform(-0.008, 0.008), h * t)))
    # Purple-tinged stem
    make_tube(bm, pts, 0.010, 0.005, 5,
              (0.25, 0.18, 0.24), (0.30, 0.22, 0.28),
              uv, co, 0.0, 0.5)

    # Lance leaves along stem
    for node in range(2, 6):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.3 + rng.uniform(-0.2, 0.2)
            leaf_off = Vector((math.cos(la) * 0.06, math.sin(la) * 0.06, 0))
            make_leaf_card(bm, lc + leaf_off, 0.06, 0.14, la,
                          rng.uniform(-0.1, 0.2),
                          (0.16, 0.32, 0.06), t * 0.3 + 0.2, uv, co)

    # Deep purple flower clusters at top — loose terminal arrangement
    for b in range(4):
        ba = rng.uniform(0, math.tau)
        fc = pts[-1] + Vector((math.cos(ba) * 0.10, math.sin(ba) * 0.10,
                               rng.uniform(-0.05, 0.1)))
        for _ in range(5):
            fv = fc + Vector((rng.uniform(-0.03, 0.03),
                              rng.uniform(-0.03, 0.03),
                              rng.uniform(-0.01, 0.03)))
            make_leaf_card(bm, fv, 0.025, 0.025, rng.uniform(0, math.tau),
                          0.2, (0.38, 0.05, 0.42), 0.92, uv, co)

    return bm


def make_rose_mallow():
    """Rose mallow (Hibiscus moscheutos) — 1-2m.
    ENORMOUS dinner-plate flowers 15-30cm across, white/pink with dark eye."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1103)

    h = 1.6
    # Sturdy single stem
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((0, 0, h * t)))
    make_tube(bm, pts, 0.012, 0.006, 5,
              (0.24, 0.32, 0.10), (0.28, 0.36, 0.12),
              uv, co, 0.0, 0.5)

    # Broad tropical-looking leaves
    for node in range(2, 6):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.1 + rng.uniform(-0.3, 0.3)
            leaf_off = Vector((math.cos(la) * 0.1, math.sin(la) * 0.1, 0))
            make_leaf_card(bm, lc + leaf_off, 0.14, 0.12, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.38, 0.08), t * 0.3 + 0.2, uv, co)

    # ENORMOUS flower at top — 20cm across, pink/white with dark center
    fc = pts[-1] + Vector((0.05, 0, 0.05))
    # 5 large overlapping petals
    for p in range(5):
        pa = (p / 5) * math.tau + rng.uniform(-0.1, 0.1)
        pv = fc + Vector((math.cos(pa) * 0.04, math.sin(pa) * 0.04, 0))
        make_leaf_card(bm, pv, 0.08, 0.10, pa, rng.uniform(-0.1, 0.2),
                      (0.90, 0.65, 0.72), 0.9, uv, co)  # soft pink
    # Dark eye center
    make_leaf_card(bm, fc, 0.04, 0.04, 0, 0.0,
                  (0.45, 0.05, 0.12), 0.95, uv, co)

    return bm


def make_burdock():
    """Burdock (Arctium spp.) — 0.8-1.5m.
    Very large heart-shaped leaves, round burr-like flower heads."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1104)

    h = 1.2
    pts = []
    for i in range(6):
        t = i / 5
        pts.append(Vector((rng.uniform(-0.01, 0.01),
                           rng.uniform(-0.01, 0.01), h * t)))
    make_tube(bm, pts, 0.015, 0.008, 5,
              (0.28, 0.25, 0.18), (0.32, 0.30, 0.22),
              uv, co, 0.0, 0.5)

    # VERY large basal leaves — up to 50cm, heart-shaped
    for node in range(1, 4):
        t = node / 5
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.0 + rng.uniform(-0.4, 0.4)
            leaf_off = Vector((math.cos(la) * 0.12, math.sin(la) * 0.12,
                              rng.uniform(-0.05, 0.02)))
            # Massive leaves — grey-green on underside
            size_scale = 1.3 - t * 0.5  # bigger at base
            make_leaf_card(bm, lc + leaf_off,
                          0.22 * size_scale, 0.18 * size_scale, la,
                          rng.uniform(-0.2, 0.1),
                          (0.20, 0.34, 0.10), t * 0.3 + 0.2, uv, co)

    # Round burr-like flower heads on upper branches
    for b in range(4):
        bt = rng.uniform(0.5, 0.9)
        idx = min(int(bt * 5), 4)
        ba = rng.uniform(0, math.tau)
        fc = pts[idx] + Vector((math.cos(ba) * 0.15, math.sin(ba) * 0.15,
                                rng.uniform(0.05, 0.15)))
        # Round purple-brown burr
        make_leaf_card(bm, fc, 0.035, 0.035, rng.uniform(0, math.tau),
                      0.0, (0.42, 0.18, 0.35), 0.9, uv, co)

    return bm


# ==========================================================================
# Species: TIER 3 — FERNS
# ==========================================================================

def make_cinnamon_fern():
    """Cinnamon fern (Osmundastrum cinnamomeum) — 0.6-1.2m.
    Blue-green sterile fronds in vase shape. CINNAMON-BROWN fertile fronds
    stand erect in center — unique visual signature."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1201)

    # Sterile fronds — blue-green, vase shape
    n_fronds = 6
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.15, 0.15)
        make_frond(bm, Vector((0, 0, 0.04)),
                   length=1.1, width=0.12, segments=5,
                   arch=0.48, droop=0.25, angle_y=angle,
                   color_base=(0.10, 0.28, 0.12),   # blue-green base
                   color_tip=(0.22, 0.42, 0.18),     # blue-green tip
                   uv_layer=uv, col_layer=co)

    # CINNAMON fertile fronds in center — 2-3 erect brown spikes
    for i in range(3):
        angle = (i / 3) * math.tau + rng.uniform(-0.3, 0.3)
        make_frond(bm, Vector((0, 0, 0.04)),
                   length=0.85, width=0.035, segments=3,
                   arch=0.08, droop=0.05, angle_y=angle,
                   color_base=(0.50, 0.28, 0.08),   # cinnamon brown
                   color_tip=(0.58, 0.32, 0.10),     # lighter cinnamon
                   uv_layer=uv, col_layer=co)

    return bm


def make_sensitive_fern():
    """Sensitive fern (Onoclea sensibilis) — 0.3-1m.
    Broad triangular fronds (unusual for fern). Coarse texture."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1202)

    # Broad triangular fronds — wider and coarser than typical ferns
    n_fronds = 5
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.2, 0.2)
        # Broader, more spreading fronds
        make_frond(bm, Vector((0, 0, 0.03)),
                   length=0.75, width=0.20, segments=4,  # WIDE
                   arch=0.65, droop=0.20, angle_y=angle,
                   color_base=(0.14, 0.32, 0.08),
                   color_tip=(0.28, 0.46, 0.16),
                   uv_layer=uv, col_layer=co)

    # Separate beaded fertile frond — dark, stiff
    make_frond(bm, Vector((0, 0, 0.03)),
               length=0.5, width=0.03, segments=3,
               arch=0.10, droop=0.05, angle_y=rng.uniform(0, math.tau),
               color_base=(0.28, 0.18, 0.08),
               color_tip=(0.32, 0.22, 0.10),
               uv_layer=uv, col_layer=co)

    return bm


# ==========================================================================
# Species: TIER 3 — GRASS
# ==========================================================================

def make_bottlebrush_grass():
    """Bottlebrush grass (Elymus hystrix) — 0.6-1.4m.
    Shade-tolerant woodland grass with distinctive seed heads."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1301)

    # Tufted clump — narrow grey-green leaves + seed stalks
    def color_func(t):
        if t < 0.1:
            return (0.28, 0.32, 0.16)  # base
        elif t < 0.6:
            return (0.32, 0.40, 0.22)  # grey-green blades
        elif t < 0.75:
            return (0.36, 0.38, 0.22)  # stalk
        else:
            # Straw-colored bottlebrush seed head
            return (0.58, 0.50, 0.28)

    make_crossed_planes(bm, 1.1, 0.22, 0.15, 3, 5, color_func, uv, co)

    # Extra seed head stalks sticking up
    for s in range(2):
        sa = rng.uniform(0, math.tau)
        sx = math.cos(sa) * 0.04
        sy = math.sin(sa) * 0.04
        stalk_pts = [
            Vector((sx, sy, 0.6)),
            Vector((sx * 1.1, sy * 1.1, 0.9)),
            Vector((sx * 1.2, sy * 1.2, 1.15)),
        ]
        make_tube(bm, stalk_pts, 0.003, 0.002, 3,
                  (0.36, 0.38, 0.22), (0.52, 0.46, 0.26),
                  uv, co, 0.6, 0.85)

    return bm


# ==========================================================================
# Species: TIER 3 — WETLAND
# ==========================================================================

def make_yellow_flag_iris():
    """Yellow flag iris (Iris pseudacorus) — 0.6-1.5m.
    Sword-shaped dark green leaves, bright yellow flowers."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1401)

    # 4-5 sword-like leaves — similar to cattail but shorter, stiffer
    for i in range(5):
        angle = (i / 5) * math.tau + rng.uniform(-0.25, 0.25)
        leaf_h = rng.uniform(0.8, 1.2)
        make_frond(bm, Vector((0, 0, 0.0)),
                   length=leaf_h, width=0.04, segments=4,
                   arch=0.20, droop=0.10, angle_y=angle,
                   color_base=(0.12, 0.30, 0.06),  # dark green
                   color_tip=(0.18, 0.38, 0.10),
                   uv_layer=uv, col_layer=co)

    # Flower stalk — taller than leaves
    stalk_pts = []
    for i in range(5):
        t = i / 4
        stalk_pts.append(Vector((0, 0, 1.2 * t)))
    make_tube(bm, stalk_pts, 0.006, 0.004, 4,
              (0.18, 0.30, 0.08), (0.22, 0.34, 0.10),
              uv, co, 0.0, 0.5)

    # Bright yellow flower at top — 3 drooping petals + 3 upright standards
    fc = stalk_pts[-1]
    for p in range(3):
        pa = (p / 3) * math.tau
        # Drooping falls
        pv = fc + Vector((math.cos(pa) * 0.04, math.sin(pa) * 0.04, -0.02))
        make_leaf_card(bm, pv, 0.035, 0.05, pa, -0.3,
                      (0.88, 0.82, 0.12), 0.9, uv, co)  # bright yellow
        # Upright standards
        pv2 = fc + Vector((math.cos(pa + 0.5) * 0.02, math.sin(pa + 0.5) * 0.02, 0.02))
        make_leaf_card(bm, pv2, 0.02, 0.04, pa + 0.5, 0.3,
                      (0.85, 0.78, 0.15), 0.9, uv, co)

    return bm


def make_lizards_tail():
    """Lizard's tail (Saururus cernuus) — 0.6-1.2m.
    Heart-shaped leaves, distinctive drooping white flower spikes that curve at tip."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1402)

    h = 0.9
    # Main stem
    pts = []
    for i in range(6):
        t = i / 5
        pts.append(Vector((rng.uniform(-0.01, 0.01),
                           rng.uniform(-0.01, 0.01), h * t)))
    make_tube(bm, pts, 0.006, 0.003, 4,
              (0.20, 0.30, 0.10), (0.24, 0.34, 0.12),
              uv, co, 0.0, 0.5)

    # Heart-shaped leaves
    for node in range(2, 5):
        t = node / 5
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.1 + rng.uniform(-0.2, 0.2)
            leaf_off = Vector((math.cos(la) * 0.08, math.sin(la) * 0.08, 0))
            make_leaf_card(bm, lc + leaf_off, 0.09, 0.08, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.40, 0.08), t * 0.3 + 0.2, uv, co)

    # Drooping curved white flower spike — the "lizard's tail"
    fc = pts[-1]
    spike_pts = []
    for i in range(5):
        t = i / 4
        # Curves downward and to one side
        spike_pts.append(Vector((
            fc.x + t * 0.08,
            fc.y,
            fc.z + 0.03 - t * 0.10  # droops
        )))
    make_tube(bm, spike_pts, 0.010, 0.005, 5,
              (0.92, 0.94, 0.86), (0.96, 0.97, 0.90),  # white
              uv, co, 0.85, 0.95)

    return bm


def make_phragmites():
    """Common reed / Phragmites (Phragmites australis) — 2-5m.
    Tall rigid tan stems, large feathery purplish-brown seed heads.
    Creates dense monoculture reed beds."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1403)

    # Cluster of 3-4 tall reed stems
    for s in range(4):
        h = rng.uniform(2.8, 3.8)
        ox = rng.uniform(-0.15, 0.15)
        oy = rng.uniform(-0.15, 0.15)

        pts = []
        for i in range(8):
            t = i / 7
            pts.append(Vector((
                ox + rng.uniform(-0.005, 0.005),
                oy + rng.uniform(-0.005, 0.005),
                h * t
            )))

        # Rigid tan stems
        make_tube(bm, pts, 0.012, 0.008, 5,
                  (0.35, 0.38, 0.18), (0.42, 0.40, 0.22),
                  uv, co, 0.0, 0.5)

        # Long arching leaves at nodes
        for node in range(3, 7):
            t = node / 7
            lc = pts[node].copy()
            la = rng.uniform(0, math.tau)
            make_frond(bm, lc,
                       length=0.45, width=0.04, segments=3,
                       arch=0.70, droop=0.30, angle_y=la,
                       color_base=(0.28, 0.35, 0.14),
                       color_tip=(0.38, 0.40, 0.20),
                       uv_layer=uv, col_layer=co)

        # Feathery plume at top — purplish-brown
        top = pts[-1]
        for _ in range(8):
            pa = rng.uniform(0, math.tau)
            pr = rng.uniform(0, 0.06)
            pz = rng.uniform(-0.08, 0.15)
            pv = top + Vector((math.cos(pa) * pr, math.sin(pa) * pr, pz))
            make_leaf_card(bm, pv, 0.015, 0.06, pa,
                          rng.uniform(-0.2, 0.3),
                          (0.50, 0.30, 0.32), 0.85, uv, co)

    return bm


# ==========================================================================
# Build all species
# ==========================================================================

SPECIES = [
    # Tier 1+2 (original 16)
    (make_spicebush,          "Shrub_Spicebush"),
    (make_witch_hazel,        "Shrub_WitchHazel"),
    (make_viburnum,           "Shrub_Viburnum"),
    (make_sumac,              "Shrub_Sumac"),
    (make_elderberry,         "Shrub_Elderberry"),
    (make_pokeweed,           "Herb_Pokeweed"),
    (make_japanese_knotweed,  "Herb_JapaneseKnotweed"),
    (make_joe_pye_weed,       "Herb_JoePyeWeed"),
    (make_coneflower,         "Herb_Coneflower"),
    (make_cardinal_flower,    "Herb_CardinalFlower"),
    (make_white_wood_aster,   "Herb_WhiteWoodAster"),
    (make_jewelweed,          "Herb_Jewelweed"),
    (make_mugwort,            "Herb_Mugwort"),
    (make_ostrich_fern,       "Fern_Ostrich"),
    (make_christmas_fern,     "Fern_Christmas"),
    (make_cattail,            "Wetland_Cattail"),
    # Tier 3 (12 new species)
    (make_sweet_pepperbush,   "Shrub_SweetPepperbush"),
    (make_flowering_raspberry, "Shrub_FloweringRaspberry"),
    (make_white_snakeroot,    "Herb_WhiteSnakeroot"),
    (make_ironweed,           "Herb_Ironweed"),
    (make_rose_mallow,        "Herb_RoseMallow"),
    (make_burdock,            "Herb_Burdock"),
    (make_cinnamon_fern,      "Fern_Cinnamon"),
    (make_sensitive_fern,     "Fern_Sensitive"),
    (make_bottlebrush_grass,  "Grass_Bottlebrush"),
    (make_yellow_flag_iris,   "Wetland_YellowIris"),
    (make_lizards_tail,       "Wetland_LizardsTail"),
    (make_phragmites,         "Wetland_Phragmites"),
]

if __name__ == "__main__":
    print("=" * 60)
    print(f"Building {len(SPECIES)} undergrowth species")
    print("=" * 60)

    for func, name in SPECIES:
        print(f"\n  Building {name}...")
        clear_scene()
        bm = func()
        finalize_and_export(bm, name)

    print(f"\n{'=' * 60}")
    print(f"Done — {len(SPECIES)} undergrowth GLBs exported")
    print("=" * 60)

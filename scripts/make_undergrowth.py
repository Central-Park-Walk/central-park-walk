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


def make_leaf_quad(bm, center, width, height, angle_y, tilt, color,
                   uv_y, uv_layer, col_layer):
    """Single billboard leaf quad at given position and orientation."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    ct, st = math.cos(tilt), math.sin(tilt)
    hw, hh = width * 0.5, height * 0.5

    # Quad corners in local frame, rotated by angle_y around Z, tilted
    dx = Vector((ca, sa, 0))
    dz = Vector((-sa * st, ca * st, ct))

    v0 = bm.verts.new(center - dx * hw - dz * hh)
    v1 = bm.verts.new(center + dx * hw - dz * hh)
    v2 = bm.verts.new(center + dx * hw + dz * hh)
    v3 = bm.verts.new(center - dx * hw + dz * hh)
    col_rgba = list(color[:3]) + [1.0] if len(color) == 3 else list(color)
    try:
        f = bm.faces.new([v0, v1, v2, v3])
        for loop in f.loops:
            loop[uv_layer].uv = (0.5, uv_y)
            loop[col_layer] = col_rgba
    except ValueError:
        pass


def make_crossed_planes(bm, height, width_base, width_top, n_planes, segments,
                        color_func, uv_layer, col_layer):
    """Create n_planes vertical billboard planes crossing at center.
    color_func(t) returns (r,g,b) for height fraction t."""
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

            v0 = bm.verts.new((-ca * w0, -sa * w0, z0))
            v1 = bm.verts.new((ca * w0, sa * w0, z0))
            v2 = bm.verts.new((ca * w1, sa * w1, z1))
            v3 = bm.verts.new((-ca * w1, -sa * w1, z1))
            try:
                f = bm.faces.new([v0, v1, v2, v3])
                for loop in f.loops:
                    if loop.vert in (v0, v1):
                        loop[uv_layer].uv = (0.5, t0)
                        loop[col_layer] = c0
                    else:
                        loop[uv_layer].uv = (0.5, t1)
                        loop[col_layer] = c1
            except ValueError:
                pass


def make_frond(bm, origin, length, width, segments, arch, droop, angle_y,
               color_base, color_tip, uv_layer, col_layer):
    """Create one fern frond as a curved tapered strip."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    verts = []
    for i in range(segments + 1):
        t = i / segments
        # Frond curves up then droops
        rise = length * 0.7 * t * (1.0 - t * droop)
        out = length * t * arch
        fw = width * (1.0 - t * 0.7) * 0.5  # taper

        cx = origin.x + ca * out
        cy = origin.y + sa * out
        cz = origin.z + rise

        # Perpendicular to frond direction in XY plane
        px, py = -sa * fw, ca * fw

        col = _lerp_color(color_base, color_tip, t)
        uv_y = t

        vl = bm.verts.new((cx + px, cy + py, cz))
        vr = bm.verts.new((cx - px, cy - py, cz))
        verts.append((vl, vr, uv_y, col))

    for i in range(segments):
        vl0, vr0, uv0, c0 = verts[i]
        vl1, vr1, uv1, c1 = verts[i + 1]
        try:
            f = bm.faces.new([vl0, vr0, vr1, vl1])
            for loop in f.loops:
                if loop.vert in (vl0, vr0):
                    loop[uv_layer].uv = (0.5, uv0)
                    loop[col_layer] = c0
                else:
                    loop[uv_layer].uv = (0.5, uv1)
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
    """Generic multi-stem shrub with leaf billboard clusters."""
    stem_color_tip = [min(c + 0.08, 1.0) for c in stem_color]

    for s in range(n_stems):
        angle = (s / n_stems) * math.tau + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.15, 0.45) * spread
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean

        # Build stem path with optional zigzag
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

        r_base = stem_r * rng.uniform(0.8, 1.2)
        make_tube(bm, pts, r_base, r_base * 0.25, 4,
                  stem_color, stem_color_tip, uv_layer, col_layer,
                  uv_y_start=0.0, uv_y_end=0.5)

        # Sub-branches
        n_sub = rng.randint(1, 3)
        for sb in range(n_sub):
            branch_t = rng.uniform(0.4, 0.8)
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
            make_tube(bm, sub_pts, r_base * 0.3, r_base * 0.1, 4,
                      stem_color, stem_color_tip, uv_layer, col_layer,
                      uv_y_start=0.3, uv_y_end=0.6)

        # Leaf quads along upper portion of stem
        for i in range(leaf_density):
            lt = rng.uniform(0.4, 1.0)
            idx = min(int(lt * (n_seg - 1)), n_seg - 1)
            lc = pts[idx].copy()
            lc.x += rng.uniform(-0.15, 0.15) * spread
            lc.y += rng.uniform(-0.15, 0.15) * spread
            lc.z += rng.uniform(-0.1, 0.1) * height
            la = rng.uniform(0, math.tau)
            lt_angle = rng.uniform(-0.3, 0.5)
            lw = leaf_size * rng.uniform(0.7, 1.3)
            lh = leaf_size * rng.uniform(0.8, 1.4)
            make_leaf_quad(bm, lc, lw, lh, la, lt_angle, leaf_color,
                          lt * 0.5 + 0.3, uv_layer, col_layer)


def make_spicebush():
    """Spicebush (Lindera benzoin) — THE dominant Central Park understory shrub.
    2-4m, multi-stemmed, open spreading form, zigzag branching."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(101)

    _make_shrub(bm, rng, n_stems=5, height=3.0, spread=1.8,
                stem_r=0.025, leaf_size=0.12,
                stem_color=(0.35, 0.28, 0.18),
                leaf_color=(0.22, 0.42, 0.12),
                zigzag=True, leaf_density=8,
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
                stem_r=0.035, leaf_size=0.16,
                stem_color=(0.40, 0.34, 0.25),
                leaf_color=(0.20, 0.38, 0.10),
                zigzag=True, leaf_density=7,
                uv_layer=uv, col_layer=co)

    return bm


def make_viburnum():
    """Arrowwood viburnum (Viburnum dentatum) — 2-3m, dense rounded form.
    Creates solid visual screens in understory."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(303)

    _make_shrub(bm, rng, n_stems=6, height=2.5, spread=1.5,
                stem_r=0.020, leaf_size=0.10,
                stem_color=(0.32, 0.26, 0.16),
                leaf_color=(0.18, 0.40, 0.08),
                zigzag=False, leaf_density=12,
                uv_layer=uv, col_layer=co)

    # Add white flower cluster at top
    for _ in range(3):
        fc = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3),
                      rng.uniform(1.8, 2.3)))
        for _ in range(5):
            make_leaf_quad(bm, fc + Vector((rng.uniform(-0.06, 0.06),
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

        # Flat-topped canopy: feathery compound leaf quads
        top = pts[-1]
        for _ in range(10):
            lc = top + Vector((rng.uniform(-0.6, 0.6),
                               rng.uniform(-0.6, 0.6),
                               rng.uniform(-0.2, 0.3)))
            make_leaf_quad(bm, lc, 0.25, 0.08, rng.uniform(0, math.tau),
                          rng.uniform(-0.1, 0.2),
                          (0.20, 0.38, 0.08), 0.8, uv, co)

        # Red fruit cluster at top
        fruit_c = top + Vector((0, 0, 0.15))
        for _ in range(4):
            fc = fruit_c + Vector((rng.uniform(-0.03, 0.03),
                                   rng.uniform(-0.03, 0.03),
                                   rng.uniform(-0.05, 0.05)))
            make_leaf_quad(bm, fc, 0.04, 0.06, rng.uniform(0, math.tau),
                          0.1, (0.72, 0.15, 0.10), 0.95, uv, co)

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
            make_leaf_quad(bm, lc, 0.14, 0.08, rng.uniform(0, math.tau),
                          rng.uniform(-0.2, 0.3),
                          (0.16, 0.36, 0.06), lt * 0.4 + 0.3, uv, co)

        # White flower cluster near top
        fc = pts[-2] + Vector((0, 0, 0.1))
        for _ in range(6):
            fv = fc + Vector((rng.uniform(-0.08, 0.08),
                              rng.uniform(-0.08, 0.08),
                              rng.uniform(-0.02, 0.04)))
            make_leaf_quad(bm, fv, 0.03, 0.03, rng.uniform(0, math.tau),
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
              (0.65, 0.12, 0.30), (0.72, 0.18, 0.38),  # magenta!
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
        make_leaf_quad(bm, leaf_c, 0.18, 0.28, ba,
                      rng.uniform(-0.1, 0.2),
                      (0.15, 0.35, 0.06), bt * 0.5 + 0.2, uv, co)

    # Drooping berry raceme at top
    top = main_pts[-1]
    for b in range(5):
        bt = b / 4
        bc = top + Vector((rng.uniform(-0.02, 0.02),
                           rng.uniform(-0.02, 0.02),
                           -bt * 0.15 + 0.05))
        make_leaf_quad(bm, bc, 0.03, 0.03, rng.uniform(0, math.tau),
                      0.0, (0.25, 0.05, 0.20), 0.95, uv, co)

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

        # Green stem with purple speckles (represented as brownish-green)
        make_tube(bm, pts, 0.018, 0.012, 5,
                  (0.28, 0.38, 0.12), (0.32, 0.42, 0.15),
                  uv, co, 0.0, 0.5)

        # Large heart-shaped leaves at nodes
        for node in range(3, 7):
            t = node / 7
            lc = pts[node].copy()
            for side in range(2):
                la = (s / 4) * math.tau + side * math.pi + rng.uniform(-0.3, 0.3)
                leaf_off = Vector((math.cos(la) * 0.2, math.sin(la) * 0.2, 0.02))
                make_leaf_quad(bm, lc + leaf_off, 0.15, 0.12, la,
                              rng.uniform(-0.2, 0.1),
                              (0.18, 0.40, 0.08), t * 0.4 + 0.3, uv, co)

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
            make_leaf_quad(bm, lc + leaf_off, 0.08, 0.18, la,
                          rng.uniform(-0.1, 0.2),
                          (0.16, 0.34, 0.06), t * 0.4 + 0.2, uv, co)

    # Domed pink-purple flower head at top
    top = pts[-1]
    for _ in range(8):
        fc = top + Vector((rng.uniform(-0.08, 0.08),
                           rng.uniform(-0.08, 0.08),
                           rng.uniform(-0.02, 0.06)))
        make_leaf_quad(bm, fc, 0.04, 0.04, rng.uniform(0, math.tau),
                      rng.uniform(-0.2, 0.3),
                      (0.68, 0.35, 0.55), 0.9, uv, co)

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
            make_leaf_quad(bm, lc + leaf_off, 0.10, 0.14, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.36, 0.06), t * 0.4 + 0.2, uv, co)

    # Flower heads — branching top with 2-3 flowers
    for fl in range(2):
        ft = rng.uniform(0.7, 0.95)
        idx = min(int(ft * 6), 5)
        fc = pts[idx] + Vector((rng.uniform(-0.15, 0.15),
                                rng.uniform(-0.15, 0.15), 0.1))

        # Green cone center
        make_leaf_quad(bm, fc, 0.03, 0.04, 0, 0.1,
                      (0.35, 0.50, 0.15), 0.95, uv, co)

        # Yellow drooping petals
        for p in range(6):
            pa = (p / 6) * math.tau
            pdx = math.cos(pa) * 0.04
            pdy = math.sin(pa) * 0.04
            pv = fc + Vector((pdx, pdy, -0.02))
            make_leaf_quad(bm, pv, 0.02, 0.05, pa, -0.4,
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
            make_leaf_quad(bm, lc + Vector((math.cos(la) * 0.04,
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
            make_leaf_quad(bm, Vector((fx, fy, fz)),
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

    make_crossed_planes(bm, 0.40, 0.25, 0.35, 3, 4, color_func, uv, co)
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

    make_crossed_planes(bm, 0.80, 0.30, 0.40, 3, 4, color_func, uv, co)
    return bm


def make_mugwort():
    """Mugwort (Artemisia vulgaris) — 0.6-1.5m.
    SILVERY-WHITE leaf undersides flash in wind. Dark green upper."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.15:
            return (0.30, 0.24, 0.16)  # woody stem base
        elif t < 0.5:
            # Mix of green upper and silvery under — reads as grey-green
            return (0.35, 0.42, 0.28)
        else:
            # Upper foliage — more silvery, the distinctive feature
            return (0.55, 0.58, 0.48)

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
        # Vase shape: fronds arch outward
        make_frond(bm, Vector((0, 0, 0.05)),
                   length=1.3, width=0.12, segments=5,
                   arch=0.7, droop=0.3, angle_y=angle,
                   color_base=(0.10, 0.32, 0.04),
                   color_tip=(0.30, 0.52, 0.15),
                   uv_layer=uv, col_layer=co)

    # Brown fertile frond in center (shorter, darker)
    make_frond(bm, Vector((0, 0, 0.05)),
               length=0.7, width=0.04, segments=3,
               arch=0.15, droop=0.1, angle_y=rng.uniform(0, math.tau),
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
        make_frond(bm, Vector((0, 0, 0.02)),
                   length=0.38, width=0.06, segments=4,
                   arch=0.85, droop=0.15, angle_y=angle,
                   color_base=(0.06, 0.22, 0.03),
                   color_tip=(0.12, 0.32, 0.06),
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
    make_tube(bm, spike_pts, 0.022, 0.020, 6,
              (0.38, 0.22, 0.08), (0.42, 0.25, 0.10),
              uv, co, 0.7, 0.85)

    return bm


# ==========================================================================
# Build all species
# ==========================================================================

SPECIES = [
    # (builder_func, output_name)
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

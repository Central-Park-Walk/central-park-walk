"""Create undergrowth vegetation models for Central Park Walk.

28 species across 5 vertical layers — the missing vegetation between
ankle height and tree canopy that makes wild areas feel real.

Run: blender --background --python scripts/make_undergrowth.py

Outputs to models/vegetation/:
  Shrub_Spicebush.glb          — 3m, dominant understory shrub
  Shrub_WitchHazel.glb         — 4m, large zigzag understory
  Shrub_Viburnum.glb           — 2.5m, dense screening shrub
  Shrub_Sumac.glb              — 4m, flat-topped colony shrub
  Shrub_Elderberry.glb         — 3m, arching woodland edge
  Shrub_SweetPepperbush.glb    — 2.2m, bottlebrush flowers, wetland edge
  Shrub_FloweringRaspberry.glb — 1.8m, large leaves, rose-purple flowers
  Herb_Pokeweed.glb            — 2m, magenta stems (signature)
  Herb_JapaneseKnotweed.glb    — 3m, invasive bamboo-like thicket
  Herb_JoePyeWeed.glb          — 2m, tall pink wetland flower
  Herb_Coneflower.glb          — 2m, yellow drooping petals
  Herb_CardinalFlower.glb      — 0.8m, scarlet spike
  Herb_WhiteSnakeroot.glb      — 1.2m, white corymbs
  Herb_Ironweed.glb            — 2m, deep purple flowers
  Herb_RoseMallow.glb          — 1.6m, enormous flowers
  Herb_Burdock.glb             — 1.2m, massive leaves, burrs
  Herb_WhiteWoodAster.glb      — 0.4m, woodland floor carpet
  Herb_Jewelweed.glb           — 0.8m, stream bank
  Herb_Mugwort.glb             — 1m, silvery invasive
  Fern_Ostrich.glb             — 1.3m, tall vase-shaped
  Fern_Christmas.glb           — 0.4m, evergreen rosette
  Fern_Cinnamon.glb            — 1.1m, cinnamon fertile fronds
  Fern_Sensitive.glb           — 0.75m, broad triangular fronds
  Grass_Bottlebrush.glb        — 1.1m, shade-tolerant woodland grass
  Wetland_Cattail.glb          — 2m, iconic pond edge
  Wetland_YellowIris.glb       — 1.2m, bright yellow iris
  Wetland_LizardsTail.glb      — 0.9m, drooping white spikes
  Wetland_Phragmites.glb       — 3m, tall reed beds
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
        export_vertex_color='ACTIVE',
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
    """6-triangle leaf card with UV mapped for procedural alpha cutout.
    UV.x spans 0-1 across leaf width, UV.y spans 0-1 base to tip.
    Shader uses these UVs to generate a natural leaf silhouette.
    Shape: base → lower-right(30%) → mid-right widest(45%) → tip →
           mid-left widest(45%) → lower-left(30%) → midrib center(Z offset).
    _uv_y is accepted for call-site compatibility but ignored."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    ct, st = math.cos(tilt), math.sin(tilt)
    hw, hh = width * 0.5, height * 0.5

    dx = Vector((ca, sa, 0))
    dz = Vector((-sa * st, ca * st, ct))
    # Small forward offset for midrib curvature
    doff = Vector((sa * ct * 0.03, -ca * ct * 0.03, st * 0.03))

    # 7 vertices
    vbase  = bm.verts.new(center - dz * hh)                         # UV (0.5, 0.0)
    vrl    = bm.verts.new(center + dx * hw * 0.55 - dz * hh * 0.40)  # UV (1.0, 0.30) lower-right
    vrm    = bm.verts.new(center + dx * hw        - dz * hh * 0.05)  # UV (1.0, 0.45) mid-right widest
    vtip   = bm.verts.new(center + dz * hh)                         # UV (0.5, 1.0)
    vlm    = bm.verts.new(center - dx * hw        - dz * hh * 0.05)  # UV (0.0, 0.45) mid-left widest
    vll    = bm.verts.new(center - dx * hw * 0.55 - dz * hh * 0.40)  # UV (0.0, 0.30) lower-left
    vmid   = bm.verts.new(center + doff)                              # UV (0.5, 0.50) midrib

    col_rgba = list(color[:3]) + [1.0] if len(color) == 3 else list(color)

    uv_map = {
        id(vbase): (0.5, 0.0),
        id(vrl):   (1.0, 0.30),
        id(vrm):   (1.0, 0.45),
        id(vtip):  (0.5, 1.0),
        id(vlm):   (0.0, 0.45),
        id(vll):   (0.0, 0.30),
        id(vmid):  (0.5, 0.50),
    }

    # 5 triangles forming the leaf silhouette
    tris = [
        [vbase, vrl, vmid],   # lower-right lobe base
        [vrl,   vrm, vmid],   # right upper lobe
        [vrm,   vtip, vmid],  # right tip sector
        [vtip,  vlm, vmid],   # left tip sector
        [vlm,   vll, vmid],   # left upper lobe
        # close bottom: [vll, vbase, vmid] — 6th tri completes the shape
        [vll,   vbase, vmid],
    ]
    for tri in tris:
        try:
            f = bm.faces.new(tri)
            for loop in f.loops:
                loop[uv_layer].uv = uv_map[id(loop.vert)]
                loop[col_layer] = col_rgba
        except ValueError:
            pass


def make_crossed_planes(bm, height, width_base, width_top, n_planes, segments,
                        color_func, uv_layer, col_layer, fold=0.0):
    """Create n_planes vertical billboard planes crossing at center.
    UV.x spans 0-1 across each plane width (for shader leaf alpha cutout).
    UV.y spans 0-1 from base to tip. color_func(t) returns (r,g,b).
    fold > 0 gives V-shaped cross section by pushing segment-center vertices outward."""
    for p in range(n_planes):
        angle = (p / n_planes) * math.pi
        ca, sa = math.cos(angle), math.sin(angle)
        # Perpendicular direction for fold push (outward from plane normal)
        fold_dx = -sa
        fold_dy = ca

        for s in range(segments):
            t0 = s / segments
            t1 = (s + 1) / segments
            z0 = height * t0
            z1 = height * t1
            w0 = (width_base + (width_top - width_base) * t0) * 0.5
            w1 = (width_base + (width_top - width_base) * t1) * 0.5
            c0 = list(color_func(t0)) + [1.0]
            c1 = list(color_func(t1)) + [1.0]

            if fold > 0.0:
                # Split each quad into 2 tris with center verts pushed out
                # Bottom edge
                vL0 = bm.verts.new((-ca * w0, -sa * w0, z0))
                vR0 = bm.verts.new((ca * w0, sa * w0, z0))
                # Top edge
                vL1 = bm.verts.new((-ca * w1, -sa * w1, z1))
                vR1 = bm.verts.new((ca * w1, sa * w1, z1))
                # Center verts pushed outward (V-shape fold)
                fc0 = fold * (w0 + w1) * 0.5
                vC0 = bm.verts.new((fold_dx * fc0, fold_dy * fc0, (z0 + z1) * 0.5))
                vC1 = bm.verts.new((-fold_dx * fc0, -fold_dy * fc0, (z0 + z1) * 0.5))

                for verts_set, center_v in [([vL0, vC0, vL1], vC0), ([vR0, vR1, vC0], vC0)]:
                    uv_map_fold = {
                        id(vL0): (0.0, t0), id(vR0): (1.0, t0),
                        id(vL1): (0.0, t1), id(vR1): (1.0, t1),
                        id(vC0): (0.5, (t0 + t1) * 0.5), id(vC1): (0.5, (t0 + t1) * 0.5),
                    }
                    try:
                        f = bm.faces.new(verts_set)
                        for loop in f.loops:
                            uv_val = uv_map_fold.get(id(loop.vert), (0.5, (t0 + t1) * 0.5))
                            loop[uv_layer].uv = uv_val
                            if loop.vert in (vL0, vR0):
                                loop[col_layer] = c0
                            else:
                                loop[col_layer] = c1
                    except ValueError:
                        pass
                # Second half of V (other side)
                for verts_set in [[vL0, vL1, vC1], [vR0, vC1, vR1]]:
                    uv_map_fold2 = {
                        id(vL0): (0.0, t0), id(vR0): (1.0, t0),
                        id(vL1): (0.0, t1), id(vR1): (1.0, t1),
                        id(vC1): (0.5, (t0 + t1) * 0.5),
                    }
                    try:
                        f = bm.faces.new(verts_set)
                        for loop in f.loops:
                            uv_val = uv_map_fold2.get(id(loop.vert), (0.5, (t0 + t1) * 0.5))
                            loop[uv_layer].uv = uv_val
                            if loop.vert in (vL0, vR0):
                                loop[col_layer] = c0
                            else:
                                loop[col_layer] = c1
                    except ValueError:
                        pass
            else:
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
    """Create one fern frond as a curved tapered strip (rachis).
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
    return verts  # return for pinnae attachment


def make_pinnate_frond(bm, origin, length, n_segments, n_pinnae_per_side,
                       pinna_length, pinna_width, arch, droop, angle_y,
                       colors, uv_layer, col_layer):
    """Pinnate frond: narrow central rachis with paired pinna leaf cards.
    colors = (color_base, color_tip) for the rachis and pinnae.
    Pinnae taper toward tip. Each pinna uses make_leaf_card."""
    color_base, color_tip = colors
    ca, sa = math.cos(angle_y), math.sin(angle_y)

    # Build rachis points
    rachis_pts = []
    for i in range(n_segments + 1):
        t = i / n_segments
        rise = length * 0.72 * t * (1.0 - t * droop)
        out = length * t * arch
        rachis_pts.append(Vector((
            origin.x + ca * out,
            origin.y + sa * out,
            origin.z + rise
        )))

    # Narrow rachis strip (width = pinna_width * 0.18 so it's thin)
    rachis_w = pinna_width * 0.18
    rachis_verts = []
    for i, pt in enumerate(rachis_pts):
        t = i / n_segments
        fw = rachis_w * (1.0 - t * 0.5) * 0.5
        px, py = -sa * fw, ca * fw
        col = _lerp_color(color_base, color_tip, t)
        vl = bm.verts.new((pt.x + px, pt.y + py, pt.z))
        vr = bm.verts.new((pt.x - px, pt.y - py, pt.z))
        rachis_verts.append((vl, vr, t, col))

    for i in range(n_segments):
        vl0, vr0, uv0, c0 = rachis_verts[i]
        vl1, vr1, uv1, c1 = rachis_verts[i + 1]
        try:
            f = bm.faces.new([vl0, vr0, vr1, vl1])
            uv_map = {id(vl0): (0.0, uv0), id(vr0): (1.0, uv0),
                      id(vr1): (1.0, uv1), id(vl1): (0.0, uv1)}
            for loop in f.loops:
                loop[uv_layer].uv = uv_map[id(loop.vert)]
                loop[col_layer] = c0 if loop.vert in (vl0, vr0) else c1
        except ValueError:
            pass

    # Attach pinnae along rachis
    # Pinnae are placed at evenly-spaced segments, skipping the base
    pinna_spacing = max(1, n_segments // (n_pinnae_per_side + 1))
    for pi in range(n_pinnae_per_side):
        seg_idx = pi * pinna_spacing + 1
        if seg_idx >= len(rachis_pts):
            break
        t = seg_idx / n_segments
        pt = rachis_pts[seg_idx]
        # Taper: pinnae get smaller toward tip
        taper = 1.0 - t * 0.65
        pl = pinna_length * taper
        pw = pinna_width * taper

        # Angle of rachis at this segment
        if seg_idx < n_segments:
            dp = rachis_pts[seg_idx + 1] - rachis_pts[seg_idx]
        else:
            dp = rachis_pts[seg_idx] - rachis_pts[seg_idx - 1]
        rachis_angle = math.atan2(dp.y, dp.x)

        # Pinnae spread outward from rachis plane at ~45-60°
        for side in [-1, 1]:
            pinna_angle = rachis_angle + side * (math.pi * 0.5 + 0.3)
            pinna_tilt = side * 0.45  # tilt outward from rachis plane
            pinna_color = _lerp_color(color_base, color_tip, t)[:3]
            make_leaf_card(bm,
                           pt + Vector((side * rachis_w * 0.5, 0, 0)),
                           pw, pl, pinna_angle, pinna_tilt,
                           pinna_color, t, uv_layer, col_layer)


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
    Leaves start low (20% height) and spread wide to fill the crown.
    Upgraded: more stems, more sub-branches, tertiary twigs, 5-sided main stems."""
    # Stems: lighter, greener — blend toward leaf color so they disappear
    stem_blend = [stem_color[i] * 0.6 + leaf_color[i] * 0.4 for i in range(3)]
    stem_color_tip = [min(c + 0.06, 1.0) for c in stem_blend]

    # Increase n_stems by ~50%
    actual_stems = int(n_stems * 1.5)

    for s in range(actual_stems):
        angle = (s / actual_stems) * math.tau + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.15, 0.45) * spread
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean

        pts = []
        n_seg = 7
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

        # Main stem: 5-sided for visual roundness
        r_base = stem_r * rng.uniform(0.7, 1.0)
        make_tube(bm, pts, r_base, r_base * 0.2, 5,
                  stem_blend, stem_color_tip, uv_layer, col_layer,
                  uv_y_start=0.0, uv_y_end=0.5)

        # Sub-branches: 2-4 per stem
        n_sub = rng.randint(2, 4)
        for sb in range(n_sub):
            branch_t = rng.uniform(0.3, 0.75)
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
            make_tube(bm, sub_pts, r_base * 0.28, r_base * 0.09, 4,
                      stem_blend, stem_color_tip, uv_layer, col_layer,
                      uv_y_start=0.3, uv_y_end=0.6)

            # Tertiary twigs: 1-2 short twigs off each sub-branch
            n_tert = rng.randint(1, 2)
            for tb in range(n_tert):
                twig_t = rng.uniform(0.4, 0.85)
                twig_idx = min(int(twig_t * 2), 1)
                twig_origin = sub_pts[twig_idx].copy()
                twig_angle = sub_angle + rng.uniform(-1.4, 1.4)
                twig_len = sub_len * rng.uniform(0.3, 0.55)
                twig_dx = math.cos(twig_angle)
                twig_dy = math.sin(twig_angle)
                twig_pts = [
                    twig_origin,
                    Vector((twig_origin.x + twig_dx * twig_len * 0.5,
                             twig_origin.y + twig_dy * twig_len * 0.5,
                             twig_origin.z + twig_len * 0.35)),
                    Vector((twig_origin.x + twig_dx * twig_len,
                             twig_origin.y + twig_dy * twig_len,
                             twig_origin.z + twig_len * 0.12)),
                ]
                make_tube(bm, twig_pts, r_base * 0.12, r_base * 0.04, 3,
                          stem_blend, stem_color_tip, uv_layer, col_layer,
                          uv_y_start=0.4, uv_y_end=0.65)

        # Dense leaf cards — tripled density, start LOW (20% height), spread WIDE
        for i in range(leaf_density * 3):
            lt = rng.uniform(0.20, 1.0)
            idx = min(int(lt * (n_seg - 1)), n_seg - 1)
            lc = pts[idx].copy()
            lc.x += rng.uniform(-0.28, 0.28) * spread
            lc.y += rng.uniform(-0.28, 0.28) * spread
            lc.z += rng.uniform(-0.08, 0.14) * height
            la = rng.uniform(0, math.tau)
            lt_angle = rng.uniform(-0.3, 0.5)
            lw = leaf_size * rng.uniform(0.7, 1.3)
            lh = leaf_size * rng.uniform(0.8, 1.4)
            make_leaf_card(bm, lc, lw, lh, la, lt_angle, leaf_color,
                          lt * 0.5 + 0.3, uv_layer, col_layer)


def make_spicebush():
    """Spicebush (Lindera benzoin) — THE dominant Central Park understory shrub.
    2-4m, multi-stemmed, open spreading form, zigzag branching. ~2000 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(101)

    # Glossy aromatic leaves — warmer yellow-green, dense understory
    _make_shrub(bm, rng, n_stems=8, height=3.0, spread=1.8,
                stem_r=0.020, leaf_size=0.10,
                stem_color=(0.30, 0.25, 0.14),
                leaf_color=(0.30, 0.48, 0.12),
                zigzag=True, leaf_density=50,
                uv_layer=uv, col_layer=co)

    return bm


def make_witch_hazel():
    """Witch hazel (Hamamelis virginiana) — 3-5m, open irregular crown,
    larger than spicebush, distinctive zigzag architecture. ~1800 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(202)

    _make_shrub(bm, rng, n_stems=6, height=4.0, spread=2.2,
                stem_r=0.025, leaf_size=0.13,
                stem_color=(0.34, 0.30, 0.20),
                leaf_color=(0.20, 0.38, 0.10),
                zigzag=True, leaf_density=40,
                uv_layer=uv, col_layer=co)

    return bm


def make_viburnum():
    """Arrowwood viburnum (Viburnum dentatum) — 2-3m, dense rounded form.
    Creates solid visual screens in understory. ~2500 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(303)

    # Glossy dark green toothed leaves — dense visual screen
    _make_shrub(bm, rng, n_stems=8, height=2.5, spread=1.5,
                stem_r=0.015, leaf_size=0.08,
                stem_color=(0.22, 0.28, 0.12),
                leaf_color=(0.10, 0.32, 0.05),
                zigzag=False, leaf_density=60,
                uv_layer=uv, col_layer=co)

    # White flower corymbs at top — multiple clusters
    for _ in range(6):
        fc = Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4),
                      rng.uniform(1.8, 2.4)))
        for _ in range(8):
            make_leaf_card(bm, fc + Vector((rng.uniform(-0.07, 0.07),
                                            rng.uniform(-0.07, 0.07),
                                            rng.uniform(-0.03, 0.03))),
                          0.04, 0.04, rng.uniform(0, math.tau), 0.1,
                          (0.92, 0.94, 0.88), 0.9, uv, co)

    return bm


def make_sumac():
    """Staghorn sumac (Rhus typhina) — 3-5m, flat-topped, colony-forming.
    Feathery compound leaves, red fruit clusters, velvety stems. ~1800 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(404)

    # 4 thick velvety stems (6-sided for visual roundness)
    for s in range(4):
        angle = (s / 4) * math.tau + rng.uniform(-0.3, 0.3)
        lean = rng.uniform(0.3, 0.8)
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean
        h = rng.uniform(3.5, 4.5)

        pts = []
        for i in range(7):
            t = i / 6
            pts.append(Vector((dx * t, dy * t, h * t * (1.0 - 0.05 * t))))
        make_tube(bm, pts, 0.045, 0.018, 6,
                  (0.45, 0.30, 0.18), (0.50, 0.35, 0.22),
                  uv, co, 0.0, 0.4)

        # Compound pinnate leaf branches radiating from top
        top = pts[-1]
        n_leaf_branches = 6
        for lb in range(n_leaf_branches):
            la = (lb / n_leaf_branches) * math.tau + rng.uniform(-0.3, 0.3)
            lb_len = rng.uniform(0.5, 0.9)
            lb_dx = math.cos(la) * lb_len
            lb_dy = math.sin(la) * lb_len
            lb_pts = [
                top,
                Vector((top.x + lb_dx * 0.4, top.y + lb_dy * 0.4, top.z + 0.1)),
                Vector((top.x + lb_dx, top.y + lb_dy, top.z - 0.05)),
            ]
            make_tube(bm, lb_pts, 0.008, 0.003, 3,
                      (0.38, 0.25, 0.14), (0.42, 0.30, 0.16),
                      uv, co, 0.4, 0.6)
            # Feathery pinnate leaflets along branch
            for lf in range(8):
                lt = lf / 7
                lc_idx = min(int(lt * 2), 1)
                lc = lb_pts[lc_idx] + Vector((lb_dx * lt * 0.5, lb_dy * lt * 0.5, 0))
                make_leaf_card(bm, lc, 0.14, 0.06, la + rng.uniform(-0.3, 0.3),
                              rng.uniform(-0.1, 0.2),
                              (0.18, 0.42, 0.06), 0.8, uv, co)

        # Fuzzy crimson-red fruit cluster at top — vivid upright cone
        fruit_c = top + Vector((0, 0, 0.18))
        for _ in range(8):
            fc = fruit_c + Vector((rng.uniform(-0.04, 0.04),
                                   rng.uniform(-0.04, 0.04),
                                   rng.uniform(-0.06, 0.06)))
            make_leaf_card(bm, fc, 0.045, 0.065, rng.uniform(0, math.tau),
                          0.1, (0.82, 0.10, 0.06), 0.95, uv, co)

    return bm


def make_elderberry():
    """Elderberry (Sambucus canadensis) — 2-3.5m, arching multi-stemmed.
    Compound leaves, large white flower clusters. ~1500 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(505)

    for s in range(5):
        angle = (s / 5) * math.tau + rng.uniform(-0.4, 0.4)
        lean = rng.uniform(0.4, 1.0)
        dx, dy = math.cos(angle) * lean, math.sin(angle) * lean
        h = rng.uniform(2.5, 3.2)

        # Arching stem path
        pts = []
        for i in range(8):
            t = i / 7
            arch_drop = -0.4 * t * t
            pts.append(Vector((
                dx * t * 1.2, dy * t * 1.2,
                h * t * (1.0 - 0.15 * t) + arch_drop
            )))
        make_tube(bm, pts, 0.024, 0.009, 5,
                  (0.38, 0.30, 0.20), (0.42, 0.36, 0.24),
                  uv, co, 0.0, 0.5)

        # Sub-branches
        n_sub = rng.randint(2, 3)
        for sb in range(n_sub):
            bi = rng.randint(3, 6)
            sub_origin = pts[bi].copy()
            sub_angle = angle + rng.uniform(-1.0, 1.0)
            sub_len = h * rng.uniform(0.22, 0.38)
            sdx, sdy = math.cos(sub_angle), math.sin(sub_angle)
            sub_pts = [
                sub_origin,
                Vector((sub_origin.x + sdx * sub_len * 0.5,
                        sub_origin.y + sdy * sub_len * 0.5,
                        sub_origin.z + sub_len * 0.3)),
                Vector((sub_origin.x + sdx * sub_len,
                        sub_origin.y + sdy * sub_len,
                        sub_origin.z + sub_len * 0.1)),
            ]
            make_tube(bm, sub_pts, 0.009, 0.004, 3,
                      (0.38, 0.30, 0.20), (0.42, 0.36, 0.24),
                      uv, co, 0.3, 0.6)

        # Compound leaf quads along upper stem — pinnate leaflets
        for lf in range(8):
            lt = rng.uniform(0.35, 0.95)
            idx = min(int(lt * 7), 6)
            lc = pts[idx] + Vector((rng.uniform(-0.18, 0.18),
                                    rng.uniform(-0.18, 0.18),
                                    rng.uniform(-0.05, 0.1)))
            make_leaf_card(bm, lc, 0.15, 0.09, rng.uniform(0, math.tau),
                          rng.uniform(-0.2, 0.3),
                          (0.22, 0.44, 0.10), lt * 0.4 + 0.3, uv, co)

        # White flower cluster near top
        fc = pts[-2] + Vector((0, 0, 0.1))
        for _ in range(10):
            fv = fc + Vector((rng.uniform(-0.10, 0.10),
                              rng.uniform(-0.10, 0.10),
                              rng.uniform(-0.03, 0.05)))
            make_leaf_card(bm, fv, 0.035, 0.035, rng.uniform(0, math.tau),
                          0.1, (0.92, 0.94, 0.86), 0.92, uv, co)

    return bm


def make_sweet_pepperbush():
    """Sweet pepperbush (Clethra alnifolia) — 1-2.5m, upright suckering shrub.
    White bottlebrush flower spikes. Wetland edge. ~1800 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1001)

    # Narrow upright form — suckering stems close together
    _make_shrub(bm, rng, n_stems=7, height=2.2, spread=0.9,
                stem_r=0.015, leaf_size=0.09,
                stem_color=(0.35, 0.28, 0.18),
                leaf_color=(0.22, 0.44, 0.10),
                zigzag=False, leaf_density=40,
                uv_layer=uv, col_layer=co)

    # White bottlebrush flower spikes at stem tips — more spikes, denser
    for _ in range(6):
        fc = Vector((rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35),
                      rng.uniform(1.5, 2.1)))
        for fi in range(10):
            fv = fc + Vector((rng.uniform(-0.025, 0.025),
                              rng.uniform(-0.025, 0.025),
                              fi * 0.022 - 0.07))
            make_leaf_card(bm, fv, 0.028, 0.018, rng.uniform(0, math.tau),
                          0.1, (0.94, 0.96, 0.90), 0.92, uv, co)

    return bm


def make_flowering_raspberry():
    """Purple flowering raspberry (Rubus odoratus) — 1-2m, spreading.
    Large maple-like leaves (to 25cm), rose-purple flowers 5cm across. ~1200 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1002)

    # Spreading shrub with large leaves — fewer stems, bigger leaves
    _make_shrub(bm, rng, n_stems=5, height=1.8, spread=1.6,
                stem_r=0.015, leaf_size=0.18,
                stem_color=(0.38, 0.30, 0.20),
                leaf_color=(0.22, 0.42, 0.10),
                zigzag=False, leaf_density=28,
                uv_layer=uv, col_layer=co)

    # Rose-purple flowers (5cm across, scattered)
    for _ in range(7):
        fc = Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6),
                      rng.uniform(0.9, 1.6)))
        # 5-petal flower
        for p in range(5):
            pa = (p / 5) * math.tau + rng.uniform(-0.1, 0.1)
            pv = fc + Vector((math.cos(pa) * 0.022, math.sin(pa) * 0.022, 0))
            make_leaf_card(bm, pv, 0.028, 0.028, pa, 0.1,
                          (0.72, 0.28, 0.55), 0.9, uv, co)

    return bm


# ==========================================================================
# Species: TALL HERBACEOUS (stem + leaves + flowers)
# ==========================================================================

def make_pokeweed():
    """Pokeweed (Phytolacca americana) — 1.2-3m, MAGENTA/PURPLE stems.
    The signature color. Large leaves, drooping purple berry clusters. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(601)

    h = 2.0
    # Main stem — MAGENTA is the signature, 6-sided
    main_pts = []
    for i in range(9):
        t = i / 8
        main_pts.append(Vector((
            rng.uniform(-0.025, 0.025),
            rng.uniform(-0.025, 0.025),
            h * t
        )))
    make_tube(bm, main_pts, 0.030, 0.012, 6,
              (0.72, 0.08, 0.35), (0.80, 0.12, 0.42),
              uv, co, 0.0, 0.6)

    # Side branches with large leaves — 3 branches
    for b in range(3):
        bt = 0.25 + b * 0.22
        idx = min(int(bt * 8), 7)
        origin = main_pts[idx].copy()
        ba = rng.uniform(0, math.tau)
        bl = rng.uniform(0.35, 0.65)
        bdx, bdy = math.cos(ba) * bl, math.sin(ba) * bl
        branch_pts = [
            origin,
            Vector((origin.x + bdx * 0.5, origin.y + bdy * 0.5, origin.z + 0.12)),
            Vector((origin.x + bdx, origin.y + bdy, origin.z + 0.08)),
        ]
        make_tube(bm, branch_pts, 0.012, 0.005, 4,
                  (0.65, 0.10, 0.32), (0.70, 0.12, 0.38),
                  uv, co, 0.3, 0.6)
        # Large elliptical leaf
        leaf_c = branch_pts[-1]
        make_leaf_card(bm, leaf_c, 0.20, 0.30, ba,
                      rng.uniform(-0.1, 0.2),
                      (0.15, 0.35, 0.06), bt * 0.5 + 0.2, uv, co)
        # Additional smaller leaves
        for _ in range(4):
            lc = origin + Vector((rng.uniform(-0.15, 0.15),
                                  rng.uniform(-0.15, 0.15),
                                  rng.uniform(0.05, 0.25)))
            make_leaf_card(bm, lc, 0.16, 0.22, rng.uniform(0, math.tau),
                          rng.uniform(-0.2, 0.3),
                          (0.15, 0.35, 0.06), bt * 0.4 + 0.2, uv, co)

    # 2 drooping berry racemes at top
    for raceme in range(2):
        top = main_pts[-1] + Vector((rng.uniform(-0.04, 0.04),
                                      rng.uniform(-0.04, 0.04), 0))
        for b in range(8):
            bt = b / 7
            bc = top + Vector((rng.uniform(-0.025, 0.025),
                               rng.uniform(-0.025, 0.025),
                               -bt * 0.20 + 0.06))
            make_leaf_card(bm, bc, 0.028, 0.028, rng.uniform(0, math.tau),
                          0.0, (0.12, 0.02, 0.12), 0.95, uv, co)

    return bm


def make_japanese_knotweed():
    """Japanese knotweed (Fallopia japonica) — 2-4.5m, bamboo-like thicket.
    THE invasive that defines disturbed areas. Dense walls of vegetation. ~500 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(602)

    for s in range(5):
        h = rng.uniform(2.5, 3.5)
        ox = rng.uniform(-0.30, 0.30)
        oy = rng.uniform(-0.30, 0.30)

        # Thick bamboo-like stem with nodes — 6-sided
        pts = []
        for i in range(9):
            t = i / 8
            pts.append(Vector((
                ox + rng.uniform(-0.012, 0.012),
                oy + rng.uniform(-0.012, 0.012),
                h * t
            )))

        make_tube(bm, pts, 0.020, 0.013, 6,
                  (0.32, 0.35, 0.14), (0.38, 0.38, 0.18),
                  uv, co, 0.0, 0.5)

        # Node rings (small dark ring at each node — visual marker)
        for node in [2, 4, 6]:
            if node < len(pts):
                np = pts[node]
                node_ring_pts = [
                    np + Vector((0, 0, -0.02)),
                    np + Vector((0, 0, 0)),
                    np + Vector((0, 0, 0.02)),
                ]
                make_tube(bm, node_ring_pts, 0.022, 0.022, 6,
                          (0.25, 0.28, 0.10), (0.25, 0.28, 0.10),
                          uv, co, 0.5, 0.5)

        # Large heart-shaped leaves at nodes
        for node in range(3, 8):
            t = node / 8
            lc = pts[node].copy()
            for side in range(2):
                la = (s / 5) * math.tau + side * math.pi + rng.uniform(-0.3, 0.3)
                leaf_off = Vector((math.cos(la) * 0.22, math.sin(la) * 0.22, 0.02))
                make_leaf_card(bm, lc + leaf_off, 0.20, 0.16, la,
                              rng.uniform(-0.2, 0.1),
                              (0.20, 0.46, 0.08), t * 0.4 + 0.3, uv, co)

        # Flower sprays near top — small white clusters
        top = pts[-1]
        for _ in range(4):
            fa = rng.uniform(0, math.tau)
            fv = top + Vector((math.cos(fa) * 0.08, math.sin(fa) * 0.08,
                               rng.uniform(-0.05, 0.12)))
            make_leaf_card(bm, fv, 0.025, 0.025, fa, 0.1,
                          (0.92, 0.94, 0.88), 0.9, uv, co)

    return bm


def make_joe_pye_weed():
    """Joe Pye weed (Eutrochium spp.) — 1.2-3m, tall wetland wildflower.
    Large domed pink-purple flower heads. Whorled leaves. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(603)

    h = 2.0
    pts = []
    for i in range(8):
        t = i / 7
        pts.append(Vector((rng.uniform(-0.015, 0.015),
                           rng.uniform(-0.015, 0.015), h * t)))

    # Purple-tinged stem — 6-sided
    make_tube(bm, pts, 0.016, 0.009, 6,
              (0.30, 0.22, 0.28), (0.35, 0.25, 0.32),
              uv, co, 0.0, 0.5)

    # Whorled leaves at 4 nodes — 4-6 leaves per whorl
    for node in range(2, 6):
        t = node / 7
        lc = pts[node].copy()
        n_whorl = rng.randint(4, 6)
        for w in range(n_whorl):
            la = (w / n_whorl) * math.tau + rng.uniform(-0.15, 0.15)
            leaf_off = Vector((math.cos(la) * 0.14, math.sin(la) * 0.14, 0))
            make_leaf_card(bm, lc + leaf_off, 0.09, 0.20, la,
                          rng.uniform(-0.1, 0.2),
                          (0.16, 0.34, 0.06), t * 0.4 + 0.2, uv, co)

    # Large domed pink-purple flower head at top
    top = pts[-1]
    for _ in range(14):
        fc = top + Vector((rng.uniform(-0.10, 0.10),
                           rng.uniform(-0.10, 0.10),
                           rng.uniform(-0.02, 0.07)))
        make_leaf_card(bm, fc, 0.045, 0.045, rng.uniform(0, math.tau),
                      rng.uniform(-0.2, 0.3),
                      (0.75, 0.30, 0.58), 0.9, uv, co)

    # 2 side flowers on branching stems
    for sf in range(2):
        sa = rng.uniform(0, math.tau)
        spt = pts[-2] + Vector((math.cos(sa) * 0.14, math.sin(sa) * 0.14, 0.06))
        for _ in range(7):
            fv = spt + Vector((rng.uniform(-0.07, 0.07),
                               rng.uniform(-0.07, 0.07),
                               rng.uniform(-0.02, 0.04)))
            make_leaf_card(bm, fv, 0.038, 0.038, rng.uniform(0, math.tau),
                          0.2, (0.70, 0.25, 0.52), 0.88, uv, co)

    return bm


def make_coneflower():
    """Green-headed coneflower (Rudbeckia laciniata) — 1.5-3m.
    Yellow drooping ray petals around green cone center. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(604)

    h = 2.0
    # Main stem
    pts = []
    for i in range(8):
        t = i / 7
        pts.append(Vector((rng.uniform(-0.012, 0.012),
                           rng.uniform(-0.012, 0.012), h * t)))
    make_tube(bm, pts, 0.009, 0.005, 5,
              (0.20, 0.32, 0.08), (0.24, 0.36, 0.10),
              uv, co, 0.0, 0.5)

    # 2 branching side stems
    for br in range(2):
        bi = rng.randint(4, 6)
        ba = rng.uniform(0, math.tau)
        bl = rng.uniform(0.35, 0.55)
        bpts = [
            pts[bi].copy(),
            pts[bi] + Vector((math.cos(ba) * bl * 0.5, math.sin(ba) * bl * 0.5,
                              bl * 0.3)),
            pts[bi] + Vector((math.cos(ba) * bl, math.sin(ba) * bl, bl * 0.15)),
        ]
        make_tube(bm, bpts, 0.005, 0.003, 4,
                  (0.20, 0.32, 0.08), (0.24, 0.36, 0.10),
                  uv, co, 0.3, 0.6)
        # Flower head on branch
        fc_b = bpts[-1]
        make_leaf_card(bm, fc_b, 0.03, 0.04, 0, 0.1,
                      (0.35, 0.50, 0.15), 0.95, uv, co)
        for p in range(8):
            pa = (p / 8) * math.tau
            pv = fc_b + Vector((math.cos(pa) * 0.045, math.sin(pa) * 0.045, -0.025))
            make_leaf_card(bm, pv, 0.022, 0.055, pa, -0.45,
                          (0.90, 0.80, 0.15), 0.92, uv, co)

    # 8 deeply lobed leaves
    for node in range(2, 6):
        t = node / 7
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.2 + rng.uniform(-0.3, 0.3)
            leaf_off = Vector((math.cos(la) * 0.12, math.sin(la) * 0.12, 0))
            make_leaf_card(bm, lc + leaf_off, 0.12, 0.16, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.36, 0.06), t * 0.4 + 0.2, uv, co)

    # Main flower head — top
    fc = pts[-1]
    make_leaf_card(bm, fc, 0.035, 0.045, 0, 0.1,
                  (0.35, 0.50, 0.15), 0.95, uv, co)
    for p in range(10):
        pa = (p / 10) * math.tau
        pv = fc + Vector((math.cos(pa) * 0.05, math.sin(pa) * 0.05, -0.03))
        make_leaf_card(bm, pv, 0.025, 0.060, pa, -0.45,
                      (0.90, 0.80, 0.15), 0.92, uv, co)

    return bm


def make_cardinal_flower():
    """Cardinal flower (Lobelia cardinalis) — 0.6-1m.
    BRILLIANT SCARLET flower spike. The most intensely red native wildflower. ~300 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(605)

    h = 0.8
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.008, 0.008),
                           rng.uniform(-0.008, 0.008), h * t)))
    make_tube(bm, pts, 0.006, 0.003, 5,
              (0.18, 0.28, 0.06), (0.22, 0.32, 0.08),
              uv, co, 0.0, 0.4)

    # 8 lance leaves along stem
    for node in range(1, 5):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.3 + rng.uniform(-0.2, 0.2)
            make_leaf_card(bm, lc + Vector((math.cos(la) * 0.045,
                                            math.sin(la) * 0.045, 0)),
                          0.045, 0.11, la, 0.1,
                          (0.14, 0.30, 0.05), t * 0.3 + 0.2, uv, co)

    # SCARLET flower spike — 10 tiers, top 40% of stem
    for fi in range(10):
        ft = 0.52 + fi * 0.048
        fz = h * ft
        for fa in range(3):
            a = (fa / 3) * math.tau + fi * 0.6
            fx = math.cos(a) * 0.016
            fy = math.sin(a) * 0.016
            make_leaf_card(bm, Vector((fx, fy, fz)),
                          0.016, 0.022, a, 0.2,
                          (0.88, 0.08, 0.06), ft, uv, co)

    return bm


def make_white_snakeroot():
    """White snakeroot (Ageratina altissima) — 0.5-1.5m.
    Erect branching, white fluffy flower clusters at woodland edges. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1101)

    h = 1.2
    # Main stem — 5-sided
    pts = []
    for i in range(8):
        t = i / 7
        pts.append(Vector((rng.uniform(-0.012, 0.012),
                           rng.uniform(-0.012, 0.012), h * t)))
    make_tube(bm, pts, 0.007, 0.003, 5,
              (0.22, 0.30, 0.10), (0.26, 0.34, 0.12),
              uv, co, 0.0, 0.5)

    # 3 branching side stems
    for b in range(3):
        bi = rng.randint(4, 6)
        ba = rng.uniform(0, math.tau)
        bl = h * rng.uniform(0.22, 0.38)
        bdx, bdy = math.cos(ba) * bl, math.sin(ba) * bl
        bpts = [
            pts[bi].copy(),
            pts[bi] + Vector((bdx * 0.5, bdy * 0.5, bl * 0.35)),
            pts[bi] + Vector((bdx, bdy, bl * 0.12)),
        ]
        make_tube(bm, bpts, 0.004, 0.002, 4,
                  (0.22, 0.30, 0.10), (0.26, 0.34, 0.12),
                  uv, co, 0.3, 0.6)
        # White corymb cluster on branch tip
        for _ in range(10):
            fv = bpts[-1] + Vector((rng.uniform(-0.07, 0.07),
                                    rng.uniform(-0.07, 0.07),
                                    rng.uniform(-0.02, 0.04)))
            make_leaf_card(bm, fv, 0.022, 0.022, rng.uniform(0, math.tau),
                          0.1, (0.94, 0.96, 0.92), 0.92, uv, co)

    # Heart-shaped toothed leaves along main stem — 10 leaves
    for node in range(2, 7):
        t = node / 7
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.2 + rng.uniform(-0.3, 0.3)
            leaf_off = Vector((math.cos(la) * 0.09, math.sin(la) * 0.09, 0))
            make_leaf_card(bm, lc + leaf_off, 0.11, 0.09, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.36, 0.08), t * 0.4 + 0.2, uv, co)

    # Top corymb cluster
    for _ in range(10):
        fv = pts[-1] + Vector((rng.uniform(-0.07, 0.07),
                               rng.uniform(-0.07, 0.07),
                               rng.uniform(-0.02, 0.06)))
        make_leaf_card(bm, fv, 0.022, 0.022, rng.uniform(0, math.tau),
                      0.1, (0.94, 0.96, 0.92), 0.92, uv, co)

    return bm


def make_ironweed():
    """New York ironweed (Vernonia noveboracensis) — 1.2-2.4m.
    Stiff erect stems, deep purple fluffy disc flowers. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1102)

    h = 2.0
    pts = []
    for i in range(8):
        t = i / 7
        pts.append(Vector((rng.uniform(-0.009, 0.009),
                           rng.uniform(-0.009, 0.009), h * t)))
    # Purple-tinged stem — 6-sided
    make_tube(bm, pts, 0.011, 0.005, 6,
              (0.25, 0.18, 0.24), (0.30, 0.22, 0.28),
              uv, co, 0.0, 0.5)

    # 10 lance leaves along stem
    for node in range(2, 7):
        t = node / 7
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.3 + rng.uniform(-0.2, 0.2)
            leaf_off = Vector((math.cos(la) * 0.07, math.sin(la) * 0.07, 0))
            make_leaf_card(bm, lc + leaf_off, 0.065, 0.16, la,
                          rng.uniform(-0.1, 0.2),
                          (0.16, 0.32, 0.06), t * 0.3 + 0.2, uv, co)

    # 4 deep purple flower clusters at top — loose terminal arrangement
    for b in range(4):
        ba = rng.uniform(0, math.tau)
        fc = pts[-1] + Vector((math.cos(ba) * 0.12, math.sin(ba) * 0.12,
                               rng.uniform(-0.06, 0.12)))
        for _ in range(7):
            fv = fc + Vector((rng.uniform(-0.035, 0.035),
                              rng.uniform(-0.035, 0.035),
                              rng.uniform(-0.012, 0.032)))
            make_leaf_card(bm, fv, 0.028, 0.028, rng.uniform(0, math.tau),
                          0.2, (0.38, 0.05, 0.42), 0.92, uv, co)

    return bm


def make_rose_mallow():
    """Rose mallow (Hibiscus moscheutos) — 1-2m.
    ENORMOUS dinner-plate flowers 15-30cm across, white/pink with dark eye. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1103)

    h = 1.6
    # Sturdy single stem — 6-sided
    pts = []
    for i in range(8):
        t = i / 7
        pts.append(Vector((rng.uniform(-0.008, 0.008),
                           rng.uniform(-0.008, 0.008), h * t)))
    make_tube(bm, pts, 0.014, 0.007, 6,
              (0.24, 0.32, 0.10), (0.28, 0.36, 0.12),
              uv, co, 0.0, 0.5)

    # 16 broad tropical-looking leaves
    for node in range(1, 7):
        t = node / 7
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.1 + rng.uniform(-0.3, 0.3)
            leaf_off = Vector((math.cos(la) * 0.12, math.sin(la) * 0.12, 0))
            make_leaf_card(bm, lc + leaf_off, 0.16, 0.14, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.38, 0.08), t * 0.3 + 0.2, uv, co)

    # ENORMOUS main flower at top — 8 overlapping petals
    fc_main = pts[-1] + Vector((0.05, 0, 0.06))
    for p in range(8):
        pa = (p / 8) * math.tau + rng.uniform(-0.08, 0.08)
        pv = fc_main + Vector((math.cos(pa) * 0.05, math.sin(pa) * 0.05, 0))
        make_leaf_card(bm, pv, 0.09, 0.12, pa, rng.uniform(-0.12, 0.22),
                      (0.90, 0.65, 0.72), 0.9, uv, co)
    # Dark eye center
    make_leaf_card(bm, fc_main, 0.04, 0.04, 0, 0.0,
                  (0.45, 0.05, 0.12), 0.95, uv, co)

    # Second large flower at node below
    fc2 = pts[-2] + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0.04))
    for p in range(8):
        pa = (p / 8) * math.tau + rng.uniform(-0.08, 0.08)
        pv = fc2 + Vector((math.cos(pa) * 0.045, math.sin(pa) * 0.045, 0))
        make_leaf_card(bm, pv, 0.08, 0.10, pa, rng.uniform(-0.12, 0.22),
                      (0.88, 0.60, 0.70), 0.9, uv, co)
    make_leaf_card(bm, fc2, 0.035, 0.035, 0, 0.0,
                  (0.45, 0.05, 0.12), 0.95, uv, co)

    return bm


def make_burdock():
    """Burdock (Arctium spp.) — 0.8-1.5m.
    Very large heart-shaped leaves, round burr-like flower heads. ~350 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1104)

    h = 1.2
    # Main stem — 5-sided
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.012, 0.012),
                           rng.uniform(-0.012, 0.012), h * t)))
    make_tube(bm, pts, 0.017, 0.009, 5,
              (0.28, 0.25, 0.18), (0.32, 0.30, 0.22),
              uv, co, 0.0, 0.5)

    # 3 side branches
    for b in range(3):
        bi = rng.randint(2, 5)
        ba = rng.uniform(0, math.tau)
        bl = rng.uniform(0.25, 0.45)
        bpts = [
            pts[bi].copy(),
            pts[bi] + Vector((math.cos(ba) * bl * 0.5, math.sin(ba) * bl * 0.5, bl * 0.3)),
            pts[bi] + Vector((math.cos(ba) * bl, math.sin(ba) * bl, bl * 0.08)),
        ]
        make_tube(bm, bpts, 0.008, 0.004, 4,
                  (0.28, 0.25, 0.18), (0.32, 0.30, 0.22),
                  uv, co, 0.3, 0.6)

    # 8 massive leaves — grey-green, biggest at base
    for node in range(1, 5):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.0 + rng.uniform(-0.4, 0.4)
            leaf_off = Vector((math.cos(la) * 0.14, math.sin(la) * 0.14,
                              rng.uniform(-0.06, 0.02)))
            size_scale = 1.35 - t * 0.55
            make_leaf_card(bm, lc + leaf_off,
                          0.24 * size_scale, 0.20 * size_scale, la,
                          rng.uniform(-0.2, 0.1),
                          (0.20, 0.34, 0.10), t * 0.3 + 0.2, uv, co)

    # 6 round burr-like flower heads on upper branches
    for b in range(6):
        bt = rng.uniform(0.45, 0.92)
        idx = min(int(bt * 6), 5)
        ba = rng.uniform(0, math.tau)
        fc = pts[idx] + Vector((math.cos(ba) * 0.17, math.sin(ba) * 0.17,
                                rng.uniform(0.06, 0.18)))
        make_leaf_card(bm, fc, 0.038, 0.038, rng.uniform(0, math.tau),
                      0.0, (0.42, 0.18, 0.35), 0.9, uv, co)
        # Small bracts around each burr
        for br in range(4):
            bra = (br / 4) * math.tau
            brv = fc + Vector((math.cos(bra) * 0.025, math.sin(bra) * 0.025, 0))
            make_leaf_card(bm, brv, 0.018, 0.025, bra, 0.2,
                          (0.35, 0.15, 0.28), 0.88, uv, co)

    return bm


# ==========================================================================
# Species: SMALL HERBS (stem + leaf cards — replaced crossed-plane billboards)
# ==========================================================================

def make_white_wood_aster():
    """White wood aster (Eurybia divaricata) — 0.3-0.6m.
    THE woodland floor wildflower. White carpet in autumn. Zigzag dark stems
    with heart-shaped leaves and loose corymbs of small white flowers. ~250 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    H = 0.55
    # 3 zigzag stems from a common base (asters are clumping)
    for si in range(3):
        angle = si * math.tau / 3 + 0.2
        lean_x = math.cos(angle) * 0.04
        lean_y = math.sin(angle) * 0.04
        pts = []
        for j in range(7):
            t = j / 6
            zz = H * t
            # Zigzag offset alternating at each node
            zig = 0.02 * (1 if j % 2 == 0 else -1)
            pts.append(Vector((lean_x * t + zig, lean_y * t + zig * 0.5, zz)))
        make_tube(bm, pts, 0.006, 0.003, 4,
                  (0.22, 0.15, 0.10), (0.18, 0.12, 0.08), uv, co)

        # Heart-shaped leaves at nodes 1-4, alternating sides
        for li in range(4):
            lt = (li + 1) / 6
            lz = H * lt
            la = angle + (math.pi * 0.4 if li % 2 == 0 else -math.pi * 0.4)
            lc = Vector((lean_x * lt + 0.015 * math.cos(la),
                         lean_y * lt + 0.015 * math.sin(la), lz))
            sz = 0.06 - li * 0.008  # lower leaves larger
            make_leaf_card(bm, lc, sz, sz * 1.3, la, 0.25,
                           (0.18, 0.38, 0.10), lt, uv, co)

        # White flower corymb at top — 5 tiny flower cards
        for fi in range(5):
            fa = angle + fi * math.tau / 5
            fr = 0.02
            fc = Vector((lean_x + math.cos(fa) * fr,
                         lean_y + math.sin(fa) * fr,
                         H * 0.92 + fi * 0.01))
            make_leaf_card(bm, fc, 0.018, 0.015, fa, 0.1,
                           (0.92, 0.93, 0.88), 0.95, uv, co)

    return bm


def make_jewelweed():
    """Jewelweed (Impatiens capensis) — 0.6-1.5m.
    Translucent pale-green succulent stems, serrated ovate leaves.
    Orange spotted flowers dangle like tiny cornucopias. ~300 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    H = 1.0
    # 2 main stems (jewelweed grows in dense patches, translucent)
    for si in range(2):
        angle = si * math.pi + 0.3
        lean = 0.06 * si
        pts = []
        for j in range(8):
            t = j / 7
            pts.append(Vector((math.cos(angle) * lean * t,
                               math.sin(angle) * lean * t,
                               H * t)))
        make_tube(bm, pts, 0.010, 0.005, 4,
                  (0.35, 0.50, 0.18), (0.45, 0.60, 0.22), uv, co)

        # Ovate leaves at nodes 2-6, alternating
        for li in range(5):
            lt = (li + 2) / 7
            lz = H * lt
            la = angle + (math.pi * 0.45 if li % 2 == 0 else -math.pi * 0.45)
            off = 0.02
            lc = Vector((math.cos(angle) * lean * lt + math.cos(la) * off,
                         math.sin(angle) * lean * lt + math.sin(la) * off, lz))
            sz = 0.065 - li * 0.006
            make_leaf_card(bm, lc, sz, sz * 1.4, la, 0.3,
                           (0.40, 0.58, 0.25), lt, uv, co)

        # Orange spotted flowers at nodes 4-6 (dangling)
        for fi in range(3):
            ft = (fi + 4) / 7
            fz = H * ft
            fa = angle + (fi - 1) * 0.5
            fc = Vector((math.cos(angle) * lean * ft + math.cos(fa) * 0.035,
                         math.sin(angle) * lean * ft + math.sin(fa) * 0.035,
                         fz - 0.01))  # slight droop
            make_leaf_card(bm, fc, 0.020, 0.025, fa + 0.3, 0.5,
                           (0.90, 0.50, 0.08), ft, uv, co)

    return bm


def make_mugwort():
    """Mugwort (Artemisia vulgaris) — 0.6-1.5m.
    Stiff upright herb, deeply lobed dark-green leaves with silvery-white
    undersides. Ridged woody stems. Small inconspicuous flower heads. ~280 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    H = 1.0
    # 2-3 stiff upright stems (mugwort is a colony former)
    for si in range(3):
        angle = si * math.tau / 3
        lean = 0.03
        pts = []
        for j in range(8):
            t = j / 7
            pts.append(Vector((math.cos(angle) * lean * t,
                               math.sin(angle) * lean * t,
                               H * t)))
        make_tube(bm, pts, 0.008, 0.004, 4,
                  (0.30, 0.24, 0.16), (0.25, 0.20, 0.12), uv, co)

        # Deeply lobed leaves at nodes 1-5
        for li in range(5):
            lt = (li + 1) / 7
            lz = H * lt
            la = angle + (math.pi * 0.4 if li % 2 == 0 else -math.pi * 0.4)
            off = 0.018
            lc = Vector((math.cos(angle) * lean * lt + math.cos(la) * off,
                         math.sin(angle) * lean * lt + math.sin(la) * off, lz))
            # Lower leaves dark green, upper silvery (undersides show more)
            if li < 3:
                leaf_col = (0.22, 0.34, 0.16)
            else:
                leaf_col = (0.52, 0.56, 0.46)  # silvery
            sz = 0.055 - li * 0.005
            make_leaf_card(bm, lc, sz, sz * 1.6, la, 0.2,
                           leaf_col, lt, uv, co)

    return bm


# ==========================================================================
# Species: FERNS (pinnate frond arrangements — major upgrade)
# ==========================================================================

def make_ostrich_fern():
    """Ostrich fern (Matteuccia struthiopteris) — 1-1.8m.
    TALLEST fern. Elegant vase-shaped clump of bright green pinnate fronds. ~1000 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(801)

    # 10 sterile fronds — vase shape, pinnate
    n_fronds = 10
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.12, 0.12)
        make_pinnate_frond(
            bm, Vector((0, 0, 0.06)),
            length=1.65, n_segments=8, n_pinnae_per_side=7,
            pinna_length=0.28, pinna_width=0.08,
            arch=0.48, droop=0.28, angle_y=angle,
            colors=((0.10, 0.32, 0.04), (0.30, 0.52, 0.15)),
            uv_layer=uv, col_layer=co
        )

    # 2 brown fertile fronds in center — shorter, darker, erect
    for i in range(2):
        fi_angle = rng.uniform(0, math.tau)
        make_pinnate_frond(
            bm, Vector((0, 0, 0.04)),
            length=0.85, n_segments=5, n_pinnae_per_side=4,
            pinna_length=0.10, pinna_width=0.04,
            arch=0.10, droop=0.08, angle_y=fi_angle,
            colors=((0.38, 0.22, 0.10), (0.44, 0.28, 0.14)),
            uv_layer=uv, col_layer=co
        )

    return bm


def make_christmas_fern():
    """Christmas fern (Polystichum acrostichoides) — 0.3-0.6m.
    EVERGREEN. Glossy deep green rosette on rocky slopes. ~530 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(802)

    # 8 fronds — low rosette, more horizontal
    n_fronds = 8
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.08, 0.08)
        make_pinnate_frond(
            bm, Vector((0, 0, 0.02)),
            length=0.52, n_segments=6, n_pinnae_per_side=5,
            pinna_length=0.12, pinna_width=0.05,
            arch=0.88, droop=0.14, angle_y=angle,
            colors=((0.03, 0.16, 0.02), (0.06, 0.24, 0.04)),
            uv_layer=uv, col_layer=co
        )

    return bm


def make_cinnamon_fern():
    """Cinnamon fern (Osmundastrum cinnamomeum) — 0.6-1.2m.
    Blue-green sterile fronds in vase shape. CINNAMON-BROWN fertile fronds
    stand erect in center — unique visual signature. ~750 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1201)

    # 8 sterile fronds — blue-green, vase shape, pinnate
    n_fronds = 8
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.14, 0.14)
        make_pinnate_frond(
            bm, Vector((0, 0, 0.04)),
            length=1.12, n_segments=7, n_pinnae_per_side=6,
            pinna_length=0.22, pinna_width=0.07,
            arch=0.48, droop=0.24, angle_y=angle,
            colors=((0.10, 0.28, 0.12), (0.22, 0.42, 0.18)),
            uv_layer=uv, col_layer=co
        )

    # 3 CINNAMON fertile fronds in center — erect, brown
    for i in range(3):
        fi_angle = (i / 3) * math.tau + rng.uniform(-0.3, 0.3)
        make_pinnate_frond(
            bm, Vector((0, 0, 0.04)),
            length=0.88, n_segments=5, n_pinnae_per_side=4,
            pinna_length=0.08, pinna_width=0.03,
            arch=0.07, droop=0.04, angle_y=fi_angle,
            colors=((0.50, 0.28, 0.08), (0.58, 0.32, 0.10)),
            uv_layer=uv, col_layer=co
        )

    return bm


def make_sensitive_fern():
    """Sensitive fern (Onoclea sensibilis) — 0.3-1m.
    Broad triangular fronds (unusual for fern). Coarse texture. ~400 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1202)

    # 6 broad triangular fronds — wider pinnae than typical fern
    n_fronds = 6
    for i in range(n_fronds):
        angle = (i / n_fronds) * math.tau + rng.uniform(-0.18, 0.18)
        make_pinnate_frond(
            bm, Vector((0, 0, 0.03)),
            length=0.78, n_segments=5, n_pinnae_per_side=4,
            pinna_length=0.20, pinna_width=0.12,  # WIDE — distinctive
            arch=0.68, droop=0.20, angle_y=angle,
            colors=((0.14, 0.32, 0.08), (0.28, 0.46, 0.16)),
            uv_layer=uv, col_layer=co
        )

    # 1 beaded fertile frond — dark, stiff
    make_pinnate_frond(
        bm, Vector((0, 0, 0.03)),
        length=0.52, n_segments=4, n_pinnae_per_side=3,
        pinna_length=0.06, pinna_width=0.04,
        arch=0.08, droop=0.04, angle_y=rng.uniform(0, math.tau),
        colors=((0.28, 0.18, 0.08), (0.32, 0.22, 0.10)),
        uv_layer=uv, col_layer=co
    )

    return bm


# ==========================================================================
# Species: TIER 3 — GRASS
# ==========================================================================

def make_bottlebrush_grass():
    """Bottlebrush grass (Elymus hystrix) — 0.6-1.4m.
    Shade-tolerant woodland grass with distinctive seed heads. ~150 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1301)

    def color_func(t):
        if t < 0.1:
            return (0.28, 0.32, 0.16)
        elif t < 0.6:
            return (0.32, 0.40, 0.22)
        elif t < 0.75:
            return (0.36, 0.38, 0.22)
        else:
            return (0.58, 0.50, 0.28)

    # 5 folded planes, 6 segments
    make_crossed_planes(bm, 1.1, 0.22, 0.15, 5, 6, color_func, uv, co, fold=0.18)

    # 3 seed head stalks with bristles
    for s in range(3):
        sa = rng.uniform(0, math.tau)
        sx = math.cos(sa) * 0.045
        sy = math.sin(sa) * 0.045
        stalk_pts = [
            Vector((sx, sy, 0.58)),
            Vector((sx * 1.1, sy * 1.1, 0.88)),
            Vector((sx * 1.2, sy * 1.2, 1.14)),
        ]
        make_tube(bm, stalk_pts, 0.003, 0.002, 3,
                  (0.36, 0.38, 0.22), (0.52, 0.46, 0.26),
                  uv, co, 0.6, 0.85)
        # Bristle sprays at top of each stalk
        top = stalk_pts[-1]
        for br in range(6):
            bra = (br / 6) * math.tau
            brv = top + Vector((math.cos(bra) * 0.025, math.sin(bra) * 0.025,
                                rng.uniform(-0.03, 0.04)))
            make_leaf_card(bm, brv, 0.008, 0.04, bra, 0.2,
                          (0.58, 0.50, 0.28), 0.88, uv, co)

    return bm


# ==========================================================================
# Species: WETLAND
# ==========================================================================

def make_cattail():
    """Cattail (Typha latifolia) — 1.5-3m.
    THE wetland plant. Sword-like leaves + iconic brown spike. ~250 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(901)

    h = 2.0

    # 7 tall sword-like leaves — folded (V-cross-section)
    for i in range(7):
        angle = (i / 7) * math.tau + rng.uniform(-0.18, 0.18)
        leaf_h = rng.uniform(1.3, 1.9)

        def lcolor(t, _h=leaf_h):
            return (0.15 + t * 0.13, 0.35 + t * 0.10, 0.08 + t * 0.07)

        # Use crossed_planes with fold for sword-leaf V shape
        bm2 = bmesh.new()
        uv2 = bm2.loops.layers.uv.new("UVMap")
        co2 = bm2.loops.layers.color.new("Col")
        make_crossed_planes(bm2, leaf_h, 0.05, 0.02, 1, 5, lcolor, uv2, co2, fold=0.22)
        # Transfer to main bm with rotation
        ca, sa = math.cos(angle), math.sin(angle)
        for v in bm2.verts:
            x, y, z = v.co
            rx = x * ca - y * sa
            ry = x * sa + y * ca
            bm.verts.new(Vector((rx, ry, z)))
        # Just add the faces referencing transferred verts — merge via frond instead
        bm2.free()

        # Use make_frond for proper connectivity
        make_frond(bm, Vector((0, 0, 0.0)),
                   length=leaf_h, width=0.045, segments=5,
                   arch=0.22, droop=0.14, angle_y=angle,
                   color_base=(0.30, 0.55, 0.15),
                   color_tip=(0.45, 0.62, 0.22),
                   uv_layer=uv, col_layer=co)

    # 2 detailed central stalks
    for stalk_i in range(2):
        ox = rng.uniform(-0.04, 0.04)
        oy = rng.uniform(-0.04, 0.04)
        stalk_pts = []
        for i in range(7):
            t = i / 6
            stalk_pts.append(Vector((ox, oy, h * t)))
        make_tube(bm, stalk_pts, 0.009, 0.006, 5,
                  (0.35, 0.55, 0.18), (0.42, 0.60, 0.20),
                  uv, co, 0.0, 0.5)

        # Brown spike ("hot dog") near top
        spike_base = h * 0.63
        spike_top = h * 0.80
        spike_pts = []
        for i in range(5):
            t = i / 4
            spike_pts.append(Vector((ox, oy, spike_base + (spike_top - spike_base) * t)))
        make_tube(bm, spike_pts, 0.024, 0.022, 7,
                  (0.45, 0.25, 0.10), (0.55, 0.30, 0.12),
                  uv, co, 0.7, 0.85)

    return bm


def make_yellow_flag_iris():
    """Yellow flag iris (Iris pseudacorus) — 0.6-1.5m.
    Sword-shaped dark green leaves, bright yellow flowers. ~300 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1401)

    # 6 sword-like leaves — folded via frond
    for i in range(6):
        angle = (i / 6) * math.tau + rng.uniform(-0.22, 0.22)
        leaf_h = rng.uniform(0.85, 1.25)
        make_frond(bm, Vector((0, 0, 0.0)),
                   length=leaf_h, width=0.045, segments=5,
                   arch=0.18, droop=0.09, angle_y=angle,
                   color_base=(0.12, 0.30, 0.06),
                   color_tip=(0.18, 0.38, 0.10),
                   uv_layer=uv, col_layer=co)

    # 2 flower stalks — taller than leaves
    for fi in range(2):
        stalk_offset = Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 0))
        stalk_pts = []
        for i in range(6):
            t = i / 5
            stalk_pts.append(stalk_offset + Vector((0, 0, (1.1 + fi * 0.12) * t)))
        make_tube(bm, stalk_pts, 0.007, 0.004, 4,
                  (0.18, 0.30, 0.08), (0.22, 0.34, 0.10),
                  uv, co, 0.0, 0.5)

        # Bright yellow flower — 3 drooping falls + 3 upright standards
        fc = stalk_pts[-1]
        for p in range(3):
            pa = (p / 3) * math.tau
            # Drooping falls
            pv = fc + Vector((math.cos(pa) * 0.045, math.sin(pa) * 0.045, -0.022))
            make_leaf_card(bm, pv, 0.038, 0.055, pa, -0.32,
                          (0.88, 0.82, 0.12), 0.9, uv, co)
            # Upright standards
            pv2 = fc + Vector((math.cos(pa + 0.52) * 0.022, math.sin(pa + 0.52) * 0.022, 0.022))
            make_leaf_card(bm, pv2, 0.022, 0.045, pa + 0.52, 0.32,
                          (0.85, 0.78, 0.15), 0.9, uv, co)

    return bm


def make_lizards_tail():
    """Lizard's tail (Saururus cernuus) — 0.6-1.2m.
    Heart-shaped leaves, distinctive drooping white flower spikes. ~300 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1402)

    h = 0.9
    # Main stem — 5-sided
    pts = []
    for i in range(7):
        t = i / 6
        pts.append(Vector((rng.uniform(-0.012, 0.012),
                           rng.uniform(-0.012, 0.012), h * t)))
    make_tube(bm, pts, 0.007, 0.003, 5,
              (0.20, 0.30, 0.10), (0.24, 0.34, 0.12),
              uv, co, 0.0, 0.5)

    # 2 side branches
    for b in range(2):
        bi = rng.randint(2, 4)
        ba = rng.uniform(0, math.tau)
        bl = h * rng.uniform(0.28, 0.45)
        bpts = [
            pts[bi].copy(),
            pts[bi] + Vector((math.cos(ba) * bl * 0.5, math.sin(ba) * bl * 0.5, bl * 0.3)),
            pts[bi] + Vector((math.cos(ba) * bl, math.sin(ba) * bl, bl * 0.08)),
        ]
        make_tube(bm, bpts, 0.004, 0.002, 3,
                  (0.20, 0.30, 0.10), (0.24, 0.34, 0.12),
                  uv, co, 0.3, 0.6)

    # 10 heart-shaped leaves
    for node in range(2, 6):
        t = node / 6
        lc = pts[node].copy()
        for side in [-1, 1]:
            la = side * 1.1 + rng.uniform(-0.2, 0.2)
            leaf_off = Vector((math.cos(la) * 0.09, math.sin(la) * 0.09, 0))
            make_leaf_card(bm, lc + leaf_off, 0.10, 0.09, la,
                          rng.uniform(-0.1, 0.2),
                          (0.18, 0.40, 0.08), t * 0.3 + 0.2, uv, co)

    # 3 drooping curved white flower spikes
    for sp in range(3):
        sp_origin = pts[-1] if sp == 0 else pts[rng.randint(4, 5)]
        spike_pts = []
        drift_x = rng.uniform(0.04, 0.10) * (1 if sp % 2 == 0 else -1)
        for i in range(6):
            t = i / 5
            spike_pts.append(Vector((
                sp_origin.x + drift_x * t,
                sp_origin.y + rng.uniform(-0.02, 0.02),
                sp_origin.z + 0.035 - t * 0.12
            )))
        make_tube(bm, spike_pts, 0.011, 0.005, 5,
                  (0.92, 0.94, 0.86), (0.96, 0.97, 0.90),
                  uv, co, 0.85, 0.95)

    return bm


def make_phragmites():
    """Common reed / Phragmites (Phragmites australis) — 2-5m.
    Tall rigid tan stems, large feathery purplish-brown seed heads.
    Creates dense monoculture reed beds. ~1200 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1403)

    # 5 tall reed stems — 6-sided
    for s in range(5):
        h = rng.uniform(2.8, 3.8)
        ox = rng.uniform(-0.18, 0.18)
        oy = rng.uniform(-0.18, 0.18)

        pts = []
        for i in range(9):
            t = i / 8
            pts.append(Vector((
                ox + rng.uniform(-0.006, 0.006),
                oy + rng.uniform(-0.006, 0.006),
                h * t
            )))

        # Rigid tan stems — 6-sided
        make_tube(bm, pts, 0.014, 0.009, 6,
                  (0.35, 0.38, 0.18), (0.42, 0.40, 0.22),
                  uv, co, 0.0, 0.5)

        # Long arching leaves at 4 nodes — each as a frond
        for node in range(3, 8):
            t = node / 8
            lc = pts[node].copy()
            la = rng.uniform(0, math.tau)
            make_frond(bm, lc,
                       length=0.50, width=0.045, segments=4,
                       arch=0.72, droop=0.32, angle_y=la,
                       color_base=(0.28, 0.35, 0.14),
                       color_tip=(0.38, 0.40, 0.20),
                       uv_layer=uv, col_layer=co)

        # Feathery plume at top — large, multi-branching
        top = pts[-1]
        # Central plume stalk
        plume_base_pts = [top, top + Vector((0, 0, 0.10)), top + Vector((0, 0, 0.22))]
        make_tube(bm, plume_base_pts, 0.005, 0.003, 4,
                  (0.48, 0.28, 0.30), (0.52, 0.32, 0.34),
                  uv, co, 0.8, 0.95)
        # 12 plume branch cards
        for _ in range(12):
            pa = rng.uniform(0, math.tau)
            pr = rng.uniform(0, 0.08)
            pz = rng.uniform(-0.06, 0.20)
            pv = top + Vector((math.cos(pa) * pr, math.sin(pa) * pr, pz))
            make_leaf_card(bm, pv, 0.018, 0.072, pa,
                          rng.uniform(-0.22, 0.32),
                          (0.50, 0.30, 0.32), 0.85, uv, co)

    return bm


# ==========================================================================
# Build all species
# ==========================================================================

# All species generated procedurally — no external asset dependencies.
# BD3D models were previously used but removed for distributable-only policy.

SPECIES = [
    # Tier 1+2: shrubs (BD3D replaced — skipped), herbs, ferns, wetland
    (make_spicebush,           "Shrub_Spicebush"),
    (make_witch_hazel,         "Shrub_WitchHazel"),
    (make_viburnum,            "Shrub_Viburnum"),
    (make_sumac,               "Shrub_Sumac"),
    (make_elderberry,          "Shrub_Elderberry"),
    (make_pokeweed,            "Herb_Pokeweed"),
    (make_japanese_knotweed,   "Herb_JapaneseKnotweed"),
    (make_joe_pye_weed,        "Herb_JoePyeWeed"),
    (make_coneflower,          "Herb_Coneflower"),
    (make_cardinal_flower,     "Herb_CardinalFlower"),
    (make_white_wood_aster,    "Herb_WhiteWoodAster"),
    (make_jewelweed,           "Herb_Jewelweed"),
    (make_mugwort,             "Herb_Mugwort"),
    (make_ostrich_fern,        "Fern_Ostrich"),
    (make_christmas_fern,      "Fern_Christmas"),
    (make_cattail,             "Wetland_Cattail"),
    # Tier 3
    (make_sweet_pepperbush,    "Shrub_SweetPepperbush"),
    (make_flowering_raspberry, "Shrub_FloweringRaspberry"),
    (make_white_snakeroot,     "Herb_WhiteSnakeroot"),
    (make_ironweed,            "Herb_Ironweed"),
    (make_rose_mallow,         "Herb_RoseMallow"),
    (make_burdock,             "Herb_Burdock"),
    (make_cinnamon_fern,       "Fern_Cinnamon"),
    (make_sensitive_fern,      "Fern_Sensitive"),
    (make_bottlebrush_grass,   "Grass_Bottlebrush"),
    (make_yellow_flag_iris,    "Wetland_YellowIris"),
    (make_lizards_tail,        "Wetland_LizardsTail"),
    (make_phragmites,          "Wetland_Phragmites"),
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

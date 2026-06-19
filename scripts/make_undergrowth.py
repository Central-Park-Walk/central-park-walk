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


def make_textured_material(name, tex_path):
    """Material with an image texture for alpha-masked leaf cards.
    Godot's GLB importer reads this as StandardMaterial3D with albedo_texture,
    which undergrowth_builder.gd detects and sets use_texture=1.0."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.blend_method = 'CLIP'  # alpha clip for export
    tree = mat.node_tree
    for n in tree.nodes:
        tree.nodes.remove(n)
    out = tree.nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)
    bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Roughness'].default_value = 0.6
    tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    img = bpy.data.images.load(tex_path)
    tex_node = tree.nodes.new('ShaderNodeTexImage')
    tex_node.location = (-300, 0)
    tex_node.image = img
    tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    tree.links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
    return mat


def finalize_and_export(bm, name, mat=None):
    """Convert bmesh to object, export as GLB.
    If a species leaf texture exists (tex_{name}.png), embeds it in the GLB
    so Godot's importer creates a StandardMaterial3D with albedo_texture."""
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

    # Ensure our bmesh color layer ("Col") is the active render color attribute.
    # Without this, textured materials cause the exporter to write material
    # vertex colors (all white) as COLOR_0, pushing our stem/leaf alpha tags
    # to COLOR_1 where the Godot shader can't read them.
    if mesh.color_attributes:
        mesh.color_attributes.render_color_index = 0

    # Check for cluster texture first (volumetric card approach), then single-leaf
    cluster_path = os.path.join(OUT_DIR, f"cluster_{name}_v0.png")
    tex_path = os.path.join(OUT_DIR, f"tex_leaf_{name}.png")
    # Variant species (name ends _0/_1/_2) with no per-variant texture share the
    # base species' leaf texture (e.g. Wetland_Cattail_0 → tex_leaf_Wetland_Cattail.png).
    base_name = name.rsplit("_", 1)[0] if ("_" in name and name.rsplit("_", 1)[1].isdigit()) else name
    tex_path_base = os.path.join(OUT_DIR, f"tex_leaf_{base_name}.png")
    if os.path.exists(cluster_path):
        m = make_textured_material(name + "_Mat", cluster_path)
        print(f"    → embedded cluster texture: cluster_{name}_v0.png")
    elif os.path.exists(tex_path):
        m = make_textured_material(name + "_Mat", tex_path)
        print(f"    → embedded texture: tex_leaf_{name}.png")
    elif os.path.exists(tex_path_base):
        m = make_textured_material(name + "_Mat", tex_path_base)
        print(f"    → embedded shared texture: tex_leaf_{base_name}.png")
    else:
        m = make_material(name + "_Mat")
    obj.data.materials.append(m)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    bm.free()

    # Export — include textures in GLB when embedded
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
        export_image_format='AUTO',
    )
    nv = len(mesh.vertices)
    nf = len(mesh.polygons)
    print(f"  {name}: {nv} verts, {nf} faces → {path}")
    return obj


# ==========================================================================
# Geometry helpers
# ==========================================================================

def _lerp_color(c0, c1, t, alpha=1.0):
    return [c0[i] + (c1[i] - c0[i]) * t for i in range(3)] + [alpha]


def make_tube(bm, points, r_start, r_end, n_sides, color_start, color_end,
              uv_layer, col_layer, uv_y_start=0.0, uv_y_end=1.0, alpha=0.0,
              cap=False, radii=None):
    """Create a tube mesh along a list of points. Returns list of vertex rings.
    alpha: vertex color alpha — 0.0 for stem (shader bark path), 1.0 for leaf.
    cap: close the first and last ring with n-gon end caps (solid ends, e.g. the
    cattail cigar) — winding is irrelevant since the undergrowth shader is cull_disabled.
    radii: optional per-point radius list (len == len(points)); overrides r_start/r_end,
    e.g. a rounded-end profile for the cigar (faces are flat-shaded by finalize's
    normal blend, so smoothness comes from side count + a rounded profile)."""
    rings = []
    n = len(points)
    for i, pt in enumerate(points):
        t = i / max(n - 1, 1)
        r = radii[i] if radii is not None else r_start + (r_end - r_start) * t
        uv_y = uv_y_start + (uv_y_end - uv_y_start) * t
        col = _lerp_color(color_start, color_end, t, alpha=alpha)

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

    # End caps — close the first/last ring so the tube isn't a hollow open cylinder.
    if cap and n_sides >= 3 and len(rings) >= 1:
        for ring in (rings[0], rings[-1]):
            verts = [v for (v, _uv, _c) in ring]
            try:
                f = bm.faces.new(verts)
                for loop in f.loops:
                    loop[uv_layer].uv = (0.5, ring[0][1])
                    loop[col_layer] = ring[0][2]
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
        col = _lerp_color(color_base, color_tip, t, alpha=0.0)  # stem
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


def _scatter_cluster_cards(bm, positions, card_size, uv_layer, col_layer, rng,
                           n_cards_per_cluster=8, flatten=0.7,
                           leaf_color=(0.303, 0.456, 0.244)):
    """Scatter alpha-tested quads in spheroidal volumes around branch positions.

    Same technique as tree foliage (generate_trees_mtree.py create_leaf_cards_at_positions):
    each cluster gets multiple randomly-oriented quads filling a spheroidal volume.
    The texture on each card shows multiple leaves — geometry creates depth through overlap.

    Args:
        bm: bmesh to add geometry to
        positions: list of (Vector, radius) tuples — cluster center + size
        card_size: base card size in meters
        uv_layer, col_layer: bmesh layers
        rng: random.Random instance
        n_cards_per_cluster: quads per cluster (8-12 for shrubs)
        flatten: vertical squash (0.7 = slightly oblate, matching natural leaf layer)
        leaf_color: (r, g, b) base leaf color in gamma sRGB (from spectral pipeline)
    """
    lr, lg, lb = leaf_color
    for center, radius in positions:
        for q in range(n_cards_per_cluster):
            # Random position within cluster sphere (bias toward surface for shell fill)
            r = radius * (0.3 + 0.7 * rng.random() ** 0.5)
            theta = rng.uniform(0, math.tau)
            phi = rng.uniform(-0.5, 0.7)  # bias upward
            jx = r * math.cos(theta) * math.cos(phi)
            jy = r * math.sin(theta) * math.cos(phi)
            jz = r * math.sin(phi) * flatten

            # Random orientation: full yaw, wide pitch range for dappled look
            yaw = rng.uniform(0, math.tau)
            pitch = rng.uniform(-1.2, 1.2)  # ±69° — some nearly vertical, some nearly horizontal
            # 30% of cards near-horizontal (canopy fill / light-catching)
            if rng.random() < 0.30:
                pitch = rng.uniform(1.0, 1.45)

            # Per-card size variation (75-125%)
            w = card_size * rng.uniform(0.75, 1.25)
            h = w * rng.uniform(0.85, 1.15)
            half_w = w * 0.5
            half_h = h * 0.5

            # Per-card color variation: ±8% brightness + warm/cool hue shift
            # Lower cards darker (interior shadow), upper cards brighter (light-catching)
            height_bias = (phi + 0.5) / 1.2  # 0 at bottom, ~1 at top
            bright = 0.92 + 0.16 * height_bias + rng.uniform(-0.06, 0.06)
            # Warm/cool shift: slight toward yellow-green or blue-green
            hue_shift = rng.uniform(-0.02, 0.02)
            cr = min(1.0, lr * bright + hue_shift * 0.5)
            cg = min(1.0, lg * bright)
            cb = min(1.0, lb * bright - hue_shift * 0.5)

            # Build oriented quad
            cy_r, sy_r = math.cos(yaw), math.sin(yaw)
            cp, sp_v = math.cos(pitch), math.sin(pitch)

            local_corners = [
                (-half_w, 0, -half_h),
                ( half_w, 0, -half_h),
                ( half_w, 0,  half_h),
                (-half_w, 0,  half_h),
            ]
            verts = []
            for lx, ly, lz in local_corners:
                rx = lx * cy_r - ly * sy_r
                ry = lx * sy_r + ly * cy_r
                rz = lz
                ry2 = ry * cp - rz * sp_v
                rz2 = ry * sp_v + rz * cp
                pos = center + Vector((rx + jx, ry2 + jy, rz2 + jz))
                verts.append(bm.verts.new(pos))

            try:
                face = bm.faces.new(verts)
                uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
                # Bottom verts slightly darker, top slightly lighter (gradient within card)
                card_col = [cr, cg, cb, 1.0]  # alpha=1.0 → leaf
                for loop, uv in zip(face.loops, uvs):
                    loop[uv_layer].uv = uv
                    loop[col_layer] = card_col
            except ValueError:
                pass


def _make_branch(bm, origin, direction, length, r_start, n_segs, zigzag_amt,
                 stem_color_base, stem_color_tip, uv_layer, col_layer, rng,
                 arch=0.0, depth=0, max_depth=3, cluster_list=None):
    """Recursively build a branch with natural zigzag, taper, and child branches.

    Each branch node is a potential foliage attachment point. Child branches
    spawn at zigzag nodes. Leaf clusters are placed at branch tips and along
    upper portions, connected to the branch structure.

    Args:
        origin: Vector — start position
        direction: Vector — initial growth direction (normalized)
        length: total branch length
        r_start: radius at base
        n_segs: number of segments
        zigzag_amt: lateral displacement per node (characteristic of spicebush)
        depth: current recursion depth (0=main stem, 1=secondary, 2=tertiary)
        max_depth: stop branching beyond this
        cluster_list: list to append (position, radius, branch_dir) tuples for foliage
    """
    if cluster_list is None:
        cluster_list = []

    # Build points with continuous curvature using noise-based displacement.
    # Instead of zigzag (sharp alternating angles), use smooth sinusoidal
    # wander with incommensurate frequencies — this produces organic curves
    # that look like real branch growth responding to light and obstacles.
    n_fine = n_segs * 3  # high-res point sampling for smooth curves
    pts = []
    current_dir = direction.copy()

    # Two perpendicular axes for 3D displacement
    if abs(current_dir.dot(Vector((0, 0, 1)))) < 0.9:
        perp1 = current_dir.cross(Vector((0, 0, 1))).normalized()
    else:
        perp1 = current_dir.cross(Vector((1, 0, 0))).normalized()
    perp2 = current_dir.cross(perp1).normalized()

    # Random phase offsets so each branch curves differently
    phase1 = rng.uniform(0, math.tau)
    phase2 = rng.uniform(0, math.tau)
    phase3 = rng.uniform(0, math.tau)

    # Horizontal heading of this branch — the azimuth the arch bends outward along.
    az = Vector((direction.x, direction.y, 0.0))
    az = az.normalized() if az.length > 1e-4 else Vector((1.0, 0.0, 0.0))

    seg_len = length / n_fine
    pos = origin.copy()

    for i in range(n_fine + 1):
        t = i / n_fine

        # Smooth displacement: sum of incommensurate sine waves
        # Low freq = broad sweeping arcs (like real branches responding to light)
        # Mid freq = secondary curves  |  High freq = fine wander
        d1 = (math.sin(t * 1.8 * math.pi + phase1) * 0.55 +
              math.sin(t * 4.1 * math.pi + phase2) * 0.30 +
              math.sin(t * 7.3 * math.pi + phase3) * 0.15) * zigzag_amt
        d2 = (math.sin(t * 2.3 * math.pi + phase2 + 1.0) * 0.50 +
              math.sin(t * 5.5 * math.pi + phase3 + 2.0) * 0.30 +
              math.sin(t * 8.8 * math.pi + phase1 + 0.5) * 0.20) * zigzag_amt * 0.8

        displacement = perp1 * d1 + perp2 * d2

        if i == 0:
            pts.append(origin.copy())
            continue

        if arch > 0.0 and depth == 0:
            # GRAVITY ARCH (Lindera mounding cascade): the cane rises ~straight,
            # then in its UPPER portion bends outward and gently over — a fountain
            # cane. All canes together make a rounded DOME that flows over itself,
            # NOT a straight outward V/vase nor a flat pancake. The bend is held
            # off until ~30% height (smoothstep) so the dome stays tall.
            bt = max(0.0, (t - 0.35) / 0.65)
            bend = 0.75 * bt * bt * (3.0 - 2.0 * bt)     # ease-in, capped <1 so tips
            #                                              keep rising → rounded dome top
            tip = az * (0.50 + 0.30 * arch) + Vector((0.0, 0.0, -0.12 * arch))
            tip = tip.normalized() if tip.length > 1e-4 else az
            fwd = Vector((0.0, 0.0, 1.0)) * (1.0 - bend) + tip * bend
            fwd = fwd.normalized() if fwd.length > 1e-4 else Vector((0.0, 0.0, 1.0))
            new_pos = pts[-1] + fwd * seg_len + displacement * seg_len
        elif arch > 0.0 and depth >= 1:
            # Secondary/tertiary growth droops and layers over the mound — the
            # "flows over itself" habit. Blend the spawn direction toward straight
            # down as the twig extends.
            dt = t
            fwd = current_dir * (1.0 - 0.75 * arch * dt) + Vector((0.0, 0.0, -1.0)) * (0.95 * arch * dt)
            fwd = fwd.normalized() if fwd.length > 1e-4 else current_dir
            new_pos = pts[-1] + fwd * seg_len + displacement * seg_len
        else:
            # Original phototropic behavior (non-arch shrubs): upward + outward bend.
            up_bias = 0.04 * seg_len
            fwd = current_dir.copy()
            if depth == 0:
                horizontal = Vector((pos.x, pos.y, 0))
                if horizontal.length > 0.01:
                    fwd = (fwd + horizontal.normalized() * (0.02 * t)).normalized()
            new_pos = pts[-1] + fwd * seg_len + displacement * seg_len + Vector((0, 0, up_bias))

        pts.append(new_pos)
        pos = new_pos

    n_segs_smooth = len(pts) - 1

    # Taper ratio depends on depth
    taper = [0.25, 0.20, 0.15, 0.10][min(depth, 3)]
    n_sides = [5, 4, 3, 3][min(depth, 3)]
    make_tube(bm, pts, r_start, r_start * taper, n_sides,
              stem_color_base, stem_color_tip, uv_layer=uv_layer, col_layer=col_layer,
              uv_y_start=0.0, uv_y_end=0.5)

    # Foliage clusters along the branch — sample at TWICE node density and start
    # lower so the dense leafy SHELL of the mound fills in (the reference shrubs
    # read as a solid rounded mass, not bunched mid-stem with straggly tips).
    n_foliage_samples = max(6, n_segs * 2)
    for i in range(n_foliage_samples + 1):
        t = i / n_foliage_samples
        # Foliage covers most of each cane (only the very base is bare wood).
        min_foliage_t = [0.28, 0.10, 0.0, 0.0][min(depth, 3)]
        if t >= min_foliage_t:
            # Map to smooth pts index
            pi = min(int(t * n_segs_smooth), n_segs_smooth)
            cluster_r = 0.26 + (0.16 * t) + rng.uniform(0, 0.08)
            cluster_r *= [1.0, 0.85, 0.7, 0.55][min(depth, 3)]
            if pi < n_segs_smooth:
                br_dir = (pts[pi + 1] - pts[pi]).normalized()
            else:
                br_dir = (pts[pi] - pts[pi - 1]).normalized()
            cluster_list.append((pts[pi].copy(), cluster_r, br_dir))

    # Spawn child branches at zigzag nodes (use coarse nodes for branching)
    if depth < max_depth:
        n_children = [rng.randint(3, 5), rng.randint(2, 3), rng.randint(1, 2), rng.randint(1, 1)][min(depth, 3)]
        for c in range(n_children):
            node_t = rng.uniform(0.25, 0.85)
            # Map to smooth curve index
            node_idx = max(1, min(int(node_t * n_segs_smooth), n_segs_smooth - 1))
            node_pos = pts[node_idx].copy()

            parent_dir = (pts[node_idx] - pts[node_idx - 1]).normalized()
            branch_angle = rng.uniform(-1.3, 1.3)
            ca, sa = math.cos(branch_angle), math.sin(branch_angle)
            if abs(parent_dir.dot(Vector((0, 0, 1)))) < 0.9:
                side = parent_dir.cross(Vector((0, 0, 1))).normalized()
            else:
                side = parent_dir.cross(Vector((1, 0, 0))).normalized()
            up = side.cross(parent_dir).normalized()
            # With arch, children start more horizontal (less upward bias) so the
            # gravity droop in the recursion carries them out and over the mound.
            up_z = 0.2 * (1.0 - 0.8 * arch)
            child_dir = (parent_dir * 0.4 + side * ca * 0.5 + up * sa * 0.3
                        + Vector((0, 0, up_z))).normalized()

            child_len = length * rng.uniform(0.3, 0.55)
            child_r = r_start * node_t * rng.uniform(0.3, 0.5)
            child_segs = max(3, n_segs - 2)
            child_zigzag = zigzag_amt * 0.8

            _make_branch(bm, node_pos, child_dir, child_len, child_r,
                        child_segs, child_zigzag,
                        stem_color_base, stem_color_tip,
                        uv_layer, col_layer, rng, arch=arch,
                        depth=depth + 1, max_depth=max_depth,
                        cluster_list=cluster_list)

    return cluster_list


def make_spicebush(seed=101):
    """Spicebush (Lindera benzoin) — THE dominant Central Park understory shrub.
    2-4m, multi-stemmed, wide vase shape, zigzag branching.

    Architecture: root collar → 5-8 main stems leaning outward → recursive
    branching (3 levels) → dense leaf clusters in upper canopy.
    Lower stems are bare, foliage concentrated in upper half.
    Ref: Lindera benzoin_webbc0078__03548.jpg

    seed: random seed for this variant (different seeds → different branching)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)

    # --- Colors (spectral pipeline: CIE 1931 + D65 → sRGB) ---
    # Bark: olive-brown at base, greener toward tips
    bark_base = (0.28, 0.24, 0.14)
    bark_tip = (0.26, 0.32, 0.16)
    # Root collar is darker
    root_color = (0.22, 0.18, 0.10)
    # Leaf color from spectral reflectance data (gamma sRGB)
    leaf_color = (0.303, 0.456, 0.244)  # Lindera benzoin — spectral_colors.py

    # --- Root collar ---
    # Wide mound where all stems emerge — real spicebush root crowns are 15-25cm
    collar_r = 0.14
    collar_pts = [
        Vector((0, 0, -0.05)),  # just below ground
        Vector((0, 0, 0.0)),    # ground level
        Vector((0, 0, 0.08)),   # slight flare above ground
    ]
    make_tube(bm, collar_pts, collar_r * 1.3, collar_r, 6,
              root_color, bark_base, uv_layer=uv, col_layer=co)

    # --- Surface roots ---
    n_roots = rng.randint(3, 5)
    for ri in range(n_roots):
        root_angle = (ri / n_roots) * math.tau + rng.uniform(-0.3, 0.3)
        root_len = rng.uniform(0.3, 0.6)
        root_r = rng.uniform(0.012, 0.022)
        ca, sa = math.cos(root_angle), math.sin(root_angle)
        root_pts = [
            Vector((0, 0, 0.02)),
            Vector((ca * root_len * 0.4, sa * root_len * 0.4, -0.02)),
            Vector((ca * root_len, sa * root_len, -0.06)),
        ]
        make_tube(bm, root_pts, root_r, root_r * 0.3, 3,
                  root_color, root_color, uv_layer=uv, col_layer=co)

    # --- Main stems ---
    # Real spicebush: 5-8 stems from a root crown that RISE then ARCH outward and
    # over — primary stems bend under their own weight and secondary growth droops
    # and layers, so the shrub flows over itself into a rounded MOUND (NOT a
    # straight-stemmed V/vase — that was the §1 rule-not-reference failure).
    # The arch (not the initial lean) makes the width; lower stems read as bare
    # arching canes, foliage cascades over the dome.  Ref: iNat Lindera benzoin.
    n_stems = rng.randint(5, 8)
    all_clusters = []

    for s in range(n_stems):
        # Stems emerge near the collar, fairly upright — the arch supplies spread.
        stem_angle = (s / n_stems) * math.tau + rng.uniform(-0.30, 0.30)
        # Gentle initial lean only; the gravity arch does the outward sweep.
        lean = rng.uniform(0.08, 0.22)
        ca, sa = math.cos(stem_angle), math.sin(stem_angle)

        spread = rng.uniform(0.06, 0.12)
        stem_origin = Vector((ca * spread, sa * spread, -0.08))
        stem_dir = Vector((ca * lean, sa * lean, 1.0)).normalized()

        # Canes arch over, so the mound apex lands below the cane length and the
        # tips droop. Tuned for a ~2.5-3m-tall, ~3-3.5m-wide rounded mound.
        stem_height = rng.uniform(2.5, 3.2)
        stem_r = rng.uniform(0.022, 0.035)

        # arch>0 turns on the gravity-bend (rise → out → over) + drooping
        # secondaries.  max_depth=3 keeps the intricate twig/foliage cloud.
        _make_branch(bm, stem_origin, stem_dir, stem_height, stem_r,
                    n_segs=5, zigzag_amt=0.18,
                    stem_color_base=bark_base, stem_color_tip=bark_tip,
                    uv_layer=uv, col_layer=co, rng=rng,
                    arch=rng.uniform(0.60, 0.85),
                    depth=0, max_depth=3, cluster_list=all_clusters)

    # --- Scatter leaf clusters at all branch-attached positions ---
    # Convert (pos, radius, branch_dir) to (pos, radius) for scatter function
    cluster_positions = [(pos, radius) for pos, radius, _ in all_clusters]

    # 20 cards/cluster at 0.20m — smaller cards break up blobby silhouette,
    # higher density fills the volume without individual quads being visible.
    # Bigger cards, fewer per cluster (cluster COUNT roughly doubled above) →
    # a continuous leafy shell over the mound without ballooning face count.
    _scatter_cluster_cards(bm, cluster_positions, card_size=0.24,
                          uv_layer=uv, col_layer=co, rng=rng,
                          n_cards_per_cluster=13, flatten=0.70,
                          leaf_color=leaf_color)

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

def make_cattail(seed=901, spike_stage="brown", height=2.0):
    """Cattail (Typha latifolia) — broadleaf, 1.5-3m. BRIEF: notes/refs/veg/cattail.
    Identity (BRIEF §1/§6): a STRICT-VERTICAL, unbranched strap-leaf shoot topped by
    the brown no-gap "hot-dog" spike (female cylinder + male section, touching). Leaves
    are individual curved blades at irregular angles (organic, not a radial star).
    spike_stage: "green" (immature) | "brown" (mature) | "bursting" (winter seed-burst).
    """
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)

    h = height

    # --- Leaves: INDIVIDUAL curved blades at irregular azimuths/heights — organic and
    # asymmetric. The old crossed-planes clump read as a rigid radial STAR from above
    # (user note 2026-06-18) with no curvature. Real cattail blades arch gracefully and
    # splay every which way; flat straps at random azimuths present broadside from any
    # view (edge-on thinness is true to life), and varied arch/height/base-offset kills
    # the symmetry. Refs: reference_photos/. ---
    # Refs (34-cattail-pond...webp): TALL blades that clearly OVERTOP the spikes, fairly
    # upright with gentle curves (NOT strongly arching), forming a DENSE clump of many
    # wide straps. Height variation + gentle varied curve = organic without the rigid
    # radial star or the floppy-fountain look.
    leaf_h = h * rng.uniform(0.98, 1.08)
    n_blades = rng.randint(22, 28)
    for _i in range(n_blades):
        az = rng.uniform(0.0, math.tau)             # irregular — NOT evenly spaced
        blade_h = leaf_h * rng.uniform(0.82, 1.05)  # tall — foliage overtops the spikes
        # Reconciled data: reference photos (ground truth) + FNA ("leaves quite flexible")
        # show leaves that curve OUTWARD and droop at the tips. The botany doc's "strict
        # vertical / no arching" describes the overall HABIT (a vertical wall, not an
        # arching mound) and the stiff flower-STALK — not the leaves. So: upright at the
        # base, real curve + flexible droop toward the tips, varied per blade (inner
        # straighter, outer/taller ones curving more). NOT a floppy fountain.
        arch = rng.uniform(0.05, 0.28)
        droop = rng.uniform(0.14, 0.42)
        bx = rng.uniform(-0.055, 0.055)             # wider clump base — not one point
        by = rng.uniform(-0.055, 0.055)
        # Color = GLAUCOUS grey/blue-green (verified: FNA describes the blade as glaucous;
        # reference_photos/cattail confirm a muted blue-green/grey-green, NOT a saturated
        # grass-green — the internal botany doc's "true grass-green, NOT blue-green" is an
        # unverified/likely-hallucinated claim, overridden by FNA + photos). Variation is
        # VALUE + how strong the waxy bloom (grey) reads; ~12% of blades yellow at the tip
        # (older leaves; July is pre-fall, so few). Seasonal browning is Oct+.
        val = rng.uniform(-0.045, 0.05)             # light/dark
        glauc = rng.uniform(0.0, 0.07)              # waxy grey-blue bloom amount
        base = (0.16 + val + glauc, 0.30 + val, 0.18 + val + glauc)
        if rng.random() < 0.12:
            tip = (0.42 + val, 0.42 + val, 0.20)            # older blade — yellowing tip
        else:
            tip = (0.26 + val + glauc, 0.43 + val, 0.24 + glauc)
        bw = rng.uniform(0.038, 0.062)              # per-blade width — varied sizes
        make_frond(bm, Vector((bx, by, 0.0)),
                   length=blade_h, width=bw, segments=6,
                   arch=arch, droop=droop, angle_y=az,
                   color_base=base, color_tip=tip,
                   uv_layer=uv, col_layer=co)

    # --- Spike colors by maturity stage ---
    if spike_stage == "green":
        fem0, fem1 = (0.26, 0.38, 0.13), (0.32, 0.44, 0.16)   # immature green
        mal0, mal1 = (0.34, 0.46, 0.18), (0.46, 0.56, 0.24)
        fem_r = 0.021
    elif spike_stage == "bursting":
        fem0, fem1 = (0.46, 0.36, 0.22), (0.62, 0.52, 0.40)   # paler, cottony burst
        mal0, mal1 = (0.50, 0.42, 0.28), (0.34, 0.28, 0.22)
        fem_r = 0.028
    else:  # brown (mature) — WARM cinnamon-brown (reads brown not black at range;
           # the dark-chocolate value went near-black in-engine), fat enough to read
        fem0, fem1 = (0.44, 0.27, 0.13), (0.52, 0.34, 0.18)
        mal0, mal1 = (0.56, 0.44, 0.24), (0.66, 0.56, 0.34)
        fem_r = 0.024

    # --- 2-4 culms, each LEANING in a random direction (real culms aren't dead-straight
    # ramrods) with the no-gap female+male spike riding the leaned top. ---
    for _si in range(rng.randint(3, 4)):
        ang = rng.uniform(0.0, math.tau)
        rad = rng.uniform(0.05, 0.11)
        ox, oy = rad * math.cos(ang), rad * math.sin(ang)
        lean_az = rng.uniform(0.0, math.tau)         # culm leans this way at the top
        # Data: the flowering culm is STIFF / nearly rigid (botany doc: holds the cylinder
        # "quite rigid, sways minimally") — only a slight lean, unlike the flexible leaves.
        lean = rng.uniform(0.02, 0.10)
        lx, ly = lean * math.cos(lean_az), lean * math.sin(lean_az)
        # Refs: spike sits at ~60-70% of leaf height — blades clearly OVERTOP it.
        crown = h * rng.uniform(0.56, 0.74)
        fem_top = crown - 0.06                        # ~6cm male above the female
        fem_base = fem_top - rng.uniform(0.15, 0.21)  # female "hot-dog" 15-21cm
        mal_top = crown + rng.uniform(0.0, 0.03)

        # curved/leaning culm: lateral offset grows with height (∝ t²)
        def _cx(t): return ox + lx * t * t
        def _cy(t): return oy + ly * t * t
        stalk_pts = [Vector((_cx(i / 6.0), _cy(i / 6.0), (fem_base + 0.02) * (i / 6.0)))
                     for i in range(7)]
        make_tube(bm, stalk_pts, 0.010, 0.007, 7,
                  (0.34, 0.52, 0.18), (0.40, 0.56, 0.20), uv, co, 0.0, 0.45)

        tx, ty = ox + lx, oy + ly                     # culm top (leaned) XY
        # female cylinder ("hot-dog"): 18-sided with a ROUNDED radius profile (tapered
        # round bottom into the stalk, full body, gently rounded top) so it reads as a
        # smooth cigar, not a faceted hollow tube. (finalize flat-shades faces, so
        # roundness comes from the side count + this profile, not smooth normals.)
        nf = 9
        fpts = [Vector((tx, ty, fem_base + (fem_top - fem_base) * (i / (nf - 1.0))))
                for i in range(nf)]
        f_rad = []
        for i in range(nf):
            ft = i / (nf - 1.0)
            if ft <= 0.16:        # rounded bottom: 0 -> full
                rf = math.sin(ft / 0.16 * math.pi * 0.5)
            elif ft >= 0.86:      # gently rounded top: full -> ~0.5 (male emerges here)
                rf = 0.5 + 0.5 * math.sin((1.0 - ft) / 0.14 * math.pi * 0.5)
            else:
                rf = 1.0
            f_rad.append(fem_r * rf)
        make_tube(bm, fpts, fem_r, fem_r, 18, fem0, fem1, uv, co, 0.55, 0.80,
                  cap=True, radii=f_rad)

        # male section directly on top — NO gap (the T. latifolia ID), tapering to a point
        mpts = [Vector((tx, ty, fem_top + (mal_top - fem_top) * (i / 4.0))) for i in range(5)]
        make_tube(bm, mpts, fem_r * 0.5, 0.003, 14, mal0, mal1, uv, co, 0.80, 0.95, cap=True)

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
# Species: MISSING TIER 1/2 — grasses + Black-eyed Susan
# ==========================================================================

def make_little_bluestem():
    """Little Bluestem (Schizachyrium scoparium) — 0.6-1.2m.
    Signature meadow bunch grass. Blue-green summer, coppery-bronze fall.
    Upright clump with fluffy silver seed heads. ~180 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.15:
            return (0.28, 0.34, 0.20)   # blue-green base
        elif t < 0.6:
            return (0.30, 0.38, 0.22)   # blue-green mid
        elif t < 0.8:
            return (0.40, 0.38, 0.24)   # transition
        else:
            return (0.55, 0.42, 0.22)   # seed head zone

    # 6 narrow folded planes, 7 segments — tighter clump than bottlebrush
    make_crossed_planes(bm, 0.90, 0.16, 0.08, 6, 7, color_func, uv, co, fold=0.15)

    # 4 seed stalks with fluffy silver-white tufts
    rng = random.Random(1401)
    for s in range(4):
        sa = rng.uniform(0, math.tau)
        sx = math.cos(sa) * 0.035
        sy = math.sin(sa) * 0.035
        stalk_pts = [
            Vector((sx, sy, 0.50)),
            Vector((sx * 1.1, sy * 1.1, 0.72)),
            Vector((sx * 1.15, sy * 1.15, 0.92)),
        ]
        make_tube(bm, stalk_pts, 0.002, 0.0015, 3,
                  (0.40, 0.38, 0.24), (0.55, 0.48, 0.30),
                  uv, co, 0.55, 0.85)
        # Fluffy tuft at top
        top = stalk_pts[-1]
        for br in range(4):
            bra = (br / 4) * math.tau + rng.uniform(-0.3, 0.3)
            brv = top + Vector((math.cos(bra) * 0.015, math.sin(bra) * 0.015,
                                rng.uniform(-0.01, 0.03)))
            make_leaf_card(bm, brv, 0.010, 0.030, bra, 0.3,
                          (0.72, 0.68, 0.60), 0.88, uv, co)  # silvery white
    return bm


def make_switchgrass():
    """Switchgrass (Panicum virgatum) — 1.0-2.0m.
    Tall warm-season native grass. Broad arching leaves, airy panicle.
    Blue-green summer, golden fall. ~200 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.1:
            return (0.25, 0.32, 0.18)
        elif t < 0.55:
            return (0.28, 0.38, 0.20)   # blue-green
        elif t < 0.75:
            return (0.35, 0.38, 0.22)
        else:
            return (0.48, 0.42, 0.22)   # panicle zone

    # Taller, broader than bluestem — 5 planes, 8 segments
    make_crossed_planes(bm, 1.6, 0.28, 0.12, 5, 8, color_func, uv, co, fold=0.12)

    # 3 airy panicle stalks
    rng = random.Random(1402)
    for s in range(3):
        sa = rng.uniform(0, math.tau)
        sx = math.cos(sa) * 0.04
        sy = math.sin(sa) * 0.04
        stalk_pts = [
            Vector((sx, sy, 0.95)),
            Vector((sx * 1.1, sy * 1.1, 1.30)),
            Vector((sx * 1.15, sy * 1.15, 1.58)),
        ]
        make_tube(bm, stalk_pts, 0.003, 0.002, 3,
                  (0.35, 0.38, 0.22), (0.48, 0.42, 0.22),
                  uv, co, 0.6, 0.88)
        # Open panicle — sparse leaf cards at angles
        top = stalk_pts[-1]
        for br in range(5):
            bra = (br / 5) * math.tau + rng.uniform(-0.3, 0.3)
            dist = rng.uniform(0.02, 0.05)
            brv = top + Vector((math.cos(bra) * dist, math.sin(bra) * dist,
                                rng.uniform(-0.06, 0.02)))
            make_leaf_card(bm, brv, 0.006, 0.025, bra, rng.uniform(-0.4, 0.4),
                          (0.50, 0.45, 0.25), 0.88, uv, co)
    return bm


def make_tussock_sedge():
    """Tussock Sedge (Carex stricta) — 0.3-1.0m.
    Forms dense elevated tussocks in wetland areas. Triangular stems.
    Yellow-green, arching narrow leaves. ~150 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.1:
            return (0.22, 0.28, 0.12)   # dark base
        elif t < 0.6:
            return (0.30, 0.40, 0.18)   # yellow-green
        else:
            return (0.38, 0.42, 0.20)   # tip

    # Dense arching clump — 7 narrow planes, 5 segments
    make_crossed_planes(bm, 0.70, 0.20, 0.06, 7, 5, color_func, uv, co, fold=0.20)
    return bm


def make_pa_sedge():
    """Pennsylvania Sedge (Carex pensylvanica) — 0.15-0.30m.
    Low ground-hugging sedge, shade-tolerant woodland ground cover.
    Forms dense mats. Very short, fine-textured. ~100 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")

    def color_func(t):
        if t < 0.15:
            return (0.18, 0.26, 0.10)
        elif t < 0.7:
            return (0.24, 0.34, 0.14)   # medium green
        else:
            return (0.30, 0.36, 0.16)   # lighter tip

    # Very short, dense — 8 narrow planes, 3 segments
    make_crossed_planes(bm, 0.22, 0.18, 0.04, 8, 3, color_func, uv, co, fold=0.25)
    return bm


def make_black_eyed_susan():
    """Black-eyed Susan (Rudbeckia hirta) — 0.5-1.0m.
    Bright yellow-orange ray petals around dark brown-black cone.
    Meadow/prairie signature flower. Hairy stems. ~300 faces."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(1405)

    h = 0.80
    # 2 stems (main + side branch)
    for stem in range(2):
        pts = []
        off_x = rng.uniform(-0.04, 0.04) if stem > 0 else 0
        off_y = rng.uniform(-0.04, 0.04) if stem > 0 else 0
        stem_h = h * (0.7 if stem > 0 else 1.0)
        for i in range(6):
            t = i / 5
            pts.append(Vector((off_x + rng.gauss(0, 0.008),
                               off_y + rng.gauss(0, 0.008),
                               stem_h * t)))
        make_tube(bm, pts, 0.005, 0.003, 4,
                  (0.22, 0.30, 0.10), (0.26, 0.34, 0.12),
                  uv, co, 0.0, 0.5)

        # 3-4 hairy lanceolate leaves per stem
        for node in range(1, 4):
            t = node / 5
            lc = pts[node].copy()
            for side in [-1, 1]:
                if rng.random() < 0.6:
                    la = side * 1.3 + rng.uniform(-0.3, 0.3)
                    make_leaf_card(bm, lc + Vector((math.cos(la) * 0.06,
                                                    math.sin(la) * 0.06, 0)),
                                  0.06, 0.10, la, rng.uniform(-0.1, 0.2),
                                  (0.20, 0.34, 0.08), t * 0.4, uv, co)

        # Flower head — dark brown-black cone center
        fc = pts[-1]
        make_leaf_card(bm, fc + Vector((0, 0, 0.01)), 0.025, 0.030, 0, 0.1,
                      (0.15, 0.10, 0.04), 0.95, uv, co)  # dark cone

        # 10-14 bright yellow ray petals radiating outward
        n_rays = rng.randint(10, 14)
        for p in range(n_rays):
            pa = (p / n_rays) * math.tau + rng.uniform(-0.08, 0.08)
            petal_len = rng.uniform(0.035, 0.050)
            pv = fc + Vector((math.cos(pa) * 0.020, math.sin(pa) * 0.020, -0.005))
            make_leaf_card(bm, pv, 0.014, petal_len, pa, -0.35,
                          (0.88, 0.72, 0.08), 0.92, uv, co)  # bright yellow-orange

    return bm


def make_goldenrod(seed=2301):
    """Goldenrod (Solidago canadensis/altissima) — 0.8-1.2m.
    Densely-leafy erect stem topped by a one-sided (SECUND) arching golden
    plume — pyramidal, nodding to one side like a golden fountain. Colonial
    autumn meadow perennial; the secund plume is the identity. ~750 faces.
    See notes/refs/veg/goldenrod/BRIEF.md."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)

    H = rng.uniform(0.85, 1.15)
    lean_dir = rng.uniform(0.0, math.tau)            # the side the plume arches to
    ldx, ldy = math.cos(lean_dir), math.sin(lean_dir)
    stem_lo = (0.20, 0.30, 0.12)
    stem_hi = (0.30, 0.34, 0.16)
    leaf_lo = (0.17, 0.34, 0.09)
    leaf_hi = (0.27, 0.45, 0.15)
    leaf_top = H * 0.70                               # foliage clothes up to the plume

    # --- erect stem, accumulating a gentle lean toward the plume side
    n_seg = 9
    pts = []
    for i in range(n_seg):
        t = i / (n_seg - 1)
        bend = (t ** 1.6) * 0.06
        pts.append(Vector((ldx * bend + rng.uniform(-0.008, 0.008),
                           ldy * bend + rng.uniform(-0.008, 0.008),
                           H * t)))
    make_tube(bm, pts, 0.011, 0.004, 5, stem_lo, stem_hi, uv, co)

    def stem_at(z):
        t = max(0.0, min(1.0, z / H))
        bend = (t ** 1.6) * 0.06
        return Vector((ldx * bend, ldy * bend, z))

    # --- DENSE lanceolate foliage clothing the whole stem (no bare zone):
    #     ascending, appressed leaves at tightly-spaced nodes (golden-angle
    #     phyllotaxy), overlapping vertically into an erect leafy spike that
    #     hides the stem; longer below, shorter upward — NOT a drooping tassel.
    n_nodes = 28
    for li in range(n_nodes):
        t = (li + 0.5) / n_nodes
        z = leaf_top * t
        base = stem_at(z)
        leaf_len = (0.15 - t * 0.07) * rng.uniform(0.85, 1.15)
        for k in range(3):                           # 3 leaves per node
            la = li * 2.39996 + k * math.tau / 3 + rng.uniform(-0.2, 0.2)  # golden-angle
            off = leaf_len * 0.22                     # hug the stem
            lc = base + Vector((math.cos(la) * off, math.sin(la) * off, leaf_len * 0.34))
            lcol = _lerp_color(leaf_lo, leaf_hi, rng.random())[:3]
            tilt = rng.uniform(0.7, 1.05)             # strongly ascending (appressed)
            make_leaf_card(bm, lc, leaf_len * 0.24, leaf_len, la, tilt, lcol, 0.5, uv, co)

    # --- one-sided arching golden plume: spine arches to lean side & nods over,
    #     branchlets longer at the base (pyramidal), each densely massed with
    #     tiny heads so the plume reads as a solid golden fountain, not dots.
    #     Starts where the leafy spike ends (no bare stem between).
    gold_lo = (0.83, 0.70, 0.09)
    gold_hi = (0.95, 0.85, 0.24)
    pz0 = H * 0.68
    plume_h = H * 0.40
    n_spine = 8
    spine = []
    for i in range(n_spine):
        t = i / (n_spine - 1)
        arch = math.sin(t * 1.4) * 0.24                  # lateral reach (the secund curve)
        rise = plume_h * (t - 0.12 * t * t)              # rises, tip noses over
        spine.append(Vector((ldx * arch, ldy * arch, pz0 + rise)))
    for i in range(n_spine):
        t = i / (n_spine - 1)
        sp = spine[i]
        branch_len = (1.0 - t) * 0.20 + 0.03             # long low → short at tip
        n_br = max(3, int(7 * (1.0 - t)) + 2)
        for _ in range(n_br):
            # spread biased to the lean side keeps the plume one-sided
            ba = lean_dir + rng.uniform(-0.9, 0.9)
            bl = branch_len * rng.uniform(0.7, 1.1)
            tip = sp + Vector((math.cos(ba) * bl, math.sin(ba) * bl, -bl * 0.4 + 0.02))
            n_fc = 6
            for f in range(n_fc):
                ft = (f + 0.5) / n_fc
                fcp = sp.lerp(tip, ft) + Vector((rng.uniform(-0.014, 0.014),
                                                 rng.uniform(-0.014, 0.014),
                                                 rng.uniform(-0.008, 0.008)))
                gcol = _lerp_color(gold_lo, gold_hi, rng.random())[:3]
                make_leaf_card(bm, fcp, 0.022, 0.030,
                               ba + rng.uniform(-0.4, 0.4),
                               rng.uniform(-0.25, 0.35), gcol, 0.9, uv, co)

    return bm


def _aster_daisy(bm, center, radius, ray_col, n_rays, uv_layer, col_layer, rng):
    """A small composite daisy: yellow disc center + ring of ray petals."""
    make_leaf_card(bm, center + Vector((0, 0, 0.002)),
                   radius * 0.5, radius * 0.5, rng.uniform(0, math.tau), 0.0,
                   (0.92, 0.78, 0.12), 0.95, uv_layer, col_layer)   # yellow eye
    for p in range(n_rays):
        pa = (p / n_rays) * math.tau + rng.uniform(-0.1, 0.1)
        pv = center + Vector((math.cos(pa) * radius * 0.55,
                              math.sin(pa) * radius * 0.55, -0.002))
        make_leaf_card(bm, pv, radius * 0.42, radius * 1.05, pa, -0.25,
                       ray_col, 0.92, uv_layer, col_layer)


def make_aster(seed=2901):
    """Aster (Symphyotrichum spp. — New England / smooth) — 0.8-1.2m.
    Bushy, much-branched rounded mound smothered in masses of small
    purple/violet daisies with yellow centers in fall — a dense mounded
    bush of color (NOT the low white woodland carpet of white wood aster).
    ~1700 faces. See notes/refs/veg/aster/BRIEF.md."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    co = bm.loops.layers.color.new("Col")
    rng = random.Random(seed)

    H = rng.uniform(0.85, 1.15)
    mound_r = H * 0.38                                # aspect ~0.75:1 (W ≈ 0.76·H)
    mound_cz = H * 0.58                               # mound center height
    if rng.random() < 0.2:
        ray_col = (0.92, 0.93, 0.95)                  # occasional white form
    else:
        ray_col = (rng.uniform(0.52, 0.64), rng.uniform(0.34, 0.44),
                   rng.uniform(0.66, 0.78))           # purple/violet, per-plant jitter
    stem_lo = (0.22, 0.28, 0.13)
    stem_hi = (0.28, 0.32, 0.16)
    leaf_lo = (0.16, 0.32, 0.10)
    leaf_hi = (0.26, 0.42, 0.16)

    # mound shell radius at a given height fraction (0 base … 1 top): rounded dome
    def shell_r(ef):
        return mound_r * math.sqrt(max(0.0, 1.0 - ((ef - 0.45) / 0.62) ** 2))

    # --- short, central structural stems (kept inside the leaf mass so they
    #     don't read as a splayed vase of sticks)
    n_stems = rng.randint(4, 5)
    for si in range(n_stems):
        ang = si * math.tau / n_stems + rng.uniform(-0.3, 0.3)
        lean = mound_r * rng.uniform(0.30, 0.6)       # stay near the core
        n_seg = 7
        pts = []
        for i in range(n_seg):
            t = i / (n_seg - 1)
            r = lean * (t ** 1.3)
            pts.append(Vector((math.cos(ang) * r + rng.uniform(-0.01, 0.01),
                               math.sin(ang) * r + rng.uniform(-0.01, 0.01),
                               H * t * rng.uniform(0.92, 1.0))))
        make_tube(bm, pts, 0.008, 0.003, 5, stem_lo, stem_hi, uv, co)

    # --- DENSE leafy mound body: scatter many overlapping narrow lance leaves
    #     through the rounded dome volume, outward-facing, so the bush reads as a
    #     solid leafy mass with little see-through (daisies nestle ON this).
    n_leaves = 110
    for _ in range(n_leaves):
        ef = rng.random() ** 0.6                      # bias toward the upper mound
        phi = rng.uniform(0, math.tau)
        rr = shell_r(ef) * rng.uniform(0.35, 1.0)     # fill interior→shell densely
        zz = (H * 0.10) + (H - H * 0.10) * ef
        cx, cy = math.cos(phi) * rr, math.sin(phi) * rr
        ll = rng.uniform(0.055, 0.10)
        lcol = _lerp_color(leaf_lo, leaf_hi, rng.random())[:3]
        # outward + upward facing, slight droop
        make_leaf_card(bm, Vector((cx, cy, zz)), ll * 0.32, ll, phi,
                       rng.uniform(-0.1, 0.45), lcol, 0.5, uv, co)

    # --- daisies smothering the outer-upper surface of the leafy mound
    n_daisies = rng.randint(24, 30)
    for _ in range(n_daisies):
        ef = 0.30 + 0.70 * rng.random()              # upper-outer surface
        phi = rng.uniform(0, math.tau)
        rr = shell_r(ef) * rng.uniform(0.95, 1.12)   # sit just outside the leaf shell
        zz = (H * 0.10) + (H - H * 0.10) * ef + rng.uniform(-0.02, 0.02)
        center = Vector((math.cos(phi) * rr, math.sin(phi) * rr, zz))
        _aster_daisy(bm, center, rng.uniform(0.020, 0.030),
                     ray_col, rng.randint(7, 9), uv, co, rng)

    return bm


# ==========================================================================
# Build all species
# ==========================================================================

# All species generated procedurally — no external asset dependencies.
# BD3D models were previously used but removed for distributable-only policy.

SPECIES = [
    # Tier 1+2: shrubs (BD3D replaced — skipped), herbs, ferns, wetland
    # Spicebush: 3 variants with different seeds for visual variety
    # Named _0/_1/_2 to match undergrowth_builder.gd variant loader
    (lambda: make_spicebush(seed=101), "Shrub_Spicebush_0"),
    (lambda: make_spicebush(seed=202), "Shrub_Spicebush_1"),
    (lambda: make_spicebush(seed=303), "Shrub_Spicebush_2"),
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
    # Cattail: 3 seed variants (different blade angles/heights + spike placement) so
    # dense colony stands don't tile. All share tex_leaf_Wetland_Cattail.png + the
    # warm-brown stem_color (spike). Named _0/_1/_2 for the runtime variant loader.
    (lambda: make_cattail(seed=901, height=2.5),  "Wetland_Cattail_0"),
    (lambda: make_cattail(seed=917, height=2.8),  "Wetland_Cattail_1"),
    (lambda: make_cattail(seed=933, height=2.25), "Wetland_Cattail_2"),
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
    # Additional grasses + meadow flower
    (make_little_bluestem,     "Grass_LittleBluestem"),
    (make_switchgrass,         "Grass_Switchgrass"),
    (make_tussock_sedge,       "Grass_TussockSedge"),
    (make_pa_sedge,            "Grass_PASedge"),
    (make_black_eyed_susan,    "Herb_BlackeyedSusan"),
    # Meadow fall-color forbs — colonial, 3 variants each (v=3 in the runtime
    # SPECIES array) for anti-tiling in the dense patches they form.
    (lambda: make_goldenrod(seed=2301), "Flower_Goldenrod_0"),
    (lambda: make_goldenrod(seed=2302), "Flower_Goldenrod_1"),
    (lambda: make_goldenrod(seed=2303), "Flower_Goldenrod_2"),
    (lambda: make_aster(seed=2901),     "Flower_Aster_0"),
    (lambda: make_aster(seed=2902),     "Flower_Aster_1"),
    (lambda: make_aster(seed=2903),     "Flower_Aster_2"),
]

def render_thumbnail(obj, name, out_dir):
    """Render a lit 3/4 view of a freshly-built species (vertex colors wired
    via make_material). Offscreen Eevee — no display needed. For visual DoD."""
    import mathutils
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 700
    scene.render.resolution_y = 900
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("thumb_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.60, 0.65, 0.72, 1.0)
        bg.inputs[1].default_value = 0.9
    scene.world = world

    zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    xs = [(obj.matrix_world @ v.co).x for v in obj.data.vertices]
    h = (max(zs) - min(zs)) if zs else 1.0
    cz = ((max(zs) + min(zs)) * 0.5) if zs else 0.5
    span = max(h, (max(xs) - min(xs)) if xs else 0.6, 0.5)

    cam_data = bpy.data.cameras.new("thumb_cam")
    cam = bpy.data.objects.new("thumb_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dist = span * 2.1
    cam.location = (dist * 0.5, -dist, cz + h * 0.12)
    look = mathutils.Vector((0, 0, cz)) - mathutils.Vector(cam.location)
    cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = 55

    sun_d = bpy.data.lights.new("sun", 'SUN'); sun_d.energy = 3.5
    sun = bpy.data.objects.new("sun", sun_d); scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(55), math.radians(10), math.radians(40))
    fill_d = bpy.data.lights.new("fill", 'SUN'); fill_d.energy = 1.1
    fill = bpy.data.objects.new("fill", fill_d); scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(62), 0, math.radians(-130))

    scene.render.filepath = os.path.join(out_dir, f"thumb_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"    thumbnail → {scene.render.filepath}")


if __name__ == "__main__":
    import sys
    # Optional name filter after `--` (build a subset): e.g.
    #   blender --background --python scripts/make_undergrowth.py -- Goldenrod Aster
    # Include the token `thumb` to also render lit thumbnails (visual DoD).
    name_filter: list = []
    want_thumb = False
    if "--" in sys.argv:
        name_filter = sys.argv[sys.argv.index("--") + 1:]
        if "thumb" in [k.lower() for k in name_filter]:
            want_thumb = True
            name_filter = [k for k in name_filter if k.lower() != "thumb"]
    build = [(f, n) for (f, n) in SPECIES
             if not name_filter or any(k.lower() in n.lower() for k in name_filter)]

    print("=" * 60)
    print(f"Building {len(build)} undergrowth species"
          + (f" (filter: {name_filter})" if name_filter else ""))
    print("=" * 60)

    for func, name in build:
        print(f"\n  Building {name}...")
        clear_scene()
        bm = func()
        obj = finalize_and_export(bm, name)
        if want_thumb and obj is not None:
            render_thumbnail(obj, name,
                             os.path.join(PROJECT_DIR, "notes", "veg_thumbs"))

    print(f"\n{'=' * 60}")
    print(f"Done — {len(build)} undergrowth GLBs exported")
    print("=" * 60)

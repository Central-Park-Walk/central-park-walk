"""Shared geometry helpers for vegetation model generation.

Used by all make_*.py vegetation scripts. Provides reusable primitives
for tubes, leaf cards, hemisphere shells, fern fronds, and mushroom caps.

Import: sys.path.insert(0, os.path.dirname(__file__))
        from vegetation_helpers import *
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
VEG_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
TREE_DIR = os.path.join(PROJECT_DIR, "models", "trees")


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
    """Vertex-color material for vegetation."""
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


def lerp_color(c0, c1, t):
    """Interpolate between two RGB tuples, return RGBA list."""
    return [c0[i] + (c1[i] - c0[i]) * t for i in range(3)] + [1.0]


# ==========================================================================
# Tubes (stems, branches, trunks)
# ==========================================================================

def make_tube(bm, points, r_start, r_end, n_sides, color_start, color_end,
              uv_layer, col_layer, uv_y_start=0.0, uv_y_end=1.0):
    """Tapered tube along a list of points. UV.x=0.5 (stem convention)."""
    rings = []
    n = len(points)
    for i, pt in enumerate(points):
        t = i / max(n - 1, 1)
        r = r_start + (r_end - r_start) * t
        uv_y = uv_y_start + (uv_y_end - uv_y_start) * t
        col = lerp_color(color_start, color_end, t)

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


# ==========================================================================
# Leaf cards (diamond shape with atlas UV)
# ==========================================================================

def make_leaf_card(bm, center, width, height, angle_y, tilt, color,
                   uv_layer, col_layer):
    """Diamond-shaped leaf card. UV spans 0-1 for shader alpha cutout."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)
    ct, st = math.cos(tilt), math.sin(tilt)
    hw, hh = width * 0.5, height * 0.5

    dx = Vector((ca, sa, 0))
    dz = Vector((-sa * st, ca * st, ct))

    vb = bm.verts.new(center - dz * hh)
    vr = bm.verts.new(center + dx * hw - dz * hh * 0.1)
    vt = bm.verts.new(center + dz * hh)
    vl = bm.verts.new(center - dx * hw - dz * hh * 0.1)

    col_rgba = list(color[:3]) + [1.0] if len(color) == 3 else list(color)
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


# ==========================================================================
# Hemisphere card shell (shrubs, leaf clusters)
# ==========================================================================

def make_hemisphere_shell(bm, center, radius, n_outer, n_inner,
                          card_size, color, uv_layer, col_layer, rng):
    """Hemisphere of outward-facing leaf cards for shrub/cluster volume.
    Cards face outward from center — custom normals applied separately."""
    col_rgba = list(color[:3]) + [1.0]

    # Outer shell cards (define the silhouette)
    for i in range(n_outer):
        azimuth = (i / n_outer) * math.tau + rng.uniform(-0.25, 0.25)
        elevation = rng.uniform(0.3, 1.3)
        dist = radius * rng.uniform(0.65, 0.85)
        cs = card_size * rng.uniform(0.8, 1.2)

        cx = math.cos(azimuth) * math.cos(elevation) * dist
        cy = math.sin(azimuth) * math.cos(elevation) * dist
        cz = math.sin(elevation) * dist + radius * 0.2

        pos = center + Vector((cx, cy, cz))
        angle = azimuth + rng.uniform(-0.3, 0.3)
        tilt = elevation * 0.5 + rng.uniform(-0.2, 0.2)
        make_leaf_card(bm, pos, cs, cs * rng.uniform(0.8, 1.3),
                       angle, tilt, color, uv_layer, col_layer)

    # Inner fill cards (prevent see-through)
    for i in range(n_inner):
        azimuth = rng.uniform(0, math.tau)
        elevation = rng.uniform(0.4, 1.0)
        dist = radius * rng.uniform(0.25, 0.50)
        cs = card_size * rng.uniform(0.5, 0.8)

        cx = math.cos(azimuth) * math.cos(elevation) * dist
        cy = math.sin(azimuth) * math.cos(elevation) * dist
        cz = math.sin(elevation) * dist + radius * 0.15

        pos = center + Vector((cx, cy, cz))
        make_leaf_card(bm, pos, cs, cs, rng.uniform(0, math.tau),
                       rng.uniform(-0.3, 0.3), color, uv_layer, col_layer)


# ==========================================================================
# Fern fronds (rachis + individual pinnae)
# ==========================================================================

def make_fern_frond(bm, origin, length, n_pinnae, pinna_len, pinna_width,
                    arch, droop, angle_y, color_base, color_tip,
                    uv_layer, col_layer):
    """Fern frond with individual pinnae cards along a curved rachis.
    Creates the distinctive comb-like silhouette that reads as 'fern'."""
    ca, sa = math.cos(angle_y), math.sin(angle_y)

    # Build rachis path (curved, arching outward then drooping)
    n_rachis = 6
    rachis_pts = []
    for i in range(n_rachis):
        t = i / (n_rachis - 1)
        rise = length * 0.75 * t * (1.0 - t * droop)
        out = length * t * arch
        rachis_pts.append(Vector((
            origin.x + ca * out,
            origin.y + sa * out,
            origin.z + rise
        )))

    # Draw thin rachis stem
    make_tube(bm, rachis_pts, 0.004, 0.001, 3,
              color_base, color_tip, uv_layer, col_layer, 0.0, 1.0)

    # Pinnae along rachis — alternating left/right
    for i in range(n_pinnae):
        t = (i + 1.5) / (n_pinnae + 1)
        if t > 0.98:
            break
        idx = min(int(t * (n_rachis - 1)), n_rachis - 2)
        frac = t * (n_rachis - 1) - idx
        pt = rachis_pts[idx].lerp(rachis_pts[idx + 1], frac)

        # Pinnae taper toward tip
        scale = 1.0 - t * 0.6
        pw = pinna_width * scale
        pl = pinna_len * scale
        if pw < 0.005 or pl < 0.005:
            continue

        # Alternate sides, slight angle off rachis plane
        side = 1.0 if i % 2 == 0 else -1.0
        pinna_angle = angle_y + side * 1.3 + (i * 0.05)
        pinna_tilt = side * 0.25

        col = lerp_color(color_base, color_tip, t)
        make_leaf_card(bm, pt, pw, pl, pinna_angle, pinna_tilt,
                       col[:3], uv_layer, col_layer)


# ==========================================================================
# Star-pattern herbs (3 crossed planes at 60°)
# ==========================================================================

def make_star_herb(bm, height, width, n_planes, segments, color_func,
                   uv_layer, col_layer):
    """Star pattern crossed planes. UV.x spans 0-1 for alpha cutout."""
    for p in range(n_planes):
        angle = (p / n_planes) * math.pi
        ca, sa = math.cos(angle), math.sin(angle)

        for s in range(segments):
            t0 = s / segments
            t1 = (s + 1) / segments
            z0 = height * t0
            z1 = height * t1
            w0 = width * 0.5 * (1.0 + 0.3 * math.sin(t0 * math.pi))
            w1 = width * 0.5 * (1.0 + 0.3 * math.sin(t1 * math.pi))
            c0 = list(color_func(t0)) + [1.0]
            c1 = list(color_func(t1)) + [1.0]

            v0 = bm.verts.new((-ca * w0, -sa * w0, z0))
            v1 = bm.verts.new((ca * w0, sa * w0, z0))
            v2 = bm.verts.new((ca * w1, sa * w1, z1))
            v3 = bm.verts.new((-ca * w1, -sa * w1, z1))
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


# ==========================================================================
# Mushroom cap (lathe/spin)
# ==========================================================================

def make_mushroom_cap(bm, stem_top, cap_radius, cap_height, n_segments,
                      color, uv_layer, col_layer):
    """Smooth mushroom cap via profile + spin around Z axis."""
    col_rgba = list(color[:3]) + [1.0]

    # Cap profile (half cross-section): stem-top → edge → rim
    n_profile = 5
    profile_verts = []
    for i in range(n_profile):
        t = i / (n_profile - 1)
        r = cap_radius * math.sin(t * math.pi * 0.5)
        z = stem_top + cap_height * math.cos(t * math.pi * 0.5)
        v = bm.verts.new((r, 0, z))
        profile_verts.append(v)

    # Create edges for spin
    profile_edges = []
    for i in range(len(profile_verts) - 1):
        e = bm.edges.new([profile_verts[i], profile_verts[i + 1]])
        profile_edges.append(e)

    # Spin around Z axis
    geom = list(profile_verts) + list(profile_edges)
    result = bmesh.ops.spin(bm, geom=geom, cent=(0, 0, 0),
                            axis=(0, 0, 1), angle=math.tau,
                            steps=n_segments, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)

    # Apply color and UVs to all cap faces
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = (0.5, 0.5)
            loop[col_layer] = col_rgba


# ==========================================================================
# Normal editing
# ==========================================================================

def apply_hemisphere_normals(mesh, center=None):
    """Set custom split normals pointing outward from plant center.
    Hides individual card planarity under smooth hemisphere-like shading."""
    if center is None:
        # Compute center from bounding box
        verts = mesh.vertices
        if len(verts) == 0:
            return
        xs = [v.co.x for v in verts]
        ys = [v.co.y for v in verts]
        center = Vector((
            (min(xs) + max(xs)) * 0.5,
            (min(ys) + max(ys)) * 0.5,
            0.0  # base of plant
        ))

    # NB: mesh.use_auto_smooth / auto_smooth_angle were REMOVED in Blender 4.1.
    # Custom split normals set below are always honored now — no flag needed.

    up = Vector((0, 0, 1))
    custom_normals = []
    for loop in mesh.loops:
        vert = mesh.vertices[loop.vertex_index]
        outward = Vector(vert.co) - center
        if outward.length < 0.001:
            outward = up.copy()
        outward.normalize()
        # Blend outward + up for softer lighting
        blended = outward.lerp(up, 0.35).normalized()
        custom_normals.append(tuple(blended))

    mesh.normals_split_custom_set(custom_normals)


# ==========================================================================
# Export
# ==========================================================================

def finalize_and_export(bm, name, out_dir=None):
    """Convert bmesh to mesh, apply hemisphere normals, export GLB."""
    if out_dir is None:
        out_dir = VEG_DIR
    os.makedirs(out_dir, exist_ok=True)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)

    # Apply hemisphere normals
    apply_hemisphere_normals(mesh)

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    mat = make_material(name + "_Mat")
    obj.data.materials.append(mat)

    for poly in obj.data.polygons:
        poly.use_smooth = True

    bm.free()

    # Export
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(out_dir, f"{name}.glb")
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

"""Mtree-independent mesh finishing shared by authored tree inputs."""
from __future__ import annotations

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree


def weld_bark_junctions(obj, distance=0.045):
    """Weld overlapping verts at parent/child forks only.

    Blind ``remove_doubles`` at sculpt junction distances (≥0.1) merges opposite
    sides of thin tubes (tip diameter ~0.05), collapsing bark into ribbons with
    thousands of non-manifold edges. When ``stem_id`` is present, only verts from
    *different* strands may merge — same-ring geometry stays volumetric.

    Cross-strand pairs are further limited by local ``radius``: an absolute search
    ball of ``distance`` on thin forks (r≈0.04) still pulls whole rings into one
    clump (pinched / hourglass collars). Merge only when
    ``d <= min(distance, 0.55*(r_i+r_j))``.
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    before = len(bm.verts)
    stem_attr = mesh.attributes.get("stem_id")
    if stem_attr is None or before < 2:
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=float(distance))
    else:
        stem = [0] * before
        stem_attr.data.foreach_get("value", stem)
        radii = [0.05] * before
        radius_attr = mesh.attributes.get("radius")
        if radius_attr is not None:
            radius_attr.data.foreach_get("value", radii)
        kd = KDTree(before)
        for i, vert in enumerate(bm.verts):
            kd.insert(vert.co, i)
        kd.balance()
        parent = list(range(before))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i, vert in enumerate(bm.verts):
            for _co, j, dist in kd.find_range(vert.co, float(distance)):
                if j <= i:
                    continue
                if int(stem[i]) == int(stem[j]):
                    continue
                lim = 0.55 * (float(radii[i]) + float(radii[j]))
                lim = max(0.02, min(float(distance), lim))
                if dist <= lim:
                    union(i, j)

        targetmap = {}
        for i, vert in enumerate(bm.verts):
            root = find(i)
            if root != i:
                targetmap[vert] = bm.verts[root]
        if targetmap:
            bmesh.ops.weld_verts(bm, targetmap=targetmap)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return before - len(mesh.vertices)


def bake_wind_vertex_colors(obj):
    """Pack hierarchy depth, path extent and strand phase into COLOR_0."""
    mesh = obj.data
    count = len(mesh.vertices)
    if not count:
        return
    depth = np.zeros(count)
    extent = np.zeros(count)
    stem = np.zeros(count)
    hd = mesh.attributes.get("hierarchy_depth")
    be = mesh.attributes.get("branch_extent")
    si = mesh.attributes.get("stem_id")
    if hd and be and si:
        hd.data.foreach_get("value", depth)
        be.data.foreach_get("value", extent)
        si.data.foreach_get("value", stem)
    depth /= max(float(depth.max()), 1.0)
    extent /= max(float(extent.max()), 1.0)
    phase = np.mod(stem * 0.61803398875, 1.0)
    color = mesh.color_attributes.get("COLOR_0")
    if color is None:
        color = mesh.color_attributes.new(name="COLOR_0", type="BYTE_COLOR", domain="CORNER")
    values = []
    for loop in mesh.loops:
        index = loop.vertex_index
        values.extend((float(depth[index]), float(extent[index]), float(phase[index]), 1.0))
    color.data.foreach_set("color", values)
    mesh.color_attributes.active_color = color


def connected_components(obj):
    mesh = obj.data
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = set()
    components = 0
    for start in range(len(adjacency)):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            for neighbour in adjacency[stack.pop()]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
    return components


def non_manifold_edge_count(obj):
    mesh = obj.data
    face_count = [0] * len(mesh.edges)
    edge_lookup = {tuple(sorted(edge.vertices)): edge.index for edge in mesh.edges}
    for poly in mesh.polygons:
        vertices = list(poly.vertices)
        for i, a in enumerate(vertices):
            key = tuple(sorted((a, vertices[(i + 1) % len(vertices)])))
            if key in edge_lookup:
                face_count[edge_lookup[key]] += 1
    return sum(count != 2 for count in face_count)


def apply_leaf_shell_normals(obj, up_blend=0.32):
    mesh = obj.data
    leaf_materials = {
        i for i, material in enumerate(mesh.materials)
        if material is not None and "leaf" in material.name.lower()
    }
    leaf_vertices = {
        vertex for poly in mesh.polygons if poly.material_index in leaf_materials
        for vertex in poly.vertices
    }
    if not leaf_vertices:
        return 0
    points = [mesh.vertices[i].co for i in leaf_vertices]
    center = Vector((
        sum(p.x for p in points) / len(points),
        sum(p.y for p in points) / len(points),
        min(p.z for p in points) + 0.42 * (max(p.z for p in points) - min(p.z for p in points)),
    ))
    up = Vector((0, 0, 1))
    normals = [tuple(value.vector) for value in mesh.corner_normals]
    changed = 0
    for poly in mesh.polygons:
        if poly.material_index not in leaf_materials:
            continue
        poly.use_smooth = True
        for loop_index in poly.loop_indices:
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            outward = co - center
            if outward.length_squared < 1e-8:
                outward = up.copy()
            normal = outward.normalized().lerp(up, up_blend).normalized()
            normals[loop_index] = tuple(normal)
            changed += 1
    mesh.normals_split_custom_set(normals)
    return changed


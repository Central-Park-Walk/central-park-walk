"""Blender-native tree sculpting primitives and runtime compiler.

Editable authority is bare Bézier strands; GIMP leaf cards attach at compile.
Meshes, GLBs and review renders are generated products and can always be rebuilt.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import interpolate_bezier

SCRIPT_DIR = Path(__file__).resolve().parent
PROJ = SCRIPT_DIR.parent.parent
if str(PROJ / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJ / "scripts"))

from leaf_card_utils import create_leaf_material
import pipeline_common

SOURCE_COLLECTION = "TREE_SCULPT"
GENERATED_COLLECTION = "TREE_GENERATED"
REVIEW_COLLECTION = "TREE_REVIEW"
MODEL_HEIGHT = 5.0


def ensure_collection(name: str, parent=None):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(collection)
    return collection


def clear_collection(name: str):
    collection = bpy.data.collections.get(name)
    if collection is None:
        return
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def strand_objects(stage: str | None = None):
    collection = bpy.data.collections.get(SOURCE_COLLECTION)
    if collection is None:
        return []
    result = [o for o in collection.objects if o.type == "CURVE" and o.get("strand_id")]
    if stage is not None:
        result = [o for o in result if o.get("stage") == stage]
    return sorted(result, key=lambda o: (int(o.get("branch_order", 0)), o["strand_id"]))


def find_strand(strand_id: str, stage: str | None = None):
    for obj in strand_objects(stage):
        if obj.get("strand_id") == strand_id:
            return obj
    raise KeyError(f"unknown strand: {strand_id}")


def create_strand(
    strand_id: str,
    points,
    radii,
    *,
    stage="mature",
    parent_strand="",
    branch_order=0,
    role="trunk",
    card_pattern="none",
    attach_u=1.0,
):
    if len(points) < 2 or len(points) != len(radii):
        raise ValueError("points and radii must have equal length >= 2")
    try:
        delete_strand(strand_id, stage)
    except KeyError:
        pass
    curve = bpy.data.curves.new(f"curve_{stage}_{strand_id}", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 3
    curve.bevel_resolution = 2
    curve.bevel_depth = 1.0
    curve.resolution_u = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co, radius in zip(spline.bezier_points, points, radii):
        bp.co = Vector(co)
        bp.radius = float(radius)
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(f"{stage}:{strand_id}", curve)
    ensure_collection(SOURCE_COLLECTION).objects.link(obj)
    obj["species"] = "london_plane"
    obj["stage"] = stage
    obj["strand_id"] = strand_id
    obj["parent_strand"] = parent_strand
    obj["branch_order"] = int(branch_order)
    obj["role"] = role
    obj["card_pattern"] = card_pattern
    obj["attach_u"] = float(attach_u)
    obj.show_in_front = True
    return obj


def delete_strand(strand_id: str, stage: str | None = None):
    obj = find_strand(strand_id, stage)
    bpy.data.objects.remove(obj, do_unlink=True)


def set_stage_visible(stage: str):
    for obj in strand_objects():
        visible = obj.get("stage") == stage
        obj.hide_viewport = not visible
        obj.hide_render = not visible
    bpy.context.scene["tree_sculpt_stage"] = stage


def move_point(strand_id: str, index: int, delta=None, co=None, stage=None):
    obj = find_strand(strand_id, stage)
    bp = obj.data.splines[0].bezier_points[index]
    bp.co = Vector(co) if co is not None else bp.co + Vector(delta)


def set_point_radius(strand_id: str, index: int, radius: float, stage=None):
    find_strand(strand_id, stage).data.splines[0].bezier_points[index].radius = float(radius)


def _descendants(root_id: str, stage: str):
    by_parent = {}
    for obj in strand_objects(stage):
        by_parent.setdefault(obj.get("parent_strand", ""), []).append(obj)
    result = []
    stack = [find_strand(root_id, stage)]
    while stack:
        obj = stack.pop()
        result.append(obj)
        stack.extend(by_parent.get(obj["strand_id"], []))
    return result


def transform_system(strand_id: str, *, stage, translate=(0, 0, 0), rotate_z=0.0, scale=1.0):
    objects = _descendants(strand_id, stage)
    pivot = objects[0].data.splines[0].bezier_points[0].co.copy()
    angle = math.radians(float(rotate_z))
    ca, sa = math.cos(angle), math.sin(angle)
    offset = Vector(translate)
    for obj in objects:
        for bp in obj.data.splines[0].bezier_points:
            p = (bp.co - pivot) * float(scale)
            p = Vector((p.x * ca - p.y * sa, p.x * sa + p.y * ca, p.z))
            bp.co = pivot + p + offset
            bp.radius *= float(scale)


def set_emitter(strand_id: str, pattern: str, stage=None):
    if pattern not in {"none", "tip", "along"}:
        raise ValueError("card pattern must be none, tip, or along")
    find_strand(strand_id, stage)["card_pattern"] = pattern


def duplicate_system(strand_id: str, new_id: str, *, stage, translate=(0, 0, 0), rotate_z=0.0):
    source = _descendants(strand_id, stage)
    id_map = {}
    for obj in source:
        old = obj["strand_id"]
        suffix = old[len(strand_id):]
        id_map[old] = new_id + suffix
    created = []
    for obj in source:
        points = obj.data.splines[0].bezier_points
        parent = obj.get("parent_strand", "")
        created.append(create_strand(
            id_map[obj["strand_id"]],
            [tuple(p.co) for p in points],
            [p.radius for p in points],
            stage=stage,
            parent_strand=id_map.get(parent, parent),
            branch_order=int(obj.get("branch_order", 0)),
            role=obj.get("role", ""),
            card_pattern=obj.get("card_pattern", "none"),
            attach_u=float(obj.get("attach_u", 1.0)),
        ))
    transform_system(new_id, stage=stage, translate=translate, rotate_z=rotate_z)
    return created


def _sample_strand(obj, samples_per_segment=5):
    points = obj.data.splines[0].bezier_points
    sampled = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        segment = interpolate_bezier(a.co, a.handle_right, b.handle_left, b.co, samples_per_segment + 1)
        for j, co in enumerate(segment[:-1]):
            t = j / samples_per_segment
            radius = a.radius * (1.0 - t) + b.radius * t
            sampled.append((Vector(co), radius))
    sampled.append((Vector(points[-1].co), points[-1].radius))
    return sampled


def compile_graph(stage: str):
    """Sample authored Bézier strands into a rooted vert/edge graph for Skin.

    Child strands reuse the parent attach vertex (no duplicate at the fork).
    A near-zero edge from child-base→parent is what made Skin spit out hundreds
    of components; real forks share one joint vertex.
    """
    objects = strand_objects(stage)
    if not objects:
        raise ValueError(f"stage has no authored strands: {stage}")
    nodes = []
    strands = []
    sampled_by_id = {}
    node_ids_by_id = {}
    for sid, obj in enumerate(objects):
        sampled = _sample_strand(obj)
        parent_id = obj.get("parent_strand", "")
        root_parent = -1
        if parent_id:
            parent_samples = sampled_by_id[parent_id]
            attach = sampled[0][0]
            parent_local = min(
                range(len(parent_samples)), key=lambda i: (parent_samples[i][0] - attach).length_squared
            )
            root_parent = node_ids_by_id[parent_id][parent_local]
            # Keep the joint at least as thick as the child base.
            nodes[root_parent]["radius"] = max(
                float(nodes[root_parent]["radius"]), max(0.025, float(sampled[0][1]))
            )
        ids = []
        for i, (co, radius) in enumerate(sampled):
            r = max(0.025, float(radius))
            if i == 0 and root_parent >= 0:
                ids.append(root_parent)
                continue
            parent = root_parent if i == 0 else ids[-1]
            ids.append(len(nodes))
            nodes.append({"pos": co.copy(), "parent": parent, "radius": r})
            strands.append(sid)
        sampled_by_id[obj["strand_id"]] = sampled
        node_ids_by_id[obj["strand_id"]] = ids
    return {"nodes": nodes, "strand": strands, "root": 0}


def build_curve_bevel_bark(stage: str, name="bark", *, bevel_resolution=4, resolution_u=6):
    """Mesh the authored Bézier tubes as Blender already draws them.

    Each strand is a beveled curve (viewport authority). Convert → join.
    Forks are overlapping tubes — a filled crotch volume — not leafback
    child-on-parent weld (pinch) and not Skin Modifier (sausage waists).
    """
    objects = strand_objects(stage)
    if not objects:
        raise ValueError(f"stage has no authored strands: {stage}")
    # Bump curve resolution for the convert; restore after.
    saved = []
    for obj in objects:
        curve = obj.data
        saved.append((curve, curve.bevel_resolution, curve.resolution_u))
        if obj.get("role") == "tip_host":
            # Path A: tip hosts stay thin/cheap; scaffold keeps full bevel.
            curve.bevel_resolution = min(1, int(bevel_resolution))
            curve.resolution_u = min(3, int(resolution_u))
        else:
            curve.bevel_resolution = int(bevel_resolution)
            curve.resolution_u = int(resolution_u)
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new()
        for obj in objects:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = bpy.data.meshes.new_from_object(evaluated)
            bm.from_mesh(mesh)
            bpy.data.meshes.remove(mesh)
        out_mesh = bpy.data.meshes.new(name)
        bm.to_mesh(out_mesh)
        bm.free()
    finally:
        for curve, bevel_res, res_u in saved:
            curve.bevel_resolution = bevel_res
            curve.resolution_u = res_u
    obj = bpy.data.objects.new(name, out_mesh)
    bpy.context.scene.collection.objects.link(obj)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.update()
    return obj


def _bark_material():
    mat = bpy.data.materials.get("london_plane_bark_sculpt")
    if mat is None:
        mat = bpy.data.materials.new("london_plane_bark_sculpt")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (0.30, 0.26, 0.19, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.82
        mat.diffuse_color = (0.30, 0.26, 0.19, 1.0)
    return mat


# Chris's GIMP 4-leaf sprig. One card already IS the foliage unit; stacking
# rebuilds a "tight green ball" (tree-pipeline-playbook §4).
LEAF_CLUSTER_TEXTURE = PROJ / "textures/leaves/london_plane_cluster.png"
CARDS_PER_CLUSTER = 1
# Match production `_LP_V2_HALF` (was 1.20). Garden scales the 5 m model up to
# 12/20/26 m, so oversized half-factors turned tip sprigs into ~1.5 m world stamps.
CARD_HALF_FACTOR = 1.00
# Measured stem base in london_plane_cluster.png (opaque tip of drawn petiole;
# image 1024², lowest opaque band centroid ≈ px(286,971) → u=0.28, v=0.05 from
# bottom). Pinning UV (0.5,0) left the stem ~0.22·width beside the tip — Chris's
# "thrown at the branch" read. Same contract as generate_trees_mtree._sprig_cards.
CARD_STEM_ANCHOR = (0.28, 0.055)
# Authoring-space half-extent before MODEL_HEIGHT normalize. Prior 0.42–0.58 read
# as floating sheets after garden height scale; ~half keeps a 4-leaf sprig
# tip-local (~0.5–0.7 m world on mature) so stem→twig stays visible.
CARD_SIZE_MATURE = (0.20, 0.28)
CARD_SIZE_YOUNG = (0.14, 0.20)


def _leaf_material():
    mat = bpy.data.materials.get("london_plane_leaf_sculpt")
    if mat is None:
        mat = create_leaf_material(
            "london_plane_leaf_sculpt",
            real_texture=str(LEAF_CLUSTER_TEXTURE),
        )
        mat.diffuse_color = (0.28, 0.52, 0.18, 1.0)
    return mat


def foliage_anchors(stage: str):
    """Emitter samples: (position, outward direction, strand_id, sample_index).

    `tip` = one card at the strand's true terminal. `along` = spaced mid-strand
    samples. `cluster` = dense along-branch sprigs on Path A tip hosts (skip the
    scaffold attach; stations from ~12%→tip, with a small lateral pair so each
    station reads as a leafy knot — not a stacked green ball at one UV).
    """
    anchors = []
    for obj in strand_objects(stage):
        pattern = obj.get("card_pattern", "none")
        # Path A tip hosts always get along-branch clusters (W-31), even if an
        # older .blend still stores card_pattern=tip.
        if obj.get("role") == "tip_host":
            pattern = "cluster"
        if pattern == "none":
            continue
        samples_per = 4 if pattern == "cluster" else 6
        samples = _sample_strand(obj, samples_per)
        if not samples:
            continue
        if pattern == "tip":
            indices = [len(samples) - 1]
        elif pattern == "cluster":
            start = max(1, int(len(samples) * 0.12))
            indices = list(range(start, len(samples)))
        else:
            start = int(len(samples) * 0.35)
            indices = list(range(start, len(samples), 2))
        for i in indices:
            co = samples[i][0]
            if i + 1 < len(samples):
                direction = samples[i + 1][0] - co
            elif i > 0:
                direction = co - samples[i - 1][0]
            else:
                direction = Vector((0.0, 0.0, 1.0))
            if direction.length_squared < 1e-12:
                direction = Vector((0.0, 0.0, 1.0))
            direction = direction.normalized()
            if pattern == "cluster":
                # One on-twig sprig + one offset sibling = a small cluster station.
                anchors.append((co, direction, obj["strand_id"], i))
                # Perpendicular in the XY-ish plane of the twig (stable lateral).
                side = direction.cross(Vector((0.0, 0.0, 1.0)))
                if side.length_squared < 1e-10:
                    side = direction.cross(Vector((1.0, 0.0, 0.0)))
                side = side.normalized()
                offset = 0.06 + 0.02 * (i % 3)
                anchors.append((co + side * offset, direction, obj["strand_id"], i))
            else:
                anchors.append((co, direction.normalized(), obj["strand_id"], i))
    return anchors


def _append_sprig_card(bm, uv_layer, pos, size, direction, rng, gidx):
    """One GIMP sprig quad, twig-aligned — drawn stem pinned to the tip junction.

    Local +Z is outward along the twig. CARD_STEM_ANCHOR (texture u,v of the
    painted petiole base) is shifted onto the branch vertex with a small inboard
    tuck so leaf→stem→twig read as one line — not a centred quad with the stem
    dangling beside the wood.
    """
    from mathutils import Matrix

    golden = math.radians(137.5)
    track = direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    half = size * CARD_HALF_FACTOR
    su, sv = CARD_STEM_ANCHOR
    tuck = half * 0.06
    for q in range(CARDS_PER_CLUSTER):
        roll = golden * (gidx * CARDS_PER_CLUSTER + q) + rng.uniform(-0.25, 0.25)
        tilt = (
            Matrix.Rotation(rng.uniform(-0.18, 0.18), 4, "X")
            @ Matrix.Rotation(rng.uniform(-0.18, 0.18), 4, "Y")
        )
        matrix = (
            Matrix.Translation(pos)
            @ track
            @ Matrix.Rotation(roll, 4, "Z")
            @ tilt
        )
        hw = half * rng.uniform(0.9, 1.1)
        hh = half * rng.uniform(0.9, 1.1)
        # UV→local: u→X (0→-hw,1→+hw), v→Z (0→-hh base,1→+hh tip). Shift so
        # texture (su,sv) lands on the tip vertex, tucked slightly into the wood.
        ox = (1.0 - 2.0 * su) * hw
        oz = (1.0 - 2.0 * sv) * hh - tuck
        local = [
            (-hw + ox, 0.0, -hh + oz),
            (hw + ox, 0.0, -hh + oz),
            (hw + ox, 0.0, hh + oz),
            (-hw + ox, 0.0, hh + oz),
        ]
        face = bm.faces.new([bm.verts.new(matrix @ Vector(corner)) for corner in local])
        for loop, uv in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv_layer].uv = uv


def build_card_cloud(stage: str, rng):
    """Attach Chris's GIMP sprig cards to emitter tips — one card per anchor."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    anchors = foliage_anchors(stage)
    sprays = 0
    for gidx, (center, direction, _, _) in enumerate(anchors):
        lo, hi = CARD_SIZE_YOUNG if stage == "young" else CARD_SIZE_MATURE
        size = rng.uniform(lo, hi)
        _append_sprig_card(bm, uv_layer, center, size, direction, rng, gidx)
        sprays += CARDS_PER_CLUSTER
    mesh = bpy.data.meshes.new(f"london_plane_{stage}_cards")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"london_plane_{stage}_cards", mesh)
    obj.data.materials.append(_leaf_material())
    ensure_collection(GENERATED_COLLECTION).objects.link(obj)
    return obj, len(anchors), sprays


def compile_stage(stage: str, *, export_path=None, keep_source=True, foliage=True):
    """Compile bark skeleton; optionally attach GIMP leaf cards.

    Authorship judgment is on the bare skeleton. Cards are a compile-time
    attach of Chris's sprig texture — never densified by stacking quads.
    """
    clear_collection(GENERATED_COLLECTION)
    generated = ensure_collection(GENERATED_COLLECTION)
    # Authored beveled Bézier curves → mesh join. No leafback weld, no Skin.
    bark = build_curve_bevel_bark(stage, name=f"london_plane_{stage}")
    for collection in list(bark.users_collection):
        collection.objects.unlink(bark)
    generated.objects.link(bark)
    bark.data.materials.append(_bark_material())
    bark["junction_vertices_welded"] = 0
    bark["bark_connected_components"] = pipeline_common.connected_components(bark)
    bark["bark_non_manifold_edges"] = pipeline_common.non_manifold_edge_count(bark)

    anchor_count = 0
    spray_count = 0
    if foliage:
        rng = random.Random({"young": 31, "mature": 47, "veteran": 73}.get(stage, 47))
        card_cloud, anchor_count, spray_count = build_card_cloud(stage, rng)
        bpy.ops.object.select_all(action="DESELECT")
        bark.select_set(True)
        card_cloud.select_set(True)
        bpy.context.view_layer.objects.active = bark
        bpy.ops.object.join()

    coords = [v.co for v in bark.data.vertices]
    min_z = min(v.z for v in coords)
    max_z = max(v.z for v in coords)
    real_height = max_z - min_z
    if real_height > 0:
        scale = MODEL_HEIGHT / real_height
        for v in bark.data.vertices:
            v.co = (v.co - Vector((0, 0, min_z))) * scale
    bark.data.update()
    pipeline_common.bake_wind_vertex_colors(bark)
    if foliage:
        bark["leaf_shell_normal_loops"] = pipeline_common.apply_leaf_shell_normals(bark)
    else:
        bark["leaf_shell_normal_loops"] = 0
    bark.data.validate(clean_customdata=False)
    bark["source_stage"] = stage
    bark["real_height_m"] = real_height
    bark["card_anchors"] = anchor_count
    bark["card_sprays"] = spray_count
    bark["foliage"] = bool(foliage)
    if not keep_source:
        set_stage_visible(stage)
    if export_path:
        export_path = str(export_path)
        Path(export_path).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        bark.select_set(True)
        bpy.context.view_layer.objects.active = bark
        bpy.ops.export_scene.gltf(
            filepath=export_path, use_selection=True, export_format="GLB", export_apply=True,
            export_vertex_color="ACTIVE",
        )
    return bark


def mesh_metrics(obj):
    dims = obj.dimensions
    leaf_faces = 0
    leaf_vertices = set()
    leaf_surface_area = 0.0
    for poly in obj.data.polygons:
        if poly.material_index and poly.material_index < len(obj.data.materials):
            leaf_faces += 1
            leaf_vertices.update(poly.vertices)
            leaf_surface_area += poly.area
    min_z = min((obj.data.vertices[i].co.z for i in leaf_vertices), default=0.0)
    return {
        "vertices": len(obj.data.vertices),
        "triangles": sum(max(1, len(p.vertices) - 2) for p in obj.data.polygons),
        "materials": len(obj.data.materials),
        "height_model_m": round(dims.z, 3),
        "width_model_m": round(max(dims.x, dims.y), 3),
        "leaf_faces": leaf_faces,
        "leaf_surface_area_model_m2": round(leaf_surface_area, 3),
        "clear_bole_model_m": round(min_z, 3),
        "card_anchors": int(obj.get("card_anchors", 0)),
        "card_sprays": int(obj.get("card_sprays", 0)),
        "bark_connected_components": int(obj.get("bark_connected_components", 0)),
        "junction_vertices_welded": int(obj.get("junction_vertices_welded", 0)),
        "bark_non_manifold_edges": int(obj.get("bark_non_manifold_edges", 0)),
        "leaf_shell_normal_loops": int(obj.get("leaf_shell_normal_loops", 0)),
        "real_height_m": round(float(obj.get("real_height_m", 0)), 3),
        "foliage": bool(obj.get("foliage", True)),
    }


def save_manifest(path: str, stage: str, obj):
    data = {
        "stage": stage,
        "scene_revision": int(bpy.context.scene.get("tree_sculpt_revision", 0)),
        "metrics": mesh_metrics(obj),
        "strands": [
            {
                "id": o["strand_id"],
                "parent": o.get("parent_strand", ""),
                "order": int(o.get("branch_order", 0)),
                "role": o.get("role", ""),
                "card_pattern": o.get("card_pattern", "none"),
            }
            for o in strand_objects(stage)
        ],
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2) + "\n")
    return data


"""Deterministic review renders: bare skeleton authority + foliated runtime."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector

import sculpt_core as core

ROOT = core.PROJ / "tmp/tree_sculpt"

VIEWS = [
    ("front", lambda r: (0, -r, 2.8), 50),
    ("quarter", lambda r: (r * .72, -r * .72, 3.2), 50),
    ("side", lambda r: (r, 0, 2.8), 50),
    ("rear", lambda r: (0, r, 2.8), 50),
    ("top_oblique", lambda r: (r * .72, -r * .72, r * .78), 52),
    ("stood_under", lambda r: (1.2, -2.0, 1.6), 28),
    ("30m_read", lambda r: (0, -r * 2.0, 2.8), 85),
    ("60m_read", lambda r: (0, -r * 4.0, 3.2), 120),
]


def _look_at(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def _ensure_scene():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.035, 0.045, 0.06)
    scene.view_settings.look = "AgX - Medium High Contrast"

    camera = bpy.data.objects.get("TreeReviewCamera")
    if camera is None:
        data = bpy.data.cameras.new("TreeReviewCamera")
        camera = bpy.data.objects.new("TreeReviewCamera", data)
        core.ensure_collection(core.REVIEW_COLLECTION).objects.link(camera)
    camera.data.lens = 50
    scene.camera = camera

    sun = bpy.data.objects.get("TreeReviewSun")
    if sun is None:
        data = bpy.data.lights.new("TreeReviewSun", "SUN")
        data.energy = 2.4
        data.angle = math.radians(12)
        sun = bpy.data.objects.new("TreeReviewSun", data)
        core.ensure_collection(core.REVIEW_COLLECTION).objects.link(sun)
    sun.rotation_euler = (math.radians(38), 0, math.radians(-35))

    fill = bpy.data.objects.get("TreeReviewFill")
    if fill is None:
        data = bpy.data.lights.new("TreeReviewFill", "AREA")
        data.energy = 650
        data.shape = "DISK"
        data.size = 8
        fill = bpy.data.objects.new("TreeReviewFill", data)
        core.ensure_collection(core.REVIEW_COLLECTION).objects.link(fill)
    fill.location = (-5, -7, 9)
    return camera


def _role_material(role):
    colors = {
        "trunk": (0.30, 0.52, 0.95, 1.0),
        "reiterated_scaffold": (0.95, 0.48, 0.14, 1.0),
        "rhythmic_primary": (0.95, 0.48, 0.14, 1.0),
        "secondary": (0.22, 0.82, 0.36, 1.0),
        "tertiary": (0.72, 0.90, 0.28, 1.0),
    }
    name = f"TreeRole_{role}"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = colors.get(role, (0.8, 0.8, 0.8, 1.0))
    return mat


def _render_role_diagnostic(stage, obj, camera, path):
    obj.hide_render = True
    core.set_stage_visible(stage)
    for strand in core.strand_objects(stage):
        strand.hide_render = False
        strand.data.materials.clear()
        strand.data.materials.append(_role_material(strand.get("role", "")))
    radius = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z) * 1.35
    camera.location = (0, -radius, 2.8)
    camera.data.lens = 50
    _look_at(camera, (0, 0, 2.45))
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    for strand in core.strand_objects():
        strand.hide_render = True
    obj.hide_render = False


def _prepare_mesh_renders(stage, obj):
    for strand in core.strand_objects():
        strand.hide_render = True
    camera = _ensure_scene()
    target = Vector((0, 0, 2.45))
    radius = max(obj.dimensions.x, obj.dimensions.y, obj.dimensions.z) * 1.35
    return camera, target, radius


def _render_view_set(stage, obj, camera, target, radius, stage_dir):
    stage_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for name, loc_fn, lens in VIEWS:
        camera.location = loc_fn(radius)
        camera.data.lens = lens
        _look_at(camera, target)
        path = stage_dir / f"{name}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        rendered.append(str(path))
    diagnostic = stage_dir / "branch_roles.png"
    _render_role_diagnostic(stage, obj, camera, diagnostic)
    rendered.append(str(diagnostic))
    return rendered


def _assemble_contact_sheet(output, title, rendered, reference=None):
    labels = [name for name, _, _ in VIEWS] + [
        "branch roles: trunk / primary / secondary / tertiary"
    ]
    command = [
        "python3",
        str(Path(__file__).with_name("make_contact_sheet.py")),
        "--output",
        str(output),
        "--title",
        title,
        "--labels",
        json.dumps(labels),
        *rendered,
    ]
    if reference:
        command.extend(["--reference", str(reference)])
    subprocess.run(command, check=True)


def render_contact_sheet(stage="mature", output=None, export_path=None, reference=None):
    """Bare skeleton + foliated contact sheets; GLB export only for foliated compile."""
    ROOT.mkdir(parents=True, exist_ok=True)
    export_path = export_path or str(core.PROJ / f"models/trees/london_plane_sculpt_{stage}.glb")

    bare_output = ROOT / f"london_plane_{stage}_bare_review.png"
    bare_dir = ROOT / f"review_{stage}_bare"
    obj_bare = core.compile_stage(stage, foliage=False)
    camera, target, radius = _prepare_mesh_renders(stage, obj_bare)
    bare_views = _render_view_set(stage, obj_bare, camera, target, radius, bare_dir)
    bare_manifest = core.save_manifest(str(bare_dir / "manifest.json"), stage, obj_bare)
    _assemble_contact_sheet(
        bare_output,
        f"London plane — {stage} — bare skeleton (sculpt authority)",
        bare_views,
        reference=None,
    )

    foliated_output = Path(output or ROOT / f"london_plane_{stage}_review.png")
    foliated_dir = ROOT / f"review_{stage}"
    obj = core.compile_stage(stage, export_path=export_path, foliage=True)
    camera, target, radius = _prepare_mesh_renders(stage, obj)
    foliated_views = _render_view_set(stage, obj, camera, target, radius, foliated_dir)
    foliated_manifest = core.save_manifest(str(foliated_dir / "manifest.json"), stage, obj)
    _assemble_contact_sheet(
        foliated_output,
        f"London plane — {stage} — bare skeleton + GIMP leaf cards",
        foliated_views,
        reference=reference,
    )

    return {
        "contact_sheet_bare": str(bare_output),
        "contact_sheet": str(foliated_output),
        "views_bare": bare_views,
        "views": foliated_views,
        "manifest_bare": bare_manifest,
        "manifest": foliated_manifest,
        "glb": str(export_path),
    }

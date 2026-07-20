"""Create the first editable London-plane sculpture and review artifacts.

This is an authored starting sculpture, not a growth simulation.  The fixed
limb-system specifications below are deliberately legible and editable in the
visible Blender session.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import sculpt_core as core
from review_rig import render_contact_sheet
from tip_web import grow_envelope_tip_hosts

SHAPE_FIT_DIR = PROJ / "tmp" / "tree_sculpt" / "habit_refs"


def load_stage_shape_fit(stage: str) -> dict:
    """World strands from ``shape_fit.py`` (system Python). Blender has no scipy."""
    import json

    path = SHAPE_FIT_DIR / f"{stage}_shape_fit.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"missing {path}; run: python3 scripts/tree_sculpt/shape_fit.py {stage}"
        )
    return json.loads(path.read_text())



def reset():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    core.ensure_collection(core.SOURCE_COLLECTION)
    bpy.context.scene["tree_sculpt_revision"] = 0
    bpy.context.scene["tree_sculpt_stage"] = "mature"


def _branch_points(base, tangent, side, lift, length, droop=0.0):
    base = Vector(base)
    tangent = Vector(tangent).normalized()
    if tangent.length_squared < 1e-12:
        tangent = Vector((0, 0, 1))
    radial = Vector((-tangent.y, tangent.x, 0.0))
    if radial.length_squared < 1e-8:
        radial = Vector((1, 0, 0))
    else:
        radial.normalize()
    direction = (radial * side + tangent * 0.42 + Vector((0, 0, lift))).normalized()
    p1 = base + direction * (length * 0.35)
    p2 = base + direction * (length * 0.72) + Vector((0, 0, length * 0.10))
    p3 = base + direction * length + Vector((0, 0, -droop))
    return [base, p1, p2, p3], direction


def _radius_at(points, radii, base):
    """Parent radius at an attach point (nearest segment, linearly interpolated)."""
    pts = [Vector(p) for p in points]
    base = Vector(base)
    best_i, best_d, best_t = 0, 1e18, 0.0
    for i in range(len(pts) - 1):
        ab = pts[i + 1] - pts[i]
        denom = ab.length_squared
        t = 0.0 if denom < 1e-12 else max(0.0, min(1.0, (base - pts[i]).dot(ab) / denom))
        d = (pts[i] + ab * t - base).length_squared
        if d < best_d:
            best_d, best_i, best_t = d, i, t
    return float(radii[best_i]) * (1.0 - best_t) + float(radii[best_i + 1]) * best_t


def _taper_radii(base_r, tip_frac=0.40, n=4, shoulder_frac=0.28):
    """Parent-radius shoulder hold, then taper to tip (Inkscape L1 crotch disk)."""
    base_r = max(0.028, float(base_r))
    tip = max(0.022, base_r * tip_frac)
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        if t <= shoulder_frac:
            out.append(base_r)
        else:
            u = (t - shoulder_frac) / max(1e-6, 1.0 - shoulder_frac)
            out.append(base_r * (1.0 - u) + tip * u)
    return out


def _tertiary(stage, parent_id, sid, base, tangent, side, lift, length, droop=0.0,
              base_radius=0.048):
    """Structural ramification fork — cards attach only at its true tip."""
    points, _ = _branch_points(base, tangent, side, lift, length, droop)
    return core.create_strand(
        sid,
        points,
        _taper_radii(base_radius, tip_frac=0.38),
        stage=stage,
        parent_strand=parent_id,
        branch_order=3,
        role="tertiary",
        card_pattern="tip",
    )


def _secondary(stage, parent_id, sid, base, tangent, side, lift, length, droop=0.0,
               ramify=False, base_radius=0.090):
    points, direction = _branch_points(base, tangent, side, lift, length, droop)
    # Authored base near parent thickness (curve-bevel crotch = overlapping tubes).
    radii = _taper_radii(base_radius, tip_frac=0.42)
    obj = core.create_strand(
        sid,
        points,
        radii,
        stage=stage,
        parent_strand=parent_id,
        branch_order=2,
        role="secondary",
        # Order-2 is scaffold only — cards root on tertiary tips, not mid-thin wood.
        card_pattern="none",
    )
    tip = points[-1]
    # Longer tip host so foliage sits past the secondary end on a real fork.
    _tertiary(stage, sid, f"{sid}.t_tip", tip, direction, side * 0.75,
              lift * 0.18 + 0.05, max(1.15, length * 0.48), droop * 0.55,
              base_radius=radii[-1] * 0.85)
    if ramify and length >= 1.8:
        mid = points[1]
        outer = points[2]
        _tertiary(stage, sid, f"{sid}.t1", mid, direction, -side * 0.95,
                  lift * 0.38 + 0.14, length * 0.58, droop * 0.30,
                  base_radius=_radius_at(points, radii, mid) * 0.78)
        _tertiary(stage, sid, f"{sid}.t2", outer, direction, side * 0.85,
                  lift * 0.22 + 0.08, length * 0.46, droop * 0.45,
                  base_radius=_radius_at(points, radii, outer) * 0.78)
        _tertiary(stage, sid, f"{sid}.t3", outer, direction, -side * 0.55,
                  lift * 0.12 + 0.04, length * 0.38, droop * 0.65,
                  base_radius=_radius_at(points, radii, outer) * 0.72)
    elif length >= 1.2:
        # Short carriers still get one mid fork so the web is not tip-only stubs.
        mid = points[1]
        _tertiary(stage, sid, f"{sid}.t1", mid, direction, -side * 0.8,
                  lift * 0.28 + 0.10, length * 0.42, droop * 0.40,
                  base_radius=_radius_at(points, radii, mid) * 0.78)
    return obj


def _limb(stage, spec):
    sid, points, radii, secondaries = spec
    obj = core.create_strand(
        sid,
        points,
        radii,
        stage=stage,
        parent_strand="trunk",
        branch_order=1,
        role="reiterated_scaffold",
        card_pattern="none",  # thick wood never hosts cards
    )
    pts = [Vector(p) for p in points]
    for i, (u, side, lift, length, droop) in enumerate(secondaries):
        seg = min(len(pts) - 2, max(0, int(u * (len(pts) - 1))))
        local_t = u * (len(pts) - 1) - seg
        base = pts[seg].lerp(pts[seg + 1], local_t)
        tangent = pts[seg + 1] - pts[seg]
        parent_r = _radius_at(points, radii, base)
        # Near-parent base so the child tube fills the crotch when bevel-meshed.
        _secondary(stage, sid, f"{sid}.s{i+1}", base, tangent, side, lift, length, droop,
                   ramify=True, base_radius=parent_r * 0.95)
        # Companion carrier also ramifies — refs fill the periphery with a web,
        # not a single tip stub per secondary.
        u2 = min(0.96, u + 0.048)
        seg2 = min(len(pts) - 2, max(0, int(u2 * (len(pts) - 1))))
        local2 = u2 * (len(pts) - 1) - seg2
        base2 = pts[seg2].lerp(pts[seg2 + 1], local2)
        tangent2 = pts[seg2 + 1] - pts[seg2]
        parent_r2 = _radius_at(points, radii, base2)
        _secondary(stage, sid, f"{sid}.c{i+1}", base2, tangent2, -side * 0.8,
                   lift + 0.08, length * 0.88, droop * 0.65, ramify=True,
                   base_radius=parent_r2 * 0.92)
    return obj


def _radii_along(points, base_r, tip_frac=0.22):
    n = len(points)
    return _taper_radii(base_r, tip_frac=tip_frac, n=n)


def _sparse_secondaries(length):
    """Few carriers so cyan reads shape-fit primaries, not a procedural bush."""
    if length < 2.5:
        return [(.35, 1, .18, max(1.2, length * 0.35), .04),
                (.70, -1, .14, max(1.0, length * 0.28), .08)]
    return [(.28, 1, .18, length * 0.32, .02),
            (.52, -1, .16, length * 0.30, .06),
            (.78, 1, .12, length * 0.24, .12)]


def _limbs_from_shape_fit(stage, trunk_r0, primary_r_frac, primary_ids):
    """Build trunk + named primaries from automated silhouette raycast fit."""
    data = load_stage_shape_fit(stage)
    strands = data["strands"]
    trunk_pts = strands["trunk"]
    # Snap bole to world origin so garden/review stay centered.
    bole = Vector(trunk_pts[0])
    trunk_pts = [tuple(Vector(p) - Vector((bole.x, bole.y, 0.0))) for p in trunk_pts]
    trunk_r = _radii_along(trunk_pts, trunk_r0, tip_frac=0.18)
    core.create_strand(
        "trunk",
        trunk_pts,
        trunk_r,
        stage=stage,
        role="trunk",
    )
    env = data.get("envelope", {})
    print(
        f"TREE_SCULPT_SHAPE_FIT {stage} bole_plate={data['bole_plate']} "
        f"scale={data['scale_m_per_px']:.5f} fork_t={env.get('fork_t')} "
        f"primaries={primary_ids}",
        flush=True,
    )
    for sid in primary_ids:
        raw = strands[sid]
        pts = [tuple(Vector(p) - Vector((bole.x, bole.y, 0.0))) for p in raw]
        base_r = _radius_at(trunk_pts, trunk_r, pts[0]) * primary_r_frac
        radii = _radii_along(pts, base_r, tip_frac=0.20)
        length = sum(
            (Vector(pts[i + 1]) - Vector(pts[i])).length for i in range(len(pts) - 1)
        )
        _limb(stage, (sid, pts, radii, _sparse_secondaries(length)))


def mature():
    stage = "mature"
    # W-39: primaries raycast onto locked-plate silhouette (hand SVG retired).
    _limbs_from_shape_fit(
        stage,
        trunk_r0=0.42,
        primary_r_frac=0.72,
        primary_ids=[
            "west_low", "east_low", "north_mid", "south_mid", "crown_reiterate",
        ],
    )


def young():
    stage = "young"
    # W-39: same shape-fit path as m/L — tips on nursery plate silhouette.
    _limbs_from_shape_fit(
        stage,
        trunk_r0=0.12,
        primary_r_frac=0.48,
        primary_ids=[f"tier{i}" for i in range(1, 8)],
    )


def veteran():
    stage = "veteran"
    # W-39: V-fan tips on nyc11 silhouette (no hand Inkscape).
    _limbs_from_shape_fit(
        stage,
        trunk_r0=0.70,
        primary_r_frac=0.68,
        primary_ids=["v_west", "v_east", "v_north", "v_south", "v_crown"],
    )


def clone_stage(source_stage, target_stage):
    source = list(core.strand_objects(source_stage))
    for obj in source:
        points = obj.data.splines[0].bezier_points
        core.create_strand(
            obj["strand_id"],
            [tuple(point.co) for point in points],
            [point.radius for point in points],
            stage=target_stage,
            parent_strand=obj.get("parent_strand", ""),
            branch_order=int(obj.get("branch_order", 0)),
            role=obj.get("role", ""),
            card_pattern=obj.get("card_pattern", "none"),
        )


def mature_variants():
    clone_stage("mature", "mature_open")
    core.transform_system("west_low", stage="mature_open", rotate_z=-7.0, translate=(-0.25, 0, 0))
    core.transform_system("east_low", stage="mature_open", rotate_z=6.0, translate=(0.22, 0, 0.05))
    core.transform_system("crown_reiterate", stage="mature_open", rotate_z=9.0, translate=(0, 0, -0.18))

    clone_stage("mature", "mature_upright")
    core.transform_system("west_low", stage="mature_upright", rotate_z=8.0, translate=(0.25, 0, 0.15))
    core.transform_system("east_low", stage="mature_upright", rotate_z=-7.0, translate=(-0.2, 0, 0.2))
    core.transform_system("north_mid", stage="mature_upright", rotate_z=5.0, translate=(0, 0, 0.28))


def main():
    reset()
    young()
    print("TREE_SCULPT_TIP_WEB", grow_envelope_tip_hosts("young"), flush=True)
    mature()
    print("TREE_SCULPT_TIP_WEB", grow_envelope_tip_hosts("mature"), flush=True)
    veteran()
    print("TREE_SCULPT_TIP_WEB", grow_envelope_tip_hosts("veteran"), flush=True)
    mature_variants()
    core.set_stage_visible("mature")
    source = PROJ / "models/tree_sources/london_plane.blend"
    source.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    requested = os.environ.get(
        "TREE_SCULPT_REVIEW_STAGES",
        "young,mature,veteran,mature_open,mature_upright",
    ).split(",")
    for stage in [value.strip() for value in requested if value.strip()]:
        # Locked habit refs — same files as habit_refs.STAGE_REFS (no Pillow).
        from habit_refs import STAGE_REFS
        ref_meta = STAGE_REFS.get(stage)
        reference = None
        if ref_meta:
            candidate = PROJ / "reference_photos/london planetree" / ref_meta["file"]
            if candidate.exists():
                reference = str(candidate)
        render_contact_sheet(stage=stage, reference=reference)
    core.set_stage_visible("mature")
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    print(f"TREE_SCULPT_CREATED {source}", flush=True)
    os._exit(0)  # Blender 4.5 add-ons can hang during background teardown.


if __name__ == "__main__":
    main()


"""Envelope-guided tip hosts on a curve-bevel scaffold (Path A).

Envelope *tables* are tip targets only — not the deprecated leaf-attractor
generator. Tip hosts are thin curve-bevel strands; leaf cards attach as
along-branch *clusters* (`card_pattern=cluster`), not a single tip pin.

W-35 photo-match: one locked photograph per stage is habit authority
(see `habit_refs.STAGE_REFS`). Scaffold wood is rewritten so bare
silhouette + apparent primary forks match that photo; tip-host *count*
stays frozen after W-29. Envelope *tables* remain tip targets only.
W-34 retargeted mature/veteran profiles once; further envelope edits follow
the locked photo, not another abstract habit pass.
"""
from __future__ import annotations

import math
import random
from typing import Iterable

from mathutils import Vector

import sculpt_core as core

# Young: nursery Exclamation upright. Mature: image-3172802200 open crown.
# Veteran: nyc11 full-crown Great Tree (W-36; was Lincolns Inn trunk crop).
_T_S = [0.00, 0.15, 0.30, 0.45, 0.55, 0.68, 0.80, 0.90, 1.00]
_P_S = [0.10, 0.42, 0.68, 0.90, 1.00, 0.95, 0.80, 0.56, 0.18]
# Mature: image-3172802200 — wide open crown; long low primaries; rounded tip.
_T_M = [0.00, 0.10, 0.22, 0.38, 0.52, 0.66, 0.80, 0.90, 1.00]
_P_M = [0.05, 0.18, 0.40, 0.68, 0.90, 1.00, 0.95, 0.78, 0.42]
# Veteran: nyc11 — tall ascending V-fan; narrower than mature; crest retained.
_T_L = [0.00, 0.12, 0.25, 0.40, 0.55, 0.68, 0.80, 0.90, 1.00]
_P_L = [0.08, 0.20, 0.38, 0.58, 0.78, 0.92, 1.00, 0.88, 0.55]

# stage → (shell target count, seed, profile T/P)
# Host counts frozen after W-29 densify (two-struck); habit changes shape only.
_STAGE_SHELL = {
    "young": (288, 31, (_T_S, _P_S)),
    "mature": (1920, 47, (_T_M, _P_M)),
    "veteran": (1260, 73, (_T_L, _P_L)),
    "mature_open": (1920, 53, (_T_M, _P_M)),
    "mature_upright": (1920, 59, (_T_M, _P_M)),
}

_MAX_HOSTS_PER_TIP = 8
_MIN_HOST_LEN = 0.35
_MAX_HOST_LEN = 3.2
_SHELL_OUTSET = 1.12  # envelope slightly outside measured tip cloud


def _interp_profile(t: float, T: list[float], P: list[float]) -> float:
    t = max(0.0, min(1.0, float(t)))
    for i in range(len(T) - 1):
        if T[i] <= t <= T[i + 1]:
            u = (t - T[i]) / max(1e-9, T[i + 1] - T[i])
            return P[i] * (1.0 - u) + P[i + 1] * u
    return P[-1]


def _scaffold_terminals(stage: str) -> list[tuple[object, Vector, Vector, float]]:
    """Outermost scaffold tips (no tip_host children yet).

    Prefer order-3 terminals; fall back to childless order-2 tips. These are the
    secondary tip *region* — hosts grow from here toward the envelope shell.
    """
    objects = list(core.strand_objects(stage))
    by_parent: dict[str, list] = {}
    for obj in objects:
        if obj.get("role") == "tip_host":
            continue
        by_parent.setdefault(obj.get("parent_strand", ""), []).append(obj)

    terminals = []
    for obj in objects:
        if obj.get("role") == "tip_host":
            continue
        order = int(obj.get("branch_order", 0))
        if order < 2:
            continue
        kids = [
            c for c in by_parent.get(obj["strand_id"], [])
            if c.get("role") != "tip_host"
        ]
        if kids:
            continue
        pts = obj.data.splines[0].bezier_points
        tip = Vector(pts[-1].co)
        if len(pts) >= 2:
            direction = (tip - Vector(pts[-2].co)).normalized()
        else:
            direction = Vector((0, 0, 1))
        if direction.length_squared < 1e-12:
            direction = Vector((0, 0, 1))
        terminals.append((obj, tip, direction, float(pts[-1].radius)))
    return terminals


def _fit_envelope(tips: Iterable[Vector], T, P) -> tuple[float, float, float]:
    """Fit CB/H/RX so the habit profile hugs the authored tip cloud (Z-up)."""
    tips = list(tips)
    if not tips:
        return 3.0, 12.0, 4.0
    zs = [p.z for p in tips]
    rs = [math.hypot(p.x, p.y) for p in tips]
    z0, z1 = min(zs), max(zs)
    r_max = max(rs) if rs else 1.0
    cb = max(0.5, z0 - 0.35 * max(0.5, z1 - z0))
    h = z1 + 0.15 * max(0.5, z1 - z0)
    # Peak profile ≈ 1.0 → RX ≈ r_max * outset.
    rx = max(0.8, r_max * _SHELL_OUTSET)
    _ = (T, P)  # shape used at sample time
    return cb, h, rx


def _sample_shell(n: int, cb: float, h: float, rx: float, T, P, seed: int) -> list[Vector]:
    """Near-skin shell samples (not volume fill — outer canopy rim)."""
    rng = random.Random(seed)
    ch = max(1e-3, h - cb)
    points = []
    attempts = 0
    while len(points) < n and attempts < n * 40:
        attempts += 1
        t = rng.random()
        r_env = rx * _interp_profile(t, T, P)
        if r_env < 0.12:
            continue
        # Outer skin only — interior samples waste hosts inside the canopy void.
        rr = r_env * (0.92 + 0.08 * rng.random())
        th = rng.uniform(0.0, 2.0 * math.pi)
        z = cb + t * ch
        points.append(Vector((rr * math.cos(th), rr * math.sin(th), z)))
    return points


def _host_polyline(base: Vector, target: Vector, tangent: Vector) -> list[Vector]:
    delta = target - base
    length = delta.length
    if length < 1e-6:
        target = base + tangent * _MIN_HOST_LEN
        delta = target - base
        length = delta.length
    if length > _MAX_HOST_LEN:
        delta = delta.normalized() * _MAX_HOST_LEN
        target = base + delta
        length = _MAX_HOST_LEN
    if length < _MIN_HOST_LEN:
        target = base + delta.normalized() * _MIN_HOST_LEN
        delta = target - base
    direction = delta.normalized()
    blend = (direction * 0.72 + tangent * 0.28).normalized()
    p1 = base + blend * (length * 0.38)
    p2 = base + direction * (length * 0.72) + Vector((0, 0, length * 0.04))
    return [base, p1, p2, target]


def _clear_existing_tip_hosts(stage: str) -> None:
    for obj in list(core.strand_objects(stage)):
        if obj.get("role") == "tip_host":
            core.delete_strand(obj["strand_id"], stage)


def _demote_scaffold_cards(stage: str) -> None:
    for obj in core.strand_objects(stage):
        if obj.get("role") == "tip_host":
            continue
        if obj.get("card_pattern", "none") != "none":
            obj["card_pattern"] = "none"


def grow_envelope_tip_hosts(stage: str) -> dict:
    """Grow thin tip hosts from scaffold terminals toward an envelope shell.

    Idempotent: replaces prior tip_host strands for the stage. Leaves orders 0–3
    geometry untouched (card_pattern demoted to none on scaffold).
    """
    cfg = _STAGE_SHELL.get(stage)
    if cfg is None:
        raise ValueError(f"no tip-web config for stage: {stage}")
    n_shell, seed, (T, P) = cfg

    _clear_existing_tip_hosts(stage)
    _demote_scaffold_cards(stage)

    terminals = _scaffold_terminals(stage)
    if not terminals:
        return {"stage": stage, "tip_hosts": 0, "terminals": 0, "shell": 0}

    tips = [tip for _, tip, _, _ in terminals]
    cb, h, rx = _fit_envelope(tips, T, P)
    shell = _sample_shell(n_shell, cb, h, rx, T, P, seed)

    counts = {obj["strand_id"]: 0 for obj, _, _, _ in terminals}
    hosts = 0
    for i, target in enumerate(shell):
        best = None
        best_d = 1e18
        for obj, tip, tangent, radius in terminals:
            sid = obj["strand_id"]
            if counts[sid] >= _MAX_HOSTS_PER_TIP:
                continue
            d = (target - tip).length_squared
            if d < best_d:
                best_d = d
                best = (obj, tip, tangent, radius)
        if best is None:
            continue
        obj, tip, tangent, radius = best
        outward = target - tip
        if outward.length < _MIN_HOST_LEN * 0.5:
            continue
        if outward.dot(tangent) < -0.15 * outward.length:
            continue
        points = _host_polyline(tip, target, tangent)
        base_r = max(0.014, min(0.032, float(radius) * 0.55))
        tip_r = max(0.010, base_r * 0.42)
        mid_r = base_r * 0.72
        hid = f"{obj['strand_id']}.th{counts[obj['strand_id']] + 1}"
        core.create_strand(
            hid,
            [tuple(p) for p in points],
            [base_r, mid_r, mid_r * 0.85, tip_r],
            stage=stage,
            parent_strand=obj["strand_id"],
            branch_order=4,
            role="tip_host",
            card_pattern="cluster",
        )
        host = core.find_strand(hid, stage)
        host.data.bevel_resolution = 1
        host.data.resolution_u = 2
        counts[obj["strand_id"]] += 1
        hosts += 1

    return {
        "stage": stage,
        "tip_hosts": hosts,
        "terminals": len(terminals),
        "shell": len(shell),
        "cb": round(cb, 3),
        "h": round(h, 3),
        "rx": round(rx, 3),
    }

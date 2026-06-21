"""Shared London-plane leaf outline — SYMMETRIC parametric, ONE canonical frame.

Pure Python (math only) so it imports in both Blender's bundled Python (geometry)
and system python3 (texture); both read this single source, so the texture's
veins always hit the geometry's lobe tips.

CANONICAL FRAME (fixed — do not flip anywhere): petiole/stem at the ORIGIN (0,0),
apex straight up at (0, ~1), leaf MIRRORED about x=0 (symmetric, centred). Tips
point up-and-out. Veins are built from the stem (0,0) OUTWARD to each lobe tip.
Keeping one frame end-to-end is the fix for the repeated orientation flips
(user 2026-06-20): the shape is defined once here, never re-oriented per view.

Proportions measured from the real flat-leaf reference + morphometrics (5 lobes,
W/L ~1.2, sinuses ~1/3 the blade, coarse sparse teeth, base truncate). The teeth
are real perpendicular sawtooth along every margin segment.

palmate_outline() -> (boundary_xy, boundary_uv, vein_tip_uv, base_uv).
vein_tip_uv order: central, +lateral, -lateral, +basal, -basal.
"""
import math

DEFAULTS = {
    # Botanical morphology (towerlandscapedesign plane-vs-maple, user 2026-06-20):
    # plane = "3-5 SHALLOW lobes with angular sinuses", "more triangular", and
    # "7in long x up to 10in wide" => WIDER than tall (W/L ~1.47). The maple
    # distinction is DEEP rounded sinuses — so shallow cuts here are what stops it
    # reading as a maple. Central lobe longest, lobes taper to a broad basal pair
    # (widest low => triangular). Coarse pointed marginal teeth.
    "lobe_angles_deg": (0.0, 38.0, 72.0),   # central / upper-lateral / basal, from +Y
    "lobe_radius": (1.0, 0.86, 0.66),       # all prominent; central longest (triangular)
    "sinus_frac": 0.80,                     # SHALLOW angular cuts (broad lobes, not maple)
    "base_width": 0.16,                     # truncate base half-width
    "width_scale": 1.18,                    # broad: W/L ~1.45-1.5, widest at basal lobes
    "tooth_spacing": 0.20,                  # gap between marginal teeth (coarse plane teeth)
    "tooth_amp": 0.055,                     # tooth height ⊥ margin — prominent triangular spikes
}


def _p(cfg):
    d = dict(DEFAULTS)
    if cfg:
        d.update({k: v for k, v in cfg.items() if k in DEFAULTS})
    return d


def palmate_outline(cfg=None):
    p = _p(cfg)
    width_scale = p["width_scale"]
    sinus_frac = p["sinus_frac"]
    base_width = p["base_width"]
    tooth_spacing = p["tooth_spacing"]
    tooth_amp = p["tooth_amp"]
    CENTER = (0.0, 0.42)

    def polar(a_deg, r):
        a = math.radians(a_deg)
        return (math.sin(a) * r * width_scale, math.cos(a) * r)

    # Lobes mirrored about x=0 (symmetric): central(0) + ±lateral + ±basal.
    lobes = []
    for a, r in zip(p["lobe_angles_deg"], p["lobe_radius"]):
        lobes.append((a, r))
        if a != 0.0:
            lobes.append((-a, r))
    lobes.sort(key=lambda t: -t[0])  # right base -> apex -> left base

    # Skeleton: base corner, alternating lobe tip / sinus, other base corner.
    key = [(base_width, 0.0)]
    for i, (a, r) in enumerate(lobes):
        key.append(polar(a, r))
        if i < len(lobes) - 1:
            na, nr = lobes[i + 1]
            key.append(polar((a + na) / 2.0, sinus_frac * min(r, nr)))
    key.append((-base_width, 0.0))

    def sawtooth(p0, p1):
        ex, ey = p1[0] - p0[0], p1[1] - p0[1]
        elen = math.hypot(ex, ey)
        if elen < 1e-6:
            return []
        nteeth = max(1, int(round(elen / tooth_spacing)))
        nx, ny = -ey / elen, ex / elen
        mx, my = (p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0
        if ((mx + nx - CENTER[0]) ** 2 + (my + ny - CENTER[1]) ** 2
                < (mx - CENTER[0]) ** 2 + (my - CENTER[1]) ** 2):
            nx, ny = -nx, -ny
        out = []
        for k in range(1, nteeth * 2):
            t = k / (nteeth * 2)
            px, py = p0[0] + ex * t, p0[1] + ey * t
            if k % 2 == 1:
                px += nx * tooth_amp
                py += ny * tooth_amp
            out.append((px, py))
        return out

    pts = [key[0]]
    for j in range(1, len(key)):
        pts.extend(sawtooth(key[j - 1], key[j]))
        pts.append(key[j])

    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    half_w = max(abs(min(xs)), abs(max(xs))) or 1.0
    ymin, ymax = min(ys), max(ys)
    span = (ymax - ymin) or 1.0

    def to_uv(x, y):
        return (0.5 + x / (2.0 * half_w), 1.0 - (y - ymin) / span)

    uvs = [to_uv(x, y) for (x, y) in pts]
    # Vein tips: central, then ± pairs — built from the stem outward, symmetric.
    tip_uv = [to_uv(*polar(0.0, p["lobe_radius"][0]))]
    for a, r in zip(p["lobe_angles_deg"][1:], p["lobe_radius"][1:]):
        tip_uv.append(to_uv(*polar(a, r)))
        tip_uv.append(to_uv(*polar(-a, r)))
    base_uv = to_uv(0.0, 0.0)
    return pts, uvs, tip_uv, base_uv

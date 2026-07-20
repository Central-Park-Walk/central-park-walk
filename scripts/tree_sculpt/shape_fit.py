#!/usr/bin/env python3
"""Automated habit shape → primary skeleton (no hand tracing).

Chris W-38 verdict: pipeline must be automated; learn tier shape from a
photo corpus, then draw the (already-good) skeleton *to that shape* —
same failure mode as Mtree parameter grinding.

Authority chain:
  1. ``habit_refs.CORPUS`` + locked ``STAGE_REFS`` plates — measure silhouette
  2. Stage primary *recipes* (angles / attach heights) — botanical layout only
  3. Tip positions — **raycast onto the locked-plate silhouette** (OUTPUT)

    python3 scripts/tree_sculpt/shape_fit.py mature veteran
    → tmp/tree_sculpt/habit_refs/{stage}_shape_fit.{png,json}
      tmp/tree_sculpt/habit_refs/shape_corpus.json
"""
from __future__ import annotations

import json
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from habit_refs import CORPUS, STAGE_REFS
from inkscape_habit import STAGE_HEIGHT_M, plate_to_world
from ref_habit_overlay import _crop_frac, _fit

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[1]
REF_DIR = PROJ / "reference_photos" / "london planetree"
OUT_DIR = PROJ / "tmp" / "tree_sculpt" / "habit_refs"
PLATE = 640

# Botanical layout only — tip *length* comes from the silhouette raycast.
# Angles: 0° = +X (east/right on plate), 90° = +Y depth (into scene),
# plate front uses X and Z; depth Y = sin(azimuth) * depth_scale.
STAGE_RECIPES = {
    "young": {
        "fork_frac_default": 0.35,
        "primaries": [
            # id, attach_frac (bole→tip), azimuth_deg, aim_up (plate), arch
            ("tier1", 0.28, 0, 0.35, "up_out"),
            ("tier2", 0.38, 150, 0.40, "up_out"),
            ("tier3", 0.48, 285, 0.45, "up_out"),
            ("tier4", 0.58, 70, 0.50, "up_out"),
            ("tier5", 0.68, 205, 0.55, "up_out"),
            ("tier6", 0.78, 335, 0.60, "up_out"),
            ("tier7", 0.86, 115, 0.70, "up_out"),
        ],
    },
    "mature": {
        # Corpus (geograph 7338525 + A149): clear bole, heavy low scaffold, dome crown.
        "fork_frac_default": 0.28,
        "primaries": [
            ("west_low", 0.26, 185, 0.15, "out_then_up"),
            ("east_low", 0.26, 5, 0.15, "out_then_up"),
            ("north_mid", 0.38, 95, 0.45, "up_out"),
            ("south_mid", 0.38, 265, 0.45, "up_out"),
            ("crown_reiterate", 0.48, 15, 0.75, "up"),
        ],
    },
    "veteran": {
        # Winter bank + open veterans: low heavy scaffold, ascending wood, crest kept.
        "fork_frac_default": 0.22,
        "primaries": [
            ("v_west", 0.20, 205, 0.55, "ascend"),
            ("v_east", 0.20, 335, 0.55, "ascend"),
            ("v_north", 0.24, 90, 0.65, "ascend"),
            ("v_south", 0.22, 270, 0.55, "ascend"),
            ("v_crown", 0.30, 8, 0.85, "ascend"),
        ],
    },
}


def ensure_plate(stage: str) -> Path:
    """Write ``{stage}_ref_plate.png`` if missing (same fit as overlays)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{stage}_ref_plate.png"
    if out.is_file():
        return out
    meta = STAGE_REFS[stage]
    ref = _fit(_crop_frac(Image.open(REF_DIR / meta["file"]), meta["crop_frac"]), PLATE)
    ref.save(out)
    return out


def segment_tree(rgb: np.ndarray) -> np.ndarray:
    """Full-tree silhouette without eating the crown through sky windows.

    Border flood with a loose color tol tunnels through bright canopy holes and
    leaves a tiny island (W-39 first pass: mature bbox height 52px on a 640
    plate). Instead: classify sky + lower lawn, flood *only through those*,
    fill holes, keep the tallest large component.
    """
    h, w, _ = rgb.shape
    r = rgb[:, :, 0].astype(np.float32)
    g = rgb[:, :, 1].astype(np.float32)
    b = rgb[:, :, 2].astype(np.float32)
    lum = (r + g + b) / 3.0
    yy = np.arange(h, dtype=np.float32)[:, None]

    sky = ((lum > 185) & (b + 8 >= g)) | ((lum > 210) & (np.abs(r - g) < 28) & (np.abs(g - b) < 28))
    # Lower-third green lawn / gravel — not mid-canopy foliage.
    lawn = (g > r + 10) & (g > b + 6) & (lum > 55) & (lum < 195) & (yy > h * 0.70)
    # Near-black void (review plates / letterbox).
    void = lum < 22
    seed_bg = sky | lawn | void

    bg = seed_bg.copy()
    q: deque[tuple[int, int]] = deque()
    for y, x in zip(*np.where(seed_bg)):
        # Only seed from the frame border so interior sky windows are filled
        # *after* we have the outer shell — see binary_fill_holes below.
        if y == 0 or x == 0 or y == h - 1 or x == w - 1:
            q.append((int(y), int(x)))
    # Ensure every border pixel can start a flood through seed_bg-like colors.
    for x in range(w):
        q.append((0, x))
        q.append((h - 1, x))
    for y in range(h):
        q.append((y, 0))
        q.append((y, w - 1))
    seen = np.zeros((h, w), dtype=bool)
    while q:
        y, x = q.popleft()
        if seen[y, x]:
            continue
        seen[y, x] = True
        if not seed_bg[y, x] and not (lum[y, x] > 175 or void[y, x]):
            # Do not tunnel into foliage/bark.
            continue
        bg[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx]:
                q.append((ny, nx))

    fg = ~bg
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_closing(fg, iterations=3)
    labeled, nlab = ndimage.label(fg)
    if nlab == 0:
        return fg
    # Prefer the component that is both large and tall (full tree, not a bush clump).
    best_i, best_score = 1, -1.0
    for i in range(1, nlab + 1):
        comp = labeled == i
        ys, xs = np.where(comp)
        if len(xs) < 200:
            continue
        height = float(ys.max() - ys.min() + 1)
        area = float(len(xs))
        score = area * (height / h) ** 2
        if score > best_score:
            best_score = score
            best_i = i
    fg = labeled == best_i
    # Require a plausible whole-tree height; otherwise fall back to green+bark.
    ys, xs = np.where(fg)
    if len(xs) == 0 or (ys.max() - ys.min()) < 0.35 * h:
        foliage = (g > r + 6) & (g > b + 4) & (g > 35) & (yy < h * 0.92)
        bark = (lum > 35) & (lum < 190) & (np.abs(r - g) < 45) & (np.abs(g - b) < 50)
        fg = (foliage | bark) & ~sky & ~(lawn & (yy > h * 0.78))
        fg = ndimage.binary_fill_holes(fg)
        fg = ndimage.binary_closing(fg, iterations=2)
        labeled, nlab = ndimage.label(fg)
        if nlab:
            best_i, best_score = 1, -1.0
            for i in range(1, nlab + 1):
                comp = labeled == i
                ys, xs = np.where(comp)
                if len(xs) < 200:
                    continue
                height = float(ys.max() - ys.min() + 1)
                score = float(len(xs)) * (height / h) ** 2
                if score > best_score:
                    best_score = score
                    best_i = i
            fg = labeled == best_i
    return fg

def measure_envelope(mask: np.ndarray) -> dict:
    ys, xs = np.where(mask)
    if len(xs) < 50:
        raise ValueError("silhouette too small")
    y_min, y_max = int(ys.min()), int(ys.max())
    x_min, x_max = int(xs.min()), int(xs.max())
    crown_h = max(1, y_max - y_min)
    crown_w = max(1, x_max - x_min)

    # Bole: centroid of the bottom 4% of the crown mask.
    bole_y0 = int(y_max - 0.04 * crown_h)
    band = mask[bole_y0 : y_max + 1]
    bys, bxs = np.where(band)
    if len(bxs) == 0:
        bole_x = int(0.5 * (x_min + x_max))
        bole_y = y_max
        trunk_w = 8
    else:
        bole_x = int(np.median(bxs))
        bole_y = int(bole_y0 + np.median(bys))
        trunk_w = int(max(4, bxs.max() - bxs.min()))

    # Width half-profile vs height fraction t (0=bole, 1=tip).
    profile = []
    for t in np.linspace(0.0, 1.0, 41):
        yi = int(round(bole_y - t * crown_h))
        yi = int(np.clip(yi, 0, mask.shape[0] - 1))
        cols = np.where(mask[yi])[0]
        if len(cols) < 2:
            profile.append({"t": float(t), "half_w_px": 0.0, "cx": float(bole_x)})
            continue
        profile.append(
            {
                "t": float(t),
                "half_w_px": float(0.5 * (cols.max() - cols.min())),
                "cx": float(0.5 * (cols.min() + cols.max())),
            }
        )

    # Fork: first t from bole where half-width exceeds ~1.75× bole half-width.
    bole_hw = max(2.0, trunk_w * 0.5)
    fork_t = None
    for row in profile:
        if row["t"] < 0.08:
            continue
        if row["half_w_px"] > 1.75 * bole_hw:
            fork_t = row["t"]
            break

    tip_y = y_min
    tip_cols = np.where(mask[tip_y])[0]
    tip_x = int(np.median(tip_cols)) if len(tip_cols) else bole_x

    return {
        "bole_xy": [bole_x, bole_y],
        "tip_xy": [tip_x, tip_y],
        "bbox": [x_min, y_min, x_max, y_max],
        "crown_h_px": crown_h,
        "crown_w_px": crown_w,
        "aspect_w_over_h": crown_w / crown_h,
        "trunk_w_px": trunk_w,
        "fork_t": fork_t,
        "profile": profile,
    }


def _raycast(mask: np.ndarray, origin: tuple[float, float], dx: float, dy: float) -> tuple[float, float]:
    """Last foreground pixel along a plate-space ray (dy positive = down).

    Uses a hole-filled / dilated mask so internal sky windows do not truncate
    the limb before the outer crown shell.
    """
    h, w = mask.shape
    solid = ndimage.binary_fill_holes(mask)
    solid = ndimage.binary_dilation(solid, iterations=2)
    x, y = float(origin[0]), float(origin[1])
    length = math.hypot(dx, dy) or 1.0
    dx, dy = dx / length, dy / length
    last = (x, y)
    for _ in range(int(max(h, w) * 3)):
        x += dx * 0.5
        y += dy * 0.5
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= ix < w and 0 <= iy < h):
            break
        if solid[iy, ix]:
            last = (float(ix), float(iy))
        else:
            break
    return last


def _tip_on_envelope(
    mask: np.ndarray,
    env: dict,
    attach: tuple[float, float],
    azimuth_deg: float,
    tip_frac: float,
) -> tuple[float, float]:
    """Prefer silhouette half-width at tip height; fall back to raycast."""
    bole_x, bole_y = env["bole_xy"]
    crown_h = env["crown_h_px"]
    t = float(np.clip(tip_frac, 0.05, 0.98))
    yi = int(round(bole_y - t * crown_h))
    yi = int(np.clip(yi, 0, mask.shape[0] - 1))
    cols = np.where(mask[yi])[0]
    az = math.radians(azimuth_deg)
    spread = math.cos(az)
    if len(cols) >= 2:
        left, right = int(cols.min()), int(cols.max())
        cx = 0.5 * (left + right)
        if spread >= 0:
            tip = (float(right), float(yi))
        else:
            tip = (float(left), float(yi))
        # Soften pure N/S: pull slightly off centerline.
        if abs(spread) < 0.3:
            tip = (float(cx + (right - left) * 0.15 * (1 if azimuth_deg < 180 else -1)), float(yi))
        return tip
    # Fallback ray.
    dx = spread if abs(spread) > 0.2 else (0.3 if azimuth_deg < 180 else -0.3)
    dy = -0.55
    return _raycast(mask, attach, dx, dy)

def _arch_polyline(
    start: tuple[float, float],
    tip: tuple[float, float],
    arch: str,
    n: int = 7,
) -> list[tuple[float, float]]:
    """Plate polyline from attach → tip with a stage-appropriate bow."""
    x0, y0 = start
    x1, y1 = tip
    pts = []
    for i in range(n):
        u = i / (n - 1)
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u
        # Bow in plate: toward horizon (increase |x|) and/or lift (decrease y).
        side = 1.0 if (x1 - x0) >= 0 else -1.0
        span = math.hypot(x1 - x0, y1 - y0)
        if arch == "out_then_up":
            # Early outward, late tip-lift (mature low limbs).
            x += side * span * 0.12 * math.sin(math.pi * u)
            y += span * 0.08 * math.sin(math.pi * max(0.0, u - 0.35) / 0.65) if u > 0.35 else 0.0
            # tip-lift is toward smaller y (up)
            y -= span * 0.10 * (u ** 2)
        elif arch == "ascend":
            x += side * span * 0.04 * math.sin(math.pi * u)
            y -= span * 0.02 * math.sin(math.pi * u)
        elif arch == "up_out":
            x += side * span * 0.06 * math.sin(math.pi * u)
            y -= span * 0.04 * u * (1 - u) * 4
        else:  # "up"
            x += side * span * 0.02 * math.sin(math.pi * u)
        pts.append((x, y))
    pts[0] = start
    pts[-1] = tip
    return pts


def fit_primaries(stage: str, mask: np.ndarray, env: dict) -> dict[str, dict]:
    """Named plate paths: trunk + primaries with tips on the silhouette."""
    recipe = STAGE_RECIPES[stage]
    bole_x, bole_y = env["bole_xy"]
    tip_x, tip_y = env["tip_xy"]
    crown_h = env["crown_h_px"]
    fork_t = env["fork_t"] if env["fork_t"] is not None else recipe["fork_frac_default"]

    # Trunk centerline: follow mask centroid up to tip.
    trunk_pts: list[tuple[float, float]] = []
    for t in np.linspace(0.0, 1.0, 9):
        yi = int(round(bole_y - t * crown_h))
        yi = int(np.clip(yi, 0, mask.shape[0] - 1))
        cols = np.where(mask[yi])[0]
        if len(cols) == 0:
            cx = bole_x + (tip_x - bole_x) * t
        else:
            # Prefer columns near previous trunk x so we stay on the bole.
            if trunk_pts:
                cx = float(cols[np.argmin(np.abs(cols - trunk_pts[-1][0]))])
            else:
                cx = float(np.median(cols))
        trunk_pts.append((cx, float(yi)))
    trunk_pts[0] = (float(bole_x), float(bole_y))
    trunk_pts[-1] = (float(tip_x), float(tip_y))

    paths: dict[str, dict] = {
        "trunk": {"plate_pts": trunk_pts, "data_y": None},
    }

    for sid, attach_frac, azimuth_deg, aim_up, arch in recipe["primaries"]:
        # Attach at max(fork, recipe attach) so primaries leave the real crotch.
        t_att = max(fork_t, attach_frac)
        yi = bole_y - t_att * crown_h
        idx = min(len(trunk_pts) - 1, int(round(t_att * (len(trunk_pts) - 1))))
        ox, _oy = trunk_pts[idx]
        oy = float(yi)
        # Tip height: climb from attach by aim_up fraction of remaining crown.
        tip_frac = min(0.97, t_att + (1.0 - t_att) * max(0.35, aim_up))
        tip = _tip_on_envelope(mask, env, (ox, oy), azimuth_deg, tip_frac)
        # If tip collapsed onto attach, raycast hard outward.
        if math.hypot(tip[0] - ox, tip[1] - oy) < 18:
            az = math.radians(azimuth_deg)
            tip = _raycast(mask, (ox, oy), math.cos(az) or 0.4, -max(0.25, aim_up))

        poly = _arch_polyline((ox, oy), tip, arch)
        depth = 0.55 * math.sin(math.radians(azimuth_deg)) * STAGE_HEIGHT_M[stage] * 0.35
        paths[sid] = {"plate_pts": poly, "data_y": float(depth)}

    return paths


def _draw_fit_png(stage: str, plate: Image.Image, paths: dict, env: dict) -> Path:
    im = plate.convert("RGBA")
    # Dim background slightly.
    dim = Image.new("RGBA", im.size, (0, 0, 0, 80))
    im = Image.alpha_composite(im, dim)
    draw = ImageDraw.Draw(im)
    # Silhouette edge hint.
    bole = tuple(env["bole_xy"])
    draw.ellipse((bole[0] - 4, bole[1] - 4, bole[0] + 4, bole[1] + 4), fill=(255, 200, 40, 255))
    for sid, meta in paths.items():
        pts = [(p[0], p[1]) for p in meta["plate_pts"]]
        color = (0, 230, 255, 255) if sid != "trunk" else (255, 180, 40, 255)
        width = 3 if sid != "trunk" else 4
        if len(pts) >= 2:
            draw.line(pts, fill=color, width=width)
        for p in pts:
            draw.ellipse((p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2), fill=color)
    out = OUT_DIR / f"{stage}_shape_fit.png"
    im.convert("RGB").save(out)
    return out


def measure_corpus_entry(stage: str, entry: dict) -> dict:
    path = REF_DIR / entry["file"]
    rgb = np.asarray(
        _fit(_crop_frac(Image.open(path), entry["crop_frac"]), PLATE).convert("RGB")
    )
    mask = segment_tree(rgb)
    env = measure_envelope(mask)
    return {
        "file": entry["file"],
        "why": entry.get("why", ""),
        "aspect_w_over_h": round(env["aspect_w_over_h"], 3),
        "fork_t": env["fork_t"],
        "trunk_w_px": env["trunk_w_px"],
        "crown_h_px": env["crown_h_px"],
        "crown_w_px": env["crown_w_px"],
    }


def build_stage(stage: str) -> dict:
    plate_path = ensure_plate(stage)
    plate = Image.open(plate_path).convert("RGB")
    rgb = np.asarray(plate)
    mask = segment_tree(rgb)
    env = measure_envelope(mask)
    # Prefer corpus-median fork when the locked plate fork is noisy.
    corpus_forks = []
    for entry in CORPUS.get(stage, []):
        try:
            m = measure_corpus_entry(stage, entry)
            if m["fork_t"] is not None:
                corpus_forks.append(m["fork_t"])
        except Exception as exc:  # noqa: BLE001 — one bad photo must not kill fit
            print(f"TREE_SCULPT_SHAPE_CORPUS_SKIP {stage} {entry['file']}: {exc}", flush=True)
    if corpus_forks:
        env["fork_t_corpus_median"] = float(np.median(corpus_forks))
        if env["fork_t"] is None:
            env["fork_t"] = env["fork_t_corpus_median"]
        else:
            # Blend locked plate with corpus (photo identity + species prior).
            env["fork_t"] = 0.6 * env["fork_t"] + 0.4 * env["fork_t_corpus_median"]
    elif env["fork_t"] is None:
        env["fork_t"] = STAGE_RECIPES[stage]["fork_frac_default"]

    paths = fit_primaries(stage, mask, env)
    world = plate_to_world(stage, paths, bole_xy=tuple(env["bole_xy"]))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = _draw_fit_png(stage, plate, paths, env)
    js = OUT_DIR / f"{stage}_shape_fit.json"
    payload = {
        "method": "shape_fit_raycast",
        "stage": stage,
        "envelope": {
            k: env[k]
            for k in (
                "bole_xy",
                "tip_xy",
                "bbox",
                "aspect_w_over_h",
                "trunk_w_px",
                "fork_t",
                "fork_t_corpus_median",
                "crown_h_px",
                "crown_w_px",
            )
            if k in env
        },
        "recipe_primaries": [p[0] for p in STAGE_RECIPES[stage]["primaries"]],
        **world,
    }
    # plate_to_world already nested strands; avoid double keys — rebuild cleanly.
    payload = {
        "method": "shape_fit_raycast",
        "stage": stage,
        "envelope": payload["envelope"],
        "recipe_primaries": payload["recipe_primaries"],
        "bole_plate": world["bole_plate"],
        "tip_plate": world["tip_plate"],
        "scale_m_per_px": world["scale_m_per_px"],
        "height_m": world["height_m"],
        "strands": world["strands"],
    }
    js.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"TREE_SCULPT_SHAPE_FIT {stage} aspect={env['aspect_w_over_h']:.2f} "
        f"fork_t={env['fork_t']:.2f} primaries={list(world['strands'])} → {png.name}",
        flush=True,
    )
    return payload


def load_stage_shape_fit(stage: str, rebuild: bool = False) -> dict:
    """World strands for create_london_plane (same schema as Inkscape world JSON)."""
    js = OUT_DIR / f"{stage}_shape_fit.json"
    if rebuild or not js.is_file():
        return build_stage(stage)
    data = json.loads(js.read_text())
    return data


def write_corpus_report() -> Path:
    report = {"stages": {}}
    for stage, entries in CORPUS.items():
        rows = []
        for entry in entries:
            try:
                rows.append(measure_corpus_entry(stage, entry))
            except Exception as exc:  # noqa: BLE001
                rows.append({"file": entry["file"], "error": str(exc)})
        forks = [r["fork_t"] for r in rows if r.get("fork_t") is not None]
        aspects = [r["aspect_w_over_h"] for r in rows if "aspect_w_over_h" in r]
        report["stages"][stage] = {
            "n": len(rows),
            "fork_t_median": float(np.median(forks)) if forks else None,
            "aspect_median": float(np.median(aspects)) if aspects else None,
            "samples": rows,
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "shape_corpus.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print("TREE_SCULPT_SHAPE_CORPUS", out, flush=True)
    return out


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stages", nargs="*", default=["young", "mature", "veteran"])
    ap.add_argument("--corpus-only", action="store_true")
    args = ap.parse_args()
    write_corpus_report()
    if args.corpus_only:
        return
    for stage in args.stages:
        build_stage(stage)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Tier-approach continuity check (trees.md §5 / walk-around 2026-06-11 #1).

Analyzes a walk-bot frame sequence shot while closing on a tree group
(user's line: Conservatory Water → Belvedere, --pos=-53,884,11) and
reports per-frame canopy statistics so discrete tier/fog steps stand out
from smooth approach trends.

The user-visible defect: distant tree line reads PALE/washed, then turns
greener/saturated and gains shape in discrete steps on approach
(impostor→lod2 at ~230-250 m, lod2→near at ~50-60 m, fog veil on top).

Protocol (same family as the crossfade-walk DoD in trees.md §7): compare
per-frame canopy STATISTICS, never raw pixel deltas — a walking camera
measures parallax otherwise. A "step" = consecutive-frame stat delta well
above the sequence median delta, at a distance that matches a tier band.

Usage:
  tier_approach_check.py <frames_dir> [--box x0,y0,x1,y1] [--speed M_S]
                         [--interval S] [--csv out.csv]
  tier_approach_check.py <dirA> --compare <dirB>   # e.g. default vs fog-off

Canopy mask inside the box: green-dominant pixels (G >= R-8 and G > B+4,
8-bit) — deliberately loose so PALE washed canopy still counts; sky is
B-dominant and excluded, sunlit turf is below the box.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LUMA = np.array([0.2126, 0.7152, 0.0722])


def frame_stats(path: Path, box):
    img = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w, _ = img.shape
    x0, y0, x1, y1 = box
    crop = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
    mask = (g >= r - 8.0) & (g > b + 4.0)
    if mask.sum() < 200:
        return None
    px = crop[mask]
    mx = px.max(axis=1)
    mn = px.min(axis=1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
    return {
        "n": int(mask.sum()),
        "cover": float(mask.mean()),
        "luma": float(np.median(px @ LUMA)),
        "r": float(np.median(px[:, 0])),
        "g": float(np.median(px[:, 1])),
        "b": float(np.median(px[:, 2])),
        "sat": float(np.median(sat)),
    }


def load_seq(d: Path, box):
    rows = []
    for p in sorted(d.glob("*.png")):
        s = frame_stats(p, box)
        if s is not None:
            s["frame"] = p.name
            rows.append(s)
    if not rows:
        sys.exit(f"no usable frames in {d}")
    return rows


def report(rows, speed, interval, label=""):
    print(f"\n== {label or 'sequence'}: {len(rows)} frames, "
          f"{speed * interval:.1f} m/frame ==")
    print(f"{'frame':>5} {'walked_m':>8} {'luma':>6} {'sat':>6} "
          f"{'R':>5} {'G':>5} {'B':>5} {'cover':>6}  step?")
    deltas = []
    for i in range(1, len(rows)):
        d = abs(rows[i]["sat"] - rows[i - 1]["sat"]) + \
            abs(rows[i]["luma"] - rows[i - 1]["luma"]) / 255.0
        deltas.append(d)
    med = float(np.median(deltas)) if deltas else 0.0
    for i, s in enumerate(rows):
        walked = i * speed * interval
        flag = ""
        if i > 0 and med > 0 and deltas[i - 1] > max(3.0 * med, 0.02):
            flag = f"<< STEP (Δ {deltas[i - 1]:.3f}, {deltas[i - 1] / med:.1f}x med)"
        print(f"{i:>5} {walked:>8.1f} {s['luma']:>6.1f} {s['sat']:>6.3f} "
              f"{s['r']:>5.0f} {s['g']:>5.0f} {s['b']:>5.0f} "
              f"{s['cover']:>6.3f}  {flag}")
    print(f"median consecutive-frame delta: {med:.4f}")
    return med


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir", type=Path)
    ap.add_argument("--compare", type=Path, default=None,
                    help="second frames dir (e.g. fog-off run)")
    ap.add_argument("--box", default="0.30,0.32,0.70,0.55",
                    help="fractional x0,y0,x1,y1 canopy box")
    ap.add_argument("--speed", type=float, default=2.4, help="walk m/s")
    ap.add_argument("--interval", type=float, default=1.0, help="s/frame")
    ap.add_argument("--csv", type=Path, default=None)
    a = ap.parse_args()
    box = tuple(float(v) for v in a.box.split(","))

    rows = load_seq(a.frames_dir, box)
    report(rows, a.speed, a.interval, a.frames_dir.name)

    if a.csv:
        with open(a.csv, "w", newline="") as f:
            wtr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wtr.writeheader()
            wtr.writerows(rows)
        print(f"csv: {a.csv}")

    if a.compare:
        rows_b = load_seq(a.compare, box)
        report(rows_b, a.speed, a.interval, a.compare.name)
        n = min(len(rows), len(rows_b))
        print(f"\n== A-B per-frame (first {n}): attribution ==")
        print("(steps in BOTH runs = tier handoff; trend/steps only in A = fog)")
        print(f"{'frame':>5} {'Δluma':>7} {'Δsat':>7}")
        for i in range(n):
            print(f"{i:>5} {rows[i]['luma'] - rows_b[i]['luma']:>7.1f} "
                  f"{rows[i]['sat'] - rows_b[i]['sat']:>7.3f}")


if __name__ == "__main__":
    main()

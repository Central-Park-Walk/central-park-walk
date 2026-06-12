#!/usr/bin/env python3
"""Silhouette tier-fit check (walk-around 2026-06-12 cpw_003: the mesh
tier comes in "not as tall or dense as the impostor").

Consumes tier_handoff_check.sh captures (a --tier-isolate pair plus the
no-trees plate at one viewpoint) and reports GEOMETRY fit, complementing
the mean|dRGB| color DoD with three directional metrics:

  height : median signed top-edge delta over columns where both tiers
           have canopy, in px (positive = tier B tops out LOWER on
           screen, i.e. B reads SHORTER than A)
  cover  : canopy mask area ratio B/A (<1 = B covers less of the frame)
  density: median per-column fill ratio (canopy px / column span) B/A
           (<1 = B sparser inside the same silhouette)

Background caveat (same as tier_handoff_check.sh header): the impostor
isolate renders trees to 2500 m while mesh isolates stop at ~460 m, so
canopy BEHIND the studied band leaks into the impostor mask only.
Median statistics keep contaminated columns from dominating, but treat
a marginal FAIL as "inspect the masks" (--save-masks), not as a hard
failure.

Usage:
  scripts/tier_fit_check.py <capture_dir> --a mesh_12 --b impostor_12 \
      --plate notrees_12 [--save-masks]

DoD (1080p): |height median| <= 8 px, cover ratio in [0.80, 1.20],
density ratio in [0.80, 1.20]. Exit 1 on FAIL.
"""
import argparse
import sys

import numpy as np
from PIL import Image

DIFF_THRESHOLD = 0.02   # same plate-diff threshold as tier_handoff_check.sh
MIN_COLUMN_PX = 3       # ignore columns with fewer canopy px (edge slivers)
HEIGHT_TOL_PX = 8.0
RATIO_LO, RATIO_HI = 0.80, 1.20


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def canopy_mask(img, plate):
    return np.abs(img - plate).mean(axis=2) > DIFF_THRESHOLD


def column_stats(mask):
    """Per-column top row index, bottom row index, and canopy px count.
    Columns with < MIN_COLUMN_PX canopy px are marked invalid (top = -1)."""
    h, w = mask.shape
    counts = mask.sum(axis=0)
    any_col = counts >= MIN_COLUMN_PX
    # First/last True row per column; argmax on a column of all-False is 0,
    # so gate by any_col.
    tops = np.where(any_col, mask.argmax(axis=0), -1)
    bots = np.where(any_col, h - 1 - mask[::-1].argmax(axis=0), -1)
    return tops, bots, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--a", required=True, help="reference tier capture name (no .png)")
    ap.add_argument("--b", required=True, help="compared tier capture name")
    ap.add_argument("--plate", required=True, help="no-trees plate capture name")
    ap.add_argument("--save-masks", action="store_true",
                    help="write <dir>/fit_mask_{a,b}.png for visual inspection")
    args = ap.parse_args()

    a = load(f"{args.dir}/{args.a}.png")
    b = load(f"{args.dir}/{args.b}.png")
    plate = load(f"{args.dir}/{args.plate}.png")

    ma = canopy_mask(a, plate)
    mb = canopy_mask(b, plate)
    if args.save_masks:
        for name, m in (("a", ma), ("b", mb)):
            Image.fromarray((m * 255).astype(np.uint8)).save(
                f"{args.dir}/fit_mask_{name}.png")

    area_a, area_b = int(ma.sum()), int(mb.sum())
    if area_a == 0 or area_b == 0:
        print(f"FAIL: empty canopy mask (a={area_a} px, b={area_b} px) — "
              "wrong viewpoint or plate?")
        sys.exit(1)
    cover_ratio = area_b / area_a

    tops_a, bots_a, counts_a = column_stats(ma)
    tops_b, bots_b, counts_b = column_stats(mb)
    both = (tops_a >= 0) & (tops_b >= 0)
    n_cols = int(both.sum())
    if n_cols < 50:
        print(f"FAIL: only {n_cols} shared canopy columns — band too sparse "
              "for a column-wise fit; pick a denser viewpoint")
        sys.exit(1)

    # Signed top-edge delta: row index grows downward, so (top_b - top_a) > 0
    # means B's silhouette starts lower on screen = B is shorter.
    height_delta = (tops_b - tops_a)[both].astype(np.float64)
    h_med = float(np.median(height_delta))
    h_p95 = float(np.percentile(np.abs(height_delta), 95))

    # Per-column fill density inside each tier's own span; ratio B/A.
    span_a = (bots_a - tops_a + 1).astype(np.float64)
    span_b = (bots_b - tops_b + 1).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        fill_a = np.where(span_a > 0, counts_a / span_a, 0.0)
        fill_b = np.where(span_b > 0, counts_b / span_b, 0.0)
        dens = np.where(fill_a > 0, fill_b / np.maximum(fill_a, 1e-6), 0.0)
    d_med = float(np.median(dens[both]))

    scale = a.shape[0] / 1080.0  # thresholds defined at 1080p
    h_ok = abs(h_med) <= HEIGHT_TOL_PX * scale
    c_ok = RATIO_LO <= cover_ratio <= RATIO_HI
    d_ok = RATIO_LO <= d_med <= RATIO_HI

    taller = "B SHORTER than A" if h_med > 0 else "B taller than A"
    print(f"tier fit {args.a} (A) vs {args.b} (B), {n_cols} shared columns:")
    print(f"  height: median top-edge delta {h_med:+.1f} px ({taller}), "
          f"p95 |delta| {h_p95:.1f} px  -> {'PASS' if h_ok else 'FAIL'}")
    print(f"  cover:  mask area ratio B/A = {cover_ratio:.3f} "
          f"(A {area_a} px, B {area_b} px)  -> {'PASS' if c_ok else 'FAIL'}")
    print(f"  density: median column fill ratio B/A = {d_med:.3f}  "
          f"-> {'PASS' if d_ok else 'FAIL'}")
    if not (h_ok and c_ok and d_ok):
        print("  DoD FAIL — inspect masks (--save-masks) before acting; see "
              "background caveat in header")
        sys.exit(1)
    print("  DoD PASS")


if __name__ == "__main__":
    main()

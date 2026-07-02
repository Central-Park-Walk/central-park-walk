#!/usr/bin/env python3
"""Distance-band texture statistics for flat-ground grass images.

Quantifies how the grass "texture character" changes band by band so a game
capture can be matched to a reference photo RELATIONSHIP-for-relationship
(Chris 2026-07-02: "understand fully how the different bands relate to each
other in that photo... then apply the same relationships between bands to our
game"). For each ground-distance band it reports:

  mean luma        -- overall tone
  luma std         -- total variation in the band
  hi-pass std s3   -- blade-scale salt-and-pepper (luma minus 3px gaussian)
  hi-pass std s9   -- clump/mottle scale (luma minus 9px gaussian)
  p5/p95 luma      -- the dark-blade and bright-blade extremes the eye reads

Ground model matches ref_photo_range_rings.py: pinhole over a flat plane.
Level camera: r = f*h/(v-v0). Pitched camera: depression angle per row,
r = h/tan(delta). Central 60% of columns only (edges get oblique smear).

Usage:
  # reference photo (level camera, horizon row known):
  python3 scripts/band_texture_analysis.py IMG --horizon 470 --cam-height 1.6 --hfov 60
  # game capture (pitched camera):
  python3 scripts/band_texture_analysis.py IMG --pitch -10 --cam-height 1.7 --hfov 60
"""
import argparse
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

BANDS = [(1.5, 5), (5, 10), (10, 15), (15, 25), (25, 50), (50, 100), (100, 200)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("--horizon", type=float, default=None,
                    help="horizon row px (level-camera model)")
    ap.add_argument("--pitch", type=float, default=None,
                    help="camera pitch deg, negative = down (pitched model)")
    ap.add_argument("--cam-height", type=float, default=1.6)
    ap.add_argument("--hfov", type=float, default=60.0)
    ap.add_argument("--green-mask", action="store_true",
                    help="grass pixels only (g>=r and g>=0.9b) — excludes rings, "
                         "objects, lines; hp stats then use masked pixels")
    ap.add_argument("--rings-calibrate", action="store_true",
                    help="fit the camera pitch from the --diag-rings red rings in the "
                         "image itself (game captures: the CLI --pitch is NOT the "
                         "rendered pitch — measured -4.4 deg for a requested -10; "
                         "2026-07-02 mis-registration bug). Needs a rings capture.")
    args = ap.parse_args()

    img = Image.open(args.src).convert("RGB")
    W, H = img.size
    arr = np.asarray(img, dtype=np.float64)
    luma = arr @ np.array([0.2126, 0.7152, 0.0722])
    f = (W / 2.0) / np.tan(np.radians(args.hfov / 2.0))
    v = np.arange(H, dtype=np.float64)

    if args.rings_calibrate:
        # Detect the --diag-rings red rings near frame centre and fit the pitch:
        # for each ring at distance R, depression = atan(h/R) = screen_angle + pitch.
        r_, g_, b_ = arr[..., 0], arr[..., 1], arr[..., 2]
        red = (r_ > 130) & (r_ > g_ * 1.7) & (r_ > b_ * 1.7)
        rowfrac = red[:, int(W * 0.30):int(W * 0.70)].mean(axis=1)
        rows_hit = np.where(rowfrac > 0.05)[0]
        groups: list = []
        for rr in rows_hit:
            if groups and rr - groups[-1][-1] <= 6:
                groups[-1].append(rr)
            else:
                groups.append([rr])
        centers = sorted(float(np.mean(g)) for g in groups)[::-1]  # nearest first
        merged: list = []
        for c in centers:  # a wide near ring can split across blades/terrain
            if merged and merged[-1] - c < 35:
                merged[-1] = (merged[-1] + c) / 2.0
            else:
                merged.append(c)
        centers = merged
        rings_all = [5, 10, 15, 25, 50, 100]
        if len(centers) < 3:
            ap.error(f"rings-calibrate: only {len(centers)} rings detected")
        n = min(len(centers), 5)

        def fit(assign_rings, rows_):
            ps = [np.degrees(np.arctan(args.cam_height / R)
                             - np.arctan((row - H / 2.0) / f))
                  for R, row in zip(assign_rings, rows_)]
            return float(np.mean(ps)), float(np.std(ps)), ps

        # detection can miss the nearest ring — pick the assignment window whose
        # per-ring pitches agree best
        best = None
        for start in range(0, len(rings_all) - n + 1):
            mean_p, std_p, ps = fit(rings_all[start:start + n], centers[:n])
            if best is None or std_p < best[1]:
                best = (mean_p, std_p, ps, rings_all[start:start + n])
        pitch_fit, std_p, ps, used = best
        print(f"# rings-calibrate: rows {[int(c) for c in centers[:n]]} = {used}m -> "
              f"pitch {pitch_fit:.2f} deg (std {std_p:.2f}, per-ring "
              f"{[f'{p:.1f}' for p in ps]})")
        delta = np.radians(pitch_fit) + np.arctan((v - H / 2.0) / f)
        r_row = np.where(delta > 1e-4, args.cam_height / np.tan(delta), np.inf)
    elif args.pitch is not None:
        # depression angle of each row for a camera pitched pitch deg
        delta = np.radians(-args.pitch) + np.arctan((v - H / 2.0) / f)
        r_row = np.where(delta > 1e-4, args.cam_height / np.tan(delta), np.inf)
    else:
        if args.horizon is None:
            ap.error("need --horizon (level) or --pitch (pitched)")
        dv = v - args.horizon
        r_row = np.where(dv > 0.5, f * args.cam_height / np.maximum(dv, 0.5), np.inf)

    hp3 = luma - gaussian_filter(luma, 3.0)
    hp9 = luma - gaussian_filter(luma, 9.0)
    c0, c1 = int(W * 0.2), int(W * 0.8)  # central columns only
    gmask = np.ones(luma.shape, bool)
    if args.green_mask:
        r_, g_, b_ = arr[..., 0], arr[..., 1], arr[..., 2]
        gmask = (g_ >= r_) & (g_ >= 0.9 * b_)

    print(f"{'band m':>10} {'rows':>10} {'mean':>6} {'std':>6} "
          f"{'hp3':>6} {'hp9':>6} {'p5':>5} {'p95':>5} {'mask%':>6}")
    for lo, hi in BANDS:
        rows = np.where((r_row >= lo) & (r_row < hi))[0]
        if len(rows) < 4:
            print(f"{lo:>5.1f}-{hi:<4.0f} {'--too few rows--':>10}")
            continue
        sl = (slice(rows.min(), rows.max() + 1), slice(c0, c1))
        m = gmask[sl]
        if m.sum() < 100:
            print(f"{lo:>5.1f}-{hi:<4.0f} {'--masked out--':>10}")
            continue
        L, h3, h9 = luma[sl][m], hp3[sl][m], hp9[sl][m]
        print(f"{lo:>5.1f}-{hi:<4.0f} {rows.min():>4}-{rows.max():<5} "
              f"{L.mean():>6.1f} {L.std():>6.1f} {h3.std():>6.2f} {h9.std():>6.2f} "
              f"{np.percentile(L, 5):>5.0f} {np.percentile(L, 95):>5.0f} "
              f"{100.0 * m.mean():>5.1f}%")


if __name__ == "__main__":
    main()

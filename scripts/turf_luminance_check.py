#!/usr/bin/env python3
"""Lawn/sky luminance ratio check (docs/grass.md §6).

Measures the clean-turf vs sky luminance ratio that the Sheep Meadow
reference comparison flagged (game 0.37 vs reference 0.63, 2026-06-11).
Display-referred (sRGB-encoded) Rec.709 luminance medians, same convention
as the sky calibration session (rendering.md §6b "sky median 178/255").

Lawn pixels are additionally gated by green dominance (G >= R and
G >= 0.9*B) inside the lawn box so people/objects/signs in reference
footage don't skew the median.

Usage:
  turf_luminance_check.py game /tmp/turf_cal/hero_baseline.png
  turf_luminance_check.py hq_02-08 notes/refs/sheep_meadow_FRlNuZ4zz8U/hq_02-08.jpg
  turf_luminance_check.py hq_08-08 notes/refs/sheep_meadow_FRlNuZ4zz8U/hq_08-08.jpg
  turf_luminance_check.py custom img.png --lawn x0,y0,x1,y1 --sky x0,y0,x1,y1

Presets (fractional boxes, x0,y0,x1,y1):
  game     — s_skyline_hero pose (--pos=-820,1080,180 --time=13): big clean
             sunlit lawn band, sky strip right of the left-edge tree canopy.
  hq_02-08 — W view: lawn lower half (median robust to crowds), sky window
             between tower clusters (blue + cirrus).
  hq_08-08 — hero S view: lawn right of the info sign, sky window right of
             the 111 W 57th supertall.
"""
import argparse
import sys

import numpy as np
from PIL import Image

PRESETS = {
    "game":     {"lawn": (0.15, 0.62, 0.95, 0.95), "sky": (0.30, 0.02, 0.95, 0.16)},
    "hq_02-08": {"lawn": (0.05, 0.62, 0.95, 0.95), "sky": (0.35, 0.03, 0.75, 0.25)},
    "hq_08-08": {"lawn": (0.45, 0.70, 0.95, 0.92), "sky": (0.57, 0.02, 0.70, 0.28)},
}

LUMA = np.array([0.2126, 0.7152, 0.0722])


def box_px(box, w, h):
    x0, y0, x1, y1 = box
    return int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)


def median_luma(img, box, green_mask):
    w, h = img.size
    x0, y0, x1, y1 = box_px(box, w, h)
    a = np.asarray(img.convert("RGB"), dtype=np.float32)[y0:y1, x0:x1]
    if green_mask:
        g = a[..., 1]
        keep = (g >= a[..., 0]) & (g >= 0.9 * a[..., 2])
        a = a[keep]
        if a.size == 0:
            raise SystemExit("green mask rejected every pixel in the lawn box")
    else:
        a = a.reshape(-1, 3)
    return float(np.median(a @ LUMA))


def parse_box(s):
    v = tuple(float(t) for t in s.split(","))
    if len(v) != 4:
        raise argparse.ArgumentTypeError("box must be x0,y0,x1,y1 (fractions)")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", help="game | hq_02-08 | hq_08-08 | custom")
    ap.add_argument("image")
    ap.add_argument("--lawn", type=parse_box, help="override lawn box (fractions)")
    ap.add_argument("--sky", type=parse_box, help="override sky box (fractions)")
    args = ap.parse_args()

    if args.preset == "custom":
        if not (args.lawn and args.sky):
            ap.error("custom preset needs --lawn and --sky")
        boxes = {"lawn": args.lawn, "sky": args.sky}
    else:
        if args.preset not in PRESETS:
            ap.error(f"unknown preset {args.preset!r}")
        boxes = dict(PRESETS[args.preset])
        if args.lawn:
            boxes["lawn"] = args.lawn
        if args.sky:
            boxes["sky"] = args.sky

    img = Image.open(args.image)
    lawn = median_luma(img, boxes["lawn"], green_mask=True)
    sky = median_luma(img, boxes["sky"], green_mask=False)
    ratio = lawn / sky if sky > 0 else float("nan")
    print(f"{args.preset}  {args.image}")
    print(f"  lawn median {lawn:6.1f}/255   sky median {sky:6.1f}/255   "
          f"lawn/sky {ratio:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

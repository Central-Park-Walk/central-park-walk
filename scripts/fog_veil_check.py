#!/usr/bin/env python3
"""Aerial-perspective / fog-veil check (rendering.md §6c, COMPARISON.md #5).

Measures the distant tree-line band and skyline-tower patches on the two
Sheep Meadow calibration poses, and (in pair mode) the volumetric-fog
contribution as an on/off delta. Display-referred sRGB Rec.709, same
convention as turf_luminance_check.py / rendering.md §6b.

Reference targets (notes/refs/sheep_meadow_FRlNuZ4zz8U, clear noon):
  - tree line at ~400 m: dark mass, luma 36-62 (e.g. 55/65/36 in hq_02-08)
  - fog veil over it: ~10% of the unfogged value, slightly BLUE
    (game measured 2026-06-11 pre-fix: +37 luma = 38%, warm +49R/+33G/+36B)
  - towers 1-3 km: blue-shifted, lifted blacks (not flat-crisp, not washed)

Poses (scripts/sheep_meadow_ref_captures.sh conditions, --cloud-seed=7):
  treeline — nw_across_meadow  --pos=-720,1360,45  --time=13
  hero     — s_skyline_hero    --pos=-820,1080,180 --time=13

Usage:
  fog_veil_check.py treeline fogged.png [unfogged.png]
  fog_veil_check.py hero     fogged.png [unfogged.png]
  fog_veil_check.py custom   img.png --band x0,y0,x1,y1 [--dark-only]
"""
import argparse

import numpy as np
from PIL import Image

# Fractional boxes x0,y0,x1,y1. "tree" bands gate to vegetation-dark pixels
# (G-dominant, luma < 0.75 of band max) so sky gaps / lawn / towers between
# crowns don't skew the read; "tower" boxes gate to non-sky (low-saturation
# bright sky removed by the blue-dominance test).
POSES = {
    "treeline": {"tree": (0.05, 0.40, 0.95, 0.50), "tower": (0.10, 0.10, 0.45, 0.38)},
    "hero":     {"tree": (0.30, 0.44, 0.95, 0.52), "tower": (0.35, 0.10, 0.85, 0.38)},
}

LUMA = np.array([0.2126, 0.7152, 0.0722])


def crop(img, box):
    w, h = img.size
    x0, y0, x1, y1 = box
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    return a[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]


def tree_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    luma = a @ LUMA
    return (g >= r) & (g >= b * 0.9) & (luma < np.percentile(luma, 60))


def tower_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # towers are grey/warm-grey; sky is blue-dominant and brighter
    return ~((b > r * 1.08) & (b > 120))


def stats(a, mask, label):
    sel = a[mask]
    if sel.size == 0:
        print(f"  {label:8s}  (no pixels matched)")
        return None
    rgb = np.median(sel, axis=0)
    luma = float(np.median(sel @ LUMA))
    print(f"  {label:8s}  luma {luma:6.1f}  RGB {rgb[0]:.0f}/{rgb[1]:.0f}/{rgb[2]:.0f}"
          f"  ({100*mask.mean():.0f}% of band)")
    return luma, rgb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pose", choices=list(POSES) + ["custom"])
    ap.add_argument("fogged")
    ap.add_argument("unfogged", nargs="?")
    ap.add_argument("--band", help="custom x0,y0,x1,y1")
    args = ap.parse_args()

    if args.pose == "custom":
        boxes = {"band": tuple(float(v) for v in args.band.split(","))}
    else:
        boxes = POSES[args.pose]

    imgs = [("fogged", Image.open(args.fogged))]
    if args.unfogged:
        imgs.append(("unfogged", Image.open(args.unfogged)))

    # In pair mode the mask comes from the UNFOGGED frame (crisper sky/object
    # separation) and is applied to both, so deltas compare the same pixels.
    mask_src = imgs[-1][1]
    results = {}
    masks = {}
    for label, box in boxes.items():
        a = crop(mask_src, box)
        masks[label] = tree_mask(a) if label in ("tree", "band") else tower_mask(a)
    for name, img in imgs:
        print(f"{name}: {args.fogged if name == 'fogged' else args.unfogged}")
        for label, box in boxes.items():
            results[(name, label)] = stats(crop(img, box), masks[label], label)

    if args.unfogged:
        print("fog contribution (fogged - unfogged, same mask convention):")
        for label in boxes:
            f, u = results.get(("fogged", label)), results.get(("unfogged", label))
            if not f or not u:
                continue
            dl, drgb = f[0] - u[0], f[1] - u[1]
            pct = 100.0 * dl / max(u[0], 1e-3)
            tone = "BLUE" if drgb[2] >= drgb[0] else "WARM"
            print(f"  {label:8s}  Δluma {dl:+6.1f} ({pct:+.0f}% of unfogged)"
                  f"  ΔRGB {drgb[0]:+.0f}/{drgb[1]:+.0f}/{drgb[2]:+.0f}  [{tone}]")


if __name__ == "__main__":
    main()

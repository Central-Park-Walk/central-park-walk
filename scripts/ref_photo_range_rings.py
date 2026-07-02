#!/usr/bin/env python3
"""Draw camera-range rings on a flat-ground reference photo.

Projects the same diagnostic rings the game draws (--diag-rings / R key:
1/5/10/15/25/50m then every 50m to 500m) onto a photo of flat ground, so a
reference photo and a game screenshot can be compared distance-band by
distance-band ("how much detail does the real world actually show at 15m?").

Ground-plane pinhole model. You supply the camera height, the horizon row
(eyeball the treeline/field edge) and the horizontal FOV; everything below
the horizon maps to a ground range r = sqrt(x^2 + z^2), and rings are bands
of |r - R| < tol with tol following the pixel footprint (the shader's fwidth
trick) so the lines stay a few px wide everywhere.

Example (the KBG sod reference):
  python3 scripts/ref_photo_range_rings.py \
      "reference_photos/grass/91suSCsHsdL._AC_SL1500_.jpg" tmp/sodref_rings.png \
      --horizon 470 --cam-height 1.6 --hfov 60
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RINGS = [1, 5, 10, 15, 25] + list(range(50, 501, 50))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--horizon", type=float, required=True,
                    help="horizon row in px from top (base of the far treeline)")
    ap.add_argument("--cam-height", type=float, default=1.6)
    ap.add_argument("--hfov", type=float, default=60.0, help="horizontal FOV, deg")
    args = ap.parse_args()

    img = Image.open(args.src).convert("RGB")
    W, H = img.size
    v0, h_cam = args.horizon, args.cam_height
    f = (W / 2.0) / np.tan(np.radians(args.hfov / 2.0))
    u0 = W / 2.0

    u = np.arange(W)[None, :].repeat(H, 0).astype(np.float64)
    v = np.arange(H)[:, None].repeat(W, 1).astype(np.float64)
    below = v > v0 + 0.5
    z = np.where(below, f * h_cam / np.maximum(v - v0, 0.5), np.nan)
    x = (u - u0) * z / f
    r = np.sqrt(x * x + z * z)
    gy, gx = np.gradient(np.where(np.isfinite(r), r, 0.0))
    fw = np.nan_to_num(np.sqrt(gx * gx + gy * gy))

    mask = np.zeros((H, W), bool)
    for R in RINGS:
        tol = np.clip(fw * 1.8, 0.01, R * 0.02)
        mask |= below & np.isfinite(r) & (np.abs(r - R) < tol)

    arr = np.array(img, dtype=np.float64)
    arr[mask] = arr[mask] * 0.15 + np.array([200.0, 15.0, 15.0]) * 0.85
    out = Image.fromarray(arr.astype(np.uint8))

    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype(FONT, 34)
        small = ImageFont.truetype(FONT, 24)
    except OSError:
        font = small = ImageFont.load_default()
    for R in [5, 10, 15, 25, 50, 100]:
        vr = v0 + f * h_cam / R
        if vr > H - 8:
            continue
        fnt = font if R <= 25 else small
        tx = u0 if R <= 50 else u0 - 320  # 100m goes left, clear of 50m
        ty = vr - (40 if R <= 25 else 28)
        txt = f"{R}m"
        tw = draw.textlength(txt, font=fnt)
        draw.text((tx - tw / 2 + 2, ty + 2), txt, fill=(0, 0, 0), font=fnt)
        draw.text((tx - tw / 2, ty), txt, fill=(255, 60, 60), font=fnt)
    note = ("rings: 1/5/10/15/25/50m then every 50m to 500m — cam %.1fm, "
            "hFOV %.0fdeg, horizon row %.0f" % (h_cam, args.hfov, v0))
    draw.text((22, 22), note, fill=(0, 0, 0), font=small)
    draw.text((20, 20), note, fill=(255, 235, 235), font=small)
    out.save(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    main()

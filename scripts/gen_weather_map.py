#!/usr/bin/env python3
"""Generate cloud_sky/weather.bmp — the volumetric-cloud weather map.

Why this exists (2026-06-10, docs/rendering.md sky calibration): the stock
demo weather.bmp's coverage channel (B) is mid-gray noise with NO zeros —
94% of texels > 0.3 — so `cloud_coverage * weather.b` is non-zero across
the whole dome and clouds.glsl's threshold remap renders one giant
connected slab at any coverage setting. Real fair-weather cumulus is a
field of DISCRETE cells with genuinely clear sky between them.

Field model (real-world envelope, NYC summer):
- individual cells 0.5–2 km across (lognormal radii), flat-based
- jittered-grid placement ~1.5–3x cell size apart
- mild anisotropy along one axis (boundary-layer "cloud streets")
- 5–10 km patchiness: a low-frequency mask clears some regions entirely
- map wraps (sampler repeats); 1 repeat = 1/0.00006 m = 16.7 km

Channels (Schneider convention, consumed by clouds.glsl density()):
- R: cloud type (0 stratus .. 1 cumulus). Cores read more cumulus.
- G: unused by the shader — zeroed.
- B: coverage. Cell interiors ~0.75–1.0 with soft edges, hard 0 between.
  `params.cloud_coverage` (NOAA monthly data via day_night_cycle.gd)
  remains the global scale on top of this.

Usage: python3 scripts/gen_weather_map.py [--seed N] [--coverage 0.38]
Writes cloud_sky/weather.bmp (512x512). Reimport happens on next editor
open or `godot --headless --import`.
"""
import argparse
import os
import numpy as np
from PIL import Image

SIZE = 512
KM_PER_REPEAT = 16.667           # 1 / 0.00006 m weather_scale
PX_PER_KM = SIZE / KM_PER_REPEAT  # ~30.7

def torus_dist2(px, py, cx, cy, size):
    """Squared distance on a wrapping square (seamless map)."""
    dx = np.abs(px - cx); dx = np.minimum(dx, size - dx)
    dy = np.abs(py - cy); dy = np.minimum(dy, size - dy)
    return dx * dx + dy * dy

def value_noise(rng, size, cells):
    """Bilinear-interpolated lattice noise, wrapping."""
    lat = rng.random((cells, cells))
    yy, xx = np.mgrid[0:size, 0:size]
    fx = xx * cells / size; fy = yy * cells / size
    x0 = fx.astype(int) % cells; y0 = fy.astype(int) % cells
    x1 = (x0 + 1) % cells; y1 = (y0 + 1) % cells
    tx = fx - np.floor(fx); ty = fy - np.floor(fy)
    tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty)
    return (lat[y0, x0] * (1 - tx) * (1 - ty) + lat[y0, x1] * tx * (1 - ty)
            + lat[y1, x0] * (1 - tx) * ty + lat[y1, x1] * tx * ty)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260610)
    ap.add_argument("--coverage", type=float, default=0.38,
                    help="target fraction of map area inside cloud cells")
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(__file__), "..", "cloud_sky", "weather.bmp"))
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(float)

    # --- Cell placement: jittered grid, ~2.4 km pitch ---
    pitch_km = 2.1
    n = max(4, int(round(KM_PER_REPEAT / pitch_km)))   # cells per axis
    step = SIZE / n
    coverage = np.zeros((SIZE, SIZE))
    strength = np.zeros((SIZE, SIZE))   # blob-core strength for the R channel

    # Cloud-street anisotropy: stretch along a session direction.
    street_ang = rng.uniform(0, np.pi)
    ca, sa = np.cos(street_ang), np.sin(street_ang)
    stretch = 1.35

    for gy in range(n):
        for gx in range(n):
            if rng.random() < 0.10:      # some grid slots stay empty
                continue
            cx = (gx + 0.5) * step + rng.uniform(-0.45, 0.45) * step
            cy = (gy + 0.5) * step + rng.uniform(-0.45, 0.45) * step
            # lognormal radii: median ~0.85 km, tail to ~1.8 km
            r_km = float(np.clip(rng.lognormal(np.log(0.85), 0.45), 0.35, 1.8))
            r_px = r_km * PX_PER_KM
            # anisotropic distance (rotate into street frame, squash one axis)
            dx = xx - cx; dx -= SIZE * np.round(dx / SIZE)
            dy = yy - cy; dy -= SIZE * np.round(dy / SIZE)
            u = (dx * ca + dy * sa) / stretch
            v = -dx * sa + dy * ca
            d = np.sqrt(u * u + v * v)
            # soft-edged disc: full inside 0.55r, fades to 0 at r
            blob = np.clip((1.0 - d / r_px) / 0.45, 0.0, 1.0)
            blob = blob * blob * (3 - 2 * blob)
            coverage = np.maximum(coverage, blob)
            strength = np.maximum(strength, blob * min(1.0, r_km / 1.1))

    # --- 5-10 km patchiness: clear out whole regions ---
    patch = value_noise(rng, SIZE, 3)            # ~5.6 km features
    patch = np.clip((patch - 0.22) / 0.25, 0.0, 1.0)
    coverage *= patch
    strength *= patch

    # --- Per-cell edge raggedness (small-scale erosion of the soft edge) ---
    rag = value_noise(rng, SIZE, 24)             # ~700 m features
    coverage = np.clip(coverage - (1.0 - coverage) * rag * 0.35, 0.0, 1.0)

    # --- Normalize to the target areal coverage ---
    area = (coverage > 0.05).mean()
    print(f"raw cell area: {area:.2f} (target {args.coverage:.2f})")
    # If badly off, scale the patch threshold rather than the values —
    # but in practice the defaults land close; warn instead of force.
    if abs(area - args.coverage) > 0.10:
        print("WARN: areal coverage off target — tune pitch/empty-slot rate")

    # Interiors: lift cell cores toward 1.0 so coverage*B keeps punch
    b_chan = np.clip(coverage * 0.85 + (coverage ** 3) * 0.15, 0.0, 1.0)

    # R: cloud type — cores of big cells most cumulus; thin edges stratocu-ish
    r_chan = np.clip(0.45 + strength * 0.5 + (rag - 0.5) * 0.08, 0.0, 1.0)

    img = np.stack([r_chan, np.zeros_like(b_chan), b_chan], axis=-1)
    img8 = (img * 255 + 0.5).astype(np.uint8)
    out = os.path.abspath(args.out)
    Image.fromarray(img8, "RGB").save(out)

    b = b_chan
    print(f"wrote {out}")
    print(f"B stats: zero {np.mean(b < 0.02) * 100:.0f}%  >0.5 {np.mean(b > 0.5) * 100:.0f}%  "
          f"mean-inside {b[b > 0.05].mean():.2f}")

if __name__ == "__main__":
    main()

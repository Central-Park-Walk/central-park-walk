#!/usr/bin/env python3
"""Generate cloud_sky/weather_<type>.bmp — per-weather-state cloud maps.

Why this exists (2026-06-10, docs/rendering.md sky calibration): the stock
demo weather.bmp's coverage channel (B) is mid-gray noise with NO zeros —
94% of texels > 0.3 — so `cloud_coverage * weather.b` is non-zero across
the whole dome and clouds.glsl's threshold remap renders one giant
connected slab at any coverage setting. Real fair-weather cumulus is a
field of DISCRETE cells with genuinely clear sky between them.

2026-06-11 (docs/sky.md P1): one map per weather state. The state machine
crossfades between maps at runtime (clouds.glsl weather_mix), so overcast
stops being "denser cumulus" and each weather mode gets a
meteorologically correct sky:

- fair_cumulus        discrete humilis/mediocris cells (CLEAR)
- stratocumulus_sheet lumpy grey sheet with blue gaps (SNOW)
- stratus_overcast    featureless low veil (RAIN, FOG)
- storm_congestus     large merged towers (THUNDERSTORM)
- broken_dramatic     big torn sheets + gaps (scheduled dusk/dawn skies)

Channels (Schneider convention, consumed by clouds.glsl density()):
- R: cloud type (0 stratus .. 1 cumulus) — selects the height-density
  gradient profile.
- G: tower height — fraction of the 2.5 km layer this column's cloud top
  reaches (2026-06-11 marshmallow fix). clouds.glsl rescales
  height_fraction by G: flat shared bases, per-column tops.
- B: coverage. `params.cloud_coverage` (NOAA monthly data via
  day_night_cycle.gd) remains the global scale on top of this.

Usage: python3 scripts/gen_weather_map.py [--type all|<name>] [--seed N]
Writes cloud_sky/weather_<type>.bmp (512x512). Reimport happens on next
editor open or `godot --headless --import`.
"""
import argparse
import os
import numpy as np
from PIL import Image

SIZE = 512
KM_PER_REPEAT = 16.667           # 1 / 0.00006 m weather_scale
PX_PER_KM = SIZE / KM_PER_REPEAT  # ~30.7
LAYER_KM = 2.5                   # clouds.glsl sky_b..sky_t thickness

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

def cell_field(rng, pitch_km, r_median_km, r_sigma, r_min_km, r_max_km,
               empty_rate, stretch=1.35, cluster_p=0.0):
    """Jittered-grid soft-disc cell field (shared by cumulus/storm types).

    cluster_p (sky.md §6 P2 de-bunning): probability a cell grows 1-3
    satellite lobes fused to its flank — an isolated soft disc extrudes to
    a smooth single-dome "bun", while real humilis/mediocris masses are
    irregular multi-lobed clusters. Satellites are smaller and slightly
    lower, so the merged silhouette reads as one ragged cloud, not two.

    Returns (coverage, strength, tower_km) — tower in km, caller scales.
    """
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    n = max(3, int(round(KM_PER_REPEAT / pitch_km)))
    step = SIZE / n
    coverage = np.zeros((SIZE, SIZE))
    strength = np.zeros((SIZE, SIZE))
    tower_km = np.zeros((SIZE, SIZE))

    # Cloud-street anisotropy: stretch along a session direction.
    street_ang = rng.uniform(0, np.pi)
    ca, sa = np.cos(street_ang), np.sin(street_ang)

    def stamp(cx, cy, r_km, h_scale):
        r_px = r_km * PX_PER_KM
        dx = xx - cx; dx -= SIZE * np.round(dx / SIZE)
        dy = yy - cy; dy -= SIZE * np.round(dy / SIZE)
        u = (dx * ca + dy * sa) / stretch
        v = -dx * sa + dy * ca
        d = np.sqrt(u * u + v * v)
        # soft-edged disc: full inside 0.55r, fades to 0 at r
        blob = np.clip((1.0 - d / r_px) / 0.45, 0.0, 1.0)
        blob = blob * blob * (3 - 2 * blob)
        np.maximum(coverage, blob, out=coverage)
        np.maximum(strength, blob * min(1.0, r_km / 1.1), out=strength)
        # Tower height: ~0.75 x radius at the core. blob^0.45 keeps the
        # dome flat on top, dropping fast only at the rim.
        h_km = max(0.75 * r_km, 0.35) * h_scale
        np.maximum(tower_km, (blob ** 0.45) * h_km, out=tower_km)

    for gy in range(n):
        for gx in range(n):
            if rng.random() < empty_rate:
                continue
            cx = (gx + 0.5) * step + rng.uniform(-0.45, 0.45) * step
            cy = (gy + 0.5) * step + rng.uniform(-0.45, 0.45) * step
            r_km = float(np.clip(rng.lognormal(np.log(r_median_km), r_sigma),
                                 r_min_km, r_max_km))
            stamp(cx, cy, r_km, 1.0)
            if rng.random() < cluster_p:
                for _ in range(rng.integers(1, 3)):
                    ang = rng.uniform(0, 2 * np.pi)
                    off = rng.uniform(0.65, 1.15) * r_km * PX_PER_KM
                    sat_r = rng.uniform(0.45, 0.75) * r_km
                    if sat_r < r_min_km * 0.6:
                        continue
                    stamp(cx + np.cos(ang) * off, cy + np.sin(ang) * off,
                          sat_r, rng.uniform(0.65, 0.85))
    return coverage, strength, tower_km


def gen_fair_cumulus(rng):
    """Discrete fair-weather cumulus cells with clear sky between (CLEAR)."""
    # P2 de-bunning (sky.md §6): wider size anarchy (sigma .45->.60),
    # stronger wind elongation (stretch 1.6), and satellite-lobe clustering
    # so masses read multi-lobed instead of single smooth domes.
    coverage, strength, tower_km = cell_field(
        rng, pitch_km=2.15, r_median_km=0.85, r_sigma=0.60,
        r_min_km=0.35, r_max_km=1.9, empty_rate=0.22,
        stretch=1.6, cluster_p=0.55)
    tower = tower_km / LAYER_KM

    # 5-10 km patchiness: clear out whole regions
    patch = value_noise(rng, SIZE, 3)            # ~5.6 km features
    patch = np.clip((patch - 0.30) / 0.25, 0.0, 1.0)
    coverage *= patch
    strength *= patch
    tower *= 0.4 + 0.6 * patch          # patch edges get shallower cells

    # Per-cell edge raggedness
    rag = value_noise(rng, SIZE, 24)             # ~700 m features
    coverage = np.clip(coverage - (1.0 - coverage) * rag * 0.65, 0.0, 1.0)

    # Interiors: lift cell cores toward 1.0 so coverage*B keeps punch.
    # ^0.75: the finer base-noise scale in clouds.glsl adds within-cell
    # variance, so interiors need headroom against the Schneider threshold.
    b = np.clip(coverage ** 0.75, 0.0, 1.0)
    r = np.clip(0.45 + strength * 0.5 + (rag - 0.5) * 0.08, 0.0, 1.0)
    g = np.clip(tower, 0.0, 1.0)
    return r, g, b


def gen_stratocumulus_sheet(rng):
    """Lumpy grey sheet with blue gaps (SNOW / closed-cell stratocu).

    Real stratocumulus: contiguous deck of ~1 km lumps, 10-25% sky in
    irregular gaps, shallow (~0.6-0.8 km thick), tops gently rippled.
    """
    lump = value_noise(rng, SIZE, 16)            # ~1 km lumps
    lump2 = value_noise(rng, SIZE, 32)           # ~0.5 km fine ripple
    sheet = np.clip(0.62 + 0.38 * lump + 0.12 * (lump2 - 0.5), 0.0, 1.0)

    # Gaps: low-frequency holes torn open where the hole field runs low.
    hole = value_noise(rng, SIZE, 5)             # ~3.3 km gap pattern
    gap = np.clip((hole - 0.30) / 0.10, 0.0, 1.0)  # 0 = open sky
    b = sheet * gap
    # Sharpen gap edges a little (real decks have crisp blue holes)
    b = np.clip(b, 0.0, 1.0) ** 0.85

    r = np.clip(0.38 + (lump - 0.5) * 0.12, 0.0, 1.0)   # stratocu profile
    # Tops ripple with the lumps: 0.55-0.85 km over the 2.5 km layer
    g = np.clip((0.55 + 0.30 * lump) / LAYER_KM + 0.0 * b, 0.0, 1.0)
    g *= np.where(b > 0.02, 1.0, 0.0) * 0.0 + 1.0  # keep field defined everywhere
    return r, g, b


def gen_stratus_overcast(rng):
    """Featureless low veil (RAIN / drizzle / FOG deck)."""
    soft = value_noise(rng, SIZE, 6)             # ~2.8 km gentle variation
    fine = value_noise(rng, SIZE, 20)
    b = np.clip(0.93 + 0.07 * soft - 0.02 * fine, 0.0, 1.0)
    r = np.clip(0.03 + 0.05 * soft, 0.0, 1.0)    # stratus density profile
    # Flat base, flat top: ~0.55-0.65 km deck
    g = np.clip((0.55 + 0.12 * soft) / LAYER_KM, 0.0, 1.0)
    return r, g, b


def gen_storm_congestus(rng):
    """Large merged congestus/cumulonimbus bases (THUNDERSTORM).

    Big cells (2-4.5 km) merged into masses; cores reach the full layer
    (G=1) — the anvil/mammatus pass (sky.md §2.3) keys off R≈1, G>0.8.
    """
    coverage, strength, tower_km = cell_field(
        rng, pitch_km=4.5, r_median_km=2.4, r_sigma=0.40,
        r_min_km=1.2, r_max_km=4.5, empty_rate=0.30, stretch=1.2)
    tower = np.clip(tower_km / LAYER_KM, 0.0, 1.0)
    # Storm towers fill the layer: re-scale so big-cell cores hit 1.0
    tower = np.clip(tower * 1.6, 0.0, 1.0)

    # Mild patchiness only — storm skies are mostly filled
    patch = value_noise(rng, SIZE, 3)
    patch = np.clip((patch - 0.08) / 0.22, 0.0, 1.0)
    coverage *= patch
    tower *= 0.6 + 0.4 * patch

    # Ragged torn edges (gust-front shred)
    rag = value_noise(rng, SIZE, 20)
    coverage = np.clip(coverage - (1.0 - coverage) * rag * 0.65, 0.0, 1.0)

    b = np.clip(coverage ** 0.7, 0.0, 1.0)
    r = np.clip(0.75 + strength * 0.25, 0.0, 1.0)        # hard cumulus profile
    g = np.clip(np.maximum(tower, 0.20 * (b > 0.02)), 0.0, 1.0)
    return r, g, b


def gen_broken_dramatic(rng):
    """Big torn sheets + gaps — the dramatic dusk/dawn sky (sky.md §2.6).

    Bands of broken stratocumulus/altocumulus with wide clear lanes: lots
    of cloud EDGE for low sun to paint, ~50% coverage.
    """
    band = value_noise(rng, SIZE, 4)             # ~4 km sheet masses
    band2 = value_noise(rng, SIZE, 9)            # ~1.9 km secondary tears
    sheet = np.clip((band - 0.22) / 0.24, 0.0, 1.0) * \
        np.clip((band2 - 0.04) / 0.30, 0.0, 1.0)

    # Ragged edges at two scales — torn look
    rag = value_noise(rng, SIZE, 24)
    sheet = np.clip(sheet - (1.0 - sheet) * rag * 0.40, 0.0, 1.0)

    b = np.clip(sheet ** 0.8, 0.0, 1.0)
    # Mixed types: stratocu sheets with cumulus-leaning cores
    r = np.clip(0.30 + 0.40 * sheet + (rag - 0.5) * 0.10, 0.0, 1.0)
    # Mid towers 0.75-1.5 km: enough relief for shadowed undersides
    g = np.clip((0.75 + 0.75 * sheet) / LAYER_KM, 0.0, 1.0)
    return r, g, b


GENERATORS = {
    "fair_cumulus": gen_fair_cumulus,
    "stratocumulus_sheet": gen_stratocumulus_sheet,
    "stratus_overcast": gen_stratus_overcast,
    "storm_congestus": gen_storm_congestus,
    "broken_dramatic": gen_broken_dramatic,
}


def write_map(name, rng, out_dir):
    r, g, b = GENERATORS[name](rng)
    img = np.stack([r, g, b], axis=-1)
    img8 = (img * 255 + 0.5).astype(np.uint8)
    out = os.path.abspath(os.path.join(out_dir, f"weather_{name}.bmp"))
    Image.fromarray(img8, "RGB").save(out)
    inside = b > 0.05
    gt = g[inside] if inside.any() else g
    print(f"wrote {out}")
    print(f"  B: zero {np.mean(b < 0.02) * 100:.0f}%  >0.5 {np.mean(b > 0.5) * 100:.0f}%  "
          f"area {inside.mean():.2f}  mean-inside {b[inside].mean() if inside.any() else 0:.2f}")
    print(f"  G inside cells: p50 {np.percentile(gt, 50):.2f} p90 {np.percentile(gt, 90):.2f} "
          f"max {gt.max():.2f} (x{LAYER_KM:.1f} km = cloud-top height)")
    print(f"  R inside cells: p50 {np.percentile(r[inside], 50) if inside.any() else 0:.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260610)
    ap.add_argument("--type", default="all",
                    help="all | " + " | ".join(GENERATORS))
    ap.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(__file__), "..", "cloud_sky"))
    args = ap.parse_args()

    names = list(GENERATORS) if args.type == "all" else [args.type]
    for name in names:
        if name not in GENERATORS:
            raise SystemExit(f"unknown type '{name}' — options: {list(GENERATORS)}")
        # fair_cumulus keeps the ORIGINAL seed stream so the field stays
        # byte-identical to the calibrated 2026-06-11 weather.bmp; other
        # types get independent deterministic streams.
        if name == "fair_cumulus":
            rng = np.random.default_rng(args.seed)
        else:
            rng = np.random.default_rng([args.seed, list(GENERATORS).index(name)])
        write_map(name, rng, args.out_dir)


if __name__ == "__main__":
    main()

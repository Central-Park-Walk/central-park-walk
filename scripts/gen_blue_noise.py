#!/usr/bin/env python3
"""Generate a tileable blue-noise dither texture (void-and-cluster, Ulichney 1993).

Central Park Walk uses a screen-space ordered dither to cross-fade the lod0 tree
mesh into its far impostor over the 40-80 m band (shaders/include/lod_dither.gdshaderinc).
That dither was Interleaved Gradient Noise, designed to be resolved by TAA into smooth
alpha. TAA is force-off under FSR2 (main.gd, -4.6 ms), so the static IGN pattern reads
as a regular diagonal "screen-door" net on foliage.

Blue noise is the fix for the *no-temporal* case: void-and-cluster constructs the array
so that EVERY thresholded level is spatially well-distributed (high-frequency, no low-freq
clumps, no regular structure). Thresholding it at the fade fraction therefore gives fine
even film-grain instead of a net — with no dependence on any temporal filter. Generated
with wrap-around energy so the 64x64 tile repeats seamlessly across the screen.

Output: textures/blue_noise_64.png  (8-bit grayscale, the rank/N*N normalised to 0..255).
Sampled in-shader with texelFetch (integer coord % size) so it needs no sampler
filter/repeat hints and returns the exact stored value.

Deterministic (fixed seed) so re-running reproduces the same asset byte-for-byte.
"""
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
import os

N = 64
SIGMA = 1.9          # energy kernel width (Ulichney's ~1.5-1.9 gives good blue noise)
INIT_FRACTION = 0.1  # initial minority-pixel density before the ranking phases
SEED = 20260704

OUT = os.path.join(os.path.dirname(__file__), "..", "textures", "blue_noise_64.png")


def energy(binary: np.ndarray) -> np.ndarray:
    # Toroidal Gaussian filter => the pattern is seamlessly tileable.
    return gaussian_filter(binary.astype(np.float64), sigma=SIGMA, mode="wrap")


def tightest_cluster(binary, e):
    # Location of the 1-pixel sitting in the densest cluster (max energy among ones).
    masked = np.where(binary.ravel(), e.ravel(), -np.inf)
    return int(np.argmax(masked))


def largest_void(binary, e):
    # Location of the 0-pixel sitting in the largest void (min energy among zeros).
    masked = np.where(~binary.ravel(), e.ravel(), np.inf)
    return int(np.argmin(masked))


def main():
    rng = np.random.default_rng(SEED)
    binary = np.zeros((N, N), dtype=bool)
    num_init = int(INIT_FRACTION * N * N)
    binary.ravel()[rng.choice(N * N, size=num_init, replace=False)] = True

    # --- Relax the initial pattern into a blue-noise prototype ------------------
    # Repeatedly move the tightest cluster's pixel into the largest void until stable.
    for _ in range(10 * N * N):
        e = energy(binary)
        tight = tightest_cluster(binary, e)
        binary.ravel()[tight] = False
        e = energy(binary)
        void = largest_void(binary, e)
        binary.ravel()[void] = True
        if void == tight:
            break

    rank = np.full(N * N, -1, dtype=np.int64)
    ones = int(binary.sum())

    # --- Phase 1: rank the prototype's ones, removing tightest clusters first ----
    b = binary.copy()
    for r in range(ones - 1, -1, -1):
        e = energy(b)
        t = tightest_cluster(b, e)
        b.ravel()[t] = False
        rank[t] = r

    # --- Phase 2: rank the remaining zeros, filling largest voids first ----------
    b = binary.copy()
    for r in range(ones, N * N):
        e = energy(b)
        v = largest_void(b, e)
        b.ravel()[v] = True
        rank[v] = r

    assert (rank >= 0).all(), "every pixel must be ranked"

    # rank in [0, N*N) -> threshold value in [0,255]. Comparing a fade fraction t to
    # (rank/N*N) draws exactly the fraction t of pixels, evenly distributed.
    tex = np.floor(rank.astype(np.float64) / (N * N) * 256.0)
    tex = np.clip(tex, 0, 255).astype(np.uint8).reshape(N, N)

    Image.fromarray(tex, mode="L").save(os.path.normpath(OUT))
    print("wrote", os.path.normpath(OUT),
          "min", int(tex.min()), "max", int(tex.max()), "mean %.1f" % tex.mean())


if __name__ == "__main__":
    main()

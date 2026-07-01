#!/usr/bin/env python3
"""Generate original tileable water normal maps for shaders/water.gdshader.

Two maps, both FFT-synthesized from a directional gravity–capillary wave
spectrum so they tile perfectly and contain no third-party content:
  water_normal_a.png — fine capillary ripples, wide directional spread
  water_normal_b.png — larger gravity wavelets, tighter directional spread

The shader scrolls the two maps at different speeds/directions (wind-biased)
and blends the normals, which reads as pond surface ripple instead of the old
value-noise swirl.

Usage: python3 scripts/gen_water_normals.py   (writes into textures/)
"""

import numpy as np
from PIL import Image
from pathlib import Path

SIZE = 512
OUT_DIR = Path(__file__).resolve().parent.parent / "textures"


def wave_heightfield(size: int, seed: int, peak_wavelength_px: float,
                     directionality: float, wind_angle: float) -> np.ndarray:
    """Tileable heightfield from a Phillips-like directional spectrum.

    peak_wavelength_px: wavelength (in pixels) where the spectrum peaks.
    directionality: exponent on |k̂·ŵ| — higher = waves more aligned to wind.
    """
    rng = np.random.default_rng(seed)
    k1 = np.fft.fftfreq(size) * size          # integer wavenumbers
    kx, ky = np.meshgrid(k1, k1)
    k = np.hypot(kx, ky)
    k[0, 0] = 1.0                              # avoid /0; DC zeroed below

    # Phillips-style: suppress waves longer than the peak, roll off short ones
    kp = size / peak_wavelength_px
    spectrum = np.exp(-(kp / k) ** 2) / k ** 4

    # Directional spread about the wind direction
    wx, wy = np.cos(wind_angle), np.sin(wind_angle)
    cos_kw = (kx * wx + ky * wy) / k
    spectrum *= np.abs(cos_kw) ** directionality

    # Random phases, hermitian not required — take real part of IFFT
    phases = rng.uniform(0.0, 2.0 * np.pi, (size, size))
    field = np.fft.ifft2(np.sqrt(spectrum) * np.exp(1j * phases)).real
    field[0, 0] = 0.0
    field -= field.mean()
    field /= np.abs(field).max()
    return field


def height_to_normal_map(h: np.ndarray, strength: float) -> np.ndarray:
    """Tangent-space normal map (RG=XY, B=Z), wrap-aware gradients."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength
    n = np.stack([-dx, -dy, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgb = ((n * 0.5 + 0.5) * 255.0).round().clip(0, 255).astype(np.uint8)
    return rgb


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    # A: fine capillary ripple, wide spread (choppy pond texture)
    ha = wave_heightfield(SIZE, seed=20260701, peak_wavelength_px=28.0,
                          directionality=2.0, wind_angle=0.35)
    # B: broader wavelets, more directional (drifting wind rows)
    hb = wave_heightfield(SIZE, seed=8451923, peak_wavelength_px=90.0,
                          directionality=6.0, wind_angle=-0.20)
    for name, field, strength in (("water_normal_a", ha, 10.0),
                                  ("water_normal_b", hb, 7.0)):
        rgb = height_to_normal_map(field, strength)
        path = OUT_DIR / f"{name}.png"
        Image.fromarray(rgb, "RGB").save(path)
        print(f"wrote {path} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()

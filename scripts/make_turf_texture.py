"""Generate a top-down TURF texture for the Terrain3D grass slot.

The previous grass_albedo_height.png was flat pale speckle with NO blade
structure — at the 13 m tiling it read as painted felt, which is why fantasy
mode threw it away for a flat colour (equally lifeless). This builds a real
lawn-from-above texture: thousands of individual blade strokes, z-tested so
taller blades occlude shorter ones, over a dark-green understory so any gaps
read as shadowed grass base rather than brown dirt.

Outputs (seamless, tile small ~2 m via uv_scale 1.0 in save_terrain3d_assets):
  textures/terrain3d/grass_albedo_height.png   RGB blade colour + A height
  textures/terrain3d/grass_normal_rough.png    RGB tangent normal + A roughness

The texture is deliberately a NEUTRAL mid-green carrying luminance/relief
detail only — the terrain shader recolours it per zone (spectral palette) or to
the lush fantasy green, preserving this blade detail as a multiplier. So the
colour here just needs natural green variation; the VALUE structure is the
asset. Run: python3 scripts/make_turf_texture.py
"""

import os
import numpy as np
from PIL import Image

SIZE = 1024
N_BLADES = 46000
SEED = 7

rng = np.random.default_rng(SEED)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "textures", "terrain3d")


def value_noise(size, scale, seed):
    """Tileable smooth value noise in [0,1] at the given cell scale."""
    cells = max(2, int(round(size / scale)))
    g = np.random.default_rng(seed).random((cells, cells))
    # wrap a row/col for seamless bilinear interpolation
    g = np.pad(g, ((0, 1), (0, 1)), mode="wrap")
    ys = np.linspace(0, cells, size, endpoint=False)
    xs = np.linspace(0, cells, size, endpoint=False)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    # smoothstep
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    g00 = g[np.ix_(y0, x0)]; g10 = g[np.ix_(y0 + 1, x0)]
    g01 = g[np.ix_(y0, x0 + 1)]; g11 = g[np.ix_(y0 + 1, x0 + 1)]
    top = g00 * (1 - fx) + g01 * fx
    bot = g10 * (1 - fx) + g11 * fx
    return top * (1 - fy) + bot * fy


# Blade colour palette (linear-ish sRGB 0..1). Neutral mid-greens with a few
# dry/yellow blades; the shader handles final hue, so keep these natural.
PALETTE = np.array([
    [0.16, 0.40, 0.13],   # standard green
    [0.20, 0.46, 0.15],
    [0.28, 0.54, 0.18],   # lighter vigorous
    [0.11, 0.29, 0.10],   # deep shade green
    [0.34, 0.52, 0.20],   # light yellow-green
    [0.46, 0.46, 0.18],   # dry straw (rare)
])
PAL_W = np.array([0.30, 0.26, 0.18, 0.14, 0.09, 0.03])
PAL_W /= PAL_W.sum()

# Understory: dark green so gaps look like shadowed base, never dirt.
SOIL = np.array([0.055, 0.115, 0.050])


def build():
    # Flow field: low-frequency angle so blades clump into cowlicks/swirls.
    flow = value_noise(SIZE, 180.0, SEED + 11) * 2.0 * np.pi
    # Understory mottle.
    soil_mot = (value_noise(SIZE, 60.0, SEED + 3) * 0.5
                + value_noise(SIZE, 18.0, SEED + 4) * 0.5)

    color = (SOIL[None, None, :] * (0.7 + 0.6 * soil_mot[:, :, None])).astype(np.float32)
    color = np.clip(color, 0, 1)
    zbuf = np.zeros((SIZE, SIZE), np.float32)        # blade height (0=soil)
    rough = np.full((SIZE, SIZE), 0.90, np.float32)

    color_f = color.reshape(-1, 3)
    z_f = zbuf.reshape(-1)
    r_f = rough.reshape(-1)

    pal_idx = rng.choice(len(PALETTE), size=N_BLADES, p=PAL_W)
    bx = rng.random(N_BLADES) * SIZE
    by = rng.random(N_BLADES) * SIZE
    lengths = rng.uniform(9.0, 22.0, N_BLADES)
    halfw = rng.uniform(0.9, 1.9, N_BLADES)
    ang_jit = rng.normal(0, 0.55, N_BLADES)
    curve = rng.normal(0, 0.5, N_BLADES)
    base_elev = rng.uniform(0.12, 0.34, N_BLADES)
    tip_gain = rng.uniform(0.34, 0.66, N_BLADES)
    bright = rng.uniform(0.80, 1.06, N_BLADES)

    for i in range(N_BLADES):
        x0 = bx[i]; y0 = by[i]
        ang = flow[int(y0) % SIZE, int(x0) % SIZE] + ang_jit[i]
        dx, dy = np.cos(ang), np.sin(ang)
        px_, py_ = -dy, dx                            # perpendicular
        L = lengths[i]
        nseg = max(4, int(L))
        t = np.linspace(0.0, 1.0, nseg)
        # slight parabolic curve along perpendicular
        cur = curve[i] * (t * t) * L * 0.12
        cx = x0 + dx * L * t + px_ * cur
        cy = y0 + dy * L * t + py_ * cur
        # width tapers base->tip; sample across width
        wt = halfw[i] * (1.0 - 0.85 * t)
        offs = np.array([-1.0, -0.4, 0.4, 1.0])
        ox = (cx[:, None] + px_ * (offs[None, :] * wt[:, None])).reshape(-1)
        oy = (cy[:, None] + py_ * (offs[None, :] * wt[:, None])).reshape(-1)
        # height + shade vary along length (repeat per width sample)
        h = (base_elev[i] + tip_gain[i] * t)[:, None].repeat(len(offs), 1).reshape(-1)
        shade = (0.52 + 0.50 * t)[:, None].repeat(len(offs), 1).reshape(-1)
        col = PALETTE[pal_idx[i]] * bright[i]
        cols = np.clip(col[None, :] * shade[:, None], 0, 1)
        rg = 0.80 - 0.10 * (h > 0.6)                   # tips a touch glossier

        ix = (np.round(ox).astype(np.int64) % SIZE)
        iy = (np.round(oy).astype(np.int64) % SIZE)
        flat = iy * SIZE + ix
        # write tallest-last so fancy-index keeps the max within this blade
        order = np.argsort(h, kind="stable")
        flat = flat[order]; h = h[order]; cols = cols[order]; rg = rg[order]
        m = h > z_f[flat]
        sel = flat[m]
        z_f[sel] = h[m]
        color_f[sel] = cols[m]
        r_f[sel] = rg[m]

    # ---- Albedo + height ----
    alb = np.clip(color.reshape(SIZE, SIZE, 3), 0, 1)
    height = np.clip(zbuf / max(1e-3, zbuf.max()), 0, 1)
    # gamma the height a little so blade tips dominate the blend
    height = height ** 0.85
    albedo_rgba = np.dstack([alb, height]).astype(np.float32)

    # ---- Normal from height (Sobel), tangent space, +Z up ----
    hb = zbuf
    # wrap-aware gradient
    gx = (np.roll(hb, -1, 1) - np.roll(hb, 1, 1)) * 0.5
    gy = (np.roll(hb, -1, 0) - np.roll(hb, 1, 0)) * 0.5
    strength = 2.6
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(hb)
    nl = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= nl; ny /= nl; nz /= nl
    normal = np.dstack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5])
    normal_rgba = np.dstack([normal, rough]).astype(np.float32)

    os.makedirs(OUT_DIR, exist_ok=True)
    Image.fromarray((albedo_rgba * 255).astype(np.uint8), "RGBA").save(
        os.path.join(OUT_DIR, "grass_albedo_height.png"))
    Image.fromarray((normal_rgba * 255).astype(np.uint8), "RGBA").save(
        os.path.join(OUT_DIR, "grass_normal_rough.png"))

    luma = float((alb * np.array([0.299, 0.587, 0.114])).sum(2).mean())
    cover = float((zbuf > 0).mean())
    print("turf texture written to %s" % OUT_DIR)
    print("  mean albedo luma = %.3f   blade coverage = %.1f%%" % (luma, cover * 100))


if __name__ == "__main__":
    build()

"""Draw a grass-CLUMP card texture (RGBA) — the fill primitive for the card-based
grass. One quad wears this texture and shows ~40-70 blades, so the mid-field fills
densely for ~2 triangles instead of hundreds of blade meshes.

Side-on view of a clump: many fine curved blades fanning up from a shared base,
tapering to soft tips, dark shadowed base -> bright warm tips, a few straw blades.
Alpha = the blade silhouette. RGB carries a luminance/colour ramp that the in-game
card shader modulates against the shared grass-colour field (so it stays seasonal
and matches the terrain), exactly like the blade shader does.

Supersampled x2 then box-downscaled for clean anti-aliased alpha edges.

Run: python3 scripts/make_grass_clump_card.py
"""

import os
import math
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_DIR, "textures", "grass")
os.makedirs(OUT_DIR, exist_ok=True)

RES = 1024          # final card resolution
SS = 2              # supersample factor
W = H = RES * SS

# RGBA float accumulation buffers (premultiplied-ish: we composite blades over).
rgb = np.zeros((H, W, 3), np.float32)
alpha = np.zeros((H, W), np.float32)

rng = np.random.default_rng(7)


def blade_color(t, straw, vitality):
    """t: 0 base .. 1 tip. Returns rgb 0..1 — dark cool base to bright warm tip."""
    base = np.array([0.24, 0.36, 0.15])
    tip = np.array([0.62, 0.80, 0.34])
    c = base * (1.0 - t) + tip * t
    if straw:
        s = np.array([0.68, 0.60, 0.32])
        c = c * 0.3 + s * 0.7
    return np.clip(c * vitality, 0.0, 1.0)


def stamp_tri(p0, p1, p2, color):
    """Rasterise a filled triangle into rgb/alpha with a small AA via bbox coverage."""
    xs = np.array([p0[0], p1[0], p2[0]])
    ys = np.array([p0[1], p1[1], p2[1]])
    x0, x1 = int(math.floor(xs.min())), int(math.ceil(xs.max()))
    y0, y1 = int(math.floor(ys.min())), int(math.ceil(ys.max()))
    x0 = max(0, x0); y0 = max(0, y0); x1 = min(W - 1, x1); y1 = min(H - 1, y1)
    if x1 <= x0 or y1 <= y0:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
    # barycentric
    d = (p1[1] - p2[1]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[1] - p2[1])
    if abs(d) < 1e-6:
        return
    a = ((p1[1] - p2[1]) * (gx - p2[0]) + (p2[0] - p1[0]) * (gy - p2[1])) / d
    b = ((p2[1] - p0[1]) * (gx - p2[0]) + (p0[0] - p2[0]) * (gy - p2[1])) / d
    c = 1.0 - a - b
    mask = (a >= 0) & (b >= 0) & (c >= 0)
    if not mask.any():
        return
    sub = (slice(y0, y1 + 1), slice(x0, x1 + 1))
    m = mask
    # blades drawn base-first; later (front) blades overwrite -> simple over
    alpha[sub][m] = 1.0
    rgb[sub][m] = color


def draw_blade(bx, by, length, lean, curl, width0, straw, vitality, segs=14):
    """A curved tapered blade from base (bx,by) rising with lean + tip curl."""
    ang = lean                      # radians from vertical (+ = lean right)
    x, y = bx, by
    left_prev = right_prev = None
    seg_len = length / segs
    for i in range(segs + 1):
        t = i / segs
        w = width0 * (1.0 - t) ** 0.7 * SS      # taper to a point
        # perpendicular to heading
        hx, hy = math.sin(ang), -math.cos(ang)  # heading (up is -y)
        px, py = -hy, hx                          # perpendicular
        lx, ly = x - px * w, y - py * w
        rx, ry = x + px * w, y + py * w
        if left_prev is not None:
            col = blade_color(t, straw, vitality)
            col255 = col  # store 0..1
            stamp_tri(left_prev, right_prev, (lx, ly), col255)
            stamp_tri(right_prev, (rx, ry), (lx, ly), col255)
        left_prev, right_prev = (lx, ly), (rx, ry)
        # advance
        x += hx * seg_len
        y += hy * seg_len
        ang += curl / segs          # curl the tip over


# --- lay out the clump: a DENSE band of blades filling the card width edge-to-edge
# so many cards tile into a continuous mass. Bases spread evenly (not fanned from a
# centre, which leaves a hollow V); small random leans both ways; back rows shorter
# and darker so the mass has depth. Drawn back-to-front (short/back first). ---
N_BLADES = 150
base_y = H * 0.99
order = sorted(range(N_BLADES), key=lambda _: rng.random())
for i in order:
    bx = (0.015 + 0.97 * rng.random()) * W          # even across full width
    by = base_y - rng.random() * H * 0.03
    lean = (rng.random() - 0.5) * 0.9               # small random tilt both ways
    length = H * (0.42 + rng.random() * 0.52)        # varied heights -> natural top
    # tips curl in the lean direction; a few flop over more
    curl = (0.45 + rng.random() * 1.1) * (1.0 if lean >= 0 else -1.0)
    width0 = 2.6 + rng.random() * 3.2
    straw = rng.random() < 0.09
    # back rows (shorter) a bit darker for depth
    vitality = (0.72 + rng.random() * 0.28) * (0.85 + 0.15 * (length / (H * 0.94)))
    draw_blade(bx, by, length, lean, curl, width0, straw, vitality)

# --- composite -> downscale for AA ---
out = np.zeros((H, W, 4), np.float32)
out[..., :3] = np.clip(rgb, 0, 1)
out[..., 3] = np.clip(alpha, 0, 1)
img = Image.fromarray((out * 255).astype(np.uint8), "RGBA")
img = img.resize((RES, RES), Image.LANCZOS)

# hard-ish alpha (avoid a grey halo) but keep edge AA
arr = np.array(img).astype(np.float32)
a = arr[..., 3] / 255.0
a = np.clip((a - 0.25) / 0.5, 0, 1)   # tighten cutout
arr[..., 3] = a * 255.0
Image.fromarray(arr.astype(np.uint8), "RGBA").save(os.path.join(OUT_DIR, "clump_card.png"))
# opaque preview on mid-grey to eyeball the blades
prev = np.array(img).astype(np.float32)
bg = np.full((RES, RES, 3), 90.0)
af = (prev[..., 3:4] / 255.0)
comp = prev[..., :3] * af + bg * (1 - af)
Image.fromarray(comp.astype(np.uint8), "RGB").save(os.path.join(OUT_DIR, "clump_card_preview.png"))
print("wrote", os.path.join(OUT_DIR, "clump_card.png"))

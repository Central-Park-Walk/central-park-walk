"""Generate leaf CLUSTER textures for undergrowth species.

Instead of single-leaf textures (which look like clip art on flat cards),
this generates clusters of 5-8 overlapping leaves on a twig segment.
Each cluster texture is 512x512 RGBA with proper alpha cutout.

These textures go on larger cards (~20cm) arranged in volumetric clusters,
matching the tree foliage card approach that actually works.

Colors derived from spectral reflectance pipeline (scripts/spectral_colors.py):
    R(λ) × CIE 1931 × D65 → sRGB

Run: python3 scripts/vegetation/gen_cluster_textures.py
"""

import math
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
OUT_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Leaf drawing primitives
# ---------------------------------------------------------------------------

def _leaf_outline(n_points, half_l, half_w, lcx, lcy, serration, rng):
    """Build a natural leaf outline with optional serration."""
    outline = []
    for i in range(n_points):
        t = i / n_points
        if t < 0.5:
            s = t * 2
            # Asymmetric width profile: widest at ~35-45%, natural variation
            peak = 0.38 + rng.uniform(-0.04, 0.04)
            if s < peak:
                w = math.sin(s / peak * math.pi / 2)
            else:
                w = math.cos((s - peak) / (1 - peak) * math.pi / 2) * 0.95 + 0.05
            w *= (1.0 - 0.25 * s)  # taper toward tip
            if serration > 0 and 0.08 < s < 0.92:
                tooth = math.sin(s * math.pi * (7 + serration * 7)) * serration * 0.12
                w *= (1.0 + tooth)
            # Slight natural asymmetry
            w *= 1.0 + rng.uniform(-0.03, 0.03)
            outline.append((lcx + half_w * w, lcy - half_l + s * half_l * 2))
        else:
            s = (t - 0.5) * 2
            peak = 0.38 + rng.uniform(-0.04, 0.04)
            rs = 1.0 - s
            if rs < peak:
                w = math.sin(rs / peak * math.pi / 2)
            else:
                w = math.cos((rs - peak) / (1 - peak) * math.pi / 2) * 0.95 + 0.05
            w *= (1.0 - 0.25 * rs)
            if serration > 0 and 0.08 < rs < 0.92:
                tooth = math.sin(rs * math.pi * (7 + serration * 7)) * serration * 0.12
                w *= (1.0 + tooth)
            w *= 1.0 + rng.uniform(-0.03, 0.03)
            outline.append((lcx - half_w * w, lcy + half_l - s * half_l * 2))
    return outline


def draw_single_leaf(img, cx, cy, length, width, angle, color, vein_color,
                     serration=0, backlit=False, rng=None):
    """Draw one leaf with natural gradients, translucency, and subtle veins.

    Args:
        img: RGBA PIL Image
        cx, cy: center position
        length, width: leaf dimensions in pixels
        angle: rotation in radians
        color: (r, g, b) base color (spectral pipeline sRGB)
        vein_color: (r, g, b) vein color
        serration: 0-1, edge serration amount
        backlit: if True, leaf appears translucent (warmer, brighter)
        rng: random.Random instance
    """
    if rng is None:
        rng = random.Random()

    pad = int(max(length, width) * 1.6)
    leaf_img = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
    draw = ImageDraw.Draw(leaf_img)

    lcx, lcy = pad // 2, pad // 2
    half_l = length // 2
    half_w = width // 2

    outline = _leaf_outline(48, half_l, half_w, lcx, lcy, serration, rng)

    # --- Per-leaf color variation ---
    r, g, b = color
    # Age/health variation: young leaves lighter+yellower, old leaves darker
    age = rng.uniform(-0.12, 0.12)
    base_r = max(0, min(255, int(r * (1.0 + age * 0.8 + rng.uniform(-0.03, 0.03)))))
    base_g = max(0, min(255, int(g * (1.0 + age * 0.5 + rng.uniform(-0.02, 0.02)))))
    base_b = max(0, min(255, int(b * (1.0 + age * 0.3 + rng.uniform(-0.02, 0.02)))))

    if backlit:
        # Translucent: warmer, lighter — simulates light passing through
        base_r = min(255, int(base_r * 1.25 + 12))
        base_g = min(255, int(base_g * 1.15 + 8))
        base_b = max(0, int(base_b * 0.85))

    # Fill with base color
    draw.polygon(outline, fill=(base_r, base_g, base_b, 255))

    # --- Surface gradients using numpy (fast) ---
    arr = np.array(leaf_img)
    alpha_mask = arr[:, :, 3] > 0

    # Coordinate grids relative to leaf center
    ys, xs = np.mgrid[0:pad, 0:pad]
    dx = (xs - lcx).astype(np.float32) / max(half_w, 1)  # -1..1 across width
    dy = (ys - lcy).astype(np.float32) / max(half_l, 1)  # -1..1 base to tip

    # 1) Base-to-tip gradient: slight lightening toward tip (younger tissue)
    tip_grad = np.clip(dy * 0.5 + 0.5, 0, 1)  # 0 at base, 1 at tip
    tip_factor = 1.0 - tip_grad * 0.06  # darken slightly at tip (mature)

    # 2) Midrib translucency: lighter near center vein (light penetrates there)
    midrib_dist = np.abs(dx)
    midrib_factor = 1.0 + (1.0 - np.clip(midrib_dist * 2.5, 0, 1)) * 0.08

    # 3) Edge darkening: cuticle/shadow at margins
    edge_dist = np.sqrt(dx**2 * 0.7 + dy**2 * 0.3)
    edge_factor = 1.0 - np.clip(edge_dist - 0.5, 0, 1) * 0.2

    # 4) Micro-noise: cellular variation
    noise = np.random.RandomState(rng.randint(0, 2**31)).uniform(
        -0.025, 0.025, (pad, pad)).astype(np.float32)

    # Combined factor
    factor = tip_factor * midrib_factor * edge_factor + noise
    factor = np.clip(factor, 0.75, 1.25)

    # Apply to RGB channels where alpha > 0
    for c in range(3):
        channel = arr[:, :, c].astype(np.float32)
        channel[alpha_mask] *= factor[alpha_mask]
        arr[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

    # --- Edge alpha softening: 1px soft edge for natural look ---
    # Erode the alpha slightly, then blur for a gradient edge
    alpha_f = arr[:, :, 3].astype(np.float32)
    # Simple edge detection: pixels adjacent to transparent
    from scipy.ndimage import binary_erosion, gaussian_filter
    interior = binary_erosion(alpha_mask, iterations=1)
    edge_band = alpha_mask & ~interior
    alpha_f[edge_band] *= 0.5  # semi-transparent edge pixels
    alpha_f = gaussian_filter(alpha_f, sigma=0.6)
    arr[:, :, 3] = np.clip(alpha_f, 0, 255).astype(np.uint8)

    leaf_img = Image.fromarray(arr)
    draw = ImageDraw.Draw(leaf_img)

    # --- Veins: subtle, close to base color ---
    vr, vg, vb = vein_color
    # Midrib: thin, semi-transparent
    midrib_w = max(1, width // 40)
    midrib_start = (lcx, lcy - half_l + int(length * 0.06))
    midrib_end = (lcx, lcy + half_l - int(length * 0.03))
    draw.line([midrib_start, midrib_end], fill=(vr, vg, vb, 100), width=midrib_w)

    # Secondary veins: 5-7 pairs, very subtle
    n_veins = rng.randint(5, 7)
    for vi in range(n_veins):
        vt = 0.12 + (vi / n_veins) * 0.72
        vy = lcy - half_l + int(vt * length)
        vein_len = half_w * rng.uniform(0.55, 0.85)
        vein_ang = rng.uniform(0.35, 0.75)
        vein_alpha = rng.randint(50, 80)
        # Right
        vex = lcx + int(vein_len * math.cos(vein_ang))
        vey = vy - int(vein_len * math.sin(vein_ang) * 0.35)
        draw.line([(lcx, vy), (vex, vey)], fill=(vr, vg, vb, vein_alpha), width=1)
        # Left (mirror)
        lex = lcx - int(vein_len * math.cos(vein_ang))
        ley = vy - int(vein_len * math.sin(vein_ang) * 0.35)
        draw.line([(lcx, vy), (lex, ley)], fill=(vr, vg, vb, vein_alpha), width=1)

    # --- Natural imperfections ---
    # Insect damage: small holes (transparent)
    if rng.random() < 0.35:
        n_holes = rng.randint(1, 2)
        for _ in range(n_holes):
            hx = rng.randint(lcx - half_w // 3, lcx + half_w // 3)
            hy = rng.randint(lcy - half_l // 3, lcy + half_l // 3)
            hr = rng.randint(2, max(3, width // 20))
            draw.ellipse([(hx-hr, hy-hr), (hx+hr, hy+hr)], fill=(0, 0, 0, 0))

    # Brown spots / aging
    n_spots = rng.randint(0, 2)
    for _ in range(n_spots):
        sx = rng.randint(lcx - half_w // 2, lcx + half_w // 2)
        sy = rng.randint(lcy - half_l // 2, lcy + half_l // 2)
        sr = rng.randint(2, max(3, width // 18))
        spot_a = rng.randint(30, 70)
        draw.ellipse([(sx-sr, sy-sr), (sx+sr, sy+sr)],
                     fill=(rng.randint(70, 100), rng.randint(55, 75),
                           rng.randint(15, 35), spot_a))

    # Anti-alias blur
    leaf_img = leaf_img.filter(ImageFilter.GaussianBlur(radius=0.4))

    # Rotate and paste
    leaf_img = leaf_img.rotate(-math.degrees(angle), resample=Image.BICUBIC, expand=False)
    img.alpha_composite(leaf_img, (cx - pad // 2, cy - pad // 2))


def draw_twig(img, x0, y0, x1, y1, thickness, color):
    """Draw a twig/petiole line with slight taper."""
    draw = ImageDraw.Draw(img)
    draw.line([(x0, y0), (x1, y1)], fill=color + (200,), width=max(1, thickness))


def generate_cluster_texture(species_name, config, size=512):
    """Generate a leaf cluster texture.

    config dict:
        leaf_color: (r, g, b) base leaf color (spectral sRGB)
        vein_color: (r, g, b) vein color (subtle, close to base)
        twig_color: (r, g, b) twig/stem color
        leaf_length: pixels (at 512 scale)
        leaf_width: pixels (at 512 scale)
        n_leaves: number of leaves in cluster
        serration: 0-1
        arrangement: 'alternate', 'opposite', 'whorled', 'basal'
        backlit_ratio: fraction of leaves rendered as backlit (0-1)
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rng = random.Random(hash(species_name) & 0xFFFFFFFF)

    leaf_color = config["leaf_color"]
    vein_color = config.get("vein_color", tuple(min(255, c + 15) for c in leaf_color))
    twig_color = config.get("twig_color", (90, 70, 45))
    leaf_len = config.get("leaf_length", 120)
    leaf_wid = config.get("leaf_width", 70)
    n_leaves = config.get("n_leaves", 6)
    serration = config.get("serration", 0)
    arrangement = config.get("arrangement", "alternate")
    backlit_ratio = config.get("backlit_ratio", 0.25)

    cx, cy = size // 2, size // 2

    # Draw central twig with slight curve
    twig_start = (cx + rng.randint(-3, 3), cy + size // 3)
    twig_end = (cx + rng.randint(-5, 5), cy - size // 3)
    draw_twig(img, twig_start[0], twig_start[1], twig_end[0], twig_end[1],
              max(2, size // 130), twig_color)

    # Place leaves — draw back-to-front for natural overlap
    leaf_params = []
    for i in range(n_leaves):
        if arrangement == "alternate":
            t = 0.10 + (i / n_leaves) * 0.75
            side = 1 if i % 2 == 0 else -1
            ly = int(cy + size // 3 - t * (size * 2 // 3))
            lx = cx + side * rng.randint(leaf_wid // 4, int(leaf_wid * 0.9))
            angle = side * rng.uniform(0.25, 0.85)
        elif arrangement == "opposite":
            pair_idx = i // 2
            side = 1 if i % 2 == 0 else -1
            t = 0.15 + (pair_idx / max(1, n_leaves // 2)) * 0.65
            ly = int(cy + size // 3 - t * (size * 2 // 3))
            lx = cx + side * rng.randint(leaf_wid // 3, leaf_wid)
            angle = side * rng.uniform(0.35, 0.75)
        elif arrangement == "whorled":
            whorl_idx = i // 3
            in_whorl = i % 3
            t = 0.2 + (whorl_idx / max(1, n_leaves // 3)) * 0.6
            ly = int(cy + size // 3 - t * (size * 2 // 3))
            whorl_angle = (in_whorl / 3) * math.pi * 2 + rng.uniform(-0.2, 0.2)
            lx = cx + int(math.cos(whorl_angle) * leaf_wid * 0.8)
            ly += int(math.sin(whorl_angle) * leaf_wid * 0.3)
            angle = whorl_angle - math.pi / 2
        else:  # basal / rosette
            angle_around = (i / n_leaves) * math.pi * 2 + rng.uniform(-0.2, 0.2)
            dist = rng.uniform(leaf_len * 0.3, leaf_len * 0.6)
            lx = cx + int(math.cos(angle_around) * dist)
            ly = cy + int(math.sin(angle_around) * dist * 0.5)
            angle = angle_around - math.pi / 2

        # Petiole from twig to leaf base
        petiole_y = ly
        draw_twig(img, cx, petiole_y, lx, ly, max(1, size // 220), twig_color)

        # Per-leaf size variation (more varied than before)
        this_len = int(leaf_len * rng.uniform(0.65, 1.25))
        this_wid = int(leaf_wid * rng.uniform(0.70, 1.20))

        # Decide if backlit
        is_backlit = rng.random() < backlit_ratio

        leaf_params.append((lx, ly, this_len, this_wid, angle, is_backlit))

    # Per-leaf color variation + draw
    for lx, ly, this_len, this_wid, angle, is_backlit in leaf_params:
        draw_single_leaf(img, lx, ly, this_len, this_wid, angle,
                         leaf_color, vein_color, serration=serration,
                         backlit=is_backlit, rng=rng)

    # Final cohesion pass: very gentle blur on RGB only, preserve alpha edges
    rgb = img.convert("RGB")
    alpha = img.getchannel("A")
    rgb = rgb.filter(ImageFilter.GaussianBlur(radius=0.5))
    img = Image.merge("RGBA", (*rgb.split(), alpha))

    return img


# ---------------------------------------------------------------------------
# Species definitions — colors from spectral reflectance pipeline
# (scripts/spectral_colors.py: CIE 1931 + D65 → sRGB)
# ---------------------------------------------------------------------------

# Spicebush (Lindera benzoin): dominant CP understory shrub
# Spectral RGB8: (77, 116, 62) — shade-adapted broadleaf
SPICEBUSH = {
    "leaf_color": (77, 116, 62),       # spectral pipeline output
    "vein_color": (88, 126, 72),       # subtle — just slightly lighter
    "twig_color": (85, 72, 48),        # olive-brown
    "leaf_length": 125,                # ~12.5cm at 512px
    "leaf_width": 60,                  # ~6cm, ovate-elliptic
    "n_leaves": 8,                     # denser cluster
    "serration": 0,                    # entire margins
    "arrangement": "alternate",
    "backlit_ratio": 0.30,             # 30% of leaves show translucency
}


def main():
    print("Generating cluster textures...")

    # Generate 1 cluster texture per model variant (3 variants)
    # Named cluster_Shrub_Spicebush_{variant}_v0.png to match finalize_and_export lookup
    for variant in range(3):
        name = f"cluster_Shrub_Spicebush_{variant}_v0"
        config = dict(SPICEBUSH)
        # Per-variant: slight color shift + different seed
        v_rng = random.Random(variant * 37 + 11)
        config["leaf_color"] = tuple(
            max(0, min(255, c + v_rng.randint(-6, 6)))
            for c in SPICEBUSH["leaf_color"]
        )
        img = generate_cluster_texture(name, config)
        path = os.path.join(OUT_DIR, f"{name}.png")
        img.save(path)
        print(f"  Saved {path} ({img.size[0]}x{img.size[1]})")

    print("Done.")


if __name__ == "__main__":
    main()

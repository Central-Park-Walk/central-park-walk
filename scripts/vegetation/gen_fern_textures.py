"""Generate fern pinna textures for each species.

Creates PNG textures with alpha for use as leaf cards in 3D fern models.
Each texture shows a single pinna (leaflet) with species-correct shape.

Run: python3 scripts/vegetation/gen_fern_textures.py
"""

import math
import random
import os
from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TEX_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")


def _draw_vein(draw, x0, y0, x1, y1, color, width=1):
    """Draw a slightly curved vein line."""
    steps = 12
    mx = (x0 + x1) / 2 + random.uniform(-3, 3)
    my = (y0 + y1) / 2 + random.uniform(-2, 2)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        # Quadratic bezier through midpoint
        px = (1-t)**2 * x0 + 2*(1-t)*t * mx + t**2 * x1
        py = (1-t)**2 * y0 + 2*(1-t)*t * my + t**2 * y1
        pts.append((px, py))
    draw.line(pts, fill=color, width=width)


def make_christmas_fern_pinna(size=(256, 384)):
    """Christmas Fern (Polystichum acrostichoides) pinna.

    Once-pinnate, lanceolate with characteristic auricle ("boot" shape).
    Dark green, glossy, leathery. Bristle-tipped teeth on margin.
    The auricle is on the acroscopic side (toward frond tip).
    """
    W, H = size
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(42)

    cx = W * 0.48  # slightly off-center to make room for auricle

    # Define pinna outline — boot/auricle shape
    # Base at bottom, tip at top
    # Auricle protrudes on the RIGHT side near the base
    outline = []
    n_pts = 40
    for i in range(n_pts):
        t = i / (n_pts - 1)  # 0=base, 1=tip

        # Base width profile: widest below mid, taper both ends
        # Christmas fern pinnae are widest in the lower third
        if t < 0.15:
            # Base taper-in
            w = 0.3 + t * 3.5
        elif t < 0.4:
            # Widest zone
            w = 0.82 + 0.18 * math.sin((t - 0.15) / 0.25 * math.pi * 0.5)
        else:
            # Upper taper to acute tip
            w = 1.0 * (1.0 - (t - 0.4) / 0.6) ** 0.7

        w *= 0.42  # scale to fraction of image width

        # Auricle: extra width on right side at base
        auricle = 0.0
        if t < 0.25:
            auricle = 0.12 * math.sin(t / 0.25 * math.pi) ** 0.6

        # Bristle-tip serrations (small teeth along margin)
        tooth = 0.0
        if 0.1 < t < 0.95:
            tooth_phase = t * 28
            tooth = 0.015 * max(0, math.sin(tooth_phase * math.pi))

        left_x = cx - (w + tooth) * W
        right_x = cx + (w + tooth + auricle) * W

        outline.append((t, left_x, right_x))

    # Build polygon points (go up left side, then down right side)
    poly = []
    for t, lx, rx in outline:
        y = H - t * (H - 20) - 10
        poly.append((lx, y))
    for t, lx, rx in reversed(outline):
        y = H - t * (H - 20) - 10
        poly.append((rx, y))

    # Draw filled pinna shape
    # Bright enough to survive the shader's EGTTR grading
    # (55% desaturation, ×0.82 brightness, shadow lift)
    base_green = (65, 155, 50)
    draw.polygon(poly, fill=(*base_green, 255))

    # Add natural color variation with noise
    pixels = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = pixels[x, y]
            if a > 0:
                # Distance from center for subtle edge darkening
                t_along = 1.0 - y / H  # 0=base, 1=tip
                dist_from_mid = abs(x - cx) / (W * 0.5)

                # Noise for natural variation
                nx = rng.gauss(0, 4)
                ny = rng.gauss(0, 3)

                # Slight glossy highlight near center
                highlight = max(0, 1.0 - dist_from_mid * 1.8) * 0.15

                # Darken edges slightly
                edge_dark = dist_from_mid * 0.1

                # Vein brightening near midline
                vein_bright = max(0, 1.0 - abs(x - cx) / 8) * 0.08

                r2 = int(min(255, max(0, r + nx + (highlight - edge_dark + vein_bright) * 40)))
                g2 = int(min(255, max(0, g + ny + (highlight - edge_dark + vein_bright) * 55)))
                b2 = int(min(255, max(0, b + nx * 0.5 - edge_dark * 12)))

                pixels[x, y] = (r2, g2, b2, a)

    # Draw midvein
    vein_color = (75, 170, 55, 255)
    for y in range(int(H * 0.05), int(H * 0.95)):
        t = 1.0 - y / H
        vx = int(cx + rng.uniform(-0.5, 0.5))
        for dx in range(-1, 2):
            if 0 <= vx + dx < W:
                r, g, b, a = pixels[vx + dx, y]
                if a > 0:
                    pixels[vx + dx, y] = (
                        min(255, r + 5),
                        min(255, g + 12),
                        min(255, b + 3),
                        a
                    )

    # Draw side veins (curved, from midvein to edges)
    for i in range(12):
        t = 0.1 + i * 0.065
        y_start = int(H * (1.0 - t))
        x_start = int(cx)

        # Find edge position at this height
        for _, lx, rx in outline:
            if abs(_ - t) < 0.04:
                # Left vein
                _draw_vein(draw, x_start, y_start,
                          lx + 8, y_start - rng.randint(3, 12),
                          (22, 68, 18, 180), width=1)
                # Right vein
                _draw_vein(draw, x_start, y_start,
                          rx - 8, y_start - rng.randint(3, 12),
                          (22, 68, 18, 180), width=1)
                break

    # Soften edges slightly (1px anti-aliasing)
    alpha = img.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.putalpha(alpha)

    return img


def make_ostrich_fern_pinna(size=(256, 384)):
    """Ostrich Fern (Matteuccia struthiopteris) pinna.

    Deeply pinnatifid (lobed but not fully divided). Lanceolate,
    no auricle. Wider than Christmas fern, more deeply cut.
    Medium bright green, matte.
    """
    W, H = size
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(43)

    cx = W * 0.5

    # Ostrich fern pinnae are deeply lobed with rounded sub-lobes
    outline_left = []
    outline_right = []
    n_lobes = 16

    for i in range(60):
        t = i / 59  # 0=base, 1=tip

        # Width envelope
        if t < 0.1:
            env = t * 7
        elif t < 0.5:
            env = 0.7 + 0.3 * (t - 0.1) / 0.4
        else:
            env = 1.0 * (1.0 - (t - 0.5) / 0.5) ** 0.6

        # Add lobes (sinusoidal indentations)
        lobe_phase = t * n_lobes * math.pi
        lobe_depth = 0.15 * env * (0.3 + 0.7 * min(1, t * 4))
        lobe = lobe_depth * (0.5 + 0.5 * math.cos(lobe_phase))

        w = (env * 0.45 - lobe) * W

        y = H - t * (H - 20) - 10
        outline_left.append((cx - w, y))
        outline_right.append((cx + w, y))

    poly = outline_left + list(reversed(outline_right))

    base_green = (62, 150, 48)
    draw.polygon(poly, fill=(*base_green, 255))

    # Add noise variation
    pixels = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = pixels[x, y]
            if a > 0:
                nx = rng.gauss(0, 5)
                dist = abs(x - cx) / (W * 0.5)
                edge = dist * 0.08
                r2 = int(min(255, max(0, r + nx - edge * 40)))
                g2 = int(min(255, max(0, g + nx + 2 - edge * 50)))
                b2 = int(min(255, max(0, b + nx * 0.3)))
                pixels[x, y] = (r2, g2, b2, a)

    # Midvein
    for y in range(int(H * 0.03), int(H * 0.97)):
        vx = int(cx + rng.uniform(-0.5, 0.5))
        for dx in range(-1, 2):
            if 0 <= vx + dx < W:
                r, g, b, a = pixels[vx + dx, y]
                if a > 0:
                    pixels[vx + dx, y] = (min(255, r + 8), min(255, g + 15), min(255, b + 4), a)

    alpha = img.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.putalpha(alpha)

    return img


def make_cinnamon_fern_pinna(size=(256, 384)):
    """Cinnamon Fern (Osmundastrum cinnamomeum) pinna.

    Similar to ostrich fern but broader, blunter lobes.
    Slightly warm-toned green. Woolly tufts at base (not in texture).
    """
    W, H = size
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(44)

    cx = W * 0.5

    outline_left = []
    outline_right = []
    n_lobes = 14  # fewer, broader lobes than ostrich

    for i in range(60):
        t = i / 59

        if t < 0.08:
            env = t * 8
        elif t < 0.5:
            env = 0.64 + 0.36 * (t - 0.08) / 0.42
        else:
            env = 1.0 * (1.0 - (t - 0.5) / 0.5) ** 0.55

        lobe_phase = t * n_lobes * math.pi
        lobe_depth = 0.12 * env * (0.3 + 0.7 * min(1, t * 5))
        lobe = lobe_depth * (0.5 + 0.5 * math.cos(lobe_phase))

        w = (env * 0.48 - lobe) * W  # slightly wider than ostrich

        y = H - t * (H - 20) - 10
        outline_left.append((cx - w, y))
        outline_right.append((cx + w, y))

    poly = outline_left + list(reversed(outline_right))

    # Slightly warmer green than ostrich
    base_green = (68, 145, 45)
    draw.polygon(poly, fill=(*base_green, 255))

    pixels = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = pixels[x, y]
            if a > 0:
                nx = rng.gauss(0, 4)
                dist = abs(x - cx) / (W * 0.5)
                r2 = int(min(255, max(0, r + nx + 2 - dist * 30)))
                g2 = int(min(255, max(0, g + nx - dist * 40)))
                b2 = int(min(255, max(0, b + nx * 0.3)))
                pixels[x, y] = (r2, g2, b2, a)

    alpha = img.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.putalpha(alpha)

    return img


def make_sensitive_fern_pinna(size=(320, 320)):
    """Sensitive Fern (Onoclea sensibilis) pinna.

    Broad, triangular, wing-connected to rachis. Wavy margins.
    Bright yellow-green. Few large pinnae (5-11 pairs).
    The broadest, most un-fern-like shape.
    """
    W, H = size
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(45)

    cx = W * 0.5

    outline = []
    for i in range(50):
        t = i / 49

        # Broad triangular shape, widest at base
        if t < 0.1:
            env = 0.3 + t * 5
        else:
            env = 0.8 * (1.0 - (t - 0.1) / 0.9) ** 0.45

        # Wavy (sinuate) margins — smooth undulations, no teeth
        wave = 0.04 * math.sin(t * 7 * math.pi) * env

        w = (env * 0.48 + wave) * W

        y = H - t * (H - 20) - 10
        outline.append((t, cx - w, cx + w, y))

    poly_l = [(lx, y) for _, lx, _, y in outline]
    poly_r = [(rx, y) for _, _, rx, y in outline]
    poly = poly_l + list(reversed(poly_r))

    # Bright yellow-green (distinctly lighter than other ferns)
    base_green = (80, 170, 55)
    draw.polygon(poly, fill=(*base_green, 255))

    # Visible reticulate venation (network pattern)
    pixels = img.load()
    for y in range(H):
        for x in range(W):
            r, g, b, a = pixels[x, y]
            if a > 0:
                nx = rng.gauss(0, 5)
                dist = abs(x - cx) / (W * 0.5)
                # Brighter, more yellow-green than others
                r2 = int(min(255, max(0, r + nx + 4)))
                g2 = int(min(255, max(0, g + nx + 6)))
                b2 = int(min(255, max(0, b + nx * 0.5)))
                pixels[x, y] = (r2, g2, b2, a)

    # Midvein
    for y in range(int(H * 0.03), int(H * 0.97)):
        vx = int(cx + rng.uniform(-0.5, 0.5))
        for dx in range(-1, 2):
            if 0 <= vx + dx < W:
                r, g, b, a = pixels[vx + dx, y]
                if a > 0:
                    pixels[vx + dx, y] = (min(255, r + 6), min(255, g + 12), min(255, b + 3), a)

    alpha = img.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=1.0))
    img.putalpha(alpha)

    return img


if __name__ == "__main__":
    os.makedirs(TEX_DIR, exist_ok=True)

    print("Generating Christmas Fern pinna texture...")
    img = make_christmas_fern_pinna()
    path = os.path.join(TEX_DIR, "tex_pinna_christmas.png")
    img.save(path)
    print(f"  Saved {path} ({img.size[0]}x{img.size[1]})")

    print("Generating Ostrich Fern pinna texture...")
    img = make_ostrich_fern_pinna()
    path = os.path.join(TEX_DIR, "tex_pinna_ostrich.png")
    img.save(path)
    print(f"  Saved {path} ({img.size[0]}x{img.size[1]})")

    print("Generating Cinnamon Fern pinna texture...")
    img = make_cinnamon_fern_pinna()
    path = os.path.join(TEX_DIR, "tex_pinna_cinnamon.png")
    img.save(path)
    print(f"  Saved {path} ({img.size[0]}x{img.size[1]})")

    print("Generating Sensitive Fern pinna texture...")
    img = make_sensitive_fern_pinna()
    path = os.path.join(TEX_DIR, "tex_pinna_sensitive.png")
    img.save(path)
    print(f"  Saved {path} ({img.size[0]}x{img.size[1]})")

    print("Done.")

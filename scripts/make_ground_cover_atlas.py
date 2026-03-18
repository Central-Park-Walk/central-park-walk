"""
Generate shared ground cover texture atlas.

Layout: 4×2 grid, 512px per cell = 2048×1024
  Row 0: bramble, fern_cluster, mixed_weeds, tall_grass
  Row 1: fallen_leaves, twig_litter, (empty), (empty)

Run in Blender:  blender --background --python scripts/make_ground_cover_atlas.py
Output: textures/ground_cover_atlas.png
"""

import bpy
import math
import random
import os
import struct

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "textures")
CELL = 512
COLS = 4
ROWS = 2
TEX_W = CELL * COLS  # 2048
TEX_H = CELL * ROWS  # 1024

# Atlas layout: (col, row) for each patch type
ATLAS_MAP = {
    "bramble":       (0, 0),
    "fern_cluster":  (1, 0),
    "mixed_weeds":   (2, 0),
    "tall_grass":    (3, 0),
    "fallen_leaves": (0, 1),
    "twig_litter":   (1, 1),
}


def _set_pixel(pixels, x, y, r, g, b, a=1.0):
    if 0 <= x < TEX_W and 0 <= y < TEX_H:
        idx = (y * TEX_W + x) * 4
        # Allow overlap — blend for richer coverage
        pixels[idx] = r
        pixels[idx + 1] = g
        pixels[idx + 2] = b
        pixels[idx + 3] = a


def _paint_leaf(pixels, cx, cy, size, angle, r, g, b, rng, shape="elliptic"):
    aspect = 0.45 if shape == "elliptic" else 0.65 if shape == "broad" else 0.30
    leaf_h = int(size)
    leaf_w = int(size * aspect)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    radius = max(leaf_w, leaf_h)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            lx = dx * cos_a + dy * sin_a
            ly = -dx * sin_a + dy * cos_a
            nx = lx / max(leaf_w, 1)
            ny = ly / max(leaf_h, 1)
            dist = math.sqrt(nx * nx + ny * ny)
            if dist <= 1.0:
                edge_dark = 1.0 - 0.25 * dist
                vein = 1.0 - 0.06 * math.exp(-abs(nx) * 6.0)
                px = int(cx + dx)
                py = int(cy + dy)
                _set_pixel(pixels, px, py,
                           r * edge_dark * vein, g * edge_dark * vein,
                           b * edge_dark * vein)


def _paint_stem(pixels, sx, sy, angle, length, rng):
    for t in range(length):
        px = int(sx + math.sin(angle) * t + math.sin(t * 0.05) * 3)
        py = int(sy + math.cos(angle) * t)
        r = rng.uniform(0.22, 0.35)
        g = rng.uniform(0.18, 0.26)
        b = rng.uniform(0.10, 0.16)
        for w in range(-1, 2):
            _set_pixel(pixels, px + w, py, r, g, b)


def paint_bramble(pixels, ox, oy, rng):
    """Dense thorny leaves — fill 60%+ of cell."""
    for _ in range(rng.randint(55, 75)):
        cx = ox + rng.randint(CELL // 16, CELL * 15 // 16)
        cy = oy + rng.randint(CELL // 16, CELL * 15 // 16)
        size = CELL * rng.uniform(0.08, 0.16)
        angle = rng.uniform(0, math.pi * 2)
        r = rng.uniform(0.28, 0.42)
        g = rng.uniform(0.48, 0.68)
        b = rng.uniform(0.18, 0.32)
        _paint_leaf(pixels, cx, cy, size, angle, r, g, b, rng, "broad")
    for _ in range(rng.randint(6, 10)):
        sx = ox + rng.randint(CELL // 6, CELL * 5 // 6)
        sy = oy + rng.randint(0, CELL // 3)
        _paint_stem(pixels, sx, sy, rng.uniform(-0.3, 0.3),
                    rng.randint(CELL // 3, CELL * 2 // 3), rng)


def paint_fern(pixels, ox, oy, rng):
    """Fern fronds radiating — multiple rosettes to fill cell."""
    # Paint 2-3 overlapping rosettes
    for _ in range(rng.randint(2, 3)):
        center_x = ox + rng.randint(CELL // 4, CELL * 3 // 4)
        center_y = oy + rng.randint(CELL // 4, CELL * 3 // 4)
        n_fronds = rng.randint(6, 9)
        for f in range(n_fronds):
            angle = f * math.pi * 2 / n_fronds + rng.uniform(-0.3, 0.3)
            frond_len = rng.randint(CELL // 4, CELL * 3 // 8)
            r_col = rng.uniform(0.18, 0.28)
            g_col = rng.uniform(0.42, 0.58)
            b_col = rng.uniform(0.12, 0.22)
            for t in range(frond_len):
                px = int(center_x + math.sin(angle) * t)
                py = int(center_y + math.cos(angle) * t * 0.7 + t * 0.3)
                _set_pixel(pixels, px, py, r_col * 0.7, g_col * 0.7, b_col * 0.7)
                if t > 5 and t % 3 < 2:
                    pinna_len = int((frond_len - t) * 0.35)
                    for p in range(pinna_len):
                        side = 1 if (t % 6 < 3) else -1
                        perp = angle + side * math.pi / 2
                        ppx = int(px + math.sin(perp) * p)
                        ppy = int(py + math.cos(perp) * p * 0.7)
                        fade = 1.0 - p / max(pinna_len, 1) * 0.3
                        _set_pixel(pixels, ppx, ppy,
                                   r_col * fade, g_col * fade, b_col * fade)


def paint_weeds(pixels, ox, oy, rng):
    """Mixed broad-leaf weeds — dock, plantain rosettes."""
    for _ in range(rng.randint(25, 40)):
        cx = ox + rng.randint(CELL // 8, CELL * 7 // 8)
        cy = oy + rng.randint(CELL // 8, CELL * 7 // 8)
        n_leaves = rng.randint(4, 8)
        for l in range(n_leaves):
            la = l * math.pi * 2 / n_leaves + rng.uniform(-0.3, 0.3)
            size = CELL * rng.uniform(0.05, 0.10)
            dist = rng.uniform(0.3, 0.8) * size
            lx = cx + math.cos(la) * dist
            ly = cy + math.sin(la) * dist
            r = rng.uniform(0.32, 0.52)
            g = rng.uniform(0.52, 0.76)
            b = rng.uniform(0.18, 0.36)
            _paint_leaf(pixels, lx, ly, size, la, r, g, b, rng,
                        rng.choice(["elliptic", "broad"]))


def paint_tall_grass(pixels, ox, oy, rng):
    """Tall tussock grasses — vertical blades."""
    n_blades = rng.randint(35, 50)
    base_x = ox + CELL // 2
    base_y = oy + CELL // 10
    for _ in range(n_blades):
        bx = base_x + rng.randint(-CELL // 5, CELL // 5)
        angle = rng.uniform(-0.35, 0.35)
        length = rng.randint(CELL // 3, CELL * 3 // 4)
        width = rng.randint(2, max(3, CELL // 80))
        r = rng.uniform(0.32, 0.52)
        g = rng.uniform(0.52, 0.75)
        b = rng.uniform(0.16, 0.30)
        for t in range(length):
            curve = math.sin(t * 0.02 + rng.uniform(0, 3)) * t * 0.003
            px = int(bx + math.sin(angle + curve) * t * 0.3)
            py = int(base_y + t)
            fade = 1.0 - (t / length) * 0.25
            for w in range(-width, width + 1):
                _set_pixel(pixels, px + w, py,
                           r * fade, g * fade, b * fade)


def paint_fallen_leaves(pixels, ox, oy, rng):
    """Scattered fallen leaves — brown/orange/yellow."""
    palettes = [
        (0.60, 0.40, 0.15), (0.70, 0.45, 0.10), (0.75, 0.60, 0.15),
        (0.55, 0.20, 0.10), (0.65, 0.55, 0.20), (0.45, 0.30, 0.12),
    ]
    for _ in range(rng.randint(50, 70)):
        cx = ox + rng.randint(CELL // 8, CELL * 7 // 8)
        cy = oy + rng.randint(CELL // 8, CELL * 7 // 8)
        size = CELL * rng.uniform(0.04, 0.11)
        angle = rng.uniform(0, math.pi * 2)
        r, g, b = rng.choice(palettes)
        r += rng.uniform(-0.05, 0.05)
        g += rng.uniform(-0.05, 0.05)
        b += rng.uniform(-0.03, 0.03)
        _paint_leaf(pixels, cx, cy, size, angle, r, g, b, rng,
                    rng.choice(["elliptic", "broad"]))


def paint_twig_litter(pixels, ox, oy, rng):
    """Winter twigs + dead leaf fragments."""
    for _ in range(rng.randint(15, 22)):
        sx = ox + rng.randint(CELL // 8, CELL * 7 // 8)
        sy = oy + rng.randint(CELL // 8, CELL * 7 // 8)
        angle = rng.uniform(0, math.pi * 2)
        length = rng.randint(CELL // 6, CELL // 3)
        for t in range(length):
            px = int(sx + math.cos(angle) * t)
            py = int(sy + math.sin(angle) * t)
            r = rng.uniform(0.25, 0.38)
            g = rng.uniform(0.18, 0.28)
            b = rng.uniform(0.10, 0.18)
            for w in range(-1, 2):
                _set_pixel(pixels, px + w, py, r, g, b)
    for _ in range(rng.randint(25, 40)):
        cx = ox + rng.randint(CELL // 6, CELL * 5 // 6)
        cy = oy + rng.randint(CELL // 6, CELL * 5 // 6)
        size = CELL * rng.uniform(0.03, 0.07)
        angle = rng.uniform(0, math.pi * 2)
        r = rng.uniform(0.28, 0.42)
        g = rng.uniform(0.20, 0.30)
        b = rng.uniform(0.10, 0.18)
        _paint_leaf(pixels, cx, cy, size, angle, r, g, b, rng, "elliptic")


PAINTERS = {
    "bramble": paint_bramble,
    "fern_cluster": paint_fern,
    "mixed_weeds": paint_weeds,
    "tall_grass": paint_tall_grass,
    "fallen_leaves": paint_fallen_leaves,
    "twig_litter": paint_twig_litter,
}


def main():
    pixels = [0.0] * (TEX_W * TEX_H * 4)
    rng = random.Random(42)

    for name, (col, row) in ATLAS_MAP.items():
        ox = col * CELL
        oy = row * CELL
        painter = PAINTERS[name]
        painter(pixels, ox, oy, rng)
        print(f"Painted: {name} at ({col},{row})")

    # Write as raw PNG via Blender
    img = bpy.data.images.new("ground_cover_atlas", width=TEX_W, height=TEX_H, alpha=True)
    img.pixels[:] = pixels
    img.filepath_raw = os.path.join(OUT_DIR, "ground_cover_atlas.png")
    img.file_format = 'PNG'
    img.save()
    print(f"Saved: {img.filepath_raw}")


if __name__ == "__main__":
    main()

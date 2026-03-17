"""Generate leaf texture atlas for undergrowth vegetation.

Creates a 2048x2048 RGBA texture atlas (4x4 grid, 512x512 per species)
with species-specific leaf shapes, real-world colors from botanical data,
alpha masks, and procedural vein patterns.

Run: python3 scripts/make_leaf_atlas.py

Output: textures/leaf_atlas.png
"""

import math
import os
from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUT_PATH = os.path.join(PROJECT_DIR, "textures", "leaf_atlas.png")

CELL = 512       # pixels per species cell
ATLAS = 2048     # 4x4 grid = 2048x2048
PAD = 8          # padding inside each cell


def draw_veins(draw, cx, cy, length, angle, color, width=1, depth=0, max_depth=2):
    """Draw branching vein pattern from a point."""
    ex = cx + math.cos(angle) * length
    ey = cy + math.sin(angle) * length
    draw.line([(cx, cy), (ex, ey)], fill=color, width=width)
    if depth < max_depth and length > 15:
        # Side branches
        for side in [-1, 1]:
            ba = angle + side * 0.6
            bl = length * 0.55
            bx = cx + math.cos(angle) * length * 0.4
            by = cy + math.sin(angle) * length * 0.4
            draw_veins(draw, bx, by, bl, ba, color, max(1, width - 1), depth + 1, max_depth)


def draw_midrib_veins(draw, cx, cy, length, n_pairs, vein_color, midrib_w=2):
    """Draw a leaf midrib with alternating side veins."""
    # Midrib (vertical, pointing up)
    draw.line([(cx, cy), (cx, cy - length)], fill=vein_color, width=midrib_w)
    for i in range(n_pairs):
        t = 0.15 + (i / n_pairs) * 0.75
        vy = cy - length * t
        vl = length * 0.3 * (1.0 - t * 0.4)
        for side in [-1, 1]:
            angle = -math.pi / 2 + side * 1.1  # ~60° from midrib
            draw_veins(draw, cx, vy, vl, angle, vein_color, 1, 0, 1)


def make_elliptical_leaf(img, color, vein_color, aspect=1.8, serrated=False):
    """Draw an elliptical leaf with optional serrated edges."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx, cy = w // 2, h // 2
    rw = (w - PAD * 2) // 2
    rh = int(rw * aspect)
    rh = min(rh, (h - PAD * 2) // 2)

    if serrated:
        # Draw serrated edge using polygon points
        pts = []
        n = 48
        for i in range(n):
            a = (i / n) * math.tau
            r_base = 1.0
            tooth = 0.92 + 0.08 * math.cos(a * 12)  # 12 teeth
            rx = rw * r_base * tooth * math.cos(a)
            ry = rh * r_base * tooth * math.sin(a)
            pts.append((cx + rx, cy + ry))
        d.polygon(pts, fill=color)
    else:
        d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=color)

    draw_midrib_veins(d, cx, cy + rh * 0.85, int(rh * 1.7), 6, vein_color)
    return img


def make_heart_leaf(img, color, vein_color):
    """Heart-shaped leaf (knotweed, aster)."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx, cy = w // 2, h // 2
    r = (w - PAD * 2) // 2

    pts = []
    n = 64
    for i in range(n):
        t = i / n
        a = t * math.tau
        # Heart shape parametric
        x = r * 0.85 * math.sin(a) ** 3
        y = -r * (0.75 * math.cos(a) - 0.25 * math.cos(2 * a) -
                   0.10 * math.cos(3 * a) - 0.05 * math.cos(4 * a))
        pts.append((cx + x, cy + y * 0.9))
    d.polygon(pts, fill=color)
    draw_midrib_veins(d, cx, cy + r * 0.6, int(r * 1.3), 5, vein_color)
    return img


def make_lance_leaf(img, color, vein_color):
    """Lance/narrow leaf (Joe Pye, cardinal flower)."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx, cy = w // 2, h // 2
    rw = (w - PAD * 2) // 4  # narrow
    rh = (h - PAD * 2) // 2

    pts = []
    n = 48
    for i in range(n):
        a = (i / n) * math.tau
        # Tapered: wider in lower middle, pointed at both ends
        shape = math.sin(a) if math.sin(a) >= 0 else math.sin(a) * 0.7
        rx = rw * abs(shape)
        ry = rh * math.cos(a)
        pts.append((cx + rx * (1 if i < n // 2 else -1), cy + ry))
    d.polygon(pts, fill=color)
    draw_midrib_veins(d, cx, cy + rh * 0.9, int(rh * 1.8), 8, vein_color)
    return img


def make_pinnate_frond(img, color, vein_color, n_pinnae=12, pinna_w=0.35):
    """Pinnate frond (fern) — alternating pinnae along a rachis."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx = w // 2
    rachis_top = PAD + 20
    rachis_bot = h - PAD - 10
    rachis_len = rachis_bot - rachis_top

    # Draw rachis
    d.line([(cx, rachis_bot), (cx, rachis_top)], fill=vein_color, width=2)

    pw = int(w * pinna_w)  # pinna width
    ph = int(rachis_len / n_pinnae * 0.7)  # pinna height

    for i in range(n_pinnae):
        t = (i + 0.5) / n_pinnae
        py = rachis_bot - int(rachis_len * t)
        side = 1 if i % 2 == 0 else -1
        # Tapers toward tip
        scale = 1.0 - t * 0.5
        cpw = int(pw * scale)
        cph = int(ph * scale)
        if cpw < 4 or cph < 4:
            continue

        # Each pinna is a small ellipse
        px = cx + side * (cpw // 2 + 4)
        d.ellipse([px - cpw // 2, py - cph // 2, px + cpw // 2, py + cph // 2],
                  fill=color)
        # Tiny vein in each pinna
        d.line([(cx + side * 3, py), (px + side * cpw // 3, py)],
               fill=vein_color, width=1)

    return img


def make_compound_leaf(img, color, vein_color, n_leaflets=7):
    """Compound leaf (elderberry, sumac) — leaflets along a rachis."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx = w // 2
    rachis_bot = h - PAD - 10
    rachis_top = PAD + 30
    rachis_len = rachis_bot - rachis_top

    d.line([(cx, rachis_bot), (cx, rachis_top)], fill=vein_color, width=2)

    lw = int(w * 0.22)
    lh = int(rachis_len / n_leaflets * 1.0)

    for i in range(n_leaflets):
        t = (i + 0.5) / n_leaflets
        ly = rachis_bot - int(rachis_len * t)
        if i == n_leaflets - 1:
            # Terminal leaflet — centered
            d.ellipse([cx - lw // 2, ly - lh // 2, cx + lw // 2, ly + lh // 2],
                      fill=color)
        else:
            side = 1 if i % 2 == 0 else -1
            scale = 0.7 + t * 0.3
            clw = int(lw * scale)
            clh = int(lh * scale * 0.7)
            px = cx + side * (clw // 2 + 6)
            d.ellipse([px - clw // 2, ly - clh // 2, px + clw // 2, ly + clh // 2],
                      fill=color)
            d.line([(cx + side * 2, ly), (px, ly)], fill=vein_color, width=1)

    return img


def make_lobed_leaf(img, color, vein_color, n_lobes=5, depth=0.4):
    """Deeply lobed leaf (mugwort, coneflower)."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx, cy = w // 2, h // 2
    r = (w - PAD * 2) // 2

    pts = []
    n = 128
    for i in range(n):
        a = (i / n) * math.tau - math.pi / 2
        # Lobed shape: sinusoidal modulation
        lobe = 1.0 - depth * (0.5 + 0.5 * math.cos(a * n_lobes * 2))
        # Overall elliptical envelope (taller than wide)
        env_x = 0.85 * math.cos(a)
        env_y = 1.0 * math.sin(a)
        env = math.sqrt(env_x ** 2 + env_y ** 2)
        if env > 0:
            rx = r * lobe * env_x / env * abs(env)
            ry = r * lobe * env_y / env * abs(env) * 1.15
        else:
            rx, ry = 0, 0
        pts.append((cx + rx, cy + ry))
    d.polygon(pts, fill=color)
    draw_midrib_veins(d, cx, cy + r * 0.8, int(r * 1.5), 5, vein_color)
    return img


def make_sword_leaf(img, color, vein_color):
    """Long narrow sword-like leaf (cattail)."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    cx = w // 2
    lw = w // 6  # narrow

    pts = [
        (cx, PAD),              # tip
        (cx + lw, h // 3),     # right edge widens
        (cx + lw, h - PAD),    # right base
        (cx - lw, h - PAD),    # left base
        (cx - lw, h // 3),     # left edge widens
    ]
    d.polygon(pts, fill=color)
    # Central vein
    d.line([(cx, PAD + 5), (cx, h - PAD - 5)], fill=vein_color, width=2)
    # Parallel veins
    for offset in [-lw // 3, lw // 3]:
        d.line([(cx + offset, PAD + 30), (cx + offset, h - PAD - 5)],
               fill=vein_color, width=1)
    return img


def add_color_variation(img, seed=42):
    """Add subtle color variation across the leaf for realism."""
    import random
    rng = random.Random(seed)
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0:
                # Darken edges slightly
                dx = abs(x - w / 2) / (w / 2)
                dy = abs(y - h / 2) / (h / 2)
                edge = max(dx, dy)
                darken = 1.0 - edge * 0.12
                # Subtle random noise
                noise = rng.uniform(0.95, 1.05)
                factor = darken * noise
                r = max(0, min(255, int(r * factor)))
                g = max(0, min(255, int(g * factor)))
                b = max(0, min(255, int(b * factor)))
                px[x, y] = (r, g, b, a)
    return img


def add_flower_spots(img, flower_color, n_spots=8, spot_size=12, seed=99):
    """Add small flower spots for flowering species."""
    import random
    rng = random.Random(seed)
    d = ImageDraw.Draw(img)
    w, h = img.size
    px = img.load()
    for _ in range(n_spots):
        fx = rng.randint(PAD + 20, w - PAD - 20)
        fy = rng.randint(PAD + 20, h // 2)  # flowers in upper half
        # Only draw on existing leaf area
        if px[fx, fy][3] > 128:
            ss = rng.randint(spot_size // 2, spot_size)
            d.ellipse([fx - ss, fy - ss, fx + ss, fy + ss], fill=flower_color)
    return img


# ==========================================================================
# Species definitions: (name, shape_func, leaf_color_rgb, vein_color_rgb, extras)
# Colors are in 0-255 sRGB, matched to botanical reference data.
# ==========================================================================

SPECIES = [
    # Row 0 (shrubs)
    {"name": "Spicebush", "shape": "elliptical",
     "color": (77, 122, 31), "vein": (55, 90, 22),
     "opts": {"aspect": 1.6}},

    {"name": "WitchHazel", "shape": "elliptical",
     "color": (61, 107, 30), "vein": (42, 78, 20),
     "opts": {"aspect": 1.3, "serrated": True}},

    {"name": "Viburnum", "shape": "elliptical",
     "color": (36, 92, 18), "vein": (25, 65, 12),
     "opts": {"aspect": 1.5, "serrated": True}},

    {"name": "Sumac", "shape": "compound",
     "color": (56, 117, 22), "vein": (38, 82, 15),
     "opts": {"n_leaflets": 11}},

    # Row 1 (shrubs + tall herbs)
    {"name": "Elderberry", "shape": "compound",
     "color": (66, 122, 30), "vein": (45, 88, 20),
     "opts": {"n_leaflets": 7}},

    {"name": "Pokeweed", "shape": "elliptical",
     "color": (48, 102, 20), "vein": (35, 74, 14),
     "opts": {"aspect": 2.0}},

    {"name": "Knotweed", "shape": "heart",
     "color": (61, 128, 26), "vein": (42, 92, 18)},

    {"name": "JoePyeWeed", "shape": "lance",
     "color": (51, 102, 22), "vein": (36, 74, 15)},

    # Row 2 (herbs + wildflowers)
    {"name": "Coneflower", "shape": "lobed",
     "color": (56, 107, 22), "vein": (40, 78, 15),
     "opts": {"n_lobes": 4, "depth": 0.45}},

    {"name": "CardinalFlower", "shape": "lance",
     "color": (46, 92, 18), "vein": (32, 66, 12),
     "flower": (224, 20, 15)},

    {"name": "WhiteWoodAster", "shape": "heart",
     "color": (56, 112, 30), "vein": (40, 82, 20),
     "flower": (230, 235, 218)},

    {"name": "Jewelweed", "shape": "elliptical",
     "color": (102, 148, 64), "vein": (75, 112, 45),
     "opts": {"aspect": 1.4, "serrated": True},
     "flower": (217, 140, 30)},

    # Row 3 (ferns + wetland + mugwort)
    {"name": "Mugwort", "shape": "lobed",
     "color": (72, 92, 52), "vein": (50, 68, 38),
     "opts": {"n_lobes": 6, "depth": 0.5}},

    {"name": "OstrichFern", "shape": "pinnate",
     "color": (41, 112, 15), "vein": (28, 82, 10),
     "opts": {"n_pinnae": 16, "pinna_w": 0.30}},

    {"name": "ChristmasFern", "shape": "pinnate",
     "color": (18, 71, 12), "vein": (12, 52, 8),
     "opts": {"n_pinnae": 14, "pinna_w": 0.28}},

    {"name": "Cattail", "shape": "sword",
     "color": (51, 107, 28), "vein": (38, 82, 20)},
]


def build_atlas():
    atlas = Image.new("RGBA", (ATLAS, ATLAS), (0, 0, 0, 0))

    for idx, sp in enumerate(SPECIES):
        row = idx // 4
        col = idx % 4
        x0 = col * CELL
        y0 = row * CELL

        cell = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
        shape = sp["shape"]
        color = sp["color"] + (255,)
        vein = sp["vein"] + (255,)
        opts = sp.get("opts", {})

        if shape == "elliptical":
            make_elliptical_leaf(cell, color, vein, **opts)
        elif shape == "heart":
            make_heart_leaf(cell, color, vein)
        elif shape == "lance":
            make_lance_leaf(cell, color, vein)
        elif shape == "pinnate":
            make_pinnate_frond(cell, color, vein, **opts)
        elif shape == "compound":
            make_compound_leaf(cell, color, vein, **opts)
        elif shape == "lobed":
            make_lobed_leaf(cell, color, vein, **opts)
        elif shape == "sword":
            make_sword_leaf(cell, color, vein)

        # Add flower spots for flowering species
        if "flower" in sp:
            fc = sp["flower"] + (255,)
            add_flower_spots(cell, fc, n_spots=6, spot_size=10, seed=idx * 37)

        # Subtle color variation for realism
        add_color_variation(cell, seed=idx * 13 + 7)

        # Slight blur on alpha to soften edges
        r, g, b, a = cell.split()
        a = a.filter(ImageFilter.GaussianBlur(radius=1.0))
        cell = Image.merge("RGBA", (r, g, b, a))

        atlas.paste(cell, (x0, y0))
        print(f"  [{row},{col}] {sp['name']}: {shape}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    atlas.save(OUT_PATH, "PNG")
    size_kb = os.path.getsize(OUT_PATH) // 1024
    print(f"\nAtlas saved: {OUT_PATH} ({ATLAS}x{ATLAS}, {size_kb} KB)")


if __name__ == "__main__":
    print("=" * 60)
    print("Building 16-species leaf texture atlas")
    print("=" * 60)
    build_atlas()
    print("Done.")

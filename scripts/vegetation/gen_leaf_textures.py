"""Parametric leaf texture generator for all undergrowth species.

Generates alpha-masked PNG leaf textures from species data — outline shape,
serration, vein pattern, base color. One script for all species; adding a
species is just adding a data dict entry.

Run: python3 scripts/vegetation/gen_leaf_textures.py
"""

import math
import random
import os
from PIL import Image, ImageDraw, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TEX_DIR = os.path.join(PROJECT_DIR, "models", "vegetation")

# ── Species Data ──────────────────────────────────────────────────────
# Each entry drives the parametric generator.
#   size:         (W, H) texture pixels
#   base_color:   (R, G, B) 0-255
#   vein_color:   (R, G, B) 0-255 or None for auto (base + bright shift)
#   widest_pos:   0-1 where leaf is widest (0.35=ovate, 0.5=elliptic, 0.65=obovate)
#   max_w:        max half-width as fraction of W
#   base_w:       width at base (0=pointed, >0 rounded)
#   tip_sharp:    taper exponent at tip (0.5=blunt, 1.0=normal, 2.0=very sharp)
#   base_sharp:   taper exponent at base
#   teeth:        (count_per_side, depth_fraction) or None
#   wave:         (count, depth_fraction) or None
#   vein_count:   secondary veins per side
#   vein_angle:   degrees from midvein (30-70)
#   gloss:        0-1 center highlight strength
#   noise_std:    pixel color noise (gaussian sigma)
#   palmate:      None or (lobe_count, lobe_depth) for palmate leaves
#   truncate:     True for flat base (knotweed)
#   cordate:      depth fraction for heart-shaped notch or None

SPECIES = {
    # ── SHRUBS ──
    "Shrub_Spicebush": {
        "size": (256, 384),
        "base_color": (55, 148, 42),       # medium green, aromatic
        "widest_pos": 0.45,                 # slightly below center
        "max_w": 0.42,
        "base_w": 0.08,                     # cuneate (wedge) base
        "tip_sharp": 1.2,
        "base_sharp": 1.5,
        "teeth": None,                      # entire margin
        "wave": (6, 0.015),                 # very slight waviness
        "vein_count": 8,
        "vein_angle": 40,
        "gloss": 0.20,                      # semi-glossy
        "noise_std": 4,
    },
    "Shrub_WitchHazel": {
        "size": (256, 384),
        "base_color": (62, 140, 40),
        "widest_pos": 0.60,                 # obovate — widest above center
        "max_w": 0.44,
        "base_w": 0.15,                     # asymmetric rounded base
        "tip_sharp": 0.8,                   # blunt tip
        "base_sharp": 1.0,
        "teeth": None,
        "wave": (8, 0.035),                 # distinctly wavy/crenate margin
        "vein_count": 7,
        "vein_angle": 45,
        "gloss": 0.08,                      # matte
        "noise_std": 5,
    },
    "Shrub_Viburnum": {
        "size": (256, 320),
        "base_color": (45, 130, 35),        # dark green
        "widest_pos": 0.42,                 # ovate-orbicular
        "max_w": 0.46,                      # wide, roundish
        "base_w": 0.12,
        "tip_sharp": 1.3,
        "base_sharp": 1.0,
        "teeth": (18, 0.025),               # coarsely serrate
        "wave": None,
        "vein_count": 9,
        "vein_angle": 38,
        "gloss": 0.10,
        "noise_std": 4,
    },
    "Shrub_Sumac": {
        "size": (192, 384),                 # narrow lanceolate leaflet
        "base_color": (70, 150, 42),        # medium green
        "widest_pos": 0.38,
        "max_w": 0.38,                      # narrow
        "base_w": 0.05,
        "tip_sharp": 1.5,                   # long taper
        "base_sharp": 1.8,
        "teeth": (25, 0.018),               # finely serrate
        "wave": None,
        "vein_count": 14,                   # many parallel veins
        "vein_angle": 55,
        "gloss": 0.06,                      # matte
        "noise_std": 5,
    },
    "Shrub_Elderberry": {
        "size": (224, 384),
        "base_color": (58, 145, 38),
        "widest_pos": 0.40,                 # ovate-elliptic leaflet
        "max_w": 0.42,
        "base_w": 0.06,
        "tip_sharp": 1.4,
        "base_sharp": 1.3,
        "teeth": (20, 0.022),               # serrate
        "wave": None,
        "vein_count": 10,
        "vein_angle": 42,
        "gloss": 0.08,
        "noise_std": 4,
    },
    "Shrub_SweetPepperbush": {
        "size": (224, 384),
        "base_color": (52, 142, 36),
        "widest_pos": 0.58,                 # obovate
        "max_w": 0.40,
        "base_w": 0.05,                     # narrow base
        "tip_sharp": 0.9,                   # blunt
        "base_sharp": 1.6,                  # narrow base taper
        "teeth": (14, 0.020),               # serrate upper half only
        "teeth_start": 0.4,                 # teeth begin at 40% height
        "wave": None,
        "vein_count": 8,
        "vein_angle": 45,
        "gloss": 0.06,
        "noise_std": 4,
    },
    "Shrub_FloweringRaspberry": {
        "size": (384, 384),
        "base_color": (65, 152, 42),
        "palmate": (5, 0.45),               # 5 lobes, moderate depth
        "max_w": 0.46,
        "teeth": (30, 0.015),               # fine serrate on lobe margins
        "wave": None,
        "vein_count": 5,                    # one per lobe
        "vein_angle": 50,
        "gloss": 0.06,
        "noise_std": 5,
    },

    # ── KEY HERBS ──
    "Herb_Pokeweed": {
        "size": (256, 512),
        "base_color": (52, 138, 32),
        "widest_pos": 0.42,                 # ovate-lanceolate
        "max_w": 0.40,
        "base_w": 0.10,                     # rounded base
        "tip_sharp": 1.4,
        "base_sharp": 1.0,
        "teeth": None,                      # entire margin — key ID
        "wave": (5, 0.012),                 # slightly undulate
        "vein_count": 10,
        "vein_angle": 40,
        "vein_color": (60, 120, 40),        # pinkish-green midrib
        "gloss": 0.18,                      # semi-glossy waxy
        "noise_std": 4,
    },
    "Herb_JapaneseKnotweed": {
        "size": (320, 384),
        "base_color": (48, 135, 30),        # dark green, leathery
        "widest_pos": 0.40,                 # broadly ovate
        "max_w": 0.46,
        "base_w": 0.40,                     # very wide — truncate base
        "truncate": True,
        "tip_sharp": 1.6,                   # acuminate tip
        "base_sharp": 0.5,
        "teeth": None,
        "wave": (4, 0.010),                 # slightly wavy
        "vein_count": 8,
        "vein_angle": 42,
        "gloss": 0.15,                      # slightly glossy, leathery
        "noise_std": 3,                     # uniform color
    },
    "Herb_JoePyeWeed": {
        "size": (256, 512),
        "base_color": (50, 125, 32),        # dull dark green, matte
        "widest_pos": 0.35,                 # lance-ovate
        "max_w": 0.38,
        "base_w": 0.06,
        "tip_sharp": 1.5,                   # acuminate
        "base_sharp": 1.2,
        "teeth": (22, 0.020),               # coarsely serrate
        "wave": None,
        "vein_count": 12,
        "vein_angle": 35,                   # palmately 3-veined at base
        "vein_color": (55, 110, 40),        # purple-tinged midrib
        "gloss": 0.04,                      # very matte, rough
        "noise_std": 5,
    },
    "Herb_Burdock": {
        "size": (384, 384),
        "base_color": (55, 138, 38),
        "widest_pos": 0.45,
        "max_w": 0.48,                      # very wide
        "base_w": 0.15,
        "cordate": 0.08,                    # heart-shaped notch at base
        "tip_sharp": 1.0,
        "base_sharp": 0.8,
        "teeth": None,
        "wave": (7, 0.025),                 # wavy margin
        "vein_count": 7,
        "vein_angle": 40,
        "gloss": 0.05,                      # woolly matte
        "noise_std": 6,                     # rough surface
    },
    "Herb_WhiteWoodAster": {
        "size": (192, 320),
        "base_color": (55, 142, 38),
        "widest_pos": 0.38,                 # ovate
        "max_w": 0.44,
        "base_w": 0.10,
        "tip_sharp": 1.3,
        "base_sharp": 1.0,
        "teeth": (16, 0.018),               # serrate
        "wave": None,
        "vein_count": 6,
        "vein_angle": 40,
        "gloss": 0.06,
        "noise_std": 4,
    },
    "Herb_WhiteSnakeroot": {
        "size": (224, 384),
        "base_color": (52, 140, 35),
        "widest_pos": 0.40,
        "max_w": 0.42,
        "base_w": 0.08,
        "tip_sharp": 1.3,
        "base_sharp": 1.0,
        "teeth": (20, 0.022),               # coarsely serrate
        "wave": None,
        "vein_count": 8,
        "vein_angle": 38,
        "gloss": 0.06,
        "noise_std": 4,
    },
    "Herb_Mugwort": {
        "size": (256, 384),
        "base_color": (68, 140, 50),        # silvery-green (grayish)
        "widest_pos": 0.42,
        "max_w": 0.44,
        "base_w": 0.06,
        "tip_sharp": 1.2,
        "base_sharp": 1.4,
        "teeth": (12, 0.035),               # deeply lobed/cut
        "wave": None,
        "vein_count": 7,
        "vein_angle": 45,
        "gloss": 0.02,                      # very matte, woolly
        "noise_std": 7,                     # rough, hairy texture
    },

    # ── REMAINING HERBS ──
    "Herb_Coneflower": {
        "size": (256, 384),
        "base_color": (52, 140, 35),
        "widest_pos": 0.38,                 # ovate, deeply lobed
        "max_w": 0.44,
        "base_w": 0.06,
        "tip_sharp": 1.4,
        "base_sharp": 1.2,
        "teeth": (10, 0.040),               # deep lobes (pinnately cut)
        "wave": None,
        "vein_count": 8,
        "vein_angle": 40,
        "gloss": 0.06,
        "noise_std": 5,
    },
    "Herb_CardinalFlower": {
        "size": (160, 448),                 # narrow lanceolate
        "base_color": (48, 130, 28),        # dark green
        "widest_pos": 0.35,
        "max_w": 0.36,
        "base_w": 0.04,
        "tip_sharp": 1.6,                   # acuminate
        "base_sharp": 1.4,
        "teeth": (18, 0.012),               # finely serrate
        "wave": None,
        "vein_count": 10,
        "vein_angle": 35,
        "gloss": 0.08,
        "noise_std": 3,
    },
    "Herb_Ironweed": {
        "size": (192, 512),                 # narrow lanceolate
        "base_color": (45, 125, 30),        # dark green
        "widest_pos": 0.32,
        "max_w": 0.34,
        "base_w": 0.04,
        "tip_sharp": 1.5,
        "base_sharp": 1.6,
        "teeth": (24, 0.015),               # finely serrate
        "wave": None,
        "vein_count": 14,
        "vein_angle": 40,
        "gloss": 0.05,
        "noise_std": 4,
    },
    "Herb_RoseMallow": {
        "size": (320, 384),                 # broadly ovate
        "base_color": (58, 145, 38),        # medium-light green
        "widest_pos": 0.42,
        "max_w": 0.46,
        "base_w": 0.12,
        "tip_sharp": 1.2,
        "base_sharp": 0.9,
        "teeth": (16, 0.025),               # coarsely serrate
        "wave": None,
        "vein_count": 7,
        "vein_angle": 42,
        "gloss": 0.08,
        "noise_std": 4,
    },
    "Herb_Jewelweed": {
        "size": (224, 384),
        "base_color": (72, 158, 55),        # pale translucent green
        "widest_pos": 0.42,                 # ovate
        "max_w": 0.42,
        "base_w": 0.08,
        "tip_sharp": 1.2,
        "base_sharp": 1.0,
        "teeth": (14, 0.020),               # crenate-serrate
        "wave": (5, 0.015),
        "vein_count": 8,
        "vein_angle": 42,
        "gloss": 0.12,                      # slightly waxy
        "noise_std": 4,
    },
    "Herb_BlackeyedSusan": {
        "size": (192, 448),                 # oblanceolate
        "base_color": (56, 138, 35),
        "widest_pos": 0.55,                 # widest above center
        "max_w": 0.38,
        "base_w": 0.05,
        "tip_sharp": 1.0,                   # blunt-rounded tip
        "base_sharp": 1.5,                  # narrow base taper
        "teeth": None,                      # entire to slightly toothed
        "wave": (4, 0.010),
        "vein_count": 6,
        "vein_angle": 30,
        "gloss": 0.04,                      # rough, hairy
        "noise_std": 6,
    },

    # ── ACCENT FLOWERS ──
    "Flower_Goldenrod": {
        "size": (160, 448),                 # narrow lanceolate
        "base_color": (55, 140, 32),
        "widest_pos": 0.35,
        "max_w": 0.34,
        "base_w": 0.04,
        "tip_sharp": 1.4,
        "base_sharp": 1.4,
        "teeth": (16, 0.012),               # finely serrate
        "wave": None,
        "vein_count": 8,
        "vein_angle": 30,                   # nearly parallel veins
        "gloss": 0.06,
        "noise_std": 4,
    },
    "Flower_Aster": {
        "size": (192, 384),
        "base_color": (50, 135, 32),
        "widest_pos": 0.38,                 # ovate-lanceolate
        "max_w": 0.40,
        "base_w": 0.06,
        "tip_sharp": 1.3,
        "base_sharp": 1.1,
        "teeth": (18, 0.016),               # serrate
        "wave": None,
        "vein_count": 7,
        "vein_angle": 38,
        "gloss": 0.06,
        "noise_std": 4,
    },

    # ── WETLAND ──
    "Wetland_Cattail": {
        "size": (96, 512),                  # very narrow sword blade
        "base_color": (118, 150, 72),       # MEASURED from reference_photos/cattail (2026-06-19):
                                            # pooled leaf median (102,145,54), aquatic-cluster ref
                                            # (129,153,81). Real foliage is a WARM yellow-green
                                            # (high R, low B), NOT cool blue-green. Prior (90,146,80)
                                            # was too blue. Glaucous banding (below) adds the grey-
                                            # blue FNA zones on top of this warm base.
        "widest_pos": 0.15,                 # widest near base
        "max_w": 0.42,
        "base_w": 0.38,                     # nearly as wide at base
        "tip_sharp": 2.0,                   # long taper
        "base_sharp": 0.5,                  # broad base
        "teeth": None,
        "wave": None,
        "vein_count": 4,                    # parallel veins
        "vein_angle": 8,                    # nearly parallel
        "gloss": 0.07,                      # matte-waxy, not glossy plastic
        "noise_std": 8,                     # tonal mottle (was 3 — read flat)
        "striations": 18,                   # fine longitudinal venation (de-plastics)
        "glaucous_amt": 0.40,               # waxy grey-blue banding
        # Imperfections (user 2026-06-19: "the leaves are too clean and pretty"). Real
        # cattail blades carry tan senescence spots and dry browned tips. Refs:
        # reference_photos/cattail show flecking + browned tips even on summer foliage.
        "blemish_amt": 0.55,                # strength of brown senescence spots
        "blemish_count": 9,                 # number of scattered spots
        "tip_brown": 0.85,                  # fraction up the blade where the dry tip starts
        "brown_color": (110, 84, 46),       # tan-brown senescence / dry-tip target
    },
    "Wetland_YellowIris": {
        "size": (96, 512),
        "base_color": (42, 118, 25),        # dark green
        "widest_pos": 0.20,
        "max_w": 0.40,
        "base_w": 0.36,
        "tip_sharp": 1.8,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 5,
        "vein_angle": 6,                    # nearly parallel
        "gloss": 0.12,                      # slightly waxy
        "noise_std": 3,
    },
    "Wetland_LizardsTail": {
        "size": (224, 320),
        "base_color": (50, 138, 32),
        "widest_pos": 0.42,                 # ovate
        "max_w": 0.44,
        "base_w": 0.12,
        "cordate": 0.06,                    # heart-shaped base
        "tip_sharp": 1.3,
        "base_sharp": 0.9,
        "teeth": None,                      # entire margin
        "wave": (5, 0.012),
        "vein_count": 7,
        "vein_angle": 38,
        "gloss": 0.10,
        "noise_std": 4,
    },
    "Wetland_Phragmites": {
        "size": (112, 512),                 # linear blade, wider than cattail
        "base_color": (60, 135, 38),
        "widest_pos": 0.18,
        "max_w": 0.40,
        "base_w": 0.35,
        "tip_sharp": 2.0,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 5,
        "vein_angle": 8,
        "gloss": 0.06,
        "noise_std": 3,
    },

    # ── GRASSES ──
    "Grass_Bottlebrush": {
        "size": (80, 448),                  # very narrow blade
        "base_color": (58, 138, 38),
        "widest_pos": 0.15,
        "max_w": 0.38,
        "base_w": 0.34,
        "tip_sharp": 2.0,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 3,
        "vein_angle": 5,
        "gloss": 0.06,
        "noise_std": 3,
    },
    "Grass_LittleBluestem": {
        "size": (64, 384),                  # narrow, blue-green
        "base_color": (55, 130, 48),        # blue-green tint
        "widest_pos": 0.12,
        "max_w": 0.38,
        "base_w": 0.34,
        "tip_sharp": 2.2,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 2,
        "vein_angle": 5,
        "gloss": 0.04,
        "noise_std": 3,
    },
    "Grass_Switchgrass": {
        "size": (96, 512),                  # wider, tall blade
        "base_color": (52, 132, 42),        # blue-green
        "widest_pos": 0.15,
        "max_w": 0.38,
        "base_w": 0.34,
        "tip_sharp": 2.0,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 4,
        "vein_angle": 6,
        "gloss": 0.06,
        "noise_std": 3,
    },
    "Grass_TussockSedge": {
        "size": (64, 384),                  # narrow sedge blade
        "base_color": (58, 140, 36),        # yellow-green
        "widest_pos": 0.15,
        "max_w": 0.36,
        "base_w": 0.30,
        "tip_sharp": 2.0,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 2,
        "vein_angle": 5,
        "gloss": 0.04,
        "noise_std": 3,
    },
    "Grass_PASedge": {
        "size": (48, 256),                  # very short, fine blade
        "base_color": (52, 130, 32),        # medium green
        "widest_pos": 0.12,
        "max_w": 0.36,
        "base_w": 0.30,
        "tip_sharp": 2.0,
        "base_sharp": 0.5,
        "teeth": None,
        "wave": None,
        "vein_count": 1,
        "vein_angle": 5,
        "gloss": 0.04,
        "noise_std": 3,
    },
}


def _draw_vein(draw, x0, y0, x1, y1, color, width=1):
    """Draw a slightly curved vein line."""
    rng = random.Random(int(x0 * 7 + y0 * 13 + x1 * 3))
    steps = 12
    mx = (x0 + x1) / 2 + rng.uniform(-3, 3)
    my = (y0 + y1) / 2 + rng.uniform(-2, 2)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t ** 2 * x1
        py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t ** 2 * y1
        pts.append((px, py))
    draw.line(pts, fill=color, width=width)


def _simple_leaf_outline(W, H, sp):
    """Generate outline polygon for a simple (non-palmate) leaf."""
    rng = random.Random(hash(str(sp.get("base_color", (0,0,0)))) & 0x7FFFFFFF)
    cx = W * 0.5
    widest = sp.get("widest_pos", 0.45)
    max_w = sp.get("max_w", 0.42)
    base_w = sp.get("base_w", 0.08)
    tip_sharp = sp.get("tip_sharp", 1.2)
    base_sharp = sp.get("base_sharp", 1.2)
    truncate = sp.get("truncate", False)
    cordate = sp.get("cordate", None)
    teeth = sp.get("teeth", None)
    teeth_start = sp.get("teeth_start", 0.0)
    wave = sp.get("wave", None)

    n_pts = 80
    outline_left = []
    outline_right = []

    for i in range(n_pts):
        t = i / (n_pts - 1)  # 0=base, 1=tip

        # Width envelope — sine/cosine for smooth rounded outlines.
        # sin(0→π/2) for rise, cos(0→π/2) for fall — both have zero
        # derivative at the peak, so the widest point is rounded, not angular.
        if truncate and t < 0.06:
            w = max_w * (0.85 + 0.15 * (t / 0.06))
        elif t <= widest:
            s = math.sin(t / max(widest, 0.01) * math.pi * 0.5)
            w = (base_w + (1.0 - base_w) * s ** (1.0 / max(base_sharp, 0.3))) * max_w
        else:
            s = math.cos((t - widest) / max(1.0 - widest, 0.01) * math.pi * 0.5)
            w = max(s, 0.0) ** tip_sharp * max_w

        # Cordate notch at base
        if cordate and t < 0.10:
            notch_t = t / 0.10
            notch = cordate * math.sin(notch_t * math.pi)
            # Widen at sides of notch, narrow at center
            w = max(w * (1.0 + notch * 0.3), 0.02)
            if notch_t < 0.5:
                w *= (0.7 + 0.3 * notch_t * 2)

        # Margin effects — kept subtle
        margin_left = 0.0
        margin_right = 0.0
        if teeth and t > teeth_start and t < 0.93:
            count, depth = teeth
            # Teeth are small bumps, not deep cuts. Scale depth relative
            # to current width so teeth are proportional.
            tooth_size = depth * w * 0.4
            tooth_phase_l = t * count * 2.0
            tooth_phase_r = t * count * 2.0 + 0.3  # slight offset between sides
            margin_left += tooth_size * max(0, math.sin(tooth_phase_l * math.pi))
            margin_right += tooth_size * max(0, math.sin(tooth_phase_r * math.pi))
        if wave and t > 0.05 and t < 0.93:
            count, depth = wave
            wave_size = depth * w * 0.5
            margin_left += wave_size * math.sin(t * count * math.pi * 2)
            margin_right += wave_size * math.sin(t * count * math.pi * 2 + 0.5)

        # Organic irregularity — subtle random edge noise
        edge_noise = rng.gauss(0, 0.003 * w)
        margin_left += edge_noise
        margin_right += rng.gauss(0, 0.003 * w)

        lx = cx - (w + margin_left) * W
        rx = cx + (w + margin_right) * W

        y = H - t * (H - 20) - 10
        outline_left.append((lx, y))
        outline_right.append((rx, y))

    return outline_left + list(reversed(outline_right))


def _palmate_leaf_outline(W, H, sp):
    """Generate outline polygon for a palmate (lobed) leaf like Flowering Raspberry / maple.
    Creates pointed lobe tips with deep angular sinuses — true maple-like shape,
    not soft gaussian bumps (which produce clover)."""
    cx = W * 0.5
    cy = H * 0.52  # center slightly below middle
    lobe_count, lobe_depth = sp["palmate"]
    max_w = sp.get("max_w", 0.46)
    teeth = sp.get("teeth", None)
    radius = min(W, H) * max_w * 0.9

    # Lobes spread over the upper arc — petiole at bottom
    # Wider spread so outer lobes aren't pinched against the petiole
    spread = math.pi * 0.80
    lobe_angles = []
    for li in range(lobe_count):
        a = -spread + (2 * spread) * li / (lobe_count - 1)
        lobe_angles.append(a - math.pi * 0.5)  # rotate so 0 = straight up

    # Sinus midpoint angles
    sinus_angles = []
    for si in range(lobe_count - 1):
        sinus_angles.append((lobe_angles[si] + lobe_angles[si + 1]) * 0.5)

    n_pts = 400
    points = []
    for i in range(n_pts):
        frac = i / (n_pts - 1)
        angle = -math.pi * 0.85 + frac * math.pi * 1.7  # ~310° arc

        # Find nearest lobe and compute how deep into lobe vs sinus we are.
        # Use a triangular wave per lobe for pointed tips, not gaussian.
        r = radius * 0.35  # base radius (visible between lobes)

        # For each lobe: triangular spike centered on lobe angle.
        # Lobe angular half-width = half the spacing between adjacent lobes.
        lobe_spacing = (2 * spread) / max(lobe_count - 1, 1)
        lobe_hw = lobe_spacing * 0.5  # angular half-width

        best_lobe_contrib = 0.0
        for la in lobe_angles:
            da = angle - la
            while da > math.pi: da -= 2 * math.pi
            while da < -math.pi: da += 2 * math.pi
            abs_da = abs(da)
            if abs_da < lobe_hw:
                # Triangular: 1.0 at center, 0.0 at half-width boundary
                tri = 1.0 - abs_da / lobe_hw
                # Sharpen the peak for pointed tips (power < 1 = sharper)
                tri = tri ** 0.65
                best_lobe_contrib = max(best_lobe_contrib, tri)

        r += radius * 0.72 * best_lobe_contrib

        # Deep sinuses — sharp V-shaped cuts between lobes
        for sa in sinus_angles:
            da = angle - sa
            while da > math.pi: da -= 2 * math.pi
            while da < -math.pi: da += 2 * math.pi
            abs_da = abs(da)
            sinus_hw = lobe_spacing * 0.28  # narrow V
            if abs_da < sinus_hw:
                sinus_t = 1.0 - abs_da / sinus_hw
                sinus_t = sinus_t ** 0.8  # sharpen
                r -= radius * lobe_depth * 0.65 * sinus_t

        # Taper to petiole at bottom
        bottom_angle = math.pi * 0.5  # straight down
        da_bottom = abs(angle - bottom_angle)
        if da_bottom > math.pi:
            da_bottom = 2 * math.pi - da_bottom
        if da_bottom < 0.45:
            petiole_t = 1.0 - da_bottom / 0.45
            r *= (1.0 - petiole_t * 0.78)
            r = max(r, 8)

        # Fine serration on lobe edges
        if teeth and r > radius * 0.35:
            count, depth = teeth
            tooth = math.sin(i * count / n_pts * math.pi * 2)
            r += r * depth * 0.12 * max(0, tooth)

        x = cx + math.cos(angle) * r
        y = cy - math.sin(angle) * r
        points.append((x, y))

    return points


def generate_leaf(species_name, sp):
    """Generate a leaf texture from species parameters."""
    W, H = sp["size"]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(hash(species_name) & 0x7FFFFFFF)

    base_r, base_g, base_b = sp["base_color"]
    cx = W * 0.5

    # Build outline
    if sp.get("palmate"):
        poly = _palmate_leaf_outline(W, H, sp)
    else:
        poly = _simple_leaf_outline(W, H, sp)

    # Fill with base color
    draw.polygon(poly, fill=(base_r, base_g, base_b, 255))

    # Add natural color variation with noise
    pixels = img.load()
    gloss = sp.get("gloss", 0.08)
    noise_std = sp.get("noise_std", 4)

    striations = sp.get("striations", 0)       # fine longitudinal veins (linear blades)
    glaucous_amt = sp.get("glaucous_amt", 0.0)  # waxy grey-blue bloom banding

    # Imperfection layer: scattered tan senescence spots + a dry browned tip. Defaults off
    # so other species are untouched. Spots are elongated along the blade (narrow in x).
    blemish_amt = sp.get("blemish_amt", 0.0)
    blemish_count = sp.get("blemish_count", 0)
    tip_brown = sp.get("tip_brown", 1.0)        # 1.0 = no tip browning
    brown_col = sp.get("brown_color", (110, 84, 46))
    spots = []
    if blemish_amt > 0.0 and blemish_count > 0:
        # Rejection-sample spot centres ONTO the filled leaf silhouette — earlier spots fell
        # in the transparent margins of the narrow blade and never showed (user 2026-06-19:
        # "leaves still look clean"). Bias toward the upper blade where senescence starts.
        tries = 0
        while len(spots) < blemish_count and tries < blemish_count * 40:
            tries += 1
            sxp = rng.randint(0, W - 1)
            syp = rng.randint(int(H * 0.05), H - 1)
            if pixels[sxp, syp][3] > 0:                     # must be on the leaf body
                spots.append((float(sxp), float(syp),
                              rng.uniform(0.035, 0.11) * H,  # radius (along-blade)
                              rng.uniform(0.55, 1.0)))       # per-spot intensity

    for y in range(H):
        for x in range(W):
            r, g, b, a = pixels[x, y]
            if a > 0:
                t_along = 1.0 - y / H  # 0=base, 1=tip
                dist_from_mid = abs(x - cx) / (W * 0.5)

                # Gaussian noise for natural variation
                nx = rng.gauss(0, noise_std)
                ny = rng.gauss(0, noise_std * 0.8)

                # Center highlight (gloss)
                highlight = max(0, 1.0 - dist_from_mid * 1.8) * gloss

                # Edge darkening
                edge_dark = dist_from_mid * 0.08

                # Slight tip-to-base gradient (tips slightly lighter)
                tip_grad = t_along * 0.04

                # Fine longitudinal striations (parallel venation of strap blades) —
                # a flat fill reads plastic; these give the leaf real surface structure.
                stri = (math.sin((x / W) * math.pi * striations) * 0.12) if striations else 0.0
                # Broad glaucous banding: desaturate toward grey-blue in soft bands that
                # drift along the blade (the waxy bloom catching light unevenly).
                gl = (((math.sin((x / W) * 6.3 + t_along * 9.0) * 0.5 + 0.5)) * glaucous_amt) \
                    if glaucous_amt else 0.0

                # broad low-freq value banding for depth (light/shadow along the blade)
                vband = math.sin(t_along * 5.0 + (x / W) * 1.5) * 0.05
                mod = highlight - edge_dark + tip_grad + stri + vband
                # glaucous adds a balanced grey (R≈B), only slightly cool — NOT teal
                r2 = int(min(255, max(0, r + nx + mod * 50 + gl * 28)))
                g2 = int(min(255, max(0, g + ny + mod * 64 + gl * 20)))
                b2 = int(min(255, max(0, b + nx * 0.4 - edge_dark * 15 + gl * 24)))

                # Imperfections: brown amount from the dry tip + any senescence spot
                if blemish_amt > 0.0 or tip_brown < 1.0:
                    br = 0.0
                    if t_along > tip_brown:
                        br = (t_along - tip_brown) / (1.0 - tip_brown) * 0.9
                    for sx, sy, sr_, inten in spots:
                        ddx = (x - sx) / (sr_ * 0.42)   # x tighter — blade is narrow
                        ddy = (y - sy) / sr_
                        d2 = ddx * ddx + ddy * ddy
                        if d2 < 1.0:
                            br = max(br, (1.0 - d2) * inten * blemish_amt)
                    if br > 0.0:
                        r2 = int(r2 + (brown_col[0] - r2) * br)
                        g2 = int(g2 + (brown_col[1] - g2) * br)
                        b2 = int(b2 + (brown_col[2] - b2) * br)
                        if br > 0.30:               # dry zones are rougher/noisier
                            j = rng.gauss(0, 11)
                            r2 = int(min(255, max(0, r2 + j)))
                            g2 = int(min(255, max(0, g2 + j * 0.8)))
                            b2 = int(min(255, max(0, b2 + j * 0.5)))

                pixels[x, y] = (r2, g2, b2, a)

    # Draw midvein
    vein_count = sp.get("vein_count", 8)
    vein_angle = sp.get("vein_angle", 42)
    vc = sp.get("vein_color", None)
    if vc is None:
        vc = (min(255, base_r + 8), min(255, base_g + 15), min(255, base_b + 5))

    if not sp.get("palmate"):
        # Simple leaf: straight midvein
        for y in range(int(H * 0.05), int(H * 0.95)):
            vx = int(cx + rng.uniform(-0.5, 0.5))
            for dx in range(-1, 2):
                if 0 <= vx + dx < W:
                    r, g, b, a = pixels[vx + dx, y]
                    if a > 0:
                        pixels[vx + dx, y] = (
                            min(255, r + 5),
                            min(255, g + 12),
                            min(255, b + 3), a)

        # Side veins
        for i in range(vein_count):
            t = 0.08 + i * (0.82 / max(vein_count, 1))
            y_start = int(H * (1.0 - t))
            x_start = int(cx)
            angle_rad = math.radians(vein_angle)

            # Find edge at this height from outline
            half_w = 0
            for px, py in poly[:len(poly) // 2]:
                if abs(py - y_start) < H / 60:
                    half_w = max(half_w, abs(px - cx))
                    break

            if half_w < 5:
                half_w = W * 0.3  # fallback

            vein_len = half_w - 8
            # Left vein
            _draw_vein(draw, x_start, y_start,
                       x_start - vein_len, y_start - vein_len * math.tan(angle_rad) * 0.3,
                       (*vc, 160), width=1)
            # Right vein
            _draw_vein(draw, x_start, y_start,
                       x_start + vein_len, y_start - vein_len * math.tan(angle_rad) * 0.3,
                       (*vc, 160), width=1)
    else:
        # Palmate leaf: radial veins from center
        lobe_count = sp["palmate"][0]
        pcy = H * 0.55
        for i in range(lobe_count):
            angle = -math.pi * 0.5 + (i / (lobe_count - 1)) * math.pi
            vein_len = min(W, H) * sp.get("max_w", 0.46) * 0.85
            ex = cx + math.cos(angle) * vein_len
            ey = pcy - math.sin(angle) * vein_len
            _draw_vein(draw, cx, pcy, ex, ey, (*vc, 180), width=1)

    # Soften alpha edges
    alpha = img.split()[3]
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.putalpha(alpha)

    return img


if __name__ == "__main__":
    os.makedirs(TEX_DIR, exist_ok=True)

    for species_name, sp in SPECIES.items():
        print(f"Generating {species_name} leaf texture...")
        img = generate_leaf(species_name, sp)
        path = os.path.join(TEX_DIR, f"tex_leaf_{species_name}.png")
        img.save(path)
        print(f"  Saved {path} ({img.size[0]}x{img.size[1]})")

    print(f"\nDone. {len(SPECIES)} species generated.")

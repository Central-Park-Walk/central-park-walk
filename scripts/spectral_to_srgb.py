#!/usr/bin/env python3
"""Convert grass species spectral reflectance curves to sRGB vertex colors.

Uses CIE 1931 2° observer color matching functions under D65 illuminant
to derive physically correct colors from published leaf reflectance data.

Spectral reflectance values sourced from:
  - Jiang et al. 2007: Broadband Spectral Reflectance Models of Turfgrass
  - PMC 5703567: Reflectance of bermudagrass/manilagrass canopies
  - General C3/C4 grass leaf reflectance literature
  - USDA turfgrass management spectral studies

Output: base_rgb and tip_rgb values for make_ground_cover.py / make_blade_mesh.py
        + zone palette values for grass_particle_render.gdshader

Run: python3 scripts/spectral_to_srgb.py
"""

import math

# ---------------------------------------------------------------------------
# CIE 1931 2° observer color matching functions at 10nm intervals (400-700nm)
# Source: CIE 015:2018, public standard
# ---------------------------------------------------------------------------
WAVELENGTHS = list(range(400, 710, 10))  # 400, 410, ..., 700

CIE_X = [
    0.0143, 0.0435, 0.1344, 0.2839, 0.3483, 0.3362, 0.2908, 0.1954,
    0.0956, 0.0320, 0.0049, 0.0093, 0.0633, 0.1655, 0.2904, 0.4334,
    0.5945, 0.7621, 0.9163, 1.0263, 1.0622, 1.0026, 0.8544, 0.6424,
    0.4479, 0.2835, 0.1649, 0.0874, 0.0468, 0.0227, 0.0114,
]
CIE_Y = [
    0.0004, 0.0012, 0.0040, 0.0116, 0.0230, 0.0380, 0.0600, 0.0910,
    0.1390, 0.2080, 0.3230, 0.5030, 0.7100, 0.8620, 0.9540, 0.9950,
    0.9950, 0.9520, 0.8700, 0.7570, 0.6310, 0.5030, 0.3810, 0.2650,
    0.1750, 0.1070, 0.0610, 0.0320, 0.0170, 0.0082, 0.0041,
]
CIE_Z = [
    0.0679, 0.2074, 0.6456, 1.3856, 1.7471, 1.7721, 1.6692, 1.2876,
    0.8130, 0.4652, 0.2720, 0.1582, 0.0782, 0.0422, 0.0203, 0.0087,
    0.0039, 0.0021, 0.0017, 0.0011, 0.0008, 0.0003, 0.0002, 0.0000,
    0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
]

# D65 illuminant relative spectral power distribution (10nm, 400-700nm)
# Source: CIE 015:2018
D65 = [
    82.75, 91.49, 93.43, 86.68, 104.86, 117.01, 117.81, 114.86,
    115.92, 108.81, 109.35, 107.80, 104.79, 107.69, 104.41, 104.05,
    100.00, 96.33, 95.79, 88.69, 90.01, 89.60, 87.70, 83.29,
    83.70, 80.03, 80.21, 82.28, 78.28, 69.72, 71.61,
]


def spectral_to_xyz(reflectance):
    """Convert spectral reflectance curve to CIE XYZ tristimulus values.

    reflectance: list of fractional reflectance (0-1) at 10nm intervals 400-700nm
    Returns: (X, Y, Z) normalized so a perfect white diffuser has Y=1.
    """
    assert len(reflectance) == len(WAVELENGTHS), \
        f"Expected {len(WAVELENGTHS)} values, got {len(reflectance)}"

    X = Y = Z = 0.0
    N = 0.0  # normalization factor

    for i in range(len(WAVELENGTHS)):
        s = D65[i]
        r = reflectance[i]
        X += s * r * CIE_X[i]
        Y += s * r * CIE_Y[i]
        Z += s * r * CIE_Z[i]
        N += s * CIE_Y[i]

    # Normalize so Y of perfect white = 1.0
    X /= N
    Y /= N
    Z /= N
    return X, Y, Z


def xyz_to_linear_srgb(X, Y, Z):
    """Convert CIE XYZ to linear sRGB (D65 adapted)."""
    R = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    G = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    B = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
    return max(0, R), max(0, G), max(0, B)


def linear_to_srgb(c):
    """Apply sRGB gamma curve to a single linear channel value."""
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def srgb_gamma(rgb):
    """Apply sRGB gamma to (R, G, B) tuple."""
    return tuple(linear_to_srgb(c) for c in rgb)


def reflectance_to_srgb(reflectance):
    """Full pipeline: spectral reflectance → sRGB color."""
    X, Y, Z = spectral_to_xyz(reflectance)
    linear = xyz_to_linear_srgb(X, Y, Z)
    return srgb_gamma(linear)


# ---------------------------------------------------------------------------
# Grass species spectral reflectance curves (fractional, 0-1)
# 31 values at 10nm intervals from 400nm to 700nm
#
# Derived from published turfgrass reflectance studies:
#   - Jiang et al. 2007 (Crop Science): KBG, tall fescue, bermuda drought curves
#   - Fenstermaker-Shaulis et al. 2007: turfgrass canopy reflectance
#   - PMC5703567: bermuda/manilagrass transmittance/reflectance
#   - General C3/C4 grass leaf optics (Gates et al. 1965, Woolley 1971)
#
# Values represent single-leaf diffuse reflectance (not canopy), healthy
# midsummer condition. These are what GPU particle blade meshes represent.
# ---------------------------------------------------------------------------

SPECIES = {
    # Kentucky Bluegrass (Poa pratensis) — C3, waxy glaucous bloom
    # Slightly blue-shifted green peak (~545nm), moderate reflectance
    "Kentucky Bluegrass": {
        "tip": [
            # 400  410   420   430   440   450   460   470   480   490
            0.035, 0.038, 0.042, 0.045, 0.048, 0.052, 0.055, 0.060, 0.070, 0.085,
            # 500  510   520   530   540   550   560   570   580   590
            0.100, 0.115, 0.128, 0.138, 0.145, 0.148, 0.140, 0.122, 0.100, 0.080,
            # 600  610   620   630   640   650   660   670   680   690   700
            0.065, 0.055, 0.050, 0.046, 0.043, 0.040, 0.038, 0.035, 0.032, 0.080, 0.200,
        ],
        "base_factor": 0.55,  # sheathed base: 55% of tip chlorophyll
        "biome": "Lawn",
    },

    # Perennial Ryegrass (Lolium perenne) — C3, shiny adaxial surface
    # Brighter, broader green peak, slightly higher reflectance
    "Perennial Ryegrass": {
        "tip": [
            0.038, 0.042, 0.046, 0.050, 0.053, 0.057, 0.060, 0.068, 0.078, 0.095,
            0.112, 0.130, 0.145, 0.155, 0.162, 0.165, 0.158, 0.138, 0.115, 0.092,
            0.075, 0.063, 0.057, 0.052, 0.048, 0.045, 0.042, 0.039, 0.036, 0.090, 0.220,
        ],
        "base_factor": 0.50,
        "biome": "Lawn (mix)",
    },

    # Fine Fescue (Festuca rubra) — C3, narrow dark leaves
    # Lower reflectance, slightly yellow-shifted peak (~555nm)
    "Fine Fescue": {
        "tip": [
            0.030, 0.032, 0.035, 0.038, 0.040, 0.043, 0.046, 0.052, 0.060, 0.072,
            0.085, 0.098, 0.108, 0.115, 0.120, 0.122, 0.118, 0.105, 0.088, 0.070,
            0.058, 0.050, 0.045, 0.042, 0.039, 0.037, 0.035, 0.032, 0.029, 0.070, 0.175,
        ],
        "base_factor": 0.50,
        "biome": "Shade",
    },

    # Switchgrass (Panicum virgatum) — C4, warm-season, yellow-green
    # Lower chlorophyll density, peak at 555-560nm, warmer tint
    "Switchgrass": {
        "tip": [
            0.040, 0.042, 0.045, 0.048, 0.050, 0.053, 0.055, 0.062, 0.072, 0.088,
            0.102, 0.118, 0.132, 0.142, 0.150, 0.155, 0.152, 0.140, 0.120, 0.098,
            0.082, 0.070, 0.062, 0.056, 0.052, 0.048, 0.045, 0.042, 0.038, 0.085, 0.210,
        ],
        "base_factor": 0.45,
        "biome": "Wild",
    },

    # Little Bluestem (Schizachyrium scoparium) — C4, blue-green waxy
    # Blue-shifted peak similar to KBG, slightly higher blue reflectance
    "Little Bluestem": {
        "tip": [
            0.042, 0.045, 0.048, 0.052, 0.055, 0.058, 0.062, 0.068, 0.078, 0.092,
            0.105, 0.120, 0.132, 0.140, 0.145, 0.146, 0.138, 0.120, 0.100, 0.082,
            0.068, 0.058, 0.052, 0.048, 0.045, 0.042, 0.040, 0.037, 0.034, 0.082, 0.205,
        ],
        "base_factor": 0.48,
        "biome": "Wild",
    },

    # Tussock Sedge (Carex stricta) — dark green, high chlorophyll
    # Lower overall reflectance, strong chlorophyll absorption
    "Tussock Sedge": {
        "tip": [
            0.028, 0.030, 0.033, 0.035, 0.037, 0.040, 0.043, 0.048, 0.056, 0.068,
            0.080, 0.092, 0.102, 0.110, 0.115, 0.118, 0.114, 0.100, 0.084, 0.068,
            0.055, 0.048, 0.043, 0.040, 0.037, 0.035, 0.033, 0.030, 0.027, 0.065, 0.170,
        ],
        "base_factor": 0.52,
        "biome": "Sedge",
    },

    # Soft Rush (Juncus effusus) — cylindrical stem, medium green
    "Soft Rush": {
        "tip": [
            0.032, 0.035, 0.038, 0.040, 0.042, 0.045, 0.048, 0.054, 0.062, 0.075,
            0.088, 0.100, 0.112, 0.120, 0.125, 0.128, 0.124, 0.110, 0.092, 0.074,
            0.060, 0.052, 0.047, 0.043, 0.040, 0.038, 0.036, 0.033, 0.030, 0.072, 0.185,
        ],
        "base_factor": 0.50,
        "biome": "Sedge",
    },

    # White Clover (Trifolium repens) — broadleaf, dark rich green
    "White Clover": {
        "tip": [
            0.032, 0.035, 0.038, 0.042, 0.045, 0.048, 0.052, 0.058, 0.068, 0.082,
            0.095, 0.110, 0.122, 0.130, 0.135, 0.138, 0.132, 0.118, 0.098, 0.078,
            0.064, 0.055, 0.050, 0.046, 0.043, 0.040, 0.038, 0.035, 0.032, 0.075, 0.190,
        ],
        "base_factor": 0.60,  # petiole, less etiolated
        "biome": "Accent (lawn)",
    },

    # Dandelion (Taraxacum officinale) — broadleaf, medium green
    "Dandelion": {
        "tip": [
            0.035, 0.038, 0.042, 0.045, 0.048, 0.052, 0.056, 0.064, 0.074, 0.090,
            0.105, 0.120, 0.132, 0.140, 0.146, 0.148, 0.142, 0.126, 0.105, 0.085,
            0.070, 0.060, 0.054, 0.050, 0.047, 0.044, 0.041, 0.038, 0.035, 0.082, 0.200,
        ],
        "base_factor": 0.55,
        "biome": "Accent (lawn)",
    },

    # Broadleaf Plantain (Plantago major) — dark matte leaves
    "Plantain": {
        "tip": [
            0.028, 0.030, 0.034, 0.037, 0.040, 0.043, 0.046, 0.052, 0.062, 0.075,
            0.088, 0.100, 0.112, 0.120, 0.126, 0.128, 0.122, 0.108, 0.090, 0.072,
            0.060, 0.052, 0.046, 0.042, 0.039, 0.037, 0.035, 0.032, 0.029, 0.068, 0.175,
        ],
        "base_factor": 0.55,
        "biome": "Accent (lawn)",
    },

    # Dried leaf litter — no chlorophyll, tannin/lignin dominated
    "Dried Leaf": {
        "tip": [
            0.050, 0.055, 0.060, 0.065, 0.072, 0.080, 0.088, 0.095, 0.105, 0.115,
            0.125, 0.132, 0.140, 0.148, 0.155, 0.160, 0.165, 0.170, 0.172, 0.170,
            0.165, 0.158, 0.150, 0.142, 0.135, 0.128, 0.120, 0.112, 0.105, 0.100, 0.098,
        ],
        "base_factor": 1.0,  # uniform color
        "biome": "Accent (shade)",
    },

    # Dried grass seed head — straw/senescent
    "Dried Seed Head": {
        "tip": [
            0.060, 0.065, 0.072, 0.080, 0.088, 0.098, 0.108, 0.118, 0.130, 0.142,
            0.155, 0.165, 0.175, 0.185, 0.195, 0.200, 0.205, 0.210, 0.212, 0.210,
            0.205, 0.198, 0.190, 0.182, 0.175, 0.168, 0.160, 0.152, 0.145, 0.140, 0.138,
        ],
        "base_factor": 0.90,  # slightly darker stem
        "biome": "Accent (wild)",
    },
}


def make_base_curve(tip_curve, factor):
    """Create etiolated base reflectance from tip curve.

    Less chlorophyll → weaker absorption at 450nm and 680nm →
    flatter curve → more yellow/straw appearance.
    """
    # Find the structural (non-pigment) reflectance baseline
    # This is roughly the NIR plateau, estimated from the 700nm value
    structural = tip_curve[-1]  # ~0.20 for green leaves

    base = []
    for i, r in enumerate(tip_curve):
        # The pigment absorption features are the dips below structural
        absorption_depth = max(0, structural - r)
        # Reduce absorption by factor (less pigment at base)
        new_r = structural - absorption_depth * factor
        # Clamp
        base.append(max(0.01, min(0.99, new_r)))
    return base


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 72)
print("Spectral Reflectance → sRGB Color Conversion")
print("CIE 1931 2° observer, D65 illuminant")
print("=" * 72)

# Collect results for output
results = {}

for name, spec in SPECIES.items():
    tip_curve = spec["tip"]
    base_factor = spec["base_factor"]
    base_curve = make_base_curve(tip_curve, base_factor)

    tip_srgb = reflectance_to_srgb(tip_curve)
    base_srgb = reflectance_to_srgb(base_curve)

    # Also compute linear values (for Godot shader uniforms)
    tip_xyz = spectral_to_xyz(tip_curve)
    tip_linear = xyz_to_linear_srgb(*tip_xyz)
    base_xyz = spectral_to_xyz(base_curve)
    base_linear = xyz_to_linear_srgb(*base_xyz)

    results[name] = {
        "tip_srgb": tip_srgb,
        "base_srgb": base_srgb,
        "tip_linear": tip_linear,
        "base_linear": base_linear,
        "biome": spec["biome"],
    }

    print(f"\n{name} ({spec['biome']})")
    print(f"  Peak reflectance: {max(tip_curve)*100:.1f}% at "
          f"{WAVELENGTHS[tip_curve.index(max(tip_curve))]}nm")
    print(f"  Tip  sRGB: ({tip_srgb[0]:.3f}, {tip_srgb[1]:.3f}, {tip_srgb[2]:.3f})"
          f"  = ({int(tip_srgb[0]*255)}, {int(tip_srgb[1]*255)}, {int(tip_srgb[2]*255)})")
    print(f"  Base sRGB: ({base_srgb[0]:.3f}, {base_srgb[1]:.3f}, {base_srgb[2]:.3f})"
          f"  = ({int(base_srgb[0]*255)}, {int(base_srgb[1]*255)}, {int(base_srgb[2]*255)})")
    print(f"  Tip  linear: ({tip_linear[0]:.4f}, {tip_linear[1]:.4f}, {tip_linear[2]:.4f})")
    print(f"  Base linear: ({base_linear[0]:.4f}, {base_linear[1]:.4f}, {base_linear[2]:.4f})")


# ---------------------------------------------------------------------------
# Output formatted for make_ground_cover.py / make_blade_mesh.py
# (These scripts use sRGB vertex colors in 0-1 range)
# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("VERTEX COLOR VALUES for make_ground_cover.py / make_blade_mesh.py")
print("(sRGB 0-1, used as vertex colors in Blender)")
print("=" * 72)

biome_map = {
    "Lawn": ["Kentucky Bluegrass", "Perennial Ryegrass"],
    "Shade": ["Fine Fescue"],
    "Wild": ["Switchgrass", "Little Bluestem"],
    "Sedge": ["Tussock Sedge", "Soft Rush"],
}

for biome, species_list in biome_map.items():
    print(f"\n--- {biome} biome ---")
    for sp in species_list:
        r = results[sp]
        t = r["tip_srgb"]
        b = r["base_srgb"]
        print(f'  # {sp}')
        print(f'  "base_rgb": ({b[0]:.2f}, {b[1]:.2f}, {b[2]:.2f}),')
        print(f'  "tip_rgb":  ({t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}),')

print("\n--- Accents ---")
for sp in ["White Clover", "Dandelion", "Plantain", "Dried Leaf", "Dried Seed Head"]:
    r = results[sp]
    t = r["tip_srgb"]
    b = r["base_srgb"]
    print(f'  # {sp}')
    print(f'  "base_rgb": ({b[0]:.2f}, {b[1]:.2f}, {b[2]:.2f}),')
    print(f'  "tip_rgb":  ({t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}),')


# ---------------------------------------------------------------------------
# Output formatted for grass_particle_render.gdshader zone palettes
# (Godot shaders work in linear sRGB space)
# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
print("SHADER PALETTE VALUES for grass_particle_render.gdshader")
print("(linear sRGB 0-1, for vec3() uniforms)")
print("=" * 72)

for biome, species_list in biome_map.items():
    # Average the species in each biome for the zone base color
    avg_tip = [0, 0, 0]
    avg_base = [0, 0, 0]
    for sp in species_list:
        r = results[sp]
        for c in range(3):
            avg_tip[c] += r["tip_linear"][c]
            avg_base[c] += r["base_linear"][c]
    n = len(species_list)
    avg_tip = [v / n for v in avg_tip]
    avg_base = [v / n for v in avg_base]

    print(f"\n  // {biome} — {', '.join(species_list)}")
    print(f"  // tip:  vec3({avg_tip[0]:.4f}, {avg_tip[1]:.4f}, {avg_tip[2]:.4f})")
    print(f"  // base: vec3({avg_base[0]:.4f}, {avg_base[1]:.4f}, {avg_base[2]:.4f})")


print("\n" + "=" * 72)
print("COMPARISON: current vs spectral")
print("=" * 72)

current = {
    "Blade_Lawn": {"base": (0.15, 0.35, 0.06), "tip": (0.35, 0.55, 0.18)},
    "Blade_Shade": {"base": (0.06, 0.18, 0.03), "tip": (0.16, 0.30, 0.10)},
    "Blade_Wild": {"base": (0.12, 0.28, 0.04), "tip": (0.40, 0.42, 0.16)},
    "Blade_Sedge": {"base": (0.10, 0.26, 0.05), "tip": (0.24, 0.40, 0.14)},
}

spectral = {
    "Blade_Lawn": {"species": "Kentucky Bluegrass"},
    "Blade_Shade": {"species": "Fine Fescue"},
    "Blade_Wild": {"species": "Switchgrass"},
    "Blade_Sedge": {"species": "Tussock Sedge"},
}

for blade, cur in current.items():
    sp_name = spectral[blade]["species"]
    sp = results[sp_name]
    print(f"\n  {blade} ({sp_name}):")
    print(f"    Current base: ({cur['base'][0]:.2f}, {cur['base'][1]:.2f}, {cur['base'][2]:.2f})")
    print(f"    Spectral base: ({sp['base_srgb'][0]:.2f}, {sp['base_srgb'][1]:.2f}, {sp['base_srgb'][2]:.2f})")
    print(f"    Current tip:  ({cur['tip'][0]:.2f}, {cur['tip'][1]:.2f}, {cur['tip'][2]:.2f})")
    print(f"    Spectral tip:  ({sp['tip_srgb'][0]:.2f}, {sp['tip_srgb'][1]:.2f}, {sp['tip_srgb'][2]:.2f})")

    # Delta
    for part in ["base", "tip"]:
        c = cur[part]
        s = sp[f"{part}_srgb"]
        dr = s[0] - c[0]
        dg = s[1] - c[1]
        db = s[2] - c[2]
        direction = []
        if abs(dr) > 0.02:
            direction.append(f"{'more' if dr > 0 else 'less'} red")
        if abs(dg) > 0.02:
            direction.append(f"{'more' if dg > 0 else 'less'} green")
        if abs(db) > 0.02:
            direction.append(f"{'more' if db > 0 else 'less'} blue")
        if direction:
            print(f"    {part} shift: {', '.join(direction)}")

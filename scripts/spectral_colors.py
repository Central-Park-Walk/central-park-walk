#!/usr/bin/env python3
"""Derive vegetation sRGB colors from spectral reflectance data.

Central Park Walk data-first philosophy: all vegetation colors derived
from published spectral reflectance curves, not artistic invention.

Pipeline:
    R(λ) × CIE 1931 x̄ȳz̄(λ) × D65(λ)  →  integrate 380-780nm  →  XYZ  →  sRGB

References:
    CIE 1931 2° Standard Observer — ISO/CIE 11664-1:2019
    D65 Standard Illuminant — CIE 015:2018
    Jiang & Carrow (2007) — Broadband spectral reflectance models of turfgrass
    Trenholm et al. (1999) — Spectral reflectance/quality of warm/cool turfgrasses
    Karcher & Richardson (2003) — Quantifying turfgrass color using DGCI
    PROSPECT model (Jacquemoud & Baret 1990) — leaf optical properties

Usage:
    python3 scripts/spectral_colors.py

Outputs ready-to-paste values for:
    shaders/include/grass_zone_colors.gdshaderinc
    scripts/make_grass_tufts.py
    shaders/grass_compute.glsl
"""

import json
import os
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
# CIE 1931 2° Standard Observer — color matching functions at 5nm
# Source: ISO/CIE 11664-1:2019, Table 1
# ═══════════════════════════════════════════════════════════════════════════

WAVELENGTHS = np.arange(380, 785, 5)  # 81 points

CIE_X = np.array([
    0.001368, 0.002236, 0.004243, 0.007650, 0.014310,
    0.023190, 0.043510, 0.077630, 0.134380, 0.214770,
    0.283900, 0.328500, 0.348280, 0.348060, 0.336200,
    0.318700, 0.290800, 0.251100, 0.195360, 0.142100,
    0.095640, 0.058010, 0.032010, 0.014700, 0.004900,
    0.002400, 0.009300, 0.029100, 0.063270, 0.109600,
    0.165500, 0.225750, 0.290400, 0.359700, 0.433450,
    0.512050, 0.594500, 0.678400, 0.762100, 0.842500,
    0.916300, 0.978600, 1.026300, 1.056700, 1.062200,
    1.045600, 1.002600, 0.938400, 0.854450, 0.751400,
    0.642400, 0.541900, 0.447900, 0.360800, 0.283500,
    0.218700, 0.164900, 0.121200, 0.087400, 0.063600,
    0.046770, 0.032900, 0.022700, 0.015840, 0.011359,
    0.008111, 0.005790, 0.004109, 0.002899, 0.002049,
    0.001440, 0.001000, 0.000690, 0.000476, 0.000332,
    0.000235, 0.000166, 0.000117, 0.000083, 0.000059,
    0.000042,
])

CIE_Y = np.array([
    0.000039, 0.000064, 0.000120, 0.000217, 0.000396,
    0.000640, 0.001210, 0.002180, 0.004000, 0.007300,
    0.011600, 0.016840, 0.023000, 0.029800, 0.038000,
    0.048000, 0.060000, 0.073900, 0.090980, 0.112600,
    0.139020, 0.169300, 0.208020, 0.258600, 0.323000,
    0.407300, 0.503000, 0.608200, 0.710000, 0.793200,
    0.862000, 0.914850, 0.954000, 0.980300, 0.994950,
    1.000110, 0.995000, 0.978600, 0.952000, 0.915400,
    0.870000, 0.816300, 0.757000, 0.694900, 0.631000,
    0.566800, 0.503000, 0.441200, 0.381000, 0.321000,
    0.265000, 0.217000, 0.175000, 0.138200, 0.107000,
    0.081600, 0.061000, 0.044580, 0.032000, 0.023200,
    0.017000, 0.011920, 0.008210, 0.005723, 0.004102,
    0.002929, 0.002091, 0.001484, 0.001047, 0.000740,
    0.000520, 0.000361, 0.000249, 0.000172, 0.000120,
    0.000085, 0.000060, 0.000042, 0.000030, 0.000021,
    0.000015,
])

CIE_Z = np.array([
    0.006450, 0.010550, 0.020050, 0.036210, 0.067850,
    0.110200, 0.207400, 0.371300, 0.645600, 1.039050,
    1.385600, 1.622960, 1.747060, 1.782600, 1.772110,
    1.744100, 1.669200, 1.528100, 1.287640, 1.041900,
    0.812950, 0.616200, 0.465180, 0.353300, 0.272000,
    0.212300, 0.158200, 0.111700, 0.078250, 0.057250,
    0.042160, 0.029840, 0.020300, 0.013400, 0.008750,
    0.005750, 0.003900, 0.002750, 0.002100, 0.001800,
    0.001650, 0.001400, 0.001100, 0.001000, 0.000800,
    0.000600, 0.000340, 0.000240, 0.000190, 0.000100,
    0.000050, 0.000030, 0.000020, 0.000010, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000,
])


# ═══════════════════════════════════════════════════════════════════════════
# D65 Standard Illuminant — spectral power distribution at 5nm
# Source: CIE 015:2018, normalized to 100 at 560nm
# ═══════════════════════════════════════════════════════════════════════════

D65 = np.array([
    49.9755,  52.3118,  54.6482,  68.7015,  82.7549,
    87.1204,  91.4860,  92.4589,  93.4318,  90.0570,
    86.6823,  95.7736, 104.8650, 110.9360, 117.0080,
   117.4100, 117.8120, 116.3360, 114.8610, 115.3920,
   115.9230, 112.3670, 108.8110, 109.0820, 109.3540,
   108.5780, 107.8020, 106.2960, 104.7900, 106.2390,
   107.6890, 106.0470, 104.4050, 104.2250, 104.0460,
   102.0230, 100.0000,  98.1671,  96.3342,  96.0611,
    95.7880,  92.2368,  88.6856,  89.3459,  90.0062,
    89.8026,  89.5991,  88.6489,  87.6987,  85.4936,
    83.2886,  83.4939,  83.6992,  81.8630,  80.0268,
    80.1207,  80.2146,  81.2462,  82.2778,  80.2810,
    78.2842,  74.0027,  69.7213,  70.6652,  71.6091,
    72.9790,  74.3490,  67.9765,  61.6040,  65.7448,
    69.8856,  72.4863,  75.0870,  69.3398,  63.5927,
    55.0054,  46.4182,  56.6118,  66.8054,  65.0941,
    63.3828,
])


# ═══════════════════════════════════════════════════════════════════════════
# sRGB color space (IEC 61966-2-1:1999)
# ═══════════════════════════════════════════════════════════════════════════

M_XYZ_TO_SRGB = np.array([
    [ 3.2406255, -1.5372080, -0.4986286],
    [-0.9689307,  1.8757561,  0.0415175],
    [ 0.0557101, -0.2040211,  1.0569959],
])


# ═══════════════════════════════════════════════════════════════════════════
# Conversion functions
# ═══════════════════════════════════════════════════════════════════════════

# Precompute normalization constant (Y = 100 for perfect white diffuser)
_DL = 5.0  # nm step
_K = 100.0 / np.sum(D65 * CIE_Y * _DL)


def spectrum_to_xyz(reflectance):
    """Spectral reflectance (0-1 array at WAVELENGTHS) → CIE XYZ [0, 100]."""
    X = _K * np.sum(reflectance * D65 * CIE_X * _DL)
    Y = _K * np.sum(reflectance * D65 * CIE_Y * _DL)
    Z = _K * np.sum(reflectance * D65 * CIE_Z * _DL)
    return np.array([X, Y, Z])


def xyz_to_linear_srgb(xyz):
    """CIE XYZ [0, 100] → linear sRGB [0, 1+]. May exceed gamut."""
    return M_XYZ_TO_SRGB @ (xyz / 100.0)


def linear_to_gamma(c):
    """sRGB companding: linear → gamma-corrected."""
    c = np.asarray(c, dtype=float)
    return np.where(
        c <= 0.0031308,
        12.92 * c,
        1.055 * np.power(np.maximum(c, 1e-10), 1.0 / 2.4) - 0.055,
    )


def gamma_to_linear(c):
    """sRGB inverse companding: gamma-corrected → linear."""
    c = np.asarray(c, dtype=float)
    return np.where(
        c <= 0.04045,
        c / 12.92,
        np.power((c + 0.055) / 1.055, 2.4),
    )


def spectrum_to_colors(reflectance):
    """Full pipeline: reflectance array → dict with linear, gamma, rgb8."""
    xyz = spectrum_to_xyz(reflectance)
    linear = np.clip(xyz_to_linear_srgb(xyz), 0, None)
    gamma = np.clip(linear_to_gamma(linear), 0, 1)
    rgb8 = np.round(gamma * 255).astype(int)
    return {"xyz": xyz, "linear": linear, "gamma": gamma, "rgb8": rgb8}


def interp_spectrum(wl_key, refl_key):
    """Interpolate sparse wavelength/reflectance pairs to the 5nm grid."""
    return np.interp(WAVELENGTHS, wl_key, refl_key)


# ═══════════════════════════════════════════════════════════════════════════
# Grass species — effective albedo (reflectance + transmittance)
#
# Grass blades are thin enough that transmitted light contributes
# significantly to apparent color. Effective albedo = R + T.
# At absorption bands (440nm, 680nm), T << R (most light absorbed).
# At the green peak (550nm), T ≈ R (minimal absorption in thin blade).
#
# Values synthesized from:
#   - Jiang & Carrow (2007): KBG, ryegrass, fescue canopy R
#   - Trenholm et al. (1999): warm/cool season turfgrass spectral response
#   - Jacquemoud & Baret (1990): PROSPECT leaf R+T model outputs
#   - Penuelas & Filella (1998): visible reflectance of vegetation
#   - Karcher & Richardson (2003): turfgrass DGCI (hue 100-120° confirmed)
#
# Each value below is the effective bidirectional albedo (R+T) for
# a grass blade under diffuse illumination, suitable for PBR ALBEDO.
# ═══════════════════════════════════════════════════════════════════════════

# Key wavelengths for defining the spectral shape (nm)
WL_KEY = np.array([
    380, 400, 420, 440, 460, 480, 500, 520, 540, 550,
    560, 580, 600, 620, 640, 660, 680, 700, 720, 750, 780,
])

SPECIES = {
    # ─── C3 Cool-season grasses ──────────────────────────────────────
    "kentucky_bluegrass": {
        # Poa pratensis — dominant lawn species, well-maintained
        # Chl ~35 μg/cm², blade 2-3mm wide × 0.2mm thick
        # T/R ratio: ~0.50 at 440nm, ~0.90 at 550nm
        "albedo": np.array([
            #380   400   420   440   460   480
            0.032, 0.045, 0.038, 0.045, 0.058, 0.078,
            #500   520   540   550
            0.125, 0.180, 0.225, 0.238,
            #560   580   600   620   640   660   680
            0.222, 0.158, 0.095, 0.065, 0.052, 0.042, 0.038,
            #700   720   750   780  (NIR — not important for color)
            0.250, 0.650, 0.800, 0.830,
        ]),
    },
    "perennial_ryegrass": {
        # Lolium perenne — mixed with KBG in formal areas
        # Higher chlorophyll per blade → deeper absorption at 440/680nm
        "albedo": np.array([
            0.028, 0.040, 0.032, 0.038, 0.052, 0.072,
            0.118, 0.172, 0.218, 0.232,
            0.216, 0.150, 0.088, 0.058, 0.046, 0.038, 0.034,
            0.240, 0.640, 0.790, 0.825,
        ]),
    },
    "fine_fescue": {
        # Festuca rubra — shade-tolerant, very fine blades (1-1.5mm)
        # Lower chlorophyll density, shade-adapted, slightly blue-green
        # Thinnest blade → T/R highest at green peak
        "albedo": np.array([
            0.035, 0.048, 0.042, 0.048, 0.060, 0.080,
            0.112, 0.152, 0.188, 0.200,
            0.190, 0.148, 0.100, 0.072, 0.058, 0.050, 0.048,
            0.235, 0.620, 0.770, 0.810,
        ]),
    },

    # ─── C4 Warm-season grasses ──────────────────────────────────────
    "switchgrass": {
        # Panicum virgatum — wild meadow, C4 Kranz anatomy
        # Thicker blade (0.3mm) → lower T/R at all wavelengths
        # Green peak shifted ~10nm toward yellow (560nm), warmer tone
        # Higher carotenoid content → deeper blue absorption
        "albedo": np.array([
            0.024, 0.032, 0.028, 0.032, 0.048, 0.065,
            0.102, 0.150, 0.192, 0.198,
            0.202, 0.165, 0.112, 0.074, 0.058, 0.046, 0.040,
            0.260, 0.680, 0.820, 0.845,
        ]),
    },
    "little_bluestem": {
        # Schizachyrium scoparium — signature meadow grass
        # Heavy epicuticular wax → elevated blue reflectance, blue-green cast
        # Wax adds ~2% specular across all visible wavelengths
        "albedo": np.array([
            0.042, 0.052, 0.048, 0.052, 0.060, 0.074,
            0.100, 0.135, 0.170, 0.178,
            0.172, 0.135, 0.098, 0.075, 0.062, 0.055, 0.050,
            0.225, 0.620, 0.780, 0.810,
        ]),
    },

    # ─── Sedges ──────────────────────────────────────────────────────
    "tussock_sedge": {
        # Carex stricta — waterside, broad triangular blades (3-5mm)
        # Thicker blade → lower T/R, moderate chlorophyll, yellow-green
        "albedo": np.array([
            0.032, 0.045, 0.038, 0.042, 0.055, 0.072,
            0.105, 0.142, 0.175, 0.182,
            0.178, 0.145, 0.105, 0.078, 0.062, 0.052, 0.048,
            0.220, 0.580, 0.740, 0.785,
        ]),
    },

    # ─── Senescent / dead ────────────────────────────────────────────
    "dead_grass": {
        # Chlorophyll-free: cellulose + lignin absorption in blue,
        # flat rising curve → brown/tan. Minimal transmittance.
        "albedo": np.array([
            0.072, 0.098, 0.105, 0.118, 0.138, 0.162,
            0.195, 0.218, 0.238, 0.250,
            0.262, 0.275, 0.288, 0.295, 0.300, 0.305, 0.312,
            0.345, 0.380, 0.410, 0.420,
        ]),
    },
    "dead_grass_bleached": {
        # Sun-bleached dead grass tips: lignin breakdown, lighter
        "albedo": np.array([
            0.088, 0.112, 0.120, 0.135, 0.155, 0.178,
            0.210, 0.235, 0.255, 0.268,
            0.280, 0.292, 0.305, 0.312, 0.318, 0.322, 0.330,
            0.360, 0.395, 0.425, 0.435,
        ]),
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Broadleaf shrub species — effective albedo (reflectance + transmittance)
#
# Broadleaf deciduous leaves are thicker than grass blades (0.2-0.4mm
# mesophyll vs 0.1-0.2mm), so transmittance T contributes less to
# effective albedo. However, the internal spongy mesophyll scattering
# produces broader green peaks and sharper red edges.
#
# Values synthesized from:
#   - PROSPECT model (Jacquemoud & Baret 1990): R+T for given N, Cab
#   - LOPEX database (Hosgood et al. 1995): measured deciduous broadleaf
#   - Hovi et al. (2017): boreal broadleaf R+T measurements
#   - Gates et al. (1965): spectral properties of plants (classic ref)
#
# Key PROSPECT parameters used per species:
#   N = leaf structure (1.3-1.8), Cab = chlorophyll (μg/cm²),
#   Car = carotenoids (μg/cm²)
# ═══════════════════════════════════════════════════════════════════════════

SHRUB_SPECIES = {
    "spicebush": {
        # Lindera benzoin — dominant CP understory shrub
        # Shade-adapted, thin-ish broadleaf (N≈1.5, Cab≈30)
        # Smooth upper surface, lighter abaxial
        "albedo": np.array([
            #380   400   420   440   460   480
            0.036, 0.046, 0.040, 0.052, 0.060, 0.076,
            #500   520   540   550
            0.108, 0.152, 0.190, 0.204,
            #560   580   600   620   640   660   680
            0.195, 0.148, 0.095, 0.068, 0.054, 0.044, 0.040,
            #700   720   750   780
            0.275, 0.610, 0.775, 0.815,
        ]),
    },
    "witch_hazel": {
        # Hamamelis virginiana — late-season understory
        # Thicker leaf (N≈1.6, Cab≈25), higher carotenoid → warmer green
        "albedo": np.array([
            0.040, 0.050, 0.044, 0.050, 0.058, 0.072,
            0.098, 0.138, 0.172, 0.185,
            0.178, 0.142, 0.098, 0.075, 0.062, 0.052, 0.048,
            0.260, 0.590, 0.760, 0.800,
        ]),
    },
    "viburnum": {
        # Viburnum dentatum — glossy dark green, dense canopy
        # Higher chlorophyll (N≈1.4, Cab≈40) → deeper absorption
        "albedo": np.array([
            0.030, 0.038, 0.032, 0.038, 0.048, 0.065,
            0.095, 0.132, 0.162, 0.172,
            0.164, 0.125, 0.080, 0.055, 0.042, 0.035, 0.032,
            0.250, 0.600, 0.770, 0.810,
        ]),
    },
    "sumac": {
        # Rhus typhina — sun-adapted, thin compound leaflets
        # (N≈1.3, Cab≈28, Car≈12 → warm green)
        "albedo": np.array([
            0.028, 0.035, 0.030, 0.038, 0.052, 0.070,
            0.112, 0.165, 0.210, 0.225,
            0.218, 0.170, 0.110, 0.078, 0.060, 0.048, 0.042,
            0.290, 0.650, 0.800, 0.835,
        ]),
    },
    "elderberry": {
        # Sambucus canadensis — compound leaf, woodland edge
        # Moderate (N≈1.4, Cab≈32)
        "albedo": np.array([
            0.034, 0.044, 0.038, 0.048, 0.058, 0.074,
            0.105, 0.148, 0.185, 0.198,
            0.190, 0.148, 0.096, 0.068, 0.054, 0.045, 0.040,
            0.270, 0.615, 0.780, 0.818,
        ]),
    },
    "mountain_laurel": {
        # Kalmia latifolia — evergreen, thick waxy leaf
        # (N≈1.8, Cab≈45) → very dark green, low effective albedo
        "albedo": np.array([
            0.028, 0.034, 0.028, 0.032, 0.038, 0.050,
            0.072, 0.098, 0.120, 0.128,
            0.122, 0.095, 0.065, 0.048, 0.040, 0.035, 0.032,
            0.210, 0.520, 0.710, 0.760,
        ]),
    },
    "dogwood": {
        # Cornus florida — understory tree/shrub, thin ovate leaf
        # (N≈1.4, Cab≈30)
        "albedo": np.array([
            0.035, 0.045, 0.040, 0.050, 0.060, 0.076,
            0.108, 0.150, 0.188, 0.200,
            0.192, 0.150, 0.098, 0.070, 0.056, 0.046, 0.042,
            0.272, 0.610, 0.775, 0.815,
        ]),
    },
    "sweet_pepperbush": {
        # Clethra alnifolia — wetland edge, moderate shade
        # (N≈1.5, Cab≈28)
        "albedo": np.array([
            0.034, 0.044, 0.038, 0.050, 0.058, 0.074,
            0.106, 0.148, 0.186, 0.200,
            0.192, 0.150, 0.098, 0.072, 0.058, 0.048, 0.044,
            0.268, 0.605, 0.770, 0.812,
        ]),
    },
}


def compute_species_color(name, stress_blend=0.0):
    """Compute sRGB color for a species.

    stress_blend: 0.0 = healthy, 1.0 = full stress (reduced chlorophyll).
    Stress blends toward dead_grass spectrum → yellower, lighter.
    """
    # Check both grass and shrub species dicts
    if name in SPECIES:
        sp = SPECIES[name]
    elif name in SHRUB_SPECIES:
        sp = SHRUB_SPECIES[name]
    else:
        raise KeyError(f"Unknown species: {name}")
    albedo_key = sp["albedo"].copy()

    if stress_blend > 0 and name not in ("dead_grass", "dead_grass_bleached"):
        dead_key = SPECIES["dead_grass"]["albedo"]
        albedo_key = albedo_key * (1 - stress_blend * 0.3) + dead_key * (stress_blend * 0.3)

    refl = interp_spectrum(WL_KEY, albedo_key)
    return spectrum_to_colors(refl)


# ═══════════════════════════════════════════════════════════════════════════
# Zone → species mapping
#
# Each zone has a primary species and optional adjustments:
#   chlorophyll_adj: >1 = lusher, <1 = more stressed
#   These modulate the reflectance curve shape (deeper/shallower absorption)
# ═══════════════════════════════════════════════════════════════════════════

ZONES = {
    0:  {"name": "SheepMeadow",    "species": "kentucky_bluegrass", "stress": 0.00,
         "note": "A-lawn, pristine maintenance"},
    1:  {"name": "GreatLawn",      "species": "kentucky_bluegrass", "stress": 0.00,
         "note": "Well-maintained, deeper soil"},
    2:  {"name": "NorthMeadow",    "species": "kentucky_bluegrass", "stress": 0.12,
         "note": "More sun exposure, drier → slight yellow shift"},
    3:  {"name": "FormalGarden",   "species": "perennial_ryegrass", "stress": 0.00,
         "note": "KBG/ryegrass mix, manicured"},
    4:  {"name": "SportsTurf",     "species": "kentucky_bluegrass", "stress": 0.05,
         "note": "Maintained but heavy foot traffic"},
    5:  {"name": "NorthWoods",     "species": "fine_fescue",        "stress": 0.00,
         "note": "Shade-tolerant understory"},
    6:  {"name": "Ramble",         "species": "fine_fescue",        "stress": 0.00,
         "note": "Dense woodland shade floor"},
    7:  {"name": "Waterside",      "species": "tussock_sedge",      "stress": 0.00,
         "note": "Riparian sedge"},
    8:  {"name": "WildMeadow",     "species": "switchgrass",        "stress": 0.00,
         "note": "Native grass meadow restoration"},
    9:  {"name": "OpenLawn",       "species": "kentucky_bluegrass", "stress": 0.00,
         "note": "Standard maintained lawn"},
    10: {"name": "Woodland_A",     "species": "fine_fescue",        "stress": 0.10,
         "note": "Woodland understory, leaf litter influence"},
    11: {"name": "Woodland_B",     "species": "fine_fescue",        "stress": 0.10,
         "note": "Woodland understory, leaf litter influence"},
}

# c_lo/c_hi spread: ±18% around base (matches current shader range)
LO_SCALE = 0.84
HI_SCALE = 1.16


# ═══════════════════════════════════════════════════════════════════════════
# Tuft biome mapping (for make_grass_tufts.py)
# ═══════════════════════════════════════════════════════════════════════════

TUFT_BIOMES = {
    "Tuft_Tiny": {
        "species": "kentucky_bluegrass",
        "tip_stress": 0.08,      # tips thinner → slight warm shift
        "dark_brightness": 0.75, # base/shadow
    },
    "Tuft_Woodland": {
        "species": "fine_fescue",
        "tip_stress": 0.06,
        "dark_brightness": 0.72,
    },
    "Tuft_Wild": {
        "species": "switchgrass",
        "tip_stress": 0.10,
        "dark_brightness": 0.75,
    },
    "Tuft_Meadow": {
        "species": "tussock_sedge",
        "tip_stress": 0.08,
        "dark_brightness": 0.72,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Compute and output
# ═══════════════════════════════════════════════════════════════════════════

def format_vec3(v):
    """Format as GLSL vec3."""
    return f"vec3({v[0]:.3f}, {v[1]:.3f}, {v[2]:.3f})"


def format_rgb_tuple(rgb8):
    """Format as Python RGB tuple."""
    return f"({rgb8[0]}, {rgb8[1]}, {rgb8[2]})"


def main():
    print("=" * 72)
    print("SPECTRAL COLOR PIPELINE — Central Park Walk")
    print("CIE 1931 2° Observer + D65 Illuminant")
    print("=" * 72)

    # ─── Species base colors ─────────────────────────────────────────
    print("\n─── Species Base Colors (leaf reflectance × transmittance) ──")
    print(f"{'Species':<22} {'Linear sRGB':<28} {'sRGB 8-bit':<18} {'XYZ Y'}")
    print("-" * 72)
    for name, sp in SPECIES.items():
        c = compute_species_color(name)
        lin_str = f"({c['linear'][0]:.4f}, {c['linear'][1]:.4f}, {c['linear'][2]:.4f})"
        rgb_str = f"({c['rgb8'][0]:>3}, {c['rgb8'][1]:>3}, {c['rgb8'][2]:>3})"
        print(f"{name:<22} {lin_str:<28} {rgb_str:<18} {c['xyz'][1]:.2f}")

    # ─── Zone palette (for grass_zone_colors.gdshaderinc) ────────────
    print("\n\n─── Zone Palette: grass_zone_colors.gdshaderinc ──────────")
    print("// Zone spectral palettes — derived from spectral reflectance data.")
    print("// Pipeline: R(λ) × CIE 1931 × D65 → XYZ → sRGB")
    print("// Generated by scripts/spectral_colors.py")
    print("void grass_zone_palette(int zone_id, out vec3 c_lo, out vec3 c_hi) {")

    for zid in sorted(ZONES.keys()):
        z = ZONES[zid]
        c = compute_species_color(z["species"], stress_blend=z["stress"])
        base = c["linear"]
        lo = base * LO_SCALE
        hi = base * HI_SCALE

        cond = "if" if zid == 0 else "} else if"
        # Group zones that share species
        if zid == 5:
            print(f"\t{cond} (zone_id == 5 || zone_id == 6) {{")
        elif zid == 6:
            continue  # handled with 5
        elif zid == 10:
            print(f"\t{cond} (zone_id == 10 || zone_id == 11) {{")
        elif zid == 11:
            continue  # handled with 10
        else:
            print(f"\t{cond} (zone_id == {zid}) {{")

        print(f"\t\t// {z['name']}: {z['species'].replace('_', ' ').title()} — {z['note']}")
        print(f"\t\tc_lo = {format_vec3(lo)};")
        print(f"\t\tc_hi = {format_vec3(hi)};")

    print("\t} else {")
    # Default: KBG average
    c = compute_species_color("kentucky_bluegrass")
    base = c["linear"]
    print(f"\t\t// Default: Kentucky Bluegrass average")
    print(f"\t\tc_lo = {format_vec3(base * LO_SCALE)};")
    print(f"\t\tc_hi = {format_vec3(base * HI_SCALE)};")
    print("\t}")
    print("}")

    # Dead tuft color
    dead_c = compute_species_color("dead_grass")
    print(f"\n// Dead tuft accent (spectral dried grass)")
    print(f"// vec3 dead_col = {format_vec3(dead_c['linear'])};")

    # ─── Tuft colors (for make_grass_tufts.py) ───────────────────────
    print("\n\n─── Tuft Colors: make_grass_tufts.py ────────────────────")
    for tuft_name, tb in TUFT_BIOMES.items():
        base_c = compute_species_color(tb["species"])
        tip_c = compute_species_color(tb["species"], stress_blend=tb["tip_stress"])
        dead_c = compute_species_color("dead_grass")
        dead_tip_c = compute_species_color("dead_grass_bleached")

        dark_rgb8 = np.round(np.clip(
            linear_to_gamma(base_c["linear"] * tb["dark_brightness"]), 0, 1
        ) * 255).astype(int)

        print(f'    "{tuft_name}": {{')
        print(f'        "color": {format_rgb_tuple(base_c["rgb8"])},')
        print(f'        "tip_color": {format_rgb_tuple(tip_c["rgb8"])},')
        print(f'        "dark_color": {format_rgb_tuple(dark_rgb8)},')
        print(f'        "dead_color": {format_rgb_tuple(dead_c["rgb8"])},')
        print(f'        "dead_tip_color": {format_rgb_tuple(dead_tip_c["rgb8"])},')
        print(f'    }},')

    # ─── Compute shader tints (for grass_compute.glsl) ───────────────
    print("\n\n─── Compute Shader Tints: grass_compute.glsl ────────────")
    biome_species = {
        0: "kentucky_bluegrass",  # lawn
        1: "fine_fescue",         # shade
        2: "switchgrass",         # wild
        3: "tussock_sedge",       # sedge
    }
    for biome_id, sp_name in biome_species.items():
        c = compute_species_color(sp_name)
        lin = c["linear"]
        print(f"// Biome {biome_id} ({sp_name}): tint_r = {lin[0]:.2f}; tint_g = {lin[1]:.2f};")

    # ─── Comparison with current values ──────────────────────────────
    print("\n\n─── Comparison: Current vs Spectral ─────────────────────")
    current_zones = {
        0: ((0.062, 0.195, 0.068), (0.088, 0.268, 0.096)),
        1: ((0.056, 0.186, 0.063), (0.080, 0.258, 0.088)),
        5: ((0.054, 0.156, 0.054), (0.078, 0.214, 0.078)),
        7: ((0.055, 0.156, 0.054), (0.080, 0.216, 0.080)),
        8: ((0.073, 0.192, 0.064), (0.104, 0.264, 0.086)),
    }
    print(f"{'Zone':<5} {'Channel':<8} {'Old c_lo':<10} {'New c_lo':<10} {'Old c_hi':<10} {'New c_hi':<10} {'Δ%'}")
    print("-" * 72)
    for zid, (old_lo, old_hi) in sorted(current_zones.items()):
        z = ZONES[zid]
        c = compute_species_color(z["species"], stress_blend=z["stress"])
        new_lo = c["linear"] * LO_SCALE
        new_hi = c["linear"] * HI_SCALE
        for ch, ch_name in enumerate(["R", "G", "B"]):
            delta_lo = (new_lo[ch] - old_lo[ch]) / old_lo[ch] * 100 if old_lo[ch] > 0 else 0
            delta_hi = (new_hi[ch] - old_hi[ch]) / old_hi[ch] * 100 if old_hi[ch] > 0 else 0
            print(f"{zid:<5} {ch_name:<8} {old_lo[ch]:<10.3f} {new_lo[ch]:<10.3f} "
                  f"{old_hi[ch]:<10.3f} {new_hi[ch]:<10.3f} {delta_hi:>+.0f}%")
        print()

    # ─── Undergrowth shrub colors (for make_undergrowth.py) ──────────
    print("\n\n─── Undergrowth Shrub Colors: make_undergrowth.py ─────────")
    print(f"{'Species':<22} {'Linear sRGB':<28} {'Gamma sRGB':<28} {'RGB8':<18}")
    print("-" * 96)
    for name in SHRUB_SPECIES:
        c = compute_species_color(name)
        lin_str = f"({c['linear'][0]:.4f}, {c['linear'][1]:.4f}, {c['linear'][2]:.4f})"
        gam_str = f"({c['gamma'][0]:.3f}, {c['gamma'][1]:.3f}, {c['gamma'][2]:.3f})"
        rgb_str = f"({c['rgb8'][0]:>3}, {c['rgb8'][1]:>3}, {c['rgb8'][2]:>3})"
        print(f"{name:<22} {lin_str:<28} {gam_str:<28} {rgb_str:<18}")

    # Ready-to-paste vertex color values (gamma-space for Blender vertex colors)
    print("\n# Vertex color values (gamma-space sRGB, for Blender vertex colors):")
    print("SHRUB_LEAF_COLORS = {")
    for name in SHRUB_SPECIES:
        c = compute_species_color(name)
        g = c["gamma"]
        print(f'    "{name}": ({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f}),')
    print("}")

    # Shadow variant (for stem-base darkening, 70% brightness)
    print("\n# Shadow variants (70% brightness, for understory shade):")
    print("SHRUB_SHADOW_COLORS = {")
    for name in SHRUB_SPECIES:
        c = compute_species_color(name)
        dark = np.clip(linear_to_gamma(c["linear"] * 0.70), 0, 1)
        print(f'    "{name}": ({dark[0]:.3f}, {dark[1]:.3f}, {dark[2]:.3f}),')
    print("}")

    # ─── Save reference JSON ─────────────────────────────────────────
    ref = {}
    for name in SPECIES:
        c = compute_species_color(name)
        ref[name] = {
            "linear_srgb": c["linear"].tolist(),
            "gamma_srgb": c["gamma"].tolist(),
            "rgb8": c["rgb8"].tolist(),
            "xyz": c["xyz"].tolist(),
        }
    for name in SHRUB_SPECIES:
        c = compute_species_color(name)
        ref[name] = {
            "linear_srgb": c["linear"].tolist(),
            "gamma_srgb": c["gamma"].tolist(),
            "rgb8": c["rgb8"].tolist(),
            "xyz": c["xyz"].tolist(),
        }
    ref_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "spectral_colors.json"
    )
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, "w") as f:
        json.dump(ref, f, indent=2)
    print(f"\nReference data saved to: {ref_path}")


if __name__ == "__main__":
    main()

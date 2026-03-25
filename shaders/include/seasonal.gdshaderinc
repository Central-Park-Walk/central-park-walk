// Unified season timing for Central Park Walk.
// season_t: 0.0 = spring equinox, 1.0 = summer, 2.0 = autumn, 3.0 = winter, 4.0 = wrap
//
// Three distinct seasonal concepts:
//   veg_*   — leaf phenology (color turn, leaf-out, dormancy)
//   canopy_*— tree cover density (shade, dapple on ground/water)
//   atmo_*  — atmospheric/ambient (sky color grading, wide-band)

// --- Vegetation color (tight band — leaves change fast) ---
float sn_veg_spring(float s) { return 1.0 - smoothstep(0.0, 1.0, s); }
float sn_veg_autumn(float s) { return smoothstep(2.0, 2.6, s) * (1.0 - smoothstep(2.8, 3.5, s)); }
float sn_veg_winter(float s) { return smoothstep(2.7, 3.1, s); }

// --- Canopy density (shade/dapple on surfaces below trees) ---
float sn_canopy_loss(float s) { return smoothstep(2.5, 3.2, s); }
float sn_canopy_bare(float s) { return smoothstep(3.0, 3.5, s); }
float sn_canopy_fill(float s) { return smoothstep(0.0, 0.4, s); }

// --- Atmosphere (wide band — sky/grading shifts earlier and lingers) ---
float sn_atmo_autumn(float s) { return smoothstep(1.5, 2.5, s) * (1.0 - smoothstep(2.5, 3.5, s)); }
float sn_atmo_winter(float s) { return smoothstep(2.5, 3.5, s); }
float sn_atmo_spring(float s) { return clamp(smoothstep(1.0, 0.0, s) + smoothstep(3.5, 4.0, s), 0.0, 1.0); }

// --- Warm season (spring through summer — moss, lichen, dew) ---
float sn_warm_season(float s) { return smoothstep(0.0, 1.0, s) * (1.0 - smoothstep(2.5, 3.5, s)); }

// --- Winter discard (deciduous plants shrink/vanish) ---
float sn_winter_kill(float s) { return smoothstep(3.2, 3.8, s); }

// --- Frost (snow/ice effects on surfaces) ---
float sn_frost(float s) { return smoothstep(2.8, 3.5, s); }

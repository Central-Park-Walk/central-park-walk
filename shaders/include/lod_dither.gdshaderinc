// Complementary screen-space ORDERED dither for the lod0-mesh <-> impostor crossfade.
//
// At the 40-80 m tier boundary both tiers render simultaneously; each screen pixel is
// drawn by exactly ONE tier per frame (water-tight — the two tiers share the same
// per-pixel threshold and use complementary comparisons). The dither pattern MUST be
// screen-space, not surface-anchored: the lod0 mesh and the flat impostor billboard are
// different geometry with no shared surface coordinate, so FRAGCOORD is the only common
// per-pixel key that keeps the split complementary (no gaps, no double-draw).
//
// NOISE SOURCE = a pre-baked BLUE-NOISE tile (textures/blue_noise_64.png, void-and-cluster,
// scripts/gen_blue_noise.py), NOT Interleaved Gradient Noise. IGN was chosen to be resolved
// by TAA into smooth alpha, but TAA is force-off under FSR2 (main.gd, a measured -4.6 ms
// perf win we are NOT giving back), so the *static* IGN pattern reads as a regular diagonal
// "screen-door" net on foliage. Blue noise is the deterministic, no-temporal fix: it is
// constructed so that EVERY thresholded level is high-frequency and evenly distributed, so
// thresholding it at the fade fraction gives fine even film-grain instead of a structured
// net — with zero dependence on any temporal filter. Sampled with texelFetch(coord % size)
// so it needs no sampler filter/repeat hints and returns the exact stored value.
//
// Registered by main.gd as a global sampler (GLOBAL_VAR_TYPE_SAMPLER2D) before the park
// materials are built, so every tier that includes this file shares one tile automatically.
global uniform sampler2D lod_blue_noise;

float _lod_dither_noise(vec2 frag_coord) {
	ivec2 tsz = textureSize(lod_blue_noise, 0);
	// Integer pixel coord, tiled across the screen. texelFetch ignores filtering/wrap,
	// so the value is exact and identical for both tiers at a given screen pixel.
	return texelFetch(lod_blue_noise, ivec2(frag_coord) % tsz, 0).r;
}

// Returns true if this fragment should be DISCARDED during a crossfade.
// fade_begin/fade_end: camera distance range of the crossfade zone.
// is_incoming: true = tier fading IN, false = tier fading OUT.
bool lod_dither_discard(float cam_dist, float fade_begin, float fade_end,
                        vec2 frag_coord, bool is_incoming) {
	// Outside the fade zone: fully drawn (incoming beyond end, outgoing before begin)
	if (!is_incoming && cam_dist < fade_begin) return false;  // outgoing: fully visible before fade
	if (is_incoming && cam_dist > fade_end) return false;     // incoming: fully visible after fade
	if (!is_incoming && cam_dist > fade_end) return true;     // outgoing: fully gone after fade
	if (is_incoming && cam_dist < fade_begin) return true;    // incoming: fully gone before fade

	float t = clamp((cam_dist - fade_begin) / (fade_end - fade_begin), 0.0, 1.0);
	float noise = _lod_dither_noise(frag_coord);

	if (is_incoming) {
		return noise > t;   // incoming: discard most at start, none at end
	} else {
		return noise < t;   // outgoing: discard none at start, most at end
	}
}

// Complementary dithered LOD crossfade — resolved by TAA into smooth blending.
//
// At tier boundaries, both outgoing and incoming tiers render simultaneously.
// Each screen pixel is drawn by exactly one tier per frame (water-tight).
// TAA jitter varies the pattern each frame, accumulating into smooth alpha.
//
// Interleaved Gradient Noise (Jimenez 2014) — minimal banding, good TAA response.

float _ign(vec2 frag_coord) {
	return fract(52.9829189 * fract(dot(frag_coord, vec2(0.06711056, 0.00583715))));
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
	float noise = _ign(frag_coord);

	if (is_incoming) {
		return noise > t;   // incoming: discard most at start, none at end
	} else {
		return noise < t;   // outgoing: discard none at start, most at end
	}
}

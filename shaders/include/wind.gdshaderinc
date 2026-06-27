// Shared wind biomechanics for vegetation shaders.
// Three models: cantilever (upright plants), pendulum (hanging vines), gust overlay.
//
// All models sample global uniform wind_vec (XZ direction + magnitude).

// --- Gust generation ---
// Periodic gust front that travels across the scene.
// Returns 0-1 strength; sharpened via squaring so gusts are brief peaks.
float wind_gust(vec3 origin, float freq, float sharpness_power) {
	float gust_phase = origin.x * 0.02 + origin.z * 0.03;
	float raw = sin(TIME * freq + gust_phase) * 0.5 + 0.5;
	// sharpness_power: 2.0 = soft gusts (undergrowth), 3.0 = sharp gusts (trees)
	return (sharpness_power > 2.5) ? raw * raw * raw : raw * raw;
}

// --- Cantilever trunk sway ---
// Upright plant displacement: zero at base, peaks at crown (h² curve).
// phase: spatial hash for per-instance variation.
// Returns XZ displacement to add to VERTEX.
vec2 wind_cantilever_trunk(float h, float sway_freq, float trunk_flex,
                           float rustle, float phase) {
	float trunk_h = h * h * 0.008;
	float dx = sin(TIME * 0.7 * sway_freq + phase) * trunk_flex * trunk_h * rustle;
	float dz = sin(TIME * 1.1 * sway_freq + phase * 1.3) * trunk_flex * trunk_h * 0.6 * rustle;
	return vec2(dx, dz);
}

// --- Secondary branch oscillation ---
// Higher frequency sway for branch-level detail (crown zone only).
vec2 wind_branch_sway(float h, float crown, float sway_freq, float branch_flex,
                      float branch_phase, float rustle,
                      float amp_x, float amp_z) {
	float dx = sin(TIME * 1.4 * sway_freq + branch_phase) * branch_flex * amp_x * h * crown * rustle;
	float dz = sin(TIME * 1.9 * sway_freq + branch_phase * 0.7) * branch_flex * amp_z * h * crown * rustle;
	return vec2(dx, dz);
}

// --- Constant wind push ---
// Steady lean in wind direction, proportional to height.
vec2 wind_push(vec2 wv, float h, float coeff, float trunk_flex) {
	return wv * h * coeff * mix(0.5, 1.0, trunk_flex);
}

// --- Per-instance spatial phase ---
// Hash from world-space origin to break synchronization between instances.
float wind_phase(vec3 origin) {
	return origin.x * 0.04 + origin.z * 0.06;
}

// --- Combined structural tree sway (trunk + branch + push + gust) ---
// SINGLE SOURCE OF TRUTH for the displacement that moves the woody skeleton.
// BOTH tree_bark and tree_leaf MUST call this with identical arguments so the leaf
// cluster cards stay glued to the branch tips they sit on. Divergent constants in
// the two shaders (leaf had bigger branch amp / push / gust than bark) made the
// cards translate off the limbs as the wind swung and snap back at the zero
// crossing — "limbs that split apart and rejoin" (user 2026-06-27). Any
// leaf-specific motion (the high-frequency blade flutter) is added by the leaf
// shader ON TOP of this shared base, never by changing these terms.
//   vertex      = local VERTEX (y = height up the model)
//   color       = per-vertex COLOR (r=hierarchy depth, g=branch extent, b=phase seed)
//   tree_origin = per-instance world origin (MODEL_MATRIX * 0)
//   wp          = WIND_PARAMS row (x=trunk_flex, y=branch_flex, z=sway_freq, w=gust_resp)
//   wv          = wind_vec (global)
//   wind_lod    = distance amplitude fade (1 near → 0 far); must match across shaders
vec3 wind_tree_sway(vec3 vertex, vec4 color, vec3 tree_origin, vec4 wp,
                    vec2 wv, float wind_lod) {
	float h = max(vertex.y, 0.0);
	float wind_str = length(wv);
	float rustle = (0.3 + wind_str * 0.7) * wind_lod;
	float phase = wind_phase(tree_origin);
	float branch_phase = color.b * 6.283 + phase;
	float crown = smoothstep(1.5, 4.0, h);
	// Thin, higher-order branches whip far more than the thick limb base.
	float branch_flex_w = wp.y * (1.0 + color.r * 1.8) * (0.6 + 0.4 * color.g);
	vec2 trunk_d  = wind_cantilever_trunk(h, wp.z, wp.x, rustle, phase);
	vec2 branch_d = wind_branch_sway(h, crown, wp.z, branch_flex_w, branch_phase, rustle, 0.06, 0.04);
	vec2 push_d   = wind_push(wv, h, 0.10, wp.x) * wind_lod;
	float gust = wind_gust(tree_origin, 0.3, 3.0);
	float gust_strength = gust * wind_str * 0.20 * wp.w * wind_lod;
	return vec3(trunk_d.x + branch_d.x + push_d.x + wv.x * h * gust_strength,
	            0.0,
	            trunk_d.y + branch_d.y + push_d.y + wv.y * h * gust_strength);
}

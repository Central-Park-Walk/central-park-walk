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

shader_type spatial;
render_mode cull_disabled;

// Grass impostor: flat plane per chunk that replicates the look of
// 3D grass blades using world-space texture sampling. Bridges the gap
// between full-geometry blades (0-35m) and terrain shader grass (100m+).
// Based on hexaquo LOD Part 4.

#include "res://shaders/include/hash_noise.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;

uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;

// Per-instance alpha for crossfade (set by grass_builder.gd)
instance uniform float alpha : hint_range(0.0, 1.0) = 1.0;

varying vec3 v_world_pos;

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 wuv = v_world_pos.xz;

	// --- Patch noise (same as blade shader) ---
	float patch_factor = vnoise(wuv / 3.0);

	// --- Grass type from atlas zone (simplified: assume lawn=0 for impostor) ---
	// In the terrain shader, zone data drives color. Here we approximate
	// with a spatial hash since impostors are flat planes without per-blade data.
	float zone_hash = vnoise(wuv * 0.002);  // very broad spatial variation
	float grass_type = zone_hash < 0.3 ? 0.0 : (zone_hash < 0.6 ? 2.0 : 5.0);

	// --- Color (matching blade shader zone colors) ---
	vec3 color_small, color_large;
	if (grass_type < 0.5) {
		// Lawn: cool blue-green
		color_small = vec3(0.06, 0.30, 0.10);
		color_large = vec3(0.15, 0.40, 0.14);
	} else if (grass_type < 2.5) {
		// Meadow/field: warm yellow-green
		color_small = vec3(0.10, 0.28, 0.06);
		color_large = vec3(0.22, 0.42, 0.12);
	} else {
		// Woodland: dark blue-green
		color_small = vec3(0.04, 0.20, 0.06);
		color_large = vec3(0.08, 0.32, 0.10);
	}

	ALBEDO = mix(color_small, color_large, patch_factor);

	// --- Viewing angle adjustment (hexaquo) ---
	// Looking across grass at a low angle = see more blade tips (lighter)
	// Looking straight down = see more ground between blades (darker)
	float normal_to_view = 1.0 - abs(dot(VIEW, vec3(0.0, 1.0, 0.0)));
	ALBEDO = mix(ALBEDO, color_large, normal_to_view * 0.3);

	// --- High-frequency detail: simulated blade pattern ---
	float hf = vnoise(wuv * 8.0);  // blade-scale noise
	float hf2 = vnoise(wuv * 24.0 + vec2(17.3, 41.7));  // finer detail

	// Ground visibility: at steep angles, see dirt between blades
	float ground_color_mix = (1.0 - normal_to_view) * 0.4 - patch_factor * 0.15;
	float ground_factor = smoothstep(ground_color_mix + 0.1, ground_color_mix - 0.1, hf);
	vec3 ground_col = vec3(0.12, 0.10, 0.06);  // dark earth
	ALBEDO = mix(ALBEDO, ground_col, ground_factor * 0.35);

	// --- Wind AO (matching blade shader wind calculation) ---
	float wind_str = length(wind_vec);
	float px = wuv.x * 0.15 + wuv.y * 0.22;
	float gust_phase = wuv.x * 0.04 + wuv.y * 0.05;
	float gust = sin(TIME * 0.5 + gust_phase) * 0.5 + 0.5;
	gust = gust * gust * gust;
	float wind_ao = (wind_str * 0.3 + gust * wind_str * 0.2);

	// AO from simulated blade depth
	float ao = mix(0.6, 1.0, hf) - wind_ao * 0.15;
	AO = clamp(ao, 0.0, 1.0);

	// --- Normal: subtle grass-like normal variation ---
	// Approximate blade normals with high-frequency noise
	vec3 grass_normal = vec3(
		(hf2 - 0.5) * 0.3,
		1.0,
		(vnoise(wuv * 24.0 + vec2(83.1, 29.4)) - 0.5) * 0.3
	);
	NORMAL = normalize(mix(vec3(0.0, 1.0, 0.0), normalize(grass_normal), 0.4));

	// --- Lighting (matching blade shader) ---
	BACKLIGHT = vec3(0.15);
	ROUGHNESS = 0.45;
	SPECULAR = 0.10;
	AO_LIGHT_AFFECT = 1.0;

	// --- Seasonal color shift ---
	float autumn_t = smoothstep(2.0, 3.0, season_t);
	if (autumn_t > 0.0) {
		ALBEDO = mix(ALBEDO, ALBEDO * vec3(1.08, 0.90, 0.70), autumn_t * 0.6);
	}
	float winter_t = smoothstep(3.0, 3.5, season_t);
	if (winter_t > 0.0) {
		vec3 dormant = vec3(0.22, 0.18, 0.10);
		ALBEDO = mix(ALBEDO, dormant, winter_t * 0.7);
	}

	// Snow cover
	if (snow_cover > 0.01) {
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.94, 0.96), snow_cover * 0.8);
		ROUGHNESS = mix(ROUGHNESS, 0.9, snow_cover);
	}

	// Rain wetness
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.7, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.15, rain_wetness * 0.6);
	}

	// Canopy shade
	vec2 canopy_uv = (v_world_pos.xz + hm_world_size * 0.5) / hm_world_size;
	float canopy_shade = texture(canopy_map, canopy_uv).r;
	if (canopy_shade > 0.1) {
		ALBEDO *= mix(1.0, 0.65, canopy_shade);
	}

	// --- Alpha crossfade ---
	// Blend toward ground as alpha decreases (fading out at close range
	// where real blades take over, or at far range where terrain takes over)
	ALBEDO = mix(ground_col, ALBEDO, alpha);
	ALPHA = alpha;
	ALPHA_HASH_SCALE = 1.0;
}

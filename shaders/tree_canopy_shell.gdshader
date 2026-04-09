shader_type spatial;
render_mode cull_disabled, depth_prepass_alpha;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"
#include "res://shaders/include/tree_species.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

uniform sampler2D canopy_tex : source_color, filter_linear_mipmap;

varying vec3 v_canopy_color;
varying float v_canopy_alpha;

void vertex() {
	// INSTANCE_CUSTOM: R=phenology/13, G=timing+0.5, B=evergreen, A=color_jitter
	int sp = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	float timing = INSTANCE_CUSTOM.g;
	float evergreen = INSTANCE_CUSTOM.b;

	// Seasonal color (same logic as tree_leaf)
	float s = season_t + timing * 0.3;
	vec3 summer_col = SUMMER_COLORS[sp];
	vec3 fall_col = FALL_COLORS[sp];

	float spring_t = smoothstep(0.0, 0.8, s) * smoothstep(1.2, 0.8, s);
	float fall_t = smoothstep(1.8, 2.5, s) * (1.0 - smoothstep(2.8, 3.2, s));
	float late_fall = smoothstep(2.8, 3.4, s);
	float winter_bare = smoothstep(3.0, 3.5, s);

	vec3 col = summer_col;
	vec3 spring_tint = summer_col * vec3(1.15, 1.20, 0.75);
	col = mix(spring_tint, summer_col, spring_t);
	col = mix(col, fall_col, fall_t);
	col = mix(col, fall_col * 0.5, late_fall * 0.6);

	// Evergreen stays green
	if (evergreen > 0.5) {
		col = summer_col;
	}

	v_canopy_color = col;
	// Winter: canopy shell becomes transparent (bare branches)
	v_canopy_alpha = mix(1.0, 0.0, winter_bare * (1.0 - evergreen));

	// ---- Organic silhouette noise ----
	// Subtle displacement to break up the perfect hemisphere.
	// Goal: irregular crown edge, not alien egg pod.
	vec3 world_pos = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float tree_id = world_pos.x * 0.173 + world_pos.z * 0.317;

	// Fine-grain noise — small bumps that roughen the silhouette edge
	vec2 disp_seed = VERTEX.xz * 5.0 + vec2(tree_id, tree_id * 0.7);
	float bump = vnoise(disp_seed) * 0.06
	           + vnoise(disp_seed * 3.1 + vec2(7.1, 3.3)) * 0.03;
	// Inward pulls create gaps/holes in the canopy silhouette (more natural)
	bump -= 0.02;
	// Strongest at equator (silhouette edge), gentle on top
	float equator_weight = sin(acos(clamp(NORMAL.y, 0.0, 1.0)));
	VERTEX += NORMAL * bump * equator_weight;

	// ---- Species-specific wind sway (simplified LOD1) ----
	vec4 wp = WIND_PARAMS[sp];
	float wind_str = length(wind_vec);
	float phase = world_pos.x * 0.07 + world_pos.z * 0.11;
	// Trunk sway: amplitude scaled by species flexibility
	float sway_amp = 0.02 * mix(0.5, 1.0, wp.x);
	float sway = sin(TIME * 0.8 * wp.z + phase) * sway_amp * wind_str;
	VERTEX.x += sway * VERTEX.y;
	// Branch shimmer: slight cross-axis flutter
	float shimmer = sin(TIME * 1.6 * wp.z + phase * 1.5) * 0.008 * wp.y * wind_str;
	VERTEX.z += shimmer * VERTEX.y;
	// Gust response
	float gust_ph = world_pos.x * 0.02 + world_pos.z * 0.03;
	float gust = sin(TIME * 0.3 + gust_ph) * 0.5 + 0.5;
	gust = gust * gust * gust;
	VERTEX.x += wind_vec.x * VERTEX.y * gust * wind_str * 0.015 * wp.w;
	VERTEX.z += wind_vec.y * VERTEX.y * gust * wind_str * 0.015 * wp.w;
}

void fragment() {
	// Sample canopy texture
	vec4 tex = texture(canopy_tex, UV);
	float alpha = tex.a * v_canopy_alpha;

	// Mip-level alpha compensation: counteract coverage loss from mipmap averaging
	float delta_max = max(length(dFdx(UV)), length(dFdy(UV)));
	float mip_level = max(log2(max(delta_max * 1024.0, 1.0)), 0.0);
	alpha *= 1.0 + mip_level * 0.3;
	alpha = min(alpha, 1.0);

	if (alpha < 0.3) discard;

	vec3 col = v_canopy_color;

	// Top-lit gradient: sunlit top, darker underside
	vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
	float top_lit = world_n.y * 0.5 + 0.5;  // 0=bottom, 1=top
	col *= mix(0.55, 1.15, top_lit);

	// Per-pixel variation from texture luminance
	float tex_lum = dot(tex.rgb, vec3(0.3, 0.6, 0.1));
	col *= (0.7 + tex_lum * 0.5);

	// Aerial perspective (matches tree_leaf.gdshader exactly)
	vec3 shell_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float shell_dist = length(shell_world - INV_VIEW_MATRIX[3].xyz);
	float shell_aerial = smoothstep(200.0, 500.0, shell_dist);
	col = apply_aerial(col, shell_aerial, 0.30, 0.30, sky_reflect_color);

	ALBEDO = col;
	ROUGHNESS = 0.85;
	SPECULAR = 0.06;
	METALLIC = 0.0;

	// Backlight — canopy shell glows when backlit
	BACKLIGHT = v_canopy_color * 0.3;

	// Snow
	if (snow_cover > 0.01) {
		float upward = max(world_n.y, 0.0);
		float snow_on = upward * snow_cover;
		ALBEDO = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_on * 0.55);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_on * 0.4);
	}

	// Rain
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.70, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.45, rain_wetness);
	}

	ALPHA = alpha;
}

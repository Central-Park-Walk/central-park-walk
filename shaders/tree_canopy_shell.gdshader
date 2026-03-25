shader_type spatial;
render_mode cull_disabled, depth_prepass_alpha;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

uniform sampler2D canopy_tex : source_color, filter_linear_mipmap;

// Species color data (same as tree_leaf.gdshader)
const vec3 SUMMER_COLORS[16] = vec3[16](
	vec3(0.20, 0.42, 0.12),   // 0 oak
	vec3(0.22, 0.44, 0.14),   // 1 maple
	vec3(0.18, 0.40, 0.12),   // 2 elm
	vec3(0.28, 0.48, 0.18),   // 3 birch
	vec3(0.20, 0.42, 0.14),   // 4 deciduous
	vec3(0.08, 0.22, 0.06),   // 5 conifer
	vec3(0.24, 0.46, 0.12),   // 6 honeylocust
	vec3(0.28, 0.48, 0.18),   // 7 callery_pear
	vec3(0.32, 0.52, 0.10),   // 8 ginkgo
	vec3(0.22, 0.40, 0.14),   // 9 london_plane
	vec3(0.22, 0.42, 0.14),   // 10 linden
	vec3(0.30, 0.50, 0.20),   // 11 cherry
	vec3(0.20, 0.40, 0.12),   // 12 willow
	vec3(0.18, 0.35, 0.12),   // 13 magnolia
	vec3(0.20, 0.42, 0.12),   // 14 cathedral_elm
	vec3(0.0)                  // 15 dead (unused)
);

const vec3 FALL_COLORS[16] = vec3[16](
	vec3(0.55, 0.25, 0.08),   // 0 oak: russet-brown
	vec3(0.75, 0.30, 0.08),   // 1 maple: flame red-orange
	vec3(0.60, 0.52, 0.18),   // 2 elm: muted gold
	vec3(0.72, 0.62, 0.15),   // 3 birch: bright gold
	vec3(0.55, 0.42, 0.12),   // 4 deciduous: generic amber
	vec3(0.08, 0.22, 0.06),   // 5 conifer: stays green
	vec3(0.68, 0.58, 0.12),   // 6 honeylocust: golden yellow
	vec3(0.60, 0.28, 0.15),   // 7 callery_pear: red-purple
	vec3(0.80, 0.72, 0.10),   // 8 ginkgo: brilliant yellow
	vec3(0.52, 0.38, 0.12),   // 9 london_plane: tan-brown
	vec3(0.62, 0.55, 0.12),   // 10 linden: gold-yellow
	vec3(0.65, 0.30, 0.12),   // 11 cherry: orange-red
	vec3(0.58, 0.50, 0.15),   // 12 willow: muted gold
	vec3(0.50, 0.35, 0.10),   // 13 magnolia: brown-gold
	vec3(0.60, 0.52, 0.18),   // 14 cathedral_elm
	vec3(0.0)                  // 15 dead
);

// Per-species wind biomechanics: (trunk_flex, branch_flex, sway_freq, gust_response)
const vec4 WIND_PARAMS[14] = vec4[14](
	vec4(0.15, 0.45, 0.70, 0.50),  // 0 oak
	vec4(0.35, 0.55, 0.90, 0.60),  // 1 maple
	vec4(0.45, 0.70, 0.85, 0.65),  // 2 elm
	vec4(0.70, 0.50, 1.20, 0.80),  // 3 birch
	vec4(0.35, 0.50, 0.90, 0.55),  // 4 deciduous
	vec4(0.20, 0.25, 0.60, 0.35),  // 5 conifer
	vec4(0.40, 0.65, 1.05, 0.70),  // 6 honeylocust
	vec4(0.25, 0.40, 0.95, 0.45),  // 7 callery_pear
	vec4(0.20, 0.30, 0.75, 0.40),  // 8 ginkgo
	vec4(0.30, 0.45, 0.80, 0.50),  // 9 london_plane
	vec4(0.35, 0.50, 0.90, 0.55),  // 10 linden
	vec4(0.50, 0.55, 1.15, 0.65),  // 11 cherry
	vec4(0.85, 0.95, 0.75, 0.90),  // 12 willow
	vec4(0.25, 0.35, 0.80, 0.40)   // 13 magnolia
);

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
	// Sample canopy texture — texture itself has ~45% coverage with leaf gaps
	vec4 tex = texture(canopy_tex, UV);
	float alpha = tex.a * v_canopy_alpha;
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

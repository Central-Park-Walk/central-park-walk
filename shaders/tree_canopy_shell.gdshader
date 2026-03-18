shader_type spatial;
render_mode cull_disabled, depth_prepass_alpha;

#include "res://shaders/include/hash_noise.gdshaderinc"

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

varying vec3 v_canopy_color;
varying float v_canopy_alpha;

void vertex() {
	// INSTANCE_CUSTOM: R=phenology_idx, G=timing_offset, B=evergreen, A=species_idx
	float pheno_idx = INSTANCE_CUSTOM.r;
	float timing = INSTANCE_CUSTOM.g;
	float evergreen = INSTANCE_CUSTOM.b;
	int sp = int(INSTANCE_CUSTOM.a * 15.0 + 0.5);

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
	vec3 disp_seed = VERTEX * 5.0 + vec3(tree_id);
	float bump = vnoise(disp_seed) * 0.06
	           + vnoise(disp_seed * 3.1 + vec3(7.1)) * 0.03;
	// Inward pulls create gaps/holes in the canopy silhouette (more natural)
	bump -= 0.02;
	// Strongest at equator (silhouette edge), gentle on top
	float equator_weight = sin(acos(clamp(NORMAL.y, 0.0, 1.0)));
	VERTEX += NORMAL * bump * equator_weight;

	// ---- Wind sway ----
	float wind_str = length(wind_vec);
	float phase = world_pos.x * 0.07 + world_pos.z * 0.11;
	float sway = sin(TIME * 0.8 + phase) * 0.02 * wind_str;
	VERTEX.x += sway * VERTEX.y;
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
	if (shell_aerial > 0.01) {
		float al = dot(col, vec3(0.2126, 0.7152, 0.0722));
		col = mix(col, vec3(al), shell_aerial * 0.30);
		col = mix(col, col * vec3(0.94, 0.96, 1.04), shell_aerial);
		float sky_l = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
		vec3 haze = mix(vec3(0.58, 0.56, 0.52), sky_reflect_color * 0.8 + vec3(0.20), 0.35);
		float night_f = smoothstep(0.15, 0.02, sky_l);
		haze = mix(haze, vec3(0.14, 0.10, 0.06), night_f * 0.6);
		col = mix(col, haze, shell_aerial * 0.30);
	}

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

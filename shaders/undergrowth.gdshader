shader_type spatial;
render_mode cull_disabled;

#include "res://shaders/include/hash_noise.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

uniform float wind_flex : hint_range(0.0, 1.0) = 0.4;
uniform float is_evergreen : hint_range(0.0, 1.0) = 0.0;
uniform vec3 fall_tint = vec3(0.5, 0.35, 0.08);
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;

// Leaf texture atlas (4-col grid, variable rows, 512px per species cell)
uniform sampler2D leaf_atlas : filter_linear, repeat_disable;
uniform vec2 atlas_offset = vec2(0.0, 0.0);  // species cell position in atlas (UV space)
uniform vec2 atlas_cell_size = vec2(0.25, 0.25);  // cell size in UV space (1/cols, 1/rows)
uniform float use_atlas = 0.0;  // 1.0 = sample atlas, 0.0 = procedural only

varying vec3 v_world_pos;
varying float v_seed;
varying float v_wind_amount;

void vertex() {
	vec3 instance_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_world_pos = instance_origin;
	v_seed = INSTANCE_CUSTOM.r;

	// -- Wind sway --
	float sway = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);
	float flex = wind_flex;

	float px = instance_origin.x * 0.08 + instance_origin.z * 0.12;
	float pz = instance_origin.z * 0.10 + instance_origin.x * 0.06;

	float rustle = (0.15 + wind_str * 0.6) * flex;
	VERTEX.x += sin(TIME * 1.2 + px) * 0.08 * sway * rustle;
	VERTEX.z += sin(TIME * 1.5 + pz) * 0.06 * sway * rustle;

	VERTEX.x += wind_vec.x * sway * 0.25 * flex;
	VERTEX.z += wind_vec.y * sway * 0.25 * flex;

	float gust_phase = instance_origin.x * 0.03 + instance_origin.z * 0.04;
	float gust = sin(TIME * 0.4 + gust_phase) * 0.5 + 0.5;
	gust = gust * gust;
	float gust_str = gust * wind_str * 0.3 * flex;
	VERTEX.x += wind_vec.x * sway * gust_str;
	VERTEX.z += wind_vec.y * sway * gust_str;

	v_wind_amount = (rustle + gust_str) * sway * 0.5;

	// Winter die-back
	float winter_t = smoothstep(3.0, 3.5, season_t);
	if (winter_t > 0.0 && is_evergreen < 0.5) {
		VERTEX.y *= mix(1.0, 0.1, winter_t);
	}
}

void fragment() {
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// ---- LEAF vs STEM detection from UV ----
	// UV.x = 0..1 across leaf cards, UV.x ≈ 0.5 for stems
	float edge_dist = abs(UV.x - 0.5) * 2.0;
	float is_leaf = smoothstep(0.05, 0.2, edge_dist);

	// ---- ALPHA CUTOUT (atlas or procedural) ----
	float leaf_alpha = 1.0;
	vec3 tex_color = COLOR.rgb;

	if (use_atlas > 0.5) {
		// Sample species-specific leaf texture from atlas
		vec2 atlas_uv = atlas_offset + UV * atlas_cell_size;
		vec4 tex = texture(leaf_atlas, atlas_uv);

		// Blend: stems use vertex color, leaves use atlas
		tex_color = mix(COLOR.rgb, tex.rgb, is_leaf * step(0.1, tex.a));
		leaf_alpha = mix(1.0, tex.a, is_leaf);
	} else {
		// Procedural leaf shape from UV
		float leaf_width = sin(UV.y * 3.14159) * (1.0 - UV.y * 0.25);
		float edge_noise = vnoise(UV * 6.0 + vec2(v_seed * 13.0, v_seed * 7.0)) * 0.12;
		leaf_width += edge_noise;
		float proc_mask = smoothstep(leaf_width, leaf_width - 0.06, edge_dist);
		leaf_alpha = mix(1.0, proc_mask, is_leaf);
	}

	if (leaf_alpha < 0.35) discard;

	// ---- HEMISPHERE NORMALS ----
	vec3 outward = normalize(vec3(VERTEX.x, VERTEX.y * 0.25, VERTEX.z));
	NORMAL = normalize(mix(NORMAL, outward, 0.45));
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// Winter discard
	float winter_discard = smoothstep(3.2, 3.8, season_t);
	if (winter_discard > 0.95 && is_evergreen < 0.5) discard;

	// ---- COLOR ----
	vec3 col = tex_color;

	// Per-instance hue variation
	col *= mix(vec3(0.95, 1.02, 1.04), vec3(1.05, 0.98, 0.94), v_seed);

	// Broad spatial variation
	float broad = vnoise(v_world_pos.xz / 10.0);
	col *= mix(0.90, 1.10, broad);

	// ---- AO from vertex height ----
	// Steeper curve at ground contact — mushrooms and low plants get dark
	// base where they meet the grass, preventing the "floating" look.
	float height_frac = clamp(VERTEX.y / 3.0, 0.0, 1.0);
	float ao = mix(0.30, 1.0, smoothstep(0.0, 0.4, height_frac)) - v_wind_amount * 0.2;
	AO = clamp(ao, 0.0, 1.0);
	AO_LIGHT_AFFECT = 1.0;

	// ---- SEASONAL COLOR ----
	float spring_t = 1.0 - smoothstep(0.0, 1.0, season_t);
	float autumn_t = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(2.8, 3.5, season_t));
	float winter_t = smoothstep(2.7, 3.1, season_t);

	col = mix(col, col * vec3(1.1, 1.15, 0.80), spring_t * 0.5);
	if (is_evergreen < 0.5) {
		col = mix(col, fall_tint, autumn_t * 0.65);
		col = mix(col, vec3(0.14, 0.10, 0.06), winter_t);
	}

	// Wind color shift
	float wind_darken = v_wind_amount * length(wind_vec) * 0.15;
	col *= (1.0 - wind_darken);

	// Canopy shade
	{
		vec2 canopy_uv = (v_world_pos.xz + hm_world_size * 0.5) / hm_world_size;
		float canopy = texture(canopy_map, canopy_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = smoothstep(2.5, 3.2, season_t);
			float winter_bare = smoothstep(3.0, 3.5, season_t);
			float spring_fill = smoothstep(0.0, 0.4, season_t);
			float sc = canopy * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare) * mix(0.5, 1.0, spring_fill);
			vec2 dapple_uv = v_world_pos.xz * 0.3 + wind_vec * TIME * 0.06;
			float dapple = vnoise(dapple_uv);
			float light_gap = smoothstep(0.35, 0.65, dapple);
			float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum);
			float shade = sc * sun_factor;
			col *= (1.0 - shade * (1.0 - light_gap) * 0.30);
		}
	}

	ALBEDO = col;

	// Roughness varies with height: lower stems rougher, upper leaves glossier
	ROUGHNESS = mix(0.72, 0.48, height_frac);
	SPECULAR = mix(0.08, 0.16, height_frac);
	METALLIC = 0.0;
	// Green-gold transmission — ferns and herbs are thin-leaved and glow
	// when backlit; shrubs are thicker and transmit less.
	// v_seed encodes species info; higher height_frac = more leaf, more SSS.
	BACKLIGHT = vec3(0.30, 0.35, 0.10) * mix(0.5, 1.0, height_frac);

	// ---- WEATHER ----
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.70, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.30, rain_wetness);
	}

	if (snow_cover > 0.01) {
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		float snow_on = upward * snow_cover;
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_on * 0.55);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_on * 0.4);
	}

	// ---- DISTANCE LOD (alpha hash fade) ----
	float cam_dist = length(v_world_pos - INV_VIEW_MATRIX[3].xyz);
	float fade_start = 35.0;
	float fade_end = 45.0;
	float alpha = 1.0 - smoothstep(fade_start, fade_end, cam_dist);
	AO_LIGHT_AFFECT = mix(0.3, 1.0, alpha);
	NORMAL = mix(NORMAL, vec3(0.0, 1.0, 0.0), 1.0 - alpha);
	ALPHA = alpha;
	ALPHA_HASH_SCALE = 1.0;
}

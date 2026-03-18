shader_type spatial;
render_mode cull_disabled;

#include "res://shaders/include/hash_noise.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

uniform float wind_flex : hint_range(0.0, 1.0) = 0.3;
uniform float is_seasonal : hint_range(0.0, 1.0) = 1.0; // 0=always visible, 1=seasonal
uniform float is_litter : hint_range(0.0, 1.0) = 0.0;   // 1=fallen leaves/twigs
uniform float hm_world_size = 5000.0;
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform sampler2D cover_atlas : filter_linear;
uniform vec2 atlas_offset = vec2(0.0, 0.0);     // cell origin in atlas UV
uniform vec2 atlas_cell_size = vec2(0.25, 0.5);  // 4 cols, 2 rows

varying vec3 v_world_pos;
varying float v_seed;
varying float v_scale;
varying float v_wind_amount;

void vertex() {
	v_world_pos = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_seed = INSTANCE_CUSTOM.r;
	v_scale = INSTANCE_CUSTOM.g;

	float sway = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);

	// Wind sway — lighter than undergrowth, ground-hugging
	float flex = wind_flex * (1.0 - is_litter * 0.8); // litter barely moves
	float rustle = (0.10 + wind_str * 0.5) * flex;

	vec2 blade_xz = v_world_pos.xz;
	float px = blade_xz.x * 0.12 + blade_xz.y * 0.18;
	float pz = blade_xz.y * 0.15 + blade_xz.x * 0.10;
	VERTEX.x += sin(TIME * 1.5 + px) * 0.08 * sway * rustle;
	VERTEX.z += sin(TIME * 2.0 + pz) * 0.06 * sway * rustle;

	// Wind push
	VERTEX.x += wind_vec.x * sway * 0.25 * flex;
	VERTEX.z += wind_vec.y * sway * 0.25 * flex;

	v_wind_amount = rustle * sway * 0.4;

	// Winter dormancy — living plants shrink, litter stays
	float winter_t = smoothstep(3.0, 3.5, season_t);
	if (winter_t > 0.0 && is_seasonal > 0.5 && is_litter < 0.5) {
		VERTEX.y *= mix(1.0, 0.08, winter_t);
	}
}

void fragment() {
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// Winter discard for living plants
	float winter_discard = smoothstep(3.2, 3.8, season_t);
	if (winter_discard > 0.95 && is_seasonal > 0.5 && is_litter < 0.5) discard;

	// Litter visibility: only in autumn/winter (season_t > 2.0)
	if (is_litter > 0.5) {
		float litter_vis = smoothstep(1.8, 2.3, season_t);
		// Also visible in early spring (leftover from winter)
		litter_vis = max(litter_vis, 1.0 - smoothstep(0.0, 0.5, season_t));
		if (litter_vis < 0.1) discard;
	}

	// Aerial discard — reduce noise from above
	float cam_h = INV_VIEW_MATRIX[3].y - v_world_pos.y;
	if (cam_h > 10.0) {
		float aerial_discard = smoothstep(10.0, 30.0, cam_h);
		float ad = hash2(v_world_pos.xz * 1.5 + vec2(33.7, 51.2));
		if (ad < aerial_discard) discard;
	}

	// Sample shared atlas texture
	vec2 atlas_uv = atlas_offset + UV * atlas_cell_size;
	vec4 tex_col = texture(cover_atlas, atlas_uv);
	if (tex_col.a < 0.35) discard;
	vec3 col = tex_col.rgb;

	// Per-instance color variation
	col *= mix(vec3(0.92, 1.04, 1.06), vec3(1.08, 0.96, 0.92), v_seed);

	// Broad spatial variation (8m scale)
	float broad = vnoise(v_world_pos.xz / 8.0);
	col *= mix(0.88, 1.12, broad);

	// Seasonal color
	float spring_t = 1.0 - smoothstep(0.0, 1.0, season_t);
	float autumn_t = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(2.8, 3.5, season_t));
	float winter_t = smoothstep(2.7, 3.1, season_t);

	if (is_litter < 0.5) {
		// Living plants — seasonal tinting
		col = mix(col, col * vec3(1.08, 1.12, 0.78), spring_t * 0.5);
		col = mix(col, col * vec3(1.30, 0.70, 0.30), autumn_t * 0.6);
		col = mix(col, vec3(0.14, 0.10, 0.06), winter_t);
	}
	// Litter stays its baked color (already brown/orange)

	// AO — darken near ground
	float height_frac = clamp(VERTEX.y / 0.5, 0.0, 1.0);
	AO = mix(0.35, 1.0, height_frac);
	AO_LIGHT_AFFECT = 1.0;

	// Canopy shade
	vec2 canopy_uv = (v_world_pos.xz + hm_world_size * 0.5) / hm_world_size;
	float canopy = texture(canopy_map, canopy_uv).r;
	if (canopy > 0.01) {
		float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
		float sun_factor = smoothstep(0.02, 0.20, sky_lum);
		vec2 dapple_uv = v_world_pos.xz * 0.35 + wind_vec * TIME * 0.08;
		float dapple = vnoise(dapple_uv);
		float light_gap = smoothstep(0.35, 0.65, dapple);
		float shade = canopy * sun_factor;
		col *= (1.0 - shade * (1.0 - light_gap) * 0.30);
	}

	ALBEDO = col;

	// Material — ground cover is rougher than tree leaves
	ROUGHNESS = mix(0.78, 0.60, height_frac);
	SPECULAR = mix(0.05, 0.10, height_frac);
	METALLIC = 0.0;

	// Backlight transmission for living plants
	if (is_litter < 0.5) {
		BACKLIGHT = vec3(0.20, 0.25, 0.06) * mix(0.4, 1.0, height_frac);
	}

	// Weather
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

	// Distance LOD — alpha hash fade
	float cam_dist = length(v_world_pos - INV_VIEW_MATRIX[3].xyz);
	float alpha = 1.0 - smoothstep(18.0, 25.0, cam_dist);
	NORMAL = mix(NORMAL, vec3(0.0, 1.0, 0.0), 1.0 - alpha);
	ALPHA = alpha;
	ALPHA_HASH_SCALE = 1.0;
}

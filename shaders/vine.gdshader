shader_type spatial;
render_mode cull_disabled;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/seasonal.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

uniform float wind_flex : hint_range(0.0, 1.0) = 0.6;
uniform float is_trunk_wrap : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;

// INSTANCE_CUSTOM encoding:
//   R = species index (0.0=VA creeper, 0.143=ivy, 0.286=bittersweet,
//       0.429=porcelain berry, 0.571=wild grape, 0.714=honeysuckle, 0.857=wisteria)
//   G = seed (0-1 variation)
//   B = height fraction (0=base, 1=canopy)
//   A = vine age (0.3=young, 1.0=old)

varying vec3 v_world_pos;
varying float v_seed;
varying float v_species;
varying float v_wind_amount;

void vertex() {
	vec3 instance_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_world_pos = instance_origin;
	v_seed = INSTANCE_CUSTOM.g;
	v_species = INSTANCE_CUSTOM.r;

	// Wind: hanging vines sway more than rooted plants
	float sway_base = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);
	float flex = wind_flex;

	if (is_trunk_wrap < 0.5) {
		// Hanging strand: pendulum sway from attachment point
		// Lower parts swing more (inverted from undergrowth)
		float hang_dist = max(-VERTEX.y, 0.0);
		float pendulum = hang_dist * 0.3;

		float px = instance_origin.x * 0.06 + instance_origin.z * 0.10;
		float pz = instance_origin.z * 0.08 + instance_origin.x * 0.05;

		float rustle = (0.20 + wind_str * 0.8) * flex;
		VERTEX.x += sin(TIME * 0.8 + px) * pendulum * rustle;
		VERTEX.z += sin(TIME * 1.1 + pz) * pendulum * rustle * 0.7;

		// Constant wind push — vines lean with wind
		VERTEX.x += wind_vec.x * pendulum * 0.35 * flex;
		VERTEX.z += wind_vec.y * pendulum * 0.35 * flex;

		// Gusts
		float gust_phase = instance_origin.x * 0.025 + instance_origin.z * 0.035;
		float gust = sin(TIME * 0.35 + gust_phase) * 0.5 + 0.5;
		gust = gust * gust;
		float gust_str = gust * wind_str * 0.4 * flex;
		VERTEX.x += wind_vec.x * pendulum * gust_str;
		VERTEX.z += wind_vec.y * pendulum * gust_str;

		v_wind_amount = (rustle + gust_str) * pendulum * 0.4;
	} else {
		// Trunk wrap: minimal sway, mostly at top
		float top_flex = sway_base * 0.1;
		VERTEX.x += sin(TIME * 0.6 + instance_origin.x * 0.1) * top_flex * flex * wind_str;
		VERTEX.z += sin(TIME * 0.8 + instance_origin.z * 0.1) * top_flex * flex * wind_str * 0.5;
		v_wind_amount = top_flex * wind_str * 0.1;
	}

	// Winter: leaves collapse but stem structure persists
	// Leaf quads detected by UV.x being far from 0.5
	float edge_dist = abs(UV.x - 0.5) * 2.0;
	float is_leaf = step(0.2, edge_dist);
	float winter_t = sn_canopy_bare(season_t);
	// Evergreen species keep leaves through winter
	float vert_evergreen = 0.0;
	if (v_species > 0.07 && v_species < 0.21) vert_evergreen = 1.0;  // ivy
	else if (v_species > 0.64 && v_species < 0.78) vert_evergreen = 0.4;  // honeysuckle
	if (winter_t > 0.0 && is_leaf > 0.5 && vert_evergreen < 0.5) {
		VERTEX.y *= mix(1.0, 0.05, winter_t);
	}
}

void fragment() {
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// Stem vs leaf detection from UV
	float edge_dist = abs(UV.x - 0.5) * 2.0;
	float is_leaf = smoothstep(0.05, 0.2, edge_dist);
	float is_berry = step(0.88, UV.y) * is_leaf;

	// --- Alpha cutout ---
	float leaf_alpha = 1.0;
	if (is_leaf > 0.1) {
		// Procedural leaf shape
		float leaf_width = sin(UV.y * 3.14159) * (1.0 - UV.y * 0.2);
		float edge_noise = vnoise(UV * 5.0 + vec2(v_seed * 11.0, v_seed * 7.0)) * 0.10;
		leaf_width += edge_noise;
		float proc_mask = smoothstep(leaf_width, leaf_width - 0.08, edge_dist);
		leaf_alpha = mix(1.0, proc_mask, is_leaf);
	}
	if (leaf_alpha < 0.35) discard;

	// Winter discard for leaves (but NOT stems — bare vine canes visible year-round)
	// Evergreen species (ivy, partial honeysuckle) keep leaves through winter
	float winter_discard = sn_winter_kill(season_t);
	float sp_eg = 0.0;
	if (v_species > 0.07 && v_species < 0.21) sp_eg = 1.0;       // ivy: fully evergreen
	else if (v_species > 0.64 && v_species < 0.78) sp_eg = 0.4;  // honeysuckle: semi
	if (winter_discard > (0.95 - sp_eg * 0.9) && is_leaf > 0.5 && sp_eg < 0.9) discard;

	// --- Hemisphere normals ---
	vec3 outward = normalize(vec3(VERTEX.x, VERTEX.y * 0.2, VERTEX.z));
	NORMAL = normalize(mix(NORMAL, outward, 0.4));
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// --- BASE COLOR — 7 species ---
	vec3 stem_col = vec3(0.25, 0.19, 0.12);
	stem_col *= mix(0.9, 1.1, vnoise(v_world_pos.xz * 0.5 + vec2(v_seed * 30.0)));

	// Species leaf color lookup (7 species via quantized index)
	vec3 leaf_col;
	if (v_species < 0.07)       leaf_col = vec3(0.14, 0.36, 0.10);  // VA creeper: medium green
	else if (v_species < 0.21)  leaf_col = vec3(0.06, 0.20, 0.05);  // ivy: dark glossy green
	else if (v_species < 0.36)  leaf_col = vec3(0.16, 0.34, 0.10);  // bittersweet
	else if (v_species < 0.50)  leaf_col = vec3(0.12, 0.30, 0.14);  // porcelain berry
	else if (v_species < 0.64)  leaf_col = vec3(0.14, 0.32, 0.08);  // wild grape
	else if (v_species < 0.78)  leaf_col = vec3(0.10, 0.28, 0.06);  // honeysuckle
	else                        leaf_col = vec3(0.16, 0.38, 0.12);  // wisteria
	leaf_col *= mix(vec3(0.93, 1.03, 1.05), vec3(1.07, 0.97, 0.93), v_seed);

	vec3 col = mix(stem_col, leaf_col, is_leaf);

	// --- Berry/flower color (seasonal, 7 species) ---
	float fruit_season = smoothstep(1.8, 2.3, season_t) * (1.0 - smoothstep(3.5, 4.0, season_t));
	float is_flower = step(0.92, UV.y) * is_leaf;  // UV.y > 0.92 = flower region

	if (is_berry > 0.5 && fruit_season > 0.01) {
		vec3 berry_col = vec3(0.3, 0.2, 0.1);
		if (v_species < 0.07) {
			// VA creeper: small blue-black berries
			berry_col = vec3(0.10, 0.08, 0.18);
		} else if (v_species < 0.36) {
			// Bittersweet: yellow membrane splits to reveal red
			float split = smoothstep(2.2, 2.8, season_t);
			berry_col = mix(vec3(0.75, 0.65, 0.15), vec3(0.80, 0.15, 0.10), split);
		} else if (v_species < 0.50) {
			// Porcelain berry: multicolor (turquoise → blue → lilac)
			float bp = fract(v_seed * 7.7 + UV.x * 3.3);
			vec3 turquoise = vec3(0.25, 0.65, 0.60);
			vec3 blue = vec3(0.20, 0.30, 0.70);
			vec3 lilac = vec3(0.55, 0.35, 0.65);
			vec3 pale = vec3(0.75, 0.72, 0.55);
			if (bp < 0.25)      berry_col = mix(pale, turquoise, bp * 4.0);
			else if (bp < 0.5)  berry_col = mix(turquoise, blue, (bp - 0.25) * 4.0);
			else if (bp < 0.75) berry_col = mix(blue, lilac, (bp - 0.5) * 4.0);
			else                berry_col = mix(lilac, pale, (bp - 0.75) * 4.0);
		} else if (v_species < 0.64) {
			// Wild grape: small dark purple-black berries
			berry_col = vec3(0.12, 0.06, 0.15);
		} else if (v_species < 0.78) {
			// Honeysuckle: small black berries
			berry_col = vec3(0.05, 0.04, 0.06);
		}
		col = mix(col, berry_col, is_berry * fruit_season);
	}

	// Flowers: wisteria purple racemes (spring), honeysuckle white-yellow (summer)
	if (is_flower > 0.5) {
		vec3 flower_col = vec3(0.0);
		float flower_t = 0.0;
		if (v_species > 0.64 && v_species < 0.78) {
			// Honeysuckle: white turning yellow, summer bloom
			flower_col = mix(vec3(0.95, 0.92, 0.82), vec3(0.90, 0.80, 0.35), v_seed);
			flower_t = smoothstep(0.6, 0.9, season_t) * (1.0 - smoothstep(1.6, 1.9, season_t));
		} else if (v_species > 0.78) {
			// Wisteria: lavender-purple pendant racemes, early spring
			flower_col = mix(vec3(0.55, 0.30, 0.65), vec3(0.70, 0.45, 0.75), v_seed);
			flower_t = smoothstep(0.2, 0.5, season_t) * (1.0 - smoothstep(0.8, 1.1, season_t));
		}
		col = mix(col, flower_col, is_flower * flower_t * 0.85);
	}

	// --- Spatial variation ---
	float broad = vnoise(v_world_pos.xz / 12.0);
	col *= mix(0.88, 1.12, broad);

	// --- AO ---
	float ao = 0.65 - v_wind_amount * 0.15;
	AO = clamp(ao, 0.0, 1.0);
	AO_LIGHT_AFFECT = 1.0;

	// --- Seasonal color ---
	float spring_t = sn_veg_spring(season_t);
	float autumn_t = sn_veg_autumn(season_t);
	float winter_t = sn_veg_winter(season_t);

	// Evergreen factor — ivy stays green, honeysuckle semi-evergreen
	float sp_evergreen = 0.0;
	if (v_species > 0.07 && v_species < 0.21) sp_evergreen = 1.0;       // ivy: fully evergreen
	else if (v_species > 0.64 && v_species < 0.78) sp_evergreen = 0.4;  // honeysuckle: partial

	// Spring: fresh bright green
	col = mix(col, col * vec3(1.12, 1.18, 0.78), spring_t * 0.4 * is_leaf);

	// Autumn: species-specific fall color
	if (is_leaf > 0.1 && sp_evergreen < 0.5) {
		vec3 fall_col;
		if (v_species < 0.07)       fall_col = vec3(0.85, 0.10, 0.06);  // VA creeper: BRILLIANT SCARLET
		else if (v_species < 0.36)  fall_col = vec3(0.70, 0.60, 0.12);  // bittersweet: bright yellow
		else if (v_species < 0.50)  fall_col = vec3(0.55, 0.50, 0.15);  // porcelain berry: yellow-green
		else if (v_species < 0.64)  fall_col = vec3(0.60, 0.50, 0.10);  // wild grape: yellow-brown
		else                        fall_col = vec3(0.55, 0.45, 0.10);  // wisteria: yellow
		// VA creeper colors earliest (season_t 1.8), others at 2.0+
		float early = v_species < 0.07 ? 0.2 : 0.0;
		float adj_autumn = smoothstep(2.0 - early, 2.6 - early, season_t)
		                  * (1.0 - smoothstep(3.0, 3.5, season_t));
		col = mix(col, fall_col, adj_autumn * 0.70 * is_leaf);
	}

	// Winter: bare brown canes (stems only, leaves discarded for deciduous)
	float winter_stem_darken = winter_t * (1.0 - is_leaf);
	col = mix(col, vec3(0.18, 0.14, 0.08), winter_stem_darken);

	// Wind color shift
	float wind_darken = v_wind_amount * length(wind_vec) * 0.12;
	col *= (1.0 - wind_darken);

	// Canopy shade
	{
		vec2 canopy_uv = (v_world_pos.xz + hm_world_size * 0.5) / hm_world_size;
		float canopy = texture(canopy_map, canopy_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = sn_canopy_loss(season_t);
			float winter_bare = sn_canopy_bare(season_t);
			float spring_fill = sn_canopy_fill(season_t);
			float sc = canopy * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare) * mix(0.5, 1.0, spring_fill);
			vec2 dapple_uv = v_world_pos.xz * 0.3 + wind_vec * TIME * 0.06;
			float dapple = vnoise(dapple_uv);
			float light_gap = smoothstep(0.35, 0.65, dapple);
			float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum);
			float shade = sc * sun_factor;
			col *= (1.0 - shade * (1.0 - light_gap) * 0.10);
		}
	}

	ALBEDO = col;

	// Roughness: stems rougher, leaves smoother, berries glossy
	float base_rough = mix(0.75, 0.55, is_leaf);
	if (is_berry > 0.5) base_rough = 0.30;  // berries are glossy
	ROUGHNESS = base_rough;
	SPECULAR = mix(0.10, 0.18, is_leaf);
	METALLIC = 0.0;

	// Backlight: leaves transmit light, berries glow
	float backlight_str = mix(0.05, 0.25, is_leaf);
	if (is_berry > 0.5 && fruit_season > 0.01) backlight_str = 0.35;
	BACKLIGHT = vec3(backlight_str);

	// --- Weather ---
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.72, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.25, rain_wetness);
	}

	if (snow_cover > 0.01) {
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		float snow_on = upward * snow_cover;
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_on * 0.50);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_on * 0.4);
	}

	// --- Distance LOD fade ---
	float cam_dist = length(v_world_pos - INV_VIEW_MATRIX[3].xyz);
	float fade_start = 50.0;
	float fade_end = 65.0;
	float alpha = 1.0 - smoothstep(fade_start, fade_end, cam_dist);
	if (alpha < 0.01) discard;
	ALPHA = alpha;
	ALPHA_HASH_SCALE = 1.0;
}

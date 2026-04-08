shader_type spatial;
render_mode cull_disabled, depth_prepass_alpha, alpha_to_coverage;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/seasonal.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

uniform float wind_flex : hint_range(0.0, 1.0) = 0.4;
uniform float is_evergreen : hint_range(0.0, 1.0) = 0.0;
uniform vec3 fall_tint = vec3(0.5, 0.35, 0.08);
uniform vec3 flower_color = vec3(0.0, 0.0, 0.0);  // (0,0,0) = no flowers
uniform vec2 bloom_range = vec2(1.0, 2.0);  // season_t range when flowers appear
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;

// Leaf texture atlas (4-col grid, variable rows, 512px per species cell)
uniform sampler2D leaf_atlas : filter_linear, repeat_disable;
uniform vec2 atlas_offset = vec2(0.0, 0.0);  // species cell position in atlas (UV space)
uniform vec2 atlas_cell_size = vec2(0.25, 0.25);  // cell size in UV space (1/cols, 1/rows)
uniform float use_atlas = 0.0;  // 1.0 = sample atlas, 0.0 = procedural only

// Per-surface albedo texture for 3D meshes (BD3D plant library etc.)
uniform sampler2D albedo_tex : source_color, filter_linear;
uniform float use_texture = 0.0;  // 1.0 = read albedo+alpha from albedo_tex

// Per-species material tuning (set in undergrowth_builder.gd)
uniform float roughness_base : hint_range(0.3, 1.0) = 0.82;
uniform float specular_base : hint_range(0.0, 0.5) = 0.04;
uniform float translucency : hint_range(0.0, 1.5) = 0.5;

// Stem rendering — procedural bark when COLOR.a < 0.5 (stem vertex)
uniform vec3 stem_color : source_color = vec3(0.30, 0.25, 0.15);
uniform float stem_roughness : hint_range(0.5, 1.0) = 0.92;


varying vec3 v_world_pos;
varying float v_seed;
varying float v_wind_amount;
varying float v_is_stem;  // 1.0 when COLOR.a < 0.5 (stem vertex), 0.0 for leaf

void vertex() {
	vec3 instance_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_world_pos = instance_origin;
	v_seed = INSTANCE_CUSTOM.r;
	v_is_stem = step(0.5, 1.0 - COLOR.a);  // COLOR.a=0 → stem (1.0), COLOR.a=1 → leaf (0.0)

	// -- Wind sway --
	// Squared height curve (cantilever model) — base stays locked to ground,
	// upper branches sway freely. Linear sway made bases slide sideways.
	float h = max(VERTEX.y, 0.0);
	float sway = h * h;
	float wind_str = length(wind_vec);
	float flex = wind_flex;

	float px = instance_origin.x * 0.08 + instance_origin.z * 0.12;
	float pz = instance_origin.z * 0.10 + instance_origin.x * 0.06;

	float rustle = (0.15 + wind_str * 0.8) * flex;
	VERTEX.x += sin(TIME * 1.2 + px) * 0.06 * sway * rustle;
	VERTEX.z += sin(TIME * 1.5 + pz) * 0.05 * sway * rustle;

	// Steady lean — cantilever: strong at top, zero at base
	VERTEX.x += wind_vec.x * sway * 0.28 * flex;
	VERTEX.z += wind_vec.y * sway * 0.28 * flex;

	float gust_phase = instance_origin.x * 0.03 + instance_origin.z * 0.04;
	float gust = sin(TIME * 0.4 + gust_phase) * 0.5 + 0.5;
	gust = gust * gust;
	float gust_str = gust * wind_str * 0.3 * flex;
	VERTEX.x += wind_vec.x * sway * gust_str;
	VERTEX.z += wind_vec.y * sway * gust_str;

	v_wind_amount = (rustle + gust_str) * sway * 0.5;

	// Winter die-back
	float winter_t = sn_canopy_bare(season_t);
	if (winter_t > 0.0 && is_evergreen < 0.5) {
		VERTEX.y *= mix(1.0, 0.1, winter_t);
	}
}

void fragment() {
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// ---- STEM vs LEAF BRANCHING ----
	float is_stem = v_is_stem;  // 1.0 = stem vertex, 0.0 = leaf vertex

	// ---- ALPHA CUTOUT (leaf path only — stems are opaque geometry) ----
	float leaf_alpha = 1.0;
	vec3 tex_color = COLOR.rgb;

	if (is_stem < 0.5) {
		if (use_texture > 0.5) {
			// 3D mesh with per-surface PBR texture (BD3D plant library)
			vec4 tex = texture(albedo_tex, UV);
			tex_color = tex.rgb;
			leaf_alpha = tex.a;

			// Light color grade: just a touch of desaturation + warm shift.
			float lum = dot(tex_color, vec3(0.2126, 0.7152, 0.0722));
			tex_color = mix(vec3(lum), tex_color, 0.80);
			tex_color *= vec3(1.01, 1.00, 0.94);
		} else if (use_atlas > 0.5) {
			// Flat-card mesh with shared leaf atlas
			float edge_dist = abs(UV.x - 0.5) * 2.0;
			float is_leaf_card = smoothstep(0.05, 0.2, edge_dist);
			vec2 atlas_uv = atlas_offset + UV * atlas_cell_size;
			vec4 tex = texture(leaf_atlas, atlas_uv);
			tex_color = mix(COLOR.rgb, tex.rgb, is_leaf_card * step(0.1, tex.a));
			leaf_alpha = mix(1.0, tex.a, is_leaf_card);
		} else {
			// Procedural leaf shape from UV (billboard herbs etc.)
			float edge_dist = abs(UV.x - 0.5) * 2.0;
			float is_leaf_card = smoothstep(0.05, 0.2, edge_dist);
			float leaf_width = sin(UV.y * 3.14159) * (1.0 - UV.y * 0.25);
			float edge_noise = vnoise(UV * 6.0 + vec2(v_seed * 13.0, v_seed * 7.0)) * 0.12;
			leaf_width += edge_noise;
			float proc_mask = smoothstep(leaf_width, leaf_width - 0.06, edge_dist);
			leaf_alpha = mix(1.0, proc_mask, is_leaf_card);
		}

		if (leaf_alpha < 0.4) discard;
	}

	// ---- NORMALS ----
	vec3 frag_world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float bump_coarse, bump_fine, bump_h;

	if (is_stem > 0.5) {
		// Stems: keep mesh normals (tubes have real geometry normals).
		// Bark-like normal perturbation: longitudinal ridges + fine grain.
		float bark_ridge = vnoise(frag_world.xz * 18.0 + vec2(0.0, frag_world.y * 40.0));
		float bark_grain = vnoise(frag_world.xz * 80.0);
		bump_h = bark_ridge * 0.6 + bark_grain * 0.4;
		NORMAL = normalize(NORMAL + vec3(dFdx(bump_h), dFdy(bump_h), 0.0) * 0.6);
		bump_coarse = bark_ridge;
		bump_fine = bark_grain;
	} else {
		// Leaves: flat-card meshes need hemisphere blend
		if (use_texture < 0.5) {
			vec3 outward = normalize(vec3(VERTEX.x, VERTEX.y * 0.25, VERTEX.z));
			NORMAL = normalize(mix(NORMAL, outward, 0.45));
			if (!FRONT_FACING) NORMAL = -NORMAL;
		}

		// Leaf micro-texture normal perturbation: veins, cell structure, cuticle bumps.
		bump_coarse = vnoise(frag_world.xz * 55.0);
		bump_fine = vnoise(frag_world.xz * 130.0);
		bump_h = bump_coarse * 0.6 + bump_fine * 0.4;
		NORMAL = normalize(NORMAL + vec3(dFdx(bump_h), dFdy(bump_h), 0.0) * 1.2);
	}

	// Winter discard — deciduous shrubs disappear under snow
	float winter_discard = sn_winter_kill(season_t);
	// Snow accelerates hiding: heavy snow hides shrubs earlier
	float snow_hide = snow_cover * 0.6;
	if ((winter_discard + snow_hide) > 0.7 && is_evergreen < 0.5) discard;


	// ---- COLOR ----
	vec3 col = is_stem > 0.5 ? stem_color : tex_color;

	// Per-instance color variation: brightness ±12%, warm/cool hue shift
	// (matches tree_leaf.gdshader so undergrowth blends into the canopy palette)
	float bright_off = (v_seed - 0.5) * 0.25;
	col *= 1.0 + bright_off;
	float warm_off = fract(v_seed * 7.37) - 0.5;
	col += warm_off * vec3(0.025, -0.008, -0.03);

	// Broad spatial variation (patch-scale color drift)
	float broad = vnoise(v_world_pos.xz / 10.0);
	col *= mix(0.88, 1.12, broad);

	// ---- AO from vertex height ----
	// Gentle darkening at ground contact to anchor plants without making small
	// species invisible. Raised floor from 0.30→0.55 so lawn accent plants
	// (clover, plantain, speedwell) stay visible against the grass.
	float height_frac = clamp(VERTEX.y / 3.0, 0.0, 1.0);
	float ao = mix(0.75, 1.0, smoothstep(0.0, 0.2, height_frac)) - v_wind_amount * 0.10;
	AO = clamp(ao, 0.0, 1.0);
	AO_LIGHT_AFFECT = 1.0;

	// ---- SEASONAL COLOR ----
	float spring_t = sn_veg_spring(season_t);
	float autumn_t = sn_veg_autumn(season_t);
	float winter_t = sn_veg_winter(season_t);

	col = mix(col, col * vec3(1.1, 1.15, 0.80), spring_t * 0.5);
	if (is_evergreen < 0.5) {
		col = mix(col, fall_tint, autumn_t * 0.65);
		col = mix(col, vec3(0.14, 0.10, 0.06), winter_t);
	}

	// Flowering — tint upper parts during bloom season
	// flower_color (0,0,0) = no flowers; bloom_range = season_t window
	if (flower_color.r + flower_color.g + flower_color.b > 0.01) {
		float bloom_t = smoothstep(bloom_range.x, bloom_range.x + 0.3, season_t)
		              * (1.0 - smoothstep(bloom_range.y - 0.2, bloom_range.y, season_t));
		// Flowers appear on upper 30% of plant, per-instance variation
		float flower_mask = smoothstep(0.6, 0.85, height_frac) * bloom_t;
		// Per-instance: ~60% of plants bloom, rest stay green
		float bloom_chance = step(0.4, v_seed);
		// Per-pixel flower color variation — petals have veining, fading, moisture
		vec3 f_col = flower_color * mix(0.85, 1.15, v_seed);
		vec2 fl_px = v_world_pos.xz * 31.7 + vec2(height_frac * 17.3);
		float fl_noise = hash2(fl_px) * 0.10 - 0.05;
		float fl_hue = hash2(fl_px + vec2(43.1, 0.0)) * 0.06 - 0.03;
		f_col += vec3(fl_noise + fl_hue, fl_noise, fl_noise - fl_hue);
		col = mix(col, f_col, flower_mask * bloom_chance * 0.8);
	}

	// Wind color shift
	float wind_darken = v_wind_amount * length(wind_vec) * 0.15;
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

	// ---- TOP-LIT GRADIENT ----
	// World-space normal creates 3D depth — bright top, darker underside.
	// Key cue for volumetric frond rosettes and leaf clusters.
	vec3 world_n_lit = mat3(INV_VIEW_MATRIX) * NORMAL;
	float top_lit = world_n_lit.y * 0.5 + 0.5;
	col *= mix(0.85, 1.08, top_lit);
	// Underside warm ground-bounce from grass below + cool sky-fill
	col = mix(col, col * vec3(0.97, 1.02, 0.95), (1.0 - top_lit) * 0.15);
	col = mix(col, col * vec3(0.94, 0.97, 1.04), (1.0 - top_lit) * 0.10);

	// ---- FRESNEL RIM LIGHT ----
	// Thin leaf edges glow at grazing view angles — depth cue for translucent fronds
	float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), 3.0);
	col += col * fresnel * 0.15;

	// ---- CANOPY INTERIOR POCKETS + PER-LEAF BRIGHTNESS ----
	// Dark shadow pockets where foliage overlaps (same as tree_leaf.gdshader)
	float detail_n = vnoise(UV * 12.0 + v_world_pos.xz * 0.5);
	float pocket_n = vnoise(UV * 4.0 + v_world_pos.xz * 0.3);
	col *= mix(1.0, 0.78, smoothstep(0.3, 0.6, pocket_n) * 0.22);
	col *= (0.92 + detail_n * 0.16);

	// ---- PER-PIXEL MICRO-VARIATION ----
	// Chlorophyll patches, dust, cell structure — ±4% brightness, ±3% hue
	vec2 px_uv = frag_world.xz * 97.3;
	float px_n = hash2(px_uv) * 0.08 - 0.04;
	float px_hr = hash2(px_uv + vec2(71.9, 0.0)) * 0.03;
	float px_hb = hash2(px_uv + vec2(0.0, 53.1)) * 0.03;
	col += vec3(px_n + px_hr, px_n, px_n + px_hb);

	ALBEDO = col;

	// ---- PBR ----
	float rough, spec;
	if (is_stem > 0.5) {
		// Stems: bark-like — high roughness, very low specular
		rough = stem_roughness;
		spec = 0.02;
	} else if (use_texture > 0.5) {
		// Textured leaf species: per-species uniforms with height gradient
		rough = mix(roughness_base, roughness_base - 0.15, height_frac);
		spec = mix(specular_base, specular_base + 0.04, height_frac);
	} else {
		// Atlas/procedural leaf path: legacy values
		rough = mix(0.72, 0.48, height_frac);
		spec = mix(0.08, 0.16, height_frac);
	}
	// Micro-roughness variation from surface bump (veins matte, smooth patches glossy)
	float rough_var = (bump_coarse - 0.5) * 0.14;
	rough = clamp(rough + rough_var, 0.3, 0.98);
	spec = clamp(spec - rough_var * 0.08, 0.02, 0.30);
	ROUGHNESS = rough;
	SPECULAR = spec;
	METALLIC = 0.0;

	// ---- ENHANCED SUBSURFACE SCATTERING ----
	// Leaves only — stems are opaque woody tissue, no light transmission.
	// Matched to tree_leaf.gdshader SSS pipeline for visual coherence.
	if (is_stem < 0.5) {
		vec3 sss_col = vec3(0.46, 0.36, 0.10);  // warm green-gold (matches tree shader)
		// Tint with leaf color so autumn leaves glow amber/red
		sss_col = mix(sss_col, col * 0.6, 0.45);
		float sss_str = translucency;
		// Spring leaves are thinner, more translucent
		sss_str *= mix(1.0, 1.3, spring_t);
		// Height-dependent: tips thinner than base
		sss_str *= mix(0.7, 1.0, height_frac);
		BACKLIGHT = sss_col * sss_str;
	}

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

	// ---- DISTANCE EFFECTS ----
	float cam_dist = length(v_world_pos - INV_VIEW_MATRIX[3].xyz);

	// Aerial perspective: haze + desaturation at distance, consistent with trees/terrain
	float aerial = smoothstep(40.0, 200.0, cam_dist);
	ALBEDO = apply_aerial(ALBEDO, aerial, 0.25, 0.25, sky_reflect_color);

	// Alpha hash fade for LOD pop-out
	float fade_start = 50.0;
	float fade_end = 62.0;
	float alpha = 1.0 - smoothstep(fade_start, fade_end, cam_dist);
	AO_LIGHT_AFFECT = mix(0.3, 1.0, alpha);
	NORMAL = mix(NORMAL, vec3(0.0, 1.0, 0.0), 1.0 - alpha);
	ALPHA = alpha;
	ALPHA_HASH_SCALE = 1.0;
}

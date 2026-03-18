shader_type spatial;
render_mode cull_disabled;

#include "res://shaders/include/hash_noise.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform float dew_amount;
global uniform vec3 sky_reflect_color;

uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;

varying float v_grass_type;
varying float v_bottom_to_top;  // 0 at base, 1 at tip
varying vec3 v_world_blade;     // per-BLADE world position (not tile center)
varying float v_path_prox;
varying float v_blade_seed;     // per-blade random (0-1) for hue variation
varying float v_is_flower;      // >0 = flower (use vertex color instead of grass color)
varying float v_wind_bend;      // current wind bend amount (for AO in fragment)
varying float v_patch_factor;   // 0=small/young, 1=tall/old — ties size to color

void vertex() {
	v_grass_type = INSTANCE_CUSTOM.r;
	v_path_prox = INSTANCE_CUSTOM.b;
	v_blade_seed = INSTANCE_CUSTOM.g;
	v_is_flower = INSTANCE_CUSTOM.a;

	// Each blade is its own MultiMesh instance. MODEL_MATRIX origin
	// gives the true per-blade world position.
	vec3 blade_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec2 blade_world_xz = blade_origin.xz;
	v_world_blade = blade_origin;

	// Bottom-to-top from UV (0 at base, 1 at tip — set in Blender)
	v_bottom_to_top = clamp(UV.y, 0.0, 1.0);

	// --- Patchiness (hexaquo) — world-space noise ties size to color ---
	v_patch_factor = vnoise(blade_world_xz / 3.0);
	float size_lo = 0.6; float size_hi = 1.0;
	if (v_grass_type > 7.5) {
		size_lo = 0.3; size_hi = 1.0;   // wild meadow: dramatic
	} else if (v_grass_type > 4.5 && v_grass_type < 7.5) {
		size_lo = 0.4; size_hi = 1.0;   // woodland/water
	}
	// Flowers keep natural size — don't shrink with grass patchiness
	if (v_is_flower < 0.5) {
		VERTEX *= mix(size_lo, size_hi, v_patch_factor);
	}

	// Sway amount: only tips move, base is rooted
	float sway = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);

	// Wind flex varies by zone type
	float flex = 0.7;
	if (v_grass_type > 7.5) {
		flex = 2.5;  // wild meadow
	} else if (v_grass_type > 6.5) {
		flex = 0.8;  // waterside
	} else if (v_grass_type > 4.5) {
		flex = 0.35; // woodland
	} else if (v_grass_type > 3.5) {
		flex = 0.5;  // sports turf
	}
	float rustle = (0.2 + wind_str * 0.8) * flex;

	// --- Wind: per-blade world position for phase ---
	float px = blade_world_xz.x * 0.15 + blade_world_xz.y * 0.22;
	float pz = blade_world_xz.y * 0.18 + blade_world_xz.x * 0.12;
	VERTEX.x += sin(TIME * 1.8 + px) * 0.12 * sway * rustle;
	VERTEX.z += sin(TIME * 2.3 + pz) * 0.08 * sway * rustle;

	// Wind push: constant lean in wind direction
	VERTEX.x += wind_vec.x * sway * 0.4 * flex;
	VERTEX.z += wind_vec.y * sway * 0.4 * flex;

	// Traveling wind gusts — per-blade phase
	float gust_phase = blade_world_xz.x * 0.04 + blade_world_xz.y * 0.05;
	float gust = sin(TIME * 0.5 + gust_phase) * 0.5 + 0.5;
	gust = gust * gust * gust;
	float gust_str = gust * wind_str * 0.5 * flex;
	VERTEX.x += wind_vec.x * sway * gust_str;
	VERTEX.z += wind_vec.y * sway * gust_str;

	// Store wind bend for AO in fragment
	v_wind_bend = (rustle + gust_str) * sway * 0.5;

	// Blade flutter
	float flutter = sin(TIME * 5.5 + VERTEX.x * 14.0 + VERTEX.z * 10.0) * 0.015 * rustle;
	flutter += sin(TIME * 8.0 + VERTEX.z * 18.0) * 0.008 * gust_str;
	VERTEX.y += flutter * sway;

	// Winter dormancy
	float winter_t = smoothstep(3.0, 3.5, season_t);
	if (winter_t > 0.0 && (v_grass_type < 4.5 || v_grass_type > 8.5)) {
		VERTEX.y *= mix(1.0, 0.08, winter_t);
	}
	if (winter_t > 0.0 && v_grass_type > 4.5 && v_grass_type < 8.5) {
		VERTEX.y *= mix(1.0, 0.25, winter_t);
	}
}

void fragment() {
	// Back-face normal fix — with cull_disabled, back faces get flipped normals
	// which breaks our custom normal logic. Flip them back.
	if (!FRONT_FACING) NORMAL = -NORMAL;

	// Winter discard
	float winter_discard = smoothstep(3.2, 3.8, season_t);
	if (winter_discard > 0.95 && v_grass_type < 4.5) discard;

	// Aerial height discard — from above, sub-pixel blades create noise
	float cam_h = INV_VIEW_MATRIX[3].y - v_world_blade.y;
	if (cam_h > 12.0) {
		float aerial_discard = smoothstep(12.0, 35.0, cam_h);
		float ad = hash2(v_world_blade.xz * 1.3 + vec2(41.2, 63.9));
		if (ad < aerial_discard) discard;
	}

	float blade_t = v_bottom_to_top;
	float blade_seed = v_blade_seed;

	// Blade roundness is baked into custom split normals from Blender
	// (cylinder Data Transfer technique). Tips blend toward up for
	// specular highlights, but not fully — prevents white shimmer.
	NORMAL = mix(NORMAL, vec3(0.0, 1.0, 0.0), blade_t * 0.6);

	// --- Color tied to size + zone type (hexaquo) ---
	// Each grass type gets a visually distinct color pair.
	// Values are pushed apart so zones read differently at a glance.
	vec3 color_small, color_large;

	if (v_grass_type < 0.5) {
		// SheepMeadow: cool blue-green Kentucky bluegrass
		color_small = vec3(0.06, 0.30, 0.10);
		color_large = vec3(0.15, 0.40, 0.14);
	} else if (v_grass_type < 1.5) {
		// GreatLawn: deep rich emerald
		color_small = vec3(0.05, 0.25, 0.05);
		color_large = vec3(0.12, 0.35, 0.08);
	} else if (v_grass_type < 2.5) {
		// NorthMeadow: warm open meadow, noticeably yellower
		color_small = vec3(0.14, 0.28, 0.04);
		color_large = vec3(0.35, 0.42, 0.08);
	} else if (v_grass_type < 3.5) {
		// FormalGarden: uniform bright green, low contrast
		color_small = vec3(0.10, 0.32, 0.08);
		color_large = vec3(0.16, 0.36, 0.10);
	} else if (v_grass_type < 4.5) {
		// SportsTurf: vivid saturated green (fertilized)
		color_small = vec3(0.04, 0.32, 0.03);
		color_large = vec3(0.10, 0.42, 0.06);
	} else if (v_grass_type < 5.5) {
		// NorthWoods: dark blue-green shade grass
		color_small = vec3(0.04, 0.14, 0.06);
		color_large = vec3(0.08, 0.20, 0.10);
	} else if (v_grass_type < 6.5) {
		// Ramble: warm brown-green woodland understory
		color_small = vec3(0.08, 0.16, 0.04);
		color_large = vec3(0.16, 0.22, 0.06);
	} else if (v_grass_type < 7.5) {
		// Waterside: dark lush green, very saturated
		color_small = vec3(0.04, 0.22, 0.08);
		color_large = vec3(0.10, 0.34, 0.14);
	} else if (v_grass_type < 8.5) {
		// WildMeadow: golden-green, dramatic warm tones
		color_small = vec3(0.18, 0.24, 0.03);
		color_large = vec3(0.45, 0.42, 0.08);
	} else {
		// OpenLawn: standard mid-green
		color_small = vec3(0.10, 0.26, 0.06);
		color_large = vec3(0.24, 0.36, 0.10);
	}

	vec3 col = mix(color_small, color_large, v_patch_factor);

	// Base-to-tip gradient: slightly darker base, full color at tip
	col *= mix(0.82, 1.0, blade_t);

	// Per-blade hue variation: subtle cool↔warm shift per blade
	col *= mix(vec3(0.97, 1.01, 1.03), vec3(1.03, 0.99, 0.95), blade_seed);

	// Broad meadow variation (12m scale) — gentle brightness shifts
	float broad_patch = vnoise(v_world_blade.xz / 12.0);
	col *= mix(0.92, 1.08, broad_patch);

	// Dry blade tips: ~30% of blades get subtle yellowed tips
	float dry_tip = smoothstep(0.75, 1.0, blade_t) * step(0.7, blade_seed);
	col = mix(col, col * vec3(1.08, 1.02, 0.80), dry_tip * 0.15);

	// Flowers: use baked vertex color from flower GLB mesh
	if (v_is_flower > 0.5) {
		col = COLOR.rgb;
	}

	// --- AO: self-shadowing + wind darkening (hexaquo) ---
	float ao = blade_t - v_wind_bend * 0.3;
	AO = clamp(ao, 0.0, 1.0);
	AO_LIGHT_AFFECT = 1.0;

	// Seasonal colour
	float spring_t = 1.0 - smoothstep(0.0, 1.0, season_t);
	float autumn_t = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(2.8, 3.5, season_t));
	float winter_t = smoothstep(2.7, 3.1, season_t);
	col = mix(col, col * vec3(1.1, 1.15, 0.75), spring_t * 0.6);
	col = mix(col, vec3(0.16, 0.12, 0.04), autumn_t * 0.7);
	col = mix(col, vec3(0.12, 0.10, 0.06), winter_t);

	// Path-edge wear (data-driven)
	if (v_path_prox > 0.05) {
		vec3 worn_col = col * vec3(1.10, 0.88, 0.60);
		col = mix(col, worn_col, v_path_prox * 0.55);
		float wear_lum = dot(col, vec3(0.299, 0.587, 0.114));
		col = mix(col, vec3(wear_lum), v_path_prox * 0.25);
	}

	// Canopy shade (data-driven from tree census)
	{
		vec2 canopy_uv = (v_world_blade.xz + hm_world_size * 0.5) / hm_world_size;
		float canopy = texture(canopy_map, canopy_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = smoothstep(2.5, 3.2, season_t);
			float winter_bare = smoothstep(3.0, 3.5, season_t);
			float spring_fill = smoothstep(0.0, 0.4, season_t);
			float sc = canopy * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare) * mix(0.5, 1.0, spring_fill);
			vec2 dapple_uv = v_world_blade.xz * 0.35 + wind_vec * TIME * 0.08;
			float dapple = vnoise(dapple_uv);
			float dapple_fine = vnoise(v_world_blade.xz * 1.2 + wind_vec * TIME * 0.15);
			float light_gap = smoothstep(0.35, 0.65, dapple) * 0.6 + smoothstep(0.55, 0.75, dapple_fine) * 0.4;
			float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum);
			float shade = sc * sun_factor;
			col *= (1.0 - shade * (1.0 - light_gap) * 0.35);
			col *= vec3(1.0 + light_gap * shade * 0.08, 1.0 + light_gap * shade * 0.04, 1.0 - light_gap * shade * 0.024);
		}
	}

	ALBEDO = col;

	// --- Proper grass material (hexaquo) ---
	// Grass IS shiny. Real blades have a waxy cuticle that's glossiest
	// at the tip and progressively matte toward the base sheath.
	ROUGHNESS = mix(0.65, 0.35, blade_t);  // base matte, tip glossy
	SPECULAR = mix(0.08, 0.20, blade_t);   // tip catches specular highlights
	METALLIC = 0.0;

	// Translucency — grass blades are thin, light passes through as
	// warm green-gold glow (not white). This is what makes sunlit
	// meadows glow rather than look flat.
	BACKLIGHT = vec3(0.25, 0.30, 0.08) * mix(0.6, 1.0, blade_t);

	// --- Weather effects ---
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.65, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.25, rain_wetness);
		SPECULAR = mix(SPECULAR, 0.35, rain_wetness);
	}

	if (snow_cover > 0.01) {
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		float snow_on = upward * snow_cover * mix(0.5, 1.0, v_grass_type);
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_on * 0.65);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_on * 0.5);
	}

	if (winter_t > 0.1 && snow_cover < 0.6) {
		float frost_mask = winter_t * smoothstep(0.2, 0.8, blade_t);
		float crystal = hash2(floor(v_world_blade.xz * 12.0 + vec2(blade_t * 5.0)));
		float sparkle = step(0.80, crystal) * frost_mask;
		ALBEDO = mix(ALBEDO, ALBEDO * vec3(1.10, 1.12, 1.18), frost_mask * 0.4);
		ROUGHNESS = mix(ROUGHNESS, 0.10, sparkle * 0.8);
		SPECULAR = mix(SPECULAR, 0.60, sparkle * 0.9);
		ROUGHNESS = mix(ROUGHNESS, 0.40, frost_mask * 0.3);
	}

	if (dew_amount > 0.01 && blade_t > 0.5) {
		float dew = dew_amount * smoothstep(0.5, 0.85, blade_t);
		ROUGHNESS = mix(ROUGHNESS, 0.20, dew * 0.4);
		SPECULAR = mix(SPECULAR, 0.30, dew * 0.3);
		ALBEDO *= mix(1.0, 1.06, dew * 0.3);
	}

	// --- Hexaquo LOD crossfade: alpha hash at distance ---
	// Blades dither out near the vis boundary, revealing the impostor
	// terrain underneath. Per-blade fade (not per-chunk) eliminates
	// visible chunk rectangles.
	float cam_dist = length(v_world_blade - INV_VIEW_MATRIX[3].xyz);
	float fade_start = 20.0;  // start fading
	float fade_end = 25.0;    // fully transparent
	float alpha = 1.0 - smoothstep(fade_start, fade_end, cam_dist);
	// Also reduce AO harshness as blades fade (hexaquo trick)
	AO_LIGHT_AFFECT = mix(0.3, 1.0, alpha);
	// Flatten normals as blades fade (reduces noise at distance)
	NORMAL = mix(NORMAL, vec3(0.0, 1.0, 0.0), 1.0 - alpha);
	ALPHA = alpha;
	ALPHA_HASH_SCALE = 1.0;
}

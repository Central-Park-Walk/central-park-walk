// Central Park grass render shader — GPU particle grass tufts
// Renders real-geometry grass tuft meshes with zone-aware color,
// seasonal modulation, canopy dapple, weather effects, and wind.

shader_type spatial;
render_mode skip_vertex_transform, cull_disabled;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap;
uniform bool has_normal_map = false;
uniform bool use_texture = true;

global uniform float season_t;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform float dew_amount;
global uniform vec3 sky_reflect_color;
global uniform float cloud_coverage_g;
global uniform float cloud_speed_g;

#include "res://shaders/include/seasonal.gdshaderinc"
#include "res://shaders/include/hash_noise.gdshaderinc"

varying vec4 data;
varying vec3 v_world_pos;
varying float v_height_t;

void vertex() {
	v_height_t = use_texture ? UV.y : clamp((VERTEX.y + 0.55) * 0.91, 0.0, 1.0);
	float bend_factor = v_height_t * v_height_t;

	if (!use_texture) {
		VERTEX.xz *= (1.0 - bend_factor);
	}

	data.rg = INSTANCE_CUSTOM.rg;
	data[3] = INSTANCE_CUSTOM[3];

	vec3 w_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_pos = w_vertex;

	// Winter: shrink blades toward ground
	float w_winter = smoothstep(2.7, 3.5, season_t);
	float w_snow = max(w_winter, snow_cover);
	if (w_snow > 0.0) {
		VERTEX.y *= mix(1.0, 0.08, w_snow);
	}

	// Wind bending — suppress in winter/snow
	float wind_suppression = 1.0 - w_snow;
	float grass_scale = pow(INSTANCE_CUSTOM[3] * INSTANCE_CUSTOM[3], 0.707);
	float force = INSTANCE_CUSTOM[2] * bend_factor * grass_scale * wind_suppression;
	force -= fract(force * 256.0) * force * 0.05;
	force = pow(max(force, 0.0), 0.707);

	vec2 direction = normalize(wind_vec + vec2(0.001));
	float lateral_wobble = sin(TIME * 2.0 * (1.0 + data.r + data.g)) * 0.25 * (1.0 - INSTANCE_CUSTOM[2]) * wind_suppression;
	w_vertex.xz -= (vec2(-direction.y, direction.x) * lateral_wobble + direction) * force;
	w_vertex.y -= INSTANCE_CUSTOM[2] * force * bend_factor;

	data[2] = force;

	VERTEX = (VIEW_MATRIX * vec4(w_vertex, 1.0)).xyz;
	NORMAL = MODELVIEW_NORMAL_MATRIX * NORMAL;
	BINORMAL = MODELVIEW_NORMAL_MATRIX * BINORMAL;
	TANGENT = MODELVIEW_NORMAL_MATRIX * TANGENT;
}

void fragment() {
	// Heavy snow/winter: hide grass entirely
	float frag_snow = max(smoothstep(2.7, 3.5, season_t), snow_cover);
	if (frag_snow > 0.6) discard;

	// Texture-based alpha cutout
	if (use_texture) {
		float tex_alpha = texture(grass_albedo, UV).a;
		ALPHA = tex_alpha;
		ALPHA_SCISSOR_THRESHOLD = 0.4;
	}

	// Decode zone data from COLOR (set by particle process shader)
	// R = zone_id / 15.0, G = canopy_cover, B = woodland flag, A = season_t / 4
	int zone_id = int(COLOR.r * 15.0 + 0.5);
	float canopy_cover = COLOR.g;
	float blade_seed = data.r;

	// --- Zone-specific color palettes (from grass_blade.gdshader) ---
	vec3 color_small, color_large;
	if (zone_id == 0) {
		// SheepMeadow: cool blue-green Kentucky bluegrass
		color_small = vec3(0.06, 0.30, 0.10);
		color_large = vec3(0.15, 0.40, 0.14);
	} else if (zone_id == 1) {
		// GreatLawn: deep rich emerald
		color_small = vec3(0.05, 0.25, 0.05);
		color_large = vec3(0.12, 0.35, 0.08);
	} else if (zone_id == 2) {
		// NorthMeadow: warm open meadow, noticeably yellower
		color_small = vec3(0.14, 0.28, 0.04);
		color_large = vec3(0.35, 0.42, 0.08);
	} else if (zone_id == 3) {
		// FormalGarden: uniform bright green, low contrast
		color_small = vec3(0.10, 0.32, 0.08);
		color_large = vec3(0.16, 0.36, 0.10);
	} else if (zone_id == 5) {
		// NorthWoods: dark blue-green shade grass
		color_small = vec3(0.04, 0.14, 0.06);
		color_large = vec3(0.08, 0.20, 0.10);
	} else if (zone_id == 7) {
		// Waterside: dark lush green, very saturated
		color_small = vec3(0.04, 0.22, 0.08);
		color_large = vec3(0.10, 0.34, 0.14);
	} else if (zone_id == 10 || zone_id == 11) {
		// Woodland: warm brown-green understory
		color_small = vec3(0.08, 0.16, 0.04);
		color_large = vec3(0.16, 0.22, 0.06);
	} else {
		// Default: standard mid-green
		color_small = vec3(0.10, 0.26, 0.06);
		color_large = vec3(0.24, 0.36, 0.10);
	}

	// Patchiness: world-space noise ties size to color
	float patch_factor = vnoise(v_world_pos.xz / 3.0);
	vec3 col = mix(color_small, color_large, patch_factor);

	// Modulate by texture luminance if available (preserves blade detail)
	if (use_texture) {
		vec3 tex_col = texture(grass_albedo, UV).rgb;
		float tex_lum = dot(tex_col, vec3(0.3, 0.6, 0.1));
		col *= (0.6 + tex_lum * 0.8);
	}

	// Base-to-tip gradient
	col *= mix(0.82, 1.0, v_height_t);

	// Per-instance hue variation
	col *= mix(vec3(0.97, 1.01, 1.03), vec3(1.03, 0.99, 0.95), blade_seed);

	// Broad meadow variation (12m scale)
	float broad_patch = vnoise(v_world_pos.xz / 12.0);
	col *= mix(0.92, 1.08, broad_patch);

	// --- Seasonal color ---
	float spring_t = sn_veg_spring(season_t);
	float autumn_t = sn_veg_autumn(season_t);
	float winter_t = sn_veg_winter(season_t);
	col = mix(col, col * vec3(1.1, 1.15, 0.75), spring_t * 0.6);
	col = mix(col, vec3(0.16, 0.12, 0.04), autumn_t * 0.7);
	col = mix(col, vec3(0.12, 0.10, 0.06), winter_t);

	// --- Canopy dapple (not flat darkening — SDFGI handles bulk shade) ---
	if (canopy_cover > 0.01) {
		float deciduous_loss = sn_canopy_loss(season_t);
		float winter_bare = sn_canopy_bare(season_t);
		float spring_fill = sn_canopy_fill(season_t);
		float sc = canopy_cover * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare) * mix(0.5, 1.0, spring_fill);
		vec2 dapple_uv = v_world_pos.xz * 0.35 + wind_vec * TIME * 0.08;
		float dapple = vnoise(dapple_uv);
		float dapple_fine = vnoise(v_world_pos.xz * 1.2 + wind_vec * TIME * 0.15);
		float light_gap = smoothstep(0.35, 0.65, dapple) * 0.6 + smoothstep(0.55, 0.75, dapple_fine) * 0.4;
		float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
		float sun_factor = smoothstep(0.02, 0.20, sky_lum);
		float shade = sc * sun_factor;
		col *= (1.0 - shade * (1.0 - light_gap) * 0.10);
		col *= vec3(1.0 + light_gap * shade * 0.08, 1.0 + light_gap * shade * 0.04, 1.0 - light_gap * shade * 0.024);
	}

	// Cloud shadows
	float sky_lum_cs = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
	float daytime_cs = smoothstep(0.05, 0.20, sky_lum_cs);
	col *= (1.0 - cloud_shadow(v_world_pos.xz, cloud_coverage_g, cloud_speed_g, TIME, wind_vec) * daytime_cs);

	ALBEDO = col;

	// Normal map
	if (has_normal_map) {
		NORMAL_MAP = texture(grass_normal, UV).rgb;
		NORMAL_MAP_DEPTH = 1.5;
	}

	// PBR — grass waxy cuticle, tip shinier
	ROUGHNESS = mix(0.72, 0.52, v_height_t);
	ROUGHNESS += (blade_seed - 0.5) * 0.10;
	SPECULAR = mix(0.06, 0.12, v_height_t);
	METALLIC = 0.0;
	BACKLIGHT = vec3(0.25, 0.30, 0.08) * mix(0.6, 1.0, v_height_t);

	// --- Weather ---
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.65, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.25, rain_wetness);
		SPECULAR = mix(SPECULAR, 0.35, rain_wetness);
	}

	if (snow_cover > 0.01) {
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_cover * 0.65);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_cover * 0.5);
	}

	// Frost crystals
	if (winter_t > 0.1 && snow_cover < 0.6) {
		float frost_mask = winter_t * smoothstep(0.2, 0.8, v_height_t);
		float crystal = hash2(floor(v_world_pos.xz * 12.0 + vec2(v_height_t * 5.0)));
		float sparkle = step(0.80, crystal) * frost_mask;
		ALBEDO = mix(ALBEDO, ALBEDO * vec3(1.10, 1.12, 1.18), frost_mask * 0.4);
		ROUGHNESS = mix(ROUGHNESS, 0.10, sparkle * 0.8);
		SPECULAR = mix(SPECULAR, 0.60, sparkle * 0.9);
	}

	// Dew
	if (dew_amount > 0.01 && v_height_t > 0.5) {
		float dew = dew_amount * smoothstep(0.5, 0.85, v_height_t);
		ROUGHNESS = mix(ROUGHNESS, 0.20, dew * 0.4);
		SPECULAR = mix(SPECULAR, 0.30, dew * 0.3);
		ALBEDO *= mix(1.0, 1.06, dew * 0.3);
	}
}

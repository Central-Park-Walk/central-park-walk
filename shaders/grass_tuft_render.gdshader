// Grass Tier 2 render shader — static MultiMesh crossed-card tufts (15-55m)
// Lightweight version of grass_particle_render.gdshader for mid-distance rendering.
// Zone palettes and patch noise are shared with Tier 1 blade shader and Tier 3
// terrain impostor to ensure seamless color coherence across all LOD tiers.

shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap;

global uniform float season_t;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;
global uniform float cloud_coverage_g;
global uniform float cloud_speed_g;

#include "res://shaders/include/seasonal.gdshaderinc"
#include "res://shaders/include/hash_noise.gdshaderinc"

varying vec3 v_world_pos;
varying float v_height_t;
varying vec4 v_custom;  // zone_id/15, canopy, seed, unused

void vertex() {
	v_height_t = UV.y;
	v_custom = INSTANCE_CUSTOM;
	v_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;

	// Winter shrink
	float w_winter = smoothstep(2.7, 3.5, season_t);
	float w_snow = max(w_winter, snow_cover);
	if (w_snow > 0.0) {
		VERTEX.y *= mix(1.0, 0.15, w_snow);
	}

	// Simplified wind: world-space noise displaces tips in wind direction.
	// No Rodrigues rotation — at 15-50m, per-blade curvature is invisible.
	float wind_str = length(wind_vec) * (1.0 - w_snow);
	if (wind_str > 0.001 && v_height_t > 0.1) {
		vec2 wind_dir = normalize(wind_vec + vec2(0.001));
		vec2 wind_uv = v_world_pos.xz * 0.08 - wind_dir * TIME * 0.4;
		float wind_noise = vnoise(wind_uv) * wind_str;
		float bend = wind_noise * v_height_t * v_height_t * 0.15;
		VERTEX.x += bend * wind_dir.x;
		VERTEX.z += bend * wind_dir.y;
	}
}

void fragment() {
	// Heavy snow/winter: discard
	float frag_snow = max(smoothstep(2.7, 3.5, season_t), snow_cover);
	if (frag_snow > 0.6) discard;

	// Texture alpha for blade silhouette
	vec4 tex = texture(grass_albedo, UV);
	ALPHA = tex.a;
	ALPHA_HASH_SCALE = 1.0;

	// Decode per-instance data
	int zone_id = int(v_custom.r * 15.0 + 0.5);
	float canopy_cover = v_custom.g;
	float inst_seed = v_custom.b;

	// --- Zone-specific color palettes (identical to grass_particle_render) ---
	vec3 color_small, color_large;
	if (zone_id == 0) {
		color_small = vec3(0.08, 0.38, 0.12);
		color_large = vec3(0.18, 0.48, 0.16);
	} else if (zone_id == 1) {
		color_small = vec3(0.07, 0.34, 0.07);
		color_large = vec3(0.16, 0.44, 0.11);
	} else if (zone_id == 2) {
		color_small = vec3(0.17, 0.36, 0.06);
		color_large = vec3(0.40, 0.50, 0.10);
	} else if (zone_id == 3) {
		color_small = vec3(0.12, 0.40, 0.10);
		color_large = vec3(0.20, 0.45, 0.13);
	} else if (zone_id == 4) {
		color_small = vec3(0.08, 0.36, 0.08);
		color_large = vec3(0.15, 0.42, 0.12);
	} else if (zone_id == 5 || zone_id == 6) {
		color_small = vec3(0.06, 0.20, 0.08);
		color_large = vec3(0.12, 0.28, 0.13);
	} else if (zone_id == 7) {
		color_small = vec3(0.06, 0.30, 0.10);
		color_large = vec3(0.14, 0.42, 0.16);
	} else if (zone_id == 8) {
		color_small = vec3(0.16, 0.32, 0.06);
		color_large = vec3(0.36, 0.46, 0.10);
	} else if (zone_id == 9) {
		color_small = vec3(0.09, 0.35, 0.08);
		color_large = vec3(0.18, 0.44, 0.12);
	} else if (zone_id == 10 || zone_id == 11) {
		color_small = vec3(0.10, 0.22, 0.06);
		color_large = vec3(0.20, 0.30, 0.08);
	} else {
		color_small = vec3(0.12, 0.34, 0.08);
		color_large = vec3(0.28, 0.44, 0.12);
	}

	// Patchiness: same world-space noise as blade shader (3m scale)
	float patch_factor = vnoise(v_world_pos.xz / 3.0);
	vec3 col = mix(color_small, color_large, patch_factor);

	// Texture luminance modulates zone color (preserves blade detail, enforces palette)
	float tex_lum = dot(tex.rgb, vec3(0.299, 0.587, 0.114));
	col *= mix(0.80, 1.20, tex_lum);

	// Root-to-tip gradient
	float root_t = smoothstep(0.0, 0.30, v_height_t);
	col *= mix(0.60, 1.0, root_t);

	// Thatch tint at base
	vec3 thatch_col = color_small * 0.5;
	col = mix(col, thatch_col, (1.0 - root_t) * 0.4);

	// Per-instance hue variation (±10%)
	col *= mix(vec3(0.90, 1.04, 1.06), vec3(1.10, 0.96, 0.90), inst_seed);

	// Broad meadow variation (12m scale) + warm/cool hue shift (8m scale)
	float broad_patch = vnoise(v_world_pos.xz / 12.0);
	col *= mix(0.95, 1.05, broad_patch);
	float hue_patch = vnoise(v_world_pos.xz / 8.0 + vec2(51.3, 17.9));
	col *= mix(vec3(1.02, 1.0, 0.96), vec3(0.97, 1.0, 1.04), hue_patch);

	// Dead tuft accents (~22% of area, same noise as blade shader)
	float dead_noise = vnoise(v_world_pos.xz * 0.8 + vec2(73.1, 29.7));
	float dead_mask = smoothstep(0.55, 0.68, dead_noise);
	if (dead_mask > 0.0) {
		vec3 dead_col = vec3(0.22, 0.18, 0.08);
		col = mix(col, dead_col, dead_mask * 0.50);
	}

	// EGTTR-style warmth
	col *= vec3(1.04, 1.01, 0.94);
	if (v_height_t > 0.5) {
		float yellow_t = smoothstep(0.5, 1.0, v_height_t);
		col *= vec3(1.0 + yellow_t * 0.10, 1.0 + yellow_t * 0.05, 1.0 - yellow_t * 0.06);
	}

	// Seasonal color
	float spring_t = sn_veg_spring(season_t);
	float autumn_t = sn_veg_autumn(season_t);
	float winter_t = sn_veg_winter(season_t);
	col = mix(col, col * vec3(1.1, 1.15, 0.75), spring_t * 0.6);
	col = mix(col, vec3(0.16, 0.12, 0.04), autumn_t * 0.7);
	col = mix(col, vec3(0.12, 0.10, 0.06), winter_t);

	// Canopy leaf litter at roots
	if (canopy_cover > 0.3) {
		vec3 litter_col = mix(vec3(0.28, 0.22, 0.14), vec3(0.34, 0.26, 0.16),
			vnoise(v_world_pos.xz * 0.5));
		float litter_strength = smoothstep(0.3, 0.7, canopy_cover) * (1.0 - root_t) * 0.5;
		col = mix(col, litter_col, litter_strength);
	}

	// Canopy dapple (simplified — single octave)
	if (canopy_cover > 0.01) {
		float sc = canopy_cover * mix(1.0, 0.3, sn_canopy_loss(season_t))
			* mix(1.0, 0.15, sn_canopy_bare(season_t))
			* mix(0.5, 1.0, sn_canopy_fill(season_t));
		vec2 dapple_uv = v_world_pos.xz * 0.35 + wind_vec * TIME * 0.08;
		float light_gap = smoothstep(0.35, 0.65, vnoise(dapple_uv));
		float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
		float shade = sc * smoothstep(0.02, 0.20, sky_lum);
		col *= (1.0 - shade * (1.0 - light_gap) * 0.10);
	}

	// Cloud shadows
	float sky_lum_cs = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
	float daytime_cs = smoothstep(0.05, 0.20, sky_lum_cs);
	col *= (1.0 - cloud_shadow(v_world_pos.xz, cloud_coverage_g, cloud_speed_g, TIME, wind_vec) * daytime_cs);

	// Aerial perspective: desaturate + cool shift with distance (matches terrain shader)
	float cam_dist = length(v_world_pos - (inverse(VIEW_MATRIX) * vec4(0, 0, 0, 1)).xyz);
	float aerial_t = smoothstep(20.0, 120.0, cam_dist);
	float g_lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
	col = mix(col, vec3(g_lum), aerial_t * 0.15);
	col *= mix(vec3(1.0), vec3(0.96, 0.97, 1.04), aerial_t);

	ALBEDO = col;

	// PBR — simplified for distance
	ROUGHNESS = mix(0.72, 0.58, v_height_t);
	SPECULAR = mix(0.06, 0.10, v_height_t);
	METALLIC = 0.0;
	BACKLIGHT = vec3(0.30, 0.36, 0.10) * mix(0.5, 1.0, v_height_t);

	// Weather
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.65, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.30, rain_wetness);
	}
	if (snow_cover > 0.01) {
		ALBEDO = mix(ALBEDO, vec3(0.92, 0.93, 0.96), snow_cover * 0.65);
		ROUGHNESS = mix(ROUGHNESS, 0.90, snow_cover * 0.5);
	}
}

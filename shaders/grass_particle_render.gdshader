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
	// Height within tuft: UV.y = 0 at base, 1 at tip (baked in mesh).
	// Used for wind bend (roots stay, tips sway) and color gradient.
	v_height_t = UV.y;

	data.rg = INSTANCE_CUSTOM.rg;
	data[3] = INSTANCE_CUSTOM[3];

	// Winter: shrink blades toward ground (model space, before world transform)
	float w_winter = smoothstep(2.7, 3.5, season_t);
	float w_snow = max(w_winter, snow_cover);
	if (w_snow > 0.0) {
		VERTEX.y *= mix(1.0, 0.08, w_snow);
	}

	// Transform to world space
	vec3 w_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 instance_root = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_world_pos = w_vertex;

	// --- Wind curvature: rotate vertex in an arc around blade root ---
	// Real grass bends with progressive curvature — base stays upright,
	// mid-blade curves, tip arcs over. Rodrigues rotation with angle
	// proportional to height² gives natural droop.
	float wind_suppression = 1.0 - w_snow;
	float grass_scale = pow(max(INSTANCE_CUSTOM[3], 0.01), 0.707);
	float wind_noise = INSTANCE_CUSTOM[2]; // per-instance wind from process shader

	// Bend angle: quadratic with height for progressive curvature
	// Clamped to ~1.0 rad (~57°) to prevent blades flattening against ground
	float bend_strength = wind_noise * grass_scale * wind_suppression;
	float bend_angle = bend_strength * v_height_t * v_height_t * 0.9;
	bend_angle = min(bend_angle, 1.0);

	// Bend axis: perpendicular to wind direction (horizontal)
	vec2 wind_dir = normalize(wind_vec + vec2(0.001));
	vec3 bend_axis = vec3(-wind_dir.y, 0.0, wind_dir.x);

	// Per-instance lateral wobble: subtle sway perpendicular to wind
	float wobble = sin(TIME * 2.0 * (1.0 + data.r + data.g)) * 0.12 * wind_suppression;
	bend_axis = normalize(bend_axis + vec3(wind_dir.x, 0.0, wind_dir.y) * wobble);

	// Rodrigues rotation: rotate offset from root around bend_axis
	if (bend_angle > 0.001) {
		vec3 offset = w_vertex - instance_root;
		float c = cos(bend_angle);
		float s = sin(bend_angle);
		float d = dot(bend_axis, offset);
		vec3 rotated = offset * c + cross(bend_axis, offset) * s + bend_axis * d * (1.0 - c);
		w_vertex = instance_root + rotated;
	}

	data[2] = bend_strength; // pass to fragment for wind color shift

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

	// Decode zone + terrain data from COLOR (set by particle process shader)
	// R = zone_id / 15.0, G = canopy_cover, B = terrain_tint.r, A = terrain_tint.g
	int zone_id = int(COLOR.r * 15.0 + 0.5);
	float canopy_cover = COLOR.g;
	float blade_seed = data.r;
	vec3 terrain_tint = vec3(COLOR.b, COLOR.a, min(COLOR.b, COLOR.a));

	// --- Zone-specific color palettes ---
	// Values in linear sRGB; all brightened ~25-30% from original to compensate
	// for stacking darkening (base-to-tip, broad patch, canopy, cloud shadows).
	vec3 color_small, color_large;
	if (zone_id == 0) {
		// SheepMeadow: cool blue-green Kentucky bluegrass
		color_small = vec3(0.08, 0.38, 0.12);
		color_large = vec3(0.18, 0.48, 0.16);
	} else if (zone_id == 1) {
		// GreatLawn: deep rich emerald
		color_small = vec3(0.07, 0.34, 0.07);
		color_large = vec3(0.16, 0.44, 0.11);
	} else if (zone_id == 2) {
		// NorthMeadow: warm open meadow, noticeably yellower
		color_small = vec3(0.17, 0.36, 0.06);
		color_large = vec3(0.40, 0.50, 0.10);
	} else if (zone_id == 3) {
		// FormalGarden: uniform bright green, low contrast
		color_small = vec3(0.12, 0.40, 0.10);
		color_large = vec3(0.20, 0.45, 0.13);
	} else if (zone_id == 4) {
		// SportsTurf: maintained athletic green
		color_small = vec3(0.08, 0.36, 0.08);
		color_large = vec3(0.15, 0.42, 0.12);
	} else if (zone_id == 5 || zone_id == 6) {
		// NorthWoods/Ramble: cooler shade grass, still visible
		color_small = vec3(0.06, 0.20, 0.08);
		color_large = vec3(0.12, 0.28, 0.13);
	} else if (zone_id == 7) {
		// Waterside: lush saturated sedge green
		color_small = vec3(0.06, 0.30, 0.10);
		color_large = vec3(0.14, 0.42, 0.16);
	} else if (zone_id == 8) {
		// WildMeadow: warm mixed grasses, golden-green
		color_small = vec3(0.16, 0.32, 0.06);
		color_large = vec3(0.36, 0.46, 0.10);
	} else if (zone_id == 9) {
		// OpenLawn: standard maintained green
		color_small = vec3(0.09, 0.35, 0.08);
		color_large = vec3(0.18, 0.44, 0.12);
	} else if (zone_id == 10 || zone_id == 11) {
		// Woodland: warm brown-green understory
		color_small = vec3(0.10, 0.22, 0.06);
		color_large = vec3(0.20, 0.30, 0.08);
	} else {
		// Default: standard mid-green
		color_small = vec3(0.12, 0.34, 0.08);
		color_large = vec3(0.28, 0.44, 0.12);
	}

	// Patchiness: world-space noise ties size to color
	float patch_factor = vnoise(v_world_pos.xz / 3.0);
	vec3 col = mix(color_small, color_large, patch_factor);

	// Textured tufts: use the mesh's own PBR texture color as primary,
	// with subtle zone tint for regional variation. This ensures grass
	// particles blend with the terrain (both use natural grass hues)
	// rather than fighting it with a separate palette.
	if (use_texture) {
		vec3 tex_col = texture(grass_albedo, UV).rgb;
		// 75% mesh texture, 25% zone palette — texture drives appearance,
		// zone provides subtle regional hue shift
		col = mix(tex_col, col, 0.25);
	}

	// Root-to-tip gradient: grass emerges from dark thatch layer at ground.
	// Real grass has a dense brown thatch zone at its base where dead stems,
	// soil, and mulch are visible. This hides the terrain-to-grass transition.
	float root_t = smoothstep(0.0, 0.30, v_height_t);
	col *= mix(0.60, 1.0, root_t);

	// Zone-derived thatch tint at base — ties grass roots to terrain character.
	// Woodland roots are browner (leaf litter), lawns are dark green (dense turf).
	vec3 thatch_col = color_small * 0.5;
	col = mix(col, thatch_col, (1.0 - root_t) * 0.4);

	// Terrain color map influence at roots (propagates Terrain3D color painting).
	// When terrain_tint is white (default), this is a no-op.
	col *= mix(terrain_tint, vec3(1.0), root_t * 0.7 + 0.3);

	// Per-instance hue variation
	col *= mix(vec3(0.97, 1.01, 1.03), vec3(1.03, 0.99, 0.95), blade_seed);

	// Broad meadow variation (12m scale)
	float broad_patch = vnoise(v_world_pos.xz / 12.0);
	col *= mix(0.95, 1.05, broad_patch);

	// --- Seasonal color ---
	float spring_t = sn_veg_spring(season_t);
	float autumn_t = sn_veg_autumn(season_t);
	float winter_t = sn_veg_winter(season_t);
	col = mix(col, col * vec3(1.1, 1.15, 0.75), spring_t * 0.6);
	col = mix(col, vec3(0.16, 0.12, 0.04), autumn_t * 0.7);
	col = mix(col, vec3(0.12, 0.10, 0.06), winter_t);

	// --- Canopy leaf litter at grass roots (matches terrain shader overlay) ---
	if (canopy_cover > 0.3) {
		vec3 litter_col = mix(vec3(0.28, 0.22, 0.14), vec3(0.34, 0.26, 0.16),
			vnoise(v_world_pos.xz * 0.5));
		float litter_strength = smoothstep(0.3, 0.7, canopy_cover) * (1.0 - root_t) * 0.5;
		col = mix(col, litter_col, litter_strength);
	}

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

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
#include "res://shaders/include/grass_zone_colors.gdshaderinc"

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

	// Texture-based alpha — use hash dithering for soft edges instead of
	// hard scissor cutout. Eliminates the jagged card-geometry look.
	if (use_texture) {
		float tex_alpha = texture(grass_albedo, UV).a;
		ALPHA = tex_alpha;
		ALPHA_HASH_SCALE = 1.0;
	}

	// Distance fade: dissolve blades as they approach the particle grid edge.
	// CUSTOM[3] = scale.y (includes fade_factor from process shader).
	// Without this, shortened blades create a hard arc where the grid ends.
	float blade_scale = data[3];
	float dist_alpha = smoothstep(0.0, 0.4, blade_scale);
	if (dist_alpha < 0.01) discard;
	if (use_texture) {
		ALPHA *= dist_alpha;
	} else {
		ALPHA = dist_alpha;
		ALPHA_HASH_SCALE = 1.0;
	}

	// Decode zone + terrain data from COLOR (set by particle process shader)
	// R = zone_id / 15.0, G = canopy_cover, B = terrain_tint.r, A = terrain_tint.g
	int zone_id = int(COLOR.r * 15.0 + 0.5);
	float canopy_cover = COLOR.g;
	float blade_seed = data.r;
	vec3 terrain_tint = vec3(COLOR.b, COLOR.a, min(COLOR.b, COLOR.a));

	// --- Base color from shared zone palette + macro variation ---
	// grass_base_color handles: zone palette, macro splotchiness (20m),
	// landscape gradient (70m), warm/cool drift (8m), micro (3m),
	// dead tuft accents, and EGTTR warmth.
	vec3 col = grass_base_color(zone_id, v_world_pos.xz);

	// Texture modulation: texture luminance adds blade-level detail
	// without overriding the zone palette. Same approach as tuft shader
	// so the LOD boundary is invisible.
	if (use_texture) {
		float tex_lum = dot(texture(grass_albedo, UV).rgb, vec3(0.299, 0.587, 0.114));
		col *= mix(0.85, 1.15, tex_lum);
	} else {
		// Blade meshes (no texture): raw palette green is 3× red — too vivid
		// compared to naturally muted tufts and terrain. Real massed grass
		// at eye level reads as olive, not vivid green.
		float blade_lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
		col = mix(col, vec3(blade_lum), 0.28); // 28% desaturation
		col *= vec3(1.06, 0.99, 0.90);         // strong warm shift
	}

	// Root-to-tip gradient: subtle darkening at base only.
	// 0.80 base (was 0.70) — blade roots still slightly darker than tips
	// but not enough to create a visible dark circle around the camera.
	float root_t = smoothstep(0.0, 0.30, v_height_t);
	col *= mix(0.80, 1.0, root_t);

	// Thatch tint at base — ties roots to terrain character.
	vec3 c_lo, c_hi;
	grass_zone_palette(zone_id, c_lo, c_hi);
	vec3 thatch_col = c_lo * 0.5;
	col = mix(col, thatch_col, (1.0 - root_t) * 0.25);

	// Terrain color map influence at roots (propagates Terrain3D color painting).
	col *= mix(terrain_tint, vec3(1.0), root_t * 0.7 + 0.3);

	// Compensate for root darkening + thatch averaging 95% brightness.
	// Without this, the blade-covered area reads as a shadow around the camera
	// because the terrain impostor is at 100%.
	col *= 1.05;

	// Per-instance hue variation (±10% for visible blade-to-blade difference)
	col *= mix(vec3(0.90, 1.04, 1.06), vec3(1.10, 0.96, 0.90), blade_seed);

	// Tip warmth: yellow highlights at blade tips from waxy cuticle
	if (v_height_t > 0.5) {
		float yellow_t = smoothstep(0.5, 1.0, v_height_t);
		col *= vec3(1.0 + yellow_t * 0.10, 1.0 + yellow_t * 0.05, 1.0 - yellow_t * 0.06);
	}

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
	BACKLIGHT = vec3(0.35, 0.42, 0.12) * mix(0.5, 1.0, v_height_t);

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

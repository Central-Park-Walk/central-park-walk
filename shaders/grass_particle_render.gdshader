// Central Park grass render shader — GPU particle grass tufts
// Renders real-geometry grass tuft meshes with zone-aware color,
// seasonal modulation, canopy dapple, weather effects, and wind.

shader_type spatial;
// diffuse_lambert matches the terrain shader (Burley's grazing retro-
// reflection is wrong for turf — see terrain3d_override.gdshader header).
render_mode skip_vertex_transform, cull_disabled, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap;
uniform bool has_normal_map = false;
uniform bool use_texture = true;
uniform bool debug_highlight = false;
uniform vec3 debug_color : source_color = vec3(1.0, 0.0, 1.0);
// 0=Lawn 1=Shade 2=Wild 3=Sedge — set per layer in _setup_grass_particles
uniform int biome_id = 0;

global uniform float season_t;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform float dew_amount;
global uniform vec3 sky_reflect_color;
global uniform float cloud_coverage_g;
global uniform float cloud_speed_g;
global uniform float turf_sheen;

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
	// Blend blade normals toward world up so blades shade like the turf
	// surface they grow from: with raw card normals, blade sides face the
	// sun at NdotL≈0 and the carpet reads darker than the terrain beyond
	// the 36-60m fade. 0.7 keeps a little directional life on the taller
	// unmown biomes. Pairs with the FRONT_FACING pre-flip in fragment() —
	// without it, the engine's backface negation turns half of these
	// normals DOWN (measured 2026-06-11: blade pixels -25..-40% vs
	// terrain under ambient-only light — the "dark circle" root cause).
	vec3 up_view = normalize((VIEW_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
	NORMAL = normalize(mix(MODELVIEW_NORMAL_MATRIX * NORMAL, up_view, 0.7));
	BINORMAL = MODELVIEW_NORMAL_MATRIX * BINORMAL;
	TANGENT = MODELVIEW_NORMAL_MATRIX * TANGENT;
}

void fragment() {
	// The renderer negates the geometric normal for backfacing fragments
	// (cull_disabled). Half of all blade quads face away from the camera,
	// so the up-blended vertex normal becomes DOWN for them — ground-
	// hemisphere ambient and zero sun. Measured 2026-06-11: blade pixels
	// -25..-40% vs terrain under ambient-only light. Pre-flip here so the
	// engine's flip restores the intended up-facing normal.
	if (!FRONT_FACING) { NORMAL = -NORMAL; }

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

	// Decode zone data from COLOR (set by particle process shader).
	// R = zone_id/15, G = canopy_cover, B = turf wear, A = unused.
	// biome_id comes as a material uniform — each layer has its own render
	// material. (Decoding it from COLOR.b was a bug: the spawn shader writes
	// terrain tint there, so per-biome tints fired on color-map data.)
	int zone_id = int(COLOR.r * 15.0 + 0.5);
	float canopy_cover = COLOR.g;
	float blade_seed = data.r;

	// --- Base color from shared zone palette + macro variation ---
	// grass_base_color_no_dead handles: zone palette, macro splotchiness
	// (20m), landscape gradient (70m), warm/cool drift (8m), micro (3m),
	// and golden undertone. Dead tufts are applied below with a seasonal
	// gate so July reads green and autumn ramps the brown up.
	vec3 col = grass_base_color_no_dead(zone_id, v_world_pos.xz);
	// Shore band: sedge palette comes in by tussock patches (same mask as
	// the terrain shader so patches line up across the 36-60m fade).
	if (zone_id == 13) {
		col = mix(grass_base_color_no_dead(0, v_world_pos.xz), col,
			sedge_patch_mask(v_world_pos.xz));
	}
	float autumn_t_early = sn_veg_autumn(season_t);
	col = apply_dead_tufts(col, v_world_pos.xz, 0.15 + 0.85 * autumn_t_early);

	// Turf wear: survivors in worn patches read dusty/dry instead of
	// popping green against the dirt. COLOR.b carries the spawn-time wear
	// (baked + ambient); turf_wear_total re-maxes it with the canopy
	// compaction term so blades under dense crowns match the dirt terrain
	// (ambient recomputes to the identical value — same noise, same pos).
	float wear_total = turf_wear_total(COLOR.b, canopy_cover, zone_id, v_world_pos.xz);
	col = apply_turf_wear(col, wear_total, v_world_pos.xz);

	// Texture modulation: texture luminance adds blade-level detail
	// without overriding the zone palette. Same approach as tuft shader
	// so the LOD boundary is invisible.
	if (use_texture) {
		float tex_lum = dot(texture(grass_albedo, UV).rgb, vec3(0.299, 0.587, 0.114));
		col *= mix(0.85, 1.15, tex_lum);
	} else {
		// Blade meshes (no texture): light desaturation only.
		float blade_lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
		col = mix(col, vec3(blade_lum), 0.08);
		col *= vec3(1.02, 1.00, 0.97);
	}

	// Per-biome tint — moderate now that the terrain shader also tints
	// per biome. Blades and terrain pull in the same hue direction so
	// boundaries read clearly without either fighting the other.
	if (biome_id == 0) {
		col *= vec3(1.05, 1.02, 0.92);  // Lawn: subtle warm
	} else if (biome_id == 1) {
		col *= vec3(0.75, 0.88, 1.18);  // Shade: cool blue-green
	} else if (biome_id == 2) {
		col *= vec3(1.32, 1.05, 0.65);  // Wild: warm amber
	} else if (biome_id == 3) {
		// Sedge: cool teal — masked by the same tussock patches; off-patch
		// blades read like the lawn tint so the band isn't a flat decal.
		col *= mix(vec3(1.05, 1.02, 0.92), vec3(0.78, 1.02, 1.25),
			sedge_patch_mask(v_world_pos.xz));
	}

	// Root-to-tip gradient: very subtle darkening at base only.
	// 0.96 base — relaxed from 0.92 (and originally 0.80). Closer to 1.0
	// because looking down at the close-up grid means most pixels are
	// blade bases; any noticeable root darkening reads as a "dark disc
	// following the camera" against the terrain just beyond.
	float root_t = smoothstep(0.0, 0.30, v_height_t);
	col *= mix(0.98, 1.0, root_t);

	// Thatch tint at base — barely-there now. The previous values created
	// a visible darker zone where blades render vs terrain just beyond.
	vec3 c_lo, c_hi;
	grass_zone_palette(zone_id, c_lo, c_hi);
	vec3 thatch_col = c_lo * 0.5;
	col = mix(col, thatch_col, (1.0 - root_t) * 0.02);

	// Blade-vs-terrain equalization (dark-circle fix, 2026-06-11). With
	// the backface normal pre-flip + up-blended normals + Lambert in
	// place, blade pixels measured +10.5% BRIGHTER than the terrain they
	// cover (same-pixel A/B vs --diag-hide=grass at fixed cloud seed,
	// noon): the blade chain's extras (dead tufts, biome tint, tip
	// warmth, card specular) stack on top of now-correct lighting. Trim
	// to parity so the 36-60m fade ring is invisible in both directions.
	col *= 0.905;

	// terrain_tint removed — dithered crossfade means terrain between blades
	// is now filled by the next LOD tier, not visible through blade gaps.

	// Compensation factor dropped: previously col *= 1.05 here to lift the
	// blade area against a terrain that rendered at 100% native brightness.
	// terrain3d_override now blends ALBEDO 75% toward grass_base_color_no_dead
	// in grass zones, which brings the surrounding terrain into the blade
	// brightness range. Keeping the boost made blades read brighter/yellower
	// than terrain → a halo following the camera as the player walked.

	// Per-instance hue variation (±10% for visible blade-to-blade difference)
	col *= mix(vec3(0.90, 1.04, 1.06), vec3(1.10, 0.96, 0.90), blade_seed);

	// Tip warmth: yellow highlights at blade tips from waxy cuticle.
	// Scaled by season — full strength in autumn dry-down, ~25% in peak
	// summer so July blades read green instead of constantly amber-tipped.
	if (v_height_t > 0.5) {
		float yellow_t = smoothstep(0.5, 1.0, v_height_t);
		float tip_scale = 0.25 + 0.75 * autumn_t_early;
		col *= vec3(1.0 + yellow_t * 0.10 * tip_scale,
		            1.0 + yellow_t * 0.05 * tip_scale,
		            1.0 - yellow_t * 0.06 * tip_scale);
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

	if (debug_highlight) {
		ALBEDO = debug_color;  // per-biome flat color — verifies coverage + height
		ALPHA = 1.0;
	} else {
		ALBEDO = col;
	}

	// Normal map
	if (has_normal_map) {
		NORMAL_MAP = texture(grass_normal, UV).rgb;
		NORMAL_MAP_DEPTH = 1.5;
	}

	// PBR — aligned with tuft render shader for seamless LOD transitions
	ROUGHNESS = mix(0.72, 0.58, v_height_t);
	ROUGHNESS += (blade_seed - 0.5) * 0.10;
	SPECULAR = mix(0.06, 0.10, v_height_t);
	// Turf sheen (grass.md §6) — same global as the terrain shader so the
	// 36-60m blade fade ring stays invisible. Tips sheen more than bases.
	ROUGHNESS = mix(ROUGHNESS, 0.60, turf_sheen);
	SPECULAR = mix(SPECULAR, 0.30, turf_sheen * mix(0.7, 1.0, v_height_t));
	METALLIC = 0.0;
	BACKLIGHT = vec3(0.30, 0.36, 0.10) * mix(0.5, 1.0, v_height_t);

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

shader_type spatial;
render_mode cull_disabled;

#include "res://shaders/include/hash_noise.gdshaderinc"

global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float snow_cover;
global uniform float rain_wetness;
global uniform float dew_amount;
global uniform vec3 sky_reflect_color;

// Canopy coverage map: grayscale, 2K resolution. Bright = under tree canopy.
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;

varying float v_grass_type;
varying vec3 v_world_pos;
varying float v_path_prox;   // 0-1: proximity to nearest path (for edge wear)
varying float v_edge_fade;   // 0-1: soft fade at tile edge (0=center, 1=perimeter)

void vertex() {
	// INSTANCE_CUSTOM: R = grass_type, G = random, B = path_proximity
	v_grass_type = INSTANCE_CUSTOM.r;
	v_path_prox = INSTANCE_CUSTOM.b;

	vec3 origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	v_world_pos = origin;

	v_edge_fade = 0.0;

	// --- Per-BLADE variation from world-space noise ---
	// Sample at each blade's world XZ position (not tile center).
	// Continuous across tile boundaries — no visible grid.
	vec2 blade_world_xz = origin.xz + VERTEX.xz;
	float blade_h_noise = vnoise(blade_world_xz * 0.5);
	float blade_clump = vnoise(blade_world_xz * 0.25 + vec2(42.0));
	// Height: ±20% per blade
	VERTEX.y *= 0.80 + blade_h_noise * 0.40;
	// Clumping: thin out blades in sparse noise areas
	float clump_scale = smoothstep(0.10, 0.40, blade_clump);
	VERTEX.xyz *= mix(0.5, 1.0, clump_scale);

	// Height-based sway: model-space VERTEX.y (0 at base, tip varies by type)
	float sway = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);

	// Wind response varies by type (0-9):
	// 0-4: lawn types — moderate sway
	// 5-6: woodland — minimal sway (sheltered under canopy)
	// 7: waterside — moderate
	// 8: wild meadow — strong dramatic flow
	// 9: open lawn — moderate
	float flex = 0.7;  // default
	if (v_grass_type > 7.5) {
		flex = 2.5;  // wild meadow: dramatic flow
	} else if (v_grass_type > 6.5) {
		flex = 0.8;  // waterside: moderate
	} else if (v_grass_type > 4.5) {
		flex = 0.35; // woodland: sheltered under canopy
	} else if (v_grass_type > 3.5) {
		flex = 0.5;  // sports turf: short, less sway
	}
	float rustle = (0.2 + wind_str * 0.8) * flex;

	// Mowing stripes removed — would need to come from data, not procedural noise.

	// Base sway: continuous oscillation
	float px = origin.x * 0.15 + origin.z * 0.22;
	float pz = origin.z * 0.18 + origin.x * 0.12;
	VERTEX.x += sin(TIME * 1.8 + px) * 0.12 * sway * rustle;
	VERTEX.z += sin(TIME * 2.3 + pz) * 0.08 * sway * rustle;

	// Wind push: constant lean in wind direction
	VERTEX.x += wind_vec.x * sway * 0.4 * flex;
	VERTEX.z += wind_vec.y * sway * 0.4 * flex;

	// Traveling wind gusts
	float gust_phase = origin.x * 0.04 + origin.z * 0.05;
	float gust = sin(TIME * 0.5 + gust_phase) * 0.5 + 0.5;
	gust = gust * gust * gust;
	float gust_str = gust * wind_str * 0.5 * flex;
	VERTEX.x += wind_vec.x * sway * gust_str;
	VERTEX.z += wind_vec.y * sway * gust_str;

	// Blade flutter: high-frequency micro-movement
	float flutter = sin(TIME * 5.5 + VERTEX.x * 14.0 + VERTEX.z * 10.0) * 0.015 * rustle;
	flutter += sin(TIME * 8.0 + VERTEX.z * 18.0) * 0.008 * gust_str;
	VERTEX.y += flutter * sway;

	// Winter: lawn types go dormant — shrink nearly flat to avoid grid pattern
	// on brown terrain. Terrain shader handles winter ground color.
	float winter_t = smoothstep(3.0, 3.5, season_t);
	if (winter_t > 0.0 && (v_grass_type < 4.5 || v_grass_type > 8.5)) {
		VERTEX.y *= mix(1.0, 0.08, winter_t);  // nearly flat — 8% of summer height
	}
	// Woodland grass also shrinks but less (some evergreen understory)
	if (winter_t > 0.0 && v_grass_type > 4.5 && v_grass_type < 8.5) {
		VERTEX.y *= mix(1.0, 0.25, winter_t);
	}
}

void fragment() {
	// In deep winter, discard lawn grass entirely — the tiny 8% stubs create
	// a visible grid pattern in fog/snow. Terrain shader handles winter ground.
	float winter_discard = smoothstep(3.2, 3.8, season_t);
	if (winter_discard > 0.95 && v_grass_type < 4.5) discard;  // lawn types only

	// Soft tile edge: stochastically discard blades near tile perimeter.
	// Uses world-space hash (not FRAGCOORD) so pattern is stable as camera moves.
	if (v_edge_fade > 0.01) {
		float edge_dither = hash2(v_world_pos.xz * 3.7 + vec2(VERTEX.x * 11.0, VERTEX.z * 13.0));
		if (edge_dither < v_edge_fade * 0.85) discard;
	}

	// Aerial height-based fade — from above, individual grass blades would be
	// sub-pixel, but the tile grid pattern becomes visible as colored blocks.
	// World-space hash for stable discard pattern (no per-frame sparkle).
	float cam_h = INV_VIEW_MATRIX[3].y - v_world_pos.y;
	if (cam_h > 12.0) {
		float aerial_discard = smoothstep(12.0, 35.0, cam_h);
		float ad = hash2(v_world_pos.xz * 1.3 + vec2(41.2, 63.9));
		if (ad < aerial_discard) discard;
	}

	// Vertex colors from Blender model are the base — type determines color.
	vec3 col = COLOR.rgb;

	// Per-blade color variation from world-space noise.
	// Uses actual blade world position (v_world_pos + fragment XZ offset).
	vec2 frag_world_xz = v_world_pos.xz + VERTEX.xz;
	float col_var = vnoise(frag_world_xz * 0.4 + vec2(17.0, 33.0));
	col *= 0.90 + col_var * 0.20;
	float hue_var = vnoise(frag_world_xz * 0.2 + vec2(71.0, 13.0));
	col *= vec3(1.0 + hue_var * 0.06, 1.0, 1.0 - hue_var * 0.04);

	// Height-based AO: blade bases are darker (lighting effect).
	float blade_t = clamp(UV.y, 0.0, 1.0);
	float ao = mix(0.80, 1.0, smoothstep(0.0, 0.4, blade_t));
	col *= ao;

	// --- Seasonal colour modulation ---
	// Seasonal ramps MUST match terrain.gdshader exactly to prevent grass tile grid
	// being visible from seasonal color mismatch between blades and terrain
	float spring_t = 1.0 - smoothstep(0.0, 1.0, season_t);
	float autumn_t = smoothstep(2.0, 2.6, season_t) * (1.0 - smoothstep(2.8, 3.5, season_t));
	float winter_t = smoothstep(2.7, 3.1, season_t);  // match terrain's dormancy start

	col = mix(col, col * vec3(1.1, 1.15, 0.75), spring_t * 0.6);    // spring: match terrain
	// Autumn: flat target color (matching terrain) prevents noise amplification
	vec3 autumn_blade = vec3(0.16, 0.12, 0.04);  // match terrain's autumn_target
	col = mix(col, autumn_blade, autumn_t * 0.7);                     // autumn: uniform golden
	// Winter dormancy: match terrain's flat dormant brown color
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 dormant_brown = vec3(0.12, 0.10, 0.06);  // match terrain shader's winter_grass target
	col = mix(col, dormant_brown, winter_t);                          // winter: dormant brown

	// Color comes from the 3D model vertex colors. No procedural noise.
	// Path-edge wear is data-driven (pre-baked proximity in instance data).
	if (v_path_prox > 0.05) {
		vec3 worn_col = col * vec3(1.10, 0.88, 0.60);
		col = mix(col, worn_col, v_path_prox * 0.55);
		float wear_lum = dot(col, vec3(0.299, 0.587, 0.114));
		col = mix(col, vec3(wear_lum), v_path_prox * 0.25);
	}

	// --- Dappled canopy shade — grass under trees receives filtered light ---
	// Matches terrain.gdshader and path.gdshader canopy shade algorithm exactly.
	{
		vec2 canopy_uv = (v_world_pos.xz + hm_world_size * 0.5) / hm_world_size;
		float canopy = texture(canopy_map, canopy_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = smoothstep(2.5, 3.2, season_t);
			float winter_bare = smoothstep(3.0, 3.5, season_t);
			float spring_fill = smoothstep(0.0, 0.4, season_t);
			float sc = canopy * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare) * mix(0.5, 1.0, spring_fill);
			vec2 dapple_uv = v_world_pos.xz * 0.35 + wind_vec * TIME * 0.08;
			float dapple = vnoise(dapple_uv);
			float dapple_fine = vnoise(v_world_pos.xz * 1.2 + wind_vec * TIME * 0.15);
			float light_gap = smoothstep(0.35, 0.65, dapple) * 0.6 + smoothstep(0.55, 0.75, dapple_fine) * 0.4;
			float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum);
			float shade = sc * sun_factor;
			col *= (1.0 - shade * (1.0 - light_gap) * 0.35);
			// Warm sun spots through canopy gaps
			float warm_spots = light_gap * shade * 0.08;
			col *= vec3(1.0 + warm_spots, 1.0 + warm_spots * 0.5, 1.0 - warm_spots * 0.3);
		}
	}

	// Distance-based darkening (match terrain shader: blade highlights average out at distance)
	float blade_dist = length(v_world_pos - INV_VIEW_MATRIX[3].xyz);
	float dist_darken = smoothstep(30.0, 150.0, blade_dist) * 0.25;
	col *= (1.0 - dist_darken);
	// Aerial perspective: desaturate + cool shift at distance (match terrain)
	float blade_aerial = smoothstep(60.0, 300.0, blade_dist);
	float col_lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
	col = mix(col, vec3(col_lum), blade_aerial * 0.25);
	col = mix(col, col * vec3(0.94, 0.96, 1.04), blade_aerial);

	ALBEDO    = col;
	// Real grass is one of the most Lambertian surfaces in nature — almost no specular.
	// Any specular on 3D blades makes them pop brighter than the flat terrain underneath,
	// creating a visible grid pattern from tile placement.
	ROUGHNESS = 0.95;
	SPECULAR  = 0.0;
	METALLIC  = 0.0;

	// Rain: wet darkening + gloss
	if (rain_wetness > 0.01) {
		ALBEDO   *= mix(1.0, 0.65, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.25, rain_wetness);
		SPECULAR  = mix(SPECULAR,  0.35, rain_wetness);
	}

	// Snow on upper surfaces
	if (snow_cover > 0.01) {
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		float snow_on = upward * snow_cover * mix(0.5, 1.0, v_grass_type);
		ALBEDO    = mix(ALBEDO,    vec3(0.92, 0.93, 0.96), snow_on * 0.65);
		ROUGHNESS = mix(ROUGHNESS, 0.90,                   snow_on * 0.5);
	}

	// Frost sparkle: ice crystals on blade surfaces in winter
	// Each crystal is a tiny mirror — creates bright specular pinpoints
	if (winter_t > 0.1 && snow_cover < 0.6) {
		// Frost forms preferentially on blade tips (exposed, cools fastest)
		float frost_mask = winter_t * smoothstep(0.2, 0.8, blade_t);
		// Ice crystal facets: high-frequency hash gives random sparkle per blade position
		float crystal = hash2(floor(v_world_pos.xz * 12.0 + vec2(blade_t * 5.0)));
		// Only ~20% of positions sparkle (discrete crystal facets)
		float sparkle = step(0.80, crystal) * frost_mask;
		// Frost coating: thin rime ice makes surface smoother and more reflective
		ALBEDO    = mix(ALBEDO, ALBEDO * vec3(1.10, 1.12, 1.18), frost_mask * 0.4);
		ROUGHNESS = mix(ROUGHNESS, 0.10, sparkle * 0.8);
		SPECULAR  = mix(SPECULAR,  0.60, sparkle * 0.9);
		// Broad frost reduces roughness subtly even without sparkle
		ROUGHNESS = mix(ROUGHNESS, 0.40, frost_mask * 0.3);
	}

	// Morning dew — time-limited to dawn/morning via dew_amount global uniform.
	// Broad surface moisture + discrete droplet sparkle on blade tips.
	if (dew_amount > 0.01 && blade_t > 0.5) {
		float dew = dew_amount * smoothstep(0.5, 0.85, blade_t);
		ROUGHNESS = mix(ROUGHNESS, 0.20, dew * 0.4);
		SPECULAR  = mix(SPECULAR,  0.30, dew * 0.3);
		// Vividity boost — wet grass catches more light, looks greener
		ALBEDO *= mix(1.0, 1.06, dew * 0.3);
	}

	// Backlight / subsurface scattering — subtle, only at blade tips.
	// Reduced to prevent grass tiles appearing brighter than terrain underneath.
	BACKLIGHT = col * mix(0.05, 0.20, blade_t);

}

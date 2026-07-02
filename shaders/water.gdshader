shader_type spatial;
render_mode cull_disabled;

uniform sampler2D heightmap_tex : filter_nearest, repeat_disable;
uniform float hm_world_size = 5000.0;
uniform float hm_min_h      = 0.0;
uniform float hm_range      = 1.0;
uniform float hm_res        = 256.0;
uniform float water_y_offset = 0.03;
global uniform float rain_wetness;
global uniform float snow_cover;
global uniform vec3 sky_reflect_color;
global uniform float season_t;
global uniform vec2 wind_vec;

// Canopy coverage map for dappled shade on water under trees
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float canopy_world_size = 5000.0;

// Screen/depth for true shore depth + refraction (reads keep us in the
// transparent pass — reflections come from the planar viewport, not SSR)
uniform sampler2D depth_texture : hint_depth_texture, repeat_disable, filter_nearest;
uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;
uniform float refraction_strength = 0.025;

// Baked shore-distance field (convert_to_godot.py): A channel = distance INTO
// water, 0-30m → 0-1. LiDAR DEMs record the water surface as ground — the real
// depth buffer reads ~3cm under every pond — so murk/reflection depth comes
// from this synthetic shore-slope profile instead.
uniform sampler2D shore_distance : filter_linear, repeat_disable;
uniform float shore_world_size = 5000.0;
uniform float shore_depth_slope = 0.12;  // metres of depth per metre from shore
uniform float shore_depth_max = 2.6;     // typical CP pond depth cap

// Planar reflection (water_reflection.gd): mirrored-camera viewport.
// Sampled x-flipped because the mirror basis negates X to stay right-handed.
uniform sampler2D planar_reflection_tex : source_color, filter_linear, repeat_disable;
uniform float planar_reflection_on = 0.0;
// Keep small: tower reflections are thin — large offsets shred them to noise
uniform float planar_distortion = 0.06;
uniform float planar_debug = 0.0;   // 1 = paint raw reflection sample (--refl-debug)
// Mirror camera's view-projection AS OF ITS LAST RENDER (water_reflection.gd
// pushes it on every mirror render). Sampling by reprojecting world_pos through
// this matrix instead of raw SCREEN_UV keeps the reflection world-anchored when
// the mirror renders at a sparse interval: screen-UV sampling composited a
// frames-old mirror as if rendered from the CURRENT pose, so every sparse
// update snapped the reflection by the accumulated camera motion (the
// 2026-07-02 "reflections popping at normal walk" report). On a fresh frame the
// two samplings are identical by construction.
uniform mat4 planar_mirror_vp;

varying vec3 world_pos;
varying float v_shore_dist;

// Raindrop ripple rings — concentric circles from random impact points
float raindrop_ripple(vec2 p) {
	float t = TIME;
	float ripple = 0.0;
	for (int i = 0; i < 6; i++) {
		vec2 cell = floor(p * (1.5 + float(i) * 0.3)) + vec2(float(i) * 17.3, float(i) * 31.7);
		vec2 center = cell + vec2(fract(sin(dot(cell, vec2(127.1, 311.7))) * 43758.5453),
		                          fract(sin(dot(cell, vec2(269.5, 183.3))) * 43758.5453));
		float phase = fract(sin(dot(cell, vec2(113.5, 271.9))) * 43758.5453) * 3.0;
		float age = fract(t * 0.4 + phase);
		float dist = length(p * (1.5 + float(i) * 0.3) - center);
		float ring = sin((dist - age * 3.0) * 18.0) * exp(-dist * 2.5) * (1.0 - age);
		ripple += ring * 0.15;
	}
	return ripple;
}

#include "res://shaders/include/decode_terrain.gdshaderinc"
#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/seasonal.gdshaderinc"
// gnoise/ghash now provided by hash_noise.gdshaderinc

// Wave normal maps — FFT-synthesized directional ripple (tools/gen_water_normals.py)
uniform sampler2D water_normal_a : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D water_normal_b : hint_normal, filter_linear_mipmap, repeat_enable;

// World-space wave normal from two scrolling ripple maps at three scales.
// Wind biases drift direction and increases slope amplitude.
// Scales/speeds calmed 2026-07-02 (Chris walk: waves read too busy/fast for
// a sheltered pond) — ~1.6× longer wavelengths, ~0.6× drift speed.
vec3 wave_normal(vec2 wpos) {
	float t = TIME;
	float wind_str = length(wind_vec);
	vec2 wind_dir = wind_str > 0.01 ? normalize(wind_vec) : vec2(0.55, 0.83);
	// Fine capillary ripple, wind-drifted
	vec2 uv_a = wpos / 8.0  + wind_dir * t * (0.012 + wind_str * 0.007);
	// Same map counter-scrolled at another scale — breaks single-sheet drift
	vec2 uv_c = wpos / 13.5 - wind_dir * t * 0.008 + vec2(0.37, 0.61);
	// Broader wavelet rows, slower
	vec2 uv_b = wpos / 28.0 + wind_dir * t * (0.006 + wind_str * 0.005);
	vec2 slope = (texture(water_normal_a, uv_a).xy * 2.0 - 1.0) * 0.50
	           + (texture(water_normal_a, uv_c).xy * 2.0 - 1.0) * 0.35
	           + (texture(water_normal_b, uv_b).xy * 2.0 - 1.0) * 0.80;
	float amp = 0.35 + wind_str * 0.20;   // calm pond → windy chop
	return normalize(vec3(slope.x * amp, 1.0, slope.y * amp));
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	// Clamp water Y so it never pokes below the terrain surface
	float terrain_h = sample_terrain(w.xz) + water_y_offset;
	if (w.y < terrain_h) {
		vec3 snapped = (inverse(MODEL_MATRIX) * vec4(w.x, terrain_h, w.z, 1.0)).xyz;
		VERTEX.y = snapped.y;
		w.y = terrain_h;
	}
	world_pos = w;
	// Shore softening: fade water alpha where terrain is close to or above water level.
	// Sample terrain at this vertex and at 4 neighbors. Use the maximum terrain height
	// to detect shore proximity — if any nearby terrain rises to water level, we're
	// near the shore and should start fading.
	float bed_h = sample_terrain(w.xz);
	float step_d = 2.0;
	float t_n = sample_terrain(w.xz + vec2(0.0, -step_d));
	float t_s = sample_terrain(w.xz + vec2(0.0,  step_d));
	float t_e = sample_terrain(w.xz + vec2( step_d, 0.0));
	float t_w = sample_terrain(w.xz + vec2(-step_d, 0.0));
	float max_neighbor = max(max(t_n, t_s), max(t_e, t_w));
	// How far below the water surface is the terrain here?
	// depth > 0 = water is deep, depth ≈ 0 = shore edge
	float depth_here = w.y - bed_h;
	float depth_neighbor = w.y - max_neighbor;
	// Shore dist: blend of local depth and neighbor depth.
	// Use the shallower of the two — if ANY measurement says "shore", fade.
	v_shore_dist = min(depth_here, depth_neighbor);
}

void fragment() {
	vec2 uv      = world_pos.xz / 12.0;   // scale for the gnoise color/foam layers
	vec3 wave_nrm = wave_normal(world_pos.xz);
	// Distant water reads mirror-flat (slopes foreshorten away); also kills
	// ripple shimmer against the 1/3-res reflection texture.
	float cam_dist = length(world_pos - CAMERA_POSITION_WORLD);
	float slope_fade = mix(1.0, 0.25, smoothstep(25.0, 140.0, cam_dist));
	wave_nrm = normalize(vec3(wave_nrm.x * slope_fade, 1.0, wave_nrm.z * slope_fade));

	// Synthetic bathymetry: shore-slope profile from the baked distance field
	vec2 shore_uv = (world_pos.xz + shore_world_size * 0.5) / shore_world_size;
	float dist_in_m = texture(shore_distance, shore_uv).a * 30.0;
	float synth_depth = min(dist_in_m * shore_depth_slope, shore_depth_max);

	// Three noise layers at different scales for natural variation
	float t = TIME;
	float n_large = gnoise(uv * 0.4 + vec2(t * 0.06, t * 0.04));
	float n_med   = gnoise(uv * 1.2 + vec2(-t * 0.1, t * 0.08));
	float n_fine  = gnoise(uv * 3.5 + vec2(t * 0.15, -t * 0.12));
	float wave_h  = n_large * 0.4 + n_med * 0.35 + n_fine * 0.25;

	vec3 deep    = vec3(0.020, 0.038, 0.028);   // dark olive-green (Central Park lakes)
	vec3 shallow = vec3(0.050, 0.075, 0.045);   // slightly warmer shallow
	float extra_reflect = 0.0;
	float murk_m = 1.4;   // metres of water column to reach full opacity

	// Per-water-body character based on world position
	// Conservatory Water (Model Boat Pond): shallow formal reflecting pool
	float d_conserv = length(world_pos.xz - vec2(-152.0, 958.0));
	if (d_conserv < 80.0) {
		deep    = vec3(0.035, 0.050, 0.045);   // lighter, blue-gray
		shallow = vec3(0.065, 0.085, 0.075);
		extra_reflect = 0.15;
		murk_m  = 2.4;   // formal reflecting pool, clearer
	}
	// Turtle Pond: shallow, murky, dark green-brown
	float d_turtle = length(world_pos.xz - vec2(-213.0, 374.0));
	if (d_turtle < 120.0) {
		deep    = vec3(0.018, 0.030, 0.020);   // darker, murkier
		shallow = vec3(0.040, 0.055, 0.035);
		murk_m  = 0.9;
	}
	// Reservoir: large, open, more reflective blue
	float d_reserv = length(world_pos.xz - vec2(282.0, -424.0));
	if (d_reserv < 500.0) {
		deep    = vec3(0.015, 0.030, 0.035);   // blue-tinted deep
		shallow = vec3(0.040, 0.065, 0.070);
		extra_reflect = 0.10;
	}
	// Harlem Meer: large, dark green-blue, reflective
	float d_meer = length(world_pos.xz - vec2(1132.0, -1494.0));
	if (d_meer < 250.0) {
		deep    = vec3(0.015, 0.032, 0.032);
		shallow = vec3(0.040, 0.060, 0.058);
		extra_reflect = 0.08;
	}
	// The Pool (North Woods): secluded, dark, tree-shadowed
	float d_pool = length(world_pos.xz - vec2(394.0, -1311.0));
	if (d_pool < 100.0) {
		deep    = vec3(0.012, 0.025, 0.018);   // very dark, canopy-shadowed
		shallow = vec3(0.030, 0.048, 0.032);
	}
	// The Lake (main): classic Central Park, moderate reflectivity
	float d_lake = length(world_pos.xz - vec2(-522.0, 694.0));
	if (d_lake < 300.0) {
		deep    = vec3(0.018, 0.034, 0.028);   // natural dark green
		shallow = vec3(0.045, 0.065, 0.050);
		extra_reflect = 0.05;
	}
	// The Pond (59th St): formal, shallow, clear, near Columbus Circle
	float d_pond = length(world_pos.xz - vec2(-764.0, 1829.0));
	if (d_pond < 100.0) {
		deep    = vec3(0.025, 0.040, 0.035);   // clearer than most
		shallow = vec3(0.050, 0.070, 0.060);
		extra_reflect = 0.10;  // reflecting nearby skyscrapers
		murk_m  = 2.0;
	}
	// Azalea Pond (Ramble): small, secluded, tree-shadowed
	float d_azalea = length(world_pos.xz - vec2(-358.0, 645.0));
	if (d_azalea < 50.0) {
		deep    = vec3(0.012, 0.025, 0.018);   // very dark, canopy-filtered
		shallow = vec3(0.028, 0.042, 0.030);
	}

	// Seasonal water color shifts
	// Spring (0): clear, slightly green from algae bloom
	// Summer (1): base colors (tuned above)
	// Autumn (2): brown-amber tint from leaf tannins
	// Winter (3): lighter, grayer, less saturated
	float autumn_t = sn_veg_autumn(season_t);
	float winter_t = sn_atmo_winter(season_t);
	float spring_t = sn_atmo_spring(season_t);
	if (autumn_t > 0.01) {
		// Fallen leaves leach tannins: amber-brown tint
		deep    = mix(deep,    deep    * vec3(1.15, 0.95, 0.70), autumn_t * 0.4);
		shallow = mix(shallow, shallow * vec3(1.20, 0.95, 0.65), autumn_t * 0.4);
	}
	if (winter_t > 0.01) {
		// Cold water: desaturated, slightly lighter, gray shift
		float d_lum = dot(deep, vec3(0.33));
		float s_lum = dot(shallow, vec3(0.33));
		deep    = mix(deep,    vec3(d_lum) * 1.15, winter_t * 0.3);
		shallow = mix(shallow, vec3(s_lum) * 1.15, winter_t * 0.3);
	}
	if (spring_t > 0.01) {
		// Spring algae bloom: green boost, more visible in shallow warm areas
		deep    = mix(deep,    deep    * vec3(0.85, 1.18, 0.78), spring_t * 0.30);
		shallow = mix(shallow, shallow * vec3(0.82, 1.22, 0.75), spring_t * 0.35);
	}
	// Summer peak algae: July-August warmth drives chlorophyll
	float summer_t = smoothstep(0.5, 1.2, season_t) * smoothstep(2.0, 1.2, season_t);
	if (summer_t > 0.01) {
		// Warm stagnant water gets greener, especially shallow edges
		deep    = mix(deep,    deep    * vec3(0.88, 1.12, 0.82), summer_t * 0.20);
		shallow = mix(shallow, shallow * vec3(0.80, 1.25, 0.72), summer_t * 0.30);
	}

	// Depth tinting: deeper water is darker and more saturated
	float depth_t = smoothstep(0.0, 2.5, synth_depth);
	deep    = mix(shallow, deep, depth_t);

	// Subtle blend — mostly deep, shallow only at wave peaks
	vec3 base_col = mix(deep, shallow, smoothstep(-0.3, 0.6, wave_h));

	// Rain ripples — concentric ring disturbance when raining
	// Intensity scales with rain: gentle drizzle → heavy downpour
	if (rain_wetness > 0.01) {
		float ripple_scale = mix(0.3, 1.0, rain_wetness);  // gentle at low rain, full at heavy
		float rr = raindrop_ripple(world_pos.xz / 6.0) * ripple_scale;
		float e = 0.02;
		float rr_dx = raindrop_ripple((world_pos.xz + vec2(e, 0.0)) / 6.0) * ripple_scale;
		float rr_dz = raindrop_ripple((world_pos.xz + vec2(0.0, e)) / 6.0) * ripple_scale;
		vec3 ripple_n = normalize(vec3(
			-(rr_dx - rr) / e * 0.3,
			1.0,
			-(rr_dz - rr) / e * 0.3
		));
		wave_nrm = normalize(mix(wave_nrm, ripple_n, rain_wetness * 0.6));
	}

	NORMAL    = normalize((VIEW_MATRIX * vec4(wave_nrm, 0.0)).xyz);

	// Fresnel — glancing angles reflect sky (color tracks time of day)
	// Power 3.0 (not 4.0) for gentler ramp — water has visible reflection even at moderate angles
	// Minimum floor 0.04: real water reflects ~2-4% at normal incidence (Schlick)
	float fresnel = max(pow(1.0 - max(dot(NORMAL, VIEW), 0.0), 3.0), 0.04);
	vec3 sky_col = sky_reflect_color;

	// Night city reflection: when sky is very dark, water reflects city light pollution
	// NYC skyline reflecting in Central Park water is iconic
	float sky_lum = dot(sky_col, vec3(0.2126, 0.7152, 0.0722));
	float night_boost = smoothstep(0.15, 0.02, sky_lum);  // 1.0 at night
	if (night_boost > 0.01) {
		// Warm amber city glow reflected in water — brighter, more vivid
		vec3 city_reflect = vec3(0.16, 0.10, 0.05);
		// Directional: west side (CPW) is residential high-rises, warm yellow windows
		// East side (5th Ave) is commercial, cooler white-blue
		float west_bias = smoothstep(0.0, -600.0, world_pos.x);  // west edge of park
		float east_bias = smoothstep(0.0, 600.0, world_pos.x);    // east edge
		city_reflect += vec3(0.04, 0.03, 0.01) * west_bias;       // warmer west
		city_reflect += vec3(0.02, 0.02, 0.03) * east_bias;       // cooler east
		// Distance from park edges increases reflected light
		float edge_factor = abs(world_pos.x) / 1000.0;
		city_reflect *= (1.0 + clamp(edge_factor, 0.0, 1.0) * 0.6);
		sky_col += city_reflect * night_boost;
		// Window sparkle: bright warm points dancing on wave crests
		float sparkle = gnoise(world_pos.xz * 0.3 + vec2(TIME * 0.02, 0.0));
		sparkle = smoothstep(0.6, 0.9, sparkle) * night_boost * 0.10;
		sky_col += vec3(1.0, 0.72, 0.32) * sparkle;
		// Occasional cool-white sparkle (modern buildings)
		float sparkle2 = gnoise(world_pos.xz * 0.45 + vec2(-TIME * 0.015, TIME * 0.01));
		sparkle2 = smoothstep(0.7, 0.95, sparkle2) * night_boost * 0.05;
		sky_col += vec3(0.70, 0.80, 1.0) * sparkle2;
	}

	// Golden hour water: warm orange-gold reflection during sunset/sunrise
	// Detect golden hour from sky_reflect_color warmth (warm R > cool B)
	float sky_warmth = sky_reflect_color.r - sky_reflect_color.b;
	float golden_w = smoothstep(0.05, 0.20, sky_warmth) * smoothstep(0.02, 0.10, sky_lum);
	if (golden_w > 0.01) {
		// Subtle warm tint at glancing angles — not a bronze mirror
		vec3 golden_reflect = sky_reflect_color * vec3(1.05, 0.90, 0.75);
		float golden_path = fresnel * golden_w * 0.08;
		sky_col += golden_reflect * golden_path;
	}

	// --- True water depth from the depth buffer: soft shore + murk gradient ---
	// (reversed-z reconstruction, same as Terrain3D's reference ocean shader)
	float depth_raw = textureLod(depth_texture, SCREEN_UV, 0.0).r;
	vec4 bed_clip = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, depth_raw, 1.0);
	vec3 bed_view = bed_clip.xyz / bed_clip.w;
	vec3 bed_world = (INV_VIEW_MATRIX * vec4(bed_view, 1.0)).xyz;
	float pixel_depth = max(world_pos.y - bed_world.y, 0.0);  // vertical column, m

	// Refraction — offset the seen-through bed by the wave normal, but never
	// pull in pixels that sit above the water surface (ghosting guard).
	vec2 bed_uv = SCREEN_UV;
	vec2 refr_uv = SCREEN_UV + wave_nrm.xz * refraction_strength
	             * clamp(pixel_depth, 0.0, 1.0);
	float refr_raw = textureLod(depth_texture, refr_uv, 0.0).r;
	vec4 refr_clip = INV_PROJECTION_MATRIX * vec4(refr_uv * 2.0 - 1.0, refr_raw, 1.0);
	vec3 refr_view = refr_clip.xyz / refr_clip.w;
	vec3 refr_world = (INV_VIEW_MATRIX * vec4(refr_view, 1.0)).xyz;
	if (refr_world.y < world_pos.y + 0.05) {
		bed_uv = refr_uv;
		pixel_depth = max(world_pos.y - refr_world.y, 0.0);
	}
	vec3 bed_col = texture(screen_texture, bed_uv).rgb;

	// Effective depth: the deeper of measured (real banks/curbs) and synthetic
	// (flat DEM pond interiors, where the real bed reads 3cm down).
	float eff_depth = max(pixel_depth, synth_depth);

	// Transmitted light: seen-through bed fades into the body color with depth.
	// Slight green cast on the bed = suspended algae/particulates.
	float depth_fade = pow(clamp(eff_depth / murk_m, 0.0, 1.0), 0.55);
	vec3 transmitted = mix(bed_col * vec3(0.88, 1.0, 0.90), base_col, depth_fade);

	// Reflection fades out over the last ~2.5m to the shore edge
	float refl_gate = smoothstep(0.0, 0.3, eff_depth);

	// Planar reflection: real mirrored scene when available, flat sky color
	// as fallback. With a real image we can use a physical Schlick weight —
	// water IS a mirror at grazing angles (the iconic treeline/skyline look).
	vec3 refl_col = sky_col;
	float refl_w = fresnel * (0.35 + extra_reflect);
	vec4 refl_clip = planar_mirror_vp * vec4(world_pos, 1.0);
	if (planar_reflection_on > 0.5 && refl_clip.w > 0.001) {
		// World-anchored mirror sample (see planar_mirror_vp above). The mirror
		// basis negates X, so the x-flip vs SCREEN_UV falls out of the matrix.
		// The y flip does NOT: the GDScript-side Projection is GL-style (NDC
		// y-up) while the viewport texture is top-left v-down — unlike the
		// in-shader PROJECTION_MATRIX, which has the Vulkan flip baked in.
		vec2 ruv = vec2(refl_clip.x, -refl_clip.y) / refl_clip.w * 0.5 + 0.5
		         + wave_nrm.xz * planar_distortion * vec2(1.0, -1.0);
		ruv = clamp(ruv, vec2(0.001), vec2(0.999));
		refl_col = texture(planar_reflection_tex, ruv).rgb;
		float cos_v = max(dot(NORMAL, VIEW), 0.0);
		refl_w = 0.03 + 0.97 * pow(1.0 - cos_v, 5.0);   // Schlick, n≈1.33
	}
	vec3 col = mix(transmitted, refl_col, refl_w * refl_gate);

	// Caustics: light dappling in shallow clear water during daytime
	// Sunlight refracting through wave surface creates bright dancing patterns on bed
	float caustic = 0.0;
	float daytime = 1.0 - night_boost;
	if (daytime > 0.1 && eff_depth < 1.5) {
		float shallow_factor = 1.0 - smoothstep(0.0, 1.5, eff_depth);
		// Two overlapping caustic layers at different scales/speeds
		float c1 = gnoise(world_pos.xz * 1.8 + vec2(t * 0.12, t * 0.08));
		float c2 = gnoise(world_pos.xz * 2.5 + vec2(-t * 0.15, t * 0.11));
		caustic = (c1 + c2) * 0.5;
		caustic = smoothstep(0.1, 0.5, caustic) * shallow_factor * daytime * 0.12;
		// Rain disrupts caustics (turbid water)
		caustic *= (1.0 - rain_wetness * 0.7);
		col += vec3(caustic * 1.1, caustic, caustic * 0.8);
	}

	// Canopy shade on water — dappled sunlight through overhanging trees.
	// The light pattern dances on the water surface, one of Central Park's
	// most beautiful effects visible at The Lake, The Pool, Azalea Pond.
	{
		vec2 canopy_uv = (world_pos.xz + canopy_world_size * 0.5) / canopy_world_size;
		float canopy = texture(canopy_map, canopy_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = sn_canopy_loss(season_t);
			float winter_bare = sn_canopy_bare(season_t);
			float spring_fill = sn_canopy_fill(season_t);
			float sc = canopy * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare) * mix(0.5, 1.0, spring_fill);
			// Dappled light pattern — larger scale on water (light travels further)
			vec2 dapple_uv = world_pos.xz * 0.25 + wind_vec * TIME * 0.06;
			float dapple = gnoise(dapple_uv * 3.0) * 0.5 + 0.5;
			float dapple_fine = gnoise(world_pos.xz * 0.8 + wind_vec * TIME * 0.12) * 0.5 + 0.5;
			float light_gap = smoothstep(0.30, 0.65, dapple) * 0.55 + smoothstep(0.50, 0.75, dapple_fine) * 0.45;
			float sky_lum2 = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum2);
			float shade = sc * sun_factor;
			// Shade darkens water; light gaps create bright dancing patches
			col *= (1.0 - shade * (1.0 - light_gap) * 0.10);
			// Bright sun patches on water have a warm golden quality
			float warm_patch = light_gap * shade * 0.06;
			col += vec3(warm_patch * 1.2, warm_patch * 0.8, warm_patch * 0.3);
		}
	}

	// Foam — white caps at wave peaks (subtle in ponds, more on reservoir)
	// Wind increases foam: lower threshold, more visible caps
	float wind_str = length(wind_vec);
	// Ponds rarely whitecap — foam only at strong wind, and subtle
	float foam_thresh = mix(0.78, 0.50, clamp(wind_str, 0.0, 2.0) * 0.5);
	float foam = smoothstep(foam_thresh, foam_thresh + 0.25, wave_h);
	float foam_vis = night_boost > 0.5 ? 0.15 : 0.35;  // less visible foam at night
	foam_vis *= (1.0 + wind_str * 0.3);  // wind makes foam more prominent
	col = mix(col, vec3(0.85, 0.90, 0.92), foam * min(foam_vis, 1.0));

	ALBEDO    = col;
	ROUGHNESS = mix(0.12, 0.02, fresnel);
	// Ambient sky-radiance specular — fallback shimmer when the planar mirror
	// is off; mostly disabled when on, to avoid counting the sky twice.
	METALLIC  = 0.15 * (1.0 - planar_reflection_on * 0.7);
	SPECULAR  = 0.5 + night_boost * 0.2;

	// Winter ice — shallow edges freeze first, center stays open longer
	// Central Park water bodies partially freeze in deep winter
	if (winter_t > 0.3 && snow_cover > 0.1) {
		// Ice forms from shores inward: shallow areas freeze first
		float freeze = smoothstep(0.3, 0.8, winter_t) * smoothstep(0.1, 0.6, snow_cover);
		// Shallow edges freeze before deep center
		float depth_resist = smoothstep(0.0, 1.5, eff_depth);
		float ice_mask = freeze * (1.0 - depth_resist * 0.6);
		// Noise breaks up ice edge naturally
		float ice_noise = gnoise(world_pos.xz * 0.15) * 0.3;
		ice_mask = smoothstep(0.2, 0.6, ice_mask + ice_noise);
		if (ice_mask > 0.01) {
			// Ice color: pale blue-white with slight translucency
			vec3 ice_col = mix(vec3(0.72, 0.78, 0.84), vec3(0.82, 0.86, 0.90), gnoise(world_pos.xz * 0.4) * 0.5 + 0.5);
			// Snow dusting on top of ice
			if (snow_cover > 0.4) {
				float snow_noise = gnoise(world_pos.xz * 0.25 + vec2(17.3)) * 0.5 + 0.5;
				float snow_on_ice = smoothstep(0.3, 0.7, snow_noise) * smoothstep(0.4, 0.8, snow_cover);
				ice_col = mix(ice_col, vec3(0.90, 0.91, 0.94), snow_on_ice * 0.6);
			}
			ALBEDO = mix(ALBEDO, ice_col, ice_mask);
			ROUGHNESS = mix(ROUGHNESS, 0.35, ice_mask);  // ice is somewhat smooth
			SPECULAR = mix(SPECULAR, 0.25, ice_mask);
			// Flatten normal on ice (no waves)
			vec3 flat_n = normalize((VIEW_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
			NORMAL = mix(NORMAL, flat_n, ice_mask * 0.85);
		}
	}

	// Skirt cutoff — the grid mesh is terrain-clamped, so triangles ride up
	// onto the banks; hide those. The VISIBLE shore softening is now the
	// depth-buffer murk gradient above (transmitted → bed as depth → 0).
	ALPHA = smoothstep(-0.02, 0.10, v_shore_dist);

	// Diagnostic: paint the raw mirror sample so flip/aim errors are obvious
	// (reprojected path — same UV math as the live reflection above)
	if (planar_debug > 0.5) {
		ALBEDO = texture(planar_reflection_tex,
			clamp(vec2(refl_clip.x, -refl_clip.y) / max(refl_clip.w, 0.001) * 0.5 + 0.5,
				vec2(0.001), vec2(0.999))).rgb;
		ROUGHNESS = 1.0;
		METALLIC = 0.0;
		SPECULAR = 0.0;
		ALPHA = 1.0;
	}
}

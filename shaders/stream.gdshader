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

// Canopy coverage map for dappled shade on streams under trees
uniform sampler2D canopy_map : filter_linear, repeat_disable;
uniform float canopy_world_size = 5000.0;

varying vec3 world_pos;
varying float v_water_depth;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/decode_terrain.gdshaderinc"

// Gradient noise for wave patterns
vec2 ghash(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
	return fract(sin(p) * 43758.5453) * 2.0 - 1.0;
}
float gnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(dot(ghash(i),          f),
	               dot(ghash(i+vec2(1,0)), f-vec2(1,0)), u.x),
	           mix(dot(ghash(i+vec2(0,1)), f-vec2(0,1)),
	               dot(ghash(i+vec2(1,1)), f-vec2(1,1)), u.x), u.y);
}

// Raindrop ripple rings
float raindrop_ripple(vec2 p) {
	float t = TIME;
	float ripple = 0.0;
	for (int i = 0; i < 4; i++) {
		vec2 cell = floor(p * (1.5 + float(i) * 0.3)) + vec2(float(i) * 17.3, float(i) * 31.7);
		vec2 center = cell + vec2(fract(sin(dot(cell, vec2(127.1, 311.7))) * 43758.5453),
		                          fract(sin(dot(cell, vec2(269.5, 183.3))) * 43758.5453));
		float phase = fract(sin(dot(cell, vec2(113.5, 271.9))) * 43758.5453) * 3.0;
		float age = fract(t * 0.5 + phase);
		float dist = length(p * (1.5 + float(i) * 0.3) - center);
		float ring = sin((dist - age * 3.0) * 18.0) * exp(-dist * 2.5) * (1.0 - age);
		ripple += ring * 0.12;
	}
	return ripple;
}

void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float terrain_h = sample_terrain(w.xz) + water_y_offset;
	if (w.y < terrain_h) {
		vec3 snapped = (inverse(MODEL_MATRIX) * vec4(w.x, terrain_h, w.z, 1.0)).xyz;
		VERTEX.y = snapped.y;
		w.y = terrain_h;
	}
	world_pos = w;
	float bed_h = sample_terrain(w.xz);
	v_water_depth = max(0.0, w.y - bed_h);
}

void fragment() {
	// UV.x = cross-stream (0..1), UV.y = along-stream distance
	float t = TIME;

	// Flow speed: base speed + slope-driven acceleration
	// Terrain gradient gives local slope for turbulence
	float e_t = 2.0;
	float h_here = sample_terrain(world_pos.xz);
	float h_dx = sample_terrain(world_pos.xz + vec2(e_t, 0.0));
	float h_dz = sample_terrain(world_pos.xz + vec2(0.0, e_t));
	float slope = length(vec2(h_dx - h_here, h_dz - h_here)) / e_t;
	float turb = smoothstep(0.02, 0.15, slope);  // turbulence factor from slope

	// Directional flow — scroll along stream (UV.y is distance)
	float flow_speed = 0.8 + turb * 1.2;  // faster over steeper terrain
	float flow_uv = UV.y * 0.3 - t * flow_speed;

	// Wave normal from flowing noise layers
	vec2 flow_p = vec2(UV.x * 3.0, flow_uv);
	float wind_str = length(wind_vec);
	float amp = 0.25 + turb * 0.3 + wind_str * 0.08;

	// Three layers: fast flow + cross-stream ripples + fine detail
	float h1 = gnoise(flow_p * 1.2) * 0.45;
	float h2 = gnoise(flow_p * 2.5 + vec2(t * 0.15, -t * 0.08)) * 0.35;
	float h3 = gnoise(flow_p * 5.0 + vec2(-t * 0.2, t * 0.12)) * 0.20;
	float wave_h = h1 + h2 + h3;

	// Finite-difference normal from flowing waves
	float eps = 0.04;
	vec2 fp_dx = flow_p + vec2(eps, 0.0);
	vec2 fp_dz = flow_p + vec2(0.0, eps);
	float hx = gnoise(fp_dx * 1.2) * 0.45 + gnoise(fp_dx * 2.5 + vec2(t * 0.15, -t * 0.08)) * 0.35 + gnoise(fp_dx * 5.0 + vec2(-t * 0.2, t * 0.12)) * 0.20;
	float hz = gnoise(fp_dz * 1.2) * 0.45 + gnoise(fp_dz * 2.5 + vec2(t * 0.15, -t * 0.08)) * 0.35 + gnoise(fp_dz * 5.0 + vec2(-t * 0.2, t * 0.12)) * 0.20;
	vec3 wave_nrm = normalize(vec3(-(hx - wave_h) / eps * amp, 1.0, -(hz - wave_h) / eps * amp));

	// Rain ripples
	if (rain_wetness > 0.01) {
		float ripple_scale = mix(0.3, 1.0, rain_wetness);
		float rr = raindrop_ripple(world_pos.xz / 4.0) * ripple_scale;
		float rr_dx = raindrop_ripple((world_pos.xz + vec2(0.02, 0.0)) / 4.0) * ripple_scale;
		float rr_dz = raindrop_ripple((world_pos.xz + vec2(0.0, 0.02)) / 4.0) * ripple_scale;
		vec3 ripple_n = normalize(vec3(-(rr_dx - rr) / 0.02 * 0.3, 1.0, -(rr_dz - rr) / 0.02 * 0.3));
		wave_nrm = normalize(mix(wave_nrm, ripple_n, rain_wetness * 0.4));
	}

	NORMAL = normalize((VIEW_MATRIX * vec4(wave_nrm, 0.0)).xyz);

	// Stream water color — shallower, clearer than lakes
	vec3 deep    = vec3(0.025, 0.042, 0.032);   // dark green-brown creek water
	vec3 shallow = vec3(0.055, 0.078, 0.055);   // brighter shallow

	// Seasonal shifts
	float autumn_t = smoothstep(1.5, 2.5, season_t) * smoothstep(3.5, 2.5, season_t);
	float winter_t = smoothstep(2.5, 3.5, season_t);
	if (autumn_t > 0.01) {
		deep    = mix(deep,    deep    * vec3(1.15, 0.90, 0.65), autumn_t * 0.5);
		shallow = mix(shallow, shallow * vec3(1.20, 0.90, 0.60), autumn_t * 0.5);
	}
	if (winter_t > 0.01) {
		float d_lum = dot(deep, vec3(0.33));
		float s_lum = dot(shallow, vec3(0.33));
		deep    = mix(deep,    vec3(d_lum) * 1.15, winter_t * 0.3);
		shallow = mix(shallow, vec3(s_lum) * 1.15, winter_t * 0.3);
	}

	// Depth tinting
	float depth_t = smoothstep(0.0, 1.0, v_water_depth);
	vec3 base_col = mix(shallow, deep, depth_t);
	base_col = mix(base_col, shallow, smoothstep(-0.3, 0.6, wave_h) * 0.4);

	// Fresnel reflection
	float fresnel = pow(1.0 - max(dot(NORMAL, VIEW), 0.0), 4.0);
	vec3 sky_col = sky_reflect_color;
	float sky_lum = dot(sky_col, vec3(0.2126, 0.7152, 0.0722));
	float night_boost = smoothstep(0.15, 0.02, sky_lum);
	if (night_boost > 0.01) {
		sky_col += vec3(0.08, 0.05, 0.03) * night_boost;
	}
	vec3 col = mix(base_col, sky_col, fresnel * 0.5);

	// White water / foam over rocky terrain (high slope = turbulent)
	float foam = smoothstep(0.3, 0.7, turb) * (0.5 + wave_h * 0.5);
	// Cross-stream foam is thicker at center
	float center_x = 1.0 - abs(UV.x * 2.0 - 1.0);
	foam *= smoothstep(0.0, 0.3, center_x);
	foam *= (0.4 + gnoise(flow_p * 3.0) * 0.6);
	col = mix(col, vec3(0.78, 0.82, 0.85), clamp(foam, 0.0, 0.6));

	// Edge foam — subtle white froth along stream banks
	float edge_mask = smoothstep(0.15, 0.0, min(UV.x, 1.0 - UV.x));
	float edge_foam = edge_mask * (0.3 + gnoise(vec2(flow_uv * 4.0, UV.x * 8.0)) * 0.4);
	col = mix(col, vec3(0.80, 0.84, 0.86), clamp(edge_foam * 0.35, 0.0, 0.3));

	// Canopy shade on stream — most CP streams flow through wooded areas
	{
		vec2 canopy_uv = (world_pos.xz + canopy_world_size * 0.5) / canopy_world_size;
		float canopy = texture(canopy_map, canopy_uv).r;
		if (canopy > 0.01) {
			float deciduous_loss = smoothstep(2.5, 3.2, season_t);
			float winter_bare2 = smoothstep(3.0, 3.5, season_t);
			float spring_fill = smoothstep(0.0, 0.4, season_t);
			float sc = canopy * mix(1.0, 0.3, deciduous_loss) * mix(1.0, 0.15, winter_bare2) * mix(0.5, 1.0, spring_fill);
			float sky_lum2 = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
			float sun_factor = smoothstep(0.02, 0.20, sky_lum2);
			float dapple = gnoise(world_pos.xz * 0.3 + wind_vec * TIME * 0.06) * 0.5 + 0.5;
			float light_gap = smoothstep(0.30, 0.70, dapple);
			float shade = sc * sun_factor;
			col *= (1.0 - shade * (1.0 - light_gap) * 0.30);
			col += vec3(1.0, 0.8, 0.3) * light_gap * shade * 0.04;
		}
	}

	ALBEDO    = col;
	ROUGHNESS = mix(0.15, 0.05, fresnel);
	METALLIC  = 0.05;
	SPECULAR  = 0.45;

	// Winter partial freeze — streams freeze from edges inward
	if (winter_t > 0.4 && snow_cover > 0.15) {
		float freeze = smoothstep(0.4, 0.9, winter_t) * smoothstep(0.15, 0.7, snow_cover);
		// Edges freeze first
		float edge_dist = min(UV.x, 1.0 - UV.x);
		float ice_mask = freeze * smoothstep(0.35, 0.05, edge_dist);
		ice_mask += freeze * 0.2;  // thin ice can form everywhere in deep cold
		float ice_noise = gnoise(world_pos.xz * 0.2) * 0.3;
		ice_mask = smoothstep(0.15, 0.55, ice_mask + ice_noise);
		if (ice_mask > 0.01) {
			vec3 ice_col = mix(vec3(0.72, 0.78, 0.84), vec3(0.82, 0.86, 0.90),
			                   gnoise(world_pos.xz * 0.5) * 0.5 + 0.5);
			if (snow_cover > 0.5) {
				float sn = gnoise(world_pos.xz * 0.3 + vec2(17.3)) * 0.5 + 0.5;
				ice_col = mix(ice_col, vec3(0.90, 0.91, 0.94), smoothstep(0.3, 0.7, sn) * 0.5);
			}
			ALBEDO = mix(ALBEDO, ice_col, ice_mask);
			ROUGHNESS = mix(ROUGHNESS, 0.30, ice_mask);
			vec3 flat_n = normalize((VIEW_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
			NORMAL = mix(NORMAL, flat_n, ice_mask * 0.9);
		}
	}

	// Shore softening — fade alpha at edges
	float edge = min(UV.x, 1.0 - UV.x);
	ALPHA = smoothstep(0.0, 0.08, edge);
}

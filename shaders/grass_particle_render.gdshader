// Central Park grass render shader — GPU particle grass blades
// Adapted from Terrain3D particle example with seasonal color, zone-aware tinting,
// canopy shade response, and EGTTR-inspired muted naturalism.

shader_type spatial;
render_mode skip_vertex_transform, cull_disabled, blend_mix;

global uniform float season_t;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float rain_wetness;

varying vec4 data;
varying vec3 v_world_pos;

void vertex() {
	// Wind from model data — vertex Y drives bend amount
	data[2] = (VERTEX.y + 0.55);
	data[2] *= data[2];  // non-linear

	// Pinch top of ribbon mesh for grass blade shape
	VERTEX.xz *= (1.0 - data[2]);

	// Save random seed data from particle shader
	data.rg = INSTANCE_CUSTOM.rg;

	// World space vertex
	vec3 w_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_pos = w_vertex;

	// Wind bending — use global wind_vec instead of hardcoded direction
	float grass_scale = pow(INSTANCE_CUSTOM[3] * INSTANCE_CUSTOM[3], 0.707);
	float force = INSTANCE_CUSTOM[2] * data[2] * grass_scale;
	force -= fract(force * 256.0) * force * 0.05;
	force = pow(force, 0.707);

	vec2 direction = normalize(wind_vec + vec2(0.001));
	float lateral_wobble = sin(TIME * 2.0 * (1.0 + data.r + data.g)) * 0.25 * (1.0 - INSTANCE_CUSTOM[2]);
	w_vertex.xz -= (vec2(-direction.y, direction.x) * lateral_wobble + direction) * force;
	w_vertex.y -= INSTANCE_CUSTOM[2] * force * data[2];

	data[3] = force;

	VERTEX = (VIEW_MATRIX * vec4(w_vertex, 1.0)).xyz;
	NORMAL = MODELVIEW_NORMAL_MATRIX * NORMAL;
	BINORMAL = MODELVIEW_NORMAL_MATRIX * BINORMAL;
	TANGENT = MODELVIEW_NORMAL_MATRIX * TANGENT;
}

void fragment() {
	// Decode zone data from COLOR (set by particle process shader)
	float canopy_cover = COLOR.g;
	bool is_woodland = COLOR.b > 0.5;
	float season = COLOR.a * 4.0;

	// --- Seasonal grass color ---
	// Two-tone patchiness from world position noise
	float patch = fract(sin(dot(floor(v_world_pos.xz * 0.3), vec2(12.9898, 78.233))) * 43758.5453);
	vec3 color_fresh = vec3(0.08, 0.22, 0.04);   // deep fresh green
	vec3 color_dry   = vec3(0.22, 0.30, 0.08);    // older yellow-green
	vec3 base_col = mix(color_fresh, color_dry, patch);

	// Tip brightening
	base_col = mix(base_col, base_col * 1.4, smoothstep(0.7, 1.0, data[2]));
	// Base darkening (self-shadow)
	float grow_in = INSTANCE_CUSTOM[3];
	base_col *= grow_in < 0.35 ? 1.0 : mix(1.0, 0.70, smoothstep(0.35, 0.0, data[2]));

	// Per-blade color variation
	base_col.rg *= (data.rg * 0.25 + 0.88);

	// Seasonal modulation
	float spring_t = 1.0 - smoothstep(0.0, 1.0, season);
	float autumn_t = smoothstep(2.0, 2.6, season) * (1.0 - smoothstep(2.8, 3.5, season));
	float winter_t = smoothstep(2.7, 3.2, season);

	base_col = mix(base_col, base_col * vec3(1.15, 1.2, 0.8), spring_t * 0.5);
	base_col = mix(base_col, vec3(0.20, 0.15, 0.06), autumn_t * 0.65);
	base_col = mix(base_col, vec3(0.14, 0.12, 0.08), winter_t * 0.8);

	// Woodland: darker, cooler forest floor grass
	if (is_woodland) {
		base_col *= vec3(0.75, 0.80, 0.70);
	}

	// Canopy shade
	if (canopy_cover > 0.1) {
		base_col *= mix(1.0, 0.65, smoothstep(0.1, 0.6, canopy_cover));
	}

	// Snow on blade tips
	if (snow_cover > 0.01) {
		float snow_on_blade = smoothstep(0.2, 0.6, data[2]) * snow_cover;
		base_col = mix(base_col, vec3(0.90, 0.91, 0.94), snow_on_blade * 0.7);
	}

	ALBEDO = base_col;

	// PBR — rougher than the Terrain3D example for naturalistic grass
	float spec_rough = clamp(max(data[2], data[3]), 0.0, 1.0);
	ROUGHNESS = mix(0.75, 0.40, spec_rough);
	SPECULAR = clamp(spec_rough * 0.12, 0.0, 0.10);
	BACKLIGHT = vec3(0.25);  // leaf translucency

	// Rain: darken + lower roughness
	ALBEDO *= mix(1.0, 0.70, rain_wetness);
	ROUGHNESS = mix(ROUGHNESS, max(ROUGHNESS * 0.3, 0.08), rain_wetness);
}

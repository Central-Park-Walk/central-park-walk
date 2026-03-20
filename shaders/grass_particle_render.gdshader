// Central Park grass render shader — GPU particle grass tufts
// Renders BD3D-decimated grass tuft meshes with alpha scissor,
// seasonal color modulation, zone-aware tinting, canopy shade,
// and wind animation driven by particle INSTANCE_CUSTOM data.

shader_type spatial;
render_mode skip_vertex_transform, cull_disabled;

uniform sampler2D grass_albedo : source_color, filter_linear_mipmap;
// When true, sample grass_albedo for color+alpha. When false, use procedural color (legacy ribbon).
uniform bool use_texture = true;

global uniform float season_t;
global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float rain_wetness;

varying vec4 data;
varying vec3 v_world_pos;
varying float v_height_t;

void vertex() {
	// UV.y = normalized height within tuft (0=ground, 1=tip) for textured meshes.
	// For legacy ribbon mesh, fall back to vertex Y position.
	v_height_t = use_texture ? UV.y : clamp((VERTEX.y + 0.55) * 0.91, 0.0, 1.0);
	float bend_factor = v_height_t * v_height_t;

	// Legacy ribbon: pinch top for blade shape
	if (!use_texture) {
		VERTEX.xz *= (1.0 - bend_factor);
	}

	// Save random seed data from particle shader
	data.rg = INSTANCE_CUSTOM.rg;
	data[3] = INSTANCE_CUSTOM[3]; // scale

	// World space vertex
	vec3 w_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_world_pos = w_vertex;

	// Wind bending
	float grass_scale = pow(INSTANCE_CUSTOM[3] * INSTANCE_CUSTOM[3], 0.707);
	float force = INSTANCE_CUSTOM[2] * bend_factor * grass_scale;
	force -= fract(force * 256.0) * force * 0.05;
	force = pow(max(force, 0.0), 0.707);

	vec2 direction = normalize(wind_vec + vec2(0.001));
	float lateral_wobble = sin(TIME * 2.0 * (1.0 + data.r + data.g)) * 0.25 * (1.0 - INSTANCE_CUSTOM[2]);
	w_vertex.xz -= (vec2(-direction.y, direction.x) * lateral_wobble + direction) * force;
	w_vertex.y -= INSTANCE_CUSTOM[2] * force * bend_factor;

	data[2] = force;

	VERTEX = (VIEW_MATRIX * vec4(w_vertex, 1.0)).xyz;
	NORMAL = MODELVIEW_NORMAL_MATRIX * NORMAL;
	BINORMAL = MODELVIEW_NORMAL_MATRIX * BINORMAL;
	TANGENT = MODELVIEW_NORMAL_MATRIX * TANGENT;
}

void fragment() {
	// Texture-based color + alpha
	vec3 base_col;
	if (use_texture) {
		vec4 tex = texture(grass_albedo, UV);
		ALPHA = tex.a;
		ALPHA_SCISSOR_THRESHOLD = 0.4;
		base_col = tex.rgb;
	} else {
		// Legacy procedural color for ribbon mesh
		float patch = fract(sin(dot(floor(v_world_pos.xz * 0.3), vec2(12.9898, 78.233))) * 43758.5453);
		base_col = mix(vec3(0.08, 0.22, 0.04), vec3(0.22, 0.30, 0.08), patch);
	}

	// Decode zone data from COLOR (set by particle process shader)
	float canopy_cover = COLOR.g;
	bool is_woodland = COLOR.b > 0.5;
	float season = COLOR.a * 4.0;

	// Two-tone patchiness from world position
	float patch_noise = fract(sin(dot(floor(v_world_pos.xz * 0.3), vec2(12.9898, 78.233))) * 43758.5453);
	base_col = mix(base_col, base_col * 0.82, patch_noise * 0.3);

	// Tip brightening (subtle) + base darkening
	base_col = mix(base_col, base_col * 1.1, smoothstep(0.7, 1.0, v_height_t));
	base_col *= mix(0.60, 0.90, smoothstep(0.0, 0.35, v_height_t));

	// Per-instance color variation
	base_col.rg *= (data.rg * 0.2 + 0.90);

	// Seasonal modulation
	float spring_t = 1.0 - smoothstep(0.0, 1.0, season);
	float autumn_t = smoothstep(2.0, 2.6, season) * (1.0 - smoothstep(2.8, 3.5, season));
	float winter_t = smoothstep(2.7, 3.2, season);

	base_col = mix(base_col, base_col * vec3(1.15, 1.2, 0.8), spring_t * 0.5);
	base_col = mix(base_col, vec3(0.20, 0.15, 0.06), autumn_t * 0.65);
	base_col = mix(base_col, vec3(0.14, 0.12, 0.08), winter_t * 0.8);

	// Woodland: darker, cooler
	if (is_woodland) {
		base_col *= vec3(0.75, 0.80, 0.70);
	}

	// Canopy shade
	if (canopy_cover > 0.1) {
		base_col *= mix(1.0, 0.65, smoothstep(0.1, 0.6, canopy_cover));
	}

	// Snow — match terrain coverage (full blend, not just tips)
	if (snow_cover > 0.01) {
		base_col = mix(base_col, vec3(0.92, 0.93, 0.96), snow_cover * 0.85);
	}

	ALBEDO = base_col;

	// PBR — muted specular to reduce sparkle
	float spec_rough = clamp(max(v_height_t, data[2]), 0.0, 1.0);
	ROUGHNESS = mix(0.85, 0.55, spec_rough);
	SPECULAR = clamp(spec_rough * 0.06, 0.0, 0.05);
	BACKLIGHT = vec3(0.15);

	// Rain
	ALBEDO *= mix(1.0, 0.70, rain_wetness);
	ROUGHNESS = mix(ROUGHNESS, max(ROUGHNESS * 0.3, 0.08), rain_wetness);
}

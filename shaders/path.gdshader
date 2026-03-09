shader_type spatial;
render_mode cull_disabled;

uniform sampler2D tex_alb : source_color,      filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_nrm : hint_normal,        filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_rgh : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D heightmap_tex : filter_nearest, repeat_disable;
uniform vec4 tint : source_color = vec4(1.0);
uniform float hm_world_size = 5000.0;
uniform float hm_min_h      = 0.0;
uniform float hm_range      = 1.0;
uniform float hm_res        = 256.0;
uniform float path_y_offset = 0.08;
global uniform float rain_wetness;
global uniform float snow_cover;

#include "res://shaders/include/decode_terrain.gdshaderinc"

varying flat float depth_jitter;

float pos_hash(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 43.21);
	return fract(p.x * p.y);
}

void vertex() {
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float terrain_h = sample_terrain(world.xz);
	vec3 snapped = (inverse(MODEL_MATRIX) * vec4(world.x, terrain_h + path_y_offset, world.z, 1.0)).xyz;
	VERTEX.y = snapped.y;
	// Per-triangle depth jitter to break z-fighting at same-type intersections
	depth_jitter = pos_hash(floor(world.xz * 0.5)) * 0.0003;
}

void fragment() {
	vec3  alb   = texture(tex_alb, UV).rgb;
	float rough = texture(tex_rgh, UV).r;
	ALBEDO     = alb * tint.rgb * COLOR.rgb;
	NORMAL_MAP = texture(tex_nrm, UV).rgb;
	ROUGHNESS  = clamp(rough + 0.10, 0.0, 1.0);
	METALLIC   = 0.0;
	SPECULAR   = 0.06;  // matte paving default

	// Rain: wet pavement darkens, gets glossy
	if (rain_wetness > 0.01) {
		ALBEDO   *= mix(1.0, 0.60, rain_wetness);   // 40% darker when wet
		ROUGHNESS = mix(ROUGHNESS, 0.08, rain_wetness);
		SPECULAR  = mix(SPECULAR, 0.45, rain_wetness);
	}

	// Snow accumulation on paths
	if (snow_cover > 0.01) {
		// Upward-facing surfaces collect snow (paths are mostly flat)
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		float snow_amt = snow_cover * smoothstep(0.3, 0.8, upward);
		ALBEDO    = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_amt * 0.85);
		ROUGHNESS = mix(ROUGHNESS, 0.70, snow_amt);
		SPECULAR  = mix(SPECULAR, 0.15, snow_amt);
	}

	DEPTH = FRAGCOORD.z - depth_jitter;
}

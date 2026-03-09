shader_type spatial;
render_mode cull_disabled;

// Weathered wood — rain darkening, snow accumulation
uniform vec3 wood_color = vec3(0.38, 0.32, 0.25);
uniform float base_roughness = 0.88;
global uniform float rain_wetness;
global uniform float snow_cover;
global uniform float season_t;

#include "res://shaders/include/hash_noise.gdshaderinc"

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// Per-plank variation from world position
	float var_h = hash2(floor(world_pos.xz * 2.0 + world_pos.yy * 1.5));

	// Grain pattern: elongated noise along Y axis
	float grain = vnoise(vec2(world_pos.x * 6.0 + world_pos.z * 6.0, world_pos.y * 1.5));
	float fine_grain = vnoise(vec2(world_pos.x * 18.0 + world_pos.z * 18.0, world_pos.y * 4.0));

	vec3 col = wood_color * (0.85 + var_h * 0.30);
	col *= (0.88 + grain * 0.18 + fine_grain * 0.06);

	ALBEDO = col;
	ROUGHNESS = base_roughness;
	METALLIC = 0.0;

	// Rain: wet wood darkens significantly, becomes slightly reflective
	if (rain_wetness > 0.01) {
		float wet = rain_wetness;
		ALBEDO *= mix(1.0, 0.55, wet);
		ROUGHNESS = mix(ROUGHNESS, 0.40, wet);
		SPECULAR = mix(0.0, 0.25, wet);
	}

	// Snow on upward-facing surfaces
	if (snow_cover > 0.01) {
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		if (upward > 0.4) {
			float sn = hash2(floor(world_pos.xz * 4.0)) * 0.2;
			float snow_amt = clamp((upward + sn - 0.2) * snow_cover, 0.0, 1.0);
			ALBEDO = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_amt * 0.7);
			ROUGHNESS = mix(ROUGHNESS, 0.90, snow_amt);
		}
	}

	// Subtle emission for shadow-side visibility
	EMISSION = ALBEDO * 0.12;
}

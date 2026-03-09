shader_type spatial;
render_mode cull_disabled;

// Generic ground surface — sports fields, playgrounds, etc.
// Weather-responsive: rain darkening, snow cover, puddle pooling
uniform vec3 surface_color = vec3(0.5, 0.4, 0.3);
uniform float base_roughness = 0.90;
uniform float surface_specular = 0.10;
global uniform float rain_wetness;
global uniform float snow_cover;
global uniform float season_t;
global uniform vec3 sky_reflect_color;

#include "res://shaders/include/hash_noise.gdshaderinc"

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// Per-patch variation
	float var_h = hash2(floor(world_pos.xz * 0.5));
	vec3 col = surface_color * (0.90 + var_h * 0.20);

	// Subtle surface texture noise
	float tex_noise = vnoise(world_pos.xz * 4.0);
	col *= (0.94 + tex_noise * 0.12);

	ALBEDO = col;
	ROUGHNESS = base_roughness;
	METALLIC = 0.0;
	SPECULAR = surface_specular;

	// Rain: darkens surface, increases specularity
	if (rain_wetness > 0.01) {
		float wet = rain_wetness;
		ALBEDO *= mix(1.0, 0.60, wet);
		ROUGHNESS = mix(ROUGHNESS, max(ROUGHNESS * 0.3, 0.08), wet);
		SPECULAR = mix(SPECULAR, 0.45, wet);

		// Puddle formation on flat surfaces
		if (wet > 0.4) {
			float puddle_noise = vnoise(world_pos.xz * 0.1);
			puddle_noise += vnoise(world_pos.xz * 0.3) * 0.4;
			float puddle = smoothstep(0.4, 0.6, puddle_noise) * smoothstep(0.4, 0.8, wet);
			if (puddle > 0.01) {
				float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
				float night_t = smoothstep(0.15, 0.02, sky_lum);
				vec3 puddle_col = sky_reflect_color * 0.35 + ALBEDO * 0.12;
				puddle_col = mix(puddle_col, vec3(0.08, 0.06, 0.03) + ALBEDO * 0.06, night_t);
				ALBEDO = mix(ALBEDO, puddle_col, puddle);
				ROUGHNESS = mix(ROUGHNESS, 0.02, puddle);
				SPECULAR = mix(SPECULAR, 0.65, puddle);
			}
		}
	}

	// Snow accumulation
	if (snow_cover > 0.01) {
		float sn = hash2(floor(world_pos.xz * 2.0)) * 0.2;
		float snow_amt = clamp(snow_cover * (0.7 + sn), 0.0, 1.0);
		ALBEDO = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_amt * 0.75);
		ROUGHNESS = mix(ROUGHNESS, 0.88, snow_amt);
	}

	// Subtle emission for visibility
	EMISSION = ALBEDO * 0.10;
}

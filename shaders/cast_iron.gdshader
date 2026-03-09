shader_type spatial;

// Cast iron material for lampposts, fences, trash cans
// Central Park iron: painted dark green-black, weathers to show rust patina
uniform vec3 iron_color = vec3(0.08, 0.08, 0.06);
uniform float base_roughness = 0.78;
uniform float base_metallic = 0.45;

global uniform float rain_wetness;
global uniform float snow_cover;
global uniform float season_t;

varying vec3 world_pos;
varying vec3 world_nrm;

#include "res://shaders/include/hash_noise.gdshaderinc"

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 col = iron_color;
	float rough = base_roughness;
	float metal = base_metallic;
	float spec = 0.20;

	// Per-object variation: slight tint shift from repaint cycles
	float obj_hash = hash2(floor(world_pos.xz * 0.03));
	col *= (0.92 + obj_hash * 0.16);

	// Micro-texture: brushed/cast surface imperfections
	float surface = vnoise(world_pos * 15.0);
	col *= (0.95 + surface * 0.10);
	rough += surface * 0.05;

	// Paint chips and rust patina — accumulates at joints and bottom edges
	float rust_seed = hash2(floor(world_pos.xz * 2.5 + world_pos.yy * 1.5));
	float height_factor = smoothstep(1.5, 0.0, world_pos.y - floor(world_pos.y));
	float rust_mask = step(0.75, rust_seed) * (0.3 + height_factor * 0.7);
	// Rust shows more on exposed (upward-facing) and joint areas
	rust_mask *= (0.5 + max(world_nrm.y, 0.0) * 0.5);
	if (rust_mask > 0.01) {
		vec3 rust_col = mix(vec3(0.35, 0.18, 0.08), vec3(0.28, 0.12, 0.05), rust_seed);
		col = mix(col, rust_col, rust_mask * 0.25);
		rough = mix(rough, 0.92, rust_mask * 0.3);
		metal = mix(metal, 0.20, rust_mask * 0.2);
	}

	ALBEDO = col;
	ROUGHNESS = rough;
	METALLIC = metal;
	SPECULAR = spec;

	// Rain: wet iron darkens, becomes highly reflective
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.70, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.06, rain_wetness);
		SPECULAR = mix(SPECULAR, 0.55, rain_wetness);
		METALLIC = mix(METALLIC, 0.65, rain_wetness);
	}

	// Snow on upward-facing surfaces
	if (snow_cover > 0.01 && world_nrm.y > 0.3) {
		float snow_noise = hash2(floor(world_pos.xz * 4.0 + world_pos.yy * 3.0));
		float snow_amt = snow_cover * smoothstep(0.3, 0.7, world_nrm.y + snow_noise * 0.2);
		ALBEDO = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_amt * 0.6);
		ROUGHNESS = mix(ROUGHNESS, 0.85, snow_amt);
		METALLIC = mix(METALLIC, 0.0, snow_amt);
	}
}

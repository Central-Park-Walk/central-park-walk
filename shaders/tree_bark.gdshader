shader_type spatial;

uniform vec3 bark_color = vec3(0.48, 0.38, 0.28);
global uniform float rain_wetness;
global uniform float snow_cover;
global uniform float season_t;

varying vec3 world_pos;
varying vec3 world_nrm;

#include "res://shaders/include/hash_noise.gdshaderinc"

// Variable-octave FBM for bark texture detail
float fbm(vec2 p, int oct) {
	float v = 0.0, a = 0.5;
	for (int i = 0; i < oct; i++) { v += a*vnoise(p); p *= 2.17; a *= 0.49; }
	return v;
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_nrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	// Per-tree variation seed from model origin
	vec3 tree_base = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float tree_var = hash2(floor(tree_base.xz * 0.5));
	vec3 col = bark_color * (0.90 + tree_var * 0.20);

	// --- Bark furrow texture: deep vertical grooves ---
	// UV approximation: vertical = world_pos.y, horizontal = angular position
	float local_h = world_pos.y - tree_base.y;
	float bark_y = local_h * 4.0;  // vertical scale for furrow frequency
	// Horizontal position around trunk (hash of xz gives pseudo-angular coord)
	float bark_u = world_pos.x * 3.5 + world_pos.z * 2.8;

	// Primary furrows: vertical grooves with slight waviness
	float furrow_wave = sin(bark_u * 6.0 + vnoise(vec2(bark_u * 0.8, bark_y * 0.3)) * 2.5);
	float furrow = smoothstep(0.15, 0.55, furrow_wave);
	// Ridge/groove color modulation: grooves darker, ridges lighter
	col *= mix(0.78, 1.08, furrow);

	// Secondary micro-texture: fine bark surface detail
	float micro = fbm(vec2(bark_u * 12.0, bark_y * 8.0), 3);
	col *= (0.92 + micro * 0.16);

	// Bark roughness varies: grooves smoother (compressed), ridges rougher
	float rough = mix(0.82, 0.95, furrow);
	rough += micro * 0.05;

	// --- Height-based bark variation ---
	// Lower trunk: more weathered, darker, thicker bark plates
	float height_factor = smoothstep(0.0, 6.0, local_h);
	col *= mix(0.88, 1.0, height_factor);  // darker at base
	rough = mix(rough + 0.03, rough, height_factor);  // rougher at base

	// Upper trunk/branches: smoother, lighter bark
	float upper = smoothstep(4.0, 10.0, local_h);
	col = mix(col, col * 1.12, upper * 0.3);  // lighter higher up

	ALBEDO = col;
	ROUGHNESS = clamp(rough, 0.0, 1.0);
	METALLIC = 0.0;
	SPECULAR = 0.04;

	// --- Lichen patches: gray-green crusty patches common on NYC park trees ---
	float lichen_season = smoothstep(0.0, 0.8, season_t) * (1.0 - smoothstep(3.0, 3.8, season_t));
	if (lichen_season > 0.01) {
		float lich_noise = fbm(vec2(bark_u * 2.0, bark_y * 1.5) + tree_var * 10.0, 2);
		float lich_mask = smoothstep(0.55, 0.72, lich_noise) * lichen_season;
		// Only on bark ridges (not in deep furrows) and mid-height
		lich_mask *= furrow * smoothstep(1.0, 3.0, local_h) * smoothstep(8.0, 5.0, local_h);
		if (lich_mask > 0.01) {
			// Gray-green crustose lichen
			vec3 lichen_col = mix(vec3(0.35, 0.42, 0.30), vec3(0.45, 0.48, 0.38), lich_noise);
			ALBEDO = mix(ALBEDO, lichen_col, lich_mask * 0.45);
			ROUGHNESS = mix(ROUGHNESS, 0.92, lich_mask * 0.3);
		}
	}

	// --- Moss at trunk base: more in spring/summer, north-facing ---
	float spring_summer = smoothstep(0.0, 1.0, season_t) * (1.0 - smoothstep(2.5, 3.5, season_t));
	float moss_height = smoothstep(3.0, 0.0, local_h);  // bottom 3m of trunk
	float moss_facing = max(0.0, -world_nrm.z) * 0.5 + max(0.0, -world_nrm.x) * 0.3 + 0.2;
	float moss_noise = fbm(vec2(bark_u * 3.0, bark_y * 2.0), 2);
	float moss = moss_height * moss_facing * smoothstep(0.35, 0.6, moss_noise) * spring_summer;
	if (moss > 0.01) {
		vec3 moss_col = mix(vec3(0.10, 0.20, 0.06), vec3(0.16, 0.26, 0.08), moss_noise);
		ALBEDO = mix(ALBEDO, moss_col, moss * 0.45);
		ROUGHNESS = mix(ROUGHNESS, 0.95, moss * 0.3);
	}

	// --- Rain: wet bark darkens, gets glossy ---
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.62, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.35, rain_wetness);
		SPECULAR = mix(SPECULAR, 0.28, rain_wetness);
		// Water streaks in furrows — darker wet lines running down bark
		float wet_streak = smoothstep(0.45, 0.20, furrow) * rain_wetness;
		ALBEDO *= mix(1.0, 0.82, wet_streak * 0.6);
		ROUGHNESS = mix(ROUGHNESS, 0.12, wet_streak * 0.4);
		// Wet moss becomes vivid green
		if (moss > 0.01) {
			ALBEDO = mix(ALBEDO, ALBEDO * vec3(0.82, 1.25, 0.78), moss * rain_wetness * 0.4);
		}
	}

	// --- Snow on upward-facing bark and branch crotches ---
	if (snow_cover > 0.01) {
		float upward = max(world_nrm.y, 0.0);
		float snow_noise = hash2(floor(world_pos.xz * 5.0 + world_pos.yy * 3.0));
		float snow_amt = snow_cover * smoothstep(0.3, 0.7, upward + snow_noise * 0.3);
		// Snow collects more in bark furrows (concavities)
		snow_amt += snow_cover * (1.0 - furrow) * upward * 0.15;
		snow_amt = min(snow_amt, 1.0);
		ALBEDO = mix(ALBEDO, vec3(0.90, 0.91, 0.94), snow_amt * 0.7);
		ROUGHNESS = mix(ROUGHNESS, 0.85, snow_amt);
	}
}

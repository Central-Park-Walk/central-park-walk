// Aerial perspective: desaturate + optional cool shift + haze blend at distance.
// Shared by tree, stone, cast_iron, wood, hedge, facade, terrain shaders.
//
// aerial_t: smoothstep result (0 = near, 1 = far)
// desat:    desaturation strength at full distance (0.25-0.30 typical)
// haze_str: haze blend strength at full distance (0.25-0.30 typical)
// cool:     apply blue cool shift (true for vegetation, false for metals/stone)

float sky_luminance(vec3 sky_col) {
	return dot(sky_col, vec3(0.2126, 0.7152, 0.0722));
}

vec3 aerial_haze(vec3 sky_col) {
	float sky_l = sky_luminance(sky_col);
	vec3 haze = mix(vec3(0.58, 0.56, 0.52), sky_col * 0.8 + vec3(0.20), 0.35);
	float night_f = smoothstep(0.15, 0.02, sky_l);
	haze = mix(haze, vec3(0.14, 0.10, 0.06), night_f * 0.6);
	return haze;
}

vec3 apply_aerial(vec3 albedo, float aerial_t, float desat, float haze_str, vec3 sky_col) {
	if (aerial_t < 0.01) return albedo;
	// Desaturate toward luminance
	float lum = dot(albedo, vec3(0.2126, 0.7152, 0.0722));
	albedo = mix(albedo, vec3(lum), aerial_t * desat);
	// Cool shift (distant objects appear bluer)
	albedo = mix(albedo, albedo * vec3(0.94, 0.96, 1.04), aerial_t);
	// Haze blend
	albedo = mix(albedo, aerial_haze(sky_col), aerial_t * haze_str);
	return albedo;
}

// Variant without cool shift (for metals, dark surfaces)
vec3 apply_aerial_no_cool(vec3 albedo, float aerial_t, float desat, float haze_str, vec3 sky_col) {
	if (aerial_t < 0.01) return albedo;
	float lum = dot(albedo, vec3(0.2126, 0.7152, 0.0722));
	albedo = mix(albedo, vec3(lum), aerial_t * desat);
	albedo = mix(albedo, aerial_haze(sky_col), aerial_t * haze_str);
	return albedo;
}

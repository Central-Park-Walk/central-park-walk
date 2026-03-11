shader_type fog;

// Localized water body mist — visible at dawn, dusk, and cool mornings.
// Central Park's ponds and lake produce ethereal low-lying mist.
global uniform vec3 sky_reflect_color;
global uniform float season_t;
global uniform float rain_wetness;

void fog() {
	// Time detection from sky luminance — mist appears at low light (dawn/dusk)
	float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
	// Dawn/dusk: mist strongest when sky is dim but not full dark
	float mist_time = smoothstep(0.02, 0.10, sky_lum) * smoothstep(0.30, 0.15, sky_lum);

	// Season: more mist in cool months (autumn, winter, spring), less in summer heat
	float cool_season = 1.0 - smoothstep(0.5, 1.2, season_t) * (1.0 - smoothstep(1.8, 2.5, season_t));
	cool_season = 0.6 + cool_season * 0.4;  // 0.6 minimum even in summer

	// Rain increases mist (evaporation from warm water surface)
	float rain_mist = rain_wetness * 0.3;

	// Vertical falloff: mist is densest at the base, fades upward
	float height_fade = 1.0 - clamp(UVW.y * 2.0, 0.0, 1.0);
	height_fade = height_fade * height_fade;  // quadratic falloff

	// Noise for natural patchiness
	float t = TIME * 0.05;
	vec2 drift = UVW.xz * 3.0 + vec2(t, t * 0.7);
	float n1 = sin(drift.x * 1.3 + drift.y * 0.7) * 0.5 + 0.5;
	float n2 = sin(drift.x * 0.5 - drift.y * 1.2 + 3.0) * 0.5 + 0.5;
	float noise = n1 * 0.6 + n2 * 0.4;
	noise = smoothstep(0.25, 0.75, noise);

	float density = (mist_time + rain_mist) * cool_season * height_fade * noise;
	density = clamp(density, 0.0, 1.0);

	// Mist color: slightly blue-gray, warmer at golden hour
	vec3 mist_col = vec3(0.75, 0.78, 0.82);  // cool blue-gray base
	float warm = smoothstep(0.08, 0.25, sky_lum) * smoothstep(0.35, 0.20, sky_lum);
	mist_col = mix(mist_col, vec3(0.85, 0.78, 0.68), warm * 0.4);

	DENSITY = density * 0.8;
	ALBEDO = mist_col;
}

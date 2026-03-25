shader_type canvas_item;

uniform sampler2D SCREEN_TEXTURE : hint_screen_texture, filter_linear;
global uniform vec3 sky_reflect_color;
global uniform float season_t;
global uniform float lightning_flash;

#include "res://shaders/include/seasonal.gdshaderinc"

void fragment() {
	vec2 px = SCREEN_PIXEL_SIZE;
	vec3 c = texture(SCREEN_TEXTURE, SCREEN_UV).rgb;

	// --- Impressionist color diffusion ---
	// Light bleeds into shadows, edges soften — painterly quality.
	// 8 samples at 1-2px radius, blend 12% toward average.
	vec3 n1 = texture(SCREEN_TEXTURE, SCREEN_UV + vec2(px.x, 0.0)).rgb;
	vec3 n2 = texture(SCREEN_TEXTURE, SCREEN_UV - vec2(px.x, 0.0)).rgb;
	vec3 n3 = texture(SCREEN_TEXTURE, SCREEN_UV + vec2(0.0, px.y)).rgb;
	vec3 n4 = texture(SCREEN_TEXTURE, SCREEN_UV - vec2(0.0, px.y)).rgb;
	vec3 n5 = texture(SCREEN_TEXTURE, SCREEN_UV + vec2(px.x * 2.0, px.y)).rgb;
	vec3 n6 = texture(SCREEN_TEXTURE, SCREEN_UV - vec2(px.x * 2.0, px.y)).rgb;
	vec3 n7 = texture(SCREEN_TEXTURE, SCREEN_UV + vec2(px.x, px.y * 2.0)).rgb;
	vec3 n8 = texture(SCREEN_TEXTURE, SCREEN_UV - vec2(px.x, px.y * 2.0)).rgb;
	vec3 neighbor_avg = (n1 + n2 + n3 + n4 + n5 + n6 + n7 + n8) * 0.125;
	c = mix(c, neighbor_avg, 0.12);

	// Time-of-day detection from sky luminance
	float sky_lum = dot(sky_reflect_color, vec3(0.2126, 0.7152, 0.0722));
	float night_t  = smoothstep(0.15, 0.02, sky_lum);  // 1.0 at night
	float golden_t = smoothstep(0.1, 0.3, sky_lum) * smoothstep(0.5, 0.3, sky_lum);  // warm hours

	// Season detection
	float autumn_s = sn_atmo_autumn(season_t);
	float winter_s = sn_atmo_winter(season_t);
	float spring_s = sn_atmo_spring(season_t);

	// Warm dark floor — keep shadow detail, NYC is never pitch black
	// Slightly brighter floor at night (city light pollution)
	vec3 dark_floor = mix(vec3(0.018, 0.014, 0.012), vec3(0.022, 0.018, 0.016), night_t);
	c = max(c, dark_floor);
	// Very gentle shadow shaping — preserve detail like EGTTR's soft look
	c = pow(c, vec3(mix(1.02, 1.01, night_t)));

	float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));

	// Split-tone: tints shift with time and season
	vec3 shadow_tint = vec3(0.85, 0.92, 1.10);    // base: teal-blue shadows
	vec3 highlight_tint = vec3(1.12, 1.04, 0.86);  // base: amber highlights

	// Night: cooler shadows, neutral highlights
	shadow_tint    = mix(shadow_tint, vec3(0.80, 0.85, 1.15), night_t);
	highlight_tint = mix(highlight_tint, vec3(1.05, 0.95, 0.85), night_t);

	// Golden hour: warmer everything
	shadow_tint    = mix(shadow_tint, vec3(0.95, 0.88, 1.02), golden_t * 0.5);
	highlight_tint = mix(highlight_tint, vec3(1.18, 1.06, 0.78), golden_t * 0.6);

	// Autumn: push amber/brown
	if (autumn_s > 0.01) {
		shadow_tint    = mix(shadow_tint, vec3(0.92, 0.86, 0.95), autumn_s * 0.3);
		highlight_tint = mix(highlight_tint, vec3(1.20, 1.02, 0.72), autumn_s * 0.4);
	}
	// Winter: desaturated, cool steel-blue
	if (winter_s > 0.01) {
		shadow_tint    = mix(shadow_tint, vec3(0.82, 0.88, 1.12), winter_s * 0.3);
		highlight_tint = mix(highlight_tint, vec3(1.02, 1.02, 0.96), winter_s * 0.3);
	}

	float shadow_blend = 1.0 - smoothstep(0.0, 0.25, lum);
	float highlight_blend = smoothstep(0.40, 0.75, lum);
	c *= mix(vec3(1.0), shadow_tint, shadow_blend * 0.20);
	c *= mix(vec3(1.0), highlight_tint, highlight_blend * 0.15);

	// Enrich greens — subtle foliage warmth, EGTTR-style muted olive
	float green_boost = 0.03 * (1.0 - night_t * 0.7);
	green_boost *= (1.0 + spring_s * 0.2);            // spring: slightly lusher
	green_boost *= (1.0 - winter_s * 0.5);            // winter: muted foliage
	c.g *= 1.0 + green_boost * smoothstep(0.08, 0.4, c.g);
	// Gentle blue enrichment — soft sky, not vivid
	float blue_boost = 0.04 * (1.0 - night_t * 0.5);
	c.b *= 1.0 + blue_boost * smoothstep(0.06, 0.35, c.b);
	// Soften reds toward warm brown (less at night)
	float red_excess = max(c.r - (c.g + c.b) * 0.5, 0.0);
	c.r -= red_excess * mix(0.15, 0.08, night_t);
	c.g += red_excess * 0.04;

	// AgX tonemapper handles highlight compression — no manual filmic curve needed.
	// Only apply a very gentle midtone lift to compensate for AgX's slight desaturation.

	// Saturation — restrained, naturalistic. EGTTR greens are muted olive, not vivid.
	float lum2 = dot(c, vec3(0.2126, 0.7152, 0.0722));
	float sat = 1.12;  // compensate for AgX desaturation
	sat = mix(sat, 1.02, night_t);     // near-neutral at night
	sat = mix(sat, sat * 0.85, winter_s * 0.4);  // cooler winter
	c = mix(vec3(lum2), c, sat);

	// Warm cast — minimal, sun color handles warmth at golden hour
	vec3 cast = mix(vec3(1.01, 1.005, 0.97), vec3(0.98, 0.98, 1.02), night_t);
	// Golden hour: very slight — sun keyframe already warm, avoid double-dipping
	cast = mix(cast, vec3(1.02, 1.005, 0.95), golden_t * 0.15);
	c *= cast;

	// Eye adaptation — lift shadows in very dark scenes (NYC never pitch black)
	float scene_lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
	float lift = smoothstep(0.04, 0.0, scene_lum) * night_t * 0.015;
	c += lift;

	// Vignette — very subtle, EGTTR barely uses any
	vec2 vig_uv = SCREEN_UV * 2.0 - 1.0;
	float vig_strength = mix(0.08, 0.14, night_t);
	float vig = 1.0 - dot(vig_uv, vig_uv) * vig_strength;
	c *= vig;

	// Lightning flash — bright white wash, reduced vignette, desaturated
	if (lightning_flash > 0.01) {
		float lf = lightning_flash;
		// Wash toward blue-white (lightning color temperature ~15000K)
		vec3 flash_col = vec3(0.85, 0.88, 1.0);
		c = mix(c, flash_col, lf * 0.4);
		// Brighten
		c += flash_col * lf * 0.15;
		// Desaturate during flash (bright light washes out color)
		float flash_lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
		c = mix(c, vec3(flash_lum), lf * 0.5);
	}

	// Film grain — subtle photographic texture, more visible at night
	float grain_seed = dot(SCREEN_UV, vec2(12.9898, 78.233)) + TIME * 0.1;
	float grain = fract(sin(grain_seed) * 43758.5453) - 0.5;
	float grain_strength = mix(0.012, 0.025, night_t);  // subtler in daylight
	c += grain * grain_strength;

	COLOR = vec4(c, 1.0);
}

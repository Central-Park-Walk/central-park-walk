shader_type sky;

uniform vec3 sky_top_color = vec3(0.18, 0.38, 0.72);
uniform vec3 sky_horizon_color = vec3(0.55, 0.58, 0.68);
uniform vec3 ground_bottom_color = vec3(0.10, 0.12, 0.08);
uniform vec3 ground_horizon_color = vec3(0.35, 0.38, 0.30);

uniform float cloud_coverage = 0.65;
uniform float cloud_density = 0.50;
uniform float cloud_speed = 0.0015;
uniform vec3 cloud_color_top = vec3(0.90, 0.90, 0.92);
uniform vec3 cloud_color_bottom = vec3(0.45, 0.45, 0.50);
uniform float cloud_type = 0.0;  // 0=fair cumulus, 1=stratus overcast, 2=cumulonimbus
global uniform vec2 wind_vec;
global uniform float season_t;
global uniform float rain_wetness;
global uniform float lightning_flash;

#include "res://shaders/include/seasonal.gdshaderinc"

// Scalar hash — used for stars (cell-based)
float sky_hash(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 43.21);
	return fract(p.x * p.y);
}
// Gradient hash — returns 2D direction per lattice point
vec2 sky_grad(vec2 p) {
	p = vec2(dot(p, vec2(127.1, 311.7)),
	         dot(p, vec2(269.5, 183.3)));
	return -1.0 + 2.0 * fract(sin(p) * 43758.5453);
}
// Gradient (Perlin-style) noise — no grid artifacts
float sky_gnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	// Quintic interpolation (C2 continuous — no second-derivative seams)
	vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	return mix(mix(dot(sky_grad(i),                 f),
	               dot(sky_grad(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
	           mix(dot(sky_grad(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
	               dot(sky_grad(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x), u.y);
}
// FBM with per-octave rotation to break any residual grid alignment
float sky_fbm(vec2 p, int oct) {
	float v = 0.0, a = 0.5;
	mat2 rot = mat2(vec2(0.80, 0.60), vec2(-0.60, 0.80)); // ~37 deg
	for (int i = 0; i < oct; i++) {
		v += a * sky_gnoise(p);
		p = rot * p * 2.0;
		a *= 0.5;
	}
	return v * 0.5 + 0.5; // remap [-1,1] → [0,1]
}
// Billowy cloud noise: abs() of gradient noise creates sharp ridges
// that look like cumulus cloud edges. More defined than standard FBM.
float sky_billow(vec2 p, int oct) {
	float v = 0.0, a = 0.6;
	mat2 rot = mat2(vec2(0.80, 0.60), vec2(-0.60, 0.80));
	for (int i = 0; i < oct; i++) {
		v += a * abs(sky_gnoise(p));  // abs creates sharp valleys = cloud edges
		p = rot * p * 2.0;
		a *= 0.45;  // each octave contributes less — large shapes dominate
	}
	return v;
}
// Curl noise: perpendicular gradient of noise creates divergence-free
// (mass-conserving) flow field. Advects cloud UVs so clouds stretch,
// compress, and billow naturally instead of translating rigidly.
vec2 sky_curl(vec2 p) {
	const float e = 0.15;
	float n0 = sky_gnoise(p);
	float nx = sky_gnoise(p + vec2(e, 0.0));
	float ny = sky_gnoise(p + vec2(0.0, e));
	return vec2(ny - n0, -(nx - n0)) / e;
}

// Ridged noise: inverted billow, creates mountain-like peaks = towering cumulus
float sky_ridged(vec2 p, int oct) {
	float v = 0.0, a = 0.5, prev = 1.0;
	mat2 rot = mat2(vec2(0.80, 0.60), vec2(-0.60, 0.80));
	for (int i = 0; i < oct; i++) {
		float n = 1.0 - abs(sky_gnoise(p));
		n = n * n;  // sharpen ridges
		v += a * n * prev;  // previous octave modulates — detail only in high areas
		prev = n;
		p = rot * p * 2.1;
		a *= 0.5;
	}
	return v;
}

void sky() {
	vec3 dir = EYEDIR;
	float elev = dir.y;

	// --- Sky gradient ---
	vec3 sky_col;
	if (elev >= 0.0) {
		float t = clamp(elev * 2.5, 0.0, 1.0);
		sky_col = mix(sky_horizon_color, sky_top_color, t);
	} else {
		float t = clamp(-elev * 4.0, 0.0, 1.0);
		sky_col = mix(ground_horizon_color, ground_bottom_color, t);
	}

	// --- Seasonal sky modulation ---
	// Winter: paler, hazier, more gray-white
	// Autumn: warm amber horizon, slightly hazier
	// Spring: fresh, slightly cooler blue
	// Summer: deep rich blue (baseline)
	if (elev >= 0.0) {
		float s_autumn = sn_atmo_autumn(season_t);
		float s_winter = sn_atmo_winter(season_t);
		float s_spring = sn_atmo_spring(season_t);
		// Winter: pale blue-gray, washed out
		sky_col = mix(sky_col, sky_col * vec3(0.92, 0.95, 1.02) + vec3(0.04, 0.04, 0.05), s_winter * 0.25);
		// Autumn: warmer amber-gold in lower sky
		float low_sky = 1.0 - smoothstep(0.0, 0.35, elev);
		sky_col += vec3(0.06, 0.03, 0.0) * s_autumn * low_sky;
		// Spring: slightly cooler, more saturated blue
		sky_col = mix(sky_col, sky_col * vec3(0.96, 1.0, 1.06), s_spring * 0.15);
	}

	// --- Urban atmospheric haze layer ---
	// NYC air: warm haze band at horizon from urban heat island + particulates.
	// Visible from CP looking at skylines on both sides. Thicker in summer.
	if (elev >= 0.0) {
		float haze_band = exp(-elev * 12.0);  // concentrated at horizon, decays above
		// Summer smog is thicker; winter air is cleaner
		float s_summer = smoothstep(0.5, 1.2, season_t) * smoothstep(2.0, 1.2, season_t);
		float s_winter2 = sn_atmo_winter(season_t);
		float haze_density = mix(0.12, 0.22, s_summer) * (1.0 - s_winter2 * 0.3);
		// Rain cleans air, reducing haze
		haze_density *= (1.0 - rain_wetness * 0.6);
		vec3 haze_col = vec3(0.62, 0.63, 0.68);  // blue-gray urban haze
		// Sun-lit haze: warmer when sun illuminates from behind
		float sun_elev_pre = LIGHT0_DIRECTION.y;
		float haze_warm = smoothstep(0.30, 0.05, sun_elev_pre);
		haze_col = mix(haze_col, vec3(0.72, 0.62, 0.52), haze_warm * 0.4);
		sky_col = mix(sky_col, haze_col, haze_band * haze_density);
	}

	// --- Sun disc + atmospheric scattering ---
	float sun_dot = dot(dir, LIGHT0_DIRECTION);
	float sun_disc = smoothstep(0.9992, 0.9998, sun_dot);
	vec3 sun_col = LIGHT0_COLOR * LIGHT0_ENERGY * 2.0;
	// Sun glow halo — tight inner core + wider outer aureole
	float sun_glow = pow(max(sun_dot, 0.0), 64.0) * 0.3;
	float sun_aureole = pow(max(sun_dot, 0.0), 8.0) * 0.12;
	// Mie forward scattering: broader warm halo from atmospheric aerosols
	float mie = pow(max(sun_dot, 0.0), 3.0) * 0.06;
	vec3 mie_col = LIGHT0_COLOR * vec3(1.05, 0.95, 0.85);  // slightly warm
	sky_col += sun_col * (sun_disc + sun_glow + sun_aureole) + mie_col * mie * LIGHT0_ENERGY;

	// Golden hour scatter — warm tint near horizon when sun is low
	float sun_elev = LIGHT0_DIRECTION.y;  // negative = below horizon
	float golden = smoothstep(0.15, -0.05, sun_elev);  // peaks at sunset/sunrise
	if (golden > 0.01 && elev >= 0.0) {
		// Rayleigh-like forward scatter: warm orange glow around sun direction on horizon
		float scatter_dot = max(sun_dot, 0.0);
		float scatter = pow(scatter_dot, 3.0) * golden * 0.40;
		vec3 scatter_col = LIGHT0_COLOR * vec3(1.15, 0.65, 0.35);  // deeper orange
		// Stronger near horizon, fades above
		scatter *= (1.0 - smoothstep(0.0, 0.35, elev));
		sky_col += scatter_col * scatter;

		// Earth shadow: deep blue-purple band on the horizon opposite the sun at dusk
		// The shadow of the earth rises as the sun sets — visible from CP looking east
		float anti_sun = max(-sun_dot, 0.0);  // strongest away from sun
		float earth_shadow = pow(anti_sun, 1.5) * golden * 0.25;
		vec3 shadow_tint = vec3(0.12, 0.08, 0.30);  // deep purple-blue
		earth_shadow *= (1.0 - smoothstep(0.0, 0.20, elev));  // tight horizon band
		sky_col = mix(sky_col, shadow_tint, earth_shadow);

		// Belt of Venus: pink-orange band just ABOVE the earth shadow
		float venus_belt = smoothstep(0.05, 0.12, elev) * smoothstep(0.25, 0.12, elev);
		venus_belt *= anti_sun * golden * 0.18;
		sky_col += vec3(0.20, 0.10, 0.08) * venus_belt;

		// Blue hour: opposite-sun sky deepens to purple-blue at dusk/dawn
		float blue_hour = pow(anti_sun, 1.5) * golden * 0.20;
		vec3 blue_tint = vec3(0.15, 0.10, 0.35);  // deep purple-blue
		blue_hour *= (1.0 - smoothstep(0.0, 0.5, elev));  // near horizon
		sky_col += blue_tint * blue_hour;
	}

	// --- Moon — visible through NYC light pollution ---
	if (elev > 0.0 && LIGHT0_ENERGY < 0.15) {
		// Moon direction: opposite sun with slight south offset (NYC ~40°N)
		vec3 moon_dir = normalize(-LIGHT0_DIRECTION + vec3(0.0, 0.35, 0.1));
		float moon_dot = dot(dir, moon_dir);
		float moon_fade = smoothstep(0.15, 0.0, LIGHT0_ENERGY);  // appears at dusk

		// Moon disc — angular diameter ~0.5°, bright white-blue through atmosphere
		float moon_disc = smoothstep(0.9996, 0.9999, moon_dot);
		// Subtle surface variation (maria dark patches)
		float maria = sky_gnoise(dir.xz / max(elev, 0.01) * 120.0) * 0.15;
		vec3 moon_col = vec3(0.82, 0.85, 0.92) * (1.0 - max(maria, 0.0) * moon_disc);
		// Moon glow halo — atmospheric scattering around the disc
		float moon_glow = pow(max(moon_dot, 0.0), 128.0) * 0.15;
		float moon_halo = pow(max(moon_dot, 0.0), 16.0) * 0.04;
		sky_col += moon_col * (moon_disc * 1.5 + moon_glow + moon_halo) * moon_fade;
	}

	// --- Stars (Bortle 8-9: inner-city light pollution) ---
	// Central Park: nearly starless sky. Only ~10 brightest stars visible on clear nights.
	if (elev > 0.0) {
		float star_fade = smoothstep(0.15, 0.0, LIGHT0_ENERGY);
		if (star_fade > 0.0) {
			vec2 star_uv = dir.xz / (elev + 0.001) * 80.0;
			vec2 star_cell = floor(star_uv);
			float star_rand = sky_hash(star_cell);
			float star_mask = step(0.997, star_rand);  // 0.3% density — only brightest stars
			float star_bright = sky_hash(star_cell + vec2(13.7, 29.3));
			star_bright = star_bright * star_bright * 0.8;  // dimmer through light pollution
			float twinkle = 0.8 + 0.2 * sin(TIME * 2.0 + star_rand * 100.0);
			vec2 star_frac = fract(star_uv) - 0.5;
			float star_point = smoothstep(0.10, 0.02, length(star_frac));
			// Star color variation: some warm (Betelgeuse), some blue-white (Sirius)
			float star_hue = sky_hash(star_cell + vec2(37.1, 71.3));
			vec3 star_color = mix(vec3(1.0, 0.85, 0.70), vec3(0.80, 0.90, 1.0), star_hue);
			sky_col += star_color * (star_bright * star_mask * star_point * star_fade * twinkle);
		}
		// Light pollution sky glow — warm amber dome, directional
		// NYC Bortle 8-9: dim warm amber, never truly dark but not bright
		float lp_fade = smoothstep(0.15, 0.0, LIGHT0_ENERGY);
		vec3 light_pollution = vec3(0.10, 0.06, 0.03);  // subtle warm amber
		// Directional: south = Midtown (brighter), north = Harlem (dimmer)
		float south_bias = dir.z * 0.20 + 0.70;
		float side_glow = abs(dir.x) * 0.10;
		// Fades toward zenith — light pollution concentrated at horizon
		float lp_height = mix(1.0, 0.3, smoothstep(0.0, 0.6, elev));
		float lp_strength = lp_fade * lp_height * (south_bias + side_glow);
		sky_col += light_pollution * lp_strength;
	}

	// --- Cloud layer: type-dependent rendering ---
	// cloud_type: 0=fair cumulus, 1=stratus overcast, 2=cumulonimbus storm
	if (elev > -0.05) {
		float cloud_y = max(elev, 0.01);
		vec2 cloud_uv = dir.xz / (cloud_y + 0.1) * 0.8;
		// Wind-driven cloud drift (base translation)
		float wind_mag = length(wind_vec);
		vec2 wind_dir = wind_mag > 0.001 ? wind_vec / wind_mag : vec2(0.7, 0.3);
		float drift_speed = cloud_speed + wind_mag * 0.08;
		cloud_uv += TIME * wind_dir * drift_speed;

		// Curl noise flow advection: clouds billow and stretch naturally.
		// Large scale (~5min period): slow swirling air masses push cloud shapes
		vec2 flow = sky_curl(cloud_uv * 0.15 + TIME * vec2(0.0008, 0.0003));
		// Medium scale (~90s period): turbulent eddies create detail evolution
		flow += sky_curl(cloud_uv * 0.4 + TIME * vec2(0.002, 0.001)) * 0.4;
		// Small scale (~30s period): fine turbulence at cloud edges
		flow += sky_curl(cloud_uv * 1.2 + TIME * vec2(0.005, 0.003)) * 0.15;
		cloud_uv += flow * 0.12;

		float sun_illum = max(dot(LIGHT0_DIRECTION, vec3(0.0, 1.0, 0.0)), 0.0);
		float cloud_mask = 0.0;
		float cloud_depth = 0.0;
		vec3 cloud_col = vec3(0.5);

		if (cloud_type < 0.5) {
			// --- FAIR WEATHER CUMULUS: billowy defined clouds with blue gaps ---
			// Billow noise creates sharp cloud edges like real cumulus
			float n_shape = sky_billow(cloud_uv * 2.0, 5);
			// Ridged noise adds towering vertical structure
			float n_tower = sky_ridged(cloud_uv * 1.5 + vec2(7.3, 0.0), 4);
			float n = n_shape * 0.65 + n_tower * 0.35;
			// Sharp threshold — distinct cloud/sky boundary
			float thresh = 1.0 - cloud_coverage;
			cloud_mask = smoothstep(thresh - 0.02, thresh + 0.08, n);
			cloud_mask *= cloud_density;
			cloud_depth = smoothstep(thresh + 0.05, thresh + 0.35, n);

			// Bright white tops, defined gray bases
			vec2 shadow_off = LIGHT0_DIRECTION.xz * 0.05;
			float n_shadow = sky_billow((cloud_uv + shadow_off) * 2.0, 3);
			float self_shadow = smoothstep(0.3, 0.65, n_shadow) * 0.40;
			// Strong contrast: dark base to bright top
			vec3 c_dark = cloud_color_bottom * 0.7;
			vec3 c_bright = cloud_color_top * 1.1;
			cloud_col = mix(c_dark, c_bright,
				clamp(cloud_depth * 0.5 + sun_illum * 0.35 - self_shadow + 0.15, 0.0, 1.0));
			// Silver lining: bright rim on thin backlit edges
			float edge_thin = (1.0 - cloud_depth) * cloud_mask;
			cloud_col += LIGHT0_COLOR * pow(max(sun_dot, 0.0), 3.0) * 0.5 * edge_thin;

		} else if (cloud_type < 1.5) {
			// --- STRATUS: flat layered overcast with subtle variation ---
			float n_base = sky_fbm(cloud_uv * vec2(1.5, 3.5), 5);
			float n_thin = sky_billow(cloud_uv * vec2(4.0, 6.0) + vec2(11.3, 7.1), 3);
			float n = n_base * 0.65 + n_thin * 0.35;
			// Wide coverage band — overcast but with thin/thick variation
			cloud_mask = smoothstep(1.0 - cloud_coverage - 0.12, 1.0 - cloud_coverage + 0.05, n);
			cloud_mask *= cloud_density;
			cloud_depth = smoothstep(1.0 - cloud_coverage, 1.0 - cloud_coverage + 0.25, n);

			// Gray with visible variation — not flat uniform
			vec3 strat_dark = vec3(0.38, 0.40, 0.44);
			vec3 strat_light = vec3(0.62, 0.64, 0.68);
			cloud_col = mix(strat_dark, strat_light,
				(1.0 - cloud_depth) * 0.5 + n_thin * 0.3 + sun_illum * 0.12);
			// Thinner patches show brighter sky through
			cloud_col += vec3(0.10) * (1.0 - cloud_mask) * (1.0 - cloud_depth);

		} else {
			// --- CUMULONIMBUS: towering dark storm with dramatic structure ---
			float n_tower = sky_ridged(cloud_uv * 1.2, 5);
			float n_turb = sky_billow(cloud_uv * 4.0 + vec2(5.3, 9.1), 4);
			float n_anvil = sky_fbm(cloud_uv * vec2(0.8, 2.5) + vec2(17.0, 3.0), 4);
			// Turbulent towering mass with anvil spread
			float n = n_tower * 0.45 + n_turb * 0.30 + n_anvil * 0.25;
			float thresh = 1.0 - cloud_coverage;
			cloud_mask = smoothstep(thresh - 0.08, thresh + 0.05, n);
			cloud_mask *= cloud_density;
			cloud_depth = smoothstep(thresh, thresh + 0.40, n);

			// Very dark bases, bright anvil tops — high contrast
			vec2 shadow_off = LIGHT0_DIRECTION.xz * 0.07;
			float n_shadow = sky_ridged((cloud_uv + shadow_off) * 1.5, 4);
			float self_shadow = smoothstep(0.25, 0.6, n_shadow) * 0.55;
			vec3 storm_dark = vec3(0.12, 0.12, 0.16);   // very dark storm base
			vec3 storm_mid = vec3(0.30, 0.30, 0.35);     // mid-cloud
			vec3 storm_bright = vec3(0.52, 0.52, 0.58);  // anvil top
			float vert = clamp(cloud_depth * 0.6 - self_shadow + sun_illum * 0.1, 0.0, 1.0);
			cloud_col = mix(storm_dark, mix(storm_mid, storm_bright, vert), vert);
			// Green-yellow tinge in severe storms (real meteorological phenomenon)
			cloud_col += vec3(-0.02, 0.03, -0.04) * cloud_depth;
		}

		// --- Common cloud effects (all types) ---

		// Sunset/sunrise: clouds blaze with dramatic warm colors
		float cloud_golden = smoothstep(0.20, -0.08, LIGHT0_DIRECTION.y);
		if (cloud_golden > 0.01) {
			// Sunward clouds: deep orange to crimson blaze
			float sun_face = pow(max(sun_dot, 0.0), 1.5);
			vec3 blaze = mix(vec3(1.2, 0.55, 0.18), vec3(1.0, 0.30, 0.10), cloud_golden);
			cloud_col += blaze * sun_face * cloud_golden * 0.55;
			// Anti-sun clouds: pink-magenta tones (reflected light through atmosphere)
			float anti_face = pow(max(-sun_dot, 0.0), 2.0);
			cloud_col += vec3(0.50, 0.22, 0.38) * anti_face * cloud_golden * 0.30;
			// Overall warm shift — entire cloud layer goes golden/orange
			cloud_col *= mix(vec3(1.0), vec3(1.25, 0.88, 0.68), cloud_golden * 0.45);
			// Bright rim/silver lining on cloud edges facing sun
			float rim = pow(max(sun_dot, 0.0), 3.0) * 0.35;
			cloud_col += LIGHT0_COLOR * vec3(1.3, 0.7, 0.35) * rim * cloud_golden;
			// Deep sunset: clouds go from orange to deep red at the very end
			float deep_sunset = smoothstep(-0.02, -0.10, LIGHT0_DIRECTION.y);
			cloud_col += vec3(0.35, 0.05, 0.02) * deep_sunset * cloud_depth * 0.40;
		}

		// Night darkening
		if (LIGHT0_ENERGY < 0.15) {
			vec3 moon_dir2 = normalize(-LIGHT0_DIRECTION + vec3(0.0, 0.35, 0.1));
			float moon_edge = pow(max(dot(dir, moon_dir2), 0.0), 4.0) * 0.25;
			float night_f = smoothstep(0.15, 0.0, LIGHT0_ENERGY);
			cloud_col += vec3(0.20, 0.22, 0.28) * moon_edge * night_f;
			cloud_col *= mix(1.0, 0.25, night_f);
		}

		// Horizon fade
		float horizon_fade = smoothstep(0.0, 0.10, elev);
		cloud_mask *= horizon_fade;

		sky_col = mix(sky_col, cloud_col, cloud_mask);

		// --- Cirrus wisps (only with fair weather or light stratus) ---
		if (cloud_type < 1.5 && elev > 0.15) {
			vec2 cirrus_uv = dir.xz / (cloud_y + 0.05) * 0.3;
			// Cirrus blown faster by wind (high altitude = stronger wind)
			vec2 cirrus_wind = wind_mag > 0.001 ? wind_dir * (cloud_speed * 2.0 + wind_mag * 0.20) : vec2(cloud_speed * 3.5, cloud_speed * 0.4);
			cirrus_uv += TIME * cirrus_wind;
			// Cirrus flow: stretched, faster eddies (jet stream shear)
			cirrus_uv += sky_curl(cirrus_uv * 0.3 + TIME * vec2(0.003, 0.001)) * 0.08;
			float cn = sky_gnoise(cirrus_uv * vec2(2.0, 6.0));
			cn += sky_gnoise(cirrus_uv * vec2(4.0, 12.0)) * 0.4;
			float cirrus = smoothstep(0.3, 0.8, cn) * 0.12;
			cirrus *= smoothstep(0.15, 0.35, elev);
			vec3 cirrus_col = cloud_color_top + LIGHT0_COLOR * 0.12;
			sky_col = mix(sky_col, cirrus_col, cirrus);
		}
	}

	// Lightning flash — clouds light up from within during thunderstorm
	if (lightning_flash > 0.01 && elev > -0.05) {
		float lf = lightning_flash;
		// Clouds glow bright blue-white from internal lightning
		float cloud_y2 = max(elev, 0.01);
		float lf_wm = length(wind_vec);
		vec2 lf_wd = lf_wm > 0.001 ? wind_vec / lf_wm : vec2(0.7, 0.7);
		vec2 lf_uv = dir.xz / (cloud_y2 + 0.1) * 0.8 + TIME * lf_wd * (cloud_speed + lf_wm * 0.08);
		float lf_cloud = sky_fbm(lf_uv * 3.0, 3);
		float lf_mask = smoothstep(0.4, 0.8, lf_cloud);
		// Lightning illuminates from below: brighter cloud bases
		vec3 lf_col = vec3(0.70, 0.75, 1.0);  // cool white-blue
		sky_col += lf_col * lf * lf_mask * 0.6;
		// Even clear sky brightens slightly (atmospheric scatter from flash)
		sky_col += lf_col * lf * 0.08;
	}

	COLOR = sky_col;
}

shader_type sky;
render_mode use_debanding;

uniform sampler2D blend_from_texture : filter_linear, repeat_disable, source_color;
uniform sampler2D blend_to_texture : filter_linear, repeat_disable, source_color;

uniform sampler2D sky_blend_from_texture : filter_linear, repeat_disable, source_color;
uniform sampler2D sky_blend_to_texture : filter_linear, repeat_disable, source_color;

uniform sampler2D source_transmittance : filter_linear, hint_default_black, repeat_disable;

uniform float blend_amount : hint_range(0.0, 1.0, 0.01);
// Background-atmosphere brightness calibration (2026-06-10): the LUT/50
// convention came from the upstream demo's exposure setup; under our AgX
// pipeline a clear noon sky measured ~1 stop under reference. Calibrated
// via --sky-cal sweeps against real-photo targets (docs/rendering.md).
uniform float sky_brightness = 1.0;
// Celestial sun direction from day_night_cycle.gd (decoupled from the
// shadow light during twilight, 2026-06-11). ZERO = unset → LIGHT0.
// At night it hands over to the MOON (the LUT/clouds are moonlit), so
// the visible sun disk uses true_sun_dir instead (sky.md 2.5) — the old
// path drew the sun disk at the night light's position, which is what
// the "always-full moon" actually was.
uniform vec3 celestial_dir = vec3(0.0);
uniform vec3 true_sun_dir = vec3(0.0);
uniform float sun_disk_scale = 1.0;
uniform float sun_disk_hdr_brightness : hint_range(0.0, 100.0, 0.01) = 5.0;
uniform float sun_disk_hdr_attenuation : hint_range(1.0, 10.0, 0.01) = 1.0;
// Refraction flattening within ~2 deg of the horizon (vertical squash)
uniform float sun_disk_squash = 1.0;
// Moon (sky.md 2.5): direction + (illum fraction, perceptual disk scale,
// visibility, refraction squash). The terminator is geometric — the disk
// is shaded as a sphere lit by true_sun_dir, so phase AND orientation
// are exact by construction.
uniform vec3 moon_dir = vec3(0.0, -1.0, 0.0);
uniform vec4 moon_params = vec4(1.0, 1.0, 0.0, 1.0);

// High ice layer (sky.md P2): cirrus / cirrostratus / altocumulus at 6-10
// km, far above the volumetric shell. Rendered as a flat sheet the view
// ray pierces, advected by the upper wind (high_cloud_offset, in metres,
// integrated in cloud_sky.gd). Each type is gated by an opacity that the
// day/night cycle sets per weather state (CLEAR wisps, dramatic-dusk
// mackerel, snow veil). high_cloud_gain anchors lit-ice brightness in the
// sky LUT exposure (calibrated by capture, like sky_brightness/sun_cal).
uniform vec2 high_cloud_offset = vec2(0.0);
uniform float cirrus_amount : hint_range(0.0, 1.0) = 0.0;
uniform float cirrostratus_amount : hint_range(0.0, 1.0) = 0.0;
uniform float altocumulus_amount : hint_range(0.0, 1.0) = 0.0;
uniform float high_cloud_gain : hint_range(0.0, 40.0) = 6.0;

// Night sky layers (sky.md §6 P0). The LUT darkens honestly to ~0 at
// night (real sun below the horizon); what you actually see over NYC is
// additive on top of that: the amber light-pollution dome (Bortle 8-9,
// Midtown-south brighter) and the brighter stars punching through it —
// art-directed a touch past strict Bortle for "dramatic night skies".
// night_amount is set by day_night_cycle.gd (0 day -> 1 night).
uniform float night_amount : hint_range(0.0, 1.0) = 0.0;
uniform float star_intensity : hint_range(0.0, 4.0) = 1.0;
uniform float light_pollution_gain : hint_range(0.0, 4.0) = 1.0;

vec2 oct_wrap(vec2 v) {
	vec2 signVal;
	signVal.x = v.x >= 0.0 ? 1.0 : -1.0;
	signVal.y = v.y >= 0.0 ? 1.0 : -1.0;
	return (1.0 - abs(v.yx)) * signVal;
}

vec2 vec3_to_oct(vec3 e) {
	e /= abs(e.x) + abs(e.y) + abs(e.z);
	e.xy = e.z >= 0.0 ? e.xy : oct_wrap( e.xy );

	vec2 n;
	n.y = e.y * 0.5 + 0.5;
	n.x = e.x * 0.5 + n.y;
	n.y = e.x * -0.5 + n.y;

	return n;
}

vec3 getValFromSkyLUT(vec3 rayDir) {
	vec2 uv;
	float phi = atan(rayDir.z, rayDir.x);
    float theta = asin(rayDir.y);
	uv.x = (phi / PI * 0.5 + 0.5);
    // Undo the non-linear transformation from the sky-view LUT
    uv.y = sqrt(abs(theta) / (PI * 0.5)) * sign(theta) * 0.5 + 0.5;

	vec3 blend_from = texture(sky_blend_from_texture, uv).rgb;
	vec3 blend_to = texture(sky_blend_to_texture, uv).rgb;
    return mix(blend_from, blend_to, blend_amount) / 50.0 * sky_brightness;
}

// Decompose the angular offset from a body into horizontal/vertical
// components and return an effective cosTheta with the vertical axis
// squashed (refraction flattening near the horizon). squash=1 → exact.
float squashed_cos_theta(vec3 rayDir, vec3 bodyDir, float squash) {
	float cosTheta = dot(rayDir, bodyDir);
	if (squash >= 0.999 || abs(bodyDir.y) > 0.99) return cosTheta;
	vec3 u = normalize(cross(vec3(0.0, 1.0, 0.0), bodyDir)); // horizontal
	vec3 v = cross(bodyDir, u);                              // vertical
	vec3 off = rayDir - bodyDir * cosTheta;
	float du = dot(off, u);
	float dv = dot(off, v) / squash;
	float s2 = du * du + dv * dv;                            // ~sin^2 theta
	return sqrt(max(1.0 - s2, 0.0)) * sign(cosTheta);
}

// https://www.shadertoy.com/view/slSXRW
vec3 sunWithBloom(vec3 rayDir, vec3 sunDir) {
    float sunSolidAngle = sun_disk_scale * 0.53*PI/180.0;
    float minSunCosTheta = cos(sunSolidAngle);

    float cosTheta = squashed_cos_theta(rayDir, sunDir, sun_disk_squash);
    if (cosTheta >= minSunCosTheta) return vec3(1.0 + pow(smoothstep(minSunCosTheta, 1.0, cosTheta), sun_disk_hdr_attenuation) * sun_disk_hdr_brightness);

    float offset = minSunCosTheta - cosTheta;
    float gaussianBloom = exp(-offset*50000.0)*0.5;
    float invBloom = 1.0/(0.02 + offset*300.0)*0.01;
    return vec3(gaussianBloom+invBloom);
}

float rayIntersectSphere(vec3 ro, vec3 rd, float rad) {
    float b = dot(ro, rd);
    float c = dot(ro, ro) - rad*rad;
    if (c > 0.0f && b > 0.0) return -1.0;
    float discr = b*b - c;
    if (discr < 0.0) return -1.0;
    // Special case: inside sphere, use far discriminant
    if (discr > b*b) return (-b + sqrt(discr));
    return -b - sqrt(discr);
}

const float groundRadiusMM = 6.360;
const float atmosphereRadiusMM = 6.460;
const vec3 viewPos = vec3(0.0, groundRadiusMM + 0.0002, 0.0);
const vec2 tLUTRes = vec2(256.0, 64.0);

vec3 getValFromTLUT(sampler2D tex, vec2 bufferRes, vec3 pos, vec3 sunDir) {
    float height = length(pos);
    vec3 up = pos / height;
	float sunCosZenithAngle = dot(up,sunDir);
    vec2 uv = vec2(tLUTRes.x*clamp(0.5 + 0.5*sunCosZenithAngle, 0.0, 1.0),
                   tLUTRes.y*max(0.0, min(1.0, (height - groundRadiusMM)/(atmosphereRadiusMM - groundRadiusMM))));
    uv /= bufferRes;
    return texture(tex, uv).rgb;
}

vec3 sun_dir() {
	return dot(celestial_dir, celestial_dir) > 0.25 ? celestial_dir : LIGHT0_DIRECTION;
}

// The VISIBLE sun disk/blaze follow the true sun (which sets for real);
// the LUT/cloud lighting direction (sun_dir) becomes the moon at night.
vec3 disk_sun_dir() {
	return dot(true_sun_dir, true_sun_dir) > 0.25 ? true_sun_dir : sun_dir();
}

// Cheap value-noise stack (also used by the high ice layer below).
float h21(vec2 p) {
	// Precision-safe hash (Dave Hoskins) — the sin-based hash loses precision
	// at the large coordinates the flat-sheet projection reaches near the
	// horizon, which banded the cirrus/altocumulus into scratchy lattices.
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = h21(i);
	float b = h21(i + vec2(1.0, 0.0));
	float c = h21(i + vec2(0.0, 1.0));
	float d = h21(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0;
	float a = 0.5;
	for (int i = 0; i < 5; i++) {
		s += a * vnoise(p);
		p *= 2.02;
		a *= 0.5;
	}
	return s;
}

// Moon body (sky.md 2.5): opaque phase-shaded disk. Returns the pixel
// color with the moon composited over the background — the lit part is
// moonlight through atmospheric transmittance (reddens/dims at the
// horizon) plus the sky's own in-scatter haze (daytime moon reads pale
// blue-washed for free); the dark limb keeps faint earthshine.
vec3 moon_body(vec3 dir, vec3 bg) {
	if (moon_params.z <= 0.001) return bg;
	vec3 m = normalize(moon_dir);
	if (dot(dir, m) < 0.5) return bg;
	float ang_r = moon_params.y * 0.53 * PI / 180.0; // matches sun convention
	vec3 u = normalize(cross(vec3(0.0, 1.0, 0.0), m));
	vec3 v = cross(m, u);
	vec3 off = dir - m * dot(dir, m);
	float sin_r = sin(ang_r);
	float px = dot(off, u) / sin_r;
	float pv = dot(off, v) / (moon_params.w * sin_r);
	float r2 = px * px + pv * pv;
	if (r2 >= 1.0) return bg;
	// Sphere normal on the earth-facing hemisphere; light with the true
	// sun direction (sun is ~400x farther — its earth-relative direction
	// IS the light direction at the moon).
	float z = sqrt(1.0 - r2);
	vec3 n = normalize(u * px + v * pv - m * z);
	float lit = dot(n, normalize(disk_sun_dir()));
	float shade = smoothstep(-0.06, 0.18, lit);
	// Limb darkening + irregular maria blotches (P1: the disk reads up to
	// ~5x now — the old sine plaid read as a checker at that size).
	float limb = 0.95 + 0.05 * z;  // real moon is near-flat (regolith backscatter), not solar limb-darkened
	float mn = vnoise(vec2(px, pv) * 3.0 + 7.0) * 0.65
			+ vnoise(vec2(px, pv) * 6.5 + 2.0) * 0.35;
	float maria = 1.0 - 0.22 * smoothstep(0.42, 0.62, mn);
	// Day washes the disk toward the sky (contrast collapses; the in-
	// scatter term below does the rest).
	float dayness = smoothstep(-0.05, 0.20, disk_sun_dir().y);
	float lum = mix(2.2, 0.9, dayness);
	vec3 surf = vec3(0.92, 0.93, 0.95) * lum * limb * maria
			* (shade + 0.018 * (1.0 - shade));         // earthshine
	surf *= getValFromTLUT(source_transmittance, tLUTRes, viewPos, m);
	vec3 moon_col = surf + getValFromSkyLUT(dir);       // in-scatter haze
	float edge = smoothstep(1.0, 0.93, r2);             // soft limb
	return mix(bg, moon_col, edge * moon_params.z);
}

// Precision-safe scalar hash (Dave Hoskins) for the star cells.
float star_hash(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// Light-pollution dome + starfield, in sky-LUT display units (added to
// the background BEFORE the moon composite and the cloud layers, so
// clouds/ice occlude stars and the moon draws over them).
vec3 night_sky(vec3 dir) {
	if (night_amount < 0.001 || dir.y < 0.0) return vec3(0.0);
	// Amber dome: horizon-heavy with a zenith floor (NYC is never black);
	// south (+Z, Midtown) brighter than north (Harlem).
	float lp_h = exp(-max(dir.y, 0.0) * 5.0) + 0.22;
	float south = 0.78 + 0.22 * clamp(dir.z, -1.0, 1.0);
	vec3 lp = vec3(0.085, 0.054, 0.027) * lp_h * south * light_pollution_gain;
	// Stars: hashed cells, power-law brightness (few bright, many faint),
	// jittered subpixel points, gentle twinkle; murk-fade near the horizon.
	vec2 suv = dir.xz / (dir.y + 0.08) * 60.0;
	vec2 cell = floor(suv);
	float rnd = star_hash(cell);
	vec3 star = vec3(0.0);
	if (rnd > 0.988) {
		float b = star_hash(cell + 19.19);
		b = b * b * b;
		vec2 jit = (vec2(star_hash(cell + 7.7), star_hash(cell + 3.3)) - 0.5) * 0.6;
		float pt = smoothstep(0.11, 0.02, length(fract(suv) - 0.5 - jit));
		float tw = 0.75 + 0.25 * sin(TIME * (1.5 + rnd * 2.0) + rnd * 40.0);
		float hue = star_hash(cell + 11.1);
		vec3 scol = mix(vec3(1.0, 0.83, 0.65), vec3(0.72, 0.84, 1.0), hue);
		float horiz = smoothstep(0.03, 0.25, dir.y);
		star = scol * (0.10 + b) * pt * tw * horiz * 2.0 * star_intensity;
	}
	return (lp + star) * night_amount;
}

// Earth shadow + Belt of Venus (sky.md §6 P5, ported from the dead
// fallback shader but rebuilt HDR-relative): at civil twilight the
// anti-solar horizon carries the planet's own shadow — a cool blue-grey
// band whose top edge RISES as the sun sinks — with the pink anti-
// twilight arch (Belt of Venus) riding just above it. Both scale off
// the local sky luminance so they track exposure/calibration instead
// of the old absolute LDR constants.
vec3 twilight_bands(vec3 col, vec3 dir) {
	vec3 sdir = disk_sun_dir();
	float se = sdir.y;
	// Active sun +1.7..-6.9 deg; strongest -0.6..-2.9 deg.
	float gate = smoothstep(0.03, -0.01, se) * smoothstep(-0.12, -0.05, se);
	if (gate < 0.005 || dir.y < -0.02) { return col; }
	float anti = max(-dot(normalize(sdir.xz), normalize(dir.xz + vec2(1e-5))), 0.0);
	// Shadow top edge tracks sun depression (~1:1, softened); belt sits
	// in a band just above it and fades with altitude.
	float dep = max(-se, 0.0);
	float shadow_w = pow(anti, 1.8) * gate
			* smoothstep(dep * 1.4 + 0.05, 0.0, dir.y) * 0.45;
	float belt_w = pow(anti, 1.4) * gate
			* smoothstep(dep * 0.5, dep * 1.2 + 0.06, dir.y)
			* smoothstep(dep * 2.2 + 0.20, dep * 1.4 + 0.08, dir.y);
	float lum = dot(col, vec3(0.2126, 0.7152, 0.0722));
	col = mix(col, lum * vec3(0.60, 0.68, 1.05), shadow_w);
	col += lum * vec3(0.55, 0.12, 0.16) * belt_w;
	return col;
}

vec3 get_atmo(vec3 dir) {
	vec3 col = getValFromSkyLUT(dir);
	col = twilight_bands(col, dir);
	col += night_sky(dir);
	vec3 sunLum = sunWithBloom(dir, disk_sun_dir());
    if (length(sunLum) > 0.0) {
        if (rayIntersectSphere(viewPos, dir, groundRadiusMM) >= 0.0) {
            sunLum *= 0.0;
        } else {
            // If the sun value is applied to this pixel, we need to calculate the transmittance to obscure it.
        	sunLum *= getValFromTLUT(source_transmittance, tLUTRes, viewPos, disk_sun_dir());
		}
    }
    col += sunLum;
	col = moon_body(dir, col);
	// Moon halo (P1): tight scatter glow + faint wide aureole, night-gated
	// (daylight washes it out anyway) and phase-scaled via moon_params.x.
	if (moon_params.z > 0.001 && night_amount > 0.001) {
		float md = max(dot(dir, normalize(moon_dir)), 0.0);
		float halo = pow(md, 400.0) * 0.10 + pow(md, 40.0) * 0.012;
		col += vec3(0.55, 0.60, 0.72) * halo * moon_params.z * night_amount
				* (0.25 + 0.75 * moon_params.x);
	}
	return col;
}

// --- High ice layer noise (cheap value-noise fBm + Worley cells) ---
// (h21/vnoise/fbm live above moon_body — the moon maria reuse them.)
// Worley F1 distance — small value near a cell centre, ~1 at cell edges.
float worley(vec2 p) {
	vec2 ip = floor(p);
	vec2 fp = fract(p);
	float d = 1.5;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = vec2(h21(ip + g), h21(ip + g + vec2(31.4, 17.7)));
			vec2 r = g + o - fp;
			d = min(d, dot(r, r));
		}
	}
	return sqrt(d);
}

// The high ice deck. Returns the lit cloud colour (rgb) and a coverage
// (a) to composite OVER the atmosphere but UNDER the volumetric clouds
// (which sit lower and occlude the ice). sdir = the true sun direction.
vec4 high_clouds(vec3 rayDir, vec3 sdir) {
	float amt = cirrus_amount + cirrostratus_amount + altocumulus_amount;
	if (amt < 0.001 || rayDir.y < 0.02) return vec4(0.0);

	// Pierce a flat sheet: p is the world-plane position where the ray
	// crosses the deck. As rayDir.y -> 0 the sheet compresses toward the
	// horizon (natural perspective foreshortening of distant cloud).
	vec2 p = rayDir.xz / rayDir.y * 8.0 + high_cloud_offset * 0.0004;
	p = clamp(p, vec2(-160.0), vec2(160.0));  // cap horizon blow-up (only the already-faded band)

	float cover = 0.0;
	float shade = 1.0;   // per-cell shading multiplier (altocumulus undersides)

	// Cirrostratus: broad smooth milky veil (the halo-bearing sheet).
	if (cirrostratus_amount > 0.001) {
		float v = fbm(p * 0.55 + 17.0);
		float cs = smoothstep(0.30, 0.72, v);
		cover = max(cover, cs * cirrostratus_amount * 0.65);
	}
	// Cirrus (sky.md §6 P3): the old single-axis anisotropic fBm rendered
	// every filament parallel to X — "a sky full of contrails". Real
	// fibratus/uncinus is PATCHY (bands with clear sky between), the
	// filament direction drifts across the dome, and fall-streaks bend
	// into hooks. Patch gate -> slowly-rotating local streak frame ->
	// shear warp that curves the filaments.
	if (cirrus_amount > 0.001) {
		float cpatch = smoothstep(0.36, 0.62, fbm(p * 0.13 + 31.0));
		if (cpatch > 0.003) {
			// Rotation drifts SLOWLY (fast variation swirled the filaments
			// into marbling) and the hook bend stays gentle — wind-combed
			// strands that curve, not squiggles.
			float ang = (fbm(p * 0.018 + 5.0) - 0.5) * 1.7;
			vec2 dirv = vec2(cos(ang), sin(ang));
			vec2 q = vec2(dot(p, dirv), dot(p, vec2(-dirv.y, dirv.x)));
			q.y += (fbm(p * 0.16 + 13.0) - 0.5) * 1.1;   // uncinus hook bend
			vec2 qa = vec2(q.x * 0.20, q.y * 1.5);
			// Soft fibrous sheet under the strands — bare hairline threads
			// read as cat-scratches; real fibratus is tufts with body.
			float cbody = smoothstep(0.44, 0.82, fbm(qa * 0.55 + 4.0));
			float r = fbm(qa * 0.95 + 4.0);
			float streak = smoothstep(0.48, 0.88, r);
			streak *= 0.50 + 0.50 * smoothstep(0.40, 0.85, fbm(qa * 3.6 + 1.0));
			cover = max(cover, min(1.0, cbody * 0.34 + streak * 0.66)
					* cpatch * cirrus_amount * 0.60);
		}
	}
	// Altocumulus: mackerel sky — cloudlets in wind-aligned rows (cloud
	// streets), domain-warped so they read as organic ripples, not a
	// uniform dot grid. Bigger-than-before cells, gaps of blue between
	// groups, soft edges.
	if (altocumulus_amount > 0.001) {
		// Domain warp breaks the regular Worley lattice into organic shapes
		// with cell-to-cell size variation.
		vec2 wp = p * 1.7 + 0.9 * vec2(fbm(p * 0.8 + 3.0), fbm(p * 0.8 + 8.0));
		float w = worley(wp);
		float cell = smoothstep(0.70, 0.10, w);
		// Mackerel rows: a directional ripple (cloud streets) wobbled by
		// noise so the bands meander rather than march in straight lines.
		vec2 rdir = vec2(0.80, 0.60);
		float ripple = 0.5 + 0.5 * sin(dot(p, rdir) * 3.1 + fbm(p * 1.1) * 4.0);
		float rows = mix(0.45, 1.0, smoothstep(0.30, 0.90, ripple));
		// Large patches of clear blue between cloud groups.
		float patch = smoothstep(0.40, 0.74, fbm(p * 0.40 + 9.0));
		float ac = cell * rows * patch * altocumulus_amount * 0.78;
		if (ac > cover) {
			// Cell centres bright (sunlit tops), gaps/edges shaded undersides.
			shade = 0.50 + 0.50 * smoothstep(0.60, 0.05, w);
		}
		cover = max(cover, ac);
	}
	if (cover < 0.001) return vec4(0.0);

	// Fade the compressed sheet near the horizon (avoids an aliased band).
	cover *= smoothstep(0.02, 0.16, rayDir.y);

	// Lighting: lift the sun to the deck's horizon (~+4 deg dip at ~8 km)
	// so the ice stays sunlit ~20 min past ground sunset — the dusk pinks.
	// Sun colour through the atmosphere (reddens/dims when low) IS the
	// colour of light hitting the ice; the local sky LUT is the ambient.
	vec3 lifted = normalize(sdir + vec3(0.0, 0.07, 0.0));
	float lit = smoothstep(-0.14, 0.06, lifted.y) * shade;
	vec3 sun_col = getValFromTLUT(source_transmittance, tLUTRes, viewPos, sdir);
	vec3 lit_col = sun_col * high_cloud_gain * vec3(0.95, 0.97, 1.03);
	vec3 sky_here = getValFromSkyLUT(rayDir);
	vec3 col = mix(sky_here * 0.85, lit_col, lit);
	return vec4(col, clamp(cover, 0.0, 1.0));
}

void sky() {
	vec3 norm = EYEDIR;
	norm.y = max(0.0, norm.y);
	norm = normalize(norm);

	norm.xz = vec3_to_oct(norm.xzy);
	vec4 blend_from = textureLod(blend_from_texture, norm.xz, 0.0);
	vec4 blend_to = textureLod(blend_to_texture, norm.xz, 0.0);
	vec4 clouds = mix(blend_from, blend_to, blend_amount);
	vec3 background = get_atmo(EYEDIR);

	// High ice layer (sky.md P2) sits above the volumetric shell: composite
	// it onto the atmosphere first, then let the volumetric clouds occlude
	// it. A veil crossing the sun dims the disk (and glows — halo-ready).
	vec4 ice = high_clouds(EYEDIR, disk_sun_dir());
	background = background * (1.0 - ice.a) + ice.rgb * ice.a;

	// Sunset/sunrise: volumetric clouds blaze with warm colors when sun is
	// low. Keyed on the celestial sun (crosses the horizon, 2026-06-11) —
	// peaks at elev 0 to -4 deg where the reference pinks live, fades out
	// by -8 deg (clouds past the terminator go grey-mauve).
	// Blaze keys on the TRUE sun (celestial blends to the moon at night)
	vec3 sdir = disk_sun_dir();
	float sun_elev = sdir.y;
	float golden = smoothstep(0.25, -0.02, sun_elev) * smoothstep(-0.14, -0.06, sun_elev);
	if (golden > 0.01 && clouds.a > 0.01) {
		float sun_dot_c = dot(normalize(EYEDIR), sdir);
		// Sunward clouds: deep orange to crimson
		float sun_face = pow(max(sun_dot_c, 0.0), 1.5);
		vec3 blaze = mix(vec3(1.2, 0.55, 0.18), vec3(1.0, 0.30, 0.10), golden);
		clouds.rgb += blaze * sun_face * golden * clouds.a * 0.45;
		// Anti-sun clouds: salmon-pink (scattered skylight; reference dusk
		// frames show pink across the WHOLE dome, not just sunward)
		float anti_face = pow(max(-sun_dot_c, 0.0), 2.0);
		clouds.rgb += vec3(0.55, 0.28, 0.38) * anti_face * golden * clouds.a * 0.40;
		// Overall warm shift on all clouds at golden hour
		clouds.rgb *= mix(vec3(1.0), vec3(1.20, 0.90, 0.72), golden * 0.22);  // toned: clouds are already sun-tinted in compute
		// Bright rim on backlit cloud edges
		float rim = pow(max(sun_dot_c, 0.0), 4.0);
		clouds.rgb += LIGHT0_COLOR * rim * golden * 0.25;
		// Deep sunset: clouds shift salmon-pink at the very end (reference
		// dusk undersides are pink, not brown-red; scaled by the golden
		// gate so it fades out with everything else past the terminator)
		float deep = smoothstep(-0.02, -0.10, sun_elev);
		clouds.rgb += vec3(0.32, 0.10, 0.14) * deep * clamp(golden * 2.0, 0.0, 1.0) * clouds.a * 0.40;
	}

	COLOR = background * (1.0-clouds.a) + clouds.xyz;
	// Horizon blend (sky.md §6 P4): was smoothstep(0.6, 1.0, ..) — that
	// erased ALL volumetric cloud below ~24 deg elevation, so decks never
	// stacked at the skyline (a big "not a real sky" tell). Keep only a
	// slim band above the true horizon to mask the octahedral-map edge +
	// grazing-ray undersample (the compute side already fades 0-3 deg and
	// scales its step count for long horizon paths).
	COLOR = mix(clamp(COLOR, vec3(0.0), vec3(100.0)), clamp(background, vec3(0.0), vec3(100.0)), smoothstep(0.92, 1.0, 1.0 - EYEDIR.y));
}

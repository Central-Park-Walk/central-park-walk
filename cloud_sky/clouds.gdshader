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
uniform vec3 celestial_dir = vec3(0.0);
uniform float sun_disk_scale = 1.0;
uniform float sun_disk_hdr_brightness : hint_range(0.0, 100.0, 0.01) = 5.0;
uniform float sun_disk_hdr_attenuation : hint_range(1.0, 10.0, 0.01) = 1.0;

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

// https://www.shadertoy.com/view/slSXRW
vec3 sunWithBloom(vec3 rayDir, vec3 sunDir) {
    float sunSolidAngle = sun_disk_scale * 0.53*PI/180.0;
    float minSunCosTheta = cos(sunSolidAngle);

    float cosTheta = dot(rayDir, sunDir);
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

vec3 get_atmo(vec3 dir) {
	vec3 col = getValFromSkyLUT(dir);
	vec3 sunLum = sunWithBloom(dir, sun_dir());
    if (length(sunLum) > 0.0) {
        if (rayIntersectSphere(viewPos, dir, groundRadiusMM) >= 0.0) {
            sunLum *= 0.0;
        } else {
            // If the sun value is applied to this pixel, we need to calculate the transmittance to obscure it.
        	sunLum *= getValFromTLUT(source_transmittance, tLUTRes, viewPos, sun_dir());
		}
    }
    col += sunLum;
	return col;
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

	// Sunset/sunrise: volumetric clouds blaze with warm colors when sun is
	// low. Keyed on the celestial sun (crosses the horizon, 2026-06-11) —
	// peaks at elev 0 to -4 deg where the reference pinks live, fades out
	// by -8 deg (clouds past the terminator go grey-mauve).
	vec3 sdir = sun_dir();
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
		clouds.rgb *= mix(vec3(1.0), vec3(1.20, 0.90, 0.72), golden * 0.40);
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
	COLOR = mix(clamp(COLOR, vec3(0.0), vec3(100.0)), clamp(background, vec3(0.0), vec3(100.0)), smoothstep(0.6, 1.0, 1.0 - EYEDIR.y));
}

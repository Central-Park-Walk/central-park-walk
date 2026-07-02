#[compute]
#version 450

// Invocations in the (x, y, z) dimension
layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

// Our textures
layout(rgba16f, set = 0, binding = 0) uniform restrict writeonly image2D current_image;

layout(set = 1, binding = 0) uniform sampler3D large_scale_noise;
layout(set = 1, binding = 1) uniform sampler3D small_scale_noise;
layout(set = 1, binding = 2) uniform sampler2D weather_noise;
// Second weather map for crossfading between weather states (sky.md P1):
// weather_at() lerps noise->noise_b by weather_mix so fronts ARRIVE over
// minutes instead of the sky popping when the state machine switches.
layout(set = 1, binding = 3) uniform sampler2D weather_noise_b;

layout(set = 2, binding = 0) uniform sampler2D sky_lut;
// Sun transmittance LUT (256x64: u = 0.5+0.5*cosZenith, v = altitude
// fraction of the 100 km column) — the twilight underside term samples it
// at cloud altitude (sky.md §6 P5).
layout(set = 2, binding = 1) uniform sampler2D transmittance_lut;

// Our push constant.
// Push constants have a max size of 128 bytes (32 floats).
layout(push_constant, std430) uniform Params {
	vec2 texture_size;
	vec2 update_position;

	vec2 cloud_pos;
	vec2 detailed_pos;

	vec2 weather_pos;
	vec2 noise_offset;  // random per-session offset for cloud shape variety

	vec4 ground_color;

	vec3 LIGHT_DIRECTION;
	float LIGHT_ENERGY;

	vec3 LIGHT_COLOR;
	float time;

	float noise_offset_z;  // third axis offset
	float density;
	float cloud_coverage;
	float time_offset;

	float sun_scale;      // calibration: direct-sun term multiplier
	float ambient_scale;  // calibration: sky/ground ambient multiplier
	float weather_mix;    // 0 = weather_noise, 1 = weather_noise_b
	float dither_index;   // temporal index for the blue-noise raymarch dither (was pad3)
} params;

// Approximately earth sizes
const float g_radius = 6000000.0; //ground radius
const float sky_b_radius = 6001500.0;//bottom of cloud layer
const float sky_t_radius = 6004000.0;//top of cloud layer

const float PI = 3.141592;

vec3 getValFromSkyLUT(vec3 rayDir) {
	vec2 uv;
	float phi = atan(rayDir.z, rayDir.x);
    float theta = asin(rayDir.y);
	uv.x = (phi / PI * 0.5 + 0.5);
    // Undo the non-linear transformation from the sky-view LUT
    uv.y = sqrt(abs(theta) / (PI * 0.5)) * sign(theta) * 0.5 + 0.5;
    return texture(sky_lut, uv).rgb;
}

// Interleaved Gradient Noise (Jimenez) — a blue-noise-like dither for the
// raymarch start offset. Distributes the step pattern across neighbouring
// pixels far better than a white-noise hash, so the slab no longer bands.
// The dither_index term (advanced once per sky-texture build) animates it so
// the 3-texture temporal blend averages residual structure out.
float interleaved_gradient_noise(vec2 px) {
	px += 5.588238 * params.dither_index;
	return fract(52.9829189 * fract(0.06711056 * px.x + 0.00583715 * px.y));
}

// Utility function that maps a value from one range to another. 
float remap(float originalValue,  float originalMin,  float originalMax,  float newMin,  float newMax) {
	return newMin + (((originalValue - originalMin) / (originalMax - originalMin)) * (newMax - newMin));
}

// Phase function
float henyey_greenstein(float cos_theta, float g) {
	const float k = 0.0795774715459;
	return k * (1.0 - g * g) / (pow(1.0 + g * g - 2.0 * g * cos_theta, 1.5));
}

float GetHeightFractionForPoint(float inPosition) { 
	float height_fraction = (inPosition -  sky_b_radius) / (sky_t_radius - sky_b_radius); 
	return clamp(height_fraction, 0.0, 1.0);
}

// Height-density profiles in RESCALED hf (height / weather.g tower).
// Since the tower-height fix, weather.g owns cloud THICKNESS — these
// profiles only shape base/top edge character. Schneider's originals were
// authored for the unrescaled 2.5 km layer; under rescaling the stratus
// profile (0.02-0.11) squeezed an overcast deck into a ~60 m paper sheet.
// Stratus: flat fill, hard base and top (featureless veil). Stratocumulus:
// lumpy top. Cumulus: domed top, fills the column (unchanged).
vec4 mixGradients(float cloudType){
	const vec4 STRATUS_GRADIENT = vec4(0.0f, 0.06f, 0.82f, 0.94f);
	const vec4 STRATOCUMULUS_GRADIENT = vec4(0.0f, 0.12f, 0.62f, 0.85f);
	const vec4 CUMULUS_GRADIENT = vec4(0.01f, 0.0625f, 0.78f, 1.0f);
	float stratus = 1.0f - clamp(cloudType * 2.0f, 0.0, 1.0);
	float stratocumulus = 1.0f - abs(cloudType - 0.5f) * 2.0f;
	float cumulus = clamp(cloudType - 0.5f, 0.0, 1.0) * 2.0f;
	return STRATUS_GRADIENT * stratus + STRATOCUMULUS_GRADIENT * stratocumulus + CUMULUS_GRADIENT * cumulus;
}

float densityHeightGradient(float heightFrac, float cloudType) {
	vec4 cloudGradient = mixGradients(cloudType);
	return smoothstep(cloudGradient.x, cloudGradient.y, heightFrac) - smoothstep(cloudGradient.z, cloudGradient.w, heightFrac);
}

float intersectSphere(vec3 pos, vec3 dir,float r) {
    float a = dot(dir, dir);
    float b = 2.0 * dot(dir, pos);
    float c = dot(pos, pos) - (r * r);
	float d = sqrt((b*b) - 4.0*a*c);
	float p = -b - d;
	float p2 = -b + d;
    return max(p, p2) / (2.0 * a);
}

// World-space wind offset shared by the weather envelope, base noise and
// detail noise (2026-06-11 flow fix). Before, three drift rates coexisted
// (envelope 16.7x wind, base 12x, detail -40x) so clouds churned through
// their own shapes instead of riding the wind. One offset = shapes move
// with their envelopes. cloud_pos integrates wind_speed (true m/s at
// cloud altitude, set by main.gd) — this IS meters of drift, factor 1.
// params.detailed_pos stays in the push constant for layout stability but
// is no longer read; params.weather_pos now carries the per-session
// random weather-map origin (see weather_at).
vec2 wind_world() {
	return params.cloud_pos;
}

// Single source of truth for weather sampling — the light march previously
// omitted the drift offset on its distant sample, shading against a stale
// weather field. weather_pos carries the per-session random map origin
// (without it every launch shows the same formation in the same place).
vec3 weather_at(vec3 p) {
	const float weather_scale = 0.00006;
	vec2 uv = (p.xz + wind_world()) * weather_scale + 0.5 + params.weather_pos;
	return mix(texture(weather_noise, uv).xyz,
			texture(weather_noise_b, uv).xyz, params.weather_mix);
}

// Returns density at a given point
// Heavily based on method from Schneider
float density(vec3 pip, vec3 weather, float mip) {
	vec3 p = pip;
	float height_fraction = GetHeightFractionForPoint(length(p));
	// Tower height (weather.g, 2026-06-11 marshmallow fix): fraction of
	// the layer this column's cloud top reaches. Rescaling the height
	// fraction gives every cell a flat shared base at the condensation
	// level and a per-column domed top — fair-weather cumulus is wider
	// than tall (~3:1). Without it every cell extruded through the full
	// 2.5 km layer as a vertical pill.
	float tower = max(weather.g, 0.03);
	float hf = height_fraction / tower;
	if (hf >= 1.0) {
		return 0.0;
	}
	// Per-session random offset — shifts noise sampling only, not altitude
	p += vec3(params.noise_offset.x, params.noise_offset_z, params.noise_offset.y) * 50000.0;

	// Wind: same world offset as the weather envelope.
	p.xz += wind_world();

	// Define the base of the cloud. 0.00018 puts the perlin-worley lobes
	// at ~hundreds of meters against 1-3 km cells (cauliflower); the old
	// 0.00008 (12.5 km wavelength) barely varied across a cell, leaving
	// the soft weather-map disc as the silhouette (smooth extruded sides).
	// (0.00025 fragmented too much — whole cells fell below the coverage
	// threshold and the noon dome emptied out.)
	vec4 n = textureLod(large_scale_noise, p.xyz * 0.00018, mip - 2.0);
	float fbm = n.g * 0.625 + n.b * 0.25 + n.a * 0.125;

	// Remap based on weather, coverage, and cloud shape gradient.
	float g = densityHeightGradient(hf, weather.r);
	float base_cloud = remap(n.r, -(1.0 - fbm), 1.0, 0.0, 1.0);
	float weather_coverage = params.cloud_coverage * weather.b;
	base_cloud = remap(base_cloud * g, 1.0 - (weather_coverage), 1.0, 0.0, 1.0);
	base_cloud *= weather_coverage;

	// Detail rides with the base (zero horizontal slip); shape evolution
	// comes from a slow vertical boil. Real thermal updrafts are m/s
	// scale — the old 40 m/s churned a cloud's whole texture in seconds.
	p.y -= params.time * 5.0;

	// Curl-style flow distortion of the detail lookup (Schneider): a coarse,
	// slowly-varying noise vector swirls the high-frequency erosion off-axis
	// so cloud edges tear into wisps instead of staying rounded. Weighted by
	// hf so it is strongest near the top, where real cumulus shears into
	// cauliflower/wisps; the flat condensation base stays crisp. (Approximate
	// curl — reuses the bound Perlin-Worley volume, no extra texture binding.)
	vec3 curl = textureLod(large_scale_noise, p * 0.00002, 0.0).rgb * 2.0 - 1.0;
	p += curl * 140.0 * hf;

	// Detailed texture.
	vec3 hn = textureLod(small_scale_noise, p * 0.001, mip).rgb;
	float hfbm = hn.r * 0.625 + hn.g * 0.25 + hn.b * 0.125;
	hfbm = mix(hfbm, 1.0 - hfbm, clamp(hf * 4.0, 0.0, 1.0));
	// Erosion floor 0.15 nibbles silhouette edges at every height (buns had
	// untouched smooth rims); the hf term still tears tops hardest while
	// the flat condensation base stays near-crisp (sky.md §6 P2).
	base_cloud = remap(base_cloud, hfbm * (0.15 + 0.50 * hf), 1.0, 0.0, 1.0);
	return pow(clamp(base_cloud, 0.0, 1.0), (1.0 - hf) * 0.8 + 0.5);
}

vec4 march(vec3 pos,  vec3 end, vec3 dir, int depth, float jitter) {
	const vec3 RANDOM_VECTORS[6] = {vec3( 0.38051305f,  0.92453449f, -0.02111345f),vec3(-0.50625799f, -0.03590792f, -0.86163418f),vec3(-0.32509218f, -0.94557439f,  0.01428793f),vec3( 0.09026238f, -0.27376545f,  0.95755165f),vec3( 0.28128598f,  0.42443639f, -0.86065785f),vec3(-0.16852403f,  0.14748697f,  0.97460106f)};

	// Initialize ray length, direction, and position.
	float ss = length(dir);
	dir = normalize(dir);
	vec3 p = pos + dir * jitter * ss;

	// Initialize light ray.
	const float t_dist = sky_t_radius - sky_b_radius;
	float lss = (t_dist / 64.0);
	vec3 ldir = normalize(params.LIGHT_DIRECTION);

	float t = 1.0;
	float T = 1.0;
	float alpha = 0.0;
	vec3 L = vec3(0.0);
	

	float costheta = dot(ldir, dir);
	// Per-octave phase values are constant along the ray — precompute
	// (the multi-scatter loop below would otherwise re-evaluate 9 HG
	// lobes per lit sample).
	vec3 ms_phase;
	float pc = 1.0;
	for (int k = 0; k < 3; k++) {
		ms_phase[k] = max(max(
			henyey_greenstein(costheta, clamp(0.6 * pc, -0.99, 0.99)),
			henyey_greenstein(costheta, clamp((0.4 - 1.4 * ldir.y) * pc, -0.99, 0.99))),
			henyey_greenstein(costheta, clamp(-0.2 * pc, -0.99, 0.99)));
		pc *= 0.7;
	}

	// Read sun and ambient colors from the sky LUT. sun_scale/ambient_scale
	// are calibration multipliers (1.0 = upstream demo behavior) — see
	// docs/rendering.md sky calibration.
	// Clouds at ~2 km altitude see the sun ~2 deg past ground sunset
	// (horizon dip + refraction) — sample the sun LUT slightly lifted so
	// undersides stay lit (the reference pinks/corals) through civil
	// twilight instead of cutting to black with the ground (2026-06-11).
	vec3 sun_lut_dir = params.LIGHT_DIRECTION + vec3(0.0, 0.035, 0.0);
	// The +2 deg dip lift is not enough past sun -2 deg: the lifted sample
	// drops into the LUT's BELOW-horizon half (ground rays, near-black), so
	// undersides cut to black in the middle of the reference pink window
	// (sky.md §6 P5). Keep the sample on the sky side through the march
	// handover — the grazing sample carries the deep-red horizon colour and
	// the gd-side twilight window (cal_sun boost) owns the fade-out timing.
	if (params.LIGHT_DIRECTION.y > -0.20) {
		sun_lut_dir.y = max(sun_lut_dir.y, 0.012);
	}
	sun_lut_dir = normalize(sun_lut_dir);
	vec3 atmosphere_sun = getValFromSkyLUT(sun_lut_dir) * 0.1 * params.LIGHT_ENERGY * params.LIGHT_COLOR * params.sun_scale;
	vec3 atmosphere_ambient = getValFromSkyLUT(normalize(vec3(1.0, 1.0, 0.0))) * 0.05 * params.ambient_scale;
	atmosphere_ambient = mix(atmosphere_ambient, vec3(length(atmosphere_ambient)), 0.5); // interpolate towards white with this intensity.
	vec3 atmosphere_ground = getValFromSkyLUT(normalize(vec3(1.0, -1.0, 0.0))) * 5.0 * 0.05 * params.ambient_scale;
	atmosphere_ground = mix(atmosphere_ground, params.ground_color.rgb * vec3(length(atmosphere_ground)), 0.5); // interpolate towards ground color with this intensity.

	// Night lighting (sky.md §6 P0). The LUT terms above go to ~0 once the
	// real sun is below ~-14 deg, so the night factor (ground_color.a — the
	// push constant is otherwise full) blends in the two real night sources:
	// - moonlight: LIGHT_DIRECTION is the moon at night and LIGHT_ENERGY is
	//   already phase-scaled (~0.05 full moon, ~0.003 moonless floor), so
	//   this term self-scales with phase and vanishes when the moon is down;
	// - NYC city glow: the amber wash a lit city throws on cloud bases —
	//   phase-independent, the dominant light on overcast nights.
	// Twilight underside light (sky.md §6 P5). The sky-view LUT above is a
	// GROUND-observer product: its in-scatter dies with the ground sunset,
	// so the sun term cuts cloud undersides to black by sun -2 deg — but
	// the reference window (notes/refs/sky_2026_06_11) keeps pink/coral
	// undersides to sun ~-6 deg (2 km clouds see the sun longer, and the
	// glow feeding them comes from air further west that is still lit).
	// Same approximation family as the high ice deck in clouds.gdshader:
	// sample the sun TRANSMITTANCE at cloud altitude with a lifted sun —
	// hue (deep orange -> red -> gone) and fade-in ride the physics; the
	// window fade-out is art-directed to match the refs. Diagnosed by
	// channel-attribution flood: the term chain (beers/phase/march) was
	// healthy, the sky-LUT sample was the dead factor — no multiplier on
	// a zero could work (tmp/skydiag*).
	float tw_win = (1.0 - smoothstep(-0.025, 0.01, params.LIGHT_DIRECTION.y))
			* smoothstep(-0.14, -0.075, params.LIGHT_DIRECTION.y);
	if (tw_win > 0.001) {
		vec3 tw_dir = normalize(params.LIGHT_DIRECTION + vec3(0.0, 0.09, 0.0));
		vec2 t_uv = vec2(clamp(0.5 + 0.5 * tw_dir.y, 0.0, 1.0), 0.03);
		// The red channel of the grazing transmittance drives intensity and
		// fade timing (it dies as the lifted sun path drops into the earth);
		// hue is art-directed salmon (raw grazing T is blood-red — the refs'
		// pink is sunlight + blue skylight mixing). Scale anchor: a flood
		// test at 8.0 read as full bright; the window peak lands ~2.5.
		float tw_drive = texture(transmittance_lut, t_uv).r;
		atmosphere_sun += tw_drive * 10.0 * tw_win * vec3(1.0, 0.42, 0.42);
	}
	float night_f = params.ground_color.a;
	atmosphere_sun += night_f * vec3(0.75, 0.85, 1.05) * 0.6 * params.LIGHT_ENERGY * params.LIGHT_COLOR;
	// City glow tuned so cloud bases read ~2x BRIGHTER than the night-sky
	// LP dome behind them (NYC clouds catch the city — cloudy nights are
	// brighter than clear ones). Converged sweeps showed 0.02-0.032 lands
	// clouds AT sky level (silhouettes; the early "salmon" reading at
	// 0.036 was a stale-LUT capture artifact) — the ambient occlusion +
	// alpha compositing eat roughly half the term. Hue amber, not red.
	atmosphere_ground += night_f * vec3(0.070, 0.050, 0.026);
	atmosphere_ambient += night_f * vec3(0.012, 0.012, 0.014);
	
	for (int i = 0; i < depth; i++) {
		p += dir * ss;
		vec3 weather_sample = weather_at(p);
		float height_fraction = GetHeightFractionForPoint(length(p));

		t = density(p, weather_sample, 0.0);
		float dt = exp(-params.density * t * ss);

		vec3 lp = p;
		float lt = 1.0;
		float cd = 0.0;

		if (t > 0.0) { //calculate lighting, but only when we are in the cloud
			float lheight_fraction = 0.0;
			for (int j = 0; j < 6; j++) {
				lp +=  (ldir + RANDOM_VECTORS[j] * float(j)) * lss;
				lheight_fraction = GetHeightFractionForPoint(length(lp));
				vec3 lweather = weather_at(lp);
				lt = density(lp, lweather, float(j));
				cd += lt;
			}

			// Take a single distant sample
			lp = p + ldir * 18.0 * lss;
			lheight_fraction = GetHeightFractionForPoint(length(lp));
			vec3 lweather = weather_at(lp);
			lt = density(lp, lweather, 5.0);
			cd += lt;
			
			// Direct sun via multi-scattering octaves (Wrenninge/Schneider,
			// 2026-06-11 "lacks detail and depth"): each octave relaxes
			// extinction and phase anisotropy, the way real multiple
			// scattering floods light through dense cores. Replaces the
			// single-octave Beer x powder, which clamped thin regions to
			// black (no translucent edges, no silver lining) and dense
			// regions to a flat mid-grey.
			float tau = params.density * cd * lss * 3.0;
			float beers_total = 0.0;
			float ms_a = 1.0;  // octave contribution
			float ms_b = 1.0;  // octave extinction relax
			for (int k = 0; k < 3; k++) {
				beers_total += ms_a * exp(-tau * ms_b) * ms_phase[k];
				ms_a *= 0.45; ms_b *= 0.45;
			}
			// Powder (dark in-shadow crevices) belongs on front-lit views
			// only — applying it everywhere is what erased the backlit
			// translucent rim.
			// Powder weight peaks front-lit (sun behind viewer, costheta<0) and
			// vanishes back-lit (costheta>0) so the silver-lining rim survives.
			float powder_sugar_effect = 1.0 - exp(-tau * 2.0);
			beers_total *= 2.0 * mix(1.0, powder_sugar_effect,
					clamp(0.5 - 0.5 * costheta, 0.0, 1.0));

			// Ambient mixes ground->sky by position within the CLOUD, not
			// absolute layer height: with tower-capped shallow cumulus the
			// whole cloud sits in the bottom ~30% of the layer, and the old
			// absolute mix locked it to the dark ground term (grey clouds at
			// noon). A shallow cloud's top still sees the whole sky dome.
			// The exp() term occludes ambient with interior depth — dense
			// cores and under-bellies read deeper than wisps.
			float col_hf = clamp(height_fraction / max(weather_sample.g, 0.03), 0.0, 1.0);
			vec3 ambient = mix(atmosphere_ground, atmosphere_ambient, smoothstep(0.0, 1.0, col_hf))
					* (0.55 + 0.45 * exp(-tau * 0.6));
			alpha += (1.0 - dt) * (1.0 - alpha);
			vec3 radiance = (ambient + beers_total * atmosphere_sun) * t;
			L += T * (radiance - radiance * dt) / max(0.0000001, t);
			T *= dt;
			if (T < 0.01) { T = 0.0; break; }  // early ray termination once opaque
		}
	}
	alpha = clamp(alpha, 0.0, 1.0);
	return vec4(L, alpha);
}

// Take a direction as input and draw the sky.
vec4 sky(vec3 dir, float jitter) {
	vec4 col = vec4(0.0);

	if (dir.y > 0.0) {
		// Only draw clouds above the horizon.
		vec3 camPos = vec3(0.0, g_radius, 0.0);
		vec3 start = camPos + dir * intersectSphere(camPos, dir, sky_b_radius);
		vec3 end = camPos + dir * intersectSphere(camPos, dir, sky_t_radius);
		float shelldist = (length(end - start));
		// Step COUNT scales with the slab path length so the step SIZE stays
		// ~constant: grazing/horizon rays (long path through the 2.5 km slab)
		// get more steps instead of undersampling and banding, while
		// near-vertical rays keep ~128. Capped at 256 for the worst grazing.
		float steps = clamp(shelldist / 20.0, 128.0, 320.0);

		vec3 raystep = dir * shelldist / steps;
		col = march(start, end, raystep, int(steps), jitter);
		// Soft horizon fade: the deck dissolves into the distance instead of
		// terminating abruptly at dir.y==0 (also masks grazing-ray undersample).
		col *= smoothstep(0.0, 0.05, dir.y);
	} else {
		col = vec4(0.0);
	}

    return col;
}

vec2 oct_wrap(vec2 v) {
	vec2 signVal;
	signVal.x = v.x >= 0.0 ? 1.0 : -1.0;
	signVal.y = v.y >= 0.0 ? 1.0 : -1.0;
	return (1.0 - abs(v.yx)) * signVal;
}

// Hemisphere octahedral. Maximizes use of square texture.
// Adapted from https://johnwhite3d.blogspot.com/2017/10/signed-octahedron-normal-encoding.html
vec3 oct_to_vec3(vec2 e) {
	vec3 n;
	n.x = (e.x - e.y);
	n.y = (e.x + e.y) - 1.0;
	n.z = 1.0 - abs(n.x) - abs(n.y);
    n.xy = n.z >= 0.0 ? n.xy : oct_wrap( n.xy );

	return normalize(n);
}

void main() {
	// Calculate direction from pixel position.
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy) + ivec2(params.update_position);
	// Guard the ceil()-rounded dispatch against over-running the texture.
	if (pos.x >= int(params.texture_size.x) || pos.y >= int(params.texture_size.y)) return;
	vec2 uv = (vec2(pos) + 0.5) / params.texture_size;   // texel centre (half-texel fix)
	vec3 dir = oct_to_vec3(uv).xzy;

	// Blue-noise raymarch jitter, keyed on the absolute texel + temporal index.
	float jitter = interleaved_gradient_noise(vec2(pos));
	imageStore(current_image, pos, sky(dir, jitter));

}



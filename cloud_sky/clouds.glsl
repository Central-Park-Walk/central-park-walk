#[compute]
#version 450

// Invocations in the (x, y, z) dimension
layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

// Our textures
layout(rgba16f, set = 0, binding = 0) uniform restrict writeonly image2D current_image;

layout(set = 1, binding = 0) uniform sampler3D large_scale_noise;
layout(set = 1, binding = 1) uniform sampler3D small_scale_noise;
layout(set = 1, binding = 2) uniform sampler2D weather_noise;

layout(set = 2, binding = 0) uniform sampler2D sky_lut;

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
	vec2 pad3;            // keep push-constant size 16-byte aligned
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

// From: https://www.shadertoy.com/view/4sfGzS credit to iq
float hash(vec3 p) {
	p  = fract( p * 0.3183099 + 0.1 );
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
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

vec4 mixGradients(float cloudType){
	const vec4 STRATUS_GRADIENT = vec4(0.02f, 0.05f, 0.09f, 0.11f);
	const vec4 STRATOCUMULUS_GRADIENT = vec4(0.02f, 0.2f, 0.48f, 0.625f);
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
// with their envelopes. The 12.0 preserves the 2026-04-03 apparent-speed
// calibration (main.gd wind_speed = wlen * 0.6). params.detailed_pos /
// params.weather_pos stay in the push constant for layout stability but
// are no longer read.
vec2 wind_world() {
	return params.cloud_pos * 12.0;
}

// Single source of truth for weather sampling — the light march previously
// omitted the drift offset on its distant sample, shading against a stale
// weather field.
vec3 weather_at(vec3 p) {
	const float weather_scale = 0.00006;
	return texture(weather_noise, (p.xz + wind_world()) * weather_scale + 0.5).xyz;
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

	// Detailed texture.
	vec3 hn = textureLod(small_scale_noise, p * 0.001, mip).rgb;
	float hfbm = hn.r * 0.625 + hn.g * 0.25 + hn.b * 0.125;
	hfbm = mix(hfbm, 1.0 - hfbm, clamp(hf * 4.0, 0.0, 1.0));
	base_cloud = remap(base_cloud, hfbm * 0.45 * hf, 1.0, 0.0, 1.0);
	return pow(clamp(base_cloud, 0.0, 1.0), (1.0 - hf) * 0.8 + 0.5);
}

vec4 march(vec3 pos,  vec3 end, vec3 dir, int depth) {
	const vec3 RANDOM_VECTORS[6] = {vec3( 0.38051305f,  0.92453449f, -0.02111345f),vec3(-0.50625799f, -0.03590792f, -0.86163418f),vec3(-0.32509218f, -0.94557439f,  0.01428793f),vec3( 0.09026238f, -0.27376545f,  0.95755165f),vec3( 0.28128598f,  0.42443639f, -0.86065785f),vec3(-0.16852403f,  0.14748697f,  0.97460106f)};

	// Initialize ray length, direction, and position.
	float ss = length(dir);
	dir = normalize(dir);
	vec3 p = pos + dir * hash(pos * 10.0) * ss;

	// Initialize light ray.
	const float t_dist = sky_t_radius - sky_b_radius;
	float lss = (t_dist / 64.0);
	vec3 ldir = normalize(params.LIGHT_DIRECTION);

	float t = 1.0;
	float T = 1.0;
	float alpha = 0.0;
	vec3 L = vec3(0.0);
	

	float costheta = dot(ldir, dir);
	// Stack multiple phase functions to emulate some backscattering
	float phase = max(max(henyey_greenstein(costheta, 0.6), henyey_greenstein(costheta, (0.4 - 1.4 * ldir.y))), henyey_greenstein(costheta, -0.2));

	// Read sun and ambient colors from the sky LUT. sun_scale/ambient_scale
	// are calibration multipliers (1.0 = upstream demo behavior) — see
	// docs/rendering.md sky calibration.
	// Clouds at ~2 km altitude see the sun ~2 deg past ground sunset
	// (horizon dip + refraction) — sample the sun LUT slightly lifted so
	// undersides stay lit (the reference pinks/corals) through civil
	// twilight instead of cutting to black with the ground (2026-06-11).
	vec3 sun_lut_dir = normalize(params.LIGHT_DIRECTION + vec3(0.0, 0.035, 0.0));
	vec3 atmosphere_sun = getValFromSkyLUT(sun_lut_dir) * 0.1 * params.LIGHT_ENERGY * params.LIGHT_COLOR * params.sun_scale;
	vec3 atmosphere_ambient = getValFromSkyLUT(normalize(vec3(1.0, 1.0, 0.0))) * 0.05 * params.ambient_scale;
	atmosphere_ambient = mix(atmosphere_ambient, vec3(length(atmosphere_ambient)), 0.5); // interpolate towards white with this intensity.
	vec3 atmosphere_ground = getValFromSkyLUT(normalize(vec3(1.0, -1.0, 0.0))) * 5.0 * 0.05 * params.ambient_scale;
	atmosphere_ground = mix(atmosphere_ground, params.ground_color.rgb * vec3(length(atmosphere_ground)), 0.5); // interpolate towards ground color with this intensity.
	
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
			lt = pow(density(lp, lweather, 5.0), (1.0 - lheight_fraction) * 0.8 + 0.5);
			cd += lt;
			
			// captures the direct lighting from the sun
			float beers = exp(-params.density * cd * lss * 3.0);
			float powder_sugar_effect = 1.0 - exp(-params.density * cd * lss * 3.0 * 2.0);
			float beers_total = 2 * beers * powder_sugar_effect;

			// Ambient mixes ground->sky by position within the CLOUD, not
			// absolute layer height: with tower-capped shallow cumulus the
			// whole cloud sits in the bottom ~30% of the layer, and the old
			// absolute mix locked it to the dark ground term (grey clouds at
			// noon). A shallow cloud's top still sees the whole sky dome.
			float col_hf = clamp(height_fraction / max(weather_sample.g, 0.03), 0.0, 1.0);
			vec3 ambient = mix(atmosphere_ground, atmosphere_ambient, smoothstep(0.0, 1.0, col_hf));
			alpha += (1.0 - dt) * (1.0 - alpha);
			vec3 radiance = (ambient + beers_total * atmosphere_sun * phase) * t;
			L += T * (radiance - radiance * dt) / max(0.0000001, t);
			T *= dt;
		}
	}
	alpha = clamp(alpha, 0.0, 1.0);
	return vec4(L, alpha);
}

// Take a direction as input and draw the sky.
vec4 sky(vec3 dir) {
	vec4 col = vec4(0.0);

	if (dir.y > 0.0) {
		// Only draw clouds above the horizon.
		vec3 camPos = vec3(0.0, g_radius, 0.0);
		vec3 start = camPos + dir * intersectSphere(camPos, dir, sky_b_radius);
		vec3 end = camPos + dir * intersectSphere(camPos, dir, sky_t_radius);
		float shelldist = (length(end - start));
		// Take fewer steps towards horizon
		float steps = 128.0;

		vec3 raystep = dir * shelldist / steps;
		col = march(start, end, raystep, int(steps));
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
	vec2 uv = vec2(pos) / params.texture_size;
	vec3 dir = oct_to_vec3(uv).xzy;
	
	imageStore(current_image, pos, sky(dir));

}



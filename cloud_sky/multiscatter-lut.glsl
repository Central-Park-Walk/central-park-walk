#[compute]
#version 450

// Multiple-scattering LUT (Hillaire 2020, "A Scalable and Production Ready Sky
// and Atmosphere Rendering Technique"). Parameterised by (sun cos-zenith,
// altitude) exactly like the transmittance LUT, so sky-lut.glsl can sample it
// with the same uv. Stores the multiscattering transfer Psi_ms in the same
// spectral vec4 space (630/560/490/430 nm) as the rest of the model.
// Computed once at init (atmosphere params are static).

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(rgba16f, set = 0, binding = 0) uniform restrict writeonly image2D current_image;
layout(set = 1, binding = 0) uniform sampler2D transmittance_lut;

layout(push_constant, std430) uniform Params {
	vec2 texture_size;
	vec2 pad;
} params;

const float PI = 3.14159265358979323846;
const float INV_4PI = 0.25 / PI;
const float PHASE_ISOTROPIC = INV_4PI;

const float EARTH_RADIUS = 6371.0;          // km — must match sky-lut.glsl
const float ATMOSPHERE_THICKNESS = 100.0;   // km
const float ATMOSPHERE_RADIUS = EARTH_RADIUS + ATMOSPHERE_THICKNESS;
const vec4  GROUND_ALBEDO = vec4(0.3);

// --- atmosphere coefficients (identical to sky-lut.glsl) ---
const vec4 molecular_scattering_coefficient_base = vec4(6.605e-3, 1.067e-2, 1.842e-2, 3.156e-2);
const vec4 ozone_absorption_cross_section = vec4(3.472e-21, 3.914e-21, 1.349e-21, 11.03e-23) * 1e-4f;
const float ozone_mean_monthly_dobson = 350.0;
const vec4 aerosol_absorption_cross_section = vec4(2.8722e-24, 4.6168e-24, 7.9706e-24, 1.3578e-23);
const vec4 aerosol_scattering_cross_section = vec4(1.5908e-22, 1.7711e-22, 2.0942e-22, 2.4033e-22);
const float aerosol_base_density = 1.3681e20;
const float aerosol_background_density = 2e6;
const float aerosol_height_scale = 0.73;
const float aerosol_background_divided_by_base_density = aerosol_background_density / aerosol_base_density;

// Sphere-integration sampling
const int SQRT_SAMPLES = 8;                 // -> 64 directions
const int MS_STEPS = 20;

float ray_sphere_intersection(vec3 ro, vec3 rd, float radius) {
	float b = dot(ro, rd);
	float c = dot(ro, ro) - radius*radius;
	if (c > 0.0 && b > 0.0) return -1.0;
	float d = b*b - c;
	if (d < 0.0) return -1.0;
	if (d > b*b) return (-b + sqrt(d));
	return (-b - sqrt(d));
}

vec4 get_molecular_scattering_coefficient(float h) {
	return molecular_scattering_coefficient_base * exp(-0.07771971 * pow(h, 1.16364243));
}
vec4 get_molecular_absorption_coefficient(float h) {
	h += 1e-4;
	float t = log(h) - 3.22261;
	float density = 3.78547397e20 * (1.0 / h) * exp(-t * t * 5.55555555);
	return ozone_absorption_cross_section * ozone_mean_monthly_dobson * density;
}
float get_aerosol_density(float h) {
	return aerosol_base_density * (exp(-h / aerosol_height_scale) + aerosol_background_divided_by_base_density);
}
void get_collision(in float h, out vec4 scattering, out vec4 extinction) {
	h = max(h, 0.0);
	float ad = get_aerosol_density(h);
	vec4 aero_abs = aerosol_absorption_cross_section * ad;
	vec4 aero_scat = aerosol_scattering_cross_section * ad;
	vec4 mol_abs = get_molecular_absorption_coefficient(h);
	vec4 mol_scat = get_molecular_scattering_coefficient(h);
	scattering = aero_scat + mol_scat;
	extinction = aero_abs + aero_scat + mol_abs + mol_scat;
}
vec4 transmittance_from_lut(float cos_theta, float normalized_altitude) {
	float u = clamp(cos_theta * 0.5 + 0.5, 0.0, 1.0);
	float v = clamp(normalized_altitude, 0.0, 1.0);
	return texture(transmittance_lut, vec2(u, v));
}

// Integrate single scattering (white, uniform-phase, sun-illuminated) and the
// scattering transfer along one direction. Returns L (2nd-order radiance) in
// .rgb-style vec4 and accumulates fms (transfer) via the out param.
vec4 integrate_direction(vec3 ro, vec3 dir, vec3 sun_dir, out vec4 fms) {
	fms = vec4(0.0);
	float atmos_dist = ray_sphere_intersection(ro, dir, ATMOSPHERE_RADIUS);
	float ground_dist = ray_sphere_intersection(ro, dir, EARTH_RADIUS);
	float t_max = (ground_dist > 0.0) ? ground_dist : atmos_dist;
	if (t_max <= 0.0) return vec4(0.0);

	float dt = t_max / float(MS_STEPS);
	vec4 L = vec4(0.0);
	vec4 throughput = vec4(1.0);

	for (int i = 0; i < MS_STEPS; ++i) {
		float t = (float(i) + 0.5) * dt;
		vec3 x = ro + dir * t;
		float r = length(x);
		float alt = r - EARTH_RADIUS;
		float alt_n = alt / ATMOSPHERE_THICKNESS;
		vec3 up = x / r;
		float sun_cos = dot(up, sun_dir);

		vec4 scattering, extinction;
		get_collision(alt, scattering, extinction);

		vec4 T_sun = transmittance_from_lut(sun_cos, alt_n);
		vec4 step_T = exp(-dt * extinction);

		// Single scatter from the sun, uniform phase, white sun illuminance.
		vec4 S = scattering * PHASE_ISOTROPIC * T_sun;
		L += throughput * (S - S * step_T) / max(extinction, 1e-7);
		// Multiscatter transfer: integral of scattering * throughput.
		fms += throughput * (scattering - scattering * step_T) / max(extinction, 1e-7);
		throughput *= step_T;
	}

	// Ground bounce (Lambertian) for directions that hit the planet.
	if (ground_dist > 0.0) {
		vec3 hit = ro + dir * ground_dist;
		vec3 up = normalize(hit);
		float sun_cos = dot(up, sun_dir);
		vec4 T_sun = transmittance_from_lut(sun_cos, 0.0);
		L += throughput * T_sun * max(sun_cos, 0.0) * (GROUND_ALBEDO / PI);
	}
	return L;
}

void main() {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
	if (pos.x >= int(params.texture_size.x) || pos.y >= int(params.texture_size.y)) return;
	vec2 uv = (vec2(pos) + 0.5) / params.texture_size;

	float sun_cos_zenith = uv.x * 2.0 - 1.0;
	float altitude = uv.y * ATMOSPHERE_THICKNESS;
	vec3 ro = vec3(0.0, 0.0, EARTH_RADIUS + altitude);
	vec3 sun_dir = vec3(sqrt(clamp(1.0 - sun_cos_zenith * sun_cos_zenith, 0.0, 1.0)), 0.0, sun_cos_zenith);

	vec4 L_sum = vec4(0.0);
	vec4 fms_sum = vec4(0.0);
	const float inv_n = 1.0 / float(SQRT_SAMPLES * SQRT_SAMPLES);
	for (int i = 0; i < SQRT_SAMPLES; ++i) {
		for (int j = 0; j < SQRT_SAMPLES; ++j) {
			float a = (float(i) + 0.5) / float(SQRT_SAMPLES);
			float b = (float(j) + 0.5) / float(SQRT_SAMPLES);
			float theta = 2.0 * PI * a;            // azimuth
			float phi = acos(1.0 - 2.0 * b);       // uniform-area polar
			float sp = sin(phi);
			vec3 wi = vec3(sp * cos(theta), sp * sin(theta), cos(phi));
			vec4 fms;
			L_sum += integrate_direction(ro, wi, sun_dir, fms);
			fms_sum += fms;
		}
	}
	// Uniform-phase sphere integral: the 4pi and 1/4pi cancel, leaving the mean.
	vec4 L_2nd = L_sum * inv_n;
	vec4 f_ms = fms_sum * inv_n;
	vec4 psi = L_2nd / max(vec4(1.0) - f_ms, vec4(1e-4));   // infinite-scattering series

	imageStore(current_image, pos, psi);
}

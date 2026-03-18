// Shared hash and value noise functions.
// Used by terrain, stone, facade, path, tree_bark, imagine_mosaic, water shaders.

float hash2(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 43.21);
	return fract(p.x * p.y);
}
float vnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash2(i), hash2(i+vec2(1.,0.)), u.x),
	           mix(hash2(i+vec2(0.,1.)), hash2(i+vec2(1.,1.)), u.x), u.y);
}
float fbm3(vec2 p) {
	return vnoise(p) * 0.5 + vnoise(p * 2.13) * 0.3 + vnoise(p * 4.57) * 0.2;
}

// Cloud shadow: project world position onto cloud plane along sun direction,
// sample matching noise to darken ground under clouds.
// cloud_coverage/cloud_speed/cloud_time are global uniforms set by main.gd.
float cloud_shadow(vec2 world_xz, float cloud_coverage_val, float cloud_speed_val,
                   float time_val, vec2 wind_val) {
	// Project onto cloud dome (same UV calculation as sky shader)
	vec2 cloud_uv = world_xz * 0.00016;  // world scale → cloud UV scale
	vec2 drift = vec2(cloud_speed_val, cloud_speed_val * 0.7) + wind_val * 0.002;
	cloud_uv += time_val * drift;
	// Match sky shader FBM (simplified — 3 octaves for performance)
	float n = vnoise(cloud_uv * 3.0) * 0.5
	        + vnoise(cloud_uv * 6.0) * 0.3
	        + vnoise(cloud_uv * 12.0) * 0.2;
	float shadow = smoothstep(1.0 - cloud_coverage_val - 0.05,
	                          1.0 - cloud_coverage_val + 0.15, n);
	return shadow * 0.25;  // subtle: 0-25% darkening under clouds
}

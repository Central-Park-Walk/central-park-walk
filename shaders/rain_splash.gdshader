shader_type spatial;
render_mode blend_add, depth_draw_never, cull_disabled, unshaded, particle_billboard;

// Expanding splash ring — billboard quad that fades from center outward.
// Particle lifetime drives the ring expansion via COLOR.a from the process material.

uniform vec4 splash_color : source_color = vec4(0.75, 0.78, 0.88, 0.5);

void fragment() {
	vec2 uv = UV * 2.0 - 1.0;
	float r = length(uv);

	// Ring shape: hollow center, visible band, fading edge
	// As particle ages, COLOR.a decreases → ring fades out
	float ring = smoothstep(0.9, 0.6, r) * smoothstep(0.1, 0.35, r);

	// Soft outer glow
	float glow = exp(-r * r * 3.0) * 0.15;

	float alpha = (ring + glow) * COLOR.a * splash_color.a;
	ALBEDO = splash_color.rgb;
	ALPHA = alpha;
}

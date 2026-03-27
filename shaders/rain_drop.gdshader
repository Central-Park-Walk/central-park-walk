shader_type spatial;
render_mode blend_add, depth_draw_never, cull_disabled, unshaded, particle_billboard;

// Soft oblong raindrop — rounded teardrop silhouette with refraction core.
// Applied to elongated QuadMesh billboard particles.

uniform vec4 drop_color : source_color = vec4(0.7, 0.75, 0.85, 0.25);
uniform float core_brightness : hint_range(0.0, 1.0) = 0.35;

void fragment() {
	// Center UV at origin
	vec2 uv = UV * 2.0 - 1.0;

	// Teardrop taper: narrower at trailing edge (top, uv.y > 0),
	// wider at leading edge (bottom, uv.y < 0)
	float taper = 1.0 + uv.y * 0.3;
	uv.x *= taper;

	// Elliptical distance — X squeezed tighter for oblong shape
	float dx = uv.x * 2.2;
	float dy = uv.y * 1.0;
	float dist = dx * dx + dy * dy;

	// Soft rounded edge
	float alpha = smoothstep(1.0, 0.2, dist) * drop_color.a;

	// Bright refraction core — off-center highlight like light through water
	vec2 core_offset = vec2(0.15, -0.2);
	float core_dist = dot(uv - core_offset, uv - core_offset);
	float core = exp(-core_dist * 12.0) * core_brightness;

	ALBEDO = drop_color.rgb + vec3(core);
	ALPHA = alpha;
}

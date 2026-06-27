shader_type spatial;
// Fireflies as a single MultiMesh (one draw call). The flash pulse is computed on
// the CPU (it already rewrites per-instance data every frame) and handed in via
// INSTANCE_CUSTOM.r — that way the CPU knows exactly when each firefly is lit and can
// hold it roughly still during the flash, so the bright additive sprite never smears
// into a TAA "pixie dust" trail while it flies between flashes.
// Additive blend = warm glow that layers like light; depth-tested so a firefly behind
// a tree is occluded, but writes no depth itself.
render_mode cull_disabled, unshaded, shadows_disabled, depth_draw_never, blend_add;

uniform sampler2D ff_tex : source_color, filter_linear_mipmap;
uniform float ff_bright = 1.0;          // global edge-dim factor (set per frame from intensity)

varying float v_glow;

void vertex() {
	v_glow = INSTANCE_CUSTOM.r * ff_bright;   // 0..1 flash brightness, computed CPU-side

	// full camera-facing billboard; per-instance scale from the transform
	vec3 origin = MODEL_MATRIX[3].xyz;
	float sc = length(MODEL_MATRIX[0].xyz);
	vec3 cam = INV_VIEW_MATRIX[3].xyz;
	vec3 dir = normalize(cam - origin);
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), dir));
	vec3 up = cross(dir, right);
	vec3 local = right * VERTEX.x * sc + up * VERTEX.y * sc;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(origin + local, 1.0);
}

void fragment() {
	float a = texture(ff_tex, UV).a * v_glow;
	if (a < 0.003) {
		discard;
	}
	// warm gold, HDR-punchy so it blooms; additive contribution = ALBEDO * ALPHA
	ALBEDO = vec3(1.0, 0.78, 0.18) * 4.0;
	ALPHA = a;
}

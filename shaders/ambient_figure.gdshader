shader_type spatial;
// Vague distant figures (people walking / swimming / flying) for the ambient-life
// module. Y-axis billboard so the silhouette always faces the camera while staying
// upright. Per-instance tint (skin/clothing tone) + walk phase come in via
// INSTANCE_CUSTOM. A hard near-fade guarantees figures NEVER render crisp up close
// even if the CPU evasion lags — they only ever read as distant suggestions.
render_mode cull_disabled, unshaded, shadows_disabled, depth_prepass_alpha;

uniform sampler2D fig_tex : source_color, filter_linear_mipmap;
// Scene-ambient multiplier (main pushes this from the day/night cycle so figures
// darken at dusk / brighten at noon instead of glowing flatly).
global uniform float ambient_life_light;

// Near-fade window (world metres). Figures begin fading below `fade_start` and are
// fully gone by `fade_end`. Kept just under the agents' min-distance so a figure
// that slips inside the evasion radius dissolves rather than popping into detail.
uniform float fade_start = 52.0;
uniform float fade_end   = 44.0;
// Bob amplitude (metres) for the walk/idle motion.
uniform float bob_amp = 0.05;
uniform float bob_rate = 3.4;

varying vec3 v_tone;
varying float v_fade;

void vertex() {
	// --- per-instance data ---
	vec3 tone = INSTANCE_CUSTOM.rgb;
	float phase = INSTANCE_CUSTOM.a;           // 0..1 unique per figure
	v_tone = tone;

	// Instance world origin + per-instance scale (rotation is discarded — we billboard).
	vec3 origin = MODEL_MATRIX[3].xyz;
	float sx = length(MODEL_MATRIX[0].xyz);
	float sy = length(MODEL_MATRIX[1].xyz);

	// Camera world position.
	vec3 cam = INV_VIEW_MATRIX[3].xyz;

	// Y-billboard basis: face the camera around the vertical axis only.
	vec3 to_cam = cam - origin;
	to_cam.y = 0.0;
	float l = length(to_cam);
	to_cam = l > 0.0001 ? to_cam / l : vec3(0.0, 0.0, 1.0);
	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 right = normalize(cross(up, to_cam));

	// Walk bob: subtle vertical bounce + a touch of squash, keyed to TIME + phase.
	float t = TIME * bob_rate + phase * 6.28318;
	float bob = sin(t) * bob_amp;
	float squash = 1.0 + cos(t * 2.0) * 0.015;

	vec3 local = right * (VERTEX.x * sx) + up * (VERTEX.y * sy * squash);
	vec3 wpos = origin + local;
	wpos.y += bob;

	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(wpos, 1.0);

	// Distance-based near fade (use horizontal distance to match the agent logic).
	float d = length(cam - origin);
	v_fade = smoothstep(fade_end, fade_start, d);   // 0 when very close, 1 once far enough
}

void fragment() {
	vec4 tx = texture(fig_tex, UV);
	float a = tx.a * v_fade;
	if (a < 0.02) {
		discard;
	}
	// Slightly desaturated, ambient-modulated tone so figures sit in the scene light
	// rather than glowing. Kept a hair below full opacity for a "vague" read.
	ALBEDO = v_tone * clamp(ambient_life_light, 0.04, 1.0);
	ALPHA = a * 0.94;
}

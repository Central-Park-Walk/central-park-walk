shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, unshaded;

// Simple soft-circle snowflake billboard.
// Applied to small QuadMesh particles — renders as a round white dot.

uniform vec4 snow_color : source_color = vec4(0.95, 0.95, 1.0, 0.85);

void vertex() {
	// Billboard: face camera, preserving particle scale and position
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		INV_VIEW_MATRIX[0],
		INV_VIEW_MATRIX[1],
		INV_VIEW_MATRIX[2],
		MODEL_MATRIX[3]
	);
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(
		vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0),
		vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0),
		vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0),
		vec4(0.0, 0.0, 0.0, 1.0)
	);
}

void fragment() {
	vec2 uv = UV * 2.0 - 1.0;
	float dist = dot(uv, uv);
	// Soft circle with feathered edge
	float alpha = smoothstep(1.0, 0.3, dist) * snow_color.a;
	ALBEDO = snow_color.rgb;
	ALPHA = alpha;
}

shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque;

// TURF BAKE — the offline twin of turf_tile.gdshader, used only by
// scripts/bake_turf.gd to render the turf-tile mesh top-down into the far-field
// terrain texture. Same ALBEDO logic as the runtime fragment (baked vertex COLOR
// for standing blades, world-XZ grass texture for the horizontal mat/thatch) with
// everything positional stripped: no terrain conform, no wind, no density falloff,
// no land mask — the bake is one flat, fully dense tile.
//
// ⚠ KEEP IN SYNC with turf_tile.gdshader: the mat_* uniform DEFAULTS below must
// match the runtime shader's defaults (main.gd does not override them), and the
// fragment maths must match its v_ground branch — otherwise the baked far field
// drifts from the live dome and the handoff ring returns.

uniform sampler2D mat_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float mat_tex_scale = 1.3;                    // texture repeats per metre
uniform vec3  mat_tint      = vec3(0.48, 0.94, 0.56); // = turf_tile.gdshader default
uniform float mat_bright    = 0.46;                   // = turf_tile.gdshader default

varying vec3  v_col;
varying float v_ground;   // 1 = horizontal ground mat/thatch (sample mat_tex)
varying vec2  v_wxz;      // world XZ for the mat texture

void vertex(){
	// Identity placement: the bake scene positions tile instances itself (a 3x3
	// periodic grid, all yaw 0, so the centre crop tiles seamlessly).
	v_col = COLOR.rgb;        // no per-tile tint jitter — the bake is ONE canonical tile
	v_ground = UV2.x;
	v_wxz = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment(){
	vec3 alb = v_col;
	if (v_ground > 0.5) {
		vec3 tex = texture(mat_tex, v_wxz * mat_tex_scale).rgb;
		float qbright = clamp(v_col.g * 3.2, 0.5, 1.3);   // per-quad brightness var
		alb = tex * mat_tint * (mat_bright * qbright);
	}
	ALBEDO = alb;
}

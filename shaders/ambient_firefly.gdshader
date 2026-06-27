shader_type spatial;
// Fireflies as a single MultiMesh (one draw call). They must FLY (sometimes briskly),
// and the park renders through a temporal upscaler — FSR2 by default, TAA when native —
// that reprojects every pixel using the motion-vector buffer. Godot's transparent /
// additive pass writes NO motion vectors, so an additive firefly smeared into a "pixie
// dust" comet trail whenever it moved (the filter had nothing to track it by).
//
// Fix: render them OPAQUE (alpha-tested). Opaque geometry writes depth AND motion
// vectors, so FSR2/TAA reproject the firefly correctly at any speed — no trail. The CPU
// orients each quad toward the camera and writes the per-instance transform every frame
// (default vertex path, no camera math here), so the engine derives motion vectors
// straight from the frame-to-frame transform delta. Brightness still blooms because the
// HDR emission feeds the glow buffer; the flash pulse arrives in INSTANCE_CUSTOM.r.
render_mode cull_disabled, unshaded, shadows_disabled;

uniform sampler2D ff_tex : source_color, filter_linear_mipmap;
uniform float ff_bright = 1.0;          // global edge-dim factor (set per frame from intensity)

varying float v_glow;

void vertex() {
	v_glow = INSTANCE_CUSTOM.r * ff_bright;   // 0..1 flash brightness, computed CPU-side
}

void fragment() {
	float tex_a = texture(ff_tex, UV).a;
	// Alpha-tested -> this fragment is opaque, so it writes depth + motion vectors.
	// Discard the soft skirt and when the firefly is dark; the surviving disc is
	// brightness-shaped by tex_a so the glow buffer rounds it back into a soft spark.
	if (tex_a < 0.35 || v_glow < 0.02) {
		discard;
	}
	// Warm gold, HDR (>1) so it feeds the glow/bloom buffer. Brightness tracks the flash
	// pulse and the radial falloff, giving a soft bright core that fades as it blinks.
	ALBEDO = vec3(1.0, 0.78, 0.18) * (4.0 * v_glow * tex_a);
}

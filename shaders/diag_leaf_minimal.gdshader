shader_type spatial;
// DIAGNOSTIC ONLY (--simple-leaf): minimal leaf shader with the same render
// modes and alpha-discard structure as tree_leaf.gdshader but none of its
// per-fragment work (wind, SSS, phenology, noise, aerial perspective).
// The cost delta vs the real shader isolates shader complexity from
// raster structure (overdraw, quad efficiency). Not used in normal play.
render_mode cull_disabled, depth_prepass_alpha, alpha_to_coverage;

uniform vec3 albedo_tint = vec3(0.28, 0.48, 0.18);
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic;

void fragment() {
	vec4 tex = texture(albedo_tex, UV);
	if (tex.a < 0.15) {
		discard;
	}
	ALBEDO = tex.rgb * albedo_tint;
	ALPHA = tex.a;
	ROUGHNESS = 1.0;
	SPECULAR = 0.1;
}

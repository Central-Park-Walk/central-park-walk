shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque;

// TURF HEIGHT BAKE — second pass of scripts/bake_turf.gd: the same periodic
// tile mesh rendered top-down, but outputting HEIGHT (tile-local y, normalized
// by h_max) as greyscale instead of albedo. The terrain shader marches this
// field for parallax occlusion on the baked sward (POM = near-field depth for
// the terrain-only grass — Chris 2026-07-02: "pom"). Background bakes 0
// (ground level) via the pass's black clear colour.

uniform float h_max = 0.12;   // normalizer: TURF_BLADE_H 0.10 x 1.15 rand + margin

varying float v_h;

void vertex(){
	v_h = clamp(VERTEX.y / h_max, 0.0, 1.0);
}

void fragment(){
	ALBEDO = vec3(v_h);
}

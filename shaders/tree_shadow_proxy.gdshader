shader_type spatial;
render_mode unshaded, cull_disabled;

// Whole-tree shadow proxy crown (docs/trees.md §3). The proxy MMI is
// SHADOWS_ONLY, so this shader only ever runs in the shadow/depth pass.
// World-space hash discard punches leaf-density holes that PCF blurs into
// canopy dapple. Per-instance phenology (same INSTANCE_CUSTOM packing and
// density curves as tree_leaf.gdshader) scales the hole coverage, so the
// crown shadow thins through autumn shed and goes effectively bare in
// winter — marcescent species keep their retention floor — in step with
// the visible canopy by construction.

#include "res://shaders/include/tree_species.gdshaderinc"

global uniform float season_t;

uniform float coverage : hint_range(0.0, 1.0) = 0.62;
uniform float hole_scale = 1.1;

varying float v_density;

float hash3(vec3 p) {
	p = fract(p * 0.3183099 + 0.1);
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

void vertex() {
	// Same decode as tree_leaf.gdshader: R=phenology index, G=timing offset,
	// B=evergreen flag.
	float is_evergreen = INSTANCE_CUSTOM.b;
	int sp_idx = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	float timing_off = INSTANCE_CUSTOM.g - 0.5;
	float s = mod(season_t + timing_off, 4.0);
	float density = 1.0;
	if (is_evergreen < 0.5) {
		vec4 ph = PHENOLOGY[sp_idx];
		float grow = smoothstep(ph.w - 0.1, ph.w + 0.3, s);
		float shed = 1.0 - smoothstep(ph.z - 0.2, ph.z + 0.3, s);
		density = mix(WINTER_RETENTION[sp_idx], 1.0, min(grow, shed));
		// Spring blossoms (cherry, callery pear, magnolia) fill the crown
		// before leaf-out and cast like foliage.
		vec3 bt = BLOSSOM_TIMING[sp_idx];
		if (bt.y > 0.0) {
			float blossom = smoothstep(bt.x, bt.y, s) * (1.0 - smoothstep(bt.y, bt.z, s));
			density = max(density, blossom * 0.85);
		}
	}
	v_density = density;
}

void fragment() {
	vec3 wp = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	if (hash3(floor(wp / hole_scale)) > coverage * v_density) {
		discard;
	}
}

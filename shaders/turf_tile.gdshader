shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// TURF TILE — a real 3D mesh of a patch of grass (hundreds of baked blade geometries),
// instanced as tiles across a camera-following world grid. This is the "3d mesh world"
// approach: genuine blades viewable from ANY angle (including straight down), no
// billboard swivel, no radial rings. Cost lives in triangles (batched, few instances),
// not in millions of per-blade instances. Per-blade shape/colour is BAKED at build time
// (main.gd _make_turf_tile_mesh) so the vertex shader stays cheap: terrain conform,
// per-tile yaw (breaks the one-mesh repeat), wind, far-rim fade.

uniform sampler2D heightmap_tex : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;
uniform float hm_min_h = 0.0;
uniform float hm_range  = 1.0;
uniform float hm_res    = 4096.0;
#include "res://shaders/include/decode_terrain.gdshaderinc"

global uniform vec2 wind_vec;
uniform vec2  band_center = vec2(0.0);
// Ring band fades: this LOD ring's blades fade IN past inner_r (overlapping the next-denser
// ring inside it) and OUT approaching far_radius, so adjacent LOD rings cross-dissolve with
// no visible density step or pop. inner_r < 0 disables the inner cut (the near ring centre).
uniform float inner_r     = -100.0;
uniform float inner_fade  = 3.5;
uniform float far_radius  = 30.0;
uniform float far_fade    = 9.0;

// Ground-mat grass texture (world-XZ planar): breaks up the flat colour of the horizontal
// mat + thatch so straight-down shows real turf detail, never solid colour pools.
uniform sampler2D mat_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform float mat_tex_scale = 1.3;                    // texture repeats per metre
uniform vec3  mat_tint      = vec3(0.80, 1.18, 0.70); // pull the olive photo into the sward
uniform float mat_bright    = 1.0;                    // overall mat brightness (tunable)

varying vec3  v_col;
varying float v_up;
varying float v_ground;   // 1 = horizontal ground mat/thatch (sample mat_tex)
varying vec2  v_wxz;      // stable (uncollapsed) world XZ for the mat texture

float h21(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

void vertex(){
	vec3 base = MODEL_MATRIX[3].xyz;              // tile world origin (pure translation)
	// Per-tile yaw so the single tile mesh doesn't read as a repeating stamp.
	float yaw = h21(floor(base.xz + 0.5) * 0.137) * 6.2831;
	float cy = cos(yaw), sy = sin(yaw);
	vec2  lx  = VERTEX.xz;
	vec2  rot = vec2(lx.x * cy - lx.y * sy, lx.x * sy + lx.y * cy);

	float up = UV.y;                             // 0 base .. 1 tip (baked)

	vec2  rot_full = rot;                         // uncollapsed rotated offset (for mat UV)
	vec2  approx_w = base.xz + rot;
	float dist  = distance(approx_w, band_center);

	// RING BAND: this LOD ring's mesh has a fixed baked density; it fades IN past inner_r
	// (overlapping the denser ring inside it) and OUT approaching far_radius, so the whole
	// field is a set of concentric density rings that cross-dissolve. Both ends are smooth
	// and driven by the continuous band_center, so nothing pops as the camera moves.
	float cover = smoothstep(inner_r, inner_r + inner_fade, dist)
	            * (1.0 - smoothstep(far_radius - far_fade, far_radius, dist));
	rot *= cover;
	float y = VERTEX.y * cover;

	// Wind: gentle coherent sway of the tip (bend from base).
	vec2  wdir = (abs(wind_vec.x) + abs(wind_vec.y) > 0.001) ? normalize(wind_vec) : vec2(0.7071, 0.7071);
	float sway = sin(TIME * 0.85 + dot(approx_w, wdir) * 0.3) * 0.06 + 0.03;
	vec2  worldxz = base.xz + rot + wdir * (sway * up * up * cover);

	float H = sample_terrain(worldxz);
	VERTEX = vec3(worldxz.x, H + y, worldxz.y) - base;
	NORMAL = vec3(0.0, 1.0, 0.0);                 // up (lit as a soft mass; ramp is baked)

	float tint = mix(0.90, 1.10, h21(floor(base.xz + 0.5) * 1.7 + 3.0));
	v_col = COLOR.rgb * tint;
	v_up  = up;
	v_ground = UV2.x;
	v_wxz = base.xz + rot_full;                   // true world XZ (stable under collapse)
}

void fragment(){
	vec3 alb = v_col;
	if (v_ground > 0.5) {
		// Real grass detail on the horizontal mat/thatch: the world-XZ texture supplies
		// blade detail, the baked mat tone (v_col, per-quad brightness jitter) keeps it in
		// the shaded-thatch value range. No flat colour pools when looking straight down.
		vec3 tex = texture(mat_tex, v_wxz * mat_tex_scale).rgb;
		float qbright = clamp(v_col.g * 3.2, 0.5, 1.3);   // carries per-quad brightness var
		alb = tex * mat_tint * (mat_bright * qbright);
	}
	ALBEDO    = alb;
	ROUGHNESS = 0.90;
	SPECULAR  = 0.10;
	// Faint translucency only at the very tip — kept low so blades read as solid grass,
	// not a pale/washed-out sheen (Chris: "less white/transparent").
	BACKLIGHT = vec3(0.08, 0.11, 0.05) * v_up * v_up;
}

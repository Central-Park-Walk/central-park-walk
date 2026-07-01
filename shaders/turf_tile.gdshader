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
uniform float far_radius  = 30.0;
uniform float far_fade    = 9.0;

varying vec3  v_col;
varying float v_up;

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

	float up   = UV.y;                            // 0 base .. 1 tip (baked)
	float rank = UV.x;                            // per-blade stable LOD priority [0,1)

	vec2  approx_w = base.xz + rot;
	float dist  = distance(approx_w, band_center);

	// DISTANCE-DENSITY LOD: keep only blades whose rank is under the band's keep
	// fraction, so the field is incredibly dense up close and thins with distance.
	// Bands (Chris): 0-5 LOD0 (all) | 5-10 LOD1 | 10-15 LOD2 | 15-25 LOD3 | >25 → shell.
	float keep;
	if      (dist <  5.0) keep = 1.0;
	else if (dist < 10.0) keep = mix(1.0,  0.72, smoothstep( 5.0, 10.0, dist));
	else if (dist < 15.0) keep = mix(0.72, 0.45, smoothstep(10.0, 15.0, dist));
	else if (dist < 25.0) keep = mix(0.45, 0.20, smoothstep(15.0, 25.0, dist));
	else                  keep = 0.20;
	// Smooth size-fade at the cull edge (not a hard pop) → no visible LOD rings.
	float alive = smoothstep(0.0, 0.06, keep - rank);

	// Far-rim fade: shrink whole blades to nothing over the rim so the patch hands off
	// to the shell/terrain with no hard edge (smooth, camera-distance based but gradual).
	float cover = (1.0 - smoothstep(far_radius - far_fade, far_radius, dist)) * alive;
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
}

void fragment(){
	ALBEDO    = v_col;
	ROUGHNESS = 0.90;
	SPECULAR  = 0.10;
	// Faint translucency only at the very tip — kept low so blades read as solid grass,
	// not a pale/washed-out sheen (Chris: "less white/transparent").
	BACKLIGHT = vec3(0.08, 0.11, 0.05) * v_up * v_up;
}

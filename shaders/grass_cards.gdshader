shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// Grass CARD fill (the affordable-density layer). Each instance is ONE quad wearing
// a clump texture (~150 painted blades, scripts/make_grass_clump_card.py), so the
// mid-field fills as a dense grass mass for ~2 triangles per card instead of hundreds
// of blade meshes. The tight nadir foreground keeps real 3D blades (grass_blades);
// cards take over from there; shell/terrain beyond. Ground texture handles pure
// top-down (cards go edge-on from above), so no starburst.
//
// Camera-following MultiMesh, world-XZ keyed (like grass_blades) so nothing swims.
// Each card Y-billboards toward the camera so it always presents its blade face.

uniform sampler2D heightmap_tex : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;
uniform float hm_min_h = 0.0;
uniform float hm_range  = 1.0;
uniform float hm_res    = 4096.0;
#include "res://shaders/include/decode_terrain.gdshaderinc"
#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/grass_zone_colors.gdshaderinc"

uniform sampler2D card_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform sampler2D wear_map    : filter_linear,  repeat_disable;
uniform float fantasy   : hint_range(0.0, 1.0) = 1.0;
uniform float aesthetic : hint_range(0.0, 1.0) = 1.0;
global uniform vec2 wind_vec;

uniform vec2  band_center = vec2(0.0);
uniform float near_start  = 5.0;    // cards begin here (blades own inside)
uniform float near_fade   = 3.0;
uniform float far_radius  = 46.0;   // cards fully gone here (shell takes over)
uniform float far_fade    = 12.0;
uniform float cell_size   = 0.30;   // card grid spacing (m); MUST match main.gd
uniform float card_width  = 0.55;   // card quad width (m)
uniform float lush_mult   = 2.8;
uniform float lush_floor  = 0.20;
uniform float lush_ceil   = 0.46;

varying vec2  v_uv;
varying vec3  v_felt;
varying float v_shade;

vec2 splat_uv(vec2 w){ return (w + hm_world_size * 0.5) / hm_world_size; }
int zone_at(vec2 w){
	vec2 jit = vec2(hash2(w * 13.1), hash2(w * 13.1 + vec2(7.3, 41.9))) - 0.5;
	return int(texture(landuse_map, splat_uv(w + jit * 1.8)).r * 255.0 + 0.5);
}
bool zone_is_unmown(int z){ return z == 5 || z == 10 || z == 11 || z == 13 || z == 14; }
float zone_height_m(int z){
	if (z == 8 || z == 12) return 0.0;
	if (z == 1)            return 0.07;
	if (z == 2)            return 0.085;
	if (z == 3 || z == 7 || z == 9) return 0.07;
	if (z == 4 || z == 6)  return 0.08;
	if (z == 0)            return 0.10;
	if (z == 5)            return 0.22;
	if (z == 10 || z == 11) return 0.17;
	if (z == 13)           return 0.20;
	if (z == 14)           return 0.30;
	return 0.085;
}
float hash21(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}
vec2 hash22(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

void vertex(){
	vec3 base = MODEL_MATRIX[3].xyz;
	vec2 cw   = floor(base.xz / cell_size + 0.5) * cell_size;
	vec2 h2   = hash22(cw);
	vec2 pos  = cw + (h2 - 0.5) * cell_size * 0.85;

	int   zone   = zone_at(pos);
	float zh     = zone_height_m(zone);
	if (aesthetic > 0.5 && zh > 0.001) zh = clamp(zh * lush_mult, lush_floor, lush_ceil);
	float wear   = texture(wear_map, splat_uv(pos)).r;

	// Alive within the card ring, faded by DITHER (drop whole cards) not by shrinking
	// them — shrinking makes concentric size-bands. A per-card threshold vs the ring
	// gives a soft stochastic transition at both rims, cards stay full size.
	// Coverage is a SMOOTH size-fade, not a binary per-card cull — a binary cull pops
	// cards on/off as the camera-distance threshold sweeps world cells while walking
	// (the "pulse"). Cards exist by a stable zone/wear test (camera-independent) and
	// only SCALE down at the far rim. Radius noise-perturbed so the rim isn't a circle.
	float dist   = distance(pos, band_center) + (hash21(cw * 0.63 + 1.0) - 0.5) * 7.0;
	float cover  = 1.0 - smoothstep(far_radius - far_fade, far_radius, dist);
	float wear_cut = aesthetic > 0.5 ? 0.97 : 0.85;
	float alive  = float(zh > 0.001) * float(wear < wear_cut);

	float up  = clamp(VERTEX.y, 0.0, 1.0);    // 0 base .. 1 top
	vec2  loc = VERTEX.xz;                      // crossed-quad local offset (±0.5)

	// Turf-tile size: height from the (aesthetic) zone height with per-tile variation.
	float ch = zh * mix(1.4, 2.3, h2.y);
	float cw_m = card_width * mix(0.85, 1.3, h2.x);
	if (aesthetic > 0.5) ch *= mix(1.0, 0.7, smoothstep(0.3, 0.9, wear));

	// FIXED per-tile yaw (world-hash) — the tile is locked to the ground, NOT facing the
	// camera. This is the whole point: no swivel as you walk, and no radial/concentric
	// rings (a grid of fixed-yaw tiles has no camera-centred symmetry).
	float yaw = hash21(cw * 7.7 + 3.0) * 6.2831;
	float cy = cos(yaw), sy = sin(yaw);
	vec2  offs = vec2(loc.x * cy - loc.y * sy, loc.x * sy + loc.y * cy) * cw_m;

	// Wind: gentle coherent sway of the tile top (bend from base).
	vec2  wdir = (abs(wind_vec.x) + abs(wind_vec.y) > 0.001) ? normalize(wind_vec) : vec2(0.7071, 0.7071);
	float sway = sin(TIME * 0.85 + dot(pos, wdir) * 0.3) * 0.05 + 0.03;
	vec2  bend = wdir * sway * ch * up * up;

	float H = sample_terrain(pos);
	vec3  local = vec3(offs.x + bend.x, up * ch, offs.y + bend.y);
	local *= alive * cover;                    // smooth far-rim size-fade (no pop)

	VERTEX = vec3(pos.x, H, pos.y) - base + local;
	NORMAL = vec3(0.0, 1.0, 0.0);              // up (lit mass; blade detail from the texture)

	// Per-tile horizontal flip breaks the tiled-repeat of one texture across the field.
	float flip = step(0.5, hash21(cw * 5.3 + 2.0));
	v_uv = vec2(mix(UV.x, 1.0 - UV.x, flip), UV.y);

	// Shared, calibrated colour field (same as blades/terrain) so cards match the felt.
	vec3 felt = (fantasy < 0.5) ? grass_base_color_no_dead(zone, pos) : fantasy_grass_color(pos);
	if (fantasy < 0.5 && zone == 13)
		felt = mix(grass_base_color_no_dead(0, pos), felt, sedge_patch_mask(pos));
	if (fantasy < 0.5) {
		float cwr = turf_wear_total(wear, 0.0, zone, pos);
		if (aesthetic > 0.5) cwr *= 0.20;
		felt = apply_turf_wear(felt, cwr, pos);
	}
	felt *= mix(vec3(0.93, 0.97, 0.90), vec3(1.07, 1.05, 0.96), hash21(cw * 2.1 + 5.0));
	v_felt  = felt;
	v_shade = 1.0;
}

void fragment(){
	vec4 t = texture(card_tex, v_uv);
	if (t.a < 0.5) discard;                    // alpha cutout (no blend → cheap, no sort)

	// Card luminance carries the blade shapes + tip-bright/base-dark ramp; modulate the
	// shared felt colour by it so the mass stays the calibrated seasonal green.
	float luma = clamp(dot(t.rgb, vec3(0.299, 0.587, 0.114)) * 1.7, 0.25, 1.35);
	vec3  col  = v_felt * luma;
	col = mix(col, t.rgb * 1.15, 0.15);        // keep a hint of the card's own straw/variation
	ALBEDO    = col;
	ROUGHNESS = 0.85;
	SPECULAR  = 0.12;
	BACKLIGHT = vec3(0.32, 0.40, 0.20) * clamp(1.0 - v_uv.y, 0.0, 1.0);  // tips glow
}

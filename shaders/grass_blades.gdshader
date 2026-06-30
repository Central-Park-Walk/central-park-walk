shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// Near-field MESH-BLADE band (the hybrid step, 2026-06-30). The shell turf
// (shell_grass.gdshader) is horizontal cards stacked into a carpet — it reads
// correct from any angle but is intrinsically flat: it has no real silhouette
// looking down or across, and tall zones (meadow/shore/woodland) can't show real
// blades. This shader adds genuine 3D CURVED blades in the near ~12 m so the
// looking-down case and tall-zone silhouettes get real geometry. It LAYERS over
// the shell mat (shells still provide the dense ground coverage) and DISSOLVES
// into the shells at the band edge so there is no seam.
//
// One MultiMesh of a small bent-blade mesh is drawn ~15k times on a camera-
// following grid. The per-instance transform is pure translation onto the grid;
// the blade mesh stays in LOCAL space (x = ±0.5 across, y = 0..1 up). Everything
// per-blade (jitter, orientation, height, bend, wind, colour) is keyed off the
// blade's WORLD XZ (MODEL_MATRIX[3]) — never off INSTANCE_ID — so the camera-
// following parent can snap freely (main.gd) without the blades swimming:
// whichever instance covers a world cell renders the identical blade.
//
// History (project_grass_lod / docs/grass.md §0b): radial-tuft / dome geometry
// was REJECTED — it starbursts from above and is a perf sink. The right near-
// field geometry is UPRIGHT CURVED blades, which is what this is.

// --- terrain height sampling (shared project decode) ---
uniform sampler2D heightmap_tex : filter_linear, repeat_disable;
uniform float hm_world_size = 5000.0;
uniform float hm_min_h      = 0.0;
uniform float hm_range      = 1.0;
uniform float hm_res        = 4096.0;
#include "res://shaders/include/decode_terrain.gdshaderinc"

// Shared, calibrated grass colour field — the SAME functions the terrain shader
// and the shell turf use, so the near blades are the same hue/value as the felt
// they sit in and the band edge has nothing to transition between.
#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/grass_zone_colors.gdshaderinc"

// --- zone + wear data (same maps as shell turf / particle grass) ---
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform sampler2D wear_map    : filter_linear,  repeat_disable;

uniform float fantasy : hint_range(0.0, 1.0) = 1.0;
global uniform vec2 wind_vec;

// Band geometry. The blade patch follows the camera; blades fade out toward its
// rim so they hand off to the shell turf with no visible boundary.
uniform vec2  band_center  = vec2(0.0);
uniform float band_radius  = 12.0;   // metres from camera where blades are fully gone
uniform float band_fade    = 4.5;    // dissolve-ring width
uniform float cell_size    = 0.26;   // placement grid spacing (m); MUST match main.gd
uniform float blade_width  = 0.013;  // base half-width (m)
uniform float height_scale = 1.0;    // global height multiplier (tuning)
uniform float density      = 0.82;   // fraction of cells that grow a blade in mown turf

varying vec3  v_felt;   // per-blade felt colour (matches shell + terrain)
varying float v_h;      // 0..1 up the blade (shading)
varying float v_r;      // per-blade vitality jitter

vec2 splat_uv(vec2 w){ return (w + hm_world_size * 0.5) / hm_world_size; }
// Same ±jitter as shell_grass / terrain3d_override so the zone boundaries (water,
// shore) dither identically and the blades line up with the dithered felt.
int zone_at(vec2 w){
	vec2 jit = vec2(hash2(w * 13.1), hash2(w * 13.1 + vec2(7.3, 41.9))) - 0.5;
	return int(texture(landuse_map, splat_uv(w + jit * 1.8)).r * 255.0 + 0.5);
}
bool zone_is_unmown(int z){ return z == 5 || z == 10 || z == 11 || z == 13 || z == 14; }

// Per-zone standing height in METERS — identical table to shell_grass.gdshader so
// blade height matches the shell stack height in every zone.
float zone_height_m(int z){
	if (z == 8 || z == 12) return 0.0;    // pool / water — no grass
	if (z == 1)            return 0.07;
	if (z == 2)            return 0.085;
	if (z == 3 || z == 7 || z == 9) return 0.07;
	if (z == 4 || z == 6)  return 0.08;
	if (z == 0)            return 0.10;
	if (z == 5)            return 0.22;   // nature reserve unmown
	if (z == 10 || z == 11) return 0.17;  // woodland floor
	if (z == 13)           return 0.20;   // shore sedge
	if (z == 14)           return 0.30;   // wild meadow
	return 0.085;
}

// Hoskins hashes (no axis symmetry → no mirror seam at x=0/z=0).
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
	// Instance world origin (pure-translation MODEL → its translation column).
	// The instance grid + the camera-follow snap (main.gd) keep this on the
	// cell_size lattice; round defensively against float error.
	vec3 base = MODEL_MATRIX[3].xyz;
	vec2 cell_world = floor(base.xz / cell_size + 0.5) * cell_size;
	float up   = clamp(VERTEX.y, 0.0, 1.0);   // authored 0..1 up the blade
	float side = VERTEX.x;                     // authored ±0.5 across

	// Per-blade world hash → jitter, orientation, height, vitality.
	vec2  h2  = hash22(cell_world);
	vec2  jit = (h2 - 0.5) * cell_size * 0.9;
	vec2  pos = cell_world + jit;

	int   zone   = zone_at(pos);
	float zh     = zone_height_m(zone);
	float wear   = texture(wear_map, splat_uv(pos)).r;
	bool  unmown = zone_is_unmown(zone);

	// Keep test. A blade is ALIVE only on grass, unworn-enough ground, inside the
	// band, and passing a stochastic density gate. Dead blades collapse to a point
	// (degenerate triangle → no fragments), cheaper than a fragment discard.
	float dist  = distance(pos, band_center);
	float band  = 1.0 - smoothstep(band_radius - band_fade, band_radius, dist);
	float keep  = mix(density, 0.95, float(unmown));
	float r     = hash21(cell_world * 1.7 + 4.0);
	float alive = float(zh > 0.001) * float(r < keep * band) * float(wear < 0.82);

	// Per-blade orientation + height.
	float ang = hash21(cell_world * 3.1) * 6.2831;
	vec2  fwd = vec2(cos(ang), sin(ang));         // lean / bend direction (horizontal)
	vec2  rgt = vec2(-fwd.y, fwd.x);              // width direction (horizontal)
	float hv  = unmown ? mix(0.55, 1.35, h2.y) : mix(0.80, 1.12, h2.y);
	float bh  = zh * hv * height_scale;
	bh       *= mix(1.0, 0.35, smoothstep(0.1, 0.6, wear));   // wear shortens

	// Width tapers base→tip; tip is soft (not a needle).
	float halfw = blade_width * (1.0 - up * 0.80);

	// Bend: tip leans over (so the blade presents area when viewed from above and
	// reads as grass, not a vertical spike). Quadratic so the base stays upright.
	float lean = (up * 0.30 + up * up * 0.70) * bh * 0.55;
	// Wind: a shared gust sway + the global wind_vec push, both ramping up the blade.
	float gust = sin(TIME * 1.6 + pos.x * 0.7 + pos.y * 0.55) * 0.10;
	vec2  wind = fwd * lean + (wind_vec * 0.12 + fwd * gust) * (up * up);

	float H = sample_terrain(pos);
	vec3  local;
	local.xz = rgt * (side * 2.0 * halfw) + wind;
	local.y  = up * bh;
	local   *= alive;                             // collapse dead blades to a point

	// Write VERTEX as the offset from the instance origin (MODEL is pure
	// translation, so MODEL * offset = base + offset = the world blade vertex).
	VERTEX = vec3(pos.x, H, pos.y) - base + local;

	// Normal: the blade ribbon plane contains the up-tangent and the width dir;
	// the broad-face normal is ~horizontal along fwd, biased upward so blades catch
	// soft top light instead of reading as dark edges. MODEL is pure translation,
	// so this model-space normal already points the right way in world; the pipeline
	// transforms it to view space.
	vec3 rgt3   = vec3(rgt.x, 0.0, rgt.y);
	vec3 tan_up = normalize(vec3(fwd.x * 0.5 + wind_vec.x * 0.1, 1.0, fwd.y * 0.5 + wind_vec.y * 0.1));
	NORMAL = normalize(cross(rgt3, tan_up) + vec3(0.0, 0.7, 0.0));

	// --- colour: SAME shared field as shell turf + terrain ---
	vec3 felt = (fantasy < 0.5)
		? grass_base_color_no_dead(zone, pos)
		: fantasy_grass_color(pos);
	if (fantasy < 0.5 && zone == 13) {
		felt = mix(grass_base_color_no_dead(0, pos), felt, sedge_patch_mask(pos));
	}
	if (fantasy < 0.5) {
		float cw = turf_wear_total(wear, 0.0, zone, pos);
		felt = apply_turf_wear(felt, cw, pos);
	}
	v_felt = felt;
	v_h    = up;
	v_r    = hash21(cell_world + 9.1);
}

void fragment(){
	// Vertical gradient: shaded base → lit tip, both shades of the SAME felt.
	float vgrad = clamp(v_h * 0.70 + 0.30, 0.0, 1.0);
	vec3  col   = v_felt * mix(0.55, 1.10, vgrad);
	col        *= mix(0.93, 1.07, v_r);            // per-blade vitality jitter
	float ao    = mix(0.58, 1.0, v_h);             // soil-darkening toward the base
	ALBEDO    = col * ao;
	ROUGHNESS = 0.72;
	SPECULAR  = 0.20;
	BACKLIGHT = vec3(0.25 * v_h);                  // translucent tip glow
}

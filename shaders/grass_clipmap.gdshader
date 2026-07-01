shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// CLIPMAP GRASS — ONE camera-centered MultiMesh of grass-blade clumps, placed by a clipmap in
// the vertex shader: a dense inner square, then rings whose cell size DOUBLES each level, so a
// single system covers the whole park (dense centre → sparse edge → terrain beyond) at a
// BOUNDED instance count (grows with the number of levels ~log(radius), not area R²). This is
// the thing our uniform camera-following tile grid could never do (its cost was R²).
//
// Ported from the TerraBrush foliage clipmap (spimort/TerraBrush,
// foliage_multimesh_shader_include.gdshaderinc) and wired to OUR data: Terrain3D height
// (terrain3d_height.gdshaderinc), the landuse mask, and the shared sward/zone colour field
// (grass_zone_colors.gdshaderinc) so blades match the terrain exactly — no zone banding.
//
// The MMI is NEVER moved: placement is INSTANCE_ID + player_world_pos (a global uniform), so
// MODEL_MATRIX stays constant and TAA/FSR2 get correct motion vectors (moving a procedurally
// placed MMI emits bogus motion vectors → the whole field smears every snap = the old pop).
// TerraBrush independently switched GPUParticles→MultiMesh for the same flicker reason.

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/grass_zone_colors.gdshaderinc"
#include "res://shaders/include/terrain3d_height.gdshaderinc"

global uniform vec2 wind_vec;
global uniform vec3 player_world_pos;

// Clipmap config — these MUST match main.gd _clipmap_instance_count() (the MultiMesh instance
// count is the exact number of clipmap points these values produce; the shader collapses any
// index it considers out-of-range, so an under-count leaves gaps).
uniform float initial_cell = 0.35;   // inner cell size (m) = densest blade-clump spacing
uniform int   lod_rows     = 21;     // rows per clipmap level (forced odd in-shader)
uniform int   lod_levels   = 5;      // doubling levels (reach = ~(lod_rows/2)*initial_cell*2^(levels-1))
uniform float rand_place   = 0.16;   // per-clump world-locked random offset (m), breaks the grid

uniform float height_scale        = 1.0;    // blade-height multiplier (lush lever)
uniform float footprint_grow_pow  = 0.35;   // far clumps widen with cell size to hold coverage
uniform float blade_far           = 118.0;  // clumps fade out by here (terrain carries beyond)
uniform float blade_far_fade      = 20.0;   // soft fade width at the far rim
uniform float alt_fade_lo         = 14.0;   // full field at/below this height above ground
uniform float alt_fade_hi         = 32.0;   // field gone by here (flying)

// LAND MASK — the field is tied to the LAND, not the camera: no blades over water/pool.
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform float world_size = 5000.0;

varying vec3  v_base;   // per-instance terrain-matched base colour (flat across the clump)
varying vec3  v_tint;   // per-blade family multiplier (baked in COLOR)
varying float v_up;     // 0 base .. 1 tip

float h21(vec2 p){
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// Landuse zone at world XZ, jittered so the low-res texel grid dithers instead of staircasing
// (matches the turf/terrain lookup so masks line up).
int zone_at(vec2 w){
	vec2 jit = vec2(h21(w * 13.1), h21(w * 13.1 + vec2(7.3, 41.9))) - 0.5;
	vec2 uv = (w + jit * 1.8 + world_size * 0.5) / world_size;
	return int(texture(landuse_map, uv).r * 255.0 + 0.5);
}
bool zone_no_grass(int z){ return z == 8 || z == 12; }   // 8=pool 12=water

mat2 rot2(float a){ float c = cos(a), s = sin(a); return mat2(vec2(c, -s), vec2(s, c)); }

void vertex(){
	// ---- Clipmap: INSTANCE_ID → cell (cx,cz) + cellWidth. Ported from TerraBrush. ----
	int idx  = INSTANCE_ID;
	int rows = lod_rows;
	if (rows % 2 == 0) { rows += 1; }        // rows per level must be odd
	int P = 2 * rows + 3;                     // points per side of a level
	float cx = 0.0, cz = 0.0;
	float cell = initial_cell;
	bool valid = true;

	if (idx < P * P) {
		// Inner full-density square (level 1)
		cx = float(idx % P) - float(P / 2);
		cz = floor(float(idx / P)) - float(P / 2);
	} else {
		int rem      = lod_levels - 1;
		int topLines = (rows + 1) / 2;
		int nTop     = P * topLines * rem;                 // indices in the top OR bottom band
		int perSide  = P - topLines * 2;
		int nSide    = topLines * perSide * rem;           // indices in the left OR right band
		idx -= P * P;

		if (idx < nTop * 2) {                              // top / bottom bands
			bool bottom = idx >= nTop;
			if (bottom) { idx -= nTop; }
			int lvl = lod_levels - int(floor(float(idx / (P * topLines))));
			idx -= (lod_levels - lvl) * (P * topLines);
			cx = float(idx % P) - float(P / 2);
			cz = floor(float(idx / P)) - float(P / 2);
			if (bottom) { cz *= -1.0; }
			cell = pow(2.0, float(lvl - 1)) * initial_cell;
		} else if (idx < nTop * 2 + nSide * 2) {          // left / right bands
			bool right = idx >= nTop * 2 + nSide;
			if (right) { idx -= nTop * 2 + nSide; } else { idx -= nTop * 2; }
			int lvl = lod_levels - int(floor(float(idx / (perSide * topLines))));
			idx -= (lod_levels - lvl) * (perSide * topLines);
			cx = float(idx % topLines) - float(P / 2);
			cz = floor(float(idx / topLines)) - float(P / 2);
			cz += float(topLines);
			if (right) { cx *= -1.0; }
			cell = pow(2.0, float(lvl - 1)) * initial_cell;
		} else {
			valid = false;                                // spare index → collapse
		}
	}

	// ---- Camera-follow: world-lock EACH level to ITS OWN cell grid (snap by `cell`) ----
	// Snapping every level by the small inner cell (initial_cell) made the outer, doubled cells
	// shift only a FRACTION of their own width each step and re-hash their offset/yaw/colour → the
	// whole far field visibly "popped to catch up" as you walked (Chris). Snapping each level by
	// its own cell size lands every level on a fixed world grid of that spacing, so every clump is
	// world-stationary; only WHICH cells fall inside the ring changes as the camera moves (and the
	// distance fade hides that at the rim). Inner level still snaps at initial_cell = smooth.
	vec2 camxz   = player_world_pos.xz;
	vec2 snap    = round(camxz / cell) * cell;
	vec2 lattice = vec2(cx, cz) * cell + snap;

	// Per-clump world-locked random offset breaks the lattice look (hash off the fixed cell).
	float ha = h21(lattice * 0.7);
	float hb = h21(lattice * 0.7 + vec2(19.3, 4.1));
	vec2 particle = lattice + vec2(mix(-rand_place, rand_place, ha),
	                               mix(-rand_place, rand_place, hb));

	int zone = zone_at(particle);
	float alive = valid ? 1.0 : 0.0;
	if (zone_no_grass(zone)) { alive = 0.0; }

	float H = sample_terrain(particle);

	// Distance + altitude fades (clumps shrink to zero → degenerate → invisible; no hard pop).
	float dist    = distance(particle, camxz);
	float farf    = 1.0 - smoothstep(blade_far - blade_far_fade, blade_far, dist);
	float cam_alt = player_world_pos.y - H;
	float altf    = 1.0 - smoothstep(alt_fade_lo, alt_fade_hi, cam_alt);
	float cover   = alive * farf * altf;

	// Per-clump scale: footprint widens gently with cell size (far coverage); height is steady.
	float nz        = mix(0.8, 1.25, h21(lattice * 1.7 + vec2(3.0, 7.0)));
	float footprint = nz * pow(cell / initial_cell, footprint_grow_pow) * cover;
	float bladeH    = nz * height_scale * cover;
	float yaw       = h21(lattice * 0.137) * 6.2831;

	// Local blade vertex → rotate by the clump yaw, scale, wind-bend the tip, place in world.
	float up = UV.y;
	vec3 lp  = VERTEX;
	lp.xz    = rot2(yaw) * lp.xz;
	lp.xz   *= footprint;
	lp.y    *= bladeH;

	// Wind: gentle coherent sway along a FIXED spatial axis (phasing off the wandering wind dir
	// snapped the whole field — see turf_tile). Wind only sets amplitude (capped) + lean dir.
	float wlen  = length(wind_vec);
	vec2  wdir  = wlen > 0.001 ? wind_vec / wlen : vec2(0.7071, 0.7071);
	float wstr  = clamp(wlen * 1.6, 0.0, 1.0);
	float phase = TIME * 0.9 + dot(particle, vec2(0.7071, 0.7071)) * 0.35;
	float sway  = sin(phase) * mix(0.008, 0.05, wstr);
	lp.xz += wdir * (sway * up * up * footprint);

	// Absolute world position — MODEL_MATRIX is identity (MMI at origin, never moved).
	VERTEX = vec3(particle.x + lp.x, H + lp.y, particle.y + lp.z);
	NORMAL = vec3(0.0, 1.0, 0.0);

	// Colour from the SAME field the terrain uses → the blade layer can't band against it.
	v_base = grass_base_color_no_dead(zone, particle);
	v_tint = COLOR.rgb;
	v_up   = up;
}

void fragment(){
	// base (terrain-matched) × per-blade family tint × base→tip brightness ramp.
	ALBEDO    = v_base * v_tint * mix(0.72, 1.18, v_up);
	ROUGHNESS = 0.98;   // near-matte (Chris: grass too shiny)
	SPECULAR  = 0.02;
	BACKLIGHT = vec3(0.06, 0.09, 0.04) * v_up * v_up;   // faint tip translucency only
}

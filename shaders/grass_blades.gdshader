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
uniform float band_radius  = 40.0;   // metres from camera where blades are fully gone
uniform float band_fade    = 10.0;   // dissolve-ring width
uniform float lod_near     = 12.0;   // full density inside this radius; thins beyond
uniform float lod_far_keep = 0.38;   // density fraction at the far edge (screen stays dense)
uniform float cell_size    = 0.053;  // placement grid spacing (m); MUST match main.gd
uniform float blade_width  = 0.006;  // half-width scale (m); full blade ~2x (thin: reads as individual blades in a dense mass)
uniform float height_scale = 1.0;    // global height multiplier (tuning)
uniform float density      = 0.97;   // fraction of cells that grow a blade (dense mass)

// --- AAA look controls ---
uniform float clump_size   = 0.62;   // tuft spacing (m): blades gather into clumps this big
uniform float clump_pull   = 0.35;   // 0=even grid, 1=all blades on the clump centre
uniform float bare_frac    = 0.04;   // fraction of clumps left bare (negative space)
uniform float height_var   = 0.45;   // ± per-clump height spread
uniform float dead_frac    = 0.05;   // fraction of dead/straw blades
uniform float gust_scale   = 0.045;  // spatial freq of the rolling gust field
uniform float gust_speed   = 0.55;   // how fast gusts travel across the field
uniform float spec_strength = 0.40;
// Blade arc: real grass blades CURVE over (the reference tuft is a mass of bent
// blades), not straight spikes. This is the per-blade tip bend as a fraction of
// height; large values lay the tip well over for a soft feathery silhouette.
uniform float curve_amt    = 0.62;

// --- AESTHETIC SCALE (temporary: suspend data-driven height for pure look) ---
// The mown-turf data (7–10 cm) is too short to READ from standing height — each
// tuft is a few pixels = fuzzy carpet. When aesthetic is on, blade height is driven
// to a lush, readable scale (zone variety preserved but lifted + clamped) so the
// grass looks like real grass and makes a good backdrop for the trees. ONE flag in
// main.gd (GRASS_LUSH) → reversible.
uniform float aesthetic  : hint_range(0.0, 1.0) = 1.0;
uniform float lush_mult  = 2.8;     // scale-up applied to the data height
uniform float lush_floor = 0.20;    // shortest readable blade (m)
uniform float lush_ceil  = 0.46;    // tallest blade (m)

varying vec3  v_felt;   // per-blade felt colour (matches shell + terrain)
varying float v_h;      // 0..1 up the blade (shading)
varying float v_r;      // per-blade vitality jitter
varying float v_dead;   // 1 = dead/straw blade

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

	// Per-blade world hash → jitter, height, vitality.
	vec2  h2   = hash22(cell_world);
	vec2  jit  = (h2 - 0.5) * cell_size * 0.9;
	vec2  bpos = cell_world + jit;             // raw per-cell blade root

	// --- CLUMPING: gather blades into tufts on a coarser world grid. This is what
	// turns a uniform "carpet" into real grass: blades pulled toward shared clump
	// centres, fanned out like a rosette, with whole clumps left bare for negative
	// space. All keyed off the WORLD clump cell, so it stays put as the patch snaps.
	vec2  clump_cell   = floor(bpos / clump_size);
	vec2  ch           = hash22(clump_cell * 1.37 + 2.0);
	vec2  clump_center = (clump_cell + 0.5 + (ch - 0.5) * 0.75) * clump_size;
	float cr           = hash21(clump_cell * 2.1 + 5.0);   // per-clump random
	vec2  pos          = mix(bpos, clump_center, clump_pull);

	int   zone   = zone_at(pos);
	float zh     = zone_height_m(zone);
	float wear   = texture(wear_map, splat_uv(pos)).r;
	bool  unmown = zone_is_unmown(zone);

	// AESTHETIC SCALE: lift the (too-short) data height to a readable lush scale,
	// keeping the relative zone variety but clamped to a pleasing band. Water/pool
	// zones (zh==0) stay grassless.
	if (aesthetic > 0.5 && zh > 0.001) {
		zh = clamp(zh * lush_mult, lush_floor, lush_ceil);
	}

	// Keep test. ALIVE only on grass, on a non-bare clump, inside the band, passing
	// the density gate, on unworn ground. Dead blades collapse to a point (degenerate
	// triangle → no fragments), cheaper than a fragment discard.
	float clump_dens = hash21(clump_cell * 3.7 + 1.0);
	float clump_ok   = step(bare_frac, clump_dens);   // some tufts are bare ground
	float dist  = distance(pos, band_center);
	// Distance-density LOD: full density near, thinning with distance (far blades are
	// small on screen, so fewer read as just as dense) — lets the band reach far while
	// staying affordable. Then a short rim fade hands off to the shell.
	float lod   = mix(1.0, lod_far_keep, smoothstep(lod_near, band_radius - band_fade, dist));
	float rim   = 1.0 - smoothstep(band_radius - band_fade, band_radius, dist);
	float keep  = mix(density, 0.96, float(unmown));
	float r     = hash21(cell_world * 1.7 + 4.0);
	// Keep grass lush over worn ground too (aesthetic): only the most-trodden bare
	// paths strip out, so we don't expose the shell mat's weave as Mario64 dirt.
	float wear_cut = aesthetic > 0.5 ? 0.95 : 0.85;
	float alive = float(zh > 0.001) * clump_ok * float(r < keep * lod * rim) * float(wear < wear_cut);

	// Orientation: fan OUT from the clump centre (rosette splay) + a per-blade twist
	// so a tuft reads as many blades from one root, not parallel copies.
	vec2  outv  = pos - clump_center;
	float outl  = length(outv);
	vec2  fan   = outl > 0.001 ? outv / outl : vec2(cos(cr * 6.2831), sin(cr * 6.2831));
	float twist = (hash21(cell_world * 3.1) - 0.5) * 1.5;
	float ct = cos(twist), st = sin(twist);
	vec2  fwd = vec2(fan.x * ct - fan.y * st, fan.x * st + fan.y * ct);  // lean/bend dir
	vec2  rgt = vec2(-fwd.y, fwd.x);                                     // width dir

	// Height: per-clump tall/short (visual rhythm) × per-blade × rare tall stragglers.
	float clump_hm = mix(1.0 - height_var, 1.0 + height_var, cr);
	float blade_hm = unmown ? mix(0.70, 1.30, h2.y) : mix(0.82, 1.12, h2.y);
	float strag    = step(0.96, r) * 0.55;            // occasional extra-tall blade
	float bh = zh * clump_hm * blade_hm * (1.0 + strag) * height_scale;
	// Wear shortens blades, but gently in aesthetic mode so worn lawn stays lush.
	bh      *= aesthetic > 0.5 ? mix(1.0, 0.70, smoothstep(0.25, 0.85, wear))
	                           : mix(1.0, 0.40, smoothstep(0.1, 0.6, wear));

	// Width: a touch wider for tall grass; mesh owns the parallel-sided taper.
	float halfw = blade_width * mix(0.9, 1.35, smoothstep(0.08, 0.30, bh));

	// Bend: a real ARC so blades curve over like the reference tuft (not straight
	// spikes). Quadratic-dominant so the base stays planted and the tip lays over;
	// per-blade variation so some blades arc more than others.
	float curve_v  = curve_amt * mix(0.6, 1.25, h2.x);
	float lean     = (up * 0.25 + up * up * 0.75) * bh * curve_v;

	// Wind: a rolling COHERENT GUST envelope that travels across the field in the
	// wind direction (you see waves of wind move over the grass), plus a gentle
	// base sway. Tall blades bend more. Applied as an arc (quadratic in up).
	vec2  wdir = (abs(wind_vec.x) + abs(wind_vec.y) > 0.001) ? normalize(wind_vec) : vec2(0.7071, 0.7071);
	float wstr = clamp(length(wind_vec), 0.0, 1.0);
	float gco  = dot(pos, wdir) * gust_scale - TIME * gust_speed;
	float gust = max(sin(gco) * 0.6 + sin(gco * 0.43 + 1.7) * 0.4, 0.0);   // 0..1 rolling
	float sway = sin(TIME * 0.9 + dot(pos, wdir) * 0.30) * 0.04;
	float wfrac = (0.10 + 0.40 * gust) * (0.45 + 0.55 * wstr);   // fraction of height at tip
	vec2  bendv = (wdir * (wfrac + sway) + wind_vec * 0.04) * bh; // metres
	vec2  hbend = fwd * lean + bendv * (up * up);                 // total horizontal bend

	float H = sample_terrain(pos);
	vec3  local;
	local.xz = rgt * (side * 2.0 * halfw) + hbend;
	// Foreshorten: a bent blade lowers its tip a little so it doesn't look stretched.
	local.y  = up * bh - 0.30 * length(bendv) * up * up;
	local   *= alive;                             // collapse dead blades to a point

	// Write VERTEX as the offset from the instance origin (MODEL is pure translation).
	VERTEX = vec3(pos.x, H, pos.y) - base + local;

	// Normal: proper curved-blade normal from the centreline tangent (d/dup of the
	// bend) crossed with the width dir, up-biased so the field catches sky light and
	// reads as form, not dark edges.
	float dlean = (0.25 + 1.50 * up) * bh * curve_v;
	vec2  doff  = fwd * dlean + bendv * (2.0 * up);
	vec3  tang  = normalize(vec3(doff.x, bh, doff.y));
	vec3  rgt3  = vec3(rgt.x, 0.0, rgt.y);
	vec3  nrm   = cross(rgt3, tang);
	if (nrm.y < 0.0) nrm = -nrm;                  // face up-ish for either ribbon side
	// Strong up-bias: blades catch sky light and read as a soft lit mass instead of
	// dark vertical edges (the near-black blades in the GPU walk were edge-on faces).
	NORMAL = normalize(nrm + vec3(0.0, 1.10, 0.0));

	// --- colour: SAME shared field as shell turf + terrain (keeps the seam killed) ---
	vec3 felt = (fantasy < 0.5)
		? grass_base_color_no_dead(zone, pos)
		: fantasy_grass_color(pos);
	if (fantasy < 0.5 && zone == 13) {
		felt = mix(grass_base_color_no_dead(0, pos), felt, sedge_patch_mask(pos));
	}
	// Wear drying turns grass tan/dead on high-traffic ground (e.g. The Mall) — that
	// is data fidelity that reads as barren/sparse. In aesthetic mode keep it green
	// (only a whisper of wear so there's still subtle variation), so worn lawns stay
	// lush. Realistic mode keeps the full calibrated wear.
	if (fantasy < 0.5) {
		float cw = turf_wear_total(wear, 0.0, zone, pos);
		if (aesthetic > 0.5) cw *= 0.20;
		felt = apply_turf_wear(felt, cw, pos);
	}
	// Per-clump tint drift so each tuft is its own subtle hue (still in-family).
	felt *= mix(vec3(0.93, 0.97, 0.90), vec3(1.07, 1.05, 0.96), cr);
	v_felt = felt;
	v_h    = up;
	v_r    = hash21(cell_world + 9.1);
	v_dead = step(1.0 - dead_frac, hash21(cell_world + 11.0));
}

void fragment(){
	float g = v_h;                                  // 0 base .. 1 tip
	// Tip-to-base gradient: base cooler/darker, tip warmer (yellow-green) + brighter.
	// All multiplied off the shared felt so it stays the calibrated colour family.
	// Blades are LIT grass standing above a darker understory — keep them clearly on
	// the bright side of the felt (base a touch deeper, tip brighter) so even edge-on
	// slivers read as green, never the dark "hairs" of the GPU walk.
	vec3 basec = v_felt * vec3(0.95, 1.02, 0.84);
	vec3 tipc  = v_felt * vec3(1.22, 1.28, 0.92);
	vec3 col   = mix(basec, tipc, smoothstep(0.0, 1.0, g));
	col       *= mix(0.94, 1.10, v_r);             // per-blade vitality jitter
	// Dead/straw blades: desaturated tan, still height-shaded.
	if (v_dead > 0.5) col = mix(col, vec3(0.62, 0.55, 0.33) * (0.6 + 0.5 * g), 0.7);
	col       *= mix(0.82, 1.0, g);                // soft contact darkening only at the very base
	ALBEDO    = col;
	ROUGHNESS = mix(0.82, 0.62, g);                // matte; minimal glint (no dark spec angles)
	SPECULAR  = 0.18;
	BACKLIGHT = vec3(0.45, 0.52, 0.24) * (0.4 + 0.6 * g * g);  // translucency keeps thin blades lit
}

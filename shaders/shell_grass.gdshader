shader_type spatial;
render_mode cull_disabled, world_vertex_coords;

// Shell-textured mown turf (POC promoted to in-game eval, 2026-06-29).
// A camera-following tessellated patch is drawn N times by a MultiMesh; each
// instance is one horizontal "shell" lifted by layer*grass_height, and the
// fragment shader carves blades out of each shell with discard. Stacked, the
// shells read as a continuous grass carpet from ANY angle (the top-down case
// the card/tuft grass could never solve). The patch CONFORMS to the terrain by
// sampling the project heightmap per-vertex (decode_terrain.gdshaderinc), so it
// follows hills instead of sitting on a flat plane.

// --- terrain height sampling — conform to TERRAIN3D's real surface (not the divergent
// heightmap.bin) so the shell agrees with the ground and the turf. hm_world_size is kept
// only for splat_uv() (landuse/wear map lookups), not for height. ---
uniform float hm_world_size = 5000.0;
#include "res://shaders/include/terrain3d_height.gdshaderinc"
// Shared, calibrated grass color field — the SAME function the terrain shader
// uses for its grass zones (fantasy_grass_color). Coloring the shell blades from
// this instead of hardcoded greens makes the near grass and the far terrain
// "felt" one continuous field, so the patch edge stops reading as a seam.
// (grass_zone_colors requires vnoise/fbm3 from hash_noise — include it first.)
#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/grass_zone_colors.gdshaderinc"

// --- zone + wear data (same maps the particle grass uses) ---
// Zone IDs (docs/grass.md §2): 0=unzoned 1=garden 2=grass(named lawns) 3=pitch
//   4=playground 5=nature_reserve 6=dog_park 7=sports 8=pool 9=track 10=wood
//   11=forest 12=water 13=shore 14=wild_meadow
uniform sampler2D landuse_map : filter_nearest, repeat_disable;
uniform sampler2D wear_map    : filter_linear,  repeat_disable;

// Fantasy toggle (mirrors terrain3d_override + grass_particle_render): 1.0 =
// lush idealized green (fantasy_grass_color); <0.5 = data-driven Central Park
// palette (grass_base_color_no_dead + turf wear), so the shell felt matches the
// terrain felt in BOTH modes and the patch edge never reads as a color seam.
uniform float fantasy : hint_range(0.0, 1.0) = 1.0;
// Aesthetic mode (GRASS_LUSH): suspend the data-driven foot-traffic wear so worn
// lawns (e.g. The Mall) stay lush green instead of eroding to tan dirt. Only the
// most extreme wear still erodes. Matches grass_blades.gdshader's aesthetic flag.
uniform float aesthetic : hint_range(0.0, 1.0) = 1.0;
// Near-field clear: when the 3D blade band owns the near ground, don't draw the shell
// there (it would only be hidden). The shell fades IN past near_clear_r so it fills the
// ground BEYOND the blade band. near_clear_r=0 disables (blades off → shell everywhere).
uniform vec2  near_center     = vec2(0.0);
uniform float near_clear_r    = 0.0;
uniform float near_clear_fade = 6.0;
uniform int   shell_count  = 32;
uniform float density       = 33.0;   // blade cells per meter
// blade_len/blade_wid are now the BASE half-extents (near-full cell), so the
// lowest shells of neighbouring cells MERGE into a continuous sward that hides
// the terrain beneath; the footprint tapers to a thin point at the tip.
uniform float blade_len     = 0.62;   // base half-length along the blade (cell frac)
uniform float blade_wid     = 0.46;   // base half-width across the blade (cell frac)
uniform float lean_amt      = 0.62;   // blade lean (cell frac)
uniform float mat_height    = 0.30;   // shell fraction below which the dense mat is solid
// (Blade colors are no longer uniforms — derived per-fragment from the shared
// fantasy_grass_color field so they track the terrain felt exactly.)
// Patch fade: the camera-following patch dissolves into the terrain in its outer
// ring so it never reads as a hard disc. Center is pushed per-frame from main.gd.
uniform vec2  patch_center  = vec2(0.0);
uniform float patch_radius  = 72.0;   // metres from center where grass is fully gone
uniform float patch_fade    = 34.0;   // width of the dissolve ring (long, so no visible ring)

varying float v_layer;
varying vec3  v_world;

vec2 splat_uv(vec2 w){ return (w + hm_world_size * 0.5) / hm_world_size; }
// Jitter the sample position with a world-space hash (±0.9m) so int-zone
// boundaries dither organically instead of rendering the landuse texel grid as
// hard axis-aligned staircases — this is the blocky teal "quilt" the shell patch
// showed along the lakeshore (cpw_004/005/006). Uses the SAME hash2*13.1 jitter
// as terrain3d_override so the dithered water/shore band lines up with the felt.
int zone_at(vec2 w){
	vec2 jit = vec2(hash2(w * 13.1), hash2(w * 13.1 + vec2(7.3, 41.9))) - 0.5;
	return int(texture(landuse_map, splat_uv(w + jit * 1.8)).r * 255.0 + 0.5);
}
bool zone_is_unmown(int z){ return z == 5 || z == 10 || z == 11 || z == 13 || z == 14; }

// Per-zone standing height in METERS (CPC Turf Care Handbook; docs/grass.md §3).
// Each shell stack lifts to ITS OWN zone height, so a mown lawn packs all shells
// densely while a meadow spreads them — no global-max waste on the common case.
float zone_height_m(int z){
	if (z == 8 || z == 12) return 0.0;    // pool / water — no grass
	if (z == 1)            return 0.07;   // formal garden panels ~7cm
	if (z == 2)            return 0.085;  // named lawns (A/B) ~8.5cm
	if (z == 3 || z == 7 || z == 9) return 0.07;  // pitch/sports/track ~7cm
	if (z == 4 || z == 6)  return 0.08;   // playground / dog park ~8cm
	if (z == 0)            return 0.10;   // unzoned fringe ~10cm
	if (z == 5)            return 0.22;   // nature reserve (Hallett) unmown ~22cm
	if (z == 10 || z == 11) return 0.17;  // woodland floor ~17cm
	if (z == 13)           return 0.20;   // shore sedge ~20cm
	if (z == 14)           return 0.30;   // wild meadow ~30cm
	return 0.085;                          // default: treat as mown lawn
}

// Hash21/22 (Hoskins) — no axis symmetry, so no mirror seam at x=0/z=0.
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
// vnoise/fbm3 come from hash_noise.gdshaderinc (shared with the terrain shader,
// so the macro patchiness lines up across the near-grass / far-felt boundary).

void vertex(){
	float f = float(INSTANCE_ID) / float(max(shell_count - 1, 1));
	v_layer = f;
	// world_vertex_coords: VERTEX is already world-space. Snap each shell onto
	// the terrain surface, then lift it by this zone's standing height.
	float ground = sample_terrain(VERTEX.xz);
	VERTEX.y = ground + f * zone_height_m(zone_at(VERTEX.xz));
	v_world = VERTEX;
}

void fragment(){
	vec2 world = v_world.xz;
	float f = v_layer;

	// --- zone + wear (data-driven, same maps as the particle grass) ---
	int  zone   = zone_at(world);
	if (zone == 8 || zone == 12) discard;          // pool / water — no grass
	bool unmown = zone_is_unmown(zone);
	float wear  = texture(wear_map, splat_uv(world)).r;
	// Effective wear for erosion/drying — suppressed in aesthetic mode so worn lawns
	// stay a lush continuous sward (only near-total wear still erodes).
	float wear_e = aesthetic > 0.5 ? wear * 0.15 : wear;

	// --- patch edge dissolve: thin coverage toward the rim so the camera-following
	// patch melts into the terrain instead of ending in a visible disc. ---
	float edge = 1.0 - smoothstep(patch_radius - patch_fade, patch_radius,
		length(world - patch_center));

	// --- patch-scale variation (low frequency) ---
	float patchH = vnoise(world * 0.55 + 31.0);
	float sparse = vnoise(world * 0.40 + 7.0);

	// --- per-blade cell ---
	// Domain-warp the lattice before flooring so cell boundaries CURVE instead of
	// running in long straight world-axis rows. Straight down, an axis-aligned grid
	// of cells reads as Minecraft turf-blocks (Chris's walk, cpw_000). The warp is
	// low-frequency (~5m) so neighbouring cells still merge into a continuous mat at
	// eye level — only the top-down row regularity is broken. Rotated octaves so the
	// warp field itself carries no axis lattice.
	vec2 wrot = mat2(vec2(0.80, -0.60), vec2(0.60, 0.80)) * world;
	vec2 warp = vec2(vnoise(wrot * 0.19 + 4.0), vnoise(wrot * 0.19 + 19.0)) - 0.5;
	vec2 uv    = (world + warp * 3.0) * density;
	vec2 cell  = floor(uv);
	vec2 local = fract(uv) - 0.5;
	float r1   = hash21(cell);
	// Stronger per-cell position jitter (±0.42 vs ±0.25) so the bumps don't sit on a
	// regular grid from above — the other half of the Minecraft cue.
	local -= (hash22(cell) - 0.5) * 0.84;

	// Coverage model: every cell forms a dense MAT up to mat_height so the lowest
	// shells knit into a continuous sward (the terrain never shows through as
	// "felt"); ABOVE the mat only a `keep` fraction of cells grow individual tall
	// blades. Foot-traffic wear erodes the mat AND thins the tall blades so paths
	// go to bare ground.
	float keep = mix(0.78, 0.97, sparse);   // fraction of cells with tall blades
	if (unmown) keep *= 0.92;
	float mat = mat_height * (1.0 - smoothstep(0.20, 0.62, wear_e));   // mat erodes on paths
	keep *= 1.0 - smoothstep(0.15, 0.6, wear_e) * 0.98;
	// Near-field clear: fade the shell OUT inside the blade zone (blades own it) and
	// IN beyond it, so the shell is only drawn where it does real work (the distance).
	float near_vis = near_clear_r > 0.01
		? smoothstep(near_clear_r, near_clear_r + near_clear_fade, distance(world, near_center))
		: 1.0;
	keep *= near_vis;
	mat  *= near_vis;
	if (near_vis < 0.02) discard;

	// Rim dissolve: thin height (mat), tall-blade count (keep), and drop whole
	// cells stochastically so the patch grades into terrain instead of a disc edge.
	keep *= edge;
	mat  *= edge;
	if (hash21(cell + 7.7) > smoothstep(0.0, 0.35, edge)) discard;
	bool tall = hash21(cell + 3.3) <= keep;
	if (f > mat && !tall) discard;          // above the mat, only tall-blade cells survive
	if (f > mat && mat <= 0.001) discard;    // fully worn / past rim: no mat, no blades

	// --- combing: coherent per-area flow direction + STRONG per-blade scatter ---
	// A uniform per-area comb makes every blade rake the same way -> reads as
	// corduroy/aligned spikes from above. Two hashes widen the per-blade angular
	// spread (~±2 rad) so the sward looks tousled, not brushed.
	float ang = vnoise(world * 0.16) * 6.2831
	          + (r1 - 0.5) * 2.4 + (hash21(cell + 5.1) - 0.5) * 1.6;
	vec2  dir = vec2(cos(ang), sin(ang));
	// Linear lean term tilts even low shells (pure-vertical bases empty the
	// nadir top-down); quadratic term bends the tip over further than the base.
	local -= dir * (f * 0.35 + f * f * 0.65) * lean_amt;

	// --- blade height: mowing homogenizes (±10%), unmown keeps natural clumping
	// (±30%); wear shortens what blades survive. The mat is always at least
	// mat_height tall so it stays solid.
	float hv_lo = unmown ? 0.55 : 0.80;
	float hv_hi = unmown ? 1.35 : 1.12;
	float bh = clamp(mix(0.5, 1.0, r1) * mix(hv_lo, hv_hi, patchH), 0.0, 1.0);
	bh *= mix(1.0, 0.40, smoothstep(0.1, 0.6, wear_e));
	bh = max(bh, mat);
	if (f > bh) discard;

	// --- coverage. The bottom couple of shells (f < floor_solid) fill the WHOLE
	// cell with NO footprint test, a genuinely opaque skin that occludes the
	// terrain so it can never show through as black speckle on a shaded slope —
	// only 2 of 32 shells, so the overdraw cost is tiny. Above that the footprint
	// tapers from a wide overlapping base (mat body) to a thin point (blade tip).
	const float floor_solid = 0.06;
	vec2 rl = vec2(dot(local, dir), dot(local, vec2(-dir.y, dir.x)));
	if (f >= floor_solid) {
		float t = smoothstep(mat, bh, f);   // 0 through the mat body, 1 at blade tip
		float halfL = mix(blade_len, 0.12, t);
		float halfW = mix(blade_wid, 0.020, t);
		// ELLIPTICAL (rounded) footprint, not a hard rectangle: straight down, a grid
		// of rectangular tips reads as crisp angular "spikes" (Chris: minecraft spikes,
		// not realistic). A rounded cross-section that tapers to a soft (not needle)
		// tip reads as blade, not chip.
		float rx = rl.x / max(halfL, 1e-4);
		float ry = rl.y / max(halfW, 1e-4);
		if (rx * rx + ry * ry > 1.0) discard;
	}

	// --- colour: derived from the SHARED grass field (fantasy_grass_color) so the
	// blades are the same hue/value as the terrain "felt" they sit in — the patch
	// edge then has nothing to transition BETWEEN, and the macro patchiness lines up
	// across the boundary because both call the same noise. ---
	// Felt color: realistic data-driven zone palette, or the lush fantasy green —
	// identical to the terrain3d_override grass-zone path so near grass and far
	// felt are one continuous field.
	vec3 felt = (fantasy < 0.5)
		? grass_base_color_no_dead(zone, world)
		: fantasy_grass_color(world);
	// Shore (zone 13): the sedge palette is a cool saturated teal. Applied as a
	// flat strip it read as a painted teal band (cpw_004/005/006). Blend it in by
	// tussock patches over bank grass so it reads as clumped wetland vegetation —
	// identical to terrain3d_override's shore handling so blades match the felt.
	if (fantasy < 0.5 && zone == 13) {
		felt = mix(grass_base_color_no_dead(0, world), felt, sedge_patch_mask(world));
	}
	// Vertical gradient: shaded base → lit tip, both shades of the SAME felt color
	// (a darker green, never a contrasting brown). Remapped to start part-way up so
	// tall blades don't EMERGE from the mat as near-black pepper specks.
	float vgrad = clamp(f * 0.62 + 0.34, 0.0, 1.0);
	vec3  col = felt * mix(0.60, 1.06, vgrad);
	col *= mix(0.93, 1.07, r1);               // per-blade vitality jitter
	// AO deepens toward the soil so the near sward reads 3D; the understory shade is
	// a DARK felt (same hue), so worn/thinned spots look like shadow in the sward,
	// not the black/brown holes a contrasting understory color produced.
	float ao = mix(0.66, 1.0, smoothstep(0.0, 0.85, f));
	vec3 understory_c = felt * 0.46;
	// Toward the patch RIM (edge→0) fade the shading OUT to flat felt: blades aren't
	// resolved at that distance, so converging the mat to the terrain color makes the
	// handoff seamless instead of the dark/brown moat ring the old understory left.
	ao = mix(1.0, ao, edge);
	understory_c = mix(felt, understory_c, edge);
	ALBEDO = mix(understory_c, col, smoothstep(0.0, mat_height + 0.10, f)) * ao;

	// Realistic mode: pull worn/compacted patches toward dried turf + dirt so the
	// near sward matches the terrain felt (which calls apply_turf_wear with the
	// same wear). Includes ambient mottle (turf_wear_total) for mown zones; canopy
	// compaction is omitted here (no canopy_map on this patch) — paths/benches and
	// ambient mottle are the dominant signal. Skipped in fantasy mode (no dirt).
	if (fantasy < 0.5) {
		float color_wear = turf_wear_total(wear, 0.0, zone, world);
		if (aesthetic > 0.5) color_wear *= 0.20;   // keep worn lawns green, not tan
		ALBEDO = apply_turf_wear(ALBEDO, color_wear, world);
	}

	// --- shading: flatter ribbon normal, softer varied specular ---
	vec3 n = normalize(vec3(rl.y * 0.5 * dir.x, 1.0, rl.y * 0.5 * dir.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ROUGHNESS = mix(0.55, 0.80, hash21(cell + 9.1));
	SPECULAR  = 0.25;
	BACKLIGHT = vec3(0.25 * f);
}

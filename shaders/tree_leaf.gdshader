shader_type spatial;
// OPAQUE pass (2026-06-10, docs/trees.md §4): no ALPHA write, no A2C —
// coverage is discard-only, so leaves get early-Z and shade once per pixel
// instead of once per canopy layer (was −18 ms at Ramble). Seasonal thinning
// is per-CARD stochastic drop (v_leaf_seed vs density), not alpha ghosting.
render_mode cull_disabled, depth_prepass_alpha;

uniform vec3 albedo_tint = vec3(0.28, 0.48, 0.18);
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic;

global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float season_t;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;
// Player camera world position. Pushed each frame from main.gd. Use this
// (not INV_VIEW_MATRIX[3]) for distance-based effects (LOD dither, aerial
// perspective) so the calculation stays consistent across shadow and
// reflection passes whose INV_VIEW_MATRIX reflects the light/probe view.
global uniform vec3 player_world_pos;
// Crown-interior AO mapping (trees.md §6): x = AO at the crown core,
// y = exponent on the baked crown radius rho (COLOR.a), z = AO at the
// outer shell (< 1: even shell leaves see ~half the sky hemisphere, and
// scene ambient is calibrated for unobstructed ground). Registered in
// main.gd; sweep via --canopy-ao=core:exp:shell.
global uniform vec3 canopy_ao;

// LOD crossfade dither ranges (begin, end). Set per LOD tier.
// vec2(0,0) = no dithering (default).
uniform vec2 lod_fade_out = vec2(0.0, 0.0);
uniform vec2 lod_fade_in = vec2(0.0, 0.0);

// Per-tier brightness compensation. LOD1 decimated mesh has less self-shadowing
// than LOD0 full mesh, so it reads brighter at the same camera distance.
// Set to ~0.82 on LOD1 materials to match LOD0 perceived brightness.
uniform float tier_brightness : hint_range(0.4, 1.5) = 1.0;

// IMPOSTOR BAKE MODE (scripts/bake_impostors.gd). 0 = normal render. When set,
// the fragment outputs one octahedral-atlas channel UNSHADED via EMISSION so the
// runtime-lit impostor (shaders/tree_impostor.gdshader) re-lights it at distance —
// NOT a baked-lit atlas (the double-lit bug class). 1 = albedo (leaf colour with
// the dapple self-shadow folded in, but BEFORE the top-lit/fresnel directional fakes
// — runtime normal lighting supplies directionality); 2 = camera-space normal
// (0.5+0.5 packed); 3 = ORM (R = crown-interior AO re-applied ambient-only by the
// impostor so the far tier isn't ~1.5x too bright, G = roughness, B = metallic).
// Discard/coverage shares the normal render's code path EXCEPT it can drop a
// fraction of cluster cards during the bake: a full-density (1.0) crown PROJECTS
// solid at the bake's resolution (every card front+back covers the interior), so
// the baked atlas read ~0.64-0.74 filled vs the live mesh's see-through ~0.38-0.58
// at the handoff distance (the mesh loses small/far cards to sub-pixel rasterisation
// the high-res bake doesn't) => the impostor was a solid blob, "fuller/bigger than
// lod1" (measured 2026-06-24). bake_density (0..1) reuses the seasonal per-card drop
// (v_card_seed) to punch matching card-scale holes so the atlas coverage matches the
// mesh; -1 = no bake drop (live density).
uniform int bake_mode = 0;
uniform float bake_density = -1.0;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"
#include "res://shaders/include/tree_species.gdshaderinc"
#include "res://shaders/include/wind.gdshaderinc"
#include "res://shaders/include/lod_dither.gdshaderinc"

varying float v_leaf_density;
varying vec3 v_leaf_color;
varying float v_blossom;     // 0-1 blossom intensity (cherry/callery pear spring bloom)
varying float v_species_idx; // species index for fragment shader
// Per-cluster hash for stochastic seasonal card drop. flat = no interpolation
// (the provoking vertex's value covers the triangle); ~0.8m world quantization
// makes leaves on the same twig drop together, like real abscission.
varying flat float v_card_seed;
varying float v_crown_rho;   // COLOR.a: 0 = crown core, 1 = outer shell

// Spring blossom colors: cherry = pink, callery_pear = white, magnolia = pink-white
const vec3 BLOSSOM_COLORS[14] = vec3[14](
	vec3(0.0),                     // 0 oak: no blossoms
	vec3(0.0),                     // 1 maple: no blossoms
	vec3(0.0),                     // 2 elm: no blossoms
	vec3(0.0),                     // 3 birch: no blossoms
	vec3(0.0),                     // 4 deciduous: no blossoms
	vec3(0.0),                     // 5 conifer: no blossoms
	vec3(0.0),                     // 6 honeylocust: no blossoms
	vec3(0.92, 0.90, 0.85),       // 7 callery_pear: white blossoms (Bradford pear)
	vec3(0.0),                     // 8 ginkgo: no blossoms
	vec3(0.0),                     // 9 london_plane: no blossoms
	vec3(0.0),                     // 10 linden: no blossoms
	vec3(0.88, 0.68, 0.72),       // 11 cherry: Yoshino pale pink blossoms
	vec3(0.0),                     // 12 willow: no showy blossoms
	vec3(0.90, 0.72, 0.78)        // 13 magnolia: pink-white tulip-shaped blooms
);

// BLOSSOM_TIMING moved to include/tree_species.gdshaderinc (shared with the
// shadow-proxy shader so blossoming crowns cast like foliage).

void vertex() {
	// Decode per-instance season data (all INSTANCE_CUSTOM reads in vertex only)
	float is_evergreen = INSTANCE_CUSTOM.b;
	int sp_idx = int(INSTANCE_CUSTOM.r * 13.0 + 0.5);
	float timing_off = INSTANCE_CUSTOM.g - 0.5;
	float s = mod(season_t + timing_off, 4.0);
	v_species_idx = float(sp_idx);

	// Compute leaf density for vertex shrinking and fragment alpha.
	// Two independent curves: spring growth ramps up, fall shedding ramps down.
	// min() ensures density is only high when BOTH agree (growing season).
	// Marcescent species (oak, london plane) retain dead leaves through winter
	// via WINTER_RETENTION floor; clean abscission species drop to near-zero.
	float leaf_density = 1.0;
	if (is_evergreen < 0.5) {
		vec4 ph = PHENOLOGY[sp_idx];
		float retention = WINTER_RETENTION[sp_idx];
		float grow = smoothstep(ph.w - 0.1, ph.w + 0.3, s);   // spring ramp-up
		float shed = 1.0 - smoothstep(ph.z - 0.2, ph.z + 0.3, s); // fall ramp-down
		float canopy = min(grow, shed);  // full only when both say yes
		leaf_density = mix(retention, 1.0, canopy);
		// No floor: with per-card drop, density 0 = truly bare (clean
		// abscission). The old 0.08 floor was for the alpha-ghost regime.
	}
	v_leaf_density = leaf_density;

	// Spring blossom phase (cherry, callery pear)
	float blossom = 0.0;
	vec3 bt = BLOSSOM_TIMING[sp_idx];
	if (bt.y > 0.0) {  // species has blossoms
		// Ramp up to peak, then fade
		float bloom_up = smoothstep(bt.x, bt.y, s);
		float bloom_dn = 1.0 - smoothstep(bt.y, bt.z, s);
		blossom = bloom_up * bloom_dn;
		// Blossoms boost density during bloom (full canopy of flowers)
		leaf_density = max(leaf_density, blossom * 0.85);
		v_leaf_density = leaf_density;
	}
	v_blossom = blossom;

	// Compute seasonal leaf color in vertex, pass to fragment via varying
	// Use per-species summer color instead of uniform tint
	vec3 species_green = SUMMER_COLORS[sp_idx];
	vec3 leaf_color = species_green;
	if (is_evergreen < 0.5) {
		vec4 ph = PHENOLOGY[sp_idx];
		vec3 fall_col = FALL_COLORS[sp_idx];
		vec3 spring_tint = species_green * vec3(1.15, 1.2, 0.7);
		float spring_t = smoothstep(ph.w, ph.w + 0.4, s);
		leaf_color = mix(spring_tint, species_green, spring_t);
		float fall_t = smoothstep(ph.x, ph.y, s);
		leaf_color = mix(leaf_color, fall_col, fall_t);
		float late_fall = smoothstep(ph.y, ph.z, s);
		leaf_color = mix(leaf_color, fall_col * 0.5, late_fall * 0.6);
	}
	// Blend blossom color during bloom
	if (blossom > 0.01) {
		vec3 blossom_col = BLOSSOM_COLORS[sp_idx];
		// Per-tree variation: some trees slightly pinker/whiter
		blossom_col += (timing_off * 0.06) * vec3(0.08, -0.04, -0.02);
		leaf_color = mix(leaf_color, blossom_col, blossom * 0.9);
	}
	// Per-tree color variation: brightness ±12%, warm/cool ±shift
	float jitter = INSTANCE_CUSTOM.a;
	float bright_off = (jitter - 0.5) * 0.25;
	leaf_color *= 1.0 + bright_off;
	float warm_off = fract(jitter * 7.37) - 0.5;
	leaf_color += warm_off * vec3(0.025, -0.008, -0.03);

	// Per-leaf jitter — each leaf card hashes its world XZ (quantized to 5 cm)
	// so all 4 vertices of one card share a seed and neighboring cards differ.
	// Sits between per-tree (±12%) and per-pixel (±4%) variation in scale.
	vec3 leaf_world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float leaf_seed = hash2(floor(leaf_world_pos.xz * 20.0));
	// Upper-crown cards drop first (marcescence holds low/inner leaves):
	// lower-crown seeds compress into [0, 0.7] so they survive to deeper
	// retention. Model space is 0..5 units tall (MODEL_H normalization).
	float upper01 = smoothstep(2.0, 4.2, VERTEX.y);
	v_card_seed = hash2(floor(leaf_world_pos.xz * 1.3) + floor(leaf_world_pos.y * 1.3))
		* mix(0.7, 1.0, upper01);
	float leaf_bright = (leaf_seed - 0.5) * 0.12;                // ±6%
	float leaf_warm   = (fract(leaf_seed * 13.7) - 0.5) * 0.04;
	leaf_color *= 1.0 + leaf_bright;
	leaf_color += leaf_warm * vec3(0.04, -0.01, -0.04);

	v_leaf_color = leaf_color;

	// --- Per-species wind biomechanics (shared wind include) ---
	vec4 wp = WIND_PARAMS[sp_idx];
	float trunk_flex = wp.x;
	float branch_flex = wp.y;
	float sway_freq = wp.z;
	float gust_resp = wp.w;

	vec3 tree_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float h = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);
	float rustle = (0.3 + wind_str * 0.7) * mix(0.3, 1.0, leaf_density);
	float phase = wind_phase(tree_origin);

	float branch_phase = COLOR.b * 6.283 + phase;
	float crown = smoothstep(1.5, 4.0, h);
	v_crown_rho = COLOR.a;

	// Thin, higher-order branches whip far more than the thick limb base. COLOR.r
	// = hierarchy depth (trunk 0 -> branch tip 1), COLOR.g = branch extent (branch
	// base 0 -> tip 1); both rise toward the flexible extremities (leaf cards
	// inherit their parent twig's values). Weighting the secondary sway by them
	// decouples twig/leaf flutter from absolute height.
	float branch_flex_w = branch_flex * (1.0 + COLOR.r * 1.8) * (0.6 + 0.4 * COLOR.g);

	// Cantilever trunk + branch sway + wind push (leaves: higher amplitudes than bark)
	vec2 trunk_d = wind_cantilever_trunk(h, sway_freq, trunk_flex, rustle, phase);
	vec2 branch_d = wind_branch_sway(h, crown, sway_freq, branch_flex_w, branch_phase, rustle, 0.08, 0.05);
	vec2 push_d = wind_push(wind_vec, h, 0.18, trunk_flex);
	VERTEX.x += trunk_d.x + branch_d.x + push_d.x;
	VERTEX.z += trunk_d.y + branch_d.y + push_d.y;

	// Gusts (leaves catch more wind than bark)
	float gust = wind_gust(tree_origin, 0.3, 3.0);
	float gust_strength = gust * wind_str * 0.25 * gust_resp;
	VERTEX.x += wind_vec.x * h * gust_strength;
	VERTEX.z += wind_vec.y * h * gust_strength;

	// Leaf flutter: high-frequency per-leaf vibration
	float flutter = sin(TIME * 3.5 + VERTEX.x * 11.0 + VERTEX.z * 7.0) * 0.012 * rustle;
	flutter += sin(TIME * 5.7 + VERTEX.z * 17.0) * 0.006 * gust_strength;
	VERTEX.y += flutter * h;

	// Winter: retained (marcescent) leaves sit closer to the branches.
	// Softened from 0.4 since cards are now opaque — a hard shrink pancaked
	// the surviving cards into a dense blob at the trunk.
	if (is_evergreen < 0.5 && leaf_density < 0.5) {
		float shrink = mix(0.7, 1.0, leaf_density * 2.0);
		VERTEX.xz *= shrink;
	}
}

void fragment() {
	// Seasonal card drop: a cluster whose seed exceeds current leaf density
	// is gone — whole leaves detach (real abscission), replacing the old
	// alpha *= density ghosting that an opaque threshold would cliff on.
	// First statement so the depth prepass rejects dropped cards cheaply.
	// 0.96 keeps the winter retention floor (density 0.08 → ~8% of cards).
	float drop_density = v_leaf_density;
	// Impostor bake: thin cards to the handoff-distance coverage (a full-density
	// crown projects solid at bake res; the live mesh is see-through at distance).
	if (bake_mode > 0 && bake_density >= 0.0) drop_density = bake_density;
	if (v_card_seed * 0.96 > drop_density) {
		discard;
	}
	vec4 tex = texture(albedo_tex, UV);
	float lum = dot(tex.rgb, vec3(0.3, 0.6, 0.1));
	float alpha = tex.a;

	// [DIAG-DISABLED 2026-05-18] Mip-level alpha compensation disabled — was
	// causing visible color steps as mips shifted with distance. Left commented
	// in case the lod1 distance handoff degrades and we need it back, targeted.
	// float delta_max = max(length(dFdx(UV)), length(dFdy(UV)));
	// float mip_level = max(log2(max(delta_max * 1024.0, 1.0)), 0.0);
	// alpha *= 1.0 + mip_level * 0.3;
	// alpha = min(alpha, 1.0);

	// [DIAG-DISABLED 2026-05-18] Second LOD system disabled for A/B comparison.
	// Was: distance-adaptive alpha threshold ramping discard 0.15→0.02 over 60-180m.
	vec3 frag_tree_pos = MODEL_MATRIX[3].xyz;
	// player_world_pos (not INV_VIEW_MATRIX[3]) so the dither discards
	// correctly in shadow/reflection passes.
	float frag_cam_dist = length(frag_tree_pos - player_world_pos);

	// Coverage-preserving discard threshold, driven by the SAMPLED MIP —
	// not camera distance. Box-filtered mips dilute alpha (binary at mip 0,
	// graded above), so a fixed high threshold deletes small or edge-on
	// cards wholesale. The old 100-180m camera ramp caused the Jun 11
	// "leaves vanish as you approach" defect: walking in raised the
	// threshold to 0.5 while edge-on under-crown cards kept sampling high
	// mips whose alpha never reaches it. Mip 0 keeps 0.5 (crisp leaf
	// shapes, halo pixels cut); by mip 4 the threshold reaches 0.10 (the
	// dilated silhouette IS the leaf mass — keeping it preserves canopy
	// density). Unlike the May 18 alpha-boost attempt (color steps via
	// ALPHA blending), a threshold can't shift shading — surviving
	// fragments shade identically.
	float alpha_lod = textureQueryLod(albedo_tex, UV).y;
	if (alpha < mix(0.5, 0.10, clamp(alpha_lod * 0.25, 0.0, 1.0))) discard;

	// LOD crossfade: complementary dithering at tier boundaries.
	// Outgoing: this tier dissolves away as camera moves beyond its range.
	// Incoming: this tier dissolves in as camera enters from the previous tier.
	// TAA smooths the dither pattern across frames.
	if (lod_fade_out.y > 0.0 && frag_cam_dist > lod_fade_out.x) {
		if (lod_dither_discard(frag_cam_dist, lod_fade_out.x, lod_fade_out.y,
		                       FRAGCOORD.xy, false)) discard;
	}
	if (lod_fade_in.y > 0.0 && frag_cam_dist < lod_fade_in.y) {
		if (lod_dither_discard(frag_cam_dist, lod_fade_in.x, lod_fade_in.y,
		                       FRAGCOORD.xy, true)) discard;
	}

	vec3 col = v_leaf_color * (0.50 + lum * 0.50);  // texture luminance modulation (raised floor for denser canopy read)

	// Within-leaf gradient: base (greener, denser chlorophyll) → tip (warmer, yellower).
	// Assumes Mtree UV convention with leaf running 0=base to 1=tip along UV.y.
	// Flipped UVs across leaves average out, so worst-case is half the leaves
	// carry the gradient inverted — still adds variation. Suppressed on blossoms
	// where petal patterns are radial, not axial.
	vec3 grad_tint = mix(vec3(0.96, 1.03, 0.92), vec3(1.05, 0.99, 0.86), UV.y);
	grad_tint = mix(grad_tint, vec3(1.0), v_blossom);
	col *= grad_tint;

	int sp = int(v_species_idx + 0.5);
	// Desaturate slightly — preserve species hue while keeping it natural
	float leaf_lum = dot(col, vec3(0.299, 0.587, 0.114));
	col = mix(vec3(leaf_lum), col, 0.80);  // 20% desaturation (keeps green vibrancy)
	col *= vec3(0.96, 0.94, 0.88);  // subtle warm darken (lighter than before)

	// Impostor albedo snapshot: pure leaf colour (species hue + texture luminance +
	// per-tree/leaf variation + within-leaf gradient) BEFORE the top-lit gradient,
	// dapple and fresnel directional fakes below. The runtime-lit impostor supplies
	// directionality from the normal atlas, so baking those fakes in would double-light.
	vec3 bake_albedo = col;

	// --- Top-lit canopy gradient: world-space normal creates 3D depth ---
	// Sunlit top = bright, shaded underside = darker blue-shifted.
	// This is the single biggest cue for 3D canopy shape.
	vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
	float top_lit = world_n.y * 0.5 + 0.5;  // 0=facing down, 1=facing up
	col *= mix(0.86, 1.08, top_lit);  // 86% underneath — less harsh underside darkening
	// Underside gets warm ground-bounce (green grass reflects up into canopy)
	// plus cool sky-fill — fakes indirect illumination without GI
	float underside = (1.0 - top_lit);
	col = mix(col, col * vec3(0.96, 1.02, 0.94), underside * 0.20);  // warm green bounce
	col = mix(col, col * vec3(0.94, 0.96, 1.04), underside * 0.10);  // cool sky fill

	// --- Fresnel rim light: leaf edges glow at grazing view angles ---
	// Real leaves show bright translucent edges when viewed at shallow angles
	float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), 3.0);
	col += col * fresnel * 0.18;

	// --- Distance gates for procedural detail (docs/trees.md §4c lever 1) ---
	// Each detail layer fades its AMPLITUDE to zero over the range where its
	// features go sub-pixel at 1080p, and the noise evaluations are skipped
	// beyond it. frag_cam_dist is per-tree, so the branches are coherent
	// across each tree's fragments. Near field (< the fade start) runs the
	// exact pre-gate code path — pixel-identical by construction.
	float gate_micro = 1.0 - smoothstep(25.0, 40.0, frag_cam_dist);  // cuticle/vein bumps
	float gate_leaf  = 1.0 - smoothstep(50.0, 80.0, frag_cam_dist);  // per-leaf pockets/detail
	float gate_px    = 1.0 - smoothstep(15.0, 25.0, frag_cam_dist);  // per-pixel hash variation

	// --- Procedural leaf micro-texture: veins, cell structure, surface bumps ---
	// Real leaves have complex surface topology that catches light at micro-scale.
	// Two noise octaves: coarse (vein ridges) + fine (cell/cuticle texture).
	vec3 frag_world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float bump_coarse = 0.5;  // neutral when gated (rough_var → 0)
	if (gate_micro > 0.001) {
		bump_coarse = vnoise(frag_world.xz * 45.0);
		float bump_fine = vnoise(frag_world.xz * 110.0);
		float bump_h = bump_coarse * 0.6 + bump_fine * 0.4;
		// Perturb normal via screen-space height derivatives (subtle — just enough
		// to break up uniform lighting, not enough to flip normals or wash out)
		NORMAL = normalize(NORMAL + vec3(dFdx(bump_h), dFdy(bump_h), 0.0) * (1.2 * gate_micro));
		bump_coarse = mix(0.5, bump_coarse, gate_micro);
	}

	// Within-canopy detail: simulate individual leaf shadows, overlap, light pockets
	vec3 tree_pos = MODEL_MATRIX[3].xyz;
	if (gate_leaf > 0.001) {
		float detail_n = vnoise(UV * 12.0 + tree_pos.xz * 0.5);  // per-leaf-scale noise
		float pocket_n = vnoise(UV * 4.0 + tree_pos.xz * 0.3);   // shadow pocket scale
		// Dark shadow pockets in canopy interior
		col *= mix(1.0, 0.78, smoothstep(0.3, 0.6, pocket_n) * 0.15 * gate_leaf);
		// Per-leaf brightness variation (some leaves catch more light)
		col *= mix(1.0, 0.92 + detail_n * 0.16, gate_leaf);
	}

	// --- Dappled canopy light/shadow patches (world-space) ---
	// Real tree canopies show large-scale dappling as sunlight filters
	// through upper foliage. Two octaves in world coords — survives mip
	// averaging, so the pattern stays vivid at LOD1+ distance where the
	// UV-space per-leaf detail above goes sub-pixel and washes flat.
	// Bias toward sun-exposed (most pixels stay near 1.0×); a minority
	// sit in deeper shade pockets, a few catch sun-spots.
	float dapple_main = vnoise(frag_world.xz * 0.35 + frag_world.y * 0.08);
	float dapple_sub  = vnoise(frag_world.xz * 1.10);
	float dapple = dapple_main * 0.72 + dapple_sub * 0.28;
	dapple = smoothstep(0.22, 0.88, dapple);
	col *= mix(0.72, 1.12, dapple);

	// Per-pixel micro-variation: chlorophyll patches, dust, cell structure
	// Real leaves have millions of unique shades across their surface
	if (gate_px > 0.001) {
		vec2 px_uv = UV * 97.3 + tree_pos.xz * 5.1;
		float px_n = hash2(px_uv) * 0.08 - 0.04;             // ±4% brightness
		float px_hr = hash2(px_uv + vec2(71.9, 0.0)) * 0.03;  // warm shift
		float px_hb = hash2(px_uv + vec2(0.0, 53.1)) * 0.03;  // cool shift
		col += vec3(px_n + px_hr, px_n, px_n + px_hb) * gate_px;
	}

	// --- Species-specific material properties ---
	// Broad-leaved trees (maple, london plane) have smoother, more reflective leaves
	// Compound-leaved (honeylocust) and small-leaved (birch) are finer-textured
	float rough = 0.88;
	float spec = 0.08;
	if (sp == 1) { rough = 0.78; spec = 0.12; }        // maple: waxy broad leaf
	else if (sp == 3) { rough = 0.92; spec = 0.06; }    // birch: small matte leaves
	else if (sp == 5) { rough = 0.95; spec = 0.04; }    // conifer: needle texture
	else if (sp == 6) { rough = 0.90; spec = 0.07; }    // honeylocust: tiny compound leaflets
	else if (sp == 8) { rough = 0.75; spec = 0.14; }    // ginkgo: smooth fan-shaped
	else if (sp == 9) { rough = 0.80; spec = 0.11; }    // london plane: large waxy leaves

	// Micro-roughness variation: waxy cuticle creates glossy patches,
	// leaf edges and veins are matte. Breaks up uniform specular response.
	float rough_var = (bump_coarse - 0.5) * 0.14;
	rough = clamp(rough + rough_var, 0.3, 0.98);
	// Specular inversely follows roughness (glossier patches reflect more)
	spec = clamp(spec - rough_var * 0.08, 0.02, 0.25);

	// --- Blossom rendering: petals are smoother, more translucent ---
	if (v_blossom > 0.01) {
		// Petals have a delicate translucent quality
		rough = mix(rough, 0.55, v_blossom);    // smooth petal surface
		spec = mix(spec, 0.22, v_blossom);       // subtle sheen on petals
		// Per-pixel petal variation — real petals have veining, bruising, moisture spots
		float petal_var = lum * 0.15;
		float petal_noise = hash2(UV * 83.7 + tree_pos.xz * 11.3) * 0.08 - 0.04;
		float petal_hue = hash2(UV * 47.1 + tree_pos.xz * 7.9) * 0.04 - 0.02;
		col += vec3(petal_var + petal_noise + petal_hue,
		            (petal_var + petal_noise) * 0.8,
		            (petal_var + petal_noise) * 0.7 - petal_hue) * v_blossom;
	}

	// Snow accumulation
	if (snow_cover > 0.01) {
		vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
		float upward = max(world_n.y, 0.0);
		float noise = sin(tree_pos.x * 0.3 + tree_pos.z * 0.4) * 0.15;
		float snow_amt = clamp((0.3 + upward * 0.7 + noise) * snow_cover, 0.0, 1.0);
		col = mix(col, vec3(0.92, 0.93, 0.96), snow_amt * 0.65);
	}

	ALBEDO = col * tier_brightness;
	ROUGHNESS = rough;
	SPECULAR = spec;
	METALLIC = 0.0;

	// Crown-interior AO (trees.md §6): interior leaves see a small
	// fraction of the sky hemisphere; without this, every leaf receives
	// full calibrated sky ambient and distant canopy reads ~2.5× too
	// bright (ambient owned ~70% of the excess by measurement).
	// AO_LIGHT_AFFECT stays 0: direct sun and SSS untouched.
	float canopy_occ = mix(canopy_ao.x, canopy_ao.z, pow(v_crown_rho, canopy_ao.y));
	AO = canopy_occ;
	AO_LIGHT_AFFECT = 0.0;

	// Rain: wet leaves darken and get glossier (water film on surface)
	if (rain_wetness > 0.01) {
		ALBEDO *= mix(1.0, 0.70, rain_wetness);
		ROUGHNESS = mix(ROUGHNESS, 0.25, rain_wetness);
		SPECULAR = mix(SPECULAR, 0.35, rain_wetness);
		// Rain droplets clinging to leaf surfaces — individual water beads
		float droplet = sin(UV.x * 28.0) * sin(UV.y * 35.0);
		droplet = smoothstep(0.85, 0.95, droplet) * rain_wetness;
		ROUGHNESS = mix(ROUGHNESS, 0.04, droplet * 0.3);
		SPECULAR = mix(SPECULAR, 0.50, droplet * 0.4);
	}

	// --- Subsurface scattering / transmission ---
	// Real leaves transmit 5–15% of incident light; the SSS term gives that
	// backlit glow when the sun is behind the leaf. Strength stays modest
	// so backlit cards don't read as "the leaf is see-through" — a too-hot
	// BACKLIGHT swing as the camera rotates makes solid foliage look fake.
	vec3 backlight_col = vec3(0.62, 0.50, 0.14);
	// Tint with leaf color so autumn leaves glow amber/red, blossoms pink, etc.
	backlight_col = mix(backlight_col, v_leaf_color * 0.75, 0.5);
	float sss_strength = v_leaf_density * 0.7;
	float spring_boost = (1.0 - smoothstep(0.3, 0.8, season_t)) * 0.15;
	sss_strength += spring_boost;
	if (sp == 5) sss_strength *= 0.25;   // conifer needles: thick, minimal SSS
	if (sp == 13) sss_strength *= 0.55;  // magnolia: thick waxy leaves
	if (sp == 9) sss_strength *= 0.6;    // london plane: large but thick/leathery leaves
	if (v_blossom > 0.01) {
		vec3 petal_sss = BLOSSOM_COLORS[sp] * 0.7;
		backlight_col = mix(backlight_col, petal_sss, v_blossom);
		sss_strength = mix(sss_strength, 0.9, v_blossom);  // petals translucent but still capped
	}
	// Cap BACKLIGHT to real leaf transmittance: 5-15% of incident (the comment
	// above). The old 0.7 cap let backlit leaves transmit ~70% — ~5x the data —
	// and that over-bright green glow bounced (SSIL/GI) onto the bark, turning
	// the canopy-embedded limbs green while the bare lower trunk stayed pale
	// (user 2026-06-19, diagnosed via a forced-red-bark test). 0.15 = data high
	// end; thick/leathery species pull further down via sss_strength below.
	BACKLIGHT = min(backlight_col * sss_strength, ALBEDO * 0.15);

	// --- Impostor bake override (coverage/discard already applied above) ---
	// Emit ONE octahedral-atlas channel unshaded so the runtime-lit impostor
	// re-lights it. Placed last so it cleanly supersedes the lit-render outputs.
	if (bake_mode == 1) {            // NEUTRAL luminance/detail (hue applied at runtime)
		// Bake a HUE-FREE grayscale: the impostor shader supplies the per-tree
		// season colour at runtime (tree_impostor v_season_color) and uses this only
		// for luminance/detail. So baked hue can't fight the runtime tint — where the
		// density-thinning (bake_density) drops cards and bark shows through, it bakes
		// as neutral gray and recolours to darker-green canopy, never brown (user
		// 2026-06-24: "bake neutral rather than compensate"). Dapple self-shadow
		// (an ALBEDO multiply on the mesh) is folded in as luminance mottling; the
		// crown-interior AO rides the ORM atlas (bake_mode 3), re-applied ambient-only.
		float bake_lum = dot(bake_albedo, vec3(0.2126, 0.7152, 0.0722));
		EMISSION = vec3(bake_lum) * mix(0.72, 1.12, dapple);
		ALBEDO = vec3(0.0); ROUGHNESS = 1.0; SPECULAR = 0.0;
		METALLIC = 0.0; BACKLIGHT = vec3(0.0); AO = 1.0;
	} else if (bake_mode == 2) {     // camera-space normal, packed [0,1]
		EMISSION = NORMAL * 0.5 + 0.5;
		ALBEDO = vec3(0.0); ROUGHNESS = 1.0; SPECULAR = 0.0;
		METALLIC = 0.0; BACKLIGHT = vec3(0.0); AO = 1.0;
	} else if (bake_mode == 3) {     // ORM: R=crown-interior occlusion, G=rough(matte), B=metallic
		// Ambient-only AO for the impostor, identical to the mesh's AO channel
		// (the dominant "impostor too bright" term — crown interior reads ~0.12,
		// outer shell ~0.55 of sky ambient). Roughness kept 1.0 (matte foliage,
		// as the prior white-ORM default); metallic 0.
		EMISSION = vec3(canopy_occ, 1.0, 0.0);
		ALBEDO = vec3(0.0); ROUGHNESS = 1.0; SPECULAR = 0.0;
		METALLIC = 0.0; BACKLIGHT = vec3(0.0); AO = 1.0;
	}

	// NO shader-level aerial haze on leaves (removed 2026-06-11): the
	// calibrated volumetric fog owns the distance veil (rendering.md §6c).
	// This apply_aerial call double-counted it — its haze blend LIGHTENED
	// distant canopy toward sky color (the tree line measured ~2.5× too
	// bright vs reference) and its desat pushed leaf R/G toward grey
	// (game 0.90 vs ref 0.85). Real summer canopy stays saturated and
	// DARK at distance.

	// No ALPHA write: opaque pass, coverage is discard-only (see render_mode
	// note at top).
}

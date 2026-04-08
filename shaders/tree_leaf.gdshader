shader_type spatial;
render_mode cull_disabled, depth_prepass_alpha, alpha_to_coverage;

uniform vec3 albedo_tint = vec3(0.28, 0.48, 0.18);
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic;

global uniform vec2 wind_vec;
global uniform float snow_cover;
global uniform float season_t;
global uniform float rain_wetness;
global uniform vec3 sky_reflect_color;

#include "res://shaders/include/hash_noise.gdshaderinc"
#include "res://shaders/include/aerial_perspective.gdshaderinc"
#include "res://shaders/include/tree_species.gdshaderinc"

varying float v_leaf_density;
varying vec3 v_leaf_color;
varying float v_blossom;     // 0-1 blossom intensity (cherry/callery pear spring bloom)
varying float v_species_idx; // species index for fragment shader

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

// Blossom timing: (start, peak, end) — before leaf-out
// season_t 0=spring start, 1=summer, 2=autumn, 3=winter
const vec3 BLOSSOM_TIMING[14] = vec3[14](
	vec3(0.0),                     // 0 oak
	vec3(0.0),                     // 1 maple
	vec3(0.0),                     // 2 elm
	vec3(0.0),                     // 3 birch
	vec3(0.0),                     // 4 deciduous
	vec3(0.0),                     // 5 conifer
	vec3(0.0),                     // 6 honeylocust
	vec3(0.15, 0.30, 0.50),       // 7 callery_pear: early spring, short bloom
	vec3(0.0),                     // 8 ginkgo
	vec3(0.0),                     // 9 london_plane
	vec3(0.0),                     // 10 linden
	vec3(0.05, 0.20, 0.42),       // 11 cherry: very early, 2-week bloom peak
	vec3(0.0),                     // 12 willow: no showy blossoms
	vec3(0.02, 0.15, 0.35)        // 13 magnolia: very early spring, before leaf-out
);

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
		leaf_density = max(leaf_density, 0.08);  // never fully invisible
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
	v_leaf_color = leaf_color;

	// --- Per-species wind biomechanics ---
	vec4 wp = WIND_PARAMS[sp_idx];
	float trunk_flex = wp.x;
	float branch_flex = wp.y;
	float sway_freq = wp.z;
	float gust_resp = wp.w;

	vec3 tree_origin = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	// Height in model space — always correct gradient (0 at base, increases to crown)
	float h = max(VERTEX.y, 0.0);
	float wind_str = length(wind_vec);
	float rustle = (0.3 + wind_str * 0.7) * mix(0.3, 1.0, leaf_density);
	float phase = tree_origin.x * 0.04 + tree_origin.z * 0.06;

	// Baked wind weights for branch detail (COLOR_0 from GLB)
	// G = branch extent (0 at attachment, 1 at tip), B = per-branch phase hash
	// If vertex colors aren't imported, COLOR defaults to white — branch_w=1 is fine
	float branch_w = COLOR.g;
	float branch_phase = COLOR.b * 6.283 + phase;
	// Crown zone: branches start above lower trunk
	float crown = smoothstep(1.5, 4.0, h);

	// Trunk sway: cantilever bending (displacement ∝ height²)
	// Height-based — reliable regardless of vertex color availability
	float trunk_h = h * h * 0.008;
	VERTEX.x += sin(TIME * 0.7 * sway_freq + phase) * trunk_flex * trunk_h * rustle;
	VERTEX.z += sin(TIME * 1.1 * sway_freq + phase * 1.3) * trunk_flex * trunk_h * 0.6 * rustle;

	// Branch sway: secondary oscillation at ~2× trunk frequency
	VERTEX.x += sin(TIME * 1.4 * sway_freq + branch_phase) * branch_flex * 0.08 * h * crown * rustle;
	VERTEX.z += sin(TIME * 1.9 * sway_freq + branch_phase * 0.7) * branch_flex * 0.05 * h * crown * rustle;

	// Wind push: constant lean in wind direction
	VERTEX.x += wind_vec.x * h * 0.18 * mix(0.5, 1.0, trunk_flex);
	VERTEX.z += wind_vec.y * h * 0.18 * mix(0.5, 1.0, trunk_flex);

	// Gusts: periodic stronger push traveling across the canopy
	float gust_ph = tree_origin.x * 0.02 + tree_origin.z * 0.03;
	float gust = sin(TIME * 0.3 + gust_ph) * 0.5 + 0.5;
	gust = gust * gust * gust;  // sharpen peaks: brief strong gusts, long calm
	float gust_strength = gust * wind_str * 0.25 * gust_resp;
	VERTEX.x += wind_vec.x * h * gust_strength;
	VERTEX.z += wind_vec.y * h * gust_strength;

	// Leaf flutter: high-frequency per-leaf vibration
	float flutter = sin(TIME * 3.5 + VERTEX.x * 11.0 + VERTEX.z * 7.0) * 0.012 * rustle;
	flutter += sin(TIME * 5.7 + VERTEX.z * 17.0) * 0.006 * gust_strength;
	VERTEX.y += flutter * h;

	// Winter: shrink canopy toward trunk
	if (is_evergreen < 0.5 && leaf_density < 0.5) {
		float shrink = mix(0.4, 1.0, leaf_density * 2.0);
		VERTEX.xz *= shrink;
	}
}

void fragment() {
	vec4 tex = texture(albedo_tex, UV);
	float lum = dot(tex.rgb, vec3(0.3, 0.6, 0.1));
	float alpha = tex.a * v_leaf_density;
	// Early-out for fully transparent pixels (texture gap).
	// Kept loose (0.02) so distance-adaptive boost below can rescue
	// mipmapped leaf fragments that would otherwise be culled prematurely.
	if (alpha < 0.02) discard;

	vec3 col = v_leaf_color * (0.4 + lum * 0.6);  // reduced: Blender vertex colors are too bright for PBR
	int sp = int(v_species_idx + 0.5);
	// Desaturate slightly — preserve species hue while keeping it natural
	float leaf_lum = dot(col, vec3(0.299, 0.587, 0.114));
	col = mix(vec3(leaf_lum), col, 0.72);  // 28% desaturation (was 35%)
	col *= vec3(0.94, 0.90, 0.80);  // subtle warm darken

	// --- Top-lit canopy gradient: world-space normal creates 3D depth ---
	// Sunlit top = bright, shaded underside = darker blue-shifted.
	// This is the single biggest cue for 3D canopy shape.
	vec3 world_n = mat3(INV_VIEW_MATRIX) * NORMAL;
	float top_lit = world_n.y * 0.5 + 0.5;  // 0=facing down, 1=facing up
	col *= mix(0.82, 1.10, top_lit);  // 82% underneath (was 72% — too dark without GI)
	// Underside gets warm ground-bounce (green grass reflects up into canopy)
	// plus cool sky-fill — fakes indirect illumination without GI
	float underside = (1.0 - top_lit);
	col = mix(col, col * vec3(0.96, 1.02, 0.94), underside * 0.20);  // warm green bounce
	col = mix(col, col * vec3(0.94, 0.96, 1.04), underside * 0.10);  // cool sky fill

	// --- Fresnel rim light: leaf edges glow at grazing view angles ---
	// Real leaves show bright translucent edges when viewed at shallow angles
	float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), 3.0);
	col += col * fresnel * 0.18;

	// --- Procedural leaf micro-texture: veins, cell structure, surface bumps ---
	// Real leaves have complex surface topology that catches light at micro-scale.
	// Two noise octaves: coarse (vein ridges) + fine (cell/cuticle texture).
	vec3 frag_world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float bump_coarse = vnoise(frag_world.xz * 45.0);
	float bump_fine = vnoise(frag_world.xz * 110.0);
	float bump_h = bump_coarse * 0.6 + bump_fine * 0.4;
	// Perturb normal via screen-space height derivatives (subtle — just enough
	// to break up uniform lighting, not enough to flip normals or wash out)
	NORMAL = normalize(NORMAL + vec3(dFdx(bump_h), dFdy(bump_h), 0.0) * 1.2);

	// Within-canopy detail: simulate individual leaf shadows, overlap, light pockets
	vec3 tree_pos = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float detail_n = vnoise(UV * 12.0 + tree_pos.xz * 0.5);  // per-leaf-scale noise
	float pocket_n = vnoise(UV * 4.0 + tree_pos.xz * 0.3);   // shadow pocket scale
	// Dark shadow pockets in canopy interior (softer than before)
	col *= mix(1.0, 0.78, smoothstep(0.3, 0.6, pocket_n) * 0.22);
	// Per-leaf brightness variation (some leaves catch more light)
	col *= (0.92 + detail_n * 0.16);

	// Per-pixel micro-variation: chlorophyll patches, dust, cell structure
	// Real leaves have millions of unique shades across their surface
	vec2 px_uv = UV * 97.3 + tree_pos.xz * 5.1;
	float px_n = hash2(px_uv) * 0.08 - 0.04;             // ±4% brightness
	float px_hr = hash2(px_uv + vec2(71.9, 0.0)) * 0.03;  // warm shift
	float px_hb = hash2(px_uv + vec2(0.0, 53.1)) * 0.03;  // cool shift
	col += vec3(px_n + px_hr, px_n, px_n + px_hb);

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
		vec3 tree_pos = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
		float noise = sin(tree_pos.x * 0.3 + tree_pos.z * 0.4) * 0.15;
		float snow_amt = clamp((0.3 + upward * 0.7 + noise) * snow_cover, 0.0, 1.0);
		col = mix(col, vec3(0.92, 0.93, 0.96), snow_amt * 0.65);
	}

	ALBEDO = col;
	ROUGHNESS = rough;
	SPECULAR = spec;
	METALLIC = 0.0;

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

	// --- Enhanced subsurface scattering / transmission ---
	// Real leaves are translucent — light physically passes through the tissue.
	// BACKLIGHT must stay well below ALBEDO or it washes the canopy white.
	// Target: ~30-40% of front-face brightness for a visible green-gold glow.
	vec3 backlight_col = vec3(0.46, 0.36, 0.10);  // warm green-gold (modest boost from original)
	// Tint with leaf color so autumn leaves glow amber/red
	backlight_col = mix(backlight_col, v_leaf_color * 0.6, 0.45);
	float sss_strength = v_leaf_density;
	// Spring leaves are thinner, more translucent
	float spring_boost = (1.0 - smoothstep(0.3, 0.8, season_t)) * 0.3;
	sss_strength += spring_boost;
	// Conifer needles: thick, minimal SSS
	if (sp == 5) sss_strength *= 0.25;
	// Magnolia: thick waxy leaves, reduced transmission
	if (sp == 13) sss_strength *= 0.55;
	// Blossom petals: strong pink/white translucency (backlit cherry blossoms are iconic)
	if (v_blossom > 0.01) {
		vec3 petal_sss = BLOSSOM_COLORS[sp] * 0.7;  // petal color glows through
		backlight_col = mix(backlight_col, petal_sss, v_blossom);
		sss_strength = mix(sss_strength, 1.2, v_blossom);  // petals are very translucent
	}
	BACKLIGHT = backlight_col * sss_strength;

	// Aerial perspective: desaturate + cool shift + haze blend at distance.
	// Matches terrain, grass, and facade distance fog for visual coherence.
	vec3 leaf_world = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float leaf_dist = length(leaf_world - INV_VIEW_MATRIX[3].xyz);
	float leaf_aerial = smoothstep(60.0, 300.0, leaf_dist);
	ALBEDO = apply_aerial(ALBEDO, leaf_aerial, 0.30, 0.30, sky_reflect_color);

	// Distance-adaptive alpha: counteract mipmap erosion that thins leaves at distance.
	// At distance, mipmapped alpha textures lose coverage — leaf cards become transparent
	// confetti. LOD1/LOD2 models have fewer leaf cards from decimation, compounding
	// the problem — need aggressive boost to maintain canopy mass beyond 130m.
	alpha *= mix(1.0, 3.0, leaf_aerial);
	alpha = min(alpha, 1.0);

	// Distance-adaptive discard: lower threshold at distance so partially-covered
	// leaf fragments survive instead of being culled. Near-field keeps tight 0.15
	// threshold for clean edges; far-field drops to 0.03 to preserve canopy volume.
	float discard_thresh = mix(0.15, 0.03, leaf_aerial);
	if (alpha < discard_thresh) discard;

	// Feed continuous alpha to alpha_to_coverage (4x MSAA).
	// Depth prepass already wrote depth for fragments above discard threshold.
	ALPHA = alpha;
}

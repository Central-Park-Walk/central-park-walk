// Per-species tree data shared by bark, leaf, canopy shell, and impostor shaders.
// 14 species: oak, maple, elm, birch, deciduous, conifer, honeylocust,
//   callery_pear, ginkgo, london_plane, linden, cherry, willow, magnolia

// Summer leaf color — field observation + USDA plant database
const vec3 SUMMER_COLORS[14] = vec3[14](
	vec3(0.22, 0.42, 0.14),  // 0 oak: deep dark green, slightly blue
	vec3(0.26, 0.48, 0.16),  // 1 maple: medium green, hint of yellow-green
	vec3(0.30, 0.52, 0.20),  // 2 elm: lighter bright green (quintessential shade tree)
	vec3(0.32, 0.54, 0.18),  // 3 birch: fresh light green, slightly golden
	vec3(0.28, 0.48, 0.18),  // 4 deciduous: generic mid-green (baseline)
	vec3(0.12, 0.28, 0.10),  // 5 conifer: very dark blue-green (pine/spruce)
	vec3(0.30, 0.50, 0.14),  // 6 honeylocust: fine-textured yellow-green
	vec3(0.24, 0.44, 0.16),  // 7 callery_pear: glossy dark green
	vec3(0.35, 0.52, 0.12),  // 8 ginkgo: unique chartreuse/yellow-green
	vec3(0.26, 0.45, 0.20),  // 9 london_plane: dark slightly gray-green
	vec3(0.24, 0.46, 0.16),  // 10 linden: rich medium green, slightly lime
	vec3(0.28, 0.48, 0.18),  // 11 cherry: medium green, reddish tint to new growth
	vec3(0.30, 0.50, 0.16),  // 12 willow: pale sage green
	vec3(0.22, 0.42, 0.14)   // 13 magnolia: thick waxy dark green
);

// Fall colors
const vec3 FALL_COLORS[14] = vec3[14](
	vec3(0.55, 0.25, 0.12),  // 0 oak: russet red-brown
	vec3(0.85, 0.22, 0.08),  // 1 maple: brilliant red-orange
	vec3(0.78, 0.72, 0.18),  // 2 elm: golden yellow
	vec3(0.82, 0.75, 0.22),  // 3 birch: bright yellow
	vec3(0.65, 0.45, 0.15),  // 4 deciduous: amber
	vec3(0.14, 0.30, 0.10),  // 5 conifer: stays green
	vec3(0.80, 0.75, 0.28),  // 6 honeylocust: clear golden yellow
	vec3(0.72, 0.18, 0.12),  // 7 callery_pear: deep red-purple
	vec3(0.92, 0.85, 0.20),  // 8 ginkgo: brilliant pure yellow
	vec3(0.70, 0.52, 0.18),  // 9 london_plane: tawny brown-gold
	vec3(0.78, 0.70, 0.22),  // 10 linden: warm yellow
	vec3(0.80, 0.30, 0.15),  // 11 cherry: orange-red
	vec3(0.82, 0.78, 0.25),  // 12 willow: golden yellow (early)
	vec3(0.60, 0.42, 0.18)   // 13 magnolia: warm brown-gold
);

// Phenology timing: (fall_start, fall_peak, bare_start, leaf_start)
const vec4 PHENOLOGY[14] = vec4[14](
	vec4(2.3, 2.7, 3.1, 0.4),  // 0 oak: late, holds leaves
	vec4(2.1, 2.5, 2.9, 0.3),  // 1 maple: classic mid-fall
	vec4(2.2, 2.6, 3.0, 0.3),  // 2 elm: mid-fall
	vec4(2.0, 2.4, 2.8, 0.2),  // 3 birch: early fall, early spring
	vec4(2.2, 2.6, 3.0, 0.3),  // 4 deciduous: average
	vec4(0.0, 0.0, 0.0, 0.0),  // 5 conifer (unused — evergreen)
	vec4(2.0, 2.3, 2.6, 0.4),  // 6 honeylocust: early, drops fast
	vec4(2.3, 2.7, 3.1, 0.3),  // 7 callery_pear: late, persistent
	vec4(2.4, 2.6, 2.8, 0.5),  // 8 ginkgo: very late, drops all at once
	vec4(2.2, 2.6, 3.0, 0.3),  // 9 london_plane: mid-fall, persistent
	vec4(2.1, 2.5, 2.9, 0.3),  // 10 linden: mid-fall
	vec4(2.0, 2.4, 2.8, 0.3),  // 11 cherry: early fall
	vec4(2.0, 2.3, 2.7, 0.2),  // 12 willow: early fall yellow, early spring
	vec4(2.3, 2.6, 3.0, 0.2)   // 13 magnolia: late fall, early spring bloom
);

// Winter leaf retention: fraction of leaves kept through winter (0.0 = fully bare)
// Marcescent species hold dead brown leaves; semi-evergreen hold some green.
// Sources: USDA Plants DB, NYC urban forestry, Arnold Arboretum phenology records
// Since 2026-06-10 these are LITERAL retained-card fractions (the leaf shader
// drops whole clusters stochastically in the opaque pass — no alpha ghosting),
// recalibrated down: a mature oak's marcescence reads right at ~15-20% of
// clusters, held low/inner crown (upper-crown-first bias in tree_leaf vertex).
const float WINTER_RETENTION[14] = float[14](
	0.18,  // 0 oak: marcescent — patchy dead brown leaves into Feb, spring push drops them
	0.0,   // 1 maple: clean abscission by late Nov
	0.0,   // 2 elm: clean drop by mid-Nov
	0.0,   // 3 birch: among first to shed, bare by late Oct
	0.0,   // 4 deciduous: generic clean abscission
	1.0,   // 5 conifer: evergreen (handled by is_evergreen flag, not this)
	0.0,   // 6 honeylocust: tiny leaflets drop early/fast, bare by late Oct
	0.18,  // 7 callery_pear: holds dark red-purple leaves into Dec
	0.0,   // 8 ginkgo: drops ALL leaves in 1-3 days after first hard frost
	0.12,  // 9 london_plane: partially marcescent, some brown leaves into Jan
	0.0,   // 10 linden: clean drop mid-Nov
	0.0,   // 11 cherry: clean drop by early Nov
	0.0,   // 12 willow: early dropper, bare by late Oct
	0.45   // 13 magnolia: semi-evergreen in mild winters, holds green leaves late
);

// Blossom timing: (start, peak, end) on the season_t axis — before leaf-out.
// season_t 0=spring start, 1=summer, 2=autumn, 3=winter. vec3(0.0) = none.
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

// Wind biomechanics: (trunk_flex, branch_flex, sway_freq, gust_response)
// Sources: forestry drag coefficients, Gardiner 1995, James et al 2006
const vec4 WIND_PARAMS[14] = vec4[14](
	vec4(0.15, 0.45, 0.70, 0.50),  // 0 oak: massive stiff trunk, slow sway
	vec4(0.35, 0.55, 0.90, 0.60),  // 1 maple: medium all-around
	vec4(0.45, 0.70, 0.85, 0.65),  // 2 elm: flexible vase-form, long arching branches
	vec4(0.70, 0.50, 1.20, 0.80),  // 3 birch: whip-like trunk, lightweight, fast
	vec4(0.35, 0.50, 0.90, 0.55),  // 4 deciduous: balanced baseline
	vec4(0.20, 0.25, 0.60, 0.35),  // 5 conifer: deep roots, stiff, dense dampening
	vec4(0.40, 0.65, 1.05, 0.70),  // 6 honeylocust: airy compound leaves, supple wood
	vec4(0.25, 0.40, 0.95, 0.45),  // 7 callery_pear: tight upright branching
	vec4(0.20, 0.30, 0.75, 0.40),  // 8 ginkgo: ancient rigid wood, sparse crown
	vec4(0.30, 0.45, 0.80, 0.50),  // 9 london_plane: large solid trunk, moderate
	vec4(0.35, 0.50, 0.90, 0.55),  // 10 linden: medium rounded crown
	vec4(0.50, 0.55, 1.15, 0.65),  // 11 cherry: smaller tree, limber, fast sway
	vec4(0.85, 0.95, 0.75, 0.90),  // 12 willow: extremely flexible, flowing, high drag
	vec4(0.25, 0.35, 0.80, 0.40)   // 13 magnolia: stiff trunk, heavy waxy leaves dampen
);

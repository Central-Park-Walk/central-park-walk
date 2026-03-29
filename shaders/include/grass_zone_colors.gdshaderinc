// Shared grass color system — zone palettes + macro variation.
// All LOD tiers include this for color coherence across distances.
//
// Zone palettes: CIE 1931 + D65 from published leaf reflectance curves,
// boosted ~50% from single-leaf to massed-canopy brightness.
//
// Macro variation: field-scale splotchiness from soil moisture, mowing
// timing, species mix, drainage, and foot traffic. This is the dominant
// visual signal at >5m — real grass fields are patchy, not uniform.
//
// Requires: hash_noise.gdshaderinc (vnoise, fbm3)

// Zone spectral palettes.
// Returns the low/high range for blade-group variation within each zone.
void grass_zone_palette(int zone_id, out vec3 c_lo, out vec3 c_hi) {
	if (zone_id == 0) {
		// SheepMeadow: KBG (Poa pratensis) — maintained A-lawn
		c_lo = vec3(0.062, 0.195, 0.068);
		c_hi = vec3(0.088, 0.268, 0.096);
	} else if (zone_id == 1) {
		// GreatLawn: KBG, slightly deeper soil
		c_lo = vec3(0.056, 0.186, 0.063);
		c_hi = vec3(0.080, 0.258, 0.088);
	} else if (zone_id == 2) {
		// NorthMeadow: KBG, warmer open exposure
		c_lo = vec3(0.076, 0.192, 0.060);
		c_hi = vec3(0.105, 0.262, 0.080);
	} else if (zone_id == 3) {
		// FormalGarden: KBG/ryegrass, low contrast manicured
		c_lo = vec3(0.068, 0.206, 0.073);
		c_hi = vec3(0.088, 0.252, 0.090);
	} else if (zone_id == 4) {
		// SportsTurf: maintained KBG
		c_lo = vec3(0.062, 0.195, 0.068);
		c_hi = vec3(0.084, 0.258, 0.090);
	} else if (zone_id == 5 || zone_id == 6) {
		// NorthWoods/Ramble: Fine Fescue (Festuca rubra) — shade-tolerant
		c_lo = vec3(0.054, 0.156, 0.054);
		c_hi = vec3(0.078, 0.214, 0.078);
	} else if (zone_id == 7) {
		// Waterside: Tussock Sedge (Carex stricta)
		c_lo = vec3(0.055, 0.156, 0.054);
		c_hi = vec3(0.080, 0.216, 0.080);
	} else if (zone_id == 8) {
		// WildMeadow: Switchgrass (Panicum virgatum)
		c_lo = vec3(0.073, 0.192, 0.064);
		c_hi = vec3(0.104, 0.264, 0.086);
	} else if (zone_id == 9) {
		// OpenLawn: KBG standard
		c_lo = vec3(0.062, 0.195, 0.068);
		c_hi = vec3(0.088, 0.268, 0.096);
	} else if (zone_id == 10 || zone_id == 11) {
		// Woodland understory: Fine Fescue, warmer (leaf litter influence)
		c_lo = vec3(0.058, 0.150, 0.050);
		c_hi = vec3(0.084, 0.206, 0.070);
	} else {
		// Default: KBG average
		c_lo = vec3(0.062, 0.190, 0.065);
		c_hi = vec3(0.086, 0.258, 0.090);
	}
}

// Grass base color with multi-scale variation.
// Returns the color for a given zone at a world XZ position.
// Does NOT include: root-to-tip gradient, per-instance variation,
// texture blending, seasonal color, canopy effects, or weather.
// Those are tier-specific and applied by each consuming shader.
vec3 grass_base_color(int zone_id, vec2 world_xz) {
	vec3 c_lo, c_hi;
	grass_zone_palette(zone_id, c_lo, c_hi);

	// --- Micro variation (3m) ---
	// Blade-group patchiness: small clumps of taller/shorter grass
	float micro = vnoise(world_xz / 3.0);
	vec3 col = mix(c_lo, c_hi, micro);

	// --- Macro variation (20-25m patches) ---
	// The dominant visual signal at field scale. Real grass fields have
	// large splotches of different tone from soil moisture, drainage,
	// mowing timing, species mix, and foot traffic.
	// Two octaves: 22m (dominant patches) + 9m (secondary breakup)
	float macro = vnoise(world_xz / 22.0 + vec2(13.7, 41.2)) * 0.6
	            + vnoise(world_xz / 9.0 + vec2(37.1, 83.9)) * 0.4;
	// Range 0.78–1.42: stressed patches go darker/yellower,
	// vigorous patches go brighter/greener. Average ~1.10 (+10% boost).
	float macro_scale = mix(0.78, 1.42, macro);
	col *= macro_scale;

	// Stressed patches lean warm (yellow-brown); vigorous lean cool (blue-green)
	// This hue shift correlates with the brightness — dry = yellow, lush = green
	float stress_hue = smoothstep(0.78, 1.10, macro_scale);
	col *= mix(vec3(1.08, 1.0, 0.86),   // stressed: warm/yellow
	           vec3(0.96, 1.0, 1.04),    // vigorous: cool/green
	           stress_hue);

	// --- Landscape gradient (70m) ---
	// Gentle tone drift across large fields — one end of Great Lawn
	// might be subtly different from the other
	float landscape = vnoise(world_xz / 70.0 + vec2(91.3, 7.7));
	col *= mix(0.96, 1.04, landscape);

	// --- Warm/cool hue drift (8m) ---
	// Independent of brightness — patches lean yellow-green vs blue-green
	float hue = vnoise(world_xz / 8.0 + vec2(51.3, 17.9));
	col *= mix(vec3(1.04, 1.0, 0.92), vec3(0.95, 1.0, 1.07), hue);

	// --- Dead tuft accents (~22% of area) ---
	// Stressed, dormant, or recently-mowed spots with warm brown cast
	float dead_n = vnoise(world_xz * 0.8 + vec2(73.1, 29.7));
	float dead_mask = smoothstep(0.55, 0.68, dead_n);
	if (dead_mask > 0.0) {
		vec3 dead_col = vec3(0.16, 0.16, 0.075); // spectral dried leaf linear
		col = mix(col, dead_col, dead_mask * 0.50);
	}

	// --- EGTTR warmth ---
	// Golden undertone throughout — waxy cuticle + chlorophyll
	col *= vec3(1.04, 1.01, 0.94);

	return col;
}

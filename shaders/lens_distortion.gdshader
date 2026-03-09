shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float barrel_strength = 0.025;
uniform float chroma_strength = 0.0008;
global uniform float rain_wetness;

// Simple hash for raindrop placement
float lens_hash(vec2 p) {
	p = fract(p * vec2(127.1, 311.7));
	p += dot(p, p + 43.21);
	return fract(p.x * p.y);
}

void fragment() {
	vec2 uv = SCREEN_UV - 0.5;
	float dist2 = dot(uv, uv);
	// Brown-Conrady barrel distortion with 4th-order term for realism
	float distort = 1.0 + barrel_strength * dist2 + barrel_strength * 0.3 * dist2 * dist2;
	vec2 warped = uv * distort;

	// Rain-on-lens: subtle water distortion at screen edges during rain
	if (rain_wetness > 0.2) {
		float rain_t = smoothstep(0.2, 0.8, rain_wetness);
		// Edge mask: droplets concentrate at screen edges (like a real camera lens)
		float edge_mask = smoothstep(0.08, 0.25, dist2) * rain_t;
		// Raindrop cells: grid of potential droplet locations
		vec2 drop_uv = SCREEN_UV * 12.0 + vec2(0.0, TIME * 0.3);
		vec2 drop_cell = floor(drop_uv);
		vec2 drop_frac = fract(drop_uv) - 0.5;
		float drop_rand = lens_hash(drop_cell);
		// Only ~30% of cells have visible drops
		if (drop_rand > 0.70 && edge_mask > 0.01) {
			// Drop center offset from cell center (randomized)
			vec2 drop_offset = vec2(lens_hash(drop_cell + vec2(3.7, 0.0)),
			                        lens_hash(drop_cell + vec2(0.0, 7.3))) - 0.5;
			drop_offset *= 0.6;
			float drop_dist = length(drop_frac - drop_offset * 0.3);
			float drop_size = 0.08 + drop_rand * 0.12;
			float drop = smoothstep(drop_size, drop_size * 0.3, drop_dist);
			// Droplets refract/distort: shift UV inward (like a water lens)
			vec2 drop_dir = normalize(drop_frac - drop_offset * 0.3);
			warped += drop_dir * drop * edge_mask * 0.008;
		}
		// Vertical water streaks — running down the "lens"
		float streak_x = sin(SCREEN_UV.x * 40.0 + lens_hash(floor(vec2(SCREEN_UV.x * 40.0, 0.0))) * 20.0);
		float streak = smoothstep(0.7, 0.95, streak_x) * edge_mask * 0.3;
		// Streaks run downward
		float streak_y = fract(SCREEN_UV.y * 0.5 + TIME * 0.15);
		streak *= smoothstep(0.0, 0.3, streak_y) * smoothstep(1.0, 0.5, streak_y);
		warped.y += streak * 0.003;
	}

	// Chromatic aberration: scales with distance from center (real lens behavior)
	float ca = chroma_strength * (1.0 + dist2 * 3.0);
	vec2 uv_r = warped * (1.0 + ca) + 0.5;
	vec2 uv_g = warped + 0.5;
	vec2 uv_b = warped * (1.0 - ca) + 0.5;
	float r = texture(screen_tex, uv_r).r;
	float g = texture(screen_tex, uv_g).g;
	float b = texture(screen_tex, uv_b).b;
	COLOR = vec4(r, g, b, 1.0);
}

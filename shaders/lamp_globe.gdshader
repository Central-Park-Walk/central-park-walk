shader_type spatial;
render_mode blend_mix, unshaded;

// Lamppost luminaire globe — warm amber glow at night
global uniform float lamp_glow;

void fragment() {
	// Warm sodium vapor amber, intensity driven by time of day
	vec3 warm_amber = vec3(1.0, 0.62, 0.22);
	float glow = lamp_glow;
	// Frosted glass base color when off
	vec3 off_color = vec3(0.85, 0.82, 0.75);
	ALBEDO = mix(off_color, warm_amber, glow);
	EMISSION = warm_amber * glow * 4.0;
	ALPHA = 0.85 + glow * 0.15;
}

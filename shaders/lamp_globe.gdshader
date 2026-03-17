shader_type spatial;
render_mode blend_mix;

// Lamppost luminaire globe — warm amber glow at night
global uniform float lamp_glow;

void fragment() {
	vec3 warm_amber = vec3(1.0, 0.62, 0.22);
	float glow = lamp_glow;
	// Frosted glass — translucent white when off, warm amber when on
	ALBEDO = vec3(0.75, 0.72, 0.68);
	ROUGHNESS = 0.4;
	METALLIC = 0.0;
	EMISSION = warm_amber * glow * 6.0;
	ALPHA = 0.8;
}

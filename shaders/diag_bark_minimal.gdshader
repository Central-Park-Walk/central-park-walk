shader_type spatial;
// DIAGNOSTIC ONLY (--simple-bark): minimal opaque bark shader. The cost
// delta vs tree_bark.gdshader isolates bark shader complexity (triplanar
// sampling, wind) from raw geometry cost. Not used in normal play.

uniform vec3 bark_color = vec3(0.48, 0.38, 0.28);

void fragment() {
	ALBEDO = bark_color;
	ROUGHNESS = 0.9;
	SPECULAR = 0.1;
}

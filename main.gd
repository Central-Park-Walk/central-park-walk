extends Node3D

# References kept for per-frame HUD updates
var _player: CharacterBody3D
var _coord_label: Label
var _heading_label: Label


func _ready() -> void:
	_setup_environment()
	_setup_ground()
	_setup_compass_discs()
	_setup_poles()
	_setup_scatter()
	_player = _setup_player()
	_setup_hud()


# ---------------------------------------------------------------------------
# Per-frame: update HUD with player position and compass heading
# ---------------------------------------------------------------------------
func _process(_delta: float) -> void:
	if not _player or not _coord_label:
		return

	var pos := _player.position
	_coord_label.text   = "X: %7.1f      Z: %7.1f" % [pos.x, pos.z]

	# Convert Godot Y-rotation to a 0–360 compass bearing.
	# rotation_degrees.y = 0  → facing -Z → we call that North (0°)
	# Turning right decreases rotation_degrees.y, so bearing = -yaw mod 360.
	var bearing := fmod(fmod(-_player.rotation_degrees.y, 360.0) + 360.0, 360.0)
	_heading_label.text = "Heading: %5.1f°  %s" % [bearing, _compass_label(bearing)]


func _compass_label(deg: float) -> String:
	var labels := ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
	return labels[int(fmod(deg + 22.5, 360.0) / 45.0) % 8]


# ---------------------------------------------------------------------------
# Sky + lighting
# ---------------------------------------------------------------------------
func _setup_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color      = Color(0.13, 0.40, 0.82)
	sky_mat.sky_horizon_color  = Color(0.58, 0.78, 0.96)
	sky_mat.ground_bottom_color   = Color(0.10, 0.10, 0.10)
	sky_mat.ground_horizon_color  = Color(0.32, 0.52, 0.32)
	sky_mat.sun_angle_max  = 30.0
	sky_mat.sun_curve      = 0.06

	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode         = Environment.BG_SKY
	env.sky                     = sky
	env.ambient_light_source    = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy    = 0.75
	env.tonemap_mode            = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure        = 1.0
	env.glow_enabled            = true
	env.glow_intensity          = 0.4
	env.glow_bloom              = 0.05

	var world_env := WorldEnvironment.new()
	world_env.environment = env
	add_child(world_env)

	# Main sun – high angle, slightly warm
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees  = Vector3(-55.0, -30.0, 0.0)
	sun.light_energy      = 2.2
	sun.light_color       = Color(1.00, 0.95, 0.85)
	sun.shadow_enabled    = true
	add_child(sun)

	# Soft fill from the opposite side
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25.0, 150.0, 0.0)
	fill.light_energy     = 0.35
	fill.light_color      = Color(0.75, 0.85, 1.00)
	fill.shadow_enabled   = false
	add_child(fill)


# ---------------------------------------------------------------------------
# Ground plane with procedural grid shader
# ---------------------------------------------------------------------------
func _setup_ground() -> void:
	var plane := PlaneMesh.new()
	plane.size            = Vector2(400.0, 400.0)
	plane.subdivide_width  = 1
	plane.subdivide_depth  = 1

	var shader := Shader.new()
	shader.code = _grid_shader_code()

	var mat := ShaderMaterial.new()
	mat.shader = shader

	var mi := MeshInstance3D.new()
	mi.mesh              = plane
	mi.material_override = mat
	add_child(mi)

	# Infinite flat collision floor
	var body := StaticBody3D.new()
	var col  := CollisionShape3D.new()
	col.shape = WorldBoundaryShape3D.new()
	body.add_child(col)
	add_child(body)


func _grid_shader_code() -> String:
	return """shader_type spatial;
render_mode cull_disabled;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 pos = world_pos.xz;

	// Fine grid lines every 10 m
	vec2 fine_d  = abs(fract(pos / 10.0 + 0.5) - 0.5) * 10.0;
	float fine_a = 1.0 - smoothstep(0.0, 0.22, min(fine_d.x, fine_d.y));

	// Coarse grid lines every 50 m
	vec2 coarse_d  = abs(fract(pos / 50.0 + 0.5) - 0.5) * 50.0;
	float coarse_a = 1.0 - smoothstep(0.0, 0.60, min(coarse_d.x, coarse_d.y));

	// Cardinal axis lines (thicker stripes through origin)
	float x_axis = 1.0 - smoothstep(0.0, 1.0, abs(pos.y));  // Z = 0 line (runs East–West)
	float z_axis = 1.0 - smoothstep(0.0, 1.0, abs(pos.x));  // X = 0 line (runs North–South)

	// Build up color in layers
	vec3 color = vec3(0.19, 0.46, 0.19);                                  // green base
	color = mix(color, vec3(0.34, 0.68, 0.34), fine_a   * 0.55);          // fine lines
	color = mix(color, vec3(0.82, 0.96, 0.55), coarse_a * 0.82);          // coarse lines
	color = mix(color, vec3(0.95, 0.25, 0.20), x_axis   * 0.90);          // red  – X axis
	color = mix(color, vec3(0.25, 0.45, 1.00), z_axis   * 0.90);          // blue – Z axis

	ALBEDO    = color;
	ROUGHNESS = 0.95;
	METALLIC  = 0.0;
}
"""


# ---------------------------------------------------------------------------
# Cardinal direction discs on the ground (N/S/E/W at 45 m out)
# ---------------------------------------------------------------------------
func _setup_compass_discs() -> void:
	_add_compass_disc(Vector3(  0.0, 0.01, -45.0), Color(0.90, 0.90, 1.00), "N")  # -Z = North
	_add_compass_disc(Vector3(  0.0, 0.01,  45.0), Color(1.00, 0.80, 0.80), "S")
	_add_compass_disc(Vector3( 45.0, 0.01,   0.0), Color(1.00, 0.70, 0.30), "E")  # +X = East
	_add_compass_disc(Vector3(-45.0, 0.01,   0.0), Color(0.70, 1.00, 0.70), "W")


func _add_compass_disc(pos: Vector3, color: Color, _dir: String) -> void:
	var cyl := CylinderMesh.new()
	cyl.top_radius    = 2.2
	cyl.bottom_radius = 2.2
	cyl.height        = 0.12

	var mat := StandardMaterial3D.new()
	mat.albedo_color              = color
	mat.emission_enabled          = true
	mat.emission                  = color * 0.6
	mat.emission_energy_multiplier = 0.7

	var mi := MeshInstance3D.new()
	mi.mesh              = cyl
	mi.material_override = mat
	mi.position          = pos
	add_child(mi)


# ---------------------------------------------------------------------------
# Grid of tall colored poles (9 × 9 at 20 m spacing, centre skipped)
# ---------------------------------------------------------------------------
func _setup_poles() -> void:
	var palette := [
		Color(1.00, 0.18, 0.18),  # red
		Color(0.18, 0.38, 1.00),  # blue
		Color(1.00, 0.85, 0.08),  # yellow
		Color(0.10, 0.82, 0.38),  # green
		Color(0.88, 0.22, 1.00),  # purple
		Color(0.08, 0.90, 0.88),  # cyan
		Color(1.00, 0.48, 0.08),  # orange
		Color(1.00, 0.38, 0.65),  # pink
	]

	var spacing := 20.0
	var count   := 4   # −4 … +4 → 9 × 9 grid

	for xi: int in range(-count, count + 1):
		for zi: int in range(-count, count + 1):
			if xi == 0 and zi == 0:
				continue  # leave spawn area clear

			var ci := (absi(xi) * 3 + absi(zi) * 5) % palette.size()

			var cyl := CylinderMesh.new()
			cyl.top_radius      = 0.22
			cyl.bottom_radius   = 0.28
			cyl.height          = 10.0
			cyl.radial_segments = 8

			var mat := StandardMaterial3D.new()
			mat.albedo_color              = palette[ci]
			mat.emission_enabled          = true
			mat.emission                  = palette[ci] * 0.25
			mat.emission_energy_multiplier = 0.4

			var mi := MeshInstance3D.new()
			mi.mesh              = cyl
			mi.material_override = mat
			mi.position          = Vector3(xi * spacing, 5.0, zi * spacing)
			add_child(mi)

			# Tiny cap sphere so poles are easier to spot against the sky
			var cap_mesh := SphereMesh.new()
			cap_mesh.radius = 0.35
			cap_mesh.height = 0.70

			var cap_mat := StandardMaterial3D.new()
			cap_mat.albedo_color              = Color.WHITE
			cap_mat.emission_enabled          = true
			cap_mat.emission                  = Color.WHITE
			cap_mat.emission_energy_multiplier = 0.8

			var cap_mi := MeshInstance3D.new()
			cap_mi.mesh              = cap_mesh
			cap_mi.material_override = cap_mat
			cap_mi.position          = Vector3(xi * spacing, 10.15, zi * spacing)
			add_child(cap_mi)


# ---------------------------------------------------------------------------
# Scattered cubes and spheres for extra spatial reference
# ---------------------------------------------------------------------------
func _setup_scatter() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 42

	var palette := [
		Color(0.90, 0.10, 0.10),
		Color(0.10, 0.25, 0.90),
		Color(0.90, 0.80, 0.08),
		Color(0.10, 0.80, 0.28),
		Color(0.80, 0.10, 0.90),
		Color(0.08, 0.90, 0.90),
		Color(0.90, 0.48, 0.08),
		Color(0.90, 0.28, 0.60),
	]

	# --- Cubes ---
	for i: int in range(28):
		var w := rng.randf_range(0.7, 4.0)
		var h := w * rng.randf_range(0.4, 3.0)
		var d := rng.randf_range(0.7, 4.0)
		var px := rng.randf_range(-95.0, 95.0)
		var pz := rng.randf_range(-95.0, 95.0)

		# Avoid spawning on top of the player start area
		if Vector2(px, pz).length() < 10.0:
			px += 15.0

		var bm := BoxMesh.new()
		bm.size = Vector3(w, h, d)

		var mat := StandardMaterial3D.new()
		mat.albedo_color = palette[i % palette.size()]
		mat.roughness    = 0.65

		var mi := MeshInstance3D.new()
		mi.mesh              = bm
		mi.material_override = mat
		mi.position          = Vector3(px, h * 0.5, pz)
		mi.rotation_degrees.y = rng.randf_range(0.0, 360.0)
		add_child(mi)

	# --- Spheres ---
	for i: int in range(22):
		var r  := rng.randf_range(0.4, 2.8)
		var px := rng.randf_range(-90.0, 90.0)
		var pz := rng.randf_range(-90.0, 90.0)

		if Vector2(px, pz).length() < 10.0:
			px -= 15.0

		var sm := SphereMesh.new()
		sm.radius          = r
		sm.height          = r * 2.0
		sm.radial_segments = 20
		sm.rings           = 10

		var mat := StandardMaterial3D.new()
		mat.albedo_color = palette[(i + 3) % palette.size()]
		mat.roughness    = rng.randf_range(0.05, 0.85)
		mat.metallic     = rng.randf_range(0.00, 0.70)

		var mi := MeshInstance3D.new()
		mi.mesh              = sm
		mi.material_override = mat
		mi.position          = Vector3(px, r, pz)
		add_child(mi)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
func _setup_player() -> CharacterBody3D:
	var p: CharacterBody3D = load("res://player.gd").new()
	p.name = "Player"
	add_child(p)
	return p


# ---------------------------------------------------------------------------
# HUD: semi-transparent panel at top-left with coords + compass
# ---------------------------------------------------------------------------
func _setup_hud() -> void:
	var canvas := CanvasLayer.new()
	canvas.name = "HUD"
	add_child(canvas)

	# Background panel
	var style := StyleBoxFlat.new()
	style.bg_color                  = Color(0.0, 0.0, 0.0, 0.58)
	style.corner_radius_top_left    = 7
	style.corner_radius_top_right   = 7
	style.corner_radius_bottom_left = 7
	style.corner_radius_bottom_right = 7
	style.content_margin_left   = 14.0
	style.content_margin_right  = 14.0
	style.content_margin_top    = 10.0
	style.content_margin_bottom = 10.0

	var panel := PanelContainer.new()
	panel.position = Vector2(18.0, 18.0)
	panel.add_theme_stylebox_override("panel", style)
	canvas.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	panel.add_child(vbox)

	_coord_label = Label.new()
	_coord_label.text = "X:       0.0      Z:       0.0"
	_coord_label.add_theme_font_size_override("font_size", 22)
	_coord_label.add_theme_color_override("font_color", Color(0.85, 1.00, 0.85))
	vbox.add_child(_coord_label)

	_heading_label = Label.new()
	_heading_label.text = "Heading:    0.0°  N"
	_heading_label.add_theme_font_size_override("font_size", 22)
	_heading_label.add_theme_color_override("font_color", Color(0.85, 0.92, 1.00))
	vbox.add_child(_heading_label)

	# Tiny hint at bottom
	var hint := Label.new()
	hint.text = "Left stick: walk   Right stick: look"
	hint.add_theme_font_size_override("font_size", 15)
	hint.add_theme_color_override("font_color", Color(0.65, 0.65, 0.65))
	vbox.add_child(hint)

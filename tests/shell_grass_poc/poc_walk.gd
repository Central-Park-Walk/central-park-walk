extends Node3D
# Free-look walkable shell-grass POC. Same field as poc.gd, but driven by you:
#   Mouse        - look
#   W/A/S/D      - move (relative to gaze)
#   Q / E        - down / up
#   Shift        - sprint (3x)
#   Mouse wheel  - eye height up/down
#   F            - toggle sun angle (noon <-> low/raking)
#   G            - cycle shell_count 44 / 16 / 8 (eyeball the LOD tiers live)
#   Tab          - release/recapture mouse
#   Esc          - quit
# Heads-up text shows position, gaze pitch, shell count, fps.

const SHELLS_FULL := 44
const SHELL_TIERS := [44, 16, 8]

var _cam: Camera3D
var _sun: DirectionalLight3D
var _grass_mat: ShaderMaterial
var _hud: Label
var _yaw := 0.0
var _pitch := -18.0
var _speed := 4.0
var _eye_h := 1.7
var _sun_low := false
var _tier := 0

func _ready() -> void:
	_build()
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _build() -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var pmat := ProceduralSkyMaterial.new()
	pmat.sky_top_color = Color(0.38, 0.58, 0.86)
	pmat.sky_horizon_color = Color(0.78, 0.84, 0.86)
	sky.sky_material = pmat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_white = 6.0
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	_sun = DirectionalLight3D.new()
	_sun.rotation_degrees = Vector3(-52.0, -38.0, 0.0)
	_sun.light_energy = 1.5
	_sun.light_color = Color(1.0, 0.97, 0.90)
	_sun.shadow_enabled = true
	add_child(_sun)

	var ground := MeshInstance3D.new()
	var gpm := PlaneMesh.new()
	gpm.size = Vector2(120, 120)
	ground.mesh = gpm
	var gmat := StandardMaterial3D.new()
	gmat.albedo_color = Color(0.045, 0.085, 0.025)
	gmat.roughness = 1.0
	ground.material_override = gmat
	add_child(ground)

	var quad := PlaneMesh.new()
	quad.size = Vector2(120, 120)
	_grass_mat = ShaderMaterial.new()
	_grass_mat.shader = load("res://tests/shell_grass_poc/shell_grass.gdshader")
	_grass_mat.set_shader_parameter("shell_count", SHELLS_FULL)
	quad.material = _grass_mat
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = quad
	mm.instance_count = SHELLS_FULL
	for i in SHELLS_FULL:
		mm.set_instance_transform(i, Transform3D.IDENTITY)
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	add_child(mmi)

	_cam = Camera3D.new()
	_cam.fov = 65.0
	_cam.position = Vector3(0.0, _eye_h, 6.0)
	add_child(_cam)

	var ci := CanvasLayer.new()
	add_child(ci)
	_hud = Label.new()
	_hud.position = Vector2(14, 10)
	_hud.add_theme_color_override("font_color", Color.WHITE)
	_hud.add_theme_color_override("font_outline_color", Color.BLACK)
	_hud.add_theme_constant_override("outline_size", 6)
	ci.add_child(_hud)

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		_yaw -= e.relative.x * 0.12
		_pitch = clampf(_pitch - e.relative.y * 0.12, -90.0, 89.0)
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			_eye_h = clampf(_eye_h + 0.06, 0.15, 8.0)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_eye_h = clampf(_eye_h - 0.06, 0.15, 8.0)
	elif e is InputEventKey and e.pressed and not e.echo:
		match e.keycode:
			KEY_ESCAPE:
				get_tree().quit()
			KEY_TAB:
				if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
					Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
				else:
					Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
			KEY_F:
				_sun_low = not _sun_low
				_sun.rotation_degrees = Vector3(-12.0 if _sun_low else -52.0, -38.0, 0.0)
			KEY_G:
				_tier = (_tier + 1) % SHELL_TIERS.size()
				_grass_mat.set_shader_parameter("shell_count", SHELL_TIERS[_tier])

func _process(dt: float) -> void:
	var basis := Basis.from_euler(Vector3(deg_to_rad(_pitch), deg_to_rad(_yaw), 0.0))
	_cam.basis = basis
	var spd := _speed * (3.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0)
	var fwd := -basis.z
	var right := basis.x
	var move := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): move += fwd
	if Input.is_key_pressed(KEY_S): move -= fwd
	if Input.is_key_pressed(KEY_D): move += right
	if Input.is_key_pressed(KEY_A): move -= right
	if Input.is_key_pressed(KEY_E): move += Vector3.UP
	if Input.is_key_pressed(KEY_Q): move += Vector3.DOWN
	if move.length() > 0.0:
		_cam.position += move.normalized() * spd * dt
	# Keep eye height tracking the wheel-set value unless flying with Q/E.
	if not (Input.is_key_pressed(KEY_E) or Input.is_key_pressed(KEY_Q)):
		_cam.position.y = lerpf(_cam.position.y, _eye_h, clampf(dt * 6.0, 0.0, 1.0))

	var p := _cam.position
	_hud.text = "pos (%.1f, %.1f, %.1f)   pitch %.0f   eye %.2fm   shells %d   %d fps\nWASD move | mouse look | wheel eye-height | Q/E down/up | Shift sprint | F sun | G shell-LOD | Tab mouse | Esc quit" % [
		p.x, p.y, p.z, _pitch, _eye_h, SHELL_TIERS[_tier], Engine.get_frames_per_second()]

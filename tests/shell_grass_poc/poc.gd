extends Node3D
# Shell-grass POC driver. Builds an isolated lit scene, captures a straight-down
# ("looking at your feet") frame and an eye-level frame, writes them to tmp/, quits.

const OUT := "/home/chris/central-park-walk/tmp/"
const SHELLS := 44

var _cam: Camera3D

func _ready() -> void:
	_build()
	await _capture()
	get_tree().quit()

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

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52.0, -38.0, 0.0)
	sun.light_energy = 1.5
	sun.light_color = Color(1.0, 0.97, 0.90)
	add_child(sun)

	# Understory floor (so between-blade gaps read as soil/shade, not sky)
	var ground := MeshInstance3D.new()
	var gpm := PlaneMesh.new()
	gpm.size = Vector2(60, 60)
	ground.mesh = gpm
	var gmat := StandardMaterial3D.new()
	gmat.albedo_color = Color(0.045, 0.085, 0.025)
	gmat.roughness = 1.0
	ground.material_override = gmat
	add_child(ground)

	# Shell stack
	var quad := PlaneMesh.new()
	quad.size = Vector2(60, 60)
	var smat := ShaderMaterial.new()
	smat.shader = load("res://tests/shell_grass_poc/shell_grass.gdshader")
	smat.set_shader_parameter("shell_count", SHELLS)
	quad.material = smat
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = quad
	mm.instance_count = SHELLS
	for i in SHELLS:
		mm.set_instance_transform(i, Transform3D.IDENTITY)
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	add_child(mmi)

	_cam = Camera3D.new()
	add_child(_cam)

func _await_frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func _grab(path: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(path)

func _capture() -> void:
	# Straight down from ~2 m — the "look at your feet" case cards fail.
	_cam.fov = 60.0
	_cam.position = Vector3(0.0, 2.0, 0.0)
	_cam.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
	await _await_frames(10)
	await _grab(OUT + "shell_poc_down.png")
	# Eye level, gentle downward gaze across the field.
	_cam.position = Vector3(0.0, 1.7, 8.0)
	_cam.rotation_degrees = Vector3(-11.0, 0.0, 0.0)
	await _await_frames(10)
	await _grab(OUT + "shell_poc_eye.png")
	# Natural walking gaze (~-28) over nearby turf — the common in-game view.
	_cam.position = Vector3(0.0, 1.7, 3.0)
	_cam.rotation_degrees = Vector3(-28.0, 0.0, 0.0)
	await _await_frames(10)
	await _grab(OUT + "shell_poc_walk.png")
	# Far-grazing: near-horizontal gaze the length of the field — the stair-step /
	# shell-banding stress case (shallow angle crosses many shells per pixel).
	_cam.position = Vector3(0.0, 1.35, 28.0)
	_cam.rotation_degrees = Vector3(-4.0, 0.0, 0.0)
	await _await_frames(10)
	await _grab(OUT + "shell_poc_graze.png")

extends Node
## Weather particle system manager.
##
## Owns rain, snow, leaf, and blossom GPUParticles3D nodes.
## Provides cycle(), set_mode(), and per-frame update for
## particle positioning and seasonal effects.

enum Weather { CLEAR, RAIN, THUNDERSTORM, SNOW, FOG }
const WEATHER_NAMES: Array = ["clear", "rain", "thunderstorm", "snow", "fog"]

var mode: int = Weather.CLEAR
var snow_cover := 0.0
var rain_wetness := 0.0

var _rain_particles: GPUParticles3D
var _snow_particles: GPUParticles3D
var _leaf_particles: GPUParticles3D
var _blossom_particles: GPUParticles3D


func cycle(day_night: Node, time_of_day: float, wind_vec: Vector2,
		lightning_flash: float, user_gamma: float, season_t: float) -> void:
	_teardown()
	mode = (mode + 1) % Weather.size()
	_setup()
	day_night.force_apply(time_of_day, mode, wind_vec, lightning_flash, user_gamma, season_t)
	print("Weather: %s" % WEATHER_NAMES[mode])


func set_mode(new_mode, day_night: Node = null, time_of_day: float = 0.0,
		wind_vec := Vector2.ZERO, lightning_flash := 0.0,
		user_gamma := 1.0, season_t := 1.5) -> void:
	_teardown()
	if new_mode is String:
		var widx := WEATHER_NAMES.find(new_mode)
		mode = widx if widx >= 0 else Weather.CLEAR
	else:
		mode = new_mode
	_setup()
	# Pre-accumulate snow/rain so screenshots don't need to wait
	if mode == Weather.SNOW:
		snow_cover = 1.0
		rain_wetness = 0.0
	elif mode == Weather.RAIN:
		rain_wetness = 0.55
		snow_cover = 0.0
	elif mode == Weather.THUNDERSTORM:
		rain_wetness = 1.0
		snow_cover = 0.0
	else:
		snow_cover = 0.0
		rain_wetness = 0.0
	RenderingServer.global_shader_parameter_set("snow_cover", snow_cover)
	RenderingServer.global_shader_parameter_set("rain_wetness", rain_wetness)
	if day_night:
		day_night.force_apply(time_of_day, mode, wind_vec, lightning_flash, user_gamma, season_t)


func update(delta: float, player_pos: Vector3, wind_vec: Vector2, season_t: float) -> void:
	# Snow accumulation
	var prev_snow := snow_cover
	if mode == Weather.SNOW:
		snow_cover = minf(snow_cover + delta * 0.02, 1.0)
	else:
		snow_cover = maxf(snow_cover - delta * 0.05, 0.0)
	if snow_cover != prev_snow:
		RenderingServer.global_shader_parameter_set("snow_cover", snow_cover)

	# Rain wetness
	var prev_wet := rain_wetness
	if mode == Weather.RAIN or mode == Weather.THUNDERSTORM:
		var wet_cap := 1.0 if mode == Weather.THUNDERSTORM else 0.55
		rain_wetness = minf(rain_wetness + delta * 0.04, wet_cap)
	else:
		rain_wetness = maxf(rain_wetness - delta * 0.015, 0.0)
	if rain_wetness != prev_wet:
		RenderingServer.global_shader_parameter_set("rain_wetness", rain_wetness)

	# Particles follow player — wind deflects rain/snow
	if _rain_particles:
		_rain_particles.global_position = player_pos + Vector3(0, 14, 0)
		var rpm: ParticleProcessMaterial = _rain_particles.process_material
		rpm.gravity = Vector3(wind_vec.x * 5.0, -1.5, wind_vec.y * 5.0)
	if _snow_particles:
		_snow_particles.global_position = player_pos + Vector3(0, 15, 0)
		var spm: ParticleProcessMaterial = _snow_particles.process_material
		spm.gravity = Vector3(wind_vec.x * 3.0, -1.5, wind_vec.y * 3.0)

	# Autumn falling leaves
	var autumn_strength := smoothstep(1.8, 2.3, season_t) * (1.0 - smoothstep(2.8, 3.2, season_t))
	if autumn_strength > 0.05 and not _leaf_particles:
		_setup_leaf_particles()
	elif autumn_strength < 0.02 and _leaf_particles:
		_leaf_particles.queue_free()
		_leaf_particles = null
	if _leaf_particles:
		_leaf_particles.global_position = player_pos + Vector3(0, 12, 0)
		var lpm: ParticleProcessMaterial = _leaf_particles.process_material
		lpm.gravity = Vector3(wind_vec.x * 4.0, -0.3, wind_vec.y * 4.0)
		_leaf_particles.amount = int(lerpf(200.0, 2000.0, autumn_strength))

	# Spring cherry blossom petals
	var bloom_strength := smoothstep(0.1, 0.4, season_t) * (1.0 - smoothstep(0.7, 1.1, season_t))
	if season_t > 3.8:
		bloom_strength = maxf(bloom_strength, smoothstep(3.8, 3.95, season_t) * 0.5)
	if bloom_strength > 0.05 and not _blossom_particles:
		_setup_blossom_particles()
	elif bloom_strength < 0.02 and _blossom_particles:
		_blossom_particles.queue_free()
		_blossom_particles = null
	if _blossom_particles:
		_blossom_particles.global_position = player_pos + Vector3(0, 10, 0)
		var bpm: ParticleProcessMaterial = _blossom_particles.process_material
		bpm.gravity = Vector3(wind_vec.x * 3.0, -0.15, wind_vec.y * 3.0)
		_blossom_particles.amount = int(lerpf(100.0, 1200.0, bloom_strength))


func _teardown() -> void:
	if _rain_particles:
		_rain_particles.queue_free()
		_rain_particles = null
	if _snow_particles:
		_snow_particles.queue_free()
		_snow_particles = null


func _setup() -> void:
	if mode == Weather.RAIN:
		_setup_rain()
	elif mode == Weather.THUNDERSTORM:
		_setup_thunderstorm()
	elif mode == Weather.SNOW:
		_setup_snow()
	elif mode == Weather.FOG:
		print("Fog: heavy atmospheric fog")


func _extract_mesh_from_glb(path: String) -> Mesh:
	var scene: PackedScene = load(path)
	if not scene:
		push_warning("Could not load GLB: %s" % path)
		return null
	var inst := scene.instantiate()
	var mesh: Mesh = null
	for child in inst.get_children():
		if child is MeshInstance3D:
			mesh = child.mesh
			break
	inst.queue_free()
	return mesh


func _setup_rain() -> void:
	_rain_particles = GPUParticles3D.new()
	_rain_particles.amount = 6000
	_rain_particles.lifetime = 4.0
	_rain_particles.visibility_aabb = AABB(Vector3(-25, -15, -25), Vector3(50, 30, 50))
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 8.0
	pm.initial_velocity_min = 1.5
	pm.initial_velocity_max = 2.2
	pm.gravity = Vector3(0, -1.0, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(25.0, 0.5, 25.0)
	_rain_particles.process_material = pm
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.008, 0.12)
	_rain_particles.draw_pass_1 = mesh
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/rain_drop.gdshader")
	mat.set_shader_parameter("drop_color", Color(0.7, 0.75, 0.85, 0.25))
	mat.set_shader_parameter("core_brightness", 0.35)
	_rain_particles.material_override = mat
	add_child(_rain_particles)
	print("Rain: 6000 gentle drops")


func _setup_thunderstorm() -> void:
	_rain_particles = GPUParticles3D.new()
	_rain_particles.amount = 30000
	_rain_particles.lifetime = 2.5
	_rain_particles.visibility_aabb = AABB(Vector3(-25, -15, -25), Vector3(50, 30, 50))
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 12.0
	pm.initial_velocity_min = 5.0
	pm.initial_velocity_max = 7.5
	pm.gravity = Vector3(0, -3.0, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(25.0, 0.5, 25.0)
	_rain_particles.process_material = pm
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.014, 0.26)
	_rain_particles.draw_pass_1 = mesh
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/rain_drop.gdshader")
	mat.set_shader_parameter("drop_color", Color(0.6, 0.65, 0.75, 0.4))
	mat.set_shader_parameter("core_brightness", 0.25)
	_rain_particles.material_override = mat
	add_child(_rain_particles)
	print("Thunderstorm: 30000 heavy drops")


func _setup_snow() -> void:
	_snow_particles = GPUParticles3D.new()
	_snow_particles.amount = 14000
	_snow_particles.lifetime = 5.0
	_snow_particles.visibility_aabb = AABB(Vector3(-25, -20, -25), Vector3(50, 40, 50))
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 15.0
	pm.initial_velocity_min = 0.8
	pm.initial_velocity_max = 2.0
	pm.gravity = Vector3(0, -1.2, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(25.0, 0.5, 25.0)
	pm.orbit_velocity_min = 0.03
	pm.orbit_velocity_max = 0.12
	pm.angular_velocity_min = -25.0
	pm.angular_velocity_max = 25.0
	pm.damping_min = 0.8
	pm.damping_max = 2.0
	var snow_mesh := _extract_mesh_from_glb("res://models/vegetation/Snowflake.glb")
	if snow_mesh:
		pm.scale_min = 0.03
		pm.scale_max = 0.06
		_snow_particles.draw_pass_1 = snow_mesh
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color(0.92, 0.94, 1.0, 0.45)
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
		mat.cull_mode = BaseMaterial3D.CULL_DISABLED
		mat.rim_enabled = true
		mat.rim = 0.6
		mat.rim_tint = 0.3
		mat.emission_enabled = true
		mat.emission = Color(1.0, 0.95, 0.85)
		mat.emission_energy_multiplier = 0.4
		_snow_particles.material_override = mat
	else:
		var fallback := QuadMesh.new()
		fallback.size = Vector2(0.04, 0.04)
		pm.scale_min = 0.7
		pm.scale_max = 1.5
		_snow_particles.draw_pass_1 = fallback
		var mat := ShaderMaterial.new()
		mat.shader = load("res://shaders/snow.gdshader")
		mat.set_shader_parameter("snow_color", Color(0.92, 0.94, 1.0, 0.45))
		_snow_particles.material_override = mat
	_snow_particles.process_material = pm
	add_child(_snow_particles)
	print("Snow: 14000 snowflake particles")


func _setup_leaf_particles() -> void:
	_leaf_particles = GPUParticles3D.new()
	_leaf_particles.amount = 800
	_leaf_particles.lifetime = 8.0
	_leaf_particles.visibility_aabb = AABB(Vector3(-30, -15, -30), Vector3(60, 30, 60))
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 45.0
	pm.initial_velocity_min = 0.3
	pm.initial_velocity_max = 0.8
	pm.gravity = Vector3(0, -0.3, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(30.0, 2.0, 30.0)
	pm.orbit_velocity_min = 0.15
	pm.orbit_velocity_max = 0.45
	pm.angular_velocity_min = -90.0
	pm.angular_velocity_max = 90.0
	pm.scale_min = 0.025
	pm.scale_max = 0.045
	var alpha_curve := CurveTexture.new()
	var curve := Curve.new()
	curve.add_point(Vector2(0.0, 1.0))
	curve.add_point(Vector2(0.7, 0.9))
	curve.add_point(Vector2(1.0, 0.5))
	alpha_curve.curve = curve
	pm.alpha_curve = alpha_curve
	pm.damping_min = 1.0
	pm.damping_max = 3.0
	_leaf_particles.process_material = pm
	var leaf_paths := [
		"res://models/vegetation/Leaf_Autumn_01.glb",
		"res://models/vegetation/Leaf_Autumn_02.glb",
		"res://models/vegetation/Leaf_Autumn_03.glb",
		"res://models/vegetation/Leaf_Autumn_04.glb",
	]
	var fallback_mesh := QuadMesh.new()
	fallback_mesh.size = Vector2(0.035, 0.025)
	for i in range(4):
		var mesh := _extract_mesh_from_glb(leaf_paths[i])
		if not mesh:
			mesh = fallback_mesh
		match i:
			0: _leaf_particles.draw_pass_1 = mesh
			1: _leaf_particles.draw_pass_2 = mesh
			2: _leaf_particles.draw_pass_3 = mesh
			3: _leaf_particles.draw_pass_4 = mesh
	add_child(_leaf_particles)


func _setup_blossom_particles() -> void:
	_blossom_particles = GPUParticles3D.new()
	_blossom_particles.amount = 600
	_blossom_particles.lifetime = 12.0
	_blossom_particles.visibility_aabb = AABB(Vector3(-35, -15, -35), Vector3(70, 30, 70))
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 60.0
	pm.initial_velocity_min = 0.1
	pm.initial_velocity_max = 0.5
	pm.gravity = Vector3(0, -0.15, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(35.0, 3.0, 35.0)
	pm.orbit_velocity_min = 0.08
	pm.orbit_velocity_max = 0.25
	pm.angular_velocity_min = -45.0
	pm.angular_velocity_max = 45.0
	pm.scale_min = 0.5
	pm.scale_max = 1.2
	pm.color = Color(0.95, 0.82, 0.85, 0.90)
	var color_ramp := GradientTexture1D.new()
	var grad := Gradient.new()
	grad.set_color(0, Color(1.0, 0.92, 0.94, 0.95))
	grad.add_point(0.25, Color(0.98, 0.82, 0.86, 0.92))
	grad.add_point(0.5, Color(0.95, 0.72, 0.78, 0.88))
	grad.add_point(0.75, Color(0.92, 0.65, 0.72, 0.80))
	grad.set_color(1, Color(0.88, 0.60, 0.65, 0.50))
	color_ramp.gradient = grad
	pm.color_initial_ramp = color_ramp
	pm.damping_min = 1.0
	pm.damping_max = 3.0
	_blossom_particles.process_material = pm
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.018, 0.016)
	_blossom_particles.draw_pass_1 = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.97, 0.85, 0.88, 0.90)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mat.emission_enabled = true
	mat.emission = Color(0.95, 0.80, 0.82)
	mat.emission_energy_multiplier = 0.15
	_blossom_particles.material_override = mat
	add_child(_blossom_particles)

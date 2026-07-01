@tool
extends Sky

# User configurable properties
@export_group("Cloud Settings")

## Sets the wind direction in degrees, where 0 degrees is a wind coming from the north (+X axis),
## 90 degrees is east, 180 is south and 270 (or rather -90) is west.
@export_custom(PROPERTY_HINT_RANGE, "-180,180,0.1,radians_as_degrees")
var wind_direction: float = 0.0

## Sets the wind speed in m/s.
@export_custom(PROPERTY_HINT_RANGE, "0,120,0.1,or_greater,or_less,suffix:m/s")
var wind_speed: float = 1.0
# wind_speed is TRUE m/s at cloud altitude since 2026-06-11: _cloud_pos
# integrates it directly and clouds.glsl applies the integral as meters of
# world drift (factor 1). main.gd maps surface wind_vec to 4-24 m/s here.

@export
var density : float = 0.05
@export
var cloud_coverage : float = 0.25
@export
var time_offset : float = 0.0
# Cloud-lighting calibration multipliers (1.0 = upstream demo behavior).
@export
var sun_scale : float = 1.0
@export
var ambient_scale : float = 1.0

@export_group("Sky Settings")
@export
var sun_disk_scale : float = 1.0:
	set(scale):
		sun_disk_scale = scale
		sky_material.set_shader_parameter("sun_disk_scale", sun_disk_scale)
@export
var ground_color : Color = Color(1.0, 1.0, 1.0, 1.0)

@export_group("Performance Settings")
@export_enum("Very Fast(4):4", "Fast(16):16", "Default(64):64", "Performance(256):256")
var frames_to_update : int = 64:
	set(value):
		if frames_to_update == value and _initialized:
			return
		frames_to_update = value
		if _initialized:
			cleanup()
			update_performance()
			request_full_sky_init()

@export_range(32.0, 8192.0, 32.0)
var texture_size : int = 768: # Needs to be divisible by sqrt(frames_to_update)
	set(value):
		if texture_size == value and _initialized:
			return
		texture_size = value
		if _initialized:
			cleanup()
			update_performance()
			request_full_sky_init()

var sun : DirectionalLight3D

# Cloud-march light direction, set by day_night_cycle.gd (decoupled from
# the shadow light during twilight — 2026-06-11). Sun by day, moon at
# night. ZERO = unset, follow the light.
var celestial_direction := Vector3.ZERO
# Atmosphere-LUT sun direction (sky.md §6 P0): the REAL sun ALWAYS — the
# LUT darkens honestly through twilight instead of re-lighting off the
# night light. ZERO = unset, follow celestial/light.
var lut_direction := Vector3.ZERO
# Night factor (0 day → 1 night, set by day_night_cycle.gd): gates the
# march's moonlight + NYC city-glow terms. Rides ground_color.a in the
# push constant (which is otherwise full).
var night_light: float = 0.0

var date_time_location : Node3D

# Everything in the compute shader must be cached here so that it only updates
# after swapping to a new texture.
class FrameData:
	# User-configurable properties
	var wind_direction : Vector2 = Vector2(1.0, 0.0)
	var wind_speed : float = 1.0
	var density : float = 0.05
	var cloud_coverage : float = 0.25
	var time_offset : float = 0.0
	var ground_color : Color = Color(1.0, 1.0, 1.0, 1.0)
	
	# Properties we calculate based on the user-configurable ones
	var _time : float = 0.0
	var _cloud_pos : Vector2 = Vector2(0.0, 0.0)
	var _detailed_pos : Vector2 = Vector2(0.0, 0.0)
	var _weather_pos : Vector2 = Vector2(0.0, 0.0)
	# Latched once per texture swap — the sky texture renders region-by-
	# region over frames_to_update frames, so a live value would tear.
	var _weather_mix : float = 0.0
	# Same latching requirement: day_night_cycle sets sun_scale/ambient_scale
	# every frame from day_f(sun_energy). Read live they varied across the
	# region-by-region build during dawn/dusk and baked hard seams at the
	# update-region boundaries (the zenith "grid" over thin cloud).
	var sun_scale : float = 1.0
	var ambient_scale : float = 1.0

	# Properties updated by the light
	var LIGHT_DIRECTION : Vector3 = Vector3(0.0, -1.0, 0.0)
	var LIGHT_ENERGY : float = 1.0
	var LIGHT_COLOR : Color = Color(1.0, 1.0, 1.0, 1.0)
	
	func update_light_data(light : Light3D):
		LIGHT_DIRECTION = (light.transform.basis * Vector3(0.0, 0.0, 1.0)).normalized()
		LIGHT_ENERGY = light.light_energy
		LIGHT_COLOR = light.light_color.srgb_to_linear()

var frame_data : FrameData = FrameData.new()

# Per-weather-state weather maps (sky.md P1). The state machine targets a
# map by name; weather_at() in clouds.glsl crossfades current->target by
# weather_mix so fronts arrive over ~a minute instead of popping.
const WEATHER_MAP_NAMES := ["fair_cumulus", "stratocumulus_sheet",
		"stratus_overcast", "storm_congestus", "broken_dramatic"]
var _weather_maps := {}          # name -> Texture2D, loaded in delayed_init
var _map_from := "fair_cumulus"
var _map_to := "fair_cumulus"
var _weather_mix := 0.0
var _weather_fade_rate := 0.0    # mix units per second

# High ice layer drift (sky.md P2). Integrated continuously per render
# frame (the 2D sheet in clouds.gdshader would step visibly if it only
# moved on the ~64-frame texture swap). Upper winds run faster than the
# cloud deck, but the high deck is far away so apparent motion stays slow.
const HIGH_WIND_FACTOR := 2.5
var _high_pos := Vector2.ZERO
var _high_time := 0.0

var _noise_offset := Vector3(randf(), randf(), randf())  # random cloud shapes per session
# Random weather-map origin per session: the map is a baked texture, so
# without this every launch shows the same cloud formation in the same
# place (user-reported 2026-06-11). Rides the weather_pos push-constant
# slot (drift itself is wind_world() in the shader).
var _weather_origin := Vector2(randf(), randf())

# Reseed the shape offset from a caller-provided RNG (--cloud-seed=N gives
# reproducible skies for calibration captures).
func set_noise_seed(rng: RandomNumberGenerator) -> void:
	_noise_offset = Vector3(rng.randf(), rng.randf(), rng.randf())
	_weather_origin = Vector2(rng.randf(), rng.randf())
var update_position : Vector2i = Vector2i(0, 0)
var update_region_size : int = 96 # texture_size / sqrt(frames_to_update)
var num_workgroups : int = 12 # update_region_size / 8

var textures : Array = []
var texture_to_update : int = 0
var texture_to_blend_from : int = 1
var texture_to_blend_to : int = 2

var sky_lut := load(get_script().resource_path.get_base_dir() + "/sky_lut.tres")
var transmittance_tex := load(get_script().resource_path.get_base_dir() + "/transmittance_lut.tres")

var frame : int = 0
var _dither_index : int = 0  # advances per texture build; animates the IGN raymarch dither

var can_run = false
var needs_full_sky_init = true
var _initialized = false

func _init():
	# Weather maps must exist before the first set_weather_map() — the
	# day/night cycle's first force_apply lands in the same frame the
	# scene tree is built, EARLIER than the deferred delayed_init (a
	# missing map made the call a silent no-op, and with a frozen clock
	# it never repeated).
	for n in WEATHER_MAP_NAMES:
		var path: String = get_script().resource_path.get_base_dir() + "/weather_%s.bmp" % n
		if ResourceLoader.exists(path):
			_weather_maps[n] = load(path)
	if not _weather_maps.has("fair_cumulus"):
		# Fallback to the legacy single map if the per-state set is missing.
		_weather_maps["fair_cumulus"] = load(
				get_script().resource_path.get_base_dir() + "/weather.bmp")
	call_deferred("delayed_init")

# Switch the target weather map; crossfades over fade_seconds (<= 0 snaps).
# No-op when already targeting `name` — safe to call every _apply().
func set_weather_map(map_name: String, fade_seconds: float = 30.0) -> void:
	if map_name == _map_to or not _weather_maps.has(map_name):
		if map_name != _map_to and OS.is_stdout_verbose():
			print("[WMAP] set_weather_map('%s') UNKNOWN — have %s" % [map_name, _weather_maps.keys()])
		return
	if OS.is_stdout_verbose():
		print("[WMAP] iid=%d %s -> %s over %.0fs (can_run=%s)" % [get_instance_id(), _map_to, map_name, fade_seconds, can_run])
	if fade_seconds <= 0.0:
		_map_from = map_name
		_map_to = map_name
		_weather_mix = 0.0
		_weather_fade_rate = 0.0
	else:
		# Interrupting a fade mid-way snaps `from` to the old target —
		# transitions are minutes apart in practice, the pop is theoretical.
		_map_from = _map_to
		_map_to = map_name
		_weather_mix = 0.0
		_weather_fade_rate = 1.0 / fade_seconds
	if can_run:
		RenderingServer.call_on_render_thread(_rebuild_noise_uniform_set)


# Jump the in-progress fade to its end state (screenshot/capture bots).
func snap_weather_fade() -> void:
	if _map_from == _map_to:
		return
	_map_from = _map_to
	_weather_mix = 0.0
	_weather_fade_rate = 0.0
	if can_run:
		RenderingServer.call_on_render_thread(_rebuild_noise_uniform_set)


# Workaround due to the fact that exports are set after _init() is called
func delayed_init():
	_initialized = true
	update_performance()

	# This calls "update_sky" at the beginning of the render loop automatically.
	RenderingServer.connect("frame_pre_draw", update_sky)

func update_performance():
	var frames_sqrt : int = int(sqrt(frames_to_update))
	update_region_size = texture_size / frames_sqrt
	if texture_size % frames_sqrt !=0:
		texture_size = update_region_size * frames_sqrt
		print("texture_size is not a multiple of sqrt(frames_to_update), changing to: ", texture_size)
	num_workgroups = (update_region_size + 7) / 8

	sky_material.set_shader_parameter("sun_disk_scale", sun_disk_scale)
	RenderingServer.call_on_render_thread.call_deferred(_initialize_compute_code.bind(texture_size))

func request_full_sky_init():
	needs_full_sky_init = true

# Initialize and update the sky so it is visible in the first frame.
func initialize_sky():
	_update_per_frame_data()
	for i in range(frames_to_update * 2):
		update_sky()

func update_sky():
	if not can_run:
		return

	if needs_full_sky_init:
		needs_full_sky_init = false
		initialize_sky()

	if frame >= frames_to_update:
		# Increase our next texture index
		texture_to_update = (texture_to_update + 1) % 3
		texture_to_blend_from = (texture_to_blend_from + 1) % 3
		texture_to_blend_to = (texture_to_blend_to + 1) % 3
		_dither_index += 1  # advance the blue-noise dither once per texture build
		_update_per_frame_data() # Only call once per update otherwise quads get out of sync

		sky_material.set_shader_parameter("blend_from_texture", textures[texture_to_blend_from])
		sky_material.set_shader_parameter("blend_to_texture", textures[texture_to_blend_to])
		
		sky_material.set_shader_parameter("sky_blend_from_texture", sky_lut.back_texture[0])
		sky_material.set_shader_parameter("sky_blend_to_texture", sky_lut.back_texture[1])

		frame = 0

	sky_material.set_shader_parameter("blend_amount", float(frame) / float(frames_to_update))

	# Advect the high ice layer continuously (sky.md P2). Same wind as the
	# deck, scaled up for the faster upper flow; integrated every frame so
	# the 2D sheet drifts smoothly rather than stepping on texture swaps.
	var hnow := Time.get_ticks_msec() / 1000.0
	var hdt := hnow - _high_time
	_high_time = hnow
	if hdt > 0.0 and hdt < 1.0:
		_high_pos += frame_data.wind_direction.normalized() \
				* frame_data.wind_speed * HIGH_WIND_FACTOR * hdt
	sky_material.set_shader_parameter("high_cloud_offset", _high_pos)

	# Snapshot the push constant on the MAIN thread (captures frame_data,
	# update_position and dither_index at queue time) so the render thread
	# can't read them mid-mutation — and so the region matches update_position
	# before it advances below.
	RenderingServer.call_on_render_thread(_render_process.bind(texture_to_update, _fill_push_constant()))
	
	update_position.x += update_region_size
	if update_position.x >= texture_size:
		update_position.x = 0
		update_position.y += update_region_size
	if update_position.y >= texture_size:
		update_position = Vector2i(0, 0)
		
	frame += 1

func _update_per_frame_data():
	if sun:
		frame_data.update_light_data(sun)
		if celestial_direction != Vector3.ZERO:
			frame_data.LIGHT_DIRECTION = celestial_direction
	frame_data.wind_direction = Vector2.from_angle(wind_direction)
	frame_data.wind_speed = wind_speed
	frame_data.density = density
	frame_data.cloud_coverage = cloud_coverage
	frame_data.time_offset = time_offset
	frame_data.ground_color = ground_color
	# Night factor rides the (unread) ground_color alpha — see night_light.
	frame_data.ground_color.a = night_light
	frame_data.sun_scale = sun_scale
	frame_data.ambient_scale = ambient_scale

	# Before we can push those constants, there's a bit of math we need to do
	var time = Time.get_ticks_msec() / 1000.0
	var delta = time - frame_data._time
	var wind_direction_normalized = frame_data.wind_direction.normalized()

	# Integrate cloud drift. (_detailed_pos/_weather_pos were integrated here too
	# but neither is read by the shader — the weather map rides _weather_origin.)
	frame_data._time = time
	frame_data._cloud_pos += delta * wind_direction_normalized * frame_data.wind_speed

	# Advance the weather-map crossfade (sky.md P1)
	if _weather_fade_rate > 0.0:
		_weather_mix = minf(_weather_mix + delta * _weather_fade_rate, 1.0)
		if _weather_mix >= 1.0:
			# Fade complete: canonicalize so both bindings carry the target.
			_map_from = _map_to
			_weather_mix = 0.0
			_weather_fade_rate = 0.0
			RenderingServer.call_on_render_thread(_rebuild_noise_uniform_set)
	frame_data._weather_mix = _weather_mix
	if OS.is_stdout_verbose():
		print("[CLOUDWIND] speed=%.1f dir=(%.2f,%.2f) cloud_pos=(%.0f,%.0f) dt=%.2f"
				% [frame_data.wind_speed, wind_direction_normalized.x,
				wind_direction_normalized.y, frame_data._cloud_pos.x,
				frame_data._cloud_pos.y, delta])

	# LUT sun = the real sun (P0); falls back to the march light if unset.
	sky_lut.update_lut(lut_direction if lut_direction != Vector3.ZERO
			else frame_data.LIGHT_DIRECTION)

func _validate_property(property):
	if property.name == "sky_material" or property.name == "process_mode":
		property.usage &= ~PROPERTY_USAGE_EDITOR

# NOTE: no NOTIFICATION_PREDELETE handler — during Resource PREDELETE the
# GDScript `self` is null, so neither the original `cleanup()` dispatch nor
# inline self-member access (rd, texture_rd, update_sky) is reachable.
# RenderingDevice frees all owned RIDs at engine teardown, so the texture/
# shader/sampler RIDs cloud_sky owns get reclaimed even without explicit
# disposal. cleanup() stays because the texture_size / frames_to_update
# setters still need to re-init while the script is live.

func cleanup():
	can_run = false
	frame = 0
	texture_to_update = 0
	texture_to_blend_from = 1
	texture_to_blend_to = 2
	update_position = Vector2i(0, 0)
	for i in range(3):
		if texture_rd[i]:
			rd.free_rid(texture_rd[i])
	if shader_rd:
		rd.free_rid(shader_rd)
	if noise_sampler:
		rd.free_rid(noise_sampler)
	if sky_sampler:
		rd.free_rid(sky_sampler)


###############################################################################
# Everything after this point is designed to run on our rendering thread

var rd : RenderingDevice

var shader_rd : RID
var pipeline : RID

# We use 3 textures:
# - One to render into
# - One that contains the last frame rendered
# - One for the frame before that
var texture_rd : Array = [ RID(), RID(), RID() ]
var texture_set : Array = [ RID(), RID(), RID() ]
var noise_uniform_set : RID = RID()
var sky_uniform_set : Array = [ RID(), RID(), RID() ]
var noise_sampler
var sky_sampler

func _render_process(p_texture_to_update, push_constant):
	textures[p_texture_to_update].texture_rd_rid = texture_rd[p_texture_to_update]

	# Run our compute shader.
	var compute_list := rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(compute_list, pipeline)
	rd.compute_list_bind_uniform_set(compute_list, sky_uniform_set[(sky_lut.current_texture + 2) % 3], 2)
	rd.compute_list_bind_uniform_set(compute_list, noise_uniform_set, 1)
	rd.compute_list_bind_uniform_set(compute_list, texture_set[p_texture_to_update], 0)

	rd.compute_list_set_push_constant(compute_list, push_constant.to_byte_array(), push_constant.size() * 4)
	rd.compute_list_dispatch(compute_list, num_workgroups, num_workgroups, 1)
	rd.compute_list_end()

	
func _fill_push_constant():
	var push_constant : PackedFloat32Array = PackedFloat32Array()
	# The order of properties here must match those in clouds.glsl, including padding
	push_constant.push_back(texture_size)
	push_constant.push_back(texture_size)
	push_constant.push_back(update_position.x)
	push_constant.push_back(update_position.y)
	
	push_constant.push_back(frame_data._cloud_pos.x)
	push_constant.push_back(frame_data._cloud_pos.y)
	push_constant.push_back(frame_data._detailed_pos.x)
	push_constant.push_back(frame_data._detailed_pos.y)

	push_constant.push_back(_weather_origin.x)
	push_constant.push_back(_weather_origin.y)
	push_constant.push_back(_noise_offset.x)  # noise_offset xy
	push_constant.push_back(_noise_offset.y)
	
	push_constant.push_back(frame_data.ground_color.r)
	push_constant.push_back(frame_data.ground_color.g)
	push_constant.push_back(frame_data.ground_color.b)
	push_constant.push_back(frame_data.ground_color.a)
	
	push_constant.push_back(frame_data.LIGHT_DIRECTION.x)
	push_constant.push_back(frame_data.LIGHT_DIRECTION.y)
	push_constant.push_back(frame_data.LIGHT_DIRECTION.z)
	push_constant.push_back(frame_data.LIGHT_ENERGY)
	
	push_constant.push_back(frame_data.LIGHT_COLOR.r)
	push_constant.push_back(frame_data.LIGHT_COLOR.g)
	push_constant.push_back(frame_data.LIGHT_COLOR.b)
	push_constant.push_back(frame_data._time)
	
	push_constant.push_back(_noise_offset.z)  # noise_offset_z
	push_constant.push_back(frame_data.density)
	push_constant.push_back(frame_data.cloud_coverage)
	push_constant.push_back(frame_data.time_offset)

	push_constant.push_back(frame_data.sun_scale)
	push_constant.push_back(frame_data.ambient_scale)
	push_constant.push_back(frame_data._weather_mix)
	push_constant.push_back(float(_dither_index))  # dither_index (temporal blue-noise)

	return push_constant

func _create_uniform_set(p_texture_rd : RID) -> RID:
	var uniform := RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
	uniform.binding = 0
	uniform.add_id(p_texture_rd)
	return rd.uniform_set_create([uniform], shader_rd, 0)

func _create_noise_uniform_set() -> RID:
	var uniforms = []

	var sampler_state = RDSamplerState.new()
	sampler_state.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_REPEAT
	sampler_state.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_REPEAT
	sampler_state.repeat_w = RenderingDevice.SAMPLER_REPEAT_MODE_REPEAT
	sampler_state.mag_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	sampler_state.min_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	sampler_state.mip_filter = RenderingDevice.SAMPLER_FILTER_LINEAR

	if noise_sampler:
		rd.free_rid(noise_sampler)  # was leaked on every weather-map switch
	noise_sampler = rd.sampler_create(sampler_state)

	var large_scale_noise = preload("perlworlnoise.tga")
	var LSN_rd = RenderingServer.texture_get_rd_texture(large_scale_noise.get_rid())
	
	var uniform := RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	uniform.binding = 0
	uniform.add_id(noise_sampler)
	uniform.add_id(LSN_rd)
	uniforms.push_back(uniform)
	
	var small_scale_noise = preload("worlnoise.bmp")
	var SSN_rd = RenderingServer.texture_get_rd_texture(small_scale_noise.get_rid())
	
	uniform = RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	uniform.binding = 1
	uniform.add_id(noise_sampler)
	uniform.add_id(SSN_rd)
	uniforms.push_back(uniform)
	
	if OS.is_stdout_verbose():
		print("[WMAP] iid=%d binding uniform set: from=%s to=%s" % [get_instance_id(), _map_from, _map_to])
	var weather_from: Texture2D = _weather_maps.get(_map_from, _weather_maps.values()[0])
	var W_rd = RenderingServer.texture_get_rd_texture(weather_from.get_rid())

	uniform = RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	uniform.binding = 2
	uniform.add_id(noise_sampler)
	uniform.add_id(W_rd)
	uniforms.push_back(uniform)

	var weather_to: Texture2D = _weather_maps.get(_map_to, weather_from)
	var WB_rd = RenderingServer.texture_get_rd_texture(weather_to.get_rid())

	uniform = RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	uniform.binding = 3
	uniform.add_id(noise_sampler)
	uniform.add_id(WB_rd)
	uniforms.push_back(uniform)

	return rd.uniform_set_create(uniforms, shader_rd, 1)


# Rebind the weather-map pair after a map switch (render thread only).
func _rebuild_noise_uniform_set() -> void:
	if not can_run:
		return
	if noise_uniform_set.is_valid():
		rd.free_rid(noise_uniform_set)
	noise_uniform_set = _create_noise_uniform_set()
	
func _create_sky_uniform_set(tex_id : int) -> RID:
	var uniforms = []
		
	var uniform = RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	uniform.binding = 0
	uniform.add_id(sky_sampler)
	uniform.add_id(sky_lut.texture_rd[tex_id])
	uniforms.push_back(uniform)
	
	return rd.uniform_set_create(uniforms, shader_rd, 2)

func _initialize_compute_code(p_texture_size):
	rd = RenderingServer.get_rendering_device()

	# Create our shader
	var shader_file = load(get_script().resource_path.get_base_dir() + "/clouds.glsl")
	var shader_spirv: RDShaderSPIRV = shader_file.get_spirv()
	shader_rd = rd.shader_create_from_spirv(shader_spirv)
	if not shader_rd.is_valid():
		can_run = false
		printerr("CloudSky: compute shader compilation FAILED — clouds disabled")
		var err_msg = shader_spirv.get_stage_compile_error(RenderingDevice.SHADER_STAGE_COMPUTE)
		if err_msg:
			printerr("  Compute stage error: ", err_msg)
		return
	pipeline = rd.compute_pipeline_create(shader_rd)

	# Create our textures to manage our wave
	var tf : RDTextureFormat = RDTextureFormat.new()
	tf.format = RenderingDevice.DATA_FORMAT_R16G16B16A16_SFLOAT
	tf.texture_type = RenderingDevice.TEXTURE_TYPE_2D
	tf.width = p_texture_size
	tf.height = p_texture_size
	tf.depth = 1
	tf.array_layers = 1
	tf.mipmaps = 1
	tf.usage_bits = RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT + RenderingDevice.TEXTURE_USAGE_STORAGE_BIT + RenderingDevice.TEXTURE_USAGE_CAN_UPDATE_BIT + RenderingDevice.TEXTURE_USAGE_CAN_COPY_TO_BIT
	if Engine.is_editor_hint():
		tf.usage_bits += RenderingDevice.TEXTURE_USAGE_CAN_COPY_FROM_BIT
	noise_uniform_set = _create_noise_uniform_set()

	var sampler_state = RDSamplerState.new()
	sampler_state.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	sampler_state.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	sampler_state.repeat_w = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	sampler_state.mag_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	sampler_state.min_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	sampler_state.mip_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	
	sky_sampler = rd.sampler_create(sampler_state)

	sky_uniform_set[0] = _create_sky_uniform_set(0)
	sky_uniform_set[1] = _create_sky_uniform_set(1)
	sky_uniform_set[2] = _create_sky_uniform_set(2)
	textures.clear()

	for i in range(3):
		# Create our texture
		texture_rd[i] = rd.texture_create(tf, RDTextureView.new(), [])

		# Make sure our textures are cleared
		rd.texture_clear(texture_rd[i], Color(float(i==0), float(i==1), float(i==2), 0), 0, 1, 0, 1)

		# Now create our uniform set so we can use these textures in our shader
		texture_set[i] = _create_uniform_set(texture_rd[i])
		textures.push_back(Texture2DRD.new())

	can_run = true
	print("CloudSky: compute pipeline initialized — volumetric clouds active")

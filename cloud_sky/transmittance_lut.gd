@tool
extends Texture2DRD

# Generates the transmittance LUT at load, AND the multiple-scattering LUT
# (Hillaire 2020) which depends on it. The MS LUT is co-computed here, right
# after the transmittance texture is written, so the dependency ordering is
# deterministic (no cross-resource render-thread race). The MS texture RID is
# exposed via `ms_texture_rd` for the sky-view LUT compute (sky_lut.gd) to bind.

var texture_size := Vector2i(256, 64)
var ms_texture_size := Vector2i(32, 32)

var rd : RenderingDevice

var shader : RID
var pipeline : RID
var texture_rd : RID
var texture_set : RID

var ms_shader : RID
var ms_pipeline : RID
var ms_texture_rd : RID
var ms_out_set : RID
var ms_in_set : RID
var ms_sampler : RID

func _init():
	rd = RenderingServer.get_rendering_device()
	RenderingServer.call_on_render_thread(_initialize_texture)
	RenderingServer.call_on_render_thread.call_deferred(_initialize_compute_code)

func _notification(what):
	if what == NOTIFICATION_PREDELETE:
		if texture_rd:
			rd.free_rid(texture_rd)
		if shader:
			rd.free_rid(shader)
		if ms_texture_rd:
			rd.free_rid(ms_texture_rd)
		if ms_shader:
			rd.free_rid(ms_shader)
		if ms_sampler:
			rd.free_rid(ms_sampler)

func _create_image_set(p_texture_rd : RID, p_shader : RID) -> RID:
	var uniform := RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
	uniform.binding = 0
	uniform.add_id(p_texture_rd)
	return rd.uniform_set_create([uniform], p_shader, 0)

func _make_texture(size : Vector2i) -> RID:
	var tf : RDTextureFormat = RDTextureFormat.new()
	tf.format = RenderingDevice.DATA_FORMAT_R16G16B16A16_SFLOAT
	tf.texture_type = RenderingDevice.TEXTURE_TYPE_2D
	tf.width = size.x
	tf.height = size.y
	tf.depth = 1
	tf.array_layers = 1
	tf.mipmaps = 1
	tf.usage_bits = RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT + RenderingDevice.TEXTURE_USAGE_STORAGE_BIT + RenderingDevice.TEXTURE_USAGE_CAN_UPDATE_BIT + RenderingDevice.TEXTURE_USAGE_CAN_COPY_TO_BIT
	if Engine.is_editor_hint():
		tf.usage_bits += RenderingDevice.TEXTURE_USAGE_CAN_COPY_FROM_BIT
	return rd.texture_create(tf, RDTextureView.new(), [])

func _initialize_texture():
	texture_rd = _make_texture(texture_size)
	ms_texture_rd = _make_texture(ms_texture_size)

func _load_compute(path : String) -> RID:
	var shader_file = load(get_script().resource_path.get_base_dir() + path)
	var shader_spirv: RDShaderSPIRV = shader_file.get_spirv()
	var s := rd.shader_create_from_spirv(shader_spirv)
	if not s.is_valid():
		printerr("transmittance_lut: invalid shader " + path)
	return s

func _push4(a : float, b : float) -> PackedByteArray:
	var pc : PackedFloat32Array = PackedFloat32Array()
	pc.push_back(a)
	pc.push_back(b)
	pc.push_back(0.0)
	pc.push_back(0.0)
	return pc.to_byte_array()

func _initialize_compute_code():
	# --- transmittance LUT ---
	shader = _load_compute("/transmittance-lut.glsl")
	if not shader.is_valid():
		return
	pipeline = rd.compute_pipeline_create(shader)
	texture_set = _create_image_set(texture_rd, shader)
	texture_rd_rid = texture_rd

	var cl := rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(cl, pipeline)
	rd.compute_list_set_push_constant(cl, _push4(texture_size.x, texture_size.y), 16)
	rd.compute_list_bind_uniform_set(cl, texture_set, 0)
	rd.compute_list_dispatch(cl, 32, 8, 1)
	rd.compute_list_end()

	# --- multiple-scattering LUT (samples the transmittance LUT above) ---
	ms_shader = _load_compute("/multiscatter-lut.glsl")
	if not ms_shader.is_valid():
		return
	ms_pipeline = rd.compute_pipeline_create(ms_shader)
	ms_out_set = _create_image_set(ms_texture_rd, ms_shader)

	var ss := RDSamplerState.new()
	ss.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	ss.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	ss.mag_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	ss.min_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	ms_sampler = rd.sampler_create(ss)
	var tin := RDUniform.new()
	tin.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	tin.binding = 0
	tin.add_id(ms_sampler)
	tin.add_id(texture_rd)
	ms_in_set = rd.uniform_set_create([tin], ms_shader, 1)

	var cl2 := rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(cl2, ms_pipeline)
	rd.compute_list_set_push_constant(cl2, _push4(ms_texture_size.x, ms_texture_size.y), 16)
	rd.compute_list_bind_uniform_set(cl2, ms_out_set, 0)
	rd.compute_list_bind_uniform_set(cl2, ms_in_set, 1)
	rd.compute_list_dispatch(cl2, 4, 4, 1)
	rd.compute_list_end()

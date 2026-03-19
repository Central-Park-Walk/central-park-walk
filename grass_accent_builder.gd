# grass_accent_builder.gd
# Chunk-based MultiMesh accent layers on top of particle grass.
# Uses decimated BD3D tufts (clover, dandelion, meadow clumps, dry grass)
# placed at lower density (1-5 per m²) for visual richness and variety.
# Seasonal: clover/dandelion spring-summer, dry grass autumn-winter.

var _loader
var _meshes: Dictionary = {}   # tuft_name -> Mesh
var _textures: Dictionary = {} # tuft_name -> Texture2D (albedo from BD3D)
var _active_chunks: Dictionary = {}
var _last_update_pos := Vector3(-99999, 0, -99999)
var _build_queue: Array = []
var _queued_set: Dictionary = {}

# Cached data refs
var _atlas_data: PackedByteArray
var _atlas_res: int
var _atlas_scale: float
var _atlas_half: float
var _hm_data: Array
var _hm_w: int
var _hm_d: int
var _hm_ws: float
var _hm_half: float

const CHUNK := 20.0
const LOAD_RANGE := 80.0
const UNLOAD_RANGE := 90.0
const UPDATE_DIST := 4.0
const VIS_END := 60.0
const VIS_FADE_MARGIN := 12.0

# Accent types with their tuft mesh names and zone rules.
# density = instances per 100 m². seasons: 0=all, 1=spring-summer, 2=autumn-winter
const ACCENT_TYPES := [
	# Clover patches on maintained lawns (spring-summer)
	{"name": "Tuft_Clover",         "season": 1, "scale": [0.8, 1.4]},
	{"name": "Tuft_Clover_B",       "season": 1, "scale": [0.7, 1.3]},
	# Dandelion on lawns (spring)
	{"name": "Tuft_Dandelion",      "season": 1, "scale": [0.8, 1.3]},
	{"name": "Tuft_Dandelion_B",    "season": 1, "scale": [0.7, 1.2]},
	# Meadow clumps (taller accent on maintained lawns)
	{"name": "Tuft_Meadow",         "season": 0, "scale": [0.6, 1.1]},
	{"name": "Tuft_Meadow_B",       "season": 0, "scale": [0.6, 1.0]},
	{"name": "Tuft_Meadow_C",       "season": 0, "scale": [0.5, 1.0]},
	# Tall wild grass (nature reserve accent)
	{"name": "Tuft_Tall",           "season": 0, "scale": [0.7, 1.3]},
	{"name": "Tuft_Tall_B",         "season": 0, "scale": [0.7, 1.2]},
	# Dry / dead grass (autumn-winter accent)
	{"name": "Tuft_Dry_Small",      "season": 2, "scale": [0.8, 1.3]},
	{"name": "Tuft_Dry_Medium",     "season": 2, "scale": [0.7, 1.2]},
	{"name": "Tuft_Dead",           "season": 2, "scale": [0.6, 1.1]},
	# Forest clover (woodland floor accent)
	{"name": "Tuft_Clover_Forest",  "season": 1, "scale": [0.7, 1.2]},
]

# Zone → list of [accent_type_index, density_per_100m2]
# Zones: 0,2=maintained lawn, 1=garden, 3,7=sports, 5=nature reserve, 10,11=woodland
const ZONE_ACCENTS := {
	0: [  # Maintained lawn (Sheep Meadow, Great Lawn)
		[0, 3.0], [1, 2.0],    # Clover patches
		[2, 1.5], [3, 1.0],    # Dandelions
		[4, 0.8],               # Occasional taller clump
	],
	2: [  # Maintained lawn (general)
		[0, 2.5], [1, 1.5],    # Clover
		[2, 1.0],               # Dandelion
		[5, 0.5], [6, 0.5],    # Occasional meadow clump
	],
	1: [  # Garden — sparse accents, mostly manicured
		[0, 1.5],               # Clover
		[2, 0.5],               # Rare dandelion
	],
	3: [  # Sports fields — minimal accents
		[0, 1.0],               # Light clover
	],
	7: [  # Sports — minimal
		[0, 1.0],
	],
	5: [  # Nature reserve — wild accents
		[7, 4.0], [8, 3.0],    # Tall wild grass
		[4, 2.0], [5, 1.5], [6, 1.0],  # Meadow clumps
		[9, 2.0], [10, 1.5], [11, 1.0],  # Dry/dead (seasonal)
	],
	10: [ # Woodland
		[12, 2.5],              # Forest clover
		[9, 1.0],               # Dry grass
		[5, 0.5],               # Sparse meadow
	],
	11: [ # Woodland
		[12, 2.0],
		[9, 0.8],
		[6, 0.5],
	],
}

var _render_shader: Shader


func _init(loader) -> void:
	_loader = loader


func _build_grass_accents() -> void:
	_render_shader = load("res://shaders/grass_particle_render.gdshader")
	if not _render_shader:
		print("grass_accent: render shader not found")
		return

	# Cache data refs
	_atlas_data = _loader._atlas_data
	_atlas_res = _loader._atlas_res
	_atlas_scale = float(_atlas_res) / _loader._hm_world_size
	_atlas_half = _loader._hm_world_size * 0.5
	_hm_data = _loader._hm_data
	_hm_w = _loader._hm_width
	_hm_d = _loader._hm_depth
	_hm_ws = _loader._hm_world_size
	_hm_half = _hm_ws * 0.5

	# Load all tuft meshes
	var loaded := 0
	for at in ACCENT_TYPES:
		var path := "res://models/vegetation/%s.glb" % at.name
		var abs_path := ProjectSettings.globalize_path(path)
		var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
		if meshes.is_empty():
			print("  grass_accent: %s not found" % at.name)
			continue
		var mesh: Mesh = meshes.values()[0]
		# Extract albedo texture from BD3D material
		var albedo: Texture2D = null
		for si in mesh.get_surface_count():
			var mat = mesh.surface_get_material(si)
			if mat is StandardMaterial3D and mat.albedo_texture:
				albedo = mat.albedo_texture
				break
		_meshes[at.name] = mesh
		if albedo:
			_textures[at.name] = albedo
		loaded += 1
	print("grass_accent: loaded %d/%d tuft meshes" % [loaded, ACCENT_TYPES.size()])

	# Queue initial chunks near spawn
	var spawn := Vector3(-480, 0, 1020)
	_update_chunks_near(spawn)


func update_camera(camera_pos: Vector3) -> void:
	var dv := camera_pos - _last_update_pos
	if dv.x * dv.x + dv.z * dv.z > UPDATE_DIST * UPDATE_DIST:
		_last_update_pos = camera_pos
		_update_chunks_near(camera_pos)
	_process_queue(camera_pos)


func _update_chunks_near(pos: Vector3) -> void:
	var cx0 := int(floor((pos.x - LOAD_RANGE) / CHUNK))
	var cx1 := int(floor((pos.x + LOAD_RANGE) / CHUNK))
	var cz0 := int(floor((pos.z - LOAD_RANGE) / CHUNK))
	var cz1 := int(floor((pos.z + LOAD_RANGE) / CHUNK))

	var needed: Dictionary = {}
	for cx in range(cx0, cx1 + 1):
		for cz in range(cz0, cz1 + 1):
			var wx := cx * CHUNK + CHUNK * 0.5
			var wz := cz * CHUNK + CHUNK * 0.5
			var dx := wx - pos.x
			var dz := wz - pos.z
			if dx * dx + dz * dz > LOAD_RANGE * LOAD_RANGE:
				continue
			# Atlas: must be grass surface (type 1)
			var ai := int((wx + _atlas_half) * _atlas_scale)
			var aj := int((wz + _atlas_half) * _atlas_scale)
			if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
				continue
			var surf: int = _atlas_data[(aj * _atlas_res + ai) * 2]
			if surf != 1:
				continue
			var ck := "%d|%d" % [cx, cz]
			needed[ck] = true

	# Unload distant
	var to_remove: Array = []
	for ck in _active_chunks:
		if not needed.has(ck):
			var parts: Array = _active_chunks[ck]
			for nd in parts:
				if is_instance_valid(nd):
					nd.queue_free()
			to_remove.append(ck)
	for ck in to_remove:
		_active_chunks.erase(ck)

	# Queue new
	for ck in needed:
		if not _active_chunks.has(ck) and not _queued_set.has(ck):
			_build_queue.append(ck)
			_queued_set[ck] = true


func _process_queue(pos: Vector3) -> void:
	if _build_queue.is_empty():
		return
	_build_queue.sort_custom(func(a: String, b: String) -> bool:
		var pa := a.split("|")
		var pb := b.split("|")
		var da := (int(pa[0]) * CHUNK - pos.x) ** 2 + (int(pa[1]) * CHUNK - pos.z) ** 2
		var db := (int(pb[0]) * CHUNK - pos.x) ** 2 + (int(pb[1]) * CHUNK - pos.z) ** 2
		return da < db)
	var ck: String = _build_queue.pop_front()
	_queued_set.erase(ck)
	var cp := ck.split("|")
	var wx := int(cp[0]) * CHUNK + CHUNK * 0.5
	var wz := int(cp[1]) * CHUNK + CHUNK * 0.5
	if (wx - pos.x) ** 2 + (wz - pos.z) ** 2 > UNLOAD_RANGE * UNLOAD_RANGE:
		return
	_build_chunk(ck)


func _get_zone_id(wx: float, wz: float) -> int:
	"""Sample the world atlas landuse zone at a world position."""
	var ai := int((wx + _atlas_half) * _atlas_scale)
	var aj := int((wz + _atlas_half) * _atlas_scale)
	if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
		return -1
	# The landuse zone is stored differently from the atlas surface type.
	# We need to check which zone this chunk belongs to.
	# Use the foliage zone system from undergrowth_builder if available.
	if _loader._undergrowth_builder and _loader._undergrowth_builder._zone_map:
		var ck := "%d|%d" % [int(floor(wx / CHUNK)), int(floor(wz / CHUNK))]
		if _loader._undergrowth_builder._zone_map.has(ck):
			return _loader._undergrowth_builder._zone_map[ck]
	# Fallback: use atlas surface type 1 = grass, assume maintained lawn
	return 0


func _sample_height(wx: float, wz: float) -> float:
	var xi: float = (wx + _hm_half) / _hm_ws * (_hm_w - 1)
	var zi: float = (wz + _hm_half) / _hm_ws * (_hm_d - 1)
	var xi0: int = clampi(int(xi), 0, _hm_w - 2)
	var zi0: int = clampi(int(zi), 0, _hm_d - 2)
	var fx: float = xi - xi0
	var fz: float = zi - zi0
	var h00: float = _hm_data[zi0 * _hm_w + xi0]
	var h10: float = _hm_data[zi0 * _hm_w + xi0 + 1]
	var h01: float = _hm_data[(zi0 + 1) * _hm_w + xi0]
	var h11: float = _hm_data[(zi0 + 1) * _hm_w + xi0 + 1]
	if fz <= fx:
		return h00 + (h10 - h00) * fx + (h11 - h10) * fz
	return h00 + (h11 - h01) * fx + (h01 - h00) * fz


func _build_chunk(ck: String) -> void:
	var cp := ck.split("|")
	var cx: int = int(cp[0])
	var cz: int = int(cp[1])
	var chunk_x := cx * CHUNK
	var chunk_z := cz * CHUNK

	# Determine zone for this chunk
	var zone_id := _get_zone_id(chunk_x + CHUNK * 0.5, chunk_z + CHUNK * 0.5)
	var accent_list: Array
	if ZONE_ACCENTS.has(zone_id):
		accent_list = ZONE_ACCENTS[zone_id]
	else:
		_active_chunks[ck] = []
		return

	# Get current season for seasonal filtering
	var season_t: float = RenderingServer.global_shader_parameter_get("season_t")
	var is_spring_summer: bool = season_t < 2.0  # spring(0) + summer(1)
	var is_autumn_winter: bool = season_t >= 2.0  # autumn(2) + winter(3)

	var chunk_parts: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(ck) + 31337  # unique seed

	for accent_cfg in accent_list:
		var at_idx: int = accent_cfg[0]
		var density: float = accent_cfg[1]
		if at_idx >= ACCENT_TYPES.size():
			continue

		var at: Dictionary = ACCENT_TYPES[at_idx]
		# Seasonal filter
		if at.season == 1 and not is_spring_summer:
			continue
		if at.season == 2 and not is_autumn_winter:
			continue

		var tuft_name: String = at.name
		if not _meshes.has(tuft_name):
			continue

		var mesh: Mesh = _meshes[tuft_name]
		var s_lo: float = at.scale[0]
		var s_hi: float = at.scale[1]
		var target: int = int(density * CHUNK * CHUNK / 100.0)
		if target < 1:
			target = 1

		var buf := PackedFloat32Array()
		buf.resize(target * 16)
		var placed := 0

		for _attempt in range(target * 3):
			if placed >= target:
				break
			var bx := chunk_x + rng.randf() * CHUNK
			var bz := chunk_z + rng.randf() * CHUNK

			# Atlas check: grass surface only
			var ai := int((bx + _atlas_half) * _atlas_scale)
			var aj := int((bz + _atlas_half) * _atlas_scale)
			if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
				continue
			var idx := (aj * _atlas_res + ai) * 2
			if _atlas_data[idx] != 1:
				continue

			var wy := _sample_height(bx, bz)
			var sc: float = rng.randf_range(s_lo, s_hi)
			var yr: float = rng.randf() * TAU
			var cos_y := cos(yr)
			var sin_y := sin(yr)
			# Random X-mirror + slight tilt
			var mx: float = 1.0 if rng.randf() > 0.5 else -1.0
			var tilt: float = rng.randf_range(-0.05, 0.05)
			var ct := cos(tilt)
			var st := sin(tilt)

			var o := placed * 16
			buf[o + 0]  = cos_y * sc * mx
			buf[o + 1]  = sin_y * st * sc * mx
			buf[o + 2]  = sin_y * ct * sc * mx
			buf[o + 3]  = bx
			buf[o + 4]  = 0.0
			buf[o + 5]  = ct * sc
			buf[o + 6]  = -st * sc
			buf[o + 7]  = wy - 0.01  # slight sink
			buf[o + 8]  = -sin_y * sc
			buf[o + 9]  = cos_y * st * sc
			buf[o + 10] = cos_y * ct * sc
			buf[o + 11] = bz
			buf[o + 12] = rng.randf()  # seed
			buf[o + 13] = sc
			buf[o + 14] = 0.0
			buf[o + 15] = 0.0
			placed += 1

		if placed == 0:
			continue

		buf.resize(placed * 16)

		# Relocate to local space
		var ox := chunk_x + CHUNK * 0.5
		var oz := chunk_z + CHUNK * 0.5
		var oy := 0.0
		for i in range(placed):
			oy += buf[i * 16 + 7]
		oy /= float(placed)
		for i in range(placed):
			buf[i * 16 + 3] -= ox
			buf[i * 16 + 7] -= oy
			buf[i * 16 + 11] -= oz

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.instance_count = placed
		mm.mesh = mesh
		mm.buffer = buf

		# Apply render shader with BD3D albedo texture
		var render_mat := ShaderMaterial.new()
		render_mat.shader = _render_shader
		render_mat.set_shader_parameter("use_texture", true)
		if _textures.has(tuft_name):
			render_mat.set_shader_parameter("grass_albedo", _textures[tuft_name])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = render_mat
		mmi.position = Vector3(ox, oy, oz)
		mmi.name = "GA_%s_%s" % [tuft_name, ck]
		mmi.visibility_range_end = VIS_END
		mmi.visibility_range_end_margin = VIS_FADE_MARGIN
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_parts.append(mmi)

	_active_chunks[ck] = chunk_parts

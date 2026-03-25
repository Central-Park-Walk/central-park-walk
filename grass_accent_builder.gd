# grass_accent_builder.gd
# Chunk-based MultiMesh accent layers on top of particle grass.
# Uses decimated BD3D tufts (clover, dandelion, meadow clumps, dry grass)
# placed at lower density (1-5 per m²) for visual richness and variety.
# Seasonal: clover/dandelion spring-summer, dry grass autumn-winter.
extends "res://chunk_builder.gd"

var _textures: Dictionary = {} # tuft_name -> Texture2D (albedo from BD3D)

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
func _build_grass_accents() -> void:
	_render_shader = load("res://shaders/grass_particle_render.gdshader")
	if not _render_shader:
		print("grass_accent: render shader not found")
		return

	_init_chunks(20.0, 160.0, 175.0, 4.0, 120.0, 25.0)

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
		var ck := "%d|%d" % [int(floor(wx / _chunk_size)), int(floor(wz / _chunk_size))]
		if _loader._undergrowth_builder._zone_map.has(ck):
			return _loader._undergrowth_builder._zone_map[ck]
	# Fallback: use atlas surface type 1 = grass, assume maintained lawn
	return 0


func _build_chunk(ck: String) -> void:
	var cp := ck.split("|")
	var cx: int = int(cp[0])
	var cz: int = int(cp[1])
	var chunk_x := cx * _chunk_size
	var chunk_z := cz * _chunk_size

	# Determine zone for this chunk
	var zone_id := _get_zone_id(chunk_x + _chunk_size * 0.5, chunk_z + _chunk_size * 0.5)
	var accent_list: Array
	if ZONE_ACCENTS.has(zone_id):
		accent_list = ZONE_ACCENTS[zone_id]
	else:
		_active_chunks[ck] = []
		return

	# Seasonal filtering from cached season_t (updated by main.gd)
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
		var target: int = int(density * _chunk_size * _chunk_size / 100.0)
		if target < 1:
			target = 1

		var buf := PackedFloat32Array()
		buf.resize(target * 16)
		var placed := 0

		for _attempt in range(target * 3):
			if placed >= target:
				break
			var bx := chunk_x + rng.randf() * _chunk_size
			var bz := chunk_z + rng.randf() * _chunk_size

			# Atlas check: grass surface only
			var ai := int((bx + _atlas_half) * _atlas_scale)
			var aj := int((bz + _atlas_half) * _atlas_scale)
			if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
				continue
			var idx := (aj * _atlas_res + ai) * 2
			if _atlas_data[idx] != 1:
				continue

			var wy := _sample_height(bx, bz)
			var s_mean: float = s_lo + (s_hi - s_lo) * 0.4
			var s_sd: float = (s_hi - s_lo) * 0.20
			var sc: float = clampf(rng.randfn(s_mean, s_sd), s_lo, s_hi)
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
		var ox := chunk_x + _chunk_size * 0.5
		var oz := chunk_z + _chunk_size * 0.5
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
		mmi.visibility_range_end = _vis_end
		mmi.visibility_range_end_margin = _vis_fade_margin
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_parts.append(mmi)

	_active_chunks[ck] = chunk_parts

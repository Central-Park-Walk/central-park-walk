# ground_cover_builder.gd
# Chunk-based MultiMesh placement for dense ground cover patches.
# Fills the gap between grass blades (0-5cm) and undergrowth (30cm+)
# with pre-assembled 2x2m patch meshes: bramble, fern clusters,
# mixed weeds, tall grass, and seasonal fallen leaves/twig litter.
# Data-first: placement driven by atlas zone type and canopy coverage.

var _loader
var _meshes: Dictionary = {}    # patch_name -> Mesh
var _shader: Shader
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
const LOAD_RANGE := 50.0
const UNLOAD_RANGE := 60.0
const UPDATE_DIST := 3.0
const VIS_END := 28.0

# Patch types: name, variants, height range, is_litter, wind_flex
const PATCH_TYPES := [
	{"name": "bramble",       "variants": 4, "flex": 0.30, "litter": 0, "seasonal": 1},
	{"name": "fern_cluster",  "variants": 4, "flex": 0.35, "litter": 0, "seasonal": 1},
	{"name": "mixed_weeds",   "variants": 4, "flex": 0.25, "litter": 0, "seasonal": 1},
	{"name": "tall_grass",    "variants": 4, "flex": 0.45, "litter": 0, "seasonal": 1},
	{"name": "fallen_leaves", "variants": 4, "flex": 0.05, "litter": 1, "seasonal": 0},
	{"name": "twig_litter",   "variants": 4, "flex": 0.02, "litter": 1, "seasonal": 0},
]

# Zone type -> list of [patch_type_index, density_per_100m2, scale_min, scale_max]
# Patch types: 0=bramble, 1=fern_cluster, 2=mixed_weeds, 3=tall_grass, 4=fallen_leaves, 5=twig_litter
const ZONE_PATCHES := {
	5: [  # NorthWoods — fern-heavy ground cover, leaf litter
		[1, 6.0, 0.8, 1.3],   # Fern clusters (dominant)
		[0, 2.0, 0.7, 1.1],   # Bramble (scattered)
		[2, 3.0, 0.6, 1.0],   # Mixed weeds
		[4, 4.0, 0.8, 1.2],   # Fallen leaves (seasonal)
		[5, 2.0, 0.7, 1.0],   # Twig litter (seasonal)
	],
	6: [  # Ramble — dense thickets, stream-edge weeds
		[0, 5.0, 0.8, 1.2],   # Bramble (dominant — designed wildness)
		[2, 4.0, 0.7, 1.1],   # Mixed weeds (diverse)
		[1, 2.0, 0.7, 1.0],   # Fern clusters
		[3, 1.5, 0.8, 1.2],   # Tall grass (path edges)
		[4, 3.0, 0.8, 1.2],   # Fallen leaves (seasonal)
		[5, 1.5, 0.7, 1.0],   # Twig litter (seasonal)
	],
	7: [  # Waterside — tall grasses, weeds
		[3, 6.0, 0.9, 1.4],   # Tall grass (dominant)
		[2, 3.0, 0.7, 1.1],   # Mixed weeds
		[0, 1.0, 0.6, 0.9],   # Bramble (sparse)
		[4, 2.0, 0.7, 1.0],   # Fallen leaves (seasonal)
	],
	8: [  # WildMeadow — tall grasses and weeds
		[3, 7.0, 1.0, 1.5],   # Tall grass (dominant, tall)
		[2, 4.0, 0.8, 1.2],   # Mixed weeds
		[0, 2.0, 0.7, 1.0],   # Bramble
		[4, 2.0, 0.8, 1.1],   # Fallen leaves (seasonal)
	],
}

# Woodland fallback
const WOODLAND_PATCHES: Array = [
	[1, 4.0, 0.7, 1.1],   # Fern clusters
	[2, 2.0, 0.6, 1.0],   # Mixed weeds
	[0, 1.5, 0.7, 1.0],   # Bramble
	[4, 3.0, 0.8, 1.2],   # Fallen leaves
	[5, 2.0, 0.7, 1.0],   # Twig litter
]

# Z ranges where woodland fallback is allowed
const WOODLAND_Z_RANGES: Array = [
	[-1800, -1050],  # North Woods + The Pool
	[375, 975],      # The Ramble
	[1650, 2050],    # Hallett & The Pond
]


func _init(loader) -> void:
	_loader = loader


func _build_ground_cover() -> void:
	_shader = load("res://shaders/ground_cover.gdshader")
	if not _shader:
		print("ground_cover: shader not found")
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

	# Load patch meshes
	var loaded := 0
	for pt in PATCH_TYPES:
		for vi in range(pt.variants):
			var mesh_name := "Patch_%s_v%d" % [pt.name, vi]
			var mesh := _load_model(mesh_name, pt)
			if mesh:
				_meshes[mesh_name] = mesh
				loaded += 1
	print("ground_cover: loaded %d patch meshes" % loaded)

	# Queue initial chunks near spawn
	var spawn := Vector3(-480, 0, 1020)
	_update_chunks_near(spawn)


func _load_model(mesh_name: String, pt: Dictionary) -> Mesh:
	var path := "res://models/vegetation/%s.glb" % mesh_name
	var abs_path: String = ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(abs_path):
		return null
	var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
	if meshes.is_empty():
		return null
	var mesh: Mesh = meshes.values()[0]

	# Apply shader material
	var mat := ShaderMaterial.new()
	mat.shader = _shader
	mat.set_shader_parameter("wind_flex", pt.flex)
	mat.set_shader_parameter("is_seasonal", float(pt.seasonal))
	mat.set_shader_parameter("is_litter", float(pt.litter))
	mat.set_shader_parameter("hm_world_size", _hm_ws)
	if _loader._canopy_texture:
		mat.set_shader_parameter("canopy_map", _loader._canopy_texture)

	for si in range(mesh.get_surface_count()):
		mesh.surface_set_material(si, mat)
	return mesh


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
			# Atlas check: must be grass (surface type 1)
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
	# Sort by distance, build closest first
	_build_queue.sort_custom(func(a: String, b: String) -> bool:
		var pa: PackedStringArray = a.split("|")
		var pb: PackedStringArray = b.split("|")
		var ax: float = int(pa[0]) * CHUNK + CHUNK * 0.5
		var az: float = int(pa[1]) * CHUNK + CHUNK * 0.5
		var bx: float = int(pb[0]) * CHUNK + CHUNK * 0.5
		var bz: float = int(pb[1]) * CHUNK + CHUNK * 0.5
		var da: float = (ax - pos.x) * (ax - pos.x) + (az - pos.z) * (az - pos.z)
		var db: float = (bx - pos.x) * (bx - pos.x) + (bz - pos.z) * (bz - pos.z)
		return da < db)
	var ck: String = _build_queue.pop_front()
	_queued_set.erase(ck)
	# Check distance still valid
	var cp: PackedStringArray = ck.split("|")
	var wx := int(cp[0]) * CHUNK + CHUNK * 0.5
	var wz := int(cp[1]) * CHUNK + CHUNK * 0.5
	var dd := (wx - pos.x) * (wx - pos.x) + (wz - pos.z) * (wz - pos.z)
	if dd > UNLOAD_RANGE * UNLOAD_RANGE:
		return
	_build_chunk(ck)


func _get_zone_type(cx: int, cz: int) -> int:
	# Check undergrowth builder's zone map if available
	var ug_builder = _loader._undergrowth_builder if _loader.has_method("get") else null
	# Determine from atlas — sample center of chunk
	var wx := cx * CHUNK + CHUNK * 0.5
	var wz := cz * CHUNK + CHUNK * 0.5
	# Check if in woodland Z range
	for zr in WOODLAND_Z_RANGES:
		if wz >= zr[0] and wz <= zr[1]:
			return -1  # woodland fallback
	return -2  # no coverage


func _build_chunk(ck: String) -> void:
	var cp: PackedStringArray = ck.split("|")
	var cx: int = int(cp[0])
	var cz: int = int(cp[1])
	var chunk_x := cx * CHUNK
	var chunk_z := cz * CHUNK

	# Determine zone — check undergrowth builder zone map
	var zone_key := ck
	var zone_type := -2
	if _loader._undergrowth_builder and _loader._undergrowth_builder._zone_map.has(zone_key):
		zone_type = _loader._undergrowth_builder._zone_map[zone_key]
	else:
		zone_type = _get_zone_type(cx, cz)

	# Get patch list for this zone
	var patch_list: Array
	if ZONE_PATCHES.has(zone_type):
		patch_list = ZONE_PATCHES[zone_type]
	elif zone_type == -1:
		patch_list = WOODLAND_PATCHES
	else:
		# No ground cover for maintained lawns (zones 0-4, 9)
		_active_chunks[ck] = []
		return

	var chunk_parts: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(ck) + 7919  # different from undergrowth seed

	for patch_cfg in patch_list:
		var pt_idx: int = patch_cfg[0]
		var density: float = patch_cfg[1]
		var s_lo: float = patch_cfg[2]
		var s_hi: float = patch_cfg[3]

		var pt: Dictionary = PATCH_TYPES[pt_idx]
		var target: int = int(density * CHUNK * CHUNK / 100.0)
		if target < 1:
			target = 1

		# Pick random variant
		var vi: int = rng.randi() % pt.variants
		var mesh_name := "Patch_%s_v%d" % [pt.name, vi]
		if not _meshes.has(mesh_name):
			# Try other variants
			for try_vi in range(pt.variants):
				mesh_name = "Patch_%s_v%d" % [pt.name, try_vi]
				if _meshes.has(mesh_name):
					break
			if not _meshes.has(mesh_name):
				continue

		var mesh: Mesh = _meshes[mesh_name]
		var buf := PackedFloat32Array()
		buf.resize(target * 16)
		var placed := 0

		for _attempt in range(target * 3):
			if placed >= target:
				break
			var bx := chunk_x + rng.randf() * CHUNK
			var bz := chunk_z + rng.randf() * CHUNK

			# Atlas check
			var ai := int((bx + _atlas_half) * _atlas_scale)
			var aj := int((bz + _atlas_half) * _atlas_scale)
			if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
				continue
			var idx := (aj * _atlas_res + ai) * 2
			if _atlas_data[idx] != 1:
				continue
			if _atlas_data[idx + 1] != 0:
				continue

			# Heightmap sample
			var xi: float = (bx + _hm_half) / _hm_ws * (_hm_w - 1)
			var zi: float = (bz + _hm_half) / _hm_ws * (_hm_d - 1)
			var xi0: int = clampi(int(xi), 0, _hm_w - 2)
			var zi0: int = clampi(int(zi), 0, _hm_d - 2)
			var fx: float = xi - xi0
			var fz: float = zi - zi0
			var h00: float = _hm_data[zi0 * _hm_w + xi0]
			var h10: float = _hm_data[zi0 * _hm_w + xi0 + 1]
			var h01: float = _hm_data[(zi0 + 1) * _hm_w + xi0]
			var h11: float = _hm_data[(zi0 + 1) * _hm_w + xi0 + 1]
			var wy: float
			if fz <= fx:
				wy = h00 + (h10 - h00) * fx + (h11 - h10) * fz
			else:
				wy = h00 + (h11 - h01) * fx + (h01 - h00) * fz

			var sc: float = rng.randf_range(s_lo, s_hi)
			var yr: float = rng.randf() * TAU

			var cos_y := cos(yr)
			var sin_y := sin(yr)
			var o := placed * 16
			buf[o + 0] = cos_y * sc
			buf[o + 1] = 0.0
			buf[o + 2] = sin_y * sc
			buf[o + 3] = bx
			buf[o + 4] = 0.0
			buf[o + 5] = sc
			buf[o + 6] = 0.0
			buf[o + 7] = wy
			buf[o + 8] = -sin_y * sc
			buf[o + 9] = 0.0
			buf[o + 10] = cos_y * sc
			buf[o + 11] = bz
			# INSTANCE_CUSTOM
			buf[o + 12] = rng.randf()      # seed
			buf[o + 13] = sc               # scale
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

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = Vector3(ox, oy, oz)
		mmi.name = "GC_%s_%s" % [pt.name, ck]
		mmi.visibility_range_end = VIS_END
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_parts.append(mmi)

	_active_chunks[ck] = chunk_parts

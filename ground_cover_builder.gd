# ground_cover_builder.gd
# Chunk-based MultiMesh placement for ground cover using BD3D plant library.
# Fallen leaves, branches, moss, weeds, and saplings — all real 3D meshes
# with embedded PBR textures. No procedural patches, no atlas shader.
# Data-first: placement driven by atlas zone type and canopy coverage.
extends "res://chunk_builder.gd"

# BD3D ground cover models — each carries its own StandardMaterial3D
# [index] name (matches GLB filename in models/vegetation/)
const COVER_MODELS := [
	# 0-4: Fallen leaves (seasonal: autumn-winter)
	{"name": "DeadLeaves_Forest_01",  "seasonal": 2},   # 0
	{"name": "DeadLeaves_Forest_02",  "seasonal": 2},   # 1
	{"name": "DeadLeaves_Autumn_01",  "seasonal": 2},   # 2
	{"name": "DeadLeaves_Autumn_02",  "seasonal": 2},   # 3
	{"name": "Leaves_Scattered_01",   "seasonal": 2},   # 4
	# 5-7: Fallen branches (year-round)
	{"name": "Branch_Forest_01",      "seasonal": 0},   # 5
	{"name": "Branch_Forest_02",      "seasonal": 0},   # 6
	{"name": "Branch_Dry_01",         "seasonal": 0},   # 7
	# 8-9: Moss (year-round, woodland)
	{"name": "Moss_Forest_01",        "seasonal": 0},   # 8
	{"name": "Moss_Forest_02",        "seasonal": 0},   # 9
	# 10-13: Small weeds (spring-summer)
	{"name": "Weed_Small_01",         "seasonal": 1},   # 10
	{"name": "Weed_Small_02",         "seasonal": 1},   # 11
	{"name": "Weed_TypeA_01",         "seasonal": 1},   # 12
	{"name": "Weed_TypeA_02",         "seasonal": 1},   # 13
	# 14-17: Saplings (year-round, woodland understory)
	{"name": "Sapling_Deciduous_01",  "seasonal": 0},   # 14
	{"name": "Sapling_Deciduous_02",  "seasonal": 0},   # 15
	{"name": "Sapling_Conifer_01",    "seasonal": 0},   # 16
	{"name": "Sapling_Conifer_02",    "seasonal": 0},   # 17
]

# Zone -> list of [model_index, density_per_100m2, scale_min, scale_max]
const ZONE_COVER := {
	5: [  # NorthWoods
		[0, 3.0, 0.8, 1.3],   # Dead leaves
		[1, 2.5, 0.8, 1.2],
		[5, 1.0, 0.7, 1.1],   # Branches
		[6, 0.8, 0.7, 1.0],
		[8, 2.0, 0.8, 1.3],   # Moss
		[9, 1.5, 0.7, 1.2],
		[10, 1.5, 0.7, 1.1],  # Weeds
		[12, 1.0, 0.6, 1.0],
		[14, 0.3, 0.6, 1.0],  # Saplings
		[16, 0.2, 0.5, 0.9],
	],
	6: [  # Ramble
		[0, 2.5, 0.8, 1.2],   # Dead leaves
		[2, 2.0, 0.7, 1.2],
		[5, 1.2, 0.7, 1.1],   # Branches
		[7, 0.5, 0.6, 1.0],
		[8, 1.5, 0.8, 1.2],   # Moss
		[10, 2.0, 0.7, 1.1],  # Weeds
		[11, 1.5, 0.6, 1.0],
		[13, 1.0, 0.6, 1.0],
		[15, 0.2, 0.6, 1.0],  # Saplings
	],
	7: [  # Waterside
		[3, 2.0, 0.7, 1.1],   # Autumn leaves
		[4, 1.5, 0.8, 1.2],   # Scattered leaves
		[7, 0.5, 0.6, 0.9],   # Dry branch
		[10, 1.5, 0.7, 1.1],  # Weeds
		[11, 1.0, 0.6, 1.0],
	],
	8: [  # WildMeadow
		[2, 1.5, 0.7, 1.1],   # Autumn leaves
		[3, 1.0, 0.8, 1.2],
		[7, 0.3, 0.6, 0.9],   # Dry branch
		[10, 2.5, 0.8, 1.2],  # Weeds
		[12, 1.5, 0.7, 1.1],
		[13, 1.0, 0.6, 1.0],
	],
}

# Woodland fallback
const WOODLAND_COVER: Array = [
	[0, 3.5, 0.8, 1.3],   # Dead leaves (dominant)
	[1, 2.0, 0.7, 1.2],
	[4, 1.5, 0.8, 1.2],   # Scattered leaves
	[5, 1.0, 0.7, 1.0],   # Branches
	[6, 0.5, 0.6, 1.0],
	[8, 2.0, 0.8, 1.3],   # Moss
	[9, 1.5, 0.7, 1.2],
	[14, 0.3, 0.6, 1.0],  # Saplings
	[16, 0.2, 0.5, 0.9],
]

# Z ranges where woodland fallback is allowed
const WOODLAND_Z_RANGES: Array = [
	[-1800, -1050],  # North Woods + The Pool
	[375, 975],      # The Ramble
	[1650, 2050],    # Hallett & The Pond
]

func _build_ground_cover() -> void:
	_init_chunks(20.0, 180.0, 195.0, 3.0, 140.0, 25.0)

	# Load all BD3D models
	var loaded := 0
	for cm in COVER_MODELS:
		var abs_path := ProjectSettings.globalize_path(
			"res://models/vegetation/%s.glb" % cm.name)
		var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
		if meshes.is_empty():
			continue
		_meshes[cm.name] = meshes.values()[0]
		loaded += 1
	print("ground_cover: loaded %d/%d BD3D models" % [loaded, COVER_MODELS.size()])

	# Queue initial chunks near spawn
	_update_chunks_near(Vector3(-480, 0, 1020))


func _get_zone_type(cx: int, cz: int) -> int:
	var wz := cz * _chunk_size + _chunk_size * 0.5
	for zr in WOODLAND_Z_RANGES:
		if wz >= zr[0] and wz <= zr[1]:
			return -1
	return -2


func _build_chunk(ck: String) -> void:
	var cp := ck.split("|")
	var cx: int = int(cp[0])
	var cz: int = int(cp[1])
	var chunk_x := cx * _chunk_size
	var chunk_z := cz * _chunk_size

	var zone_type := -2
	if _loader._undergrowth_builder and _loader._undergrowth_builder._zone_map.has(ck):
		zone_type = _loader._undergrowth_builder._zone_map[ck]
	else:
		zone_type = _get_zone_type(cx, cz)

	var cover_list: Array
	if ZONE_COVER.has(zone_type):
		cover_list = ZONE_COVER[zone_type]
	elif zone_type == -1:
		cover_list = WOODLAND_COVER
	else:
		_active_chunks[ck] = []
		return

	var is_spring_summer: bool = season_t < 2.0
	var is_autumn_winter: bool = season_t >= 2.0

	var chunk_parts: Array = []
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(ck) + 7919

	for cover_cfg in cover_list:
		var cm_idx: int = cover_cfg[0]
		var density: float = cover_cfg[1]
		var s_lo: float = cover_cfg[2]
		var s_hi: float = cover_cfg[3]
		if cm_idx >= COVER_MODELS.size():
			continue

		var cm: Dictionary = COVER_MODELS[cm_idx]
		# Seasonal filter
		if cm.seasonal == 1 and not is_spring_summer:
			continue
		if cm.seasonal == 2 and not is_autumn_winter:
			continue

		if not _meshes.has(cm.name):
			continue

		var mesh: Mesh = _meshes[cm.name]
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

			var ai := int((bx + _atlas_half) * _atlas_scale)
			var aj := int((bz + _atlas_half) * _atlas_scale)
			if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
				continue
			var idx := (aj * _atlas_res + ai) * 2
			if _atlas_data[idx] != 1:
				continue
			if _atlas_data[idx + 1] != 0:
				continue

			var wy := _sample_height(bx, bz)
			var s_mean: float = s_lo + (s_hi - s_lo) * 0.4
			var s_sd: float = (s_hi - s_lo) * 0.20
			var sc: float = clampf(rng.randfn(s_mean, s_sd), s_lo, s_hi)
			var yr: float = rng.randf() * TAU
			var mx: float = 1.0 if rng.randf() > 0.5 else -1.0
			var tilt: float = rng.randf_range(-0.07, 0.07)
			var ct := cos(tilt)
			var st := sin(tilt)
			var cos_y := cos(yr)
			var sin_y := sin(yr)

			var o := placed * 16
			buf[o + 0]  = cos_y * sc * mx
			buf[o + 1]  = sin_y * st * sc * mx
			buf[o + 2]  = sin_y * ct * sc * mx
			buf[o + 3]  = bx
			buf[o + 4]  = 0.0
			buf[o + 5]  = ct * sc
			buf[o + 6]  = -st * sc
			buf[o + 7]  = wy
			buf[o + 8]  = -sin_y * sc
			buf[o + 9]  = cos_y * st * sc
			buf[o + 10] = cos_y * ct * sc
			buf[o + 11] = bz
			buf[o + 12] = rng.randf()
			buf[o + 13] = sc
			buf[o + 14] = 0.0
			buf[o + 15] = 0.0
			placed += 1

		if placed == 0:
			continue

		buf.resize(placed * 16)

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

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = Vector3(ox, oy, oz)
		mmi.name = "GC_%s_%s" % [cm.name, ck]
		mmi.visibility_range_end = _vis_end
		mmi.visibility_range_end_margin = _vis_fade_margin
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		chunk_parts.append(mmi)

	_active_chunks[ck] = chunk_parts

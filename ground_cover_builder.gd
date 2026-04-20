# ground_cover_builder.gd
# Chunk-based MultiMesh placement for ground cover.
# Fallen leaves, branches, moss, weeds, and saplings — real 3D meshes.
# Data-first: placement driven by atlas zone type and canopy coverage.
extends "res://chunk_builder.gd"

# Ground cover models — procedural vertex-color meshes (make_forest_floor.py)
# seasonal: 0=year-round, 1=spring/summer only, 2=autumn/winter only
const COVER_MODELS := [
	{name="GroundCover_DeadLeaves_01", seasonal=2},    # 0 — autumn fallen leaves
	{name="GroundCover_DeadLeaves_02", seasonal=2},    # 1 — variant
	{name="GroundCover_ForestLeaves_01", seasonal=0},  # 2 — year-round decomposed litter
	{name="GroundCover_ForestLeaves_02", seasonal=0},  # 3 — variant
	{name="GroundCover_Moss_01", seasonal=0},           # 4 — green moss patch
	{name="GroundCover_Moss_02", seasonal=0},           # 5 — variant
	{name="GroundCover_Branch_01", seasonal=0},         # 6 — fallen twig
	{name="GroundCover_Branch_02", seasonal=0},         # 7 — variant
	{name="GroundCover_Seedling_01", seasonal=1},       # 8 — deciduous seedling
	{name="GroundCover_Seedling_02", seasonal=1},       # 9 — conifer seedling
]

# Zone -> list of [model_index, density_per_100m2, scale_min, scale_max]
const ZONE_COVER := {
	5: [  # North Woods — rich forest floor
		[2, 3.5, 0.8, 1.3],   # decomposed leaves (dominant)
		[3, 2.0, 0.7, 1.2],
		[4, 2.0, 0.8, 1.3],   # moss
		[5, 1.5, 0.7, 1.2],
		[6, 1.0, 0.7, 1.0],   # fallen branches
		[7, 0.5, 0.6, 1.0],
		[8, 0.3, 0.6, 1.0],   # seedlings
		[9, 0.2, 0.5, 0.9],
	],
	6: [  # Ramble — denser forest floor
		[2, 4.5, 0.8, 1.3],   # decomposed leaves
		[3, 3.0, 0.7, 1.2],
		[4, 2.5, 0.8, 1.3],   # moss
		[5, 2.0, 0.7, 1.2],
		[6, 1.2, 0.7, 1.0],   # branches
		[7, 0.8, 0.6, 1.0],
		[8, 0.4, 0.6, 1.0],   # seedlings
		[9, 0.3, 0.5, 0.9],
	],
	7: [  # Waterside — sparse, no moss
		[2, 1.5, 0.7, 1.2],   # some decomposed leaves
		[6, 0.5, 0.6, 1.0],   # scattered branches
	],
	8: [  # Wild Meadow — dry litter
		[2, 1.0, 0.7, 1.2],   # scattered litter
		[6, 0.8, 0.7, 1.0],   # dry branches
	],
}

# Woodland fallback (for chunks in WOODLAND_Z_RANGES without zone data)
const WOODLAND_COVER: Array = [
	[2, 3.5, 0.8, 1.3],   # decomposed leaves (dominant)
	[3, 2.0, 0.7, 1.2],
	[4, 2.0, 0.8, 1.3],   # moss
	[5, 1.5, 0.7, 1.2],
	[6, 1.0, 0.7, 1.0],   # fallen branches
	[7, 0.5, 0.6, 1.0],
	[8, 0.3, 0.6, 1.0],   # seedlings
	[9, 0.2, 0.5, 0.9],
]

# Z ranges where woodland fallback is allowed
const WOODLAND_Z_RANGES: Array = [
	[-1800, -1050],  # North Woods + The Pool
	[375, 975],      # The Ramble
	[1650, 2050],    # Hallett & The Pond
]

func _build_ground_cover() -> void:
	_init_chunks(20.0, 120.0, 135.0, 3.0, 100.0, 20.0)

	# Load ground cover models
	var loaded := 0
	for cm in COVER_MODELS:
		var abs_path := ProjectSettings.globalize_path(
			"res://models/vegetation/%s.glb" % cm.name)
		var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
		if meshes.is_empty():
			continue
		_meshes[cm.name] = meshes.values()[0]
		loaded += 1
	print("ground_cover: loaded %d/%d models" % [loaded, COVER_MODELS.size()])

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

	# Distance-based density thinning
	var chunk_center := Vector3(chunk_x + _chunk_size * 0.5, 0, chunk_z + _chunk_size * 0.5)
	var chunk_dist := chunk_center.distance_to(_last_update_pos)
	var tier_mult := 1.0
	if chunk_dist >= 80.0:
		tier_mult = 0.5
	elif chunk_dist >= 50.0:
		tier_mult = 0.75

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
		var target: int = int(density * _chunk_size * _chunk_size / 100.0 * tier_mult)
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

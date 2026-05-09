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
# Primitives retired 2026-05-08: ForestLeaves (2,3) and Moss (4,5) are flat
# cards too sparse to read as ground cover. Available gscatter BarkMulch and
# BankHaircapMoss are tiny single-element scans (~3-7cm) that need a much
# higher-density scatter system to substitute. Branches (6,7) and seedlings
# (8,9) kept pending fitness verification.
const ZONE_COVER := {
	5: [  # North Woods — branches + seedlings only until bespoke litter/moss
		[6, 1.0, 0.7, 1.0],   # fallen branches
		[7, 0.5, 0.6, 1.0],
		[8, 0.3, 0.6, 1.0],   # seedlings
		[9, 0.2, 0.5, 0.9],
	],
	6: [  # Ramble — branches + seedlings only
		[6, 1.2, 0.7, 1.0],   # branches
		[7, 0.8, 0.6, 1.0],
		[8, 0.4, 0.6, 1.0],   # seedlings
		[9, 0.3, 0.5, 0.9],
	],
	7: [  # Waterside — sparse, no moss
		[6, 0.5, 0.6, 1.0],   # scattered branches
	],
	8: [  # Wild Meadow — dry litter
		[6, 0.8, 0.7, 1.0],   # dry branches
	],
}

# Woodland fallback (for chunks in WOODLAND_Z_RANGES without zone data)
const WOODLAND_COVER: Array = [
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

		var RS := RenderingServer
		var mm_rid := RS.multimesh_create()
		RS.multimesh_allocate_data(mm_rid, placed, RS.MULTIMESH_TRANSFORM_3D, false, true)
		RS.multimesh_set_mesh(mm_rid, mesh.get_rid())
		RS.multimesh_set_buffer(mm_rid, buf)

		# Compute tight AABB from local-space positions
		var aabb_min := Vector3(INF, INF, INF)
		var aabb_max := Vector3(-INF, -INF, -INF)
		for j in placed:
			var o := j * 16
			var px: float = buf[o + 3]
			var py: float = buf[o + 7]
			var pz: float = buf[o + 11]
			if px < aabb_min.x: aabb_min.x = px
			if py < aabb_min.y: aabb_min.y = py
			if pz < aabb_min.z: aabb_min.z = pz
			if px > aabb_max.x: aabb_max.x = px
			if py > aabb_max.y: aabb_max.y = py
			if pz > aabb_max.z: aabb_max.z = pz
		aabb_min -= Vector3(2, 1, 2)
		aabb_max += Vector3(2, 3, 2)
		RS.multimesh_set_custom_aabb(mm_rid, AABB(aabb_min, aabb_max - aabb_min))

		var inst_rid := RS.instance_create()
		RS.instance_set_base(inst_rid, mm_rid)
		RS.instance_set_scenario(inst_rid, _scenario)
		RS.instance_set_transform(inst_rid, Transform3D(Basis.IDENTITY, Vector3(ox, oy, oz)))
		RS.instance_set_visible(inst_rid, true)
		RS.instance_geometry_set_visibility_range(inst_rid, 0.0, _vis_end, 0.0,
			_vis_fade_margin, RS.VISIBILITY_RANGE_FADE_SELF)
		RS.instance_geometry_set_cast_shadows_setting(inst_rid,
			RS.SHADOW_CASTING_SETTING_OFF)
		chunk_parts.append([mm_rid, inst_rid])

	_active_chunks[ck] = chunk_parts

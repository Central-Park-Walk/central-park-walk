# undergrowth_builder.gd
# Chunk-based MultiMesh placement for 16 undergrowth species.
# Fills the missing vertical layers between grass (0-25cm) and tree canopy (5m+).
# Placement driven by atlas zone type — data-first, no procedural invention.

var _loader
var _meshes: Dictionary = {}    # species_name -> Mesh
var _shader: Shader
var _leaf_atlas: Texture2D       # 2048x2048 leaf texture atlas (4x4 grid)
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

# Zone type data from ground_cover_instances
var _zone_map: Dictionary = {}  # "cx|cz" (grass chunk) -> dominant zone type

const CHUNK := 20.0
const LOAD_RANGE := 60.0
const UNLOAD_RANGE := 70.0
const UPDATE_DIST := 2.0
const VIS_END := 50.0

# Species definitions: name, scale range (relative to model), wind flex, evergreen, fall tint
# Models are already built at natural reference height; s=[min,max] is scale multiplier
const SPECIES := [
	# Shrubs (0-4)
	{"name": "Shrub_Spicebush",        "s": [0.75, 1.20], "flex": 0.25, "green": 0, "fall": [0.70, 0.65, 0.15]},
	{"name": "Shrub_WitchHazel",        "s": [0.80, 1.15], "flex": 0.20, "green": 0, "fall": [0.65, 0.60, 0.12]},
	{"name": "Shrub_Viburnum",          "s": [0.75, 1.20], "flex": 0.25, "green": 0, "fall": [0.60, 0.25, 0.15]},
	{"name": "Shrub_Sumac",             "s": [0.80, 1.15], "flex": 0.20, "green": 0, "fall": [0.80, 0.20, 0.08]},
	{"name": "Shrub_Elderberry",        "s": [0.80, 1.15], "flex": 0.30, "green": 0, "fall": [0.55, 0.45, 0.10]},
	# Tall herbs (5-9)
	{"name": "Herb_Pokeweed",           "s": [0.70, 1.30], "flex": 0.45, "green": 0, "fall": [0.50, 0.15, 0.30]},
	{"name": "Herb_JapaneseKnotweed",   "s": [0.80, 1.20], "flex": 0.35, "green": 0, "fall": [0.40, 0.30, 0.12]},
	{"name": "Herb_JoePyeWeed",         "s": [0.75, 1.25], "flex": 0.50, "green": 0, "fall": [0.45, 0.30, 0.20]},
	{"name": "Herb_Coneflower",         "s": [0.75, 1.25], "flex": 0.55, "green": 0, "fall": [0.50, 0.40, 0.12]},
	{"name": "Herb_CardinalFlower",     "s": [0.80, 1.20], "flex": 0.40, "green": 0, "fall": [0.30, 0.18, 0.08]},
	# Billboard herbs (10-12) — scale verified against real-world heights
	{"name": "Herb_WhiteWoodAster",     "s": [0.55, 1.00], "flex": 0.35, "green": 0, "fall": [0.35, 0.28, 0.10]},
	{"name": "Herb_Jewelweed",          "s": [0.80, 1.30], "flex": 0.50, "green": 0, "fall": [0.40, 0.30, 0.08]},
	{"name": "Herb_Mugwort",            "s": [1.00, 1.50], "flex": 0.30, "green": 0, "fall": [0.45, 0.38, 0.20]},
	# Ferns (13-14) — scale verified against real-world heights
	{"name": "Fern_Ostrich",            "s": [0.55, 0.95], "flex": 0.40, "green": 0, "fall": [0.50, 0.40, 0.10]},
	{"name": "Fern_Christmas",          "s": [0.85, 1.30], "flex": 0.20, "green": 1, "fall": [0.10, 0.28, 0.06]},
	# Wetland (15)
	{"name": "Wetland_Cattail",         "s": [0.75, 1.25], "flex": 0.35, "green": 0, "fall": [0.35, 0.25, 0.10]},
	# Fungi (16-17) — seasonal: peak late summer through fall, absent in winter/spring
	# Laetiporus (chicken of the woods) on oaks; common mushrooms on woodland floor
	{"name": "Mushroom_Common",         "s": [0.80, 1.50], "flex": 0.0, "green": 0, "fall": [0.30, 0.22, 0.12]},
	{"name": "Mushroom_Laetiporus",     "s": [0.60, 1.20], "flex": 0.0, "green": 0, "fall": [0.60, 0.35, 0.08]},
]

# Zone type -> list of [species_index, density_per_100m2]
# Zone types: 0=SheepMeadow, 1=GreatLawn, 2=NorthMeadow, 3=FormalGarden,
#   4=SportsTurf, 5=NorthWoods, 6=Ramble, 7=Waterside, 8=WildMeadow, 9=OpenLawn
const ZONE_SPECIES := {
	5: [  # NorthWoods — dense woodland understory
		[0, 3.0],   # Spicebush
		[1, 1.5],   # Witch Hazel
		[10, 10.0],  # White Wood Aster
		[13, 4.0],  # Ostrich Fern
		[14, 6.0],  # Christmas Fern
		[5, 1.0],   # Pokeweed (edges)
		[16, 0.5],  # Common Mushroom (woodland floor, seasonal)
		[17, 0.3],  # Chicken of the Woods (on oaks, seasonal)
	],
	6: [  # Ramble — designed wild garden, dense understory
		[0, 4.0],   # Spicebush (dominant)
		[1, 1.0],   # Witch Hazel
		[2, 2.0],   # Viburnum
		[10, 12.0], # White Wood Aster
		[14, 5.0],  # Christmas Fern
		[13, 3.0],  # Ostrich Fern
		[5, 1.5],   # Pokeweed
		[16, 0.6],  # Common Mushroom (seasonal)
		[17, 0.2],  # Chicken of the Woods (seasonal)
	],
	7: [  # Waterside — wetland edge
		[15, 8.0],  # Cattail
		[9, 3.0],   # Cardinal Flower
		[7, 4.0],   # Joe Pye Weed
		[11, 6.0],  # Jewelweed
		[13, 2.0],  # Ostrich Fern
	],
	8: [  # WildMeadow — unmowed tall herbs
		[12, 5.0],  # Mugwort
		[5, 3.0],   # Pokeweed
		[6, 2.0],   # Japanese Knotweed
		[8, 4.0],   # Coneflower
		[7, 3.0],   # Joe Pye Weed
		[3, 1.0],   # Sumac
		[4, 1.5],   # Elderberry
	],
	# Zones 0-4 (SheepMeadow, GreatLawn, NorthMeadow, FormalGarden, SportsTurf)
	# and zone 9 (OpenLawn) are maintained lawns — NO undergrowth.
}

# Woodland chunks (no pre-baked data) get understory — but ONLY in actual
# woodland foliage zones, not on maintained lawns that happen to lack data.
const WOODLAND_SPECIES: Array = [
	[0, 2.0],   # Spicebush
	[10, 6.0],  # White Wood Aster
	[14, 4.0],  # Christmas Fern
	[13, 2.0],  # Ostrich Fern
	[16, 0.4],  # Common Mushroom (seasonal)
	[17, 0.2],  # Chicken of the Woods (seasonal)
]
# Z ranges where woodland fallback is allowed (from park_data.json foliage_zones)
const WOODLAND_Z_RANGES: Array = [
	[-1800, -1050],  # North Woods + The Pool
	[375, 975],      # The Ramble
	[1650, 2050],    # Hallett & The Pond
]


func _init(loader) -> void:
	_loader = loader


func _build_undergrowth() -> void:
	var t0 := Time.get_ticks_msec()
	_shader = _loader._get_shader("undergrowth", "res://shaders/undergrowth.gdshader")
	if _shader == null:
		print("Undergrowth: shader not found"); return

	# Load leaf texture atlas
	var atlas_path := ProjectSettings.globalize_path("res://textures/leaf_atlas.png")
	if FileAccess.file_exists(atlas_path):
		var img := Image.load_from_file(atlas_path)
		if img:
			_leaf_atlas = ImageTexture.create_from_image(img)
			print("Undergrowth: leaf atlas loaded (%dx%d)" % [img.get_width(), img.get_height()])

	# Load all species meshes
	var loaded := 0
	for sp in SPECIES:
		var mesh := _load_model(sp.name)
		if mesh != null:
			_meshes[sp.name] = mesh
			loaded += 1
	print("Undergrowth: %d/%d species loaded" % [loaded, SPECIES.size()])
	if loaded == 0: return

	# Cache atlas/heightmap
	_atlas_data = _loader._atlas_data
	_atlas_res = _loader._atlas_res
	_atlas_scale = float(_atlas_res) / _loader._hm_world_size
	_atlas_half = _loader._hm_world_size * 0.5
	_hm_data = _loader._hm_data
	_hm_w = _loader._hm_width
	_hm_d = _loader._hm_depth
	_hm_ws = _loader._hm_world_size
	_hm_half = _hm_ws * 0.5

	# Build zone map from ground_cover_instances (same data as grass builder)
	_build_zone_map()

	# Initial chunk loading near spawn
	var spawn := Vector3(-480, 0, 1020)
	_last_update_pos = spawn
	_update_chunks_near(spawn)
	print("Undergrowth: ready (%d chunks queued, %.0fms)" % [
		_build_queue.size(), Time.get_ticks_msec() - t0])


func _build_zone_map() -> void:
	# Read ground_cover_instances.bin to get zone type per grass cell.
	# Build a coarse map: one dominant zone type per 20m chunk.
	var abs_path := ProjectSettings.globalize_path("res://ground_cover_instances.bin")
	var f := FileAccess.open(abs_path, FileAccess.READ)
	if f == null:
		f = FileAccess.open("res://ground_cover_instances.bin", FileAccess.READ)
	if f == null:
		print("Undergrowth: no ground_cover_instances.bin"); return

	f.get_32()  # magic
	var count: int = f.get_32()
	if count == 0: return

	# Binary format: magic(4) + count(4) + gc_x(float32) + gc_y/height(float32)
	#                + gc_z(float32) + gc_type(uint8) + gc_prox(uint8)
	var x_buf := f.get_buffer(count * 4)   # gc_x = world X
	f.get_buffer(count * 4)                # gc_y = height (skip)
	var z_buf := f.get_buffer(count * 4)   # gc_z = world Z
	var t_buf := f.get_buffer(count)       # gc_type = zone type (0-9)
	f.close()

	# Build per-chunk zone type histogram
	var chunk_types: Dictionary = {}  # "cx|cz" -> Dictionary of type->count
	for i in count:
		var wx: float = x_buf.decode_float(i * 4)
		var wz: float = z_buf.decode_float(i * 4)
		var zt: int = t_buf[i]
		var cx: int = int(floorf(wx / CHUNK))
		var cz: int = int(floorf(wz / CHUNK))
		var ck := "%d|%d" % [cx, cz]
		if not chunk_types.has(ck):
			chunk_types[ck] = {}
		var d: Dictionary = chunk_types[ck]
		d[zt] = d.get(zt, 0) + 1

	# Pick dominant type per chunk
	for ck in chunk_types:
		var d: Dictionary = chunk_types[ck]
		var best_type := -1
		var best_count := 0
		for zt in d:
			if d[zt] > best_count:
				best_count = d[zt]
				best_type = zt
		if best_type >= 0:
			_zone_map[ck] = best_type

	print("  Undergrowth: zone map built (%d chunks)" % _zone_map.size())


func update_camera(camera_pos: Vector3) -> void:
	var moved := camera_pos.distance_to(_last_update_pos) > UPDATE_DIST
	if moved:
		_last_update_pos = camera_pos
		_update_chunks_near(camera_pos)
	# Build 1 queued chunk per frame
	if not _build_queue.is_empty():
		_process_queue(camera_pos)


func _update_chunks_near(pos: Vector3) -> void:
	var load_r := int(ceili(LOAD_RANGE / CHUNK))
	var cam_cx := int(floorf(pos.x / CHUNK))
	var cam_cz := int(floorf(pos.z / CHUNK))
	var needed: Dictionary = {}

	for dx in range(-load_r, load_r + 1):
		for dz in range(-load_r, load_r + 1):
			var cx := cam_cx + dx
			var cz := cam_cz + dz
			var cc := Vector3((cx + 0.5) * CHUNK, 0, (cz + 0.5) * CHUNK)
			if cc.distance_to(pos) > LOAD_RANGE: continue
			var ck := "%d|%d" % [cx, cz]

			# Check atlas: only place undergrowth on grass (type 1)
			var sample_x: float = (cx + 0.5) * CHUNK
			var sample_z: float = (cz + 0.5) * CHUNK
			var apx: int = int((sample_x + _atlas_half) * _atlas_scale)
			var apz: int = int((sample_z + _atlas_half) * _atlas_scale)
			if apx < 0 or apx >= _atlas_res or apz < 0 or apz >= _atlas_res: continue
			if _atlas_data[(apz * _atlas_res + apx) * 2] != 1: continue

			needed[ck] = true

	# Unload distant chunks
	var to_remove: Array = []
	for key: String in _active_chunks:
		# key format: "species|cx|cz"
		var p: PackedStringArray = key.split("|")
		var ck := "%s|%s" % [p[1], p[2]]
		if not needed.has(ck):
			_active_chunks[key].queue_free()
			to_remove.append(key)
	for key in to_remove:
		_active_chunks.erase(key)

	# Queue new chunks
	for ck in needed:
		if _chunk_loaded(ck) or _queued_set.has(ck):
			continue
		_build_queue.append(ck)
		_queued_set[ck] = true

	# Prune queue
	var nq: Array = []
	for ck in _build_queue:
		if needed.has(ck): nq.append(ck)
		else: _queued_set.erase(ck)
	_build_queue = nq


func _process_queue(pos: Vector3) -> void:
	var best_i := -1
	var best_d := 999999.0
	for i in _build_queue.size():
		var ck: String = _build_queue[i]
		var p: PackedStringArray = ck.split("|")
		var d := Vector3((float(p[0]) + 0.5) * CHUNK, 0,
						 (float(p[1]) + 0.5) * CHUNK).distance_to(pos)
		if d < best_d: best_d = d; best_i = i
	if best_i < 0: return
	var ck: String = _build_queue[best_i]
	_build_queue.remove_at(best_i)
	_queued_set.erase(ck)
	if not _chunk_loaded(ck):
		_build_chunk(ck)


func _chunk_loaded(ck: String) -> bool:
	for sp_idx in SPECIES.size():
		if _active_chunks.has("%d|%s" % [sp_idx, ck]): return true
	return false


func _build_chunk(ck: String) -> void:
	var ck_p: PackedStringArray = ck.split("|")
	var cx: float = float(ck_p[0]) * CHUNK
	var cz: float = float(ck_p[1]) * CHUNK

	# Determine what species to place based on zone type
	var zone_type: int = _zone_map.get(ck, -1)
	var species_list: Array
	if zone_type >= 0 and ZONE_SPECIES.has(zone_type):
		species_list = ZONE_SPECIES[zone_type]
	elif zone_type < 0:
		# No pre-baked zone data — only treat as woodland if actually in a
		# woodland foliage zone. Otherwise it's a gap in maintained lawn data.
		var chunk_z: float = cz + CHUNK * 0.5
		var in_woodland := false
		for zr in WOODLAND_Z_RANGES:
			if chunk_z >= zr[0] and chunk_z <= zr[1]:
				in_woodland = true
				break
		if in_woodland:
			species_list = WOODLAND_SPECIES
		else:
			return  # Gap in lawn data — no undergrowth
	else:
		return  # Mowed lawn, formal garden, etc. — no undergrowth

	var rng := RandomNumberGenerator.new()
	rng.seed = (int(ck_p[0]) * 73856093 + int(ck_p[1]) * 19349669 + 42) & 0x7FFFFFFF

	# Seasonal check for fungi (indices 16, 17)
	# Mushrooms: peak late summer through fall (season_t 1.5-2.8), absent otherwise
	var season_val = RenderingServer.global_shader_parameter_get("season_t")
	var cur_season: float = float(season_val) if season_val != null else 1.5
	var mushroom_active: bool = cur_season > 1.3 and cur_season < 2.9
	# Rain boosts mushroom density
	var rain_val = RenderingServer.global_shader_parameter_get("rain_wetness")
	var rain_boost: float = 1.0 + (float(rain_val) if rain_val != null else 0.0) * 0.5

	# Pre-allocate buffers per species
	var bufs: Dictionary = {}
	var cnts: Dictionary = {}
	var sums: Dictionary = {}

	for sp_entry in species_list:
		var sp_idx: int = sp_entry[0]
		var density: float = sp_entry[1]
		var sp_name: String = SPECIES[sp_idx].name
		if not _meshes.has(sp_name): continue

		# Skip fungi outside their season
		if sp_idx >= 16 and sp_idx <= 17:
			if not mushroom_active: continue
			density *= rain_boost

		var target := int(density * CHUNK * CHUNK / 100.0)
		if target <= 0: continue

		var buf := PackedFloat32Array()
		buf.resize(target * 2 * 16)  # over-allocate
		bufs[sp_idx] = buf
		cnts[sp_idx] = 0
		sums[sp_idx] = [0.0, 0.0, 0.0]

		var placed := 0
		var sp: Dictionary = SPECIES[sp_idx]
		var s_lo: float = sp.s[0]
		var s_hi: float = sp.s[1]

		for _attempt in int(target * 3):
			if placed >= target: break
			var bx: float = cx + rng.randf() * CHUNK
			var bz: float = cz + rng.randf() * CHUNK

			# Atlas check — must be grass
			var apx: int = int((bx + _atlas_half) * _atlas_scale)
			var apz: int = int((bz + _atlas_half) * _atlas_scale)
			if apx < 0 or apx >= _atlas_res or apz < 0 or apz >= _atlas_res: continue
			var ai: int = (apz * _atlas_res + apx) * 2
			if _atlas_data[ai] != 1: continue
			# Check occupancy — avoid trees, benches, etc.
			if _atlas_data[ai + 1] != 0: continue

			# Heightmap lookup
			var xi: float = (bx + _hm_half) / _hm_ws * (_hm_w - 1)
			var zi: float = (bz + _hm_half) / _hm_ws * (_hm_d - 1)
			var xi0: int = clampi(int(xi), 0, _hm_w - 2)
			var zi0: int = clampi(int(zi), 0, _hm_d - 2)
			var fx: float = xi - xi0
			var fz: float = zi - zi0
			var h00: float = float(_hm_data[zi0 * _hm_w + xi0])
			var h10: float = float(_hm_data[zi0 * _hm_w + xi0 + 1])
			var h01: float = float(_hm_data[(zi0 + 1) * _hm_w + xi0])
			var h11: float = float(_hm_data[(zi0 + 1) * _hm_w + xi0 + 1])
			var wy: float
			if fz <= fx:
				wy = h00 + (h10 - h00) * fx + (h11 - h10) * fz
			else:
				wy = h00 + (h11 - h01) * fx + (h01 - h00) * fz

			var yr: float = rng.randf() * TAU
			var sc: float = rng.randf_range(s_lo, s_hi)
			var seed_val: float = rng.randf()

			# Write transform (rotation Y + uniform scale) + custom data
			var cr: float = cos(yr)
			var sr: float = sin(yr)
			var c: int = cnts[sp_idx]
			var o: int = c * 16
			buf[o] = cr * sc; buf[o+1] = 0.0; buf[o+2] = sr * sc; buf[o+3] = bx
			buf[o+4] = 0.0; buf[o+5] = sc; buf[o+6] = 0.0; buf[o+7] = wy
			buf[o+8] = -sr * sc; buf[o+9] = 0.0; buf[o+10] = cr * sc; buf[o+11] = bz
			buf[o+12] = seed_val; buf[o+13] = sc; buf[o+14] = 0.0; buf[o+15] = 0.0
			cnts[sp_idx] = c + 1
			sums[sp_idx][0] += bx
			sums[sp_idx][1] += wy
			sums[sp_idx][2] += bz
			placed += 1

	# Create MultiMesh per species
	for sp_idx in bufs:
		var c: int = cnts[sp_idx]
		if c == 0: continue
		var sp: Dictionary = SPECIES[sp_idx]
		var sp_name: String = sp.name
		var mesh: Mesh = _meshes[sp_name]

		var buf: PackedFloat32Array = bufs[sp_idx]
		var ox: float = sums[sp_idx][0] / float(c)
		var oy: float = sums[sp_idx][1] / float(c)
		var oz: float = sums[sp_idx][2] / float(c)

		# Relocate to local space
		for j in c:
			var o: int = j * 16
			buf[o+3] -= ox; buf[o+7] -= oy; buf[o+11] -= oz
		buf.resize(c * 16)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = c
		mm.buffer = buf

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = Vector3(ox, oy, oz)
		mmi.name = "UG_%s_%s" % [sp_name, ck]
		mmi.visibility_range_end = VIS_END
		mmi.visibility_range_begin = 0.0
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		_active_chunks["%d|%s" % [sp_idx, ck]] = mmi


func _load_model(sp_name: String) -> Mesh:
	# Try .glb first, then .gltf (mushroom models are .gltf)
	var abs_path := ProjectSettings.globalize_path(
		"res://models/vegetation/%s.glb" % sp_name)
	if not FileAccess.file_exists(abs_path):
		abs_path = ProjectSettings.globalize_path(
			"res://models/vegetation/%s.gltf" % sp_name)
	if not FileAccess.file_exists(abs_path): return null
	var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
	if meshes.is_empty(): return null
	var mesh: Mesh = meshes.values()[0]

	# Find species config
	var sp_cfg: Dictionary = {}
	for sp in SPECIES:
		if sp.name == sp_name:
			sp_cfg = sp
			break

	# Find species index for atlas coordinates
	var sp_idx := 0
	for i in SPECIES.size():
		if SPECIES[i].name == sp_name:
			sp_idx = i
			break

	# Atlas grid: 4x4, each cell = 0.25 UV
	var atlas_col: int = sp_idx % 4
	var atlas_row: int = sp_idx / 4
	var atlas_off := Vector2(atlas_col * 0.25, atlas_row * 0.25)

	# Apply undergrowth shader
	for si in mesh.get_surface_count():
		var mat := ShaderMaterial.new()
		mat.shader = _shader
		mat.set_shader_parameter("wind_flex", sp_cfg.get("flex", 0.3))
		mat.set_shader_parameter("is_evergreen", float(sp_cfg.get("green", 0)))
		var ft: Array = sp_cfg.get("fall", [0.5, 0.35, 0.08])
		mat.set_shader_parameter("fall_tint", Color(ft[0], ft[1], ft[2]))
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		if _loader._canopy_texture:
			mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
		# Leaf texture atlas
		if _leaf_atlas:
			mat.set_shader_parameter("leaf_atlas", _leaf_atlas)
			mat.set_shader_parameter("atlas_offset", atlas_off)
			mat.set_shader_parameter("use_atlas", 1.0)
		mesh.surface_set_material(si, mat)
	return mesh

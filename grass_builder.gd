# grass_builder.gd
# Full-geometry grass (hexaquo method). Each blade is its own MultiMesh
# instance. Patchiness, color, wind, AO all driven by the shader.
#
# Optimized: 5m chunks, inlined atlas/heightmap lookups, buffer-based
# MultiMesh creation. Queue loads 1 chunk per meter walked, closest first.

var _loader
var _blade_meshes: Array = []
var _grass_shader: Shader
# Flat arrays from binary file (~10MB total vs 429MB of per-position Dicts)
var _pos_x: PackedFloat32Array
var _pos_z: PackedFloat32Array
var _pos_type: PackedByteArray
var _pos_prox: PackedByteArray
var _chunk_indices: Dictionary = {}   # "cx|cz" -> PackedInt32Array of indices into flat arrays
var _active_chunks: Dictionary = {}
var _last_update_pos := Vector3(-99999, 0, -99999)
var _build_queue: Array = []
var _queued_set: Dictionary = {}

# Cached atlas/heightmap for inline lookups (set in _build_grass)
var _atlas_data: PackedByteArray
var _atlas_res: int
var _atlas_scale: float
var _atlas_half: float
var _hm_data: Array
var _hm_w: int
var _hm_d: int
var _hm_ws: float
var _hm_half: float

const CHUNK := 10.0
const BLADES_PER_M2 := 600.0
const CELL_SIZE := 1.22
const MAX_BLADES := 40000
const VIS_RANGE := 25.0
const LOAD_RANGE := 40.0
const UNLOAD_RANGE := 50.0
const UPDATE_DIST := 1.0

const BLADE_NAMES: Array = ["Blade_Lawn", "Blade_Wild", "Blade_Shade", "Blade_Sedge"]
const TYPE_TO_BLADE: Array = [0, 0, 0, 0, 0, 2, 2, 3, 1, 0]


func _init(loader) -> void:
	_loader = loader


func _build_grass() -> void:
	var t0 := Time.get_ticks_msec()
	_grass_shader = _loader._get_shader("grass_blade", "res://shaders/grass_blade.gdshader")

	for bname in BLADE_NAMES:
		_blade_meshes.append(_load_blade_model(bname))

	var loaded := 0
	for m in _blade_meshes:
		if m != null: loaded += 1
	if loaded == 0:
		print("Grass: no blade meshes"); return

	# Cache atlas/heightmap refs for inline lookups
	_atlas_data = _loader._atlas_data
	_atlas_res = _loader._atlas_res
	_atlas_scale = float(_atlas_res) / _loader._hm_world_size
	_atlas_half = _loader._hm_world_size * 0.5
	_hm_data = _loader._hm_data
	_hm_w = _loader._hm_width
	_hm_d = _loader._hm_depth
	_hm_ws = _loader._hm_world_size
	_hm_half = _hm_ws * 0.5

	var instances: Array = _load_binary("res://ground_cover_instances.bin", 0x47524332)
	if instances.is_empty():
		print("Grass: no ground cover instances"); return

	_pos_x = instances[0]
	_pos_z = instances[1]
	_pos_type = instances[2]
	# instances[3] = y (not needed — we sample heightmap per blade)
	_pos_prox = instances[4]

	for i in _pos_x.size():
		var cx := int(floorf(_pos_x[i] / CHUNK))
		var cz := int(floorf(_pos_z[i] / CHUNK))
		var ck := "%d|%d" % [cx, cz]
		if not _chunk_indices.has(ck):
			_chunk_indices[ck] = PackedInt32Array()
		_chunk_indices[ck].append(i)

	print("Grass: %d cells in %d chunks (%.0fms)" % [
		_pos_x.size(), _chunk_indices.size(), Time.get_ticks_msec() - t0])

	var spawn := Vector3(350, 0, -1100)
	_last_update_pos = spawn
	_update_chunks_near(spawn)
	# Don't flush queue at startup — let chunks build gradually
	# to avoid VRAM spike during terrain mesh load
	print("Grass: %d chunks queued for gradual loading" % _build_queue.size())


func update_camera(camera_pos: Vector3) -> void:
	var moved := camera_pos.distance_to(_last_update_pos) > UPDATE_DIST
	if moved:
		_last_update_pos = camera_pos
		_update_chunks_near(camera_pos)

	# Build 1 queued chunk per frame (always, not just on movement)
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
			if _chunk_indices.has(ck):
				needed[ck] = true

	var to_remove: Array = []
	for key: String in _active_chunks:
		var p: PackedStringArray = key.split("|")
		var ck: String = "%s|%s" % [p[1], p[2]]
		if not needed.has(ck):
			_active_chunks[key].queue_free()
			to_remove.append(key)
	for key in to_remove:
		_active_chunks.erase(key)

	for ck in needed:
		if _chunk_loaded(ck) or _queued_set.has(ck):
			continue
		_build_queue.append(ck)
		_queued_set[ck] = true

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
		var d := Vector3((float(p[0]) + 0.5) * CHUNK, 0, (float(p[1]) + 0.5) * CHUNK).distance_to(pos)
		if d < best_d: best_d = d; best_i = i
	if best_i < 0: return
	var ck: String = _build_queue[best_i]
	_build_queue.remove_at(best_i)
	_queued_set.erase(ck)
	if not _chunk_loaded(ck) and _chunk_indices.has(ck):
		_build_chunk(ck)


func _flush_queue(pos: Vector3) -> void:
	while not _build_queue.is_empty():
		_process_queue(pos)
	print("Grass: initial build done (active: %d)" % _active_chunks.size())


func _chunk_loaded(ck: String) -> bool:
	for bt in BLADE_NAMES.size():
		if _active_chunks.has("%d|%s" % [bt, ck]): return true
	return false


func _build_chunk(ck: String) -> void:
	var indices: PackedInt32Array = _chunk_indices[ck]
	if indices.is_empty(): return

	var ck_p: PackedStringArray = ck.split("|")
	var cx: float = float(ck_p[0]) * CHUNK
	var cz: float = float(ck_p[1]) * CHUNK

	# Cell lookup: cell_key -> index into flat arrays (for type/prox)
	var cells: Dictionary = {}
	for idx in indices:
		var lx: int = int((_pos_x[idx] - cx) / CELL_SIZE)
		var lz: int = int((_pos_z[idx] - cz) / CELL_SIZE)
		cells[lx * 256 + lz] = idx

	var target: int = mini(int(indices.size() * CELL_SIZE * CELL_SIZE * BLADES_PER_M2), MAX_BLADES)

	var rng := RandomNumberGenerator.new()
	rng.seed = (int(ck_p[0]) * 73856093 + int(ck_p[1]) * 19349669) & 0x7FFFFFFF

	# Pre-allocate buffers per blade type (16 floats per instance: 12 transform + 4 custom)
	var bufs: Array = []
	var cnts: Array = []
	var sum_x: Array = []
	var sum_y: Array = []
	var sum_z: Array = []
	for _bt in 4:
		var b := PackedFloat32Array()
		b.resize(target * 16)
		bufs.append(b)
		cnts.append(0)
		sum_x.append(0.0); sum_y.append(0.0); sum_z.append(0.0)

	var placed := 0
	var ar: int = _atlas_res
	var asc: float = _atlas_scale
	var ah: float = _atlas_half
	var ad: PackedByteArray = _atlas_data
	var hd: Array = _hm_data
	var hw: int = _hm_w
	var hde: int = _hm_d
	var hws: float = _hm_ws
	var hh: float = _hm_half

	for _i in int(target * 1.5):
		if placed >= target: break
		var bx: float = cx + rng.randf() * CHUNK
		var bz: float = cz + rng.randf() * CHUNK

		# Inline atlas check
		var apx: int = int((bx + ah) * asc)
		var apz: int = int((bz + ah) * asc)
		if apx < 0 or apx >= ar or apz < 0 or apz >= ar: continue
		if ad[(apz * ar + apx) * 2] != 1: continue

		# Cell lookup
		var lx: int = int((bx - cx) / CELL_SIZE)
		var lz: int = int((bz - cz) / CELL_SIZE)
		var ck_key: int = lx * 256 + lz
		var ot: int = 9
		var pp: float = 0.0
		if cells.has(ck_key):
			var ci: int = cells[ck_key]
			ot = _pos_type[ci]
			pp = float(_pos_prox[ci]) / 255.0

		var bt: int = TYPE_TO_BLADE[ot] if ot < TYPE_TO_BLADE.size() else 0
		if bt >= _blade_meshes.size() or _blade_meshes[bt] == null: continue

		# Inline heightmap (barycentric)
		var xi: float = (bx + hh) / hws * (hw - 1)
		var zi: float = (bz + hh) / hws * (hde - 1)
		var xi0: int = clampi(int(xi), 0, hw - 2)
		var zi0: int = clampi(int(zi), 0, hde - 2)
		var fx: float = xi - xi0
		var fz: float = zi - zi0
		var h00: float = float(hd[zi0 * hw + xi0])
		var h10: float = float(hd[zi0 * hw + xi0 + 1])
		var h01: float = float(hd[(zi0 + 1) * hw + xi0])
		var h11: float = float(hd[(zi0 + 1) * hw + xi0 + 1])
		var wy: float = h00 + (h10 - h00) * fx + (h11 - h10) * fz if fz <= fx else h00 + (h11 - h01) * fx + (h01 - h00) * fz

		var yr: float = rng.randf() * TAU
		var hs: float = rng.randf_range(0.7, 1.3)
		if pp > 0.1: hs *= lerpf(1.0, 0.4, pp)
		var rs: float = rng.randf()

		# Wildflower flag: ~3% of lawn blades become flowers
		# 0.0=grass, 0.1=white clover, 0.2=dandelion, 0.3=violet, 0.4=buttercup
		var flower: float = 0.0
		if ot <= 4 or ot == 9:  # lawn types only
			if rs < 0.03:  # 3% chance (rs is the blade seed)
				var ftype: float = fmod(rs * 1000.0, 4.0)
				flower = (floorf(ftype) + 1.0) * 0.1  # 0.1, 0.2, 0.3, or 0.4

		# Direct buffer write (no Transform3D/Color objects)
		var cr: float = cos(yr)
		var sr: float = sin(yr)
		var buf: PackedFloat32Array = bufs[bt]
		var idx: int = cnts[bt]
		var o: int = idx * 16
		buf[o] = cr; buf[o+1] = 0.0; buf[o+2] = sr; buf[o+3] = bx
		buf[o+4] = 0.0; buf[o+5] = hs; buf[o+6] = 0.0; buf[o+7] = wy
		buf[o+8] = -sr; buf[o+9] = 0.0; buf[o+10] = cr; buf[o+11] = bz
		buf[o+12] = float(ot); buf[o+13] = rs; buf[o+14] = pp; buf[o+15] = flower
		cnts[bt] = idx + 1
		sum_x[bt] += bx; sum_y[bt] += wy; sum_z[bt] += bz
		placed += 1

	# Create MultiMesh per blade type
	for bt in 4:
		var c: int = cnts[bt]
		if c == 0: continue
		if _blade_meshes[bt] == null: continue

		var buf: PackedFloat32Array = bufs[bt]
		var ox: float = sum_x[bt] / float(c)
		var oy: float = sum_y[bt] / float(c)
		var oz: float = sum_z[bt] / float(c)

		# Relocate to local space
		for j in c:
			var o: int = j * 16
			buf[o+3] -= ox; buf[o+7] -= oy; buf[o+11] -= oz
		buf.resize(c * 16)

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = _blade_meshes[bt]
		mm.instance_count = c
		mm.buffer = buf  # bulk set — much faster than per-instance calls

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.position = Vector3(ox, oy, oz)
		mmi.name = "Grass_%d_%s" % [bt, ck]
		mmi.visibility_range_end = VIS_RANGE
		mmi.visibility_range_end_margin = VIS_RANGE * 0.40
		mmi.visibility_range_begin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_loader.add_child(mmi)
		_active_chunks["%d|%s" % [bt, ck]] = mmi


func _load_blade_model(bname: String) -> Mesh:
	var abs_path := ProjectSettings.globalize_path("res://models/vegetation/%s.glb" % bname)
	if not FileAccess.file_exists(abs_path): return null
	var meshes: Dictionary = _loader._load_glb_meshes(abs_path)
	if meshes.is_empty(): return null
	var mesh: Mesh = meshes.values()[0]
	for si in mesh.get_surface_count():
		var mat := ShaderMaterial.new()
		mat.shader = _grass_shader
		if _loader._canopy_texture:
			mat.set_shader_parameter("canopy_map", _loader._canopy_texture)
		mat.set_shader_parameter("hm_world_size", _loader._hm_world_size)
		mesh.surface_set_material(si, mat)
	return mesh


func _load_binary(res_path: String, expected_magic: int) -> Array:
	var abs_path := ProjectSettings.globalize_path(res_path)
	var f := FileAccess.open(abs_path, FileAccess.READ)
	if f == null: f = FileAccess.open(res_path, FileAccess.READ)
	if f == null: return []
	var magic: int = f.get_32()
	var magic_rev: int = ((magic & 0xFF) << 24) | ((magic & 0xFF00) << 8) | ((magic & 0xFF0000) >> 8) | ((magic & 0xFF000000) >> 24)
	if magic != expected_magic and magic_rev != expected_magic: return []
	var cnt: int = f.get_32()
	if cnt == 0: return []
	var xb := f.get_buffer(cnt * 4)
	var yb := f.get_buffer(cnt * 4)
	var zb := f.get_buffer(cnt * 4)
	var tb := f.get_buffer(cnt)
	var pb := f.get_buffer(cnt)
	var xa := PackedFloat32Array(); xa.resize(cnt)
	var ya := PackedFloat32Array(); ya.resize(cnt)
	var za := PackedFloat32Array(); za.resize(cnt)
	var ta := PackedByteArray(); ta.resize(cnt)
	var pa := PackedByteArray(); pa.resize(cnt)
	for j in cnt:
		xa[j] = xb.decode_float(j * 4)
		ya[j] = yb.decode_float(j * 4)
		za[j] = zb.decode_float(j * 4)
		ta[j] = tb[j]; pa[j] = pb[j]
	print("  Grass: %d positions loaded" % cnt)
	return [xa, za, ta, ya, pa]

# chunk_builder.gd
# Base class for chunk-based MultiMesh builders with distance-based loading.
# Shared by ground_cover_builder and grass_accent_builder.
# Handles chunk grid management, queue processing, and terrain sampling.

var _loader
var _meshes: Dictionary = {}
var _active_chunks: Dictionary = {}  # "cx|cz" -> Array of [mm_rid, inst_rid]
var _last_update_pos := Vector3(-99999, 0, -99999)
var _build_queue: Array = []
var _queued_set: Dictionary = {}
var _scenario: RID                    # cached World3D scenario for RS instances

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

var season_t: float = 1.5

# Chunk params — set by subclass via _init_chunks()
var _chunk_size: float
var _load_range: float
var _unload_range: float
var _update_dist: float
var _vis_end: float
var _vis_fade_margin: float


func _init(loader) -> void:
	_loader = loader


func _init_chunks(chunk: float, load_r: float, unload_r: float,
		update_d: float, vis_end: float, vis_fade: float) -> void:
	_chunk_size = chunk
	_load_range = load_r
	_unload_range = unload_r
	_update_dist = update_d
	_vis_end = vis_end
	_vis_fade_margin = vis_fade
	_atlas_data = _loader._atlas_data
	_atlas_res = _loader._atlas_res
	_atlas_scale = float(_atlas_res) / _loader._hm_world_size
	_atlas_half = _loader._hm_world_size * 0.5
	_scenario = _loader.get_world_3d().get_scenario()
	_hm_data = _loader._hm_data
	_hm_w = _loader._hm_width
	_hm_d = _loader._hm_depth
	_hm_ws = _loader._hm_world_size
	_hm_half = _hm_ws * 0.5


func update_camera(camera_pos: Vector3) -> void:
	var dv := camera_pos - _last_update_pos
	if dv.x * dv.x + dv.z * dv.z > _update_dist * _update_dist:
		_last_update_pos = camera_pos
		_update_chunks_near(camera_pos)
	_process_queue(camera_pos)


func _update_chunks_near(pos: Vector3) -> void:
	var cx0 := int(floor((pos.x - _load_range) / _chunk_size))
	var cx1 := int(floor((pos.x + _load_range) / _chunk_size))
	var cz0 := int(floor((pos.z - _load_range) / _chunk_size))
	var cz1 := int(floor((pos.z + _load_range) / _chunk_size))

	var needed: Dictionary = {}
	for cx in range(cx0, cx1 + 1):
		for cz in range(cz0, cz1 + 1):
			var wx := cx * _chunk_size + _chunk_size * 0.5
			var wz := cz * _chunk_size + _chunk_size * 0.5
			var dx := wx - pos.x
			var dz := wz - pos.z
			if dx * dx + dz * dz > _load_range * _load_range:
				continue
			var ai := int((wx + _atlas_half) * _atlas_scale)
			var aj := int((wz + _atlas_half) * _atlas_scale)
			if ai < 0 or ai >= _atlas_res or aj < 0 or aj >= _atlas_res:
				continue
			var surf: int = _atlas_data[(aj * _atlas_res + ai) * 2]
			if surf != 1:
				continue
			var ck := "%d|%d" % [cx, cz]
			needed[ck] = true

	var to_remove: Array = []
	for ck in _active_chunks:
		if not needed.has(ck):
			for rid_pair in _active_chunks[ck]:
				RenderingServer.free_rid(rid_pair[1])  # instance first
				RenderingServer.free_rid(rid_pair[0])  # then multimesh
			to_remove.append(ck)
	for ck in to_remove:
		_active_chunks.erase(ck)

	for ck in needed:
		if not _active_chunks.has(ck) and not _queued_set.has(ck):
			_build_queue.append(ck)
			_queued_set[ck] = true


func _process_queue(pos: Vector3) -> void:
	if _build_queue.is_empty():
		return
	_build_queue.sort_custom(func(a: String, b: String) -> bool:
		var pa := a.split("|"); var pb := b.split("|")
		var da := (int(pa[0]) * _chunk_size - pos.x) ** 2 + (int(pa[1]) * _chunk_size - pos.z) ** 2
		var db := (int(pb[0]) * _chunk_size - pos.x) ** 2 + (int(pb[1]) * _chunk_size - pos.z) ** 2
		return da < db)
	var ck: String = _build_queue.pop_front()
	_queued_set.erase(ck)
	var cp := ck.split("|")
	var wx := int(cp[0]) * _chunk_size + _chunk_size * 0.5
	var wz := int(cp[1]) * _chunk_size + _chunk_size * 0.5
	if (wx - pos.x) ** 2 + (wz - pos.z) ** 2 > _unload_range * _unload_range:
		return
	_build_chunk(ck)


func _build_chunk(_ck: String) -> void:
	pass


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

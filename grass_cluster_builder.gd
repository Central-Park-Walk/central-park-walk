## Grass LOD Tier 2: Static MultiMesh blade clusters (10-35m).
##
## Bridges the visual gap between individual GPU-particle blades (Tier 1)
## and crossed-card tufts (Tier 3). Each instance is a procedurally generated
## cluster of 3 thin crossed quads with blade-like proportions — reads as
## "a few grass blades" from mid-distance, not "a textured card."
##
## Uses the same render shader as tufts (grass_tuft_render.gdshader) with
## different dither distance uniforms for its position in the LOD chain.

extends Node3D

var terrain: Terrain3D
var landuse_image: Image
var canopy_image: Image
var world_size: float = 5000.0
var render_shader: Shader

## Cluster geometry parameters per biome (height_cm, width_cm, blade_count)
## Wider than real blades — at 10-35m these are a few pixels on screen.
## 3 crossed quads give blade-like silhouette, not flat-card character.
const BIOME_CLUSTER := {
	0: {"height": 10.0, "width": 25.0, "blades": 3},  # lawn: ~25cm coverage radius
	1: {"height": 14.0, "width": 22.0, "blades": 3},  # shade
	2: {"height": 28.0, "width": 28.0, "blades": 3},  # wild
	3: {"height": 20.0, "width": 25.0, "blades": 3},  # sedge
}

const CHUNK_SIZE := 32.0
## Same spacing as tuft builder — gives ~300K instances, fast build, low memory.
## Coverage comes from wider geometry, not tighter packing.
const BIOME_SPACING := {0: 1.00, 1: 1.30, 2: 1.20, 3: 1.30}

## Visibility range for GPU culling. Shader dither handles soft transitions.
const VIS_BEGIN := 8.0
const VIS_END := 40.0

## Zone → biome mapping (matches particle shader)
const ZONE_TO_BIOME := {
	0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 9: 0,
	5: 1, 6: 1, 10: 1, 11: 1,
	8: 2,
	7: 3,
}

const BIOME_CANOPY_SUPPRESS := {0: 0.90, 1: 0.30, 2: 0.60, 3: 0.60}

## Dither crossfade ranges — set on the shader material
const DITHER_NEAR_BEGIN := 10.0
const DITHER_NEAR_END := 14.0
const DITHER_FAR_BEGIN := 28.0
const DITHER_FAR_END := 35.0

var _cluster_meshes: Dictionary = {}  # biome_id → ArrayMesh
var _chunks_built := 0
var _instances_total := 0
var _rng := RandomNumberGenerator.new()

var _lu_bytes: PackedByteArray
var _lu_w: int
var _lu_h: int
var _can_bytes: PackedByteArray
var _can_w: int
var _can_h: int


func build_all_chunks() -> void:
	if not terrain or not terrain.data:
		push_warning("GrassClusterBuilder: no terrain data")
		return
	if not landuse_image:
		push_warning("GrassClusterBuilder: no landuse image")
		return

	_lu_bytes = landuse_image.get_data()
	_lu_w = landuse_image.get_width()
	_lu_h = landuse_image.get_height()
	if canopy_image:
		_can_bytes = canopy_image.get_data()
		_can_w = canopy_image.get_width()
		_can_h = canopy_image.get_height()

	# Generate procedural cluster meshes per biome
	for biome_id in BIOME_CLUSTER:
		_cluster_meshes[biome_id] = _make_cluster_mesh(biome_id)

	_rng.seed = 137  # Different seed from tuft builder to avoid alignment

	print("GrassClusterBuilder: starting (%dx%d landuse)" % [_lu_w, _lu_h])

	var half := world_size * 0.5
	var cx_start := int(floor((-1300.0 + half) / CHUNK_SIZE))
	var cx_end := int(ceil((1300.0 + half) / CHUNK_SIZE))
	var cz_start := int(floor((-2100.0 + half) / CHUNK_SIZE))
	var cz_end := int(ceil((2100.0 + half) / CHUNK_SIZE))

	for cx in range(cx_start, cx_end):
		for cz in range(cz_start, cz_end):
			var origin_x := cx * CHUNK_SIZE - half
			var origin_z := cz * CHUNK_SIZE - half
			_build_chunk(origin_x, origin_z)

	print("GrassClusterBuilder: %d chunks, %d clusters total" % [
		_chunks_built, _instances_total])


func _make_cluster_mesh(biome_id: int) -> ArrayMesh:
	## Generate a procedural blade cluster: 3 crossed thin quads forming a star.
	## Reads as "a few grass blades" from 10-35m — bridges blade↔tuft gap.
	var cfg: Dictionary = BIOME_CLUSTER[biome_id]
	var h: float = float(cfg.height) / 100.0  # cm → m
	var w: float = float(cfg.width) / 100.0
	var n_blades: int = int(cfg.blades)

	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var normals := PackedVector3Array()

	for i in n_blades:
		var angle: float = float(i) / float(n_blades) * PI  # 0°, 60°, 120°
		var dx: float = cos(angle) * w * 0.5
		var dz: float = sin(angle) * w * 0.5
		var nx: float = -sin(angle)
		var nz: float = cos(angle)
		var norm := Vector3(nx, 0.0, nz).normalized()

		# Slight taper: tip is 40% of base width
		var tip_dx: float = dx * 0.4
		var tip_dz: float = dz * 0.4

		# Quad: 2 triangles, bottom-left to top-right
		# Bottom-left, bottom-right, top-right (tri 1)
		verts.append(Vector3(-dx, 0.0, -dz))
		verts.append(Vector3( dx, 0.0,  dz))
		verts.append(Vector3( tip_dx, h,  tip_dz))
		# Bottom-left, top-right, top-left (tri 2)
		verts.append(Vector3(-dx, 0.0, -dz))
		verts.append(Vector3( tip_dx, h,  tip_dz))
		verts.append(Vector3(-tip_dx, h, -tip_dz))

		# UVs: y=0 at base, y=1 at tip (for root-to-tip color gradient)
		uvs.append(Vector2(0.0, 0.0))
		uvs.append(Vector2(1.0, 0.0))
		uvs.append(Vector2(1.0, 1.0))
		uvs.append(Vector2(0.0, 0.0))
		uvs.append(Vector2(1.0, 1.0))
		uvs.append(Vector2(0.0, 1.0))

		for _j in 6:
			normals.append(norm)

	var mesh := ArrayMesh.new()
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_NORMAL] = normals
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


func _build_chunk(origin_x: float, origin_z: float) -> void:
	var has_grass := false
	for sx in [0.0, 0.5, 1.0]:
		for sz in [0.0, 0.5, 1.0]:
			var zone := _zone_fast(origin_x + sx * CHUNK_SIZE,
				origin_z + sz * CHUNK_SIZE)
			if ZONE_TO_BIOME.has(zone):
				has_grass = true
				break
		if has_grass:
			break
	if not has_grass:
		return

	# Pre-sample terrain height grid (4m resolution)
	var h_step := 4.0
	var h_cols := int(CHUNK_SIZE / h_step) + 1
	var h_grid := PackedFloat32Array()
	h_grid.resize(h_cols * h_cols)
	var all_nan := true
	for hx in h_cols:
		for hz in h_cols:
			var wx := origin_x + float(hx) * h_step
			var wz := origin_z + float(hz) * h_step
			var h := terrain.data.get_height(Vector3(wx, 0.0, wz))
			if is_nan(h):
				h = -999.0
			else:
				all_nan = false
			h_grid[hx * h_cols + hz] = h
	if all_nan:
		return

	var xforms: Dictionary = {}
	var customs: Dictionary = {}
	for biome_id in _cluster_meshes:
		xforms[biome_id] = []
		customs[biome_id] = []

	# Iterate at 1.0m grid — matches minimum biome spacing
	var step := 1.0
	var cols := int(CHUNK_SIZE / step)

	for ix in cols:
		for iz in cols:
			var base_x := origin_x + (float(ix) + 0.5) * step
			var base_z := origin_z + (float(iz) + 0.5) * step

			var zone := _zone_fast(base_x, base_z)
			if not ZONE_TO_BIOME.has(zone):
				continue
			var biome_id: int = ZONE_TO_BIOME[zone]
			if not _cluster_meshes.has(biome_id):
				continue

			var target_spacing: float = BIOME_SPACING.get(biome_id, 0.40)
			var keep_ratio := (step * step) / (target_spacing * target_spacing)
			if _rng.randf() > keep_ratio:
				continue

			var jx := base_x + _rng.randf_range(-0.15, 0.15)
			var jz := base_z + _rng.randf_range(-0.15, 0.15)

			var canopy := _canopy_fast(jx, jz)
			var suppress: float = BIOME_CANOPY_SUPPRESS.get(biome_id, 0.5)
			if canopy > 0.1 and _rng.randf() < canopy * suppress:
				continue

			var height := _height_interp(h_grid, h_cols, h_step,
				origin_x, origin_z, jx, jz)
			if height < -50.0:
				continue

			var rot := _rng.randf() * TAU
			var sf := _rng.randf_range(0.8, 1.4)
			var t := Transform3D()
			t = t.scaled(Vector3(sf, sf, sf))
			t = t.rotated(Vector3.UP, rot)
			t.origin = Vector3(jx, height - 0.005, jz)

			xforms[biome_id].append(t)
			customs[biome_id].append(Color(
				float(zone) / 15.0, canopy, _rng.randf(), 0.0))

	for biome_id in xforms:
		var tlist: Array = xforms[biome_id]
		if tlist.is_empty():
			continue
		var clist: Array = customs[biome_id]
		var count := tlist.size()

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = _cluster_meshes[biome_id]
		mm.instance_count = count

		for i in count:
			mm.set_instance_transform(i, tlist[i])
			mm.set_instance_custom_data(i, clist[i])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mmi.visibility_range_begin = VIS_BEGIN
		mmi.visibility_range_begin_margin = 0.0
		mmi.visibility_range_end = VIS_END
		mmi.visibility_range_end_margin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED

		if render_shader:
			var mat := ShaderMaterial.new()
			mat.shader = render_shader
			mat.set_shader_parameter("use_texture", false)
			mat.set_shader_parameter("dither_near_begin", DITHER_NEAR_BEGIN)
			mat.set_shader_parameter("dither_near_end", DITHER_NEAR_END)
			mat.set_shader_parameter("dither_far_begin", DITHER_FAR_BEGIN)
			mat.set_shader_parameter("dither_far_end", DITHER_FAR_END)
			mmi.material_override = mat

		add_child(mmi)
		_instances_total += count

	_chunks_built += 1


func _zone_fast(wx: float, wz: float) -> int:
	var u := (wx + world_size * 0.5) / world_size
	var v := (wz + world_size * 0.5) / world_size
	var px := clampi(int(u * _lu_w), 0, _lu_w - 1)
	var py := clampi(int(v * _lu_h), 0, _lu_h - 1)
	return _lu_bytes[py * _lu_w + px]


func _canopy_fast(wx: float, wz: float) -> float:
	if _can_bytes.is_empty():
		return 0.0
	var u := (wx + world_size * 0.5) / world_size
	var v := (wz + world_size * 0.5) / world_size
	var px := clampi(int(u * _can_w), 0, _can_w - 1)
	var py := clampi(int(v * _can_h), 0, _can_h - 1)
	return float(_can_bytes[py * _can_w + px]) / 255.0


func _height_interp(grid: PackedFloat32Array, grid_cols: int, grid_step: float,
		ox: float, oz: float, wx: float, wz: float) -> float:
	var lx := (wx - ox) / grid_step
	var lz := (wz - oz) / grid_step
	var ix := int(lx)
	var iz := int(lz)
	ix = clampi(ix, 0, grid_cols - 2)
	iz = clampi(iz, 0, grid_cols - 2)
	var fx := clampf(lx - float(ix), 0.0, 1.0)
	var fz := clampf(lz - float(iz), 0.0, 1.0)
	var h00 := grid[ix * grid_cols + iz]
	var h10 := grid[(ix + 1) * grid_cols + iz]
	var h01 := grid[ix * grid_cols + iz + 1]
	var h11 := grid[(ix + 1) * grid_cols + iz + 1]
	if h00 < -50.0 or h10 < -50.0 or h01 < -50.0 or h11 < -50.0:
		return -999.0
	return h00 * (1.0 - fx) * (1.0 - fz) + h10 * fx * (1.0 - fz) \
		+ h01 * (1.0 - fx) * fz + h11 * fx * fz

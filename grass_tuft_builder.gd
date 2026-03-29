## Grass LOD Tier 2: Static MultiMeshInstance3D chunks of crossed-card tufts.
##
## Scatters pre-made tuft meshes (Tuft_Tiny/Woodland/Wild/Meadow.glb) into
## world-fixed 32×32m chunks using zone-aware density from the landuse map.
## Uses Godot's visibility_range for automatic distance culling (15-55m).
##
## This is a fundamentally different rendering method from the GPU particle
## blade system (Tiers 0/1): chunks are built once at load, don't follow the
## camera, and use simpler wind. The visual character at 15-50m is "textured
## carpet" rather than "individual blades."

extends Node3D

## Terrain3D node for height queries
var terrain: Terrain3D
## R8 landuse zone image (8192×8192, zone IDs 0-13)
var landuse_image: Image
## Grayscale canopy coverage image
var canopy_image: Image
## World extent in meters (centered at origin)
var world_size: float = 5000.0

## Tuft meshes keyed by biome_id
var tuft_meshes: Dictionary = {}   # int → Mesh
## Tuft textures keyed by biome_id
var tuft_textures: Dictionary = {} # int → Texture2D
## Shared render shader
var render_shader: Shader

const CHUNK_SIZE := 32.0
## Tuft spacing per biome (meters between instances).
const BIOME_SPACING := {0: 1.20, 1: 1.60, 2: 1.40, 3: 1.60}
## Visibility range — begin just inside Tier 1's fade start (13.5m) so tufts
## appear as background while blades are still dominant. Far enough that
## tufts aren't individually distinguishable, avoiding moiré with blade grid.
## Extended far end (70m) for longer 3D grass coverage before terrain-only.
const VIS_BEGIN := 13.0
const VIS_END := 70.0
const VIS_FADE := 10.0

## Zone → biome mapping (matches grass_particles.gdshader)
const ZONE_TO_BIOME := {
	0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 9: 0,  # lawn zones
	5: 1, 6: 1, 10: 1, 11: 1,              # shade/woodland
	8: 2,                                    # wild meadow
	7: 3,                                    # waterside/sedge
}

## Canopy suppression per biome
const BIOME_CANOPY_SUPPRESS := {0: 0.90, 1: 0.30, 2: 0.60, 3: 0.60}

var _chunks_built := 0
var _tufts_total := 0
var _rng := RandomNumberGenerator.new()

# Raw byte buffers for fast pixel lookup (avoid get_pixel overhead)
var _lu_bytes: PackedByteArray
var _lu_w: int
var _lu_h: int
var _can_bytes: PackedByteArray
var _can_w: int
var _can_h: int


func build_all_chunks() -> void:
	if not terrain or not terrain.data:
		push_warning("GrassTuftBuilder: no terrain data")
		return
	if not landuse_image:
		push_warning("GrassTuftBuilder: no landuse image")
		return

	# Pre-extract raw bytes for fast zone/canopy lookup
	_lu_bytes = landuse_image.get_data()
	_lu_w = landuse_image.get_width()
	_lu_h = landuse_image.get_height()
	if canopy_image:
		_can_bytes = canopy_image.get_data()
		_can_w = canopy_image.get_width()
		_can_h = canopy_image.get_height()

	_rng.seed = 42
	print("GrassTuftBuilder: starting (%dx%d landuse, %d tuft meshes)" % [
		_lu_w, _lu_h, tuft_meshes.size()])

	# Park bounds (generous)
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

	print("GrassTuftBuilder: %d chunks, %d tufts total" % [_chunks_built, _tufts_total])


func _build_chunk(origin_x: float, origin_z: float) -> void:
	# Quick reject: sample 9 points
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

	# Pre-sample terrain height on a coarse 4m grid (9×9 = 81 queries per chunk)
	# then bilinearly interpolate for each tuft. Avoids millions of get_height calls.
	var h_step := 4.0
	var h_cols := int(CHUNK_SIZE / h_step) + 1  # 9
	var h_grid: PackedFloat32Array = PackedFloat32Array()
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

	# Collect transforms + custom_data per biome
	var xforms: Dictionary = {}
	var customs: Dictionary = {}
	for biome_id in tuft_meshes:
		xforms[biome_id] = []
		customs[biome_id] = []

	# Iterate at 1.2m grid (26×26 = 676 samples per chunk)
	var step := 1.20
	var cols := int(CHUNK_SIZE / step)

	for ix in cols:
		for iz in cols:
			var base_x := origin_x + (float(ix) + 0.5) * step
			var base_z := origin_z + (float(iz) + 0.5) * step

			var zone := _zone_fast(base_x, base_z)
			if not ZONE_TO_BIOME.has(zone):
				continue
			var biome_id: int = ZONE_TO_BIOME[zone]
			if not tuft_meshes.has(biome_id):
				continue

			# Density thinning based on biome spacing
			var target_spacing: float = BIOME_SPACING.get(biome_id, 0.60)
			var keep_ratio := (step * step) / (target_spacing * target_spacing)
			if _rng.randf() > keep_ratio:
				continue

			# Jitter — ±0.50 (was ±0.30) to break up grid regularity
			# and prevent moiré/denim patterns in the overlap zone
			var jx := base_x + _rng.randf_range(-0.50, 0.50)
			var jz := base_z + _rng.randf_range(-0.50, 0.50)

			# Canopy suppression
			var canopy := _canopy_fast(jx, jz)
			var suppress: float = BIOME_CANOPY_SUPPRESS.get(biome_id, 0.5)
			if canopy > 0.1 and _rng.randf() < canopy * suppress:
				continue

			# Interpolate height from pre-sampled grid
			var height := _height_interp(h_grid, h_cols, h_step,
				origin_x, origin_z, jx, jz)
			if height < -50.0:
				continue

			# Build transform
			var rot := _rng.randf() * TAU
			var sf := _rng.randf_range(0.7, 1.3)
			var t := Transform3D()
			t = t.scaled(Vector3(sf, sf, sf))
			t = t.rotated(Vector3.UP, rot)
			t.origin = Vector3(jx, height - 0.01, jz)

			xforms[biome_id].append(t)
			customs[biome_id].append(Color(
				float(zone) / 15.0, canopy, _rng.randf(), 0.0))

	# Build MultiMeshInstance3D per biome
	for biome_id in xforms:
		var tlist: Array = xforms[biome_id]
		if tlist.is_empty():
			continue
		var clist: Array = customs[biome_id]
		var count := tlist.size()

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = tuft_meshes[biome_id]
		mm.instance_count = count

		for i in count:
			mm.set_instance_transform(i, tlist[i])
			mm.set_instance_custom_data(i, clist[i])

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# Visibility range for GPU culling (chunks outside range aren't drawn).
		# Fade is DISABLED — dithered crossfade in the fragment shader handles
		# smooth transitions (lod_dither.gdshaderinc), coordinated with particles.
		mmi.visibility_range_begin = VIS_BEGIN
		mmi.visibility_range_begin_margin = 0.0
		mmi.visibility_range_end = VIS_END
		mmi.visibility_range_end_margin = 0.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED

		if render_shader and tuft_textures.has(biome_id):
			var mat := ShaderMaterial.new()
			mat.shader = render_shader
			mat.set_shader_parameter("grass_albedo", tuft_textures[biome_id])
			mmi.material_override = mat

		add_child(mmi)
		_tufts_total += count

	_chunks_built += 1


func _zone_fast(wx: float, wz: float) -> int:
	"""Fast zone lookup via raw byte array (no get_pixel overhead)."""
	var u := (wx + world_size * 0.5) / world_size
	var v := (wz + world_size * 0.5) / world_size
	var px := clampi(int(u * _lu_w), 0, _lu_w - 1)
	var py := clampi(int(v * _lu_h), 0, _lu_h - 1)
	return _lu_bytes[py * _lu_w + px]


func _canopy_fast(wx: float, wz: float) -> float:
	"""Fast canopy lookup via raw byte array."""
	if _can_bytes.is_empty():
		return 0.0
	var u := (wx + world_size * 0.5) / world_size
	var v := (wz + world_size * 0.5) / world_size
	var px := clampi(int(u * _can_w), 0, _can_w - 1)
	var py := clampi(int(v * _can_h), 0, _can_h - 1)
	return float(_can_bytes[py * _can_w + px]) / 255.0


func _height_interp(grid: PackedFloat32Array, grid_cols: int, grid_step: float,
		ox: float, oz: float, wx: float, wz: float) -> float:
	"""Bilinear interpolation of pre-sampled height grid."""
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
	# Skip if any corner is invalid
	if h00 < -50.0 or h10 < -50.0 or h01 < -50.0 or h11 < -50.0:
		return -999.0
	return h00 * (1.0 - fx) * (1.0 - fz) + h10 * fx * (1.0 - fz) \
		+ h01 * (1.0 - fx) * fz + h11 * fx * fz

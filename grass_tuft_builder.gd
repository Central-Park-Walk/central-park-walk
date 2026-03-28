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
## Shared render shader material (cloned per chunk for per-mesh texture)
var render_shader: Shader

const CHUNK_SIZE := 32.0
## Spacing between tuft instances (meters). Lawn is denser, others sparser.
const BIOME_SPACING := {0: 0.35, 1: 0.50, 2: 0.45, 3: 0.50}
## Visibility range: tufts fade in at 15m, fully gone at 55m
const VIS_BEGIN := 15.0
const VIS_END := 55.0
## Fade margin for smooth dither transitions
const VIS_FADE := 8.0

## Zone → biome mapping (matches grass_particles.gdshader)
const ZONE_TO_BIOME := {
	0: 0,   # unzoned → lawn
	1: 0,   # garden → lawn
	2: 0,   # grass → lawn
	3: 0,   # pitch → lawn
	4: 0,   # playground → lawn
	5: 1,   # nature_reserve → shade
	6: 1,   # dog_park → shade
	7: 3,   # sports/waterside → sedge
	8: 2,   # wild meadow → wild
	9: 0,   # track → lawn
	10: 1,  # wood → shade
	11: 1,  # forest → shade
}

## Canopy suppression per biome (matches process shader)
const BIOME_CANOPY_SUPPRESS := {0: 0.90, 1: 0.30, 2: 0.60, 3: 0.60}

var _chunks_built := 0
var _tufts_total := 0
var _rng := RandomNumberGenerator.new()


func build_all_chunks() -> void:
	"""Scatter tufts across the entire park. Call once during setup."""
	if not terrain or not terrain.data:
		push_warning("GrassTuftBuilder: no terrain data")
		return
	if not landuse_image:
		push_warning("GrassTuftBuilder: no landuse image")
		return

	_rng.seed = 42  # Deterministic scatter

	# Park bounds: iterate only the area that could contain grass.
	# Central Park runs roughly X:-1200..1200, Z:-2000..2000.
	var x_min := -1300.0
	var x_max := 1300.0
	var z_min := -2100.0
	var z_max := 2100.0

	var cx_start := int(floor((x_min + world_size * 0.5) / CHUNK_SIZE))
	var cx_end := int(ceil((x_max + world_size * 0.5) / CHUNK_SIZE))
	var cz_start := int(floor((z_min + world_size * 0.5) / CHUNK_SIZE))
	var cz_end := int(ceil((z_max + world_size * 0.5) / CHUNK_SIZE))

	for cx in range(cx_start, cx_end):
		for cz in range(cz_start, cz_end):
			var origin_x := cx * CHUNK_SIZE - world_size * 0.5
			var origin_z := cz * CHUNK_SIZE - world_size * 0.5
			_build_chunk(origin_x, origin_z)

	print("GrassTuftBuilder: %d chunks, %d tufts total" % [_chunks_built, _tufts_total])


func _build_chunk(origin_x: float, origin_z: float) -> void:
	"""Build a single 32×32m chunk of tuft instances."""
	# Quick reject: sample 9 points to check if any grass zones exist
	var has_grass := false
	for sx in [0.0, 0.5, 1.0]:
		for sz in [0.0, 0.5, 1.0]:
			var zone := _sample_zone(origin_x + sx * CHUNK_SIZE,
				origin_z + sz * CHUNK_SIZE)
			if ZONE_TO_BIOME.has(zone):
				has_grass = true
				break
		if has_grass:
			break
	if not has_grass:
		return

	# Collect instances per biome (separate MultiMeshes for different meshes)
	var instances: Dictionary = {}  # biome_id → Array of {transform, custom_data}
	for biome_id in tuft_meshes:
		instances[biome_id] = []

	# Jittered grid scatter within chunk
	# Use the finest biome spacing to determine grid resolution, then
	# thin per-biome based on its target spacing
	var finest_spacing: float = 0.35
	var cols := int(CHUNK_SIZE / finest_spacing)

	for ix in cols:
		for iz in cols:
			var base_x := origin_x + (float(ix) + 0.5) * finest_spacing
			var base_z := origin_z + (float(iz) + 0.5) * finest_spacing

			# Jitter position (60% of spacing)
			var jx := base_x + _rng.randf_range(-0.21, 0.21)
			var jz := base_z + _rng.randf_range(-0.21, 0.21)

			var zone := _sample_zone(jx, jz)
			if not ZONE_TO_BIOME.has(zone):
				continue
			var biome_id: int = ZONE_TO_BIOME[zone]
			if not tuft_meshes.has(biome_id):
				continue

			# Density thinning: skip instances based on biome spacing
			var target_spacing: float = BIOME_SPACING.get(biome_id, 0.45)
			if target_spacing > finest_spacing:
				var keep_ratio := (finest_spacing * finest_spacing) / (target_spacing * target_spacing)
				if _rng.randf() > keep_ratio:
					continue

			# Canopy suppression
			var canopy := _sample_canopy(jx, jz)
			var suppress: float = BIOME_CANOPY_SUPPRESS.get(biome_id, 0.5)
			if canopy > 0.1 and _rng.randf() < canopy * suppress:
				continue

			# Terrain height
			var height := terrain.data.get_height(Vector3(jx, 0.0, jz))
			if is_nan(height) or height < -50.0:
				continue  # Outside terrain bounds

			# Random rotation and scale
			var rot := _rng.randf() * TAU
			var scale_factor := _rng.randf_range(0.7, 1.3)
			var t := Transform3D()
			t = t.scaled(Vector3(scale_factor, scale_factor, scale_factor))
			t = t.rotated(Vector3.UP, rot)
			t.origin = Vector3(jx, height - 0.01, jz)  # slight sink into ground

			# Custom data: zone_id, canopy, seed
			var custom := Color(
				float(zone) / 15.0,
				canopy,
				_rng.randf(),  # per-instance seed
				0.0
			)

			instances[biome_id].append({"transform": t, "custom": custom})

	# Build MultiMeshInstance3D per biome that has instances
	for biome_id in instances:
		var inst_array: Array = instances[biome_id]
		if inst_array.is_empty():
			continue

		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = tuft_meshes[biome_id]
		mm.instance_count = inst_array.size()

		for i in inst_array.size():
			mm.set_instance_transform(i, inst_array[i].transform)
			mm.set_instance_custom_data(i, inst_array[i].custom)

		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

		# Visibility range: tufts render between 15-55m from camera
		mmi.visibility_range_begin = VIS_BEGIN
		mmi.visibility_range_begin_margin = VIS_FADE
		mmi.visibility_range_end = VIS_END
		mmi.visibility_range_end_margin = VIS_FADE
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF

		# Render material
		if render_shader and tuft_textures.has(biome_id):
			var mat := ShaderMaterial.new()
			mat.shader = render_shader
			mat.set_shader_parameter("grass_albedo", tuft_textures[biome_id])
			mmi.material_override = mat

		add_child(mmi)
		_tufts_total += inst_array.size()

	_chunks_built += 1


func _sample_zone(wx: float, wz: float) -> int:
	"""Read zone ID from landuse image at world coordinates."""
	if not landuse_image:
		return -1
	var u := (wx + world_size * 0.5) / world_size
	var v := (wz + world_size * 0.5) / world_size
	var px := clampi(int(u * landuse_image.get_width()), 0, landuse_image.get_width() - 1)
	var py := clampi(int(v * landuse_image.get_height()), 0, landuse_image.get_height() - 1)
	return int(landuse_image.get_pixel(px, py).r * 255.0 + 0.5)


func _sample_canopy(wx: float, wz: float) -> float:
	"""Read canopy coverage (0-1) at world coordinates."""
	if not canopy_image:
		return 0.0
	var u := (wx + world_size * 0.5) / world_size
	var v := (wz + world_size * 0.5) / world_size
	var px := clampi(int(u * canopy_image.get_width()), 0, canopy_image.get_width() - 1)
	var py := clampi(int(v * canopy_image.get_height()), 0, canopy_image.get_height() - 1)
	return canopy_image.get_pixel(px, py).r

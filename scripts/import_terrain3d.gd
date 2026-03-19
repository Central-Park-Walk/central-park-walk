## Terrain3D heightmap importer — run headlessly:
##   godot --headless -s res://scripts/import_terrain3d.gd
##
## Reads heightmap.bin (8192x8192 float32) and imports into Terrain3D regions.
## Saves terrain data to res://data/terrain3d/.
extends SceneTree


const TERRAIN_DATA_DIR := "res://data/terrain3d"


func _init() -> void:
	# Give the engine a frame to initialize GDExtension
	await process_frame
	await process_frame

	print("=== Terrain3D Heightmap Import ===")

	# ── Load heightmap.bin ──────────────────────────────────────────────
	if not FileAccess.file_exists("res://heightmap.bin"):
		printerr("heightmap.bin not found")
		quit(1)
		return

	var fa := FileAccess.open("res://heightmap.bin", FileAccess.READ)
	var hm_width: int = fa.get_32()
	var hm_depth: int = fa.get_32()
	var world_size: float = fa.get_float()
	var _origin_h: float = fa.get_float()
	var buf: PackedByteArray = fa.get_buffer(hm_width * hm_depth * 4)
	fa.close()
	print("Heightmap: %d×%d  world=%.0fm  origin_h=%.2fm" % [hm_width, hm_depth, world_size, _origin_h])

	var cell_size: float = world_size / float(hm_width - 1)
	print("Cell size: %.4fm" % cell_size)

	# ── Create height Image (FORMAT_RF = single-channel float32) ──────
	var img := Image.create_from_data(hm_width, hm_depth, false, Image.FORMAT_RF, buf)
	print("Image created: %d×%d FORMAT_RF" % [img.get_width(), img.get_height()])

	# Quick sanity check — sample center pixel
	var cx := hm_width / 2
	var cz := hm_depth / 2
	var center_color: Color = img.get_pixel(cx, cz)
	print("Center pixel height (R channel): %.2f" % center_color.r)

	# ── Create Terrain3D ──────────────────────────────────────────────
	# Must add to tree FIRST so internal data objects are initialized,
	# then set region_size and vertex_spacing afterward.
	var terrain := Terrain3D.new()
	terrain.name = "Terrain3D"
	root.add_child(terrain)

	# Wait a frame for initialization to complete
	await process_frame

	# Now set properties — data object exists after add_child + init
	terrain.region_size = Terrain3D.SIZE_1024
	terrain.vertex_spacing = cell_size

	# Verify internal state
	print("Terrain3D region_size=%d  vertex_spacing=%.4f" % [
		terrain.region_size, terrain.vertex_spacing])

	var max_dim: int = 1024 * 32 / 2  # region_size * REGION_MAP_SIZE / 2
	print("Max dimension (vertices): %d  image size: %d  fits: %s" % [
		max_dim, hm_width, str(hm_width <= max_dim)])

	print("Region coverage: %.0fm  regions needed: %d×%d = %d" % [
		1024.0 * cell_size,
		ceili(float(hm_width) / 1024.0),
		ceili(float(hm_depth) / 1024.0),
		ceili(float(hm_width) / 1024.0) * ceili(float(hm_depth) / 1024.0)
	])

	# ── Import ────────────────────────────────────────────────────────
	# Centered import: position = -(image_size * vertex_spacing) / 2
	var half_world := float(hm_width) * cell_size * 0.5
	var import_pos := Vector3(-half_world, 0, -half_world)
	print("Import position: %s" % str(import_pos))
	print("Importing heightmap into Terrain3D regions...")

	var images: Array[Image] = []
	images.resize(Terrain3DRegion.TYPE_MAX)
	images[Terrain3DRegion.TYPE_HEIGHT] = img

	terrain.data.import_images(images, import_pos, 0.0, 1.0)

	# Verify
	var regions := terrain.data.get_regions_active()
	print("Active regions: %d" % regions.size())

	if regions.size() == 0:
		printerr("Import failed — no regions created")
		terrain.queue_free()
		quit(1)
		return

	# Sample some known locations to verify heights match
	var test_points := {
		"Origin": Vector3(0, 0, 0),
		"Literary Walk": Vector3(-600, 0, 1420),
		"Bethesda": Vector3(-480, 0, 1020),
		"North Woods": Vector3(600, 0, -1315),
	}
	for label in test_points:
		var pos: Vector3 = test_points[label]
		var h := terrain.data.get_height(pos)
		print("  %s (%.0f, %.0f): height = %.2f" % [label, pos.x, pos.z, h])

	# ── Save terrain data ─────────────────────────────────────────────
	DirAccess.make_dir_recursive_absolute(TERRAIN_DATA_DIR)
	terrain.data.save_directory(TERRAIN_DATA_DIR)
	print("Terrain data saved to %s" % TERRAIN_DATA_DIR)

	# Also save the Terrain3D resource files
	terrain.material.resource_path = TERRAIN_DATA_DIR + "/terrain_material.tres"
	ResourceSaver.save(terrain.material)
	terrain.assets.resource_path = TERRAIN_DATA_DIR + "/terrain_assets.tres"
	ResourceSaver.save(terrain.assets)
	print("Material and assets saved")

	# List saved files
	var dir := DirAccess.open(TERRAIN_DATA_DIR)
	if dir:
		dir.list_dir_begin()
		var fname := dir.get_next()
		while fname != "":
			if not dir.current_is_dir():
				var fsize := FileAccess.get_file_as_bytes(TERRAIN_DATA_DIR + "/" + fname).size()
				print("  %s (%.1f KB)" % [fname, fsize / 1024.0])
			fname = dir.get_next()

	print("=== Import complete ===")
	terrain.queue_free()
	quit()

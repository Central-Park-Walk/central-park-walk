## Terrain3D heightmap importer — run headlessly:
##   godot --headless -s res://scripts/import_terrain3d.gd
##
## Reads heightmap.bin (8192x8192 float32) at native LiDAR resolution (0.6104m)
## and imports into Terrain3D regions with autoshader control map.
extends SceneTree

const TERRAIN_DATA_DIR := "res://data/terrain3d"


func _init() -> void:
	await process_frame
	await process_frame

	print("=== Terrain3D Heightmap Import ===")

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

	var cell_size: float = world_size / float(hm_width - 1)
	print("Heightmap: %d×%d  world=%.0fm  cell=%.4fm" % [hm_width, hm_depth, world_size, cell_size])

	# Height image — native resolution
	var img := Image.create_from_data(hm_width, hm_depth, false, Image.FORMAT_RF, buf)
	print("Center height: %.2f" % img.get_pixel(hm_width / 2, hm_depth / 2).r)

	# Control map — autoshader bit everywhere (auto_slope handles grass vs rock)
	var ctrl_buf := PackedByteArray()
	ctrl_buf.resize(hm_width * hm_depth * 4)
	for i in hm_width * hm_depth:
		ctrl_buf[i * 4] = 0x02  # autoshader bit
	var ctrl_img := Image.create_from_data(hm_width, hm_depth, false, Image.FORMAT_RF, ctrl_buf)
	print("Control map: %d×%d (autoshader)" % [hm_width, hm_depth])

	# Create Terrain3D
	var terrain := Terrain3D.new()
	terrain.name = "Terrain3D"
	root.add_child(terrain)
	await process_frame

	terrain.region_size = Terrain3D.SIZE_1024
	terrain.vertex_spacing = cell_size

	print("Terrain3D: spacing=%.4f  regions=%d×%d=%d" % [
		cell_size,
		ceili(float(hm_width) / 1024.0),
		ceili(float(hm_depth) / 1024.0),
		ceili(float(hm_width) / 1024.0) * ceili(float(hm_depth) / 1024.0)])

	# Import
	var half_world := float(hm_width) * cell_size * 0.5
	var import_pos := Vector3(-half_world, 0, -half_world)

	var images: Array[Image] = []
	images.resize(Terrain3DRegion.TYPE_MAX)
	images[Terrain3DRegion.TYPE_HEIGHT] = img
	images[Terrain3DRegion.TYPE_CONTROL] = ctrl_img
	terrain.data.import_images(images, import_pos, 0.0, 1.0)

	var regions := terrain.data.get_regions_active()
	print("Active regions: %d" % regions.size())

	# Verify
	for label in {"Origin": Vector3(0,0,0), "Bethesda": Vector3(-480,0,1020), "North Woods": Vector3(600,0,-1315)}:
		var h := terrain.data.get_height({"Origin": Vector3(0,0,0), "Bethesda": Vector3(-480,0,1020), "North Woods": Vector3(600,0,-1315)}[label])
		print("  %s: %.2f" % [label, h])

	# Save
	DirAccess.make_dir_recursive_absolute(TERRAIN_DATA_DIR)
	terrain.data.save_directory(TERRAIN_DATA_DIR)
	print("Saved to %s" % TERRAIN_DATA_DIR)

	terrain.queue_free()
	quit()

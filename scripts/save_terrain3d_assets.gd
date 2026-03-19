## Save Terrain3D texture assets — run headlessly:
##   godot --headless -s res://scripts/save_terrain3d_assets.gd
##
## Loads source textures via pixel-copy into fresh Images (avoids format quirks
## that corrupt Terrain3D texture arrays). Saves as .tres resources.
extends SceneTree

const TEX_SIZE := 512


func _make_texture(src_path: String) -> ImageTexture:
	## Load image from file, pixel-copy into fresh RGBA8 Image.
	## This strips any format metadata that breaks Terrain3D texture arrays.
	var src := Image.load_from_file(src_path)
	if src == null:
		return null
	src.convert(Image.FORMAT_RGBA8)
	src.resize(TEX_SIZE, TEX_SIZE)
	var img := Image.create(TEX_SIZE, TEX_SIZE, false, Image.FORMAT_RGBA8)
	for y in TEX_SIZE:
		for x in TEX_SIZE:
			img.set_pixel(x, y, src.get_pixel(x, y))
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _init() -> void:
	await process_frame
	await process_frame

	print("=== Creating Terrain3D Assets (pixel-copy) ===")

	var assets := Terrain3DAssets.new()
	var material := Terrain3DMaterial.new()
	material.show_checkered = false
	material.world_background = Terrain3DMaterial.NONE
	material.auto_shader = true
	material.set_shader_param(&"auto_slope", 25)

	var tex_sets := [
		["Grass",  "res://textures/terrain3d/grass_albedo_height.png",
		           "res://textures/terrain3d/grass_normal_rough.png", 0.15],
		["Rock",   "res://textures/terrain3d/rock_albedo_height.png",
		           "res://textures/terrain3d/rock_normal_rough.png", 0.2],
		["Meadow", "res://textures/terrain3d/meadow_albedo_height.png",
		           "res://textures/terrain3d/meadow_normal_rough.png", 0.12],
		["Dirt",   "res://textures/terrain3d/dirt_albedo_height.png",
		           "res://textures/terrain3d/dirt_normal_rough.png", 0.15],
	]

	var count := 0
	for ts in tex_sets:
		var tname: String = ts[0]
		var alb_path: String = ts[1]
		var nrm_path: String = ts[2]
		var uv_scale: float = ts[3]

		var alb_tex := _make_texture(alb_path)
		if alb_tex == null:
			print("  SKIP %s — not found" % tname)
			continue

		var ta := Terrain3DTextureAsset.new()
		ta.name = tname
		ta.albedo_texture = alb_tex
		ta.uv_scale = uv_scale

		var nrm_tex := _make_texture(nrm_path)
		if nrm_tex:
			ta.normal_texture = nrm_tex

		var ta_path := "res://data/terrain3d/texture_%s.tres" % tname.to_lower()
		ta.resource_path = ta_path
		ResourceSaver.save(ta)
		assets.set_texture(count, ta)
		count += 1
		print("  %s: saved (uv_scale=%.2f)" % [tname, uv_scale])

	assets.resource_path = "res://data/terrain3d/terrain_assets.tres"
	ResourceSaver.save(assets)
	material.resource_path = "res://data/terrain3d/terrain_material.tres"
	ResourceSaver.save(material)
	print("Assets + material saved (%d textures)" % count)

	quit()

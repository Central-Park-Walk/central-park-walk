## Turf far-field texture baker — renders the RUNTIME turf-tile mesh (main.gd
## _make_turf_tile_mesh, the exact dome geometry/palette the player stands in)
## straight down into a seamless 2 m-period albedo texture. The far terrain then
## shows literally the same material as the near dome — tone/hue match by
## construction instead of by hand-calibration (the sward-colour whack-a-mole).
##
## Seamlessness: uses _make_turf_tile_mesh(periodic=true) — everything placed
## over exactly one s-period with edge-reaching geometry duplicated at the
## wrapped position, so one orthographic s x s crop tiles seamlessly at UNIFORM
## density. (A 3x3 grid of the runtime's oversized tiles was tried first: their
## 1-4x extent overlap bakes as a 2 m periodic density blotch.)
##
## Needs a renderer (not --headless) — run under Xvfb like all captures:
##   xvfb-run -a -s "-screen 0 1920x1080x24" \
##     "$GODOT" --path . --rendering-driver vulkan --audio-driver Dummy \
##     -s res://scripts/bake_turf.gd
## Then reimport so the runtime can load it:  "$GODOT" --path . --import --headless
extends SceneTree

const OUT_PATH := "res://textures/grass_turf_baked.png"
const RES := 2048     # output resolution: 2 m tile -> ~1 mm/texel
const SS := 2         # supersample then Lanczos-downscale (AA for thin blades)

func _init() -> void:
	await process_frame
	await process_frame

	print("=== Turf far-field texture bake ===")
	var MainC := load("res://main.gd")
	var m: Node = MainC.new()
	var tile: ArrayMesh = m._make_turf_tile_mesh(
		MainC.TURF_BLADES, MainC.TURF_THATCH, MainC.TURF_MAT_N, true)
	var s: float = MainC.TURF_TILE_SIZE
	m.free()
	print("tile mesh: %d verts, tile size %.1f m" % [
		tile.surface_get_array_len(0), s])

	var shader: Shader = load("res://shaders/turf_bake.gdshader")
	var mat := ShaderMaterial.new()
	mat.shader = shader
	var mat_tex: Texture2D = load("res://textures/grass_albedo.jpg")
	if mat_tex:
		mat.set_shader_parameter("mat_tex", mat_tex)
	else:
		printerr("grass_albedo.jpg missing — mat will bake flat")

	# Bake viewport: own world, linear tonemap (same convention as the impostor
	# baker — the PNG round-trips back to the same albedo when sampled as
	# source_color). Background = the mat backstop green in case of pinholes.
	var vp := SubViewport.new()
	vp.size = Vector2i(RES * SS, RES * SS)
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	vp.msaa_3d = Viewport.MSAA_4X
	var world := World3D.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.13, 0.28, 0.09)
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 1.0
	env.tonemap_white = 1.0
	world.environment = env
	vp.world_3d = world
	root.add_child(vp)

	var mi := MeshInstance3D.new()
	mi.mesh = tile
	mi.material_override = mat
	vp.add_child(mi)

	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = s                      # exactly one period -> seamless crop
	cam.near = 0.1
	cam.far = 10.0
	cam.position = Vector3(0.0, 3.0, 0.0)
	vp.add_child(cam)
	cam.look_at(Vector3.ZERO, Vector3.BACK)
	cam.current = true

	vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	if SS > 1:
		img.resize(RES, RES, Image.INTERPOLATE_LANCZOS)
	img.convert(Image.FORMAT_RGB8)
	img.save_png(ProjectSettings.globalize_path(OUT_PATH))
	print("saved %s (%dx%d)" % [OUT_PATH, RES, RES])
	quit(0)

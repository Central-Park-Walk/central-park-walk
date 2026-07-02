# water_reflection.gd
# Planar reflection for water bodies (docs/rendering.md water budget).
#
# A mirrored camera renders the scene above the water plane into this
# SubViewport; shaders/water.gdshader samples the result at (1-u, v) with
# wave-normal distortion. The mirror plane follows the water body nearest
# the player (per-body water_y from water_grids.bin).
#
# Godot has no oblique near-plane clipping, so below-plane geometry would
# occlude the mirrored view — the pond bed most of all. The reflection
# camera therefore culls to layer 1 only; terrain moves to layer 4 and
# water surfaces to layer 2 (set in main.gd / water_builder.gd). Trees,
# buildings, bridges and undergrowth — the content that matters in a
# reflection — stay on layer 1.
#
# Gated by --no-water-reflection. Roll back = pass the flag or skip setup.
extends SubViewport

var water_levels: Array = []   # {bb: Rect2 (XZ), wy: float} from park_loader
var main_camera: Camera3D      # player camera (set by main.gd)
var main_viewport: Viewport    # root window viewport (set by main.gd)
var reflect_cam: Camera3D
var _plane_y := 0.0
var _dump_frame := -1          # --refl-dump diagnostic: save viewport at this frame
var _frame := 0

const RES_DIVISOR := 3         # reflection at 1/3 window resolution
const BODY_MARGIN := 40.0      # bbox grow for "player is at this body" (m)
const SLEEP_DIST := 250.0      # no water within this range → stop rendering

var _body_dist := 0.0          # distance to nearest water body (m)


func _init() -> void:
	name = "WaterReflection"
	own_world_3d = false        # render the main scene, not a private world
	render_target_update_mode = SubViewport.UPDATE_ALWAYS
	positional_shadow_atlas_size = 1024
	msaa_3d = Viewport.MSAA_DISABLED
	screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	use_debanding = false


func setup(env: Environment) -> void:
	reflect_cam = Camera3D.new()
	reflect_cam.name = "ReflectCam"
	reflect_cam.cull_mask = 1   # layer 1 only — no water(2), no terrain(4), no weather(16)
	reflect_cam.current = true
	# Stripped environment: froxel fog and GI detail are invisible in a
	# distorted 1/3-res mirror but cost full per-view passes.
	var renv := env.duplicate() as Environment
	renv.volumetric_fog_enabled = false
	renv.sdfgi_enabled = false
	reflect_cam.environment = renv
	add_child(reflect_cam)


func _process(_dt: float) -> void:
	# NOTE: get_viewport() on a SubViewport returns the SubViewport itself,
	# so the main camera/viewport must be injected by main.gd.
	var main_cam := main_camera
	if main_cam == null or reflect_cam == null or main_viewport == null:
		return
	_frame += 1
	if _frame == _dump_frame:
		get_texture().get_image().save_png("res://tmp/refl_dump.png")
		print("WaterReflection: dump at frame %d — plane_y=%.2f cam=%s -> mirror=%s"
			% [_frame, _plane_y, main_cam.global_position, reflect_cam.global_position])
	# Match render size to the window at reduced resolution
	var target: Vector2i = Vector2i(main_viewport.get_visible_rect().size) / RES_DIVISOR
	if target.x > 0 and target.y > 0 and size != target:
		size = target

	_plane_y = _nearest_water_plane(main_cam.global_position)

	# Sleep when far from all water — the mirror renders every frame otherwise
	var want_mode := SubViewport.UPDATE_DISABLED if _body_dist > SLEEP_DIST \
		else SubViewport.UPDATE_ALWAYS
	if render_target_update_mode != want_mode:
		render_target_update_mode = want_mode
	if want_mode == SubViewport.UPDATE_DISABLED:
		return

	# Mirror the camera about the horizontal plane y = _plane_y.
	var t := main_cam.global_transform
	var origin := t.origin
	origin.y = 2.0 * _plane_y - origin.y
	var bx := t.basis.x; bx.y = -bx.y
	var by := t.basis.y; by.y = -by.y
	var bz := t.basis.z; bz.y = -bz.y
	# Reflection flips handedness; negate X to restore a valid camera basis.
	# The water shader compensates by sampling the texture x-flipped.
	reflect_cam.global_transform = Transform3D(Basis(-bx, by, bz), origin)
	reflect_cam.fov = main_cam.fov
	reflect_cam.near = main_cam.near
	reflect_cam.far = main_cam.far


func _nearest_water_plane(pos: Vector3) -> float:
	var best_y := _plane_y
	var best_d := INF
	var p := Vector2(pos.x, pos.z)
	for lvl in water_levels:
		var bb: Rect2 = lvl["bb"]
		var d := 0.0
		if not bb.grow(BODY_MARGIN).has_point(p):
			# distance from point to rect
			var cl := Vector2(clampf(p.x, bb.position.x, bb.end.x),
							  clampf(p.y, bb.position.y, bb.end.y))
			d = p.distance_to(cl)
		if d < best_d:
			best_d = d
			best_y = lvl["wy"]
			if d == 0.0:
				break
	_body_dist = best_d if best_d < INF else 1e9
	return best_y

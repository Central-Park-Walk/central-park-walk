extends Node3D
## Ambient life — opt-in quality-of-life liveliness for alpha testers, so the park
## doesn't feel deserted on long walks. Two independent systems:
##
##   • Fireflies — near-camera (<22 m) dusk/summer glow agents. Faithful recovery of
##     the disabled dd482f4 firefly system: ring-spawn around the player, drift toward
##     nearby trees, flash on a ~2 s pulse. They are MEANT to be close.
##
##   • Distant figures — vague humanoid billboards (walking, swimming, flying) kept in
##     a 55-175 m annulus around the player. They steer AWAY when approached so they
##     are never seen up close, are placed only on realistic surfaces (paths/lawn for
##     walkers via the world atlas, water for swimmers, air for flyers), and are gated
##     to realistic times of day / season. A shader near-fade is a hard backstop: any
##     figure that slips inside ~50 m dissolves rather than resolving into detail.
##
## This is the seed of the future wildlife / (eventually) multiplayer agent layer —
## every kind is just a config of one steering+billboard system.
##
## Toggle at runtime with L. Disable at launch with --no-life. Off respects the
## project's data-first default; testers turn it on.

const ALM := preload("res://almanac.gd")          # for true sunset time per date

# ---- external refs (assigned by main before setup()) ----
var player: CharacterBody3D
var camera: Camera3D
var terrain_height_fn: Callable                 # func(x, z) -> float
var park_loader: Node                           # for _atlas_surface(), water_bodies
var lamp_positions: PackedVector3Array = PackedVector3Array()

# ---- live environment state (pushed each frame by main) ----
var time_of_day: float = 12.0
var season_t: float = 1.5
var weather_mode: int = 0                        # Weather enum: 0 clear,1 rain,2 storm,3 snow,4 fog
var sun_elevation_deg: float = 45.0             # from ALM.sun_horizontal().x

var enabled: bool = true
var debug: bool = false                         # dev: ignore out-of-view spawn bias + print live counts

var _t: float = 0.0
var _dbg_t: float = 0.0
var _ff_intensity: float = 0.0
var _ff_vis: int = 0
var _rng := RandomNumberGenerator.new()
var _respawn_budget: int = 0
var _tones: Array = []

# ============================== FIREFLIES (near) =============================
const FF_COUNT := 220
const FF_RANGE := 30.0
# Max drift per frame (~1.8 m/s) — fireflies genuinely fly between flashes. The
# trail problem is handled by FF_FLASH_MOVE instead: a fast-moving bright additive
# sprite smears under TAA, so we hold each firefly nearly still *while it is lit* and
# let it relocate while dark (when the sprite is discarded and leaves no smear).
const FF_DRIFT := 0.03
# Fraction of normal drift allowed while a firefly is at full flash brightness. Low so
# the lit sprite barely moves (no "pixie dust" trail); raise toward 1.0 to bring the
# trails back for a magical / RPG setting later.
const FF_FLASH_MOVE := 0.12
var _ff: Array = []                              # agent dicts {pos, target, vel, phase, ...}
var _ff_mm: MultiMesh
var _ff_mat: ShaderMaterial
var _ff_tree_xz: PackedVector2Array = PackedVector2Array()

# ============================== DISTANT FIGURES =============================
enum { K_WALK, K_SWIM, K_FLY }
const FIG_MIN   := 55.0                          # hard minimum distance (m)
const FIG_SOFT  := 82.0                          # preferred min; evade ramps MIN..SOFT
const FIG_OUTER := 175.0                         # respawn beyond this
const LEASH     := 16.0                          # wander radius around an anchor
const WALK_COUNT := 96
const SWIM_COUNT := 28
const FLY_COUNT  := 18

var _walk: Array = []
var _swim: Array = []
var _fly:  Array = []
var _walk_mm: MultiMesh
var _swim_mm: MultiMesh
var _fly_mm:  MultiMesh
var _water: Array = []                           # [{c: Vector2, h: float}]


# ===========================================================================
# SETUP
# ===========================================================================
func setup() -> void:
	_rng.seed = 20260627
	_build_tones()
	_collect_tree_xz()
	_build_water_table()
	_build_fireflies()
	_build_figures()
	print("AmbientLife: %d fireflies (%d tree attractors), figures = %d walk / %d swim / %d fly" % [
		FF_COUNT, _ff_tree_xz.size(), WALK_COUNT, SWIM_COUNT, FLY_COUNT])


func _build_tones() -> void:
	# Diversity of people: skin tones + clothing colours. The silhouette is tinted as
	# one flat colour (it reads as a vague figure at distance), so this is the whole
	# population palette.
	_tones = [
		Color(0.86, 0.67, 0.52), Color(0.74, 0.56, 0.42), Color(0.55, 0.40, 0.30),
		Color(0.42, 0.30, 0.23), Color(0.95, 0.80, 0.66), Color(0.34, 0.24, 0.19),
		Color(0.20, 0.24, 0.34), Color(0.55, 0.18, 0.16), Color(0.22, 0.34, 0.24),
		Color(0.46, 0.46, 0.50), Color(0.82, 0.82, 0.84), Color(0.74, 0.60, 0.22),
		Color(0.32, 0.22, 0.40), Color(0.15, 0.16, 0.20), Color(0.60, 0.40, 0.30),
	]


func _collect_tree_xz() -> void:
	# Sample tree XZ positions (firefly attractors). Best-effort: scan the scene for
	# tree MultiMeshInstances; fireflies fall back to free wander if none are found.
	_ff_tree_xz = PackedVector2Array()
	var root := get_tree().get_root()
	_scan_trees(root, 0)


func _scan_trees(node: Node, depth: int) -> void:
	if depth > 6 or _ff_tree_xz.size() > 4000:
		return
	for child in node.get_children():
		if child is MultiMeshInstance3D:
			var n := child.name.to_lower()
			if (n.find("tr") != -1 or n.find("leaf") != -1 or n.find("impostor") != -1) \
					and n.find("grass") == -1 and n.find("ground") == -1 and n.find("flower") == -1:
				var mmi := child as MultiMeshInstance3D
				var origin := mmi.global_position
				var mm := mmi.multimesh
				if mm:
					var stride: int = maxi(1, mm.instance_count / 64)
					var i := 0
					while i < mm.instance_count:
						var o := mm.get_instance_transform(i).origin
						_ff_tree_xz.append(Vector2(o.x + origin.x, o.z + origin.z))
						i += stride
		_scan_trees(child, depth + 1)


func _build_water_table() -> void:
	_water = []
	if park_loader == null:
		return
	var bodies = park_loader.get("water_bodies")
	if bodies == null:
		return
	for b in bodies:
		var pts = b.get("points", [])
		if pts.is_empty():
			continue
		var cx := 0.0
		var cz := 0.0
		for p in pts:
			# park_loader stores each point as a [x, z] float array.
			cx += float(p[0])
			cz += float(p[1])
		var n := float(pts.size())
		_water.append({"c": Vector2(cx / n, cz / n), "h": float(b.get("height", 0.0))})


# ===========================================================================
# FIGURE CONSTRUCTION
# ===========================================================================
func _build_figures() -> void:
	var shader: Shader = load("res://shaders/ambient_figure.gdshader")
	var quad := _upright_quad()

	var walker_tex := _make_walker_tex()
	var swimmer_tex := _make_prone_swimmer_tex()
	var flyer_tex := _make_prone_flyer_tex()

	var walk_mat := ShaderMaterial.new()
	walk_mat.shader = shader
	walk_mat.set_shader_parameter("fig_tex", walker_tex)

	var swim_mat := ShaderMaterial.new()
	swim_mat.shader = shader
	swim_mat.set_shader_parameter("fig_tex", swimmer_tex)
	# Swimmers lie low on the water — fade a touch closer and barely bob.
	swim_mat.set_shader_parameter("fade_start", 50.0)
	swim_mat.set_shader_parameter("fade_end", 42.0)
	swim_mat.set_shader_parameter("bob_amp", 0.02)

	var fly_mat := ShaderMaterial.new()
	fly_mat.shader = shader
	fly_mat.set_shader_parameter("fig_tex", flyer_tex)

	_walk_mm = _make_mm(quad, WALK_COUNT)
	_swim_mm = _make_mm(quad, SWIM_COUNT)
	_fly_mm = _make_mm(quad, FLY_COUNT)

	_add_mmi(_walk_mm, walk_mat, "Figures_Walkers")
	_add_mmi(_swim_mm, swim_mat, "Figures_Swimmers")
	_add_mmi(_fly_mm, fly_mat, "Figures_Flyers")

	_walk = _make_agents(WALK_COUNT)
	_swim = _make_agents(SWIM_COUNT)
	_fly = _make_agents(FLY_COUNT)


func _make_agents(n: int) -> Array:
	var arr: Array = []
	for i in n:
		arr.append({
			"pos": Vector3.ZERO, "anchor": Vector3.ZERO,
			"heading": 0.0, "speed": 1.0, "phase": 0.0, "cadence": 3.0,
			"tone": Color.WHITE, "size": 1.7, "alt": 0.0, "active": false,
		})
	return arr


func _make_mm(mesh: Mesh, count: int) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = mesh
	mm.instance_count = count
	mm.visible_instance_count = 0
	return mm


func _add_mmi(mm: MultiMesh, mat: Material, nm: String) -> void:
	var mmi := MultiMeshInstance3D.new()
	mmi.name = nm
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# Instances carry world-space origins; keep the MMI from being frustum-culled.
	mmi.custom_aabb = AABB(Vector3(-10000, -500, -10000), Vector3(20000, 1000, 20000))
	add_child(mmi)


func _upright_quad() -> ArrayMesh:
	# Unit billboard quad: x in [-0.5, 0.5], y in [0, 1] (pivot at the feet/waterline).
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var verts := [Vector3(-0.5, 0, 0), Vector3(0.5, 0, 0), Vector3(0.5, 1, 0), Vector3(-0.5, 1, 0)]
	var uvs := [Vector2(0, 1), Vector2(1, 1), Vector2(1, 0), Vector2(0, 0)]
	var tris := [0, 1, 2, 0, 2, 3]
	for idx in tris:
		st.set_uv(uvs[idx])
		st.set_normal(Vector3(0, 0, 1))
		st.add_vertex(verts[idx])
	return st.commit()


# ----- procedural silhouettes (crosswalk-pictogram style) -----
func _make_walker_tex() -> ImageTexture:
	var im := Image.create(64, 128, true, Image.FORMAT_RGBA8)
	im.fill(Color(1, 1, 1, 0))
	_disc(im, 32, 18, 9)                          # head
	_seg(im, 32, 27, 32, 70, 8)                   # torso
	_seg(im, 32, 35, 20, 60, 3.5)                 # left arm
	_seg(im, 32, 35, 45, 58, 3.5)                 # right arm (mid-stride asymmetry)
	_seg(im, 32, 70, 22, 119, 5)                  # left leg (splayed walk stance)
	_seg(im, 32, 70, 43, 116, 5)                  # right leg
	im.generate_mipmaps()
	return ImageTexture.create_from_image(im)


func _make_prone_swimmer_tex() -> ImageTexture:
	# Horizontal (prone) swimmer lying on the water: head, extended body, trailing
	# legs, one arm reaching forward over the head — a low sliver, not a standing bust.
	var im := Image.create(128, 48, true, Image.FORMAT_RGBA8)
	im.fill(Color(1, 1, 1, 0))
	_disc(im, 24, 24, 8)                          # head (forward / left)
	_seg(im, 30, 24, 92, 24, 8)                   # torso + hips, horizontal
	_seg(im, 92, 24, 121, 18, 3.5)               # trailing leg
	_seg(im, 92, 24, 121, 30, 3.5)               # trailing leg
	_seg(im, 40, 21, 12, 12, 3.0)                # forward arm (stroke over head)
	im.generate_mipmaps()
	return ImageTexture.create_from_image(im)


func _make_prone_flyer_tex() -> ImageTexture:
	# Horizontal soaring figure: head forward, body, trailing legs, arms swept out to
	# the sides — reads as a person flying/gliding, not standing upright in mid-air.
	var im := Image.create(128, 64, true, Image.FORMAT_RGBA8)
	im.fill(Color(1, 1, 1, 0))
	_disc(im, 24, 32, 8)                          # head (forward / left)
	_seg(im, 30, 32, 92, 32, 8)                   # body, horizontal
	_seg(im, 92, 32, 121, 26, 4.0)               # trailing leg
	_seg(im, 92, 32, 121, 38, 4.0)               # trailing leg
	_seg(im, 46, 32, 30, 10, 3.5)                # arm swept up / out
	_seg(im, 46, 32, 30, 54, 3.5)                # arm swept down / out
	im.generate_mipmaps()
	return ImageTexture.create_from_image(im)


func _disc(im: Image, cx: int, cy: int, r: float) -> void:
	var r2 := r * r
	for y in range(maxi(0, cy - int(r) - 1), mini(im.get_height(), cy + int(r) + 2)):
		for x in range(maxi(0, cx - int(r) - 1), mini(im.get_width(), cx + int(r) + 2)):
			var dx := float(x - cx)
			var dy := float(y - cy)
			if dx * dx + dy * dy <= r2:
				im.set_pixel(x, y, Color(1, 1, 1, 1))


func _seg(im: Image, x0: int, y0: int, x1: int, y1: int, half: float) -> void:
	# Fill pixels within `half` of the segment (a capsule limb).
	var minx := maxi(0, mini(x0, x1) - int(half) - 1)
	var maxx := mini(im.get_width(), maxi(x0, x1) + int(half) + 2)
	var miny := maxi(0, mini(y0, y1) - int(half) - 1)
	var maxy := mini(im.get_height(), maxi(y0, y1) + int(half) + 2)
	var ax := float(x0)
	var ay := float(y0)
	var bx := float(x1 - x0)
	var by := float(y1 - y0)
	var len2 := bx * bx + by * by
	var h2 := half * half
	for y in range(miny, maxy):
		for x in range(minx, maxx):
			var px := float(x) - ax
			var py := float(y) - ay
			var t := 0.0 if len2 < 0.001 else clampf((px * bx + py * by) / len2, 0.0, 1.0)
			var dx := px - bx * t
			var dy := py - by * t
			if dx * dx + dy * dy <= h2:
				im.set_pixel(x, y, Color(1, 1, 1, 1))


# ===========================================================================
# PER-FRAME UPDATE
# ===========================================================================
func update(delta: float) -> void:
	if player == null:
		return
	if not enabled:
		return
	_t += delta
	_respawn_budget = 400 if debug else 5

	# Firefly display window (Photinus pyralis, the common eastern firefly): begins
	# ~20 min before sunset, peaks through the first hour of twilight, thins out and
	# is gone by ~2.8 h after sunset (before midnight) — NOT an all-night glow.
	# Emergence late May–early Sept, peak June–July. Off in rain/snow.
	var bad_weather: bool = weather_mode == 1 or weather_mode == 2 or weather_mode == 3
	var sunset: float = ALM.sun_events(season_t).sunset
	var tphase := time_of_day - sunset             # hours after sunset
	if tphase < -6.0:
		tphase += 24.0                             # wrap post-midnight into "after sunset"
	var dusk_in := smoothstep(-0.4, 0.4, tphase)   # fade in from 24 min before sunset
	var dusk_out := 1.0 - smoothstep(1.2, 2.8, tphase)  # thin out, gone ~2.8 h after
	var season_w := smoothstep(0.8, 1.0, season_t) * (1.0 - smoothstep(1.8, 2.2, season_t))
	var ff_intensity := dusk_in * dusk_out * season_w
	if bad_weather:
		ff_intensity = 0.0
	_ff_intensity = ff_intensity
	_update_fireflies(delta, ff_intensity)

	# People: daylight; swimmers only warm summer midday; flyers day + twilight.
	var walk_active: bool = sun_elevation_deg > 1.0
	var swim_active: bool = sun_elevation_deg > 18.0 and season_t >= 1.0 and season_t <= 2.1
	var fly_active: bool = sun_elevation_deg > -6.0
	_update_figs(_walk, _walk_mm, K_WALK, walk_active, delta)
	_update_figs(_swim, _swim_mm, K_SWIM, swim_active, delta)
	_update_figs(_fly, _fly_mm, K_FLY, fly_active, delta)

	if debug:
		_dbg_t += delta
		if _dbg_t > 1.0:
			_dbg_t = 0.0
			print("AmbientLife[dbg]: walk=%d swim=%d fly=%d  firefly=%d (intensity %.2f)  time=%.1f season=%.2f" % [
				_walk_mm.visible_instance_count, _swim_mm.visible_instance_count,
				_fly_mm.visible_instance_count, _ff_vis, _ff_intensity, time_of_day, season_t])


func set_enabled(v: bool) -> void:
	enabled = v
	for c in get_children():
		if c is MultiMeshInstance3D:
			c.visible = v


# ===========================================================================
# DISTANT FIGURES
# ===========================================================================
func _update_figs(arr: Array, mm: MultiMesh, kind: int, active: bool, delta: float) -> void:
	if not active:
		if mm.visible_instance_count != 0:
			mm.visible_instance_count = 0
		for a in arr:
			a["active"] = false
		return

	var ppos := player.global_position
	var px := ppos.x
	var pz := ppos.z
	# Walkers stand upright; swimmers and flyers lie down (wide, low silhouette).
	var wf := 0.5
	var hf := 1.0
	if kind == K_SWIM:
		wf = 1.0
		hf = 0.32
	elif kind == K_FLY:
		wf = 1.0
		hf = 0.42
	var vis := 0
	for a in arr:
		if not a["active"]:
			if _respawn_budget > 0:
				_respawn_budget -= 1
				_spawn_agent(a, kind)
			if not a["active"]:
				continue
		if not _step_agent(a, kind, px, pz, delta):
			continue
		var s: float = a["size"]
		var basis := Basis(Vector3(wf * s, 0, 0), Vector3(0, hf * s, 0), Vector3(0, 0, 1))
		mm.set_instance_transform(vis, Transform3D(basis, a["pos"]))
		var tone: Color = a["tone"]
		mm.set_instance_custom_data(vis, Color(tone.r, tone.g, tone.b, a["phase"]))
		vis += 1
	mm.visible_instance_count = vis


func _step_agent(a: Dictionary, kind: int, px: float, pz: float, delta: float) -> bool:
	var pos: Vector3 = a["pos"]
	var heading: float = a["heading"]

	# lazy wander
	heading += _rng.randf_range(-1.0, 1.0) * delta * 0.8

	# leash: keep walkers/swimmers loitering near their anchor
	if kind != K_FLY:
		var anchor: Vector3 = a["anchor"]
		var dax := anchor.x - pos.x
		var daz := anchor.z - pos.z
		if dax * dax + daz * daz > LEASH * LEASH:
			heading = lerp_angle(heading, atan2(daz, dax), 0.06)

	# evade the player — steer away, walk faster, as they get close
	var ax := pos.x - px
	var az := pos.z - pz
	var d := sqrt(ax * ax + az * az)
	var speed_mult := 1.0
	if d < FIG_SOFT and d > 0.001:
		var urg := clampf((FIG_SOFT - d) / (FIG_SOFT - FIG_MIN), 0.0, 1.3)
		heading = lerp_angle(heading, atan2(az, ax), clampf(0.06 + urg * 0.12, 0.0, 0.5))
		speed_mult = 1.0 + urg * 0.5                  # drift away calmly, don't scurry

	# Speed jitter so they don't glide like rollerskaters: a per-stride surge
	# (faster mid-step, slower at foot-plant) plus a slow per-agent amble drift that
	# occasionally eases them to a near-stop. Flyers get only the smooth amble.
	var ph: float = a["phase"]
	var gait := 1.0 + 0.20 * sin(_t * 0.45 + ph * 17.0)
	if kind != K_FLY:
		gait += 0.34 * sin(_t * a["cadence"] + ph * TAU)
	gait = maxf(gait, 0.12)

	# advance, respecting valid surface
	var dir := Vector2(cos(heading), sin(heading))
	var step: float = a["speed"] * speed_mult * gait * delta
	var nx := pos.x + dir.x * step
	var nz := pos.z + dir.y * step
	if _valid(kind, nx, nz):
		pos.x = nx
		pos.z = nz
	else:
		heading += PI * 0.6 + _rng.randf_range(-0.6, 0.6)

	# hard minimum-distance clamp (backstop for the evade steering)
	var bx := pos.x - px
	var bz := pos.z - pz
	var bd := sqrt(bx * bx + bz * bz)
	if bd < FIG_MIN and bd > 0.01:
		pos.x = px + bx / bd * FIG_MIN
		pos.z = pz + bz / bd * FIG_MIN
		bd = FIG_MIN

	if bd > FIG_OUTER:
		a["active"] = false
		return false

	# ground / water / air height
	match kind:
		K_FLY:
			pos.y = terrain_height_fn.call(pos.x, pos.z) + a["alt"] \
				+ sin(_t * 0.5 + a["phase"] * TAU) * 0.8
		K_SWIM:
			pos.y = _water_height(pos.x, pos.z)
		_:
			pos.y = terrain_height_fn.call(pos.x, pos.z)

	a["pos"] = pos
	a["heading"] = heading
	return true


func _spawn_agent(a: Dictionary, kind: int) -> void:
	var ppos := player.global_position
	for attempt in 40:
		var ang := _rng.randf() * TAU
		var rad := _rng.randf_range(FIG_SOFT, FIG_OUTER)
		var x := ppos.x + cos(ang) * rad
		var z := ppos.z + sin(ang) * rad
		if not _valid(kind, x, z):
			continue
		# prefer spawning out of view so figures don't blink into existence ahead of you
		if not debug and attempt < 28 and camera and camera.is_position_in_frustum(Vector3(x, _base_y(kind, x, z) + 1.0, z)):
			continue
		var size := _pick_size(kind)
		var alt := _rng.randf_range(9.0, 26.0) if kind == K_FLY else 0.0
		a["anchor"] = Vector3(x, 0, z)
		a["heading"] = _rng.randf() * TAU
		a["speed"] = _pick_speed(kind)
		a["phase"] = _rng.randf()
		a["cadence"] = _rng.randf_range(1.5, 2.5)     # per-agent stride frequency (slow walk)
		a["tone"] = _tones[_rng.randi() % _tones.size()]
		a["size"] = size
		a["alt"] = alt
		a["pos"] = Vector3(x, _base_y(kind, x, z) + (alt if kind == K_FLY else 0.0), z)
		a["active"] = true
		return
	a["active"] = false                           # nowhere valid nearby (e.g. no water)


func _valid(kind: int, x: float, z: float) -> bool:
	var s := _surface(x, z)
	match kind:
		K_WALK:
			return s == 1 or s == 2 or s == 3      # lawn or path
		K_SWIM:
			return s == 4                          # water
		_:
			return s != 5                          # flyers: anywhere but inside a building


func _surface(x: float, z: float) -> int:
	if park_loader and park_loader.has_method("_atlas_surface"):
		return park_loader._atlas_surface(x, z)
	return 1                                       # assume open grass if no atlas


func _base_y(kind: int, x: float, z: float) -> float:
	if kind == K_SWIM:
		return _water_height(x, z)
	return terrain_height_fn.call(x, z)


func _water_height(x: float, z: float) -> float:
	if _water.is_empty():
		return terrain_height_fn.call(x, z) + 0.05
	var best_h := 0.0
	var best_d := INF
	var p := Vector2(x, z)
	for w in _water:
		var dd: float = p.distance_squared_to(w["c"])
		if dd < best_d:
			best_d = dd
			best_h = w["h"]
	return best_h


func _pick_size(kind: int) -> float:
	match kind:
		K_SWIM:
			return _rng.randf_range(1.3, 1.7)         # prone body length
		K_FLY:
			return _rng.randf_range(1.5, 2.0)         # prone body length
		_:
			return _rng.randf_range(1.55, 1.95)       # upright height


func _pick_speed(kind: int) -> float:
	# Deliberately slow: tiny figures drifting slowly across a vast green read as
	# FAR away, which is the whole point — they exist to convey the park's true size.
	match kind:
		K_SWIM:
			return _rng.randf_range(0.07, 0.20)       # barely-moving, idle paddling
		K_FLY:
			return _rng.randf_range(0.8, 2.0)         # slow gliding drift
		_:
			return _rng.randf_range(0.28, 0.72)       # slow stroll / amble


# ===========================================================================
# FIREFLIES (recovered from dd482f4) — near-camera, dusk/summer
# ===========================================================================
func _build_fireflies() -> void:
	# soft round glow texture
	var oval := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	for py in 32:
		for px2 in 32:
			var u := (float(px2) - 15.5) / 15.5
			var v := (float(py) - 15.5) / 15.5
			var dd := u * u + v * v
			var al := clampf(1.0 - dd * 1.5, 0.0, 1.0)
			al = al * al
			oval.set_pixel(px2, py, Color(1, 1, 1, al))
	oval.generate_mipmaps()
	var tex := ImageTexture.create_from_image(oval)

	_ff_mat = ShaderMaterial.new()
	_ff_mat.shader = load("res://shaders/ambient_firefly.gdshader")
	_ff_mat.set_shader_parameter("ff_tex", tex)
	_ff_mat.set_shader_parameter("ff_bright", 1.0)

	var qm := QuadMesh.new()
	qm.size = Vector2(1.0, 1.0)                   # unit; scaled per-instance (~2-3 cm spark)

	_ff_mm = MultiMesh.new()
	_ff_mm.transform_format = MultiMesh.TRANSFORM_3D
	_ff_mm.use_custom_data = true
	_ff_mm.mesh = qm
	_ff_mm.instance_count = FF_COUNT
	_ff_mm.visible_instance_count = 0

	var mmi := MultiMeshInstance3D.new()
	mmi.name = "Fireflies"
	mmi.multimesh = _ff_mm
	mmi.material_override = _ff_mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.custom_aabb = AABB(Vector3(-10000, -500, -10000), Vector3(20000, 1000, 20000))
	add_child(mmi)

	for i in FF_COUNT:
		_ff.append({
			"pos": Vector3.ZERO, "target": Vector3.ZERO, "vel": Vector3.ZERO,
			"phase": _rng.randf(),
			"period": _rng.randf_range(4.0, 5.5),
			"thresh": _rng.randf(),               # joins the swarm once intensity exceeds this
			"size": _rng.randf_range(0.018, 0.034),
			"spawned": false,
		})


func _find_near_tree(pos: Vector3) -> Vector3:
	if _ff_tree_xz.is_empty():
		return pos + Vector3(_rng.randf_range(-5, 5), _rng.randf_range(-0.3, 0.5), _rng.randf_range(-5, 5))
	var px := pos.x
	var pz := pos.z
	var candidates: Array = []
	for t in _ff_tree_xz:
		var dx := t.x - px
		var dz := t.y - pz
		if dx * dx + dz * dz < 625.0:              # within 25 m
			candidates.append(t)
			if candidates.size() >= 20:
				break
	if candidates.is_empty():
		return pos + Vector3(_rng.randf_range(-5, 5), _rng.randf_range(-0.3, 0.5), _rng.randf_range(-5, 5))
	var pick: Vector2 = candidates[_rng.randi() % candidates.size()]
	return Vector3(
		pick.x + _rng.randf_range(-2.5, 2.5),
		terrain_height_fn.call(pick.x, pick.y) + _rng.randf_range(0.3, 1.5),
		pick.y + _rng.randf_range(-2.5, 2.5))


func _update_fireflies(delta: float, intensity: float) -> void:
	# Edge-dim the whole swarm at the start/end of the display window.
	_ff_mat.set_shader_parameter("ff_bright", lerpf(0.55, 1.0, clampf(intensity, 0.0, 1.0)))
	var ppos := player.global_position
	var vis := 0
	for ff in _ff:
		# Each firefly joins the swarm once the display intensity clears its random
		# threshold, so the swarm thickens into peak twilight and thins at the edges.
		if float(ff["thresh"]) >= intensity:
			ff["spawned"] = false
			continue

		var pos: Vector3 = ff["pos"]
		# spawn / respawn in a ring around the player (they're meant to stay near)
		if not ff["spawned"] or pos.distance_to(ppos) > FF_RANGE:
			var angle := _rng.randf() * TAU
			var radius := _rng.randf_range(3.0, 18.0)
			var sx := ppos.x + cos(angle) * radius
			var sz := ppos.z + sin(angle) * radius
			pos = Vector3(sx, float(terrain_height_fn.call(sx, sz)) + _rng.randf_range(0.4, 1.6), sz)
			ff["target"] = _find_near_tree(pos)
			ff["vel"] = Vector3.ZERO
			ff["spawned"] = true

		var tgt: Vector3 = ff["target"]
		var to_target := tgt - pos
		var dist_to_target := to_target.length()
		if dist_to_target < 1.5:
			ff["target"] = _find_near_tree(ppos)
		elif dist_to_target > 0.01:
			ff["vel"] = ff["vel"] + to_target.normalized() * 0.04 * delta

		var to_pp := ppos - pos
		var pp_dist := to_pp.length()
		if pp_dist > 5.0:
			ff["vel"] = ff["vel"] + to_pp.normalized() * 0.03 * delta * clampf((pp_dist - 5.0) * 0.2, 0.0, 1.0)

		var above: float = pos.y - float(terrain_height_fn.call(pos.x, pos.z))
		var vel: Vector3 = ff["vel"]

		# gently keep clear of the player within ~3 m (no hard snap)
		var pd2 := pp_dist * pp_dist
		if pd2 < 9.0 and pd2 > 0.01:
			vel += (-to_pp) / pp_dist * (0.3 / pd2) * delta

		if above < 0.3:
			vel.y += 0.3 * delta
		elif above > 1.8:
			vel.y -= 0.5 * delta

		vel *= 0.85
		var spd := vel.length()
		if spd > FF_DRIFT:
			vel = vel / spd * FF_DRIFT
		vel += Vector3(_rng.randf_range(-0.04, 0.04), _rng.randf_range(-0.06, 0.06), _rng.randf_range(-0.04, 0.04)) * delta
		ff["vel"] = vel

		# Flash pulse (computed here, on the CPU, so it matches what the shader reads):
		# ~1.8 s glow within the firefly's period. We hold the firefly nearly still while
		# it is lit (move_scale -> FF_FLASH_MOVE) so the bright sprite doesn't smear under
		# TAA, and let it fly freely while dark — that's the trail-free "flying" look.
		var period: float = ff["period"]
		var ct := fmod(_t + float(ff["phase"]) * period, maxf(period, 0.5))
		var glow := sin(ct / 1.8 * PI) if ct < 1.8 else 0.0
		var move_scale := lerpf(1.0, FF_FLASH_MOVE, clampf(glow, 0.0, 1.0))
		pos += vel * move_scale
		ff["pos"] = pos

		# write instance: transform (scaled spark) + flash brightness for the shader
		var sz2: float = ff["size"]
		_ff_mm.set_instance_transform(vis, Transform3D(Basis().scaled(Vector3(sz2, sz2, sz2)), pos))
		_ff_mm.set_instance_custom_data(vis, Color(glow, 0.0, 0.0, 0.0))
		vis += 1
	_ff_mm.visible_instance_count = vis
	_ff_vis = vis

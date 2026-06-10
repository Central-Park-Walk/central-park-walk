extends Node3D

const TourData = preload("res://tour_data.gd")

# ---------------------------------------------------------------------------
# Geo-projection constants – must match convert_to_godot.py
#   origin  = centre of Central Park
#   +X = East,  −Z = North
# ---------------------------------------------------------------------------
const REF_LAT            := 40.7829
const REF_LON            := -73.9654
const METRES_PER_DEG_LAT := 110_540.0
const METRES_PER_DEG_LON := 84_264.0   # 111320 × cos(40.7829°)

# Heightmap (loaded once, shared for height queries + path shader snapping)
var _hm_data:          PackedFloat32Array = PackedFloat32Array()
var _hm_width:         int     = 0
var _hm_depth:         int     = 0
var _hm_world_size:    float   = 5000.0

var _player:        CharacterBody3D
var _hud = null     # HudManager instance (hud_manager.gd)

# ---------------------------------------------------------------------------
# Day/night cycle
# ---------------------------------------------------------------------------
var _day_night: Node  # DayNightCycle instance
var _time_of_day: float = 16.0        # start at 4 PM
var _user_gamma: float = 1.0          # user brightness: , = darker, . = brighter
var _time_speed: float  = 0.001      # game-hours per real-second (~400 min full cycle)
var _time_speed_idx: int = 0
const TIME_SPEEDS: Array = [0.001, 0.01, 0.1, 0.0]
const TIME_SPEED_NAMES: Array = ["1x", "10x", "100x", "Paused"]

var _env: Environment
var _sky_mat: ShaderMaterial
var _vol_sky = null  # clayjohn volumetric cloud sky (if loaded)
var _sun: DirectionalLight3D
var _lamp_emission: float = 0.0  # cached for SpotLight3D pool
var _terrain3d: Terrain3D

# Dynamic lamppost lighting — pool of SpotLight3D nodes that follow player
var _lamp_lights: Array = []  # Array of SpotLight3D
var _lamp_positions: PackedVector3Array = PackedVector3Array()

# Cached node references (avoid repeated get_node/find_children)
var _player_head: Node3D
var _player_camera: Camera3D
var _cached_label3d_nodes: Array = []
var _lamp_light_timer: float = 0.0
var _lightning_timer: float = 0.0
var _lightning_flash: float = 0.0     # 0-1 current flash intensity (decays rapidly)
var _lightning_next: float = 5.0      # seconds until next flash
const LAMP_LIGHT_COUNT := 48
const LAMP_LIGHT_RANGE := 22.0
const LAMP_LIGHT_UPDATE_INTERVAL := 0.5  # seconds between position updates

# Per-subsystem timing (microseconds, smoothed) — displayed in F9 perf overlay
var _prof_lamps_us: float = 0.0
var _prof_wind_us: float = 0.0
var _prof_weather_us: float = 0.0
var _prof_undergrowth_us: float = 0.0
var _prof_ground_cover_us: float = 0.0
var _prof_daynight_us: float = 0.0
var _prof_hud_us: float = 0.0
var _prof_misc_us: float = 0.0       # un-bucketed bits of main._process (lightning, time advance, dist overlay)
var _prof_player_phy_us: float = 0.0  # mirrored from player._physics_process
const PROF_SMOOTH := 0.9  # EMA smoothing factor (higher = more stable)

var _audio_manager = null  # ambient sound (wind, city, water, footsteps)

var _terrain_only := false
# Weather state — enum for fast comparison in hot paths
enum Weather { CLEAR, RAIN, THUNDERSTORM, SNOW, FOG }
const WEATHER_NAMES: Array = ["clear", "rain", "thunderstorm", "snow", "fog"]
var _weather_mgr: Node  # WeatherManager instance
var _weather_mode: int = Weather.CLEAR

# Wind system — extracted to wind_system.gd
var _wind_system: Node  # WindSystem instance
var _wind_vec := Vector2.ZERO  # cached for convenience (read from _wind_system each frame)

# Snow accumulation
var _snow_cover := 0.0          # 0-1, ramps up during snow weather
# Rain wetness — ground darkens + specular increases
var _rain_wetness := 0.0        # 0-1, ramps up during rain

# Seasons — 0.0=spring equinox, 1.0=summer solstice, 2.0=autumn equinox, 3.0=winter solstice
var _season_t := 1.5            # default mid-summer (matches current look)
var _season_speed := 0.0        # season-units per real-second (0 = manual only)
const SEASON_PRESETS: Dictionary = {
	"spring": 0.5, "summer": 1.5, "autumn": 2.5, "fall": 2.5, "winter": 3.5,
}


# --time name-to-hour mapping
const TIME_PRESETS: Dictionary = {
	"dawn": 5.5, "morning": 8.0, "noon": 12.0,
	"golden_hour": 17.5, "dusk": 19.5, "night": 22.0,
}
const LANDUSE_TYPE_TO_ID: Dictionary = {
	"garden": 1, "grass": 2, "pitch": 3, "playground": 4,
	"nature_reserve": 5, "dog_park": 6, "sports": 7, "pool": 8, "track": 9,
	"wood": 10, "forest": 11,
}

var _cli_pos := Vector3.ZERO  # --pos x,z  or --pos x,z,yaw  or --pos x,z,yaw,height
var _cli_pos_set := false
var _cli_height := 1.55  # default eye height above terrain (~5'1")
var _cli_pitch := 0.0   # --pitch degrees (negative = look down)

# --walk bot: auto-walk in a direction, capturing screenshots at intervals.
# Usage: --walk --pos=x,z,yaw --walk-duration=30 --walk-interval=1.0 --walk-speed=1.2
var _tree_species_filter: Array = []  # --tree-species=oak,maple → only place those
var _walk_bot := false
var _walk_bot_duration := 30.0   # seconds of walking
var _walk_bot_interval := 1.0    # seconds between screenshots
var _walk_bot_speed := 1.2       # m/s (default = Walk pace)
var _walk_bot_dir := "walk_captures"  # output directory
var _walk_bot_timer := 0.0
var _walk_bot_shot_timer := 0.0
var _walk_bot_settle := 8.0      # seconds to let scene load before walking
var _walk_bot_settled := false
var _walk_bot_frame := 0
var _walk_bot_started := false


func _parse_cli_args() -> void:
	## Parse all --key and --key=value CLI arguments, setting member variables.
	var cli_time := ""
	for i in OS.get_cmdline_user_args().size():
		var arg: String = OS.get_cmdline_user_args()[i]
		var key := arg.split("=")[0]
		var has_eq := arg.contains("=")
		var eq_val := arg.substr(arg.find("=") + 1) if has_eq else ""
		var next_val := OS.get_cmdline_user_args()[i + 1] if (i + 1 < OS.get_cmdline_user_args().size()) else ""
		var val := eq_val if has_eq else next_val
		if arg == "--terrain-only":
			_terrain_only = true
		elif key == "--time" and val != "":
			cli_time = val
		elif key == "--weather" and val != "":
			var widx := WEATHER_NAMES.find(val)
			if widx >= 0:
				_weather_mode = widx
			else:
				print("Unknown --weather '%s'. Options: %s" % [val, ", ".join(WEATHER_NAMES)])
		elif key == "--pos" and val != "":
			var parts := val.split(",")
			if parts.size() >= 2:
				_cli_pos.x = float(parts[0])
				_cli_pos.z = float(parts[1])
				if parts.size() >= 3:
					_cli_pos.y = float(parts[2])  # yaw
				if parts.size() >= 4:
					_cli_height = float(parts[3])  # height above terrain
				_cli_pos_set = true
		elif key == "--pitch" and val != "":
			_cli_pitch = float(val)
		elif key == "--tree-species" and val != "":
			_tree_species_filter = Array(val.split(","))
			print("Tree species filter: %s" % str(_tree_species_filter))
		elif arg == "--walk":
			_walk_bot = true
		elif key == "--walk-duration" and val != "":
			_walk_bot_duration = float(val)
		elif key == "--walk-interval" and val != "":
			_walk_bot_interval = float(val)
		elif key == "--walk-speed" and val != "":
			_walk_bot_speed = float(val)
		elif key == "--walk-dir" and val != "":
			_walk_bot_dir = val
		elif key == "--walk-settle" and val != "":
			_walk_bot_settle = float(val)
		elif key == "--season" and val != "":
			var s_val: String = val
			if SEASON_PRESETS.has(s_val):
				_season_t = SEASON_PRESETS[s_val]
				print("Season: %s (%.1f)" % [s_val, _season_t])
			elif s_val.is_valid_float():
				_season_t = clampf(float(s_val), 0.0, 4.0)
				print("Season: %.1f" % _season_t)
			else:
				print("Unknown --season '%s'. Options: spring summer autumn fall winter (or 0.0-4.0)" % s_val)
		elif key == "--diag-hide" and val != "":
			_diag_hide = Array(val.split(","))
			print("[DIAG] CLI hide list: %s" % str(_diag_hide))
		elif key == "--shadow-dist" and val != "":
			_cli_shadow_dist = float(val)
		elif key == "--shadow-size" and val != "":
			_cli_shadow_size = int(val)
		elif key == "--shadow-filter" and val != "":
			_cli_shadow_filter = int(val)
		elif arg == "--shadow-census":
			_diag_shadow_census = true
		elif arg == "--screenshot":
			_auto_screenshot = true
	# Legacy trigger: sniffing --quit-after stopped working when the engine
	# began stripping recognized flags from OS.get_cmdline_args() (found
	# 2026-06-10 on 4.6.1 — loop never matches). Use `-- --screenshot`.
	for earg in OS.get_cmdline_args():
		if earg.begins_with("--quit-after"):
			_auto_screenshot = true
			break
	if cli_time != "":
		if TIME_PRESETS.has(cli_time):
			_time_of_day = TIME_PRESETS[cli_time]
			_time_speed = 0.0  # freeze clock
			_time_speed_idx = 3  # "Paused"
			print("Time locked: %s (%.1fh)" % [cli_time, _time_of_day])
		elif cli_time.is_valid_float():
			_time_of_day = clampf(float(cli_time), 0.0, 23.99)
			_time_speed = 0.0
			_time_speed_idx = 3
			print("Time locked: %.1fh" % _time_of_day)
		else:
			print("Unknown --time '%s'. Options: dawn morning noon golden_hour dusk night (or 0-24)" % cli_time)
	if _weather_mode != Weather.CLEAR:
		print("Weather: %s" % WEATHER_NAMES[_weather_mode])


func _ready() -> void:
	_parse_cli_args()
	# Enable GPU-based occlusion culling (used by canopy occluders in woodland)
	get_viewport().use_occlusion_culling = true
	# Measure renderer main-thread + GPU frame time (reported in [PERF] log)
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	var _mt := Time.get_ticks_msec()
	_day_night = preload("res://day_night_cycle.gd").new()
	_day_night.name = "DayNightCycle"
	add_child(_day_night)
	_load_heightmap()
	_carve_terrain_voids()
	print("main: heightmap + terrain voids: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	_setup_environment()
	# Wire DayNightCycle to environment objects
	_day_night.env = _env
	_day_night.sky_mat = _sky_mat
	_day_night.vol_sky = _vol_sky
	_day_night.sun = _sun
	# Register global shader parameters BEFORE park_loader creates materials
	RenderingServer.global_shader_parameter_add("wind_vec", RenderingServer.GLOBAL_VAR_TYPE_VEC2, Vector2.ZERO)
	RenderingServer.global_shader_parameter_add("snow_cover", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("rain_wetness", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("sky_reflect_color", RenderingServer.GLOBAL_VAR_TYPE_VEC3, Vector3(0.32, 0.38, 0.45))
	RenderingServer.global_shader_parameter_add("season_t", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, _season_t)
	RenderingServer.global_shader_parameter_add("lightning_flash", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("dew_amount", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("lamp_glow", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("cloud_coverage_g", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.5)
	RenderingServer.global_shader_parameter_add("cloud_speed_g", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.00004)
	# Player camera world position — pushed each frame so distance-based
	# effects (LOD dither) compute against the player view, not whatever
	# camera is active in the current render pass (shadow / reflection).
	RenderingServer.global_shader_parameter_add("player_world_pos", RenderingServer.GLOBAL_VAR_TYPE_VEC3, Vector3.ZERO)
	_wind_system = preload("res://wind_system.gd").new()
	_wind_system.name = "WindSystem"
	add_child(_wind_system)
	_weather_mgr = preload("res://weather_manager.gd").new()
	_weather_mgr.name = "WeatherManager"
	add_child(_weather_mgr)
	print("main: environment: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	# Terrain3D MUST init before park — builders need accurate terrain height
	_setup_ground()
	print("main: Terrain3D setup: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	if not _terrain_only:
		_setup_park()
		if _park_loader:
			_day_night.facade_materials = _park_loader.facade_materials
		print("main: park_loader: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	if not _terrain_only:
		# Structure textures + boundary mask + structure mask now handled by
		# Terrain3D native control map — only data maps for overlay effects needed
		if _park_loader and not _park_loader.landuse_zones.is_empty():
			_apply_landuse_map(_park_loader.landuse_zones, _park_loader.water_bodies)
		print("main: landuse map: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
		if _park_loader and _park_loader._canopy_texture:
			_set_terrain_param("canopy_map", _park_loader._canopy_texture)
		print("main: canopy map: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
		# Unified to Godot's particle system 2026-05-09: Tier 1 + Tier 0 + Accents
		# all run through _setup_grass_particles. Previous GDExtension (Tier 1) and
		# static tuft chunks (Tier 2) retired — single source of truth for zone
		# filtering, density tables, and coordinate transforms.
		if _terrain3d:
			_setup_grass_particles()
			print("main: grass particles: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	_player = _setup_player()
	if _park_loader and _park_loader.boundary_polygon.size() > 2:
		_player.boundary_polygon = _park_loader.boundary_polygon
	# Terrain3D needs the camera for clipmap LOD and dynamic collision
	if _player:
		_player_head = _player.get_node_or_null("Head")
		_player_camera = _player.get_node_or_null("Head/Camera")
	if _terrain3d and _player_camera:
		_terrain3d.set_camera(_player_camera)
	_hud = preload("res://hud_manager.gd").new()
	_hud.setup(self)
	_setup_color_grade()
	if not _terrain_only:
		_setup_lamp_lights()
	print("main: total _ready: %d ms" % (Time.get_ticks_msec() - _mt))
	_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	_weather_mgr.mode = _weather_mode
	# Ambient audio — disabled for now
	#if not _terrain_only and _park_loader and _player:
	#	_audio_manager = preload("res://audio_manager.gd").new(_park_loader)
	#	_audio_manager.setup(_player, _park_loader.water_bodies, _park_loader.boundary_polygon)
	#	print("main: audio: ready")
	# Check for --tour / --tour-showcase / --readme-shots CLI arg
	for arg in OS.get_cmdline_user_args():
		if arg in ["--tour", "--tour-showcase", "--readme-shots"]:
			_tour_mode = true
			_build_tour_shots()
			_tour_state = 0  # WAIT_LOAD
			_tour_timer = 0.0
			_tour_idx = 0
			DirAccess.make_dir_recursive_absolute(_tour_save_dir)
			if arg == "--tour-showcase":
				_tour_settle_time = 60.0  # 60s per location for interactive exploration
				_player.tour_freeze = false  # let user fly around between transports
				print("Tour showcase (interactive): %d shots, %ds per location → %s/" % [
					_tour_shots.size(), int(_tour_settle_time), _tour_save_dir])
			else:
				_tour_settle_time = 3.0
				_player.tour_freeze = true  # freeze for automated captures
				print("Tour mode: %d shots queued → %s/" % [_tour_shots.size(), _tour_save_dir])
			break
	if _walk_bot:
		_player.tour_freeze = true  # disable player input, bot controls movement
		var abs_dir := ProjectSettings.globalize_path("res://" + _walk_bot_dir)
		DirAccess.make_dir_recursive_absolute(abs_dir)
		var yaw_str := "%.0f" % _cli_pos.y if _cli_pos_set else "0"
		print("Walk bot: pos=(%.0f,%.0f) yaw=%s speed=%.1fm/s duration=%.0fs interval=%.1fs → %s/" % [
			_cli_pos.x, _cli_pos.z, yaw_str, _walk_bot_speed,
			_walk_bot_duration, _walk_bot_interval, abs_dir])
		print("Walk bot: settling for %.0fs before walking..." % _walk_bot_settle)
var _screenshot_timer := 0.0
var _screenshot_done  := false
var _labels_hidden_for_screenshot := false
var _screenshot_counter := 0  # incrementing counter for F12 screenshots
var _auto_screenshot := false  # only auto-capture when --quit-after is used
var _lt_screenshot_pending := false  # debounce for gamepad left trigger screenshots

# Distance overlay (F1) — floating Label3Ds on nearest trees, color-coded by LOD band.
# LOD bands match mission_vegetation_toolkit Phase 1: LOD0 0–100m, LOD1 100–230m, impostor 230m+.
var _dist_overlay_visible := false
var _dist_labels: Array = []  # Array[Label3D] — pool, reused each frame
const _DIST_POOL_SIZE := 40
const _DIST_MAX_RANGE := 350.0
var _dist_tree_positions: PackedVector3Array = PackedVector3Array()  # cached once

# ---------------------------------------------------------------------------
# Tour mode — automated screenshot capture across 10 locations × 3 angles × 3 times
# Activated via --tour CLI arg.  Non-tour mode is unchanged.
# ---------------------------------------------------------------------------
var _tour_mode := false
var _tour_state := 0  # 0=WAIT_LOAD, 1=SETTLE, 2=CAPTURE, 3=DONE
var _tour_timer := 0.0
var _tour_idx := 0  # index into _tour_shots array
var _tour_shots: Array = []  # populated in _build_tour_shots()
var _tour_save_dir := "/tmp/tour"  # overridden by --readme-shots
var _tour_settle_time := 3.0  # seconds to wait at each location (60 for showcase)

## Tour/showcase/readme data moved to tour_data.gd (TourData class_name)

func _build_tour_shots() -> void:
	_tour_shots.clear()
	for arg in OS.get_cmdline_user_args():
		if arg == "--readme-shots":
			_build_readme_shots()
			return
	# Check for --tour-showcase: focused set with weather/season variety
	for arg in OS.get_cmdline_user_args():
		if arg == "--tour-showcase":
			_build_showcase_shots()
			return
	for vp in TourData.VIEWPOINTS:
		for ti in range(TourData.TIMES.size()):
			for ai in range(TourData.ANGLES.size()):
				var shot_data: Dictionary = {
					"name": vp["name"],
					"x": float(vp["x"]),
					"z": float(vp["z"]),
					"yaw": float(vp["yaw"]) + float(TourData.ANGLES[ai]["yaw_offset"]),
					"pitch": float(TourData.ANGLES[ai]["pitch"]),
					"hour": TourData.TIMES[ti],
					"filename": "%s_%dh%s" % [vp["name"], int(TourData.TIMES[ti]), TourData.ANGLES[ai]["suffix"]],
				}
				if TourData.ANGLES[ai].has("height"):
					shot_data["height"] = float(TourData.ANGLES[ai]["height"])
				_tour_shots.append(shot_data)


func _build_showcase_shots() -> void:
	for shot in TourData.SHOWCASE_SHOTS:
		_tour_shots.append(shot.duplicate())
		_tour_shots.back()["filename"] = shot["name"]


func _build_readme_shots() -> void:
	_tour_save_dir = "screenshots"
	for shot in TourData.README_SHOTS:
		_tour_shots.append(shot.duplicate())
		_tour_shots.back()["filename"] = shot["name"]


# ---------------------------------------------------------------------------
# Heightmap — fallback height queries + GPU texture for path/curb shaders.
# Terrain3D handles rendering + collision; heightmap.bin is kept for builders
# that need _terrain_height() before Terrain3D is initialized.
# ---------------------------------------------------------------------------
func _load_heightmap() -> void:
	if not FileAccess.file_exists("res://heightmap.bin"):
		push_warning("heightmap.bin not found — height queries will return 0")
		return
	var fa := FileAccess.open("res://heightmap.bin", FileAccess.READ)
	_hm_width      = fa.get_32()
	_hm_depth      = fa.get_32()
	_hm_world_size = fa.get_float()
	var _origin_h  = fa.get_float()  # read past header field (unused)
	var byte_count := _hm_width * _hm_depth * 4
	var buf := fa.get_buffer(byte_count)
	fa.close()
	_hm_data = buf.to_float32_array()
	print("Heightmap loaded: %d×%d  (fallback for height queries + path shader)" % [
		_hm_width, _hm_depth])


func _terrain_height(x: float, z: float) -> float:
	## Query terrain height — uses Terrain3D when available.
	if _terrain3d and _terrain3d.data:
		var h := _terrain3d.data.get_height(Vector3(x, 0.0, z))
		if not is_nan(h):
			return h
	# Fallback: heightmap barycentric interpolation
	if _hm_data.is_empty():
		return 0.0
	var half := _hm_world_size * 0.5
	var xi   := (x + half) / _hm_world_size * (_hm_width  - 1)
	var zi   := (z + half) / _hm_world_size * (_hm_depth  - 1)
	var xi0  := clampi(int(xi), 0, _hm_width  - 2)
	var zi0  := clampi(int(zi), 0, _hm_depth  - 2)
	var fx   := xi - xi0
	var fz   := zi - zi0
	var h00  := float(_hm_data[zi0       * _hm_width + xi0    ])
	var h10  := float(_hm_data[zi0       * _hm_width + xi0 + 1])
	var h01  := float(_hm_data[(zi0 + 1) * _hm_width + xi0    ])
	var h11  := float(_hm_data[(zi0 + 1) * _hm_width + xi0 + 1])
	# Match mesh diagonal: checkerboard on flat, adaptive on slopes
	var d1 := absf(h00 - h11)
	var d2 := absf(h10 - h01)
	var use_alt: bool
	if absf(d1 - d2) < 0.02:
		use_alt = (xi0 + zi0) % 2 == 1
	else:
		use_alt = d2 < d1
	if not use_alt:
		# Split along 00→11
		if fz <= fx:
			return h00 + (h10 - h00) * fx + (h11 - h10) * fz
		else:
			return h00 + (h11 - h01) * fx + (h01 - h00) * fz
	else:
		# Split along 10→01
		if fx + fz <= 1.0:
			return h00 + (h10 - h00) * fx + (h01 - h00) * fz
		else:
			return h11 + (h01 - h11) * (1.0 - fx) + (h10 - h11) * (1.0 - fz)


# ---------------------------------------------------------------------------
# Terrain voids — lowers heightmap values for tunnel interiors so that
# path/curb shaders (which snap to the GPU heightmap texture) conform to
# the tunnel floor.  Terrain3D handles visual rendering + collision;
# this only affects the fallback _hm_data passed to park_loader.
# ---------------------------------------------------------------------------
func _carve_terrain_voids() -> void:
	if _hm_data.is_empty():
		return
	# Bethesda Terrace arcade — lower heightmap inside the tunnel passage
	# so path vertex shaders snap to the arcade floor elevation.
	# Tunnel zone: between wall peaks Z≈997-1004, narrow to arcade opening width.
	var floor_h := 17.0
	_carve_terrain_rect(-484.0, -462.0, 995.0, 1005.0, floor_h, 2.0,
		"bethesda_arcade")


func _carve_terrain_rect(x_min: float, x_max: float, z_min: float, z_max: float,
		floor_h: float, feather: float, label: String) -> void:
	## Lower heightmap values in a rectangle so path/curb GPU snapping matches tunnel floors.
	var half := _hm_world_size * 0.5
	var scale_x := float(_hm_width - 1) / _hm_world_size
	var scale_z := float(_hm_depth - 1) / _hm_world_size
	var col_lo := clampi(int((x_min - feather + half) * scale_x), 0, _hm_width - 1)
	var col_hi := clampi(int((x_max + feather + half) * scale_x) + 1, 0, _hm_width - 1)
	var row_lo := clampi(int((z_min - feather + half) * scale_z), 0, _hm_depth - 1)
	var row_hi := clampi(int((z_max + feather + half) * scale_z) + 1, 0, _hm_depth - 1)
	var cells := 0
	for zi in range(row_lo, row_hi + 1):
		var wz := float(zi) / float(_hm_depth - 1) * _hm_world_size - half
		for xi in range(col_lo, col_hi + 1):
			var wx := float(xi) / float(_hm_width - 1) * _hm_world_size - half
			var outside_x := maxf(x_min - wx, wx - x_max)
			var outside_z := maxf(z_min - wz, wz - z_max)
			var outside := maxf(outside_x, outside_z)
			if outside >= feather:
				continue
			var t := clampf(outside / feather, 0.0, 1.0)
			var blend := 1.0 - t * t * (3.0 - 2.0 * t)
			if blend <= 0.0:
				continue
			var idx := zi * _hm_width + xi
			var orig_h := float(_hm_data[idx])
			if orig_h > floor_h:
				_hm_data[idx] = lerpf(orig_h, floor_h, blend)
				cells += 1
	print("  Collision void '%s': %d cells carved" % [label, cells])


# ---------------------------------------------------------------------------
# Per-frame update: time + HUD
# ---------------------------------------------------------------------------
func _process(delta: float) -> void:
	# Player camera world position — must be pushed every frame, *before*
	# any early-return paths (tour mode, walk bot), so distance-based
	# shaders (tree LOD dither) compute against the actual view.
	if _player_camera:
		RenderingServer.global_shader_parameter_set("player_world_pos", _player_camera.global_position)

	# --- Tour mode state machine ---
	if _tour_mode:
		if _hud.canvas and _hud.canvas.visible:
			_hud.canvas.visible = false  # hide HUD for clean screenshots
			_set_labels_visible(false)
		if _hud.perf_canvas and _hud.perf_canvas.visible:
			_hud.perf_canvas.visible = false
		_tour_timer += delta
		match _tour_state:
			0:  # WAIT_LOAD — let scene fully build (Terrain3D textures, trees, sky, grass)
				if _tour_timer >= 12.0:
					_tour_state = 1
					_tour_timer = 0.0
					_tour_teleport(_tour_idx)
					print("Tour: load complete, starting captures")
			1:  # SETTLE — let SSAO/SSR/fog converge + explore time
				if _tour_timer >= _tour_settle_time:
					_tour_state = 2
					_tour_timer = 0.0
			2:  # CAPTURE
				var img := get_viewport().get_texture().get_image()
				if img:
					var shot: Dictionary = _tour_shots[_tour_idx]
					var path := "%s/%s.png" % [_tour_save_dir, shot["filename"]]
					img.save_png(path)
					print("Tour [%d/%d]: %s" % [_tour_idx + 1, _tour_shots.size(), shot["filename"]])
				_tour_idx += 1
				if _tour_idx >= _tour_shots.size():
					_tour_write_manifest()
					_tour_state = 3
					print("Tour complete: %d shots saved to %s/" % [_tour_shots.size(), _tour_save_dir])
					get_tree().quit()
				else:
					_tour_state = 1
					_tour_timer = 0.0
					_tour_teleport(_tour_idx)
			3:  # DONE
				pass
		_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
		_hud.update(_player, _time_of_day, TIME_SPEED_NAMES[_time_speed_idx], _season_t)
		return

	# --walk bot: auto-walk forward, capture screenshots at interval
	if _walk_bot and _player:
		_walk_bot_timer += delta
		# Phase 1: settle — let scene load, grass spawn, lighting converge
		if not _walk_bot_settled:
			if _walk_bot_timer >= 2.0 and _hud.canvas and _hud.canvas.visible:
				_hud.canvas.visible = false
			if _walk_bot_timer >= 2.0 and _hud.perf_canvas and _hud.perf_canvas.visible:
				_hud.perf_canvas.visible = false
			if _walk_bot_timer >= 2.0:
				_set_labels_visible(false)
			if _walk_bot_timer >= _walk_bot_settle:
				_walk_bot_settled = true
				_walk_bot_timer = 0.0
				_walk_bot_shot_timer = 0.0
				# Take first screenshot at start position
				_walk_bot_capture()
				print("Walk bot: settled, starting walk")
			return
		# Phase 2: walk and capture
		if _walk_bot_timer >= _walk_bot_duration:
			if not _walk_bot_started:
				return
			# Final screenshot and quit
			_walk_bot_capture()
			var abs_dir := ProjectSettings.globalize_path("res://" + _walk_bot_dir)
			print("Walk bot: done — %d frames saved to %s/" % [_walk_bot_frame, abs_dir])
			# Write a manifest so agents know what was captured
			var manifest_path := abs_dir + "/manifest.txt"
			var f := FileAccess.open(manifest_path, FileAccess.WRITE)
			if f:
				f.store_line("# Walk bot capture manifest")
				f.store_line("# pos=%.1f,%.1f yaw=%.1f speed=%.1fm/s duration=%.0fs interval=%.1fs" % [
					_cli_pos.x, _cli_pos.z, _cli_pos.y, _walk_bot_speed,
					_walk_bot_duration, _walk_bot_interval])
				f.store_line("frames=%d" % _walk_bot_frame)
				f.store_line("dir=%s" % abs_dir)
				f.close()
			get_tree().quit()
			return
		_walk_bot_started = true
		# Move player forward along yaw direction
		var yaw_rad := deg_to_rad(_player.rotation_degrees.y)
		var forward := Vector3(-sin(yaw_rad), 0.0, -cos(yaw_rad))
		var new_x := _player.position.x + forward.x * _walk_bot_speed * delta
		var new_z := _player.position.z + forward.z * _walk_bot_speed * delta
		var new_y := _terrain_height(new_x, new_z) + _cli_height
		_player.global_position = Vector3(new_x, new_y, new_z)
		# Screenshot at interval
		_walk_bot_shot_timer += delta
		if _walk_bot_shot_timer >= _walk_bot_interval:
			_walk_bot_shot_timer -= _walk_bot_interval
			_walk_bot_capture()
		_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
		_hud.update(_player, _time_of_day, TIME_SPEED_NAMES[_time_speed_idx], _season_t)
		return

	# Auto-screenshot for headless capture (only with --quit-after)
	if not _screenshot_done and _auto_screenshot:
		_screenshot_timer += delta
		if _screenshot_timer <= delta and _player:
			_player.set_physics_process(false)
			_player.velocity = Vector3.ZERO
		if _screenshot_timer >= 6.0 and _hud.canvas and _hud.canvas.visible:
			_hud.canvas.visible = false  # hide HUD before capture
		if _screenshot_timer >= 6.0 and _hud.perf_canvas and _hud.perf_canvas.visible:
			_hud.perf_canvas.visible = false
		if _screenshot_timer >= 6.0 and not _labels_hidden_for_screenshot:
			_labels_hidden_for_screenshot = true
			_set_labels_visible(false)   # hide Label3D (building names, etc.)
		if _screenshot_timer >= 8.0:
			_screenshot_done = true
			var img := get_viewport().get_texture().get_image()
			if img:
				img.save_png("/tmp/godot_screenshot.png")
				print("Screenshot saved to /tmp/godot_screenshot.png")
			if _player:
				_player.set_physics_process(true)
			if _hud.canvas:
				_hud.canvas.visible = true  # restore HUD after capture
				_set_labels_visible(true)
	var _t0: int  # profiling scratch

	# Update lamp lights every 0.5s
	_t0 = Time.get_ticks_usec()
	_lamp_light_timer += delta
	if _lamp_light_timer >= LAMP_LIGHT_UPDATE_INTERVAL:
		_lamp_light_timer = 0.0
		_update_lamp_lights()
	_prof_lamps_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_lamps_us, PROF_SMOOTH)

	# Wind + GPU grass push + volumetric clouds
	_t0 = Time.get_ticks_usec()
	_wind_system.update(delta, _time_of_day, _weather_mode)
	_wind_vec = _wind_system.wind_vec
	for gn in _gpu_grass_nodes:
		if is_instance_valid(gn):
			gn.set("wind_vec", _wind_vec)
	if _vol_sky:
		var wlen: float = _wind_vec.length()
		if wlen > 0.01:
			_vol_sky.wind_direction = atan2(_wind_vec.y, _wind_vec.x)
		_vol_sky.wind_speed = wlen * 0.6
	_prof_wind_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_wind_us, PROF_SMOOTH)

	# Ambient audio + weather + season
	_t0 = Time.get_ticks_usec()
	if _audio_manager:
		_audio_manager.update(delta, _wind_vec.length(), WEATHER_NAMES[_weather_mode],
			_rain_wetness, _time_of_day, _lightning_flash)
	if _player:
		_weather_mgr.update(delta, _player.global_position, _wind_vec, _season_t)
		_rain_wetness = _weather_mgr.rain_wetness
		_snow_cover = _weather_mgr.snow_cover
	if _season_speed > 0.0:
		_season_t = fmod(_season_t + _season_speed * delta, 4.0)
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
	_prof_weather_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_weather_us, PROF_SMOOTH)

	# Undergrowth chunk builder
	_t0 = Time.get_ticks_usec()
	if _player and _park_loader and _park_loader._undergrowth_builder:
		_park_loader._undergrowth_builder.season_t = _season_t
		_park_loader._undergrowth_builder.rain_wetness = _rain_wetness
		_park_loader._undergrowth_builder.update_camera(_player.global_position)
	_prof_undergrowth_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_undergrowth_us, PROF_SMOOTH)

	# Ground cover chunk builder
	_t0 = Time.get_ticks_usec()
	if _player and _park_loader and _park_loader._ground_cover_builder:
		_park_loader._ground_cover_builder.season_t = _season_t
		_park_loader._ground_cover_builder.update_camera(_player.global_position)
	_prof_ground_cover_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_ground_cover_us, PROF_SMOOTH)

	# Grass tour auto-teleport + screenshot
	_grass_tour_process(delta)

	# Misc un-bucketed: lightning, time-of-day advance, dist overlay
	var _t_misc := Time.get_ticks_usec()
	# Lightning flashes during thunderstorm
	if _weather_mode == Weather.THUNDERSTORM:
		_lightning_flash = maxf(_lightning_flash - delta * 4.0, 0.0)  # rapid decay (~0.25s)
		_lightning_timer += delta
		if _lightning_timer >= _lightning_next:
			_lightning_timer = 0.0
			_lightning_flash = randf_range(0.6, 1.0)
			# Double flash 20% of the time
			if randf() < 0.2:
				_lightning_flash = 1.0
			_lightning_next = randf_range(3.0, 12.0)
	elif _lightning_flash > 0.01:
		_lightning_flash = maxf(_lightning_flash - delta * 4.0, 0.0)
	RenderingServer.global_shader_parameter_set("lightning_flash", _lightning_flash)
	_prof_misc_us = lerpf(float(Time.get_ticks_usec() - _t_misc), _prof_misc_us, PROF_SMOOTH)

	# Advance clock + day/night cycle
	_t0 = Time.get_ticks_usec()
	_time_of_day += _time_speed * delta
	if _time_of_day >= 24.0:
		_time_of_day -= 24.0
	elif _time_of_day < 0.0:
		_time_of_day += 24.0
	_day_night.apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	_lamp_emission = _day_night.get_lamp_emission()
	_prof_daynight_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_daynight_us, PROF_SMOOTH)

	# HUD
	_t0 = Time.get_ticks_usec()
	_hud.update(_player, _time_of_day, TIME_SPEED_NAMES[_time_speed_idx], _season_t)
	_hud.update_perf(delta, _get_prof_data())
	_prof_hud_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_hud_us, PROF_SMOOTH)

	if _dist_overlay_visible:
		_dist_overlay_update()

	# Periodic perf log — runs regardless of overlay state, so we can
	# A/B test the overlay's own cost by toggling F9 off.
	_diag_log_timer += delta
	if _diag_log_timer >= 2.0:
		_diag_log_timer = 0.0
		if not _diag_hide.is_empty():
			_diag_apply_hides()
		_diag_tick_count += 1
		if _diag_shadow_census and _diag_tick_count == 3:
			_shadow_census()
		var fps := Performance.get_monitor(Performance.TIME_FPS)
		var p_ms: float = Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
		var phy_ms: float = Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
		var sub_us: float = (_prof_lamps_us + _prof_wind_us + _prof_weather_us
			+ _prof_undergrowth_us + _prof_ground_cover_us + _prof_daynight_us
			+ _prof_hud_us)
		var vp_rid := get_viewport().get_viewport_rid()
		var vpcpu_ms := RenderingServer.viewport_get_measured_render_time_cpu(vp_rid)
		var vpgpu_ms := RenderingServer.viewport_get_measured_render_time_gpu(vp_rid)
		# Visible vs shadow pass raster load (objects / primitives / draw calls)
		var vis_p := RenderingServer.viewport_get_render_info(vp_rid,
			RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE,
			RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME)
		var sh_o := RenderingServer.viewport_get_render_info(vp_rid,
			RenderingServer.VIEWPORT_RENDER_INFO_TYPE_SHADOW,
			RenderingServer.VIEWPORT_RENDER_INFO_OBJECTS_IN_FRAME)
		var sh_p := RenderingServer.viewport_get_render_info(vp_rid,
			RenderingServer.VIEWPORT_RENDER_INFO_TYPE_SHADOW,
			RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME)
		print("[PERF] fps=%d process=%.1f physics=%.1f sub=%.2f unacc=%.1f vpcpu=%.1f vpgpu=%.1f vistri=%d shobj=%d shtri=%d overlay=%s" % [
			int(fps), p_ms, phy_ms, sub_us / 1000.0, p_ms - sub_us / 1000.0,
			vpcpu_ms, vpgpu_ms, vis_p, sh_o, sh_p,
			"ON" if _hud.perf_visible else "OFF"])


func _get_prof_data() -> Dictionary:
	# Mirror player physics time (player writes its own accumulator on _physics_process)
	if _player and "prof_phy_us" in _player:
		_prof_player_phy_us = lerpf(_player.prof_phy_us, _prof_player_phy_us, PROF_SMOOTH)
	var data := {
		"lamps": _prof_lamps_us,
		"wind": _prof_wind_us,
		"weather": _prof_weather_us,
		"undergrowth": _prof_undergrowth_us,
		"ground_cover": _prof_ground_cover_us,
		"daynight": _prof_daynight_us,
		"hud": _prof_hud_us,
		"misc": _prof_misc_us,
		"player_phy": _prof_player_phy_us,
	}
	# Tree LOD instance counts (populated at build time by tree_builder)
	if _park_loader and _park_loader._tree_builder:
		var tb = _park_loader._tree_builder
		data["tree_lod0"] = tb.lod0_instances
		data["tree_lod0_chunks"] = tb.lod0_chunks
		data["tree_lod1"] = tb.lod1_instances
		data["tree_lod1_chunks"] = tb.lod1_chunks
		data["tree_imp"] = tb.imp_instances
		data["tree_imp_chunks"] = tb.imp_chunks
	# Chunk counts for context
	if _park_loader and _park_loader._undergrowth_builder:
		var ub = _park_loader._undergrowth_builder
		data["ug_chunks"] = ub._active_chunks.size()
		data["ug_queue"] = ub._build_queue.size()
		data["ug_peak_build_us"] = ub._peak_build_us
		data["ug_last_build_us"] = ub._last_build_us
	if _park_loader and _park_loader._ground_cover_builder:
		var gb = _park_loader._ground_cover_builder
		data["gc_chunks"] = gb._active_chunks.size()
		data["gc_queue"] = gb._build_queue.size()
	return data


## _update_perf_overlay, _update_hud moved to hud_manager.gd


func _set_labels_visible(vis: bool) -> void:
	if _cached_label3d_nodes.is_empty():
		_cached_label3d_nodes = find_children("*", "Label3D", true, false)
	for n: Node in _cached_label3d_nodes:
		if is_instance_valid(n):
			n.visible = vis


# ── Diagnostic A/B toggles (F6/F7/F8) ───────────────────────────────────
# Hide major subsystems to isolate which one owns the unaccounted
# engine-internal main-thread cost in TIME_PROCESS.
# --diag-hide=a,b,c drives the same paths headlessly for scripted bisection.
# Re-applied every perf tick (idempotent) so chunk systems that stream in
# after the first application stay hidden.
# Options: terrain trees undergrowth grass shadows sdfgi fog ssao ssil glow
#          treeshadows proxyshadows furnitureshadows terrainshadows
#          treeshadows/terrainshadows/furnitureshadows (stay visible, stop casting)
var _diag_hide: Array = []
# Perf-experiment knobs: --shadow-dist=meters, --shadow-size=pixels,
# --shadow-filter=0..5 (PCF quality; project default 2). -1 = keep defaults.
var _cli_shadow_dist: float = -1.0
var _cli_shadow_size: int = -1
var _cli_shadow_filter: int = -1
# --shadow-census: one-shot dump of every shadow-casting GeometryInstance3D
# (top 25 by mesh tris × instances) on the 3rd perf tick, after diag hides apply.
var _diag_shadow_census: bool = false
var _diag_tick_count: int = 0
var _diag_trees_hidden: bool = false
var _diag_ug_hidden: bool = false
var _diag_grass_hidden: bool = false
var _diag_terrain_hidden: bool = false
var _diag_tree_mmis: Array = []
var _diag_log_timer: float = 0.0

func _diag_toggle_terrain() -> void:
	if not _terrain3d:
		print("[DIAG] Terrain3D not present")
		return
	_diag_terrain_hidden = not _diag_terrain_hidden
	_terrain3d.visible = not _diag_terrain_hidden
	print("[DIAG] Terrain3D %s" % ("HIDDEN" if _diag_terrain_hidden else "VISIBLE"))

func _diag_toggle_trees() -> void:
	if _diag_tree_mmis.is_empty() and _park_loader:
		var patterns := ["Tree_*", "TreeL1_*", "TreeL2_*", "TreeImp_*"]
		for pat: String in patterns:
			for n: Node in _park_loader.find_children(pat, "MultiMeshInstance3D", true, false):
				_diag_tree_mmis.append(n)
	_diag_trees_hidden = not _diag_trees_hidden
	for n: Node in _diag_tree_mmis:
		if is_instance_valid(n):
			n.visible = not _diag_trees_hidden
	print("[DIAG] Trees %s (%d MMIs)" % [
		"HIDDEN" if _diag_trees_hidden else "VISIBLE", _diag_tree_mmis.size()])

func _diag_toggle_undergrowth() -> void:
	if not (_park_loader and _park_loader._undergrowth_builder):
		return
	_diag_ug_hidden = not _diag_ug_hidden
	var ub = _park_loader._undergrowth_builder
	var count := 0
	for key in ub._active_chunks:
		var rids: Array = ub._active_chunks[key]
		# rids[1] is the instance RID
		RenderingServer.instance_set_visible(rids[1], not _diag_ug_hidden)
		count += 1
	print("[DIAG] Undergrowth %s (%d instances)" % [
		"HIDDEN" if _diag_ug_hidden else "VISIBLE", count])

func _diag_toggle_grass() -> void:
	# Node3D.visible doesn't propagate to RS-direct instances created inside
	# the GPUGrass GDExtension, so we toggle set_process to stop the per-frame
	# compute dispatch. is_processing() is logged to confirm the flag actually
	# flipped (rules out GDExtension ignoring the base-class flag).
	_diag_grass_hidden = not _diag_grass_hidden
	var states := []
	for gn in _gpu_grass_nodes:
		if is_instance_valid(gn):
			gn.set_process(not _diag_grass_hidden)
			states.append("%s=%s" % [gn.name, gn.is_processing()])
	print("[DIAG] GPU grass dispatch %s — %s" % [
		"OFF" if _diag_grass_hidden else "ON", ", ".join(states)])

func _shadow_census() -> void:
	## Dump every node-level shadow caster, largest raster load first.
	## (RenderingServer-direct instances and Terrain3D internals don't appear.)
	var rows: Array = []
	for n: Node in find_children("*", "GeometryInstance3D", true, false):
		var gi := n as GeometryInstance3D
		if gi.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF:
			continue
		var tris := 0
		var inst := 1
		if gi is MultiMeshInstance3D:
			var mm: MultiMesh = (gi as MultiMeshInstance3D).multimesh
			if mm and mm.mesh:
				tris = _mesh_tri_count(mm.mesh)
				inst = mm.instance_count
		elif gi is MeshInstance3D:
			var m: Mesh = (gi as MeshInstance3D).mesh
			if m:
				tris = _mesh_tri_count(m)
		rows.append([tris * inst, gi.name, inst, tris, gi.get_class()])
	rows.sort_custom(func(a: Array, b: Array) -> bool: return a[0] > b[0])
	var total := 0
	for r: Array in rows:
		total += r[0]
	print("[CENSUS] %d casters, %d total mesh tris (×cascades for shadow cost)" % [
		rows.size(), total])
	for i in mini(rows.size(), 25):
		var r: Array = rows[i]
		print("[CENSUS] %10d = %6d inst × %7d tris  %-24s %s" % [r[0], r[2], r[3], r[4], r[1]])


func _mesh_tri_count(m: Mesh) -> int:
	var tris := 0
	for si in m.get_surface_count():
		var arrays: Array = m.surface_get_arrays(si)
		var idx = arrays[Mesh.ARRAY_INDEX]  # Nil when surface is non-indexed
		if idx != null and idx.size() > 0:
			tris += idx.size() / 3
		else:
			var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			tris += v.size() / 3
	return tris


func _diag_apply_hides() -> void:
	for what: String in _diag_hide:
		match what:
			"terrain":
				if _terrain3d:
					_terrain3d.visible = false
			"trees":
				if _diag_tree_mmis.is_empty() and _park_loader:
					for pat: String in ["Tree_*", "TreeL1_*", "TreeL2_*", "TreeImp_*"]:
						for n: Node in _park_loader.find_children(pat, "MultiMeshInstance3D", true, false):
							_diag_tree_mmis.append(n)
				for n: Node in _diag_tree_mmis:
					if is_instance_valid(n):
						n.visible = false
			"terrainshadows":
				if _terrain3d:
					_terrain3d.set_cast_shadows(RenderingServer.SHADOW_CASTING_SETTING_OFF)
			"furnitureshadows":
				# Repeated small furniture/details are MMIs; landmarks and
				# bridges are MeshInstance3Ds and keep casting.
				if _park_loader:
					for n: Node in _park_loader.find_children("*", "MultiMeshInstance3D", true, false):
						if not (n.name.begins_with("Tree") or n.name.begins_with("ShdwProxy")):
							(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			"treeshadows":
				if _diag_tree_mmis.is_empty() and _park_loader:
					for pat: String in ["Tree_*", "TreeL1_*", "TreeL2_*", "TreeImp_*"]:
						for n: Node in _park_loader.find_children(pat, "MultiMeshInstance3D", true, false):
							_diag_tree_mmis.append(n)
				for n: Node in _diag_tree_mmis:
					if is_instance_valid(n):
						n.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			"proxyshadows":
				# Shadow proxies are SHADOWS_ONLY — turning casting off
				# removes tree shadows entirely (visible trees cast nothing).
				if _park_loader:
					for n: Node in _park_loader.find_children("ShdwProxy_*", "MultiMeshInstance3D", true, false):
						(n as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			"undergrowth":
				if _park_loader and _park_loader._undergrowth_builder:
					var ub = _park_loader._undergrowth_builder
					for key in ub._active_chunks:
						RenderingServer.instance_set_visible(ub._active_chunks[key][1], false)
			"grass":
				for gp in _grass_particle_nodes:
					if is_instance_valid(gp):
						gp.visible = false
			"shadows":
				if _sun:
					_sun.shadow_enabled = false
			"sdfgi":
				if _env:
					_env.sdfgi_enabled = false
			"fog":
				if _env:
					_env.volumetric_fog_enabled = false
			"ssao":
				if _env:
					_env.ssao_enabled = false
			"ssil":
				if _env:
					_env.ssil_enabled = false
			"glow":
				if _env:
					_env.glow_enabled = false
			_:
				push_warning("--diag-hide: unknown option '%s'" % what)


var _diag_grass_force: bool = false
var _diag_grass_orig_biomes: Array = []
func _toggle_dist_overlay() -> void:
	_dist_overlay_visible = not _dist_overlay_visible
	if _dist_overlay_visible and _dist_tree_positions.is_empty():
		_dist_cache_tree_positions()
	if _dist_overlay_visible and _dist_labels.is_empty():
		_dist_build_label_pool()
	for lbl in _dist_labels:
		lbl.visible = _dist_overlay_visible
	print("[DIAG] Distance overlay %s (%d trees cached)" % [
		"ON" if _dist_overlay_visible else "OFF", _dist_tree_positions.size()])


func _dist_cache_tree_positions() -> void:
	_dist_tree_positions.clear()
	var body: Node = null
	if _park_loader:
		body = _park_loader.get_node_or_null("TreeTrunkCollision")
	if body == null:
		print("[DIAG] Distance overlay: TreeTrunkCollision not found")
		return
	for child in body.get_children():
		if child is CollisionShape3D:
			_dist_tree_positions.append(child.global_position)


func _dist_build_label_pool() -> void:
	for i in _DIST_POOL_SIZE:
		var lbl := Label3D.new()
		lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lbl.fixed_size = true
		lbl.pixel_size = 0.0008  # constant on-screen size regardless of distance
		lbl.no_depth_test = true
		lbl.alpha_cut = Label3D.ALPHA_CUT_DISCARD  # render with opaque-pass discard so depth-test-off actually wins over leaf transparency
		lbl.render_priority = 127  # draw last
		lbl.outline_size = 8
		lbl.outline_modulate = Color(0, 0, 0, 0.9)
		lbl.font_size = 32
		lbl.visible = false
		add_child(lbl)
		_dist_labels.append(lbl)


func _dist_overlay_update() -> void:
	if _player == null or _dist_tree_positions.is_empty():
		return
	var cam := _player.get_node_or_null("Head/Camera") as Camera3D
	if cam == null:
		return
	var cam_pos := cam.global_position
	var cam_fwd := -cam.global_transform.basis.z
	# Score = squared distance; reject behind-camera trees via dot product.
	var max_d2: float = _DIST_MAX_RANGE * _DIST_MAX_RANGE
	# Reuse two parallel arrays — squared distance and tree index.
	var picks: Array = []  # Array of [d2, idx]
	for i in _dist_tree_positions.size():
		var p: Vector3 = _dist_tree_positions[i]
		var d: Vector3 = p - cam_pos
		var d2: float = d.x * d.x + d.y * d.y + d.z * d.z
		if d2 > max_d2:
			continue
		if d.dot(cam_fwd) <= 0.0:
			continue  # behind camera
		picks.append([d2, i])
	picks.sort_custom(func(a, b): return a[0] < b[0])
	var n: int = mini(picks.size(), _DIST_POOL_SIZE)
	for k in n:
		var idx: int = picks[k][1]
		var p: Vector3 = _dist_tree_positions[idx]
		var dist: float = sqrt(picks[k][0])
		var lbl: Label3D = _dist_labels[k]
		lbl.global_position = p + Vector3(0.0, 4.0, 0.0)  # float above trunk
		lbl.text = "%.0fm" % dist
		# Color-code by LOD band (Phase 1 boundaries: 0-100, 100-230, 230+)
		if dist < 100.0:
			lbl.modulate = Color(0.5, 1.0, 0.5)  # LOD0 — green
		elif dist < 230.0:
			lbl.modulate = Color(1.0, 1.0, 0.4)  # LOD1 — yellow
		else:
			lbl.modulate = Color(1.0, 0.5, 0.5)  # impostor — red
		lbl.visible = true
	for k in range(n, _DIST_POOL_SIZE):
		_dist_labels[k].visible = false


func _diag_toggle_grass_force() -> void:
	# Set every grass node's target_biome to -2, which triggers a debug
	# bypass in grass_compute.glsl that places a blade at every grid
	# position, regardless of zone/canopy/distance filters. If grass
	# appears in this mode but not in normal mode, the zone filter or
	# its input data is the problem. If grass STILL doesn't appear,
	# the failure is downstream (mesh, instance, AABB, indirect draw).
	_diag_grass_force = not _diag_grass_force
	if _diag_grass_force and _diag_grass_orig_biomes.is_empty():
		for gn in _gpu_grass_nodes:
			_diag_grass_orig_biomes.append(gn.get("target_biome"))
	for i in _gpu_grass_nodes.size():
		var gn = _gpu_grass_nodes[i]
		if not is_instance_valid(gn):
			continue
		if _diag_grass_force:
			gn.set("target_biome", -2)
		else:
			gn.set("target_biome", _diag_grass_orig_biomes[i])
	print("[DIAG] Grass force-place %s (4 nodes, target_biome=%s)" % [
		"ON (zone filter bypassed)" if _diag_grass_force else "OFF",
		"-2" if _diag_grass_force else "original"])

var _diag_grass_highlight: bool = false
const _DIAG_BIOME_COLORS := {
	"Lawn":  Color(1.0, 0.0, 0.0),  # red
	"Shade": Color(0.0, 1.0, 0.0),  # green
	"Wild":  Color(0.0, 0.4, 1.0),  # blue
	"Sedge": Color(1.0, 1.0, 0.0),  # yellow
}
func _diag_toggle_grass_highlight() -> void:
	# Color each biome distinctly so a single screenshot at altitude shows
	# (a) which biomes are placing blades, (b) where they're placing them
	# spatially, and (c) the height differences between blade meshes
	# (Blade_Lawn=7.6cm, Shade=12cm, Wild=25cm, Sedge=16cm).
	_diag_grass_highlight = not _diag_grass_highlight
	var n := 0
	for gn in _gpu_grass_nodes:
		if not is_instance_valid(gn):
			continue
		var mat = gn.get("grass_material")
		if not (mat is ShaderMaterial):
			continue
		mat.set_shader_parameter("debug_highlight", _diag_grass_highlight)
		# Node name is "GPUGrass_<biome>" — extract suffix to pick color
		var biome: String = String(gn.name).trim_prefix("GPUGrass_")
		var c: Color = _DIAG_BIOME_COLORS.get(biome, Color(1.0, 0.0, 1.0))
		mat.set_shader_parameter("debug_color", Vector3(c.r, c.g, c.b))
		n += 1
	print("[DIAG] Grass highlight %s — %d materials. Lawn=red Shade=green Wild=blue Sedge=yellow" % [
		"ON" if _diag_grass_highlight else "OFF", n])


func _tour_teleport(idx: int) -> void:
	var shot: Dictionary = _tour_shots[idx]
	var x: float = shot["x"]
	var z: float = shot["z"]
	var yaw: float = shot["yaw"]
	var pitch: float = shot["pitch"]
	var hour: float = shot["hour"]
	var cam_height: float = shot.get("height", 1.3)
	_player.global_position = Vector3(x, _terrain_height(x, z) + cam_height, z)
	_player.velocity = Vector3.ZERO
	_player.rotation_degrees.y = yaw
	if _player_head:
		_player_head.rotation_degrees.x = pitch
	_time_of_day = hour
	_time_speed = 0.0
	# Apply weather if specified
	if shot.has("weather"):
		_set_weather(shot["weather"])
	# Apply season if specified
	if shot.has("season"):
		_season_t = float(shot["season"])
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
	_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)


func _set_weather(mode) -> void:
	_weather_mgr.set_mode(mode, _day_night, _time_of_day, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	_weather_mode = _weather_mgr.mode
	_snow_cover = _weather_mgr.snow_cover
	_rain_wetness = _weather_mgr.rain_wetness


func _tour_write_manifest() -> void:
	var manifest: Dictionary = {"shots": [], "viewpoints": TourData.VIEWPOINTS.size(), "angles": TourData.ANGLES.size(), "times": TourData.TIMES.size()}
	for shot in _tour_shots:
		manifest["shots"].append({"filename": shot["filename"] + ".png", "name": shot["name"], "hour": shot["hour"], "x": shot["x"], "z": shot["z"]})
	var fa := FileAccess.open("%s/manifest.json" % _tour_save_dir, FileAccess.WRITE)
	fa.store_string(JSON.stringify(manifest, "\t"))
	fa.close()
	print("Tour: manifest.json written")


## _compass_label, _nearest_area moved to hud_manager.gd


func _unhandled_input(event: InputEvent) -> void:
	# Gamepad left trigger → screenshot
	if event is InputEventJoypadMotion and event.axis == JOY_AXIS_TRIGGER_LEFT:
		if event.axis_value > 0.8 and not _lt_screenshot_pending:
			_lt_screenshot_pending = true
			_take_screenshot()
		elif event.axis_value < 0.2:
			_lt_screenshot_pending = false
		return
	# Gamepad buttons: D-pad left/right = time, LB = weather, RB = season
	if event is InputEventJoypadButton and event.pressed:
		if event.button_index == JOY_BUTTON_DPAD_LEFT:
			_time_of_day = fmod(_time_of_day - 1.0 + 24.0, 24.0)
			_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
			print("Time: %.1f h" % _time_of_day)
		elif event.button_index == JOY_BUTTON_DPAD_RIGHT:
			_time_of_day = fmod(_time_of_day + 1.0, 24.0)
			_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
			print("Time: %.1f h" % _time_of_day)
		elif event.button_index == JOY_BUTTON_LEFT_SHOULDER:
			_cycle_weather()
		elif event.button_index == JOY_BUTTON_RIGHT_SHOULDER:
			_season_t = fmod(_season_t + 1.0 / 3.0, 4.0)
			RenderingServer.global_shader_parameter_set("season_t", _season_t)
			print("Month: %s (season_t=%.2f)" % [_hud._month_name(_season_t), _season_t])
		return
	if not (event is InputEventKey and event.pressed):
		return
	if event.keycode == KEY_T:
		_time_speed_idx = (_time_speed_idx + 1) % TIME_SPEEDS.size()
		_time_speed = TIME_SPEEDS[_time_speed_idx]
		print("Time speed: ", TIME_SPEED_NAMES[_time_speed_idx])
	elif event.keycode == KEY_BRACKETLEFT:
		_time_of_day = fmod(_time_of_day - 1.0 + 24.0, 24.0)
		_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
		print("Time: %.1f h" % _time_of_day)
	elif event.keycode == KEY_BRACKETRIGHT:
		_time_of_day = fmod(_time_of_day + 1.0, 24.0)
		_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
		print("Time: %.1f h" % _time_of_day)
	elif event.keycode == KEY_P:
		_cycle_weather()
	elif event.keycode == KEY_G:
		if _park_loader and _park_loader._gap_builder:
			var gb = _park_loader._gap_builder
			var vis: bool = not (gb._root and gb._root.visible)
			gb.set_visible(vis)
			print("Data gaps: %s" % ("ON" if vis else "OFF"))
	elif event.keycode == KEY_H:
		if _hud.canvas:
			_hud.canvas.visible = not _hud.canvas.visible
	elif event.keycode == KEY_F9:
		_hud.toggle_perf()
		print("Perf overlay: %s" % ("ON" if _hud.perf_visible else "OFF"))
	elif event.keycode == KEY_F1:
		_toggle_dist_overlay()
	elif event.keycode == KEY_F3:
		_diag_toggle_grass_force()
	elif event.keycode == KEY_F4:
		_diag_toggle_grass_highlight()
	elif event.keycode == KEY_F5:
		_diag_toggle_terrain()
	elif event.keycode == KEY_F6:
		_diag_toggle_trees()
	elif event.keycode == KEY_F7:
		_diag_toggle_undergrowth()
	elif event.keycode == KEY_F8:
		_diag_toggle_grass()
	elif event.keycode == KEY_F11:
		if DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		else:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
			Input.mouse_mode = Input.MOUSE_MODE_HIDDEN
	elif event.keycode == KEY_COMMA:
		_user_gamma = clampf(_user_gamma - 0.05, 0.5, 2.0)
		print("Gamma: %.2f" % _user_gamma)
	elif event.keycode == KEY_PERIOD:
		_user_gamma = clampf(_user_gamma + 0.05, 0.5, 2.0)
		print("Gamma: %.2f" % _user_gamma)
	# +/- reserved for movement speed (player.gd)
	elif event.keycode == KEY_9:
		if _wind_system.wind_override < 0.0:
			_wind_system.wind_override = 1.0
		_wind_system.wind_override = clampf(_wind_system.wind_override - 0.1, 0.0, 3.0)
		print("Wind: %.0f%%" % (_wind_system.wind_override * 100.0))
	elif event.keycode == KEY_0:
		if _wind_system.wind_override < 0.0:
			_wind_system.wind_override = 1.0
		_wind_system.wind_override = clampf(_wind_system.wind_override + 0.1, 0.0, 3.0)
		print("Wind: %.0f%%" % (_wind_system.wind_override * 100.0))
	elif event.keycode == KEY_N:
		if event.shift_pressed:
			_season_t = fmod(_season_t - 1.0 / 3.0 + 4.0, 4.0)
		else:
			_season_t = fmod(_season_t + 1.0 / 3.0, 4.0)
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
		print("Month: %s (season_t=%.2f)" % [_hud._month_name(_season_t), _season_t])
	elif event.keycode == KEY_F12:
		_take_screenshot()
	elif event.keycode == KEY_F10:
		_start_grass_tour()
	elif event.keycode == KEY_M:
		if _audio_manager:
			_audio_manager.toggle_mute()


func _season_name(t: float) -> String:
	if t < 1.0: return "Spring"
	if t < 2.0: return "Summer"
	if t < 3.0: return "Autumn"
	return "Winter"


## _month_name moved to hud_manager.gd

# --- Grass tour: F10 visits all grass type locations + screenshots ---
var _grass_tour_spots := []  # populated at runtime with random positions
var _grass_tour_active := false
var _grass_tour_idx := 0
var _grass_tour_timer := 0.0

func _start_grass_tour() -> void:
	# Generate random positions, times, seasons, weather across the park
	_grass_tour_spots.clear()
	var rng := RandomNumberGenerator.new()
	rng.seed = Time.get_ticks_msec()
	var weathers := ["clear", "clear", "clear", "rain", "snow", "fog"]  # bias toward clear
	var count := 60
	var attempts := 0
	for i in count:
		if attempts > 500:
			break  # safety limit
		var x := rng.randf_range(-1100.0, 1100.0)
		var z := rng.randf_range(-2000.0, 2100.0)
		attempts += 1
		# Must be inside park boundary (atlas surface > 0)
		if _park_loader and not _park_loader._in_boundary(x, z):
			continue
		# Skip water (surface type 4) and buildings (5)
		if _park_loader:
			var surf: int = _park_loader._atlas_surface(x, z)
			if surf == 4 or surf == 5:
				continue
		var h := _terrain_height(x, z)
		if h < 1.0:
			continue  # skip invalid terrain
		var yaw := rng.randf_range(0.0, 360.0)
		var pitch := rng.randf_range(-8.0, 3.0)
		var hour := rng.randf_range(5.5, 20.0)  # dawn to dusk
		var season := rng.randf_range(0.0, 4.0)  # full year
		var weather: String = weathers[rng.randi() % weathers.size()]
		_grass_tour_spots.append({"name": "rnd_%03d" % i, "x": x, "z": z,
			"yaw": yaw, "pitch": pitch, "hour": hour, "season": season, "weather": weather})
	_grass_tour_active = true
	_grass_tour_idx = 0
	_grass_tour_timer = 0.0
	print("Photo tour: starting (F10) — %d of %d survived boundary filter (%d attempts)" % [_grass_tour_spots.size(), count, attempts])
	_grass_tour_teleport()

func _grass_tour_teleport() -> void:
	var spot: Dictionary = _grass_tour_spots[_grass_tour_idx]
	var x: float = spot["x"]
	var z: float = spot["z"]
	_player.global_position = Vector3(x, _terrain_height(x, z) + 1.55, z)
	_player.velocity = Vector3.ZERO
	_player.rotation_degrees.y = spot["yaw"]
	if _player_head:
		_player_head.rotation_degrees.x = spot["pitch"]
	# Set time, season, weather for this shot
	if spot.has("hour"):
		_time_of_day = spot["hour"]
	if spot.has("season"):
		_season_t = spot["season"]
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
	if spot.has("weather"):
		_set_weather(spot["weather"])
	_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	print("Photo tour: %s (%.0f,%.0f) %s %.1fh %s" % [
		spot["name"], x, z, _hud._month_name(_season_t), spot.get("hour", 12.0), spot.get("weather", "clear")])
	_grass_tour_timer = 0.0

func _grass_tour_process(delta: float) -> void:
	if not _grass_tour_active:
		return
	_grass_tour_timer += delta
	# Wait 4 seconds for grass chunks to load, then screenshot
	if _grass_tour_timer > 4.0 and _grass_tour_timer < 4.1:
		var spot: Dictionary = _grass_tour_spots[_grass_tour_idx]
		var dir_path := ProjectSettings.globalize_path("res://screenshots")
		DirAccess.make_dir_recursive_absolute(dir_path)
		var img := get_viewport().get_texture().get_image()
		if img:
			var path := "%s/grass_%s.png" % [dir_path, spot["name"]]
			img.save_png(path)
			print("Grass tour: saved %s" % path)
	# After 5 seconds, move to next
	if _grass_tour_timer > 5.0:
		_grass_tour_idx += 1
		if _grass_tour_idx >= _grass_tour_spots.size():
			_grass_tour_active = false
			print("Grass tour: done — %d screenshots" % _grass_tour_spots.size())
			return
		_grass_tour_teleport()

func _take_screenshot() -> void:
	var dir_path := ProjectSettings.globalize_path("res://screenshots")
	DirAccess.make_dir_recursive_absolute(dir_path)
	var img := get_viewport().get_texture().get_image()
	if not img:
		print("Screenshot: failed to capture")
		return
	var path := "%s/cpw_%03d.png" % [dir_path, _screenshot_counter]
	img.save_png(path)
	_screenshot_counter += 1
	print("Screenshot saved: %s" % path)


func _walk_bot_capture() -> void:
	var img := get_viewport().get_texture().get_image()
	if not img:
		print("Walk bot: failed to capture frame %d" % _walk_bot_frame)
		return
	var abs_dir := ProjectSettings.globalize_path("res://" + _walk_bot_dir)
	var pos := _player.global_position
	var path := "%s/walk_%04d.png" % [abs_dir, _walk_bot_frame]
	img.save_png(path)
	print("Walk bot [%d]: (%.1f, %.1f) → %s" % [_walk_bot_frame, pos.x, pos.z, path])
	_walk_bot_frame += 1


# ---------------------------------------------------------------------------
# Sky + lighting
# ---------------------------------------------------------------------------
func _load_img_tex(path: String) -> Texture2D:
	return load(path) if ResourceLoader.exists(path) else null

func _setup_environment() -> void:
	# Volumetric cloud sky (clayjohn compute pipeline)
	var sky: Sky
	var vol_sky = load("res://cloud_sky/clouds_sky.tres")
	if vol_sky:
		vol_sky.cloud_coverage = 0.30
		vol_sky.density = 0.04
		vol_sky.wind_speed = 0.03
		vol_sky.texture_size = 768
		vol_sky.frames_to_update = 64
		vol_sky.sun_disk_scale = 1.5
		vol_sky.ground_color = Color(0.15, 0.18, 0.08)
		# Randomize cloud pattern each session
		vol_sky.time_offset = randf_range(0.0, 100.0)
		vol_sky.wind_direction = randf_range(-PI, PI)
		vol_sky.sun = _sun  # will be set after _sun is created — deferred below
		_sky_mat = vol_sky.sky_material
		_vol_sky = vol_sky
		sky = vol_sky
	else:
		# Fallback to old procedural sky
		var sky_shader: Shader = load("res://shaders/cloud_sky.gdshader")
		_sky_mat = ShaderMaterial.new()
		_sky_mat.shader = sky_shader
		sky = Sky.new()
		sky.sky_material = _sky_mat
		sky.process_mode = Sky.PROCESS_MODE_REALTIME

	_env = Environment.new()
	_env.background_mode       = Environment.BG_SKY
	_env.sky                   = sky
	_env.ambient_light_source  = Environment.AMBIENT_SOURCE_SKY
	_env.ambient_light_sky_contribution = 0.72  # under-canopy needs sky bounce
	_env.tonemap_mode          = Environment.TONE_MAPPER_AGX
	_env.tonemap_white         = 6.0
	_env.glow_enabled          = true
	_env.glow_intensity        = 0.4
	_env.glow_strength         = 0.6
	_env.glow_bloom            = 0.10     # soft spread — impressionist without milky wash
	_env.glow_blend_mode       = Environment.GLOW_BLEND_MODE_SCREEN  # 4.6: blends before tonemap
	_env.glow_hdr_threshold    = 1.2      # above mid-luminance only
	_env.glow_hdr_scale        = 0.4
	_env.glow_hdr_luminance_cap = 8.0
	_env.ssao_enabled          = true
	_env.ssao_detail           = 0.5
	_env.ssil_enabled          = true
	_env.ssil_radius           = 3.0    # meters — moderate reach for under-canopy bounce
	_env.ssil_intensity        = 0.6    # conservative — was causing yellow shield artifacts pre-overhaul
	_env.ssil_normal_rejection = 1.2
	_env.ssr_enabled           = false   # causes multi-colored artifacts on water from aerial view
	_env.sdfgi_enabled         = true
	_env.sdfgi_cascades        = 6      # large outdoor scene needs range
	_env.sdfgi_min_cell_size   = 0.5    # ~0.5m matches our atlas resolution
	_env.sdfgi_energy          = 1.0    # full GI bounce for natural lighting
	_env.sdfgi_normal_bias     = 1.1
	_env.sdfgi_probe_bias      = 1.1
	_env.sdfgi_bounce_feedback = 0.3    # subtle multi-bounce
	_env.sdfgi_read_sky_light  = true
	_env.sdfgi_use_occlusion   = true
	_env.adjustment_enabled    = true
	_env.adjustment_brightness = 1.06
	_env.fog_enabled           = false  # volumetric fog handles aerial perspective

	# Volumetric fog — realistic NYC atmospheric haze + light shafts
	# NYC clear-day visibility: 10-16km. At 1-2km (building distance),
	# aerial perspective should noticeably desaturate + lighten objects.
	_env.volumetric_fog_enabled = true
	_env.volumetric_fog_density = 0.003  # CD-style dense atmosphere — visible god-ray shafts under canopy
	_env.volumetric_fog_albedo = Color(0.92, 0.93, 0.96)  # slightly blue-white haze
	_env.volumetric_fog_emission = Color(0.75, 0.80, 0.88)
	_env.volumetric_fog_emission_energy = 0.06
	_env.volumetric_fog_anisotropy = 0.35
	_env.volumetric_fog_length = 800.0  # reach the buildings (was 100m!)
	_env.volumetric_fog_detail_spread = 2.0
	_env.volumetric_fog_ambient_inject = 0.12
	_env.volumetric_fog_gi_inject = 0.25  # higher now that SDFGI provides real GI data
	_env.volumetric_fog_sky_affect = 0.25
	_env.volumetric_fog_temporal_reprojection_enabled = false

	var world_env := WorldEnvironment.new()
	world_env.environment = _env
	add_child(world_env)

	_sun = DirectionalLight3D.new()
	_sun.shadow_enabled = true
	_sun.light_angular_distance = 1.5  # soft penumbra — velvety shadows
	_sun.light_volumetric_fog_energy = 5.0  # stronger god rays for Crimson-Desert-style forest shafts
	_sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	_sun.directional_shadow_split_1      = 0.05   # tighter first cascade for near-field detail
	_sun.directional_shadow_split_2      = 0.15
	_sun.directional_shadow_split_3      = 0.4
	# 150m max (was 300): LOD0 fade ends at 100m, so 150m keeps full
	# shadow coverage through LOD0 with a small buffer. Halving the
	# distance halves the cascade area → ~half as many LOD0 trees draw
	# into each cascade per frame. With 6808 LOD0 shadow casters in the
	# Ramble × 4 cascades, this is the biggest per-frame win available
	# without dropping a quality knob.
	_sun.directional_shadow_max_distance = 150.0
	_sun.directional_shadow_pancake_size = 20.0
	_sun.directional_shadow_blend_splits = true  # smooth the 7.5m/22.5m/60m cascade boundaries
	add_child(_sun)

	# Perf-experiment overrides (scripts/perf_bisect.sh)
	if _cli_shadow_dist > 0.0:
		_sun.directional_shadow_max_distance = _cli_shadow_dist
		print("[DIAG] shadow max distance = %.0f" % _cli_shadow_dist)
	if _cli_shadow_size > 0:
		RenderingServer.directional_shadow_atlas_set_size(_cli_shadow_size, true)
		print("[DIAG] directional shadow atlas = %d px" % _cli_shadow_size)
	if _cli_shadow_filter >= 0:
		RenderingServer.directional_soft_shadow_filter_set_quality(
			clampi(_cli_shadow_filter, 0, 5))
		print("[DIAG] directional soft shadow filter quality = %d" % _cli_shadow_filter)

	# Wire sun to volumetric cloud sky (deferred because _sun created after sky)
	if vol_sky:
		vol_sky.sun = _sun

	print("Sky: day/night cycle — start 6:00 AM")


# ---------------------------------------------------------------------------
# Terrain ground – Terrain3D clipmap
# ---------------------------------------------------------------------------
func _set_terrain_param(param: StringName, value) -> void:
	## Set a shader parameter on the Terrain3D override shader.
	## set_shader_param() warns "should never be used outside editor" but it's the
	## only method that correctly routes params to the override shader material.
	if _terrain3d and _terrain3d.material:
		_terrain3d.material.set_shader_param(param, value)

func _setup_ground() -> void:
	# ---- Terrain3D (geometry clipmap + built-in collision) ----
	_terrain3d = $Terrain3D if has_node("Terrain3D") else null
	if _terrain3d:
		var n_regions: int = _terrain3d.data.get_regions_active().size()
		print("Terrain3D: %d regions, spacing=%.4f" % [n_regions, _terrain3d.vertex_spacing])
		_terrain3d.collision.radius = 128

		# Apply our custom shader override — keeps Terrain3D clipmap vertex,
		# replaces fragment with zone/weather/season-aware Central Park texturing
		var override_shader: Shader = load("res://shaders/terrain3d_override.gdshader")
		if override_shader:
			_terrain3d.material.shader_override = override_shader
			_terrain3d.material.shader_override_enabled = true
			print("Terrain3D: shader override applied (terrain3d_override.gdshader)")
		else:
			push_warning("Terrain3D: override shader not found, using default auto-shader")

	# World size for data map UV lookups in overlay shader
	_set_terrain_param(&"world_size", _hm_world_size)

	# ---- Terrain3D native textures handle all surface materials via control map ----
	# The shader override only needs data maps for custom overlays (seasons, weather, canopy)
	# Textures (grass, meadow, rock, dirt, shore, asphalt, concrete, paving, gravel, wood)
	# are registered in terrain_assets.tres and painted via control map — no manual loading needed.

	# Anti-tiling noise texture for macro variation
	var noise_tex := _load_img_tex("res://textures/tile_noise.png")
	if noise_tex:
		_set_terrain_param(&"noise_texture", noise_tex)

	# Configure macro variation for distance pattern breakup
	_set_terrain_param(&"enable_macro_variation", true)
	_set_terrain_param(&"macro_variation1", Vector3(0.90, 0.92, 0.88))
	_set_terrain_param(&"macro_variation2", Vector3(1.0, 0.97, 0.95))
	_set_terrain_param(&"noise1_scale", 0.04)
	_set_terrain_param(&"noise2_scale", 0.076)

	# Autoshader: grass on flat, rock on slopes
	_set_terrain_param(&"auto_slope", 2.0)
	_set_terrain_param(&"auto_base_texture", 0)      # grass
	_set_terrain_param(&"auto_overlay_texture", 2)    # rock
	_set_terrain_param(&"blend_sharpness", 0.5)

	print("Ground: Terrain3D native textures (10 slots) + overlay shader")


# ---------------------------------------------------------------------------
# GPU Particle Grass (Terrain3D-based)
# ---------------------------------------------------------------------------
var _grass_particle_nodes: Array[Node3D] = []
var _grass_tuft_builder: Node3D  # Tier 2 static MultiMesh tuft chunks
var _gpu_grass_nodes: Array = []  # GPUGrass compute-driven grass nodes (one per biome)
var _landuse_texture: Texture2D  # cached for grass particle system

# Biome definitions for multi-layer grass particles.
# 4 Tuft layers with PBR textures + alpha cutout — one per biome type, non-overlapping.
# Tuft meshes have embedded albedo textures with alpha for realistic blade-level detail
# and blending with the terrain underneath. Undergrowth system provides taller accents.
const GRASS_BIOMES := [
	{  # Per-blade instancing: one quad strip per particle, not crossed cards.
		# Blade_Lawn: 2 segments, 7.6cm tall, 12mm wide, 4 tris
		# cell_width 11 × grid_width 11 → max_dist 60.5m. Dither fade-out begins
		# at 60% × 60.5m ≈ 36m. Recovers most of the 80m coverage the GDExtension
		# Tier 1 used to provide, before the 2026-05-09 unification to particles.
		"name": "Lawn", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Blade_Lawn.glb",
		# Lawn: densest base coverage (maintained Kentucky bluegrass turf).
		"spacing": 0.10, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
	{  # Blade_Shade: 3 segments, 12cm tall, 10mm wide, 6 tris
		"name": "Shade", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Blade_Shade.glb",
		# Shade: sparser woodland floor (less light, fewer blades).
		"spacing": 0.16, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
	{  # Blade_Wild: 4 segments, 25cm tall, 15mm wide, 8 tris
		"name": "Wild", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Blade_Wild.glb",
		# Wild meadow: clumpy native grasses, gaps between bunches.
		"spacing": 0.19, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.005, 0),
	},
	{  # Blade_Sedge: 3 segments, 16cm tall, 9mm wide, 6 tris
		"name": "Sedge", "biome_id": 3,
		"mesh_path": "res://models/vegetation/Blade_Sedge.glb",
		# Sedge: waterside, moderate density.
		"spacing": 0.16, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
]

# Tier 0: near-field blade variants (0-6m). Complement Tier 1 with different
# blade shapes for botanical close-up variety at meditation walking pace.
# 2 variants per biome (thin + wide) × 4 biomes = 8 particle systems.
const GRASS_TIER0 := [
	{  # Fine KBG blade — half the width of Tier 1 Blade_Lawn
		"name": "Lawn_T0_Thin", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Blade_Lawn_Thin.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.6,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.002, 0),
	},
	{  # Ryegrass broad blade — wider, shorter than Tier 1
		"name": "Lawn_T0_Wide", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Blade_Lawn_Wide.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.6,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.002, 0),
	},
	{  # Fine fescue — very thin, delicate shade grass
		"name": "Shade_T0_Thin", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Blade_Shade_Thin.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.6,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.002, 0),
	},
	{  # Broad woodland floor leaf
		"name": "Shade_T0_Wide", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Blade_Shade_Wide.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.6,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.002, 0),
	},
	{  # Switchgrass — narrow, tall
		"name": "Wild_T0_Thin", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Blade_Wild_Thin.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.004, 0),
	},
	{  # Big Bluestem — wide, shorter
		"name": "Wild_T0_Wide", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Blade_Wild_Wide.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.004, 0),
	},
	{  # Rush needle — very thin, stiff
		"name": "Sedge_T0_Thin", "biome_id": 3,
		"mesh_path": "res://models/vegetation/Blade_Sedge_Thin.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
	{  # Tussock broad leaf
		"name": "Sedge_T0_Wide", "biome_id": 3,
		"mesh_path": "res://models/vegetation/Blade_Sedge_Wide.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
	# Curved variants retired 2026-05-09 — the per-blade random_rotation,
	# random_spacing, and tilt already provide silhouette variety; a third
	# mesh per biome added 4 layers worth of GPUParticles3D nodes for
	# negligible visual gain.
]

# Tier 0 botanical accents — ground-level details that give each biome
# distinct near-field character. Very sparse (0.12-0.25m spacing).
const GRASS_ACCENTS := [
	{  # White clover rosettes in maintained lawns
		"name": "Accent_Clover", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Accent_Clover.glb",
		"spacing": 0.15, "cell_width": 4.0, "grid_width": 3,
		"process_fps": 15,
		"random_spacing": 0.8,
		"min_scale": Vector3(0.7, 0.7, 0.7),
		"max_scale": Vector3(1.5, 1.5, 1.5),
		"position_offset": Vector3(0, -0.001, 0),
	},
	{  # Dandelion rosettes + yellow flowers in lawns
		"name": "Accent_Dandelion", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Accent_Dandelion.glb",
		"spacing": 0.25, "cell_width": 4.0, "grid_width": 3,
		"process_fps": 15,
		"random_spacing": 0.8,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.3, 1.3, 1.3),
		"position_offset": Vector3(0, -0.001, 0),
	},
	{  # Fallen leaf litter on woodland floor
		"name": "Accent_DriedLeaf", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Accent_DriedLeaf.glb",
		"spacing": 0.12, "cell_width": 4.0, "grid_width": 3,
		"process_fps": 15,
		"random_spacing": 0.8,
		"min_scale": Vector3(0.5, 0.5, 0.5),
		"max_scale": Vector3(1.6, 1.6, 1.6),
		"position_offset": Vector3(0, 0.0, 0),
	},
	{  # Dried grass seed heads in wild meadow
		"name": "Accent_SeedHead", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Accent_SeedHead.glb",
		"spacing": 0.20, "cell_width": 4.0, "grid_width": 3,
		"process_fps": 15,
		"random_spacing": 0.7,
		"min_scale": Vector3(0.5, 0.5, 0.5),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
]

func _setup_grass_particles() -> void:
	## Multi-biome grass: Terrain3D particle layers filtered by zone.
	## Tier 1 (GRASS_BIOMES): 0-22m, base coverage with one blade per biome.
	## Tier 0 (GRASS_TIER0): 0-6m, near-field variants for close-up variety.
	## Accents (GRASS_ACCENTS): 0-6m, sparse botanical details per biome.
	var gp_script = load("res://grass_particles.gd")
	var proc_shader: Shader = load("res://shaders/grass_particles.gdshader")
	var render_shader: Shader = load("res://shaders/grass_particle_render.gdshader")
	if not gp_script or not proc_shader or not render_shader:
		push_warning("Grass particle scripts/shaders not found")
		return

	# Shared noise texture (reused across all biome layers)
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_CELLULAR
	noise.frequency = 0.0145
	noise.cellular_return_type = FastNoiseLite.RETURN_CELL_VALUE
	var noise_tex := NoiseTexture2D.new()
	noise_tex.seamless = true
	noise_tex.noise = noise

	var all_grass_layers: Array = []
	all_grass_layers.append_array(GRASS_BIOMES)   # Tier 1: 0-22m base coverage per biome
	all_grass_layers.append_array(GRASS_TIER0)    # Tier 0: 0-6m near-field variants
	all_grass_layers.append_array(GRASS_ACCENTS)  # 0-6m botanical detail

	for biome in all_grass_layers:
		# Load tuft GLB via Godot's native load()
		var scene = load(biome.mesh_path)
		if not scene:
			push_warning("Grass tuft not found: %s — skipping biome %s" % [
				biome.mesh_path, biome.name])
			continue
		var inst = scene.instantiate()
		var tuft_mesh: Mesh = null
		var albedo_tex: Texture2D = null
		# Check if root itself is a MeshInstance3D (custom GLBs)
		var mesh_node: MeshInstance3D = null
		if inst is MeshInstance3D:
			mesh_node = inst
		else:
			for child in inst.get_children():
				if child is MeshInstance3D:
					mesh_node = child
					break
		if mesh_node and mesh_node.mesh:
			tuft_mesh = mesh_node.mesh
			var mat = tuft_mesh.surface_get_material(0)
			if mat is BaseMaterial3D and mat.albedo_texture:
				albedo_tex = mat.albedo_texture
		inst.queue_free()
		if not tuft_mesh:
			push_warning("No mesh in %s" % biome.mesh_path)
			continue

		# Create particle controller node
		var gp: Node3D = Node3D.new()
		gp.set_script(gp_script)
		gp.name = "Grass_%s" % biome.name
		gp.terrain = _terrain3d
		gp.instance_spacing = biome.spacing
		gp.cell_width = biome.cell_width
		gp.grid_width = biome.grid_width
		gp.near_cull_distance = biome.get("min_distance", 0.0)
		gp.process_fixed_fps = biome.get("process_fps", 30)
		gp.shadow_mode = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		gp.mesh = tuft_mesh

		# Process material — particle placement + zone filtering
		var proc_mat := ShaderMaterial.new()
		proc_mat.shader = proc_shader
		proc_mat.set_shader_parameter("main_noise", noise_tex)
		proc_mat.set_shader_parameter("main_noise_scale", 0.01)
		proc_mat.set_shader_parameter("position_offset", biome.position_offset)
		proc_mat.set_shader_parameter("align_to_normal", true)
		proc_mat.set_shader_parameter("normal_strength", 0.3)
		proc_mat.set_shader_parameter("random_rotation", true)
		proc_mat.set_shader_parameter("random_spacing", biome.get("random_spacing", 0.5))
		proc_mat.set_shader_parameter("min_scale", biome.min_scale)
		proc_mat.set_shader_parameter("max_scale", biome.max_scale)
		proc_mat.set_shader_parameter("wind_speed", 0.025)
		proc_mat.set_shader_parameter("wind_strength", 1.0)
		proc_mat.set_shader_parameter("wind_dithering", 4.0)
		proc_mat.set_shader_parameter("wind_direction", Vector2(1, 1))
		proc_mat.set_shader_parameter("clod_scale_boost", 0.1)
		proc_mat.set_shader_parameter("surface_slope_min", 0.85)
		proc_mat.set_shader_parameter("distance_fade_ammount", 0.60)
		proc_mat.set_shader_parameter("biome_id", biome.biome_id)
		proc_mat.set_shader_parameter("world_size", _hm_world_size)
		if _landuse_texture:
			proc_mat.set_shader_parameter("landuse_map", _landuse_texture)
		if _park_loader and _park_loader._canopy_texture:
			proc_mat.set_shader_parameter("canopy_map", _park_loader._canopy_texture)
		gp.process_material = proc_mat

		# Render material — textured alpha-scissor grass with wind + seasons
		var render_mat := ShaderMaterial.new()
		render_mat.shader = render_shader
		if albedo_tex:
			render_mat.set_shader_parameter("use_texture", true)
			render_mat.set_shader_parameter("grass_albedo", albedo_tex)
		else:
			render_mat.set_shader_parameter("use_texture", false)
		# Load per-blade normal map if it exists alongside albedo
		var mesh_name: String = biome.mesh_path.get_file().get_basename()
		var nrm_path := "res://textures/grass/%s_normal.png" % mesh_name
		var nrm_tex: Texture2D = null
		if ResourceLoader.exists(nrm_path):
			nrm_tex = load(nrm_path)
		if nrm_tex:
			render_mat.set_shader_parameter("grass_normal", nrm_tex)
			render_mat.set_shader_parameter("has_normal_map", true)
		gp.mesh_material_override = render_mat

		# Pass zone textures for per-frame RenderingServer updates
		if _landuse_texture:
			gp.landuse_texture = _landuse_texture
		if _park_loader and _park_loader._canopy_texture:
			gp.canopy_texture = _park_loader._canopy_texture
		gp.world_size = _hm_world_size

		add_child(gp)
		_grass_particle_nodes.append(gp)
		# Debug: verify particles are actually set up correctly
		var pnodes: Array = gp.get("particle_nodes")
		var n_nodes := pnodes.size() if pnodes else 0
		var first_mesh_ok := false
		var first_mat_ok := false
		var first_amount := 0
		if pnodes and pnodes.size() > 0:
			var p0: GPUParticles3D = pnodes[0]
			first_mesh_ok = p0.draw_pass_1 != null
			first_mat_ok = p0.material_override != null
			first_amount = p0.amount
		print("Grass [%s]: spacing=%.2f biome_id=%d mesh=%s (%d tris) nodes=%d mesh_ok=%s mat_ok=%s amount=%d" % [
			biome.name, biome.spacing, biome.biome_id, biome.mesh_path,
			tuft_mesh.get_faces().size() / 3 if tuft_mesh.get_faces().size() > 0 else 0,
			n_nodes, first_mesh_ok, first_mat_ok, first_amount])


# Tier 2 tuft meshes: crossed-card tufts for static MultiMesh chunks (13-70m)
const TUFT_BIOMES := {
	0: "res://models/vegetation/Tuft_Tiny.glb",      # lawn
	1: "res://models/vegetation/Tuft_Woodland.glb",   # shade
	2: "res://models/vegetation/Tuft_Wild.glb",       # wild
	3: "res://models/vegetation/Tuft_Meadow.glb",     # sedge
}

func _setup_grass_tuft_chunks() -> void:
	## Build static Tier 2 MultiMesh chunks of crossed-card tufts.
	## These render at 15-55m, bridging GPU particle blades and terrain impostor.
	var builder_script = load("res://grass_tuft_builder.gd")
	var tuft_shader: Shader = load("res://shaders/grass_tuft_render.gdshader")
	if not builder_script or not tuft_shader:
		push_warning("Grass tuft builder script/shader not found")
		return

	var builder: Node3D = Node3D.new()
	builder.set_script(builder_script)
	builder.name = "GrassTuftChunks"
	builder.terrain = _terrain3d
	builder.world_size = _hm_world_size
	builder.render_shader = tuft_shader

	# Load landuse image for CPU-side zone sampling
	if _landuse_texture:
		builder.landuse_image = _landuse_texture.get_image()
	# Load canopy image
	if _park_loader and _park_loader._canopy_texture:
		builder.canopy_image = _park_loader._canopy_texture.get_image()

	# Load tuft meshes and textures per biome
	for biome_id in TUFT_BIOMES:
		var path: String = TUFT_BIOMES[biome_id]
		var scene = load(path)
		if not scene:
			push_warning("Tuft mesh not found: %s" % path)
			continue
		var inst = scene.instantiate()
		var mesh_node: MeshInstance3D = null
		if inst is MeshInstance3D:
			mesh_node = inst
		else:
			for child in inst.get_children():
				if child is MeshInstance3D:
					mesh_node = child
					break
		if mesh_node and mesh_node.mesh:
			builder.tuft_meshes[biome_id] = mesh_node.mesh
			var mat = mesh_node.mesh.surface_get_material(0)
			if mat is BaseMaterial3D and mat.albedo_texture:
				builder.tuft_textures[biome_id] = mat.albedo_texture
		inst.queue_free()

	add_child(builder)
	_grass_tuft_builder = builder
	builder.build_all_chunks()


func _setup_gpu_grass() -> void:
	## GPU compute-driven grass using GPUGrass GDExtension.
	## World-fixed placement, no camera-following grid, no rolling boundary.
	if not ClassDB.class_exists("GPUGrass"):
		push_warning("GPUGrass extension not loaded — skipping GPU grass")
		return

	# Bake heightmap to a 2048×2048 RF texture for compute shader sampling.
	# Uses the raw _hm_data array (bilinear interpolation) for speed.
	var hm_res := 2048
	var hm_img := Image.create(hm_res, hm_res, false, Image.FORMAT_RF)
	if not _hm_data.is_empty():
		var half := _hm_world_size * 0.5
		var inv_ws := 1.0 / _hm_world_size
		var w_m1 := _hm_width - 1
		var d_m1 := _hm_depth - 1
		for pz in range(hm_res):
			var wz := float(pz) / float(hm_res - 1) * _hm_world_size - half
			var zi := (wz + half) * inv_ws * d_m1
			var zi0 := clampi(int(zi), 0, d_m1 - 1)
			var fz := zi - zi0
			for px in range(hm_res):
				var wx := float(px) / float(hm_res - 1) * _hm_world_size - half
				var xi := (wx + half) * inv_ws * w_m1
				var xi0 := clampi(int(xi), 0, w_m1 - 1)
				var fx := xi - xi0
				var h00 := _hm_data[zi0 * _hm_width + xi0]
				var h10 := _hm_data[zi0 * _hm_width + xi0 + 1]
				var h01 := _hm_data[(zi0 + 1) * _hm_width + xi0]
				var h11 := _hm_data[(zi0 + 1) * _hm_width + xi0 + 1]
				var h := h00 * (1.0 - fx) * (1.0 - fz) + h10 * fx * (1.0 - fz) + h01 * (1.0 - fx) * fz + h11 * fx * fz
				hm_img.set_pixel(px, pz, Color(h, 0, 0, 1))
		print("GPU grass: baked heightmap %dx%d" % [hm_res, hm_res])
	else:
		push_warning("GPU grass: no heightmap data — blades will be at Y=0")
	var hm_tex := ImageTexture.create_from_image(hm_img)

	# Per-biome GPU grass configuration
	# Each biome gets its own GPUGrass node with appropriate blade mesh,
	# spacing, and instance budget proportional to zone coverage area.
	var biome_configs := [
		{
			"name": "Lawn", "biome_id": 0,
			"mesh": "res://models/vegetation/Blade_Lawn.glb",
			"spacing": 0.12, "max_instances": 600000, "max_distance": 80.0,
		},
		{
			"name": "Shade", "biome_id": 1,
			"mesh": "res://models/vegetation/Blade_Shade.glb",
			"spacing": 0.15, "max_instances": 250000, "max_distance": 80.0,
		},
		{
			"name": "Wild", "biome_id": 2,
			"mesh": "res://models/vegetation/Blade_Wild.glb",
			"spacing": 0.14, "max_instances": 120000, "max_distance": 80.0,
		},
		{
			"name": "Sedge", "biome_id": 3,
			"mesh": "res://models/vegetation/Blade_Sedge.glb",
			"spacing": 0.16, "max_instances": 80000, "max_distance": 80.0,
		},
	]

	var render_shader: Shader = load("res://shaders/grass_particle_render.gdshader")

	for cfg in biome_configs:
		var blade_scene = load(cfg.mesh)
		if not blade_scene:
			push_warning("GPU grass: %s not found" % cfg.mesh)
			continue
		var blade_inst = blade_scene.instantiate()
		var blade_mesh: Mesh = null
		var albedo_tex: Texture2D = null
		var mesh_node: MeshInstance3D = null
		if blade_inst is MeshInstance3D:
			mesh_node = blade_inst
		else:
			for child in blade_inst.get_children():
				if child is MeshInstance3D:
					mesh_node = child
					break
		if mesh_node and mesh_node.mesh:
			blade_mesh = mesh_node.mesh
			var mat = blade_mesh.surface_get_material(0)
			if mat is BaseMaterial3D and mat.albedo_texture:
				albedo_tex = mat.albedo_texture
		blade_inst.queue_free()
		# Diagnostic: dump mesh structure so we can compare across biomes
		# (a difference in primitive type / index count would explain why
		# only one biome's indirect-draw MultiMesh actually renders).
		if blade_mesh:
			var sc := blade_mesh.get_surface_count()
			var info := "GPU grass mesh [%s]: surfaces=%d" % [cfg.name, sc]
			for s in sc:
				var arrs: Array = blade_mesh.surface_get_arrays(s)
				var verts: PackedVector3Array = arrs[Mesh.ARRAY_VERTEX] if arrs.size() > Mesh.ARRAY_VERTEX else PackedVector3Array()
				var idx: PackedInt32Array = arrs[Mesh.ARRAY_INDEX] if arrs.size() > Mesh.ARRAY_INDEX and arrs[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
				var prim: int = blade_mesh.surface_get_primitive_type(s)
				info += " | s%d: prim=%d verts=%d idx=%d" % [s, prim, verts.size(), idx.size()]
			print(info)
		if not blade_mesh:
			push_warning("GPU grass: no mesh in %s" % cfg.mesh)
			continue

		var render_mat := ShaderMaterial.new()
		render_mat.shader = render_shader
		if albedo_tex:
			render_mat.set_shader_parameter("use_texture", true)
			render_mat.set_shader_parameter("grass_albedo", albedo_tex)
		else:
			render_mat.set_shader_parameter("use_texture", false)

		var grass: Node3D = ClassDB.instantiate("GPUGrass")
		grass.name = "GPUGrass_%s" % cfg.name
		grass.set("grass_mesh", blade_mesh)
		grass.set("grass_material", render_mat)
		grass.set("max_instances", cfg.max_instances)
		grass.set("spacing", cfg.spacing)
		grass.set("max_distance", cfg.max_distance)
		grass.set("target_biome", cfg.biome_id)
		grass.set("world_size", _hm_world_size)
		grass.set("heightmap_texture", hm_tex)
		if _landuse_texture:
			grass.set("landuse_texture", _landuse_texture)
		if _park_loader and _park_loader._canopy_texture:
			grass.set("canopy_texture", _park_loader._canopy_texture)

		add_child(grass)
		_gpu_grass_nodes.append(grass)
		print("GPU grass [%s]: biome=%d spacing=%.2f instances=%d" % [
			cfg.name, cfg.biome_id, cfg.spacing, cfg.max_instances])


# ---------------------------------------------------------------------------
# Central Park geometry (paths + boundary walls from park_data.json)
# ---------------------------------------------------------------------------
var _park_loader = null

func _setup_park() -> void:
	var loader = load("res://park_loader.gd").new()
	loader.name = "CentralPark"
	if not _hm_data.is_empty():
		loader.set_heightmap(_hm_data, _hm_width, _hm_depth, _hm_world_size)
	# Terrain3D reference for accurate height queries (_terrain_y)
	if _terrain3d:
		loader.terrain3d = _terrain3d
	loader.tree_species_filter = _tree_species_filter
	add_child(loader)
	_park_loader = loader


func _apply_structure_textures() -> void:
	## Load material texture arrays (asphalt, concrete, stone, gravel, wood)
	## used by the terrain shader's structure mask system.
	_set_terrain_param("world_size", _hm_world_size)
	_set_terrain_param("path_tile_m", 2.5)
	var prefixes: Array = [
		"res://textures/Asphalt012_2K-JPG",
		"res://textures/Concrete034_2K-JPG",
		"res://textures/PavingStones130_2K-JPG",
		"res://textures/Gravel021_2K-JPG",
		"res://textures/WoodFloor041_2K-JPG",
	]
	var suffixes: Array = ["_Color.jpg", "_NormalGL.jpg", "_Roughness.jpg"]
	for si in range(3):
		var images: Array[Image] = []
		for pi in range(prefixes.size()):
			var path: String = prefixes[pi] + suffixes[si]
			var img := Image.load_from_file(path)
			if not img:
				push_warning("Structure texture missing: " + path)
				img = Image.create(64, 64, false, Image.FORMAT_RGB8)
			if pi > 0:
				var target_size := images[0].get_size()
				if img.get_size() != target_size:
					img.resize(target_size.x, target_size.y)
				if img.get_format() != images[0].get_format():
					img.convert(images[0].get_format())
			img.generate_mipmaps()
			images.append(img)
		var tex2d_arr := Texture2DArray.new()
		tex2d_arr.create_from_images(images)
		var param_name: String = ["path_alb_arr", "path_nrm_arr", "path_rgh_arr"][si]
		_set_terrain_param(param_name, tex2d_arr)
	print("Terrain: structure material textures loaded")


func _apply_boundary_mask(poly: PackedVector2Array) -> void:
	## Load pre-baked boundary mask or rasterize at runtime.
	## White = inside park, black = outside.
	var img: Image = null

	# Try pre-baked PNG first (generated by convert_to_godot.py at 8192×8192)
	for path in ["res://boundary_mask.png"]:
		var global_path := ProjectSettings.globalize_path(path)
		if FileAccess.file_exists(path):
			img = Image.load_from_file(path)
		elif FileAccess.file_exists(global_path):
			img = Image.load_from_file(global_path)
		if img:
			if img.get_format() != Image.FORMAT_R8:
				img.convert(Image.FORMAT_R8)
			print("Terrain: loaded pre-baked boundary mask %dx%d" % [img.get_width(), img.get_height()])
			break

	# Fallback: runtime scanline rasterization at 1024×1024
	if not img:
		print("Terrain: boundary_mask.png not found — rasterizing at runtime")
		var sz := 1024
		img = Image.create(sz, sz, false, Image.FORMAT_R8)
		img.fill(Color(0, 0, 0))
		var half := _hm_world_size * 0.5
		var n := poly.size()
		for y in range(sz):
			var wz := (float(y) / float(sz) - 0.5) * _hm_world_size
			var crossings := PackedFloat32Array()
			for i in range(n):
				var j := (i + 1) % n
				var zi := poly[i].y
				var zj := poly[j].y
				if (zi > wz) != (zj > wz):
					var t := (wz - zi) / (zj - zi)
					crossings.append(poly[i].x + t * (poly[j].x - poly[i].x))
			var arr: Array = Array(crossings)
			arr.sort()
			for k in range(0, arr.size() - 1, 2):
				var px0 := int(clampf((float(arr[k]) + half) / _hm_world_size * float(sz), 0.0, float(sz - 1)))
				var px1 := int(clampf((float(arr[k + 1]) + half) / _hm_world_size * float(sz), 0.0, float(sz - 1)))
				for px in range(px0, px1 + 1):
					img.set_pixel(px, y, Color(1, 1, 1))

	img.generate_mipmaps()
	var tex := ImageTexture.create_from_image(img)
	_set_terrain_param("park_mask", tex)
	print("Terrain: boundary mask applied (%dx%d)" % [img.get_width(), img.get_height()])


func _apply_landuse_map(zones: Array, water: Array = []) -> void:
	## Load pre-baked landuse map (8192×8192) from landuse_map.png, or fall back
	## to runtime rasterization at 1024×1024 if the pre-baked file is missing.
	## Zone encoding: 0=unzoned (woodland/meadow), 1=garden, 2=grass, 3=pitch,
	## 4=playground, 5=nature_reserve, 6=dog_park, 7=sports, 8=pool, 9=track,
	## 10=wood, 11=forest, 12=water, 13=shore
	var img: Image = null

	# Try pre-baked PNG first (generated by convert_to_godot.py at 8192×8192).
	# ResourceLoader path covers the imported case; FileAccess on the globalize
	# path covers the freshly-generated-but-not-yet-imported case.
	for path in ["res://landuse_map.png"]:
		if ResourceLoader.exists(path):
			var tex2d: Texture2D = load(path)
			if tex2d:
				img = tex2d.get_image()
		if not img:
			var global_path := ProjectSettings.globalize_path(path)
			if FileAccess.file_exists(global_path):
				img = Image.load_from_file(global_path)
		if img:
			# Ensure R8 format for zone ID lookup
			if img.get_format() != Image.FORMAT_R8:
				img.convert(Image.FORMAT_R8)
			print("Terrain: loaded pre-baked landuse map %dx%d" % [img.get_width(), img.get_height()])
			break

	# Fallback: runtime rasterization at 1024×1024
	if not img:
		print("Terrain: landuse_map.png not found — rasterizing at runtime (run convert_to_godot.py to pre-bake)")
		img = _rasterize_landuse_runtime(zones, water)

	var tex := ImageTexture.create_from_image(img)
	_landuse_texture = tex
	_set_terrain_param("landuse_map", tex)

	# Load pre-baked shore distance field for smooth water-to-land transitions
	var shore_path := "res://shore_distance.png"
	var shore_tex: Texture2D = null
	if ResourceLoader.exists(shore_path):
		shore_tex = load(shore_path)
	else:
		var shore_global := ProjectSettings.globalize_path(shore_path)
		if FileAccess.file_exists(shore_global):
			var shore_img := Image.load_from_file(shore_global)
			if shore_img:
				shore_tex = ImageTexture.create_from_image(shore_img)
	if shore_tex:
		_set_terrain_param("shore_distance", shore_tex)
		print("Terrain: loaded shore distance field %dx%d" % [shore_tex.get_width(), shore_tex.get_height()])


func _rasterize_landuse_runtime(zones: Array, water: Array) -> Image:
	## Runtime fallback: scanline-fill landuse zones at 1024×1024.
	var sz := 1024
	var img := Image.create(sz, sz, false, Image.FORMAT_R8)
	img.fill(Color(0, 0, 0))
	var half := _hm_world_size * 0.5

	var _scanline_fill := func(pts: Array, zone_id: int) -> void:
		var min_row := sz
		var max_row := 0
		var poly_x := PackedFloat64Array()
		var poly_z := PackedFloat64Array()
		for pt in pts:
			poly_x.append(float(pt[0]))
			poly_z.append(float(pt[1]))
			var row := int((float(pt[1]) + half) / _hm_world_size * float(sz))
			min_row = min(min_row, row)
			max_row = max(max_row, row)
		min_row = clampi(min_row - 1, 0, sz - 1)
		max_row = clampi(max_row + 1, 0, sz - 1)
		var n := poly_x.size()
		var zone_color := Color(float(zone_id) / 255.0, 0, 0)
		for y in range(min_row, max_row + 1):
			var wz := (float(y) / float(sz)) * _hm_world_size - half
			var crossings := PackedFloat64Array()
			for i in range(n):
				var j := (i + 1) % n
				var zi := poly_z[i]
				var zj := poly_z[j]
				if (zi > wz) != (zj > wz):
					var t := (wz - zi) / (zj - zi)
					crossings.append(poly_x[i] + t * (poly_x[j] - poly_x[i]))
			var arr: Array = Array(crossings)
			arr.sort()
			for k in range(0, arr.size() - 1, 2):
				var px0 := int(clampf((float(arr[k]) + half) / _hm_world_size * float(sz), 0.0, float(sz - 1)))
				var px1 := int(clampf((float(arr[k + 1]) + half) / _hm_world_size * float(sz), 0.0, float(sz - 1)))
				for px in range(px0, px1 + 1):
					img.set_pixel(px, y, zone_color)

	var filled := 0
	for zone in zones:
		var zone_type: String = zone.get("type", "")
		var zone_id: int = LANDUSE_TYPE_TO_ID.get(zone_type, 0)
		if zone_id == 0:
			continue
		var pts: Array = zone.get("points", [])
		if pts.size() < 3:
			continue
		_scanline_fill.call(pts, zone_id)
		filled += 1

	var water_count := 0
	for body in water:
		var pts: Array = body.get("points", [])
		if pts.size() < 3:
			continue
		_scanline_fill.call(pts, 12)
		water_count += 1

	if water_count > 0:
		var shore_pixels := PackedVector2Array()
		var SHORE_R := 3
		for y in range(sz):
			for x in range(sz):
				var v := int(img.get_pixel(x, y).r * 255.0 + 0.5)
				if v == 12:
					for dy in range(-SHORE_R, SHORE_R + 1):
						for dx in range(-SHORE_R, SHORE_R + 1):
							if dx * dx + dy * dy > SHORE_R * SHORE_R:
								continue
							var nx := x + dx
							var ny := y + dy
							if nx < 0 or nx >= sz or ny < 0 or ny >= sz:
								continue
							var nv := int(img.get_pixel(nx, ny).r * 255.0 + 0.5)
							if nv != 12 and nv != 13:
								shore_pixels.append(Vector2(nx, ny))
		var shore_color := Color(13.0 / 255.0, 0, 0)
		for sp in shore_pixels:
			img.set_pixel(int(sp.x), int(sp.y), shore_color)

	print("Terrain: runtime landuse %dx%d (%d zones, %d water)" % [sz, sz, filled, water_count])
	return img


func _apply_structure_mask() -> void:
	## Load the LiDAR structure mask (HH-BE difference) and apply it to the terrain shader.
	## Structure pixels get stone/concrete textures instead of grass.
	var mask_path := "res://lidar_data/structure_mask.png"
	var global_path := ProjectSettings.globalize_path(mask_path)
	if not FileAccess.file_exists(mask_path) and not FileAccess.file_exists(global_path):
		print("Terrain: no structure mask found at %s" % mask_path)
		return
	var img := Image.load_from_file(mask_path)
	if not img:
		img = Image.load_from_file(global_path)
	if not img:
		print("Terrain: failed to load structure mask")
		return
	var tex := ImageTexture.create_from_image(img)
	_set_terrain_param("structure_mask", tex)
	print("Terrain: structure mask applied (%dx%d)" % [img.get_width(), img.get_height()])


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
func _setup_player() -> CharacterBody3D:
	var p: CharacterBody3D = load("res://player.gd").new()
	p.name       = "Player"
	if _terrain_only:
		p.position = Vector3(-300.0, _terrain_height(-300.0, 200.0) + 200.0, 200.0)
		p.rotation_degrees.y = 0.0
		p.set_physics_process(false)
	elif _cli_pos_set:
		p.position = Vector3(_cli_pos.x, _terrain_height(_cli_pos.x, _cli_pos.z) + _cli_height, _cli_pos.z)
		p.rotation_degrees.y = _cli_pos.y if _cli_pos.y != 0.0 else 30.0
		if _cli_height > 5.0:
			p.set_physics_process(false)  # disable gravity for elevated shots
	else:
		p.position = Vector3(-480.0, _terrain_height(-480.0, 1020.0) + 1.9, 1020.0)
	if not _cli_pos_set:
		p.rotation_degrees.y = 30.0
	p.terrain_height_fn = Callable(self, "_terrain_height")
	add_child(p)
	if _terrain_only and p.head:
		p.head.rotation_degrees.x = -55.0  # look down at terrain
	elif _cli_pitch != 0.0 and p.head:
		p.head.rotation_degrees.x = _cli_pitch
	return p


# ---------------------------------------------------------------------------
# Dynamic lamppost lighting — pool of OmniLight3D follows player
# ---------------------------------------------------------------------------
func _setup_lamp_lights() -> void:
	# Extract all lamppost world positions from MultiMesh instances
	_lamp_positions = PackedVector3Array()
	for child in _park_loader.get_children():
		if not (child is MultiMeshInstance3D):
			continue
		if not child.name.begins_with("Lampposts"):
			continue
		var mmi: MultiMeshInstance3D = child as MultiMeshInstance3D
		var mm: MultiMesh = mmi.multimesh
		for i in mm.instance_count:
			var xf: Transform3D = mm.get_instance_transform(i)
			# Luminaire globe center at ~3.9m above base (Type B = 4.14m total)
			_lamp_positions.append(xf.origin + Vector3(0, 3.9, 0))
	print("Lamp lights: %d lamppost positions extracted, pool of %d lights" % [
		_lamp_positions.size(), LAMP_LIGHT_COUNT])

	# Create light pool — SpotLight3D pointing downward (lamppost shade)
	for i in LAMP_LIGHT_COUNT:
		var light := SpotLight3D.new()
		light.light_color = Color(1.0, 0.62, 0.22)  # warm sodium vapor — Kent Bloomer luminaire
		light.light_energy = 0.0  # off until positioned
		light.spot_range = 45.0   # wide pool — CP lampposts illuminate ~12m radius from 3.5m height
		light.spot_angle = 75.0   # ~150° cone — directed downward from shade
		light.spot_attenuation = 0.65  # soft quadratic-ish falloff for warm pool edges
		light.shadow_enabled = false  # too expensive for 24 lights
		light.light_bake_mode = Light3D.BAKE_DISABLED
		light.rotation_degrees = Vector3(-90, 0, 0)  # point straight down
		light.name = "LampLight_%d" % i
		add_child(light)
		_lamp_lights.append(light)


func _update_lamp_lights() -> void:
	if _lamp_positions.is_empty() or _lamp_lights.is_empty() or not _player:
		return
	var player_pos := _player.global_position
	# Find closest lamps within 30m
	var dists: Array = []
	var pool_size: int = _lamp_lights.size()
	for i in _lamp_positions.size():
		var d := player_pos.distance_squared_to(_lamp_positions[i])
		if d < 2500.0:  # within 50m
			dists.append([d, i])
	# Only sort if we have more candidates than light slots
	if dists.size() > pool_size:
		dists.sort_custom(func(a, b): return a[0] < b[0])

	# Get current lamp emission energy from day/night cycle
	var night_energy: float = _lamp_emission

	for li in _lamp_lights.size():
		if li < dists.size() and night_energy > 0.1:
			var idx: int = dists[li][1]
			_lamp_lights[li].global_position = _lamp_positions[idx]
			_lamp_lights[li].light_energy = night_energy
		else:
			_lamp_lights[li].light_energy = 0.0


# ---------------------------------------------------------------------------
# HUD: semi-transparent panel, top-left corner
# ---------------------------------------------------------------------------
func _setup_color_grade() -> void:
	## Fullscreen color grade — glowing in the dark: deep darks, luminous color
	var grade_shader: Shader = load("res://shaders/color_grade.gdshader")
	var grade_mat := ShaderMaterial.new()
	grade_mat.shader = grade_shader
	var grade_canvas := CanvasLayer.new()
	grade_canvas.name = "ColorGrade"
	grade_canvas.layer = 100  # on top of everything
	var rect := ColorRect.new()
	rect.material = grade_mat
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	grade_canvas.add_child(rect)
	add_child(grade_canvas)
	print("Post-process: color grade shader applied")



func _cycle_weather() -> void:
	_weather_mgr.cycle(_day_night, _time_of_day, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	_weather_mode = _weather_mgr.mode


## _setup_hud moved to hud_manager.gd







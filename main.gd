extends Node3D

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

# HUD label references kept for per-frame updates
var _player:        CharacterBody3D
var _coord_label:   Label
var _heading_label: Label
var _latlon_label:  Label

# ---------------------------------------------------------------------------
# Day/night cycle
# ---------------------------------------------------------------------------
var _time_of_day: float = 16.0        # start at 4 PM
var _user_gamma: float = 1.0          # user brightness: , = darker, . = brighter
var _time_speed: float  = 0.001      # game-hours per real-second (~400 min full cycle)
var _time_speed_idx: int = 0
var _last_applied_tod: float = -999.0  # tracks last _apply_time_of_day() value
const TIME_SPEEDS: Array = [0.001, 0.01, 0.1, 0.0]
const TIME_SPEED_NAMES: Array = ["1x", "10x", "100x", "Paused"]

var _env: Environment
var _sky_mat: ShaderMaterial
var _vol_sky = null  # clayjohn volumetric cloud sky (if loaded)
var _sun: DirectionalLight3D
var _lamp_emission: float = 0.0  # cached for SpotLight3D pool
var _terrain3d: Terrain3D
var _time_label: Label
var _speed_label: Label
var _location_label: Label

# Dynamic lamppost lighting — pool of SpotLight3D nodes that follow player
var _lamp_lights: Array = []  # Array of SpotLight3D
var _lamp_positions: PackedVector3Array = PackedVector3Array()

var _hud_canvas: CanvasLayer
var _perf_canvas: CanvasLayer
var _perf_label: Label
var _perf_visible := false
var _perf_update_timer := 0.0
const PERF_UPDATE_INTERVAL := 0.25  # update 4x/sec to avoid flicker
var _lamp_light_timer: float = 0.0
var _lightning_timer: float = 0.0
var _lightning_flash: float = 0.0     # 0-1 current flash intensity (decays rapidly)
var _lightning_next: float = 5.0      # seconds until next flash
const LAMP_LIGHT_COUNT := 48
const LAMP_LIGHT_RANGE := 22.0
const LAMP_LIGHT_UPDATE_INTERVAL := 0.5  # seconds between position updates


# Weather particles
var _rain_particles: GPUParticles3D
var _snow_particles: GPUParticles3D
var _leaf_particles: GPUParticles3D  # autumn falling leaves
var _blossom_particles: GPUParticles3D  # spring cherry blossom petals
var _audio_manager = null  # ambient sound (wind, city, water, footsteps)

# 5 keyframes defining the full day/night cycle
# Night (21→5) wraps seamlessly; 8 hours of steady darkness.
var _keyframes: Array = []
const _KF_HOURS: Array = [5.0, 6.5, 12.0, 19.0, 21.0]


var _terrain_only := false
var _weather_mode := "clear"  # clear, rain, thunderstorm, snow, fog

# Wind system — layered crossing breezes
var _wind_vec := Vector2.ZERO   # current wind XZ direction+strength
var _wind_time := 0.0           # accumulated wind time (independent of game clock)
var _wind_override := -1.0      # <0 = auto, 0-1 = manual strength multiplier

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

func _ready() -> void:
	# Check for CLI args early
	var cli_time := ""
	for i in OS.get_cmdline_user_args().size():
		var arg: String = OS.get_cmdline_user_args()[i]
		# Support both "--key value" and "--key=value" formats
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
			_weather_mode = val
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
	# Auto-screenshot only in headless capture mode (--quit-after)
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
	if _weather_mode != "clear":
		print("Weather: %s" % _weather_mode)
	# Enable GPU-based occlusion culling (used by canopy occluders in woodland)
	get_viewport().use_occlusion_culling = true
	var _mt := Time.get_ticks_msec()
	_build_keyframes()
	_load_heightmap()
	_carve_terrain_voids()
	print("main: heightmap + terrain voids: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	_setup_environment()
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
	RenderingServer.global_shader_parameter_add("cloud_speed_g", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.004)
	RenderingServer.global_shader_parameter_add("impostor_brightness", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 1.0)
	print("main: environment: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	# Terrain3D MUST init before park — builders need accurate terrain height
	_setup_ground()
	print("main: Terrain3D setup: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	if not _terrain_only:
		_setup_park()
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
		# GPU particle grass — replaces old hexaquo MultiMesh system
		if _terrain3d:
			_setup_grass_particles()
			# Textures already set on grass process material before add_child()
			print("main: grass particles: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
	_player = _setup_player()
	if _park_loader and _park_loader.boundary_polygon.size() > 2:
		_player.boundary_polygon = _park_loader.boundary_polygon
	# Terrain3D needs the camera for clipmap LOD and dynamic collision
	if _terrain3d and _player and _player.has_node("CameraMount/Camera3D"):
		_terrain3d.set_camera(_player.get_node("CameraMount/Camera3D"))
	_setup_hud()
	_setup_color_grade()
	if not _terrain_only:
		_setup_lamp_lights()
	print("main: total _ready: %d ms" % (Time.get_ticks_msec() - _mt))
	_apply_time_of_day()
	_setup_weather()
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
var _screenshot_timer := 0.0
var _screenshot_done  := false
var _labels_hidden_for_screenshot := false
var _screenshot_counter := 0  # incrementing counter for F12 screenshots
var _auto_screenshot := false  # only auto-capture when --quit-after is used
var _lt_screenshot_pending := false  # debounce for gamepad left trigger screenshots

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

const TOUR_VIEWPOINTS: Array = [
	{"name": "bethesda_fountain", "x": -480.0, "z": 1020.0, "yaw": 180.0},
	{"name": "literary_walk", "x": -600.0, "z": 1420.0, "yaw": 30.0},
	{"name": "great_lawn", "x": -200.0, "z": 0.0, "yaw": 0.0},
	{"name": "conservatory_water", "x": -152.0, "z": 958.0, "yaw": 270.0},
	{"name": "alice_wonderland", "x": -96.0, "z": 869.0, "yaw": 315.0},
	{"name": "balto_south", "x": -473.0, "z": 1430.0, "yaw": 60.0},
	{"name": "the_lake", "x": -560.0, "z": 780.0, "yaw": 60.0},
	{"name": "cherry_hill", "x": -630.0, "z": 880.0, "yaw": 90.0},
	{"name": "cleopatras_needle", "x": 40.0, "z": 360.0, "yaw": 250.0},
	{"name": "ramble", "x": -400.0, "z": 600.0, "yaw": 225.0},
	{"name": "cpw_skyline", "x": -600.0, "z": 1420.0, "yaw": 90.0},
	{"name": "fifth_ave_skyline", "x": 100.0, "z": 200.0, "yaw": 270.0},
	{"name": "north_woods", "x": 600.0, "z": -1315.0, "yaw": 180.0},
	{"name": "reservoir_south", "x": -200.0, "z": -300.0, "yaw": 0.0},
	{"name": "bow_bridge", "x": -540.0, "z": 740.0, "yaw": 310.0},
	{"name": "soccer_fields", "x": 390.0, "z": -1070.0, "yaw": 30.0},
	{"name": "sheep_meadow", "x": -700.0, "z": 1600.0, "yaw": 270.0},
]

const TOUR_ANGLES: Array = [
	{"suffix": "_0", "yaw_offset": 0.0, "pitch": 0.0},    # forward
	{"suffix": "_1", "yaw_offset": -90.0, "pitch": 0.0},   # left 90°
	{"suffix": "_2", "yaw_offset": 0.0, "pitch": -25.0},   # down
	{"suffix": "_aerial30", "yaw_offset": 0.0, "pitch": -55.0, "height": 30.0},   # 30m aerial
	{"suffix": "_aerial80", "yaw_offset": 0.0, "pitch": -75.0, "height": 80.0},   # 80m aerial overview
]

const TOUR_TIMES: Array = [7.0, 12.0, 17.0, 22.0]

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
	for vp in TOUR_VIEWPOINTS:
		for ti in range(TOUR_TIMES.size()):
			for ai in range(TOUR_ANGLES.size()):
				var shot_data: Dictionary = {
					"name": vp["name"],
					"x": float(vp["x"]),
					"z": float(vp["z"]),
					"yaw": float(vp["yaw"]) + float(TOUR_ANGLES[ai]["yaw_offset"]),
					"pitch": float(TOUR_ANGLES[ai]["pitch"]),
					"hour": TOUR_TIMES[ti],
					"filename": "%s_%dh%s" % [vp["name"], int(TOUR_TIMES[ti]), TOUR_ANGLES[ai]["suffix"]],
				}
				if TOUR_ANGLES[ai].has("height"):
					shot_data["height"] = float(TOUR_ANGLES[ai]["height"])
				_tour_shots.append(shot_data)


# Showcase tour — curated shots demonstrating time, weather, and season variety
const SHOWCASE_SHOTS: Array = [
	# Summer golden hour — flagship shot
	{"name": "literary_walk_summer_golden", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 17.5, "season": 1.5, "weather": "clear"},
	# Autumn morning at Bethesda
	{"name": "bethesda_autumn_morning", "x": -480.0, "z": 1020.0, "yaw": 180.0, "pitch": 0.0, "hour": 8.0, "season": 2.5, "weather": "clear"},
	# Winter snow at the Lake — Bow Bridge area
	{"name": "bow_bridge_winter_snow", "x": -540.0, "z": 740.0, "yaw": 310.0, "pitch": 0.0, "hour": 12.0, "season": 3.5, "weather": "snow"},
	# Spring dawn at the Ramble
	{"name": "ramble_spring_dawn", "x": -400.0, "z": 600.0, "yaw": 225.0, "pitch": 0.0, "hour": 6.0, "season": 0.5, "weather": "clear"},
	# Rain at Conservatory Water
	{"name": "conservatory_rain_afternoon", "x": -152.0, "z": 958.0, "yaw": 270.0, "pitch": 0.0, "hour": 15.0, "season": 2.0, "weather": "rain"},
	# Night at Literary Walk — sodium vapor lamps
	{"name": "literary_walk_night", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 22.0, "season": 1.5, "weather": "clear"},
	# Winter fog at Great Lawn
	{"name": "great_lawn_winter_fog", "x": -200.0, "z": 0.0, "yaw": 0.0, "pitch": 0.0, "hour": 7.0, "season": 3.2, "weather": "fog"},
	# Autumn golden hour at Cherry Hill
	{"name": "cherry_hill_autumn_golden", "x": -630.0, "z": 880.0, "yaw": 90.0, "pitch": 0.0, "hour": 17.5, "season": 2.6, "weather": "clear"},
	# Summer noon skyline from Fifth Ave side
	{"name": "fifth_ave_summer_noon", "x": 100.0, "z": 200.0, "yaw": 270.0, "pitch": 0.0, "hour": 12.0, "season": 1.5, "weather": "clear"},
	# Snow at North Woods
	{"name": "north_woods_snow_morning", "x": 600.0, "z": -1315.0, "yaw": 180.0, "pitch": 0.0, "hour": 9.0, "season": 3.5, "weather": "snow"},
	# Spring rain at the Mall
	{"name": "the_mall_spring_rain", "x": -550.0, "z": 1300.0, "yaw": 180.0, "pitch": 0.0, "hour": 14.0, "season": 0.6, "weather": "rain"},
	# Autumn dusk at CPW skyline
	{"name": "cpw_skyline_autumn_dusk", "x": -600.0, "z": 1420.0, "yaw": 90.0, "pitch": 0.0, "hour": 19.0, "season": 2.5, "weather": "clear"},
	# Summer dawn at Reservoir
	{"name": "reservoir_summer_dawn", "x": -200.0, "z": -300.0, "yaw": 0.0, "pitch": -5.0, "hour": 5.5, "season": 1.5, "weather": "clear"},
	# Summer golden hour at Sheep Meadow — mowing stripes visible on green grass
	{"name": "sheep_meadow_summer_golden", "x": -700.0, "z": 1600.0, "yaw": 270.0, "pitch": -3.0, "hour": 18.0, "season": 1.5, "weather": "clear"},
	# Autumn at the Lake
	{"name": "the_lake_autumn_afternoon", "x": -560.0, "z": 780.0, "yaw": 60.0, "pitch": 0.0, "hour": 15.0, "season": 2.7, "weather": "clear"},
	# Spring morning at soccer fields
	{"name": "soccer_fields_spring_morning", "x": 390.0, "z": -1070.0, "yaw": 30.0, "pitch": 0.0, "hour": 9.0, "season": 0.5, "weather": "clear"},
	# Aerial views — looking down from various heights
	# Bethesda Terrace + fountain from 40m — summer noon
	{"name": "bethesda_aerial_40m", "x": -480.0, "z": 1020.0, "yaw": 180.0, "pitch": -70.0, "hour": 12.0, "season": 1.5, "weather": "clear", "height": 40.0},
	# The Lake + Bow Bridge from 80m — autumn afternoon
	{"name": "lake_aerial_80m_autumn", "x": -540.0, "z": 740.0, "yaw": 0.0, "pitch": -80.0, "hour": 15.0, "season": 2.5, "weather": "clear", "height": 80.0},
	# Great Lawn from 100m — summer golden hour
	{"name": "great_lawn_aerial_100m", "x": -100.0, "z": 100.0, "yaw": 0.0, "pitch": -85.0, "hour": 17.5, "season": 1.5, "weather": "clear", "height": 100.0},
	# Conservatory Water from 30m — rainy day
	{"name": "conservatory_aerial_30m_rain", "x": -152.0, "z": 958.0, "yaw": 90.0, "pitch": -60.0, "hour": 14.0, "season": 2.0, "weather": "rain", "height": 30.0},
	# North Woods from 60m — winter snow
	{"name": "north_woods_aerial_60m_snow", "x": 600.0, "z": -1315.0, "yaw": 180.0, "pitch": -75.0, "hour": 10.0, "season": 3.5, "weather": "snow", "height": 60.0},
	# Reservoir from 120m — dawn overview
	{"name": "reservoir_aerial_120m_dawn", "x": -200.0, "z": -400.0, "yaw": 0.0, "pitch": -80.0, "hour": 6.0, "season": 1.5, "weather": "clear", "height": 120.0},
]


func _build_showcase_shots() -> void:
	for shot in SHOWCASE_SHOTS:
		_tour_shots.append(shot.duplicate())
		_tour_shots.back()["filename"] = shot["name"]


# README candidate shots — bright, well-lit, showcasing variety.
# Best 4 chosen for README.md. Saves to screenshots/.
const README_SHOTS: Array = [
	# --- SUMMER ---
	# Literary Walk summer midday — flagship tree-lined path
	{"name": "readme_literary_walk_summer", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 11.0, "season": 1.5, "weather": "clear"},
	# Ramble summer late morning — dappled forest walk
	{"name": "readme_ramble_summer", "x": -350.0, "z": 650.0, "yaw": 200.0, "pitch": 0.0, "hour": 10.5, "season": 1.5, "weather": "clear"},
	# Bethesda Terrace summer noon — fountain + terrace
	{"name": "readme_bethesda_summer", "x": -480.0, "z": 1020.0, "yaw": 350.0, "pitch": -5.0, "hour": 12.0, "season": 1.5, "weather": "clear"},
	# Sheep Meadow summer afternoon — open green with skyline
	{"name": "readme_sheep_meadow_summer", "x": -750.0, "z": 1700.0, "yaw": 120.0, "pitch": 0.0, "hour": 14.0, "season": 1.5, "weather": "clear"},
	# Bow Bridge summer — lake + bridge
	{"name": "readme_bow_bridge_summer", "x": -540.0, "z": 740.0, "yaw": 310.0, "pitch": -3.0, "hour": 13.0, "season": 1.5, "weather": "clear"},
	# CPW skyline summer golden hour
	{"name": "readme_cpw_skyline_golden", "x": -600.0, "z": 1420.0, "yaw": 90.0, "pitch": 0.0, "hour": 16.5, "season": 1.5, "weather": "clear"},
	# --- AUTUMN ---
	# Literary Walk autumn midday — fall colors on the Mall
	{"name": "readme_literary_walk_autumn", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 12.0, "season": 2.5, "weather": "clear"},
	# Sheep Meadow autumn afternoon — foliage + skyline
	{"name": "readme_sheep_meadow_autumn", "x": -750.0, "z": 1700.0, "yaw": 120.0, "pitch": 0.0, "hour": 14.0, "season": 2.3, "weather": "clear"},
	# Cherry Hill autumn — fall trees + lake view
	{"name": "readme_cherry_hill_autumn", "x": -630.0, "z": 880.0, "yaw": 90.0, "pitch": -3.0, "hour": 13.0, "season": 2.5, "weather": "clear"},
	# North Woods autumn — dense forest fall color
	{"name": "readme_north_woods_autumn", "x": 600.0, "z": -1315.0, "yaw": 180.0, "pitch": 0.0, "hour": 11.0, "season": 2.5, "weather": "clear"},
	# --- WINTER ---
	# Great Lawn winter snow midday — open space + skyline
	{"name": "readme_great_lawn_snow", "x": -99.0, "z": 173.0, "yaw": 270.0, "pitch": 0.0, "hour": 12.0, "season": 3.5, "weather": "snow"},
	# Bow Bridge winter snow — snowy bridge over lake
	{"name": "readme_bow_bridge_snow", "x": -540.0, "z": 740.0, "yaw": 310.0, "pitch": -3.0, "hour": 11.0, "season": 3.5, "weather": "snow"},
	# Literary Walk winter noon — bare elms, snow-covered
	{"name": "readme_literary_walk_winter", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 12.0, "season": 3.5, "weather": "snow"},
	# --- SPRING ---
	# Cherry Hill spring midday — blossoms + lake
	{"name": "readme_cherry_hill_spring", "x": -630.0, "z": 880.0, "yaw": 90.0, "pitch": -3.0, "hour": 11.0, "season": 0.5, "weather": "clear"},
	# Conservatory Water spring afternoon
	{"name": "readme_conservatory_spring", "x": -152.0, "z": 958.0, "yaw": 200.0, "pitch": -3.0, "hour": 13.0, "season": 0.5, "weather": "clear"},
	# --- WEATHER ---
	# Bethesda rain afternoon — moody weather showcase
	{"name": "readme_bethesda_rain", "x": -480.0, "z": 1020.0, "yaw": 350.0, "pitch": -5.0, "hour": 13.0, "season": 1.5, "weather": "rain"},
	# North Woods fog late morning
	{"name": "readme_north_woods_fog", "x": 850.0, "z": -1300.0, "yaw": 45.0, "pitch": 0.0, "hour": 10.0, "season": 1.5, "weather": "fog"},
	# --- GOLDEN HOUR ---
	# Sheep Meadow golden hour — warm light across open meadow
	{"name": "readme_sheep_golden", "x": -700.0, "z": 1600.0, "yaw": 270.0, "pitch": -3.0, "hour": 16.5, "season": 1.5, "weather": "clear"},
	# Lake autumn golden hour
	{"name": "readme_lake_autumn_golden", "x": -560.0, "z": 780.0, "yaw": 60.0, "pitch": 0.0, "hour": 16.0, "season": 2.5, "weather": "clear"},
	# Reservoir autumn afternoon — water + fall foliage + skyline
	{"name": "readme_reservoir_autumn", "x": -200.0, "z": -300.0, "yaw": 0.0, "pitch": -2.0, "hour": 14.0, "season": 2.5, "weather": "clear"},
]

func _build_readme_shots() -> void:
	_tour_save_dir = "screenshots"
	for shot in README_SHOTS:
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
	# --- Tour mode state machine ---
	if _tour_mode:
		if _hud_canvas and _hud_canvas.visible:
			_hud_canvas.visible = false  # hide HUD for clean screenshots
			_set_labels_visible(false)
		if _perf_canvas and _perf_canvas.visible:
			_perf_canvas.visible = false
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
		_apply_time_of_day()
		_update_hud()
		return

	# Auto-screenshot for headless capture (only with --quit-after)
	if not _screenshot_done and _auto_screenshot:
		_screenshot_timer += delta
		if _screenshot_timer <= delta and _player:
			_player.set_physics_process(false)
			_player.velocity = Vector3.ZERO
		if _screenshot_timer >= 6.0 and _hud_canvas and _hud_canvas.visible:
			_hud_canvas.visible = false  # hide HUD before capture
		if _screenshot_timer >= 6.0 and _perf_canvas and _perf_canvas.visible:
			_perf_canvas.visible = false
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
			if _hud_canvas:
				_hud_canvas.visible = true  # restore HUD after capture
				_set_labels_visible(true)
	# Update lamp lights every 0.5s
	_lamp_light_timer += delta
	if _lamp_light_timer >= LAMP_LIGHT_UPDATE_INTERVAL:
		_lamp_light_timer = 0.0
		_update_lamp_lights()

	# Wind
	_update_wind(delta)

	# Ambient audio
	if _audio_manager:
		_audio_manager.update(delta, _wind_vec.length(), _weather_mode,
			_rain_wetness, _time_of_day, _lightning_flash)

	# Snow accumulation — ramps up during snow, melts otherwise
	var prev_snow := _snow_cover
	if _weather_mode == "snow":
		_snow_cover = minf(_snow_cover + delta * 0.02, 1.0)  # ~50s to full cover
	else:
		_snow_cover = maxf(_snow_cover - delta * 0.05, 0.0)  # ~20s to melt
	if _snow_cover != prev_snow:
		RenderingServer.global_shader_parameter_set("snow_cover", _snow_cover)

	# Rain wetness — ground darkens, gets glossy
	var prev_wet := _rain_wetness
	if _weather_mode == "rain" or _weather_mode == "thunderstorm":
		_rain_wetness = minf(_rain_wetness + delta * 0.04, 1.0)  # ~25s to full wet
	else:
		_rain_wetness = maxf(_rain_wetness - delta * 0.015, 0.0)  # ~67s to dry
	if _rain_wetness != prev_wet:
		RenderingServer.global_shader_parameter_set("rain_wetness", _rain_wetness)

	# Season advance
	if _season_speed > 0.0:
		_season_t = fmod(_season_t + _season_speed * delta, 4.0)
		RenderingServer.global_shader_parameter_set("season_t", _season_t)

	if _player and _park_loader and _park_loader._undergrowth_builder:
		_park_loader._undergrowth_builder.season_t = _season_t
		_park_loader._undergrowth_builder.rain_wetness = _rain_wetness
		_park_loader._undergrowth_builder.update_camera(_player.global_position)
	if _player and _park_loader and _park_loader._ground_cover_builder:
		_park_loader._ground_cover_builder.season_t = _season_t
		_park_loader._ground_cover_builder.update_camera(_player.global_position)
	# grass accents removed — particle system handles all grass types

	# Grass tour auto-teleport + screenshot
	_grass_tour_process(delta)

	# Particles follow player — wind deflects rain/snow
	if _rain_particles and _player:
		_rain_particles.global_position = _player.global_position + Vector3(0, 14, 0)
		var rpm: ParticleProcessMaterial = _rain_particles.process_material
		rpm.gravity = Vector3(_wind_vec.x * 5.0, -1.5, _wind_vec.y * 5.0)
	if _snow_particles and _player:
		_snow_particles.global_position = _player.global_position + Vector3(0, 15, 0)
		var spm: ParticleProcessMaterial = _snow_particles.process_material
		spm.gravity = Vector3(_wind_vec.x * 3.0, -1.5, _wind_vec.y * 3.0)

	# Autumn falling leaves — activate during fall season (2.0-3.2)
	var autumn_strength := smoothstep(1.8, 2.3, _season_t) * (1.0 - smoothstep(2.8, 3.2, _season_t))
	if autumn_strength > 0.05 and not _leaf_particles:
		_setup_leaf_particles()
	elif autumn_strength < 0.02 and _leaf_particles:
		_leaf_particles.queue_free()
		_leaf_particles = null
	if _leaf_particles and _player:
		_leaf_particles.global_position = _player.global_position + Vector3(0, 12, 0)
		var lpm: ParticleProcessMaterial = _leaf_particles.process_material
		# Wind pushes leaves strongly — they drift on the breeze
		lpm.gravity = Vector3(_wind_vec.x * 4.0, -0.3, _wind_vec.y * 4.0)
		# Vary amount by autumn intensity (sparse early/late, dense at peak)
		_leaf_particles.amount = int(lerpf(200.0, 2000.0, autumn_strength))

	# Spring cherry blossom petals — activate during bloom season (0.2-1.0)
	# Peak bloom around season_t 0.5 (mid-spring), tapering off into summer
	var bloom_strength := smoothstep(0.1, 0.4, _season_t) * (1.0 - smoothstep(0.7, 1.1, _season_t))
	# Also catch late-winter to spring wrap (season_t near 4.0→0)
	if _season_t > 3.8:
		bloom_strength = maxf(bloom_strength, smoothstep(3.8, 3.95, _season_t) * 0.5)
	if bloom_strength > 0.05 and not _blossom_particles:
		_setup_blossom_particles()
	elif bloom_strength < 0.02 and _blossom_particles:
		_blossom_particles.queue_free()
		_blossom_particles = null
	if _blossom_particles and _player:
		_blossom_particles.global_position = _player.global_position + Vector3(0, 10, 0)
		var bpm: ParticleProcessMaterial = _blossom_particles.process_material
		# Petals drift gently on the breeze — lighter than autumn leaves
		bpm.gravity = Vector3(_wind_vec.x * 3.0, -0.15, _wind_vec.y * 3.0)
		_blossom_particles.amount = int(lerpf(100.0, 1200.0, bloom_strength))

	# Lightning flashes during thunderstorm
	if _weather_mode == "thunderstorm":
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

	# Advance clock
	_time_of_day += _time_speed * delta
	if _time_of_day >= 24.0:
		_time_of_day -= 24.0
	elif _time_of_day < 0.0:
		_time_of_day += 24.0
	# Only update sky/env/lighting when time actually changes (~0.01h threshold)
	if absf(_time_of_day - _last_applied_tod) > 0.01 or _last_applied_tod < 0.0:
		_apply_time_of_day()

	_update_hud()
	_update_perf_overlay(delta)


func _update_perf_overlay(delta: float) -> void:
	if not _perf_visible or not _perf_label:
		return
	_perf_update_timer += delta
	if _perf_update_timer < PERF_UPDATE_INTERVAL:
		return
	_perf_update_timer = 0.0

	var fps := Performance.get_monitor(Performance.TIME_FPS)
	var frame_ms := 1000.0 / maxf(fps, 1.0)
	var process_ms := Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	var physics_ms := Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0

	var draw_calls := int(RenderingServer.get_rendering_info(
		RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME))
	var primitives := int(RenderingServer.get_rendering_info(
		RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME))
	var objects := int(RenderingServer.get_rendering_info(
		RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME))

	var vram_tex := RenderingServer.get_rendering_info(
		RenderingServer.RENDERING_INFO_TEXTURE_MEM_USED)
	var vram_buf := RenderingServer.get_rendering_info(
		RenderingServer.RENDERING_INFO_BUFFER_MEM_USED)
	var vram_total := RenderingServer.get_rendering_info(
		RenderingServer.RENDERING_INFO_VIDEO_MEM_USED)

	var node_count := Performance.get_monitor(Performance.OBJECT_NODE_COUNT)

	# Format triangle count with K/M suffix
	var tri_str: String
	if primitives >= 1_000_000:
		tri_str = "%.1fM" % (primitives / 1_000_000.0)
	elif primitives >= 1_000:
		tri_str = "%.0fK" % (primitives / 1_000.0)
	else:
		tri_str = str(primitives)

	# Frame budget bar: 16.67ms = 60fps target
	var budget_pct := frame_ms / 16.667 * 100.0
	var budget_bar: String
	if budget_pct <= 80.0:
		budget_bar = "[OK]"
	elif budget_pct <= 100.0:
		budget_bar = "[WARN]"
	else:
		budget_bar = "[OVER]"

	_perf_label.text = (
		"--- PERFORMANCE BUDGET ---\n" +
		"FPS: %d  (%.1f ms)\n" % [int(fps), frame_ms] +
		"Budget: %.0f%% of 60fps %s\n" % [budget_pct, budget_bar] +
		"\n" +
		"Process:  %5.1f ms\n" % process_ms +
		"Physics:  %5.1f ms\n" % physics_ms +
		"Render:   %5.1f ms (est)\n" % maxf(frame_ms - process_ms - physics_ms, 0.0) +
		"\n" +
		"Draw calls:  %d\n" % draw_calls +
		"Triangles:   %s\n" % tri_str +
		"Objects:     %d\n" % objects +
		"Nodes:       %d\n" % int(node_count) +
		"\n" +
		"VRAM total:  %d MB\n" % (vram_total / 1_048_576) +
		"  Textures:  %d MB\n" % (vram_tex / 1_048_576) +
		"  Buffers:   %d MB\n" % (vram_buf / 1_048_576)
	)


func _update_hud() -> void:
	if not _player or not _coord_label:
		return
	var pos := _player.position
	_coord_label.text = "X: %7.1f      Z: %7.1f" % [pos.x, pos.z]
	var bearing := fmod(fmod(-_player.rotation_degrees.y, 360.0) + 360.0, 360.0)
	_heading_label.text = "Heading: %5.1f°  %s" % [bearing, _compass_label(bearing)]
	var lat :=  REF_LAT + (-pos.z / METRES_PER_DEG_LAT)
	var lon :=  REF_LON + ( pos.x / METRES_PER_DEG_LON)
	_latlon_label.text  = "%.6f° N    %.6f° W" % [lat, absf(lon)]
	if _time_label:
		var h12: int = int(_time_of_day) % 12
		if h12 == 0:
			h12 = 12
		var mins: int = int(fmod(_time_of_day, 1.0) * 60.0)
		var ampm: String = "AM" if _time_of_day < 12.0 else "PM"
		_time_label.text = "%d:%02d %s  [%s]  %s" % [h12, mins, ampm, TIME_SPEED_NAMES[_time_speed_idx], _month_name(_season_t)]
	if _speed_label and _player:
		_speed_label.text = "%s (%.1f m/s)" % [_player.SPEED_NAMES[_player._speed_idx], _player.walk_speed]
	if _location_label:
		var area := _nearest_area(pos.x, pos.z)
		_location_label.text = area if area else ""
		_location_label.visible = not area.is_empty()


func _set_labels_visible(vis: bool) -> void:
	for n: Node in find_children("*", "Label3D", true, false):
		n.visible = vis


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
	var head: Node3D = _player.get_node("Head")
	if head:
		head.rotation_degrees.x = pitch
	_time_of_day = hour
	_time_speed = 0.0
	# Apply weather if specified
	if shot.has("weather"):
		_set_weather(shot["weather"])
	# Apply season if specified
	if shot.has("season"):
		_season_t = float(shot["season"])
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
	_last_applied_tod = -999.0  # force full lighting update
	_apply_time_of_day()


func _set_weather(mode: String) -> void:
	## Set weather mode, tearing down previous particles and pre-accumulating cover.
	if _rain_particles:
		_rain_particles.queue_free()
		_rain_particles = null
	if _snow_particles:
		_snow_particles.queue_free()
		_snow_particles = null
	_weather_mode = mode
	_setup_weather()
	# Pre-accumulate snow/rain so screenshots don't need to wait
	if mode == "snow":
		_snow_cover = 1.0
		_rain_wetness = 0.0
	elif mode == "rain" or mode == "thunderstorm":
		_rain_wetness = 1.0
		_snow_cover = 0.0
	else:
		_snow_cover = 0.0
		_rain_wetness = 0.0
	RenderingServer.global_shader_parameter_set("snow_cover", _snow_cover)
	RenderingServer.global_shader_parameter_set("rain_wetness", _rain_wetness)


func _tour_write_manifest() -> void:
	var manifest: Dictionary = {"shots": [], "viewpoints": TOUR_VIEWPOINTS.size(), "angles": TOUR_ANGLES.size(), "times": TOUR_TIMES.size()}
	for shot in _tour_shots:
		manifest["shots"].append({"filename": shot["filename"] + ".png", "name": shot["name"], "hour": shot["hour"], "x": shot["x"], "z": shot["z"]})
	var fa := FileAccess.open("%s/manifest.json" % _tour_save_dir, FileAccess.WRITE)
	fa.store_string(JSON.stringify(manifest, "\t"))
	fa.close()
	print("Tour: manifest.json written")


func _compass_label(deg: float) -> String:
	var labels := ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
	return labels[int(fmod(deg + 22.5, 360.0) / 45.0) % 8]


# Central Park named areas — [x_min, x_max, z_min, z_max, name]
const PARK_AREAS: Array = [
	# ── Landmarks and major areas ──
	[-700, -400, 1300, 1500, "Literary Walk"],
	[-550, -380, 1050, 1300, "The Mall"],
	[-530, -390, 900, 1050, "Bethesda Terrace"],
	[-650, -420, 700, 900, "The Lake"],
	[-550, -200, 400, 700, "The Ramble"],
	[-700, -550, 800, 1000, "Cherry Hill"],
	[-200, 200, -200, 400, "Great Lawn"],
	[-900, -600, 1500, 2100, "Sheep Meadow"],
	[-300, 200, -800, -400, "Reservoir"],
	[-200, 100, 800, 1050, "Conservatory Water"],
	[200, 800, -1800, -1200, "North Meadow"],
	[400, 900, -1600, -1000, "North Woods"],
	[-100, 500, -200, 200, "Turtle Pond"],
	[600, 1200, -2200, -1700, "Harlem Meer"],
	[-100, 200, 600, 900, "Belvedere Castle"],
	[-350, 0, 200, 500, "Delacorte Theater"],
	[0, 300, 300, 500, "Cleopatra's Needle"],
	[-700, -500, 1450, 1550, "Naumburg Bandshell"],
	[-250, 0, -600, -300, "Reservoir Running Track"],
	[100, 500, -900, -600, "Tennis Center"],
	[-200, 200, -1200, -800, "Conservatory Garden"],
	[-600, -350, 600, 750, "Bow Bridge"],
	[-900, -650, 1100, 1350, "Strawberry Fields"],
	[-700, -400, 1900, 2100, "The Pond"],
	[-800, -500, 2050, 2200, "Wollman Rink"],
	[700, 1100, -2100, -1800, "Lasker Pool"],
	[-300, 0, 500, 700, "Shakespeare Garden"],
	[300, 700, -1100, -700, "The Pool"],
	[400, 800, -1400, -1100, "The Loch"],
	[-200, 200, -400, -200, "The Obelisk"],
	[-1100, -800, 1400, 1800, "Tavern on the Green"],
	# ── Additional areas from Conservancy maps ──
	[-500, -200, -1950, -1700, "The Ravine"],
	[-300, 100, -350, -100, "Summit Rock"],
	[-700, -500, 450, 650, "Ladies Pavilion"],
	[100, 400, 150, 400, "Cedar Hill"],
	[-650, -350, 1100, 1250, "The Dene"],
	[-400, -100, 1600, 1800, "Heckscher Ballfields"],
	[200, 600, -1050, -750, "East Meadow"],
	[-100, 200, -1800, -1500, "Great Hill"],
	[300, 600, -1600, -1350, "Conservatory Garden East"],
	[-800, -500, 1050, 1250, "Mineral Springs"],
	[-500, -200, 750, 950, "Wagner Cove"],
	[-300, 0, 50, 300, "Arthur Ross Pinetum"],
	# ── Playgrounds (from Conservancy Playground Map) ──
	[-700, -550, -1850, -1750, "Yoseoff Playground"],
	[-700, -500, -1100, -1000, "Tarr Family Playground"],
	[-750, -600, -800, -700, "Rudin Family Playground"],
	[-750, -600, -575, -475, "Wild West Playground"],
	[-750, -600, -425, -325, "Safari Playground"],
	[-750, -600, 25, 125, "West 85th St Playground"],
	[-700, -550, 100, 200, "Toll Family Playground"],
	[-750, -600, 325, 425, "Diana Ross Playground"],
	[-750, -600, 1300, 1400, "Tarr-Coyne Tots Playground"],
	[-750, -600, 1375, 1475, "Adventure Playground"],
	[-500, -300, 1675, 1800, "Heckscher Playground"],
	[250, 450, -1850, -1750, "East 110th St Playground"],
	[250, 450, -1700, -1600, "Bernard Family Playground"],
	[250, 450, -1100, -1000, "Bendheim Playground"],
	[250, 450, -800, -700, "Kempner Playground"],
	[200, 400, 25, 125, "Ancient Playground"],
	[200, 400, 475, 575, "Smadbeck Playground"],
	[200, 400, 625, 725, "Levin Playground"],
	[200, 400, 1000, 1100, "East 72nd St Playground"],
	[200, 400, 1375, 1475, "Billy Johnson Playground"],
	# ── Facilities ──
	[300, 500, -1850, -1750, "Dana Discovery Center"],
	[-600, -400, 1375, 1475, "Dairy Visitor Center"],
	[-550, -400, 1450, 1550, "Chess & Checkers House"],
	[100, 350, 1525, 1625, "Central Park Zoo"],
	[-400, -200, 1150, 1250, "SummerStage"],
	[-300, -100, 550, 700, "Swedish Cottage"],
]

func _nearest_area(x: float, z: float) -> String:
	for area in PARK_AREAS:
		if x >= float(area[0]) and x <= float(area[1]) and z >= float(area[2]) and z <= float(area[3]):
			return area[4]
	return ""


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
			_apply_time_of_day()
			print("Time: %.1f h" % _time_of_day)
		elif event.button_index == JOY_BUTTON_DPAD_RIGHT:
			_time_of_day = fmod(_time_of_day + 1.0, 24.0)
			_apply_time_of_day()
			print("Time: %.1f h" % _time_of_day)
		elif event.button_index == JOY_BUTTON_LEFT_SHOULDER:
			_cycle_weather()
		elif event.button_index == JOY_BUTTON_RIGHT_SHOULDER:
			_season_t = fmod(_season_t + 1.0 / 3.0, 4.0)
			RenderingServer.global_shader_parameter_set("season_t", _season_t)
			print("Month: %s (season_t=%.2f)" % [_month_name(_season_t), _season_t])
		return
	if not (event is InputEventKey and event.pressed):
		return
	if event.keycode == KEY_T:
		_time_speed_idx = (_time_speed_idx + 1) % TIME_SPEEDS.size()
		_time_speed = TIME_SPEEDS[_time_speed_idx]
		print("Time speed: ", TIME_SPEED_NAMES[_time_speed_idx])
	elif event.keycode == KEY_BRACKETLEFT:
		_time_of_day = fmod(_time_of_day - 1.0 + 24.0, 24.0)
		_apply_time_of_day()
		print("Time: %.1f h" % _time_of_day)
	elif event.keycode == KEY_BRACKETRIGHT:
		_time_of_day = fmod(_time_of_day + 1.0, 24.0)
		_apply_time_of_day()
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
		if _hud_canvas:
			_hud_canvas.visible = not _hud_canvas.visible
	elif event.keycode == KEY_F9:
		_perf_visible = not _perf_visible
		if _perf_canvas:
			_perf_canvas.visible = _perf_visible
		print("Perf overlay: %s" % ("ON" if _perf_visible else "OFF"))
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
		if _wind_override < 0.0:
			_wind_override = 1.0
		_wind_override = clampf(_wind_override - 0.1, 0.0, 3.0)
		print("Wind: %.0f%%" % (_wind_override * 100.0))
	elif event.keycode == KEY_0:
		if _wind_override < 0.0:
			_wind_override = 1.0
		_wind_override = clampf(_wind_override + 0.1, 0.0, 3.0)
		print("Wind: %.0f%%" % (_wind_override * 100.0))
	elif event.keycode == KEY_N:
		if event.shift_pressed:
			_season_t = fmod(_season_t - 1.0 / 3.0 + 4.0, 4.0)
		else:
			_season_t = fmod(_season_t + 1.0 / 3.0, 4.0)
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
		print("Month: %s (season_t=%.2f)" % [_month_name(_season_t), _season_t])
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


func _month_name(t: float) -> String:
	# season_t: 0=spring equinox (Mar 20), 1=summer solstice (Jun 21),
	# 2=autumn equinox (Sep 22), 3=winter solstice (Dec 21)
	# Each 1/3 of a season ≈ 1 month
	var month_idx := int(t * 3.0) % 12
	const MONTHS := ["March", "April", "May", "June", "July", "August",
		"September", "October", "November", "December", "January", "February"]
	return MONTHS[month_idx]


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
	var head: Node3D = _player.get_node("Head")
	if head:
		head.rotation_degrees.x = spot["pitch"]
	# Set time, season, weather for this shot
	if spot.has("hour"):
		_time_of_day = spot["hour"]
	if spot.has("season"):
		_season_t = spot["season"]
		RenderingServer.global_shader_parameter_set("season_t", _season_t)
	if spot.has("weather"):
		_weather_mode = spot["weather"]
		if spot["weather"] == "snow":
			_snow_cover = 1.0
			RenderingServer.global_shader_parameter_set("snow_cover", _snow_cover)
		else:
			_snow_cover = 0.0
			RenderingServer.global_shader_parameter_set("snow_cover", 0.0)
	_apply_time_of_day()
	print("Photo tour: %s (%.0f,%.0f) %s %.1fh %s" % [
		spot["name"], x, z, _month_name(_season_t), spot.get("hour", 12.0), spot.get("weather", "clear")])
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


# ---------------------------------------------------------------------------
# Sky + lighting
# ---------------------------------------------------------------------------
func _load_img_tex(path: String) -> ImageTexture:
	if not FileAccess.file_exists(path):
		return null
	var img := Image.load_from_file(path)
	if not img:
		return null
	img.generate_mipmaps()
	return ImageTexture.create_from_image(img)

func _setup_environment() -> void:
	# Volumetric cloud sky (clayjohn compute pipeline)
	var sky: Sky
	var vol_sky = load("res://cloud_sky/clouds_sky.tres")
	if vol_sky:
		vol_sky.cloud_coverage = 0.30
		vol_sky.density = 0.04
		vol_sky.wind_speed = 1.5
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
	_env.volumetric_fog_density = 0.0002
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
	_sun.light_volumetric_fog_energy = 2.0  # god rays through volumetric fog
	_sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	_sun.directional_shadow_split_1      = 0.05   # tighter first cascade for near-field detail
	_sun.directional_shadow_split_2      = 0.15
	_sun.directional_shadow_split_3      = 0.4
	_sun.directional_shadow_max_distance = 300.0
	_sun.directional_shadow_pancake_size = 20.0
	add_child(_sun)

	# Wire sun to volumetric cloud sky (deferred because _sun created after sky)
	if vol_sky:
		vol_sky.sun = _sun

	print("Sky: day/night cycle — start 6:00 AM")


# ---------------------------------------------------------------------------
# Day/night keyframes
# ---------------------------------------------------------------------------
func _build_keyframes() -> void:
	# ---- 5.0  Pre-dawn ----
	# NYC light pollution: horizon never fully dark, ambient glow from city
	_keyframes.append({
		"hour": 5.0,
		"sky_top":        Color(0.02, 0.02, 0.06),
		"sky_horizon":    Color(0.14, 0.11, 0.20),  # light pollution glow
		"gnd_bottom":     Color(0.02, 0.02, 0.035),
		"gnd_horizon":    Color(0.10, 0.07, 0.12),
		"ambient_color":  Color(0.16, 0.14, 0.22),
		"ambient_energy": 0.45,   # NYC ambient from light pollution
		"exposure":       1.05,
		"white":          6.0,
		"ssao_radius":    2.0,
		"ssao_intensity": 1.4,
		"ssao_power":     1.5,
		"saturation":     0.75,
		"contrast":       1.02,
		"brightness":     0.96,
		"fog_color":      Color(0.12, 0.10, 0.14),
		"fog_energy":     0.20,
		"fog_scatter":    0.05,
		"fog_density":    0.0005,
		"fog_aerial":     0.20,
		"fog_sky_affect": 0.6,
		"sun_energy":     0.05,
		"sun_color":      Color(0.65, 0.72, 0.95),
		"sun_pitch":      -10.0,
		"sun_yaw":        -100.0,
		"shadow_dist":    250.0,
		"lamp_emission":  5.0,  # pre-dawn: lamps on (direct SpotLight3D energy)
		"vol_fog_density":    0.0004,
		"vol_fog_anisotropy": 0.45,
		"cloud_coverage":     0.30,
		"cloud_density":      0.60,
		"cloud_color_top":    Color(0.42, 0.40, 0.44),
		"cloud_color_bottom": Color(0.16, 0.14, 0.18),
		"cloud_speed":        0.003,
	})

	# ---- 6.5  Sunrise / Golden hour ----
	# Morning light from the east bathes the Fifth Avenue buildings in gold,
	# long shadows stretch westward across the lawns, mist rises from the ponds.
	_keyframes.append({
		"hour": 6.5,
		"sky_top":        Color(0.18, 0.32, 0.62),  # deeper dawn blue
		"sky_horizon":    Color(0.75, 0.52, 0.35),    # richer sunrise glow
		"gnd_bottom":     Color(0.10, 0.08, 0.06),
		"gnd_horizon":    Color(0.46, 0.34, 0.22),
		"ambient_color":  Color(0.48, 0.38, 0.26),
		"ambient_energy": 0.75,
		"exposure":       0.95,
		"white":          5.5,
		"ssao_radius":    1.5,
		"ssao_intensity": 1.5,
		"ssao_power":     1.5,
		"saturation":     1.0,
		"contrast":       1.02,
		"brightness":     1.0,
		"fog_color":      Color(0.50, 0.42, 0.34),   # subtle warm haze, not amber wash
		"fog_energy":     0.45,
		"fog_scatter":    0.18,
		"fog_density":    0.0005,   # golden hour haze — buildings fade into warm atmosphere
		"fog_aerial":     0.18,     # gentle atmospheric depth
		"fog_sky_affect": 0.30,
		"sun_energy":     0.90,
		"sun_color":      Color(1.0, 0.75, 0.50),    # warm but not deep amber
		"sun_pitch":      -12.0,
		"sun_yaw":        -95.0,
		"shadow_dist":    350.0,
		"lamp_emission":  0.0,
		"vol_fog_density":    0.0003,  # subtle sunrise haze
		"vol_fog_anisotropy": 0.80,    # moderate forward scatter
		"cloud_coverage":     0.30,
		"cloud_density":      0.55,
		"cloud_color_top":    Color(0.95, 0.85, 0.72),   # gold-lit cloud tops
		"cloud_color_bottom": Color(0.52, 0.42, 0.32),
		"cloud_speed":        0.004,
	})

	# ---- 12.0  Noon (clear, bright daylight) ----
	_keyframes.append({
		"hour": 12.0,
		"sky_top":        Color(0.12, 0.28, 0.65),  # deep noon blue
		"sky_horizon":    Color(0.55, 0.60, 0.68),
		"gnd_bottom":     Color(0.12, 0.12, 0.10),
		"gnd_horizon":    Color(0.38, 0.36, 0.32),
		"ambient_color":  Color(0.50, 0.46, 0.38),
		"ambient_energy": 0.95,
		"exposure":       1.0,
		"white":          6.0,
		"ssao_radius":    2.0,
		"ssao_intensity": 1.3,
		"ssao_power":     1.4,
		"saturation":     1.0,
		"contrast":       1.01,
		"brightness":     1.0,
		"fog_color":      Color(0.62, 0.60, 0.56),  # warmer haze — NYC summer atmosphere
		"fog_energy":     0.5,
		"fog_scatter":    0.06,
		"fog_density":    0.00015,  # noon: clearest air of the day, crisp visibility
		"fog_aerial":     0.12,     # subtle atmospheric scattering on distant objects
		"fog_sky_affect": 0.30,
		"sun_energy":     0.95,
		"sun_color":      Color(0.95, 0.92, 0.85),
		"sun_pitch":      -55.0,
		"sun_yaw":        -20.0,
		"shadow_dist":    400.0,
		"lamp_emission":  0.0,
		"vol_fog_density":    0.0001,  # very subtle volumetric — just enough for depth
		"vol_fog_anisotropy": 0.45,
		"cloud_coverage":     0.35,
		"cloud_density":      0.55,
		"cloud_color_top":    Color(0.95, 0.95, 0.93),
		"cloud_color_bottom": Color(0.68, 0.68, 0.66),
		"cloud_speed":        0.005,
	})

	# ---- 19.0  Sunset / Golden hour ----
	# The most photogenic time in Central Park — warm light raking across meadows,
	# long shadows, golden tree canopy, NYC skyline silhouettes catching fire.
	_keyframes.append({
		"hour": 19.0,
		"sky_top":        Color(0.18, 0.14, 0.38),   # deep sunset purple
		"sky_horizon":    Color(0.82, 0.50, 0.28),    # richer orange at horizon
		"gnd_bottom":     Color(0.10, 0.07, 0.04),
		"gnd_horizon":    Color(0.48, 0.35, 0.20),    # warm ground reflection
		"ambient_color":  Color(0.48, 0.42, 0.32),    # warm ambient but not saturated amber
		"ambient_energy": 0.88,
		"exposure":       0.95,
		"white":          5.5,
		"ssao_radius":    2.0,
		"ssao_intensity": 1.4,
		"ssao_power":     1.5,
		"saturation":     1.0,    # natural — let sun color do the work
		"contrast":       1.02,   # soft long shadows
		"brightness":     0.98,
		"fog_color":      Color(0.55, 0.45, 0.35),    # neutral warm haze, not amber blanket
		"fog_energy":     0.45,
		"fog_scatter":    0.18,
		"fog_density":    0.0005,   # golden hour atmospheric haze
		"fog_aerial":     0.18,     # gentle atmospheric depth
		"fog_sky_affect": 0.30,
		"sun_energy":     0.95,    # strong low sun but not overblown
		"sun_color":      Color(1.0, 0.72, 0.45),     # warm golden, not deep amber
		"sun_pitch":      -12.0,   # lower sun angle for longer shadows
		"sun_yaw":        95.0,
		"shadow_dist":    350.0,
		"lamp_emission":  0.0,  # lamps off until after sunset (ramp 19h→21h)
		"vol_fog_density":    0.0003,  # subtle haze — clarity over drama
		"vol_fog_anisotropy": 0.80,    # moderate forward scatter
		"cloud_coverage":     0.35,
		"cloud_density":      0.55,
		"cloud_color_top":    Color(0.85, 0.55, 0.38),  # golden-lit cloud tops
		"cloud_color_bottom": Color(0.55, 0.30, 0.18),  # warm undersides
		"cloud_speed":        0.004,
	})

	# ---- 21.0  Night ----
	# NYC light pollution: never truly dark. Central Park is surrounded by 6,557 lit buildings.
	# Real nighttime in CP: you can see paths, grass, trees clearly. The city bathes everything in warm glow.
	_keyframes.append({
		"hour": 21.0,
		"sky_top":        Color(0.015, 0.01, 0.01),  # very dark — NYC Bortle 9 zenith
		"sky_horizon":    Color(0.08, 0.05, 0.03),   # dim amber glow at horizon
		"gnd_bottom":     Color(0.02, 0.015, 0.01),
		"gnd_horizon":    Color(0.08, 0.06, 0.04),  # warm ground glow from city
		"ambient_color":  Color(0.85, 0.65, 0.40),  # warm amber city glow — NYC sodium vapor spill
		"ambient_energy": 0.06,   # deep dark — only lamppost pools provide real light
		"exposure":       0.90,   # dark night but AgX needs more exposure than Filmic
		"white":          6.0,
		"ssao_radius":    2.0,
		"ssao_intensity": 1.4,
		"ssao_power":     1.5,
		"saturation":     0.50,   # colors are very muted at night — olive/brown, not green
		"contrast":       1.01,
		"brightness":     0.88,
		"fog_color":      Color(0.08, 0.06, 0.04),  # dimmer amber night haze
		"fog_energy":     0.20,
		"fog_scatter":    0.06,
		"fog_density":    0.0003,
		"fog_aerial":     0.15,
		"fog_sky_affect": 0.4,
		"sun_energy":     0.05,
		"sun_color":      Color(0.70, 0.78, 1.00),
		"sun_pitch":      -65.0,
		"sun_yaw":        40.0,
		"shadow_dist":    250.0,
		"lamp_emission":  5.0,  # night: direct SpotLight3D energy (was 110 via 22x multiplier)
		"vol_fog_density":    0.0005,  # slight night haze catches lamplight scatter
		"vol_fog_anisotropy": 0.35,
		"cloud_coverage":     0.25,
		"cloud_density":      0.55,
		"cloud_color_top":    Color(0.14, 0.12, 0.18),
		"cloud_color_bottom": Color(0.06, 0.05, 0.08),
		"cloud_speed":        0.003,
	})


func _find_keyframe_pair(hour: float) -> Array:
	## Returns [kf_a: Dictionary, kf_b: Dictionary, t: float]
	var n: int = _keyframes.size()
	for i in n:
		var ha: float = float(_keyframes[i]["hour"])
		var j: int = (i + 1) % n
		var hb: float = float(_keyframes[j]["hour"])
		# Handle wrap-around (night 21→pre-dawn 5 spans midnight)
		var span: float
		var off: float
		if hb <= ha:
			# Wrapping pair (e.g. 21→5 = 8 hours through midnight)
			span = (hb + 24.0) - ha
			if hour >= ha:
				off = hour - ha
			else:
				off = (hour + 24.0) - ha
		else:
			span = hb - ha
			off = hour - ha
		if off >= 0.0 and off < span:
			var t: float = off / span
			return [_keyframes[i], _keyframes[j], t]
	# Fallback (should not happen)
	return [_keyframes[0], _keyframes[0], 0.0]


func _lerp_kf(key: String, a: Dictionary, b: Dictionary, t: float):
	var va = a[key]
	var vb = b[key]
	if va is Color:
		return (va as Color).lerp(vb as Color, t)
	else:
		return lerpf(float(va), float(vb), t)


func _apply_time_of_day() -> void:
	if not _env or not _sky_mat or not _sun:
		return
	var pair: Array = _find_keyframe_pair(_time_of_day)
	var a: Dictionary = pair[0]
	var b: Dictionary = pair[1]
	var t: float = float(pair[2])

	# Cloud properties — route to volumetric sky or old shader
	var _cc_val: float = _lerp_kf("cloud_coverage", a, b, t)
	var _cs_val: float = _lerp_kf("cloud_speed", a, b, t)
	if _vol_sky:
		_vol_sky.cloud_coverage = clampf(_cc_val, 0.20, 0.50)  # partly cloudy for clear weather
		_vol_sky.density = clampf(_lerp_kf("cloud_density", a, b, t) * 0.08, 0.02, 0.10)
	else:
		var sky_top: Color = _lerp_kf("sky_top", a, b, t)
		var sky_hor: Color = _lerp_kf("sky_horizon", a, b, t)
		var gnd_bot: Color = _lerp_kf("gnd_bottom", a, b, t)
		var gnd_hor: Color = _lerp_kf("gnd_horizon", a, b, t)
		_sky_mat.set_shader_parameter("sky_top_color", Vector3(sky_top.r, sky_top.g, sky_top.b))
		_sky_mat.set_shader_parameter("sky_horizon_color", Vector3(sky_hor.r, sky_hor.g, sky_hor.b))
		_sky_mat.set_shader_parameter("ground_bottom_color", Vector3(gnd_bot.r, gnd_bot.g, gnd_bot.b))
		_sky_mat.set_shader_parameter("ground_horizon_color", Vector3(gnd_hor.r, gnd_hor.g, gnd_hor.b))
		_sky_mat.set_shader_parameter("cloud_coverage", _cc_val)
		_sky_mat.set_shader_parameter("cloud_density", _lerp_kf("cloud_density", a, b, t))
		var cc_top: Color = _lerp_kf("cloud_color_top", a, b, t)
		var cc_bot: Color = _lerp_kf("cloud_color_bottom", a, b, t)
		_sky_mat.set_shader_parameter("cloud_color_top", Vector3(cc_top.r, cc_top.g, cc_top.b))
		_sky_mat.set_shader_parameter("cloud_color_bottom", Vector3(cc_bot.r, cc_bot.g, cc_bot.b))
		_sky_mat.set_shader_parameter("cloud_speed", _cs_val)
	# Push to globals for cloud shadows on terrain/grass
	RenderingServer.global_shader_parameter_set("cloud_coverage_g", _cc_val)
	RenderingServer.global_shader_parameter_set("cloud_speed_g", _cs_val)

	# Ambient
	_env.ambient_light_color  = _lerp_kf("ambient_color", a, b, t)
	_env.ambient_light_energy = _lerp_kf("ambient_energy", a, b, t)

	# Impostor brightness tracks ambient — brighter at noon, dimmer at night
	# Normalized to 1.0 at noon (ambient_energy ~0.95), scales proportionally
	var _imp_bright: float = clamp(_env.ambient_light_energy / 0.95, 0.3, 1.5)
	RenderingServer.global_shader_parameter_set("impostor_brightness", _imp_bright)

	# Tonemapping
	_env.tonemap_exposure = _lerp_kf("exposure", a, b, t)
	_env.tonemap_white    = _lerp_kf("white", a, b, t)

	# SSAO
	_env.ssao_radius    = _lerp_kf("ssao_radius", a, b, t)
	_env.ssao_intensity = _lerp_kf("ssao_intensity", a, b, t)
	_env.ssao_power     = _lerp_kf("ssao_power", a, b, t)

	# Colour grading
	_env.adjustment_saturation = _lerp_kf("saturation", a, b, t)
	_env.adjustment_contrast   = _lerp_kf("contrast", a, b, t)
	_env.adjustment_brightness = _lerp_kf("brightness", a, b, t) * _user_gamma
	if _lightning_flash > 0.01:
		_env.adjustment_brightness *= (1.0 + _lightning_flash * 0.8)

	# Volumetric fog only — standard fog disabled (was double-dipping)
	_env.volumetric_fog_density    = _lerp_kf("vol_fog_density", a, b, t)
	var base_aniso: float = _lerp_kf("vol_fog_anisotropy", a, b, t)
	# Boost anisotropy for god rays when sun is low (light shafts through trees/clouds)
	var pitch_val: float = _lerp_kf("sun_pitch", a, b, t)
	var sun_low_factor: float = smoothstep(-25.0, -5.0, pitch_val) * smoothstep(5.0, -5.0, pitch_val)
	_env.volumetric_fog_anisotropy = lerpf(base_aniso, 0.88, sun_low_factor * 0.5)

	# Weather overrides — mostly cloudy (not overcast) for non-clear weather
	if _weather_mode == "fog":
		_env.volumetric_fog_density = 0.005
		_env.adjustment_saturation = 0.45
		_env.adjustment_brightness = 0.90
		if _vol_sky:
			_vol_sky.cloud_coverage = 0.60
			_vol_sky.density = 0.08
		else:
			_sky_mat.set_shader_parameter("cloud_coverage", 0.75)
			_sky_mat.set_shader_parameter("cloud_density", 0.80)
			_sky_mat.set_shader_parameter("cloud_type", 1.0)
	elif _weather_mode == "rain":
		_env.volumetric_fog_density = 0.004
		_env.adjustment_saturation *= 0.7
		_env.adjustment_brightness *= 0.88
		if _vol_sky:
			_vol_sky.cloud_coverage = 0.58
			_vol_sky.density = 0.07
		else:
			_sky_mat.set_shader_parameter("cloud_coverage", 0.72)
			_sky_mat.set_shader_parameter("cloud_density", 0.78)
			_sky_mat.set_shader_parameter("cloud_type", 1.0)
	elif _weather_mode == "thunderstorm":
		_env.volumetric_fog_density = 0.008
		_env.adjustment_saturation *= 0.50
		_env.adjustment_brightness *= 0.75
		if _vol_sky:
			_vol_sky.cloud_coverage = 0.68
			_vol_sky.density = 0.10
		else:
			_sky_mat.set_shader_parameter("cloud_coverage", 0.82)
			_sky_mat.set_shader_parameter("cloud_density", 0.85)
			_sky_mat.set_shader_parameter("cloud_type", 2.0)
	elif _weather_mode == "snow":
		_env.volumetric_fog_density = 0.003
		_env.adjustment_saturation *= 0.75
		if _vol_sky:
			_vol_sky.cloud_coverage = 0.55
			_vol_sky.density = 0.06
		else:
			_sky_mat.set_shader_parameter("cloud_coverage", 0.70)
			_sky_mat.set_shader_parameter("cloud_density", 0.72)
			_sky_mat.set_shader_parameter("cloud_type", 1.0)

	# Wind reduces volumetric fog slightly (wind disperses mist)
	var wind_str: float = _wind_vec.length()
	if wind_str > 0.1:
		_env.volumetric_fog_density *= lerpf(1.0, 0.85, clampf(wind_str * 0.3, 0.0, 1.0))

	# Sky reflection color for water surfaces — tracks time-of-day sky tone
	var sky_r: Color = _lerp_kf("fog_color", a, b, t)
	var sun_c: Color = _lerp_kf("sun_color", a, b, t)
	# Blend fog color (ambient sky) with sun color, bias toward cooler tones
	# Real water preferentially reflects blue/gray sky, not warm ground haze
	var reflect := sky_r.lerp(sun_c, 0.2)
	# Cool bias: shift toward blue-gray to prevent brown water at golden hour
	reflect = Color(reflect.r * 0.75, reflect.g * 0.85, reflect.b * 1.1)
	RenderingServer.global_shader_parameter_set("sky_reflect_color",
		Vector3(reflect.r, reflect.g, reflect.b))

	# Morning dew — specular on grass surfaces at dawn (4:30-8:30 AM)
	var dew := 0.0
	if _time_of_day >= 4.5 and _time_of_day <= 8.5:
		if _time_of_day <= 6.0:
			dew = smoothstep(4.5, 6.0, _time_of_day)
		else:
			dew = 1.0 - smoothstep(6.0, 8.5, _time_of_day)
	if _weather_mode != "clear":
		dew = 0.0  # no visible dew in rain/snow
	RenderingServer.global_shader_parameter_set("dew_amount", dew)

	# Dawn mist — natural morning fog that lifts with sunrise (5-7:30 AM)
	# Common phenomenon in Central Park near water bodies and in wooded areas
	if _weather_mode == "clear":
		var dawn_mist := 0.0
		if _time_of_day >= 4.5 and _time_of_day <= 7.5:
			# Peak at 5:30, fading by 7:30
			if _time_of_day <= 5.5:
				dawn_mist = smoothstep(4.5, 5.5, _time_of_day)
			else:
				dawn_mist = 1.0 - smoothstep(5.5, 7.5, _time_of_day)
			_env.volumetric_fog_density += dawn_mist * 0.002
			_env.adjustment_saturation *= (1.0 - dawn_mist * 0.15)  # slightly desaturated mist

	# Seasonal fog and atmosphere modulation
	# Autumn: warmer golden haze, slightly denser
	# Winter: cooler blue-gray haze, denser, more desaturated
	# Spring: fresh, clear, slightly green-tinted
	var s_autumn := smoothstep(1.5, 2.5, _season_t) * (1.0 - smoothstep(2.5, 3.5, _season_t))
	var s_winter := smoothstep(2.5, 3.5, _season_t)
	if s_autumn > 0.01:
		# Warm golden haze — slightly denser volumetric
		_env.volumetric_fog_density *= (1.0 + s_autumn * 0.12)
	if s_winter > 0.01:
		# Cold atmosphere — denser, more desaturated
		_env.volumetric_fog_density *= (1.0 + s_winter * 0.15)
		_env.adjustment_saturation *= (1.0 - s_winter * 0.2)
	# Monthly cloud coverage from NOAA/Weather Atlas data for NYC
	# season_t: 0=Mar(47%), 0.33=Apr(45%), 0.67=May(44%), 1.0=Jun(36%),
	# 1.33=Jul(31%), 1.67=Aug(30%), 2.0=Sep(34%), 2.33=Oct(41%),
	# 2.67=Nov(37%), 3.0=Dec(47%), 3.33=Jan(43%), 3.67=Feb(47%)
	var monthly_cover: Array = [0.47, 0.45, 0.44, 0.36, 0.31, 0.30,
		0.34, 0.41, 0.37, 0.47, 0.43, 0.47]
	var month_idx: int = int(_season_t * 3.0) % 12
	var month_next: int = (month_idx + 1) % 12
	var month_frac: float = fmod(_season_t * 3.0, 1.0)
	var data_cover: float = lerpf(monthly_cover[month_idx], monthly_cover[month_next], month_frac)
	if _weather_mode == "clear":
		if _vol_sky:
			_vol_sky.cloud_coverage = maxf(lerpf(_vol_sky.cloud_coverage, data_cover, 0.7), 0.25)
		else:
			var cc: float = _sky_mat.get_shader_parameter("cloud_coverage")
			_sky_mat.set_shader_parameter("cloud_coverage", lerpf(cc, data_cover, 0.7))
			if s_winter > 0.3:
				_sky_mat.set_shader_parameter("cloud_type", lerpf(0.0, 1.0, s_winter))

	# Sun / moon directional light
	_sun.light_energy    = _lerp_kf("sun_energy", a, b, t)
	_sun.light_color     = _lerp_kf("sun_color", a, b, t)
	var pitch: float     = _lerp_kf("sun_pitch", a, b, t)
	var yaw: float       = _lerp_kf("sun_yaw", a, b, t)
	_sun.rotation_degrees = Vector3(pitch, yaw, 0.0)
	_sun.directional_shadow_max_distance = _lerp_kf("shadow_dist", a, b, t)

	# Lamp emission level — drives SpotLight3D pool energy + globe glow
	_lamp_emission = _lerp_kf("lamp_emission", a, b, t)
	RenderingServer.global_shader_parameter_set("lamp_glow", clampf(_lamp_emission / 5.0, 0.0, 1.0))

	# Building window emission — smooth night_factor curve
	# 0.0 during day (7h-18h), ramps to 1.0 at night (21h-5h)
	var nf: float = 0.0
	if _time_of_day >= 18.0 and _time_of_day < 21.0:
		nf = (_time_of_day - 18.0) / 3.0  # sunset ramp
	elif _time_of_day >= 21.0 or _time_of_day < 5.0:
		nf = 1.0  # full night
	elif _time_of_day >= 5.0 and _time_of_day < 7.0:
		nf = 1.0 - (_time_of_day - 5.0) / 2.0  # dawn ramp
	if _park_loader:
		for fm in _park_loader.facade_materials:
			if fm is ShaderMaterial:
				fm.set_shader_parameter("night_factor", nf)

	_last_applied_tod = _time_of_day



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
var _landuse_texture: Texture2D  # cached for grass particle system

# Biome definitions for multi-layer grass particles.
# 4 Tuft layers with PBR textures + alpha cutout — one per biome type, non-overlapping.
# Tuft meshes have embedded albedo textures with alpha for realistic blade-level detail
# and blending with the terrain underneath. Undergrowth system provides taller accents.
const GRASS_BIOMES := [
	{  # Maintained lawns — Tuft_Tiny: 34×33cm footprint, 5.8cm tall, 99 tris
		# Data: A-class 5-8cm (mowed 2x/wk). Invisible from standing but correct.
		"name": "Lawn", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Tuft_Tiny.glb",
		"spacing": 0.4, "cell_width": 24.0, "grid_width": 5,
		"random_spacing": 0.3,
		"min_scale": Vector3(0.9, 0.9, 0.9),
		"max_scale": Vector3(1.3, 1.3, 1.3),
		"position_offset": Vector3(0, -0.005, 0),
	},
	{  # Woodland/shade floor — Tuft_Woodland: 24×20cm footprint, 8cm tall, 150 tris
		"name": "Shade", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Tuft_Woodland.glb",
		"spacing": 0.5, "cell_width": 24.0, "grid_width": 5,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.8, 0.8, 0.8),
		"max_scale": Vector3(1.5, 1.5, 1.5),
		"position_offset": Vector3(0, -0.005, 0),
	},
	{  # Wild meadow — Tuft_Wild: 68×67cm footprint, 26cm tall, 300 tris
		"name": "Wild", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Tuft_Wild.glb",
		"spacing": 0.55, "cell_width": 24.0, "grid_width": 5,
		"random_spacing": 0.5,
		"min_scale": Vector3(0.7, 0.7, 0.7),
		"max_scale": Vector3(1.2, 1.2, 1.2),
		"position_offset": Vector3(0, -0.008, 0),
	},
	{  # Waterside — Tuft_Meadow: 25×27cm footprint, 17cm tall, 266 tris
		"name": "Sedge", "biome_id": 3,
		"mesh_path": "res://models/vegetation/Tuft_Meadow.glb",
		"spacing": 0.5, "cell_width": 24.0, "grid_width": 5,
		"random_spacing": 0.4,
		"min_scale": Vector3(0.8, 0.8, 0.8),
		"max_scale": Vector3(1.5, 1.5, 1.5),
		"position_offset": Vector3(0, -0.005, 0),
	},
]

func _setup_grass_particles() -> void:
	## Multi-biome grass: one Terrain3D particle layer per biome, each with a
	## decimated BD3D tuft mesh filtered to its zone_ids.
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

	for biome in GRASS_BIOMES:
		# Load tuft GLB via Godot's native load()
		var scene = load(biome.mesh_path)
		if not scene:
			push_warning("Grass tuft not found: %s — skipping biome %s" % [
				biome.mesh_path, biome.name])
			continue
		var inst = scene.instantiate()
		var tuft_mesh: Mesh = null
		var albedo_tex: Texture2D = null
		for child in inst.get_children():
			if child is MeshInstance3D:
				tuft_mesh = child.mesh
				var mat = tuft_mesh.surface_get_material(0)
				if mat is BaseMaterial3D and mat.albedo_texture:
					albedo_tex = mat.albedo_texture
				break
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
		proc_mat.set_shader_parameter("distance_fade_ammount", 0.6)
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

	# Try pre-baked PNG first (generated by convert_to_godot.py at 8192×8192)
	for path in ["res://landuse_map.png"]:
		var global_path := ProjectSettings.globalize_path(path)
		if FileAccess.file_exists(path):
			img = Image.load_from_file(path)
		elif FileAccess.file_exists(global_path):
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
	var shore_global := ProjectSettings.globalize_path(shore_path)
	var shore_img: Image = null
	if FileAccess.file_exists(shore_path):
		shore_img = Image.load_from_file(shore_path)
	elif FileAccess.file_exists(shore_global):
		shore_img = Image.load_from_file(shore_global)
	if shore_img:
		var shore_tex := ImageTexture.create_from_image(shore_img)
		_set_terrain_param("shore_distance", shore_tex)
		print("Terrain: loaded shore distance field %dx%d" % [shore_img.get_width(), shore_img.get_height()])


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


# ---------------------------------------------------------------------------
# Wind — layered crossing breezes that vary with time of day and weather
# ---------------------------------------------------------------------------

func _update_wind(delta: float) -> void:
	_wind_time += delta
	var t := _wind_time

	# Time-of-day strength: calm 17-22h so fireflies aren't blown away
	var tod_mult := 1.0
	if _time_of_day >= 17.0 and _time_of_day < 18.0:
		tod_mult = lerpf(1.0, 0.12, (_time_of_day - 17.0))
	elif _time_of_day >= 18.0 and _time_of_day < 21.0:
		tod_mult = 0.12
	elif _time_of_day >= 21.0 and _time_of_day < 22.0:
		tod_mult = lerpf(0.12, 1.0, (_time_of_day - 21.0))

	# Weather multiplier
	var wx := 1.0
	if _weather_mode == "rain":
		wx = 1.8
	elif _weather_mode == "thunderstorm":
		wx = 2.8
	elif _weather_mode == "snow":
		wx = 0.5
	elif _weather_mode == "fog":
		wx = 0.3

	# Layer 1: slow broad wind — base direction rotates over ~3.5 min
	var a1 := t * 0.03
	var s1 := sin(t * 0.21) * 0.25 + 0.30
	var w1 := Vector2(cos(a1), sin(a1)) * s1

	# Layer 2: crossing gust from a different angle (~18s period)
	var a2 := t * 0.03 + 2.1 + sin(t * 0.07) * 0.8
	var s2 := sin(t * 0.35 + 1.7) * 0.20
	var w2 := Vector2(cos(a2), sin(a2)) * s2

	# Layer 3: quick turbulence (~4s puffs, smaller amplitude)
	var s3 := sin(t * 1.3 + 3.1) * 0.10
	var w3 := Vector2(sin(t * 1.7 + 0.5), cos(t * 2.1 + 1.3)) * s3

	_wind_vec = (w1 + w2 + w3) * tod_mult * wx

	# Manual override (- / = keys)
	if _wind_override >= 0.0:
		_wind_vec = (w1 + w2 + w3).normalized() * _wind_override * 0.55

	# Push to global shader uniform
	RenderingServer.global_shader_parameter_set("wind_vec", _wind_vec)

	# Drive volumetric cloud movement from wind
	if _vol_sky:
		var wlen: float = _wind_vec.length()
		if wlen > 0.01:
			_vol_sky.wind_direction = atan2(_wind_vec.y, _wind_vec.x)
		_vol_sky.wind_speed = maxf(wlen * 20.0, 0.5)


const WEATHER_MODES: Array = ["clear", "rain", "thunderstorm", "snow", "fog"]

func _cycle_weather() -> void:
	# Tear down current weather effects
	if _rain_particles:
		_rain_particles.queue_free()
		_rain_particles = null
	if _snow_particles:
		_snow_particles.queue_free()
		_snow_particles = null
	# Advance to next mode
	var idx := WEATHER_MODES.find(_weather_mode)
	if idx < 0:
		idx = 0
	_weather_mode = WEATHER_MODES[(idx + 1) % WEATHER_MODES.size()]
	_setup_weather()
	# Force re-apply time-of-day so keyframe values override stale weather fog/clouds
	_last_applied_tod = -999.0
	_apply_time_of_day()
	print("Weather: %s" % _weather_mode)


func _setup_weather() -> void:
	if _weather_mode == "rain":
		_setup_rain()
	elif _weather_mode == "thunderstorm":
		_setup_thunderstorm()
	elif _weather_mode == "snow":
		_setup_snow()
	elif _weather_mode == "fog":
		_setup_fog_weather()


func _setup_rain() -> void:
	# Gentle rain — soft, slow, soothing
	_rain_particles = GPUParticles3D.new()
	_rain_particles.amount = 6000
	_rain_particles.lifetime = 4.0
	_rain_particles.visibility_aabb = AABB(Vector3(-25, -15, -25), Vector3(50, 30, 50))

	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 8.0
	pm.initial_velocity_min = 1.5
	pm.initial_velocity_max = 2.2
	pm.gravity = Vector3(0, -1.0, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(25.0, 0.5, 25.0)
	_rain_particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.006, 0.10)
	_rain_particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.7, 0.75, 0.85, 0.25)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.no_depth_test = true
	mat.emission_enabled = true
	mat.emission = Color(0.4, 0.45, 0.55)
	mat.emission_energy_multiplier = 0.2
	_rain_particles.material_override = mat

	add_child(_rain_particles)
	print("Rain: 6000 gentle particles")


func _setup_thunderstorm() -> void:
	# Heavy downpour — dense, fast, thick drops
	_rain_particles = GPUParticles3D.new()
	_rain_particles.amount = 30000
	_rain_particles.lifetime = 2.5
	_rain_particles.visibility_aabb = AABB(Vector3(-25, -15, -25), Vector3(50, 30, 50))

	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 12.0
	pm.initial_velocity_min = 5.0
	pm.initial_velocity_max = 7.5
	pm.gravity = Vector3(0, -3.0, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(25.0, 0.5, 25.0)
	_rain_particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.012, 0.22)
	_rain_particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.6, 0.65, 0.75, 0.4)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.no_depth_test = true
	mat.emission_enabled = true
	mat.emission = Color(0.35, 0.40, 0.50)
	mat.emission_energy_multiplier = 0.25
	_rain_particles.material_override = mat

	add_child(_rain_particles)
	print("Thunderstorm: 30000 heavy rain")


func _setup_snow() -> void:
	_snow_particles = GPUParticles3D.new()
	_snow_particles.amount = 3000
	_snow_particles.lifetime = 4.0
	_snow_particles.visibility_aabb = AABB(Vector3(-25, -20, -25), Vector3(50, 40, 50))

	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 15.0
	pm.initial_velocity_min = 1.0
	pm.initial_velocity_max = 2.5
	pm.gravity = Vector3(0, -1.5, 0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(25.0, 0.5, 25.0)
	# Gentle drift
	pm.orbit_velocity_min = 0.1
	pm.orbit_velocity_max = 0.3
	_snow_particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.04, 0.04)
	_snow_particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.95, 0.95, 1.0, 0.8)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_snow_particles.material_override = mat

	add_child(_snow_particles)

	print("Snow: 3000 particles")



func _setup_leaf_particles() -> void:
	## Autumn falling leaves — warm-colored quads drifting down through canopy.
	## Active only during autumn season (season_t 2.0-3.2). Amount varies
	## with season intensity: sparse at start/end, dense at peak color.
	_leaf_particles = GPUParticles3D.new()
	_leaf_particles.amount = 800  # adjusted dynamically in _process
	_leaf_particles.lifetime = 8.0  # slow drift down
	_leaf_particles.visibility_aabb = AABB(Vector3(-30, -15, -30), Vector3(60, 30, 60))

	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 45.0  # wide spread — leaves tumble in all directions
	pm.initial_velocity_min = 0.3
	pm.initial_velocity_max = 0.8
	pm.gravity = Vector3(0, -0.3, 0)  # very slow fall (wind does most of the work)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(30.0, 2.0, 30.0)
	# Orbit for tumbling/spinning as leaves fall
	pm.orbit_velocity_min = 0.15
	pm.orbit_velocity_max = 0.45
	# Angular velocity for spinning
	pm.angular_velocity_min = -90.0
	pm.angular_velocity_max = 90.0
	# Scale variation — different leaf sizes
	pm.scale_min = 0.6
	pm.scale_max = 1.4
	# Randomize color: fall palette from warm yellow to deep red
	pm.color = Color(0.85, 0.55, 0.20, 0.85)
	var color_ramp := GradientTexture1D.new()
	var grad := Gradient.new()
	grad.set_color(0, Color(0.90, 0.80, 0.25, 0.90))  # golden yellow
	grad.add_point(0.3, Color(0.85, 0.50, 0.15, 0.85))  # orange
	grad.add_point(0.6, Color(0.75, 0.25, 0.10, 0.80))  # red-brown
	grad.set_color(1, Color(0.50, 0.30, 0.15, 0.70))  # dark brown (old leaves)
	color_ramp.gradient = grad
	pm.color_initial_ramp = color_ramp
	_leaf_particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.035, 0.025)  # small leaf shape — wider than tall
	_leaf_particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.85, 0.55, 0.20, 0.85)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_leaf_particles.material_override = mat

	add_child(_leaf_particles)
	print("Autumn leaves: drifting fall particles")


func _setup_blossom_particles() -> void:
	## Spring cherry blossom petals — pale pink quads floating down like snow.
	## Active during spring bloom (season_t 0.2-1.0). Yoshino cherry, callery pear,
	## and magnolia all shed petals in Central Park's April bloom.
	_blossom_particles = GPUParticles3D.new()
	_blossom_particles.amount = 600  # adjusted dynamically in _process
	_blossom_particles.lifetime = 12.0  # very slow drift — petals are light
	_blossom_particles.visibility_aabb = AABB(Vector3(-35, -15, -35), Vector3(70, 30, 70))

	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 60.0  # wide spread — petals flutter in all directions
	pm.initial_velocity_min = 0.1
	pm.initial_velocity_max = 0.5
	pm.gravity = Vector3(0, -0.15, 0)  # extremely slow fall (petals are featherlight)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(35.0, 3.0, 35.0)
	# Gentle orbit for graceful fluttering descent
	pm.orbit_velocity_min = 0.08
	pm.orbit_velocity_max = 0.25
	# Slow spin — petals rotate gracefully, not chaotically
	pm.angular_velocity_min = -45.0
	pm.angular_velocity_max = 45.0
	# Scale variation — small petals
	pm.scale_min = 0.5
	pm.scale_max = 1.2
	# Color: cherry blossom pink palette
	pm.color = Color(0.95, 0.82, 0.85, 0.90)
	var color_ramp := GradientTexture1D.new()
	var grad := Gradient.new()
	grad.set_color(0, Color(1.0, 0.92, 0.94, 0.95))    # almost white (fresh petal)
	grad.add_point(0.25, Color(0.98, 0.82, 0.86, 0.92)) # pale pink (Yoshino cherry)
	grad.add_point(0.5, Color(0.95, 0.72, 0.78, 0.88))  # medium pink
	grad.add_point(0.75, Color(0.92, 0.65, 0.72, 0.80)) # deeper pink (aging petal)
	grad.set_color(1, Color(0.88, 0.60, 0.65, 0.50))    # browning edge (ground)
	color_ramp.gradient = grad
	pm.color_initial_ramp = color_ramp
	# Damping so petals slow down as they drift
	pm.damping_min = 1.0
	pm.damping_max = 3.0
	_blossom_particles.process_material = pm

	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.018, 0.016)  # tiny petal shape — slightly wider than tall

	_blossom_particles.draw_pass_1 = mesh

	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.97, 0.85, 0.88, 0.90)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	# Slight emission for that ethereal glow of sunlit petals
	mat.emission_enabled = true
	mat.emission = Color(0.95, 0.80, 0.82)
	mat.emission_energy_multiplier = 0.15
	_blossom_particles.material_override = mat

	add_child(_blossom_particles)
	print("Cherry blossoms: spring petal drift particles")


func _setup_fog_weather() -> void:
	# Fog multipliers are applied per-frame in the day/night cycle update
	print("Fog: heavy atmospheric fog")


func _setup_hud() -> void:
	var canvas := CanvasLayer.new()
	canvas.name = "HUD"
	_hud_canvas = canvas
	add_child(canvas)

	var style := StyleBoxFlat.new()
	style.bg_color                   = Color(0.0, 0.0, 0.0, 0.58)
	style.corner_radius_top_left     = 7
	style.corner_radius_top_right    = 7
	style.corner_radius_bottom_left  = 7
	style.corner_radius_bottom_right = 7
	style.content_margin_left   = 14.0
	style.content_margin_right  = 14.0
	style.content_margin_top    = 10.0
	style.content_margin_bottom = 10.0

	var panel := PanelContainer.new()
	panel.position = Vector2(18.0, 18.0)
	panel.add_theme_stylebox_override("panel", style)
	canvas.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	panel.add_child(vbox)

	_coord_label = Label.new()
	_coord_label.text = "X:       0.0      Z:       0.0"
	_coord_label.add_theme_font_size_override("font_size", 22)
	_coord_label.add_theme_color_override("font_color", Color(0.85, 1.00, 0.85))
	vbox.add_child(_coord_label)

	_heading_label = Label.new()
	_heading_label.text = "Heading:    0.0°  N"
	_heading_label.add_theme_font_size_override("font_size", 22)
	_heading_label.add_theme_color_override("font_color", Color(0.85, 0.92, 1.00))
	vbox.add_child(_heading_label)

	_latlon_label = Label.new()
	_latlon_label.text = "40.782900° N    73.965400° W"
	_latlon_label.add_theme_font_size_override("font_size", 22)
	_latlon_label.add_theme_color_override("font_color", Color(1.00, 0.95, 0.75))
	vbox.add_child(_latlon_label)

	_time_label = Label.new()
	_time_label.text = "6:00 AM  [1x]"
	_time_label.add_theme_font_size_override("font_size", 22)
	_time_label.add_theme_color_override("font_color", Color(1.0, 0.88, 0.55))
	vbox.add_child(_time_label)

	_speed_label = Label.new()
	_speed_label.text = "Stroll (0.4 m/s)"
	_speed_label.add_theme_font_size_override("font_size", 22)
	_speed_label.add_theme_color_override("font_color", Color(0.75, 0.90, 1.0))
	vbox.add_child(_speed_label)

	_location_label = Label.new()
	_location_label.text = ""
	_location_label.add_theme_font_size_override("font_size", 26)
	_location_label.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, 0.95))
	_location_label.visible = false
	vbox.add_child(_location_label)

	var hint := Label.new()
	hint.text = "WASD: move   Mouse+RMB: look   Scroll/+/-: speed   9/0: wind   T: time   [/]: ±1h   P: weather   N: month   H: HUD   F9: perf"
	hint.add_theme_font_size_override("font_size", 15)
	hint.add_theme_color_override("font_color", Color(0.55, 0.55, 0.55))
	vbox.add_child(hint)

	# --- Performance budget overlay (top-right, hidden by default) ---
	_perf_canvas = CanvasLayer.new()
	_perf_canvas.name = "PerfOverlay"
	_perf_canvas.visible = false
	add_child(_perf_canvas)

	var perf_style := StyleBoxFlat.new()
	perf_style.bg_color                   = Color(0.0, 0.0, 0.0, 0.72)
	perf_style.corner_radius_top_left     = 7
	perf_style.corner_radius_top_right    = 7
	perf_style.corner_radius_bottom_left  = 7
	perf_style.corner_radius_bottom_right = 7
	perf_style.content_margin_left   = 14.0
	perf_style.content_margin_right  = 14.0
	perf_style.content_margin_top    = 10.0
	perf_style.content_margin_bottom = 10.0

	# Anchor to top-right via a MarginContainer that fills the viewport
	var perf_margin := MarginContainer.new()
	perf_margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	perf_margin.add_theme_constant_override("margin_top", 18)
	perf_margin.add_theme_constant_override("margin_right", 18)
	_perf_canvas.add_child(perf_margin)

	var perf_panel := PanelContainer.new()
	perf_panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	perf_panel.size_flags_horizontal = Control.SIZE_SHRINK_END
	perf_panel.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	perf_panel.add_theme_stylebox_override("panel", perf_style)
	perf_margin.add_child(perf_panel)

	_perf_label = Label.new()
	_perf_label.text = "--- PERFORMANCE BUDGET ---\nLoading..."
	_perf_label.add_theme_font_size_override("font_size", 18)
	_perf_label.add_theme_color_override("font_color", Color(0.9, 1.0, 0.85))
	perf_panel.add_child(_perf_label)







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

const ALM := preload("res://almanac.gd")

var _ambient_life = null    # ambient_life.gd — near fireflies + distant vague figures
var _ambient_life_off := false

var _player:        CharacterBody3D
var _hud = null     # HudManager instance (hud_manager.gd)
var _cloud_debug = null  # CloudDebug panel (cloud_debug.gd), toggle with C

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
var _grass_off := false  # --no-grass: skip grass blade particles (eval bare terrain)
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
var _eval_plot := ""  # --eval-plot[=spec] → Great Lawn model evaluation plot
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
		elif arg == "--no-grass":
			_grass_off = true
		elif key == "--time" and val != "":
			cli_time = val
		elif key == "--screenshot-file" and val != "":
			# Output path for --screenshot. Default /tmp/godot_screenshot.png
			# is a shared rendezvous — concurrent capture sessions clobber
			# each other; pass a unique path per session/script.
			_screenshot_file = val
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
		elif key == "--eval-plot":
			# Great Lawn model evaluation plot (eval_plot_builder.gd).
			# Bare flag = full lineup; =trees/=undergrowth = one section;
			# =name[,name] = matching species (single match → stand mode).
			_eval_plot = eq_val if has_eq and eq_val != "" else "all"
			print("Eval plot: %s" % _eval_plot)
		elif arg == "--no-life":
			_ambient_life_off = true
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
		elif key == "--shadow-splits" and val != "":
			_cli_shadow_splits = int(val)
		elif key == "--shadow-blend" and val != "":
			_cli_shadow_blend = int(val)
		elif key == "--render-scale" and val != "":
			_cli_render_scale = float(val)
		elif key == "--upscale" and val != "":
			# --upscale=fsr2:0.77 — temporal/spatial upscaler experiment knob
			# (fsr2 / fsr1 / bilinear). Unlike --render-scale (always bilinear),
			# fsr2 reconstructs toward native from temporal samples.
			var up_parts := val.split(":")
			_cli_upscale_mode = up_parts[0]
			if up_parts.size() > 1:
				_cli_upscale_scale = float(up_parts[1])
			print("[DIAG] upscale %s @ %.2f" % [_cli_upscale_mode, _cli_upscale_scale])
		elif key == "--grass-spacing-mult" and val != "":
			_cli_grass_spacing_mult = float(val)
			print("[DIAG] grass spacing ×%.2f" % _cli_grass_spacing_mult)
		elif key == "--grass-grid-mult" and val != "":
			_cli_grass_grid_mult = float(val)
			print("[DIAG] grass grid ×%.2f" % _cli_grass_grid_mult)
		elif key == "--grass-highlight":
			_cli_grass_highlight = true
			print("[DIAG] grass biome highlight requested")
		elif key == "--cloud-seed" and val != "":
			_cli_cloud_seed = int(val)
		elif key == "--wind" and val != "":
			# --wind=strength (0..3, the in-game override scale) — fixes the
			# wind for flow checks / calibration captures.
			_cli_wind_override = float(val)
			print("[DIAG] wind override %.2f" % _cli_wind_override)
		elif key == "--wind-dir" and val != "":
			# --wind-dir=degrees (0 = +X east, 90 = +Z south, world axes)
			_cli_wind_dir_deg = float(val)
			print("[DIAG] wind direction %.0f deg" % _cli_wind_dir_deg)
		elif key == "--sky-cal" and val != "":
			# --sky-cal=bg:sun:amb — background brightness, cloud direct-sun
			# and cloud ambient multipliers (calibration sweeps).
			var sc := val.split(":")
			if sc.size() >= 1: _cli_sky_bg = float(sc[0])
			if sc.size() >= 2: _cli_sky_sun = float(sc[1])
			if sc.size() >= 3: _cli_sky_amb = float(sc[2])
			print("[DIAG] sky-cal bg=%.2f sun=%.2f amb=%.2f" % [_cli_sky_bg, _cli_sky_sun, _cli_sky_amb])
		elif key == "--sun-cal" and val != "":
			_cli_sun_cal = float(val)
			print("[DIAG] sun-cal ×%.2f" % _cli_sun_cal)
		elif key == "--fog-cal" and val != "":
			# --fog-cal=sunvol:amb:emis:density:gi — volumetric-fog in-scatter
			# multipliers (aerial-perspective sweeps, rendering.md §6c).
			var fc := val.split(":")
			for fci in mini(fc.size(), _cli_fog_cal.size()):
				if fc[fci] != "": _cli_fog_cal[fci] = float(fc[fci])
			print("[DIAG] fog-cal sunvol=%.2f amb=%.2f emis=%.2f density=%.2f gi=%.2f"
					% _cli_fog_cal)
		elif key == "--turf-sheen" and val != "":
			_cli_turf_sheen = float(val)
			print("[DIAG] turf-sheen %.2f" % _cli_turf_sheen)
		elif key == "--cloud-map" and val != "":
			# --cloud-map=name forces a weather map (fair_cumulus,
			# stratocumulus_sheet, stratus_overcast, storm_congestus,
			# broken_dramatic) regardless of weather state.
			_cli_cloud_map = val
			print("[DIAG] cloud map forced: %s" % val)
		elif key == "--sky-dramatic" and val != "":
			# --sky-dramatic=1/0 forces the dramatic-sky schedule on/off.
			_cli_sky_dramatic = int(val)
			print("[DIAG] dramatic sky override: %d" % _cli_sky_dramatic)
		elif key == "--high-clouds" and val != "":
			# --high-clouds=cir:cs:ac forces the high ice layer opacities
			# (cirrus, cirrostratus, altocumulus) regardless of weather/day.
			var hc := val.split(":")
			if hc.size() >= 1 and hc[0] != "": _cli_high_clouds.x = float(hc[0])
			if hc.size() >= 2 and hc[1] != "": _cli_high_clouds.y = float(hc[1])
			if hc.size() >= 3 and hc[2] != "": _cli_high_clouds.z = float(hc[2])
			print("[DIAG] high-clouds cir=%.2f cs=%.2f ac=%.2f"
					% [_cli_high_clouds.x, _cli_high_clouds.y, _cli_high_clouds.z])
		elif key == "--canopy-ao" and val != "":
			var ca := val.split(":")
			if ca.size() >= 1 and ca[0] != "": _cli_canopy_ao.x = float(ca[0])
			if ca.size() >= 2 and ca[1] != "": _cli_canopy_ao.y = float(ca[1])
			if ca.size() >= 3 and ca[2] != "": _cli_canopy_ao.z = float(ca[2])
			print("[DIAG] canopy-ao core=%.2f exp=%.2f shell=%.2f"
					% [_cli_canopy_ao.x, _cli_canopy_ao.y, _cli_canopy_ao.z])
		elif key == "--shots" and val != "":
			# --shots=x,z,yaw[,pitch[,hour]];x,z,yaw... — generic teleporting
			# snapshot bot: every pose captured in ONE Godot session (launch
			# cost paid once). Output --shots-dir (default /tmp/tour).
			# Launch-time flags (--tier-isolate etc.) still need their own
			# sessions — this is for multi-POSE work under one config.
			_cli_shots_spec = val
		elif key == "--shots-dir" and val != "":
			_tour_save_dir = val
		elif key == "--dump-near" and val != "":
			# --dump-near=x,z[,r] — after scene build, list MeshInstance/MMI
			# geometry intersecting the ground circle, then quit. For
			# identifying mystery props at walk-around coords.
			var dn := val.split(",")
			if dn.size() >= 2:
				_dump_near = Vector3(float(dn[0]), float(dn[1]),
						float(dn[2]) if dn.size() > 2 and dn[2] != "" else 30.0)
				_dump_near_set = true
		elif key == "--hide-node" and val != "":
			# --hide-node=substr[,substr...] — hide scene nodes whose name
			# contains any substring (case-insensitive). Visual A/B for
			# builder-placed props that have no --diag-hide entry.
			_hide_node_substrings = Array(val.to_lower().split(","))
		elif arg == "--shadow-census":
			_diag_shadow_census = true
		elif arg == "--screenshot":
			_auto_screenshot = true
		elif arg == "--park":
			_force_park = true  # force the plain park (skip the default eval garden)
	# Legacy trigger: sniffing --quit-after stopped working when the engine
	# began stripping recognized flags from OS.get_cmdline_args() (found
	# 2026-06-10 on 4.6.1 — loop never matches). Use `-- --screenshot`.
	for earg in OS.get_cmdline_args():
		if earg.begins_with("--quit-after"):
			_auto_screenshot = true
			break
	# Default dev launch: a no-flag run drops into the single-species eval garden
	# in the Great Lawn (user 2026-06-19). Suppressed by any explicit mode —
	# --pos, --walk, --tour/--shots, --terrain-only, --screenshot, or --park
	# (the escape hatch back to the plain park walk).
	if _eval_plot == "" and not _force_park and not _cli_pos_set and not _walk_bot \
			and not _terrain_only and not _auto_screenshot and _cli_shots_spec == "":
		var _has_tour := false
		for a in OS.get_cmdline_user_args():
			if a in ["--tour", "--tour-showcase", "--readme-shots"]:
				_has_tour = true
				break
		if not _has_tour:
			_eval_plot = preload("res://eval_plot_builder.gd").DEFAULT_EVAL_SPECIES
			print("No mode flag → default eval garden: %s (use --park for the plain park)" % _eval_plot)
	# Eval plot: unless --pos was given, spawn at the plot's south edge
	# facing north up the specimen rows (SPAWN is x, yaw_degrees, z).
	if _eval_plot != "" and not _cli_pos_set:
		var esp: Vector3 = preload("res://eval_plot_builder.gd").SPAWN
		_cli_pos = esp
		_cli_pos_set = true
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
	_day_night.sky_cal_override = Vector3(_cli_sky_bg, _cli_sky_sun, _cli_sky_amb)
	_day_night.sun_cal_override = _cli_sun_cal
	_day_night.fog_cal_override = _cli_fog_cal
	_day_night.cloud_map_override = _cli_cloud_map
	_day_night.dramatic_override = _cli_sky_dramatic
	_day_night.high_clouds_override = _cli_high_clouds
	# Register global shader parameters BEFORE park_loader creates materials
	RenderingServer.global_shader_parameter_add("wind_vec", RenderingServer.GLOBAL_VAR_TYPE_VEC2, Vector2.ZERO)
	RenderingServer.global_shader_parameter_add("snow_cover", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("rain_wetness", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("sky_reflect_color", RenderingServer.GLOBAL_VAR_TYPE_VEC3, Vector3(0.32, 0.38, 0.45))
	RenderingServer.global_shader_parameter_add("season_t", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, _season_t)
	RenderingServer.global_shader_parameter_add("lightning_flash", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("dew_amount", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("lamp_glow", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	RenderingServer.global_shader_parameter_add("ambient_life_light", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 1.0)
	RenderingServer.global_shader_parameter_add("cloud_coverage_g", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.5)
	RenderingServer.global_shader_parameter_add("cloud_speed_g", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.00004)
	# Turf sheen blend (grass.md §6 calibration; --turf-sheen overrides)
	RenderingServer.global_shader_parameter_add("turf_sheen", RenderingServer.GLOBAL_VAR_TYPE_FLOAT,
		TURF_SHEEN if _cli_turf_sheen < 0.0 else _cli_turf_sheen)
	# Crown-interior AO mapping (trees.md §6; --canopy-ao=core:exp:shell)
	RenderingServer.global_shader_parameter_add("canopy_ao", RenderingServer.GLOBAL_VAR_TYPE_VEC3,
		Vector3(CANOPY_AO_CORE if _cli_canopy_ao.x < 0.0 else _cli_canopy_ao.x,
				CANOPY_AO_EXP if _cli_canopy_ao.y < 0.0 else _cli_canopy_ao.y,
				CANOPY_AO_SHELL if _cli_canopy_ao.z < 0.0 else _cli_canopy_ao.z))
	# Player camera world position — pushed each frame so distance-based
	# effects (LOD dither) compute against the player view, not whatever
	# camera is active in the current render pass (shadow / reflection).
	RenderingServer.global_shader_parameter_add("player_world_pos", RenderingServer.GLOBAL_VAR_TYPE_VEC3, Vector3.ZERO)
	_wind_system = preload("res://wind_system.gd").new()
	_wind_system.name = "WindSystem"
	if _cli_wind_override >= 0.0:
		_wind_system.wind_override = _cli_wind_override
	if not is_nan(_cli_wind_dir_deg):
		_wind_system.dir_override = deg_to_rad(_cli_wind_dir_deg)
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
		# Fantasy grass: terrain grass-zones match the blade shader's lush green.
		_set_terrain_param("fantasy", GRASS_FANTASY)
		print("main: canopy map: %d ms" % (Time.get_ticks_msec() - _mt)); _mt = Time.get_ticks_msec()
		# Unified to Godot's particle system 2026-05-09: Tier 1 + Tier 0 + Accents
		# all run through _setup_grass_particles. Previous GDExtension (Tier 1) and
		# static tuft chunks (Tier 2) retired — single source of truth for zone
		# filtering, density tables, and coordinate transforms.
		if _terrain3d and not _grass_off:
			_setup_grass_particles()
			if _cli_grass_highlight:
				_diag_toggle_grass_highlight()
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
	_cloud_debug = preload("res://cloud_debug.gd").new()
	_cloud_debug.setup(self, self)
	_setup_color_grade()
	if not _terrain_only:
		_setup_lamp_lights()
	print("main: total _ready: %d ms" % (Time.get_ticks_msec() - _mt))
	_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	_weather_mgr.mode = _weather_mode
	# Ambient life — opt-in QoL liveliness for testers (fireflies + distant figures).
	# Off in terrain-only / capture; disable with --no-life; toggle in-game with L.
	if not _terrain_only and not _ambient_life_off and _player:
		_ambient_life = preload("res://ambient_life.gd").new()
		_ambient_life.name = "AmbientLife"
		_ambient_life.player = _player
		_ambient_life.camera = _player_camera
		_ambient_life.terrain_height_fn = Callable(self, "_terrain_height")
		_ambient_life.park_loader = _park_loader
		_ambient_life.lamp_positions = _lamp_positions
		add_child(_ambient_life)
		_ambient_life.setup()
	# Ambient audio — disabled for now
	#if not _terrain_only and _park_loader and _player:
	#	_audio_manager = preload("res://audio_manager.gd").new(_park_loader)
	#	_audio_manager.setup(_player, _park_loader.water_bodies, _park_loader.boundary_polygon)
	#	print("main: audio: ready")
	# Check for --tour / --tour-showcase / --readme-shots / --shots CLI arg
	if _cli_shots_spec != "":
		_tour_mode = true
		_build_cli_shots()
		_tour_state = 0  # WAIT_LOAD
		_tour_timer = 0.0
		_tour_idx = 0
		_tour_settle_time = 3.0
		_player.tour_freeze = true
		DirAccess.make_dir_recursive_absolute(_tour_save_dir)
		print("Shots mode: %d poses queued → %s/" % [_tour_shots.size(), _tour_save_dir])
	for arg in OS.get_cmdline_user_args():
		if _tour_mode:
			break
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
var _cli_shots_spec := ""           # --shots=x,z,yaw[,pitch[,hour]];...
var _dump_near := Vector3.ZERO      # x, z, radius (--dump-near)
var _dump_near_set := false
var _dump_near_timer := 0.0
var _dump_near_done := false
var _hide_node_substrings: Array = []
var _hide_node_timer := 0.0
var _hide_nodes_done := false
var _labels_hidden_for_screenshot := false
var _screenshot_counter := 0  # incrementing counter for F12 screenshots
var _auto_screenshot := false  # only auto-capture when --quit-after is used
var _force_park := false  # --park: skip the default eval garden, load the plain park
var _screenshot_file := "/tmp/godot_screenshot.png"  # --screenshot-file=path overrides
var _lt_screenshot_pending := false  # debounce for gamepad left trigger screenshots

# Distance overlay (F1) — floating Label3Ds on nearest trees, color-coded by the
# rendered LOD tier: green lod0 (near) → yellow lod1 (mid) → impostor billboard, with
# the impostor range SPLIT at FAR_LABEL_DIST: blue (near impostor, ~200-500m, reads
# well) → red (far impostor, 500-800m, the band under repair). Far-impostor labels are
# lifted above the canopy so they're legible over the tree instead of buried in it.
# Trees past IMPOSTOR_FAR are culled (not drawn) so they get no label.
var _dist_overlay_visible := false
var _dist_labels: Array = []  # Array[Label3D] — pool, reused each frame
const _DIST_POOL_SIZE := 64  # 16/band round-robin — was 40 (~10/band), too few: far (red) band
                            # ran out before reaching mid-distance trees, leaving centre trees unlabelled
const _DIST_MAX_RANGE := 800.0   # reaches IMPOSTOR_FAR so the 500-800m far band is labelled (was 500)
const _DIST_FAR_LABEL_DIST := 500.0  # impostor blue→red split + canopy-lift threshold (matches shader far_band_begin)
var _dist_tree_positions: PackedVector3Array = PackedVector3Array()  # cached once
var _dist_tree_bands: PackedVector2Array = PackedVector2Array()  # parallel: (lod1_end, mesh_end) per tree, for tier-true label colour
var _dist_impostor_far := 500.0  # tree_builder.IMPOSTOR_FAR — impostor→cull handoff, cached on first toggle (overwritten from tb at runtime)

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

func _build_cli_shots() -> void:
	## --shots= spec → tour-shot dicts. Pose hour defaults to the launch
	## --time so a whole diagnostic set shares one time of day unless a
	## per-shot hour is given.
	_tour_shots.clear()
	var i := 0
	for spec in _cli_shots_spec.split(";", false):
		var p := spec.split(",")
		if p.size() < 2:
			continue
		var shot := {
			"name": "shot_%02d" % i,
			"x": float(p[0]),
			"z": float(p[1]),
			"yaw": float(p[2]) if p.size() > 2 and p[2] != "" else 0.0,
			"pitch": float(p[3]) if p.size() > 3 and p[3] != "" else 0.0,
			"hour": float(p[4]) if p.size() > 4 and p[4] != "" else _time_of_day,
			"filename": "shot_%02d_x%s_z%s" % [i, p[0], p[1]],
		}
		# Optional 6th field: camera height above terrain (metres). Lets a shot
		# pose a high top-down camera (with pitch=-90) for LOD-handoff diagnostics.
		if p.size() > 5 and p[5] != "":
			shot["height"] = float(p[5])
		_tour_shots.append(shot)
		i += 1


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
func _exit_tree() -> void:
	## Quit-path teardown (zero-error goal, 2026-06-11): free everything we
	## allocated directly on the RenderingServer / RenderingDevice. Node
	## teardown can't do it for us (chunk builders aren't scene nodes, the
	## volumetric sky is a Resource whose PREDELETE can't reach self), and
	## whatever is still live at exit prints the RID-leak error wall —
	## leaked multimesh instances also pin their meshes/materials.
	if _park_loader:
		if _park_loader._undergrowth_builder:
			_park_loader._undergrowth_builder.free_all_chunks()
		if _park_loader._ground_cover_builder:
			_park_loader._ground_cover_builder.free_all_chunks()
	if _vol_sky:
		_vol_sky.can_run = false
		# Detach the per-frame hook BEFORE freeing RD RIDs — a final
		# frame_pre_draw after cleanup dispatched against freed uniform
		# sets ("Parameter us is null" / invalid-texture exit errors).
		if RenderingServer.frame_pre_draw.is_connected(_vol_sky.update_sky):
			RenderingServer.frame_pre_draw.disconnect(_vol_sky.update_sky)
		# Drop the sky material's references to the Texture2DRDs so the
		# material system doesn't rebuild uniform sets against freed RIDs.
		for pn in ["blend_from_texture", "blend_to_texture",
				"sky_blend_from_texture", "sky_blend_to_texture"]:
			_vol_sky.sky_material.set_shader_parameter(pn, null)
		# cleanup() frees RD RIDs — serialize with the per-frame compute
		# dispatches by running it on the render thread, then flush so it
		# completes before the rest of teardown frees the LUT resources.
		RenderingServer.call_on_render_thread(_vol_sky.cleanup)
		RenderingServer.force_sync()
	# Name any orphan nodes on verbose runs (zero-error goal: anything
	# printed here will appear in the exit-time ObjectDB leak list).
	if OS.is_stdout_verbose():
		print_orphan_nodes()


func _process(delta: float) -> void:
	# Player camera world position — must be pushed every frame, *before*
	# any early-return paths (tour mode, walk bot), so distance-based
	# shaders (tree LOD dither) compute against the actual view.
	if _player_camera:
		RenderingServer.global_shader_parameter_set("player_world_pos", _player_camera.global_position)

	# Wind + GPU grass push + volumetric clouds — must run BEFORE the tour
	# and walk-bot early returns: those paths exist to CAPTURE the world,
	# and skipping the wind tick froze the cloud system in every capture
	# (2026-06-11 — the "static clouds" flow checks measured a harness
	# artifact: wind_speed stayed at the 0.03 setup value).
	var _tw0 := Time.get_ticks_usec()
	_wind_system.update(delta, _time_of_day, _weather_mode)
	_wind_vec = _wind_system.wind_vec

	if _vol_sky:
		var wlen: float = _wind_vec.length()
		if wlen > 0.01:
			_vol_sky.wind_direction = atan2(_wind_vec.y, _wind_vec.x)
		# Cloud-level wind in real m/s (2026-06-11 static-cloud fix).
		# wind_vec is a SHADER-units vector (typ. 0.2-0.6, max ~1.65 at the
		# 300% override) — the old wlen*0.6 mapping drove ~2 m/s of world
		# drift at 2 km altitude, imperceptible; the "motion" users saw was
		# the detail-churn defect. Winds aloft exceed surface wind almost
		# always: floor of 4 m/s at surface calm, ~14 m/s at default
		# breeze, ~24 m/s with wind cranked (real cumulus: 5-15+ m/s).
		_vol_sky.wind_speed = 4.0 + wlen * 12.0
	_prof_wind_us = lerpf(float(Time.get_ticks_usec() - _tw0), _prof_wind_us, PROF_SMOOTH)

	# --dump-near / --hide-node diagnostics. MUST run before the tour/walk
	# early returns (same trap as the wind tick above — capture paths skip
	# the rest of _process). Hide fires at 7s, before the tour's first
	# capture (12s load wait + 3s settle).
	if _dump_near_set and not _dump_near_done:
		_dump_near_timer += delta
		if _dump_near_timer >= 8.0:
			_dump_near_done = true
			_do_dump_near()
			get_tree().quit()
	if not _hide_node_substrings.is_empty() and not _hide_nodes_done:
		_hide_node_timer += delta
		if _hide_node_timer >= 7.0:
			_hide_nodes_done = true
			var hstack: Array = [get_tree().root]
			var hidden := 0
			while not hstack.is_empty():
				var hn: Node = hstack.pop_back()
				for hc in hn.get_children():
					hstack.push_back(hc)
				if hn is Node3D:
					var lname := String(hn.name).to_lower()
					for sub in _hide_node_substrings:
						if lname.contains(String(sub)):
							(hn as Node3D).visible = false
							hidden += 1
							break
			print("[DIAG] hide-node %s: %d nodes hidden" % [str(_hide_node_substrings), hidden])

	# Undergrowth + ground-cover chunk builders — MUST run BEFORE the tour /
	# walk-bot early returns. These are queue-driven (chunks drain one-per-frame
	# from update_camera), so the capture paths — which exist to photograph the
	# world — were skipping every undergrowth/ground-cover update and producing
	# screenshots with no forbs, ferns, spicebush, leaf litter, etc. (same trap
	# as the wind tick above). During the tour SETTLE state and the walk-bot
	# settle phase the per-frame ticks here let the nearby chunks build before
	# the first capture. (2026-06-12)
	var _t0: int  # profiling scratch (shared below)
	_t0 = Time.get_ticks_usec()
	if _player and _park_loader and _park_loader._undergrowth_builder:
		_park_loader._undergrowth_builder.season_t = _season_t
		_park_loader._undergrowth_builder.rain_wetness = _rain_wetness
		_park_loader._undergrowth_builder.update_camera(_player.global_position)
	_prof_undergrowth_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_undergrowth_us, PROF_SMOOTH)
	_t0 = Time.get_ticks_usec()
	if _player and _park_loader and _park_loader._ground_cover_builder:
		_park_loader._ground_cover_builder.season_t = _season_t
		_park_loader._ground_cover_builder.update_camera(_player.global_position)

	if _ambient_life:
		var _sun_elev: float = ALM.sun_horizontal(_season_t, _time_of_day).x
		RenderingServer.global_shader_parameter_set("ambient_life_light",
			clampf(0.12 + 0.95 * smoothstep(-6.0, 12.0, _sun_elev), 0.1, 1.05))
		_ambient_life.time_of_day = _time_of_day
		_ambient_life.season_t = _season_t
		_ambient_life.weather_mode = _weather_mode
		_ambient_life.sun_elevation_deg = _sun_elev
		_ambient_life.update(delta)
	_prof_ground_cover_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_ground_cover_us, PROF_SMOOTH)

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
				img.save_png(_screenshot_file)
				print("Screenshot saved to %s" % _screenshot_file)
			if _player:
				_player.set_physics_process(true)
			if _hud.canvas:
				_hud.canvas.visible = true  # restore HUD after capture
				_set_labels_visible(true)
	# Update lamp lights every 0.5s
	_t0 = Time.get_ticks_usec()
	_lamp_light_timer += delta
	if _lamp_light_timer >= LAMP_LIGHT_UPDATE_INTERVAL:
		_lamp_light_timer = 0.0
		_update_lamp_lights()
	_prof_lamps_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_lamps_us, PROF_SMOOTH)

	# (Wind + cloud coupling moved to the top of _process — before the
	# tour / walk-bot early returns.)

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

	# (Undergrowth + ground-cover chunk builders moved to the top of _process —
	# before the tour / walk-bot early returns, so capture modes get them.)

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
	if _cloud_debug and _cloud_debug.visible:
		_cloud_debug.refresh()
	_prof_hud_us = lerpf(float(Time.get_ticks_usec() - _t0), _prof_hud_us, PROF_SMOOTH)

	if _dist_overlay_visible:
		_dist_overlay_update()

	# Periodic perf log — runs regardless of overlay state, so we can
	# A/B test the overlay's own cost by toggling F9 off.
	var pf_ms: float = Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	_pf_window_max_ms = maxf(_pf_window_max_ms, pf_ms)
	if pf_ms > 8.0:
		_pf_window_spikes += 1
	_run_time += delta
	var d_ms: float = delta * 1000.0
	_df_window_max_ms = maxf(_df_window_max_ms, d_ms)
	if d_ms > 8.0:
		_df_window_spikes += 1
	if d_ms > 50.0 and _spike_prints_left > 0:
		_spike_prints_left -= 1
		print("[SPIKE] t=%.1fs delta=%.1fms time_process=%.1fms" % [
			_run_time, d_ms, pf_ms])
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
		print("[PERF] fps=%d process=%.1f pmax=%.1f pspk=%d dmax=%.1f dspk=%d physics=%.1f sub=%.2f unacc=%.1f vpcpu=%.1f vpgpu=%.1f vistri=%d shobj=%d shtri=%d overlay=%s" % [
			int(fps), p_ms, _pf_window_max_ms, _pf_window_spikes,
			_df_window_max_ms, _df_window_spikes, phy_ms,
			sub_us / 1000.0, p_ms - sub_us / 1000.0,
			vpcpu_ms, vpgpu_ms, vis_p, sh_o, sh_p,
			"ON" if _hud.perf_visible else "OFF"])
		_pf_window_max_ms = 0.0
		_pf_window_spikes = 0
		_df_window_max_ms = 0.0
		_df_window_spikes = 0


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
	# SDFGI strength readout (user 2026-06-21 PM) — live energy/feedback so the
	# ; / ' dial can be read off the F9 HUD while tuning to "less powerful".
	if _env:
		data["sdfgi_on"] = _env.sdfgi_enabled
		data["sdfgi_energy"] = _env.sdfgi_energy
		data["sdfgi_feedback"] = _env.sdfgi_bounce_feedback
	# Tree LOD instance counts (populated at build time by tree_builder)
	if _park_loader and _park_loader._tree_builder:
		var tb = _park_loader._tree_builder
		data["tree_lod0"] = tb.lod0_instances
		data["tree_lod0_chunks"] = tb.lod0_chunks
		data["tree_lod1"] = tb.lod1_instances
		data["tree_lod1_chunks"] = tb.lod1_chunks
		# Far LOD tier removed 2026-06-22 (full reset) — no far-tier counts.
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


func _do_dump_near() -> void:
	## --dump-near diagnostic: list scene geometry whose footprint touches
	## the XZ circle. Combined builder meshes (e.g. RetainingWalls) cover
	## huge AABBs — a hit means "candidate", confirm with --hide-node A/B.
	var cx: float = _dump_near.x
	var cz: float = _dump_near.y
	var r: float = _dump_near.z
	print("[DUMP] geometry intersecting circle (%.1f, %.1f) r=%.0f:" % [cx, cz, r])
	var stack: Array = [get_tree().root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		for c in n.get_children():
			stack.push_back(c)
		if not (n is VisualInstance3D):
			continue
		var vi := n as VisualInstance3D
		var aabb: AABB = vi.global_transform * vi.get_aabb()
		var nx: float = clampf(cx, aabb.position.x, aabb.position.x + aabb.size.x)
		var nz: float = clampf(cz, aabb.position.z, aabb.position.z + aabb.size.z)
		var ddx: float = cx - nx
		var ddz: float = cz - nz
		if ddx * ddx + ddz * ddz > r * r:
			continue
		if n is MultiMeshInstance3D:
			var mm: MultiMesh = (n as MultiMeshInstance3D).multimesh
			if mm == null:
				continue
			var cnt := 0
			for i in mm.instance_count:
				var p: Vector3 = (vi.global_transform * mm.get_instance_transform(i)).origin
				var pdx: float = p.x - cx
				var pdz: float = p.z - cz
				if pdx * pdx + pdz * pdz <= r * r:
					cnt += 1
					if cnt <= 6:
						print("  [MMI inst] %s #%d at (%.1f, %.1f, %.1f)"
								% [vi.get_path(), i, p.x, p.y, p.z])
			if cnt > 0:
				print("  [MMI] %s: %d/%d instances in radius" % [vi.get_path(), cnt, mm.instance_count])
		elif n is MeshInstance3D:
			var mi := n as MeshInstance3D
			var mat_desc := "none"
			if mi.mesh and mi.mesh.get_surface_count() > 0:
				var am: Material = mi.get_active_material(0)
				if am:
					mat_desc = am.get_class()
					if am is ShaderMaterial and (am as ShaderMaterial).shader:
						var sm2 := am as ShaderMaterial
						mat_desc += ":" + sm2.shader.resource_path.get_file()
						# CPU-side params, to split "params never set" from
						# "params set but not reaching the GPU".
						mat_desc += " tint=%s tex_alb=%s" % [
							str(sm2.get_shader_parameter("tint")),
							str(sm2.get_shader_parameter("tex_alb"))]
			print("  [MESH] %s pos=(%.1f,%.1f,%.1f) aabb=(%.1f×%.1f×%.1f) mat=%s vis=%s"
					% [vi.get_path(), mi.global_position.x, mi.global_position.y,
					mi.global_position.z, aabb.size.x, aabb.size.y, aabb.size.z,
					mat_desc, str(mi.visible)])


func _set_labels_visible(vis: bool) -> void:
	# Eval plot: species labels are the point of the plot — keep them in
	# captures too (this hide exists for clean README/tour shots).
	if _eval_plot != "" and not vis:
		return
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
#          treeshadows proxyshadows furnitureshadows terrainshadows clouds
#          treeshadows/terrainshadows/furnitureshadows (stay visible, stop casting)
#          clouds (freeze volumetric-cloud + sky-LUT compute; sky keeps the
#          last blended textures — isolates the per-frame dispatch cost)
var _diag_hide: Array = []
# Perf-experiment knobs: --shadow-dist=meters, --shadow-size=pixels,
# --shadow-filter=0..5 (PCF quality; project default 2). -1 = keep defaults.
var _cli_shadow_dist: float = -1.0
var _cli_shadow_size: int = -1
var _cli_shadow_filter: int = -1
# --shadow-splits=1/2/4 (cascade count), --shadow-blend=0/1 (blend_splits)
var _cli_shadow_splits: int = -1
var _cli_shadow_blend: int = -1
# --render-scale=0.5: 3D resolution scale (bilinear). Halving the scale
# quarters fragment work but leaves vertex work untouched — splits a GPU
# cost into fragment-bound vs vertex/primitive-bound.
var _cli_render_scale: float = -1.0
# --upscale=mode:scale (fsr2/fsr1/bilinear)
var _cli_upscale_mode: String = ""
var _cli_upscale_scale: float = 0.77
# Grass perf-sweep knobs (particle tiers only; Tier 2 tuft chunks untouched).
# --grass-spacing-mult=1.41 halves blade count; --grass-grid-mult=0.8 shrinks
# the covered radius (grid_width snapped odd).
var _cli_grass_spacing_mult: float = 1.0
var _cli_grass_grid_mult: float = 1.0
# --grass-highlight: flat per-biome colors at startup (zone-routing checks)
var _cli_grass_highlight: bool = false
# --cloud-seed=N: reproducible cloud field for calibration captures (-1 = random)
var _cli_cloud_seed: int = -1
# --wind=strength / --wind-dir=deg: fixed wind for flow checks (-1/NAN = auto)
var _cli_wind_override: float = -1.0
var _cli_wind_dir_deg: float = NAN
# --sky-cal=bg:sun:amb overrides (-1 = shipped defaults)
var _cli_sky_bg: float = -1.0
var _cli_sky_sun: float = -1.0
var _cli_sky_amb: float = -1.0
# --sun-cal=mult: ground-light (DirectionalLight) calibration override
# (-1 = shipped SUN_CAL; sky compensated — see day_night_cycle.gd)
var _cli_sun_cal: float = -1.0
# --fog-cal=sunvol:amb:emis:density:gi overrides (-1 = shipped FOG_CAL_*)
var _cli_fog_cal: Array = [-1.0, -1.0, -1.0, -1.0, -1.0]
# --cloud-map=name / --sky-dramatic=0|1: weather-map debug overrides
var _cli_cloud_map: String = ""
var _cli_sky_dramatic: int = -1
# --high-clouds=cir:cs:ac: force high ice layer opacities (-1 = data-driven)
var _cli_high_clouds: Vector3 = Vector3(-1.0, -1.0, -1.0)
# Turf sheen: broad white blade-cuticle specular on lawn terrain + blades
# (grass.md §6 calibration). --turf-sheen=0..1 overrides for sweeps.
# Measured 2026-06-11 with SUN_CAL=3 + thatch mix: lawn R/G 0.57→0.82
# display (reference 0.87); stills nearly identical 0.3–0.9, kept mid
# for view-dependent life. Full record: docs/grass.md §6.
const TURF_SHEEN := 0.6
var _cli_turf_sheen: float = -1.0
# Crown-interior AO (trees.md §6): leaf shaders map baked crown rho
# (COLOR.a / depth-atlas G) to AO = mix(CORE, SHELL, pow(rho, EXP)).
# SHELL < 1 because even outer leaves see ~half the sky hemisphere
# (scene ambient is calibrated for unobstructed ground); the rho
# gradient darkens further toward the crown core. Ambient-only by
# AO_LIGHT_AFFECT 0. --canopy-ao=core:exp:shell for sweeps.
const CANOPY_AO_CORE := 0.12
const CANOPY_AO_EXP := 1.6
const CANOPY_AO_SHELL := 0.55
var _cli_canopy_ao := Vector3(-1.0, -1.0, -1.0)
# --shadow-census: one-shot dump of every shadow-casting GeometryInstance3D
# (top 25 by mesh tris × instances) on the 3rd perf tick, after diag hides apply.
var _diag_shadow_census: bool = false
var _diag_tick_count: int = 0
var _diag_trees_hidden: bool = false
var _diag_ug_hidden: bool = false
var _diag_terrain_hidden: bool = false
var _diag_tree_mmis: Array = []
var _diag_log_timer: float = 0.0
# Per-window frame-time tail tracking (§5 floor anomaly). TIME_PROCESS is a
# point sample of the previous frame, so the [PERF] means hide which frames
# are slow; pmax/pspk expose the tail inside each 2s window. dmax/dspk track
# the same from _process delta (unsmoothed wall dt) — first floor run showed
# pmax 2210ms alongside 311 median fps, so the two are compared to pin down
# TIME_PROCESS semantics. [SPIKE] lines locate stalls >50ms in run time.
var _pf_window_max_ms: float = 0.0
var _pf_window_spikes: int = 0
var _df_window_max_ms: float = 0.0
var _df_window_spikes: int = 0
var _spike_prints_left: int = 20
var _run_time: float = 0.0

func _diag_toggle_terrain() -> void:
	if not _terrain3d:
		print("[DIAG] Terrain3D not present")
		return
	_diag_terrain_hidden = not _diag_terrain_hidden
	_terrain3d.visible = not _diag_terrain_hidden
	print("[DIAG] Terrain3D %s" % ("HIDDEN" if _diag_terrain_hidden else "VISIBLE"))

func _diag_toggle_trees() -> void:
	if _diag_tree_mmis.is_empty() and _park_loader:
		var patterns := ["Tree_*", "TreeLod1_*", "TreeImp_*"]
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
					for pat: String in ["Tree_*", "TreeLod1_*", "TreeImp_*"]:
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
					for pat: String in ["Tree_*", "TreeLod1_*", "TreeImp_*"]:
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
			"clouds":
				# Freeze the volumetric-cloud compute (and the sky-LUT updates
				# it drives). The sky shader keeps sampling the last blended
				# textures, so the sky stays visible but static.
				if _vol_sky:
					_vol_sky.can_run = false
			"cloudshadows":
				# Kill the procedural ground cloud-shadow bands (terrain +
				# grass shaders); visible volumetric clouds unaffected.
				if _day_night:
					_day_night.cloud_shadow_disabled = true
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
	_dist_tree_bands.clear()
	# Prefer tree_builder's per-tree LOD bands so the label colour reflects the
	# actual rendered tier (lod0 green / lod1 yellow / culled red), derived from
	# the SAME scaled handoffs the lod_fade shaders use — not a fixed distance band.
	var tb = _park_loader._tree_builder if _park_loader else null
	if tb and not tb.tree_lod_bands.is_empty():
		# Impostor tier renders from ~mesh_end out to IMPOSTOR_FAR; cache that far
		# edge so labels past mesh_end read as impostor (blue), culled only beyond it.
		_dist_impostor_far = float(tb.IMPOSTOR_FAR)
		for b in tb.tree_lod_bands:
			_dist_tree_positions.append(b["pos"])
			_dist_tree_bands.append(Vector2(b["lod1_end"], b["mesh_end"]))
		return
	# Fallback (no bands, e.g. legacy build): positions only, colour-by-tier off.
	var body: Node = null
	if _park_loader:
		body = _park_loader.get_node_or_null("TreeTrunkCollision")
	if body == null:
		print("[DIAG] Distance overlay: tree LOD bands + TreeTrunkCollision both missing")
		return
	for child in body.get_children():
		if child is CollisionShape3D:
			_dist_tree_positions.append(child.global_position)


func _dist_build_label_pool() -> void:
	for i in _DIST_POOL_SIZE:
		var lbl := Label3D.new()
		lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lbl.fixed_size = true
		lbl.pixel_size = 0.0005  # constant on-screen size regardless of distance
		lbl.no_depth_test = true
		lbl.alpha_cut = Label3D.ALPHA_CUT_DISCARD  # render with opaque-pass discard so depth-test-off actually wins over leaf transparency
		lbl.render_priority = 127  # draw last
		lbl.outline_size = 4
		lbl.outline_modulate = Color(0, 0, 0, 0.9)
		lbl.font_size = 50
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
	# Bucket in-range, in-front trees by the tier the engine actually renders for
	# each (band 0 lod0 / 1 lod1 / 2 near-impostor <500m / 3 far-impostor 500-800m),
	# using each tree's own scaled LOD handoffs. Only RENDERED tiers get a label — trees
	# past IMPOSTOR_FAR are culled (not drawn), so they're skipped, not labelled. Then
	# round-robin the label pool across bands so the far IMPOSTOR tier is always
	# represented — a plain nearest-N
	# pick fills entirely with near lod0/lod1 trees in a dense forest and impostors
	# never show.
	var max_d2: float = _DIST_MAX_RANGE * _DIST_MAX_RANGE
	# 4 bands: 0 lod0 (green), 1 lod1 (yellow), 2 near-impostor <500m (blue),
	# 3 far-impostor 500-800m (red, label lifted above canopy).
	var bands: Array = [[], [], [], []]  # per band: Array of [d2, idx]
	for i in _dist_tree_positions.size():
		var p: Vector3 = _dist_tree_positions[i]
		var d: Vector3 = p - cam_pos
		var d2: float = d.x * d.x + d.y * d.y + d.z * d.z
		if d2 > max_d2:
			continue
		if d.dot(cam_fwd) <= 0.0:
			continue  # behind camera
		# Saplings have no lod1 (lod1_end == mesh_end) so they go straight lod0→impostor.
		var lod1_end: float = 100.0
		var mesh_end: float = 200.0
		if i < _dist_tree_bands.size():
			lod1_end = _dist_tree_bands[i].x
			mesh_end = _dist_tree_bands[i].y
		var dist: float = sqrt(d2)
		var band: int
		if dist < lod1_end:
			band = 0
		elif dist < mesh_end:
			band = 1
		elif dist < _DIST_FAR_LABEL_DIST:
			band = 2  # near impostor (~200-500m) — blue
		elif dist < _dist_impostor_far:
			band = 3  # far impostor (500-800m) — red, label above canopy
		else:
			continue  # culled (not rendered) — don't label
		bands[band].append([d2, i])
	for b in bands:
		b.sort_custom(func(a, c): return a[0] < c[0])
	# Round-robin nearest-first across bands until the pool is full or all drained,
	# so the far impostor band shows up instead of being crowded out by near trees.
	var picks: Array = []  # Array of [idx, band]
	var ptr := [0, 0, 0, 0]
	var drained := false
	while picks.size() < _DIST_POOL_SIZE and not drained:
		drained = true
		for bi in 4:
			if picks.size() >= _DIST_POOL_SIZE:
				break
			if ptr[bi] < bands[bi].size():
				picks.append([bands[bi][ptr[bi]][1], bi])
				ptr[bi] += 1
				drained = false
	const _BAND_COLORS := [
		Color(0.5, 1.0, 0.5),   # lod0 base mesh — green
		Color(1.0, 1.0, 0.4),   # lod1 mid mesh — yellow
		Color(0.5, 0.75, 1.0),  # near impostor (~200-500m) — blue
		Color(1.0, 0.35, 0.3),  # far impostor (500-800m) — red
	]
	var n: int = picks.size()
	for k in n:
		var idx: int = picks[k][0]
		var band: int = picks[k][1]
		var p: Vector3 = _dist_tree_positions[idx]
		var dist: float = p.distance_to(cam_pos)
		var lbl: Label3D = _dist_labels[k]
		# Far-impostor (band 3) labels lift ABOVE the canopy so they hover legibly over
		# the tree instead of being buried in the foliage blob; nearer bands keep the
		# low "just above the trunk" float. Canopy height is estimated from the tree's
		# scaled mesh_end (mesh_end = 200·lod_scale, height = 22·lod_scale → ×0.11).
		var y_off: float = 4.0
		if band == 3:
			var mesh_end_i: float = 200.0
			if idx < _dist_tree_bands.size():
				mesh_end_i = _dist_tree_bands[idx].y
			y_off = clampf(mesh_end_i * 0.11, 6.0, 40.0) + 2.0
		lbl.global_position = p + Vector3(0.0, y_off, 0.0)
		lbl.text = "%.0fm" % dist
		lbl.modulate = _BAND_COLORS[band]
		lbl.visible = true
	for k in range(n, _DIST_POOL_SIZE):
		_dist_labels[k].visible = false


var _diag_grass_highlight: bool = false
# Indexed by biome_id: 0=Lawn 1=Shade 2=Wild 3=Sedge
const _DIAG_BIOME_COLORS := [
	Color(1.0, 0.0, 0.0),  # Lawn: red
	Color(0.0, 1.0, 0.0),  # Shade: green
	Color(0.0, 0.4, 1.0),  # Wild: blue
	Color(1.0, 1.0, 0.0),  # Sedge: yellow
]
func _diag_toggle_grass_highlight() -> void:
	# Color each biome distinctly so a single screenshot at altitude shows
	# (a) which biomes are placing blades, (b) where they're placing them
	# spatially, and (c) the height differences between blade meshes
	# (Blade_Lawn=7.6cm, Shade=12cm, Wild=25cm, Sedge=16cm).
	# Drives the live GPUParticles3D layers (_grass_particle_nodes).
	_diag_grass_highlight = not _diag_grass_highlight
	var n := 0
	for gp in _grass_particle_nodes:
		if not is_instance_valid(gp):
			continue
		var mat = gp.get("mesh_material_override")
		if not (mat is ShaderMaterial):
			continue
		mat.set_shader_parameter("debug_highlight", _diag_grass_highlight)
		var biome_id: int = mat.get_shader_parameter("biome_id")
		var c: Color = _DIAG_BIOME_COLORS[biome_id] if biome_id >= 0 and biome_id < 4 else Color(1, 0, 1)
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
	# Programmatic weather set (screenshot/capture bots): the sky should
	# already BE in the requested state, not fading toward it.
	if _vol_sky:
		_vol_sky.snap_weather_fade()


func _tour_write_manifest() -> void:
	var manifest: Dictionary = {"shots": [], "viewpoints": TourData.VIEWPOINTS.size(), "angles": TourData.ANGLES.size(), "times": TourData.TIMES.size()}
	for shot in _tour_shots:
		manifest["shots"].append({"filename": shot["filename"] + ".png", "name": shot["name"], "hour": shot["hour"], "x": shot["x"], "z": shot["z"]})
	var fa := FileAccess.open("%s/manifest.json" % _tour_save_dir, FileAccess.WRITE)
	fa.store_string(JSON.stringify(manifest, "\t"))
	fa.close()
	print("Tour: manifest.json written")


## _compass_label, _nearest_area moved to hud_manager.gd


# Re-apply the sky NOW (cloud panel). The day/night apply() throttles when
# the clock is frozen, so panel edits to the map / high-cloud amounts /
# coverage wouldn't take until time advanced — force it, and snap the
# weather-map crossfade so map changes are instant feedback.
func cloud_reapply() -> void:
	if not _day_night:
		return
	_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
		_lightning_flash, _user_gamma, _season_t)
	if _vol_sky:
		_vol_sky.snap_weather_fade()


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
	# Cloud panel (C): when open it eats its nav keys (arrows/R/Backspace).
	if event.keycode == KEY_C:
		_cloud_debug.toggle()
		return
	if _cloud_debug and _cloud_debug.handle_key(event.keycode):
		return
	if event.keycode == KEY_T:
		_time_speed_idx = (_time_speed_idx + 1) % TIME_SPEEDS.size()
		_time_speed = TIME_SPEEDS[_time_speed_idx]
		# Re-sync the sky to the CURRENT time on pause/speed change: apply()
		# throttles when the clock is frozen, so without this the sky (incl.
		# the high-cloud layer) could stay stranded at a stale state.
		_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
			_lightning_flash, _user_gamma, _season_t)
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

	elif event.keycode == KEY_F4:
		_diag_toggle_grass_highlight()
	elif event.keycode == KEY_F5:
		_diag_toggle_terrain()
	elif event.keycode == KEY_F6:
		_diag_toggle_trees()
	elif event.keycode == KEY_F7:
		_diag_toggle_undergrowth()

	elif event.keycode == KEY_F2:
		# SDFGI on/off A/B (F10 is the screenshot bot) — isolate the green
		# indirect-bounce cast on pale surfaces (bark/paths/buildings) from
		# material albedo (2026-06-21).
		if _env:
			_env.sdfgi_enabled = not _env.sdfgi_enabled
			print("SDFGI: %s" % ("ON" if _env.sdfgi_enabled else "OFF"))
	elif event.keycode == KEY_SEMICOLON or event.keycode == KEY_SLASH:
		# Live SDFGI strength dial. DOWN = ; or / , UP = ' (user 2026-06-21 PM
		# pressed / for down — bound both ; and / to lower so it works either way).
		# Nudges sdfgi_energy +/-0.02; value shown live in the F9 perf HUD. (Brackets
		# are time, comma/period are gamma.)
		if _env:
			_env.sdfgi_energy = max(0.0, _env.sdfgi_energy - 0.02)
			print("SDFGI energy: %.2f" % _env.sdfgi_energy)
	elif event.keycode == KEY_APOSTROPHE:
		if _env:
			_env.sdfgi_energy = min(1.0, _env.sdfgi_energy + 0.02)
			print("SDFGI energy: %.2f" % _env.sdfgi_energy)
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
		# Re-sync the sky to the new season (keyframes + dramatic-day pick)
		# even while the clock is paused — otherwise it stays stale.
		_day_night.force_apply(_time_of_day, _weather_mode, _wind_vec,
			_lightning_flash, _user_gamma, _season_t)
		print("Month: %s (season_t=%.2f)" % [_hud._month_name(_season_t), _season_t])
	elif event.keycode == KEY_F12:
		_take_screenshot()
	elif event.keycode == KEY_F10:
		_start_grass_tour()
	elif event.keycode == KEY_M:
		if _audio_manager:
			_audio_manager.toggle_mute()
	elif event.keycode == KEY_L:
		if _ambient_life:
			_ambient_life.set_enabled(not _ambient_life.enabled)
			print("Ambient life: %s" % ("ON" if _ambient_life.enabled else "OFF"))


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
		vol_sky.wind_speed = 4.0  # calm-floor m/s; per-frame coupling owns it
		vol_sky.texture_size = 768
		vol_sky.frames_to_update = 64
		vol_sky.sun_disk_scale = 1.5
		vol_sky.ground_color = Color(0.15, 0.18, 0.08)
		# Randomize cloud pattern each session. --cloud-seed=N makes the
		# field reproducible for calibration captures (same seed = same sky).
		if _cli_cloud_seed >= 0:
			var crng := RandomNumberGenerator.new()
			crng.seed = _cli_cloud_seed
			vol_sky.time_offset = crng.randf_range(0.0, 100.0)
			vol_sky.wind_direction = crng.randf_range(-PI, PI)
			vol_sky.set_noise_seed(crng)
			print("[DIAG] cloud seed = %d" % _cli_cloud_seed)
		else:
			vol_sky.time_offset = randf_range(0.0, 100.0)
			vol_sky.wind_direction = randf_range(-PI, PI)
		# Sky brightness calibration lives in day_night_cycle.gd (SKY_CAL_*
		# constants, sun-elevation-blended). --sky-cal routes there as an
		# exact-value override for sweeps — wired in _ready after _day_night.
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
	# GI = SDFGI, ON at Godot/AAA standard settings (user decision 2026-06-21).
	# SDFGI is the correct GI system for a large, fully-dynamic open world with a
	# day/night cycle (VoxelGI is small-scene only; LightmapGI can't bake
	# procedural/streamed content). Forward+ renderer required — confirmed in
	# project.godot. HISTORICAL CAVEAT (2026-06-19): the all-green scene once fed
	# SDFGI a uniform green indirect bounce that tinted pale surfaces (bark,
	# paths) green (forced-white-bark probe read G/R 1.18). If that returns, dial
	# it back via sdfgi_energy / sdfgi_bounce_feedback rather than disabling GI.
	_env.sdfgi_enabled         = true
	_env.sdfgi_cascades        = 6                                   # large outdoor scene needs range (4 = default)
	_env.sdfgi_min_cell_size   = 0.5                                 # ~0.5m cascade-0 detail, matches atlas resolution
	_env.sdfgi_y_scale         = Environment.SDFGI_Y_SCALE_75_PERCENT # Godot default; balanced for tree-height verticality
	_env.sdfgi_energy          = 1.0                                 # GODOT DEFAULT / community SOP (user 2026-06-21 PM: "even at 1.00 it doesn't look bad, when watching the whole day pass by... lighter at night with more, so that's good. set sdfgi to the industry standard"). The earlier 1.0->0.18 cuts were chasing a "green glow" that turned out to be fine across the day cycle. Live-tunable with ; / / / ' (see _input).
	_env.sdfgi_normal_bias     = 1.1                                 # Godot default
	_env.sdfgi_probe_bias      = 1.1                                 # Godot default
	_env.sdfgi_bounce_feedback = 0.5                                 # GODOT DEFAULT / community SOP (restored from 0.1; user 2026-06-21 PM set SDFGI to standard)
	_env.sdfgi_read_sky_light  = true                               # outdoor ambient from sky
	_env.sdfgi_use_occlusion   = true                               # higher-quality contact occlusion
	# SSIL (screen-space indirect light) left OFF: it is a separate near-field
	# effect from GI, and produced yellow-shield artifacts here pre-overhaul.
	# Enable separately if you want SDFGI complemented with screen-space bounce.
	_env.ssil_enabled          = false
	_env.ssil_radius           = 3.0    # meters — moderate reach for under-canopy bounce
	_env.ssil_intensity        = 0.6    # conservative — was causing yellow shield artifacts pre-overhaul
	_env.ssil_normal_rejection = 1.2
	_env.ssr_enabled           = false   # causes multi-colored artifacts on water from aerial view
	_env.adjustment_enabled    = true
	_env.adjustment_brightness = 1.06
	_env.fog_enabled           = false  # volumetric fog handles aerial perspective

	# Volumetric fog — realistic NYC atmospheric haze + light shafts
	# NYC clear-day visibility: 10-16km. At 1-2km (building distance),
	# aerial perspective should noticeably desaturate + lighten objects.
	_env.volumetric_fog_enabled = true
	_env.volumetric_fog_density = 0.003  # CD-style dense atmosphere — visible god-ray shafts under canopy
	# Albedo cool-tinted: the veil over distant objects should read slightly
	# BLUE (Rayleigh skylight scatter), measured warm-grey pre-calibration
	# (rendering.md §6c). Emission carries the sky-blue in-scatter floor;
	# its energy is day-blended in day_night_cycle.gd (FOG_CAL_EMIS).
	_env.volumetric_fog_albedo = Color(0.85, 0.90, 0.98)
	_env.volumetric_fog_emission = Color(0.45, 0.62, 1.0)
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
	if _cli_shadow_splits > 0:
		match _cli_shadow_splits:
			1: _sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
			2: _sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
			_: _sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
		print("[DIAG] shadow splits = %d" % _cli_shadow_splits)
	if _cli_shadow_blend >= 0:
		_sun.directional_shadow_blend_splits = _cli_shadow_blend != 0
		print("[DIAG] shadow blend splits = %d" % _cli_shadow_blend)
	if _cli_render_scale > 0.0:
		get_viewport().scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
		get_viewport().scaling_3d_scale = clampf(_cli_render_scale, 0.1, 2.0)
		print("[DIAG] 3D render scale = %.2f" % _cli_render_scale)
	# FSR2 @ 0.77 is the DEFAULT (2026-06-10, rendering.md §6.9): −4.6 ms real
	# at north_woods, stills + walk-motion ghosting check clean (1:1 crops:
	# canopy/sky edges, grass, trunks). Output stays 1080p. Opt out with
	# --upscale=off (native) or override mode:scale for A/Bs.
	if _cli_upscale_mode == "off":
		print("[DIAG] upscaler OFF — native render resolution")
	elif _cli_render_scale > 0.0:
		pass  # --render-scale (bilinear) already applied above wins
	else:
		var up_mode := _cli_upscale_mode if _cli_upscale_mode != "" else "fsr2"
		match up_mode:
			"fsr2":
				# FSR2 does its own temporal accumulation; the engine
				# force-disables TAA with a startup warning. Disable it
				# first to keep the log clean (zero-error goal) —
				# project.godot use_taa=true still applies under
				# --upscale=off / bilinear modes.
				get_viewport().use_taa = false
				get_viewport().scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR2
			"fsr1": get_viewport().scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR
			_: get_viewport().scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
		get_viewport().scaling_3d_scale = clampf(_cli_upscale_scale, 0.1, 1.0)
		print("Upscaler: %s @ %.2f internal scale" % [up_mode, _cli_upscale_scale])

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
var _landuse_texture: Texture2D  # cached for grass particle system
var _wear_texture: Texture2D  # baked turf wear (scripts/gen_wear_map.py)

# Perf: global density scale on every particle-layer spacing. 1.41 ≈ half
# the blade count — measured −3.6 ms real at ramble (rendering.md §6.5),
# visually neutral at eye height (screenshot A/B great_lawn + ramble noon:
# lawns read smoother/more mown, woodland floor character preserved).
# --grass-spacing-mult stacks on top for sweeps.
const GRASS_DENSITY_SCALE := 1.41

# Fantasy grass look (alpha-testing QoL): 1.0 = ON (one lush idealized green,
# data-driven Central Park palette/wear/seasons suspended), 0.0 = restore the
# full data-driven look. Drives the `fantasy` uniform on both the grass blade
# render shader and the terrain override shader so the two stay matched.
const GRASS_FANTASY := 1.0

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
		# Y-scale range tight (0.85-1.15): mowing homogenizes blade height
		# (docs/grass.md §3). Width randomness unchanged.
		"spacing": 0.16, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.7,
		"min_scale": Vector3(0.6, 0.85, 0.6),
		"max_scale": Vector3(1.4, 1.15, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
	{  # Blade_Shade: 3 segments, 12cm tall, 10mm wide, 6 tris
		"name": "Shade", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Blade_Shade.glb",
		# Shade: sparser woodland floor (less light, fewer blades).
		"spacing": 0.18, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.7,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.003, 0),
	},
	{  # Blade_Wild: 4 segments, 25cm tall, 15mm wide, 8 tris
		"name": "Wild", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Blade_Wild.glb",
		# Wild meadow: clumpy native grasses, gaps between bunches.
		"spacing": 0.22, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.7,
		"min_scale": Vector3(0.6, 0.6, 0.6),
		"max_scale": Vector3(1.4, 1.4, 1.4),
		"position_offset": Vector3(0, -0.005, 0),
	},
	{  # Blade_Sedge: 3 segments, 16cm tall, 9mm wide, 6 tris
		"name": "Sedge", "biome_id": 3,
		"mesh_path": "res://models/vegetation/Blade_Sedge.glb",
		# Sedge: waterside, moderate density.
		"spacing": 0.18, "cell_width": 11.0, "grid_width": 11,
		"min_distance": 4.0, "process_fps": 15,
		"random_spacing": 0.7,
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
		"min_scale": Vector3(0.6, 0.85, 0.6),
		"max_scale": Vector3(1.4, 1.15, 1.4),
		"position_offset": Vector3(0, -0.002, 0),
	},
	{  # Ryegrass broad blade — wider, shorter than Tier 1
		"name": "Lawn_T0_Wide", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Blade_Lawn_Wide.glb",
		"spacing": 0.0625, "cell_width": 4.0, "grid_width": 3,
		"random_spacing": 0.6,
		"min_scale": Vector3(0.6, 0.85, 0.6),
		"max_scale": Vector3(1.4, 1.15, 1.4),
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

# Mid/far CARD tier (the LOD that fixes the "hard cutoff line" in cpw_001/002,
# where grass geometry stopped ~20-30 m out and the world became flat terrain
# albedo). Each instance is a 3-crossed-quad card (6 tris, ~40x cheaper than the
# ~260-tri geometry clump) textured with the baked tuft silhouette
# (Blade_*_card.png alpha cutout). Runs through the SAME GPUParticles path as the
# geometry tufts — only the mesh, the card_texture override, the wide cells
# (reach ~140 m), the low density, and near_cull (start past where the geometry
# tufts are dense, so big flat cards never show up close) differ.
#
# Crossfade: geometry tufts (GRASS_BIOMES) draw 0-60 m fading from ~36 m; cards
# draw 14-140 m fading from ~84 m. They overlap 14-60 m (denser, no seam) so the
# tuft fade hands off to full card coverage — no hard line.
const GRASS_CARDS := [
	{  # Lawn card — maintained turf, densest far coverage
		"name": "Card_Lawn", "biome_id": 0,
		"mesh_path": "res://models/vegetation/Card_Lawn.glb",
		"card_texture": "res://textures/grass/Blade_Lawn_card.png",
		"spacing": 0.55, "cell_width": 40.0, "grid_width": 7,
		"near_cull": 14.0, "process_fps": 10,
		"random_spacing": 0.85,
		"min_scale": Vector3(0.85, 0.8, 0.85),
		"max_scale": Vector3(1.7, 1.25, 1.7),
		"position_offset": Vector3(0, -0.01, 0),
	},
	{  # Shade card — woodland floor
		"name": "Card_Shade", "biome_id": 1,
		"mesh_path": "res://models/vegetation/Card_Shade.glb",
		"card_texture": "res://textures/grass/Blade_Shade_card.png",
		"spacing": 0.62, "cell_width": 40.0, "grid_width": 7,
		"near_cull": 14.0, "process_fps": 10,
		"random_spacing": 0.85,
		"min_scale": Vector3(0.8, 0.7, 0.8),
		"max_scale": Vector3(1.7, 1.4, 1.7),
		"position_offset": Vector3(0, -0.01, 0),
	},
	{  # Wild card — meadow bunch grass, tallest
		"name": "Card_Wild", "biome_id": 2,
		"mesh_path": "res://models/vegetation/Card_Wild.glb",
		"card_texture": "res://textures/grass/Blade_Wild_card.png",
		"spacing": 0.70, "cell_width": 40.0, "grid_width": 7,
		"near_cull": 14.0, "process_fps": 10,
		"random_spacing": 0.7,
		"min_scale": Vector3(0.8, 0.7, 0.8),
		"max_scale": Vector3(1.7, 1.5, 1.7),
		"position_offset": Vector3(0, -0.015, 0),
	},
	{  # Sedge card — waterside
		"name": "Card_Sedge", "biome_id": 3,
		"mesh_path": "res://models/vegetation/Card_Sedge.glb",
		"card_texture": "res://textures/grass/Blade_Sedge_card.png",
		"spacing": 0.62, "cell_width": 40.0, "grid_width": 7,
		"near_cull": 14.0, "process_fps": 10,
		"random_spacing": 0.75,
		"min_scale": Vector3(0.8, 0.7, 0.8),
		"max_scale": Vector3(1.7, 1.4, 1.7),
		"position_offset": Vector3(0, -0.01, 0),
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
	all_grass_layers.append_array(GRASS_BIOMES)   # Tier 1: near geometry tufts 0-60m
	all_grass_layers.append_array(GRASS_CARDS)    # Mid/far card LOD 14-140m
	if GRASS_FANTASY < 0.5:
		# Data-driven: add near-field single-blade variety + botanical accents.
		all_grass_layers.append_array(GRASS_TIER0)    # Tier 0: 0-6m near-field variants
		all_grass_layers.append_array(GRASS_ACCENTS)  # 0-6m botanical detail
	# Fantasy: skip Tier 0 / accents — the Tier-1 CLUMP meshes cover from 0m as
	# a cohesive sward, and the single-blade Tier-0 layers are exactly the
	# isolated "spikes" we're eliminating. Also drops 12 particle layers.

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
		# Card tier: meshes carry no embedded albedo — the silhouette comes from
		# a separate baked card texture (Blade_*_card.png alpha cutout).
		if biome.has("card_texture"):
			var card_tex: Texture2D = load(biome.card_texture)
			if card_tex:
				albedo_tex = card_tex
			else:
				push_warning("Card texture not found: %s" % biome.card_texture)

		# Create particle controller node
		var gp: Node3D = Node3D.new()
		gp.set_script(gp_script)
		gp.name = "Grass_%s" % biome.name
		gp.terrain = _terrain3d
		gp.instance_spacing = biome.spacing * GRASS_DENSITY_SCALE * _cli_grass_spacing_mult
		gp.cell_width = biome.cell_width
		var gw: int = biome.grid_width
		if _cli_grass_grid_mult != 1.0:
			gw = maxi(1, int(round(gw * _cli_grass_grid_mult)))
			if gw % 2 == 0:
				gw += 1
		gp.grid_width = gw
		# Fantasy: Tier-1 clumps must reach the camera (no Tier-0 underlay), so
		# draw from 0m; data-driven keeps the configured inner cull. The card
		# tier sets its own near_cull so big flat cards never render up close
		# (geometry tufts own that band).
		gp.near_cull_distance = biome.get("near_cull",
			0.0 if GRASS_FANTASY >= 0.5 else biome.get("min_distance", 0.0))
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
		if _wear_texture:
			proc_mat.set_shader_parameter("wear_map", _wear_texture)
		gp.process_material = proc_mat

		# Render material — textured alpha-scissor grass with wind + seasons
		var render_mat := ShaderMaterial.new()
		render_mat.shader = render_shader
		render_mat.set_shader_parameter("biome_id", biome.biome_id)
		render_mat.set_shader_parameter("fantasy", GRASS_FANTASY)
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
	loader.tree_species_filter = _tree_species_filter
	loader.eval_plot = _eval_plot
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

	# Baked turf wear map (paths/benches → worn dirt; scripts/gen_wear_map.py).
	# Optional: missing file just means no baked wear (ambient mottle still
	# applies shader-side).
	var wear_global := ProjectSettings.globalize_path("res://wear_map.png")
	if FileAccess.file_exists(wear_global):
		var wear_img := Image.load_from_file(wear_global)
		if wear_img:
			if wear_img.get_format() != Image.FORMAT_L8:
				wear_img.convert(Image.FORMAT_L8)
			_wear_texture = ImageTexture.create_from_image(wear_img)
			_set_terrain_param("wear_map", _wear_texture)
			print("Terrain: loaded turf wear map %dx%d" % [wear_img.get_width(), wear_img.get_height()])
	else:
		print("Terrain: wear_map.png not found — run scripts/gen_wear_map.py for baked turf wear")


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
		# Default spawn: central Great Lawn (ellipse centre ≈ X-99 Z173), facing
		# north up the eval garden. Was Bethesda (-480,1020); user 2026-06-19
		# wants the Great Lawn as the default spawn area.
		p.position = Vector3(-99.0, _terrain_height(-99.0, 213.0) + 1.9, 213.0)
	if not _cli_pos_set:
		p.rotation_degrees.y = 360.0  # face north toward the specimen row
	p.terrain_height_fn = Callable(self, "_terrain_height")
	add_child(p)
	if _terrain_only and p.head:
		# Default to a downward look at the terrain, but honour an explicit --pitch.
		p.head.rotation_degrees.x = _cli_pitch if _cli_pitch != 0.0 else -55.0
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







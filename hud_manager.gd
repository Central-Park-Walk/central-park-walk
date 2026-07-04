extends RefCounted
## HUD overlay — coordinate display, time/speed, location name, performance overlay.
## Extracted from main.gd to separate display logic from game logic.

const TourData = preload("res://tour_data.gd")

# Geo-projection constants (must match main.gd / convert_to_godot.py)
const REF_LAT            := 40.7829
const REF_LON            := -73.9654
const METRES_PER_DEG_LAT := 110_540.0
const METRES_PER_DEG_LON := 84_264.0

const PERF_UPDATE_INTERVAL := 0.25

# Public — tour mode toggles visibility directly
var canvas: CanvasLayer
var perf_canvas: CanvasLayer
var perf_visible := false

# Labels
var _coord_label: Label
var _heading_label: Label
var _latlon_label: Label
var _time_label: Label
var _speed_label: Label
var _location_label: Label
var _perf_label: Label
var _perf_update_timer := 0.0

# Location name cache
var _cached_area := ""
var _cached_area_pos := Vector3.ZERO


func setup(parent: Node) -> void:
	canvas = CanvasLayer.new()
	canvas.name = "HUD"
	parent.add_child(canvas)

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
	hint.text = "WASD: move   Mouse+RMB: look   Scroll/+/-: speed   9/0: wind   T: time   [/]: ±1h   P: weather   N: month   C: clouds   H: HUD   F9: perf"
	hint.add_theme_font_size_override("font_size", 15)
	hint.add_theme_color_override("font_color", Color(0.55, 0.55, 0.55))
	vbox.add_child(hint)

	# --- Performance budget overlay (top-right, hidden by default) ---
	perf_canvas = CanvasLayer.new()
	perf_canvas.name = "PerfOverlay"
	perf_canvas.visible = false
	parent.add_child(perf_canvas)

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

	var perf_margin := MarginContainer.new()
	perf_margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	perf_margin.add_theme_constant_override("margin_top", 18)
	perf_margin.add_theme_constant_override("margin_right", 18)
	perf_canvas.add_child(perf_margin)

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


func update(player: CharacterBody3D, time_of_day: float,
			time_speed_name: String, season_t: float) -> void:
	if not player or not _coord_label:
		return
	var pos := player.position
	_coord_label.text = "X: %7.1f   Z: %7.1f   Alt: %6.1f" % [pos.x, pos.z, pos.y]
	var bearing := fmod(fmod(-player.rotation_degrees.y, 360.0) + 360.0, 360.0)
	_heading_label.text = "Heading: %5.1f°  %s" % [bearing, _compass_label(bearing)]
	var lat :=  REF_LAT + (-pos.z / METRES_PER_DEG_LAT)
	var lon :=  REF_LON + ( pos.x / METRES_PER_DEG_LON)
	_latlon_label.text  = "%.6f° N    %.6f° W" % [lat, absf(lon)]
	if _time_label:
		var h12: int = int(time_of_day) % 12
		if h12 == 0:
			h12 = 12
		var mins: int = int(fmod(time_of_day, 1.0) * 60.0)
		var ampm: String = "AM" if time_of_day < 12.0 else "PM"
		_time_label.text = "%d:%02d %s  [%s]  %s" % [h12, mins, ampm, time_speed_name, _month_name(season_t)]
	if _speed_label:
		_speed_label.text = "%s (%.1f m/s)" % [player.SPEED_NAMES[player._speed_idx], player.walk_speed]
	if _location_label:
		var area := _nearest_area(pos.x, pos.z)
		_location_label.text = area if area else ""
		_location_label.visible = not area.is_empty()


func update_perf(delta: float, prof: Dictionary = {}) -> void:
	if not perf_visible or not _perf_label:
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

	var tri_str: String
	if primitives >= 1_000_000:
		tri_str = "%.1fM" % (primitives / 1_000_000.0)
	elif primitives >= 1_000:
		tri_str = "%.0fK" % (primitives / 1_000.0)
	else:
		tri_str = str(primitives)

	var budget_pct := frame_ms / 16.667 * 100.0
	var budget_bar: String
	if budget_pct <= 80.0:
		budget_bar = "[OK]"
	elif budget_pct <= 100.0:
		budget_bar = "[WARN]"
	else:
		budget_bar = "[OVER]"

	var text := (
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

	# SDFGI strength readout (F2 = on/off, ; / ' = energy -/+ 0.02)
	if prof.has("sdfgi_energy"):
		var sdfgi_state: String = "ON" if prof.get("sdfgi_on", false) else "OFF"
		text += "\nSDFGI: %s  energy %.2f  fb %.2f\n" % [
			sdfgi_state, prof["sdfgi_energy"], prof.get("sdfgi_feedback", 0.0)]

	# Per-subsystem profiling breakdown
	if not prof.is_empty():
		# Separate timing entries from metadata (chunk counts etc.)
		var timing_keys := ["lamps", "wind", "weather", "undergrowth",
			"ground_cover", "daynight", "hud", "misc", "player_phy"]
		var total_us: float = 0.0
		for k in timing_keys:
			if prof.has(k):
				total_us += prof[k]
		text += "\n--- CPU SUBSYSTEMS (ms) ---\n"
		var entries: Array = []
		for k in timing_keys:
			if prof.has(k):
				entries.append([k, prof[k]])
		entries.sort_custom(func(a, b): return a[1] > b[1])
		for e in entries:
			var ms: float = e[1] / 1000.0
			var pct: float = e[1] / maxf(total_us, 1.0) * 100.0
			text += "  %-14s %5.2f  (%2.0f%%)\n" % [e[0], ms, pct]
		text += "  %-14s %5.2f\n" % ["TOTAL", total_us / 1000.0]
		var unaccounted_ms: float = process_ms - (total_us / 1000.0)
		text += "  %-14s %5.2f  (engine + unprofiled)\n" % ["unaccounted", unaccounted_ms]
		# Tree LOD instance counts (lod0 near → impostor far; mid tier removed 2026-07-03)
		if prof.has("tree_lod0"):
			text += "\nTrees: %d LOD0 / %d impostor\n" % [
				int(prof["tree_lod0"]), int(prof.get("tree_impostor", 0))]
			# NOTE: do NOT label instance counts "shadow casters" — the old
			# "(shadow casters: 6808)" here was just tree_lod0 (park-wide LOD0
			# instance total) and sent a whole perf investigation chasing tree
			# shadows that measure ~1ms (bisect 2026-07-01). Real caster load
			# is the [PERF] shobj/shtri fields.
			text += "  chunks: %d / %d\n" % [
				int(prof["tree_lod0_chunks"]), int(prof.get("tree_impostor_chunks", 0))]
		# Chunk counts
		if prof.has("ug_chunks"):
			text += "\nUndergrowth: %d chunks, %d queued\n" % [
				int(prof["ug_chunks"]), int(prof.get("ug_queue", 0))]
			if prof.has("ug_peak_build_us"):
				text += "  build: last %.1f ms, peak %.1f ms\n" % [
					prof["ug_last_build_us"] / 1000.0,
					prof["ug_peak_build_us"] / 1000.0]
		if prof.has("gc_chunks"):
			text += "GroundCover: %d chunks, %d queued\n" % [
				int(prof["gc_chunks"]), int(prof.get("gc_queue", 0))]
		# Water-mirror SubViewport: GPU ms + total raster (visible+shadow passes).
		# This cost hides inside "unaccounted" — it never shows in the main
		# viewport's render numbers (rendering.md §3f).
		if prof.has("mirror_gpu_ms"):
			var mi := int(prof.get("mirror_interval", 1))
			var rate_str := "asleep" if mi == 0 else "1/%d rate" % mi
			text += "Water mirror: %.1f ms GPU, %.1fM tris, %s\n" % [
				prof["mirror_gpu_ms"], prof["mirror_tri"] / 1_000_000.0, rate_str]

	_perf_label.text = text


func toggle_perf() -> void:
	perf_visible = not perf_visible
	if perf_canvas:
		perf_canvas.visible = perf_visible


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------
func _compass_label(deg: float) -> String:
	var labels := ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
	return labels[int(fmod(deg + 22.5, 360.0) / 45.0) % 8]


func _month_name(t: float) -> String:
	var month_idx := int(t * 3.0) % 12
	const MONTHS := ["March", "April", "May", "June", "July", "August",
		"September", "October", "November", "December", "January", "February"]
	return MONTHS[month_idx]


func _nearest_area(x: float, z: float) -> String:
	var pos := Vector3(x, 0.0, z)
	if _cached_area_pos.distance_squared_to(pos) < 25.0 and not _cached_area.is_empty():
		return _cached_area
	_cached_area_pos = pos
	for area in TourData.PARK_AREAS:
		if x >= float(area[0]) and x <= float(area[1]) and z >= float(area[2]) and z <= float(area[3]):
			_cached_area = area[4]
			return _cached_area
	_cached_area = ""
	return ""

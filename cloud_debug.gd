extends RefCounted
# In-game cloud control + live readout (toggle with C). Two jobs:
#   1. CONTROL — drive the weather map, the P2 high ice layer (cirrus /
#      cirrostratus / altocumulus), coverage, density, wind, and reseed the
#      cloud shapes live, so the sky can be dialled in without relaunching.
#   2. READOUT — show the ACTUAL values the schedule is producing
#      (canonical hour, weather state, map, cir/cs/ac, coverage, density).
#      This is also the diagnostic: open it where a sky looks wrong and the
#      real numbers are on screen instead of guessed.
#
# Nav (only while the panel is open): Up/Down select a row, Left/Right
# adjust it, R reseed shapes, A back to AUTO (hand control to the schedule).

var canvas: CanvasLayer
var _title: Label
var _readout: Label
var _rows: Label
var visible := false

var _main                       # the scene root (main.gd) for vol_sky/day_night/wind
var _day_night
var _vol_sky
var _sel := 0

# Selectable rows.
const ROW_MAP := 0
const ROW_CIRRUS := 1
const ROW_CIRROSTRATUS := 2
const ROW_ALTOCUMULUS := 3
const ROW_COVERAGE := 4
const ROW_DENSITY := 5
const ROW_WIND := 6
const ROW_COUNT := 7

const MAP_NAMES := ["fair_cumulus", "stratocumulus_sheet", "stratus_overcast",
		"storm_congestus", "broken_dramatic"]

var _rng := RandomNumberGenerator.new()


func setup(parent: Node, main_node) -> void:
	_main = main_node
	_day_night = main_node._day_night
	_vol_sky = main_node._vol_sky
	_rng.randomize()

	canvas = CanvasLayer.new()
	canvas.name = "CloudDebug"
	canvas.layer = 2
	parent.add_child(canvas)

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.02, 0.04, 0.09, 0.78)
	style.corner_radius_top_left = 7
	style.corner_radius_top_right = 7
	style.corner_radius_bottom_left = 7
	style.corner_radius_bottom_right = 7
	style.content_margin_left = 14.0
	style.content_margin_right = 14.0
	style.content_margin_top = 10.0
	style.content_margin_bottom = 10.0

	var panel := PanelContainer.new()
	panel.position = Vector2(18.0, 230.0)
	panel.add_theme_stylebox_override("panel", style)
	canvas.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	panel.add_child(vbox)

	_title = Label.new()
	_title.text = "☁  CLOUD CONTROL"
	_title.add_theme_font_size_override("font_size", 20)
	_title.add_theme_color_override("font_color", Color(0.75, 0.88, 1.0))
	vbox.add_child(_title)

	_readout = Label.new()
	_readout.add_theme_font_size_override("font_size", 16)
	_readout.add_theme_color_override("font_color", Color(0.80, 0.95, 0.85))
	vbox.add_child(_readout)

	_rows = Label.new()
	_rows.add_theme_font_size_override("font_size", 17)
	_rows.add_theme_color_override("font_color", Color(0.95, 0.95, 0.95))
	vbox.add_child(_rows)

	var hint := Label.new()
	hint.text = "↑↓ select   ←→ adjust   R: reseed shapes   Backspace: auto   C: close"
	hint.add_theme_font_size_override("font_size", 14)
	hint.add_theme_color_override("font_color", Color(0.55, 0.60, 0.68))
	vbox.add_child(hint)

	canvas.visible = false


func toggle() -> void:
	visible = not visible
	canvas.visible = visible
	if visible:
		refresh()


# Returns true if the panel consumed the key (so main doesn't also act on it).
func handle_key(keycode: int) -> bool:
	if not visible:
		return false
	match keycode:
		KEY_UP:
			_sel = (_sel - 1 + ROW_COUNT) % ROW_COUNT
		KEY_DOWN:
			_sel = (_sel + 1) % ROW_COUNT
		KEY_LEFT:
			_adjust(-1)
		KEY_RIGHT:
			_adjust(1)
		KEY_R:
			_reseed()
		KEY_BACKSPACE:
			_to_auto()
		_:
			return false
	refresh()
	return true


func _enter_manual() -> void:
	_day_night.manual_clouds = true


func _to_auto() -> void:
	_day_night.manual_clouds = false
	_day_night.cloud_map_override = ""
	_day_night.high_clouds_override = Vector3(-1.0, -1.0, -1.0)
	_main.cloud_reapply()


func _adjust(dir: int) -> void:
	_enter_manual()
	var dn = _day_night
	match _sel:
		ROW_MAP:
			var idx := MAP_NAMES.find(dn.live_map)
			if idx < 0: idx = 0
			idx = (idx + dir + MAP_NAMES.size()) % MAP_NAMES.size()
			dn.cloud_map_override = MAP_NAMES[idx]
		ROW_CIRRUS:
			dn.high_clouds_override.x = clampf(maxf(dn.live_cir, 0.0) + dir * 0.05, 0.0, 1.0)
		ROW_CIRROSTRATUS:
			dn.high_clouds_override.y = clampf(maxf(dn.live_cs, 0.0) + dir * 0.05, 0.0, 1.0)
		ROW_ALTOCUMULUS:
			dn.high_clouds_override.z = clampf(maxf(dn.live_ac, 0.0) + dir * 0.05, 0.0, 1.0)
		ROW_COVERAGE:
			dn.manual_cover = clampf(dn.manual_cover + dir * 0.05, 0.0, 0.95)
		ROW_DENSITY:
			dn.manual_density = clampf(dn.manual_density + dir * 0.01, 0.0, 0.16)
		ROW_WIND:
			var ws = _main._wind_system
			if ws.wind_override < 0.0: ws.wind_override = 1.0
			ws.wind_override = clampf(ws.wind_override + dir * 0.1, 0.0, 3.0)
	# Map / high-cloud / coverage edits only land on a sky re-apply (apply()
	# throttles while the clock is paused) — force it for instant feedback.
	_main.cloud_reapply()


func _reseed() -> void:
	# New cloud shapes on demand (addresses "same shapes over and over").
	_rng.randomize()
	if _vol_sky and _vol_sky.has_method("set_noise_seed"):
		_vol_sky.set_noise_seed(_rng)


func refresh() -> void:
	if not visible:
		return
	var dn = _day_night
	var cover := 0.0
	var dens := 0.0
	if _vol_sky:
		cover = _vol_sky.cloud_coverage
		dens = _vol_sky.density
	var wind_pct := 100.0
	if _main._wind_system and _main._wind_system.wind_override >= 0.0:
		wind_pct = _main._wind_system.wind_override * 100.0
	var mode_s: String = "MANUAL" if dn.manual_clouds else "AUTO (schedule)"
	_title.text = "☁  CLOUD CONTROL  —  %s" % mode_s
	_readout.text = ("canon %.1fh   weather %s   map %s\nLIVE  cirrus %.2f  cirrostratus %.2f  altocumulus %.2f"
			% [dn.live_canon, _main.WEATHER_NAMES[_main._weather_mode], dn.live_map,
			dn.live_cir, dn.live_cs, dn.live_ac])

	var lines := []
	lines.append(_fmt(ROW_MAP, "Weather map", dn.live_map))
	lines.append(_fmt(ROW_CIRRUS, "Cirrus", "%.2f" % dn.live_cir))
	lines.append(_fmt(ROW_CIRROSTRATUS, "Cirrostratus", "%.2f" % dn.live_cs))
	lines.append(_fmt(ROW_ALTOCUMULUS, "Altocumulus", "%.2f" % dn.live_ac))
	lines.append(_fmt(ROW_COVERAGE, "Coverage", "%.2f" % cover))
	lines.append(_fmt(ROW_DENSITY, "Density", "%.3f" % dens))
	lines.append(_fmt(ROW_WIND, "Wind", "%.0f%%" % wind_pct))
	_rows.text = "\n".join(lines)


func _fmt(row: int, name: String, val: String) -> String:
	var marker := "▶ " if row == _sel else "   "
	return "%s%-14s %s" % [marker, name, val]

extends RefCounted
## Loads data_gaps.json and creates Label3D markers for each data gap.
## Markers are hidden by default — toggled with G key.

var _loader  # park_loader.gd
var _root: Node3D  # container node for all gap markers
var _markers: Array = []  # Label3D nodes


func _init(loader) -> void:
	_loader = loader


func _build_gap_markers() -> void:
	var fa := FileAccess.open("res://data_gaps.json", FileAccess.READ)
	if not fa:
		print("GapBuilder: data_gaps.json not found — run generate_gaps.py")
		return
	var data = JSON.parse_string(fa.get_as_text())
	fa.close()
	if typeof(data) != TYPE_DICTIONARY:
		push_warning("GapBuilder: failed to parse data_gaps.json")
		return

	var gaps: Array = data.get("gaps", [])
	if gaps.is_empty():
		return

	_root = Node3D.new()
	_root.name = "DataGapMarkers"
	_root.visible = false  # hidden by default
	_loader.add_child(_root)

	var type_colors: Dictionary = {
		"photogrammetry": Color(0.90, 0.49, 0.13),  # orange
		"trees": Color(0.15, 0.68, 0.38),            # green
		"building_geometry": Color(0.58, 0.65, 0.65), # grey
	}
	var type_icons: Dictionary = {
		"photogrammetry": "SCAN NEEDED",
		"trees": "TREES NEEDED",
		"building_geometry": "3D MODEL NEEDED",
	}

	for gap in gaps:
		var gtype: String = str(gap.get("type", ""))
		var gname: String = str(gap.get("name", ""))
		var pos: Array = gap.get("pos", [0, 0])
		var gx := float(pos[0])
		var gz := float(pos[1])
		var gy: float = _loader._terrain_y(gx, gz)
		var priority: String = str(gap.get("priority", "medium"))
		var lat = gap.get("lat", 0.0)
		var lon = gap.get("lon", 0.0)

		var color: Color = type_colors.get(gtype, Color.WHITE)
		if priority == "high":
			color = color.lightened(0.2)

		# Title label — gap name
		var title := Label3D.new()
		title.text = gname
		title.position = Vector3(gx, gy + 4.5, gz)
		title.font_size = 36
		title.pixel_size = 0.012
		title.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		title.modulate = color
		title.outline_modulate = Color(0, 0, 0, 0.8)
		title.outline_size = 8
		title.no_depth_test = true
		_root.add_child(title)
		_markers.append(title)

		# Type tag — what's needed
		var tag := Label3D.new()
		var tag_text: String = type_icons.get(gtype, gtype.to_upper())
		if priority == "high":
			tag_text = "★ " + tag_text
		tag.text = tag_text
		tag.position = Vector3(gx, gy + 3.5, gz)
		tag.font_size = 28
		tag.pixel_size = 0.012
		tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		tag.modulate = Color(1, 1, 1, 0.85)
		tag.outline_modulate = Color(0, 0, 0, 0.7)
		tag.outline_size = 6
		tag.no_depth_test = true
		_root.add_child(tag)
		_markers.append(tag)

		# Coordinates — so contributors can navigate in real world
		var coord := Label3D.new()
		coord.text = "%.4f°N  %.4f°W" % [float(lat), absf(float(lon))]
		coord.position = Vector3(gx, gy + 2.7, gz)
		coord.font_size = 22
		coord.pixel_size = 0.012
		coord.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		coord.modulate = Color(0.7, 0.7, 0.7, 0.7)
		coord.outline_modulate = Color(0, 0, 0, 0.5)
		coord.outline_size = 4
		coord.no_depth_test = true
		_root.add_child(coord)
		_markers.append(coord)

		# Size hint or extra info
		var hint: String = str(gap.get("size_hint", ""))
		if hint.is_empty() and gap.has("current"):
			hint = "Have %s, need %s" % [str(gap.get("current", "?")), str(gap.get("expected", "?"))]
		if not hint.is_empty():
			var info := Label3D.new()
			info.text = hint
			info.position = Vector3(gx, gy + 2.0, gz)
			info.font_size = 20
			info.pixel_size = 0.012
			info.billboard = BaseMaterial3D.BILLBOARD_ENABLED
			info.modulate = Color(0.8, 0.8, 0.8, 0.6)
			info.outline_modulate = Color(0, 0, 0, 0.4)
			info.outline_size = 4
			info.no_depth_test = true
			_root.add_child(info)
			_markers.append(info)

	print("GapBuilder: %d gap markers created (G to toggle)" % gaps.size())


func set_visible(vis: bool) -> void:
	if _root:
		_root.visible = vis

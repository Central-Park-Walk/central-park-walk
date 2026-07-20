# Isolated dense-stand FPS probe for authored sculpted trees.
# Does not replace production london_plane_{s,m,l}.glb assets.
#
#   xvfb-run -a -s "-screen 0 1920x1080x24" \
#     "$GODOT" --path . --resolution 1920x1080 --disable-vsync \
#     -s res://scripts/tree_sculpt/dense_stand_gate.gd
extends SceneTree

const SPECIES := ["london_plane_sculpt_young", "london_plane_sculpt_mature", "london_plane_sculpt_veteran"]
const COUNT := 80  # ~240 trees in view ≈ deep-woodland near-band density

func _init() -> void:
	await process_frame
	await process_frame
	await _run()

func _run() -> void:
	var root := Node3D.new()
	root.name = "DenseStand"
	get_root().add_child(root)

	var camera := Camera3D.new()
	root.add_child(camera)
	camera.current = true
	camera.look_at_from_position(Vector3(0, 8, 24), Vector3(0, 6, 0))

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-42, 35, 0)
	sun.shadow_enabled = true
	root.add_child(sun)

	var env := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.45, 0.55, 0.7)
	env.environment = environment
	root.add_child(env)

	var rng := RandomNumberGenerator.new()
	rng.seed = 17
	var tris := 0
	for species in SPECIES:
		var path := "res://models/trees/%s.glb" % species
		if not ResourceLoader.exists(path):
			push_error("missing %s" % path)
			quit(2)
			return
		var scene: PackedScene = load(path)
		var sample: Node3D = scene.instantiate()
		var mesh_instance := _first_mesh(sample)
		if mesh_instance == null:
			push_error("no mesh in %s" % path)
			quit(2)
			return
		var mesh: Mesh = mesh_instance.mesh
		for surface in range(mesh.get_surface_count()):
			var arrays := mesh.surface_get_arrays(surface)
			var indices = arrays[Mesh.ARRAY_INDEX]
			if indices:
				tris += int(indices.size() / 3)
			else:
				tris += int(arrays[Mesh.ARRAY_VERTEX].size() / 3)
		var multimesh := MultiMesh.new()
		multimesh.transform_format = MultiMesh.TRANSFORM_3D
		multimesh.mesh = mesh
		multimesh.instance_count = COUNT
		for i in COUNT:
			var x := rng.randf_range(-28.0, 28.0)
			var z := rng.randf_range(-28.0, 28.0)
			var yaw := rng.randf_range(0.0, TAU)
			var xf := Transform3D(Basis.from_euler(Vector3(0, yaw, 0)), Vector3(x, 0, z))
			multimesh.set_instance_transform(i, xf)
		var node := MultiMeshInstance3D.new()
		node.multimesh = multimesh
		root.add_child(node)
		sample.queue_free()

	await process_frame
	await create_timer(3.0).timeout
	var samples: Array[float] = []
	for _i in 120:
		await process_frame
		samples.append(Engine.get_frames_per_second())
	samples.sort()
	var median: float = samples[samples.size() / 2]
	var total := 0.0
	for value in samples:
		total += value
	var report := {
		"instances": COUNT * SPECIES.size(),
		"median_fps": median,
		"min_fps": samples[0],
		"avg_fps": total / samples.size(),
		"estimated_surface_tris_one_each": tris,
		"note": "isolated MultiMesh stand; not the full 6808-tree park",
	}
	var path_out := "tmp/tree_sculpt/dense_stand_gate.json"
	var file := FileAccess.open(path_out, FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	print("DENSE_STAND_GATE ", JSON.stringify(report))
	quit(0 if median >= 45.0 else 1)

func _first_mesh(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node
	for child in node.get_children():
		var found := _first_mesh(child)
		if found:
			return found
	return null

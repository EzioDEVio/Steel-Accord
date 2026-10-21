# Steel Accord - in-engine art showcase (renders the Vanguard MBT on generated terrain and saves screenshots).
# Usage: godot --path game -- shot=rts|close out=/path.png
extends Node3D

const UNIT_SHADER := preload("res://shaders/unit.gdshader")
const TERRAIN_SHADER := preload("res://shaders/terrain.gdshader")
var grime_tex: NoiseTexture2D

func _noise(freq: float, seed_v: int, size := 512, normal := false) -> NoiseTexture2D:
	var n := FastNoiseLite.new()
	n.seed = seed_v
	n.frequency = freq
	n.fractal_octaves = 5
	var t := NoiseTexture2D.new()
	t.width = size; t.height = size; t.seamless = true; t.noise = n
	t.as_normal_map = normal; t.bump_strength = 6.0
	t.generate_mipmaps = true
	await t.changed
	return t

func _args() -> Dictionary:
	var d := {"shot": "rts", "out": "/tmp/sa_shot.png"}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		if kv.size() == 2: d[kv[0]] = kv[1]
	return d

func _ready() -> void:
	var args := _args()
	grime_tex = await _noise(0.02, 7)
	_environment()
	await _terrain()
	_place_tank(Vector3(0, 0, 0), 25.0, -15.0, Color(0.16, 0.42, 0.92))
	_place_tank(Vector3(-11, 0, 9), 35.0, 10.0, Color(0.16, 0.42, 0.92))
	_place_tank(Vector3(12, 0, 14), 15.0, 30.0, Color(0.16, 0.42, 0.92))
	_scatter_rocks()
	_camera(args.shot)
	for i in 8:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(args.out)
	print("SHOT ", args.out, " on ", RenderingServer.get_video_adapter_name())
	get_tree().quit()

func _environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.30, 0.45, 0.66)
	sky_mat.sky_horizon_color = Color(0.68, 0.72, 0.76)
	sky_mat.ground_horizon_color = Color(0.62, 0.64, 0.64)
	sky_mat.ground_bottom_color = Color(0.25, 0.25, 0.24)
	sky_mat.sun_angle_max = 20.0
	var sky := Sky.new(); sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY; env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.45
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.05
	env.ssao_enabled = true; env.ssao_radius = 1.6; env.ssao_intensity = 2.2
	env.glow_enabled = true; env.glow_intensity = 0.5; env.glow_bloom = 0.05
	env.fog_enabled = true; env.fog_density = 0.0035
	env.fog_light_color = Color(0.66, 0.70, 0.76); env.fog_aerial_perspective = 0.6
	env.adjustment_enabled = true; env.adjustment_contrast = 1.08; env.adjustment_saturation = 1.05
	var we := WorldEnvironment.new(); we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 140, 0)
	sun.light_color = Color(1.0, 0.94, 0.84); sun.light_energy = 2.1
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 160.0
	sun.directional_shadow_blend_splits = true
	sun.light_angular_distance = 0.6
	add_child(sun)

func _terrain() -> void:
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(420, 420)
	mesh.subdivide_width = 280; mesh.subdivide_depth = 280
	var mat := ShaderMaterial.new(); mat.shader = TERRAIN_SHADER
	mat.set_shader_parameter("n_macro", await _noise(0.012, 3))
	mat.set_shader_parameter("n_detail", await _noise(0.035, 11))
	mat.set_shader_parameter("n_normal", await _noise(0.06, 19, 512, true))
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.material_override = mat
	mi.extra_cull_margin = 20.0
	add_child(mi)

func _unit_material(src: Material, ao: Texture2D, team: Color) -> ShaderMaterial:
	var m := ShaderMaterial.new(); m.shader = UNIT_SHADER
	# Steel Accord unit palette (sRGB), keyed by the material names authored in Blender
	var pal := {
		"SA_Paint": [Color(0.30, 0.32, 0.20), 0.62, 0.0],
		"SA_Metal": [Color(0.13, 0.13, 0.12), 0.42, 0.75],
		"SA_Rubber": [Color(0.06, 0.06, 0.06), 0.92, 0.0],
		"SA_Glass": [Color(0.03, 0.07, 0.08), 0.08, 0.2],
		"SA_Team": [Color(0.8, 0.8, 0.8), 0.45, 0.0],
	}
	var e: Array = pal.get(src.resource_name, pal["SA_Paint"])
	m.set_shader_parameter("base_color", Vector3(e[0].r, e[0].g, e[0].b))
	m.set_shader_parameter("roughness_v", e[1])
	m.set_shader_parameter("metallic_v", e[2])
	m.set_shader_parameter("is_paint", src.resource_name == "SA_Paint")
	if src.resource_name == "SA_Glass":
		m.set_shader_parameter("emission_c", Vector3(0.25, 0.9, 1.1))
	m.set_shader_parameter("is_team", src.resource_name == "SA_Team")
	m.set_shader_parameter("team_color", Vector3(team.r, team.g, team.b))
	m.set_shader_parameter("ao_tex", ao)
	m.set_shader_parameter("grime", grime_tex)
	return m

func _apply_materials(n: Node, team: Color) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		var ao_path := "res://assets/units/vanguard_%s_ao.png" % mi.name.to_lower()
		var ao: Texture2D = load(ao_path) if ResourceLoader.exists(ao_path) else null
		for i in mi.mesh.get_surface_count():
			mi.set_surface_override_material(i, _unit_material(mi.mesh.surface_get_material(i), ao, team))
	for c in n.get_children():
		_apply_materials(c, team)

func _place_tank(pos: Vector3, heading: float, turret_yaw: float, team: Color) -> void:
	var t: Node3D = load("res://assets/units/vanguard.glb").instantiate()
	add_child(t)
	t.position = pos
	t.rotation_degrees.y = heading
	_apply_materials(t, team)
	var tur := t.find_child("Turret", true, false) as Node3D
	if tur: tur.rotation_degrees.y += turret_yaw

func _scatter_rocks() -> void:
	var src: Node3D = load("res://assets/props/rocks.glb").instantiate()
	var meshes: Array[MeshInstance3D] = []
	for c in src.get_children():
		if c is MeshInstance3D: meshes.append(c)
	var rng := RandomNumberGenerator.new(); rng.seed = 42
	for i in 46:
		var p := Vector3(rng.randf_range(-60, 60), -0.2, rng.randf_range(-60, 40))
		if abs(p.x) < 9.0 or p.length() < 26.0: continue
		var r := MeshInstance3D.new()
		r.mesh = meshes[i % meshes.size()].mesh
		var s := rng.randf_range(0.5, 2.0)
		r.scale = Vector3(s, s, s); r.position = p
		r.rotation.y = rng.randf() * TAU
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.62, 0.60, 0.55).darkened(rng.randf() * 0.2); m.roughness = 0.9
		m.albedo_texture = grime_tex; m.uv1_triplanar = true; m.uv1_scale = Vector3(0.4, 0.4, 0.4)
		r.material_override = m
		add_child(r)

func _camera(shot: String) -> void:
	var cam := Camera3D.new()
	add_child(cam)
	if shot == "close":
		cam.fov = 38.0
		cam.position = Vector3(13.5, 5.2, -12.0)
		cam.look_at(Vector3(1.0, 1.4, 0.0))
	else:
		cam.fov = 30.0
		cam.position = Vector3(20, 30, -26)
		cam.look_at(Vector3(0, 0, 5))
	cam.current = true

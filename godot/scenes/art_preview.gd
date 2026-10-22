# Steel Accord - single-asset art preview harness (technical art verification).
# Loads one glb, applies the unit shader the same way showcase.gd does, renders one screenshot.
# Usage: godot --path godot res://scenes/art_preview.tscn -- model=res://assets/units/kite.glb out=/path.png
#        view=rts|close|top [yaw=deg] [pitch=deg] [zoom=f] [focus=x,y,z] [pose=walk] [ref=0|1] [dust=on|off]
# dust=off is a preview-only approximation of "no dust" (sets dust_color to the base colour); the engine
# shader has no dust-amount uniform yet, and its dust term keys off mesh-local height (see report).
extends Node3D

const UNIT_SHADER := preload("res://shaders/unit.gdshader")
const TERRAIN_SHADER := preload("res://shaders/terrain.gdshader")
const SKY_SHADER := preload("res://shaders/sky.gdshader")
const TEAM := Color(0.12, 0.30, 0.72)
var dust_off := false


func _noise(freq: float, seed_v: int, size := 512, normal := false, oct := 5) -> NoiseTexture2D:
	var n := FastNoiseLite.new()
	n.seed = seed_v; n.frequency = freq; n.fractal_octaves = oct
	var t := NoiseTexture2D.new()
	t.width = size; t.height = size; t.seamless = true; t.noise = n
	t.as_normal_map = normal; t.bump_strength = 4.0; t.generate_mipmaps = true
	await t.changed
	return t


func _args() -> Dictionary:
	var d := {"model": "res://assets/units/vanguard.glb", "out": "/tmp/sa_preview.png", "view": "close",
		"yaw": "35", "pose": "", "ref": "1", "pitch": "", "zoom": "1", "focus": "", "dust": "on"}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		if kv.size() == 2: d[kv[0]] = kv[1]
	return d


func _ready() -> void:
	var args := _args()
	await _environment()
	await _terrain()
	var model: Node3D = load(args.model).instantiate()
	add_child(model)
	dust_off = args.dust == "off"
	UnitArt.apply(model, args.model.get_basename() + "_", TEAM, 0)
	if args.pose == "walk":
		_pose_walk(model)
	elif args.pose == "spin":
		# pivot test for rotorcraft: rotors about their hub axes, chin gun traversed + elevated
		_rot(model, "MainRotor", Vector3(0, 30, 0))
		_rot(model, "TailRotor", Vector3(45, 0, 0))
		_rot(model, "Cannon", Vector3(0, 35, 0))
	var aabb := _aabb(model, Transform3D.IDENTITY)
	print("AABB ", aabb.position, " size ", aabb.size)
	if args.view == "rts" and args.ref == "1":
		# scale reference: the Vanguard MBT parked beside the asset
		var ref: Node3D = load("res://assets/units/vanguard.glb").instantiate()
		add_child(ref)
		ref.position = Vector3(aabb.end.x + 6.0, 0, aabb.get_center().z)
		UnitArt.apply(ref, "res://assets/units/vanguard_", TEAM, 1)
	_camera(args, aabb)
	for i in 10:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(args.out)
	print("SHOT ", args.out, " on ", RenderingServer.get_video_adapter_name())
	get_tree().quit()


func _environment() -> void:
	var sky_mat := ShaderMaterial.new(); sky_mat.shader = SKY_SHADER
	sky_mat.set_shader_parameter("cloud_a", await _noise(0.006, 21, 512, false, 6))
	sky_mat.set_shader_parameter("cloud_b", await _noise(0.02, 22, 512, false, 5))
	var sky := Sky.new(); sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY; env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.55
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.ssao_enabled = true; env.ssao_radius = 1.2; env.ssao_intensity = 2.5; env.ssao_power = 1.6
	env.glow_enabled = true; env.glow_intensity = 0.35; env.glow_hdr_threshold = 1.4
	env.fog_enabled = true; env.fog_density = 0.0016; env.fog_sky_affect = 0.0
	env.fog_light_color = Color(0.62, 0.69, 0.77); env.fog_aerial_perspective = 0.75
	env.adjustment_enabled = true; env.adjustment_contrast = 1.1; env.adjustment_saturation = 1.08
	var we := WorldEnvironment.new(); we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-36, 58, 0)
	sun.light_color = Color(1.0, 0.93, 0.82); sun.light_energy = 2.6
	sun.shadow_enabled = true
	sun.shadow_bias = 0.03; sun.shadow_normal_bias = 0.6
	sun.directional_shadow_max_distance = 140.0
	sun.directional_shadow_blend_splits = true
	sun.light_angular_distance = 0.5
	add_child(sun)


func _terrain() -> void:
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(600, 600)
	mesh.subdivide_width = 300; mesh.subdivide_depth = 300
	var mat := ShaderMaterial.new(); mat.shader = TERRAIN_SHADER
	mat.set_shader_parameter("n_macro", await _noise(0.01, 3))
	mat.set_shader_parameter("n_detail", await _noise(0.03, 11))
	mat.set_shader_parameter("n_normal", await _noise(0.05, 19, 512, true, 4))
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.material_override = mat
	mi.extra_cull_margin = 30.0
	add_child(mi)


# ------------------------------------------------------------------ materials (copied from showcase.gd, palette extended)
func _unit_material(src: Material, ao: Texture2D, idx: int) -> ShaderMaterial:
	# palette (sRGB): base colour, roughness, metallic, kind
	var pal := {
		"SA_Paint": [Color(0.26, 0.30, 0.17), 0.62, 0.0, 1],
		"SA_Metal": [Color(0.14, 0.14, 0.13), 0.5, 0.7, 0],
		"SA_Rubber": [Color(0.07, 0.07, 0.07), 0.92, 0.0, 3],
		"SA_Track": [Color(0.20, 0.18, 0.16), 0.6, 0.6, 3],
		"SA_Glass": [Color(0.04, 0.06, 0.07), 0.05, 0.3, 5],
		"SA_Team": [TEAM, 0.7, 0.0, 2],
		"SA_Decal": [Color(0.78, 0.76, 0.68), 0.7, 0.0, 4],
		"SA_Canvas": [Color(0.36, 0.33, 0.23), 0.95, 0.0, 4],
		# new names introduced by the technical-art pass (engine palette must add these too)
		"SA_Skin": [Color(0.55, 0.40, 0.31), 0.7, 0.0, 4],
		"SA_Concrete": [Color(0.40, 0.39, 0.36), 0.9, 0.0, 4],
	}
	var e: Array = pal.get(src.resource_name, pal["SA_Paint"])
	var m := ShaderMaterial.new(); m.shader = UNIT_SHADER
	m.set_shader_parameter("base_color", e[0])
	m.set_shader_parameter("roughness_v", e[1])
	m.set_shader_parameter("metallic_v", e[2])
	m.set_shader_parameter("kind", e[3])
	m.set_shader_parameter("team_color", TEAM)
	m.set_shader_parameter("camo_offset", Vector3(idx * 13.7, idx * 5.1, idx * 9.3))
	m.set_shader_parameter("ao_tex", ao)
	if dust_off:
		m.set_shader_parameter("dust_color", Color(0.26, 0.30, 0.17) if e[3] == 1 else (TEAM * 0.7 if e[3] == 2 else e[0]))
	return m


func _apply_materials(n: Node, idx: int, model_path: String) -> void:
	# AO convention: <dir>/<model>_<meshnode lowercase>_ao.png next to the glb
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		var base := model_path.get_base_dir() + "/" + model_path.get_file().get_basename()
		var ao_path := "%s_%s_ao.png" % [base, mi.name.to_lower()]
		var ao: Texture2D = load(ao_path) if ResourceLoader.exists(ao_path) else null
		for i in mi.mesh.get_surface_count():
			mi.set_surface_override_material(i, _unit_material(mi.mesh.surface_get_material(i), ao, idx))
	for c in n.get_children():
		_apply_materials(c, idx, model_path)


# ------------------------------------------------------------------ test pose (proves joint pivots)
func _rot(model: Node, node_name: String, deg: Vector3) -> void:
	var n := model.find_child(node_name, true, false) as Node3D
	if n == null:
		push_warning("pose: node not found " + node_name); return
	n.rotation_degrees += deg


func _pose_walk(model: Node3D) -> void:
	_rot(model, "LegUpper_L", Vector3(25, 0, 0))
	_rot(model, "LegLower_L", Vector3(-20, 0, 0))
	_rot(model, "LegUpper_R", Vector3(-25, 0, 0))
	_rot(model, "LegLower_R", Vector3(-35, 0, 0))
	_rot(model, "ArmUpper_L", Vector3(45, 0, 0))
	_rot(model, "ArmLower_L", Vector3(30, 0, 0))
	_rot(model, "Torso", Vector3(4, 8, 0))
	_rot(model, "Head", Vector3(0, -20, 0))


# ------------------------------------------------------------------ framing
func _aabb(n: Node, xf: Transform3D) -> AABB:
	var out := AABB()
	var first := true
	var t := xf
	if n is Node3D: t = xf * (n as Node3D).transform
	if n is MeshInstance3D:
		out = t * (n as MeshInstance3D).mesh.get_aabb(); first = false
	for c in n.get_children():
		var b := _aabb(c, t)
		if b.size == Vector3.ZERO: continue
		out = b if first else out.merge(b); first = false
	return out


func _camera(args: Dictionary, aabb: AABB) -> void:
	var cam := Camera3D.new()
	add_child(cam)
	var c := aabb.get_center()
	var r := aabb.size.length() * 0.5 / float(args.zoom)
	if args.focus != "":
		var f: PackedStringArray = args.focus.split(",")
		c = Vector3(float(f[0]), float(f[1]), float(f[2]))
	var yaw := deg_to_rad(float(args.yaw))
	if args.view == "close":
		cam.fov = 30.0
		var pitch := deg_to_rad(float(args.pitch) if args.pitch != "" else 14.0)
		var dist := r / sin(deg_to_rad(cam.fov * 0.5)) * 1.05
		# yaw 0 = looking at the model's front (model forward is -Z)
		var dir := Vector3(sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
		cam.position = c + dir * dist
		cam.look_at(c)
	elif args.view == "top":
		cam.fov = 30.0
		cam.position = c + Vector3(0.01, r / tan(deg_to_rad(15.0)) * 1.1, 0)
		cam.look_at(c)
	else:
		# RTS camera: ~35 m away, looking down ~50 degrees
		cam.fov = 36.0
		var pitch := deg_to_rad(50.0)
		var dir := Vector3(sin(yaw) * cos(pitch), sin(pitch), -cos(yaw) * cos(pitch))
		var tgt := c + Vector3(3.0, 0, 0)
		cam.position = tgt + dir * 35.0
		cam.look_at(tgt)
	cam.current = true

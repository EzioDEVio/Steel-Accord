# Steel Accord - in-engine art showcase v2.
# Renders a Vanguard MBT column on a dirt road with grass, bushes, rocks and a roadside checkpoint.
# Usage: godot --path godot -- shot=rts|close out=/path.png
extends Node3D

const UNIT_SHADER := preload("res://shaders/unit.gdshader")
const TERRAIN_SHADER := preload("res://shaders/terrain.gdshader")
const GRASS_SHADER := preload("res://shaders/grass.gdshader")
const ROCK_SHADER := preload("res://shaders/rock.gdshader")
const SKY_SHADER := preload("res://shaders/sky.gdshader")
const LEAF_SHADER := preload("res://shaders/leaf.gdshader")
const TEAM := Color(0.12, 0.30, 0.72)

var props := {}
var rng := RandomNumberGenerator.new()
var tank_spots: Array[Vector3] = []


static func road_center(z: float) -> float:
	return -sin(z * 0.035) * 9.0


func _noise(freq: float, seed_v: int, size := 512, normal := false, oct := 5) -> NoiseTexture2D:
	var n := FastNoiseLite.new()
	n.seed = seed_v; n.frequency = freq; n.fractal_octaves = oct
	var t := NoiseTexture2D.new()
	t.width = size; t.height = size; t.seamless = true; t.noise = n
	t.as_normal_map = normal; t.bump_strength = 4.0; t.generate_mipmaps = true
	await t.changed
	return t


func _args() -> Dictionary:
	var d := {"shot": "rts", "out": "/tmp/sa_shot.png"}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		if kv.size() == 2: d[kv[0]] = kv[1]
	return d


func _ready() -> void:
	rng.seed = 7
	var args := _args()
	await _environment()
	await _terrain()
	_load_props()
	for i in 3:
		var z := -i * 17.0
		var p := Vector3(road_center(z) + (0.4 if i == 1 else -0.3), 0.0, z)
		tank_spots.append(p)
		_place_tank(p, i)
	_grass()
	_scatter()
	_checkpoint()
	_camera(args.shot)
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
	mesh.size = Vector2(1200, 1200)
	mesh.subdivide_width = 500; mesh.subdivide_depth = 500
	var mat := ShaderMaterial.new(); mat.shader = TERRAIN_SHADER
	mat.set_shader_parameter("n_macro", await _noise(0.01, 3))
	mat.set_shader_parameter("n_detail", await _noise(0.03, 11))
	mat.set_shader_parameter("n_normal", await _noise(0.05, 19, 512, true, 4))
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.material_override = mat
	mi.extra_cull_margin = 30.0
	add_child(mi)


func _load_props() -> void:
	var src: Node3D = load("res://assets/props/props.glb").instantiate()
	for c in src.get_children():
		if c is MeshInstance3D:
			props[c.name] = (c as MeshInstance3D).mesh


# ------------------------------------------------------------------ units
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
	return m


func _apply_materials(n: Node, idx: int) -> void:
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		var ao_path := "res://assets/units/vanguard_%s_ao.png" % mi.name.to_lower()
		var ao: Texture2D = load(ao_path) if ResourceLoader.exists(ao_path) else null
		for i in mi.mesh.get_surface_count():
			mi.set_surface_override_material(i, _unit_material(mi.mesh.surface_get_material(i), ao, idx))
	for c in n.get_children():
		_apply_materials(c, idx)


func _place_tank(pos: Vector3, idx: int) -> void:
	var t: Node3D = load("res://assets/units/vanguard.glb").instantiate()
	add_child(t)
	t.position = pos
	# face down the road (towards +Z), following the road's tangent
	var dxdz := -cos(pos.z * 0.035) * 9.0 * 0.035
	t.rotation.y = atan2(-dxdz, -1.0)
	_apply_materials(t, idx)
	var tur := t.find_child("Turret", true, false) as Node3D
	if tur: tur.rotation_degrees.y = [12.0, -20.0, 25.0][idx]
	# contact shadow: soft dark decal under the hull grounds the vehicle
	var g := GradientTexture2D.new()
	g.fill = GradientTexture2D.FILL_RADIAL; g.fill_from = Vector2(0.5, 0.5); g.fill_to = Vector2(1.0, 0.5)
	var gr := Gradient.new(); gr.set_color(0, Color(0, 0, 0, 0.75)); gr.set_color(1, Color(0, 0, 0, 0))
	g.gradient = gr; g.width = 128; g.height = 128
	var d := Decal.new()
	d.texture_albedo = g; d.size = Vector3(4.6, 2.0, 8.6); d.position = Vector3(0, 0.3, 0)
	d.albedo_mix = 1.0; d.modulate = Color(1, 1, 1, 0.8)
	t.add_child(d)


func _near_tank(p: Vector3, r: float) -> bool:
	for s in tank_spots:
		if Vector2(p.x - s.x, p.z - s.z).length() < r: return true
	return false


# ------------------------------------------------------------------ vegetation and dressing
func _tuft_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for k in 3:
		var a := k * PI / 3.0
		var dx := Vector3(cos(a), 0, sin(a)) * 0.32
		var v := [-dx, dx, dx + Vector3(0, 0.38, 0), -dx + Vector3(0, 0.38, 0)]
		var uv := [Vector2(0, 1), Vector2(1, 1), Vector2(1, 0), Vector2(0, 0)]
		for i in [0, 1, 2, 0, 2, 3]:
			st.set_normal(Vector3.UP); st.set_uv(uv[i]); st.add_vertex(v[i])
	return st.commit()


func _grass() -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D; mm.use_colors = true
	mm.mesh = _tuft_mesh()
	var xs: Array[Transform3D] = []
	var cs: Array[Color] = []
	for i in 90000:
		var p := Vector3(rng.randf_range(-70, 80), 0, rng.randf_range(-90, 45))
		var dist := absf(p.x - road_center(p.z))
		if dist < 3.2 + rng.randf() * 1.5: continue
		if dist < 6.0 and rng.randf() < 0.6: continue
		if _near_tank(p, 4.2): continue
		var s := rng.randf_range(0.6, 1.3)
		if rng.randf() < 0.35: continue
		var b := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s * rng.randf_range(0.6, 1.2), s))
		xs.append(Transform3D(b, p))
		var dry := clampf(0.5 + 0.5 * sin(p.x * 0.05 + p.z * 0.03) + rng.randf_range(-0.3, 0.3), 0, 1)
		cs.append(Color(1.0, 1.0, 1.0).lerp(Color(1.35, 1.2, 0.85), dry * 0.6) * rng.randf_range(0.8, 1.1))
	mm.instance_count = xs.size()
	for i in xs.size():
		mm.set_instance_transform(i, xs[i]); mm.set_instance_color(i, cs[i])
	var mmi := MultiMeshInstance3D.new(); mmi.multimesh = mm
	var m := ShaderMaterial.new(); m.shader = GRASS_SHADER
	mmi.material_override = m
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)


func _scatter() -> void:
	var rock_mat := ShaderMaterial.new(); rock_mat.shader = ROCK_SHADER
	for i in 60:
		var p := Vector3(rng.randf_range(-90, 100), 0, rng.randf_range(-120, 50))
		if absf(p.x - road_center(p.z)) < 6.0 or _near_tank(p, 8.0): continue
		var r := MeshInstance3D.new()
		r.mesh = props["Rock%d" % (i % 6)]
		var s := rng.randf_range(0.4, 1.3) * (1.5 if rng.randf() < 0.15 else 1.0)
		r.scale = Vector3(s, s, s); r.rotation.y = rng.randf() * TAU
		r.position = p - Vector3(0, 0.3 * s, 0)
		r.material_override = rock_mat
		add_child(r)
	for i in 140:
		var p := Vector3(rng.randf_range(-100, 110), 0, rng.randf_range(-140, 50))
		if absf(p.x - road_center(p.z)) < 7.0 or _near_tank(p, 9.0): continue
		var b := MeshInstance3D.new()
		b.mesh = props["Bush%d" % (i % 4)]
		var s := rng.randf_range(0.7, 1.7)
		b.scale = Vector3(s, s * rng.randf_range(0.8, 1.2), s); b.rotation.y = rng.randf() * TAU
		b.position = p
		if Vector2(p.x - 6.0, p.z - 13.5).length() < 14.0: continue
		var m := ShaderMaterial.new(); m.shader = LEAF_SHADER
		m.set_shader_parameter("tint", Color(0.85, 0.9, 0.8).lerp(Color(1.15, 1.1, 0.85), rng.randf()))
		b.material_override = m
		add_child(b)
	# telegraph line along the east verge
	var pole_mat := StandardMaterial3D.new(); pole_mat.albedo_color = Color(0.30, 0.22, 0.15); pole_mat.roughness = 0.9
	for k in 8:
		var z := 60.0 - k * 38.0
		var pole := MeshInstance3D.new(); pole.mesh = props["Pole"]
		pole.position = Vector3(road_center(z) + 8.0, 0, z)
		pole.rotation.z = deg_to_rad(rng.randf_range(-2, 2))
		pole.material_override = pole_mat
		add_child(pole)


func _checkpoint() -> void:
	var con := StandardMaterial3D.new(); con.albedo_color = Color(0.46, 0.45, 0.42); con.roughness = 0.9
	var drum := StandardMaterial3D.new(); drum.albedo_color = Color(0.22, 0.30, 0.16); drum.roughness = 0.55
	var z0 := -44.0
	for k in 4:
		var b := MeshInstance3D.new(); b.mesh = props["Barrier"]
		var z := z0 - k * 3.2
		b.position = Vector3(road_center(z) + 4.6 + (0.4 if k % 2 else 0.0), 0, z)
		b.rotation.y = deg_to_rad(rng.randf_range(-6, 6))
		b.material_override = con
		add_child(b)
	for k in 5:
		var d := MeshInstance3D.new(); d.mesh = props["Drum"]
		d.position = Vector3(road_center(z0) - 5.0 + (k % 3) * 0.62, 0, z0 - 1.5 - (k / 3) * 0.62)
		d.material_override = drum
		add_child(d)


func _camera(shot: String) -> void:
	var cam := Camera3D.new()
	add_child(cam)
	if shot == "close":
		cam.fov = 34.0
		cam.position = Vector3(6.0, 2.6, 13.5)
		cam.look_at(Vector3(1.0, 1.5, -3.0))
	else:
		cam.fov = 36.0
		cam.position = Vector3(24, 36, 30)
		cam.look_at(Vector3(4, 0, -14))
	cam.current = true

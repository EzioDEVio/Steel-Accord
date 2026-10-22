# Steel Accord - shared world-building helpers (environment, terrain, grass, props).
class_name World

const TERRAIN_SHADER := preload("res://shaders/terrain.gdshader")
const GRASS_SHADER := preload("res://shaders/grass.gdshader")
const ROCK_SHADER := preload("res://shaders/rock.gdshader")
const LEAF_SHADER := preload("res://shaders/leaf.gdshader")
const SKY_SHADER := preload("res://shaders/sky.gdshader")


static func noise_tex(freq: float, seed_v: int, size := 512, normal := false, oct := 5) -> NoiseTexture2D:
	var n := FastNoiseLite.new()
	n.seed = seed_v; n.frequency = freq; n.fractal_octaves = oct
	var t := NoiseTexture2D.new()
	t.width = size; t.height = size; t.seamless = true; t.noise = n
	t.as_normal_map = normal; t.bump_strength = 4.0; t.generate_mipmaps = true
	await t.changed
	return t


static func environment(parent: Node) -> DirectionalLight3D:
	var sky_mat := ShaderMaterial.new(); sky_mat.shader = SKY_SHADER
	sky_mat.set_shader_parameter("cloud_a", await noise_tex(0.006, 21, 512, false, 6))
	sky_mat.set_shader_parameter("cloud_b", await noise_tex(0.02, 22, 512, false, 5))
	var sky := Sky.new(); sky.sky_material = sky_mat
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY; env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.55
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.ssao_enabled = true; env.ssao_radius = 1.2; env.ssao_intensity = 2.5; env.ssao_power = 1.6
	env.glow_enabled = true; env.glow_intensity = 0.4; env.glow_hdr_threshold = 1.2
	env.fog_enabled = true; env.fog_density = 0.0012; env.fog_sky_affect = 0.0
	env.fog_light_color = Color(0.62, 0.69, 0.77); env.fog_aerial_perspective = 0.75
	env.adjustment_enabled = true; env.adjustment_contrast = 1.1; env.adjustment_saturation = 1.08
	var we := WorldEnvironment.new(); we.environment = env
	parent.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 35, 0)
	sun.light_color = Color(1.0, 0.94, 0.84); sun.light_energy = 2.4
	sun.shadow_enabled = true
	sun.shadow_bias = 0.03; sun.shadow_normal_bias = 0.6
	sun.directional_shadow_max_distance = 220.0
	sun.directional_shadow_blend_splits = true
	parent.add_child(sun)
	return sun


static func terrain(parent: Node, flat_radius: float, road_on: float) -> MeshInstance3D:
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(1400, 1400)
	mesh.subdivide_width = 500; mesh.subdivide_depth = 500
	var mat := ShaderMaterial.new(); mat.shader = TERRAIN_SHADER
	mat.set_shader_parameter("n_macro", await noise_tex(0.01, 3))
	mat.set_shader_parameter("n_detail", await noise_tex(0.03, 11))
	mat.set_shader_parameter("n_normal", await noise_tex(0.05, 19, 512, true, 4))
	mat.set_shader_parameter("flat_radius", flat_radius)
	mat.set_shader_parameter("flat_center", Vector2.ZERO)
	mat.set_shader_parameter("road_on", road_on)
	var mi := MeshInstance3D.new(); mi.mesh = mesh; mi.material_override = mat
	mi.extra_cull_margin = 40.0
	parent.add_child(mi)
	return mi


static func props() -> Dictionary:
	var d := {}
	var src: Node3D = load("res://assets/props/props.glb").instantiate()
	for c in src.get_children():
		if c is MeshInstance3D: d[c.name] = (c as MeshInstance3D).mesh
	src.free()
	return d


static func tuft_mesh() -> ArrayMesh:
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


## Scatter grass tufts in `area`, skipping points for which `blocked.call(p)` is true.
static func grass(parent: Node, area: Rect2, tries: int, rng: RandomNumberGenerator, blocked: Callable) -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D; mm.use_colors = true
	mm.mesh = tuft_mesh()
	var xs: Array[Transform3D] = []
	var cs: Array[Color] = []
	for i in tries:
		var p := Vector3(rng.randf_range(area.position.x, area.end.x), 0, rng.randf_range(area.position.y, area.end.y))
		if rng.randf() < 0.3 or blocked.call(p): continue
		var s := rng.randf_range(0.6, 1.3)
		xs.append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s * rng.randf_range(0.6, 1.2), s)), p))
		var dry := clampf(0.5 + 0.5 * sin(p.x * 0.05 + p.z * 0.03) + rng.randf_range(-0.3, 0.3), 0, 1)
		cs.append(Color(1, 1, 1).lerp(Color(1.35, 1.2, 0.85), dry * 0.6) * rng.randf_range(0.8, 1.1))
	mm.instance_count = xs.size()
	for i in xs.size():
		mm.set_instance_transform(i, xs[i]); mm.set_instance_color(i, cs[i])
	var mmi := MultiMeshInstance3D.new(); mmi.multimesh = mm
	var m := ShaderMaterial.new(); m.shader = GRASS_SHADER
	mmi.material_override = m
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mmi)


static func rock(parent: Node, mesh: Mesh, pos: Vector3, s: float, yaw: float) -> MeshInstance3D:
	var r := MeshInstance3D.new()
	r.mesh = mesh
	r.scale = Vector3(s, s, s); r.rotation.y = yaw
	r.position = pos - Vector3(0, 0.3 * s, 0)
	var m := ShaderMaterial.new(); m.shader = ROCK_SHADER
	r.material_override = m
	parent.add_child(r)
	return r


static func bush(parent: Node, mesh: Mesh, pos: Vector3, s: float, yaw: float, tint: Color) -> void:
	var b := MeshInstance3D.new()
	b.mesh = mesh
	b.scale = Vector3(s, s, s); b.rotation.y = yaw; b.position = pos
	var m := ShaderMaterial.new(); m.shader = LEAF_SHADER
	m.set_shader_parameter("tint", tint)
	b.material_override = m
	parent.add_child(b)

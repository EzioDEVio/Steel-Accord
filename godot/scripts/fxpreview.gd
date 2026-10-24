# Steel Accord - FX look-development scene (not part of the game). Lightweight: flat ground, sun, one tank model,
# no battle simulation, so effects can be rendered and tuned quickly under software rendering.
#   godot --path godot res://scenes/fxpreview.tscn -- case=shell out=/dir [gfx=High]
# Writes <case>.png: a 2 x 2 sheet of the effect at four moments (960 x 540 each).
extends Node3D

var args := {}
var cam: Camera3D
var tank: Node3D


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		args[kv[0]] = kv[1] if kv.size() > 1 else ""
	if args.has("gfx"): Game.settings["graphics"] = str(args.gfx)
	get_window().size = Vector2i(960, 540)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = Color(0.55, 0.65, 0.78)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; env.ambient_light_color = Color(0.6, 0.66, 0.75); env.ambient_light_energy = 0.9
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.glow_enabled = true; env.glow_intensity = 0.4; env.glow_hdr_threshold = 1.2
	env.adjustment_enabled = true; env.adjustment_contrast = 1.1; env.adjustment_saturation = 1.08
	var we := WorldEnvironment.new(); we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 35, 0); sun.light_color = Color(1.0, 0.94, 0.84); sun.light_energy = 2.4
	sun.shadow_enabled = true
	add_child(sun)
	var g := MeshInstance3D.new()
	var pm := PlaneMesh.new(); pm.size = Vector2(400, 400)
	var gm := StandardMaterial3D.new(); gm.albedo_color = Color(0.42, 0.4, 0.27); gm.roughness = 1.0
	gm.albedo_texture = FX.tex("concrete_detail"); gm.uv1_triplanar = true; gm.uv1_scale = Vector3(0.05, 0.05, 0.05)
	pm.material = gm
	g.mesh = pm
	add_child(g)
	tank = (load("res://assets/units/vanguard.glb") as PackedScene).instantiate()
	add_child(tank)
	tank.position = Vector3(-9, 0, 4)
	tank.scale = Vector3.ONE * float(UnitDefs.SCALE.vehicle)
	cam = Camera3D.new()
	cam.fov = 40.0
	add_child(cam)
	_view(float(args.get("zoom", "55")))
	_run.call_deferred()


func _view(zoom: float, at := Vector3.ZERO) -> void:
	var p := deg_to_rad(52.0)
	cam.position = at + Vector3(0, sin(p) * zoom, cos(p) * zoom)
	cam.rotation = Vector3(-p, 0, 0)


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _grab() -> Image:
	await RenderingServer.frame_post_draw
	return get_viewport().get_texture().get_image()


func _run() -> void:
	await _wait(0.5)
	var case := str(args.get("case", "shell"))
	var times: Array = [0.15, 0.6, 1.5, 3.0]
	var imgs: Array = []
	var t0 := 0.0
	match case:
		"shell": FX.impact_kind(self, Vector3(0, 0.2, 0), "shell", "ground")
		"bomb": _view(80.0); FX.explosion(self, Vector3(0, 0.2, 0), 1.0, "huge"); times = [0.2, 0.8, 2.0, 4.5]
		"large": _view(65.0); FX.explosion(self, Vector3(0, 0.2, 0), 1.0, "large"); times = [0.15, 0.6, 1.5, 3.5]
		"small": _view(35.0); FX.explosion(self, Vector3(0, 0.2, 0), 1.0, "small"); times = [0.1, 0.4, 1.0, 2.0]
		"muzzle":
			_view(35.0)
			times = [0.05, 0.3, 0.8, 1.6]
			FX.muzzle(self, Vector3(-6, 2.4, 6), Vector3(0, 0, -1), "tank")
			FX.muzzle(self, Vector3(6, 1.2, 6), Vector3(0, 0, -1), "rocket")
			for k in 6: FX.impact_kind(self, Vector3(-8 + k * 3, 0.2, -6), "bullet", "ground")
			FX.impact_kind(self, Vector3(8, 1.0, -8), "cannon", "armour")
		"trail":
			_view(70.0)
			times = [0.6, 1.2, 1.8, 3.5]
			var m := FX.missile_node(true)
			add_child(m)
			m.position = Vector3(-40, 3, 25)
			m.look_at(Vector3(30, 1, -25))
			var tw := m.create_tween()
			tw.tween_property(m, "position", Vector3(30, 1, -25), 1.6)
			tw.tween_callback(func():
				FX.detach_trails(m)
				m.queue_free()
				FX.impact_kind(self, Vector3(30, 0.2, -25), "rocket", "armour"))
		"wreck":
			_view(40.0)
			FX.explosion(self, tank.position + Vector3(0, 1, 0), 0.85, "large")
			FX.wreck_fire(tank, 1.0, 50.0)
			times = [0.5, 3.0, 8.0, 30.0]
		"dbg":
			_view(40.0)
			times = [0.3, 0.8, 1.5, 2.5]
			var ref := MeshInstance3D.new(); var sp := SphereMesh.new(); sp.radius = 2.0; sp.height = 4.0; ref.mesh = sp
			add_child(ref); ref.position = Vector3(0, 2, -8)
			for k in 4:
				var p := CPUParticles3D.new()
				var q := QuadMesh.new()
				q.material = FX.mat("softmix")
				q.size = Vector2.ONE * 4.0
				p.mesh = q
				p.local_coords = k < 2
				p.amount = 1; p.lifetime = 3.0; p.one_shot = true; p.explosiveness = 1.0
				p.scale_amount_min = [1.0, 2.0, 1.0, 2.0][k]; p.scale_amount_max = p.scale_amount_min
				p.initial_velocity_min = 0.0; p.initial_velocity_max = 0.0; p.gravity = Vector3.ZERO
				p.emitting = false
				add_child(p)
				p.position = Vector3(-15 + k * 10, 2, 4)
				p.restart(); p.emitting = true
		"ruin", "ruin_civ":
			var kind := "command_center" if case == "ruin" else "civ_apartment"
			var half: Vector2 = BuildingDefs.DEFS[kind].size * 0.5
			_view(85.0 if case == "ruin" else 65.0)
			tank.visible = false
			var root := Node3D.new()
			add_child(root)
			FX.ruin(self, root, kind, half, 14, 0.0)
			times = [1.0, 6.0, 20.0, 70.0]
	for t in times:
		await _wait(float(t) - t0)
		t0 = float(t)
		imgs.append(await _grab())
	var sheet := Image.create(1920, 1080, false, Image.FORMAT_RGBA8)
	for i in imgs.size():
		var im: Image = imgs[i]
		im.convert(Image.FORMAT_RGBA8)
		im.resize(960, 540)
		sheet.blit_rect(im, Rect2i(0, 0, 960, 540), Vector2i((i % 2) * 960, (i / 2) * 540))
	var out := str(args.get("out", "user://"))
	DirAccess.make_dir_recursive_absolute(out)
	sheet.save_png("%s/%s.png" % [out, case])
	printerr("PREVIEW %s/%s.png" % [out, case])
	get_tree().quit()

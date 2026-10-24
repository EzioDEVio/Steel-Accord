# Steel Accord - VFX evidence and benchmark driver (not part of gameplay). Uses only long-standing calls
# (battle.fire, FX.explosion, FX.impact, take_damage, add_civic) so the same driver captures "before" and "after".
#   godot --path godot -- army vfxshots out=/dir        close-up captures (render with a display, res=1920x1080)
#   godot --path godot -- army vfxbench secs=40 out=/dir   large battle: wall-clock frame time + sim tick (add prof)
extends Node

var battle: Node
var out := "user://test_output/vfx"
var args := {}
var frame_us: Array = []
var _last_us := 0


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		args[kv[0]] = kv[1] if kv.size() > 1 else ""
	out = str(args.get("out", out))
	if args.has("gfx"):
		Game.settings["graphics"] = str(args.gfx)
		Game.apply_graphics()
	DirAccess.make_dir_recursive_absolute(out)
	if args.has("res") and DisplayServer.get_name() != "headless":
		var r := str(args.res).split("x")
		get_window().size = Vector2i(int(r[0]), int(r[1]))
	_run()


func _process(_dt: float) -> void:
	var now := Time.get_ticks_usec()
	if _last_us > 0: frame_us.append(now - _last_us)
	_last_us = now


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _shot(tag: String) -> void:
	if DisplayServer.get_name() == "headless": return
	# software rendering is slow: frames are only drawn around a capture (the simulation keeps running)
	RenderingServer.render_loop_enabled = true
	await get_tree().process_frame
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	RenderingServer.render_loop_enabled = args.has("vfxbench")
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, tag])
	print("SHOT ", tag)


func _look(p: Vector3, zoom := 55.0, yaw := 0.0) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam.yaw = yaw; cam._apply()
	cam.focus(p)


func _spawn(kind: String, team: int, p: Vector3, yaw := 0.0) -> Unit:
	var u: Unit = battle._spawn(kind, team, p, yaw)
	u.order_stop()
	return u


func _structure(kind: String, team: int, p: Vector3) -> Building:
	var b := Building.new()
	battle.add_child(b)
	b.setup_structure(battle, kind, team, battle.new_uid(), battle.grounded(p), true)
	battle.units.append(b)
	battle.by_id[b.uid] = b
	return b


func _run() -> void:
	await _wait_sim(0.5)
	battle.ai = null
	battle.camera.edge_pan = false
	for u in battle.units: if u.team == 1: u.order_stop()
	if args.has("vfxbench"):
		await _bench()
	elif DisplayServer.get_name() != "headless":
		RenderingServer.render_loop_enabled = false
	else:
		await _shots()
	await get_tree().create_timer(0.5).timeout
	get_tree().quit()


# ------------------------------------------------------------------------------------------ evidence
func _shots() -> void:
	var tag := str(args.get("tag", "after"))
	# 1. tank shell: a tank fires at the ground; impact + 1.4 s later
	var A := Vector3(-150, 0, 40)
	var tank := _spawn("vanguard", 0, A + Vector3(0, 0, 34), 0.0)
	var red := _spawn("vanguard", 1, A + Vector3(-14, 0, -6), PI)
	await _wait_sim(0.3)
	_look(A + Vector3(-4, 0, 10), 52.0)
	var w: Dictionary = tank.def.weapons[0]
	battle.fire(tank, w, null, A)
	await _wait_sim(0.12)
	await _shot("%s_01_tank_fire" % tag)
	while not battle.shots.is_empty(): await get_tree().physics_frame
	await _wait_sim(0.15)
	await _shot("%s_02_tank_shell_impact" % tag)
	await _wait_sim(1.3)
	await _shot("%s_03_tank_shell_smoke" % tag)
	# 2. bomb: heavy explosion
	var B := Vector3(-60, 0, 40)
	_look(B + Vector3(0, 0, 6), 70.0)
	await _wait_sim(0.5)
	FX.explosion(battle, battle.grounded(B) + Vector3(0, 0.2, 0), 2.2)
	await _wait_sim(0.3)
	await _shot("%s_04_bomb_blast" % tag)
	await _wait_sim(1.8)
	await _shot("%s_05_bomb_smoke" % tag)
	# 3. rockets / missiles with smoke trails (AT rocket team and a TOW vehicle) at a tank 80 m away
	var C := Vector3(60, 0, 40)
	var tgt := _spawn("vanguard", 1, C + Vector3(0, 0, -40), PI)
	var at := _spawn("at4", 0, C + Vector3(-10, 0, 40), 0.0)
	var tow := _spawn("hmmwv_tow", 0, C + Vector3(12, 0, 44), 0.0)
	_look(C + Vector3(0, 0, 6), 75.0)
	await _wait_sim(0.4)
	battle.fire(at, at.def.weapons[0], tgt, tgt.position)
	battle.fire(tow, tow.def.weapons[0], tgt, tgt.position)
	var t0: float = battle.sim_time
	while battle.sim_time - t0 < 3.0:
		var far := false
		for s in battle.shots:
			if s.kind in ["missile", "rocket"] and s.left < 35.0: far = true
		if far: break
		await get_tree().physics_frame
	await _shot("%s_06_rocket_trail" % tag)
	await _wait_sim(0.6)
	await _shot("%s_07_rocket_hit" % tag)
	# 4. machine-gun tracers: three gunners and two .50 cal Humvees firing bursts at a target line
	var D := Vector3(150, 0, 40)
	var gun: Array = []
	for i in 3: gun.append(_spawn("m240_gunner", 0, D + Vector3(-12 + i * 6, 0, 30), 0.0))
	for i in 2: gun.append(_spawn("hmmwv_50cal", 0, D + Vector3(-18 + i * 36, 0, 34), 0.0))
	var line: Array = []
	for i in 3: line.append(_spawn("rifleman", 1, D + Vector3(-10 + i * 10, 0, -14), PI))
	_look(D + Vector3(0, 0, 10), 58.0)
	await _wait_sim(0.4)
	for k in 14:
		for g in gun:
			var tg: Unit = line[(k + gun.find(g)) % line.size()]
			if not tg.dead: battle.fire(g, g.def.weapons[0], tg, tg.position)
		await _wait_sim(0.07)
	await _shot("%s_08_mg_tracers" % tag)
	# 5. vehicle death and burning wreck
	_look(red.position + Vector3(0, 0, 4), 48.0)
	red.take_damage(red.hp + 50.0, null)
	await _wait_sim(0.25)
	await _shot("%s_09_vehicle_death" % tag)
	await _wait_sim(5.0)
	await _shot("%s_10_burning_wreck" % tag)
	# 6. command centre destroyed: collapse, then the ruin
	var E := Vector3(-150, 0, -90)
	var cc := _structure("command_center", 0, E)
	_look(E + Vector3(0, 0, 8), 85.0)
	await _wait_sim(1.0)
	await _shot("%s_11_cc_standing" % tag)
	cc.take_damage(cc.hp + 100.0, null)
	await _wait_sim(0.9)
	await _shot("%s_12_cc_collapse" % tag)
	await _wait_sim(9.0)
	await _shot("%s_13_cc_ruin" % tag)
	# 7. civic apartment block destroyed
	var F := Vector3(-40, 0, -90)
	var civ: Building = battle.add_civic("civ_apartment", F, false)
	if civ:
		_look(F + Vector3(0, 0, 6), 70.0)
		await _wait_sim(1.0)
		await _shot("%s_14_civic_standing" % tag)
		civ.take_damage(civ.hp + 100.0, null)
		await _wait_sim(10.0)
		await _shot("%s_15_civic_ruin" % tag)
	# 8. the command centre ruin once the fires are out
	_look(E + Vector3(0, 0, 8), 85.0)
	await _wait_sim(60.0)
	await _shot("%s_16_cc_ruin_cold" % tag)


# ------------------------------------------------------------------------------------------ benchmark
func _bench() -> void:
	var roster := {"abrams": 14, "bradley": 8, "m240_gunner": 10, "rifleman": 12, "at4": 6, "paladin": 3}
	var n := 0
	for team in 2:
		var z := 60.0 if team == 0 else -60.0
		var i := 0
		for k in roster:
			for j in int(roster[k]):
				var p := Vector3(-90.0 + (i % 18) * 10.0, 0, z + (1 if team == 0 else -1) * (i / 18) * 10.0)
				var u: Unit = battle._spawn(k, team, p, 0.0 if team == 0 else PI)
				u.order_attack_move(Vector3(p.x, 0, -z * 1.6))
				i += 1; n += 1
	_look(Vector3(0, 0, 10), 120.0)
	var secs := float(args.get("secs", "40"))
	await _wait_sim(2.0)
	frame_us.clear()
	var sim0: float = battle.sim_time
	var wall0 := Time.get_ticks_usec()
	var peak_nodes := 0
	var peak_p := 0
	var cap := -1
	while battle.sim_time - sim0 < secs:
		await get_tree().process_frame
		peak_nodes = maxi(peak_nodes, int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)))
		var d: Node = battle.get_node_or_null("FXDirector")
		if d:
			peak_p = maxi(peak_p, int(d.live_particles))
			cap = int(d.Q.particles)
	var wall := (Time.get_ticks_usec() - wall0) / 1e6
	var fu := frame_us.duplicate()
	fu.sort()
	var avg := 0.0
	for f in fu: avg += f
	avg /= maxf(1.0, fu.size())
	var p95: float = fu[int(fu.size() * 0.95)] if not fu.is_empty() else 0.0
	var alive := battle.units.filter(func(u): return not u.dead).size()
	var extra := ""
	var dd: Node = battle.get_node_or_null("FXDirector")
	if dd: extra = " fx_peak_particles=%d cap=%d fx_peak_lights=%d fx_stats=%s" % [peak_p, cap, dd.stats.peak_lights, str(dd.stats)]
	print("BENCH units=%d alive_end=%d sim=%.0fs frames=%d wall=%.1fs frame_avg=%.1fms p95=%.1fms fps=%.1f peak_nodes=%d graphics=%s%s" % [
		n, alive, secs, fu.size(), wall, avg / 1000.0, p95 / 1000.0, fu.size() / maxf(0.001, wall), peak_nodes, str(Game.settings.get("graphics")), extra])

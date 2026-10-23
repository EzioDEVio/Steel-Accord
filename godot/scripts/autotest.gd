# Steel Accord - automated playtest. Drives the game through the real input pipeline
# (Input.parse_input_event -> GUI buttons / Commander), checks outcomes, writes screenshots and a result log.
# Run: godot --path godot -- test out=/dir   (headless works; add --write-movie to record when rendering)
extends Node

var battle: Node
var out := "/tmp/sa_test"
var checks: Array = []
var shots := 0


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="): out = a.substr(4)
	DirAccess.make_dir_recursive_absolute(out)
	if DisplayServer.get_name() == "headless":
		get_tree().root.size = Vector2i(1280, 720)   # headless defaults to a tiny viewport
	_run()


func _log(name: String, ok: bool, detail := "") -> void:
	checks.append([name, ok, detail])
	printerr("TEST %s %s %s" % [name, "PASS" if ok else "FAIL", detail])


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	var stuck := 0
	while battle.sim_time < end:
		await get_tree().process_frame
		stuck += 1
		if stuck == 300 and get_tree().paused: print("TESTDBG stalled: paused=", get_tree().paused, " menu=", battle.pause_menu.visible, " sim_time=", battle.sim_time)


func _frames(n := 2) -> void:
	for i in n: await get_tree().process_frame


func _shot(tag: String) -> void:
	if DisplayServer.get_name() == "headless": return
	await RenderingServer.frame_post_draw
	shots += 1
	get_viewport().get_texture().get_image().save_png("%s/%02d_%s.png" % [out, shots, tag])


func _mouse(btn: MouseButton, pressed: bool, p: Vector2, mods := {}) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = btn; e.pressed = pressed; e.position = p; e.global_position = p
	e.shift_pressed = mods.get("shift", false); e.ctrl_pressed = mods.get("ctrl", false); e.alt_pressed = mods.get("alt", false)
	Input.parse_input_event(e)


func _click(btn: MouseButton, p: Vector2, mods := {}) -> void:
	_move_mouse(p)
	_mouse(btn, true, p, mods); _mouse(btn, false, p, mods)


func _move_mouse(p: Vector2, rel := Vector2.ZERO) -> void:
	var e := InputEventMouseMotion.new()
	e.position = p; e.global_position = p; e.relative = rel
	Input.parse_input_event(e)


func _key(k: Key, ctrl := false) -> void:
	for pressed in [true, false]:
		var e := InputEventKey.new()
		e.keycode = k; e.physical_keycode = k; e.pressed = pressed; e.ctrl_pressed = ctrl
		Input.parse_input_event(e)


func _press_button(b: Button) -> void:
	_click(MOUSE_BUTTON_LEFT, b.get_global_rect().get_center())


func _team(kinds: Array) -> Array:
	return battle.units.filter(func(u): return u.team == 0 and not u.dead and u.kind in kinds)


func _alive(us: Array) -> Array:
	return us.filter(func(u): return not u.dead)


func _screen(p: Vector3) -> Vector2:
	return battle.camera.cam.unproject_position(p)


func _box(units: Array) -> void:
	var r := Rect2(_screen(units[0].world_center()), Vector2.ZERO)
	for u in units: r = r.expand(_screen(u.world_center()))
	r = r.grow(30)
	_move_mouse(r.position); _mouse(MOUSE_BUTTON_LEFT, true, r.position)
	for i in 6:
		_move_mouse(r.position.lerp(r.end, (i + 1) / 6.0))
		await get_tree().process_frame
	_mouse(MOUSE_BUTTON_LEFT, false, r.end)
	await _frames()


func _centroid(us: Array) -> Vector3:
	var c := Vector3.ZERO
	for u in us: c += u.position
	return c / maxi(1, us.size())


func _red_hp() -> float:
	var h := 0.0
	for u in battle.units:
		if u.team == 1 and not u.dead: h += u.hp
	return h


func _run() -> void:
	await _wait_sim(1.0)
	var cmd: Commander = battle.commander
	var cam: RTSCamera = battle.camera
	cam.edge_pan = false
	var tanks := _team(["vanguard"])
	cam.focus(_centroid(tanks))
	await _frames()
	# 0a. pause menu: F10 opens and pauses; the Resume button closes; Esc with nothing selected also opens it
	_key(KEY_F10); await _frames(3)
	var opened: bool = get_tree().paused and battle.pause_menu.visible
	var resume: Button = null
	for ch in battle.pause_menu.box.get_children():
		if ch is Button and ch.text == "Resume": resume = ch
	if resume: _press_button(resume)
	await _frames(3)
	var resumed: bool = not get_tree().paused and not battle.pause_menu.visible
	_key(KEY_ESCAPE); await _frames(3)
	var esc_opens: bool = get_tree().paused
	_key(KEY_ESCAPE); await _frames(3)
	_log("pause_menu", opened and resumed and esc_opens and not get_tree().paused, "F10 open=%s, Resume closes=%s, Esc opens=%s" % [opened, resumed, esc_opens])
	# 0b. fog of war: own start area explored, enemy start not
	var cell: float = battle.FOG_RECT.size.x / battle.FOG_N
	var own_c: int = int((tanks[0].position.z - battle.FOG_RECT.position.y) / cell) * battle.FOG_N + int((tanks[0].position.x - battle.FOG_RECT.position.x) / cell)
	var red0: Unit = battle.units.filter(func(u): return u.team == 1)[0]
	var red_c: int = int((red0.position.z - battle.FOG_RECT.position.y) / cell) * battle.FOG_N + int((red0.position.x - battle.FOG_RECT.position.x) / cell)
	_log("fog_of_war", battle.explored[own_c] == 1 and battle.explored[red_c] == 0 and not red0.visible, "own base explored, enemy base unexplored and enemy hidden")
	# 1. box selection
	await _box(tanks)
	_log("box_select", cmd.live_selection().size() == tanks.size(), "selected=%d of %d" % [cmd.live_selection().size(), tanks.size()])
	await _shot("selected")
	# 2. control group
	_key(KEY_1, true); _key(KEY_ESCAPE); await _frames()
	var cleared := cmd.live_selection().is_empty()
	_key(KEY_1); await _frames()
	_log("control_group", cleared and cmd.live_selection().size() == tanks.size(), "recall=%d" % cmd.live_selection().size())
	# 3. classic scheme: LEFT click on ground moves the selection
	var start := {}
	for u in tanks: start[u.uid] = u.position
	var dest := _centroid(tanks) + Vector3(0, 0, -30)
	_click(MOUSE_BUTTON_LEFT, _screen(dest))
	await _wait_sim(4.0)
	var moved := 0.0
	for u in tanks: moved += u.position.distance_to(start[u.uid])
	_log("left_click_move", moved / tanks.size() > 12.0 and cmd.live_selection().size() == tanks.size(), "avg moved %.1f m, selection kept" % (moved / tanks.size()))
	# 4. right drag scrolls the map and keeps the selection
	var cam0: Vector3 = cam.position
	var p0 := Vector2(640, 360)
	_move_mouse(p0); _mouse(MOUSE_BUTTON_RIGHT, true, p0)
	for i in 10:
		_move_mouse(p0 + Vector2(i * 12, i * 6), Vector2(12, 6))
		await get_tree().process_frame
	_mouse(MOUSE_BUTTON_RIGHT, false, p0 + Vector2(120, 60))
	await _frames()
	_log("right_drag_scroll", cam.position.distance_to(cam0) > 5.0 and not cmd.live_selection().is_empty(), "camera moved %.1f m" % cam.position.distance_to(cam0))
	cam.focus(_centroid(tanks)); await _frames()
	# 5. right click deselects (classic)
	_click(MOUSE_BUTTON_RIGHT, Vector2(640, 300)); await _frames()
	_log("right_click_deselect", cmd.live_selection().is_empty(), "")
	_key(KEY_1); await _frames()
	# 6. Alt+click waypoints build a queue
	var c := _centroid(tanks)
	cam.focus(c + Vector3(-12, 0, -25)); await _frames()
	_click(MOUSE_BUTTON_LEFT, _screen(c + Vector3(-25, 0, -10)), {"alt": true})
	await _wait_sim(0.1)
	_click(MOUSE_BUTTON_LEFT, _screen(c + Vector3(-25, 0, -40)), {"alt": true})
	await _wait_sim(0.1)
	var queued := tanks.filter(func(u): return u.queue.size() >= 1).size()
	_log("waypoints", queued == tanks.size(), "%d units with queued waypoints" % queued)
	await _shot("waypoints")
	# 7. Guard mode via G, then click the ground
	_key(KEY_G)
	_click(MOUSE_BUTTON_LEFT, _screen(c + Vector3(0, 0, -20)))
	await _wait_sim(0.1)
	var guarding := tanks.filter(func(u): return u.state == Unit.S.GUARD).size()
	_log("guard_order", guarding == tanks.size(), "%d guarding" % guarding)
	# 8. Attack-Move via the on-screen command card button, then a ground click
	await _frames()
	_press_button(battle.hud.card_buttons["attack_move"])
	await _frames()
	var mode_ok: bool = cmd.mode == "attack_move"
	_click(MOUSE_BUTTON_LEFT, _screen(c + Vector3(0, 0, -45)))
	await _wait_sim(0.1)
	var am := tanks.filter(func(u): return u.state == Unit.S.ATTACK_MOVE).size()
	_log("command_card_attack_move", mode_ok and am == tanks.size(), "button set mode=%s, %d attack-moving" % [mode_ok, am])
	# 9. F-16 pipeline: click-select a jet on its pad, Shift+click the other, attack-move north
	var f16s := _team(["f16"])
	cam.focus(_centroid(f16s)); await _frames(3)
	_click(MOUSE_BUTTON_LEFT, Vector2(5, 700))   # empty ground: classic left click with selection = move... so deselect first
	_click(MOUSE_BUTTON_RIGHT, Vector2(640, 200)); await _frames()
	_click(MOUSE_BUTTON_LEFT, _screen(f16s[0].world_center())); await _frames()
	_click(MOUSE_BUTTON_LEFT, _screen(f16s[1].world_center()), {"shift": true}); await _frames()
	var sel_f16: int = cmd.live_selection().filter(func(u): return u.kind == "f16").size()
	_log("f16_click_select", sel_f16 == 2 and cmd.live_selection().size() == 2, "%d F-16 selected by click + shift-click" % sel_f16)
	await _shot("f16_selected_on_pad")
	_key(KEY_A)
	var reds0: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead)
	var strike: Vector3 = _centroid(reds0)
	cam.focus(strike); await _frames()
	_click(MOUSE_BUTTON_LEFT, _screen(strike))
	await _wait_sim(6.0)
	var airborne := f16s.filter(func(u): return u.altitude > 12.0 and u.airborne).size()
	_log("f16_takeoff", airborne == f16s.size(), "%d airborne, alt %.1f m" % [airborne, f16s[0].altitude])
	var ammo0: int = f16s[0].w_ammo[0]
	var fired := false
	var t_end: float = battle.sim_time + 40.0
	while battle.sim_time < t_end and not fired:
		await _wait_sim(0.5)
		fired = f16s.any(func(u): return u.w_ammo[0] < ammo0)
		if not _alive(f16s).is_empty(): cam.focus(_centroid(_alive(f16s)))
	_log("f16_missile_strike", fired, "ammo %d -> %d" % [ammo0, f16s[0].w_ammo[0]])
	await _shot("f16_attack")
	var landed := false
	t_end = battle.sim_time + 90.0
	while battle.sim_time < t_end and not landed:
		await _wait_sim(0.5)
		landed = _alive(f16s).any(func(u): return u.state == Unit.S.LANDED)
	var lj0: Array = _alive(f16s).filter(func(u): return u.state == Unit.S.LANDED)
	_log("f16_return_to_pad", landed and lj0[0].flat_dist(lj0[0].home) < 0.5, "landed %.2f m from pad centre, heading %.0f deg" % [lj0[0].flat_dist(lj0[0].home) if landed else -1.0, rad_to_deg(lj0[0].heading) if landed else 0.0])
	if landed:
		var lj: Unit = _alive(f16s).filter(func(u): return u.state == Unit.S.LANDED)[0]
		var a0: int = lj.w_ammo[0]
		await _wait_sim(4.0)
		_log("f16_rearm", lj.w_ammo[0] > a0 or lj.w_ammo[0] == 4, "ammo %d -> %d" % [a0, lj.w_ammo[0]])
	# 9b. A-10: attack order on an enemy tank -> cannon rounds fired
	var a10: Unit = _team(["a10"])[0] if not _team(["a10"]).is_empty() else null
	var redt: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead)
	if a10 and not redt.is_empty():
		var before: int = battle.shots_by.get(a10.uid, 0)
		battle.issue({"type": "attack", "ids": [a10.uid], "target": redt[0].uid})
		await _wait_sim(30.0)
		var fired_a10: int = int(battle.shots_by.get(a10.uid, 0)) - before
		_log("a10_cannon_fires", fired_a10 > 10, "%d cannon rounds fired" % fired_a10)
		battle.issue({"type": "return", "ids": [a10.uid]})
	# 9c. AH-64: fly out, then R: lands on its own pad; no rounds fired once returning
	var heli: Unit = _team(["ah64"])[0] if not _team(["ah64"]).is_empty() else null
	if heli:
		battle.issue({"type": "move", "ids": [heli.uid], "points": [heli.home + Vector3(-40, 0, -120)]})
		await _wait_sim(10.0)
		var up: bool = heli.altitude > 8.0
		cmd._set_selection([heli]); await _frames()
		_key(KEY_R); await _frames()
		var s0: int = battle.shots_by.get(heli.uid, 0)
		var t_h: float = battle.sim_time + 40.0
		while battle.sim_time < t_h and heli.state != Unit.S.LANDED:
			await _wait_sim(0.5)
		var s1: int = battle.shots_by.get(heli.uid, 0)
		_log("heli_return_lands_on_pad", up and heli.state == Unit.S.LANDED and heli.flat_dist(heli.home) < 1.0 and s1 == s0,
			"airborne=%s landed=%s %.2f m from pad, rounds fired while returning/landing: %d" % [up, heli.state == Unit.S.LANDED, heli.flat_dist(heli.home), s1 - s0])
		cmd._set_selection([])
	# 10. Support power by mouse: click the Carpet Bombing button, then click a target
	# a red structure as the target: units would chase blue forces out of the bomb line before the flight arrives
	var tb: Building = battle.add_structure("power_plant", 1, Vector3(0, 0, -120), true)
	var reds: Array = [tb]
	await _wait_sim(0.5)
	var tgt: Vector3 = _centroid(reds)
	cam.focus(tgt); await _frames(3)
	var hp0 := _red_hp()
	var cb0: int = battle.bomb_log.size()
	var bd0: float = battle.bomb_damage
	_press_button(battle.hud.power_buttons["carpet"])
	await _frames()
	var pm: bool = cmd.mode == "power:carpet"
	_click(MOUSE_BUTTON_LEFT, _screen(tgt))
	await _wait_sim(0.2)
	var flying: bool = not battle.flights.is_empty()
	await _wait_sim(5.5)
	await _shot("carpet_bombing")
	await _wait_sim(4.0)
	var hp1 := _red_hp()
	var cdrops: Array = battle.bomb_log.slice(cb0)
	var cnear := 1e9
	for bp in cdrops: cnear = minf(cnear, Vector2(bp.x - tgt.x, bp.z - tgt.z).length())
	var bdmg: float = battle.bomb_damage - bd0
	_log("support_power_carpet", pm and flying and bdmg > 0.0, "mode=%s flight=%s bomb damage to red %.0f, red hp %.0f -> %.0f; %d bombs, nearest %.0f m from target %s; reds %s" % [pm, flying, bdmg, hp0, hp1, cdrops.size(), cnear, tgt, reds.map(func(r): return "%s@(%.0f,%.0f)" % [r.kind, r.position.x, r.position.z])])
	# 10b. B-1 supersonic strike by mouse: bombs must be released and land near the marked point
	reds = battle.units.filter(func(u): return u.team == 1 and not u.dead)
	if not reds.is_empty():
		var t2: Vector3 = reds[0].position
		cam.focus(t2); await _frames(2)
		var nb0: int = battle.bomb_log.size()
		_press_button(battle.hud.power_buttons["supersonic"]); await _frames()
		_click(MOUSE_BUTTON_LEFT, _screen(t2))
		await _wait_sim(9.0)
		var drops: Array = battle.bomb_log.slice(nb0)
		var near: int = drops.filter(func(p): return Vector2(p.x - t2.x, p.z - t2.z).length() < 25.0).size()
		_log("support_power_b1", drops.size() == 6 and near >= 4, "%d bombs released, %d within 25 m of the mark" % [drops.size(), near])
	# 11. Ctrl+A then attack-move everything; play to the end
	_key(KEY_A, true); await _frames()
	_log("select_all", cmd.live_selection().size() == battle.alive_count(0), "%d selected" % cmd.live_selection().size())
	_key(KEY_A)
	cam.focus(Vector3(0, 0, -40)); await _frames()
	_click(MOUSE_BUTTON_LEFT, _screen(Vector3(0, 0, -100)))
	t_end = battle.sim_time + 200.0
	while battle.sim_time < t_end and not battle.game_over:
		await _wait_sim(1.0)
		if int(battle.sim_time) % 10 == 0:
			var idle: Array = battle.units.filter(func(u): return u.team == 0 and not u.dead and u.state == Unit.S.IDLE and u.domain != "jet")
			var reds2: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead)
			if not idle.is_empty() and not reds2.is_empty():
				var ids: Array = idle.map(func(u): return u.uid)
				battle.issue({"type": "attack_move", "ids": ids, "points": ids.map(func(_i): return reds2[0].position)})
	await _wait_sim(2.0)
	await _shot("end")
	_log("match_end", battle.game_over, battle.hud.banner)
	_log("command_log", battle.command_log.size() >= 9, "%d commands logged with ticks" % battle.command_log.size())
	var f := FileAccess.open(out + "/result.txt", FileAccess.WRITE)
	for ch in checks: f.store_line("%s %s %s" % [ch[0], "PASS" if ch[1] else "FAIL", ch[2]])
	f.close()
	print("TEST DONE ", checks.filter(func(ch): return ch[1]).size(), "/", checks.size())
	get_tree().quit()

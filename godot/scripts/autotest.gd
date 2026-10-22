# Steel Accord - automated G1 playtest. Drives the game through the real input pipeline
# (Input.parse_input_event -> Commander), checks outcomes, writes screenshots and a result log.
# Run: godot --path godot -- test out=/dir   (add --write-movie /dir/g1.avi --fixed-fps 30 to record)
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
	print("TEST %s %s %s" % [name, "PASS" if ok else "FAIL", detail])


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _shot(tag: String) -> void:
	if DisplayServer.get_name() == "headless": return
	await RenderingServer.frame_post_draw
	shots += 1
	get_viewport().get_texture().get_image().save_png("%s/%02d_%s.png" % [out, shots, tag])


func _mouse(btn: MouseButton, pressed: bool, p: Vector2, shift := false) -> void:
	var e := InputEventMouseButton.new()
	e.button_index = btn; e.pressed = pressed; e.position = p; e.global_position = p; e.shift_pressed = shift
	Input.parse_input_event(e)


func _move_mouse(p: Vector2) -> void:
	var e := InputEventMouseMotion.new()
	e.position = p; e.global_position = p
	Input.parse_input_event(e)


func _key(k: Key, ctrl := false) -> void:
	for pressed in [true, false]:
		var e := InputEventKey.new()
		e.keycode = k; e.physical_keycode = k; e.pressed = pressed; e.ctrl_pressed = ctrl
		Input.parse_input_event(e)


func _blue() -> Array:
	return battle.units.filter(func(u): return u.team == 0 and not u.dead)


func _screen(p: Vector3) -> Vector2:
	return battle.camera.cam.unproject_position(p)


func _run() -> void:
	await _wait_sim(1.0)
	var cmd: Commander = battle.commander
	battle.camera.edge_pan = false
	# 1. box selection with a real mouse drag
	var r := Rect2(_screen(_blue()[0].global_position), Vector2.ZERO)
	for u in _blue(): r = r.expand(_screen(u.global_position + Vector3.UP))
	r = r.grow(40)
	_move_mouse(r.position); _mouse(MOUSE_BUTTON_LEFT, true, r.position)
	for i in 6:
		_move_mouse(r.position.lerp(r.end, (i + 1) / 6.0))
		await get_tree().process_frame
	await _shot("box_select_drag")
	_mouse(MOUSE_BUTTON_LEFT, false, r.end)
	await get_tree().process_frame
	_log("box_select", cmd.selected.size() == _blue().size(), "selected=%d of %d" % [cmd.selected.size(), _blue().size()])
	await _shot("selected")
	# 2. control group: Ctrl+1, Esc (deselect), 1 (recall)
	_key(KEY_1, true); _key(KEY_ESCAPE)
	await get_tree().process_frame
	var cleared := cmd.selected.is_empty()
	_key(KEY_1)
	await get_tree().process_frame
	_log("control_group", cleared and cmd.selected.size() == _blue().size(), "after esc=%d after recall=%d" % [0 if cleared else -1, cmd.selected.size()])
	# 3. right-click move order
	var start := {}
	for u in _blue(): start[u.uid] = u.position
	var c0 := Vector3.ZERO
	for u in _blue(): c0 += u.position
	var dest := c0 / _blue().size() + Vector3(0, 0, -35)
	var sp := _screen(dest)
	_move_mouse(sp); _mouse(MOUSE_BUTTON_RIGHT, true, sp); _mouse(MOUSE_BUTTON_RIGHT, false, sp)
	await _wait_sim(0.5)
	await _shot("move_order")
	await _wait_sim(5.0)
	var moved := 0.0
	for u in _blue(): moved += u.position.distance_to(start[u.uid])
	moved /= _blue().size()
	_log("move_order", moved > 15.0, "avg moved %.1f m in 5.5 s" % moved)
	# 4. attack-move with A + left click, deep into enemy territory
	battle.camera.focus(dest + Vector3(0, 0, -20))
	await get_tree().process_frame
	var am := _screen(dest + Vector3(0, 0, -50))
	_key(KEY_A)
	await get_tree().process_frame
	_move_mouse(am); _mouse(MOUSE_BUTTON_LEFT, true, am); _mouse(MOUSE_BUTTON_LEFT, false, am)
	await get_tree().process_frame
	await _wait_sim(0.2)
	var n_am := _blue().filter(func(u): return u.state == Unit.S.ATTACK_MOVE).size()
	_log("attack_move_order", n_am == _blue().size(), "%d units attack-moving" % n_am)
	var follow := true
	var t_end: float = battle.sim_time + 160.0
	var fired_shot := false
	var kill_shot := false
	while battle.sim_time < t_end and not battle.game_over:
		await _wait_sim(0.5)
		var alive := _blue()
		if follow and not alive.is_empty():
			var c := Vector3.ZERO
			for u in alive: c += u.position
			battle.camera.focus(c / alive.size() + Vector3(0, 0, -18))
		if not fired_shot and not battle.shells.is_empty():
			fired_shot = true
			await _shot("first_contact")
		if not kill_shot and battle.units.any(func(u): return u.dead):
			kill_shot = true
			await _wait_sim(0.3)
			await _shot("first_kill")
		if int(battle.sim_time) % 10 == 0:
			print("T=%.0f blue=%d red=%d shells=%d" % [battle.sim_time, battle.alive_count(0), battle.alive_count(1), battle.shells.size()])
	await _wait_sim(2.0)
	await _shot("end")
	var red_dead: int = battle.units.filter(func(u): return u.team == 1 and u.dead).size()
	var blue_dead: int = battle.units.filter(func(u): return u.team == 0 and u.dead).size()
	_log("combat_fired", fired_shot, "")
	_log("units_destroyed", red_dead + blue_dead > 0, "red lost %d, blue lost %d" % [red_dead, blue_dead])
	_log("match_end", battle.game_over, battle.hud.banner)
	_log("command_log", battle.command_log.size() >= 3, "%d commands logged with ticks" % battle.command_log.size())
	var f := FileAccess.open(out + "/result.txt", FileAccess.WRITE)
	for c in checks: f.store_line("%s %s %s" % [c[0], "PASS" if c[1] else "FAIL", c[2]])
	f.close()
	print("TEST DONE ", checks.filter(func(c): return c[1]).size(), "/", checks.size())
	get_tree().quit()

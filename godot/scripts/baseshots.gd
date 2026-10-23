# Steel Accord - rendered evidence for the base loop (run with: -- baseshots lite noai out=/dir). Sets up a base state
# directly (structures, a site under construction, units) and captures what the player sees. Not part of gameplay.
extends Node

var battle: Node
var out := "user://test_output/sa_baseshots"


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="): out = a.substr(4)
	DirAccess.make_dir_recursive_absolute(out)
	_run()


func _wait(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _shot(tag: String) -> void:
	for i in 3: await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, tag])
	print("SHOT ", tag)


func _look(p: Vector3, zoom: float) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam._apply(); cam.focus(p)


func _run() -> void:
	get_tree().root.size = Vector2i(1280, 720)
	var c: Vector3 = battle.start_pos[0]
	await _wait(0.3)
	var part2: bool = "part2" in battle.args
	if not part2:
		_look(c + Vector3(0, 0, -20), 90.0)
		await _shot("b01_start")
	# a base: power plants, barracks, depot, factory, airfield, radar, tower, hesco
	var layout := [["power_plant", Vector3(-40, 0, -6)], ["power_plant", Vector3(-40, 0, 14)], ["barracks", Vector3(40, 0, -16)],
		["supply_depot", Vector3(-50, 0, -40)], ["war_factory", Vector3(0, 0, -50)], ["radar", Vector3(45, 0, 16)],
		["defense_tower", Vector3(-20, 0, -78)], ["hesco", Vector3(0, 0, -82)], ["airfield", Vector3(95, 0, -40)]]
	for e in layout:
		battle.add_structure(e[0], 0, c + e[1], true)
	battle.cash[0] = 20000
	# a site under construction, with the dozer working on it
	var site: Building = battle.add_structure("barracks", 0, c + Vector3(55, 0, -70), false)
	site.progress = 0.45
	var dz: Unit = battle.units.filter(func(u): return u.kind == "dozer" and u.team == 0)[0]
	dz.position = site.position + Vector3(-site.half.x - 4.0, 0, 0)
	dz.order_build(site)
	# units
	var y := c.z - 110.0
	var kinds := ["rifleman", "rifleman", "rifleman", "at4", "at4", "hmmwv_50cal", "avenger", "vanguard", "vanguard"]
	for i in kinds.size():
		var u: Unit = battle._spawn(kinds[i], 0, Vector3(-40 + i * 9, 0, y + (i % 2) * 6), 0.4 * i)
		u.reset_physics_interpolation()
	var reds := ["vanguard", "rifleman", "at4", "hmmwv_50cal"]
	for i in reds.size():
		var u: Unit = battle._spawn(reds[i], 1, Vector3(-20 + i * 12, 0, y - 30), PI)
		u.reset_physics_interpolation()
	if part2:
		await _part2(c, dz)
		return
	await _wait(2.0)
	_look(c + Vector3(0, 0, -35), 120.0)
	await _shot("b02_base_overview")
	_look(c + Vector3(0, 0, -30), 75.0)
	await _shot("b03_base_close")
	_look(site.position, 55.0)
	await _shot("b04_construction")
	_look(Vector3(0, 0, y - 10), 60.0)
	await _shot("b05_units")
	# combat between the two groups
	var blues: Array = battle.units.filter(func(u): return u.team == 0 and u.kind in kinds)
	battle.issue({"type": "attack_move", "ids": blues.map(func(u): return u.uid), "points": blues.map(func(_u): return Vector3(0, 0, y - 30))})
	await _wait(5.0)
	_look(Vector3(0, 0, y - 15), 60.0)
	await _shot("b06_combat")
	# placement preview and the build panel
	battle.commander._set_selection([dz])
	battle.commander.set_mode("place:power_plant")
	_look(c + Vector3(-80, 0, -60), 80.0)
	battle.commander.mouse_override = Vector2(640, 330)
	await _wait(0.2)
	await _shot("b07_placement_ok")
	battle.commander.mouse_override = battle.camera.cam.unproject_position(c + Vector3(0, 0, -50))
	_look(c + Vector3(0, 0, -50), 80.0)
	battle.commander.mouse_override = Vector2(640, 360)
	await _wait(0.2)
	await _shot("b08_placement_blocked")
	battle.commander.set_mode("")
	# a structure selected: production card
	var bk: Building = battle.structures(0, "barracks")[0]
	battle.commander._set_selection([bk])
	battle.issue({"type": "produce", "team": 0, "id": bk.uid, "kind": "rifleman"})
	battle.issue({"type": "produce", "team": 0, "id": bk.uid, "kind": "at4"})
	_look(bk.position, 80.0)
	await _wait(1.0)
	await _shot("b09_production_card")
	# helicopter rotor (two frames)
	var af: Building = battle.structures(0, "airfield")[0]
	battle.issue({"type": "produce", "team": 0, "id": af.uid, "kind": "ah64"})
	await _wait(17.0)
	var heli: Unit = null
	for u in battle.units:
		if u.kind == "ah64" and u.team == 0 and not u.dead: heli = u
	if heli:
		battle.issue({"type": "move", "ids": [heli.uid], "points": [heli.position + Vector3(-30, 0, -30)]})
		await _wait(2.5)
		_look(heli.position + Vector3(0, 0, -heli.altitude * 0.78), 46.0)
		await _shot("b10_heli_a")
		await _wait(0.1)
		await _shot("b11_heli_b")
	# a hauler at work
	var ch: Array = battle.units.filter(func(u): return u.kind == "ch47" and u.team == 0 and not u.dead)
	if not ch.is_empty():
		_look(ch[0].position, 70.0)
		await _shot("b12_hauler")
	get_tree().quit()


func _part2(c: Vector3, dz: Unit) -> void:
	await _wait(0.3)
	battle.commander._set_selection([dz])
	battle.commander.set_mode("place:power_plant")
	_look(c + Vector3(0, 0, -50), 80.0)
	battle.commander.mouse_override = Vector2(640, 360)
	await _wait(0.1)
	await _shot("b08_placement_blocked")
	battle.commander.set_mode("")
	var bk: Building = battle.structures(0, "barracks")[0]
	battle.commander._set_selection([bk])
	battle.issue({"type": "produce", "team": 0, "id": bk.uid, "kind": "rifleman"})
	battle.issue({"type": "produce", "team": 0, "id": bk.uid, "kind": "at4"})
	_look(bk.position, 80.0)
	await _wait(0.5)
	await _shot("b09_production_card")
	battle.commander._set_selection([])
	var heli: Unit = battle._spawn("ah64", 0, c + Vector3(60, 0, -120), 0.3)
	heli.reset_physics_interpolation()
	var ch: Unit = battle._spawn("ch47", 0, c + Vector3(-20, 0, -120), -0.4)
	ch.reset_physics_interpolation()
	battle.issue({"type": "move", "ids": [heli.uid, ch.uid], "points": [heli.position + Vector3(0, 0, -40), ch.position + Vector3(0, 0, -40)]})
	await _wait(1.0)
	_look(heli.position + Vector3(0, 0, -heli.altitude * 0.78), 46.0)
	await _shot("b10_heli_a")
	await _wait(0.1)
	await _shot("b11_heli_b")
	_look(ch.position + Vector3(0, 0, -ch.altitude * 0.78), 55.0)
	await _shot("b12_ch47")
	get_tree().quit()

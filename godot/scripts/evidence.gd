# Steel Accord - rendered evidence capture for aircraft behaviour (run with: -- airshow lite evidence out=/dir).
# Captures: scale reference on the pads, take-off roll, attack run with trails, B-1 / B-52 strikes with falling bombs
# and impacts, and a jet landing on its pad. Not part of gameplay.
extends Node

var battle: Node
var out := "/tmp/sa_evidence"


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="): out = a.substr(4)
	DirAccess.make_dir_recursive_absolute(out)
	_run()


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _shot(tag: String) -> void:
	for i in 3: await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, tag])
	print("SHOT ", tag)


func _u(kind: String) -> Unit:
	for u in battle.units:
		if u.kind == kind and u.team == 0 and not u.dead: return u
	return null


func _look(p: Vector3, alt := 0.0, zoom := 60.0) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam._apply()
	cam.focus(p - Vector3(0, 0, alt * 0.78))


func _run() -> void:
	await _wait_sim(0.5)
	battle.ai = null
	var cmd: Commander = battle.commander
	battle.camera.edge_pan = false
	# 0. scale reference: a Vanguard tank parked beside the pads with the aircraft
	var tank := _u("vanguard")
	tank.position = Vector3(130, 0, 165); tank.heading = 0.0
	_look(Vector3(185, 0, 167), 0.0, 95.0)
	await _shot("air2_00_scale_pads_tank")
	# 1. F-16 take-off roll and climb toward the enemy
	var f16 := _u("f16")
	var reds: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead)
	for r in reds: r.order_stop()
	var tgt: Unit = reds[3]
	tgt.position = Vector3(40, 0, -20)
	battle.issue({"type": "attack", "ids": [f16.uid], "target": tgt.uid})
	cmd._set_selection([f16])
	await _wait_sim(1.0)
	_look(f16.position, f16.altitude, 60.0)
	await _shot("air2_01_f16_takeoff_roll")
	# 2. attack run: wait for the first missile, capture jet + missile trail + target
	var t_end: float = battle.sim_time + 30.0
	while battle.sim_time < t_end:
		await _wait_sim(0.1)
		if battle.shots.any(func(s): return s.shooter == f16):
			await _wait_sim(0.5)
			_look((f16.position + tgt.position) * 0.5, 8.0, 90.0)
			await _shot("air2_02_f16_attack_run_trails")
			break
	# 3. B-1 strike: falling bombs, then impacts
	var c := Vector3(-60, 0, -60)
	for i in 3: reds[i].position = c + Vector3(i * 10 - 10, 0, 0)
	battle.issue({"type": "power", "team": 0, "id": "supersonic", "pos": c})
	_look(c + Vector3(0, 0, 40), 0.0, 120.0)
	t_end = battle.sim_time + 15.0
	while battle.sim_time < t_end and battle.bombs.is_empty():
		await _wait_sim(0.1)
	await _wait_sim(0.6)
	await _shot("air2_03_b1_bombs_falling")
	await _wait_sim(1.3)
	_look(c, 0.0, 110.0)
	await _shot("air2_04_b1_impacts")
	# 4. B-52 carpet strike
	var c2 := Vector3(80, 0, -120)
	battle.issue({"type": "power", "team": 0, "id": "carpet", "pos": c2})
	_look(c2 + Vector3(0, 0, 30), 0.0, 130.0)
	while battle.bombs.is_empty():
		await _wait_sim(0.1)
	await _wait_sim(1.5)
	await _shot("air2_05_b52_carpet")
	# 5. F-16 returns and lands on its pad
	battle.issue({"type": "return", "ids": [f16.uid]})
	t_end = battle.sim_time + 60.0
	var shot_final := false
	while battle.sim_time < t_end and f16.state != Unit.S.LANDED:
		await _wait_sim(0.2)
		if not shot_final and f16.ret_phase == 1 and f16.flat_dist(f16.home) < 50.0:
			_look(f16.home + Vector3(0, 0, 20), 0.0, 70.0)
			await _shot("air2_06_f16_final_approach")
			shot_final = true
	await _wait_sim(1.0)
	_look(f16.home, 0.0, 60.0)
	cmd._set_selection([f16])
	await _shot("air2_07_f16_landed_on_pad")
	print("EVIDENCE DONE")
	get_tree().quit()

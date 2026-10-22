# Steel Accord - rendered evidence capture for the aircraft integration (run with: -- airshow lite evidence out=/dir).
# Positions the camera on each aircraft type in flight / on the pads and saves screenshots. Not part of gameplay.
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


func _run() -> void:
	await _wait_sim(0.5)
	var cam: RTSCamera = battle.camera
	var cmd: Commander = battle.commander
	battle.hud.show_help = false
	cam.edge_pan = false
	# 1. the air wing on its pads, F-16 selected (portrait + command card visible)
	cam.zoom = 62.0; cam._apply(); cam.focus(Vector3(97, 0, 127))
	cmd._set_selection([_u("f16")])
	await _shot("air_01_pads_f16_selected")
	# 2. launch everything north in a loose formation
	var kinds := ["f16", "fa18", "f22", "a10", "ah64", "uh60", "ch47"]
	for i in kinds.size():
		var u := _u(kinds[i])
		battle.issue({"type": "move", "ids": [u.uid], "points": [Vector3(-60 + i * 22, 0, 40)]})
	cmd._set_selection([])
	await _wait_sim(7.0)
	cam.zoom = 46.0; cam._apply()
	for k in kinds:
		var u := _u(k)
		if u == null: continue
		cam.focus(u.position - Vector3(0, 0, u.altitude * 0.75))   # aim at the airframe, not its ground point
		cmd._set_selection([u])
		await _shot("air_10_%s_in_flight" % k)
	cmd._set_selection([])
	# 3. AH-64 and A-10 attack the nearest enemy tank; capture the engagement
	var reds: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead)
	var tgt: Unit = reds[0]
	for k in ["ah64", "a10", "f16"]:
		battle.issue({"type": "attack", "ids": [_u(k).uid], "target": tgt.uid})
	var t_end: float = battle.sim_time + 30.0
	var got := false
	while battle.sim_time < t_end and not got:
		await _wait_sim(0.25)
		var h := _u("ah64")
		if h and battle.shots.any(func(s): return s.shooter == h):
			cam.zoom = 48.0; cam._apply(); cam.focus((h.position + tgt.position) * 0.5)
			await _shot("air_20_ah64_attack")
			got = true
	# 4. support powers: carpet bombing and stealth strike on the enemy group, recon overflight
	reds = battle.units.filter(func(u): return u.team == 1 and not u.dead)
	var c := Vector3.ZERO
	for r in reds: c += r.position
	c /= maxi(1, reds.size())
	battle.issue({"type": "power", "team": 0, "id": "carpet", "pos": c})
	cam.zoom = 95.0; cam._apply(); cam.focus(c + Vector3(0, 0, 25))
	await _wait_sim(5.2)
	await _shot("air_30_carpet_bombing_b52")
	await _wait_sim(1.5)
	await _shot("air_31_carpet_impacts")
	battle.issue({"type": "power", "team": 0, "id": "stealth", "pos": c + Vector3(15, 0, 0)})
	await _wait_sim(4.0)
	await _shot("air_32_stealth_b2")
	battle.issue({"type": "power", "team": 0, "id": "supersonic", "pos": c - Vector3(15, 0, 0)})
	await _wait_sim(3.0)
	await _shot("air_33_supersonic_b1")
	battle.issue({"type": "power", "team": 0, "id": "recon", "pos": Vector3(-80, 0, -60)})
	cam.zoom = 120.0; cam._apply(); cam.focus(Vector3(-70, 0, 20))
	await _wait_sim(1.6)
	await _shot("air_34_recon_sr71")
	print("EVIDENCE DONE")
	get_tree().quit()

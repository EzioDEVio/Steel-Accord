# Steel Accord - rendered evidence for the B3 HD bombers (not part of gameplay).
# Run (rendered, not headless): -- bombershots army map=zagros_basin strikecam res=1920x1080 out=/dir
# Shots: each HD bomber close up in flight during a real strike, the B-52 with its bay open and bombs falling (main
# view with the picture-in-picture strike camera, and the strike camera's own image), the Strategic Strike Package
# formation over Zagros from a chase view and from the RTS camera.
extends Node

var battle: Node
var out := "user://test_output/sa_bombers"
var cam: Camera3D


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="): out = a.substr(4)
	DirAccess.make_dir_recursive_absolute(out)
	_run()


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _shot(tag: String, img: Image = null) -> void:
	for i in 4: await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var im: Image = img if img else get_viewport().get_texture().get_image()
	im.save_png("%s/%s.png" % [out, tag])
	print("SHOT ", tag, " ", im.get_size())


func _flight(id: String, i := 0) -> Dictionary:
	for f in battle.flights:
		if f.has("strike") and f.id == id and f.index == i: return f
	return {}


func _freeze(on: bool) -> void:
	get_tree().paused = on


## Free camera relative to a flight: offsets in the flight frame (right, up, back), looking at a point offset likewise.
func _cam_on(f: Dictionary, right: float, up: float, back: float, look := Vector3.ZERO, fov := 40.0) -> void:
	var p: Vector3 = f.model.global_position
	var d: Vector3 = f.dir; var r: Vector3 = f.right
	cam.fov = fov
	cam.global_position = p + r * right + Vector3.UP * up - d * back
	cam.look_at(p + r * look.x + Vector3.UP * look.y - d * look.z, Vector3.UP)
	cam.make_current()


func _rts() -> void:
	battle.camera.cam.make_current()


func _run() -> void:
	var rs: PackedStringArray = str(battle.args.get("res", "1920x1080")).split("x")
	var want := Vector2i(int(rs[0]), int(rs[1]))
	DisplayServer.window_set_size(want)
	get_tree().root.size = want
	await _wait_sim(0.5)
	battle.ai = null
	for u in battle.units: if u.team == 1: u.order_stop()
	battle.camera.edge_pan = false
	cam = Camera3D.new()
	cam.near = 0.3; cam.far = 3000.0
	battle.add_child(cam)
	var tgt: Vector3 = battle.grounded(Vector3(20, 0, -40))
	# 1. close-ups of each bomber during its own strike (doors open / B-1 swept just before release)
	for e in [["supersonic", "b3_b1_hd_close", 26.0, 7.0, 20.0], ["stealth", "b3_b2_hd_close", 24.0, 9.0, 22.0], ["carpet", "b3_b52_hd_close", 34.0, 10.0, 30.0]]:
		battle.power_ready[0][e[0]] = 0.0
		battle.launch_power(0, e[0], tgt)
		var t_end: float = battle.sim_time + 40.0
		var f := _flight(e[0])
		while battle.sim_time < t_end and not f.is_empty() and f.doors < 0.97:
			await _wait_sim(0.1)
		if f.is_empty(): continue
		_freeze(true)
		_cam_on(f, -e[2], -e[3] * 0.25, -e[4] * 0.6, Vector3(0, -1.5, 0), 38.0)
		await _shot(e[1])
		_freeze(false)
		while battle.flights.any(func(x): return x.has("strike")) or battle.bombs.any(func(b): return b.has("strike")):
			await _wait_sim(0.5)
	# 2. B-52 bay open, bombs falling: main view beside / below the bomber with the strike-camera inset, and the inset alone
	var t2: Vector3 = battle.grounded(Vector3(-30, 0, -60))
	battle.power_ready[0]["carpet"] = 0.0
	battle.launch_power(0, "carpet", t2)
	var f2 := _flight("carpet")
	var t_e: float = battle.sim_time + 40.0
	while battle.sim_time < t_e and not f2.is_empty() and f2.dropped < 7:
		await _wait_sim(0.05)
	await _wait_sim(0.35)
	_freeze(true)
	_cam_on(f2, -46.0, -16.0, -6.0, Vector3(0, -6.0, 4.0), 42.0)
	await _shot("b3_b52_bay_open_bombs_main_pip")
	var sc: Node = battle.strikes.cam
	if sc and is_instance_valid(sc):
		await _shot("b3_b52_bay_open_bombs_strikecam", sc.vp.get_texture().get_image())
	_freeze(false)
	await _wait_sim(2.2)
	_rts()
	battle.camera.zoom = 120.0; battle.camera._apply(); battle.camera.focus(t2)
	await _shot("b3_b52_impacts_rts_pip")
	while battle.flights.any(func(x): return x.has("strike")) or battle.bombs.any(func(b): return b.has("strike")) or battle.strikes.cam != null:
		await _wait_sim(0.5)
	# 3. Strategic Strike Package over Zagros
	var t3: Vector3 = battle.grounded(Vector3(0, 0, -20))
	battle.power_ready[0]["strike_package"] = 0.0
	battle.launch_power(0, "strike_package", t3)
	var lead := _flight("strike_package", 0)
	t_e = battle.sim_time + 40.0
	while battle.sim_time < t_e and not lead.is_empty() and (lead.pos - lead.aim).dot(lead.dir) < -260.0:
		await _wait_sim(0.1)
	_freeze(true)
	_cam_on(lead, 30.0, 70.0, 330.0, Vector3(0, -25.0, 60.0), 50.0)
	await _shot("b3_strike_package_zagros_chase")
	_rts()
	var c := Vector3.ZERO
	var n := 0
	for f in battle.flights:
		if f.has("strike") and f.id == "strike_package": c += f.pos; n += 1
	battle.camera.zoom = 230.0; battle.camera._apply(); battle.camera.focus(c / maxf(1.0, n) + lead.dir * 40.0)
	await _shot("b3_strike_package_zagros_rts")
	_freeze(false)
	while battle.sim_time < t_e and not lead.is_empty() and lead.dropped < 1:
		await _wait_sim(0.1)
	await _wait_sim(3.0)
	battle.camera.zoom = 200.0; battle.camera._apply(); battle.camera.focus(t3)
	await _shot("b3_strike_package_zagros_impacts")
	print("BOMBERSHOTS DONE")
	get_tree().quit()

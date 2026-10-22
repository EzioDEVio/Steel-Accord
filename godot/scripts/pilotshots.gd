# Steel Accord - rendered in-game checks for the 3D pilot set (run with: -- pilotshots lite noai out=/dir).
# Supply Depot (built + under construction), M88 Dozer, CH-47, Rifleman: camera orbit (4 yaws), tilt, close zoom,
# moving frames. Not part of gameplay.
extends Node

var battle: Node
var out := "/tmp/sa_pilot"


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


func _cam(p: Vector3, zoom: float, yaw_deg: float, pitch: float) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam.yaw = deg_to_rad(yaw_deg); cam.pitch_deg = pitch
	cam._apply(); cam.focus(p)


func _run() -> void:
	get_tree().root.size = Vector2i(1280, 720)
	var c: Vector3 = battle.start_pos[0]
	await _wait(0.3)
	var dp: Building = battle.add_structure("supply_depot", 0, c + Vector3(-45, 0, -40), true)
	var site: Building = battle.add_structure("supply_depot", 0, c + Vector3(15, 0, -60), false)
	site.progress = 0.55
	var dz: Unit = battle.units.filter(func(u): return u.kind == "dozer" and u.team == 0)[0]
	dz.position = site.position + Vector3(-site.half.x - 4.0, 0, 6); dz.reset_physics_interpolation()
	dz.order_build(site)
	# a CH-47 parked beside the finished depot, a squad next to it
	var ch: Unit = battle._spawn("ch47", 0, dp.position + Vector3(-26, 0, 0), 0.0)
	ch.state = Unit.S.LANDED; ch.altitude = 0.0; ch.body.position.y = 0.0; ch.home = ch.position
	ch.reset_physics_interpolation()
	var sq: Array = []
	for i in 4:
		var r: Unit = battle._spawn("rifleman", 0, dp.position + Vector3(-6 + i * 3.0, 0, 16), 0.3 * i)
		r.reset_physics_interpolation(); sq.append(r)
	await _wait(1.0)
	var mid: Vector3 = (dp.position + site.position) * 0.5
	for yaw in [0, 90, 180, 270]:
		_cam(mid, 95.0, yaw, 52.0)
		await _shot("p01_orbit_yaw%03d" % yaw)
	_cam(mid, 95.0, 30.0, 35.0); await _shot("p02_tilt_low")
	_cam(mid, 120.0, 0.0, 72.0); await _shot("p03_tilt_high")
	_cam(dp.position, 55.0, 25.0, 45.0); await _shot("p04_depot_close")
	_cam(site.position, 50.0, -30.0, 45.0); await _shot("p05_construction_close")
	_cam(ch.position, 44.0, 40.0, 40.0); await _shot("p06_ch47_close")
	_cam(dp.position + Vector3(-12, 0, 0), 70.0, 0.0, 52.0); await _shot("p07_ch47_vs_depot_default")
	# moving: dozer and squad
	battle.issue({"type": "move", "ids": [dz.uid], "points": [dz.position + Vector3(-30, 0, -25)]})
	battle.issue({"type": "move", "ids": sq.map(func(u): return u.uid), "points": sq.map(func(u): return u.position + Vector3(0, 0, -40))})
	await _wait(1.5)
	_cam(dz.position, 34.0, 60.0, 40.0); await _shot("p08_dozer_moving_a")
	await _wait(0.2)
	_cam(dz.position, 34.0, 60.0, 40.0); await _shot("p09_dozer_moving_b")
	_cam(sq[1].position, 26.0, 70.0, 35.0); await _shot("p10_rifle_walk_a")
	await _wait(0.25)
	_cam(sq[1].position, 26.0, 70.0, 35.0); await _shot("p11_rifle_walk_b")
	# CH-47 lift-off with spinning rotors
	battle.issue({"type": "move", "ids": [ch.uid], "points": [ch.position + Vector3(0, 0, -60)]})
	await _wait(2.5)
	_cam(ch.position, 50.0, 20.0, 50.0); await _shot("p12_ch47_flying")
	get_tree().quit()

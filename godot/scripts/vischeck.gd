# Steel Accord - rendered visual check (run with: -- vischeck out=/dir). Captures unit readability against the terrain
# and the helicopter rotor animation (two frames a fraction of a second apart). Not part of gameplay.
extends Node

var battle: Node
var out := "/tmp/sa_vischeck"


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
	for i in 2: await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, tag])
	print("SHOT ", tag)


func _look(p: Vector3, zoom: float) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam._apply(); cam.focus(p)


func _run() -> void:
	get_tree().root.size = Vector2i(1280, 720)
	await _wait(0.5)
	var blues: Array = battle.units.filter(func(u): return u.team == 0 and u.domain == "ground")
	var reds: Array = battle.units.filter(func(u): return u.team == 1 and u.domain == "ground")
	_look(blues[0].position, 70.0); await _shot("tanks_blue_default_zoom")
	_look(blues[0].position, 150.0); await _shot("tanks_blue_far_zoom")
	# bring a red tank next to the blues for a side-by-side
	reds[0].position = blues[0].position + Vector3(14, 0, -10); reds[0].reset_physics_interpolation()
	_look(blues[0].position, 55.0); await _shot("tanks_blue_vs_red_close")
	var heli: Unit = null
	for u in battle.units:
		if u.kind == "ah64" and u.team == 0: heli = u
	if heli:
		battle.issue({"type": "move", "ids": [heli.uid], "points": [heli.position + Vector3(-40, 0, -30)]})
		var t0 := Time.get_ticks_msec()
		await _wait(2.0)
		print("heli wait ms ", Time.get_ticks_msec() - t0, " alt ", heli.altitude)
		_look(heli.position + Vector3(0, 0, -heli.altitude * 0.78), 48.0)
		await _shot("heli_rotor_a")
		await _wait(0.07)
		await _shot("heli_rotor_b")
	get_tree().quit()

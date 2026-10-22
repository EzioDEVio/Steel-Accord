# Steel Accord - rendered evidence for menus, fog of war and the A-10 cannon (run with: -- uishots lite).
extends Node

var battle: Node
const OUT := "/home/claude/sa/ui"


func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(OUT)
	_run()


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().process_frame


func _shot(tag: String) -> void:
	for i in 3: await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [OUT, tag])
	print("SHOT ", tag)


func _run() -> void:
	await _wait_sim(1.0)
	var cam: RTSCamera = battle.camera
	cam.edge_pan = false
	# fog of war at match start (zoomed out over the middle of the map)
	cam.zoom = 230.0; cam._apply(); cam.focus(Vector3(0, 0, 80))
	await _shot("ui_01_fog_of_war_start")
	# A-10 strafing run on an enemy tank parked in the open
	var a10: Unit = null
	for u in battle.units:
		if u.kind == "a10": a10 = u
	var red: Unit = battle.units.filter(func(u): return u.team == 1)[0]
	battle.ai = null
	red.position = Vector3(60, 0, 20); red.order_stop()
	battle.issue({"type": "attack", "ids": [a10.uid], "target": red.uid})
	var t_end: float = battle.sim_time + 40.0
	var n0: int = battle.shots_by.get(a10.uid, 0)
	while battle.sim_time < t_end:
		await _wait_sim(0.1)
		if int(battle.shots_by.get(a10.uid, 0)) - n0 > 8:
			cam.zoom = 75.0; cam._apply(); cam.focus((a10.position + red.position) * 0.5 - Vector3(0, 0, 6))
			await _shot("ui_02_a10_strafing")
			break
	# pause menu
	battle.open_menu()
	await _shot("ui_03_pause_menu")
	battle.pause_menu.close()
	# end of match screen
	for u in battle.units:
		if u.team == 1 and not u.dead: u.take_damage(99999.0, null)
	await get_tree().create_timer(3.5).timeout
	await _shot("ui_04_end_screen")
	get_tree().quit()

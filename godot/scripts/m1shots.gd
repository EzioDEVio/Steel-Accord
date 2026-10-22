# Steel Accord - rendered milestone review (run with: -- m1shots lite noai out=/dir). Places every structure kind and
# every vehicle kind on the player's side and captures orbit / close views. Not part of gameplay.
extends Node

var battle: Node
var out := "/tmp/sa_m1"


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
	battle.cash[0] = 50000
	var layout := [["power_plant", Vector3(-45, 0, -5)], ["barracks", Vector3(42, 0, -10)], ["supply_depot", Vector3(-52, 0, -40)],
		["war_factory", Vector3(5, 0, -45)], ["radar", Vector3(48, 0, 20)], ["defense_tower", Vector3(-20, 0, -80)],
		["hesco", Vector3(0, 0, -84)], ["hesco", Vector3(8, 0, -84)], ["drop_zone", Vector3(55, 0, -45)],
		["airfield", Vector3(-110, 0, -20)]]
	var blds := {}
	for e in layout:
		blds[e[0]] = battle.add_structure(e[0], 0, c + e[1], true)
	var site: Building = battle.add_structure("power_plant", 0, c + Vector3(95, 0, -10), false)
	site.progress = 0.5
	blds.barracks.prod_queue = ["rifleman"]; blds.barracks.prod_left = 4.0
	var kinds: Array = BuildingDefs.DEFS.war_factory.produces
	var row: Array = []
	for i in kinds.size():
		var u: Unit = battle._spawn(kinds[i], 0, c + Vector3(-60 + (i % 6) * 14.0, 0, -125 - (i / 6) * 16.0), 0.5)
		u.reset_physics_interpolation(); row.append(u)
	var inf := ["rifleman", "at4", "rifleman", "at4"]
	for i in inf.size():
		var u: Unit = battle._spawn(inf[i], 0, c + Vector3(30 + i * 3.0, 0, -100), 0.3)
		u.reset_physics_interpolation()
	await _wait(1.5)
	var mid: Vector3 = c + Vector3(0, 0, -30)
	for yaw in [0, 120, 240]:
		_cam(mid, 150.0, yaw, 52.0)
		await _shot("m1_base_yaw%03d" % yaw)
	_cam(mid, 120.0, 20.0, 34.0); await _shot("m1_base_low")
	for k in blds:
		var b: Building = blds[k]
		_cam(b.position, 30.0 + maxf(b.half.x, b.half.y) * 1.8, 25.0, 45.0)
		await _shot("m1_close_%s" % k)
	_cam(site.position, 50.0, -20.0, 45.0); await _shot("m1_construction")
	_cam(c + Vector3(-25, 0, -133), 80.0, 0.0, 50.0); await _shot("m1_vehicles")
	_cam(c + Vector3(-25, 0, -133), 60.0, 160.0, 40.0); await _shot("m1_vehicles_rear")
	_cam(c + Vector3(35, 0, -100), 26.0, 60.0, 38.0); await _shot("m1_infantry")
	get_tree().quit()

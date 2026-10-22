# Steel Accord - rendered RTS-camera review of a heightfield map (run with: -- mapshots map=zagros_basin nation1=iran
# noai out=/dir). Builds a small base for each side on the terrain, spawns U.S. and Iranian infantry and vehicles,
# captures a derrick for each side and takes screenshots. Not part of gameplay.
extends Node

var battle: Node
var out := "/tmp/sa_mapshots"


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
	printerr("SHOT ", tag)


func _cam(p: Vector3, zoom: float, yaw_deg: float, pitch: float) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam.yaw = deg_to_rad(yaw_deg); cam.pitch_deg = pitch
	cam._apply(); cam.focus(p)


func _flat(team: int, k: String, p: Vector3) -> Vector3:
	for i in 300:
		var r := 4.0 * sqrt(float(i)); var ang := float(i) * 2.4
		var q: Vector3 = p + Vector3(cos(ang) * r, 0, sin(ang) * r)
		q = Vector3(snappedf(q.x, 2.0), 0, snappedf(q.z, 2.0))
		if battle.placement_problem(team, k, q) == "": return q
	return p


func _run() -> void:
	get_tree().root.size = Vector2i(1280, 720)
	RenderingServer.global_shader_parameter_set("fog_on", 0.0)
	await _wait(0.3)
	for t in 2:
		battle.cash[t] = 90000
		var c: Vector3 = battle.start_pos[t]
		var f: float = -1.0 if t == 0 else 1.0
		for e in [["power_plant", Vector3(-45, 0, 10 * f)], ["barracks", Vector3(45, 0, 0)], ["supply_depot", Vector3(-50, 0, 45 * f)],
				["war_factory", Vector3(10, 0, 55 * f)], ["radar", Vector3(55, 0, 40 * f)], ["defense_tower", Vector3(-15, 0, 95 * f)]]:
			var k: String = e[0]
			battle.add_structure(k, t, _flat(t, k, c + Vector3(e[1].x * -f, 0, e[1].z)), true)
		var inf: Array = ["rifleman", "at4", "m240_gunner", "sniper", "special_forces", "medic"] if t == 0 else ["ir_rifleman", "ir_rpg", "ir_mg", "ir_sniper", "irgc_sf", "ir_medic", "ir_rifleman", "ir_rifleman"]
		for i in inf.size():
			var u: Unit = battle._spawn(inf[i], t, c + Vector3(-12 + (i % 4) * 3.5, 0, (70 + (i / 4) * 4.0) * f), 0.0 if t == 0 else PI)
			u.reset_physics_interpolation()
		var veh: Array = ["abrams", "bradley", "hmmwv_50cal"] if t == 0 else ["abrams", "m113", "mrap"]
		for i in veh.size():
			var u: Unit = battle._spawn(veh[i], t, c + Vector3(20 + i * 12.0, 0, 80 * f), 0.0 if t == 0 else PI)
			u.reset_physics_interpolation()
	# each side holds its home derrick
	for e in battle.derricks:
		if e.pos.distance_to(battle.start_pos[0]) < 200.0: e.owner = 0; battle._set_derrick_flag(e)
		elif e.pos.distance_to(battle.start_pos[1]) < 200.0: e.owner = 1; battle._set_derrick_flag(e)
	# a tank column drives down the central pass toward the basin
	var col: Array = []
	for i in 4:
		var u: Unit = battle._spawn("abrams", 0, Vector3(-6 + (i % 2) * 8, 0, 300 - i * 12), 0.0)
		u.reset_physics_interpolation(); col.append(u)
	battle.issue({"type": "move", "team": 0, "ids": col.map(func(u): return u.uid), "points": col.map(func(u): return u.position + Vector3(0, 0, -120))})
	await _wait(2.0)
	if "infonly" in battle.args:
		# a squad on open ground in the basin, facing the camera
		var cc: Vector3 = battle.grounded(Vector3(60, 0, -150))
		var kinds := ["ir_rifleman", "ir_rpg", "ir_mg", "irgc_sf", "ir_sniper", "ir_medic", "ir_engineer", "ir_rifleman", "ir_rifleman", "irgc_sf"]
		for i in kinds.size():
			var u: Unit = battle._spawn(kinds[i], 1, cc + Vector3(-8 + (i % 5) * 4.0, 0, -2 + (i / 5) * 4.0), deg_to_rad(-20.0))
			u.reset_physics_interpolation()
		await _wait(1.0)
		_cam(cc, 26.0, 200.0, 34.0); await _shot("zb_iran_infantry")
		_cam(cc, 16.0, 160.0, 28.0); await _shot("zb_iran_infantry_close")
		get_tree().quit()
		return
	var a: Vector3 = battle.start_pos[0]; var b: Vector3 = battle.start_pos[1]
	_cam(a + Vector3(0, 0, -45), 150.0, 0.0, 52.0); await _shot("zb_base_usa")
	_cam(a + Vector3(0, 0, -70), 70.0, 20.0, 40.0); await _shot("zb_base_usa_close")
	_cam(b + Vector3(0, 0, 45), 150.0, 180.0, 52.0); await _shot("zb_base_iran")
	var irinf: Array = battle.units.filter(func(u): return u.team == 1 and u.def.get("visual") == "infantry")
	var cen := Vector3.ZERO
	for u in irinf: cen += u.position
	cen /= maxf(irinf.size(), 1)
	_cam(cen, 26.0, 200.0, 34.0); await _shot("zb_iran_infantry")
	var irveh: Array = battle.units.filter(func(u): return u.team == 1 and u.kind in ["abrams", "m113", "mrap"])
	if not irveh.is_empty():
		_cam(irveh[1].position, 45.0, 160.0, 42.0); await _shot("zb_iran_vehicles")
	await _wait(6.0)
	_cam(col[0].position + Vector3(0, 0, 10), 80.0, 30.0, 45.0); await _shot("zb_tanks_on_slope")
	_cam(Vector3(0, 0, 0), 230.0, 0.0, 55.0); await _shot("zb_centre")
	_cam(Vector3(0, 0, 150), 230.0, 35.0, 40.0); await _shot("zb_ridges_low")
	_cam(Vector3(0, 0, 0), 300.0, 0.0, 75.0); await _shot("zb_overview")
	for e in battle.derricks:
		if e.owner == 1:
			_cam(e.pos, 40.0, 210.0, 40.0); await _shot("zb_derrick_iran")
		elif e.owner == 0:
			_cam(e.pos, 40.0, 30.0, 40.0); await _shot("zb_derrick_usa")
	get_tree().quit()

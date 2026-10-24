# Steel Accord - rendered RTS-camera review of a heightfield map (run with: -- mapshots map=zagros_basin nation1=iran
# noai out=/dir). Builds a small base for each side on the terrain, spawns U.S. and Iranian infantry and vehicles,
# captures a derrick for each side and takes screenshots. Not part of gameplay.
extends Node

var battle: Node
var out := "user://test_output/sa_mapshots"


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
	if "terrainfast" in battle.args:
		# terrain-only iteration: no bases / units, straight to the terrainonly cameras (only=<prefix> picks views)
		await _terrain_views()
		get_tree().quit()
		return
	if "b2shots" in battle.args:
		await _b2_shots()
		get_tree().quit()
		return
	if "b3shots" in battle.args:
		await _b3_shots()
		get_tree().quit()
		return
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
		var veh: Array = ["abrams", "bradley", "hmmwv_50cal"] if t == 0 else ["ir_karrar", "ir_bmp2", "ir_boragh"]
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
	if "uiiran" in battle.args:
		await _ui_iran()
		get_tree().quit()
		return
	if "ironly" in battle.args:
		# Iranian vehicles and aircraft lined up on open ground for close review
		var o: Vector3 = battle.grounded(Vector3(60, 0, -150))
		var vk := ["ir_karrar", "ir_t72s", "ir_bmp2", "ir_boragh", "ir_engineer_dozer"]
		for i in vk.size():
			var u: Unit = battle._spawn(vk[i], 1, o + Vector3(-24 + i * 12.0, 0, 0), deg_to_rad(-20.0))
			u.reset_physics_interpolation()
		var ak := ["ir_f14", "ir_f4", "ir_su24"]
		for i in ak.size():
			var u: Unit = battle._spawn(ak[i], 1, o + Vector3(-20 + i * 20.0, 0, -30), deg_to_rad(-20.0))
			u.state = Unit.S.LANDED; u.altitude = u.ground_alt(); u.airborne = false; u.speed_cur = 0.0
			u.reset_physics_interpolation()
		var hk := ["ir_ah1j", "ir_ch47"]
		for i in hk.size():
			var u: Unit = battle._spawn(hk[i], 1, o + Vector3(-12 + i * 24.0, 0, -58), deg_to_rad(-20.0))
			u.state = Unit.S.LANDED; u.altitude = u.ground_alt()
			u.reset_physics_interpolation()
		await _wait(1.0)
		_cam(o + Vector3(0, 0, -2), 46.0, 160.0, 34.0); await _shot("zb_iran_vehicles_close")
		_cam(o + Vector3(0, 0, -40), 70.0, 160.0, 40.0); await _shot("zb_iran_aircraft")
		_cam(o + Vector3(0, 0, -25), 120.0, 160.0, 52.0); await _shot("zb_iran_arsenal_rts")
		battle.power_ready[1]["shahed"] = 0.0
		battle.launch_power(1, "shahed", o + Vector3(0, 0, 60))
		await _wait(9.0)
		if not battle.drones.is_empty():
			_cam(battle.drones[0].pos, 40.0, 30.0, 35.0); await _shot("zb_shahed_inbound")
		get_tree().quit()
		return
	if "terrainonly" in battle.args:
		# fixed terrain-texturing review views (tiling / repetition check); same cameras every run
		await _terrain_views()
		get_tree().quit()
		return
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


## Fixed terrain-texturing review cameras (tiling / repetition check), shared by "terrainonly" and "terrainfast".
func _terrain_views() -> void:
	var only := str(battle.args.get("only", ""))
	var views := [["tr_1_basin_mid", Vector3(60, 0, -150), 120.0, 160.0, 45.0], ["tr_2_centre_far", Vector3(0, 0, 0), 230.0, 0.0, 55.0],
		["tr_3_ridges_low", Vector3(0, 0, 150), 230.0, 35.0, 40.0], ["tr_4_basin_close", Vector3(-218, 0, -45), 65.0, 300.0, 38.0],
		["tr_5_steep_top", Vector3(-300, 0, 120), 180.0, 120.0, 70.0]]
	for v in views:
		if only != "" and not (v[0] as String).begins_with(only): continue
		_cam(battle.grounded(v[1]), v[2], v[3], v[4]); await _shot(v[0])


## UI review with the player as Iran: inspector + command card for a soldier, tank, tactical vehicle, aircraft and the
## main structures (run with nation0=iran; resolution from --resolution).
func _ui_iran() -> void:
	var tag := str(battle.args.get("tag", "1080"))
	# exact capture size from res=WxH (the shot scripts otherwise force 1280x720)
	var rs: PackedStringArray = str(battle.args.get("res", "1920x1080")).split("x")
	var want := Vector2i(int(rs[0]), int(rs[1]))
	DisplayServer.window_set_size(want)
	get_tree().root.size = want
	await _wait(0.3)
	printerr("UI capture size ", get_viewport().get_visible_rect().size, " hud scale ", battle.hud.ui_scale)
	var c: Vector3 = battle.start_pos[0]
	var f := -1.0
	battle.cash[0] = 60000
	var blds := {}
	for e in [["power_plant", Vector3(-45, 0, 10)], ["power_plant", Vector3(-45, 0, 40)], ["barracks", Vector3(45, 0, 0)], ["supply_depot", Vector3(-50, 0, -40)],
			["war_factory", Vector3(10, 0, -55)], ["airfield", Vector3(110, 0, -40)]]:
		var k: String = e[0]
		blds[k] = battle.add_structure(k, 0, _flat(0, k, c + Vector3(e[1].x, 0, e[1].z * f * -1.0)), true)
	await _wait(0.5)
	var af: Building = blds.airfield
	battle.spawn_produced(af, "ir_f14"); battle.spawn_produced(af, "ir_ah1j")
	var sol: Unit = battle._spawn("irgc_sf", 0, c + Vector3(-10, 0, -70), 0.0)
	var tank: Unit = battle._spawn("ir_karrar", 0, c + Vector3(5, 0, -75), 0.0)
	var apc: Unit = battle._spawn("ir_boragh", 0, c + Vector3(20, 0, -75), 0.0)
	tank.take_damage(260.0, null)
	var foe: Unit = battle._spawn("rifleman", 1, c + Vector3(5, 0, -110), PI)
	tank.add_xp(120.0)
	battle.issue({"type": "produce", "team": 0, "id": blds.war_factory.uid, "kind": "ir_karrar"})
	battle.issue({"type": "produce", "team": 0, "id": blds.war_factory.uid, "kind": "ir_bmp2"})
	battle.issue({"type": "produce", "team": 0, "id": blds.barracks.uid, "kind": "ir_rifleman"})
	battle.issue({"type": "research", "team": 0, "id": blds.war_factory.uid, "upgrade": "composite_armor"})
	await _wait(2.0)
	var cmd: Commander = battle.commander
	cmd._set_selection([sol]); cmd.assign_group(1)
	cmd._set_selection([tank, apc]); cmd.assign_group(2)
	var shots := [["soldier", [sol], null], ["karrar", [tank], null], ["boragh", [apc], null], ["f14", battle.units.filter(func(u): return u.kind == "ir_f14").slice(0, 1), null],
		["group", [sol, tank, apc], null], ["warfactory", [], blds.war_factory], ["airfield", [], af], ["barracks", [], blds.barracks],
		["cc", [], battle.structures(0, "command_center")[0]]]
	for sh in shots:
		cmd._set_selection(sh[1]); cmd.sel_building = sh[2]
		var focus: Vector3 = sh[2].position if sh[2] else (sh[1][0].position if not sh[1].is_empty() else c)
		_cam(focus, 70.0, 0.0, 52.0)
		await _wait(0.5)
		await _shot("ui_%s_%s" % [tag, sh[0]])
	# the Details panel (full inspector text) opened over the War Factory
	cmd._set_selection([]); cmd.sel_building = blds.war_factory
	battle.hud.details_open = true
	await _wait(0.5)
	await _shot("ui_%s_warfactory_details" % tag)
	battle.hud.details_open = false
	foe.take_damage(9999.0, null)


## B3 world evidence + frame-time measurement (run with res=1920x1080; "perfonly" skips the PNGs): basin overview,
## town with roads, industrial zone, tunnel portal with the train, minimap. Each view: mean / p95 frame time over 12
## rendered frames, draw calls and primitives, printed as "PERF <view> ...". Camera views are fixed so a run on the
## B2 map data (map=<old copy>) is directly comparable. (12 frames per view: Xvfb renders in software on a shared CPU.)
func _b3_shots() -> void:
	var rs: PackedStringArray = str(battle.args.get("res", "1920x1080")).split("x")
	var want := Vector2i(int(rs[0]), int(rs[1]))
	DisplayServer.window_set_size(want)
	get_tree().root.size = want
	Engine.max_fps = 0
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	battle.hud.visible = false
	var shots_on: bool = not ("perfonly" in battle.args)
	var z: Dictionary = battle.terrain.data.get("zones", {})
	var portal: Vector3 = battle.map_point(z.get("portal_a_east", [166.0, 294.0]))
	var views := [["b3_overview", Vector3(40, 0, 80), 300.0, 0.0, 70.0], ["b3_town", Vector3(-275, 0, 305), 125.0, 0.0, 50.0],
		["b3_industry_portal_train", portal + Vector3(30, 0, -40), 110.0, 200.0, 45.0]]
	await _wait(1.0)
	for v in views:
		_cam(battle.grounded(v[1]), v[2], v[3], v[4])
		await _wait(0.4)
		printerr("VIEW ", v[0])
		for i in 2: await get_tree().process_frame
		var ft: Array = []
		var t_prev := Time.get_ticks_usec()
		for i in 12:
			await get_tree().process_frame
			var t := Time.get_ticks_usec()
			ft.append((t - t_prev) / 1000.0); t_prev = t
		ft.sort()
		var mean := 0.0
		for f in ft: mean += f
		mean /= ft.size()
		printerr("PERF %s mean_ms %.2f p95_ms %.2f fps %.1f draw_calls %d objects %d primitives %d" % [v[0], mean, ft[int(ft.size() * 0.95)], 1000.0 / mean,
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)])
		if shots_on: await _shot(v[0])
	if shots_on:
		# minimap: the generated texture (upscaled for review) and an in-game frame with the HUD
		var img: Image = battle.make_minimap_texture().get_image()
		img.resize(768, 768, Image.INTERPOLATE_NEAREST)
		img.save_png("%s/b3_minimap.png" % out)
		battle.hud.visible = true
		_cam(battle.grounded(Vector3(-275, 0, 305)), 125.0, 0.0, 50.0)
		await _wait(0.5)
		await _shot("b3_hud_minimap")


## B2 evidence (run with res=WxH): the village with civilian buildings, an occupied house (badge + command grid),
## occupants firing at an enemy, the hospital healing, a jet taxiing on the taxiway, a helicopter over a ridge.
func _b2_shots() -> void:
	var rs: PackedStringArray = str(battle.args.get("res", "1920x1080")).split("x")
	var want := Vector2i(int(rs[0]), int(rs[1]))
	DisplayServer.window_set_size(want)
	get_tree().root.size = want
	battle.cash[0] = 90000
	var cmd: Commander = battle.commander
	var civ: Array = battle.units.filter(func(u): return u is Building and (u as Building).is_civic() and not u.dead)
	var vil := Vector3(-237, 0, 297)
	_cam(vil, 120.0, 0.0, 52.0)
	await _wait(0.6)
	await _shot("b2_village")
	var houses: Array = civ.filter(func(u): return u.bkind.begins_with("civ_house"))
	houses.sort_custom(func(a, b): return a.position.distance_to(vil) < b.position.distance_to(vil))
	var house: Building = houses[0]
	var sq: Array = []
	for i in 4:
		sq.append(battle._spawn("rifleman", 0, house.door_pos + Vector3(-5 + i * 3.5, 0, 8), 0.0))
	await _wait(0.2)
	battle.issue({"type": "board", "team": 0, "ids": sq.map(func(u): return u.uid), "target": house.uid})
	var t_end: float = battle.sim_time + 40.0
	while battle.sim_time < t_end and house.passengers.size() < 4: await _wait(0.5)
	cmd._set_selection([]); cmd.sel_building = house
	_cam(house.position, 70.0, 0.0, 50.0)
	await _wait(0.6)
	await _shot("b2_garrison_selected")
	for i in 3:
		var e: Unit = battle._spawn("rifleman", 1, house.position + Vector3(30 + i * 4, 0, -30), PI)
		battle.issue({"type": "attack_move", "team": 1, "ids": [e.uid], "points": [house.position]})
	await _wait(3.0)
	_cam(house.position + Vector3(15, 0, -12), 75.0, 0.0, 48.0)
	await _shot("b2_garrison_firing")
	await _wait(6.0)
	await _shot("b2_garrison_after")
	var hosp: Array = civ.filter(func(u): return u.bkind == "civ_hospital")
	if not hosp.is_empty():
		var hs: Building = hosp[0]
		var pats: Array = []
		for i in 3:
			var pu: Unit = battle._spawn("rifleman", 0, hs.door_pos + Vector3(-4 + i * 4, 0, 6), 0.0)
			pu.hp = pu.def.hp * 0.3; pats.append(pu)
		battle.issue({"type": "board", "team": 0, "ids": pats.map(func(u): return u.uid), "target": hs.uid})
		t_end = battle.sim_time + 40.0
		while battle.sim_time < t_end and hs.passengers.size() < 3: await _wait(0.5)
		cmd._set_selection([]); cmd.sel_building = hs
		_cam(hs.position, 85.0, 0.0, 52.0)
		await _wait(1.0)
		await _shot("b2_hospital")
	# airfield taxi: a jet leaves its pad along the taxiway (never through the hangar)
	var c0: Vector3 = battle.start_pos[0]
	var af: Building = battle.add_structure("airfield", 0, _flat(0, "airfield", c0 + Vector3(-140, 0, -60)), true)
	await _wait(0.3)
	battle.spawn_produced(af, "f16")
	await _wait(0.3)
	var jet: Array = battle.units.filter(func(u): return u.kind == "f16" and not u.dead)
	if not jet.is_empty():
		battle.issue({"type": "move", "team": 0, "ids": [jet[0].uid], "points": [c0 + Vector3(0, 0, -400)]})
		cmd._set_selection([jet[0]])
		_cam(af.position, 80.0, 0.0, 55.0)
		await _wait(3.0)
		await _shot("b2_taxi_1")
		await _wait(3.5)
		await _shot("b2_taxi_2")
		await _wait(3.5)
		await _shot("b2_taxi_3")

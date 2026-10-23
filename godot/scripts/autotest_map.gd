# Steel Accord - acceptance test for heightfield maps (default: Zagros Basin).
# Run: godot --path godot --fixed-fps 30 -- maptest map=zagros_basin out=/dir   (headless for checks; rendered for shots)
# Checks: the map loads; terrain, structures, units and props are grounded (no floating / sinking); every movement
# class has a route between the starts while cliffs stay blocked; both starts have comparable resources; steep
# placement is rejected and flat placement flattens and grounds the structure; derricks capture, change owner and pay;
# CH-47 supply delivery updates the economy. Writes result.txt and RTS-camera screenshots when rendering.
extends "res://scripts/autotest_base.gd"


func _run() -> void:
	await _wait_sim(0.5)
	var tm: TerrainMap = battle.terrain
	_log("map_loads", tm != null and battle.map_id == battle.args.get("map", "zagros_basin"),
		"map=%s samples=%d step=%.1f half=%.0f playable=%.0f" % [battle.map_id, tm.n if tm else 0, tm.step if tm else 0.0, tm.half_size() if tm else 0.0, battle.MAP_HALF])
	if tm == null:
		_finish(); return
	var a: Vector3 = battle.start_pos[0]; var b: Vector3 = battle.start_pos[1]
	_log("starts_from_map", a.distance_to(b) > 300.0, "A=%s B=%s" % [str(a), str(b)])

	# ---- grounding: everything stands on the terrain
	var worst := 0.0; var worst_name := ""
	for u in battle.units:
		var d := absf(u.position.y - battle.ground_h(u.position.x, u.position.z))
		if u is Building:
			var st := tm.footprint_stats(u.position, u.half)
			d = absf(u.position.y - st.z) + st.x * 0.0
		if d > worst: worst = d; worst_name = u.kind
	_log("units_grounded", worst < 0.25, "max |y - ground| = %.3f m (%s)" % [worst, worst_name])
	var flat_bad := 0
	for bld in battle.structures(0) + battle.structures(1):
		var st := tm.footprint_stats(bld.position, bld.half)
		if st.x > 0.6: flat_bad += 1
	_log("structures_on_flattened_ground", flat_bad == 0, "structures with >0.6 m height range under the footprint: %d" % flat_bad)
	var pworst := 0.0; var pn: int = battle.prop_roots.size()
	for o: Vector3 in battle.prop_roots:
		pworst = maxf(pworst, absf(o.y - battle.ground_h(o.x, o.z)))
	_log("props_grounded", pn > 100 and pworst < 0.05, "%d props, max |root y - ground| = %.3f m (each prop's pivot is its ground contact)" % [pn, pworst])
	var pile_bad := 0
	for pl in battle.piles:
		if absf(pl.node.position.y - battle.ground_h(pl.pos.x, pl.pos.z)) > 0.3: pile_bad += 1
	for e in battle.derricks:
		if absf(e.node.position.y - battle.ground_h(e.pos.x, e.pos.z)) > 0.3: pile_bad += 1
	_log("sites_grounded", pile_bad == 0, "piles=%d derricks=%d off-ground=%d" % [battle.piles.size(), battle.derricks.size(), pile_bad])

	# ---- routes: each class can cross the map; cliffs are blocked
	var route_txt := []
	var routes_ok := true
	for cls in ["infantry", "wheeled", "tracked"]:
		var g: GridNav = battle.navs[cls]
		var path: PackedVector3Array = battle.find_path(a + Vector3(0, 0, -40), b + Vector3(0, 0, 40), cls)
		var end_ok := path.size() >= 2 and Vector2(path[path.size() - 1].x - b.x, path[path.size() - 1].z - (b.z + 40)).length() < 6.0
		var clear := true
		for i in path.size() - 1:
			if not g.line_clear(path[i], path[i + 1]): clear = false
		var L := 0.0
		for i in path.size() - 1: L += Vector2(path[i + 1].x - path[i].x, path[i + 1].z - path[i].z).length()
		routes_ok = routes_ok and end_ok and clear
		route_txt.append("%s %s %.0f m (%d legs, %d steep cells)" % [cls, "OK" if end_ok and clear else "NO", L, path.size() - 1, g.slope_cells])
	_log("routes_passable", routes_ok, "; ".join(route_txt))
	# cliff cells: steeper than the tracked limit must be solid for wheels and tracks; infantry limit is higher
	var steep_found := 0; var steep_open := 0
	var gw: GridNav = battle.navs.wheeled
	var r_t: float = float(battle.move_rules.get("tracked", {}).get("max_slope_deg", 28.0))
	for i in 4000:
		var x := -500.0 + float((i * 38) % 1000); var z := -500.0 + float((i * 92) % 1000)   # on the 2 m sample grid
		var s := tm.max_slope_in(x, z, 0.0)
		if s > r_t + 4.0:
			steep_found += 1
			if not battle.navs.tracked.blocked_at(Vector3(x, 0, z)) or not gw.blocked_at(Vector3(x, 0, z)): steep_open += 1
	_log("cliffs_block", steep_found > 20 and steep_open == 0, "%d sampled cliff points steeper than %.0f°, open for vehicles: %d" % [steep_found, r_t + 4.0, steep_open])
	var w_s: int = battle.navs.wheeled.slope_cells; var t_s: int = battle.navs.tracked.slope_cells; var i_s: int = battle.navs.infantry.slope_cells
	_log("class_slope_rules", w_s > t_s and t_s > i_s, "impassable cells: wheeled %d > tracked %d > infantry %d" % [w_s, t_s, i_s])

	# ---- fairness: resources per start (path cost to own sites, equal amounts)
	var own := [[], []]
	for pl in battle.piles:
		var t := 0 if pl.pos.distance_to(a) < pl.pos.distance_to(b) else 1
		if minf(pl.pos.distance_to(a), pl.pos.distance_to(b)) < 220.0: own[t].append(pl)
	var cash_a := 0; var cash_b := 0
	for pl in own[0]: cash_a += int(pl.cash)
	for pl in own[1]: cash_b += int(pl.cash)
	# measured from the Command Center's front (map-centre side), as the haulers and dozers leave it
	var fa: Vector3 = a + (b - a).normalized() * 24.0; var fb: Vector3 = b + (a - b).normalized() * 24.0
	var dist_a := 0.0; var dist_b := 0.0
	var parts := []
	for cls in ["infantry", "wheeled", "tracked"]:
		var ca := 0.0; var cb := 0.0
		for pl in own[0]: ca += battle.navs[cls].path_cost(fa, pl.pos)
		for pl in own[1]: cb += battle.navs[cls].path_cost(fb, pl.pos)
		for e in battle.derricks:
			if e.pos.distance_to(a) < 200.0: ca += battle.navs[cls].path_cost(fa, e.pos)
			elif e.pos.distance_to(b) < 200.0: cb += battle.navs[cls].path_cost(fb, e.pos)
		parts.append("%s %.0f/%.0f" % [cls, ca, cb])
		dist_a += ca; dist_b += cb
	var der := [0, 0]
	for e in battle.derricks:
		if e.pos.distance_to(a) < 200.0: der[0] += 1
		elif e.pos.distance_to(b) < 200.0: der[1] += 1
	var dd := absf(dist_a - dist_b) / maxf(dist_a, 1.0)
	_log("starts_fair", cash_a == cash_b and own[0].size() == own[1].size() and der[0] == der[1] and dd < 0.05,
		"near A: %d piles $%d, %d derricks | near B: %d piles $%d, %d derricks | A* travel cost A/B to own sites: %s (total diff %.1f%%)" % [
		own[0].size(), cash_a, der[0], own[1].size(), cash_b, der[1], ", ".join(parts), dd * 100.0])

	# ---- placement on slopes
	var steep_p := Vector3.INF
	for i in 3000:
		var x := a.x + float((i * 53) % 280) - 140.0; var z := a.z + float((i * 29) % 280) - 140.0
		var st := tm.footprint_stats(Vector3(x, 0, z), Vector2(9, 8))
		if st.y > battle.build_max_slope + 3.0 and battle.map_bounds.grow(-20).has_point(Vector2(x, z)):
			steep_p = Vector3(x, 0, z); break
	battle.cash[0] += 30000
	var why: String = battle.placement_problem(0, "power_plant", steep_p) if steep_p != Vector3.INF else "no steep spot near base"
	_log("steep_placement_rejected", why.begins_with("Ground too steep"), "%s -> %s" % [str(steep_p), why])
	var cc: Building = battle.structures(0, "command_center")[0]
	var fwd := (Vector3.ZERO - a).normalized()
	var pp := await _place("power_plant", _flat_spot(cc.position + fwd * 45.0 + Vector3(-40, 0, 0), "power_plant"))
	await _until(func(): return pp != null and pp.built, 40.0)
	var pst := tm.footprint_stats(pp.position, pp.half) if pp else Vector3.ONE * 99
	_log("flat_placement_grounded", pp != null and pp.built and pst.x < 0.3 and absf(pp.position.y - pst.z) < 0.15,
		"built=%s y=%.2f footprint range=%.2f m" % [str(pp != null and pp.built), pp.position.y if pp else -1.0, pst.x])

	# ---- oil derricks: capture, ownership change, recurring income
	var ders: Array = battle.derricks.duplicate()
	ders.sort_custom(func(p, q): return p.pos.distance_to(a) < q.pos.distance_to(a))
	var dk: Dictionary = ders[0]
	var squad: Array = []
	for i in 2: squad.append(battle._spawn("rifleman", 0, dk.pos + Vector3(-15 - i * 2, 0, 0), 0.0))
	battle.issue({"type": "move", "team": 0, "ids": squad.map(func(u): return u.uid), "points": [dk.pos + Vector3(-5, 0, 3), dk.pos + Vector3(-5, 0, -3)]})
	var t0: float = battle.sim_time
	var got := await _until(func(): return dk.owner == 0, 30.0)
	_log("derrick_capture", got, "owner=%d after %.1f s (capture time %.0f s)" % [dk.owner, battle.sim_time - t0, dk.capture_s])
	var c0: int = battle.cash[0]
	await _wait_sim(dk.every + 0.6)
	_log("derrick_income", battle.cash[0] - c0 >= dk.income and battle.derrick_income[0] >= dk.income, "cash %+d in %.0f s, derrick income total $%d" % [battle.cash[0] - c0, dk.every + 0.6, battle.derrick_income[0]])
	if DisplayServer.get_name() != "headless":
		_cam(dk.pos, 60.0, 30.0, 45.0); await _wait_sim(0.5); await _shot("derrick_captured")
	for u in squad: u.take_damage(9999.0, null)
	var foes: Array = []
	for i in 2: foes.append(battle._spawn("rifleman", 1, dk.pos + Vector3(4, 0, 4 + i * 2), 0.0))
	if battle.base_ai: battle.base_ai.capturing["_test"] = foes.map(func(u): return u.uid)   # keep the AI from re-tasking them
	var flipped := await _until(func(): return dk.owner == 1, 30.0)
	_log("derrick_changes_owner", flipped, "owner=%d" % dk.owner)
	for u in foes: u.take_damage(9999.0, null)

	# ---- supply delivery updates the economy (CH-47 from a Supply Depot on this map)
	var sd := await _place("supply_depot", _flat_spot(cc.position + fwd * 40.0 + Vector3(45, 0, 0), "supply_depot"))
	await _until(func(): return sd != null and sd.built, 50.0)
	var inc0: int = battle.income[0] - battle.derrick_income[0]
	var delivered := await _until(func(): return battle.income[0] - battle.derrick_income[0] > inc0, 120.0)
	_log("supply_delivery", sd != null and delivered, "hauled income %d -> %d" % [inc0, battle.income[0] - battle.derrick_income[0]])

	# ---- a vehicle drives across terrain and stays on it
	var tank: Unit = battle._spawn("abrams", 0, cc.position + fwd * 30.0, 0.0)
	var goal: Vector3 = battle.grounded(cc.position + fwd * 240.0)
	battle.issue({"type": "move", "team": 0, "ids": [tank.uid], "points": [goal]})
	var max_off := 0.0
	var tend: float = battle.sim_time + 60.0
	while battle.sim_time < tend and tank.flat_dist(goal) > 6.0:
		await _wait_sim(0.5)
		max_off = maxf(max_off, absf(tank.position.y - battle.ground_h(tank.position.x, tank.position.z)))
	_log("vehicle_drives_on_terrain", tank.flat_dist(goal) < 8.0 and max_off < 0.05, "dist to goal %.1f m, max off-ground %.3f m, tilt %.1f°/%.1f°" % [
		tank.flat_dist(goal), max_off, rad_to_deg(tank.body.rotation.x), rad_to_deg(tank.body.rotation.z)])
	# ---- aircraft cross the ridges between the bases without touching the terrain
	var heli: Unit = battle._spawn("ah64", 0, cc.position + fwd * 20.0, 0.0)
	var jet: Unit = battle._spawn("f16", 0, cc.position + fwd * 40.0, 0.0)
	jet.airborne = true; jet.altitude = float(jet.def.altitude); jet.speed_cur = float(jet.def.speed); jet.body.position.y = jet.altitude
	heli.altitude = float(heli.def.altitude); heli.body.position.y = heli.altitude
	var far_goal: Vector3 = battle.start_pos[1]
	battle.issue({"type": "move", "team": 0, "ids": [heli.uid, jet.uid], "points": [far_goal, far_goal]})
	var min_clear := {"ah64": INF, "f16": INF}
	var peak := 0.0
	var tfly: float = battle.sim_time + 70.0
	while battle.sim_time < tfly and heli.flat_dist(far_goal) > 30.0:
		await _wait_sim(0.2)
		for u in [heli, jet]:
			if u.dead or u.altitude < float(u.def.altitude) * 0.7: continue
			var g: float = battle.ground_h(u.position.x, u.position.z)
			peak = maxf(peak, g)
			min_clear[u.kind] = minf(min_clear[u.kind], u.position.y + u.altitude - g)
	_log("aircraft_clear_terrain", min_clear.ah64 > 4.0 and min_clear.f16 > 4.0 and peak > 20.0,
		"lowest clearance above the ground: AH-64 %.1f m, F-16 %.1f m (highest ground overflown %.0f m)" % [min_clear.ah64, min_clear.f16, peak])
	heli.take_damage(99999.0, null); jet.take_damage(99999.0, null)
	# ---- the computer opponent plays the map: builds on flat ground, earns, captures a derrick, trains its nation's units
	if battle.base_ai:
		await _until(func(): return battle.sim_time > 420.0, 600.0)
		var ab: Array = battle.structures(1)
		var ab_bad := 0
		for x in ab:
			if tm.footprint_stats(x.position, x.half).x > 0.6 or absf(x.position.y - tm.footprint_stats(x.position, x.half).z) > 0.2: ab_bad += 1
		_log("ai_builds_on_terrain", ab.size() >= 5 and ab_bad == 0, "AI structures %d (%s), ungrounded %d, income $%d" % [ab.size(),
			", ".join(ab.map(func(x): return x.bkind)), ab_bad, battle.income[1]])
		var owned: int = battle.derricks.filter(func(e): return e.owner == 1).size()
		_log("ai_captures_derrick", owned >= 1, "derricks owned by AI: %d, derrick income $%d" % [owned, battle.derrick_income[1]])
		var nat: String = battle.nation_of(1)
		var mine: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead and u.def.get("visual") == "infantry")
		var kinds := {}
		for u in mine: kinds[u.kind] = true
		var ok_nat := not mine.is_empty() and mine.all(func(u): return nat != "iran" or u.kind.begins_with("ir"))
		var groom := {}
		for u in mine:
			if u.has_meta("grooming"): groom[u.get_meta("grooming")] = int(groom.get(u.get_meta("grooming"), 0)) + 1
		_log("ai_nation_roster", ok_nat, "nation %s infantry kinds %s grooming %s" % [nat, str(kinds.keys()), str(groom)])
		if nat == "iran":
			battle.cry_t[1] = -99.0      # the AI may have just shouted; start this check from a ready cooldown
			var cry0: int = battle.cries
			var p0: Vector3 = battle.grounded(Vector3(250, 0, 120))
			var us_r: Unit = battle._spawn("rifleman", 0, p0, 0.0)
			var ir_r: Unit = battle._spawn("ir_rifleman", 1, p0 + Vector3(0, 0, -25), PI)
			await _wait_sim(4.0)
			_log("iran_battle_cry", battle.cries > cry0, "battle cries %d -> %d (clip iran_shout, 14 s per-team cooldown)" % [cry0, battle.cries])
			for u in [us_r, ir_r]:
				if not u.dead: u.take_damage(9999.0, null)
			# Iranian support powers: Shahed drone strike and paratroopers from an Iranian C-130
			var tgt: Vector3 = battle.grounded(Vector3(-150, 0, 200))
			var victims: Array = []
			for i in 3: victims.append(battle._spawn("hmmwv_50cal", 0, tgt + Vector3(i * 6 - 6, 0, 0), 0.0))
			battle.power_ready[1]["shahed"] = 0.0
			var h0: int = battle.drone_hits
			battle.launch_power(1, "shahed", tgt)
			await _until(func(): return battle.drones.is_empty() and battle.drone_hits > h0, 60.0)
			var dmg_done: bool = victims.any(func(v): return v.dead or v.hp < v.def.hp)
			_log("iran_shahed_strike", battle.drone_hits - h0 == int(UnitDefs.POWERS.shahed.drones) and dmg_done,
				"drones hit %d, targets damaged=%s; impacts %s vs target %s; US-only powers refused for Iran: '%s'" % [battle.drone_hits - h0, str(dmg_done),
				str(battle.bomb_log.slice(-4).map(func(q): return Vector2i(int(q.x), int(q.z)))), str(Vector2i(int(tgt.x), int(tgt.z))), battle.power_problem(1, "carpet")])
			for v in victims:
				if not v.dead: v.take_damage(99999.0, null)
			var air_ir: Array = Nations.produces("iran", "airfield", [])
			var wf_ir: Array = Nations.produces("iran", "war_factory", [])
			var all_ok := true
			for k in air_ir + wf_ir + ["ir_ch47", "ir_engineer_dozer"]:
				var d: Dictionary = UnitDefs.def_of(k)
				if not (str(d.get("model3d", "")).contains("/ir_") or Nations.is_placeholder("iran", k)): all_ok = false
				if not ResourceLoader.exists(str(d.get("model3d", ""))): all_ok = false
			var dz: Array = battle.units.filter(func(u): return u.team == 1 and u.def.get("builder", false))
			_log("iran_roster_models", all_ok and not dz.is_empty() and dz[0].kind == "ir_engineer_dozer" and battle.c130_model(1).contains("ir_c130"),
				"airfield %s; war factory %s; builder %s; C-130 %s" % [str(air_ir), str(wf_ir), dz[0].kind if not dz.is_empty() else "none", battle.c130_model(1)])
		var flag: Node = battle.get_node_or_null("Flag_team1")
		_log("nation_flag", flag != null, "team 1 flag: %s" % (str(flag.scene_file_path) if flag else "none"))
	if DisplayServer.get_name() != "headless":
		await _shots()
	_finish()


func _path_len(from: Vector3, to: Vector3, cls: String) -> float:
	var p: PackedVector3Array = battle.find_path(from, to, cls)
	var L := 0.0
	for i in p.size() - 1: L += Vector2(p[i + 1].x - p[i].x, p[i + 1].z - p[i].z).length()
	return L


## Nearest spot to `p` where the structure may be placed (spiral search).
func _flat_spot(p: Vector3, k: String) -> Vector3:
	for i in 200:
		var r := 4.0 * sqrt(float(i)); var ang := float(i) * 2.4
		var q: Vector3 = p + Vector3(cos(ang) * r, 0, sin(ang) * r)
		q = Vector3(snappedf(q.x, 2.0), 0, snappedf(q.z, 2.0))
		if battle.placement_problem(0, k, q) == "": return q
	return p


func _cam(p: Vector3, zoom: float, yaw_deg: float, pitch: float) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam.yaw = deg_to_rad(yaw_deg); cam.pitch_deg = pitch
	cam._apply(); cam.focus(p)


## RTS-camera screenshots of the map (rendered runs only).
func _shots() -> void:
	battle.hud.visible = true
	var a: Vector3 = battle.start_pos[0]; var b: Vector3 = battle.start_pos[1]
	var views := [["base_a", a + (b - a).normalized() * 30.0, 150.0, 0.0, 52.0], ["base_a_low", a + (b - a).normalized() * 40.0, 110.0, 25.0, 38.0],
		["centre", Vector3.ZERO, 230.0, 0.0, 55.0], ["centre_close", Vector3(20, 0, 20), 120.0, 35.0, 42.0],
		["base_b", b + (a - b).normalized() * 30.0, 150.0, 180.0, 52.0], ["overview", Vector3.ZERO, 300.0, 0.0, 75.0]]
	for v in views:
		_cam(v[1], v[2], v[3], v[4])
		await _wait_sim(0.4)
		await _shot("map_" + v[0])
	for e in battle.derricks:
		_cam(e.pos, 55.0, 30.0, 45.0); await _wait_sim(0.3); await _shot("map_derrick_" + str(e.id))
		break

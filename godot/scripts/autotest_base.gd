# Steel Accord - B1.2 base-loop playtest. Drives the player side through the real input pipeline (mouse clicks on
# the HUD and the map) and checks: placement rules, dozer construction, power, supply hauling income, production
# queues, rally, cancel / sell refunds, combat roles, and that the AI opponent builds, earns, produces and attacks.
# Run: godot --headless --path godot --fixed-fps 30 -- basetest aifast out=/dir
extends "res://scripts/autotest.gd"


func _dozer() -> Unit:
	var d := _team(["dozer"])
	return d[0] if not d.is_empty() else null


func _sel(arr: Array) -> void:
	battle.commander._set_selection(arr)
	await _frames(2)


## Place a structure the way a player does: select the dozer, press the build button, click the map.
func _place(k: String, at: Vector3) -> Building:
	var dz := _dozer()
	battle.camera.focus(at)
	await _frames(2)
	await _sel([dz])
	await _frames(2)
	var btn: Button = battle.hud.econ.buttons.get(k)
	if btn == null or btn.disabled:
		printerr("TESTDBG build button %s missing/disabled" % k)
		return null
	_press_button(btn)
	await _frames(2)
	var sp := _screen(at)
	battle.commander.mouse_override = sp
	_move_mouse(sp)
	await _frames(3)
	var before: int = battle.structures(0, k, false).size()
	_click(MOUSE_BUTTON_LEFT, sp)
	await _wait_sim(0.2)
	battle.commander.mouse_override = Vector2(-1, -1)
	var now: Array = battle.structures(0, k, false)
	if now.size() <= before:
		printerr("TESTDBG place %s at %s refused: %s (ghost at %s, mode '%s', control under mouse: %s)" % [k, str(at), battle.placement_problem(0, k, battle.commander.ghost_pos),
			str(battle.commander.ghost_pos), battle.commander.mode, str(get_viewport().gui_get_hovered_control())])
		for o in battle.obstacles_2d:
			if Vector2(o.x - at.x, o.y - at.z).length() < 25.0: printerr("TESTDBG   obstacle ", o)
		for u in battle.units:
			if u.position.distance_to(at) < 25.0: printerr("TESTDBG   unit ", u.kind, " ", u.position)
		return null
	return now[now.size() - 1]


func _until(cond: Callable, max_t: float) -> bool:
	var end: float = battle.sim_time + max_t
	while battle.sim_time < end:
		if cond.call(): return true
		await _wait_sim(0.5)
	return cond.call()


func _run() -> void:
	if "build" in battle.args:
		await _run_build()
		return
	if "qa" in battle.args:
		await _run_qa()
		return
	await _run_main()


func _run_qa() -> void:
	await _wait_sim(0.5)
	# every 3D model the game references must load from this build (catches missing / skipped textures)
	var paths: Array = []
	for k in UnitDefs.all_kinds(): paths.append(str(UnitDefs.def_of(k).get("model3d", "")))
	for k in UnitDefs.POWERS: paths.append(str(UnitDefs.POWERS[k].get("model3d", "")))
	for k in BuildingDefs.DEFS: paths.append(str(BuildingDefs.DEFS[k].get("model3d", "")))
	paths += [Unit.PARA_MODEL, battle.CRATE_MODEL, battle.C130_MODEL]
	var bad: Array = []; var ok := 0
	for p in paths:
		if p == "": continue
		var r: Resource = load(p) if ResourceLoader.exists(p) else null
		if r == null: bad.append(p)
		else: ok += 1
	_log("all_models_load", bad.is_empty(), "%d loaded; failed: %s" % [ok, ", ".join(bad)])
	var ccp: Vector3 = battle.structures(0, "command_center")[0].position
	battle.cash[0] += 20000
	var pp := await _place("power_plant", ccp + Vector3(-40, 0, -6))
	await _until(func(): return pp != null and pp.built, 30.0)
	var bk := await _place("barracks", ccp + Vector3(40, 0, -16))
	await _until(func(): return bk != null and bk.built, 30.0)
	var dp := await _place("supply_depot", ccp + Vector3(-50, 0, -40))
	await _until(func(): return dp != null and dp.built, 30.0)
	var wf := await _place("war_factory", ccp + Vector3(0, 0, -50))
	await _until(func(): return wf != null and wf.built, 45.0)
	await _qa_checks(ccp, bk, wf)
	await _qa_m1(ccp)
	await _qa_m7(ccp)
	await _qa_m8(ccp)
	await _qa_ai_retreat(ccp)
	await _qa_save_load(ccp)
	_finish()


func _run_main() -> void:
	await _wait_sim(0.5)
	var cc: Array = battle.structures(0, "command_center")
	_log("start_state", cc.size() == 1 and _dozer() != null and battle.cash[0] == BuildingDefs.START_CASH and battle.piles.size() == 5,
		"cc=%d dozer=%s cash=%d piles=%d" % [cc.size(), str(_dozer() != null), battle.cash[0], battle.piles.size()])
	var ccp: Vector3 = cc[0].position
	# placement rules
	var r1: String = battle.placement_problem(0, "power_plant", ccp)
	var r2: String = battle.placement_problem(0, "power_plant", Vector3(0, 0, -200))
	var r3: String = battle.placement_problem(0, "war_factory", ccp + Vector3(50, 0, 0))
	_log("placement_rules", r1 == "Blocked" and r2 == "Too far from your base" and r3.begins_with("Requires"), "%s | %s | %s" % [r1, r2, r3])
	# power plant via HUD + map click, constructed by the dozer
	var cash0: int = battle.cash[0]
	var pp := await _place("power_plant", ccp + Vector3(-40, 0, -6))
	_log("place_power_plant", pp != null and battle.cash[0] == cash0 - 800 and not pp.built, "cash %d -> %d" % [cash0, battle.cash[0]])
	await _shot("placing")
	var gen0: int = battle.power_gen(0)
	for i in 4:
		await _wait_sim(1.0)
		var d := _dozer()
		if false: print("TESTDBG dozer state=%d pos=%s site=%s fd=%.1f path=%d/%d prog=%.2f" % [d.state, str(d.position), str(d.site), pp.footprint_dist(d.position) if pp else -1.0, d.path_i, d.path.size(), pp.progress if pp else -1.0])
	var built := await _until(func(): return pp != null and pp.built, 25.0)
	_log("dozer_constructs", built and battle.power_gen(0) == gen0 + 10, "built=%s power %d -> %d t=%.1f" % [str(built), gen0, battle.power_gen(0), battle.sim_time])
	# barracks + supply depot
	var bk := await _place("barracks", ccp + Vector3(40, 0, -16))
	await _until(func(): return bk != null and bk.built, 30.0)
	var dp := await _place("supply_depot", ccp + Vector3(-50, 0, -40))
	await _until(func(): return dp != null and dp.built, 30.0)
	var haulers: Array = _team(["ch47"])
	_log("depot_gives_hauler", dp != null and dp.built and haulers.size() == 1, "haulers=%d" % haulers.size())
	var inc0: int = battle.income[0]
	var got := await _until(func(): return battle.income[0] >= inc0 + BuildingDefs.HAUL_LOAD * 2, 90.0)
	_log("supply_income", got, "delivered %d t=%.1f" % [battle.income[0] - inc0, battle.sim_time])
	await _shot("hauling")
	# production via the structure's buttons; rally point by clicking the map
	await _sel([bk])
	battle.camera.focus(bk.position)
	await _frames(3)
	var rally := bk.position + Vector3(0, 0, -40)
	_click(MOUSE_BUTTON_LEFT, _screen(rally))
	await _wait_sim(0.2)
	_log("rally_point", bk.has_rally and bk.rally.distance_to(rally) < 3.0, "rally=%s" % str(bk.rally))
	var c1: int = battle.cash[0]
	var i1: int = battle.income[0]
	_press_button(battle.hud.econ.buttons["rifleman"]); await _frames(2)
	_press_button(battle.hud.econ.buttons["rifleman"]); await _frames(2)
	_press_button(battle.hud.econ.buttons["at4"]); await _wait_sim(0.2)
	_log("queue_units", bk.prod_queue.size() == 3 and battle.cash[0] - (battle.income[0] - i1) == c1 - 700, "queue=%s cash %d -> %d" % [str(bk.prod_queue), c1, battle.cash[0]])
	# cancel the last (refund)
	var c2: int = battle.cash[0]
	battle.issue({"type": "cancel_unit", "team": 0, "id": bk.uid}); await _wait_sim(0.2)
	_log("cancel_refund", bk.prod_queue.size() == 2 and battle.cash[0] >= c2 + 300, "queue=%s" % str(bk.prod_queue))
	var made := await _until(func(): return _team(["rifleman"]).size() >= 2, 20.0)
	await _wait_sim(8.0)
	var inf: Array = _team(["rifleman"])
	var at_rally := inf.filter(func(u): return u.position.distance_to(rally) < 15.0).size()
	_log("infantry_produced_to_rally", made and at_rally >= 1, "riflemen=%d at_rally=%d" % [inf.size(), at_rally])
	battle.camera.focus(rally)
	await _shot("infantry")
	# war factory -> vehicles
	await _until(func(): return battle.cash[0] >= 2600, 60.0)
	var wf := await _place("war_factory", ccp + Vector3(0, 0, -50))
	await _until(func(): return wf != null and wf.built, 45.0)
	if wf:
		await _sel([wf]); await _frames(3)
		await _until(func(): return battle.cash[0] >= 1700, 60.0)
		_press_button(battle.hud.econ.buttons["abrams"]); await _frames(2)
		_press_button(battle.hud.econ.buttons["hmmwv_50cal"]); await _wait_sim(0.2)
	var veh := await _until(func(): return _team(["abrams"]).size() >= 1 and _team(["hmmwv_50cal"]).size() >= 1, 40.0)
	_log("vehicles_produced", veh, "abrams=%d hmmwv=%d" % [_team(["abrams"]).size(), _team(["hmmwv_50cal"]).size()])
	# selling the only power plant leaves the base under-powered: refund + production at half speed
	var c3: int = battle.cash[0]
	var i3: int = battle.income[0]
	await _sel([pp]); await _frames(3)
	_press_button(battle.hud.econ.buttons["sell"]); await _wait_sim(0.3)
	var refund: int = battle.cash[0] - c3 - (battle.income[0] - i3)
	_log("sell_refund", pp.dead and refund == 400, "refund %d" % refund)
	var low: bool = not battle.power_ok(0)
	_log("low_power_state", low, "power use %d / gen %d" % [battle.power_use(0), battle.power_gen(0)])
	if low and bk:
		battle.issue({"type": "produce", "team": 0, "id": bk.uid, "kind": "rifleman"}); await _wait_sim(0.2)
		while bk.prod_queue.size() > 1: await _wait_sim(0.2)
		var before: float = bk.prod_left
		await _wait_sim(2.0)
		var rate := (before - bk.prod_left) / 2.0
		_log("low_power_slows_production", absf(rate - BuildingDefs.LOW_POWER_RATE) < 0.08, "rate=%.2f" % rate)
	# the AI opponent: builds, earns, produces, attacks
	var ai_ok := await _until(func(): return battle.structures(1).size() >= 5 and battle.income[1] > 0, 200.0)
	var ai_units: Array = battle.units.filter(func(u): return u.team == 1 and not u.dead and not (u is Building) and u.def.get("weapons", []).size() > 0)
	_log("ai_builds_and_earns", ai_ok, "structures=%d income=%d army=%d t=%.0f" % [battle.structures(1).size(), battle.income[1], ai_units.size(), battle.sim_time])
	var attacked := await _until(func(): return battle.base_ai.waves > 0, 240.0)
	_log("ai_attacks", attacked, "waves=%d t=%.0f" % [battle.base_ai.waves, battle.sim_time])
	var ai: BaseAI = battle.base_ai
	var scouted := await _until(func(): return ai.known.size() > 0, 120.0)
	_log("ai_scouts_and_remembers", scouted and ai.scout_t > 40.0, "known enemy structures %d, next scouting trip at %.0f s, t=%.0f" % [ai.known.size(), ai.scout_t, battle.sim_time])
	# combat roles: AT4 vs a vehicle does far more damage than a rifle; rifle vs infantry more than vs armour
	var am := UnitDefs.ARMOR_MULT
	_log("counter_matrix", am.rocket.heavy > am.bullet.heavy * 5.0 and am.bullet.infantry > am.bullet.heavy * 5.0, "")
	await _wait_sim(30.0)
	battle.camera.focus(battle.start_pos[0] + Vector3(0, 0, -60))
	await _shot("battle")
	# victory: remove every enemy structure and unit
	for u in battle.units:
		if u.team == 1 and not u.dead: u.take_damage(1e9, null)
	await _wait_sim(1.0)
	_log("victory_when_enemy_destroyed", battle.game_over and Game.last_result.get("result", "") == "Victory", "result=%s" % Game.last_result.get("result", ""))
	_finish()


## Checks added for the B1.2 playtest QA report: airfield parking, repair, rubble + rebuild, world scale.
func _qa_checks(ccp: Vector3, bk: Building, wf: Building) -> void:
	battle.cash[0] += 15000    # test funding so the checks do not wait on income
	print("TESTDBG funded +15000 for QA checks")
	var pp2 := await _place("power_plant", ccp + Vector3(-62, 0, 8))
	await _until(func(): return pp2 != null and pp2.built, 40.0)
	var pp3 := await _place("power_plant", ccp + Vector3(62, 0, 14))
	await _until(func(): return pp3 != null and pp3.built, 40.0)
	# --- airfield: pads in front of it and on the map; aircraft spawn on, return to and land on their own pad
	var af := await _place("airfield", ccp + Vector3(90, 0, -20))
	await _until(func(): return af != null and af.built, 60.0)
	var pads_ok := af != null and af.pads.size() == 4
	if af:
		for p in af.pads:
			if not battle.map_bounds.grow(-10).has_point(Vector2(p.pos.x, p.pos.z)): pads_ok = false
			var inside: bool = absf(p.pos.x - af.position.x) <= af.half.x and absf(p.pos.z - af.position.z) <= af.half.y
			var apron: bool = p.pos.z < af.position.z     # older 2D airfield: apron in front, toward the map centre
			if not (inside if af.model3d else apron): pads_ok = false
	_log("airfield_pads_on_map", pads_ok, "pads=%s" % (str(af.pads.map(func(p): return p.pos)) if af else "none"))
	if af:
		await _sel([af]); await _frames(3)
		for k in ["f16", "a10", "ah64"]:
			_press_button(battle.hud.econ.buttons[k]); await _frames(2)
		await _until(func(): return _team(["f16"]).size() >= 1 and _team(["a10"]).size() >= 1 and _team(["ah64"]).size() >= 1, 80.0)
		var air: Array = _team(["f16", "a10", "ah64"])
		var homes := {}
		var on_pads := true
		for u in air:
			var on := false
			for p in af.pads:
				if u.home.distance_to(p.pos) < 0.1 and u.flat_dist(p.pos) < 1.0: on = true
			homes[str(u.home)] = true
			if not on: on_pads = false
		_log("aircraft_spawn_on_own_pads", air.size() == 3 and on_pads and homes.size() == 3, "aircraft=%d distinct pads=%d" % [air.size(), homes.size()])
		# fly out, then R (return) - every type must land inside its pad
		await _sel(air)
		battle.issue({"type": "move", "ids": air.map(func(u): return u.uid), "points": air.map(func(u): return u.position + Vector3(0, 0, -120))})
		# jets on the ground must stay on paved surfaces: never inside the hangar / tower block at the runway's take-off end
		var jets: Array = air.filter(func(u): return u.domain == "jet")
		var bad := []
		var probe := func():
			for j in jets:
				if j.dead or j.airborne: continue
				var lp: Vector3 = af.to_local(j.position)
				if lp.x > -30.0 and lp.x < -4.5 and lp.z > -9.0 and lp.z < 10.0: bad.append("%s@(%.0f,%.0f)" % [j.kind, lp.x, lp.z])
		for i in 60:
			await _wait_sim(0.2); probe.call()
		await _sel(air); await _frames(2)
		_key(KEY_R); await _frames(2)
		var t0: float = battle.sim_time
		while battle.sim_time - t0 < 90.0 and not air.all(func(u): return u.dead or u.state == Unit.S.LANDED):
			await _wait_sim(0.2); probe.call()
		_log("jet_taxi_avoids_hangar", bad.is_empty() and af.model3d != null, "ground positions inside the hangar block: %d %s" % [bad.size(), str(bad.slice(0, 4))])
		var landed := air.filter(func(u): return not u.dead and u.state == Unit.S.LANDED and u.flat_dist(u.home) < PAD_TOL(u))
		_log("aircraft_return_land_on_pad", landed.size() == air.filter(func(u): return not u.dead).size(),
			", ".join(air.map(func(u): return "%s %.2fm %s" % [u.kind, u.flat_dist(u.home), "LANDED" if u.state == Unit.S.LANDED else "state%d" % u.state])))
		await _sel([])
		battle.camera.focus(af.position + Vector3(0, 0, -20)); await _shot("airfield_parked")
		# a fourth aircraft fills the last pad; a fifth is refused (no stacking)
		_press_button_if(af, "f16")
		await _until(func(): return _team(["f16"]).size() >= 2, 40.0)
		var why: String = battle.produce_problem(af, "a10")
		_log("full_apron_refuses_more", why == "No free pad", "reason=%s" % why)
	# --- repair: start, stop, resume, out of cash, full
	if wf and not wf.dead:
		wf.take_damage(wf.bdef.hp * 0.5, null)
		await _sel([wf]); await _frames(3)
		var h0: float = wf.hp; var c0: int = battle.cash[0]; var i0: int = battle.income[0]
		_press_button(battle.hud.econ.buttons["repair"]); await _wait_sim(2.0)
		var h1: float = wf.hp; var spent: int = c0 - battle.cash[0] + (battle.income[0] - i0)
		_log("repair_heals_and_costs", wf.repairing and h1 > h0 + wf.bdef.hp * 0.06 and spent > 0, "hp %.0f -> %.0f, spent $%d" % [h0, h1, spent])
		_press_button(battle.hud.econ.buttons["repair"]); await _wait_sim(1.0)
		var h2: float = wf.hp
		await _wait_sim(1.0)
		_log("repair_stop", not wf.repairing and absf(wf.hp - h2) < 0.01, "repairing=%s" % str(wf.repairing))
		var keep: int = battle.cash[0]
		battle.cash[0] = 0
		_press_button(battle.hud.econ.buttons["repair"]); await _wait_sim(1.0)
		var h3: float = wf.hp
		_log("repair_pauses_without_cash", wf.repairing and wf.repair_blocked != "" and absf(h3 - h2) < 1.0, "blocked=%s" % wf.repair_blocked)
		battle.cash[0] = keep
		await _until(func(): return wf.hp >= wf.bdef.hp, 40.0)
		await _frames(3)
		_log("repair_completes_and_disables", wf.hp >= wf.bdef.hp and not wf.repairing and battle.hud.econ.buttons["repair"].disabled, "hp %.0f" % wf.hp)
	# --- destroyed structure leaves rubble; Dozer click on the rubble rebuilds it the normal way
	if bk and not bk.dead:
		var bpos: Vector3 = bk.position
		bk.take_damage(1e9, null)
		await _wait_sim(0.5)
		var rb: Dictionary = battle.rubble_at(bpos, 0)
		_log("rubble_left", not rb.is_empty() and not battle.gnav.blocked_at(bpos), "rubble=%s" % str(not rb.is_empty()))
		var cash_b: int = battle.cash[0]; var inc_b: int = battle.income[0]
		await _sel([_dozer()])
		battle.camera.focus(bpos); await _frames(3)
		_click(MOUSE_BUTTON_LEFT, _screen(bpos)); await _wait_sim(0.3)
		var nb: Array = battle.structures(0, "barracks", false).filter(func(x): return x.position.distance_to(bpos) < 0.5)
		var paid: int = cash_b - battle.cash[0] + (battle.income[0] - inc_b)
		_log("rebuild_from_rubble", nb.size() == 1 and not nb[0].built and paid == 500 and battle.rubble_at(bpos, 0).is_empty(), "paid $%d" % paid)
		if nb.size() == 1:
			var t0: float = battle.sim_time
			await _until(func(): return nb[0].built, 60.0)
			_log("rebuild_completes", nb[0].built, "%.0f s (build time %d s)" % [battle.sim_time - t0, int(BuildingDefs.DEFS.barracks.build_time)])
	# --- 3D pilot models: Dozer wheels turn and tracks scroll with movement; rifleman animation follows movement
	var dz := _dozer()
	if dz and not dz.wheels.is_empty() and not dz.track_mats.is_empty():
		var w0: Basis = dz.wheels[0].transform.basis
		var t0v: float = dz.track_mats[0].uv1_offset.y
		battle.issue({"type": "move", "ids": [dz.uid], "points": [dz.position + Vector3(20, 0, -20)]})
		await _wait_sim(2.0)
		var turned: bool = not dz.wheels[0].transform.basis.is_equal_approx(w0)
		var scrolled: bool = absf(dz.track_mats[0].uv1_offset.y - t0v) > 0.5
		_log("dozer_wheels_and_tracks_animate", turned and scrolled, "wheels=%d turned=%s track dv=%.2f" % [dz.wheels.size(), str(turned), dz.track_mats[0].uv1_offset.y - t0v])
	else:
		_log("dozer_wheels_and_tracks_animate", false, "dozer has no 3D wheels/tracks")
	var rf: Array = _team(["rifleman"])
	if rf.is_empty() and bk and not bk.dead: pass
	var rm: Unit = battle._spawn("rifleman", 0, ccp + Vector3(0, 0, -30), 0.0)
	await _frames(3)
	var idle_anim: String = rm.anim_cur
	battle.issue({"type": "move", "ids": [rm.uid], "points": [rm.position + Vector3(0, 0, -30)]})
	await _wait_sim(1.0)
	var mv_anim: String = rm.anim_cur
	_log("rifleman_animation_states", rm.anim != null and idle_anim == "idle" and mv_anim in ["walk", "run"], "idle=%s moving=%s" % [idle_anim, mv_anim])
	# --- world scale guide: a CH-47 is large but smaller than a Supply Depot; selection radius follows drawn size
	var ch: Array = _team(["ch47"])
	if not ch.is_empty():
		var drawn: float = float(ch[0].def.length) * ch[0].vis_scale
		var depot: float = BuildingDefs.DEFS.supply_depot.size.x
		_log("scale_ch47_vs_depot", drawn < depot and drawn > depot * 0.6, "CH-47 drawn %.1f m, depot %.1f m" % [drawn, depot])


## Milestone M1/M4 systems: transports, air assault, paratroopers, supply drop zone, vehicle repair bay, artillery.
func _qa_m1(ccp: Vector3) -> void:
	battle.cash[0] += 20000
	# --- ground transport: 3 riflemen board a HMMWV by clicking it, then unload with D
	var hv: Unit = battle._spawn("hmmwv", 0, ccp + Vector3(30, 0, -70), 0.0)
	var sq: Array = []
	for i in 3: sq.append(battle._spawn("rifleman", 0, ccp + Vector3(10 + i * 3.0, 0, -80), 0.0))
	await _wait_sim(0.3)
	await _sel(sq)
	battle.camera.focus(hv.position); await _frames(3)
	_click(MOUSE_BUTTON_LEFT, _screen(hv.world_center())); await _frames(2)
	await _until(func(): return hv.passengers.size() == 3, 20.0)
	var gone := sq.all(func(u): return not (u in battle.units))
	_log("board_transport", hv.passengers.size() == 3 and gone, "aboard=%d" % hv.passengers.size())
	battle.issue({"type": "move", "ids": [hv.uid], "points": [hv.position + Vector3(-40, 0, -30)]})
	await _wait_sim(6.0)
	await _sel([hv]); _key(KEY_D); await _wait_sim(1.5)
	var out_ok := hv.passengers.is_empty() and sq.all(func(u): return u in battle.units and u.visible and not battle.gnav.blocked_at(u.position))
	_log("unload_transport", out_ok, "left aboard=%d" % hv.passengers.size())
	# --- air assault: riflemen board a hovering UH-60, it flies, descends and unloads
	var uh: Unit = battle._spawn("uh60", 0, ccp + Vector3(-30, 0, -90), 0.0)
	await _wait_sim(0.5)
	battle.issue({"type": "board", "team": 0, "ids": sq.map(func(u): return u.uid), "target": uh.uid})
	await _until(func(): return uh.passengers.size() == 3, 30.0)
	_log("air_assault_board", uh.passengers.size() == 3, "aboard=%d alt=%.1f" % [uh.passengers.size(), uh.altitude])
	battle.issue({"type": "move", "ids": [uh.uid], "points": [uh.position + Vector3(0, 0, -60)]})
	await _wait_sim(8.0)
	battle.issue({"type": "unload", "team": 0, "ids": [uh.uid]})
	await _until(func(): return uh.passengers.is_empty(), 20.0)
	_log("air_assault_unload", uh.passengers.is_empty() and sq.all(func(u): return u in battle.units), "alt at unload %.1f" % uh.altitude)
	# --- paratroopers support power (needs an Airfield, which _qa_checks built)
	var n0: int = _team(["paratrooper"]).size()
	var tgt: Vector3 = ccp + Vector3(0, 0, -110)
	battle.issue({"type": "power", "team": 0, "id": "paradrop", "pos": tgt})
	await _wait_sim(18.0)
	var paras: Array = _team(["paratrooper"]).filter(func(u): return u.position.distance_to(tgt) < 60.0 and u.para_alt <= 0.0)
	_log("paratroopers_land", _team(["paratrooper"]).size() >= n0 + 6 and paras.size() >= 6, "paratroopers %d -> %d, landed near target %d" % [n0, _team(["paratrooper"]).size(), paras.size()])
	await _shot("paratroopers")
	# --- supply drop zone: C-130 drops crates that add cash
	var dz := await _place("drop_zone", ccp + Vector3(-60, 0, -95))
	await _until(func(): return dz != null and dz.built, 70.0)
	await _until(func(): return battle.drop_income[0] >= 1000, 70.0)
	_log("supply_drop_zone_income", dz != null and battle.drop_income[0] >= 1000, "air-dropped $%d" % battle.drop_income[0])
	# --- War Factory repair bay
	var wf: Array = battle.structures(0, "war_factory")
	if not wf.is_empty():
		var t: Unit = battle._spawn("abrams", 0, wf[0].repair_point() + Vector3(0, 0, 20), 0.0)
		t.take_damage(t.def.hp * 0.6, null)
		await _wait_sim(0.2)
		await _sel([t])
		battle.camera.focus(wf[0].position); await _frames(3)
		_click(MOUSE_BUTTON_LEFT, _screen(wf[0].position + Vector3(0, 3, 0))); await _frames(2)
		var h0: float = t.hp
		await _wait_sim(14.0)
		_log("war_factory_repairs_vehicle", t.hp > h0 + t.def.hp * 0.2, "hp %.0f -> %.0f" % [h0, t.hp])
	# --- artillery: Paladin fires beyond tank range but not inside its minimum range
	var pal: Unit = battle._spawn("paladin", 0, ccp + Vector3(120, 0, -60), 0.0)
	var dummy: Unit = battle._spawn("abrams", 1, pal.position + Vector3(0, 0, -150), PI)
	dummy.order_stop()
	await _wait_sim(10.0)
	var shots_far: int = battle.shots_by.get(pal.uid, 0)
	dummy.position = pal.position + Vector3(0, 0, -20); dummy.reset_physics_interpolation()
	var s1: int = battle.shots_by.get(pal.uid, 0)
	await _wait_sim(8.0)
	var s2: int = battle.shots_by.get(pal.uid, 0)
	_log("artillery_range_rules", shots_far >= 1 and s2 == s1, "fired at 150 m: %d, at 20 m: %d" % [shots_far, s2 - s1])
	dummy.take_damage(1e9, null)
	# --- roster: every unit the Barracks and War Factory list spawns, and uses its 3D model when one is delivered
	var kinds: Array = BuildingDefs.DEFS.barracks.produces + BuildingDefs.DEFS.war_factory.produces
	var with3d: Array = []; var cards: Array = []; var bad: Array = []
	for i in kinds.size():
		var k: String = kinds[i]
		var u: Unit = battle._spawn(k, 0, ccp + Vector3(-80 + (i % 7) * 12.0, 0, -150 - (i / 7) * 12.0), 0.0)
		var m3: String = str(u.def.get("model3d", ""))
		var has3d := m3 != "" and ResourceLoader.exists(m3)
		if has3d and u.card_sprite == null and u.model != null: with3d.append(k)
		elif not has3d and u.card_sprite != null: cards.append(k)
		else: bad.append(k)
	_log("roster_spawns_with_models", bad.is_empty(), "3D: %s | still image: %s | wrong: %s" % [", ".join(with3d), ", ".join(cards), ", ".join(bad)])


func PAD_TOL(u: Unit) -> float:
	return 1.0


func _press_button_if(b: Building, k: String) -> void:
	await _sel([b]); await _frames(3)
	if battle.hud.econ.buttons.has(k) and not battle.hud.econ.buttons[k].disabled:
		_press_button(battle.hud.econ.buttons[k]); await _frames(2)


## M7: universal inspector and veterancy.
func _qa_m7(ccp: Vector3) -> void:
	var insp: Inspector = battle.hud.inspector
	battle.hud.details_open = true     # the Details panel (full inspector text) opens on request
	var rm: Unit = battle._spawn("rifleman", 0, ccp + Vector3(20, 0, -40), 0.0)
	await _sel([rm]); await _wait_sim(0.4)
	var txt: String = insp.body.get_parsed_text()
	_log("inspector_unit", insp.visible and insp.title.text == rm.def.name and "Weapons" in txt and "Veterancy: Recruit" in txt,
		"title=%s visible=%s" % [insp.title.text, str(insp.visible)])
	var bk: Array = battle.structures(0, "barracks")
	if not bk.is_empty():
		var b: Building = bk[0]
		battle.cash[0] += 2000
		battle.issue({"type": "produce", "team": 0, "id": b.uid, "kind": "rifleman"})
		await _wait_sim(0.3)
		battle.commander._set_selection([]); battle.commander.sel_building = b
		await _wait_sim(0.5)
		txt = insp.body.get_parsed_text()
		_log("inspector_building_queue", insp.title.text == b.def.name and "Production" in txt and "ETA" in txt, txt.substr(0, 160).replace("\n", " | "))
	var af: Array = battle.structures(0, "airfield")
	if not af.is_empty():
		battle.commander.sel_building = af[0]
		await _wait_sim(0.5)
		txt = insp.body.get_parsed_text()
		_log("inspector_airfield_pads", "Pads" in txt and "Pad 1:" in txt and "Pad 4:" in txt, txt.substr(txt.find("Pads"), 140).replace("\n", " | "))
		battle.commander.sel_building = null
	var grp: Array = [rm, battle._spawn("rifleman", 0, rm.position + Vector3(3, 0, 0), 0.0), battle._spawn("abrams", 0, rm.position + Vector3(10, 0, 0), 0.0)]
	await _sel(grp); await _wait_sim(0.4)
	var rows := insp.roster.get_child_count()
	_log("inspector_group", insp.title.text == "3 selected" and rows == 2, "title=%s roster rows=%d" % [insp.title.text, rows])
	# veterancy: kills promote, bonuses apply in the simulation and show in the inspector
	var foe: Unit = battle._spawn("abrams", 1, rm.position + Vector3(0, 0, -200), 0.0)
	var hp0: float = rm.hp
	rm.take_damage(10.0, foe)
	var taken0: float = hp0 - rm.hp
	for i in 2:
		var v: Unit = battle._spawn("abrams", 1, rm.position + Vector3(30 + i * 6, 0, -200), 0.0)
		v.take_damage(99999.0, rm)
	var promoted: bool = rm.vet_rank >= 1
	var hp1: float = rm.hp
	rm.take_damage(10.0, foe)
	var taken1: float = hp1 - rm.hp
	await _sel([rm]); await _wait_sim(0.4)
	txt = insp.body.get_parsed_text()
	_log("veterancy_promotion", promoted and taken1 < taken0 and "Veterancy: Veteran" in txt and "damage taken" in txt,
		"rank=%s xp=%d damage taken %.1f -> %.1f, promotions=%d" % [Veterancy.RANKS[rm.vet_rank], int(rm.vet_xp), taken0, taken1, battle.promotions])
	foe.take_damage(99999.0, null)
	# pin keeps the object after deselecting; close hides until a new selection
	insp._toggle_pin()
	await _sel([]); await _wait_sim(0.4)
	var pinned_ok: bool = insp.visible and insp.title.text == rm.def.name
	insp._toggle_pin()
	await _sel([]); await _wait_sim(0.4)
	_log("inspector_pin", pinned_ok and not insp.visible, "pinned shown=%s, after unpin visible=%s" % [str(pinned_ok), str(insp.visible)])


## M8: research at structures (real cost, progress, cancel refund, effect on listed units only) and battle plans.
func _qa_m8(ccp: Vector3) -> void:
	battle.cash[0] += 20000
	var wfs: Array = battle.structures(0, "war_factory")
	var wf: Building = wfs[0] if not wfs.is_empty() else battle.add_structure("war_factory", 0, ccp + Vector3(0, 0, -70), true)
	await _sel([]); battle.commander.sel_building = wf
	await _wait_sim(0.4)
	await _wait_sim(0.3)
	var btn: Button = battle.hud.econ.buttons.get("up:composite_armor")
	var c0: int = battle.cash[0]
	if btn and not btn.disabled: _press_button(btn)
	await _wait_sim(0.5)
	_log("research_starts", wf.research_id == "composite_armor" and battle.cash[0] == c0 - 1500, "research=%s cash %d -> %d" % [wf.research_id, c0, battle.cash[0]])
	# cancel refunds, restart
	battle.issue({"type": "cancel_research", "team": 0, "id": wf.uid}); await _wait_sim(0.3)
	var refunded: bool = wf.research_id == "" and battle.cash[0] == c0
	battle.issue({"type": "research", "team": 0, "id": wf.uid, "upgrade": "composite_armor"}); await _wait_sim(0.3)
	_log("research_cancel_refund", refunded and wf.research_id == "composite_armor", "refunded=%s" % str(refunded))
	var tank: Unit = battle._spawn("abrams", 0, ccp + Vector3(-30, 0, -60), 0.0)
	var jeep: Unit = battle._spawn("hmmwv_50cal", 0, ccp + Vector3(-40, 0, -60), 0.0)
	var t_before := tank.hp; tank.take_damage(100.0, null); var dt0: float = t_before - tank.hp
	await _until(func(): return battle.has_upgrade(0, "composite_armor"), 60.0)
	var t1 := tank.hp; tank.take_damage(100.0, null); var dt1: float = t1 - tank.hp
	var j1 := jeep.hp; jeep.take_damage(100.0, null); var dj: float = j1 - jeep.hp
	_log("composite_armor_effect", battle.has_upgrade(0, "composite_armor") and dt1 < dt0 * 0.9 and is_equal_approx(dj, 100.0),
		"Abrams takes %.0f -> %.0f; HMMWV .50 (not armoured) takes %.0f" % [dt0, dt1, dj])
	await _sel([tank]); await _wait_sim(0.4)
	var ti: String = battle.hud.inspector.body.get_parsed_text()
	await _sel([jeep]); await _wait_sim(0.4)
	var ji: String = battle.hud.inspector.body.get_parsed_text()
	_log("inspector_upgrade_states", "Composite Armor: Installed" in ti and not ("Composite Armor" in ji), "tank lists it installed; HMMWV .50 does not list it")
	# battle plans: locked until Advanced Training; then a plan activates, and switching has a delay
	var cc: Building = battle.structures(0, "command_center")[0]
	var why0: String = battle.plan_problem(0, "assault")
	battle.issue({"type": "research", "team": 0, "id": cc.uid, "upgrade": "adv_training"})
	await _until(func(): return battle.has_upgrade(0, "adv_training"), 70.0)
	battle.issue({"type": "plan", "team": 0, "plan": "assault"})
	await _until(func(): return battle.plan[0] == "assault", 10.0)
	var m_assault: float = battle.dealt_mult(tank, null)
	battle.issue({"type": "plan", "team": 0, "plan": "fortify"})
	await _wait_sim(1.0)
	var gap: bool = battle.plan[0] == "" and battle.plan_pending[0] == "fortify"
	await _until(func(): return battle.plan[0] == "fortify", 20.0)
	_log("battle_plans", why0.begins_with("Requires") and is_equal_approx(m_assault, 1.1) and gap and battle.plan[0] == "fortify" and battle.taken_mult(jeep) < 1.0,
		"locked before: '%s'; assault dmg x%.2f; switching gap=%s; fortify active, HMMWV taken x%.2f" % [why0, m_assault, str(gap), battle.taken_mult(jeep)])


## B2: save and load. Capture a busy state (structures, queues, research, plan, transports, groups), write it, read it
## back, rebuild the battle from it in place and compare fingerprints; then play on for 10 s. Also leaves
## user://saves/qa_e2e.sav + .sig for the separate end-to-end run (main menu -> load -> fresh match).
## B2 AI behaviour in isolation (the QA run has no live AI): a small team-1 wave attacks; one badly hurt unit falls
## back for repair; when the wave is shattered the rest are called home and the next wave is bigger.
func _qa_ai_retreat(ccp: Vector3) -> void:
	var ai := BaseAI.new(battle, 1, "Normal")
	var far: Vector3 = battle.start_pos[1]
	var wave: Array = []
	for i in 6:
		wave.append(battle._spawn("abrams" if i < 2 else "rifleman", 1, far + Vector3(-40 + i * 8, 0, 60), 0.0))
	await _wait_sim(0.2)
	ai.attacking = wave.map(func(u): return u.uid); ai.wave_n0 = wave.size(); ai.last_attack_t = battle.sim_time - 30.0
	var hurt: Unit = wave[0]
	hurt.hp = hurt.def.hp * 0.2
	ai._army()
	await _wait_sim(0.2)
	var hurt_back: bool = ai.retreating.has(hurt.uid) and not (hurt.uid in ai.attacking)
	for i in range(2, 6): wave[i].take_damage(99999.0, null)
	var size0: int = ai.attack_size
	ai._army()
	await _wait_sim(0.2)
	var called_off: bool = ai.attacking.is_empty() and ai.retreating.has(wave[1].uid) and ai.attack_size == size0 + 2
	_log("ai_retreats_when_hurt", hurt_back and called_off, "hurt unit falls back %s; wave lost 4 of 6 -> called off %s, next wave size %d -> %d" % [
		str(hurt_back), str(called_off), size0, ai.attack_size])
	for u in wave: if not u.dead: u.take_damage(99999.0, null)


func _qa_save_load(ccp: Vector3) -> void:
	battle.cash[0] += 5000
	var wfs: Array = battle.structures(0, "war_factory")
	if not wfs.is_empty():
		battle.issue({"type": "produce", "team": 0, "id": wfs[0].uid, "kind": "hmmwv"})
		battle.issue({"type": "produce", "team": 0, "id": wfs[0].uid, "kind": "abrams"})
	var hv: Unit = battle._spawn("hmmwv", 0, ccp + Vector3(30, 0, -60), 0.0)
	var r1: Unit = battle._spawn("rifleman", 0, ccp + Vector3(33, 0, -60), 0.0)
	await _wait_sim(0.3)
	battle._board(r1, hv)
	var sq: Array = battle.units.filter(func(u): return u.team == 0 and not u.dead and u.kind == "rifleman").slice(0, 3)
	battle.commander._set_selection(sq); battle.commander.assign_group(4)
	var mover: Unit = sq[0] if not sq.is_empty() else null
	if mover: battle.issue({"type": "move", "team": 0, "ids": [mover.uid], "points": [mover.position + Vector3(40, 0, -20)]})
	await _wait_sim(1.0)
	var sig0: Dictionary = SaveGame.signature(battle)
	var data: Dictionary = SaveGame.capture(battle)
	var path := SaveGame.DIR + "/qa_test.sav"
	var wrote := SaveGame.write(path, data)
	var back := SaveGame.read(path)
	_log("save_writes_and_reads", wrote and not back.is_empty() and back.units.size() == data.units.size(),
		"%d units/structures saved, file %d bytes" % [data.units.size(), FileAccess.get_file_as_bytes(path).size()])
	var goal0: Vector3 = mover.goal if mover else Vector3.ZERO
	var mover_id: int = mover.uid if mover else -1
	var hv_id: int = hv.uid
	SaveGame.restore(battle, back)
	var sig1: Dictionary = SaveGame.signature(battle)     # before any simulation tick runs
	var diffs: Array = []
	for k in sig0:
		if str(sig0[k]) != str(sig1[k]): diffs.append("%s: %s -> %s" % [k, str(sig0[k]).substr(0, 60), str(sig1[k]).substr(0, 60)])
	_log("load_restores_state", diffs.is_empty(), "fingerprint keys %d, differences: %s" % [sig0.size(), "; ".join(diffs) if not diffs.is_empty() else "none"])
	await _frames(3)
	var hv2: Unit = battle.by_id.get(hv_id)
	var m2: Unit = battle.by_id.get(mover_id)
	var g4: Array = battle.commander.groups.get(4, [])
	var cc2: Array = battle.structures(0, "command_center")
	var refs_ok: bool = hv2 != null and hv2.passengers.size() == 1 and g4.size() == sq.size() and m2 != null and m2.goal.distance_to(goal0) < 0.5 \
		and not cc2.is_empty() and not battle.gnav.box_free(cc2[0].position, Vector2(2, 2))
	_log("load_restores_links", refs_ok, "transport passengers %d, group 4 size %d, mover goal kept %s, CC blocks pathing %s" % [
		hv2.passengers.size() if hv2 else -1, g4.size(), str(m2 != null and m2.goal.distance_to(goal0) < 0.5), str(not cc2.is_empty() and not battle.gnav.box_free(cc2[0].position, Vector2(2, 2)))])
	var t_before: float = battle.sim_time
	await _wait_sim(10.0)
	var moved: bool = m2 != null and m2.flat_dist(goal0) < 6.0
	_log("play_continues_after_load", battle.sim_time > t_before + 9.0 and moved, "sim %.1f -> %.1f s, mover reached its goal %s" % [t_before, battle.sim_time, str(moved)])
	# end-to-end file for the second run
	var e2e := SaveGame.capture(battle)
	SaveGame.write(SaveGame.DIR + "/qa_e2e.sav", e2e)
	var f := FileAccess.open(SaveGame.DIR + "/qa_e2e.sig", FileAccess.WRITE)
	f.store_string(JSON.stringify(SaveGame.signature(battle))); f.close()


func _finish() -> void:
	var passed := checks.filter(func(c): return c[1]).size()
	print("RESULT %d/%d" % [passed, checks.size()])
	var f := FileAccess.open(out + "/basetest_results.txt", FileAccess.WRITE)
	for c in checks: f.store_line("%s %s %s" % [c[0], "PASS" if c[1] else "FAIL", c[2]])
	f.store_line("commands logged: %d" % battle.command_log.size())
	f.close()
	get_tree().quit()


# ================================================================== B3 construction: rotation, walls, garrison orders
# Run: godot --headless --path godot --fixed-fps 30 -- basetest build noai nation1=iran out=/dir
# (add a display and drop --headless to also write the evidence screenshots)
func _keyx(k: Key, shift := false) -> void:
	for pressed in [true, false]:
		var e := InputEventKey.new()
		e.keycode = k; e.physical_keycode = k; e.pressed = pressed; e.shift_pressed = shift
		Input.parse_input_event(e)


## Real input: dozer selected, build button, cursor on `at`, `turns` presses of R (negative: Shift+R), then either a
## click or a press-drag-release toward `drag_to`. Returns the new structure(s) of kind k.
func _place_input(k: String, at: Vector3, turns := 0, drag_to := Vector3.INF, focus := Vector3.INF) -> Array:
	var dz := _dozer()
	battle.camera.focus(at if focus == Vector3.INF else focus)
	await _frames(2)
	await _sel([dz])
	await _frames(2)
	var btn: Button = battle.hud.econ.buttons.get(k)
	if btn == null or btn.disabled:
		printerr("TESTDBG build button %s missing/disabled" % k)
		return []
	_press_button(btn)
	await _frames(2)
	var sp := _screen(at)
	battle.commander.mouse_override = sp
	_move_mouse(sp)
	await _frames(3)
	for i in absi(turns):
		_keyx(KEY_R, turns < 0)
		await _frames(1)
	var before: Array = battle.structures(0, k, false)
	if drag_to == Vector3.INF:
		_click(MOUSE_BUTTON_LEFT, sp)
	else:
		_mouse(MOUSE_BUTTON_LEFT, true, sp)
		await _frames(2)
		var sp2 := _screen(drag_to)
		for i in 8:
			var q := sp.lerp(sp2, (i + 1) / 8.0)
			battle.commander.mouse_override = q
			_move_mouse(q, (sp2 - sp) / 8.0)
			await _frames(2)
		drag_hint = battle.commander.place_hint() if battle.commander.mode.begins_with("place:") else ""
		_mouse(MOUSE_BUTTON_LEFT, false, sp2)
	await _wait_sim(0.2)
	battle.commander.mouse_override = Vector2(-1, -1)
	var made: Array = battle.structures(0, k, false).filter(func(b): return not (b in before))
	if made.is_empty():
		printerr("TESTDBG place %s at %s refused: %s" % [k, str(at), battle.commander.ghost_reason])
	battle.commander.set_mode("")
	return made


var drag_hint := ""


## Path crosses the segment a-b (top view)?
func _path_crosses(path: PackedVector3Array, a: Vector3, b: Vector3) -> bool:
	for i in path.size() - 1:
		if Geometry2D.segment_intersects_segment(Vector2(path[i].x, path[i].z), Vector2(path[i + 1].x, path[i + 1].z), Vector2(a.x, a.z), Vector2(b.x, b.z)) != null:
			return true
	return false


func _path_len(path: PackedVector3Array) -> float:
	var l := 0.0
	for i in path.size() - 1: l += Vector2(path[i + 1].x - path[i].x, path[i + 1].z - path[i].z).length()
	return l


func _all_blocked(a: Vector3, b: Vector3) -> Array:
	var gaps: Array = []
	var n := int(a.distance_to(b) / 0.5)
	for i in n + 1:
		var q := a.lerp(b, float(i) / n)
		for cls in battle.navs:
			if not (battle.navs[cls] as GridNav).blocked_at(q): gaps.append("%s@%.1f" % [cls, a.distance_to(q)])
	return gaps


func _run_build() -> void:
	await _wait_sim(0.5)
	var ccp: Vector3 = battle.structures(0, "command_center")[0].position
	battle.cash[0] += 60000
	battle.add_structure("power_plant", 0, ccp + Vector3(-40, 0, -6), true)
	battle.add_structure("barracks", 0, ccp + Vector3(40, 0, -16), true)
	await _wait_sim(0.3)
	# --- 1. rotation while placing: R, Shift+R and press-drag (through the real input pipeline)
	battle.commander.place_yaw = 0.0
	var p1: Array = await _place_input("power_plant", ccp + Vector3(-110, 0, -60), 1)
	battle.commander.place_yaw = 0.0
	var p2: Array = await _place_input("power_plant", ccp + Vector3(-60, 0, -60), -1)
	battle.commander.place_yaw = 0.0
	var p3: Array = await _place_input("power_plant", ccp + Vector3(-10, 0, -60), 0, ccp + Vector3(10, 0, -60))
	var y1: float = rad_to_deg(p1[0].yaw) if p1.size() == 1 else 999.0
	var y2: float = rad_to_deg(p2[0].yaw) if p2.size() == 1 else 999.0
	var y3: float = rad_to_deg(p3[0].yaw) if p3.size() == 1 else 999.0
	_log("place_rotate_R_keys", absf(y1 - 45.0) < 0.5 and absf(y2 + 45.0) < 0.5 and p1.size() == 1 and absf(rad_to_deg(p1[0].rotation.y) - 45.0) < 0.5,
		"R -> %.1f deg, Shift+R -> %.1f deg (node rotation %.1f)" % [y1, y2, rad_to_deg(p1[0].rotation.y) if p1.size() == 1 else 0.0])
	_log("place_rotate_drag", absf(y3 - 90.0) < 3.0, "drag toward +X -> %.1f deg (expected 90)" % y3)
	if p1.is_empty() or p3.is_empty():
		_finish(); return
	var pp1: Building = p1[0]
	# --- 2. navigation follows the oriented footprint
	var c1: Vector3 = pp1.position
	var corner := Building.local_to_world(c1, pp1.yaw, Vector2(8.5, 7.5))              # inside the rotated box, outside the old axis box
	var old_corner := c1 + Vector3(9.8, 0, 8.8)                                        # inside the old (grown) axis box, outside the rotated one
	var g: GridNav = battle.gnav
	var cells_ok: bool = g.blocked_at(c1) and g.blocked_at(corner) and not g.blocked_at(old_corner) \
		and absf(corner.x - c1.x) > 10.5
	var dirv := Building.local_to_world(Vector3.ZERO, pp1.yaw, Vector2(1, 0))         # along the rotated edge
	var lane := Building.local_to_world(c1, pp1.yaw, Vector2(0, 12.6))
	var path: PackedVector3Array = battle.find_path(lane - dirv * 35.0, lane + dirv * 35.0, "tracked")
	var inside_rot := 0; var inside_old := 0
	for i in path.size() - 1:
		for k in 281:
			var q := path[i].lerp(path[i + 1], k / 280.0)
			if pp1.contains_xz(q, 0.0): inside_rot += 1
			if absf(q.x - c1.x) < 10.0 and absf(q.z - c1.z) < 9.0: inside_old += 1
	_log("nav_rotated_footprint", cells_ok and inside_rot == 0 and inside_old > 0 and path.size() <= 3,
		"cells: centre/rot-corner blocked, old-box corner free=%s; path %d pts, samples inside rotated box %d, inside old axis box %d" % [
			str(cells_ok), path.size(), inside_rot, inside_old])
	# --- 3. placement rejected where only the rotated footprint overlaps
	battle.commander.place_yaw = 0.0
	var hpos := c1 + Vector3(16, 0, 0)
	var why_rot: String = battle.placement_problem(0, "hesco", hpos, 0.0)
	var free_far: String = battle.placement_problem(0, "hesco", c1 + Vector3(26, 0, 0), 0.0)
	var hb: Array = await _place_input("hesco", hpos)
	_log("placement_rejects_rotated_overlap", why_rot == "Blocked" and free_far == "" and hb.is_empty(),
		"hesco 16 m east of the 45-degree plant: '%s' (input placement made %d); 26 m east: '%s'" % [why_rot, hb.size(), free_far])
	# --- 4. concrete wall drawn between two Defence Towers: N connected segments, no gaps
	var wc := Vector3.INF          # centre of a clear 70 x 60 m patch for the wall test (the map has random boulders)
	for cand in [Vector3(-55, 0, 112), Vector3(-45, 0, 104), Vector3(-65, 0, 118), Vector3(-35, 0, 96), Vector3(55, 0, 120), Vector3(-80, 0, 100)]:
		if battle.gnav.box_free_static(cand + Vector3(-12, 0, -8), Vector2(36, 30)) and battle.gnav.box_free(cand, Vector2(26, 18)):
			wc = cand; break
	if wc == Vector3.INF:
		printerr("TESTDBG no clear patch for the wall test"); wc = Vector3(-55, 0, 112)
	var ta: Building = battle.add_structure("defense_tower", 0, wc + Vector3(-20, 0, 0), true)
	var tb: Building = battle.add_structure("defense_tower", 0, wc + Vector3(20, 0, 0), true)
	await _wait_sim(0.3)
	var cash_w: int = battle.cash[0]
	var walls: Array = await _place_input("concrete_wall", ta.position + Vector3(1.5, 0, 1), 0, tb.position + Vector3(-1, 0, -1.5), wc)
	var hint := drag_hint
	walls.sort_custom(func(a, b): return a.position.x < b.position.x)
	var same_run: bool = not walls.is_empty() and walls.all(func(w): return w.wall_run == walls[0].wall_run)
	var gaps := _all_blocked(ta.position, tb.position)
	var faces_north: bool = not walls.is_empty() and (Basis(Vector3.UP, walls[0].yaw) * Vector3(0, 0, 1)).z < -0.9
	_log("wall_line_between_towers", walls.size() == 6 and same_run and gaps.is_empty() and battle.cash[0] == cash_w - 6 * 75 and faces_north and "$450" in hint,
		"segments=%d (scale %.2f), one run=%s, nav gaps between tower centres: %s, paid $%d, faces enemy=%s, hint '%s'" % [walls.size(),
			walls[0].seg_scale if not walls.is_empty() else 0.0, str(same_run), str(gaps.slice(0, 6)), cash_w - battle.cash[0], str(faces_north), hint])
	var built := await _until(func(): return walls.all(func(w): return w.built), 120.0)
	_log("dozer_builds_whole_wall_line", built, "built %d/%d t=%.0f" % [walls.filter(func(w): return w.built).size(), walls.size(), battle.sim_time])
	var south := wc + Vector3(0, 0, 16); var north := wc + Vector3(0, 0, -16)
	var pth: PackedVector3Array = battle.find_path(south, north, "infantry")
	var blocked_ok: bool = not _path_crosses(pth, ta.position, tb.position) and _path_len(pth) > 45.0
	# hesco line from tower A going north-west: snaps to the tower, faces away from the base
	battle.commander.place_yaw = 0.0
	var hend := ta.position + Vector3(-28, 0, -24)
	for cand in [Vector3(-28, 0, -24), Vector3(-30, 0, 20), Vector3(-24, 0, -30), Vector3(-36, 0, 0), Vector3(-20, 0, 30)]:
		if str(battle.wall_plan(0, "hesco", ta.position, ta.position + cand).problem) == "": hend = ta.position + cand; break
	var hes: Array = await _place_input("hesco", ta.position + Vector3(-1, 0, -1), 0, hend, ta.position.lerp(hend, 0.4))
	var hgaps := _all_blocked(ta.position, ta.position + (hend - ta.position).normalized() * 12.0)
	var hmid: Vector3 = ta.position.lerp(hend, 0.5) - ccp
	var hface: bool = not hes.is_empty() and (Basis(Vector3.UP, hes[0].yaw) * Vector3(0, 0, 1)).dot(Vector3(hmid.x, 0, hmid.z).normalized()) > 0.2
	_log("hesco_line_joins_tower", hes.size() >= 3 and hgaps.is_empty() and hface, "segments=%d yaw=%.0f deg, nav gaps tower->line: %s, faces away from base=%s" % [hes.size(),
		rad_to_deg(hes[0].yaw) if not hes.is_empty() else 0.0, str(hgaps.slice(0, 4)), str(hface)])
	# a unit cannot path through the wall; destroying one segment opens a gap it walks through
	var rf: Unit = battle._spawn("rifleman", 0, south, 0.0)
	await _wait_sim(0.3)
	if walls.size() >= 3: walls[2].take_damage(1e9, null)
	await _wait_sim(0.3)
	var pth2: PackedVector3Array = battle.find_path(south, north, "infantry")
	battle.issue({"type": "move", "ids": [rf.uid], "points": [north]})
	await _until(func(): return rf.flat_dist(north) < 3.0, 25.0)
	_log("wall_blocks_until_breached", blocked_ok and _path_crosses(pth2, ta.position, tb.position) and rf.flat_dist(north) < 3.0,
		"intact: path %.0f m, crosses=%s | one segment destroyed: path %.0f m crosses=%s, rifleman reached the far side=%s" % [_path_len(pth),
			str(_path_crosses(pth, ta.position, tb.position)), _path_len(pth2), str(_path_crosses(pth2, ta.position, tb.position)), str(rf.flat_dist(north) < 3.0)])
	battle.camera.yaw = 0.0
	battle.camera.zoom = 75.0; battle.camera._apply(); battle.camera.focus(wc + Vector3(-10, 0, -2))
	await _shot("wall_towers_hesco")
	# --- 5. rotated airfield (structure placed directly, 90 degrees)
	var af: Building = battle.add_structure("airfield", 0, ccp + Vector3(90, 0, -75), true, PI / 2.0)
	await _wait_sim(0.3)
	# --- 6. occupied building: flag of the occupier's nation in its team colour; occupants attack on command
	var house: Building = battle.add_civic("civ_house_a", Vector3(125, 0, 200), false)
	var sq: Array = []
	for i in 3: sq.append(battle._spawn("rifleman", 0, house.position + Vector3(-14 + i * 2.5, 0, 8), 0.0))
	await _wait_sim(0.3)
	battle.issue({"type": "board", "team": 0, "ids": sq.map(func(u): return u.uid), "target": house.uid})
	await _until(func(): return house.passengers.size() == 3, 30.0)
	await _wait_sim(0.5)
	var fl: Node3D = house.flag_node
	var nf: Node = fl.get_node_or_null("NationFlag") if fl else null
	var want0 := str(Nations.DEFS.get(battle.nation_of(0), {}).get("flag", ""))
	var pen_ok: bool = fl != null and (fl.get_meta("team_color") as Color).is_equal_approx(UnitDefs.team_color(0))
	var on_roof: bool = fl != null and fl.position.y > 2.5
	_log("garrison_flag_shown", house.team == 0 and nf != null and nf.scene_file_path == want0 and pen_ok and on_roof and fl.is_visible_in_tree(),
		"owner=%d flag=%s (want %s) pennant team colour=%s, pole base %.1f m above ground" % [house.team, nf.scene_file_path if nf else "none", want0, str(pen_ok), fl.position.y if fl else -1.0])
	battle.camera.zoom = 55.0; battle.camera._apply(); battle.camera.focus(house.position + Vector3(0, 0, 4))
	await _shot("garrison_flag_team0")
	# ordered attack: select the house, click the chosen (farther) enemy; it is hit before the nearer one
	var ea: Unit = battle._spawn("rifleman", 1, Vector3(136, 0, 140), PI)
	var eb: Unit = battle._spawn("rifleman", 1, Vector3(142, 0, 140), PI)
	ea.order_stop(); eb.order_stop()
	await _wait_sim(0.5)
	battle.commander._set_selection([house]); await _frames(3)
	var has_tiles: bool = battle.hud.econ.buttons.has("gattack") and battle.hud.econ.buttons.has("gstop") and not battle.hud.econ.buttons["gattack"].disabled
	battle.camera.focus(Vector3(140, 0, 160)); await _frames(3)
	var picked: Unit = battle.commander.unit_at(_screen(eb.world_center()))
	_click(MOUSE_BUTTON_LEFT, _screen(eb.world_center()))
	await _wait_sim(0.4)
	if house.gar_target != eb: printerr("TESTDBG gattack: picked=%s seen=%s own_garrison=%s" % [picked.kind if picked else "none", str(battle.seen.get(eb.uid, false)), str(battle.commander.own_garrison())])
	var ordered: bool = house.gar_target == eb
	ea.position = house.position + Vector3(0, 0, -20); ea.reset_physics_interpolation()
	eb.position = house.position + Vector3(27, 0, -12); eb.reset_physics_interpolation()
	ea.order_stop(); eb.order_stop()
	var first := {}
	var t0: float = battle.sim_time
	while battle.sim_time - t0 < 15.0 and (eb.hp >= eb.def.hp or not first.has("b")):
		if not first.has("a") and ea.hp < ea.def.hp: first["a"] = battle.sim_time - t0
		if not first.has("b") and (eb.hp < eb.def.hp or eb.dead): first["b"] = battle.sim_time - t0
		await _wait_sim(0.1)
	_log("garrison_ordered_attack", has_tiles and ordered and first.has("b") and float(first.get("a", 99.0)) > float(first.b),
		"Attack/Stop tiles=%s, order set by clicking=%s, first hit on ordered target %.1f s, on the nearer enemy %s" % [str(has_tiles), str(ordered),
			float(first.get("b", -1.0)), ("%.1f s" % first.a) if first.has("a") else "not before"])
	await _until(func(): return ea.dead and eb.dead, 20.0)
	# return fire: an unarmed vehicle is closest, a rifleman shooting the building is farther; occupants turn on the shooter
	battle.issue({"type": "garrison_stop", "team": 0, "id": house.uid})
	var dzr: Unit = battle._spawn("dozer", 1, house.position + Vector3(0, 0, -16), PI)
	dzr.order_stop()
	await _wait_sim(3.0)
	var shooter: Unit = battle._spawn("rifleman", 1, house.position + Vector3(-31, 0, -9), PI)
	shooter.order_attack(house)
	var hit := await _until(func(): return shooter.dead or shooter.hp < shooter.def.hp, 12.0)
	_log("garrison_returns_fire", hit and not dzr.dead, "shooter hp %.0f/%.0f dead=%s, dozer hp %.0f/%.0f" % [shooter.hp, shooter.def.hp, str(shooter.dead), dzr.hp, dzr.def.hp])
	if not shooter.dead: shooter.take_damage(1e9, null)
	dzr.take_damage(1e9, null)
	# --- 7. save / load keeps rotations, wall segments and the garrison
	await _wait_sim(0.5)
	var rec := {}
	for b in battle.units:
		if b is Building and not b.dead: rec[b.uid] = [b.yaw, b.seg_scale, b.position]
	var probe := Building.local_to_world(c1, pp1.yaw, Vector2(8.5, 7.5))
	var house_id: int = house.uid
	var af_id: int = af.uid
	var data := SaveGame.capture(battle)
	SaveGame.write(SaveGame.DIR + "/build_test.sav", data)
	SaveGame.restore(battle, SaveGame.read(SaveGame.DIR + "/build_test.sav"))
	await _frames(2)
	var bad: Array = []
	for id in rec:
		var b: Unit = battle.by_id.get(id)
		if b == null or not (b is Building): bad.append("%d missing" % id); continue
		var bb := b as Building
		if absf(bb.yaw - float(rec[id][0])) > 0.001 or absf(bb.seg_scale - float(rec[id][1])) > 0.001 or absf(bb.rotation.y - bb.yaw) > 0.001:
			bad.append("%s yaw %.2f->%.2f" % [bb.bkind, rec[id][0], bb.yaw])
	var house2: Building = battle.by_id.get(house_id)
	_log("save_load_keeps_yaw", bad.is_empty() and rec.size() > 10 and battle.gnav.blocked_at(probe) and house2 != null and house2.passengers.size() == 3,
		"%d structures compared, mismatches: %s; rotated corner still blocks nav=%s; house occupants %d" % [rec.size(), str(bad.slice(0, 4)),
			str(battle.gnav.blocked_at(probe)), house2.passengers.size() if house2 else -1])
	house = house2
	af = battle.by_id.get(af_id)
	# capture: the occupants leave, the other side moves in; the flag changes to their nation and colour
	battle.issue({"type": "unload", "team": 0, "ids": [house.uid]})
	await _until(func(): return house.passengers.is_empty(), 10.0)
	for u in battle.units:
		if u.team == 0 and u.kind == "rifleman" and u.flat_dist(house.position) < 30.0: u.take_damage(1e9, null)
	await _wait_sim(0.5)
	var empty_flag: bool = house.flag_node == null
	var obs: Unit = battle._spawn("rifleman", 0, house.position + Vector3(0, 0, 50), PI)     # a player soldier watching the house
	obs.order_stop()
	var red: Array = []
	for i in 2: red.append(battle._spawn("rifleman", 1, house.position + Vector3(-12 + i * 2.5, 0, 9), 0.0))
	await _wait_sim(0.3)
	battle.issue({"type": "board", "team": 1, "ids": red.map(func(u): return u.uid), "target": house.uid})
	await _until(func(): return house.passengers.size() == 2, 30.0)
	await _wait_sim(0.5)
	var fl1: Node3D = house.flag_node
	var nf1: Node = fl1.get_node_or_null("NationFlag") if fl1 else null
	var want1 := str(Nations.DEFS.get(battle.nation_of(1), {}).get("flag", ""))
	var pen1: bool = fl1 != null and (fl1.get_meta("team_color") as Color).is_equal_approx(UnitDefs.team_color(1))
	_log("garrison_flag_changes_on_capture", empty_flag and house.team == 1 and nf1 != null and nf1.scene_file_path == want1 and pen1 and house.visible and fl1.is_visible_in_tree(),
		"empty: no flag=%s; captured by team %d: flag=%s (want %s), pennant team colour=%s, seen by player=%s" % [str(empty_flag), house.team,
			nf1.scene_file_path if nf1 else "none", want1, str(pen1), str(house.visible)])
	battle.camera.focus(house.position + Vector3(0, 0, 4))
	await _shot("garrison_flag_captured")
	battle._lose_passengers(house)
	battle._set_owner(house, -1)
	# --- 8. jets from the rotated airfield: taxi, take off along the runway, return and land on their pad
	await _press_button_if(af, "f16")
	await _until(func(): return _team(["f16"]).size() >= 1, 40.0)
	var jets: Array = _team(["f16"])
	var jet: Unit = jets[0] if not jets.is_empty() else null
	var rw_dir := Vector3.ZERO
	var rw_local := Vector3.ZERO
	if af.runway.size() == 2:
		rw_dir = (af.runway[1] - af.runway[0]) * Vector3(1, 0, 1)
		rw_local = (af.to_local(af.runway[1]) - af.to_local(af.runway[0])) * Vector3(1, 0, 1)
	var bad_ground := []
	var air_t := -1.0
	var lift_dir := Vector3.ZERO
	if jet:
		battle.issue({"type": "move", "ids": [jet.uid], "points": [af.position + Vector3(0, 0, -160)]})
		var tj: float = battle.sim_time
		var prev := jet.position
		while battle.sim_time - tj < 60.0 and air_t < 0.0:
			await _wait_sim(0.2)
			if not jet.airborne:
				var lp: Vector3 = af.to_local(jet.position)
				if lp.x > -30.0 and lp.x < -4.5 and lp.z > -9.0 and lp.z < 10.0: bad_ground.append("(%.0f,%.0f)" % [lp.x, lp.z])
				if not af.contains_xz(jet.position, 25.0): bad_ground.append("off-field")
			elif air_t < 0.0:
				air_t = battle.sim_time - tj; lift_dir = (jet.position - prev) * Vector3(1, 0, 1)
			prev = jet.position
	var along: float = lift_dir.normalized().dot(rw_dir.normalized()) if lift_dir.length() > 0.01 and rw_dir.length() > 0.01 else 0.0
	var turned := rw_dir.length() > 1.0 and absf(rw_dir.normalized().dot(rw_local.normalized())) < 0.2
	_log("rotated_airfield_takeoff", jet != null and air_t > 0.0 and bad_ground.is_empty() and along > 0.8 and turned,
		"airfield yaw 90: runway world dir (%.2f, %.2f) vs model dir (%.2f, %.2f) turned=%s, airborne after %.1f s, lift-off heading along runway %.2f, ground positions off the paving: %s" % [
			rw_dir.normalized().x, rw_dir.normalized().z, rw_local.normalized().x, rw_local.normalized().z, str(turned), air_t, along, str(bad_ground.slice(0, 4))])
	if jet:
		await _wait_sim(6.0)
		battle.issue({"type": "return", "ids": [jet.uid]})
		await _until(func(): return jet.dead or jet.state == Unit.S.LANDED, 90.0)
		_log("rotated_airfield_landing", not jet.dead and jet.state == Unit.S.LANDED and jet.flat_dist(jet.home) < 1.0,
			"state=%d distance to its pad %.2f m" % [jet.state, jet.flat_dist(jet.home)])
	battle.camera.zoom = 120.0; battle.camera._apply(); battle.camera.focus(af.position)
	await _shot("rotated_airfield")
	_finish()

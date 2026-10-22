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
		print("TESTDBG build button %s missing/disabled" % k)
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
	if now.size() <= before: return null
	return now[now.size() - 1]


func _until(cond: Callable, max_t: float) -> bool:
	var end: float = battle.sim_time + max_t
	while battle.sim_time < end:
		if cond.call(): return true
		await _wait_sim(0.5)
	return cond.call()


func _run() -> void:
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
		_press_button(battle.hud.econ.buttons["vanguard"]); await _frames(2)
		_press_button(battle.hud.econ.buttons["hmmwv_50cal"]); await _wait_sim(0.2)
	var veh := await _until(func(): return _team(["vanguard"]).size() >= 1 and _team(["hmmwv_50cal"]).size() >= 1, 40.0)
	_log("vehicles_produced", veh, "vanguard=%d hmmwv=%d" % [_team(["vanguard"]).size(), _team(["hmmwv_50cal"]).size()])
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


func _finish() -> void:
	var passed := checks.filter(func(c): return c[1]).size()
	print("RESULT %d/%d" % [passed, checks.size()])
	var f := FileAccess.open(out + "/basetest_results.txt", FileAccess.WRITE)
	for c in checks: f.store_line("%s %s %s" % [c[0], "PASS" if c[1] else "FAIL", c[2]])
	f.store_line("commands logged: %d" % battle.command_log.size())
	f.close()
	get_tree().quit()

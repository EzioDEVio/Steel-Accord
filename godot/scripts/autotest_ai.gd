# Steel Accord - skirmish AI acceptance matches (headless, seeded, deterministic).
# Run: godot --headless --path godot --fixed-fps 30 -- aitest <mode> [ai0] [map=zagros_basin] [nation0=usa] [nation1=iran]
#      [diff=Hard] [mins=18] out=/dir
# Modes:
#   diag     timeline only (use with ai0 for AI vs AI)
#   avsa     AI vs AI (needs ai0): later waves carry vehicles, air strikes, support powers on valid targets, artillery
#            bombardment, no stalling (cash piling up unused, army idling at home), the match is decided or still fought
#   passive  AI vs an idle player base: the AI destroys it (wins)
#   defend   a scripted raid hits the AI base: the AI defends and beats it off
#   strong   a scripted strong player army attacks early: the AI loses
# Writes result.txt (checks), timeline.txt (minute -> event) and timeline_live.txt (same, written as it happens).
extends "res://scripts/autotest_base.gd"

var timeline: Array = []          # [sim time, text]
var mins := 15.0
var _tlf: FileAccess = null
var _ev_n := {}                   # ai team -> events already copied
var wave_rec: Array = []          # [team, sim time, vehicle value, total value, composition text]
var power_rec: Array = []         # [team, sim time, id, class, target, enemy value near target (ground truth)]
var stall_min := [0, 0]           # longest run of minutes with cash >= 5000 and nothing new bought
var _stall_run := [0, 0]
var _spent_last := [0, 0]
var idle_min := [0, 0]            # longest run of minutes with >= 8 army units idle near home and no wave out
var _idle_run := [0, 0]
var _pw_n := {}


func _tl(text: String) -> void:
	timeline.append([battle.sim_time, text])
	if _tlf == null: _tlf = FileAccess.open(out + "/timeline_live.txt", FileAccess.WRITE)
	if _tlf:
		_tlf.store_line("%s %s" % [_clock(battle.sim_time), text])
		_tlf.flush()


func _clock(t: float) -> String:
	return "%02d:%02d" % [int(t) / 60, int(t) % 60]


func _ais() -> Array:
	var l: Array = []
	if battle.base_ai0: l.append(battle.base_ai0)
	if battle.base_ai: l.append(battle.base_ai)
	return l


func _comp(team: int) -> String:
	var k := {}
	for u in battle.units:
		if u.team != team or u.dead or u is Building: continue
		k[u.kind] = int(k.get(u.kind, 0)) + 1
	return str(k)


func _snapshot() -> void:
	for ai in _ais():
		var t: int = ai.team
		var bk := {}
		for b in battle.structures(t, "", false): bk[b.bkind] = int(bk.get(b.bkind, 0)) + 1
		var q: Array = []
		for b in battle.structures(t):
			if not b.prod_queue.is_empty(): q.append("%s:%s" % [b.bkind, ",".join(b.prod_queue)])
		_tl("T%d snapshot cash=%d power=%d/%d income=%d spent=%d structures=%s units=%s queues=%s" % [t, battle.cash[t], battle.power_gen(t), battle.power_use(t),
			battle.income[t] + battle.derrick_income[t] + battle.drop_income[t], battle.spent[t], str(bk), _comp(t), " ".join(q)])
		# stall bookkeeping (once a minute)
		var bought: int = battle.spent[t] - _spent_last[t]
		_spent_last[t] = battle.spent[t]
		if battle.cash[t] >= 5000 and bought < 500: _stall_run[t] += 1
		else: _stall_run[t] = 0
		stall_min[t] = maxi(stall_min[t], _stall_run[t])
		var home: Vector3 = battle.start_pos[t]
		var idle_home: int = battle.units.filter(func(u): return u.team == t and not u.dead and not (u is Building) and u.domain == "ground" \
			and u.def.get("weapons", []).size() > 0 and not u.def.get("builder", false) and u.state == Unit.S.IDLE and u.flat_dist(home) < 160.0).size()
		if idle_home >= 8 and ("attacking" in ai) and ai.attacking.is_empty(): _idle_run[t] += 1
		else: _idle_run[t] = 0
		idle_min[t] = maxi(idle_min[t], _idle_run[t])


func _val(k: String) -> float:
	if BuildingDefs.UNIT_COST.has(k): return float(BuildingDefs.UNIT_COST[k][0])
	return 300.0


func _enemy_value_near(team: int, p: Vector3, r: float) -> float:
	var v := 0.0
	for u in battle.units:
		if u.dead or u.team != 1 - team or u.is_air() or u.position.distance_to(p) > r: continue
		v += float((u as Building).bdef.cost) if u is Building else _val(u.kind)
	return v


func _watch() -> void:
	for ai in _ais():
		var t: int = ai.team
		if not ("events" in ai):
			if ai.waves > int(_ev_n.get(t, 0)):
				_ev_n[t] = ai.waves
				var k := {}
				var veh := 0.0; var tot := 0.0
				for id in ai.attacking:
					var u: Unit = battle.by_id.get(id)
					if u == null: continue
					k[u.kind] = int(k.get(u.kind, 0)) + 1
					tot += _val(u.kind)
					if u.def.get("visual") != "infantry": veh += _val(u.kind)
				_tl("T%d wave %d: %s value %d vehicles %.0f%%" % [t, ai.waves, str(k), int(tot), 100.0 * veh / maxf(1.0, tot)])
			continue
		var n0: int = int(_ev_n.get(t, 0))
		for i in range(n0, ai.events.size()):
			var e: Array = ai.events[i]
			if str(e[1]).begins_with("builds hesco") or str(e[1]).begins_with("orders hauler"): continue
			_tl("T%d %s" % [t, e[1]])
			if str(e[1]).begins_with("wave ") and " launched" in str(e[1]): _rec_wave(ai)
		_ev_n[t] = ai.events.size()
		var pn: int = int(_pw_n.get(t, 0))
		for i in range(pn, ai.stats.powers.size()):
			var pr: Array = ai.stats.powers[i]
			var v := _enemy_value_near(t, pr[3], 30.0) if pr[2] != "reveal" else -1.0
			if pr[2] == "drop":   # a drop is aimed at a derrick to seize or a flank of the fight
				v = _enemy_value_near(t, pr[3], 70.0)
				for e in battle.derricks:
					if e.pos.distance_to(pr[3]) < 25.0 and e.owner != t: v = maxf(v, 1000.0)
			power_rec.append([t, pr[0], pr[1], pr[2], pr[3], v])
			_tl("T%d   power %s check: enemy value within 30 m of the target (ground truth) = %d" % [t, pr[1], int(v)])
		_pw_n[t] = ai.stats.powers.size()


func _rec_wave(ai) -> void:
	var veh := 0.0; var tot := 0.0
	var ids: Array = ai.attacking + ai.feint
	for id in ids:
		var u: Unit = battle.by_id.get(id)
		if u == null or u.dead: continue
		var v: float = _val(u.kind)
		tot += v
		if u.def.get("visual") != "infantry": veh += v
	wave_rec.append([ai.team, battle.sim_time, veh, tot, ai._comp_text(ids)])
	_tl("T%d   wave value %d, vehicles %d (%.0f%%)" % [ai.team, int(tot), int(veh), 100.0 * veh / maxf(1.0, tot)])


func _play(until_t: float, stop_on_end := true) -> void:
	var next_snap: float = floor(battle.sim_time / 60.0) * 60.0
	while battle.sim_time < until_t and not (stop_on_end and battle.game_over):
		if battle.sim_time >= next_snap:
			_snapshot(); next_snap += 60.0
		_watch()
		await _wait_sim(1.0)
	_watch()


func _run() -> void:
	mins = float(battle.args.get("mins", 15))
	await _wait_sim(0.5)
	var mode := "diag"
	for m in ["diag", "passive", "defend", "strong", "avsa"]:
		if m in battle.args: mode = m
	_tl("start mode=%s map=%s nations=%s/%s difficulty=%s" % [mode, battle.map_id, battle.nation_of(0), battle.nation_of(1),
		str(battle.args.get("diff", Game.settings.difficulty))])
	match mode:
		"avsa": await _run_avsa()
		"passive": await _run_passive()
		"defend": await _run_defend()
		"strong": await _run_strong()
		_: await _play(mins * 60.0)
	_snapshot()
	_finish_ai()


## Checks shared by the AI-vs-AI and passive modes, per computer player.
func _check_ai(ai, tag: String, need_later_waves := true) -> void:
	var t: int = ai.team
	var later := wave_rec.filter(func(w): return w[0] == t and w[1] >= 300.0)
	var veh := 0.0; var tot := 0.0; var min_share := 1.0
	for w in later:
		veh += w[2]; tot += w[3]; min_share = minf(min_share, w[2] / maxf(1.0, w[3]))
	var share := veh / maxf(1.0, tot)
	if need_later_waves or not later.is_empty():
		_log("%s_later_waves_have_vehicles" % tag, not later.is_empty() and share >= 0.30,
			"%d waves after 5:00, vehicle share of value %.0f%% (lowest single wave %.0f%%); all waves: %s" % [later.size(), share * 100.0, min_share * 100.0,
			", ".join(wave_rec.filter(func(w): return w[0] == t).map(func(w): return "%s %.0f%%" % [_clock(w[1]), 100.0 * w[2] / maxf(1.0, w[3])]))])
	_log("%s_air_strike" % tag, ai.stats.air_strikes >= 1, "sorties %d, sorties that fired %d" % [ai.stats.air_sorties, ai.stats.air_strikes])
	var pw := power_rec.filter(func(p): return p[0] == t)
	var valid := pw.filter(func(p): return p[3] == "reveal" or p[5] >= 400.0)
	_log("%s_support_power_valid_target" % tag, not pw.is_empty() and valid.size() == pw.size(),
		"%d uses: %s" % [pw.size(), ", ".join(pw.map(func(p): return "%s %s %s(value %d)" % [_clock(p[1]), p[2], p[3], int(p[5])]))])
	if not ai.role_kinds.arty.is_empty():
		_log("%s_artillery_bombards" % tag, ai.stats.bombard >= 1, "bombardments %d" % ai.stats.bombard)


func _run_avsa() -> void:
	if battle.base_ai0 == null:
		_log("avsa_needs_ai0", false, "start with the ai0 argument")
		return
	await _play(mins * 60.0)
	for ai in _ais():
		var tag := "T%d_%s" % [ai.team, battle.nation_of(ai.team)]
		_check_ai(ai, tag)
		_log("%s_no_stall" % tag, stall_min[ai.team] <= 2 and idle_min[ai.team] <= 3,
			"longest cash>=5000 with nothing bought: %d min; longest army idle at home with no wave out: %d min" % [stall_min[ai.team], idle_min[ai.team]])
	var res := "ongoing"
	if battle.game_over: res = "team 0 won" if Game.last_result.get("result", "") == "Victory" else "team 1 won"
	var waves_ok: bool = _ais().all(func(ai): return ai.waves >= 3)
	_log("avsa_decisive_or_fought", battle.game_over or waves_ok, "%s at %s; waves %s; structures %d / %d" % [res, _clock(battle.sim_time),
		str(_ais().map(func(ai): return ai.waves)), battle.structures(0).size(), battle.structures(1).size()])


func _run_passive() -> void:
	await _play(mins * 60.0)
	var ai = battle.base_ai
	_log("ai_beats_passive_player", battle.game_over and Game.last_result.get("result", "") == "Defeat",
		"result=%s at %s, waves %d" % [Game.last_result.get("result", "none"), _clock(battle.sim_time), ai.waves])
	_check_ai(ai, "T1_%s" % battle.nation_of(1), false)


## A raid arrives at the AI base after it has built up; the AI must respond and beat it.
func _run_defend() -> void:
	await _play(330.0)
	var ai = battle.base_ai
	var d0: int = ai.stats.defend
	var home: Vector3 = battle.start_pos[1]
	var fwd: float = 1.0 if home.z < 0.0 else -1.0
	var spawn_at: Vector3 = home + Vector3(110.0, 0, 150.0 * fwd)
	var raid: Array = []
	for i in 8:
		var k: String = ["abrams", "abrams", "abrams", "bradley", "rifleman", "rifleman", "at4", "at4"][i]
		raid.append(battle._spawn(k, 0, spawn_at + Vector3((i % 4) * 7.0, 0, (i / 4) * 7.0), 0.0))
	await _wait_sim(0.3)
	var ids: Array = raid.map(func(u): return u.uid)
	battle.issue({"type": "attack_move", "team": 0, "ids": ids, "points": battle.spread(ids, home)})
	_tl("T0 scripted raid: 3 Abrams, 1 Bradley, 2 riflemen, 2 AT4 attack-move on the AI Command Center")
	var t0: float = battle.sim_time
	var responded := false
	while battle.sim_time < t0 + 150.0 and not raid.all(func(u): return u.dead):
		await _play(battle.sim_time + 2.0, false)
		if ai.stats.defend > d0 and not responded:
			responded = true
			var near: int = battle.units.filter(func(u): return u.team == 1 and not u.dead and not (u is Building) and u.def.get("weapons", []).size() > 0 \
				and (u.state == Unit.S.ATTACK_MOVE or u.target != null)).size()
			_tl("T1 defence response: %d armed units engaging" % near)
	var cc_alive: bool = not battle.structures(1, "command_center").is_empty()
	var dead_n: int = raid.filter(func(u): return u.dead).size()
	_log("ai_defends_base", ai.stats.defend > d0 and cc_alive and dead_n >= 6,
		"defence responses %d, raid units destroyed %d/8 in %.0f s, AI Command Center alive %s" % [ai.stats.defend - d0, dead_n, battle.sim_time - t0, str(cc_alive)])


## A strong scripted player: a large armoured army attacks the AI base early and keeps attacking what is left.
func _run_strong() -> void:
	var p0: Vector3 = battle.start_pos[0]
	var fwd: float = -1.0 if p0.z > 0.0 else 1.0
	var army: Array = []
	var kinds := ["abrams", "abrams", "abrams", "abrams", "abrams", "abrams", "abrams", "abrams", "abrams", "abrams", "bradley", "bradley", "bradley",
		"bradley", "avenger", "avenger", "paladin", "paladin"]
	for i in kinds.size():
		army.append(battle._spawn(kinds[i], 0, p0 + Vector3(-50.0 + (i % 6) * 14.0, 0, fwd * (50.0 + (i / 6) * 12.0)), 0.0 if fwd < 0.0 else PI))
	_tl("T0 scripted strong player: 10 Abrams, 4 Bradley, 2 Avenger, 2 Paladin; attacks at 2:00")
	await _play(120.0)
	var end: float = mins * 60.0
	while battle.sim_time < end and not battle.game_over:
		var alive: Array = army.filter(func(u): return not u.dead)
		if alive.is_empty(): break
		var tgt: Vector3 = battle.start_pos[1]
		var bd := INF
		var c := _centroid(alive)
		for b in battle.structures(1, "", false):
			if b.is_civic(): continue
			var d: float = c.distance_to(b.position)
			if d < bd: bd = d; tgt = b.position
		if bd == INF:
			for u in battle.units:
				if u.team == 1 and not u.dead and c.distance_to(u.position) < bd: bd = c.distance_to(u.position); tgt = u.position
		var idle: Array = alive.filter(func(u): return u.state == Unit.S.IDLE).map(func(u): return u.uid)
		if not idle.is_empty(): battle.issue({"type": "attack_move", "team": 0, "ids": idle, "points": battle.spread(idle, tgt)})
		await _play(battle.sim_time + 5.0)
	_log("ai_loses_to_strong_player", battle.game_over and Game.last_result.get("result", "") == "Victory",
		"result=%s at %s; scripted army left %d/%d" % [Game.last_result.get("result", "none"), _clock(battle.sim_time), army.filter(func(u): return not u.dead).size(), army.size()])


func _finish_ai() -> void:
	var passed := checks.filter(func(c): return c[1]).size()
	print("RESULT %d/%d" % [passed, checks.size()])
	var f := FileAccess.open(out + "/result.txt", FileAccess.WRITE)
	for c in checks: f.store_line("%s %s %s" % [c[0], "PASS" if c[1] else "FAIL", c[2]])
	f.store_line("RESULT %d/%d" % [passed, checks.size()])
	f.close()
	var g := FileAccess.open(out + "/timeline.txt", FileAccess.WRITE)
	for e in timeline: g.store_line("%s %s" % [_clock(e[0]), e[1]])
	g.close()
	get_tree().quit()

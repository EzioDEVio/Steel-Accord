# Steel Accord - aircraft diagnostics (headless): measures hit rates, miss distances, bomb drops and landing accuracy.
# Run: godot --headless --path godot --fixed-fps 30 -- airshow noai airdiag
extends Node

var battle: Node
var log_shots: Array = []


func _ready() -> void:
	_run()


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _u(kind: String, team := 0) -> Unit:
	for u in battle.units:
		if u.kind == kind and u.team == team and not u.dead: return u
	return null


func _run() -> void:
	await _wait_sim(0.5)
	battle.ai = null
	battle.diag = self
	var reds: Array = battle.units.filter(func(u): return u.team == 1)
	# park the enemy tanks in a line, stationary, far from the blue tanks
	for i in reds.size():
		reds[i].position = Vector3(-60 + i * 20, 0, -40)
		reds[i].order_stop()
	for u in battle.units:
		if u.team == 0 and u.kind == "vanguard": u.position.z = 140.0; u.order_stop()
	for k in ["f16", "fa18", "a10", "ah64", "f22"]:
		var a := _u(k)
		if a == null: continue
		var t: Unit = reds.filter(func(r): return not r.dead)[0]
		var hp0 := t.hp
		log_shots.clear()
		battle.issue({"type": "attack", "ids": [a.uid], "target": t.uid})
		await _wait_sim(35.0)
		var hits := log_shots.filter(func(s): return s.hit).size()
		var miss_d: Array = log_shots.map(func(s): return snappedf(s.miss, 0.1))
		print("DIAG %s vs %s: shots=%d hits=%d target hp %.0f -> %.0f state=%s alt=%.1f miss_dist=%s" % [k, t.kind, log_shots.size(), hits, hp0, t.hp, Unit.S.keys()[a.state], a.altitude, str(miss_d.slice(0, 12))])
		battle.issue({"type": "return", "ids": [a.uid]})
		await _wait_sim(0.1)
	# landing accuracy
	await _wait_sim(30.0)
	for k in ["f16", "fa18", "a10", "f22"]:
		var a := _u(k)
		if a: print("DIAG land %s state=%s dist_from_pad=%.2f m heading=%.0f deg alt=%.2f" % [k, Unit.S.keys()[a.state], a.flat_dist(a.home), rad_to_deg(a.heading), a.altitude])
	# bombers
	for id in ["carpet", "supersonic", "stealth"]:
		var live: Array = reds.filter(func(r): return not r.dead)
		var c := Vector3(0, 0, -40)
		log_shots.clear()
		var nb0: int = battle.bomb_log.size()
		battle.issue({"type": "power", "team": 0, "id": id, "pos": c})
		await _wait_sim(12.0)
		var drops: Array = battle.bomb_log.slice(nb0)
		print("DIAG power %s: bombs=%d impact offsets from target=%s" % [id, drops.size(), str(drops.map(func(p): return Vector2(snappedf(p.x - c.x, 0.1), snappedf(p.z - c.z, 0.1))))])
	get_tree().quit()


func on_shot(shooter: Unit, target: Unit, p: Vector3, hit: bool) -> void:
	var miss := 0.0
	if target and is_instance_valid(target): miss = target.world_center().distance_to(p)
	log_shots.append({"hit": hit, "miss": miss})

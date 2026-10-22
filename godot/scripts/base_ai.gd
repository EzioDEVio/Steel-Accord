# Steel Accord - skirmish opponent for the base loop (B1.2). Deterministic: decisions depend only on simulation state
# and sim time, and every action goes through Battle.issue() like the player's orders (so it is logged for replays).
# Behaviour: fixed build order around its Command Center, keeps a Dozer, adds haulers, trains a mixed army,
# defends structures under attack, and attacks the nearest enemy structure once its army is large enough.
class_name BaseAI
extends RefCounted

var battle: Node
var team := 1
var think_t := 0.0
var think_every := 1.5
var attack_size := 7
var attack_after := 150.0
var waves := 0
var attacking: Array = []      # uids sent on the current attack

# build order (kind, local x, local forward offset from the Command Center; forward = toward the map centre)
const ORDER := [
	["power_plant", -36, -6], ["barracks", 36, 14], ["supply_depot", 40, -16], ["power_plant", -36, 16],
	["war_factory", 0, 42], ["defense_tower", -26, 64], ["power_plant", -60, 2], ["defense_tower", 26, 64],
	["airfield", -100, 70], ["power_plant", -60, 22], ["drop_zone", 70, 20], ["hesco", -12, 70], ["hesco", 12, 70],
]
const BARRACKS_MIX := ["rifleman", "rifleman", "at4"]
const FACTORY_MIX := ["abrams", "hmmwv_50cal", "bradley", "avenger", "abrams", "paladin"]
const AIR_MIX := ["ah64", "a10"]


func _init(b: Node, t: int, difficulty: String) -> void:
	battle = b; team = t
	match difficulty:
		"Easy": think_every = 3.0; attack_size = 10; attack_after = 300.0
		"Hard": think_every = 1.0; attack_size = 6; attack_after = 120.0
		_: think_every = 1.5; attack_size = 8; attack_after = 200.0
	if battle._automated() and "aifast" in battle.args:
		attack_after = 60.0; attack_size = 4


func _cc() -> Node:
	var c: Array = battle.structures(team, "command_center")
	return c[0] if not c.is_empty() else null


func _fwd() -> float:
	return 1.0 if battle.start_pos[team].z < 0.0 else -1.0


func _mine(pred: Callable) -> Array:
	return battle.units.filter(func(u): return u.team == team and not u.dead and pred.call(u))


func tick(dt: float) -> void:
	think_t -= dt
	if think_t > 0.0: return
	think_t = think_every
	var cc := _cc()
	var anchor: Vector3 = cc.position if cc else battle.start_pos[team]
	_construct(anchor)
	_produce(cc)
	_army()


## Next unbuilt entry of the build order: count how many of each kind we have and find the first shortfall.
func _construct(anchor: Vector3) -> void:
	var dozers := _mine(func(u): return u.def.get("builder", false))
	if dozers.is_empty(): return
	var dz: Unit = dozers[0]
	if dz.state == Unit.S.BUILD: return
	# resume an abandoned site first
	for b in battle.structures(team, "", false):
		if not b.built:
			battle.issue({"type": "build", "team": team, "ids": [dz.uid], "site": b.uid})
			return
	var have := {}
	var need := {}
	for e in ORDER:
		need[e[0]] = int(need.get(e[0], 0)) + 1
		var count: int = battle.structures(team, e[0], false).size()
		if count >= int(need[e[0]]): continue
		var k: String = e[0]
		if battle.cash[team] < int(BuildingDefs.DEFS[k].cost) + 200: return   # keep a small reserve for units
		if not battle.requirements_met(team, k): return
		var pos := _slot(anchor, float(e[1]), float(e[2]))
		for tries in 12:
			if battle.placement_problem(team, k, pos) == "": break
			var a := tries * 0.9
			pos = _slot(anchor, float(e[1]) + cos(a) * (6.0 + tries * 2.0), float(e[2]) + sin(a) * (6.0 + tries * 2.0))
		if battle.placement_problem(team, k, pos) == "":
			battle.issue({"type": "place", "team": team, "id": k, "pos": pos, "builder": dz.uid})
		return


func _slot(anchor: Vector3, x: float, f: float) -> Vector3:
	return anchor + Vector3(x * -_fwd(), 0, f * _fwd())


func _produce(cc: Node) -> void:
	var cash: int = battle.cash[team]
	if cc and _mine(func(u): return u.def.get("builder", false)).is_empty() and cc.prod_queue.is_empty() and cash >= 1000:
		battle.issue({"type": "produce", "team": team, "id": cc.uid, "kind": "dozer"})
		return
	var haulers := _mine(func(u): return u.def.get("hauler", false)).size()
	for d in battle.structures(team, "supply_depot"):
		if haulers < 2 and d.prod_queue.is_empty() and cash >= 1800 and battle.sim_time > 120.0:
			battle.issue({"type": "produce", "team": team, "id": d.uid, "kind": "ch47"})
			return
	var army := _mine(func(u): return not (u is Building) and u.def.get("weapons", []).size() > 0).size()
	for b in battle.structures(team, "barracks"):
		if b.prod_queue.size() < 2 and cash >= 400:
			battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": BARRACKS_MIX[army % BARRACKS_MIX.size()]})
			cash -= 300
	for b in battle.structures(team, "war_factory"):
		if b.prod_queue.size() < 1 and cash >= 1100:
			battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": FACTORY_MIX[army % FACTORY_MIX.size()]})
			cash -= 900
	for b in battle.structures(team, "airfield"):
		if b.prod_queue.is_empty() and cash >= 2200 and battle.produce_problem(b, "ah64") == "":
			battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": AIR_MIX[waves % AIR_MIX.size()]})


func _army() -> void:
	var fighters := _mine(func(u): return not (u is Building) and not u.def.get("builder", false) \
		and not u.def.get("hauler", false) and u.def.get("weapons", []).size() > 0 and u.domain != "jet")
	if fighters.is_empty(): return
	# defend: enemy close to one of our structures
	for b in battle.structures(team, "", false):
		var e: Unit = battle.find_enemy_near(b, 90.0)
		if e and not (e is Building):
			var ids: Array = []
			for u in fighters:
				if not (u.uid in attacking) or u.flat_dist(b.position) < 150.0: ids.append(u.uid)
			if not ids.is_empty():
				battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": ids.map(func(_i): return e.position)})
			return
	# attack when the idle army is big enough
	attacking = attacking.filter(func(id): return battle.by_id.has(id) and not battle.by_id[id].dead)
	var idle := fighters.filter(func(u): return not (u.uid in attacking) and u.state == Unit.S.IDLE)
	if battle.sim_time >= attack_after and idle.size() >= attack_size:
		var tgt := _enemy_target(idle[0].position)
		if tgt == Vector3.INF: return
		var ids: Array = idle.map(func(u): return u.uid)
		var pts: Array = []
		for i in ids.size():
			var a := TAU * i / ids.size()
			pts.append(tgt + Vector3(cos(a), 0, sin(a)) * 8.0)
		battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": pts})
		attacking.append_array(ids)
		waves += 1
	# attackers that went idle (target area cleared) push on to the next enemy structure
	var done := fighters.filter(func(u): return u.uid in attacking and u.state == Unit.S.IDLE)
	if not done.is_empty():
		var tgt := _enemy_target(done[0].position)
		if tgt != Vector3.INF:
			var ids: Array = done.map(func(u): return u.uid)
			battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": ids.map(func(_i): return tgt)})


func _enemy_target(from: Vector3) -> Vector3:
	var best := Vector3.INF
	var bd := INF
	for u in battle.units:
		if u.dead or u.team == team or u.team < 0: continue
		var w := 1.0 if u is Building else 1.6     # prefer structures (victory needs them gone)
		var d: float = from.distance_to(u.position) * w
		if d < bd: bd = d; best = u.position
	return best

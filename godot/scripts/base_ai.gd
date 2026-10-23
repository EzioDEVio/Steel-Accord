# Steel Accord - skirmish opponent for the base loop (B1.2). Deterministic: decisions depend only on simulation state
# and sim time, and every action goes through Battle.issue() like the player's orders (so it is logged for replays).
# Behaviour: fixed build order around its Command Center, keeps a Dozer, adds haulers, trains a mixed army,
# defends structures under attack, scouts, and attacks what it has seen once its army is large enough.
# Knowledge (B2): it targets only enemy structures its units have seen (remembered) and enemy units in sight now;
# with nothing known it heads for the enemy start. Badly damaged attackers fall back for repair; a wave that loses
# most of its strength is called off and the next one is bigger.
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
var capturing := {}            # derrick id -> uids sent to capture it
var known := {}                # enemy structure uid -> position (seen by our units at least once)
var scout_t := 40.0            # sim time of the next scouting trip
var scout_uid := -1
var retreating := {}           # uid -> sim time the retreat started
var wave_n0 := 0               # strength of the current attack wave when it left
var last_attack_t := -999.0
var losses_seen := 0
var garrisoning := {}          # civic building uid -> uids sent to occupy it

# build order (kind, local x, local forward offset from the Command Center; forward = toward the map centre)
const ORDER := [
	["power_plant", -36, -6], ["barracks", 36, 14], ["supply_depot", 40, -16], ["power_plant", -36, 16],
	["war_factory", 0, 42], ["defense_tower", -26, 64], ["power_plant", -60, 2], ["defense_tower", 26, 64],
	["airfield", -100, 70], ["power_plant", -60, 22], ["drop_zone", 70, 20], ["hesco", -12, 70], ["hesco", 12, 70],
]
const BARRACKS_MIX := ["rifleman", "rifleman", "at4"]
const FACTORY_MIX := ["abrams", "hmmwv_50cal", "bradley", "avenger", "abrams", "paladin"]
const AIR_MIX := ["ah64", "a10"]
var barracks_mix: Array = BARRACKS_MIX
var factory_mix: Array = FACTORY_MIX
var air_mix: Array = AIR_MIX


func _init(b: Node, t: int, difficulty: String) -> void:
	battle = b; team = t
	match difficulty:
		"Easy": think_every = 3.0; attack_size = 10; attack_after = 300.0
		"Hard": think_every = 1.0; attack_size = 6; attack_after = 120.0
		_: think_every = 1.5; attack_size = 8; attack_after = 200.0
	var nat: String = battle.nation_of(team)
	barracks_mix = Nations.mix(nat, "barracks", BuildingDefs.DEFS.barracks.produces, BARRACKS_MIX + (["special_forces"] if nat != "usa" else []))
	factory_mix = Nations.mix(nat, "war_factory", BuildingDefs.DEFS.war_factory.produces, FACTORY_MIX)
	air_mix = Nations.mix(nat, "airfield", BuildingDefs.DEFS.airfield.produces, AIR_MIX)
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
	_capture_derricks()
	_research()
	_look()
	_scout()
	_garrison()
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
		if k == "airfield" and air_mix.is_empty(): continue     # nothing to fly yet for this nation
		if battle.cash[team] < int(BuildingDefs.DEFS[k].cost) + 200: return   # keep a small reserve for units
		if not battle.requirements_met(team, k): return
		var pos := _slot(anchor, float(e[1]), float(e[2]))
		var n_try := 40 if battle.terrain else 12      # hills: search wider for flat ground
		for tries in n_try:
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
		battle.issue({"type": "produce", "team": team, "id": cc.uid, "kind": Nations.swap_unit(battle.nation_of(team), "dozer")})
		return
	var haulers := _mine(func(u): return u.def.get("hauler", false)).size()
	for d in battle.structures(team, "supply_depot"):
		if haulers < 2 and d.prod_queue.is_empty() and cash >= 1800 and battle.sim_time > 120.0:
			battle.issue({"type": "produce", "team": team, "id": d.uid, "kind": Nations.swap_unit(battle.nation_of(team), "ch47")})
			return
	var army := _mine(func(u): return not (u is Building) and u.def.get("weapons", []).size() > 0).size()
	for b in battle.structures(team, "barracks"):
		if b.prod_queue.size() < 2 and cash >= 400:
			battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": barracks_mix[army % barracks_mix.size()]})
			cash -= 300
	for b in battle.structures(team, "war_factory"):
		if b.prod_queue.size() < 1 and cash >= 1100 and not factory_mix.is_empty():
			battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": factory_mix[army % factory_mix.size()]})
			cash -= 900
	for b in battle.structures(team, "airfield"):
		if b.prod_queue.is_empty() and cash >= 2200 and not air_mix.is_empty() and battle.produce_problem(b, air_mix[0]) == "":
			battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": air_mix[waves % air_mix.size()]})


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
				battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, e.position)})
			return
	attacking = attacking.filter(func(id): return battle.by_id.has(id) and not battle.by_id[id].dead)
	_retreat(fighters)
	# attack when the idle army is big enough
	var idle := fighters.filter(func(u): return not (u.uid in attacking) and not retreating.has(u.uid) and u.uid != scout_uid and u.state == Unit.S.IDLE)
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
		wave_n0 = attacking.size()
		last_attack_t = battle.sim_time
		waves += 1
	# attackers that went idle (target area cleared) push on to the next enemy structure
	var done := fighters.filter(func(u): return u.uid in attacking and u.state == Unit.S.IDLE)
	if not done.is_empty():
		var tgt := _enemy_target(done[0].position)
		if tgt != Vector3.INF:
			var ids: Array = done.map(func(u): return u.uid)
			battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, tgt)})


## Research when the economy allows (keeps a reserve for units); picks the Assault plan once it can.
const RESEARCH_ORDER := ["supply_efficiency", "composite_armor", "adv_armor", "adv_training", "guided_munitions"]


func _research() -> void:
	for id in RESEARCH_ORDER:
		if battle.has_upgrade(team, id) or battle.researching_at(team, id): continue
		var d: Dictionary = Upgrades.DEFS[id]
		if battle.cash[team] < int(d.cost) + 2500: return
		for b in battle.structures(team, d.at):
			if battle.research_problem(b, id) == "":
				battle.issue({"type": "research", "team": team, "id": b.uid, "upgrade": id})
				return
	if battle.plan[team] == "" and battle.plan_pending[team] == "" and battle.plan_problem(team, "assault") == "":
		battle.issue({"type": "plan", "team": team, "plan": "assault"})


## Oil derricks: send a pair of idle infantry to the nearest derrick we do not own (one team at a time).
func _capture_derricks() -> void:
	if battle.derricks.is_empty(): return
	for e in battle.derricks:
		if e.owner == team: capturing.erase(e.id)
	for id in capturing.keys():
		capturing[id] = capturing[id].filter(func(x): return battle.by_id.has(x) and not battle.by_id[x].dead)
	var inf := _mine(func(u): return u.def.get("visual") == "infantry" and u.state == Unit.S.IDLE and not (u.uid in attacking))
	var busy := {}
	for id in capturing:
		for x in capturing[id]: busy[x] = true
	inf = inf.filter(func(u): return not busy.has(u.uid))
	if inf.size() < 2: return
	var home: Vector3 = battle.start_pos[team]
	var best: Dictionary = {}
	var bd := INF
	for e in battle.derricks:
		if e.owner == team: continue
		if not capturing.get(e.id, []).is_empty(): continue
		var d := home.distance_to(e.pos)
		if d < bd: bd = d; best = e
	if best.is_empty(): return
	inf.sort_custom(func(a, b): return a.flat_dist(best.pos) < b.flat_dist(best.pos))
	var ids: Array = [inf[0].uid, inf[1].uid]
	capturing[best.id] = ids
	battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": [best.pos + Vector3(3, 0, 3), best.pos + Vector3(-3, 0, 3)]})


## Target: the nearest enemy we know about - remembered structures first (victory needs them gone), then enemy units
## in sight now; nothing known yet -> the enemy start position (starts are known on 1 v 1 maps).
func _enemy_target(from: Vector3) -> Vector3:
	var best := Vector3.INF
	var bd := INF
	for id in known.keys():
		var u: Unit = battle.by_id.get(id)
		if u == null or u.dead:
			known.erase(id)
			continue
		var d: float = from.distance_to(known[id])
		if d < bd: bd = d; best = known[id]
	for u in _in_sight:
		if u.dead or u is Building: continue
		var d2: float = from.distance_to(u.position) * 1.6
		if d2 < bd: bd = d2; best = u.position
	if best == Vector3.INF:
		var enemy_start: Vector3 = battle.start_pos[1 - team]
		var alive: bool = battle.units.any(func(u): return not u.dead and u.team == 1 - team)
		if alive: best = enemy_start
	return best


## What our units can see right now (sight radius); enemy structures seen are remembered.
var _in_sight: Array = []


func _look() -> void:
	_in_sight.clear()
	var mine := _mine(func(u): return true)
	for e in battle.units:
		if e.dead or e.team == team or e.team < 0: continue
		for m in mine:
			if m.flat_dist(e.position) <= m.sight_r():
				_in_sight.append(e)
				if e is Building: known[e.uid] = e.position
				break


## Scouting: every ~75 s one fast, cheap unit drives past the enemy start, the oil derricks and the map centre.
const SCOUT_KINDS := ["hmmwv", "hmmwv_50cal", "ir_boragh", "mrap", "rifleman", "ir_rifleman"]


func _scout() -> void:
	var s: Unit = battle.by_id.get(scout_uid)
	if s and not s.dead:
		if s.state == Unit.S.IDLE and s.queue.is_empty(): scout_uid = -1      # trip finished: back into the army
		return
	scout_uid = -1
	if battle.sim_time < scout_t: return
	scout_t = battle.sim_time + 75.0
	var pick: Unit = null
	for k in SCOUT_KINDS:
		for u in _mine(func(x): return x.kind == k and x.state == Unit.S.IDLE and not (x.uid in attacking)):
			pick = u; break
		if pick: break
	if pick == null: return
	scout_uid = pick.uid
	var route: Array = [battle.start_pos[1 - team] + Vector3(0, 0, 60.0 * _fwd())]
	for e in battle.derricks: route.append(e.pos)
	route.append(Vector3.ZERO)
	route.append(battle.start_pos[team] + Vector3(0, 0, 70.0 * _fwd()))
	battle.issue({"type": "move", "team": team, "ids": [pick.uid], "points": [route[0]]})
	for i in range(1, route.size()):
		battle.issue({"type": "move", "team": team, "ids": [pick.uid], "points": [route[i]], "append": true})


## Occupy civilian buildings near our base with spare infantry (one building at a time, three soldiers).
func _garrison() -> void:
	for id in garrisoning.keys():
		var b: Unit = battle.by_id.get(id)
		if b == null or b.dead or b.team == 1 - team:
			garrisoning.erase(id); continue
		garrisoning[id] = garrisoning[id].filter(func(x): return battle.by_id.has(x) and not battle.by_id[x].dead and battle.by_id[x].board_target != null)
		if garrisoning[id].is_empty(): garrisoning.erase(id)
	if not garrisoning.is_empty(): return
	var cc := _cc()
	if cc == null: return
	var inf := _mine(func(u): return u.def.get("visual") == "infantry" and u.state == Unit.S.IDLE and not (u.uid in attacking) and u.board_target == null)
	if inf.size() < 5: return
	var best: Building = null
	var bd := 260.0
	for u in battle.units:
		if not (u is Building) or u.dead or not (u as Building).is_civic(): continue
		if not (u.team < 0 or (u.team == team and u.capacity_left() >= 3)): continue
		var d: float = cc.position.distance_to(u.position)
		if d < bd: bd = d; best = u
	if best == null: return
	inf.sort_custom(func(a, b): return a.flat_dist(best.position) < b.flat_dist(best.position))
	var ids: Array = inf.slice(0, 3).map(func(u): return u.uid)
	garrisoning[best.uid] = ids
	battle.issue({"type": "board", "team": team, "ids": ids, "target": best.uid})


## Fall back: attackers below 30 % health go home for repair (vehicles to the War Factory bay); a wave that lost more
## than 60 % of its strength is called off - everyone regroups at home and the next wave is two units bigger.
func _retreat(fighters: Array) -> void:
	var cc := _cc()
	var home: Vector3 = cc.position + Vector3(0, 0, 40.0 * _fwd()) if cc else battle.start_pos[team]
	var wfs: Array = battle.structures(team, "war_factory")
	for id in retreating.keys():
		var u: Unit = battle.by_id.get(id)
		if u == null or u.dead or u.hp >= u.def.hp * 0.9 or battle.sim_time - float(retreating[id]) > 75.0: retreating.erase(id)
	var back: Array = []
	for u in fighters:
		if u.uid in attacking and u.hp < u.def.hp * 0.3 and not retreating.has(u.uid):
			back.append(u)
	if wave_n0 > 0 and not attacking.is_empty() and attacking.size() < wave_n0 * 0.4 and battle.sim_time - last_attack_t > 20.0:
		for id in attacking:
			var u: Unit = battle.by_id.get(id)
			if u and not u.dead and not (u in back): back.append(u)
		attack_size = mini(attack_size + 2, 16)
		wave_n0 = 0
	for u in back:
		attacking.erase(u.uid)
		retreating[u.uid] = battle.sim_time
		var dest: Vector3 = home
		if u.def.get("visual") != "infantry" and u.domain == "ground" and not wfs.is_empty():
			var wf: Building = wfs[0]
			dest = wf.position + wf.front_dir() * (wf.half.y + 8.0)
		battle.issue({"type": "move", "team": team, "ids": [u.uid], "points": [dest]})

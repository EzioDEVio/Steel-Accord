# Steel Accord - skirmish opponent (B1.2, reworked in B3). Deterministic: decisions depend only on simulation state
# and sim time, and every action goes through Battle.issue() like the player's orders (so it is logged for replays).
#
# Knowledge model (fair play): the AI targets only enemy structures its units have seen (remembered in `known`),
# enemy units its units see now, and enemy units it has seen recently (`enemy_seen`, which ages out). It never reads
# the enemy's hidden state.
#
# Economy: build order around its Command Center, extra Power Plants when power runs short, haulers scaled with the
# distance to the remaining supply, derrick capture, a Supply Drop Zone and more production when rich; anything lost
# is rebuilt.
# Production: a value budget per combat role (infantry, anti-tank, light vehicles, armour, anti-air, artillery,
# helicopters, jets) that adapts to the enemy composition it has seen; the role furthest below its share is bought
# first and cheap units do not starve the War Factory (the old infantry-only bug).
# Army: task forces. Units gather at a rally point; a combined-arms group (armour leading, infantry / anti-tank
# behind, anti-air and artillery at the rear) leaves only when its strength beats the estimated defence of the chosen
# objective, advances in legs and waits for stragglers, bombards defences with artillery, focuses fire, sends hurt
# units home, takes reinforcements, and is recalled to defend the base. Hard adds a feint before the main thrust.
# Air: helicopters and jets strike high-value targets that are light on anti-air; support powers are used on
# clustered or valuable targets only, classified by their data keys so new powers work without code changes.
class_name BaseAI
extends RefCounted

var battle: Node
var team := 1
var difficulty := "Normal"
var think_t := 0.0
var think_every := 1.5
var attack_size := 7
var attack_after := 150.0
var waves := 0
var attacking: Array = []      # uids sent on the current (main) attack
var capturing := {}            # derrick id -> uids sent to capture it
var known := {}                # enemy structure uid -> position (seen by our units at least once)
var scout_t := 40.0            # sim time of the next scouting trip
var scout_uid := -1
var retreating := {}           # uid -> sim time the retreat started
var wave_n0 := 0               # strength of the current attack wave when it left
var last_attack_t := -999.0
var losses_seen := 0
var garrisoning := {}          # civic building uid -> uids sent to occupy it
# B3 state (saved; plain data and uids only)
var enemy_seen := {}           # enemy unit uid -> [kind, position, sim time last seen]
var seen_derricks := {}        # derrick id -> owner when we last saw it
var tf_obj := Vector3.INF      # current objective of the main task force
var tf_leg := Vector3.INF      # current waypoint of the main task force
var tf_stage := ""             # "" (gathering) | "move" | "engage"
var tf_t := 0.0                # sim time the current stage / leg started
var feint: Array = []          # uids of the feint group (Hard)
var air_tasks := {}            # aircraft uid -> target uid (strike in progress)
var next_power_t := 0.0
var save_t := -1.0             # sim time we started saving cash for an expensive unit
var prod_n := 0                # production counter (deterministic rotation inside a role)
var bombarded := false         # artillery has opened up on the current objective
var defending := false
var last_recon_t := -999.0
var tf_best := INF             # closest the task force has been to its objective (progress watchdog)
var tf_prog_t := 0.0           # sim time of the last progress
var tf_stuck := 0
var air_danger := {}           # "cell" -> [position, sim time] where we lost aircraft
var place_fail := {}           # structure kind -> sim time until which placement is not retried

# Diagnostics for tests and the match timeline (not saved; they never feed back into decisions).
var events: Array = []         # [sim time, text]
var stats := {"air_strikes": 0, "air_sorties": 0, "powers": [], "bombard": 0, "defend": 0, "focus": 0, "feints": 0, "recon": 0}

# build order (kind, local x, local forward offset from the Command Center; forward = toward the map centre)
const ORDER := [
	["power_plant", -36, -6], ["barracks", 36, 14], ["supply_depot", 40, -16], ["power_plant", -36, 16],
	["war_factory", 0, 42], ["power_plant", -60, 2], ["airfield", -100, 70], ["defense_tower", -26, 64], ["defense_tower", 26, 64],
	["power_plant", -60, 22], ["drop_zone", 70, 20], ["hesco", -12, 70], ["hesco", 12, 70],
]
## Built after ORDER when cash allows (difficulty decides how many).
const LATE_ORDER := [["war_factory", 60, 48], ["power_plant", -84, 10], ["barracks", 70, -10], ["defense_tower", 0, 80], ["power_plant", -84, 30]]
const BARRACKS_MIX := ["rifleman", "rifleman", "at4"]
const FACTORY_MIX := ["abrams", "hmmwv_50cal", "bradley", "avenger", "abrams", "paladin"]
const AIR_MIX := ["ah64", "a10"]
var barracks_mix: Array = BARRACKS_MIX
var factory_mix: Array = FACTORY_MIX
var air_mix: Array = AIR_MIX

const ROLES := ["inf", "at", "light", "armor", "aa", "arty", "heli", "jet"]
## Value share of the standing army per role before adapting to the enemy.
const BASE_SHARE := {"inf": 0.17, "at": 0.12, "light": 0.07, "armor": 0.30, "aa": 0.06, "arty": 0.08, "heli": 0.11, "jet": 0.09}
## Structure values used by objective scoring (higher = better target).
const OBJ_WEIGHT := {"war_factory": 3.0, "supply_depot": 3.2, "airfield": 2.6, "power_plant": 2.4, "barracks": 2.0, "drop_zone": 2.2,
	"command_center": 1.6, "radar": 1.5, "defense_tower": 0.8, "hesco": 0.1}

## Difficulty profiles. Easy: slow, timid, small air arm, few powers. Hard: fast, bold, feints, focus fire everywhere.
const PROFILES := {
	"Easy": {"think": 3.0, "size": 10, "after": 300.0, "ratio": 1.6, "haulers": 2, "air_cap": 1, "late": 0, "focus": false, "feint": false,
		"power_gap": 75.0, "power_min": 2500.0, "reserve": 600, "patience": 300.0, "aa_avoid": 1, "research": false},
	"Normal": {"think": 1.5, "size": 8, "after": 200.0, "ratio": 1.25, "haulers": 3, "air_cap": 3, "late": 2, "focus": true, "feint": false,
		"power_gap": 25.0, "power_min": 1500.0, "reserve": 300, "patience": 200.0, "aa_avoid": 2, "research": true},
	"Hard": {"think": 1.0, "size": 6, "after": 120.0, "ratio": 1.0, "haulers": 4, "air_cap": 5, "late": 5, "focus": true, "feint": true,
		"power_gap": 10.0, "power_min": 1000.0, "reserve": 200, "patience": 150.0, "aa_avoid": 3, "research": true},
}
var P: Dictionary = PROFILES.Normal
var role_kinds := {}           # role -> [[structure kind, unit kind], ...] this nation can build


func _init(b: Node, t: int, diff: String) -> void:
	battle = b; team = t
	difficulty = diff if PROFILES.has(diff) else "Normal"
	P = PROFILES[difficulty]
	think_every = float(P.think); attack_size = int(P.size); attack_after = float(P.after)
	var nat: String = battle.nation_of(team)
	barracks_mix = Nations.mix(nat, "barracks", BuildingDefs.DEFS.barracks.produces, BARRACKS_MIX + (["special_forces"] if nat != "usa" else []))
	factory_mix = Nations.mix(nat, "war_factory", BuildingDefs.DEFS.war_factory.produces, FACTORY_MIX)
	air_mix = Nations.mix(nat, "airfield", BuildingDefs.DEFS.airfield.produces, AIR_MIX)
	for r in ROLES: role_kinds[r] = []
	for bk in ["barracks", "war_factory", "airfield"]:
		for k in Nations.produces(nat, bk, BuildingDefs.DEFS[bk].produces):
			var r := role_of_def(UnitDefs.def_of(k))
			if r != "" and BuildingDefs.UNIT_COST.has(k): role_kinds[r].append([bk, k])
	if battle._automated() and "aifast" in battle.args:
		attack_after = 60.0; attack_size = 4
		P = P.duplicate(); P.ratio = 0.5; P.patience = 60.0


func _ev(text: String) -> void:
	events.append([battle.sim_time, text])
	if events.size() > 400: events.pop_front()


## Unit by uid, or null when it is gone (dead units are freed after their fade-out but may linger in by_id).
func _u(id: Variant) -> Unit:
	var o: Variant = battle.by_id.get(id)
	if o == null or not is_instance_valid(o): return null
	return o as Unit


func _cc() -> Node:
	var c: Array = battle.structures(team, "command_center")
	return c[0] if not c.is_empty() else null


func _fwd() -> float:
	return 1.0 if battle.start_pos[team].z < 0.0 else -1.0


func _mine(pred: Callable) -> Array:
	return battle.units.filter(func(u): return u.team == team and not u.dead and pred.call(u))


func _home() -> Vector3:
	var cc := _cc()
	return cc.position if cc else battle.start_pos[team]


## Rally point in front of the base, toward the map centre.
func _rally() -> Vector3:
	return battle.grounded(_home() + Vector3(0, 0, 70.0 * _fwd()))


# ------------------------------------------------------------------ classification
## Combat role from a unit definition ("" = not an army unit: builders, haulers, transports and unarmed support).
static func role_of_def(d: Dictionary) -> String:
	if d.get("builder", false) or d.get("hauler", false): return ""
	var ws: Array = d.get("weapons", [])
	if ws.is_empty(): return ""
	var dom := str(d.get("domain", "ground"))
	var ground_w := ws.filter(func(w): return "ground" in w.targets)
	if dom == "jet": return "jet" if not ground_w.is_empty() else ""
	if dom == "heli": return "" if d.has("transport") else "heli"
	if ground_w.is_empty(): return "aa"
	for w in ws:
		if str(w.get("proj", "")) == "arty": return "arty"
	if str(d.get("visual", "")) == "infantry":
		if d.has("heal"): return ""
		for w in ws:
			if str(w.get("proj", "")) in ["rocket", "missile"]: return "at"
		return "inf"
	if str(d.get("armor", "")) == "heavy":
		for w in ws:
			if str(w.get("proj", "")) == "shell" and float(w.damage) >= 100.0: return "armor"
		for w in ws:
			if str(w.get("proj", "")) == "missile": return "armor"    # IFVs with guided missiles fight in the tank line
	return "light"


func role_of(u: Unit) -> String:
	if u is Building: return ""
	return role_of_def(u.def)


static func value_of_kind(k: String) -> float:
	if BuildingDefs.UNIT_COST.has(k): return float(BuildingDefs.UNIT_COST[k][0])
	if BuildingDefs.DEFS.has(k): return float(BuildingDefs.DEFS[k].cost)
	return float(UnitDefs.def_of(k).get("cost", 300))


func value_of(u: Unit) -> float:
	var v := float((u as Building).bdef.cost) if u is Building else value_of_kind(u.kind)
	return v * clampf(u.hp / maxf(1.0, float(u.def.hp)), 0.2, 1.0)


func _is_aa_threat(u: Unit) -> bool:
	for w in u.def.get("weapons", []):
		if "jet" in w.targets or ("heli" in w.targets and str(w.get("proj", "")) == "missile"): return true
	return false


# ------------------------------------------------------------------ main loop
func tick(dt: float) -> void:
	think_t -= dt
	if think_t > 0.0: return
	think_t = think_every
	var cc := _cc()
	var anchor: Vector3 = cc.position if cc else battle.start_pos[team]
	_look()
	_construct(anchor)
	_produce(cc)
	_capture_derricks()
	if P.research: _research()
	_scout()
	_garrison()
	_army()
	_air()
	_powers()


## Next unbuilt entry of the build order: count how many of each kind we have and find the first shortfall.
## Power comes first: a plant is added whenever the margin drops below 2. Rich bases add the late order.
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
	if battle.structures(team, "power_plant", false).size() > 0 and battle.power_gen(team) < battle.power_use(team) + 2 \
			and battle.cash[team] >= 1000:
		var npp: int = battle.structures(team, "power_plant", false).size()
		_place_near(dz, anchor, "power_plant", -70.0 - 22.0 * float(npp % 3), 40.0 - 20.0 * float(npp % 2))
		return
	var need := {}
	var order: Array = ORDER.duplicate()
	if battle.cash[team] > 3500 + int(P.reserve) * 4 and battle.sim_time > 300.0:
		order += LATE_ORDER.slice(0, int(P.late))
	for e in order:
		need[e[0]] = int(need.get(e[0], 0)) + 1
		var count: int = battle.structures(team, e[0], false).size()
		if count >= int(need[e[0]]): continue
		var k: String = e[0]
		if k == "airfield" and role_kinds.jet.is_empty() and role_kinds.heli.is_empty(): continue
		if battle.sim_time < float(place_fail.get(k, -1.0)): continue      # no room found recently: build the next item
		if battle.cash[team] < int(BuildingDefs.DEFS[k].cost) + int(P.reserve): return   # keep a small reserve for units
		if not battle.requirements_met(team, k): return
		if not _place_near(dz, anchor, k, float(e[1]), float(e[2])): place_fail[k] = battle.sim_time + 30.0
		return


func _place_near(dz: Unit, anchor: Vector3, k: String, x: float, f: float) -> bool:
	var pos := _slot(anchor, x, f)
	var big: bool = (BuildingDefs.DEFS[k].size as Vector2).x > 40.0
	var n_try := (70 if big else 40) if battle.terrain else 16      # hills: search wider for flat ground
	var step := 3.5 if big else 2.0
	for tries in n_try:
		if battle.placement_problem(team, k, pos) == "": break
		var a := tries * 0.9
		pos = _slot(anchor, x + cos(a) * (6.0 + tries * step), f + sin(a) * (6.0 + tries * step))
	if battle.placement_problem(team, k, pos) == "":
		battle.issue({"type": "place", "team": team, "id": k, "pos": pos, "builder": dz.uid})
		_ev("builds %s" % k)
		return true
	return false


func _slot(anchor: Vector3, x: float, f: float) -> Vector3:
	return anchor + Vector3(x * -_fwd(), 0, f * _fwd())


# ------------------------------------------------------------------ production
## Desired value share per role, adapted to what we have seen of the enemy army.
func _shares() -> Dictionary:
	var s: Dictionary = BASE_SHARE.duplicate()
	var ev := {"inf": 0.0, "armor": 0.0, "air": 0.0, "light": 0.0}
	var tot := 0.0
	for id in enemy_seen:
		var e: Array = enemy_seen[id]
		var d: Dictionary = UnitDefs.def_of(e[0])
		var v := value_of_kind(e[0])
		tot += v
		var dom := str(d.get("domain", "ground"))
		if dom in ["jet", "heli"]: ev.air += v
		elif str(d.get("visual", "")) == "infantry": ev.inf += v
		elif str(d.get("armor", "")) == "heavy": ev.armor += v
		else: ev.light += v
	if tot > 1500.0:
		var air: float = ev.air / tot; var arm: float = ev.armor / tot; var inf: float = ev.inf / tot
		s.aa = clampf(air * 0.7, 0.05, 0.28)
		s.at += arm * 0.12; s.armor += arm * 0.06; s.heli += arm * 0.05
		s.inf += inf * 0.08; s.light += inf * 0.06; s.arty += inf * 0.04
	if role_kinds.jet.is_empty(): s.jet = 0.0
	if role_kinds.heli.is_empty(): s.heli = 0.0
	return s


func _produce(cc: Node) -> void:
	var cash: int = battle.cash[team]
	var nat: String = battle.nation_of(team)
	if cc and _mine(func(u): return u.def.get("builder", false)).is_empty() and cc.prod_queue.is_empty() and cash >= 1000:
		battle.issue({"type": "produce", "team": team, "id": cc.uid, "kind": Nations.swap_unit(nat, "dozer")})
		return
	# haulers: more when the supply left is far from the depot
	var haulers := _mine(func(u): return u.def.get("hauler", false)).size()
	var want_h := int(P.haulers)
	var depots: Array = battle.structures(team, "supply_depot")
	if not depots.is_empty():
		var pl: Dictionary = battle.nearest_pile(depots[0].position)
		if pl.is_empty(): want_h = 1
		elif depots[0].position.distance_to(pl.pos) > 180.0: want_h += 1
	for d in depots:
		var hk := Nations.swap_unit(nat, "ch47")
		if haulers < want_h * depots.size() and d.prod_queue.is_empty() and cash >= value_of_kind(hk) + 400 and battle.sim_time > 60.0:
			battle.issue({"type": "produce", "team": team, "id": d.uid, "kind": hk})
			_ev("orders hauler (%d/%d)" % [haulers + 1, want_h * depots.size()])
			cash -= int(value_of_kind(hk))
			haulers += 1
	# army value per role, including what is queued
	var have := {}
	for r in ROLES: have[r] = 0.0
	var total := 0.0
	for u in battle.units:
		if u.team != team or u.dead: continue
		if u is Building:
			for k in (u as Building).prod_queue:
				var rq := role_of_def(UnitDefs.def_of(k))
				if rq != "": have[rq] += value_of_kind(k); total += value_of_kind(k)
			continue
		var r := role_of(u)
		if r == "": continue
		have[r] += value_of_kind(u.kind); total += value_of_kind(u.kind)
	var shares := _shares()
	var target_total := maxf(total + 1500.0, 6000.0)
	# air cap (pads and difficulty)
	var air_n := _mine(func(u): return u.is_air() and role_of(u) in ["heli", "jet"]).size()
	var airfields: Array = battle.structures(team, "airfield")
	for af in airfields: air_n += af.prod_queue.size()
	var air_cap := mini(int(P.air_cap), 4 * airfields.size())
	# best request per production structure: the role furthest below its share that this structure can make
	var reqs: Array = []
	for b in battle.structures(team):
		if not (b.bkind in ["barracks", "war_factory", "airfield"]): continue
		var qmax := 2 if b.bkind == "barracks" else 1
		if b.prod_queue.size() >= qmax: continue
		var best_r := ""; var best_def := 0.0
		for r in ROLES:
			if role_kinds[r].filter(func(e): return e[0] == b.bkind).is_empty(): continue
			if r in ["heli", "jet"] and air_n >= air_cap: continue
			var deficit: float = float(shares[r]) * target_total - float(have[r])
			if deficit > best_def: best_def = deficit; best_r = r
		if best_r == "": continue
		var opts: Array = role_kinds[best_r].filter(func(e): return e[0] == b.bkind).map(func(e): return e[1])
		var quick: Array = opts.filter(func(x): return float(UnitDefs.def_of(x).get("speed", 10.0)) >= 6.0)
		if not quick.is_empty(): opts = quick         # towed guns cannot keep up with a task force
		var k: String = opts[prod_n % opts.size()]
		if b.bkind == "airfield" and battle.produce_problem(b, k) == "No free pad": continue
		reqs.append([best_def, b, k, best_r])
	reqs.sort_custom(func(a, c): return a[0] > c[0])
	for rq in reqs:
		var k: String = rq[2]
		var cost := int(value_of_kind(k))
		if cash >= cost:
			battle.issue({"type": "produce", "team": team, "id": rq[1].uid, "kind": k})
			cash -= cost
			have[rq[3]] += cost
			prod_n += 1
			if cost >= 700: save_t = -1.0
		else:
			# save for the most-needed unit instead of spending everything on cheap infantry; give up after 25 s
			if save_t < 0.0: save_t = battle.sim_time
			if battle.sim_time - save_t < 25.0: break


## Research when the economy allows (keeps a reserve for units); picks the Assault plan once it can.
const RESEARCH_ORDER := ["supply_efficiency", "composite_armor", "adv_armor", "adv_training", "guided_munitions"]


func _research() -> void:
	# army and production come first: no research before the War Factory is up and the opening is over
	if battle.structures(team, "war_factory").is_empty() or battle.sim_time < 240.0: return
	for id in RESEARCH_ORDER:
		if battle.has_upgrade(team, id) or battle.researching_at(team, id): continue
		var d: Dictionary = Upgrades.DEFS[id]
		if battle.cash[team] < int(d.cost) + 2500: return
		for b in battle.structures(team, d.at):
			if battle.research_problem(b, id) == "":
				battle.issue({"type": "research", "team": team, "id": b.uid, "upgrade": id})
				_ev("researches %s" % id)
				return
	if battle.plan[team] == "" and battle.plan_pending[team] == "" and battle.plan_problem(team, "assault") == "":
		battle.issue({"type": "plan", "team": team, "plan": "assault"})


## Oil derricks: send a pair of idle infantry to the nearest derrick we do not own (one team at a time).
func _capture_derricks() -> void:
	if battle.derricks.is_empty(): return
	for e in battle.derricks:
		if e.owner == team: capturing.erase(e.id)
	for id in capturing.keys():
		capturing[id] = capturing[id].filter(func(x): return _u(x) != null and not _u(x).dead)
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
	_ev("sends 2 infantry to capture derrick %s" % str(best.id))


# ------------------------------------------------------------------ knowledge
## What our units can see right now (sight radius); enemy structures seen are remembered, enemy units are
## remembered with the time they were seen (strength estimates), derrick owners as last seen.
var _in_sight: Array = []


func _look() -> void:
	_in_sight.clear()
	var mine := _mine(func(u): return true)
	var zones: Array = battle.reveal_zones.filter(func(z): return int(z.team) == team)   # our recon overflights
	for e in battle.units:
		if e.dead or e.team == team or e.team < 0: continue
		var seen_by := false
		for m in mine:
			if m.flat_dist(e.position) <= m.sight_r(): seen_by = true; break
		if not seen_by:
			for z in zones:
				if battle._dist_to_segment(Vector3(e.position.x, 0, e.position.z), Vector3(z.a.x, 0, z.a.z), Vector3(z.b.x, 0, z.b.z)) <= float(z.w) * 0.5:
					seen_by = true; break
		if seen_by:
			_in_sight.append(e)
			if e is Building: known[e.uid] = e.position
			else: enemy_seen[e.uid] = [e.kind, e.position, battle.sim_time]
	for e in battle.derricks:
		for m in mine:
			if m.flat_dist(e.pos) <= m.sight_r():
				seen_derricks[e.id] = e.owner
				break
	# forget: units not seen for 150 s, or whose last position we can see now without them there
	for id in enemy_seen.keys():
		var r: Array = enemy_seen[id]
		var u: Unit = _u(id)
		if battle.sim_time - float(r[2]) > 150.0:
			enemy_seen.erase(id); continue
		if float(r[2]) < battle.sim_time - 0.01 and (u == null or u.dead or not (u in _in_sight)):
			for m in mine:
				if m.flat_dist(r[1]) <= m.sight_r() * 0.8:
					enemy_seen.erase(id); break


## Estimated enemy strength (value) within r of p, from what we know: units seen recently and remembered structures
## that shoot (defence towers count double).
func _threat_at(p: Vector3, r: float) -> float:
	var v := 0.0
	for id in enemy_seen:
		var e: Array = enemy_seen[id]
		if (e[1] as Vector3).distance_to(p) <= r and role_of_def(UnitDefs.def_of(e[0])) != "":
			v += value_of_kind(e[0])
	for id in known:
		var b: Unit = _u(id)
		if b == null or b.dead: continue
		if (known[id] as Vector3).distance_to(p) <= r and not (b as Building).bdef.get("weapons", []).is_empty():
			v += float((b as Building).bdef.cost) * 2.0
	return v


## Anti-air pieces known near p (units seen recently, remembered towers).
func _aa_at(p: Vector3, r: float) -> int:
	var n := 0
	for id in enemy_seen:
		var e: Array = enemy_seen[id]
		if (e[1] as Vector3).distance_to(p) > r: continue
		var u: Unit = _u(id)
		if u and _is_aa_threat(u): n += 1
	for id in known:
		var b: Unit = _u(id)
		if b and not b.dead and (known[id] as Vector3).distance_to(p) <= r and _is_aa_threat(b): n += 1
	# places where we lost aircraft recently count as defended even if we never saw what shot them down
	for k in air_danger:
		var dp: Array = air_danger[k]
		if battle.sim_time - float(dp[1]) < 300.0 and (dp[0] as Vector3).distance_to(p) < r + 40.0: n += 2
	return n


func _enemy_army_value() -> float:
	var v := 0.0
	for id in enemy_seen:
		if role_of_def(UnitDefs.def_of(enemy_seen[id][0])) != "": v += value_of_kind(enemy_seen[id][0])
	return v


## Target: the nearest enemy we know about - remembered structures first (victory needs them gone), then enemy units
## in sight now; nothing known yet -> the enemy start position (starts are known on 1 v 1 maps).
func _enemy_target(from: Vector3) -> Vector3:
	var best := Vector3.INF
	var bd := INF
	for id in known.keys():
		var u: Unit = _u(id)
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


## Objective for a task force: scored over remembered structures, enemy-held derricks we have seen and enemy army
## groups in the open; value / (estimated defence) with a mild preference for nearer targets.
func _pick_objective(from: Vector3, exclude := Vector3.INF) -> Vector3:
	var best := Vector3.INF
	var bs := -1.0
	var cands: Array = []
	for id in known.keys():
		var b: Unit = _u(id)
		if b == null or b.dead: known.erase(id); continue
		cands.append([known[id], float(OBJ_WEIGHT.get((b as Building).bkind, 1.0))])
	for e in battle.derricks:
		if int(seen_derricks.get(e.id, -1)) == 1 - team: cands.append([e.pos, 2.8])
	for u in _in_sight:
		if u.dead or u is Building or role_of(u) == "" or u.is_air(): continue
		cands.append([u.position, 1.2 + value_of(u) / 1500.0])
	for c in cands:
		var p: Vector3 = c[0]
		if exclude != Vector3.INF and p.distance_to(exclude) < 120.0: continue
		var s: float = float(c[1]) * 1000.0 / (_threat_at(p, 110.0) + 600.0) / (1.0 + from.distance_to(p) / 400.0)
		if s > bs: bs = s; best = p
	if best == Vector3.INF and exclude == Vector3.INF: best = _enemy_target(from)
	return best


# ------------------------------------------------------------------ scouting and garrisons
## Scouting: every ~75 s one fast, cheap unit drives past the enemy start, the oil derricks and the map centre.
const SCOUT_KINDS := ["hmmwv", "hmmwv_50cal", "ir_boragh", "mrap", "rifleman", "ir_rifleman"]


func _scout() -> void:
	var s: Unit = _u(scout_uid)
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
	_ev("scouts with %s" % pick.kind)


## Occupy civilian buildings near our base with spare infantry (one building at a time, three soldiers).
func _garrison() -> void:
	for id in garrisoning.keys():
		var b: Unit = _u(id)
		if b == null or b.dead or b.team == 1 - team:
			garrisoning.erase(id); continue
		garrisoning[id] = garrisoning[id].filter(func(x): return _u(x) != null and not _u(x).dead and _u(x).board_target != null)
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


# ------------------------------------------------------------------ army: task forces
func _fighters() -> Array:
	return _mine(func(u): return not (u is Building) and not u.def.get("builder", false) \
		and not u.def.get("hauler", false) and u.def.get("weapons", []).size() > 0 and u.domain == "ground")


func _centroid(us: Array) -> Vector3:
	var c := Vector3.ZERO
	for u in us: c += u.position
	return c / maxf(1.0, float(us.size()))


func _alive_ids(ids: Array) -> Array:
	return ids.filter(func(id): return _u(id) != null and not _u(id).dead)


func _army() -> void:
	var fighters := _fighters()
	if fighters.is_empty(): return
	attacking = _alive_ids(attacking)
	feint = _alive_ids(feint)
	_retreat(fighters)
	if _defend(fighters): return
	defending = false
	var busy := {}
	for id in capturing:
		for x in capturing[id]: busy[x] = true
	for id in garrisoning:
		for x in garrisoning[id]: busy[x] = true
	var pool := fighters.filter(func(u): return not (u.uid in attacking) and not (u.uid in feint) and not retreating.has(u.uid) \
		and u.uid != scout_uid and not busy.has(u.uid) and u.board_target == null and u.state in [Unit.S.IDLE, Unit.S.MOVE, Unit.S.GUARD, Unit.S.ATTACK_MOVE])
	if attacking.is_empty():
		tf_stage = ""
		_gather(pool)
	else:
		_reinforce(pool)
		_advance()
	_feint_tick()


## Pool units collect at the rally point; the task force leaves when it is big enough and strong enough for the
## objective (or when it has waited too long and is at least close to even).
func _gather(pool: Array) -> void:
	var rally := _rally()
	var ready: Array = []
	for u in pool:
		if u.flat_dist(rally) > 45.0 and u.state == Unit.S.IDLE:
			battle.issue({"type": "move", "team": team, "ids": [u.uid], "points": [rally + Vector3(float(u.uid % 7) * 5.0 - 15.0, 0, float(u.uid % 5) * 5.0 - 10.0)]})
		if u.flat_dist(rally) < 80.0 or u.state == Unit.S.IDLE: ready.append(u)
	if battle.sim_time < attack_after or ready.size() < attack_size: return
	var my_val := 0.0
	var veh := 0.0
	for u in ready:
		my_val += value_of(u)
		if u.def.get("visual") != "infantry": veh += value_of(u)
	var obj := _pick_objective(_centroid(ready))
	if obj == Vector3.INF: return
	var defence := _threat_at(obj, 130.0) + 0.5 * maxf(0.0, _enemy_army_value() - _threat_at(obj, 130.0))
	var ratio := my_val / maxf(1.0, defence)
	var waited: float = battle.sim_time - maxf(last_attack_t, attack_after)
	var has_factory: bool = not battle.structures(team, "war_factory").is_empty()
	# wait for armour when we can build it (combined arms), unless we have waited long
	if has_factory and veh < my_val * 0.3 and waited < float(P.patience): return
	var go: bool = ratio >= float(P.ratio) or (waited > float(P.patience) and ratio >= float(P.ratio) * 0.6) or my_val > 16000.0
	if not go: return
	# recon before the attack when a recon power is ready
	_try_power_kind("reveal", obj)
	var ids: Array = ready.map(func(u): return u.uid)
	if P.feint and ready.size() >= 8:
		var lights := ready.filter(func(u): return role_of(u) in ["light", "inf"])
		var fobj := _pick_objective(_centroid(ready), obj)
		if lights.size() >= 3 and fobj != Vector3.INF:
			var fids: Array = lights.slice(0, maxi(3, ready.size() / 4)).map(func(u): return u.uid)
			feint = fids
			ids = ids.filter(func(id): return not (id in fids))
			battle.issue({"type": "attack_move", "team": team, "ids": fids, "points": battle.spread(fids, fobj)})
			stats.feints += 1
			_ev("feint: %d units toward (%d, %d)" % [fids.size(), int(fobj.x), int(fobj.z)])
	attacking = ids
	wave_n0 = attacking.size()
	last_attack_t = battle.sim_time
	waves += 1
	tf_obj = obj
	tf_stage = "move"
	tf_t = battle.sim_time
	tf_leg = Vector3.INF
	bombarded = false
	tf_stuck = 0; tf_best = INF; tf_prog_t = battle.sim_time
	_ev("wave %d launched: %s value %d vs est. defence %d -> objective (%d, %d)" % [waves, _comp_text(attacking), int(my_val), int(defence), int(obj.x), int(obj.z)])
	_next_leg()


func _comp_text(ids: Array) -> String:
	var k := {}
	for id in ids:
		var u: Unit = _u(id)
		if u: k[u.kind] = int(k.get(u.kind, 0)) + 1
	return str(k)


func _tf_units() -> Array:
	return attacking.map(func(id): return _u(id)).filter(func(u): return u != null and not u.dead)


## Next waypoint toward the objective (70 m legs) and a formation order: armour in front, infantry and anti-tank
## behind it, anti-air and artillery at the rear.
func _next_leg() -> void:
	var us := _tf_units()
	if us.is_empty(): return
	var c := _centroid(us)
	var to := tf_obj - c
	to.y = 0.0
	var dist := to.length()
	if dist < 95.0:
		tf_stage = "engage"
		tf_t = battle.sim_time
		var ids: Array = us.map(func(u): return u.uid)
		battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, tf_obj)})
		_ev("wave %d engages at (%d, %d)" % [waves, int(tf_obj.x), int(tf_obj.z)])
		return
	var dir := to / dist
	tf_leg = battle.grounded(c + dir * minf(70.0, dist - 60.0))
	tf_t = battle.sim_time
	var rows := {"armor": 12.0, "light": 6.0, "heli": 6.0, "inf": 0.0, "at": -4.0, "aa": -16.0, "arty": -40.0}
	var groups := {}
	for u in us:
		var r := role_of(u)
		var off: float = float(rows.get(r, 0.0))
		if not groups.has(off): groups[off] = []
		groups[off].append(u.uid)
	for off in groups:
		var ids: Array = groups[off]
		battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, tf_leg + dir * float(off))})


## Task force step: wait for stragglers, advance, bombard, focus fire, push on after the objective falls.
func _advance() -> void:
	var us := _tf_units()
	if us.is_empty(): return
	if tf_obj == Vector3.INF or tf_stage == "":
		tf_obj = _pick_objective(_centroid(us)); tf_stage = "move"
		if tf_obj == Vector3.INF: return
		_next_leg()
		return
	var c := _centroid(us)
	_bombard(us, c)
	if P.focus: _focus_fire(us, c)
	# progress watchdog: a task force that neither closes on its objective nor fights for 100 s is stuck (blocked
	# route, unreachable target): first try another objective, then call the wave off and regroup
	var d_obj := c.distance_to(tf_obj)
	var fighting := us.filter(func(u): return u.target != null).size() * 3 >= us.size()
	if d_obj < tf_best - 15.0 or fighting:
		tf_best = minf(tf_best, d_obj); tf_prog_t = battle.sim_time
	elif battle.sim_time - tf_prog_t > 100.0:
		tf_stuck += 1
		tf_prog_t = battle.sim_time; tf_best = INF
		var alt := _pick_objective(c, tf_obj)
		if tf_stuck <= 1 and alt != Vector3.INF:
			_ev("wave %d makes no progress; switches objective to (%d, %d)" % [waves, int(alt.x), int(alt.z)])
			tf_obj = alt; tf_stage = "move"; bombarded = false
			_next_leg()
		else:
			_ev("wave %d makes no progress; called off to regroup" % waves)
			var ids: Array = us.map(func(u): return u.uid)
			battle.issue({"type": "move", "team": team, "ids": ids, "points": battle.spread(ids, _rally())})
			attacking = []; tf_stage = ""; wave_n0 = 0; last_attack_t = battle.sim_time
		return
	if tf_stage == "move":
		if tf_leg == Vector3.INF: _next_leg(); return
		var near := us.filter(func(u): return u.flat_dist(tf_leg) < 40.0 or u.target != null).size()
		var slow: bool = battle.sim_time - tf_t > 45.0
		if near >= int(ceil(us.size() * 0.7)) or slow:
			_next_leg()
		return
	# engage: units that went idle (area cleared) push on to the next objective
	var done := us.filter(func(u): return u.state == Unit.S.IDLE)
	if done.size() >= int(ceil(us.size() * 0.6)):
		var nobj := _pick_objective(c)
		if nobj != Vector3.INF and nobj.distance_to(tf_obj) > 20.0:
			tf_obj = nobj
			tf_stage = "move"
			bombarded = false
			tf_stuck = 0; tf_best = INF; tf_prog_t = battle.sim_time
			_ev("wave %d pushes on to (%d, %d)" % [waves, int(nobj.x), int(nobj.z)])
			_next_leg()
		elif nobj != Vector3.INF:
			var ids: Array = done.map(func(u): return u.uid)
			battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, nobj)})


## Artillery in the task force shells known defences and structures near the objective once in range, before the
## rest of the group closes in.
func _bombard(us: Array, c: Vector3) -> void:
	var arty := us.filter(func(u): return role_of(u) == "arty")
	if arty.is_empty(): return
	var rng_m := 999.0
	for u in arty: rng_m = minf(rng_m, u.max_range_any())
	var tgt: Unit = null
	var bd := INF
	var ac := _centroid(arty)       # the guns trail the group: measure range from them
	for id in known:
		var b: Unit = _u(id)
		if b == null or b.dead: continue
		var d := ac.distance_to(known[id])
		if d > rng_m * 0.95 or d < 50.0: continue
		var pri: float = d * (0.5 if _is_aa_threat(b) or not (b as Building).bdef.get("weapons", []).is_empty() else 1.0)
		if (known[id] as Vector3).distance_to(tf_obj) > 160.0: pri *= 2.0
		if pri < bd: bd = pri; tgt = b
	if tgt == null:
		# no structure in range: shell the most valuable enemy ground unit in sight within range
		var bv := 600.0
		for e in _in_sight:
			if e.dead or e is Building or e.is_air(): continue
			var d2 := ac.distance_to(e.position)
			if d2 > rng_m * 0.95 or d2 < 45.0: continue
			var v := value_of(e)
			if v > bv: bv = v; tgt = e
	if tgt == null: return
	var ids: Array = arty.filter(func(u): return u.target != tgt and u.can_target(tgt)).map(func(u): return u.uid)
	if ids.is_empty(): return
	battle.issue({"type": "attack", "team": team, "ids": ids, "target": tgt.uid})
	if not bombarded:
		bombarded = true
		stats.bombard += 1
		_ev("artillery bombards %s at (%d, %d)" % [(tgt as Building).bkind if tgt is Building else tgt.kind, int(tgt.position.x), int(tgt.position.z)])


## Focus fire: armour, anti-tank and light vehicles near the fight all shoot the same visible enemy (the one whose
## threat per remaining health is highest).
func _focus_fire(us: Array, c: Vector3) -> void:
	var best: Unit = null
	var bs := 0.0
	for e in _in_sight:
		if e.dead or e.is_air() or e.flat_dist(c) > 75.0: continue
		var threat := value_of_kind(e.kind) if not (e is Building) else (1500.0 if not (e as Building).bdef.get("weapons", []).is_empty() else 0.0)
		if threat <= 0.0: continue
		var s := threat / maxf(50.0, e.hp)
		if s > bs: bs = s; best = e
	if best == null: return
	var roles := ["armor", "at", "light"] if difficulty == "Hard" else ["armor"]
	var ids: Array = us.filter(func(u): return role_of(u) in roles and u.target != best and u.can_target(best) \
		and u.flat_dist(best.position) < u.max_range_vs(best) * 1.3).map(func(u): return u.uid)
	if ids.is_empty(): return
	battle.issue({"type": "attack", "team": team, "ids": ids, "target": best.uid})
	stats.focus += 1


## New units join the task force in groups once it is out.
func _reinforce(pool: Array) -> void:
	var rally := _rally()
	var at_rally := pool.filter(func(u): return u.flat_dist(rally) < 60.0 and u.state == Unit.S.IDLE)
	for u in pool:
		if u.flat_dist(rally) > 45.0 and u.state == Unit.S.IDLE:
			battle.issue({"type": "move", "team": team, "ids": [u.uid], "points": [rally]})
	if at_rally.size() < 3: return
	var us := _tf_units()
	if us.is_empty(): return
	var c := _centroid(us)
	var ids: Array = at_rally.map(func(u): return u.uid)
	battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, c)})
	attacking.append_array(ids)
	wave_n0 += ids.size()
	_ev("reinforces wave %d with %s" % [waves, _comp_text(ids)])


func _feint_tick() -> void:
	if feint.is_empty(): return
	var us: Array = feint.map(func(id): return _u(id)).filter(func(u): return u != null and not u.dead)
	# a feint that has done its job (main force engaged) or is being shot up goes home
	var hurt := us.filter(func(u): return u.hp < u.def.hp * 0.5).size()
	if tf_stage == "engage" or hurt * 2 > us.size() or attacking.is_empty():
		var ids: Array = us.map(func(u): return u.uid)
		if not ids.is_empty(): battle.issue({"type": "move", "team": team, "ids": ids, "points": battle.spread(ids, _rally())})
		feint = []


## Base defence: enemies close to our structures. Units at home respond; the task force is recalled when the attack
## on the base is serious.
func _defend(fighters: Array) -> bool:
	var threat_pos := Vector3.INF
	var tval := 0.0
	for b in battle.structures(team, "", false):
		for e in _in_sight:
			if e.dead or e is Building or e.flat_dist(b.position) > 90.0: continue
			if role_of(e) == "" and not e.is_air(): continue
			tval += value_of(e)
			if threat_pos == Vector3.INF: threat_pos = e.position
	if threat_pos == Vector3.INF:
		# fallback for tests / no sight: the old proximity rule (structure sight covers 90 m)
		for b in battle.structures(team, "", false):
			var e: Unit = battle.find_enemy_near(b, 90.0)
			if e and not (e is Building):
				threat_pos = e.position; tval = value_of(e); break
	if threat_pos == Vector3.INF: return false
	var home := _home()
	var recall := tval > 2500.0 or (tval > 800.0 and attacking.size() > 0 and _tf_units().all(func(u): return u.flat_dist(home) < 250.0))
	var ids: Array = []
	for u in fighters:
		if retreating.has(u.uid) and u.hp < u.def.hp * 0.3: continue
		if not (u.uid in attacking) or u.flat_dist(home) < 150.0 or recall: ids.append(u.uid)
	if recall and not attacking.is_empty():
		_ev("recalls wave %d to defend the base (threat value %d)" % [waves, int(tval)])
		attacking = []; tf_stage = ""; wave_n0 = 0
	if not ids.is_empty():
		battle.issue({"type": "attack_move", "team": team, "ids": ids, "points": battle.spread(ids, threat_pos)})
		if not defending:
			stats.defend += 1
			_ev("defends base: %d units vs threat value %d at (%d, %d)" % [ids.size(), int(tval), int(threat_pos.x), int(threat_pos.z)])
	defending = true
	# helicopters join the defence
	var helis := _mine(func(u): return role_of(u) == "heli" and not air_tasks.has(u.uid))
	if not helis.is_empty():
		var hids: Array = helis.map(func(u): return u.uid)
		battle.issue({"type": "attack_move", "team": team, "ids": hids, "points": battle.spread(hids, threat_pos)})
	return true


## Fall back: attackers below 30 % health go home for repair (vehicles to the War Factory bay); a wave that lost more
## than 60 % of its strength is called off - everyone regroups at home and the next wave is two units bigger.
func _retreat(fighters: Array) -> void:
	var cc := _cc()
	var home: Vector3 = cc.position + Vector3(0, 0, 40.0 * _fwd()) if cc else battle.start_pos[team]
	var wfs: Array = battle.structures(team, "war_factory")
	for id in retreating.keys():
		var u: Unit = _u(id)
		if u == null or u.dead or u.hp >= u.def.hp * 0.9 or battle.sim_time - float(retreating[id]) > 75.0: retreating.erase(id)
	var back: Array = []
	for u in fighters:
		if u.uid in attacking and u.hp < u.def.hp * 0.3 and not retreating.has(u.uid):
			back.append(u)
	if wave_n0 > 0 and not attacking.is_empty() and attacking.size() < wave_n0 * 0.4 and battle.sim_time - last_attack_t > 20.0:
		for id in attacking:
			var u: Unit = _u(id)
			if u and not u.dead and not (u in back): back.append(u)
		attack_size = mini(attack_size + 2, 16)
		wave_n0 = 0
		tf_stage = ""
		_ev("wave %d called off (lost more than 60%%); next wave needs %d units" % [waves, attack_size])
	for u in back:
		attacking.erase(u.uid)
		retreating[u.uid] = battle.sim_time
		var dest: Vector3 = home
		if u.def.get("visual") != "infantry" and u.domain == "ground" and not wfs.is_empty():
			var wf: Building = wfs[0]
			dest = wf.position + wf.front_dir() * (wf.half.y + 8.0)
		battle.issue({"type": "move", "team": team, "ids": [u.uid], "points": [dest]})


# ------------------------------------------------------------------ air arm
## Helicopters fly with the task force when the objective is light on anti-air, otherwise strike AA-light targets;
## jets fly strike sorties from their pads (attack a target, return to rearm when empty).
func _air() -> void:
	for id in air_tasks.keys():
		var a: Unit = _u(id)
		var t: Unit = _u(air_tasks[id])
		if a == null or a.dead:
			# lost on the sortie: remember the target area as defended
			var tp: Vector3 = t.position if t else (a.position if a else Vector3.INF)
			if tp != Vector3.INF:
				air_danger["%d,%d" % [int(tp.x / 50.0), int(tp.z / 50.0)]] = [tp, battle.sim_time]
				_ev("lost an aircraft near (%d, %d); area marked as defended" % [int(tp.x), int(tp.z)])
			air_tasks.erase(id); continue
		if t == null or t.dead or a.state in [Unit.S.IDLE, Unit.S.RETURN, Unit.S.LANDED]:
			air_tasks.erase(id)
			if a.domain == "jet" and a.state != Unit.S.LANDED and a.state != Unit.S.RETURN or (a.domain == "heli" and a.hp < a.def.hp * 0.5):
				battle.issue({"type": "return", "team": team, "ids": [a.uid]})
	var aircraft := _mine(func(u): return role_of(u) in ["heli", "jet"])
	if aircraft.is_empty(): return
	for a in aircraft:
		if air_tasks.has(a.uid) or defending and a.domain == "heli": continue
		if a.domain == "heli" and a.hp < a.def.hp * 0.5:
			if a.state != Unit.S.RETURN and a.state != Unit.S.LANDED: battle.issue({"type": "return", "team": team, "ids": [a.uid]})
			continue
		if a.domain == "jet":
			if a.state != Unit.S.LANDED or not _ammo_full(a): continue
		elif not (a.state in [Unit.S.IDLE, Unit.S.LANDED]): continue
		var tgt := _air_target(a)
		if tgt == null: continue
		air_tasks[a.uid] = tgt.uid
		battle.issue({"type": "attack", "team": team, "ids": [a.uid], "target": tgt.uid})
		stats.air_sorties += 1
		var tk: String = (tgt as Building).bkind if tgt is Building else tgt.kind
		_ev("air strike: %s -> %s at (%d, %d)" % [a.kind, tk, int(tgt.position.x), int(tgt.position.z)])
	# count sorties that actually fired
	for id in air_tasks:
		var a: Unit = _u(id)
		if a and int(battle.shots_by.get(id, 0)) > 0 and not a.has_meta("ai_fired_%d" % air_tasks[id]):
			a.set_meta("ai_fired_%d" % air_tasks[id], true)
			stats.air_strikes += 1


func _ammo_full(u: Unit) -> bool:
	for i in u.w_ammo.size():
		var full := int(u.def.weapons[i].get("ammo", -1))
		if full > 0 and u.w_ammo[i] < full: return false
	return true


## Strike target for an aircraft: valuable, reachable by its weapons, and with little known anti-air around it.
## Targets near our task force's objective score higher (air support for the assault).
func _air_target(a: Unit) -> Unit:
	var best: Unit = null
	var bs := 0.0
	var cands: Array = []
	for e in _in_sight:
		if not e.dead and not (e is Building): cands.append(e)
	for id in known:
		var b: Unit = _u(id)
		if b and not b.dead: cands.append(b)
	var max_aa := int(P.aa_avoid) - (1 if a.domain == "heli" else 0)
	var ground: Array = _mine(func(u): return u.domain == "ground" and not (u is Building) and role_of(u) != "")
	for e in cands:
		if not a.can_target(e): continue
		if a.domain == "heli" and not (e in _in_sight) and not ground.any(func(g): return g.flat_dist(e.position) < 220.0): continue
		if e is Building and (e as Building).bkind == "hesco": continue
		var aa := _aa_at(e.position, 110.0)
		if aa > max_aa: continue
		var v := value_of(e) if not (e is Building) else float(OBJ_WEIGHT.get((e as Building).bkind, 1.0)) * 600.0
		if role_of(e) in ["arty", "aa"] or (not (e is Building) and e.def.get("hauler", false)): v *= 1.6
		if tf_stage != "" and tf_obj != Vector3.INF and e.position.distance_to(tf_obj) < 150.0: v *= 1.5
		var s := v / (1.0 + aa) / (1.0 + a.flat_dist(e.position) / 600.0)
		if s > bs: bs = s; best = e
	return best if bs >= 300.0 else null


# ------------------------------------------------------------------ support powers
## Class of a support power from its data keys (new powers fall into one of these without code changes).
static func power_class(p: Dictionary) -> String:
	if p.has("reveal_width") or p.has("reveal_time"): return "reveal"
	if p.has("drones"): return "drones"
	if p.has("bombs") or p.has("damage") or p.has("dps") or p.has("strikes"): return "strike"
	if p.has("troops") or p.has("unit") or p.has("units") or p.has("vehicles") or p.has("cargo") or p.has("crates"): return "drop"
	return ""


func _powers() -> void:
	if battle.sim_time < next_power_t: return
	var nat: String = battle.nation_of(team)
	for id in Nations.powers(nat):
		if not UnitDefs.POWERS.has(id): continue
		if battle.power_cooldown_left(team, id) > 0.0 or battle.power_problem(team, id) != "": continue
		var p: Dictionary = UnitDefs.POWERS[id]
		var cls := power_class(p)
		if cls == "reveal": continue          # used before attacks (_gather) and when we know nothing
		var tgt := _power_target(cls, p)
		if tgt == Vector3.INF: continue
		_launch(id, tgt, cls)
		return
	# nothing known at all for a while: recon the enemy start
	if known.is_empty() and battle.sim_time > 150.0 and battle.sim_time - last_recon_t > 150.0:
		last_recon_t = battle.sim_time
		_try_power_kind("reveal", battle.start_pos[1 - team])


func _launch(id: String, tgt: Vector3, cls: String) -> void:
	battle.issue({"type": "power", "team": team, "id": id, "pos": tgt})
	next_power_t = battle.sim_time + float(P.power_gap)
	stats.powers.append([battle.sim_time, id, cls, tgt])
	if cls == "reveal": stats.recon += 1
	_ev("support power %s (%s) at (%d, %d)" % [id, cls, int(tgt.x), int(tgt.z)])


func _try_power_kind(cls: String, tgt: Vector3) -> void:
	if tgt == Vector3.INF or battle.sim_time < next_power_t - float(P.power_gap) * 0.5: return
	for id in Nations.powers(battle.nation_of(team)):
		if not UnitDefs.POWERS.has(id) or power_class(UnitDefs.POWERS[id]) != cls: continue
		if battle.power_cooldown_left(team, id) > 0.0 or battle.power_problem(team, id) != "": continue
		_launch(id, tgt, cls)
		return


## Target for a power, or INF when there is nothing worth it: strikes need a cluster of known value clear of our own
## units; drones prefer enemy derricks, anti-air and artillery; drops go to a flank of the fight or an enemy derrick.
func _power_target(cls: String, p: Dictionary) -> Vector3:
	match cls:
		"strike", "drones":
			var r := maxf(10.0, float(p.get("splash", 8.0)) * 1.4)
			if p.has("bombs"): r = maxf(r, float(p.get("spacing", 0.0)) * float(p.bombs) * 0.35)
			var best := Vector3.INF
			var bs := float(P.power_min)
			var cands: Array = []
			for e in _in_sight:
				if not e.dead and not e.is_air(): cands.append(e.position)
			for id in known:
				var b: Unit = _u(id)
				if b and not b.dead: cands.append(known[id])
			if cls == "drones":
				for e in battle.derricks:
					if int(seen_derricks.get(e.id, -1)) == 1 - team: cands.append(e.pos)
			for c in cands:
				var v := _cluster_value(c, r)
				if cls == "drones":
					for e in battle.derricks:
						if e.pos.distance_to(c) < 12.0 and int(seen_derricks.get(e.id, -1)) == 1 - team: v += 1500.0
				if v > bs and not _own_near(c, r + 14.0): bs = v; best = c
			return best
		"drop":
			if tf_stage == "engage" and tf_obj != Vector3.INF:
				var us := _tf_units()
				if not us.is_empty():
					var side := (tf_obj - _centroid(us)).normalized().cross(Vector3.UP)
					var p1: Vector3 = tf_obj + side * 45.0
					if _threat_at(p1, 60.0) < 2500.0: return battle.grounded(p1)
			for e in battle.derricks:
				var o := int(seen_derricks.get(e.id, -1))
				if o != team and _threat_at(e.pos, 80.0) < 1200.0 and e.pos.distance_to(battle.start_pos[team]) > 120.0:
					return battle.grounded(e.pos + Vector3(0, 0, 10.0))
	return Vector3.INF


## Value of known enemy things within r of p: units in sight now (weighted up: armies are what strikes are for) and
## remembered structures (weighted by how much losing them hurts; a Command Center soaks bombs).
func _cluster_value(p: Vector3, r: float) -> float:
	var v := 0.0
	for e in _in_sight:
		if e.dead or e.is_air() or e.position.distance_to(p) > r: continue
		v += value_of(e) * 1.3 if not (e is Building) else _struct_strike_value(e)
	for id in known:
		var b: Unit = _u(id)
		if b == null or b.dead or b in _in_sight: continue
		if (known[id] as Vector3).distance_to(p) <= r: v += _struct_strike_value(b)
	return v


func _struct_strike_value(b: Unit) -> float:
	return float((b as Building).bdef.cost) * float(OBJ_WEIGHT.get((b as Building).bkind, 1.0)) * 0.5


func _own_near(p: Vector3, r: float) -> bool:
	for u in battle.units:
		if u.team == team and not u.dead and not u.is_air() and u.position.distance_to(p) < r: return true
	return false

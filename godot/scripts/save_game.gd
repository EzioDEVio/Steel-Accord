# Steel Accord - save and load a skirmish (B2).
# A save is one Variant dictionary written with FileAccess.store_var (no objects inside; units are referenced by id):
#   meta      - version, map, nations, colours, difficulty, game speed, start cash, real date, game time
#   battle    - sim time, tick, rng state, cash / income / spending, research, battle plans, support-power cooldowns,
#               fog explored mask, derricks, supply piles, rubble, terrain edits made by construction, counters
#   units     - every living unit and structure (passengers nested inside their transport) with its simulation state
#   ai        - the computer player's state; commander control groups; camera
# Not saved: projectiles, bombs and support aircraft that are in the air at that moment (they simply do not arrive).
# Loading starts a normal match on the same map with the same settings, wipes the fresh start, then rebuilds
# everything from the save with the original unit ids so all references (targets, pads, groups, AI orders) hold.
class_name SaveGame
extends RefCounted

const VERSION := 1
const DIR := "user://saves"

# simulation fields copied for every unit (references to other units are stored as ids)
const UNIT_FIELDS := ["hp", "state", "goal", "queue", "path", "path_i", "repath_t", "target", "forced_target", "force_pos",
	"guard_pos", "guard_unit", "home", "heading", "speed_cur", "vel", "turret_yaw", "altitude", "vet_xp", "vet_rank", "bank",
	"w_reload", "w_ammo", "rearm_t", "airborne", "run_out_t", "ret_phase", "site", "has_runway", "taxi_out", "taxi_in", "taxi_i",
	"rw_start", "rw_end", "park_heading", "taxi_phase", "haul_depot", "haul_phase", "haul_t", "cargo", "idle_t", "heal_t",
	"last_fire_t", "board_target", "unload_pending", "para_alt", "garrison", "gar_slot",
	"grp", "grp_speed", "grp_lag", "stuck_t", "stuck_n", "prog_best", "arrive_t", "hold_t", "hold_sum", "nudge_pos", "nudge_t", "rest_pos", "back_t", "back_n",
	"av_ang", "av_last", "av_wait", "alt_layer", "climb_t", "climb_y", "board_slot", "board_t"]
const BUILDING_FIELDS := ["hp", "progress", "built", "prod_queue", "prod_left", "rally", "has_rally", "builder_seen_t", "ever_seen",
	"repairing", "repair_debt", "repair_blocked", "drop_t", "research_id", "research_left", "servicing", "w_reload"]
const AI_FIELDS := ["think_t", "waves", "attacking", "capturing", "scout_t", "scout_uid", "retreating", "losses_seen", "last_attack_t",
	"known", "wave_n0", "attack_size", "garrisoning"]


# ------------------------------------------------------------------ capture
static func _enc(v: Variant) -> Variant:
	if v is Unit: return {"__u": (v as Unit).uid}
	if v is Object: return null
	if v is Array:
		var out: Array = []
		for x in v: out.append(_enc(x))
		return out
	if v is Dictionary:
		var d := {}
		for k in v:
			if v[k] is Object and not (v[k] is Unit): continue
			d[k] = _enc(v[k])
		return d
	return v


static func _unit_rec(b: Node, u: Unit) -> Dictionary:
	var r := {"uid": u.uid, "kind": u.kind, "team": u.team, "pos": u.position, "is_building": u is Building, "f": {}}
	var fields: Array = BUILDING_FIELDS if u is Building else UNIT_FIELDS
	for f in fields:
		if f in u: r.f[f] = _enc(u.get(f))
	r["passengers"] = u.passengers.map(func(p): return _unit_rec(b, p))     # transports and occupied buildings
	if u is Building:
		var bb := u as Building
		r["bkind"] = bb.bkind
		r["pads"] = bb.pads.map(func(p): return int(p.uid))
	elif not u.haul_pile.is_empty(): r["haul_pile"] = b.piles.find(u.haul_pile)
	return r


static func capture(b: Node) -> Dictionary:
	var meta := {"version": VERSION, "map": b.map_id, "nation0": b.nation_of(0), "nation1": b.nation_of(1),
		"color0": Game.settings.get("color0", 0), "color1": Game.settings.get("color1", 1), "difficulty": Game.settings.get("difficulty", "Normal"),
		"start_cash": Game.settings.get("start_cash", 10000), "game_speed": Game.settings.get("game_speed", 1.0),
		"date": Time.get_datetime_string_from_system(false, true), "game_time": b.sim_time}
	var bt := {"sim_time": b.sim_time, "tick_n": b.tick_n, "rng_state": b.rng.state, "rng_seed": b.rng.seed, "uid_next": b.uid_next,
		"cash": b.cash.duplicate(), "income": b.income.duplicate(), "spent": b.spent.duplicate(), "trend_samples": b.trend_samples.duplicate(true),
		"upgrades": b.upgrades.duplicate(true), "plan": b.plan.duplicate(), "plan_pending": b.plan_pending.duplicate(),
		"plan_switch_t": b.plan_switch_t.duplicate(), "power_ready": b.power_ready.duplicate(true), "explored": b.explored,
		"derrick_income": b.derrick_income.duplicate(), "drop_income": b.drop_income.duplicate(), "kills": b.kills, "losses": b.losses,
		"promotions": b.promotions, "cry_t": b.cry_t.duplicate(), "flatten_log": b.flatten_log.duplicate(true),
		"derricks": b.derricks.map(func(e): return _enc(e)), "piles": b.piles.map(func(p): return int(p.cash)),
		"rubble": b.rubble.map(func(r): return {"pos": r.pos, "kind": r.kind, "team": r.team, "half": r.half, "seed": r.get("seed", 1)})}
	var us: Array = []
	for u in b.units:
		if u.dead or not is_instance_valid(u): continue
		us.append(_unit_rec(b, u))
	var ai := {}
	if b.base_ai:
		for f in AI_FIELDS:
			if f in b.base_ai: ai[f] = _enc(b.base_ai.get(f))
	var groups := {}
	if b.commander:
		for g in b.commander.groups:
			groups[g] = b.commander.groups[g].filter(func(u): return is_instance_valid(u) and not u.dead).map(func(u): return u.uid)
	var cam := {}
	if b.camera:
		cam = {"pos": b.camera.position, "zoom": b.camera.zoom, "pitch": b.camera.pitch_deg, "yaw": b.camera.yaw}
	return {"meta": meta, "battle": bt, "units": us, "ai": ai, "groups": groups, "camera": cam}


# ------------------------------------------------------------------ files
static func write(path: String, data: Dictionary) -> bool:
	DirAccess.make_dir_recursive_absolute(DIR)
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null: return false
	f.store_var(data, false)
	f.close()
	return true


static func read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path): return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null: return {}
	var v: Variant = f.get_var(false)
	f.close()
	if v is Dictionary and int((v as Dictionary).get("meta", {}).get("version", 0)) == VERSION: return v
	return {}


## Saves newest first: [{"path", "name", "meta"}].
static func list_saves() -> Array:
	var out: Array = []
	var d := DirAccess.open(DIR)
	if d == null: return out
	for fn in d.get_files():
		if not fn.ends_with(".sav"): continue
		var p := DIR + "/" + fn
		var data := read(p)
		if data.is_empty(): continue
		out.append({"path": p, "name": fn.get_basename(), "meta": data.meta, "mtime": FileAccess.get_modified_time(p)})
	out.sort_custom(func(a, c): return a.mtime > c.mtime)
	return out


static func describe(meta: Dictionary) -> String:
	var t := int(meta.get("game_time", 0.0))
	return "%s  -  %s vs %s  -  %02d:%02d  -  %s" % [Game.MAPS.get(meta.get("map", ""), str(meta.get("map", ""))).split(" (")[0],
		Nations.name_of(str(meta.get("nation0", "usa"))), Nations.name_of(str(meta.get("nation1", "iran"))), t / 60, t % 60, str(meta.get("date", ""))]


## Start a new battle scene that will rebuild this save (settings are taken from the save).
static func load_into_new_match(data: Dictionary) -> void:
	var m: Dictionary = data.meta
	for k in ["map", "nation0", "nation1", "color0", "color1", "difficulty", "start_cash", "game_speed"]:
		if m.has(k): Game.settings[k] = m[k]
	Game.pending_load = data
	Game.start_match()


# ------------------------------------------------------------------ restore
static func _dec(v: Variant, b: Node) -> Variant:
	if v is Dictionary:
		if (v as Dictionary).has("__u") and (v as Dictionary).size() == 1:
			return b.by_id.get(int(v.__u))
		var d := {}
		for k in v: d[k] = _dec(v[k], b)
		return d
	if v is Array:
		var out: Array = []
		for x in v: out.append(_dec(x, b))
		return out
	return v


static func _wipe(b: Node) -> void:
	var all: Array = []
	for u in b.units:
		all.append(u)
		for p in u.passengers: all.append(p)
	for u in all:
		if not is_instance_valid(u): continue
		if u is Building and not u.dead: b.nav_set_structure(u.position, u.half + Vector2(1.0, 1.0), false)
		u.queue_free()
	b.units.clear()
	b.by_id.clear()
	for r in b.rubble:
		if is_instance_valid(r.node): r.node.queue_free()
	b.rubble.clear()
	for arr in [b.shots, b.flights, b.bombs, b.drones, b.drop_flights, b.drop_crates, b.debris]:
		for e in arr:
			if e is Dictionary and e.has("node") and is_instance_valid(e.node): e.node.queue_free()
			elif e is Node and is_instance_valid(e): e.queue_free()
		arr.clear()
	b.reveal_zones.clear()
	if b.commander:
		b.commander._set_selection([])
		b.commander.sel_building = null
		b.commander.groups.clear()


static func _make(b: Node, r: Dictionary) -> Unit:
	var u: Unit
	if r.is_building:
		var k: String = r.bkind
		u = Building.new()
		b.add_child(u)
		(u as Building).setup_structure(b, k, int(r.team), int(r.uid), r.pos, bool(r.f.get("built", true)))
	else:
		u = Unit.new()
		b.add_child(u)
		u.setup(b, str(r.kind), int(r.team), int(r.uid), r.pos, float(r.f.get("heading", 0.0)))
	u.position = r.pos
	u.reset_physics_interpolation()
	b.by_id[u.uid] = u
	return u


static func restore(b: Node, data: Dictionary) -> void:
	_wipe(b)
	var bt: Dictionary = data.battle
	# terrain edits first (construction flattened the ground), then rubble and structures on top
	if b.terrain:
		for e in bt.get("flatten_log", []):
			b.terrain.flatten(e[0], e[1], e[0].y, 8.0)
	b.flatten_log = bt.get("flatten_log", []).duplicate(true)
	for r in bt.get("rubble", []):
		b.add_rubble_at(r.pos, r.kind, int(r.team), r.half, int(r.seed))
	var recs: Array = data.units.duplicate()
	recs.sort_custom(func(a, c): return int(a.uid) < int(c.uid))
	var made := {}      # uid -> [Unit, record]
	for r in recs:
		var u := _make(b, r)
		b.units.append(u)
		made[u.uid] = [u, r]
		for pr in r.get("passengers", []):
			var p := _make(b, pr)
			p.visible = false
			p.process_mode = Node.PROCESS_MODE_DISABLED
			u.passengers.append(p)
			made[p.uid] = [p, pr]
	# fields (after every unit exists, so ids resolve to units)
	for id in made:
		var u: Unit = made[id][0]
		var r: Dictionary = made[id][1]
		for f in r.f:
			if f in u: u.set(f, _dec(r.f[f], b))
		if u is Building:
			var bb := u as Building
			var pu: Array = r.get("pads", [])
			for i in mini(pu.size(), bb.pads.size()): bb.pads[i].uid = int(pu[i])
			if bb.built: bb.progress = 1.0
		else:
			var hp_i := int(r.get("haul_pile", -1))
			if hp_i >= 0 and hp_i < b.piles.size(): u.haul_pile = b.piles[hp_i]
			u.body.position.y = u.altitude
			if u.has_method("_apply_grooming"): u._apply_grooming()
	b.uid_next = int(bt.get("uid_next", b.uid_next))
	for id in made: b.uid_next = maxi(b.uid_next, int(id) + 1)
	# battle state
	b.sim_time = float(bt.sim_time); b.tick_n = int(bt.tick_n)
	b.rng.seed = int(bt.rng_seed); b.rng.state = int(bt.rng_state)
	for k in ["cash", "income", "spent", "trend_samples", "upgrades", "plan", "plan_pending", "plan_switch_t", "power_ready",
			"derrick_income", "drop_income", "cry_t"]:
		if bt.has(k): b.set(k, bt[k].duplicate(true))
	b.kills = int(bt.get("kills", 0)); b.losses = int(bt.get("losses", 0)); b.promotions = int(bt.get("promotions", 0))
	if bt.has("explored") and (bt.explored as PackedByteArray).size() == b.explored.size(): b.explored = bt.explored
	var piles_cash: Array = bt.get("piles", [])
	for i in mini(piles_cash.size(), b.piles.size()):
		b.piles[i].cash = int(piles_cash[i])
		if int(piles_cash[i]) <= 0 and is_instance_valid(b.piles[i].get("node")): b.piles[i].node.visible = false
	var ders: Array = bt.get("derricks", [])
	for i in mini(ders.size(), b.derricks.size()):
		var e: Dictionary = b.derricks[i]
		for k in ders[i]:
			if k == "node" or k == "flag": continue
			e[k] = _dec(ders[i][k], b)
		if b.has_method("_set_derrick_flag"): b._set_derrick_flag(e)
	# computer player, groups, camera
	if b.base_ai:
		for f in data.get("ai", {}):
			if f in b.base_ai: b.base_ai.set(f, _dec(data.ai[f], b))
	if b.commander:
		for g in data.get("groups", {}):
			b.commander.groups[int(g)] = data.groups[g].map(func(id): return b.by_id.get(int(id))).filter(func(u): return u != null)
	var cam: Dictionary = data.get("camera", {})
	if b.camera and not cam.is_empty():
		b.camera.zoom = float(cam.zoom); b.camera.pitch_deg = float(cam.pitch); b.camera.yaw = float(cam.yaw)
		b.camera.focus(Vector3(cam.pos.x, 0, cam.pos.z))
	b.game_over = false
	b.minimap_tex = null
	if b.hud:   # drop HUD caches that point at the old units
		b.hud._strip_sig = ""
		for c in b.hud.prod_strip.get_children(): c.queue_free()
		b.hud.econ._sig = ""
		b.hud.unit_panel._sig = ""
		b.hud.inspector.pinned = null
		b.hud.inspector._sig = ""
		b.commander.hover = null
	if b.hud: b.hud.flash_message("Game loaded (%s)" % describe(data.meta))


## A compact fingerprint of the simulation state, for tests: equal before saving and after loading.
static func signature(b: Node) -> Dictionary:
	var hp := [0.0, 0.0]; var n := [0, 0]; var bl := [0, 0]; var q := []; var vet := 0.0
	for u in b.units:
		if u.dead or u.team < 0 or u.team > 1: continue
		hp[u.team] += u.hp; n[u.team] += 1
		if u is Building:
			bl[u.team] += 1
			q.append("%d:%s:%s" % [u.uid, ",".join((u as Building).prod_queue), (u as Building).research_id])
		vet += u.vet_xp
		for p in u.passengers: n[u.team] += 1
	q.sort()
	return {"units": n, "structures": bl, "hp": [snappedf(hp[0], 0.1), snappedf(hp[1], 0.1)], "cash": b.cash.duplicate(),
		"queues": ",".join(q), "upgrades": [b.upgrades[0].keys(), b.upgrades[1].keys()], "plan": b.plan.duplicate(),
		"vet_xp": snappedf(vet, 0.1), "sim_time": snappedf(b.sim_time, 0.01), "derricks": b.derricks.map(func(e): return e.owner),
		"piles": b.piles.map(func(p): return p.cash)}

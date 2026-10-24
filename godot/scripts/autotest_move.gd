# Steel Accord - movement acceptance tests (B3 movement ticket).
# Run: godot --headless --path godot --fixed-fps 30 -- movetest noai out=/dir [map=zagros_basin] [only=crowd,group,...] [prof]
# Scenarios (each on its own patch of open ground, spawned units removed afterwards):
#   crowd   - two mixed groups (vehicles + infantry) ordered through each other; worst overlap and arrival time
#   group   - 24 mixed units moved into a confined pocket between structures / beside a building; clean stop, nothing inside
#   board   - boarding stress: surrounded transport, moving transport, hovering / landed helicopter, civic building,
#             over-capacity squad; repeated with different seeds and positions
#   heli    - helicopter group: no rotor overlap in flight, distinct hover spots
#   jets    - 4-jet group order: no mid-air intersections
#   save    - save / load in the middle of a group move: state restored, the move continues and completes
#   big     - 44-unit group move: overlap, settle time, circling, simulation cost per tick
# Overlap metric: centre distance / (r_a + r_b) between the units' hull models (Unit.hull_pts / sub_r: a vehicle is two
# circles along its drawn hull, infantry and aircraft one circle). Vehicle pairs are also checked as oriented
# rectangles (drawn length x width) for real model overlap.
extends "res://scripts/autotest_base.gd"

var rng2 := RandomNumberGenerator.new()
var only: Array = []
var spawned: Array = []
var lines: Array = []          # metrics written to result.txt


func _run() -> void:
	if battle.args.has("only"): only = str(battle.args.only).split(",")
	await _wait_sim(0.5)
	# clear the opponent's mobile units (no AI runs: "noai"); keep its Command Center so the match does not end
	for u in battle.units.duplicate():
		if u.team == 1 and not (u is Building): _drop(u)
	var base := _base_point()
	var plan := [["crowd", Vector3(0, 0, 0)], ["group", Vector3(0, 0, 0)], ["board", Vector3(0, 0, 0)],
		["heli", Vector3(0, 0, 0)], ["jets", Vector3(0, 0, 0)], ["save", Vector3(0, 0, 0)], ["big", Vector3(0, 0, 0)]]
	for p in plan:
		if not only.is_empty() and not (p[0] in only): continue
		match p[0]:
			"crowd": await _t_crowd(_open_spot(base, Vector2(80, 26), "wheeled"))
			"group": await _t_group(base)
			"board": await _t_board(base)
			"heli": await _t_heli(base)
			"jets": await _t_jets(base)
			"save": await _t_save(_open_spot(base + Vector3(0, 0, -40), Vector2(60, 24), "wheeled"))
			"big": await _t_big(_open_spot(base + Vector3(0, 0, 30), Vector2(100, 40), "wheeled"))
	_done()


func _done() -> void:
	var passed := checks.filter(func(c): return c[1]).size()
	print("RESULT %d/%d" % [passed, checks.size()])
	var f := FileAccess.open(out + "/result.txt", FileAccess.WRITE)
	for c in checks: f.store_line("%s %s %s" % [c[0], "PASS" if c[1] else "FAIL", c[2]])
	for l in lines: f.store_line("METRIC " + l)
	f.store_line("RESULT %d/%d map=%s" % [passed, checks.size(), battle.map_id])
	f.close()
	get_tree().quit()


func _metric(s: String) -> void:
	lines.append(s)
	printerr("METRIC " + s)


# ------------------------------------------------------------------ helpers
func _base_point() -> Vector3:
	if battle.terrain == null: return Vector3(0, 0, 40)
	return battle.start_pos[0] + Vector3(0, 0, -150)


## Nearest centre (spiral search) where a box of the given half size is walkable for the class: open test ground.
func _open_spot(c0: Vector3, half: Vector2, cls: String) -> Vector3:
	var g: GridNav = battle.navs.get(cls, battle.gnav)
	for ring in range(0, 40):
		var n := maxi(1, ring * 8)
		for k in n:
			var a := TAU * float(k) / float(n)
			var c := c0 + Vector3(cos(a), 0, sin(a)) * float(ring) * 12.0
			var ok := true
			var x := -half.x
			while x <= half.x and ok:
				var z := -half.y
				while z <= half.y and ok:
					var p := c + Vector3(x, 0, z)
					if g.blocked_at(p) or not battle.map_bounds.grow(-20).has_point(Vector2(p.x, p.z)): ok = false
					z += 4.0
				x += 4.0
			if ok:
				for b in battle.units:
					if b is Building and absf(b.position.x - c.x) < half.x + b.half.x + 6 and absf(b.position.z - c.z) < half.y + b.half.y + 6: ok = false; break
			if ok: return battle.grounded(c)
	return battle.grounded(c0)


func _mk(kind: String, team: int, p: Vector3, yaw := 0.0) -> Unit:
	var u: Unit = battle._spawn(kind, team, p, yaw)
	spawned.append(u)
	return u


func _drop(u: Unit) -> void:
	if not is_instance_valid(u): return
	for p in u.passengers: if is_instance_valid(p): p.queue_free()
	u.passengers.clear()
	battle.units.erase(u)
	battle.by_id.erase(u.uid)
	if u in battle.commander.selected: battle.commander.selected.erase(u)
	if u is Building and not u.dead: battle.nav_set_structure(u.position, u.half + Vector2(1.0, 1.0), false)
	u.dead = true
	u.queue_free()


func _cleanup() -> void:
	for u in spawned: _drop(u)
	spawned.clear()
	await _frames(2)


func _r(u: Unit) -> float:
	if u.has_method("body_r"): return u.body_r()
	# same formula as Unit.body_r(), for runs on code without it (before numbers)
	if u.def.get("visual") == "infantry": return float(u.def.radius) * 1.3
	if u.domain == "heli":
		var hr := maxf(float(u.def.radius), float(u.def.get("rotor", 0.0)) * u.vis_scale)
		if u.def.get("rotor_twin", false): hr = maxf(hr, float(u.def.get("length", 0.0)) * u.vis_scale * 0.5)
		return hr
	var hl := maxf(float(u.def.get("length", 0.0)) * u.vis_scale * 0.5, float(u.def.radius))
	return maxf(float(u.def.radius), 0.5 * (hl + float(u.def.radius)))


## Hull model (same as Unit.hull_pts / sub_r; formula repeated for runs on code without them): vehicles are two
## circles along the hull, everything else one circle of _r().
func _sub_r(u: Unit) -> float:
	if u.has_method("sub_r"): return u.sub_r()
	if u.domain == "ground" and u.def.get("visual") != "infantry": return maxf(float(u.def.radius) * 0.78 * 1.25, 0.8)
	return _r(u)


func _hull(u: Unit) -> PackedVector2Array:
	if u.has_method("hull_pts"): return u.hull_pts()
	var c := Vector2(u.position.x, u.position.z)
	if u.domain != "ground" or u.def.get("visual") == "infantry": return PackedVector2Array([c])
	var hl := maxf(float(u.def.get("length", 0.0)) * u.vis_scale * 0.5, float(u.def.radius))
	var o := maxf(0.0, hl - float(u.def.radius) * 0.78 * 0.9)
	if o <= 0.0: return PackedVector2Array([c])
	var f := Vector2(-sin(u.heading), -cos(u.heading)) * o
	return PackedVector2Array([c + f, c - f])


## Smallest centre distance / (r_a + r_b) over the two hull models.
func _pair_ratio(a: Unit, b: Unit) -> float:
	var s := _sub_r(a) + _sub_r(b)
	var best := 99.0
	for pa in _hull(a):
		for pb in _hull(b):
			best = minf(best, pa.distance_to(pb) / s)
	return best


func _slots(us: Array, dest: Vector3) -> Array:
	battle.commander._set_selection(us)
	var pts: Array = battle.commander.formation(dest)
	battle.commander._set_selection([])
	return pts


func _move(us: Array, dest: Vector3) -> Array:
	var pts := _slots(us, dest)
	battle.issue({"type": "move", "team": 0, "ids": us.map(func(u): return u.uid), "points": pts})
	return pts


func _flat(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


## Drawn rectangle overlap (separating axis) for two vehicles: length x width at the drawn scale.
func _obb_overlap(a: Unit, b: Unit) -> bool:
	var ra := _rect(a); var rb := _rect(b)
	for ax in [ra[1], ra[2], rb[1], rb[2]]:
		var pa := _proj(ra, ax); var pb := _proj(rb, ax)
		if pa.y <= pb.x or pb.y <= pa.x: return false
	return true


func _rect(u: Unit) -> Array:
	var f := Vector2(-sin(u.heading), -cos(u.heading))
	var r := Vector2(-f.y, f.x)
	var hl := float(u.def.get("length", 4.0)) * u.vis_scale * 0.5
	var hw := float(u.def.radius) * 0.78
	return [Vector2(u.position.x, u.position.z), f, r, hl, hw]


func _proj(rc: Array, ax: Vector2) -> Vector2:
	var c: float = (rc[0] as Vector2).dot(ax)
	var e: float = absf((rc[1] as Vector2).dot(ax)) * float(rc[3]) + absf((rc[2] as Vector2).dot(ax)) * float(rc[4])
	return Vector2(c - e, c + e)


## Samples every simulation tick while `cond` is false (max t seconds): worst pair ratio, ticks below 0.7, longest
## run of consecutive ticks a pair stays below 0.7, rectangle overlaps for vehicle pairs. Air pairs count only when
## their altitudes are within `alt_sep` metres.
func _watch(us: Array, cond: Callable, t: float, alt_sep := 1e9) -> Dictionary:
	var end: float = battle.sim_time + t
	var worst := 99.0
	var below := 0
	var runs := {}
	var max_run := 0
	var obb := 0
	var ticks := 0
	var phys := 0.0
	while battle.sim_time < end:
		await get_tree().physics_frame
		ticks += 1
		phys += Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
		var live: Array = us.filter(func(u): return is_instance_valid(u) and not u.dead and u in battle.units)
		for i in live.size():
			var a: Unit = live[i]
			for j in range(i + 1, live.size()):
				var b: Unit = live[j]
				if (a.domain == "ground") != (b.domain == "ground"): continue
				if a.domain != "ground" and absf((a.position.y + a.altitude) - (b.position.y + b.altitude)) >= alt_sep: continue
				var d := _flat(a.position, b.position)
				if d > (_r(a) + _r(b)) * 1.2 + 8.0:
					runs.erase(a.uid * 100000 + b.uid)
					continue
				var ratio := _pair_ratio(a, b)
				worst = minf(worst, ratio)
				var key: int = a.uid * 100000 + b.uid
				if ratio < 0.7:
					below += 1
					runs[key] = int(runs.get(key, 0)) + 1
					max_run = maxi(max_run, runs[key])
				else:
					runs.erase(key)
				if a.domain == "ground" and a.def.get("visual") != "infantry" and b.def.get("visual") != "infantry" and _obb_overlap(a, b): obb += 1
		if cond.call(): break
	return {"worst": worst, "below": below, "max_run": max_run, "obb": obb, "t": t - (end - battle.sim_time), "ticks": ticks,
		"phys_ms": phys / maxf(1.0, ticks)}


func _settled(us: Array, pts: Array, slack := 6.0) -> bool:
	if _speed_sum(us) > 0.3: return false
	for i in us.size():
		var u: Unit = us[i]
		if u.dead or not (u in battle.units): continue
		if u.state != Unit.S.IDLE: return false
		if _flat(u.position, pts[i]) > _slack(u): return false
	return true


## How far from its slot a unit may stop when the slot area is crowded: Unit.arrive_slack() + 1 m (about one body
## length; the old code had no such rule, so it is measured the same way for before numbers).
func _slack(u: Unit) -> float:
	return 5.0 + 3.0 * _r(u)


func _unsettled(us: Array, pts: Array) -> void:
	var parts: Array = []
	for i in us.size():
		var u: Unit = us[i]
		if u.dead: continue
		var d := _flat(u.position, pts[i])
		if u.state != Unit.S.IDLE or d > _slack(u):
			parts.append("%s#%d st=%d d=%.1f spd=%.1f stuck=%d path=%d/%d" % [u.kind, u.uid, u.state, d, u.speed_cur, int(u.get("stuck_n")) if "stuck_n" in u else -1, u.path_i, u.path.size()])
	printerr("TESTDBG unsettled: " + " | ".join(parts))


## Summed speed; a unit about to step aside or walk back to its spot counts as moving.
func _speed_sum(us: Array) -> float:
	var s := 0.0
	for u in us:
		if u.dead: continue
		s += absf(u.speed_cur)
		if "back_t" in u and (u.back_t > 0.0 or u.nudge_t > 0.0): s += 1.0
	return s


func _inside_count(us: Array) -> Array:
	var bad: Array = []
	for u in us:
		if u.dead or u.domain != "ground": continue
		for b in battle.units:
			if b is Building and not b.dead and b.footprint_dist(u.position) <= 0.0: bad.append("%s in %s" % [u.kind, b.kind])
		for o in battle.obstacles_2d:
			if Vector2(u.position.x - o.x, u.position.z - o.y).length() < o.z * 0.7: bad.append("%s in rock" % u.kind)
	return bad


# ------------------------------------------------------------------ crowd crossing
const MIX_A := ["abrams", "bradley", "hmmwv", "stryker", "m113", "mrap", "rifleman", "rifleman", "at4", "rifleman", "saw_gunner", "rifleman", "at4", "rifleman"]


func _block(kinds: Array, c: Vector3, yaw: float) -> Array:
	var out: Array = []
	var fwd := Vector3(-sin(yaw), 0, -cos(yaw)); var right := Vector3(-fwd.z, 0, fwd.x)
	var nv := 0; var ni := 0
	for k in kinds:
		var inf: bool = UnitDefs.def_of(k).get("visual") == "infantry"
		var p: Vector3
		if inf:
			p = c - fwd * (8.0 + float(ni / 4) * 2.6) + right * (float(ni % 4) - 1.5) * 2.6
			ni += 1
		else:
			p = c + fwd * (float(nv / 3) * 9.0) + right * (float(nv % 3) - 1.0) * 6.5
			nv += 1
		out.append(_mk(k, 0, battle.grounded(p), yaw))
	return out


func _t_crowd(c: Vector3) -> void:
	var A := _block(MIX_A, c + Vector3(-55, 0, 0), -PI / 2.0)    # facing +x
	var B := _block(MIX_A, c + Vector3(55, 0, 0), PI / 2.0)      # facing -x
	await _wait_sim(0.4)
	var pa := _move(A, c + Vector3(55, 0, 0))
	var pb := _move(B, c + Vector3(-55, 0, 0))
	var all: Array = A + B
	var pts: Array = pa + pb
	await _wait_sim(0.2)
	var w := await _watch(all, func(): return _settled(all, pts), 90.0)
	var arrived := all.filter(func(u): return u.state == Unit.S.IDLE).size()
	var ok: bool = w.max_run <= 6 and arrived == all.size() and w.t < 75.0
	if w.t >= 75.0: _unsettled(all, pts)
	_log("crowd_crossing", ok, "%d units, all stopped %s in %.1f s; worst pair ratio %.2f, pair-ticks <0.7: %d, longest run <0.7: %d ticks, vehicle rectangle overlaps: %d (pair-ticks)" % [
		all.size(), str(arrived == all.size()), w.t, w.worst, w.below, w.max_run, w.obb])
	_metric("crowd map=%s worst=%.2f below07=%d max_run=%d obb=%d settle_s=%.1f arrived=%d/%d" % [battle.map_id, w.worst, w.below, w.max_run, w.obb, w.t, arrived, all.size()])
	await _cleanup()


# ------------------------------------------------------------------ group move into a confined area
func _t_group(base: Vector3) -> void:
	var dest: Vector3
	var c: Vector3
	if battle.terrain:
		var hs: Array = battle.units.filter(func(b): return b is Building and b.is_civic())
		hs.sort_custom(func(a, b): return a.position.distance_to(base) < b.position.distance_to(base))
		var h: Building = hs[0]
		dest = battle.grounded(h.position + Vector3(0, 0, h.half.y + 6.0))
		c = _open_spot(dest + Vector3(0, 0, 70), Vector2(30, 20), "wheeled")
	else:
		c = _open_spot(base + Vector3(0, 0, 60), Vector2(30, 20), "wheeled")
		var pk := _open_spot(base + Vector3(60, 0, -40), Vector2(36, 30), "wheeled")
		# pocket: two structures 26 m apart with a wall-like Power Plant closing the far side
		spawned.append(battle.add_structure("barracks", 0, pk + Vector3(-23, 0, 0), true))
		spawned.append(battle.add_structure("barracks", 0, pk + Vector3(23, 0, 0), true))
		spawned.append(battle.add_structure("power_plant", 0, pk + Vector3(0, 0, -20), true))
		dest = pk + Vector3(0, 0, -6)
	var kinds: Array = ["abrams", "abrams", "bradley", "stryker", "hmmwv", "m113", "mrap", "hmmwv_tow"]
	for i in 16: kinds.append(["rifleman", "at4", "saw_gunner", "medic"][i % 4])
	var us := _block(kinds, c, 0.0 if dest.z < c.z else PI)
	await _wait_sim(0.4)
	var pts := _move(us, dest)
	await _wait_sim(0.15)
	var bad_slots := 0
	for i in pts.size():
		var cls: String = us[i].move_class()
		if battle.navs.get(cls, battle.gnav).blocked_at(pts[i]): bad_slots += 1
	var w := await _watch(us, func(): return us.all(func(u): return u.state == Unit.S.IDLE) and _speed_sum(us) < 0.3, 60.0)
	var stopped := us.filter(func(u): return u.state == Unit.S.IDLE).size()
	if stopped < us.size(): _unsettled(us, pts)
	var p0 := us.map(func(u): return u.position)
	var spd := 0.0
	for k in 6:
		await _wait_sim(0.5)
		spd = maxf(spd, _speed_sum(us))
	var drift := 0.0
	for i in us.size(): drift = maxf(drift, _flat(us[i].position, p0[i]))
	var inside := _inside_count(us)
	var near := 0
	for i in us.size(): if _flat(us[i].position, dest) < 45.0: near += 1
	var ok: bool = stopped == us.size() and w.t < 50.0 and spd < 0.5 and drift < 0.3 and inside.is_empty() and bad_slots == 0 and near == us.size()
	_log("group_move_confined", ok, "%d units stopped %d in %.1f s; afterwards max summed speed %.2f m/s, max drift %.2f m over 3 s; inside obstacles/buildings: %s; slots on blocked cells: %d; within 45 m of target: %d; worst pair ratio %.2f, longest run <0.7: %d" % [
		us.size(), stopped, w.t, spd, drift, ", ".join(inside) if not inside.is_empty() else "none", bad_slots, near, w.worst, w.max_run])
	_metric("group map=%s settle_s=%.1f stopped=%d/%d speed_after=%.2f drift=%.2f inside=%d bad_slots=%d worst=%.2f max_run=%d obb=%d" % [battle.map_id, w.t, stopped, us.size(), spd, drift, inside.size(), bad_slots, w.worst, w.max_run, w.obb])
	await _shot("group_move")
	await _cleanup()


# ------------------------------------------------------------------ boarding stress
func _squad(n: int, around: Vector3, r0: float, r1: float, kinds := ["rifleman", "at4", "saw_gunner"]) -> Array:
	var out: Array = []
	var g: GridNav = battle.navs.get("infantry", battle.gnav)
	for i in n:
		var p := around
		for tries in 30:
			var a := rng2.randf() * TAU
			p = around + Vector3(cos(a), 0, sin(a)) * rng2.randf_range(r0, r1)
			if not g.blocked_at(p): break
		out.append(_mk(kinds[i % kinds.size()], 0, battle.grounded(p), rng2.randf() * TAU))
	return out


func _board(sq: Array, tr: Unit) -> void:
	battle.issue({"type": "board", "team": 0, "ids": sq.map(func(u): return u.uid), "target": tr.uid})


func _t_board(base: Vector3) -> void:
	var trials := int(battle.args.get("trials", "4"))
	var res := {"surrounded": [0, 0], "moving": [0, 0], "heli": [0, 0], "civic": [0, 0]}
	var times := {"surrounded": 0.0, "moving": 0.0, "heli": 0.0, "civic": 0.0}
	var fails: Array = []
	for t in trials:
		rng2.seed = 7001 + t * 31
		var c: Vector3 = _open_spot(base + Vector3(-80 + 40 * (t % 4), 0, -60 + 50 * (t / 4)), Vector2(30, 30), "wheeled")
		# 1. transport surrounded by idle friendly units; the whole squad ordered in at once
		var tr: Unit = _mk(["bradley", "m113", "stryker", "ir_bmp2"][t % 4], 0, c, rng2.randf() * TAU)
		for i in 8:
			var a := TAU * float(i) / 8.0 + rng2.randf() * 0.3
			var k: String = ["rifleman", "hmmwv", "rifleman", "abrams", "saw_gunner", "hmmwv", "rifleman", "at4"][i]
			var rr := 6.0 if UnitDefs.def_of(k).get("visual") == "infantry" else 8.5
			_mk(k, 0, battle.grounded(c + Vector3(cos(a), 0, sin(a)) * rr), rng2.randf() * TAU)
		var sq := _squad(6, c, 22.0, 34.0)
		await _wait_sim(0.3)
		_board(sq, tr)
		var t0: float = battle.sim_time
		var ok: bool = await _until(func(): return tr.passengers.size() == 6, 45.0)
		res.surrounded[1] += 1
		if ok: res.surrounded[0] += 1; times.surrounded = maxf(times.surrounded, battle.sim_time - t0)
		else: fails.append("surrounded#%d %s aboard %d: %s" % [t, tr.kind, tr.passengers.size(), _why(sq, tr)])
		await _cleanup()
		# 2. moving transport: ordered away at the same moment the squad is ordered in
		c = _open_spot(c + Vector3(0, 0, 10), Vector2(40, 30), "wheeled")
		tr = _mk(["stryker", "hmmwv", "m113", "mrap"][t % 4], 0, c, rng2.randf() * TAU)
		var cap: int = mini(6, tr.capacity_left())
		sq = _squad(cap, c, 12.0, 22.0)
		await _wait_sim(0.3)
		var away := Vector3(cos(rng2.randf() * TAU), 0, sin(rng2.randf() * TAU)).normalized()
		battle.issue({"type": "move", "team": 0, "ids": [tr.uid], "points": [battle.grounded(c + away * 40.0)]})
		_board(sq, tr)
		t0 = battle.sim_time
		ok = await _until(func(): return tr.passengers.size() == cap, 45.0)
		res.moving[1] += 1
		if ok: res.moving[0] += 1; times.moving = maxf(times.moving, battle.sim_time - t0)
		else: fails.append("moving#%d %s aboard %d/%d: %s" % [t, tr.kind, tr.passengers.size(), cap, _why(sq, tr)])
		await _cleanup()
		# 3. helicopter: hovering (even trials) or landed (odd trials)
		var uh: Unit = _mk("uh60", 0, c, rng2.randf() * TAU)
		if t % 2 == 1:
			uh.state = Unit.S.LANDED; uh.altitude = 0.0; uh.airborne = false; uh.home = uh.position; uh.speed_cur = 0.0
		sq = _squad(6, c, 18.0, 30.0)
		await _wait_sim(0.5)
		_board(sq, uh)
		t0 = battle.sim_time
		ok = await _until(func(): return uh.passengers.size() == 6, 45.0)
		res.heli[1] += 1
		if ok: res.heli[0] += 1; times.heli = maxf(times.heli, battle.sim_time - t0)
		else: fails.append("heli#%d %s aboard %d alt %.1f: %s" % [t, "landed" if t % 2 == 1 else "hover", uh.passengers.size(), uh.altitude, _why(sq, uh)])
		await _cleanup()
		# 4. civic building (map building on terrain maps, placed one on the flat Proving Ground)
		var hb: Building = null
		if battle.terrain:
			var hs: Array = battle.units.filter(func(b): return b is Building and b.is_civic() and b.passengers.is_empty() and not b.dead and b.capacity_left() >= 5)
			hs.sort_custom(func(a, b): return a.position.distance_to(base) < b.position.distance_to(base))
			hb = hs[t % hs.size()] if not hs.is_empty() else null
		else:
			var hp: Vector3 = _open_spot(c + Vector3(30, 0, 0), Vector2(26, 26), "wheeled")
			hb = battle.add_civic("civ_house_b", hp, false)
			if hb: spawned.append(hb)
		if hb:
			var n: int = mini(5, hb.capacity_left())
			sq = _squad(n, hb.position, maxf(hb.half.x, hb.half.y) + 14.0, maxf(hb.half.x, hb.half.y) + 26.0)
			await _wait_sim(0.3)
			_board(sq, hb)
			t0 = battle.sim_time
			ok = await _until(func(): return hb.passengers.size() == n, 45.0)
			res.civic[1] += 1
			if ok: res.civic[0] += 1; times.civic = maxf(times.civic, battle.sim_time - t0)
			else: fails.append("civic#%d %s aboard %d/%d: %s" % [t, hb.kind, hb.passengers.size(), n, _why(sq, hb)])
			if battle.terrain:     # map building: let the occupants out again so later trials find it empty
				battle.unload_all(hb)
		await _cleanup()
	for k in res:
		_log("board_" + k, res[k][0] == res[k][1] and res[k][1] > 0, "%d/%d trials fully boarded, slowest %.1f s" % [res[k][0], res[k][1], times[k]])
		_metric("board_%s map=%s success=%d/%d slowest_s=%.1f" % [k, battle.map_id, res[k][0], res[k][1], times[k]])
	if not fails.is_empty(): printerr("TESTDBG boarding failures: " + " | ".join(fails))
	# 5. over capacity, through the real input path: 8 riflemen selected, left click on a 6-seat Bradley ->
	#    6 aboard, the other 2 walk over and wait next to it (not left standing where they were, not wandering)
	rng2.seed = 99
	var c2: Vector3 = _open_spot(base + Vector3(0, 0, -20), Vector2(30, 30), "wheeled")
	var br: Unit = _mk("bradley", 0, c2, 0.3)
	var sq8 := _squad(8, c2, 16.0, 26.0)
	await _wait_sim(0.3)
	battle.camera.focus(br.position); await _frames(3)
	await _sel(sq8)
	_click(MOUSE_BUTTON_LEFT, _screen(br.world_center())); await _frames(2)
	await _sel([])
	await _until(func(): return br.passengers.size() == 6 and sq8.filter(func(u): return u in battle.units and u.state == Unit.S.IDLE).size() == 2, 40.0)
	var left: Array = sq8.filter(func(u): return u in battle.units)
	var p0: Array = left.map(func(u): return u.position)
	await _wait_sim(3.0)
	var still := true
	for i in left.size(): if _flat(left[i].position, p0[i]) > 0.5: still = false
	var near := left.all(func(u): return u.flat_dist(br.position) < 16.0 and u.state == Unit.S.IDLE and u.board_target == null)
	_log("board_over_capacity", br.passengers.size() == 6 and left.size() == 2 and near and still,
		"aboard %d, left outside %d, waiting within 16 m and idle: %s, not wandering: %s" % [br.passengers.size(), left.size(), str(near), str(still)])
	await _cleanup()


func _why(sq: Array, tr: Unit) -> String:
	var parts: Array = []
	for u in sq:
		if not (u in battle.units): continue
		parts.append("%s st=%d d=%.1f bt=%s" % [u.kind, u.state, u.flat_dist(tr.position), str(u.board_target != null)])
	return "; ".join(parts) + " | tr spd %.1f st %d" % [tr.speed_cur, tr.state]


# ------------------------------------------------------------------ helicopters
func _t_heli(base: Vector3) -> void:
	var c: Vector3 = _open_spot(base + Vector3(-60, 0, 20), Vector2(30, 30), "infantry")
	var kinds := ["ah64", "ah64", "ah64", "uh60", "uh60", "ch47"]
	var hs: Array = []
	for i in kinds.size():
		var u := _mk(kinds[i], 0, c + Vector3((i % 3) * 9.0 - 9.0, 0, (i / 3) * 9.0), 0.0)
		u.altitude = float(u.def.altitude)
		hs.append(u)
	await _wait_sim(0.5)
	var dest := c + Vector3(0, 0, -110)
	var pts := _move(hs, dest)
	await _wait_sim(0.15)
	var w := await _watch(hs, func(): return hs.all(func(u): return u.state == Unit.S.IDLE and u.speed_cur < 0.5), 50.0)
	await _wait_sim(3.0)
	var worst_final := 99.0
	for i in hs.size():
		for j in range(i + 1, hs.size()):
			worst_final = minf(worst_final, _flat(hs[i].position, hs[j].position) / (_r(hs[i]) + _r(hs[j])))
	var ok: bool = w.max_run <= 6 and worst_final >= 0.9 and hs.all(func(u): return u.state == Unit.S.IDLE)
	_log("heli_group", ok, "%d helicopters; in flight worst rotor ratio %.2f, longest run <0.7: %d ticks; hover spots worst ratio %.2f (>= 0.9 means separate)" % [hs.size(), w.worst, w.max_run, worst_final])
	_metric("heli map=%s worst=%.2f max_run=%d final_worst=%.2f settle_s=%.1f" % [battle.map_id, w.worst, w.max_run, worst_final, w.t])
	await _shot("heli_group")
	await _cleanup()


# ------------------------------------------------------------------ jets
func _t_jets(base: Vector3) -> void:
	var c: Vector3 = base + Vector3(0, 0, 60)
	var js: Array = []
	for i in 4:
		var u := _mk("f16", 0, c + Vector3(i * 14.0 - 21.0, 0, 0), 0.0)
		u.airborne = true; u.altitude = float(u.def.altitude); u.speed_cur = float(u.def.min_speed); u.state = Unit.S.IDLE
		u.has_runway = false
		js.append(u)
	await _wait_sim(0.2)
	_move(js, c + Vector3(200, 0, -40))     # away from the opponent's base: no attack runs, just the group order
	var end: float = battle.sim_time + 50.0
	var hits := 0
	var closest := 1e9
	while battle.sim_time < end:
		await get_tree().physics_frame
		for i in js.size():
			for j in range(i + 1, js.size()):
				var a: Unit = js[i]; var b: Unit = js[j]
				var dh := _flat(a.position, b.position)
				var dv := absf((a.position.y + a.altitude) - (b.position.y + b.altitude))
				var ra := float(a.def.length) * a.vis_scale * 0.5; var rb := float(b.def.length) * b.vis_scale * 0.5
				if dv < 3.0: closest = minf(closest, dh / (ra + rb))
				if dh < ra + rb and dv < 3.0: hits += 1
	var alts := js.map(func(u): return snappedf(u.altitude, 0.1))
	_log("jets_no_midair_intersection", hits == 0, "4 F-16 group order, 50 s: intersecting pair-ticks %d; closest same-level approach %.2f x (sum of half-lengths); cruise altitudes %s" % [hits, closest, str(alts)])
	_metric("jets map=%s hits=%d closest_ratio=%.2f" % [battle.map_id, hits, closest])
	await _cleanup()


# ------------------------------------------------------------------ save / load mid-move
func _t_save(c: Vector3) -> void:
	var kinds := ["abrams", "bradley", "hmmwv", "stryker", "rifleman", "rifleman", "at4", "rifleman", "saw_gunner", "rifleman", "medic", "rifleman"]
	var us := _block(kinds, c + Vector3(-40, 0, 0), -PI / 2.0)
	await _wait_sim(0.3)
	var dest := c + Vector3(45, 0, 0)
	_move(us, dest)
	await _wait_sim(3.0)
	var ids: Array = us.map(func(u): return u.uid)
	var before := {}
	for u in us: before[u.uid] = [u.position, u.state, u.goal]
	var data: Dictionary = SaveGame.capture(battle)
	var path := SaveGame.DIR + "/movetest.sav"
	SaveGame.write(path, data)
	var back := SaveGame.read(path)
	SaveGame.restore(battle, back)
	spawned.clear()
	var same := 0; var moving := 0
	var us2: Array = []
	for id in ids:
		var u: Unit = battle.by_id.get(id)
		if u == null: continue
		us2.append(u); spawned.append(u)
		if u.position.distance_to(before[id][0]) < 0.01 and u.goal.distance_to(before[id][2]) < 0.01: same += 1
		if u.state == Unit.S.MOVE: moving += 1
	var w := await _watch(us2, func(): return us2.all(func(u): return u.state == Unit.S.IDLE), 50.0)
	var arrived := us2.filter(func(u): return u.state == Unit.S.IDLE and _flat(u.position, dest) < 30.0).size()
	_log("save_load_mid_move", same == ids.size() and moving == ids.size() and arrived == ids.size(),
		"restored %d/%d units at the same position and goal, %d still moving after load; %d arrived %.1f s later" % [same, ids.size(), moving, arrived, w.t])
	await _cleanup()


# ------------------------------------------------------------------ big group move (before / after numbers)
func _t_big(c: Vector3) -> void:
	var kinds: Array = []
	for i in 14: kinds.append(["abrams", "bradley", "hmmwv", "stryker", "m113", "mrap", "hmmwv_50cal"][i % 7])
	for i in 30: kinds.append(["rifleman", "at4", "saw_gunner", "m240_gunner", "medic"][i % 5])
	var us := _block(kinds, c + Vector3(0, 0, 45), 0.0)
	await _wait_sim(0.5)
	battle.camera.focus(c); await _frames(2)
	await _shot("big_before_move")
	var pts := _move(us, c + Vector3(0, 0, -45))
	await _wait_sim(0.15)
	var w := await _watch(us, func(): return us.all(func(u): return u.state == Unit.S.IDLE) and _speed_sum(us) < 0.3, 60.0)
	var stopped := us.filter(func(u): return u.state == Unit.S.IDLE).size()
	if stopped < us.size(): _unsettled(us, pts)
	var spd := 0.0
	for k in 6:
		await _wait_sim(0.5)
		spd = maxf(spd, _speed_sum(us))
	battle.camera.focus(c + Vector3(0, 0, -45)); await _frames(2)
	await _shot("big_after_move")
	_log("big_group_move", stopped == us.size() and spd < 0.5, "%d units: stopped %d in %.1f s, summed speed after %.2f m/s, worst pair ratio %.2f, pair-ticks <0.7 %d, longest run %d, vehicle rectangle overlaps %d; physics %.2f ms/tick" % [
		us.size(), stopped, w.t, spd, w.worst, w.below, w.max_run, w.obb, w.phys_ms])
	_metric("big map=%s n=%d settle_s=%.1f stopped=%d speed_after=%.2f worst=%.2f below07=%d max_run=%d obb=%d phys_ms=%.2f" % [battle.map_id, us.size(), w.t, stopped, spd, w.worst, w.below, w.max_run, w.obb, w.phys_ms])
	await _cleanup()

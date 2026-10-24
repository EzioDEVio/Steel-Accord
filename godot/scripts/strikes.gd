# Steel Accord - strategic bomber strikes (B3): single bombers and squadrons flying in formation.
# Owns the bomber path of battle.launch_power: aircraft (HD models at their own scale and altitude), bomb-bay doors
# that open ~2 s before the first release and close after the last, bombs staged inside the bay at their real position
# and released with a separation tumble, B-1 wing sweep for the run, contrails / heat shimmer, and the strike camera.
# Simulation state (positions, releases, damage) advances only in tick() from battle.sim_tick with battle.rng, so it is
# deterministic; the camera and the tumble wobble are presentation only.
# Each aircraft is one entry in battle.flights ({"strike": true, ...}) and each bomb one entry in battle.bombs
# ({"strike": true, ...}); battle._update_flights / _update_bombs skip those entries.
class_name StrikeDirector
extends Node

const G := 25.0                  # game gravity for bombs (same as battle._update_bombs)
const DOOR_LEAD := 2.0           # doors start opening this long before the first release
const DOOR_OPEN_S := 1.0
const DOOR_CLOSE_AFTER := 1.0
const DOOR_CLOSE_S := 1.5
const SEP_V := 1.5               # downward ejection speed at release (m/s)
const BOMB_SCENES := {"gp": "res://assets/units3d/hd_bombs/gp_bomb.glb", "pen": "res://assets/units3d/hd_bombs/penetrator.glb"}

var battle: Node
var events: Array = []           # test / diagnostics: {"ev", "t", ...}
var cam: Node = null             # the active StrikeCam (one at a time)
var _scene_cache := {}


func _scene(path: String) -> PackedScene:
	if not _scene_cache.has(path): _scene_cache[path] = load(path) if ResourceLoader.exists(path) else null
	return _scene_cache[path]


## The aircraft of a power: an explicit "wing" list, or one bomber described by the power's own fields.
static func wing_of(p: Dictionary) -> Array:
	if p.has("wing"): return p.wing
	return [{"type": p.aircraft, "lat": 0.0, "back": 0.0, "up": 0.0, "aim": 0.0, "bombs": p.bombs, "damage": p.damage,
		"splash": p.splash, "spacing": p.spacing}]


static func is_strike(p: Dictionary) -> bool:
	return p.has("wing") or UnitDefs.BOMBERS.has(str(p.get("aircraft", "")))


func launch(team: int, id: String, target: Vector3) -> void:
	var p: Dictionary = UnitDefs.POWERS[id]
	var edge_z: float = battle.map_bounds.end.y + 120.0 if team == 0 else battle.map_bounds.position.y - 120.0
	var start := Vector3(target.x * 0.7, battle.ground_h(target.x, target.z), edge_z)
	var dir := Vector3(target.x - start.x, 0, target.z - start.z).normalized()
	var right := dir.cross(Vector3.UP)
	var group: Array = []
	var wing: Array = wing_of(p)
	for i in wing.size():
		var w: Dictionary = wing[i]
		var bd: Dictionary = UnitDefs.BOMBERS[w.type]
		var speed := float(p.get("speed", bd.speed))
		var alt := float(bd.altitude) + float(w.get("up", 0.0))
		var pos: Vector3 = start + right * float(w.get("lat", 0.0)) - dir * float(w.get("back", 0.0))
		pos.y = battle.ground_h(pos.x, pos.z)
		var aim: Vector3 = target + right * float(w.get("lat", 0.0)) + dir * float(w.get("aim", 0.0))
		var node := Node3D.new()
		battle.add_child(node)
		node.position = pos
		node.rotation.y = atan2(-dir.x, -dir.z)
		var ps: PackedScene = _scene(bd.model3d)
		if ps == null: ps = _scene("res://assets/units3d/%s/%s.glb" % [w.type, w.type])   # M3 model if the HD one is missing
		var model: Node3D = ps.instantiate()
		model.scale = Vector3.ONE * UnitDefs.SCALE.bomber
		model.position.y = alt
		node.add_child(model)
		node.reset_physics_interpolation()
		var f := {"node": node, "model": model, "pos": pos, "dir": dir, "right": right, "def": p, "id": id, "team": team,
			"target": aim, "aim": aim, "strike": true, "type": w.type, "bd": bd, "speed": speed, "alt": alt, "lead": i == 0,
			"index": i, "dropped": 0, "released": [], "doors": 0.0, "door_t": -1.0, "last_rel": -1.0, "sweep": 0.0,
			"dmg": float(w.damage), "splash": float(w.splash)}
		f["door_list"] = _find_doors(model, int(bd.bays))
		f["wing_l"] = model.find_child("WingL", false, false)
		f["wing_r"] = model.find_child("WingR", false, false)
		f["plan"] = _plan(f, int(w.bombs), float(w.spacing))
		_effects(f)
		group.append(f)
		battle.flights.append(f)
	FX.target_marker(battle, target, 16.0 if group.size() > 1 else 14.0)
	events.append({"ev": "launch", "t": battle.sim_time, "id": id, "team": team, "n": group.size()})
	if battle.hud and team == battle.commander.team:
		battle.hud.flash_message("%s inbound (%d aircraft)" % [battle.lbl(team, id, p.name), group.size()] if group.size() > 1 else "%s inbound" % battle.lbl(team, id, p.name))
		_maybe_camera(group, battle.lbl(team, id, p.name))


# ------------------------------------------------------------------ release plan
## Weapon sources in model space (bay stow slots and wing-pylon stations) and the release distance of each bomb,
## measured along the run from this aircraft's aim point (negative = before it).
func _plan(f: Dictionary, n: int, spacing: float) -> Array:
	var bd: Dictionary = f.bd
	var model: Node3D = f.model
	var bays: int = int(bd.bays)
	var pylons: Array = []
	for i in 24:
		var e := model.find_child("PB%d" % i, false, false) as Node3D
		if e == null: break
		pylons.append(e)
	var n_pyl := mini(pylons.size(), maxi(0, n - int(bd.bay_cap)))
	var n_bay := n - n_pyl
	# split the bay load across the bays, fore to aft
	var per_bay: Array = []
	for b in bays: per_bay.append(n_bay / bays + (1 if b < n_bay % bays else 0))
	var bay_list: Array = []         # round robin over the bays, lowest tier first inside each bay
	var slots: Array = []
	for b in bays: slots.append(_stow_slots(model, b, int(per_bay[b]), bd))
	for r in 64:
		for b in bays:
			if r < slots[b].size(): bay_list.append({"src": "bay", "bay": b, "local": slots[b][r]})
	var lefts: Array = pylons.filter(func(e): return e.position.x < 0.0)
	var rights: Array = pylons.filter(func(e): return e.position.x >= 0.0)
	var pyl_list: Array = []
	for r in maxi(lefts.size(), rights.size()):
		if r < lefts.size(): pyl_list.append({"src": "pylon", "side": "L", "local": lefts[r].position})
		if r < rights.size(): pyl_list.append({"src": "pylon", "side": "R", "local": rights[r].position})
	pyl_list = pyl_list.slice(0, n_pyl)
	var order: Array = []
	while not bay_list.is_empty() or not pyl_list.is_empty():
		if not bay_list.is_empty(): order.append(bay_list.pop_front())
		if not pyl_list.is_empty(): order.append(pyl_list.pop_front())
	# release distances: bombs land spaced along the run, centred on the aim point
	var gy: float = battle.ground_h(f.aim.x, f.aim.z)
	for k in order.size():
		var o: Dictionary = order[k]
		var lp: Vector3 = o.local * UnitDefs.SCALE.bomber
		var h: float = maxf(1.0, f.pos.y + f.alt + lp.y - gy)
		var t_fall := (-SEP_V + sqrt(SEP_V * SEP_V + 2.0 * G * h)) / G
		var fwd := -lp.z          # model -Z is forward
		var land := -spacing * float(n - 1) / 2.0 + float(k) * spacing
		o["along"] = land - fwd - f.speed * t_fall
		o["t_fall"] = t_fall
	return order


func _stow_slots(model: Node3D, bay: int, k: int, bd: Dictionary) -> Array:
	var out: Array = []
	if k <= 0: return out
	var a := model.find_child("Bay%da" % bay, false, false) as Node3D
	var b := model.find_child("Bay%db" % bay, false, false) as Node3D
	if a == null or b == null:
		for i in k: out.append(Vector3(0, -1.0, 0))
		return out
	var cols := int(bd.stow[0]); var tiers := int(bd.stow[1])
	var dx := float(bd.stow[2]); var dz := float(bd.stow[3])
	var per_row := cols * tiers
	var rows := int(ceil(float(k) / float(per_row)))
	for t in tiers:
		for r in rows:
			var c: Vector3 = a.position.lerp(b.position, 0.5 if rows == 1 else float(r) / float(rows - 1))
			for cc in cols:
				var x := (float(cc) - float(cols - 1) / 2.0) * dx
				out.append(c + Vector3(x, (float(t) - float(tiers - 1)) * dz, 0))
	return out.slice(0, k)


# ------------------------------------------------------------------ simulation
var tick_us := 0                 # cost accounting for the performance test (strike ticks with aircraft or bombs alive)
var ticks := 0


func tick(dt: float) -> void:
	var t0 := Time.get_ticks_usec()
	var any := false
	for f in battle.flights.duplicate():
		if not f.has("strike"): continue
		any = true
		_fly(f, dt)
	for b in battle.bombs.duplicate():
		if not b.has("strike"): continue
		any = true
		_fall(b, dt)
	if any:
		tick_us += Time.get_ticks_usec() - t0
		ticks += 1


func _fly(f: Dictionary, dt: float) -> void:
	f.pos += f.dir * f.speed * dt
	var terrain: TerrainMap = battle.terrain
	if terrain:   # same look-ahead terrain clearance as the other support aircraft
		var want := terrain.height_at(f.pos.x, f.pos.z)
		for i in range(1, 7):
			var q: Vector3 = f.pos + f.dir * f.speed * 3.0 * float(i) / 6.0
			want = maxf(want, terrain.height_at(q.x, q.z))
		f.pos.y = maxf(move_toward(f.pos.y, want, dt * (45.0 if want > f.pos.y else 10.0)), terrain.height_at(f.pos.x, f.pos.z))
	f.node.position = f.pos
	var along: float = (f.pos - f.aim).dot(f.dir)
	var plan: Array = f.plan
	# B-1 wing sweep: from the cruise sweep to fully swept for the run
	if f.bd.get("sweep_deg", 0.0) > 0.0:
		var to_run: float = (float(plan[0].along) - along) / f.speed if not plan.is_empty() else 0.0
		var want_s := 1.0 if to_run < 9.0 else 0.0
		f.sweep = move_toward(f.sweep, want_s, dt / 2.5)
		var a: float = deg_to_rad(float(f.bd.sweep_deg)) * f.sweep
		if f.wing_l: f.wing_l.rotation.y = a
		if f.wing_r: f.wing_r.rotation.y = -a
	# bay doors
	if not plan.is_empty():
		var t_first: float = (float(plan[0].along) - along) / f.speed
		if f.door_t < 0.0 and t_first <= DOOR_LEAD:
			f.door_t = battle.sim_time
			_stage(f)
			events.append({"ev": "doors_open", "t": battle.sim_time, "i": f.index, "type": f.type})
		var target := 0.0
		if f.door_t >= 0.0: target = 1.0
		if f.dropped >= plan.size() and battle.sim_time - f.last_rel > DOOR_CLOSE_AFTER: target = 0.0
		var rate := 1.0 / (DOOR_OPEN_S if target > f.doors else DOOR_CLOSE_S)
		var was: float = f.doors
		f.doors = move_toward(f.doors, target, dt * rate)
		if was > 0.0 and f.doors == 0.0: events.append({"ev": "doors_closed", "t": battle.sim_time, "i": f.index, "type": f.type})
		_set_doors(f)
	# releases
	while f.dropped < plan.size() and along >= float(plan[f.dropped].along):
		_release(f, plan[f.dropped])
		f.dropped += 1
		f.last_rel = battle.sim_time
	if not f.has("snd") and along > -f.speed * 3.5 and (f.lead or f.index % 2 == 0):
		f["snd"] = true
		SFX.play(f.node, "jet_flyby", f.pos, 5.0, 0.75 if f.type == "b52" else 1.0, true)
	if along > 520.0:
		f.node.queue_free()
		battle.flights.erase(f)
		events.append({"ev": "gone", "t": battle.sim_time, "i": f.index, "type": f.type})


func door_nodes(f: Dictionary) -> Array:
	return f.door_list


static func _find_doors(model: Node3D, bays: int) -> Array:
	var out: Array = []
	for b in bays:
		for s in ["L", "R"]:
			var d := model.find_child("Door%d%s" % [b, s], false, false) as Node3D
			if d: out.append(d)
	return out


func _set_doors(f: Dictionary) -> void:
	var k: float = f.doors
	var e := k * k * (3.0 - 2.0 * k)   # smoothstep
	var ang := deg_to_rad(float(f.bd.door_deg)) * e
	for d in door_nodes(f):
		d.rotation.z = -ang if String(d.name).ends_with("L") else ang


## Bombs appear in the bay (and the pylon racks become individual bombs) when the doors start to open.
func _stage(f: Dictionary) -> void:
	var sc := _scene(BOMB_SCENES[f.bd.bomb]) as PackedScene
	if sc == null: return
	for o in f.plan:
		var n: Node3D = sc.instantiate()
		n.scale = Vector3.ONE * float(f.bd.bomb_scale)
		n.position = o.local
		f.model.add_child(n)
		o["node"] = n
	for s in ["L", "R"]:
		var st := f.model.find_child("Stores" + s, false, false) as Node3D
		# StoresL/R hold only the modelled rack bombs (the pylon and ejector beam are part of Body): once individual
		# bombs are staged at the same stations the modelled ones are hidden
		if st and f.plan.any(func(o): return o.src == "pylon"): st.visible = false


func _release(f: Dictionary, o: Dictionary) -> void:
	var n: Node3D = o.get("node")
	var gt: Transform3D
	if n == null or not is_instance_valid(n):
		var sc := _scene(BOMB_SCENES[f.bd.bomb]) as PackedScene
		n = sc.instantiate()
		f.model.add_child(n)
		n.position = o.local
		n.scale = Vector3.ONE * float(f.bd.bomb_scale)
	gt = n.global_transform
	n.get_parent().remove_child(n)
	battle.add_child(n)
	n.global_transform = gt
	n.reset_physics_interpolation()
	var rng: RandomNumberGenerator = battle.rng
	var scatter: Vector3 = f.right * rng.randf_range(-1.2, 1.2) * 0.8
	var vel: Vector3 = f.dir * f.speed + Vector3.DOWN * SEP_V + scatter * 0.4
	var b := {"node": n, "pos": gt.origin, "vel": vel, "dmg": f.dmg, "splash": f.splash, "team": f.team, "strike": true,
		"age": 0.0, "q": gt.basis.orthonormalized().get_rotation_quaternion(), "scale": gt.basis.get_scale(), "wob": Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(0, TAU)), "type": f.type}
	battle.bombs.append(b)
	f.released.append(b)
	# diagnostics for the acceptance tests: door angle at this release and distance from the bay weapon line
	var rec := {"ev": "release", "t": battle.sim_time, "i": f.index, "type": f.type, "src": o.src, "pos": gt.origin}
	if o.src == "bay":
		var dmin := 999.0
		for d in door_nodes(f):
			if String(d.name).begins_with("Door%d" % int(o.bay)): dmin = minf(dmin, absf(rad_to_deg(d.rotation.z)))
		rec["door_deg"] = dmin
		var a := f.model.find_child("Bay%da" % int(o.bay), false, false) as Node3D
		var bb := f.model.find_child("Bay%db" % int(o.bay), false, false) as Node3D
		if a and bb:
			var pa := a.global_position; var pb := bb.global_position
			var seg := pb - pa
			var tt := clampf((gt.origin - pa).dot(seg) / maxf(seg.length_squared(), 1e-4), 0.0, 1.0)
			rec["bay_err"] = (pa + seg * tt).distance_to(gt.origin)
	events.append(rec)
	if battle.bombs.size() % 3 == 0: SFX.play(battle, "bomb_fall", gt.origin, -3.0, rng.randf_range(0.92, 1.08))


func _fall(b: Dictionary, dt: float) -> void:
	b.age += dt
	b.vel.y -= G * dt
	b.pos += b.vel * dt
	var n: Node3D = b.node
	if is_instance_valid(n):
		n.global_position = b.pos
		# separation tumble: the bomb noses over towards its velocity with a decaying wobble (presentation only)
		var want := Basis.looking_at(b.vel.normalized(), Vector3.UP if absf(b.vel.normalized().y) < 0.98 else Vector3.RIGHT)
		var k := exp(-b.age * 1.6)
		var wob := Basis(Vector3.RIGHT, 0.35 * k * sin(b.age * 6.0 + b.wob.z) * b.wob.x) * Basis(Vector3.UP, 0.25 * k * sin(b.age * 5.0 + b.wob.z * 1.7) * b.wob.y)
		b.q = (b.q as Quaternion).slerp(want.get_rotation_quaternion(), clampf(dt * 1.4, 0.0, 1.0))
		n.global_transform.basis = (Basis(b.q) * wob).orthonormalized().scaled(b.scale)
	var gy: float = battle.ground_h(b.pos.x, b.pos.z)
	if b.pos.y <= gy + 0.3:
		var p := Vector3(b.pos.x, gy + 0.2, b.pos.z)
		battle.bomb_impact(p, b.dmg, b.splash, b.team)
		b["impact"] = p
		if is_instance_valid(n): n.queue_free()
		battle.bombs.erase(b)
		events.append({"ev": "impact", "t": battle.sim_time, "pos": p, "type": b.type})


# ------------------------------------------------------------------ presentation
func _effects(f: Dictionary) -> void:
	var model: Node3D = f.model
	var ex: Array = []
	for i in 16:
		var e := model.find_child("Exhaust%d" % i, false, false) as Node3D
		if e == null: break
		ex.append(e.position)
	# contrails: one per engine pair (keeps particle counts low for five-ship packages)
	var trails: Array = []
	var step := 2 if ex.size() >= 4 else 1
	for i in range(0, ex.size(), step):
		var p: Vector3 = ex[i] if step == 1 else (ex[i] + ex[i + 1]) * 0.5
		trails.append(p)
	for p in trails:
		FX.exhaust_trail(model, p + Vector3(0, 0, 1.0), 1.2 if f.type == "b52" else 1.0, true)
	for p in trails:
		model.add_child(_shimmer(p + Vector3(0, 0, 2.2), 2.4 if f.type == "b52" else 2.0))


static var _shimmer_mat: ShaderMaterial = null


## Engine heat shimmer: a small camera-facing quad that refracts the screen behind it (one screen copy per frame).
static func _shimmer(pos: Vector3, size: float) -> MeshInstance3D:
	if _shimmer_mat == null:
		var sh := Shader.new()
		sh.code = """shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
void vertex() {
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
}
void fragment() {
	vec2 c = UV - vec2(0.5);
	float fall = clamp(1.0 - length(c) * 2.0, 0.0, 1.0);
	vec2 off = vec2(sin(UV.y * 31.0 + TIME * 17.0), cos(UV.x * 27.0 + TIME * 13.0)) * 0.006 * fall;
	ALBEDO = texture(screen_tex, SCREEN_UV + off).rgb;
	ALPHA = fall * 0.9;
}"""
		_shimmer_mat = ShaderMaterial.new()
		_shimmer_mat.shader = sh
	var mi := MeshInstance3D.new()
	var q := QuadMesh.new(); q.size = Vector2(size, size)
	q.material = _shimmer_mat
	mi.mesh = q
	mi.position = pos
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


func cam_mode() -> String:
	var forced := str(battle.args.get("strikecam", ""))
	if battle._automated():
		if not battle.args.has("strikecam"): return "Off"
		return "Full screen" if forced == "full" else "Picture-in-picture"
	return str(Game.settings.get("strike_cam", "Picture-in-picture"))


func _maybe_camera(group: Array, title: String) -> void:
	var mode := cam_mode()
	if mode == "Off" or (cam != null and is_instance_valid(cam)) or DisplayServer.get_name() == "headless" and not battle.args.has("strikecam"):
		return
	var c: StrikeCam = StrikeCam.new()
	c.battle = battle
	c.director = self
	c.group = group
	c.title = title
	c.full = mode == "Full screen"
	cam = c
	battle.add_child(c)
	events.append({"ev": "cam_open", "t": battle.sim_time, "mode": mode})


func on_cam_closed() -> void:
	cam = null
	events.append({"ev": "cam_close", "t": battle.sim_time})

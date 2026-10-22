# Steel Accord - battle: map, navigation, fixed-step simulation, command queue, combat resolution, support powers.
# All gameplay state changes happen in sim_tick() at a fixed 30 Hz; player/AI orders enter through issue()
# and are executed at the start of the next tick and logged with their tick number (replay groundwork).
class_name Battle
extends Node3D

const TICK_HZ := 30
var MAP_HALF := 300.0   # half the playable size; 300 on the flat Proving Ground, read from map.json on terrain maps
const PAD_SIZE := 28.0
const PAD_POSITIONS := [Vector3(150, 0, 150), Vector3(184, 0, 150), Vector3(218, 0, 150), Vector3(252, 0, 150), Vector3(150, 0, 184), Vector3(184, 0, 184), Vector3(218, 0, 184)]

var map_bounds := Rect2(-MAP_HALF, -MAP_HALF, MAP_HALF * 2, MAP_HALF * 2)
var units: Array[Unit] = []
var by_id := {}
var obstacles_2d: Array[Vector3] = []   # x, z, radius
var rng := RandomNumberGenerator.new()
var sim_time := 0.0
var tick_n := 0
var pending: Array = []
var command_log: Array = []
var shots: Array = []          # projectiles in flight
var debris: Array = []
var flights: Array = []        # support-power aircraft
var bombs: Array = []
var reveal_zones: Array = []
var power_ready := [{}, {}]    # per team: power id -> sim time when available
var seen := {}
var gnav: GridNav
var nav_ready := false
var game_over := false
var ai: EnemyAI
var props := {}
var args := {}
var diag: Node = null
var pause_menu: PauseMenu
var kills := 0
var shots_by := {}   # shooter uid -> rounds fired (diagnostics / tests)
var losses := 0
var FOG_N := 80   # 8 m cells over 640 m; edges are smoothed by linear filtering in the shaders
var FOG_RECT := Rect2(-320, -320, 640, 640)
# ---- heightfield maps (maps/<id>/map.json): terrain, per-movement-class navigation, oil derricks
var map_id := "proving_ground"
var terrain: TerrainMap = null
var navs := {}                  # movement class ("infantry" / "wheeled" / "tracked") -> GridNav
var move_rules := {}            # movement class -> rules from map.json
var build_max_slope := 8.0
var derricks: Array = []        # {"id", "pos", "owner", "progress": [t0, t1], "income", "every", "timer", "node", ...}
var derrick_income := [0, 0]
var minimap_tex: ImageTexture = null
var prop_roots: Array = []      # world positions of placed map props (grounding checks)
var fog_img: Image
var fog_tex: ImageTexture
var fog_mini_img: Image
var fog_mini_tex: ImageTexture
var explored := PackedByteArray()
var fog_t := 0.0
var fog_stamps := {}
var fog_vis := PackedByteArray()
var bomb_log: Array = []
# ---- economy (B1.2 base loop)
var scenario := "base"          # "base": skirmish from a Command Center; "army": the G1 armour + air wing test scenario
var cash := [0, 0]
var income := [0, 0]            # total cash delivered by haulers (stats / tests)
var piles: Array = []           # {"pos": Vector3, "cash": int, "node": Node3D}
var start_pos := [Vector3(0, 0, 225), Vector3(0, 0, -225)]
var base_ai: RefCounted = null

var camera: RTSCamera
var commander: Commander
var hud: HUD


func _ready() -> void:
	args = _args()
	scenario = "army" if ("army" in args or ("test" in args and not "base" in args) or "airdiag" in args or "evidence" in args) else "base"
	var _t0 := Time.get_ticks_msec()
	_select_map()
	print("LOAD select_map %d ms" % (Time.get_ticks_msec() - _t0))
	_init_fog()
	rng.seed = 20261021
	Engine.physics_ticks_per_second = TICK_HZ
	await World.environment(self)
	props = World.props()
	if terrain:
		add_child(terrain)
		await terrain.build_visual()
		print("LOAD terrain visual %d ms" % (Time.get_ticks_msec() - _t0))
		_build_terrain_map()
		print("LOAD props %d ms" % (Time.get_ticks_msec() - _t0))
	else:
		await World.terrain(self, MAP_HALF + 30.0, 0.0)
		_build_map()
	await _bake_nav()
	print("LOAD nav %d ms" % (Time.get_ticks_msec() - _t0))
	_spawn_forces()
	print("LOAD forces %d ms" % (Time.get_ticks_msec() - _t0))
	for id in UnitDefs.POWERS:
		power_ready[0][id] = 0.0
		power_ready[1][id] = 0.0
	camera = RTSCamera.new()
	camera.bounds = map_bounds.grow(-10)
	camera.terrain = terrain
	if terrain: camera.zoom_max = 300.0
	add_child(camera)
	if scenario == "base": camera.focus(start_pos[0] + Vector3(0, 0, -25))
	else: camera.focus(Vector3(30, 0, 140.0 if "close" in args else 205.0))
	commander = Commander.new()
	commander.battle = self; commander.camera = camera
	add_child(commander)
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = HUD.new()
	hud.battle = self; hud.commander = commander; hud.camera = camera
	layer.add_child(hud)
	var diff: Dictionary = Game.DIFFICULTY.get(Game.settings.difficulty, Game.DIFFICULTY["Normal"])
	if scenario == "army":
		ai = EnemyAI.new(self, 1, 30.0 if _automated() else float(diff.attack_after))
	elif not "noai" in args:
		base_ai = BaseAI.new(self, 1, Game.settings.difficulty)
	pause_menu = PauseMenu.new()
	pause_menu.battle = self
	add_child(pause_menu)
	apply_settings()
	if scenario == "base": hud.flash_message("Build up: select your Dozer and place a Power Plant. The enemy base is to the north.")
	else: hud.flash_message("Enemy armour reported to the north. Destroy all hostile units.")
	if "uishots" in args:
		var us: Node = load("res://scripts/evidence_ui.gd").new()
		us.battle = self
		add_child(us)
	elif "airdiag" in args:
		var dg: Node = load("res://scripts/airdiag.gd").new()
		dg.battle = self
		add_child(dg)
	elif "evidence" in args:
		var ev: Node = load("res://scripts/evidence.gd").new()
		ev.battle = self
		add_child(ev)
	elif "vischeck" in args:
		var vc: Node = load("res://scripts/vischeck.gd").new()
		vc.battle = self
		add_child(vc)
	elif "m1shots" in args:
		var m1: Node = load("res://scripts/m1shots.gd").new()
		m1.battle = self
		add_child(m1)
	elif "pilotshots" in args:
		var ps: Node = load("res://scripts/pilotshots.gd").new()
		ps.battle = self
		add_child(ps)
	elif "baseshots" in args:
		var bs: Node = load("res://scripts/baseshots.gd").new()
		bs.battle = self
		add_child(bs)
	elif "maptest" in args:
		var mt: Node = load("res://scripts/autotest_map.gd").new()
		mt.battle = self
		add_child(mt)
	elif "basetest" in args:
		var bt: Node = load("res://scripts/autotest_base.gd").new()
		bt.battle = self
		add_child(bt)
	elif "test" in args:
		var t: Node = load("res://scripts/autotest.gd").new()
		t.battle = self
		add_child(t)


## Map choice: "map=<id>" on the command line, otherwise the menu setting. Automated test modes keep the flat
## Proving Ground unless a map is named explicitly, so the existing regression tests are unchanged.
func _select_map() -> void:
	var want := str(args.get("map", "" if _automated() else str(Game.settings.get("map", "proving_ground"))))
	if want == "" or want == "proving_ground" or not TerrainMap.exists(want):
		map_id = "proving_ground"
		return
	var tm := TerrainMap.new()
	tm.name = "Terrain"
	if not tm.load_map(want):
		push_error("map %s failed to load; using the Proving Ground" % want)
		return
	terrain = tm
	map_id = want
	var d: Dictionary = tm.data
	var half := tm.half_size() - float(d.get("edge_margin_m", 24.0))
	MAP_HALF = half
	map_bounds = Rect2(-half, -half, half * 2.0, half * 2.0)
	var fh := tm.half_size()
	FOG_RECT = Rect2(-fh, -fh, fh * 2.0, fh * 2.0)
	FOG_N = int(ceil(fh * 2.0 / 8.0))
	build_max_slope = float(d.get("building_max_slope_deg", 8.0))
	move_rules = d.get("movement", d.get("movement_classes", {}))
	var sp: Array = []
	for st in d.get("starts", []):
		sp.append(map_point(st))
	if sp.size() >= 2: start_pos = [sp[0], sp[1]]
	print("MAP %s size=%.0f m playable=%.0f m samples=%d step=%.2f m" % [map_id, fh * 2.0, half * 2.0, tm.n, tm.step])


## Reads a map.json point: [x, z], [x, y, z], {"x", "z"} or {"pos": ...}; returns it grounded on the terrain.
func map_point(v: Variant) -> Vector3:
	var p := Vector3.ZERO
	if v is Dictionary:
		if v.has("pos"): return map_point(v.pos)
		p = Vector3(float(v.get("x", 0.0)), 0.0, float(v.get("z", 0.0)))
	elif v is Array and v.size() == 2: p = Vector3(float(v[0]), 0.0, float(v[1]))
	elif v is Array and v.size() >= 3: p = Vector3(float(v[0]), 0.0, float(v[2]))
	p.y = ground_h(p.x, p.z)
	return p


## Terrain height (0 on the flat Proving Ground). The single source used for grounding everything.
func ground_h(x: float, z: float) -> float:
	return terrain.height_at(x, z) if terrain else 0.0


func grounded(p: Vector3) -> Vector3:
	return Vector3(p.x, ground_h(p.x, p.z), p.z)


func _automated() -> bool:
	return "test" in args or "maptest" in args or "airdiag" in args or "evidence" in args or "vischeck" in args or "basetest" in args or "baseshots" in args or "pilotshots" in args or "m1shots" in args


## Player options from the menus (mouse scheme, edge scrolling, camera speed).
func apply_settings() -> void:
	commander.scheme = Game.settings.mouse_scheme if not _automated() else "classic"
	camera.edge_pan = Game.settings.edge_pan and not _automated()
	camera.speed_mult = float(Game.settings.cam_speed)
	if hud: hud.scheme_btn.text = "Mouse: " + commander.scheme.capitalize()


func open_menu() -> void:
	if not game_over: pause_menu.open_pause()


func _args() -> Dictionary:
	var d := {}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		d[kv[0]] = kv[1] if kv.size() > 1 else ""
	return d


# ------------------------------------------------------------------ map
func _build_map() -> void:
	# rock outcrops forming three approach lanes, plus scattered boulders, bushes and grass
	var outcrops := [Vector3(-124, 0, 0), Vector3(116, 0, -16), Vector3(-20, 0, -110), Vector3(28, 0, 104), Vector3(-220, 0, 140), Vector3(210, 0, -150), Vector3(-200, 0, -200), Vector3(-90, 0, 230)]
	var k := 0
	for c in outcrops:
		for i in 8:
			var a := rng.randf() * TAU
			var d := rng.randf_range(0.0, 16.0)
			var s := rng.randf_range(3.0, 6.0)
			var p: Vector3 = c + Vector3(cos(a) * d, 0, sin(a) * d)
			World.rock(self, props["Rock%d" % (k % 6)], p, s, rng.randf() * TAU)
			obstacles_2d.append(Vector3(p.x, p.z, s * 1.4))
			k += 1
	for i in 90:
		var p := Vector3(rng.randf_range(-285, 285), 0, rng.randf_range(-285, 285))
		if _reserved(p, 10.0): continue
		var s := rng.randf_range(0.6, 1.8)
		World.rock(self, props["Rock%d" % (i % 6)], p, s, rng.randf() * TAU)
		if s > 1.1: obstacles_2d.append(Vector3(p.x, p.z, s * 1.3))
	for i in 220:
		var p := Vector3(rng.randf_range(-295, 295), 0, rng.randf_range(-295, 295))
		if _reserved(p, 6.0): continue
		World.bush(self, props["Bush%d" % (i % 4)], p, rng.randf_range(0.8, 1.8), rng.randf() * TAU,
			Color(0.85, 0.9, 0.8).lerp(Color(1.15, 1.1, 0.85), rng.randf()))
	if scenario == "army": _build_pads()
	var tries := 70000 if "lite" in args else 260000
	World.grass(self, Rect2(-310, -310, 620, 620), tries, rng, func(p): return _in_obstacle(p, 1.0) or _on_pad(p))


## Start areas, the air base and its approach lane stay clear of rocks and bushes.
func _reserved(p: Vector3, margin: float) -> bool:
	if absf(p.z) > 185 and absf(p.x) < 110: return true
	if p.x > 125 - margin and p.z > 125 - margin: return true
	return false


func _build_pads() -> void:
	var con := StandardMaterial3D.new(); con.albedo_color = Color(0.42, 0.42, 0.40); con.roughness = 0.85
	var mark := StandardMaterial3D.new(); mark.albedo_color = Color(0.85, 0.82, 0.6); mark.roughness = 0.8
	for p: Vector3 in PAD_POSITIONS:
		var slab := MeshInstance3D.new()
		var b := BoxMesh.new(); b.size = Vector3(PAD_SIZE, 0.3, PAD_SIZE); b.material = con
		slab.mesh = b; slab.position = p + Vector3(0, 0.1, 0)
		add_child(slab)
		var ring := MeshInstance3D.new()
		var t := TorusMesh.new(); t.inner_radius = 9.0; t.outer_radius = 9.6; t.material = mark
		ring.mesh = t; ring.scale = Vector3(1, 0.02, 1); ring.position = p + Vector3(0, 0.27, 0)
		add_child(ring)


func _on_pad(p: Vector3) -> bool:
	if scenario != "army": return false
	for q: Vector3 in PAD_POSITIONS:
		if absf(p.x - q.x) < PAD_SIZE * 0.55 and absf(p.z - q.z) < PAD_SIZE * 0.55: return true
	return false


func _in_obstacle(p: Vector3, margin: float) -> bool:
	for o in obstacles_2d:
		if Vector2(p.x - o.x, p.z - o.y).length() < o.z + margin: return true
	return false


func _bake_nav() -> void:
	if terrain:
		var cell: float = float(terrain.data.get("nav_cell_m", 4.0))
		var t0 := Time.get_ticks_msec()
		for cls in ["infantry", "wheeled", "tracked"]:
			var g := GridNav.new(terrain.half_size(), cell)
			g.apply_terrain(terrain, cls, move_rules.get(cls, {}))
			navs[cls] = g
		gnav = navs.tracked
		for o in obstacles_2d:
			nav_block_circle(Vector3(o.x, 0, o.y), o.z * 0.75 + 2.0)
		for b in terrain.data.get("blockers", []):
			var pts: Array = b.get("points", [])
			for i in pts.size() - 1:
				for g in navs.values(): g.block_segment(map_point(pts[i]), map_point(pts[i + 1]), float(b.get("radius_m", 3.0)))
		print("NAV terrain cell=%.1f m grid=%d  steep cells: inf=%d wheeled=%d tracked=%d  (%d ms)" % [cell, gnav.n,
			navs.infantry.slope_cells, navs.wheeled.slope_cells, navs.tracked.slope_cells, Time.get_ticks_msec() - t0])
	else:
		gnav = GridNav.new(MAP_HALF + 30.0)
		navs = {"infantry": gnav, "wheeled": gnav, "tracked": gnav}
		for o in obstacles_2d:
			gnav.block_circle(Vector3(o.x, 0, o.y), o.z * 0.75 + 2.0)
		print("NAV grid=", gnav.n, "x", gnav.n, " obstacles=", obstacles_2d.size())
	nav_ready = true


func nav_block_circle(p: Vector3, r: float) -> void:
	for g in _nav_set(): g.block_circle(p, r)


func nav_set_structure(p: Vector3, half: Vector2, on: bool) -> void:
	for g in _nav_set(): g.set_structure(p, half, on)


func _nav_set() -> Array:
	var out: Array = []
	for g in navs.values():
		if not (g in out): out.append(g)
	if out.is_empty() and gnav: out.append(gnav)
	return out


func find_path(from: Vector3, to: Vector3, move_class := "tracked") -> PackedVector3Array:
	var g: GridNav = navs.get(move_class, gnav)
	if g: return g.find_path(from, to)
	return PackedVector3Array([from, to])


## Terrain speed factor for a ground unit at its position (roads help wheels; rough ground and slopes slow).
func terrain_speed_mult(u: Unit) -> float:
	if terrain == null: return 1.0
	var r: Dictionary = move_rules.get(u.move_class(), {})
	var p := u.position
	var s := terrain.slope_deg_at(p.x, p.z)
	var m := 1.0 / sqrt(maxf(terrain.material_cost(p.x, p.z, r.get("cost", {})), 0.2))
	m *= 1.0 - float(r.get("slope_slow", 0.3)) * clampf(s / float(r.get("max_slope_deg", 30.0)), 0.0, 1.0)
	return clampf(m, 0.4, 1.25)


func _spawn_forces() -> void:
	if scenario == "base":
		_spawn_bases()
		return
	var zb := 140.0 if "close" in args else 210.0
	var zr := -140.0 if "close" in args else -215.0
	for i in 6:
		_spawn("vanguard", 0, Vector3(-20 + (i % 3) * 20, 0, zb + (i / 3) * 14), 0.0)
	for i in 7:
		_spawn("vanguard", 1, Vector3(-48 + i * 16, 0, zr - (i % 2) * 12), PI)
	# air wing on the pads (south-east). "airshow" adds every controllable aircraft type.
	var wing := ["f16", "f16", "ah64", "a10"]
	if not _automated() and not Game.settings.air_wing: wing = []
	if "airshow" in args: wing = ["f16", "fa18", "f22", "a10", "ah64", "uh60", "ch47"]
	if "noair" in args: wing = []
	for i in wing.size():
		var u := _spawn(wing[i], 0, PAD_POSITIONS[i], 0.0)
		if u.is_air():
			u.state = Unit.S.LANDED; u.altitude = 0.4; u.speed_cur = 0.0; u.body.position.y = 0.4; u.airborne = false


func _spawn(kind: String, team: int, pos: Vector3, yaw: float) -> Unit:
	var u := Unit.new()
	add_child(u)
	u.setup(self, kind, team, units.size() + 1, grounded(pos), yaw)
	u.reset_physics_interpolation()
	units.append(u)
	by_id[u.uid] = u
	return u


# ------------------------------------------------------------------ commands
func issue(cmd: Dictionary) -> void:
	pending.append(cmd)


func _execute(cmd: Dictionary) -> void:
	command_log.append({"tick": tick_n, "cmd": cmd})
	if cmd.type == "power":
		launch_power(cmd.team, cmd.id, cmd.pos)
		return
	if cmd.type == "unload_one":
		var tr: Unit = by_id.get(cmd.id)
		var pu: Unit = by_id.get(cmd.passenger)
		if tr and pu and not tr.dead and tr.team == cmd.team and tr.can_exchange(): unload_one(tr, pu)
		return
	if cmd.type in ["place", "produce", "cancel_unit", "rally", "sell", "cancel_build", "repair"]:
		_execute_econ(cmd)
		return
	var ids: Array = cmd.get("ids", [])
	for i in ids.size():
		var u: Unit = by_id.get(ids[i])
		if u == null or u.dead: continue
		if u.state in [Unit.S.LANDED, Unit.S.RETURN] and u.domain == "heli" and cmd.type in ["move", "attack_move", "attack", "force_ground", "guard", "scatter"]:
			u.state = Unit.S.IDLE
		elif u.state == Unit.S.LANDED and cmd.type in ["move", "attack_move", "attack", "force_ground", "guard"]:
			u.state = Unit.S.IDLE
		match cmd.type:
			"move": u.order_move(cmd.points[i], cmd.get("append", false))
			"attack_move": u.order_attack_move(cmd.points[i])
			"attack":
				var t: Unit = by_id.get(cmd.target)
				if t and not t.dead: u.order_attack(t)
			"force_ground": u.order_force_ground(cmd.pos)
			"guard": u.order_guard(cmd.points[i], by_id.get(cmd.get("unit", -1)))
			"stop": u.order_stop()
			"board":
				var tr: Unit = by_id.get(cmd.target)
				if tr and tr.accepts(u):
					u.board_target = tr
					u.order_move(tr.position)
			"unload":
				if u.is_transport() and not u.passengers.is_empty():
					if u.domain == "heli": u.unload_pending = true
					elif u.can_exchange(): unload_all(u)
					else: u.unload_pending = true
			"build":
				var b: Node = by_id.get(cmd.site)
				if b is Building and not b.dead and not b.built and b.team == u.team and u.def.get("builder", false):
					u.order_build(b)
			"return": u.order_return()
			"scatter":
				var away := Vector3(u.position.x - cmd.center.x, 0, u.position.z - cmd.center.z)
				if away.length() < 0.5: away = Vector3(rng.randf_range(-1, 1), 0, rng.randf_range(-1, 1))
				u.order_move(u.position + away.normalized() * 14.0)


# ------------------------------------------------------------------ simulation
func _physics_process(dt: float) -> void:
	if units.is_empty(): return
	var _tt := Time.get_ticks_usec()
	sim_tick(dt)
	if "proftick" in args and tick_n % 30 == 0: printerr("TICK %d sim=%.1f %.1f ms" % [tick_n, sim_time, (Time.get_ticks_usec() - _tt) / 1000.0])


func sim_tick(dt: float) -> void:
	for c in pending: _execute(c)
	pending.clear()
	if ai and not game_over: ai.tick(dt)
	if base_ai and not game_over: base_ai.tick(dt)
	for u in units:
		u.sim_tick(dt)
	_update_boarding()
	_separate()
	_update_shots(dt)
	_update_flights(dt)
	_update_bombs(dt)
	_update_supply_drops(dt)
	_ground_units(dt)
	_update_derricks(dt)
	if tick_n % 150 == 0:
		trend_samples.append([sim_time, income[0], spent[0], income[1], spent[1]])
		while trend_samples.size() > 13: trend_samples.pop_front()
	_update_debris(dt)
	_update_visibility()
	sim_time += dt
	tick_n += 1
	_check_end()


## Heightfield maps: every unit node stands on the terrain (aircraft altitude is above the local ground, smoothed so
## jets do not bob over every ridge); ground vehicles pitch and roll with the slope (presentation only).
func _ground_units(dt: float) -> void:
	if terrain == null: return
	for u in units:
		if u is Building: continue
		var h := terrain.height_at(u.position.x, u.position.z)
		if u.domain == "ground" or u.altitude < 3.0 or u.state == Unit.S.LANDED:
			u.position.y = h
		else:
			u.position.y = move_toward(u.position.y, h, dt * (12.0 if u.domain == "heli" else 30.0))
		if u.domain == "ground" and u.def.get("visual") != "infantry" and not u.dead:
			var nrm := terrain.normal_at(u.position.x, u.position.z)
			var grad := Vector2(-nrm.x / nrm.y, -nrm.z / nrm.y)
			var f := Vector2(-sin(u.heading), -cos(u.heading))
			var r := Vector2(cos(u.heading), -sin(u.heading))
			u.body.rotation.x = lerp_angle(u.body.rotation.x, atan(grad.dot(f)), minf(1.0, dt * 8.0))
			u.body.rotation.z = lerp_angle(u.body.rotation.z, atan(grad.dot(r)), minf(1.0, dt * 8.0))


func _separate() -> void:
	var live := units.filter(func(u): return not u.dead and u.domain != "jet" and not (u is Building))
	var blds := units.filter(func(u): return not u.dead and u is Building)
	for i in live.size():
		var a: Unit = live[i]
		for j in range(i + 1, live.size()):
			var b: Unit = live[j]
			if (a.domain == "ground") != (b.domain == "ground"): continue
			var d := Vector2(b.position.x - a.position.x, b.position.z - a.position.z)
			var min_d: float = (a.def.radius + b.def.radius) * 0.95
			var l := d.length()
			if l < min_d and l > 0.001:
				var push := (min_d - l) * 0.5 * d / l
				a.position -= Vector3(push.x, 0, push.y)
				b.position += Vector3(push.x, 0, push.y)
		if a.domain == "ground":
			for bb in blds:
				var b: Building = bb
				var dx := a.position.x - b.position.x
				var dz := a.position.z - b.position.z
				var ex: float = b.half.x + a.def.radius * 0.5 - absf(dx)
				var ez: float = b.half.y + a.def.radius * 0.5 - absf(dz)
				if ex > 0.0 and ez > 0.0:
					if ex < ez: a.position.x += signf(dx if dx != 0.0 else 1.0) * ex
					else: a.position.z += signf(dz if dz != 0.0 else 1.0) * ez
			for o in obstacles_2d:
				var d2 := Vector2(a.position.x - o.x, a.position.z - o.y)
				var r: float = o.z + a.def.radius * 0.6
				if d2.length() < r and d2.length() > 0.001:
					var n := d2.normalized() * r
					a.position = Vector3(o.x + n.x, 0, o.y + n.y)
	for u in units:
		if u.dead: continue
		var m := 0.0 if u.domain == "ground" else 30.0   # aircraft may overfly the edge by 30 m while turning
		u.position.x = clampf(u.position.x, map_bounds.position.x - m, map_bounds.end.x + m)
		u.position.z = clampf(u.position.z, map_bounds.position.y - m, map_bounds.end.y + m)


func find_enemy_near(u: Unit, r: float) -> Unit:
	return find_enemy_near_point(u, u.position, r)


func find_enemy_near_point(u: Unit, p: Vector3, r: float) -> Unit:
	var best: Unit = null
	var bd := r
	for o in units:
		if o.dead or o.team == u.team or not u.can_target(o): continue
		var d := Vector2(o.position.x - p.x, o.position.z - p.z).length()
		if d < bd: bd = d; best = o
	return best


## Spawn a projectile for weapon `w`. tunit may be null (force-fire at ground position tpos).
func fire(shooter: Unit, w: Dictionary, tunit: Unit, tpos: Vector3) -> void:
	shots_by[shooter.uid] = int(shots_by.get(shooter.uid, 0)) + 1
	var from := shooter.muzzle_pos()
	var aim: Vector3 = tunit.world_center() if tunit else Vector3(tpos.x, ground_h(tpos.x, tpos.z) + 0.3, tpos.z)
	var dist := from.distance_to(aim)
	if tunit:
		aim += tunit.vel * (dist / float(w.speed))
	var sc: float = float(w.spread) * dist / float(w.range)
	aim += Vector3(rng.randf_range(-sc, sc), rng.randf_range(-sc, sc) * 0.3, rng.randf_range(-sc, sc))
	var dir: Vector3 = (aim - from).normalized()
	_fire_sound(shooter, w, from)
	var node: Node3D
	match w.proj:
		"missile", "rocket":
			node = FX.missile_node(w.proj == "missile")
			FX.launch_puff(self, from)
		"bullet":
			if shooter.is_air():
				node = FX.tracer_mesh(0.22, 6.0)
				FX.small_flash(self, from)
			else:
				node = FX.tracer_mesh(0.08, 2.4)
				if rng.randf() < 0.5: FX.small_flash(self, from)
		_:
			node = FX.tracer_mesh(0.12, 4.0)
			FX.muzzle_flash(self, from, dir)
	add_child(node)
	node.global_position = from
	if dir.length() > 0.01: node.look_at(from + dir, Vector3.UP if absf(dir.y) < 0.99 else Vector3.RIGHT)
	node.reset_physics_interpolation()
	shots.append({"node": node, "pos": from, "dir": dir, "aim": aim, "left": dist, "speed": float(w.speed),
		"shooter": shooter, "target": tunit, "dmg": float(w.damage), "splash": float(w.splash),
		"homing": w.proj == "missile", "kind": w.proj, "targets": w.targets, "vs": w.get("vs", {}),
		"arc": w.proj == "arty", "dist0": maxf(dist, 1.0)})


var _snd_t := {}   # "uid:clip" -> sim time of the last report, so automatic weapons play one burst sound per burst


func _fire_sound(shooter: Unit, w: Dictionary, from: Vector3) -> void:
	var clip := ""
	var gap := 0.0
	var db := 0.0
	var pitch := 1.0
	match str(w.proj):
		"missile", "rocket": clip = "rocket_launch"; gap = 0.25; db = -2.0 if w.proj == "rocket" else 0.0; pitch = 1.15 if w.proj == "rocket" else 0.95
		"shell": clip = "explosion_big"; gap = 0.5; db = -9.0; pitch = 1.7
		"arty": clip = "explosion_big"; gap = 1.0; db = -3.0; pitch = 0.85
		"bullet":
			if w.id == "gau_cannon": clip = "a10_cannon"; gap = 1.9; db = 3.0
			elif shooter.def.get("visual") == "infantry": clip = "rifle_burst"; gap = 1.1; db = -6.0
			else: clip = "mg_burst"; gap = 1.25; db = -5.0
	if clip == "": return
	var key := "%d:%s" % [shooter.uid, clip]
	if sim_time - float(_snd_t.get(key, -99.0)) < gap: return
	_snd_t[key] = sim_time
	SFX.play(shooter.body if clip == "a10_cannon" else self, clip, from, db, pitch, clip == "a10_cannon")


func _update_shots(dt: float) -> void:
	for s in shots.duplicate():
		var t: Unit = s.target
		if s.homing and t and is_instance_valid(t) and not t.dead:
			var want: Vector3 = (t.world_center() - s.pos)
			s.left = want.length()
			s.dir = s.dir.lerp(want.normalized(), minf(1.0, dt * 6.0)).normalized()
		var step: float = s.speed * dt
		if step >= s.left:
			var p: Vector3 = s.pos + s.dir * s.left
			_impact(s, p)
			s.node.queue_free()
			shots.erase(s)
		else:
			s.pos += s.dir * step
			s.left -= step
			s.node.global_position = s.pos
			if s.get("arc", false):
				# ballistic shell: parabolic lift over the straight line (visual height only)
				var tf: float = 1.0 - s.left / s.dist0
				s.node.global_position = s.pos + Vector3.UP * (4.0 * s.dist0 * 0.22 * tf * (1.0 - tf))
			if s.dir.length() > 0.01:
				s.node.look_at(s.pos + s.dir, Vector3.UP if absf(s.dir.y) < 0.99 else Vector3.RIGHT)


func _impact(s: Dictionary, p: Vector3) -> void:
	var t: Unit = s.target
	var direct := false
	if t and is_instance_valid(t) and not t.dead:
		var c := t.world_center()
		direct = c.distance_to(p) < t.def.radius * 1.4 + 1.0
		if direct: t.take_damage(s.dmg * rng.randf_range(0.85, 1.15) * _dmg_mult(s.shooter) * _armor_mult(s, t), s.shooter)
	if diag and s.shooter and s.shooter.team == 0: diag.on_shot(s.shooter, t, p, direct)
	if s.splash > 0.0:
		for o in units:
			if o.dead or o == t or o.domain == "jet": continue
			if o.domain == "heli" and not ("heli" in s.targets): continue
			var d := o.world_center().distance_to(p)
			if d < s.splash:
				o.take_damage(s.dmg * 0.5 * (1.0 - d / s.splash) * _armor_mult(s, o), s.shooter)
	var gy := ground_h(p.x, p.z)
	var ground := p.y < gy + 1.5
	if s.kind == "arty":
		FX.explosion(self, Vector3(p.x, gy + 0.2, p.z), 1.1)
	elif s.kind == "bullet":
		FX.bullet_hit(self, Vector3(p.x, maxf(p.y, gy + 0.1), p.z), direct, s.shooter != null and s.shooter.is_air())
	elif direct or not ground:
		FX.impact(self, p, true)
	else:
		FX.impact(self, Vector3(p.x, gy + 0.1, p.z), false)


func _armor_mult(s: Dictionary, o: Unit) -> float:
	var a := UnitDefs.armor_of(o.def)
	var vs: Dictionary = s.get("vs", {})
	if vs.has(a): return float(vs[a])
	return float(UnitDefs.ARMOR_MULT.get(s.kind, {}).get(a, 1.0))


# ------------------------------------------------------------------ support powers
func _dmg_mult(shooter: Unit) -> float:
	if shooter == null or shooter.team != 1 or _automated(): return 1.0
	return float(Game.DIFFICULTY.get(Game.settings.difficulty, Game.DIFFICULTY["Normal"]).damage_mult)


func power_cooldown_left(team: int, id: String) -> float:
	return maxf(0.0, float(power_ready[team].get(id, 0.0)) - sim_time)


## Support powers that need a structure (e.g. Paratroopers need an Airfield) in the base scenario.
func power_problem(team: int, id: String) -> String:
	var p: Dictionary = UnitDefs.POWERS[id]
	if scenario == "base" and p.has("requires") and structures(team, p.requires).is_empty():
		return "Requires " + BuildingDefs.DEFS[p.requires].name
	return ""


func launch_power(team: int, id: String, target: Vector3) -> void:
	if power_cooldown_left(team, id) > 0.0 or power_problem(team, id) != "": return
	var p: Dictionary = UnitDefs.POWERS[id]
	power_ready[team][id] = sim_time + float(p.cooldown)
	var edge_z := map_bounds.end.y + 120.0 if team == 0 else map_bounds.position.y - 120.0
	var start := Vector3(target.x * 0.7, ground_h(target.x, target.z), edge_z)
	var dir := Vector3(target.x - start.x, 0, target.z - start.z).normalized()
	var node := Node3D.new()
	add_child(node)
	if ResourceLoader.exists(str(p.get("model3d", "_"))):
		var m3: Node3D = (load(p.model3d) as PackedScene).instantiate()
		m3.scale = Vector3.ONE * UnitDefs.SCALE.aircraft
		m3.position.y = p.altitude
		node.add_child(m3)
		for pr in m3.find_children("Prop*", "Node3D", true, false): node.set_meta("props", true)
	else:
		var s := Sprite3D.new()
		var tex: Texture2D = load(p.sprite)
		s.texture = tex; s.axis = Vector3.AXIS_Y; s.shaded = true; s.double_sided = true
		s.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
		s.pixel_size = float(p.length) / float(tex.get_height()) * 1.08
		s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		s.position.y = p.altitude
		node.add_child(s)
	var span: float = float(p.length) * (0.4 if id == "carpet" or id == "supersonic" else 0.3)
	for side in [-1.0, 1.0]:
		FX.exhaust_trail(node, Vector3(side * span * 0.5, float(p.altitude), float(p.length) * 0.35), 1.6, true)
	FX.target_marker(self, target, 14.0 if p.has("bombs") else 0.0)
	node.position = start
	node.rotation.y = atan2(-dir.x, -dir.z)
	node.reset_physics_interpolation()
	flights.append({"node": node, "pos": start, "dir": dir, "def": p, "id": id, "team": team, "target": target, "dropped": 0})
	if id == "recon":
		reveal_zones.append({"a": start, "b": target + dir * 400.0, "w": float(p.reveal_width), "team": team, "until": sim_time + float(p.reveal_time)})
	if hud: hud.flash_message("%s inbound" % p.name)


func _update_flights(dt: float) -> void:
	for f in flights.duplicate():
		var p: Dictionary = f.def
		for pr in f.node.find_children("Prop*", "Node3D", true, false): (pr as Node3D).rotate_object_local(Vector3.BACK, dt * 30.0)
		f.pos += f.dir * float(p.speed) * dt
		f.node.position = f.pos
		var along: float = (f.pos - f.target).dot(f.dir)   # <0 before the target, >0 after
		if p.has("troops"):
			var nt := int(p.troops)
			while int(f.dropped) < nt and along >= -14.0 + int(f.dropped) * 5.0:
				var u := _spawn(Nations.swap_unit(nation_of(f.team), str(p.unit)), f.team, f.pos + Vector3(0, 0, 0), atan2(-f.dir.x, -f.dir.z))
				u.start_parachute(float(p.altitude) - 4.0)
				u.reset_physics_interpolation()
				f.dropped += 1
		if not f.has("snd") and along > -float(p.speed) * 3.5:
			f["snd"] = true
			SFX.play(f.node, "jet_flyby", f.pos, 4.0, 0.8 if f.id == "carpet" else 1.0, true)
		if p.has("bombs"):
			var n := int(p.bombs)
			var fall := sqrt(2.0 * float(p.altitude) / 25.0)
			var lead := float(p.speed) * fall
			var first := -float(p.spacing) * (n - 1) / 2.0 - lead
			if f.dropped < n and along >= first + f.dropped * float(p.spacing):
				f.dropped += 1
				var b := FX.bomb_node()
				add_child(b)
				var bp: Vector3 = f.pos + Vector3.UP * float(p.altitude)
				b.global_position = bp
				b.reset_physics_interpolation()
				if bombs.size() % 3 == 0: SFX.play(self, "bomb_fall", bp, -3.0, randf_range(0.92, 1.08))
				bombs.append({"node": b, "pos": bp, "vel": f.dir * float(p.speed), "dmg": float(p.damage),
					"splash": float(p.splash), "team": f.team})
		if along > 450.0:
			f.node.queue_free()
			flights.erase(f)


func _update_bombs(dt: float) -> void:
	for b in bombs.duplicate():
		b.vel.y -= 25.0 * dt
		b.pos += b.vel * dt
		b.node.global_position = b.pos
		if b.vel.length() > 0.1: b.node.look_at(b.pos + b.vel, Vector3.RIGHT)
		var bgy := ground_h(b.pos.x, b.pos.z)
		if b.pos.y <= bgy + 0.3:
			var p := Vector3(b.pos.x, bgy + 0.2, b.pos.z)
			bomb_log.append(p)
			FX.explosion(self, p, clampf(b.splash / 7.0, 0.8, 2.2))
			for o in units:
				if o.dead or o.domain == "jet": continue
				var d := o.world_center().distance_to(p)
				if d < b.splash: o.take_damage(b.dmg * (1.0 - 0.6 * d / b.splash), null)
			b.node.queue_free()
			bombs.erase(b)


# ------------------------------------------------------------------ deaths and visibility
func on_unit_died(u: Unit) -> void:
	if not u.passengers.is_empty(): _lose_passengers(u)
	if u.engine_snd: u.engine_snd.stop()
	if u.team == 0: losses += 1
	else: kills += 1
	var vis_kind: String = u.def.get("visual", "model")
	if u is Building:
		FX.explosion(self, u.global_position + Vector3(0, 2, 0), 2.2)
		FX.wreck_fire(u.body)
	elif vis_kind == "infantry":
		FX.impact(self, u.global_position, false)
		_fade_out(u, 3.0)
	elif vis_kind == "vehicle_art":
		FX.explosion(self, u.global_position, 1.0)
		FX.wreck_fire(u.body)
		if u.card_sprite: u.card_sprite.modulate = Color(0.16, 0.14, 0.12)
	elif u.domain == "ground":
		FX.explosion(self, u.global_position, 1.0)
		FX.wreck_fire(u.body)
		if u.turret:
			var t := u.turret
			var xf := t.global_transform
			t.get_parent().remove_child(t)
			add_child(t)
			t.global_transform = xf
			t.reset_physics_interpolation()
			debris.append({"node": t, "vel": Vector3(rng.randf_range(-3, 3), rng.randf_range(9, 13), rng.randf_range(-3, 3)),
				"spin": Vector3(rng.randf_range(-3, 3), rng.randf_range(-4, 4), rng.randf_range(-3, 3)), "crash": false})
	else:
		FX.explosion(self, u.world_center(), 0.6)
		# the airframe falls and burns on impact
		debris.append({"node": u.body, "vel": u.vel * 0.6 + Vector3(0, -2, 0), "spin": Vector3(rng.randf_range(-1, 1), rng.randf_range(-2, 2), rng.randf_range(-1.5, 1.5)), "crash": true})
		for r in u.rotors: r.visible = false
	if u in commander.selected:
		commander.selected.erase(u)
		commander.selection_changed.emit()
	hud.flash_message(("Enemy %s destroyed" if u.team != 0 else "%s lost") % u.def.name)


func _fade_out(u: Unit, after: float) -> void:
	await get_tree().create_timer(after, false).timeout
	if is_instance_valid(u): u.visible = false; u.set_process(false)


func _update_debris(dt: float) -> void:
	for d in debris.duplicate():
		var n: Node3D = d.node
		d.vel.y -= 22.0 * dt
		n.global_position += d.vel * dt
		n.rotation += d.spin * dt
		var dgy := ground_h(n.global_position.x, n.global_position.z) + 0.4
		if n.global_position.y <= dgy and d.vel.y < 0:
			n.global_position.y = dgy
			if d.crash:
				FX.explosion(self, n.global_position, 0.9)
				var sp := n.find_child("Sprite", true, false) as Sprite3D
				if sp: sp.modulate = Color(0.12, 0.11, 0.1)
				FX.wreck_fire(n)
			debris.erase(d)


## Fog of war. Cells (4 m) currently seen by the player's units are clear, explored cells are dimmed, never-seen
## cells are dark. Drives the terrain/vegetation shaders (global uniforms) and the minimap overlay.
func _init_fog() -> void:
	explored.resize(FOG_N * FOG_N)
	explored.fill(0)
	fog_img = Image.create(FOG_N, FOG_N, false, Image.FORMAT_L8)
	fog_tex = ImageTexture.create_from_image(fog_img)
	fog_mini_img = Image.create(FOG_N, FOG_N, false, Image.FORMAT_RGBA8)
	fog_mini_tex = ImageTexture.create_from_image(fog_mini_img)
	RenderingServer.global_shader_parameter_set("fog_tex", fog_tex)
	RenderingServer.global_shader_parameter_set("fog_rect", Vector4(FOG_RECT.position.x, FOG_RECT.position.y, FOG_RECT.size.x, FOG_RECT.size.y))
	RenderingServer.global_shader_parameter_set("fog_on", 1.0)


func _stamp(r_cells: int) -> PackedInt32Array:
	# cell offsets (dx, dz pairs) inside a circle of the given radius, cached per radius
	if not fog_stamps.has(r_cells):
		var s := PackedInt32Array()
		for j in range(-r_cells, r_cells + 1):
			for i in range(-r_cells, r_cells + 1):
				if i * i + j * j <= r_cells * r_cells: s.append(i); s.append(j)
		fog_stamps[r_cells] = s
	return fog_stamps[r_cells]


func _update_fog() -> void:
	var vis := PackedByteArray()
	vis.resize(FOG_N * FOG_N)
	vis.fill(0)
	var cell := FOG_RECT.size.x / FOG_N
	var eyes: Array = []
	for u in units:
		if u.team == 0 and not u.dead: eyes.append([u.position, float(u.def.sight)])
	for z in reveal_zones:
		if z.team != 0: continue
		var steps := int(z.a.distance_to(z.b) / (z.w * 0.4)) + 1
		for i in steps + 1:
			eyes.append([z.a.lerp(z.b, float(i) / steps), z.w * 0.5])
	for e in eyes:
		var p: Vector3 = e[0]
		var cx := int((p.x - FOG_RECT.position.x) / cell)
		var cz := int((p.z - FOG_RECT.position.y) / cell)
		var st := _stamp(int(float(e[1]) / cell))
		for k in range(0, st.size(), 2):
			var i: int = cx + st[k]
			var j: int = cz + st[k + 1]
			if i >= 0 and j >= 0 and i < FOG_N and j < FOG_N:
				vis[j * FOG_N + i] = 1
	var data := PackedByteArray()
	data.resize(FOG_N * FOG_N)
	var mini := PackedByteArray()
	mini.resize(FOG_N * FOG_N * 4)
	mini.fill(0)
	for k in FOG_N * FOG_N:
		if vis[k]:
			explored[k] = 1
			data[k] = 255
		elif explored[k]:
			data[k] = 110
			mini[k * 4 + 3] = 110
		else:
			mini[k * 4 + 3] = 225
	fog_vis = vis
	fog_img.set_data(FOG_N, FOG_N, false, Image.FORMAT_L8, data)
	fog_tex.update(fog_img)
	fog_mini_img.set_data(FOG_N, FOG_N, false, Image.FORMAT_RGBA8, mini)
	fog_mini_tex.update(fog_mini_img)


func _update_visibility() -> void:
	fog_t -= 1.0 / TICK_HZ
	if fog_t <= 0.0:
		fog_t = 0.3
		_update_fog()
	for z in reveal_zones.duplicate():
		if sim_time > z.until: reveal_zones.erase(z)
	for u in units:
		if u.team == 0 or u.dead:
			if u.dead and not seen.get(u.uid, false): u.visible = false
			continue
		var vis := _cell_visible(u.position)
		if not vis:
			for z in reveal_zones:
				if z.team == 0 and _dist_to_segment(u.position, z.a, z.b) < z.w * 0.5:
					vis = true; break
		if u is Building:
			if vis: u.ever_seen = true
			seen[u.uid] = vis or u.ever_seen   # structures stay on the map once scouted (last known state)
			u.visible = seen[u.uid]
			continue
		seen[u.uid] = vis
		u.visible = vis


func _cell_visible(p: Vector3) -> bool:
	if fog_vis.is_empty(): return false
	var cell := FOG_RECT.size.x / FOG_N
	var i := int((p.x - FOG_RECT.position.x) / cell)
	var j := int((p.z - FOG_RECT.position.y) / cell)
	if i < 0 or j < 0 or i >= FOG_N or j >= FOG_N: return false
	return fog_vis[j * FOG_N + i] == 1


func _dist_to_segment(p: Vector3, a: Vector3, b: Vector3) -> float:
	var ab := Vector2(b.x - a.x, b.z - a.z)
	var ap := Vector2(p.x - a.x, p.z - a.z)
	var t := clampf(ap.dot(ab) / maxf(ab.length_squared(), 1e-6), 0.0, 1.0)
	return (ap - ab * t).length()


func is_visible_to(team: int, u: Unit) -> bool:
	return u.team == team or seen.get(u.uid, false)


func alive_count(team: int) -> int:
	var n := 0
	for u in units:
		if u.team == team and not u.dead: n += 1
	return n


func _check_end() -> void:
	if game_over: return
	if alive_count(1) == 0:
		game_over = true
		hud.banner = "VICTORY"; hud.banner_color = Color(0.5, 1.0, 0.6)
		print("RESULT victory t=%.1f blue_left=%d" % [sim_time, alive_count(0)])
		_end_screen(true)
	elif alive_count(0) == 0:
		game_over = true
		hud.banner = "DEFEAT"; hud.banner_color = Color(1.0, 0.4, 0.35)
		print("RESULT defeat t=%.1f red_left=%d" % [sim_time, alive_count(1)])
		_end_screen(false)


func _end_screen(victory: bool) -> void:
	var stats := {"time": "%02d:%02d" % [int(sim_time) / 60, int(sim_time) % 60], "kills": kills, "losses": losses}
	Game.last_result = stats.merged({"result": "Victory" if victory else "Defeat"})
	if _automated(): return
	await get_tree().create_timer(2.5).timeout   # let the final explosion play before the score screen
	hud.banner = ""
	pause_menu.open_end(victory, stats)


# ------------------------------------------------------------------ economy and construction (B1.2)
func _spawn_bases() -> void:
	for t in 2:
		cash[t] = BuildingDefs.START_CASH
		var cc := add_structure("command_center", t, start_pos[t], true)
		add_flag(t, cc.position + Vector3(cc.half.x + 4.0, 0, (cc.half.y - 2.0) * (1.0 if t == 0 else -1.0)))
		var fwd := -1.0 if t == 0 else 1.0     # toward the map centre
		var d := _spawn("dozer", t, cc.position + Vector3(-8, 0, fwd * (cc.half.y + 8.0)), 0.0 if t == 0 else PI)
		d.order_stop()
	if terrain:
		for sp in terrain.data.get("supply_piles", []):
			add_pile(map_point(sp), int(sp.get("cash", sp.get("amount", BuildingDefs.PILE_CASH))) if sp is Dictionary else BuildingDefs.PILE_CASH)
		for od in terrain.data.get("oil_derricks", []):
			add_derrick(od)
		return
	# neutral supply piles: two per side near each base, one larger contested pile in the centre (PROVISIONAL)
	for p in [Vector3(-75, 0, 195), Vector3(80, 0, 250), Vector3(75, 0, -195), Vector3(-80, 0, -250)]:
		add_pile(p, BuildingDefs.PILE_CASH)
	add_pile(Vector3(0, 0, 0), BuildingDefs.PILE_CASH * 2)


func add_structure(k: String, team: int, pos: Vector3, built := false) -> Building:
	pos = prepare_site(k, pos)
	var b := Building.new()
	add_child(b)
	b.setup_structure(self, k, team, units.size() + 1, pos, built)
	b.reset_physics_interpolation()
	units.append(b)
	by_id[b.uid] = b
	if built: on_structure_built(b, false)
	return b


func add_pile(p: Vector3, amount: int) -> void:
	var n := Node3D.new()
	p = grounded(p)
	n.position = p
	add_child(n)
	var wood := StandardMaterial3D.new(); wood.albedo_color = Color(0.45, 0.36, 0.22); wood.roughness = 0.9
	var crate := StandardMaterial3D.new(); crate.albedo_color = Color(0.33, 0.36, 0.22); crate.roughness = 0.8
	var r := RandomNumberGenerator.new(); r.seed = int(p.x * 13 + p.z * 7)
	for i in 26:
		var m := MeshInstance3D.new()
		var b := BoxMesh.new()
		b.size = Vector3(r.randf_range(1.6, 2.4), r.randf_range(1.0, 1.6), r.randf_range(1.6, 2.4))
		b.material = crate if i % 3 else wood
		m.mesh = b
		var a := r.randf() * TAU
		var d := r.randf_range(0.0, 7.0)
		m.position = Vector3(cos(a) * d, b.size.y * 0.5 + (b.size.y if i > 18 else 0.0), sin(a) * d)
		m.rotation.y = r.randf() * TAU
		n.add_child(m)
	piles.append({"pos": p, "cash": amount, "node": n, "start": amount})
	nav_block_circle(p, 8.0)
	obstacles_2d.append(Vector3(p.x, p.z, 8.0))


func structures(team: int, k := "", only_built := true) -> Array:
	var out: Array = []
	for u in units:
		if u is Building and not u.dead and u.team == team and (k == "" or u.bkind == k) and (u.built or not only_built):
			out.append(u)
	return out


func power_gen(team: int) -> int:
	var g := 0
	for b in structures(team):
		if b.bdef.power > 0: g += int(b.bdef.power)
	return g


func power_use(team: int) -> int:
	var c := 0
	for b in structures(team):
		if b.bdef.power < 0: c -= int(b.bdef.power)
	return c


func power_ok(team: int) -> bool:
	return power_gen(team) >= power_use(team)


func requirements_met(team: int, k: String) -> bool:
	for r in BuildingDefs.DEFS[k].requires:
		if structures(team, r).is_empty(): return false
	return true


## "" when a structure of kind k may be placed at pos for team, otherwise the reason (shown to the player).
func placement_problem(team: int, k: String, pos: Vector3) -> String:
	var d: Dictionary = BuildingDefs.DEFS[k]
	if cash[team] < int(d.cost): return "Not enough cash"
	if not requirements_met(team, k): return "Requires " + ", ".join(d.requires.map(func(x): return BuildingDefs.DEFS[x].name))
	var h: Vector2 = d.size * 0.5 + Vector2(1.0, 1.0)
	if not map_bounds.grow(-10).has_point(Vector2(pos.x, pos.z)): return "Outside the map"
	if terrain:
		var st := terrain.footprint_stats(pos, d.size * 0.5)
		if st.y > build_max_slope: return "Ground too steep (%.0f° > %.0f°)" % [st.y, build_max_slope]
	if not gnav.box_free(pos, h): return "Blocked"
	if terrain:
		for od in derricks:
			if absf(od.pos.x - pos.x) < h.x + 6.0 and absf(od.pos.z - pos.z) < h.y + 6.0: return "Blocked"
	# airfield aprons: the new apron must be clear and on the map; nothing may be built on an existing apron
	var ap := Building.apron_rect(pos, d)
	if not ap.is_empty():
		var ac: Vector3 = ap[0]; var ah: Vector2 = ap[1]
		if not map_bounds.grow(-12).encloses(Rect2(ac.x - ah.x, ac.z - ah.y, ah.x * 2, ah.y * 2)): return "Apron off the map"
		if not gnav.box_free(ac, ah): return "Apron blocked"
		for b in structures(0, "", false) + structures(1, "", false):
			if absf(b.position.x - ac.x) < b.half.x + ah.x and absf(b.position.z - ac.z) < b.half.y + ah.y: return "Apron blocked"
	for af in structures(0, "airfield", false) + structures(1, "airfield", false):
		var r := Building.apron_rect(af.position, af.bdef)
		if r.is_empty(): continue
		var rc: Vector3 = r[0]; var rh: Vector2 = r[1]
		if absf(pos.x - rc.x) < rh.x + h.x and absf(pos.z - rc.z) < rh.y + h.y: return "On an airfield apron"
	for u in units:
		if u.dead or u.is_air() or u is Building: continue
		if absf(u.position.x - pos.x) < h.x + u.def.radius * 0.5 and absf(u.position.z - pos.z) < h.y + u.def.radius * 0.5 \
				and not u.def.get("builder", false):
			return "Units in the way"
	# build radius: near any own structure (Generals-style base creep)
	var near := false
	for b in structures(team, "", false):
		if b.position.distance_to(pos) < 140.0: near = true; break
	if not near: return "Too far from your base"
	return ""


func _execute_econ(cmd: Dictionary) -> void:
	var team: int = cmd.team
	match cmd.type:
		"place":
			var k: String = cmd.id
			var dz: Unit = by_id.get(cmd.get("builder", -1))
			if dz == null or dz.dead or dz.team != team or not dz.def.get("builder", false): return
			if placement_problem(team, k, cmd.pos) != "":
				return
			spend(team, int(BuildingDefs.DEFS[k].cost))
			_clear_rubble(cmd.pos, BuildingDefs.DEFS[k].size * 0.5)
			var b := add_structure(k, team, cmd.pos, false)
			dz.order_build(b)
		"cancel_build":
			var b: Building = by_id.get(cmd.id)
			if b and not b.dead and not b.built and b.team == team:
				cash[team] += int(b.bdef.cost)
				b.die()
		"produce":
			var b: Building = by_id.get(cmd.id)
			var k: String = cmd.kind
			if b == null or b.dead or not b.built or b.team != team or not (k in b.produces_list()): return
			if produce_problem(b, k) != "": return
			spend(team, int(BuildingDefs.UNIT_COST[k][0]))
			b.queue_unit(k)
		"cancel_unit":
			var b: Building = by_id.get(cmd.id)
			if b and not b.dead and b.team == team:
				var k := b.cancel_last()
				if k != "": cash[team] += int(BuildingDefs.UNIT_COST[k][0])
		"rally":
			var b: Building = by_id.get(cmd.id)
			if b and not b.dead and b.team == team:
				b.rally = cmd.pos; b.has_rally = true
		"sell":
			var b: Building = by_id.get(cmd.id)
			if b and not b.dead and b.built and b.team == team and b.bkind != "command_center":
				cash[team] += int(float(b.bdef.cost) * BuildingDefs.SELL_REFUND * b.hp / b.bdef.hp)
				b.prod_queue.clear()
				b.sold = true
				b.die()
		"repair":
			var b: Building = by_id.get(cmd.id)
			if b and not b.dead and b.built and b.team == team:
				b.repairing = bool(cmd.on) and b.hp < b.bdef.hp
				b.repair_blocked = ""


func produce_problem(b: Building, k: String) -> String:
	if cash[b.team] < int(BuildingDefs.UNIT_COST[k][0]): return "Not enough cash"
	if b.prod_queue.size() >= 9: return "Queue full"
	if not b.pads.is_empty():
		var free := 0
		for p in b.pads:
			var u: Unit = by_id.get(int(p.uid))
			if u == null or u.dead: free += 1
		if free <= b.prod_queue.size(): return "No free pad"
	return ""


func on_structure_built(b: Building, announce := true) -> void:
	if b.bdef.has("free_unit"):
		spawn_produced(b, b.bdef.free_unit)
	if announce and b.team == 0 and hud: hud.flash_message("%s complete" % b.bdef.name)


## A finished unit leaves its building toward the rally point; aircraft appear landed on a free pad.
func spawn_produced(b: Building, k: String) -> void:
	var team := b.team
	var exit_dir := (b.rally - b.position)
	exit_dir.y = 0.0
	exit_dir = exit_dir.normalized() if exit_dir.length() > 0.1 else Vector3(0, 0, 1.0 if team == 0 else -1.0)
	var reach := absf(exit_dir.x) * b.half.x + absf(exit_dir.z) * b.half.y + 5.0
	var pos := b.position + exit_dir * reach
	var ep: Vector3 = b.exit_point()
	if ep != Vector3.INF:
		pos = ep            # the model's door / vehicle bay
		var to_r := b.rally - pos
		to_r.y = 0.0
		if to_r.length() > 0.5: exit_dir = to_r.normalized()
	var yaw := atan2(-exit_dir.x, -exit_dir.z)
	var u := _spawn(k, team, pos, yaw)
	var d: Dictionary = UnitDefs.def_of(k)
	if not b.pads.is_empty():
		var i := b.free_pad()
		if i < 0: i = 0
		b.pads[i].uid = u.uid
		u.position = b.pads[i].pos
		u.home = b.pads[i].pos
		u.heading = 0.0 if team == 0 else PI
		if b.runway.size() == 2 and u.domain == "jet":
			u.has_runway = true; u.rw_start = b.runway[0]; u.rw_end = b.runway[1]
			u.park_heading = u._runway_heading(); u.heading = u.park_heading
		u.state = Unit.S.LANDED; u.altitude = u.ground_alt(); u.speed_cur = 0.0; u.body.position.y = u.altitude; u.airborne = false
		u.reset_physics_interpolation()
		return
	u.reset_physics_interpolation()
	if d.get("hauler", false) and b.bkind == "supply_depot":
		u.home = b.position
		u.start_haul(b)
		return
	if u.is_air():
		u.home = pos
	u.order_move(b.rally if b.has_rally else pos + exit_dir * 12.0)


func nearest_pile(p: Vector3) -> Dictionary:
	var best: Dictionary = {}
	var bd := INF
	for pl in piles:
		if pl.cash <= 0: continue
		var d := p.distance_to(pl.pos)
		if d < bd: bd = d; best = pl
	return best


func deliver(team: int, amount: int) -> void:
	cash[team] += amount
	income[team] += amount


## All spending goes through here so the HUD can show a spending trend (refunds are not counted as income).
var spent := [0, 0]
var trend_samples: Array = []      # [sim_time, income0, spent0]


func spend(team: int, amount: int) -> void:
	cash[team] -= amount
	spent[team] += amount


## Cash per minute delivered and spent over the last 60 s (player team), for the top bar.
func cash_trend(team: int) -> Vector2:
	if trend_samples.is_empty(): return Vector2.ZERO
	var old: Array = trend_samples[0]
	var dt := maxf(sim_time - float(old[0]), 1.0)
	return Vector2((income[team] - int(old[1 + team * 2])) * 60.0 / dt, (spent[team] - int(old[2 + team * 2])) * 60.0 / dt)


## Radar: enemy units (not structures) appear on the minimap only with a powered radar.
func radar_online(team: int) -> bool:
	return not structures(team, "radar").is_empty() and power_ok(team)


# ------------------------------------------------------------------ rubble (destroyed structures)
var rubble: Array = []   # {"pos", "kind", "team", "half", "node"}


## A destroyed structure leaves rubble on its footprint (not an obstacle). A Dozer can rebuild the same structure
## there through the normal construction flow (normal cost, prerequisites and build time).
func add_rubble(b: Building) -> void:
	var n := Node3D.new()
	n.position = b.position
	add_child(n)
	var dark := StandardMaterial3D.new(); dark.albedo_color = Color(0.13, 0.12, 0.11); dark.roughness = 1.0
	var conc := StandardMaterial3D.new(); conc.albedo_color = Color(0.36, 0.34, 0.31); conc.roughness = 0.95
	var slab := MeshInstance3D.new()
	var bm := BoxMesh.new(); bm.size = Vector3(b.half.x * 2.0, 0.3, b.half.y * 2.0); bm.material = dark
	slab.mesh = bm; slab.position.y = 0.15
	n.add_child(slab)
	var r := RandomNumberGenerator.new(); r.seed = b.uid * 7919
	for i in int(clampf(b.half.x * b.half.y / 6.0, 6, 40)):
		var m := MeshInstance3D.new()
		var cm := BoxMesh.new()
		cm.size = Vector3(r.randf_range(0.8, 3.5), r.randf_range(0.4, 2.0), r.randf_range(0.8, 3.5))
		cm.material = conc if i % 3 else dark
		m.mesh = cm
		m.position = Vector3(r.randf_range(-b.half.x, b.half.x) * 0.85, cm.size.y * 0.4, r.randf_range(-b.half.y, b.half.y) * 0.85)
		m.rotation = Vector3(r.randf_range(-0.4, 0.4), r.randf() * TAU, r.randf_range(-0.4, 0.4))
		n.add_child(m)
	FX.wreck_fire(n)
	rubble.append({"pos": b.position, "kind": b.bkind, "team": b.team, "half": b.half, "node": n})


func _clear_rubble(pos: Vector3, h: Vector2) -> void:
	for r in rubble.duplicate():
		if absf(r.pos.x - pos.x) < r.half.x + h.x and absf(r.pos.z - pos.z) < r.half.y + h.y:
			r.node.queue_free()
			rubble.erase(r)


func rubble_at(p: Vector3, team: int) -> Dictionary:
	for r in rubble:
		if r.team == team and absf(p.x - r.pos.x) < r.half.x and absf(p.z - r.pos.z) < r.half.y: return r
	return {}


# ------------------------------------------------------------------ supply drops (Supply Drop Zone)
var drop_flights: Array = []    # {"node", "pos", "dir", "target", "team", "left", "value", "released"}
var drop_crates: Array = []
var drop_income := [0, 0]     # {"node", "pos", "vy", "team", "value", "canopy"}
const C130_SPRITE := "res://assets/aircraft/c130/c130_top.png"
const C130_MODEL := "res://assets/units3d/c130/c130.glb"
const CRATE_MODEL := "res://assets/units3d/props/supply_crate_chute.glb"


func launch_supply_drop(b: Building) -> void:
	var d: Dictionary = b.bdef.drop
	var target: Vector3 = b.drop_point_world()
	var edge_z: float = map_bounds.end.y + 140.0 if b.team == 0 else map_bounds.position.y - 140.0
	var start := Vector3(target.x + 60.0, ground_h(target.x, target.z), edge_z)
	var dir := (target - start); dir.y = 0.0; dir = dir.normalized()
	var node := Node3D.new()
	add_child(node)
	if ResourceLoader.exists(C130_MODEL):
		var m: Node3D = (load(C130_MODEL) as PackedScene).instantiate()
		m.scale = Vector3.ONE * UnitDefs.SCALE.aircraft
		m.position.y = 34.0
		node.add_child(m)
	else:
		var s := Sprite3D.new()
		var tex: Texture2D = load(C130_SPRITE)
		s.texture = tex; s.axis = Vector3.AXIS_Y; s.shaded = true; s.double_sided = true
		s.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
		s.pixel_size = 40.4 * UnitDefs.SCALE.aircraft / float(tex.get_width()) * 1.05   # C-130 span 40.4 m
		s.position.y = 34.0
		s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		node.add_child(s)
	node.position = start
	node.rotation.y = atan2(-dir.x, -dir.z)
	node.reset_physics_interpolation()
	SFX.play(node, "jet_flyby", start, 2.0, 0.7, true)
	drop_flights.append({"node": node, "pos": start, "dir": dir, "target": target, "team": b.team,
		"crates": int(d.crates), "value": int(d.value), "released": 0})
	if b.team == 0 and hud: hud.flash_message("Supply drop inbound")


func _update_supply_drops(dt: float) -> void:
	for f in drop_flights.duplicate():
		for pr in f.node.find_children("Prop*", "Node3D", true, false): (pr as Node3D).rotate_object_local(Vector3.BACK, dt * 30.0)
		f.pos += f.dir * 55.0 * dt
		f.node.position = f.pos
		var along: float = (f.pos - f.target).dot(f.dir)
		# release the crates in a short stick centred on the drop point
		while f.released < f.crates and along >= -12.0 + f.released * 8.0 - 20.0:
			var c := _make_crate()
			var p: Vector3 = f.pos + Vector3(0, 32.0, 0)
			c.node.position = p
			c.node.reset_physics_interpolation()
			drop_crates.append({"node": c.node, "canopy": c.canopy, "pos": p, "vy": -2.0, "team": f.team, "value": f.value,
				"drift": f.dir * 12.0})
			f.released += 1
		if along > 500.0:
			f.node.queue_free()
			drop_flights.erase(f)
	for c in drop_crates.duplicate():
		c.vy = maxf(c.vy - 9.0 * dt, -5.0)     # canopy opens: terminal descent ~5 m/s
		c.drift = c.drift.move_toward(Vector3.ZERO, 6.0 * dt)
		c.pos += Vector3(c.drift.x, c.vy, c.drift.z) * dt
		c.node.position = c.pos
		var cgy := ground_h(c.pos.x, c.pos.z)
		if c.pos.y <= cgy:
			c.pos.y = cgy
			c.node.position = c.pos
			if c.canopy: c.canopy.visible = false
			deliver(c.team, c.value)
			drop_income[c.team] += c.value
			FX.impact(self, c.pos, false)
			if c.team == 0 and hud: hud.flash_message("Supply crate +$%d" % c.value)
			drop_crates.erase(c)
			_fade_node(c.node, 6.0)


func _make_crate() -> Dictionary:
	if ResourceLoader.exists(CRATE_MODEL):
		var m: Node3D = (load(CRATE_MODEL) as PackedScene).instantiate()
		add_child(m)
		return {"node": m, "canopy": m.find_child("Canopy", true, false)}
	var n := Node3D.new()
	var box := MeshInstance3D.new()
	var bm := BoxMesh.new(); bm.size = Vector3(2, 1.5, 2)
	var mat := StandardMaterial3D.new(); mat.albedo_color = Color(0.33, 0.36, 0.22)
	bm.material = mat; box.mesh = bm; box.position.y = 0.75
	n.add_child(box)
	var can := MeshInstance3D.new()
	var sm := SphereMesh.new(); sm.radius = 3.5; sm.height = 2.4; sm.is_hemisphere = true
	var cm := StandardMaterial3D.new(); cm.albedo_color = Color(0.45, 0.47, 0.36)
	sm.material = cm; can.mesh = sm; can.position.y = 7.0
	n.add_child(can)
	add_child(n)
	return {"node": n, "canopy": can}


func _fade_node(n: Node, after: float) -> void:
	await get_tree().create_timer(after, false).timeout
	if is_instance_valid(n): n.queue_free()


# ------------------------------------------------------------------ transports
## Boarding: an infantry unit ordered to board walks to its transport and enters when close and the transport is
## stopped (helicopters: hovering low). Aboard, it leaves the unit list (not targetable, does not see), keeping its
## health. Rule when a transport is destroyed: all passengers are lost (documented in docs/M4_TRANSPORT.md).
func _update_boarding() -> void:
	for u in units.duplicate():
		if u.dead:
			continue
		if u.board_target:
			var tr: Unit = u.board_target
			if tr.dead or not is_instance_valid(tr) or tr.capacity_left() <= 0:
				u.board_target = null; continue
			if u.state == Unit.S.IDLE and u.flat_dist(tr.position) > 6.0:
				u.order_move(tr.position)             # transport moved: follow it
			if u.flat_dist(tr.position) < tr.def.radius + 4.0 and tr.can_exchange():
				_board(u, tr)
		if u.is_transport() and u.unload_pending and u.domain != "heli" and u.can_exchange():
			u.unload_pending = false
			unload_all(u)


func _board(u: Unit, tr: Unit) -> void:
	u.board_target = null
	u.set_selected(false)
	if u in commander.selected: commander.selected.erase(u); commander.selection_changed.emit()
	units.erase(u)
	u.visible = false
	u.process_mode = Node.PROCESS_MODE_DISABLED
	tr.passengers.append(u)
	if tr.team == 0 and hud: hud.flash_message("%s boarded %s (%d/%d)" % [u.def.name, tr.def.name, tr.passengers.size(), tr.def.transport.capacity])


func unload_all(tr: Unit) -> void:
	var n := 0
	for p in tr.passengers.duplicate():
		if unload_one(tr, p): n += 1
	if tr.team == 0 and hud and n > 0: hud.flash_message("%d unloaded from %s" % [n, tr.def.name])


## Places a passenger on a free grid cell in a ring around the transport (never inside structures or rocks).
func unload_one(tr: Unit, p: Unit) -> bool:
	if not p in tr.passengers: return false
	var spot := Vector3.INF
	for ring in range(1, 6):
		for k in 8:
			var a := TAU * float(k) / 8.0 + float(tr.passengers.size()) * 0.7
			var q: Vector3 = tr.position + Vector3(cos(a), 0, sin(a)) * (tr.def.radius + 2.0 + ring * 2.0)
			if gnav.blocked_at(q) or not map_bounds.has_point(Vector2(q.x, q.z)): continue
			var crowded := false
			for o in units:
				if not o.dead and not o.is_air() and o.flat_dist(q) < 1.6: crowded = true; break
			if not crowded: spot = q; break
		if spot != Vector3.INF: break
	if spot == Vector3.INF: return false
	tr.passengers.erase(p)
	p.position = spot
	p.process_mode = Node.PROCESS_MODE_INHERIT
	p.visible = true
	p.order_stop()
	p.reset_physics_interpolation()
	units.append(p)
	return true


func _lose_passengers(tr: Unit) -> void:
	for p in tr.passengers:
		p.dead = true
		if p.team == 0: losses += 1
		else: kills += 1
		p.queue_free()
	tr.passengers.clear()


# ------------------------------------------------------------------ heightfield maps (Zagros Basin and later maps)
## Flattens the footprint of a structure about to be placed (skirted) and returns the grounded position.
func prepare_site(k: String, pos: Vector3) -> Vector3:
	if terrain == null: return Vector3(pos.x, 0.0, pos.z)
	var half: Vector2 = BuildingDefs.DEFS[k].size * 0.5
	var st := terrain.footprint_stats(pos, half)
	terrain.flatten(pos, half + Vector2(2.0, 2.0), st.z, 8.0)
	return Vector3(pos.x, st.z, pos.z)


const PROP_DIRS := ["res://assets/units3d/props/%s.glb", "res://assets/map_props/%s/%s.glb", "res://maps/props/%s.glb"]


func _prop_path(kind: String) -> String:
	if terrain:
		var g: Variant = terrain.data.get("prop_types", {}).get(kind, {}).get("glb")
		if g is String and ResourceLoader.exists(g): return g
	for f in PROP_DIRS:
		var p: String = f % ([kind, kind] if f.count("%s") == 2 else [kind])
		if ResourceLoader.exists(p): return p
	return ""


## Places map.json props on the terrain. Each prop kind becomes one MultiMesh per mesh part (hundreds of scrub
## bushes cost a few draw calls); "block_r" adds a navigation obstacle.
func _build_terrain_map() -> void:
	var d: Dictionary = terrain.data
	var per_kind := {}
	var missing := {}
	for pr in d.get("props", []):
		var kind := str(pr.get("kind", pr.get("type", "")))
		if _prop_path(kind) == "":
			missing[kind] = true
			continue
		var p := map_point(pr)
		var yaw := deg_to_rad(float(pr.get("yaw_deg", pr.get("yaw", 0.0))))
		var sc := float(pr.get("scale", 1.0))
		var xf := Transform3D(Basis(Vector3.UP, yaw).scaled(Vector3.ONE * sc), p + Vector3(0, float(pr.get("sink_m", 0.0)) * -1.0, 0))
		if not per_kind.has(kind): per_kind[kind] = []
		per_kind[kind].append(xf)
		prop_roots.append(xf.origin)
		var br := float(pr.get("block_r", pr.get("block_radius_m", 0.0)))
		var pt: Dictionary = d.get("prop_types", {}).get(kind, {})
		if br == 0.0 and pt.get("blocks", false):
			var fp: Array = pt.get("footprint_m", [2.0, 2.0])
			br = maxf(float(fp[0]), float(fp[1])) * 0.5 * sc
		if br > 0.0: obstacles_2d.append(Vector3(p.x, p.z, br))
	for kind in per_kind:
		var scene: Node3D = (load(_prop_path(kind)) as PackedScene).instantiate()
		add_child(scene)     # temporarily, to read global transforms of the parts
		for mi in scene.find_children("*", "MeshInstance3D", true, false):
			var part: MeshInstance3D = mi
			var local := scene.global_transform.affine_inverse() * part.global_transform
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = part.mesh
			var xs: Array = per_kind[kind]
			mm.instance_count = xs.size()
			for i in xs.size(): mm.set_instance_transform(i, xs[i] * local)
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.name = "Props_%s_%s" % [kind, part.name]
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			if part.material_override: mmi.material_override = part.material_override
			add_child(mmi)
		scene.queue_free()
	if not missing.is_empty(): push_warning("map props without a model: %s" % ", ".join(missing.keys()))
	print("MAP props: %s" % ", ".join(per_kind.keys().map(func(k): return "%s x%d" % [k, per_kind[k].size()])))


const DERRICK_MODEL := "res://assets/units3d/props/oil_derrick.glb"


## Neutral oil derrick: infantry standing next to it, uncontested, capture it in capture_s seconds; the owner then
## receives `income` every `every_s` seconds. Values come from map.json (PROVISIONAL).
func add_derrick(od: Dictionary) -> void:
	var p := map_point(od)
	if terrain: terrain.flatten(p, Vector2(7, 7), p.y, 5.0)
	var n: Node3D
	if ResourceLoader.exists(DERRICK_MODEL):
		n = (load(DERRICK_MODEL) as PackedScene).instantiate()
	else:
		n = Node3D.new()
		var mi := MeshInstance3D.new(); var bm := BoxMesh.new(); bm.size = Vector3(3, 6, 8); mi.mesh = bm; mi.position.y = 3.0
		n.add_child(mi)
	n.position = p
	n.rotation.y = deg_to_rad(float(od.get("yaw_deg", 0.0)))
	add_child(n)
	var flag_anchor: Node3D = n.find_child("Flag", true, false)
	if flag_anchor == null:
		flag_anchor = Node3D.new(); flag_anchor.position = Vector3(4, 6, 0); n.add_child(flag_anchor)
	var e := {"id": str(od.get("id", "derrick_%d" % derricks.size())), "pos": p, "owner": -1, "progress": [0.0, 0.0],
		"income": int(od.get("income", 100)), "every": float(od.get("every_s", 10.0)), "capture_s": float(od.get("capture_s", 8.0)),
		"radius": float(od.get("radius_m", 12.0)), "timer": 0.0, "phase": 0.0, "node": n,
		"beam": n.find_child("WalkingBeam", true, false), "crank": n.find_child("Crank", true, false),
		"flag_anchor": flag_anchor, "flag": null, "paid": [0, 0]}
	derricks.append(e)
	_set_derrick_flag(e)
	nav_block_circle(p, 5.0)
	obstacles_2d.append(Vector3(p.x, p.z, 4.5))


func _set_derrick_flag(e: Dictionary) -> void:
	if e.flag: e.flag.queue_free()
	var path := "res://assets/units3d/props/flag_%s.glb" % nation_of(e.owner) if e.owner >= 0 else ""
	var f: Node3D
	if path != "" and ResourceLoader.exists(path):
		f = (load(path) as PackedScene).instantiate()
		f.scale = Vector3.ONE * 0.6
		e.flag_anchor.add_child(f)
		play_loop(f, "wave")
		e.flag = f
		return
	else:
		f = MeshInstance3D.new()
		var q := QuadMesh.new(); q.size = Vector2(2.4, 1.5)
		var m := StandardMaterial3D.new(); m.cull_mode = BaseMaterial3D.CULL_DISABLED
		m.albedo_color = UnitDefs.TEAM_COLORS[e.owner].lightened(0.2) if e.owner >= 0 else Color(0.85, 0.85, 0.82)
		q.material = m
		(f as MeshInstance3D).mesh = q
		f.position = Vector3(1.2, 0, 0)
	e.flag_anchor.add_child(f)
	e.flag = f


func _update_derricks(dt: float) -> void:
	for e in derricks:
		var present := [0, 0]
		for u in units:
			if u.dead or u.domain != "ground" or u.def.get("visual") != "infantry" or u.para_alt > 0.0: continue
			if u.flat_dist(e.pos) <= e.radius: present[u.team] += 1
		var cap := -1
		if present[0] > 0 and present[1] == 0: cap = 0
		elif present[1] > 0 and present[0] == 0: cap = 1
		if cap >= 0 and cap != e.owner:
			e.progress[cap] = minf(1.0, e.progress[cap] + dt / e.capture_s)
			e.progress[1 - cap] = maxf(0.0, e.progress[1 - cap] - dt / e.capture_s)
			if e.progress[cap] >= 1.0:
				var prev: int = e.owner
				e.owner = cap; e.progress = [0.0, 0.0]; e.timer = 0.0
				_set_derrick_flag(e)
				print("DERRICK %s captured by team %d (was %d) t=%.1f" % [e.id, cap, prev, sim_time])
				if hud:
					if cap == 0: hud.flash_message("Oil derrick captured: +$%d every %.0f s" % [e.income, e.every])
					elif prev == 0: hud.flash_message("Oil derrick lost")
		elif cap < 0 and present[0] == 0 and present[1] == 0:
			for t in 2: e.progress[t] = maxf(0.0, e.progress[t] - dt / (e.capture_s * 2.0))
		if e.owner >= 0:
			e.timer += dt
			if e.timer >= e.every:
				e.timer -= e.every
				deliver(e.owner, e.income)
				derrick_income[e.owner] += e.income
				e.paid[e.owner] += e.income
			e.phase += dt * 2.4
			# crank turns; the walking beam follows the crank through the pitman (ratio from the model: 1.0 / 2.2)
			if e.crank: (e.crank as Node3D).rotation.x = e.phase
			if e.beam: (e.beam as Node3D).rotation.x = asin(sin(e.phase) / 2.2)


## Nation of a team: "nationN=<id>" on the command line, otherwise the menu choice (U.S. by default).
func nation_of(team: int) -> String:
	if team < 0: return ""
	var k := "nation%d" % team
	if args.has(k): return str(args[k])
	if _automated(): return "usa"
	return str(Game.settings.get(k, "usa"))


## Minimap background for heightfield maps: hill-shaded terrain colour over the playable area, built once.
func make_minimap_texture() -> ImageTexture:
	var res := 256
	var img := Image.create(res, res, false, Image.FORMAT_RGB8)
	var mb := map_bounds
	var light := Vector3(-0.5, 0.75, -0.45).normalized()
	for j in res:
		for i in res:
			var x := mb.position.x + (i + 0.5) / res * mb.size.x
			var z := mb.position.y + (j + 0.5) / res * mb.size.y
			var sp := terrain.splat_at(x, z)
			var c := Color(0.62, 0.53, 0.39)
			c = c.lerp(Color(0.55, 0.52, 0.46), sp.g)
			c = c.lerp(Color(0.40, 0.42, 0.25), sp.b)
			c = c.lerp(Color(0.72, 0.68, 0.60), sp.a)
			c = c.lerp(Color(0.45, 0.40, 0.35), clampf(sp.r + terrain.slope_deg_at(x, z) / 40.0, 0.0, 1.0))
			c = c.lerp(Color(0.33, 0.30, 0.26), clampf(terrain.road_at(x, z) * 1.4, 0.0, 1.0))
			var shade := clampf(terrain.normal_at(x, z).dot(light) * 1.25, 0.35, 1.15)
			img.set_pixel(i, j, Color(c.r * shade, c.g * shade, c.b * shade))
	return ImageTexture.create_from_image(img)


## Nation flag on a pole beside a team's Command Center.
func add_flag(team: int, p: Vector3) -> void:
	var path := str(Nations.DEFS.get(nation_of(team), Nations.DEFS.usa).flag)
	if not ResourceLoader.exists(path): return
	var f: Node3D = (load(path) as PackedScene).instantiate()
	f.position = grounded(p)
	f.name = "Flag_team%d" % team
	add_child(f)
	play_loop(f, "wave")


## Starts a looping animation in an imported model (flags wave).
func play_loop(n: Node, anim_name: String) -> void:
	var ap := n.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if ap == null: return
	var nm := anim_name
	if not ap.has_animation(nm):
		for a in ap.get_animation_list():
			if a.contains(anim_name): nm = a
	if not ap.has_animation(nm): return
	ap.get_animation(nm).loop_mode = Animation.LOOP_LINEAR
	ap.play(nm)

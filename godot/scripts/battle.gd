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
var base_ai0: RefCounted = null   # optional second computer player on team 0 (AI-vs-AI test matches: "ai0")

var camera: RTSCamera
var commander: Commander
var hud: HUD


func _ready() -> void:
	args = _args()
	if not Game.pending_load.is_empty(): loaded_meta = Game.pending_load.meta   # nations / map come from the save
	scenario = "army" if ("army" in args or ("test" in args and not "base" in args) or "airdiag" in args or "evidence" in args) else "base"
	var _t0 := Time.get_ticks_msec()
	_select_map()
	print("LOAD select_map %d ms" % (Time.get_ticks_msec() - _t0))
	_init_fog()
	rng.seed = 20261021
	Engine.physics_ticks_per_second = TICK_HZ
	Engine.time_scale = 1.0 if _automated() else float(Game.settings.get("game_speed", 1.0))   # Skirmish: game speed
	await World.environment(self)
	props = World.props()
	if terrain:
		# bigger map and higher camera: thinner haze so distant ridges keep their contrast
		for we in find_children("*", "WorldEnvironment", false, false):
			var env: Environment = (we as WorldEnvironment).environment
			env.fog_density = float(terrain.data.get("fog_density", 0.00045))
			env.fog_aerial_perspective = 0.4
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
	if terrain:
		for cs in civic_spawns: add_civic(cs[0], cs[1], false)
		civic_spawns.clear()
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
	hud.layer = layer
	layer.add_child(hud)
	var diff: Dictionary = Game.DIFFICULTY.get(Game.settings.difficulty, Game.DIFFICULTY["Normal"])
	if scenario == "army":
		ai = EnemyAI.new(self, 1, 30.0 if _automated() else float(diff.attack_after))
	elif not "noai" in args and not ("basetest" in args and "qa" in args):   # the QA run checks player systems without a live AI
		base_ai = BaseAI.new(self, 1, str(args.get("diff", Game.settings.difficulty)))
		if "ai0" in args: base_ai0 = BaseAI.new(self, 0, str(args.get("diff0", args.get("diff", Game.settings.difficulty))))
	pause_menu = PauseMenu.new()
	pause_menu.battle = self
	add_child(pause_menu)
	apply_settings()
	if not Game.pending_load.is_empty():
		var data: Dictionary = Game.pending_load
		Game.pending_load = {}
		loaded_meta = data.meta
		SaveGame.restore(self, data)
		if "loadcheck" in args:   # end-to-end test: the rebuilt match must match the fingerprint stored with the file
			var want: Variant = JSON.parse_string(FileAccess.get_file_as_string(str(args.get("loadsave", "")).replace(".sav", ".sig")))
			var got: Variant = JSON.parse_string(JSON.stringify(SaveGame.signature(self)))
			var bad: Array = []
			if want is Dictionary:
				for k in want:
					if str(want[k]) != str(got.get(k)): bad.append("%s: %s -> %s" % [k, str(want[k]).substr(0, 60), str(got.get(k)).substr(0, 60)])
			printerr("LOADTEST %s units=%s structures=%s cash=%s differences: %s" % [str(want is Dictionary and bad.is_empty()), str(got.units), str(got.structures), str(got.cash), "; ".join(bad) if not bad.is_empty() else "none"])
			print("RESULT %d/1" % (1 if want is Dictionary and bad.is_empty() else 0))
			await get_tree().create_timer(2.0).timeout
			get_tree().quit()
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
	elif "closeshots" in args:
		var cs: Node = load("res://scripts/closeshots.gd").new()
		cs.battle = self
		add_child(cs)
	elif "mapshots" in args:
		var ms: Node = load("res://scripts/mapshots.gd").new()
		ms.battle = self
		add_child(ms)
	elif "movetest" in args:
		var mv: Node = load("res://scripts/autotest_move.gd").new()
		mv.battle = self
		add_child(mv)
	elif "vfxshots" in args or "vfxbench" in args or "vfxtest" in args:
		var vf: Node = load("res://scripts/vfxtest.gd" if "vfxtest" in args else "res://scripts/vfxshots.gd").new()
		vf.battle = self
		add_child(vf)
	elif "maptest" in args:
		var mt: Node = load("res://scripts/autotest_map.gd").new()
		mt.battle = self
		add_child(mt)
	elif "aitest" in args:
		var at: Node = load("res://scripts/autotest_ai.gd").new()
		at.battle = self
		add_child(at)
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
	if not Game.pending_load.is_empty(): want = str(Game.pending_load.meta.get("map", want))   # a saved game picks its map
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
	return "test" in args or "maptest" in args or "mapshots" in args or "airdiag" in args or "evidence" in args or "vischeck" in args or "basetest" in args or "movetest" in args or "vfxshots" in args or "vfxbench" in args or "vfxtest" in args or "aitest" in args or "baseshots" in args or "pilotshots" in args or "m1shots" in args


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


func nav_set_structure(p: Vector3, half: Vector2, on: bool, yaw := 0.0) -> void:
	for g in _nav_set(): g.set_structure(p, half, on, yaw)


func _nav_set() -> Array:
	var out: Array = []
	for g in navs.values():
		if not (g in out): out.append(g)
	if out.is_empty() and gnav: out.append(gnav)
	return out


func find_path(from: Vector3, to: Vector3, move_class := "tracked", clearance := 0.0) -> PackedVector3Array:
	var g: GridNav = navs.get(move_class, gnav)
	if g: return g.find_path(from, to, clearance)
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


## Unit ids are never reused (units.size() + 1 was: boarding removes infantry from the list, so ids could repeat).
var uid_next := 1


func new_uid() -> int:
	uid_next += 1
	return uid_next - 1


func _spawn(kind: String, team: int, pos: Vector3, yaw: float) -> Unit:
	var u := Unit.new()
	add_child(u)
	u.setup(self, kind, team, new_uid(), grounded(pos), yaw)
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
	if cmd.type in ["research", "cancel_research"]:
		var rb: Building = by_id.get(cmd.id)
		if rb == null or rb.dead or rb.team != cmd.team: return
		if cmd.type == "research":
			if research_problem(rb, cmd.upgrade) != "": return
			spend(cmd.team, int(Upgrades.DEFS[cmd.upgrade].cost))
			rb.research_id = cmd.upgrade; rb.research_left = float(Upgrades.DEFS[cmd.upgrade].time)
		elif rb.research_id != "":
			cash[cmd.team] += int(Upgrades.DEFS[rb.research_id].cost)
			rb.research_id = ""; rb.research_left = 0.0
		return
	if cmd.type == "plan":
		if plan_problem(cmd.team, cmd.plan) != "": return
		plan_pending[cmd.team] = cmd.plan
		plan_switch_t[cmd.team] = sim_time + (Upgrades.PLAN_SWITCH_S if plan[cmd.team] != "" else 5.0)
		plan[cmd.team] = ""      # the old plan stops while the new one is being prepared
		return
	if cmd.type in ["garrison_attack", "garrison_stop"]:
		_execute_garrison(cmd)
		return
	if cmd.type in ["place", "place_wall", "produce", "cancel_unit", "rally", "sell", "cancel_build", "repair"]:
		_execute_econ(cmd)
		return
	if cmd.type == "board":
		_order_board(cmd)
		return
	var ids: Array = cmd.get("ids", [])
	var movers: Array = []
	for i in ids.size():
		var u: Unit = by_id.get(ids[i])
		if u == null or u.dead: continue
		u.board_target = null          # any other order cancels a pending boarding
		if cmd.type == "move": movers.append(u)     # formation speed for plain moves; attack-move keeps unit speeds
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
	if movers.size() > 1 and not cmd.get("append", false): _assign_group(movers)


# ------------------------------------------------------------------ simulation
func _physics_process(dt: float) -> void:
	if units.is_empty(): return
	var _tt := Time.get_ticks_usec()
	sim_tick(dt)
	if "proftick" in args and tick_n % 30 == 0: printerr("TICK %d sim=%.1f %.1f ms" % [tick_n, sim_time, (Time.get_ticks_usec() - _tt) / 1000.0])


## Optional profiler ("prof" arg): microseconds per simulation stage, averaged and printed every 10 s of game time.
var prof := {}
var _pt := 0


func _pmark(k: String) -> void:
	var t := Time.get_ticks_usec()
	prof[k] = prof.get(k, 0) + (t - _pt)
	_pt = t


func sim_tick(dt: float) -> void:
	var p := "prof" in args
	Unit.prof_on = p
	if p: _pt = Time.get_ticks_usec()
	for c in pending: _execute(c)
	pending.clear()
	if ai and not game_over: ai.tick(dt)
	if base_ai and not game_over: base_ai.tick(dt)
	if base_ai0 and not game_over: base_ai0.tick(dt)
	if p: _pmark("ai+cmds")
	_build_nbr()
	for u in units:
		u.sim_tick(dt)
	if p: _pmark("units")
	_update_boarding()
	_update_groups()
	_separate()
	if p: _pmark("separate")
	_update_shots(dt)
	_update_flights(dt)
	_update_bombs(dt)
	_update_drones(dt)
	_update_supply_drops(dt)
	_update_air_ops(dt)
	if p: _pmark("shots/air")
	_ground_units(dt)
	if p: _pmark("ground")
	_update_derricks(dt)
	_update_garrisons(dt)
	_update_wall_jobs()
	if tick_n % 5 == 0: _update_civic_flags()
	_update_plans()
	if tick_n % 150 == 0:
		trend_samples.append([sim_time, income[0], spent[0], income[1], spent[1]])
		while trend_samples.size() > 13: trend_samples.pop_front()
	_update_debris(dt)
	if p: _pmark("misc")
	_update_visibility()
	if p: _pmark("fog")
	sim_time += dt
	tick_n += 1
	_check_end()
	if p and tick_n % 300 == 0:
		var parts: Array = []
		var tot := 0
		for k in prof: tot += prof[k]
		for k in prof: parts.append("%s %.2f" % [k, prof[k] / 300000.0])
		parts.append("[avoid %.2f ms/tick in %d calls, paths %.2f ms/tick in %d plans]" % [Unit.prof_av_us / 300000.0, Unit.prof_av_n, Unit.prof_path_us / 300000.0, Unit.prof_path_n])
		Unit.prof_av_us = 0; Unit.prof_av_n = 0; Unit.prof_path_us = 0; Unit.prof_path_n = 0
		printerr("PROF t=%d units=%d sim %.2f ms/tick: %s | frame process %.2f ms, physics %.2f ms, nodes %d, draw calls %d" % [int(sim_time),
			units.filter(func(u): return not u.dead).size(), tot / 300000.0, ", ".join(parts),
			Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
			int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)), int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))])
		prof.clear()


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
			# aircraft: the base height is the highest ground under the next few seconds of flight (climb early and
			# fast, descend slowly), and never below the ground right here - no flying through ridges
			var hv := Vector2(u.vel.x, u.vel.z)
			var spd := maxf(hv.length(), 8.0)
			var dir := hv.normalized() if hv.length() > 0.5 else Vector2(-sin(u.heading), -cos(u.heading))
			var look := clampf(spd * 3.0, 30.0, 260.0)
			var want := h
			for i in range(1, 7):
				var q := Vector2(u.position.x, u.position.z) + dir * look * float(i) / 6.0
				want = maxf(want, terrain.height_at(q.x, q.y))
			var up := 45.0 if u.domain == "jet" else 22.0
			var down := 10.0 if u.domain == "jet" else 6.0
			u.position.y = move_toward(u.position.y, want, dt * (up if want > u.position.y else down))
			u.position.y = maxf(u.position.y, h)
		if u.domain == "ground" and u.def.get("visual") != "infantry" and not u.dead:
			var nrm := terrain.normal_at(u.position.x, u.position.z)
			var grad := Vector2(-nrm.x / nrm.y, -nrm.z / nrm.y)
			var f := Vector2(-sin(u.heading), -cos(u.heading))
			var r := Vector2(cos(u.heading), -sin(u.heading))
			u.body.rotation.x = lerp_angle(u.body.rotation.x, atan(grad.dot(f)), minf(1.0, dt * 8.0))
			u.body.rotation.z = lerp_angle(u.body.rotation.z, atan(grad.dot(r)), minf(1.0, dt * 8.0))


## Destinations for an AI group order (same slot logic as the player's formation).
func spread(ids: Array, dest: Vector3, _spacing := 6.0) -> Array:
	var us: Array = []
	for id in ids:
		var u: Unit = by_id.get(id)
		if u != null: us.append(u)
	if us.size() != ids.size():      # unknown ids: plain grid for those
		var pts: Array = []
		for i in ids.size(): pts.append(dest + Vector3((i % 4 - 1.5) * 6.0, 0, (i / 4) * 6.0))
		return pts
	return group_slots(us, dest)


# ------------------------------------------------------------------ movement support (B3)
## Formation for a group order. Ground units and helicopters form a block centred on dest and oriented to the
## direction of travel: larger units in the front rows, each row ordered left to right as the units stand (so paths do
## not cross), slot widths from each unit's drawn size. Every slot is checked for that unit: on walkable ground for
## its movement class (structures and rocks are blocked in the grid), inside the map, not overlapping another slot;
## a bad slot moves to the nearest good spot. Jets get a line abreast 30 m apart. Returns points in the order of us.
func group_slots(us: Array, dest: Vector3) -> Array:
	var n := us.size()
	var out: Array = []
	out.resize(n)
	if n == 0: return out
	var c := Vector3.ZERO
	for u in us: c += u.position
	c /= n
	var fwd := Vector3(dest.x - c.x, 0, dest.z - c.z)
	fwd = fwd.normalized() if fwd.length() > 0.5 else Vector3(0, 0, -1)
	var right := Vector3(-fwd.z, 0, fwd.x)
	var taken: Array = []
	for dom in ["ground", "heli", "jet"]:
		var idx: Array = []
		for i in n:
			if us[i].domain == dom: idx.append(i)
		if idx.is_empty(): continue
		if dom == "jet":
			idx.sort_custom(func(a, b): return us[a].position.dot(right) < us[b].position.dot(right) or (us[a].position.dot(right) == us[b].position.dot(right) and us[a].uid < us[b].uid))
			for k in idx.size(): out[idx[k]] = dest + right * (float(k) - (idx.size() - 1) * 0.5) * 30.0
			continue
		# size class first (big in front), then the units furthest ahead, then id: a strict ordering
		var key := func(u: Unit) -> int:
			var r := u.body_r()
			return 0 if u.def.get("visual") == "infantry" else (2 if r >= 2.2 else 1)
		idx.sort_custom(func(a, b):
			var ka: int = key.call(us[a]); var kb: int = key.call(us[b])
			if ka != kb: return ka > kb
			var fa: float = us[a].position.dot(fwd); var fb: float = us[b].position.dot(fwd)
			if fa != fb: return fa > fb
			return us[a].uid < us[b].uid)
		var sz: Array = []      # slot width across the row
		var dp: Array = []      # slot depth along the direction of travel (vehicles arrive facing it)
		var area := 0.0
		var smax := 0.0
		for i in idx:
			var u: Unit = us[i]
			var gap := 3.0 if dom == "heli" else (1.0 if u.def.get("visual") == "infantry" else 1.8)
			var w := 2.0 * u.sub_r() + gap
			var dd := 2.0 * u.ext_r() + gap
			sz.append(w); dp.append(dd); area += w * dd; smax = maxf(smax, w)
		var W := maxf(smax, sqrt(area) * 1.3)
		var rows: Array = []
		var cur: Array = []
		var cw := 0.0
		var cd := 0.0
		for k in idx.size():
			if not cur.is_empty() and cw + sz[k] > W + 0.01:
				rows.append([cur, cw, cd]); cur = []; cw = 0.0; cd = 0.0
			cur.append(k); cw += sz[k]; cd = maxf(cd, dp[k])
		rows.append([cur, cw, cd])
		var depth := 0.0
		for row in rows: depth += float(row[2])
		var y := depth * 0.5
		for row in rows:
			y -= float(row[2]) * 0.5
			var mem: Array = (row[0] as Array).duplicate()
			mem.sort_custom(func(a, b):
				var pa: float = us[idx[a]].position.dot(right); var pb: float = us[idx[b]].position.dot(right)
				if pa != pb: return pa < pb
				return us[idx[a]].uid < us[idx[b]].uid)
			var x := -float(row[1]) * 0.5
			for k in mem:
				x += float(sz[k]) * 0.5
				out[idx[k]] = _free_slot(dest + right * x + fwd * y, us[idx[k]], taken, fwd, float(sz[k]) * 0.5, float(dp[k]) * 0.5)
				x += float(sz[k]) * 0.5
			y -= float(row[2]) * 0.5
	return out


func _free_slot(p: Vector3, u: Unit, taken: Array, fwd: Vector3, hw: float, hd: float) -> Vector3:
	var cls: String = u.move_class() if u.domain == "ground" else ""
	var rec := [p, hw, hd, u.domain, fwd]
	if _slot_ok(p, rec, cls, taken):
		taken.append(rec); return grounded(p)
	var step := maxf(1.5, minf(hw, hd))
	for ring in range(1, 21):
		var cnt := 6 * ring
		for k in cnt:
			var a := TAU * float(k) / float(cnt)
			var q := p + Vector3(cos(a), 0, sin(a)) * float(ring) * step
			rec = [q, hw, hd, u.domain, fwd]
			if _slot_ok(q, rec, cls, taken):
				taken.append(rec); return grounded(q)
	taken.append([p, hw, hd, u.domain, fwd])
	return grounded(p)


## A slot (rectangle hw x hd half sizes, oriented to the travel direction) is good when it lies inside the map, its
## centre and edges are walkable for the movement class, and it does not overlap a slot already given out.
func _slot_ok(p: Vector3, rec: Array, cls: String, taken: Array) -> bool:
	var hw: float = rec[1]; var hd: float = rec[2]; var dom: String = rec[3]; var f: Vector3 = rec[4]
	var rt := Vector3(-f.z, 0, f.x)
	if not map_bounds.grow(-maxf(hw, hd) - 2.0).has_point(Vector2(p.x, p.z)): return false
	if cls != "":
		var g: GridNav = navs.get(cls, gnav)
		if g:
			if g.blocked_at(p): return false
			for o in [rt * (hw - 0.5), rt * -(hw - 0.5), f * (hd - 0.5), f * -(hd - 0.5)]:
				if g.blocked_at(p + o): return false
	for t in taken:
		if t[3] != dom: continue
		var d: Vector3 = p - t[0]
		if absf(d.dot(rt)) < hw + float(t[1]) - 0.05 and absf(d.dot(f)) < hd + float(t[2]) - 0.05: return false
	return true


## Group order bookkeeping: members of one move share the slowest member's speed (per domain); jets and
## helicopters of the group are spread over altitude layers.
var _grp_seq := 0


func _assign_group(movers: Array) -> void:
	_grp_seq += 1
	var gid := tick_n * 16 + (_grp_seq % 16) + 1
	for dom in ["ground", "heli", "jet"]:
		var m: Array = movers.filter(func(u): return u.domain == dom)
		if dom == "jet" or dom == "heli":
			for k in m.size(): m[k].alt_layer = k
		if m.size() < 2 or dom == "jet": continue
		var slow := INF
		for u in m: slow = minf(slow, float(u.def.speed))
		for u in m:
			u.grp = gid; u.grp_speed = slow; u.grp_lag = false


## Every 10 ticks: a group member well behind the others (distance to its goal more than 10 m over the group's
## median) may drive at full speed to catch up; the rest keep the group speed.
func _update_groups() -> void:
	if tick_n % 10 != 0: return
	var by := {}
	for u in units:
		if u.grp == 0 or u.dead or u is Building: continue
		if not (u.state in [Unit.S.MOVE, Unit.S.ATTACK_MOVE]): continue
		if not by.has(u.grp): by[u.grp] = []
		by[u.grp].append(u)
	for g in by:
		var arr: Array = by[g]
		if arr.size() < 2:
			for u in arr: u.grp_lag = true      # alone now: no one to wait for
			continue
		var ds: Array = arr.map(func(u): return u.flat_dist(u.goal))
		var sd: Array = ds.duplicate()
		sd.sort()
		var med: float = sd[sd.size() / 2]
		for i in arr.size(): arr[i].grp_lag = float(ds[i]) > med + 10.0


## Per-tick neighbour grids for local avoidance (ground and helicopter layers), the airborne jet list, and a grid of
## structures (grown by 12 m) rebuilt whenever the set of structures changes.
const NB_CELL := 10.0
var nbr_ground := {}
var nbr_heli := {}
var nbr_blds := {}
var air_jets: Array = []
var _blds_sig := -1


func _build_nbr() -> void:
	nbr_ground.clear(); nbr_heli.clear(); air_jets.clear()
	var sig := 0
	for u in units:
		if u.dead: continue
		if u is Building:
			sig += u.uid * 7 + 1
			continue
		if u.domain == "jet":
			if u.airborne: air_jets.append(u)
			continue
		if u.domain == "heli" and u.state == Unit.S.LANDED: continue
		if u._sub_r < 0.0 or u._body_r < 0.0: u.body_r(); u.sub_r()      # cached radii, read directly by avoidance
		var g: Dictionary = nbr_ground if u.domain == "ground" else nbr_heli
		var k := Vector2i(floori(u.position.x / NB_CELL), floori(u.position.z / NB_CELL))
		var a: Variant = g.get(k)
		if a == null:
			g[k] = [u]
		else:
			(a as Array).append(u)
	if sig != _blds_sig:
		_blds_sig = sig
		nbr_blds.clear()
		for u in units:
			if not (u is Building) or u.dead: continue
			var e: float = (u as Building).half.length() + 12.0
			for cx in range(floori((u.position.x - e) / NB_CELL), floori((u.position.x + e) / NB_CELL) + 1):
				for cz in range(floori((u.position.z - e) / NB_CELL), floori((u.position.z + e) / NB_CELL) + 1):
					var k := Vector2i(cx, cz)
					if not nbr_blds.has(k): nbr_blds[k] = []
					nbr_blds[k].append(u)


## Structure footprint helpers. Footprints may be rotated (Building.yaw, radians, chosen at placement).
func _foot_yaw(b: Unit) -> float:
	return float(b.get("yaw")) if b is Building else 0.0


## Closest point of a structure's footprint rectangle to the ground point p (x, z).
func footprint_closest(b: Unit, p: Vector2) -> Vector2:
	var h: Vector2 = (b as Building).half
	var yaw := _foot_yaw(b)
	var d := p - Vector2(b.position.x, b.position.z)
	var cs := cos(yaw); var sn := sin(yaw)
	var lx := d.x * cs - d.y * sn
	var lz := d.x * sn + d.y * cs
	lx = clampf(lx, -h.x, h.x); lz = clampf(lz, -h.y, h.y)
	return Vector2(b.position.x, b.position.z) + Vector2(lx * cs + lz * sn, -lx * sn + lz * cs)


## Point `gap` metres outside the footprint wall nearest to p (p inside or outside the footprint).
func footprint_outside(b: Unit, p: Vector2, gap: float) -> Vector2:
	var h: Vector2 = (b as Building).half
	var yaw := _foot_yaw(b)
	var d := p - Vector2(b.position.x, b.position.z)
	var cs := cos(yaw); var sn := sin(yaw)
	var lx := clampf(d.x * cs - d.y * sn, -h.x, h.x)
	var lz := clampf(d.x * sn + d.y * cs, -h.y, h.y)
	if h.x - absf(lx) < h.y - absf(lz): lx = signf(lx if lx != 0.0 else 1.0) * (h.x + gap)
	else: lz = signf(lz if lz != 0.0 else 1.0) * (h.y + gap)
	return Vector2(b.position.x, b.position.z) + Vector2(lx * cs + lz * sn, -lx * sn + lz * cs)


## Safety net behind local avoidance: units that still overlap are eased apart a little each tick (deep overlaps are
## resolved faster), never pulled through each other; units are kept out of structures and rocks. Spatial hashing
## keeps this close to linear in the number of units.
const SEP_CELL := 10.0
var _obs_grid := {}
var _obs_n := -1


func _obstacle_grid() -> Dictionary:
	if _obs_n != obstacles_2d.size():
		_obs_n = obstacles_2d.size()
		_obs_grid.clear()
		for o in obstacles_2d:
			var r: float = o.z + 12.0
			for cx in range(int(floor((o.x - r) / 16.0)), int(floor((o.x + r) / 16.0)) + 1):
				for cz in range(int(floor((o.y - r) / 16.0)), int(floor((o.y + r) / 16.0)) + 1):
					var k := Vector2i(cx, cz)
					if not _obs_grid.has(k): _obs_grid[k] = []
					_obs_grid[k].append(o)
	return _obs_grid


func _separate() -> void:
	var grid := {}
	var blds: Array = []
	var live: Array = []
	var hull: Array = []          # per live unit: hull circle centres (PackedVector2Array)
	for u in units:
		if u.dead: continue
		if u is Building:
			blds.append(u)
			continue
		if u.domain == "jet" or (u.domain == "heli" and u.state == Unit.S.LANDED): continue
		if u._sub_r < 0.0: u.sub_r()
		var k := Vector2i(int(floor(u.position.x / SEP_CELL)), int(floor(u.position.z / SEP_CELL)))
		if not grid.has(k): grid[k] = []
		grid[k].append(live.size())
		live.append(u)
		hull.append(u.hull_pts())
	var og := _obstacle_grid()
	for ia in live.size():
		var a: Unit = live[ia]
		var ka := Vector2i(int(floor(a.position.x / SEP_CELL)), int(floor(a.position.z / SEP_CELL)))
		var ra: float = a._sub_r
		var ea: float = a._sub_r + a._sub_off
		var ga: bool = a.domain == "ground"
		for dz in range(-1, 2):
			for dx in range(-1, 2):
				var cell: Variant = grid.get(ka + Vector2i(dx, dz))
				if cell == null: continue
				for ib: int in cell:
					if ib <= ia: continue
					var b: Unit = live[ib]
					if (b.domain == "ground") != ga: continue
					var dcx: float = b.position.x - a.position.x
					var dcz: float = b.position.z - a.position.z
					var reach: float = ea + b._sub_r + b._sub_off
					if dcx * dcx + dcz * dcz >= reach * reach: continue
					if a.board_target == b or b.board_target == a: continue
					# deepest overlap between the two hull models (circles; vehicles have two each)
					var min_d: float = (ra + b._sub_r) * 0.9
					var pen := 0.0
					var dir := Vector2.ZERO
					for pa in hull[ia]:
						for pb in hull[ib]:
							var d: Vector2 = pb - pa
							var l := d.length()
							if min_d - l > pen:
								pen = min_d - l
								dir = d / l if l > 0.001 else (Vector2(1, 0) if a.uid % 2 == 0 else Vector2(0, 1))
					if pen > 0.0:
						var kk := 0.5 if pen > min_d * 0.4 else 0.15
						var push := dir * pen * kk
						a.position -= Vector3(push.x, 0, push.y)
						b.position += Vector3(push.x, 0, push.y)
		if ga:
			for bb in blds:
				var b: Building = bb
				var dd := Vector2(a.position.x - b.position.x, a.position.z - b.position.z)
				var lim: float = b.half.x + b.half.y + a.def.radius
				if absf(dd.x) > lim or absf(dd.y) > lim: continue
				if a.board_target == b: continue
				a.position = b.push_out(a.position, a.def.radius * 0.5)    # oriented footprint (placement rotation)
			var oc: Variant = og.get(Vector2i(int(floor(a.position.x / 16.0)), int(floor(a.position.z / 16.0))))
			if oc != null:
				for o in oc:
					var d2 := Vector2(a.position.x - o.x, a.position.z - o.y)
					var r: float = o.z * 0.75 + a.def.radius * 0.5
					if d2.length() < r and d2.length() > 0.001:
						var nn := d2.normalized() * r
						a.position = Vector3(o.x + nn.x, a.position.y, o.y + nn.y)
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
	var bd2 := r * r
	for o in units:
		if o.dead or o.team == u.team or o.team < 0: continue
		var dx := o.position.x - p.x
		var dz := o.position.z - p.z
		var d2 := dx * dx + dz * dz
		if d2 < bd2 and u.can_target(o): bd2 = d2; best = o
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
	_battle_cry(shooter)
	var node: Node3D
	var mk := FX.muzzle_kind(shooter, w)   # presentation only: weapon class for muzzle flash / tracer size
	match w.proj:
		"missile", "rocket":
			node = FX.missile_node(w.proj == "missile")
			FX.muzzle(self, from, dir, mk)
		"bullet":
			# tracers on a fraction of rounds (every Nth round of this shooter; deterministic, no rng)
			node = FX.tracer_node(mk, int(shots_by[shooter.uid]) % FX.tracer_every(mk) == 0)
			if shooter.is_air():
				FX.muzzle(self, from, dir, mk)
			elif rng.randf() < 0.5 or mk == "mg":   # (the rng draw is kept so the simulation sequence is unchanged)
				FX.muzzle(self, from, dir, mk)
		_:
			node = FX.tracer_node(mk, true)
			FX.muzzle(self, from, dir, mk)
			if w.proj == "arty":
				FX.incoming(self, aim, dist / float(w.speed) - 1.86)
	add_child(node)
	node.global_position = from
	if dir.length() > 0.01: node.look_at(from + dir, Vector3.UP if absf(dir.y) < 0.99 else Vector3.RIGHT)
	node.reset_physics_interpolation()
	shots.append({"node": node, "pos": from, "dir": dir, "aim": aim, "left": dist, "speed": float(w.speed),
		"shooter": shooter, "target": tunit, "dmg": float(w.damage), "splash": float(w.splash),
		"homing": w.proj == "missile", "kind": w.proj, "targets": w.targets, "vs": w.get("vs", {}),
		"arc": w.proj == "arty", "dist0": maxf(dist, 1.0)})


## Nation battle cries: Iranian infantry shout (Farsi, client-supplied clip) when they open fire on the enemy.
## At most one cry per team every 14 s so a firefight does not turn into a loop. Presentation only.
const BATTLE_CRY := {"iran": "iran_shout"}
var cry_t := [-99.0, -99.0]
var cries := 0


func _battle_cry(shooter: Unit) -> void:
	if shooter.def.get("visual") != "infantry" or shooter.team < 0 or shooter.team > 1: return
	var clip: String = BATTLE_CRY.get(nation_of(shooter.team), "")
	if clip == "" or sim_time - cry_t[shooter.team] < 14.0: return
	cry_t[shooter.team] = sim_time
	cries += 1
	SFX.play(shooter.body, clip, shooter.global_position, 2.0, 1.0, true)


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
			FX.detach_trails(s.node)
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
		if direct: t.take_damage(s.dmg * rng.randf_range(0.85, 1.15) * _dmg_mult(s.shooter) * dealt_mult(s.shooter, t) * _armor_mult(s, t), s.shooter)
	if diag and s.shooter and s.shooter.team == 0: diag.on_shot(s.shooter, t, p, direct)
	if s.splash > 0.0:
		for o in units:
			if o.dead or o == t or o.domain == "jet": continue
			if o.domain == "heli" and not ("heli" in s.targets): continue
			var d := o.world_center().distance_to(p)
			if d < s.splash:
				o.take_damage(s.dmg * 0.5 * (1.0 - d / s.splash) * dealt_mult(s.shooter, o) * _armor_mult(s, o), s.shooter)
	var gy := ground_h(p.x, p.z)
	var ground := p.y < gy + 1.5
	# presentation: impact effect by projectile and surface (FX.impact_kind)
	var surf := "ground"
	if direct:
		if t is Building: surf = "structure"
		elif t.def.get("visual") == "infantry": surf = "infantry"
		elif t.is_air(): surf = "air"
		else: surf = "armour"
	elif not ground: surf = "air"
	var heavy_bullet: bool = s.kind == "bullet" and s.shooter != null and is_instance_valid(s.shooter) and s.shooter.is_air()
	var fx_kind: String = {"bullet": "cannon" if heavy_bullet else "bullet", "arty": "arty", "rocket": "rocket", "missile": "rocket"}.get(s.kind, "shell")
	if fx_kind == "shell" and s.dmg < 60.0: fx_kind = "cannon"   # 25 mm autocannon
	if s.kind == "arty" or (surf == "ground" and fx_kind != "bullet"):
		FX.impact_kind(self, Vector3(p.x, gy + 0.2, p.z), fx_kind, surf)
	else:
		FX.impact_kind(self, Vector3(p.x, maxf(p.y, gy + 0.1), p.z), fx_kind, surf)


func _armor_mult(s: Dictionary, o: Unit) -> float:
	var a := UnitDefs.armor_of(o.def)
	var vs: Dictionary = s.get("vs", {})
	if vs.has(a): return float(vs[a])
	return float(UnitDefs.ARMOR_MULT.get(s.kind, {}).get(a, 1.0))


# ------------------------------------------------------------------ support powers
func _dmg_mult(shooter: Unit) -> float:
	var vet: float = Veterancy.mult(shooter, "dmg") if is_instance_valid(shooter) else 1.0
	if shooter == null or shooter.team != 1 or _automated(): return vet
	return vet * float(Game.DIFFICULTY.get(Game.settings.difficulty, Game.DIFFICULTY["Normal"]).damage_mult)


var promotions := 0


func on_promoted(u: Unit) -> void:
	promotions += 1
	if u.team == 0 and hud: hud.flash_message("%s promoted to %s" % [u.def.name, Veterancy.RANKS[u.vet_rank]])


func power_cooldown_left(team: int, id: String) -> float:
	return maxf(0.0, float(power_ready[team].get(id, 0.0)) - sim_time)


## Support powers that need a structure (e.g. Paratroopers need an Airfield) in the base scenario.
func power_problem(team: int, id: String) -> String:
	var p: Dictionary = UnitDefs.POWERS[id]
	if not (id in Nations.powers(nation_of(team))): return "Not available to %s" % Nations.name_of(nation_of(team))
	if scenario == "base" and p.has("requires") and structures(team, p.requires).is_empty():
		return "Requires " + bname(team, p.requires)
	return ""


func launch_power(team: int, id: String, target: Vector3) -> void:
	if power_cooldown_left(team, id) > 0.0 or power_problem(team, id) != "": return
	var p: Dictionary = UnitDefs.POWERS[id]
	power_ready[team][id] = sim_time + float(p.cooldown)
	if p.has("drones"):
		_launch_drones(team, id, target)
		return
	if p.has("gunship"): _launch_gunship(team, id, target); return       # B3 air operations (see the end of this file)
	if p.has("airdrop"): _launch_airdrop(team, id, target); return
	if p.has("airlift"): _launch_airlift(team, id, target); return
	var edge_z := map_bounds.end.y + 120.0 if team == 0 else map_bounds.position.y - 120.0
	var start := Vector3(target.x * 0.7, ground_h(target.x, target.z), edge_z)
	var dir := Vector3(target.x - start.x, 0, target.z - start.z).normalized()
	var node := Node3D.new()
	add_child(node)
	var pmodel := str(p.get("model3d", "_"))
	if pmodel == C130_MODEL: pmodel = c130_model(team)
	if ResourceLoader.exists(pmodel):
		var m3: Node3D = (load(pmodel) as PackedScene).instantiate()
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
	if hud and team == 0: hud.flash_message("%s inbound" % lbl(team, id, p.name))


func _update_flights(dt: float) -> void:
	for f in flights.duplicate():
		var p: Dictionary = f.def
		for pr in f.node.find_children("Prop*", "Node3D", true, false): (pr as Node3D).rotate_object_local(Vector3.BACK, dt * 30.0)
		f.pos += f.dir * float(p.speed) * dt
		if terrain:   # stay above the ridges on the way in and out (same look-ahead as aircraft units)
			var want := terrain.height_at(f.pos.x, f.pos.z)
			for i in range(1, 7):
				var q: Vector3 = f.pos + f.dir * float(p.speed) * 3.0 * float(i) / 6.0
				want = maxf(want, terrain.height_at(q.x, q.z))
			f.pos.y = maxf(move_toward(f.pos.y, want, dt * (45.0 if want > f.pos.y else 10.0)), terrain.height_at(f.pos.x, f.pos.z))
		f.node.position = f.pos
		var along: float = (f.pos - f.target).dot(f.dir)   # <0 before the target, >0 after
		if p.has("troops"):
			var nt := int(p.troops)
			while int(f.dropped) < nt and along >= -14.0 + int(f.dropped) * 5.0:
				var u := _spawn(Nations.swap_unit(nation_of(f.team), str(p.unit)), f.team, f.pos + Vector3(0, 0, 0), atan2(-f.dir.x, -f.dir.z))
				u.start_parachute(maxf(4.0, f.pos.y + float(p.altitude) - 4.0 - ground_h(f.pos.x, f.pos.z)))   # from the aircraft's real height
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


var bomb_damage := 0.0   # damage bombs have dealt to the other side (diagnostics and tests)


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
				if d < b.splash:
					var hb := o.hp
					o.take_damage(b.dmg * (1.0 - 0.6 * d / b.splash), null)
					if o.team != b.team: bomb_damage += hb - o.hp
			FX.detach_trails(b.node)
			b.node.queue_free()
			bombs.erase(b)


# ------------------------------------------------------------------ deaths and visibility
func on_unit_died(u: Unit) -> void:
	if u is Building and (u as Building).is_civic():
		_eject_garrison(u as Building)
		u.team = -1
		return
	if not u.passengers.is_empty(): _lose_passengers(u)
	if u.engine_snd: u.engine_snd.stop()
	if u.team == 0: losses += 1
	else: kills += 1
	var vis_kind: String = u.def.get("visual", "model")
	if u is Building and (u as Building).is_wall(): _update_wall_posts.call_deferred()
	if u is Building:
		# built structures collapse into a ruin (add_rubble -> FX.collapse); sold ones are dismantled in a dust cloud
		var bb := u as Building
		if bb.sold: FX.impact_kind(self, u.global_position, "bullet", "structure")
		elif not bb.built: FX.explosion(self, u.global_position + Vector3(0, 1, 0), 1.0, "large")
	elif vis_kind == "infantry":
		FX.unit_death(self, u)
		_fade_out(u, 3.0)
	elif vis_kind == "vehicle_art":
		FX.unit_death(self, u)
		if u.card_sprite: u.card_sprite.modulate = Color(0.16, 0.14, 0.12)
	elif u.domain == "ground":
		FX.unit_death(self, u)
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
		FX.unit_death(self, u)
		# the airframe falls (burning trail) and explodes where it hits the ground
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
				FX.crash(self, n, n.global_position)
				var sp := n.find_child("Sprite", true, false) as Sprite3D
				if sp: sp.modulate = Color(0.12, 0.11, 0.1)
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
		if u.team == 0 and not u.dead: eyes.append([u.position, u.sight_r()])
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
	var reveal_all := "reveal" in args     # review screenshots: show both sides
	for u in units:
		if u.team == 0 or u.dead:
			if u.dead and not seen.get(u.uid, false): u.visible = false
			continue
		var vis := reveal_all or _cell_visible(u.position)
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
		if u.team == team and not u.dead and not (u is Building and (u as Building).is_civic()) and not u.def.get("transient", false): n += 1
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
		cash[t] = BuildingDefs.START_CASH if _automated() else int(Game.settings.get("start_cash", BuildingDefs.START_CASH))
		var cc := add_structure("command_center", t, start_pos[t], true)
		add_flag(t, cc.position + Vector3(cc.half.x + 4.0, 0, (cc.half.y - 2.0) * (1.0 if t == 0 else -1.0)))
		var fwd := -1.0 if t == 0 else 1.0     # toward the map centre
		var d := _spawn(Nations.swap_unit(nation_of(t), "dozer"), t, cc.position + Vector3(-8, 0, fwd * (cc.half.y + 8.0)), 0.0 if t == 0 else PI)
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


func add_structure(k: String, team: int, pos: Vector3, built := false, yaw := 0.0, sx := 1.0) -> Building:
	pos = prepare_site(k, pos, yaw, sx)
	var b := Building.new()
	add_child(b)
	b.setup_structure(self, k, team, new_uid(), pos, built, yaw, sx)
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
## yaw: placement rotation (radians about +Y); the footprint is tested as an oriented box everywhere.
func placement_problem(team: int, k: String, pos: Vector3, yaw := 0.0, sx := 1.0) -> String:
	var d: Dictionary = BuildingDefs.DEFS[k]
	if d.get("wall", false):      # a single wall segment: may touch other walls end to end
		return wall_problem(team, k, {"segs": [{"pos": pos, "yaw": yaw, "sx": sx}], "cost": int(d.cost), "joints": []})
	if cash[team] < int(d.cost): return "Not enough cash"
	if not requirements_met(team, k): return "Requires " + ", ".join(d.requires.map(func(x): return bname(team, x)))
	var h: Vector2 = d.size * 0.5 + Vector2(1.0, 1.0)
	var box_h := Building.aabb_half(h, yaw)   # enclosing axis-aligned box (terrain, derricks, apron)
	if not map_bounds.grow(-10).has_point(Vector2(pos.x, pos.z)): return "Outside the map"
	if terrain:
		var st := terrain.footprint_stats(pos, Building.aabb_half(d.size * 0.5, yaw))
		if st.y > build_max_slope: return "Ground too steep (%.0f° > %.0f°)" % [st.y, build_max_slope]
	if not gnav.box_free(pos, h, yaw): return "Blocked"
	if terrain:
		for od in derricks:
			if absf(od.pos.x - pos.x) < box_h.x + 6.0 and absf(od.pos.z - pos.z) < box_h.y + 6.0: return "Blocked"
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
		if absf(pos.x - rc.x) < rh.x + box_h.x and absf(pos.z - rc.z) < rh.y + box_h.y: return "On an airfield apron"
	for u in units:
		if u.dead or u.is_air() or u is Building: continue
		var lu := Building.to_local_xz(pos, yaw, u.position)
		if absf(lu.x) < h.x + u.def.radius * 0.5 and absf(lu.y) < h.y + u.def.radius * 0.5 and not u.def.get("builder", false):
			return "Units in the way"
	# build radius: near any own structure (Generals-style base creep)
	var near := false
	for b in structures(team, "", false):
		if b.position.distance_to(pos) < 140.0: near = true; break
	if not near: return "Too far from your base"
	return ""


# ------------------------------------------------------------------ walls (HESCO / concrete T-wall lines)
## A wall is drawn as a line: it is split into equal segments (each 0.67-1.35 of the model length, scaled along
## the line so consecutive segments butt together exactly). A line end that starts or stops near a Defence Tower
## (WALL_TOWER_SNAP) is trimmed to just inside the tower's footprint, so the tower acts as a joint; an end near the
## free end of another wall line (WALL_END_SNAP) starts exactly there. The barrier is therefore continuous.
const WALL_TOWER_SNAP := 12.0
const WALL_END_SNAP := 5.0
const WALL_JOINT_TOWERS := ["defense_tower"]
var wall_jobs := {}             # dozer uid -> [site uid, ...] still to construct, in order
var wall_run_next := 1


## Nearest joint for a wall end at p: {"pos", "joint": Building or null, "type": "tower" / "end" / ""}.
func wall_snap(team: int, p: Vector3) -> Dictionary:
	var best := {"pos": Vector3(p.x, 0, p.z), "joint": null, "type": ""}
	var bd := INF
	for b in structures(team, "", false):
		if b.bkind in WALL_JOINT_TOWERS:
			var d := Vector2(b.position.x - p.x, b.position.z - p.z).length()
			if d < WALL_TOWER_SNAP and d < bd:
				bd = d; best = {"pos": Vector3(b.position.x, 0, b.position.z), "joint": b, "type": "tower"}
		elif b.is_wall():
			for e in b.wall_ends():
				var d2 := Vector2(e.x - p.x, e.z - p.z).length()
				if d2 < WALL_END_SNAP and d2 < bd - 0.01:
					bd = d2; best = {"pos": Vector3(e.x, 0, e.z), "joint": b, "type": "end"}
	return best


## Segments for a wall of kind k drawn from a to b: {"segs": [{"pos", "yaw", "sx"}], "cost", "problem", "joints"}.
func wall_plan(team: int, k: String, a: Vector3, b: Vector3) -> Dictionary:
	var d: Dictionary = BuildingDefs.DEFS[k]
	var seg: float = d.size.x
	var sa := wall_snap(team, a)
	var sb := wall_snap(team, b)
	var pa: Vector3 = sa.pos
	var pb: Vector3 = sb.pos
	if sa.joint != null and sa.joint == sb.joint: pb = Vector3(b.x, 0, b.z); sb = {"pos": pb, "joint": null, "type": ""}
	var dir := pb - pa
	dir.y = 0.0
	var out := {"segs": [], "cost": 0, "problem": "", "joints": [sa.joint, sb.joint].filter(func(x): return x != null), "a": pa, "b": pb}
	if dir.length() < 1.0:
		out.problem = "Drag to draw a line"
		return out
	dir = dir.normalized()
	if sa.type == "tower": pa += dir * ((sa.joint as Building).reach_along(dir) - 0.8)
	if sb.type == "tower": pb -= dir * ((sb.joint as Building).reach_along(dir) - 0.8)
	var length := (pb - pa).dot(dir)
	if length < seg * 0.5:
		out.problem = "Too short"
		return out
	var n := maxi(1, int(round(length / seg)))
	if length / n > seg * 1.35: n += 1
	var s := length / n
	var yaw := atan2(-dir.z, dir.x)        # the segment's long axis (local X) runs along the line
	# the barrier faces away from its owner's base (toward the enemy): flip the segments if their front points home
	var home_p: Vector3 = start_pos[team] if team >= 0 and team < start_pos.size() else Vector3.ZERO
	var ccs := structures(team, "command_center", false)
	if not ccs.is_empty(): home_p = ccs[0].position
	var mid := (pa + pb) * 0.5
	if Vector3(sin(yaw), 0, cos(yaw)).dot(Vector3(mid.x - home_p.x, 0, mid.z - home_p.z)) < 0.0: yaw = wrapf(yaw + PI, -PI, PI)
	for i in n:
		var c := pa + dir * (s * (i + 0.5))
		out.segs.append({"pos": Vector3(c.x, 0, c.z), "yaw": yaw, "sx": s / seg})
	out.a = pa; out.b = pb
	out.cost = int(d.cost) * n
	out.problem = wall_problem(team, k, out)
	return out


## "" when every segment of a planned wall may be built, otherwise the reason.
func wall_problem(team: int, k: String, plan: Dictionary) -> String:
	var d: Dictionary = BuildingDefs.DEFS[k]
	if cash[team] < int(plan.cost): return "Not enough cash ($%d for %d segments)" % [int(plan.cost), plan.segs.size()]
	if not requirements_met(team, k): return "Requires " + ", ".join(d.requires.map(func(x): return bname(team, x)))
	var near := false
	var others: Array = []
	for ub in units:
		if ub is Building and not ub.dead and not (ub in plan.joints): others.append(ub)
	for sg in plan.segs:
		var pos: Vector3 = sg.pos
		var h := Vector2(d.size.x * 0.5 * float(sg.sx), d.size.y * 0.5)
		if not map_bounds.grow(-10).has_point(Vector2(pos.x, pos.z)): return "Outside the map"
		if terrain:
			var st := terrain.footprint_stats(pos, Building.aabb_half(h, sg.yaw))
			if st.y > build_max_slope: return "Ground too steep (%.0f° > %.0f°)" % [st.y, build_max_slope]
		if not gnav.box_free_static(pos, h, sg.yaw): return "Blocked"
		for ob in others:
			# wall lines may touch other walls end to end; everything else keeps the usual 1 m clearance
			var grow := 0.0 if (ob as Building).is_wall() else 1.0
			var oh: Vector2 = ob.half + Vector2(grow, grow)
			var hh := h - Vector2(0.3, 0.1) if (ob as Building).is_wall() else h
			if Building.obb_overlap(pos, hh, sg.yaw, ob.position, oh, ob.yaw): return "Blocked by %s" % ob.def.name
		for od in derricks:
			if Vector2(od.pos.x - pos.x, od.pos.z - pos.z).length() < h.x + 6.0: return "Blocked"
		for u in units:
			if u.dead or u.is_air() or u is Building or u.def.get("builder", false): continue
			var lu := Building.to_local_xz(pos, sg.yaw, u.position)
			if absf(lu.x) < h.x + u.def.radius * 0.5 and absf(lu.y) < h.y + u.def.radius * 0.5: return "Units in the way"
		if not near:
			for ob in structures(team, "", false):
				if ob.position.distance_to(pos) < 140.0: near = true; break
	if not near: return "Too far from your base"
	return ""


func _place_wall(cmd: Dictionary) -> void:
	var team: int = cmd.team
	var k: String = cmd.id
	if not BuildingDefs.DEFS.has(k) or not BuildingDefs.DEFS[k].get("wall", false): return
	var dz: Unit = by_id.get(cmd.get("builder", -1))
	if dz == null or dz.dead or dz.team != team or not dz.def.get("builder", false): return
	var plan := wall_plan(team, k, cmd.a, cmd.b)
	if plan.problem != "" or plan.segs.is_empty(): return
	spend(team, int(plan.cost))
	var run := wall_run_next
	wall_run_next += 1
	var ids: Array = []
	for sg in plan.segs:
		_clear_rubble(sg.pos, Building.aabb_half(BuildingDefs.DEFS[k].size * 0.5, sg.yaw))
		var b := add_structure(k, team, sg.pos, false, sg.yaw, sg.sx)
		b.wall_run = run
		ids.append(b.uid)
	_update_wall_posts()
	var first: Building = by_id.get(ids[0])
	dz.order_build(first)
	wall_jobs[dz.uid] = ids


## A dozer given a wall line builds its segments one after another; another order from the player ends the job.
func _update_wall_jobs() -> void:
	if wall_jobs.is_empty(): return
	for id in wall_jobs.keys():
		var dz: Unit = by_id.get(id)
		var q: Array = wall_jobs[id]
		if dz == null or dz.dead or q.is_empty():
			wall_jobs.erase(id); continue
		if dz.state == Unit.S.BUILD: continue
		var cur: Unit = by_id.get(q[0])
		if cur and not cur.dead and not (cur as Building).built:
			wall_jobs.erase(id); continue      # the dozer was sent elsewhere before finishing
		while not q.is_empty():
			var nb: Unit = by_id.get(q[0])
			if nb and not nb.dead and not (nb as Building).built: break
			q.pop_front()
		if q.is_empty() or dz.state != Unit.S.IDLE:
			wall_jobs.erase(id); continue
		dz.order_build(by_id.get(q[0]))


## Concrete walls show an end post wherever a line ends freely (not against another segment or a tower).
func _update_wall_posts() -> void:
	var walls: Array = units.filter(func(u): return u is Building and not u.dead and (u as Building).is_wall())
	var towers: Array = units.filter(func(u): return u is Building and not u.dead and u.bkind in WALL_JOINT_TOWERS)
	for w: Building in walls:
		var post_path := str(w.bdef.get("post_model", ""))
		if post_path == "" or not ResourceLoader.exists(post_path): continue
		var ends := w.wall_ends()
		for i in 2:
			var e: Vector3 = ends[i]
			var free := true
			for o: Building in walls:
				if o == w or o.team != w.team: continue
				for oe in o.wall_ends():
					if Vector2(oe.x - e.x, oe.z - e.z).length() < 1.2: free = false
			for t: Building in towers:
				if t.contains_xz(e, 1.0): free = false
			var nm := "EndPost%d" % i
			var node: Node3D = w.get_node_or_null(nm)
			if free and node == null:
				node = (load(post_path) as PackedScene).instantiate()
				node.name = nm
				node.position = Vector3(-w.half.x if i == 0 else w.half.x, 0, 0)
				w.add_child(node)
				w.tint_team(node)
			elif not free and node: node.queue_free()


func _execute_econ(cmd: Dictionary) -> void:
	var team: int = cmd.team
	match cmd.type:
		"place":
			var k: String = cmd.id
			var dz: Unit = by_id.get(cmd.get("builder", -1))
			if dz == null or dz.dead or dz.team != team or not dz.def.get("builder", false): return
			var yaw := float(cmd.get("yaw", 0.0))
			var sx := clampf(float(cmd.get("sx", 1.0)), 0.5, 1.35) if BuildingDefs.DEFS[k].get("wall", false) else 1.0
			if placement_problem(team, k, cmd.pos, yaw, sx) != "":
				return
			spend(team, int(BuildingDefs.DEFS[k].cost))
			_clear_rubble(cmd.pos, Building.aabb_half(BuildingDefs.DEFS[k].size * 0.5, yaw))
			var b := add_structure(k, team, cmd.pos, false, yaw, sx)
			wall_jobs.erase(dz.uid)
			dz.order_build(b)
			if b.is_wall(): _update_wall_posts()
		"place_wall":
			_place_wall(cmd)
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
		spawn_produced(b, Nations.swap_unit(nation_of(b.team), str(b.bdef.free_unit)))
	if announce and b.team == 0 and hud: hud.flash_message("%s complete" % b.def.name)


## A finished unit leaves its building toward the rally point; aircraft appear landed on a free pad.
func spawn_produced(b: Building, k: String) -> void:
	var team := b.team
	var exit_dir := (b.rally - b.position)
	exit_dir.y = 0.0
	exit_dir = exit_dir.normalized() if exit_dir.length() > 0.1 else Vector3(0, 0, 1.0 if team == 0 else -1.0)
	var reach := b.reach_along(exit_dir) + 5.0
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
			u.taxi_out = b.taxi_route(i, true); u.taxi_in = b.taxi_route(i, false)
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
	FX.collapse(self, b)   # destruction sequence (presentation): the model sinks and tilts into a dust cloud
	add_rubble_at(b.position, b.bkind, -2 if b.is_civic() else b.team, b.half, b.uid, b.yaw)
	rubble[rubble.size() - 1]["sx"] = b.seg_scale      # a wall segment is rebuilt at its own length


## The ruin (visual only, FXRuin) is built from the kind and seed, so a saved game restores the same look.
## `half` is in the building's own frame, rotated by `yaw`; `age` = seconds since the destruction (loaded games).
func add_rubble_at(pos: Vector3, bkind: String, bteam: int, bhalf: Vector2, seed_id: int, yaw := 0.0, age := 0.0) -> void:
	var n := Node3D.new()
	n.name = "Ruin_%d" % seed_id
	n.position = pos
	n.rotation.y = yaw
	add_child(n)
	FX.ruin(self, n, bkind, bhalf, seed_id, age)
	rubble.append({"pos": pos, "kind": bkind, "team": bteam, "half": bhalf, "node": n, "seed": seed_id, "yaw": yaw, "t": sim_time - age})


func _clear_rubble(pos: Vector3, h: Vector2) -> void:
	for r in rubble.duplicate():
		if absf(r.pos.x - pos.x) < r.half.x + h.x and absf(r.pos.z - pos.z) < r.half.y + h.y:
			r.node.queue_free()
			rubble.erase(r)


func rubble_at(p: Vector3, team: int) -> Dictionary:
	for r in rubble:
		var l := Building.to_local_xz(r.pos, float(r.get("yaw", 0.0)), p)
		if r.team == team and absf(l.x) < r.half.x and absf(l.y) < r.half.y: return r
	return {}


# ------------------------------------------------------------------ supply drops (Supply Drop Zone)
var drop_flights: Array = []    # {"node", "pos", "dir", "target", "team", "left", "value", "released"}
var drop_crates: Array = []
var drop_income := [0, 0]     # {"node", "pos", "vy", "team", "value", "canopy"}
const C130_SPRITE := "res://assets/aircraft/c130/c130_top.png"
const C130_MODEL := "res://assets/units3d/c130/c130.glb"


## The transport used for supply drops and paratroopers carries the team's own national markings.
func c130_model(team: int) -> String:
	return str(Nations.DEFS.get(nation_of(team), Nations.DEFS.usa).get("c130_model", C130_MODEL))
const CRATE_MODEL := "res://assets/units3d/props/supply_crate_chute.glb"


## Supply Drop Zone delivery. The C-130 picks, among a fan of approach headings from its own side of the map, the
## one whose track crosses the lowest terrain, flies it with terrain look-ahead (climbing early enough to keep
## DROP_CLEAR over every ridge on its path, wingtips included), and releases the crates from its real height.
const DROP_CLEAR := 30.0        # minimum height of the transport above the terrain under it and its wingtips
const DROP_SPEED := 55.0
var drop_min_clear := INF       # lowest clearance any drop aircraft had over the terrain (tests / diagnostics)


func launch_supply_drop(b: Building) -> void:
	launch_drop_at(b.team, b.drop_point_world(), b.bdef.drop)


func launch_drop_at(team: int, target: Vector3, d: Dictionary) -> Dictionary:
	var edge_z: float = map_bounds.end.y + 140.0 if team == 0 else map_bounds.position.y - 140.0
	var dir0 := Vector3(target.x - (target.x + 60.0), 0, target.z - edge_z).normalized()
	var dir := best_approach(target, dir0, 12.0)
	var start: Vector3 = target - dir * (_edge_exit(target, -dir) + 140.0)
	start.y = terrain_ramp_y(start, dir, DROP_SPEED, DROP_CLEAR, 12.0, 12.0) + 10.0
	var node := Node3D.new()
	add_child(node)
	var c130: String = c130_model(team)
	if ResourceLoader.exists(c130):
		var m: Node3D = (load(c130) as PackedScene).instantiate()
		m.scale = Vector3.ONE * UnitDefs.SCALE.aircraft
		node.add_child(m)
	else:
		var s := Sprite3D.new()
		var tex: Texture2D = load(C130_SPRITE)
		s.texture = tex; s.axis = Vector3.AXIS_Y; s.shaded = true; s.double_sided = true
		s.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
		s.pixel_size = 40.4 * UnitDefs.SCALE.aircraft / float(tex.get_width()) * 1.05   # C-130 span 40.4 m
		s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		node.add_child(s)
	node.position = start
	node.rotation.y = atan2(-dir.x, -dir.z)
	node.reset_physics_interpolation()
	SFX.play(node, "jet_flyby", start, 2.0, 0.7, true)
	var f := {"node": node, "pos": start, "dir": dir, "target": target, "team": team,
		"crates": int(d.crates), "value": int(d.value), "released": 0, "min_clear": INF, "turn": last_approach.get("angle", 0.0)}
	drop_flights.append(f)
	if team == 0 and hud: hud.flash_message("Supply drop inbound")
	return f


func _update_supply_drops(dt: float) -> void:
	for f in drop_flights.duplicate():
		for pr in f.node.find_children("Prop*", "Node3D", true, false): (pr as Node3D).rotate_object_local(Vector3.BACK, dt * 30.0)
		f.pos += f.dir * DROP_SPEED * dt
		f.pos.y = fly_terrain_y(f.pos, f.dir, DROP_SPEED, DROP_CLEAR, f.pos.y, dt, 12.0)
		var cl := clearance(f.pos, f.dir, 12.0)
		f.min_clear = minf(f.min_clear, cl)
		if absf(f.pos.x) < MAP_HALF and absf(f.pos.z) < MAP_HALF: drop_min_clear = minf(drop_min_clear, cl)
		f.node.position = f.pos
		var along: float = (f.pos - f.target).dot(f.dir)
		# release the crates in a short stick centred on the drop point, from the aircraft's own height
		while f.released < f.crates and along >= -12.0 + f.released * 8.0 - 20.0:
			var c := _make_crate()
			var p: Vector3 = f.pos - f.dir * 6.0 + Vector3(0, -1.5, 0)
			c.node.position = p
			c.node.reset_physics_interpolation()
			drop_crates.append({"node": c.node, "canopy": c.canopy, "pos": p, "vy": -2.0, "team": f.team, "value": f.value,
				"drift": f.dir * 12.0})
			f.released += 1
		if along > 500.0 or (along > 0.0 and _edge_exit(f.pos, f.dir) < -120.0):
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
			var cv := int(round(c.value * income_mult(c.team)))
			deliver(c.team, cv)
			drop_income[c.team] += cv
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
			_boarding_step(u)
		if u.is_transport() and u.unload_pending and u.domain != "heli" and u.can_exchange():
			u.unload_pending = false
			unload_all(u)


## A "board" order (B3): passengers are taken nearest first up to the free capacity (seats already promised to
## infantry on the way count as taken). The rest walk to the transport and wait next to it, with a message.
func _order_board(cmd: Dictionary) -> void:
	var tr: Unit = by_id.get(cmd.get("target", -1))
	if tr == null or tr.dead: return
	var cand: Array = []
	for id in cmd.get("ids", []):
		var u: Unit = by_id.get(id)
		if u == null or u.dead or u == tr or not tr.accepts(u): continue
		cand.append(u)
	if cand.is_empty(): return
	cand.sort_custom(func(a: Unit, b: Unit) -> bool:
		var da := a.flat_dist(tr.position); var db := b.flat_dist(tr.position)
		if da != db: return da < db
		return a.uid < b.uid)
	var promised := 0
	for o in units:
		if o.board_target == tr and not (o in cand) and not o.dead: promised += 1
	var room: int = tr.capacity_left() - promised
	var slot := promised
	var waiting := 0
	for u in cand:
		if room > 0:
			room -= 1
			u.board_target = tr
			u.board_slot = slot; slot += 1
			u.board_t = 0.0
			_board_go(u, tr, true)
		else:
			u.board_target = null
			u.order_move(_wait_point(u, tr, waiting))
			waiting += 1
	if waiting > 0 and tr.team == 0 and int(cmd.get("team", tr.team)) == 0 and hud:
		hud.flash_message("%s is full - %d waiting outside" % [tr.def.name, waiting])


## Point where an infantryman boards: vehicles at the rear and rear quarters, then the sides (the hatch end, never
## the middle of the hull); a helicopter right under its fuselage; a building at its door or the nearest wall.
func board_point(u: Unit, tr: Unit) -> Vector3:
	var ur := u.body_r()
	if tr is Building:
		var b := tr as Building
		var me := Vector2(u.position.x, u.position.z)
		var at := Vector2(b.door_pos.x, b.door_pos.z) if b.door_pos != Vector3.INF else me
		var p2 := footprint_outside(b, at, ur + 0.6)
		return grounded(Vector3(p2.x, 0, p2.y))
	if tr.domain == "heli":
		return grounded(tr.position)
	var f := tr.forward()
	var rgt := Vector3(-f.z, 0, f.x)
	var hl := tr.half_len(); var hw := tr.half_wid()
	var offs := [Vector2(0, -1), Vector2(-0.8, -0.85), Vector2(0.8, -0.85), Vector2(-1, -0.3), Vector2(1, -0.3), Vector2(-1, 0.3), Vector2(1, 0.3), Vector2(0, -1.5), Vector2(-1, 0.8), Vector2(1, 0.8)]
	var o: Vector2 = offs[u.board_slot % offs.size()]
	var p := tr.position + rgt * o.x * (hw + ur + 0.4) + f * o.y * (hl + ur + 0.4)
	var g: GridNav = navs.get(u.move_class(), gnav)
	if g and g.blocked_at(p):
		for k in offs.size():     # the slot is in a wall or a rock: the first free one around the hull
			var q: Vector2 = offs[k]
			var pq := tr.position + rgt * q.x * (hw + ur + 0.4) + f * q.y * (hl + ur + 0.4)
			if not g.blocked_at(pq): return grounded(pq)
	return grounded(p)


## Clearance (m) between an infantryman's body and the transport: hull rectangle for vehicles, the area under the
## rotor for helicopters, the footprint for buildings.
func board_gap(u: Unit, tr: Unit) -> float:
	var ur := u.body_r()
	if tr is Building:
		var b := tr as Building
		var gd: float = b.footprint_dist(u.position)
		if b.door_pos != Vector3.INF: gd = minf(gd, u.flat_dist(b.door_pos) - 1.0)
		return gd - ur
	if tr.domain == "heli":
		return u.flat_dist(tr.position) - (tr.body_r() * 0.7 + ur)
	var d := u.position - tr.position
	var f := tr.forward()
	var lz := d.x * f.x + d.z * f.z
	var lx := d.x * -f.z + d.z * f.x
	var ex := maxf(0.0, absf(lx) - tr.half_wid())
	var ez := maxf(0.0, absf(lz) - tr.half_len())
	return Vector2(ex, ez).length() - ur


## Walk to the boarding point: grid path while far, a straight approach for the last metres.
func _board_go(u: Unit, tr: Unit, fresh := false) -> void:
	var ap := board_point(u, tr)
	if fresh or u.flat_dist(ap) > 12.0: u.order_move(ap)
	else: u.order_approach(ap)


func _wait_point(u: Unit, tr: Unit, k: int) -> Vector3:
	var away := Vector2(u.position.x - tr.position.x, u.position.z - tr.position.z)
	var a := away.angle() + float(k) * 0.5 if away.length() > 0.1 else float(k) * 0.9
	var p := tr.position + Vector3(cos(a), 0, sin(a)) * (tr.body_r() + u.body_r() + 5.0)
	var g: GridNav = navs.get(u.move_class(), gnav)
	if g and g.blocked_at(p): p = g.center_of(g.nearest_free(g.cell_of(p)))
	return grounded(p)


## Boarding, every tick for each infantryman with a board_target: board on contact (vehicle stopped, helicopter low,
## any building); a ground transport brakes while its passengers are within a few metres (at most ~6 s at a time);
## the approach point is re-aimed as the transport moves; a soldier pressed against a crowded hull for 1.5 s squeezes in.
func _boarding_step(u: Unit) -> void:
	var tr: Unit = u.board_target
	if not is_instance_valid(tr) or tr.dead or not tr.accepts(u):
		u.board_target = null
		return
	if tr.capacity_left() <= 0:
		_board_full(u, tr)
		return
	var gap := board_gap(u, tr)
	var ground_tr: bool = not (tr is Building) and tr.domain == "ground"
	if gap <= (1.5 if tr is Building else 1.2):
		if tr.can_exchange():
			_board(u, tr)
			return
		if ground_tr and tr.hold_sum < 6.0: tr.hold_t = 0.4
	elif gap < 8.0 and ground_tr and tr.hold_sum < 6.0 and tr.speed_cur > 0.3:
		tr.hold_t = 0.4
	if gap < 3.0 and u.speed_cur < 0.5 and tr.can_exchange():
		u.board_t += 1.0 / TICK_HZ
		if u.board_t > 1.5:
			_board(u, tr)
			return
	else:
		u.board_t = 0.0
	if u.state == Unit.S.IDLE or (tick_n + u.uid) % 10 == 0:
		var ap := board_point(u, tr)
		if u.state != Unit.S.MOVE or u.goal.distance_to(ap) > 1.5:
			_board_go(u, tr)


var _full_msg_t := -99.0


func _board_full(u: Unit, tr: Unit) -> void:
	u.board_target = null
	if u.flat_dist(tr.position) < tr.body_r() + 14.0: u.order_stop()
	else: u.order_move(_wait_point(u, tr, u.board_slot))
	if u.team == 0 and hud and sim_time - _full_msg_t > 1.0:
		_full_msg_t = sim_time
		hud.flash_message("%s is full" % tr.def.name)


func _board(u: Unit, tr: Unit) -> void:
	u.board_target = null
	u.set_selected(false)
	if u in commander.selected: commander.selected.erase(u); commander.selection_changed.emit()
	units.erase(u)
	u.visible = false
	u.process_mode = Node.PROCESS_MODE_DISABLED
	if tr is Building and (tr as Building).is_civic() and tr.team != u.team: _set_owner(tr as Building, u.team)
	tr.passengers.append(u)
	if tr.team == 0 and hud:
		var verb := "occupied" if tr is Building else "boarded"
		hud.flash_message("%s %s %s (%d/%d)" % [u.def.name, verb, tr.def.name, tr.passengers.size(), tr.def.transport.capacity])


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
	p.altitude = 0.0
	if p.body: p.body.position.y = 0.0
	p.order_stop()
	p.reset_physics_interpolation()
	units.append(p)
	if tr is Building and (tr as Building).is_civic() and tr.passengers.is_empty(): _set_owner(tr as Building, -1)
	return true


func _lose_passengers(tr: Unit) -> void:
	if tr.team == 0 and hud and not tr.passengers.is_empty():
		hud.flash_message("%s destroyed - %d passengers lost" % [tr.def.name, tr.passengers.size()])
	for p in tr.passengers:
		p.dead = true
		if p.team == 0: losses += 1
		else: kills += 1
		p.queue_free()
	tr.passengers.clear()


# ------------------------------------------------------------------ civilian buildings (garrisons)
## A civic building changes side when the first soldier enters and becomes neutral again when the last leaves.
func _set_owner(b: Building, t: int) -> void:
	b.team = t
	if t == 0:   # the player's fog pass skips own units: make sure the building is shown once we hold it
		b.ever_seen = true; seen[b.uid] = true; b.visible = true
	b.set_selected(false)
	if commander and commander.sel_building == b and t != commander.team: commander.sel_building = null


## Occupants fire from the windows (+15 % range, the building's view) and cannot be hit; a hospital heals them.
const GARRISON_RANGE := 1.15


func _update_garrisons(dt: float) -> void:
	for u in units:
		if not (u is Building) or u.dead or u.passengers.is_empty(): continue
		var b := u as Building
		if not b.is_civic(): continue
		var heal: float = float(b.bdef.get("garrison_heal", 0.0))
		# ordered target (player / AI command) first, then whoever is damaging the building, then free choice
		var gt: Unit = b.gar_target
		if gt and (not is_instance_valid(gt) or gt.dead or gt.team == b.team or gt.team < 0):
			b.gar_target = null; gt = null
		var rt: Unit = b.retaliate
		if rt and (not is_instance_valid(rt) or rt.dead or rt.team == b.team or rt.team < 0 or sim_time - b.retaliate_t > 8.0):
			b.retaliate = null; rt = null
		for i in b.passengers.size():
			var p: Unit = b.passengers[i]
			if heal > 0.0 and p.hp < p.def.hp:
				p.hp = minf(p.def.hp, p.hp + p.def.hp * heal * dt)
			var pp := b.port(i)
			p.position = Vector3(pp.x, ground_h(pp.x, pp.z), pp.z)
			p.altitude = maxf(0.0, pp.y - p.position.y)
			if p.target and (p.target.dead or p.target.team == p.team or p.target.team < 0): p.target = null
			for wi in p.def.weapons.size():
				p.w_reload[wi] = maxf(0.0, float(p.w_reload[wi]) - dt)
			if gt and garrison_reaches(p, pp, gt): p.target = gt
			elif rt and p.target != gt and garrison_reaches(p, pp, rt): p.target = rt
			elif p.target == null and (tick_n + p.uid) % 6 == 0:
				p.target = find_enemy_near_point(p, pp, p.max_range_any() * GARRISON_RANGE)
			if p.target == null: continue
			var d := Vector2(p.target.position.x - pp.x, p.target.position.z - pp.z).length()
			for wi in p.def.weapons.size():
				var w: Dictionary = p.def.weapons[wi]
				if float(p.w_reload[wi]) > 0.0 or not (p.target.domain in w.targets): continue
				if d > float(w.range) * GARRISON_RANGE or d < float(w.get("min_range", 0.0)): continue
				fire(p, w, p.target, p.target.world_center())
				p.w_reload[wi] = float(w.reload) * Veterancy.mult(p, "reload")
				p.last_fire_t = sim_time
			if d > p.max_range_any() * GARRISON_RANGE * 1.2: p.target = null


## True when one of the occupant's weapons can hit t from window port pp (garrison range bonus included).
func garrison_reaches(p: Unit, pp: Vector3, t: Unit) -> bool:
	var d := Vector2(t.position.x - pp.x, t.position.z - pp.z).length()
	for w in p.def.weapons:
		if t.domain in w.targets and d <= float(w.range) * GARRISON_RANGE and d >= float(w.get("min_range", 0.0)): return true
	return false


## Garrison orders: occupants of a held civic building focus a chosen enemy ("garrison_attack") or drop the order.
## The order stays until the target dies (occupants out of reach keep their own targets meanwhile).
func _execute_garrison(cmd: Dictionary) -> void:
	var b: Building = by_id.get(int(cmd.get("id", -1))) as Building
	if b == null or b.dead or not b.is_civic() or b.team != int(cmd.team) or b.passengers.is_empty(): return
	if cmd.type == "garrison_stop":
		b.gar_target = null
		for p in b.passengers: p.target = null
		return
	var t: Unit = by_id.get(int(cmd.get("target", -1)))
	if t == null or t.dead or t.team == b.team or t.team < 0: return
	b.gar_target = t
	var reach := 0
	for i in b.passengers.size():
		var p: Unit = b.passengers[i]
		if garrison_reaches(p, b.port(i), t):
			p.target = t; reach += 1
	if b.team == 0 and hud:
		if reach == 0: hud.flash_message("%s: target out of range - occupants will fire when it comes within reach" % b.def.name)
		else: hud.flash_message("%s: %d of %d occupants engaging" % [b.def.name, reach, b.passengers.size()])


## Occupation flags: each civic building flies the flag of the side holding it. The local player sees the current
## owner while the building is in view, otherwise the last owner they saw (it is ownership information, like the
## building itself, which stays on the map once scouted).
func _update_civic_flags() -> void:
	var reveal_all := "reveal" in args
	for u in units:
		if not (u is Building) or u.dead or not (u as Building).is_civic(): continue
		var b := u as Building
		var t := b.team if not b.passengers.is_empty() else -1
		if t == b.flag_team: continue
		if t == 0 or b.flag_team == 0 or reveal_all or _cell_visible(b.position) or b.flag_team == -9:
			b.set_flag_team(t)


## The building is destroyed: occupants get out hurt (half their health), or die when there is no room.
func _eject_garrison(b: Building) -> void:
	var n := b.passengers.size()
	if n == 0: return
	var out := 0
	for p in b.passengers.duplicate():
		p.hp = maxf(1.0, p.hp * 0.5)
		if unload_one(b, p): out += 1
	var lost := b.passengers.size()
	_lose_passengers(b)
	if hud and b.team == 0: hud.flash_message("%s destroyed - %d got out, %d lost" % [b.def.name, out, lost])


## Map civic building (neutral, built). Placed on flattened ground like any structure; never in the build menu.
var _civic_placed: Array = []


## Finds a fairly level spot near pos for a civic building and levels it (no navigation needed yet).
func _civic_site(k: String, pos: Vector3) -> Vector3:
	var half: Vector2 = BuildingDefs.DEFS[k].size * 0.5
	var p := pos
	if terrain:
		for tries in 30:
			var st := terrain.footprint_stats(p, half)
			var clear := true
			for o in obstacles_2d:
				if absf(o.x - p.x) < half.x + o.z and absf(o.y - p.z) < half.y + o.z: clear = false; break
			# keep supply piles, derricks and other civic sites free (piles are about 16 m across)
			for site in terrain.data.get("supply_piles", []) + terrain.data.get("oil_derricks", []):
				var sp := map_point(site)
				if absf(sp.x - p.x) < half.x + 14.0 and absf(sp.z - p.z) < half.y + 14.0: clear = false; break
			for q in _civic_placed:
				if absf(q.x - p.x) < half.x + 8.0 and absf(q.z - p.z) < half.y + 8.0: clear = false; break
			if st.y <= 14.0 and clear and map_bounds.grow(-20).has_point(Vector2(p.x, p.z)): break
			var a := float(tries) * 2.4
			p = pos + Vector3(cos(a), 0, sin(a)) * (4.0 + tries * 1.5)
	var site := prepare_site(k, p)
	_civic_placed.append(site)
	return site


func add_civic(k: String, pos: Vector3, search := true) -> Building:
	if not BuildingDefs.DEFS.has(k) or not ResourceLoader.exists(str(BuildingDefs.DEFS[k].model3d)): return null
	var p := _civic_site(k, pos) if search else pos
	var b := Building.new()
	add_child(b)
	b.setup_structure(self, k, -1, new_uid(), p, true)
	b.reset_physics_interpolation()
	units.append(b)
	by_id[b.uid] = b
	return b


# ------------------------------------------------------------------ heightfield maps (Zagros Basin and later maps)
## Flattens the footprint of a structure about to be placed (skirted) and returns the grounded position.
var loaded_meta := {}          # meta of the save this battle was rebuilt from
var flatten_log: Array = []     # [[centre with height, half size]] in order: terrain edits made by construction


func prepare_site(k: String, pos: Vector3, yaw := 0.0, sx := 1.0) -> Vector3:
	if terrain == null: return Vector3(pos.x, 0.0, pos.z)
	var half: Vector2 = Building.aabb_half(BuildingDefs.DEFS[k].size * Vector2(0.5 * sx, 0.5), yaw)   # rotated: enclosing box
	var st := terrain.footprint_stats(pos, half)
	terrain.flatten(pos, half + Vector2(2.0, 2.0), st.z, 8.0)
	flatten_log.append([Vector3(pos.x, st.z, pos.z), half + Vector2(2.0, 2.0)])   # replayed when a saved game loads
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
var civic_spawns: Array = []    # [kind, position] placed once navigation exists


func _build_terrain_map() -> void:
	var d: Dictionary = terrain.data
	var per_kind := {}
	var missing := {}
	var house_i := 0
	# civilian buildings first: village houses become garrisonable houses (mirrored pairs get the same type), plus the
	# map's "civic" list. Their ground is levelled now, before props are placed, so props stay grounded.
	if ResourceLoader.exists("res://assets/units3d/civic/civ_house_a/civ_house_a.glb"):
		for pr in d.get("props", []):
			if str(pr.get("kind", pr.get("type", ""))) != "village_house": continue
			civic_spawns.append(["civ_house_b" if (house_i / 2) % 3 == 1 else "civ_house_a", map_point(pr)])
			house_i += 1
		for c in d.get("civic", []): civic_spawns.append([str(c.type), map_point(c)])
		for cs in civic_spawns: cs[1] = _civic_site(cs[0], cs[1])
	for pr in d.get("props", []):
		var kind := str(pr.get("kind", pr.get("type", "")))
		if kind == "village_house" and not civic_spawns.is_empty(): continue
		var pp0 := map_point(pr)
		var inside_civic := false
		for cs in civic_spawns:
			var ch: Vector2 = BuildingDefs.DEFS[cs[0]].size * 0.5 + Vector2(3, 3)
			if absf(pp0.x - cs[1].x) < ch.x and absf(pp0.z - cs[1].z) < ch.y: inside_civic = true; break
		if inside_civic: continue
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
		m.albedo_color = UnitDefs.team_color(e.owner).lightened(0.2) if e.owner >= 0 else Color(0.85, 0.85, 0.82)
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
				var pay := int(round(e.income * income_mult(e.owner)))
				deliver(e.owner, pay)
				derrick_income[e.owner] += pay
				e.paid[e.owner] += pay
			e.phase += dt * 2.4
			# crank turns; the walking beam follows the crank through the pitman (ratio from the model: 1.0 / 2.2)
			if e.crank: (e.crank as Node3D).rotation.x = e.phase
			if e.beam: (e.beam as Node3D).rotation.x = asin(sin(e.phase) / 2.2)


## Nation of a team: "nationN=<id>" on the command line, otherwise the menu choice (U.S. by default).
func nation_of(team: int) -> String:
	if team < 0: return ""
	var k := "nation%d" % team
	if args.has(k): return str(args[k])
	if loaded_meta.has(k): return str(loaded_meta[k])    # a loaded save keeps its armies
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


# ------------------------------------------------------------------ upgrades and battle plans (M8)
var upgrades := [{}, {}]          # team -> {upgrade id: true}
var plan := ["", ""]              # active battle plan per team ("" = none)
var plan_pending := ["", ""]      # plan being switched to
var plan_switch_t := [0.0, 0.0]   # sim time when the pending plan becomes active


func has_upgrade(team: int, id: String) -> bool:
	return team >= 0 and team < 2 and upgrades[team].has(id)


## Who is researching `id` for `team` right now (null if nobody).
func researching_at(team: int, id: String) -> Building:
	for b in structures(team):
		if b.research_id == id: return b
	return null


## "" if `id` can be researched at structure b now, else the reason.
func research_problem(b: Building, id: String) -> String:
	var d: Dictionary = Upgrades.DEFS[id]
	if b.bkind != d.at: return "Researched at the %s" % bname(b.team, d.at)
	if has_upgrade(b.team, id): return "Installed"
	if researching_at(b.team, id): return "Already researching"
	if b.research_id != "": return "This building is researching"
	if not b.built: return "Under construction"
	for r in d.requires:
		if structures(b.team, r).is_empty(): return "Requires " + bname(b.team, r)
	if cash[b.team] < int(d.cost): return "Not enough cash"
	return ""


func complete_upgrade(team: int, id: String) -> void:
	upgrades[team][id] = true
	print("UPGRADE team %d %s t=%.1f" % [team, id, sim_time])
	if team == 0 and hud: hud.flash_message("Research complete: %s" % lbl(team, id, Upgrades.DEFS[id].name))


func plan_problem(team: int, id: String) -> String:
	if not Upgrades.PLANS.has(id): return "Unknown plan"
	if structures(team, "command_center").is_empty(): return "Requires a Command Center"
	if not has_upgrade(team, Upgrades.PLAN_REQUIRES): return "Requires " + lbl(team, Upgrades.PLAN_REQUIRES, Upgrades.DEFS[Upgrades.PLAN_REQUIRES].name)
	if plan[team] == id or plan_pending[team] == id: return "Already selected"
	return ""


func _update_plans() -> void:
	for t in 2:
		if plan_pending[t] != "" and sim_time >= plan_switch_t[t]:
			plan[t] = plan_pending[t]; plan_pending[t] = ""
			if t == 0 and hud: hud.flash_message("Battle plan active: %s" % lbl(t, plan[t], Upgrades.PLANS[plan[t]].name))


func _plan_effect(team: int, key: String) -> float:
	if team < 0 or team > 1 or plan[team] == "": return 1.0
	return float(Upgrades.PLANS[plan[team]].effect.get(key, 1.0))


## Damage-taken multiplier from upgrades and the battle plan (veterancy is applied in Unit.take_damage).
func taken_mult(u: Unit) -> float:
	if u.team < 0 or u.team > 1 or u is Building: return 1.0
	var m := 1.0
	for id in upgrades[u.team]:
		if Upgrades.DEFS[id].effect.has("taken") and Upgrades.applies(id, u): m *= float(Upgrades.DEFS[id].effect.taken)
	if u.domain == "ground": m *= _plan_effect(u.team, "taken")
	return m


## Damage-dealt multiplier from upgrades and the battle plan for shooter against target.
func dealt_mult(shooter: Unit, target: Unit) -> float:
	if shooter == null or not is_instance_valid(shooter) or shooter.team < 0 or shooter.team > 1 or shooter is Building: return 1.0
	var m := 1.0
	if has_upgrade(shooter.team, "guided_munitions") and Upgrades.applies("guided_munitions", shooter) and (target == null or target.domain == "ground"):
		m *= float(Upgrades.DEFS.guided_munitions.effect.dmg_ground)
	if shooter.domain == "ground": m *= _plan_effect(shooter.team, "dmg")
	return m


func sight_mult(team: int) -> float:
	return _plan_effect(team, "sight")


func speed_mult(u: Unit) -> float:
	return _plan_effect(u.team, "speed") if u.domain == "ground" and not (u is Building) else 1.0


func xp_mult(team: int) -> float:
	return float(Upgrades.DEFS.adv_training.effect.xp) if has_upgrade(team, "adv_training") else 1.0


func income_mult(team: int) -> float:
	return float(Upgrades.DEFS.supply_efficiency.effect.income) if has_upgrade(team, "supply_efficiency") else 1.0


# ------------------------------------------------------------------ loitering-munition strike (Iran: Shahed)
## Several one-way drones fly in from the team's map edge at low altitude, spread over the target area, then dive
## and detonate. They are a support-power effect (not units): they cannot be ordered or shot down yet.
var drones: Array = []   # {"node", "pos", "aim", "speed", "alt", "team", "dmg", "splash", "diving"}
var drone_hits := 0


func _launch_drones(team: int, id: String, target: Vector3) -> void:
	var p: Dictionary = UnitDefs.POWERS[id]
	var n := int(p.drones)
	var edge_z := map_bounds.end.y + 80.0 if team == 0 else map_bounds.position.y - 80.0
	for i in n:
		var off := Vector3((i - (n - 1) * 0.5) * 12.0, 0, (i % 2) * 8.0)
		var start := Vector3(target.x * 0.6 + off.x * 2.0, 0, edge_z + (i % 2) * 15.0)
		start.y = ground_h(start.x, start.z) + float(p.altitude)
		var node := Node3D.new()
		add_child(node)
		if ResourceLoader.exists(str(p.model3d)):
			var m: Node3D = (load(p.model3d) as PackedScene).instantiate()
			node.add_child(m)
		node.position = start
		node.reset_physics_interpolation()
		var aim: Vector3 = grounded(target + off)
		drones.append({"node": node, "pos": start, "aim": aim, "speed": float(p.speed), "alt": float(p.altitude), "team": team,
			"dmg": float(p.damage), "splash": float(p.splash), "diving": false})
	SFX.play(self, "jet_flyby", target, -8.0, 1.9)
	FX.target_marker(self, target, 16.0)
	if hud and team == 0: hud.flash_message("%s inbound" % p.name)


func _update_drones(dt: float) -> void:
	for d in drones.duplicate():
		var n: Node3D = d.node
		for pr in n.find_children("Prop*", "Node3D", true, false): (pr as Node3D).rotate_object_local(Vector3.BACK, dt * 40.0)
		var to: Vector3 = d.aim - d.pos
		var flat := Vector2(to.x, to.z).length()
		var gy := ground_h(d.pos.x, d.pos.z)
		var v: Vector3
		if not d.diving and flat < 14.0: d.diving = true      # steep terminal dive so ridges do not catch it short
		if d.diving:
			v = to.normalized() * d.speed * 1.6
		else:
			v = Vector3(to.x, 0, to.z).normalized() * d.speed
			# hold altitude over the terrain, climbing early for ridges up to 2.5 s ahead (look-ahead, as for aircraft)
			var hd := Vector3(to.x, 0, to.z).normalized()
			var ahead := gy
			for k in range(1, 6):
				var q: Vector3 = d.pos + hd * d.speed * 0.5 * k
				ahead = maxf(ahead, ground_h(q.x, q.z) - 4.0 * k)
			v.y = (maxf(gy, ahead) + d.alt - d.pos.y) * 2.0
		d.pos += v * dt
		if not d.diving: d.pos.y = maxf(d.pos.y, ground_h(d.pos.x, d.pos.z) + 8.0)   # terrain-following: clear ridges
		n.position = d.pos
		if v.length() > 0.1: n.look_at(d.pos + v, Vector3.UP)
		if d.diving and (d.pos.y <= ground_h(d.pos.x, d.pos.z) + 0.5 or d.pos.distance_to(d.aim) < 1.5):
			var p: Vector3 = grounded(d.pos)
			FX.explosion(self, p + Vector3(0, 0.3, 0), clampf(d.splash / 6.0, 0.8, 1.8))
			SFX.play(self, "explosion_big", p, 0.0, 1.1)
			bomb_log.append(p)
			drone_hits += 1
			for o in units:
				if o.dead or o.domain == "jet": continue
				var dist := o.world_center().distance_to(p)
				if dist < d.splash: o.take_damage(d.dmg * (1.0 - 0.6 * dist / d.splash), null)
			n.queue_free()
			drones.erase(d)


## Display name in the team's own terminology (structures, upgrades, battle plans, powers).
func lbl(team: int, id: String, fallback: String) -> String:
	return Nations.label(nation_of(team), id, fallback) if team >= 0 and team < 2 else fallback


func bname(team: int, k: String) -> String:
	return lbl(team, k, str(BuildingDefs.DEFS[k].name))


# ================================================================== B3 air operations
# Terrain-safe scripted flight, runway bookkeeping for jets, and the airlift support powers: AC-130 gunship orbit,
# C-17 (Iran: C-130) airborne armour drop, C-5 strategic airlift that lands on the player's own runway.
# In-flight support aircraft and vehicles still being unloaded / under canopy are not saved (as other powers).

## Height a scripted aircraft must be at now so that, climbing at `climb` m/s from here on, it stays `clear` m above
## the terrain along its track for the next `horizon` seconds (centre line and both wingtips at +-half_w).
func terrain_ramp_y(p: Vector3, dir: Vector3, speed: float, clear: float, half_w: float, climb := 12.0, horizon := 10.0) -> float:
	var side := Vector3(-dir.z, 0, dir.x)
	var want := -INF
	var n := 20
	for i in n + 1:
		var t := horizon * float(i) / n
		var q := p + dir * speed * t
		var h := maxf(ground_h(q.x, q.z), maxf(ground_h(q.x + side.x * half_w, q.z + side.z * half_w), ground_h(q.x - side.x * half_w, q.z - side.z * half_w)))
		want = maxf(want, h + clear - climb * t)
	return want


## Next height for a scripted aircraft at cur_y: climb early (up to 18 m/s) to the terrain ramp, descend gently, and
## never below the clearance over the ground right under it.
func fly_terrain_y(p: Vector3, dir: Vector3, speed: float, clear: float, cur_y: float, dt: float, half_w: float) -> float:
	var want := terrain_ramp_y(p, dir, speed, clear, half_w)
	var y := move_toward(cur_y, want, dt * (18.0 if want > cur_y else 6.0))
	return maxf(y, terrain_ramp_y(p, dir, speed, clear, half_w, 0.0, 0.0))


## Height of p above the highest of the terrain under it and under its wingtips.
func clearance(p: Vector3, dir: Vector3, half_w: float) -> float:
	var side := Vector3(-dir.z, 0, dir.x)
	var h := maxf(ground_h(p.x, p.z), maxf(ground_h(p.x + side.x * half_w, p.z + side.z * half_w), ground_h(p.x - side.x * half_w, p.z - side.z * half_w)))
	return p.y - h


## Distance from p along d to the edge of the map rectangle (negative when p is already outside).
func _edge_exit(p: Vector3, d: Vector3) -> float:
	var t := INF
	if absf(d.x) > 1e-4: t = minf(t, ((map_bounds.end.x if d.x > 0.0 else map_bounds.position.x) - p.x) / d.x)
	if absf(d.z) > 1e-4: t = minf(t, ((map_bounds.end.y if d.z > 0.0 else map_bounds.position.y) - p.z) / d.z)
	return t if t != INF else 0.0


## Approach heading through `target`: the base direction turned by up to +-60 deg, whichever track (in from the map
## edge, out past it) crosses the lowest maximum terrain height. Ties keep the smaller turn. Deterministic.
var last_approach := {}         # diagnostics: {"angle", "score", "scores"}

func best_approach(target: Vector3, dir0: Vector3, half_w: float) -> Vector3:
	if terrain == null: return dir0
	var best := dir0
	var best_s := INF
	var scores := {}
	for a in [0.0, -20.0, 20.0, -40.0, 40.0, -60.0, 60.0]:
		var d := dir0.rotated(Vector3.UP, deg_to_rad(a))
		var side := Vector3(-d.z, 0, d.x)
		var d_in := _edge_exit(target, -d)
		var d_out := minf(_edge_exit(target, d), 300.0)
		var top := -INF
		var x := -d_in
		while x <= d_out:
			var q := target + d * x
			for o in [-half_w, 0.0, half_w]:
				top = maxf(top, ground_h(q.x + side.x * o, q.z + side.z * o))
			x += 10.0
		var sc := top + absf(a) * 0.05
		scores[a] = snappedf(top, 0.1)
		if sc < best_s: best_s = sc; best = d
	last_approach = {"angle": rad_to_deg(dir0.signed_angle_to(best, Vector3.UP)), "score": best_s, "scores": scores}
	return best


# ------------------------------------------------------------------ runway bookkeeping
var takeoff_log: Array = []     # {"kind", "uid", "start_from_end", "heading_err", "frac"} (tests / diagnostics)


## True while a scripted aircraft (C-5) has reserved the runway of the airfield whose RunwayStart is rw_start.
func runway_reserved(rw_start: Vector3) -> bool:
	for f in airlifts:
		if f.reserved and is_instance_valid(f.af) and (f.af as Building).runway.size() == 2 and (f.af as Building).runway[0].is_equal_approx(rw_start):
			return true
	return false


func on_takeoff_roll(u: Unit) -> void:
	var tdir := u._takeoff_dir()
	takeoff_log.append({"kind": u.kind, "uid": u.uid, "start_from_end": u.flat_dist(u.rw_end),
		"heading_err": rad_to_deg(absf(wrapf(u.heading - atan2(-tdir.x, -tdir.z), -PI, PI))), "frac": -1.0, "t": sim_time})


func on_liftoff(u: Unit, frac: float) -> void:
	for i in range(takeoff_log.size() - 1, -1, -1):
		if takeoff_log[i].uid == u.uid and takeoff_log[i].frac < 0.0:
			takeoff_log[i].frac = frac
			return


func _update_air_ops(dt: float) -> void:
	_update_gunships(dt)
	_update_airdrops(dt)
	_update_airlifts(dt)
	for g in gun_fx.duplicate():
		if sim_time >= g.t:
			FX.explosion(self, g.p, g.k)
			gun_fx.erase(g)


func _remove_transient(u: Unit) -> void:
	if commander and u in commander.selected:
		commander.selected.erase(u)
		commander.selection_changed.emit()
	units.erase(u)
	by_id.erase(u.uid)
	u.queue_free()


func _team_edge_point(team: int, x: float, margin: float) -> Vector3:
	return Vector3(x, 0, map_bounds.end.y + margin if team == 0 else map_bounds.position.y - margin)


static func _fwd(h: float) -> Vector3:
	return Vector3(-sin(h), 0, -cos(h))


# ------------------------------------------------------------------ AC-130 gunship
# A real temporary unit (domain "jet": anti-air weapons and fighters engage it, it can be shot down). It flies in
# from its side's map edge, orbits the target in a left-hand pylon turn (guns on the left side toward the centre)
# for orbit_time seconds firing its 105 mm howitzer, 40 mm and 25 mm guns at enemies in the area, then leaves.
var gunships: Array = []        # {"u", "c", "r", "h", "phase", "t", "reload", "guns", "dmg0"}
var gun_fx: Array = []          # delayed howitzer / 40 mm impact flashes {"t", "p", "k"}
var gunship_shots := {}         # weapon id -> rounds fired

const GUNSHIP_WEAPONS := [
	{"id": "gunship_25", "gun": 0, "range": 220.0, "reload": 0.15, "damage": 6.0, "splash": 1.2, "proj": "bullet", "speed": 520.0,
		"spread": 2.6, "targets": ["ground"], "prefer": "infantry"},
	{"id": "gunship_40", "gun": 1, "range": 220.0, "reload": 1.0, "damage": 45.0, "splash": 3.0, "proj": "shell", "speed": 320.0,
		"spread": 2.2, "targets": ["ground"], "prefer": "vehicle", "fx": 0.7},
	{"id": "gunship_105", "gun": 2, "range": 220.0, "reload": 3.0, "damage": 180.0, "splash": 6.5, "proj": "shell", "speed": 280.0,
		"spread": 2.4, "targets": ["ground"], "prefer": "vehicle", "fx": 1.4},
]


func _launch_gunship(team: int, id: String, target: Vector3) -> void:
	var p: Dictionary = UnitDefs.POWERS[id]
	var r := float(p.orbit_r)
	var edge := _team_edge_point(team, target.x * 0.6, 0.0)
	var d0 := Vector3(target.x - edge.x, 0, target.z - edge.z).normalized()
	var h0 := atan2(-d0.x, -d0.z)
	var entry := target + Vector3(cos(h0), 0, -sin(h0)) * r          # tangent point: left wing toward the centre
	var start := entry - _fwd(h0) * (_edge_exit(entry, -_fwd(h0)) + 160.0)
	var u := _spawn(str(p.unit), team, start, h0)
	u.heading = h0; u.rotation.y = h0
	u.state = Unit.S.MOVE; u.goal = target                           # never "idle": it does not return fire on its own
	u.speed_cur = float(p.speed); u.airborne = true
	u.vel = _fwd(h0) * float(p.speed)
	u.position.y = terrain_ramp_y(start, _fwd(h0), float(p.speed), float(u.def.altitude) * 0.5, 15.0)
	u.reset_physics_interpolation()
	var guns: Array = []
	for i in 3: guns.append(u.model.find_child("Gun%d" % i, true, false) if u.model else null)
	gunships.append({"u": u, "pos": Vector3(start.x, 0, start.z), "c": grounded(target), "r": r, "h": h0, "entry": entry, "phase": "in", "t": 0.0,
		"reload": [0.0, 0.0, 0.0], "guns": guns, "speed": float(p.speed), "orbit_time": float(p.orbit_time), "area": float(p.area)})
	FX.target_marker(self, target, float(p.area))
	SFX.play(u.body, "jet_flyby", start, 2.0, 0.6, true)
	if hud and team == 0: hud.flash_message("%s inbound" % lbl(team, id, p.name))


func _update_gunships(dt: float) -> void:
	for g in gunships.duplicate():
		var u: Unit = g.u
		if not is_instance_valid(u) or u.dead:
			gunships.erase(g)
			continue
		g.t += dt
		var spd: float = g.speed
		match g.phase:
			"in":
				# own track position (the unit's position may be clamped to the map edge while it is still outside)
				g.pos += _fwd(g.h) * spd * dt
				if (g.entry - g.pos).dot(_fwd(g.h)) <= 0.0:
					g.phase = "orbit"; g.t = 0.0
				u.bank = move_toward(u.bank, 0.0, dt)
			"orbit":
				g.h = wrapf(g.h + spd / float(g.r) * dt, -PI, PI)
				var c: Vector3 = g.c
				var px: float = c.x + cos(g.h) * g.r
				var pz: float = c.z - sin(g.h) * g.r
				g.pos = Vector3(px, 0, pz)
				u.bank = move_toward(u.bank, 0.42, dt * 0.6)
				_gunship_fire(g, dt)
				if g.t >= g.orbit_time: g.phase = "out"; g.t = 0.0
			"out":
				g.pos += _fwd(g.h) * spd * dt
				u.bank = move_toward(u.bank, 0.0, dt * 0.5)
				if _edge_exit(g.pos, _fwd(g.h)) < -150.0 or g.t > 30.0:
					gunships.erase(g)
					_remove_transient(u)
					continue
		u.position.x = g.pos.x; u.position.z = g.pos.z
		u.heading = g.h
		u.rotation.y = g.h
		u.vel = _fwd(g.h) * spd
		u.speed_cur = spd


func _gunship_fire(g: Dictionary, dt: float) -> void:
	var u: Unit = g.u
	for i in GUNSHIP_WEAPONS.size():
		g.reload[i] -= dt
		if g.reload[i] > 0.0: continue
		var w: Dictionary = GUNSHIP_WEAPONS[i]
		var t := _gunship_target(u, g.c, float(g.area), str(w.prefer), i)
		if t == null: continue
		g.reload[i] = float(w.reload)
		var gun: Node3D = g.guns[w.gun]
		u.muzzle = gun
		gunship_shots[w.id] = int(gunship_shots.get(w.id, 0)) + 1
		fire(u, w, t, t.position)
		u.muzzle = null
		if w.has("fx"):
			var s: Dictionary = shots[shots.size() - 1]
			gun_fx.append({"t": sim_time + float(s.left) / float(s.speed), "p": s.aim, "k": float(w.fx)})


## Enemy in the orbit area the gun prefers (infantry for the 25 mm, vehicles / structures for the cannons), spread
## over several targets so the guns do not all fire at one; visible to the gunship's side only.
func _gunship_target(u: Unit, c: Vector3, area: float, prefer: String, salt: int) -> Unit:
	var cand: Array = []
	var other: Array = []
	for o in units:
		if o.dead or o.team == u.team or o.team < 0 or o.domain != "ground": continue
		if Vector2(o.position.x - c.x, o.position.z - c.z).length() > area: continue
		if u.team == 0 and not is_visible_to(0, o) and not (o is Building): continue   # fog applies to the player
		if o is Building and (o as Building).is_civic(): continue
		var inf: bool = o.def.get("visual", "") == "infantry"
		if (prefer == "infantry") == inf: cand.append(o)
		else: other.append(o)
	var pool: Array = cand if not cand.is_empty() else other
	if pool.is_empty(): return null
	pool.sort_custom(func(a, b): return a.uid < b.uid)
	return pool[(tick_n / 15 + salt * 7) % pool.size()]


# ------------------------------------------------------------------ C-17 airborne armour drop
# The transport flies over the target (terrain look-ahead as the supply drop), and drops vehicles on pallets under
# three canopies. On touchdown the canopies detach, the pallet stays as debris and the vehicle becomes a normal unit.
var airdrops: Array = []        # flights {"node", "pos", "dir", "team", "target", "cargo", "dropped", "speed", "alt"}
var pallets: Array = []         # {"u", "rig", "chutes", "y", "vy", "t"}
var airdrop_delivered := [0, 0]


func _launch_airdrop(team: int, id: String, target: Vector3) -> void:
	var p: Dictionary = UnitDefs.POWERS[id]
	var edge := _team_edge_point(team, target.x * 0.6 + 40.0, 0.0)
	var dir := best_approach(target, Vector3(target.x - edge.x, 0, target.z - edge.z).normalized(), 16.0)
	var start: Vector3 = target - dir * (_edge_exit(target, -dir) + 160.0)
	start.y = terrain_ramp_y(start, dir, float(p.speed), float(p.altitude), 16.0) + 10.0
	var node := Node3D.new()
	add_child(node)
	var path := str(p.model3d)
	if path == C130_MODEL: path = c130_model(team)
	if ResourceLoader.exists(path):
		var m: Node3D = (load(path) as PackedScene).instantiate()
		m.scale = Vector3.ONE * UnitDefs.SCALE.aircraft
		node.add_child(m)
	node.position = start
	node.rotation.y = atan2(-dir.x, -dir.z)
	node.reset_physics_interpolation()
	node.set_meta("model", path)
	var cargo: Array = (p.airdrop as Array).map(func(k): return Nations.swap_unit(nation_of(team), str(k)))
	airdrops.append({"node": node, "pos": start, "dir": dir, "team": team, "target": grounded(target), "cargo": cargo, "dropped": 0,
		"speed": float(p.speed), "alt": float(p.altitude), "len": float(p.length) * UnitDefs.SCALE.aircraft, "min_clear": INF})
	FX.target_marker(self, target, 12.0)
	SFX.play(node, "jet_flyby", start, 3.0, 0.65, true)
	if hud and team == 0: hud.flash_message("%s inbound" % lbl(team, id, p.name))


func _update_airdrops(dt: float) -> void:
	for f in airdrops.duplicate():
		for pr in f.node.find_children("Prop*", "Node3D", true, false): (pr as Node3D).rotate_object_local(Vector3.BACK, dt * 30.0)
		f.pos += f.dir * f.speed * dt
		f.pos.y = fly_terrain_y(f.pos, f.dir, f.speed, f.alt, f.pos.y, dt, 16.0)
		f.min_clear = minf(f.min_clear, clearance(f.pos, f.dir, 16.0))
		f.node.position = f.pos
		var along: float = (f.pos - f.target).dot(f.dir)
		var n: int = f.cargo.size()
		while f.dropped < n and along >= -(n - 1) * 5.0 + f.dropped * 10.0:
			var at: Vector3 = f.pos - f.dir * f.len * 0.42 + Vector3(0, -1.0, 0)
			var u := _spawn(f.cargo[f.dropped], f.team, at, atan2(-f.dir.x, -f.dir.z))
			units.erase(u)                                   # under canopy: not yet a unit in play
			u.position = at
			var rig := _pallet_rig(u)
			pallets.append({"u": u, "rig": rig, "y": at.y, "vy": -6.0, "t": 0.0, "drift": f.dir * 8.0, "team": f.team})
			f.dropped += 1
		if along > 200.0 and _edge_exit(f.pos, f.dir) < -150.0:
			f.node.queue_free()
			airdrops.erase(f)
	for pl in pallets.duplicate():
		var u: Unit = pl.u
		if not is_instance_valid(u): pallets.erase(pl); continue
		pl.t += dt
		var term := -5.5 if pl.t > 1.2 else -14.0        # canopies open after ~1 s of free fall
		pl.vy = move_toward(pl.vy, term, dt * (14.0 if pl.vy < term else 6.0))
		pl.drift = pl.drift.move_toward(Vector3.ZERO, 3.0 * dt)
		pl.y += pl.vy * dt
		u.position = Vector3(u.position.x + pl.drift.x * dt, pl.y, u.position.z + pl.drift.z * dt)
		var chutes: Node3D = pl.rig.get_node("Chutes")
		chutes.scale = Vector3.ONE * clampf(pl.t / 1.2, 0.15, 1.0)
		pl.rig.position = u.position
		var gy := ground_h(u.position.x, u.position.z)
		if pl.y <= gy:
			u.position.y = gy
			u.reset_physics_interpolation()
			# touchdown: canopies detach and collapse, the pallet stays, the vehicle drives off as a normal unit
			var keep: Node3D = pl.rig
			chutes.reparent(self)
			_collapse(chutes)
			keep.position = u.position
			_fade_node(keep, 25.0)
			units.append(u)
			u.order_stop()
			FX.impact(self, u.position, false)
			airdrop_delivered[u.team] += 1
			pallets.erase(pl)
			if u.team == 0 and hud: hud.flash_message("%s landed" % u.def.name)


## Pallet under the vehicle and a cluster of three canopies with rigging (procedural, original geometry).
func _pallet_rig(u: Unit) -> Node3D:
	var rig := Node3D.new()
	add_child(rig)
	rig.position = u.position
	var plen := float(u.def.get("length", 6.0)) * UnitDefs.SCALE.vehicle
	var pal := MeshInstance3D.new()
	var bm := BoxMesh.new(); bm.size = Vector3(plen * 0.5, 0.35, plen * 1.05)
	var pm := StandardMaterial3D.new(); pm.albedo_color = Color(0.38, 0.33, 0.24); pm.roughness = 0.9
	bm.material = pm; pal.mesh = bm; pal.position.y = -0.18
	pal.rotation.y = u.heading
	rig.add_child(pal)
	var chutes := Node3D.new(); chutes.name = "Chutes"
	rig.add_child(chutes)
	var cm := StandardMaterial3D.new(); cm.albedo_color = Color(0.44, 0.46, 0.34); cm.roughness = 0.95
	cm.cull_mode = BaseMaterial3D.CULL_DISABLED
	var lm := StandardMaterial3D.new(); lm.albedo_color = Color(0.2, 0.2, 0.18)
	var top := 16.0
	for k in 3:
		var a := TAU * k / 3.0 + 0.4
		var c := Vector3(cos(a) * 4.2, top + (0.6 if k == 1 else 0.0), sin(a) * 4.2)
		var can := MeshInstance3D.new()
		var sm := SphereMesh.new(); sm.radius = 4.4; sm.height = 3.2; sm.is_hemisphere = true; sm.radial_segments = 20; sm.rings = 6
		sm.material = cm
		can.mesh = sm; can.position = c
		chutes.add_child(can)
		var line := MeshInstance3D.new()
		var cyl := CylinderMesh.new(); cyl.top_radius = 0.05; cyl.bottom_radius = 0.05
		var l := c.length()
		cyl.height = l; cyl.material = lm
		line.mesh = cyl
		line.position = c * 0.5
		line.look_at_from_position(c * 0.5, c, Vector3.RIGHT if absf(c.normalized().y) > 0.99 else Vector3.UP)
		line.rotate_object_local(Vector3.RIGHT, PI / 2)
		chutes.add_child(line)
	return rig


func _collapse(n: Node3D) -> void:
	var tw := create_tween()
	tw.tween_property(n, "scale", Vector3(1.4, 0.05, 1.4), 2.5)
	tw.parallel().tween_property(n, "position", n.position + Vector3(4.0, -12.0, 2.0), 2.5)
	tw.tween_callback(n.queue_free)


# ------------------------------------------------------------------ C-5 strategic airlift
# Lands on the caller's own airfield runway in the jets' landing direction ('27' -> '09'), rolls out, opens its nose
# visor and unloads a platoon that drives off the runway's far side, closes up, turns round and takes off toward '27'.
# The runway is reserved from final approach until it has climbed out: jets hold short / hold in orbit, and the
# C-5 itself holds in orbit until no jet is on the runway or taxiing out.
const C5_MODEL := "res://assets/units3d/c5/c5.glb"
const C5_SCALE := 0.45                 # drawn smaller than the other aircraft (0.6) so it fits the stylised runway
var airlifts: Array = []
var airlift_delivered := [0, 0]
var airlift_log: Array = []            # phase changes (tests / diagnostics): [sim_time, phase]


func _launch_airlift(team: int, id: String, target: Vector3) -> void:
	var p: Dictionary = UnitDefs.POWERS[id]
	var af: Building = null
	var bd := INF
	for b in structures(team, "airfield"):
		if (b as Building).runway.size() == 2 and b.position.distance_to(target) < bd:
			bd = b.position.distance_to(target); af = b
	if af == null:
		power_ready[team][id] = sim_time       # nothing to land on: refund the cooldown
		if hud and team == 0: hud.flash_message("%s needs an airfield with a runway" % lbl(team, id, p.name))
		return
	var rs: Vector3 = af.runway[0]; var re: Vector3 = af.runway[1]
	var tdir := Vector3(rs.x - re.x, 0, rs.z - re.z).normalized()
	var hold_c := Vector3(re.x, 0, re.z) - tdir * 300.0
	var edge := _team_edge_point(team, af.position.x, 0.0)
	var d0 := Vector3(hold_c.x - edge.x, 0, hold_c.z - edge.z).normalized()
	var start := hold_c - d0 * (_edge_exit(hold_c, -d0) + 200.0)
	start.y = terrain_ramp_y(start, d0, 50.0, 55.0, 15.0) + 10.0
	var node := Node3D.new()
	add_child(node)
	var m: Node3D = (load(C5_MODEL) as PackedScene).instantiate()
	m.scale = Vector3.ONE * C5_SCALE
	node.add_child(m)
	node.position = start
	node.rotation.y = atan2(-d0.x, -d0.z)
	node.reset_physics_interpolation()
	var cargo: Array = (p.airlift as Array).map(func(k): return Nations.swap_unit(nation_of(team), str(k)))
	airlifts.append({"node": node, "model": m, "nose": m.find_child("NoseDoor", true, false), "exit": m.find_child("CargoExit", true, false),
		"team": team, "af": af, "target": target, "phase": "inbound", "pos": start, "h": atan2(-d0.x, -d0.z), "speed": 50.0, "t": 0.0,
		"cargo": cargo, "spawned": 0, "drivers": [], "reserved": false, "hold_c": hold_c, "door": 0.0, "pivot": 0.0, "id": id})
	airlift_log.append([sim_time, "inbound"])
	SFX.play(node, "jet_flyby", start, 4.0, 0.55, true)
	if hud and team == 0: hud.flash_message("%s inbound to %s" % [lbl(team, id, p.name), bname(team, "airfield")])


## Clearance for the C-5 to start its approach: no jet of this airfield on (or cleared for) the runway or taxiing out.
func _airlift_clear(af: Building) -> bool:
	var rs: Vector3 = af.runway[0]
	for o in units:
		if o.dead or o.domain != "jet" or not o.has_runway or not o.rw_start.is_equal_approx(rs): continue
		if o.uses_runway() or o.taxiing_out(): return false
	return true


func _set_phase(f: Dictionary, ph: String) -> void:
	f.phase = ph; f.t = 0.0
	airlift_log.append([sim_time, ph])


## Turn toward p at up to turn_deg/s and fly forward (horizontal only).
func _c5_steer(f: Dictionary, p: Vector3, turn_deg: float, dt: float) -> void:
	var to := Vector3(p.x - f.pos.x, 0, p.z - f.pos.z)
	var diff := wrapf(atan2(-to.x, -to.z) - f.h, -PI, PI)
	f.h = wrapf(f.h + clampf(diff, -deg_to_rad(turn_deg) * dt, deg_to_rad(turn_deg) * dt), -PI, PI)
	f.pos += _fwd(f.h) * f.speed * dt


func _update_airlifts(dt: float) -> void:
	for f in airlifts.duplicate():
		f.t += dt
		var af: Building = f.af if is_instance_valid(f.af) else null
		var lost := af == null or af.dead
		var re: Vector3 = Vector3.ZERO; var rs := Vector3.ZERO; var tdir := Vector3.FORWARD; var rw_len := 1.0
		if not lost:
			rs = af.runway[0]; re = af.runway[1]
			tdir = Vector3(rs.x - re.x, 0, rs.z - re.z).normalized()
			rw_len = rs.distance_to(re)
		var gy := ground_h(f.pos.x, f.pos.z)
		match f.phase:
			"inbound", "hold":
				if lost: _set_phase(f, "leave"); continue
				f.speed = move_toward(f.speed, 42.0 if f.phase == "inbound" else 36.0, dt * 3.0)
				if f.phase == "inbound":
					_c5_steer(f, f.hold_c, 14.0, dt)
					if Vector2(f.pos.x - f.hold_c.x, f.pos.z - f.hold_c.z).length() < 60.0: _set_phase(f, "hold")
				else:
					if not f.reserved and _airlift_clear(af): f.reserved = true
					if f.reserved:
						# intercept the extended centreline from far enough out (pattern: 36 m/s, 24 deg/s -> turn radius ~86 m)
						var rel := Vector3(f.pos.x - re.x, 0, f.pos.z - re.z)
						var out := -rel.dot(tdir)                              # metres out from the '27' end on the approach side
						var lat := (rel + tdir * out).length()
						var err := absf(wrapf(f.h - atan2(-tdir.x, -tdir.z), -PI, PI))
						if f.get("repos", false) or (out < 120.0 and not (lat < 25.0 and err < deg_to_rad(20.0) and out > 60.0)):
							f["repos"] = out < 650.0                                   # reposition far out on the centreline
							_c5_steer(f, Vector3(re.x, 0, re.z) - tdir * 700.0, 24.0, dt)
						else:
							_c5_steer(f, Vector3(re.x, 0, re.z) - tdir * maxf(out - 220.0, 0.0), 24.0, dt)
						if out < 260.0 and out > 60.0 and lat < 12.0 and err < deg_to_rad(10.0): _set_phase(f, "final")
					else:
						# holding pattern: left-hand circle round the holding point
						var rel := Vector3(f.pos.x - f.hold_c.x, 0, f.pos.z - f.hold_c.z)
						var ang := atan2(rel.z, rel.x) + 0.6
						_c5_steer(f, f.hold_c + Vector3(cos(ang), 0, sin(ang)) * 130.0, 14.0, dt)
				f.pos.y = fly_terrain_y(f.pos, _fwd(f.h), f.speed, 55.0, f.pos.y, dt, 15.0)
			"final":
				var td := Vector3(re.x, 0, re.z) + tdir * 4.0
				var to_td := Vector3(td.x - f.pos.x, 0, td.z - f.pos.z)
				var d := to_td.dot(tdir)
				# glide down the centreline; any lateral error is steered out
				var aim := td - tdir * maxf(d - maxf(d * 0.5, 40.0), 0.0)
				_c5_steer(f, aim if d > 45.0 else td + tdir * 30.0, 10.0, dt)
				f.speed = move_toward(f.speed, clampf(d * 0.25, 22.0, 42.0), dt * 4.0)
				var glide := ground_h(td.x, td.z) + 55.0 * clampf(d / 170.0, 0.0, 1.0)
				var floor_y := terrain_ramp_y(f.pos, _fwd(f.h), f.speed, 10.0, 15.0, 0.0, 0.0) if d > 40.0 else gy
				f.pos.y = maxf(move_toward(f.pos.y, glide, dt * 14.0), floor_y)
				if d <= 1.0:
					f.pos = Vector3(f.pos.x, ground_h(f.pos.x, f.pos.z), f.pos.z)
					f.h = atan2(-tdir.x, -tdir.z)
					_set_phase(f, "rollout")
			"rollout":
				var stop_s := rw_len * 0.45
				var s: float = (f.pos - re).dot(tdir)
				var rem: float = stop_s - s
				f.speed = minf(move_toward(f.speed, 0.0, dt * 11.0), sqrt(2.0 * 11.0 * maxf(rem, 0.0)))
				f.pos += tdir * f.speed * dt
				var lat: Vector3 = (f.pos - re) - tdir * (f.pos - re).dot(tdir); lat.y = 0.0
				f.pos -= lat * minf(1.0, dt * 2.0)
				f.pos.y = ground_h(f.pos.x, f.pos.z)
				if rem < 0.3 or f.speed < 0.05:
					f.speed = 0.0
					_set_phase(f, "open")
			"open":
				f.door = minf(1.0, f.door + dt / 3.0)
				if f.door >= 1.0: _set_phase(f, "unload")
			"unload":
				if lost:
					_set_phase(f, "close")
				elif f.spawned < f.cargo.size() and f.t >= 0.6 + f.spawned * 3.2:
					_c5_unload_one(f, af, tdir)
				_c5_drive(f, dt)
				if f.spawned >= f.cargo.size() and f.drivers.is_empty() and f.t > 2.0: _set_phase(f, "close")
			"close":
				_c5_drive(f, dt)
				f.door = maxf(0.0, f.door - dt / 2.5)
				if f.door <= 0.0 and f.drivers.is_empty(): _set_phase(f, "pivot")
			"pivot":
				# turn round on the runway, nose swinging away from the apron, to take off toward the '27' end
				var want := atan2(tdir.x, tdir.z)                      # heading of -tdir
				var sgn: float = f.get("pivot_sign", 0.0)
				if sgn == 0.0:
					var away := Vector3(0, 0, -1)
					if not lost: away = (af.to_global(Vector3(0, 0, -1)) - af.to_global(Vector3.ZERO)); away.y = 0.0
					sgn = 1.0 if _fwd(f.h + PI / 2).dot(away) > 0.0 else -1.0
					f["pivot_sign"] = sgn
				var diff := wrapf(want - f.h, -PI, PI)
				if absf(diff) < deg_to_rad(1.0):
					f.h = want
					_set_phase(f, "takeoff")
				else:
					f.h = wrapf(f.h + sgn * deg_to_rad(24.0) * dt, -PI, PI)
			"takeoff":
				var dir := _fwd(f.h)
				var s_left := maxf((Vector3(re.x, 0, re.z) - Vector3(f.pos.x, 0, f.pos.z)).dot(dir), 2.0)
				var v_lo := 26.0
				var acc := maxf(3.0, (v_lo * v_lo - f.speed * f.speed) / (2.0 * s_left))
				f.speed = minf(f.speed + acc * dt, v_lo + 1.0)
				f.pos += dir * f.speed * dt
				f.pos.y = ground_h(f.pos.x, f.pos.z)
				if f.speed >= v_lo: _set_phase(f, "climb")
			"climb", "leave":
				var dir := _fwd(f.h)
				f.speed = move_toward(f.speed, 50.0, dt * 4.0)
				f.pos += dir * f.speed * dt
				var want_y := terrain_ramp_y(f.pos, dir, f.speed, 55.0, 15.0)
				f.pos.y = maxf(move_toward(f.pos.y, want_y, dt * (7.0 if want_y > f.pos.y else 3.0)), terrain_ramp_y(f.pos, dir, f.speed, 3.0, 15.0, 0.0, 0.0))
				if f.reserved and (lost or (f.pos - Vector3(re.x, f.pos.y, re.z)).dot(dir) > 40.0):
					f.reserved = false
					airlift_log.append([sim_time, "runway_released"])
				if not f.reserved and _edge_exit(f.pos, dir) < -200.0:
					f.node.queue_free()
					for dv in f.drivers: units.append(dv.u)
					airlifts.erase(f)
					continue
		f.node.position = f.pos
		f.node.rotation.y = f.h
		if f.nose: (f.nose as Node3D).rotation.x = f.door * deg_to_rad(62.0)
		if f.phase in ["rollout", "takeoff"] and f.speed > 8.0 and tick_n % 20 == 0:
			FX.impact(self, f.pos - _fwd(f.h) * 4.0, false)     # tyre smoke / dust


## Next vehicle rolls out of the nose: from the cargo exit, ahead along the runway, then off its far edge (away from
## the apron) and clear of the airfield, where it becomes a normal unit and drives toward the clicked target.
func _c5_unload_one(f: Dictionary, af: Building, tdir: Vector3) -> void:
	var i: int = f.spawned
	var ex: Vector3 = (f.exit as Node3D).global_position if f.exit else f.pos + _fwd(f.h) * 15.0
	ex.y = ground_h(ex.x, ex.z)
	var u := _spawn(f.cargo[i], f.team, ex, f.h)
	units.erase(u)
	u.position = ex
	u.reset_physics_interpolation()
	var away := af.to_global(Vector3(0, 0, -1)) - af.to_global(Vector3.ZERO); away.y = 0.0; away = away.normalized()
	var rl: Vector3 = af.to_local(af.runway[0])
	var edge_off := af.half.y + rl.z + 7.0                       # local z of the runway centreline is -(distance to the back edge)
	var p1 := ex + tdir * (7.0 + 2.0 * i)
	var p2 := p1 + away * (edge_off + 2.0 * (i % 2))
	if gnav and gnav.blocked_at(p2): p2 = gnav.center_of(gnav.nearest_free(gnav.cell_of(p2)))
	f.drivers.append({"u": u, "wps": [p1, p2], "i": 0, "n": i})
	f.spawned += 1


func _c5_drive(f: Dictionary, dt: float) -> void:
	for dv in f.drivers.duplicate():
		var u: Unit = dv.u
		if not is_instance_valid(u): f.drivers.erase(dv); continue
		var wp: Vector3 = dv.wps[dv.i]
		var to := Vector3(wp.x - u.position.x, 0, wp.z - u.position.z)
		var diff := wrapf(atan2(-to.x, -to.z) - u.heading, -PI, PI)
		u.heading = wrapf(u.heading + clampf(diff, -deg_to_rad(100.0) * dt, deg_to_rad(100.0) * dt), -PI, PI)
		u.rotation.y = u.heading
		u.speed_cur = 5.0 * clampf(cos(diff), 0.2, 1.0)
		u.position += _fwd(u.heading) * u.speed_cur * dt
		u.position.y = ground_h(u.position.x, u.position.z)
		if to.length() < 1.2:
			dv.i += 1
			if dv.i >= dv.wps.size():
				f.drivers.erase(dv)
				units.append(u)
				u.speed_cur = 0.0
				var dest: Vector3 = f.target
				if Vector2(dest.x - u.position.x, dest.z - u.position.z).length() > 25.0:
					u.order_move(dest + Vector3((dv.n % 2) * 7.0 - 3.5, 0, (dv.n / 2) * 7.0 - 3.5))
				else:
					u.order_stop()
				airlift_delivered[u.team] += 1


## Loading a save: drop airlift flights, pallets under canopy and vehicles still being unloaded (not saved).
func clear_air_ops() -> void:
	for f in airdrops + airlifts:
		if is_instance_valid(f.node): f.node.queue_free()
		for dv in f.get("drivers", []):
			if is_instance_valid(dv.u): dv.u.queue_free()
	for pl in pallets:
		if is_instance_valid(pl.rig): pl.rig.queue_free()
		if is_instance_valid(pl.u): pl.u.queue_free()
	airdrops.clear(); airlifts.clear(); pallets.clear(); gunships.clear(); gun_fx.clear()

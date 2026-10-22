# Steel Accord - battle: map, navigation, fixed-step simulation, command queue, combat resolution, support powers.
# All gameplay state changes happen in sim_tick() at a fixed 30 Hz; player/AI orders enter through issue()
# and are executed at the start of the next tick and logged with their tick number (replay groundwork).
class_name Battle
extends Node3D

const TICK_HZ := 30
const MAP_HALF := 300.0   # 600 x 600 m: real-world unit sizes need real-world room (aircraft, approaches)
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
var nav_map: RID
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
const FOG_N := 80   # 8 m cells over 640 m; edges are smoothed by linear filtering in the shaders
const FOG_RECT := Rect2(-320, -320, 640, 640)
var fog_img: Image
var fog_tex: ImageTexture
var fog_mini_img: Image
var fog_mini_tex: ImageTexture
var explored := PackedByteArray()
var fog_t := 0.0
var fog_stamps := {}
var bomb_log: Array = []

var camera: RTSCamera
var commander: Commander
var hud: HUD


func _ready() -> void:
	args = _args()
	_init_fog()
	rng.seed = 20261021
	Engine.physics_ticks_per_second = TICK_HZ
	await World.environment(self)
	await World.terrain(self, MAP_HALF + 30.0, 0.0)
	props = World.props()
	_build_map()
	await _bake_nav()
	_spawn_forces()
	for id in UnitDefs.POWERS:
		power_ready[0][id] = 0.0
		power_ready[1][id] = 0.0
	camera = RTSCamera.new()
	camera.bounds = map_bounds.grow(-10)
	add_child(camera)
	camera.focus(Vector3(30, 0, 140.0 if "close" in args else 205.0))
	commander = Commander.new()
	commander.battle = self; commander.camera = camera
	add_child(commander)
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = HUD.new()
	hud.battle = self; hud.commander = commander; hud.camera = camera
	layer.add_child(hud)
	var diff: Dictionary = Game.DIFFICULTY.get(Game.settings.difficulty, Game.DIFFICULTY["Normal"])
	ai = EnemyAI.new(self, 1, 30.0 if _automated() else float(diff.attack_after))
	pause_menu = PauseMenu.new()
	pause_menu.battle = self
	add_child(pause_menu)
	apply_settings()
	hud.flash_message("Enemy armour reported to the north. Destroy all hostile units.")
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
	elif "test" in args:
		var t: Node = load("res://scripts/autotest.gd").new()
		t.battle = self
		add_child(t)


func _automated() -> bool:
	return "test" in args or "airdiag" in args or "evidence" in args


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
	_build_pads()
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
	for q: Vector3 in PAD_POSITIONS:
		if absf(p.x - q.x) < PAD_SIZE * 0.55 and absf(p.z - q.z) < PAD_SIZE * 0.55: return true
	return false


func _in_obstacle(p: Vector3, margin: float) -> bool:
	for o in obstacles_2d:
		if Vector2(p.x - o.x, p.z - o.y).length() < o.z + margin: return true
	return false


func _bake_nav() -> void:
	var nm := NavigationMesh.new()
	nm.agent_radius = 2.5; nm.agent_height = 3.0; nm.agent_max_climb = 0.6; nm.agent_max_slope = 30.0
	nm.cell_size = 0.5; nm.cell_height = 0.25
	var src := NavigationMeshSourceGeometryData3D.new()
	var ground := PlaneMesh.new(); ground.size = map_bounds.size + Vector2(20, 20)
	src.add_mesh(ground, Transform3D.IDENTITY)
	for c in get_children():
		if c is MeshInstance3D and (c as MeshInstance3D).material_override is ShaderMaterial \
				and ((c as MeshInstance3D).material_override as ShaderMaterial).shader == World.ROCK_SHADER:
			if c.scale.x > 1.1:
				src.add_mesh((c as MeshInstance3D).mesh, (c as MeshInstance3D).transform)
	NavigationServer3D.bake_from_source_geometry_data(nm, src)
	var region := NavigationRegion3D.new()
	region.navigation_mesh = nm
	add_child(region)
	nav_map = get_world_3d().navigation_map
	NavigationServer3D.map_set_cell_size(nav_map, 0.5)
	NavigationServer3D.map_set_cell_height(nav_map, 0.25)
	for i in 120:
		await get_tree().physics_frame
		if NavigationServer3D.map_get_iteration_id(nav_map) > 0:
			break
	nav_ready = NavigationServer3D.map_get_iteration_id(nav_map) > 0
	print("NAV polygons=", nm.get_polygon_count(), " ready=", nav_ready)


func find_path(from: Vector3, to: Vector3) -> PackedVector3Array:
	if nav_ready:
		var p := NavigationServer3D.map_get_path(nav_map, from, to, true)
		if p.size() >= 2: return p
	return PackedVector3Array([from, to])


func _spawn_forces() -> void:
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
	u.setup(self, kind, team, units.size() + 1, pos, yaw)
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
			"return": u.order_return()
			"scatter":
				var away := Vector3(u.position.x - cmd.center.x, 0, u.position.z - cmd.center.z)
				if away.length() < 0.5: away = Vector3(rng.randf_range(-1, 1), 0, rng.randf_range(-1, 1))
				u.order_move(u.position + away.normalized() * 14.0)


# ------------------------------------------------------------------ simulation
func _physics_process(dt: float) -> void:
	if units.is_empty(): return
	sim_tick(dt)


func sim_tick(dt: float) -> void:
	for c in pending: _execute(c)
	pending.clear()
	if ai and not game_over: ai.tick(dt)
	for u in units:
		u.sim_tick(dt)
	_separate()
	_update_shots(dt)
	_update_flights(dt)
	_update_bombs(dt)
	_update_debris(dt)
	_update_visibility()
	sim_time += dt
	tick_n += 1
	_check_end()


func _separate() -> void:
	var live := units.filter(func(u): return not u.dead and u.domain != "jet")
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
	var aim: Vector3 = tunit.world_center() if tunit else Vector3(tpos.x, 0.3, tpos.z)
	var dist := from.distance_to(aim)
	if tunit:
		aim += tunit.vel * (dist / float(w.speed))
	var sc: float = float(w.spread) * dist / float(w.range)
	aim += Vector3(rng.randf_range(-sc, sc), rng.randf_range(-sc, sc) * 0.3, rng.randf_range(-sc, sc))
	var dir: Vector3 = (aim - from).normalized()
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
		"homing": w.proj == "missile", "kind": w.proj, "targets": w.targets})


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
			if s.dir.length() > 0.01:
				s.node.look_at(s.pos + s.dir, Vector3.UP if absf(s.dir.y) < 0.99 else Vector3.RIGHT)


func _impact(s: Dictionary, p: Vector3) -> void:
	var t: Unit = s.target
	var direct := false
	if t and is_instance_valid(t) and not t.dead:
		var c := t.world_center()
		direct = c.distance_to(p) < t.def.radius * 1.4 + 1.0
		if direct: t.take_damage(s.dmg * rng.randf_range(0.85, 1.15) * _dmg_mult(s.shooter), s.shooter)
	if diag and s.shooter and s.shooter.team == 0: diag.on_shot(s.shooter, t, p, direct)
	if s.splash > 0.0:
		for o in units:
			if o.dead or o == t or o.domain == "jet": continue
			if o.domain == "heli" and not ("heli" in s.targets): continue
			var d := o.world_center().distance_to(p)
			if d < s.splash:
				o.take_damage(s.dmg * 0.5 * (1.0 - d / s.splash), s.shooter)
	var ground := p.y < 1.5
	if s.kind == "bullet":
		FX.bullet_hit(self, Vector3(p.x, maxf(p.y, 0.1), p.z), direct, s.shooter != null and s.shooter.is_air())
	elif direct or not ground:
		FX.impact(self, p, true)
	else:
		FX.impact(self, Vector3(p.x, 0.1, p.z), false)


# ------------------------------------------------------------------ support powers
func _dmg_mult(shooter: Unit) -> float:
	if shooter == null or shooter.team != 1 or _automated(): return 1.0
	return float(Game.DIFFICULTY.get(Game.settings.difficulty, Game.DIFFICULTY["Normal"]).damage_mult)


func power_cooldown_left(team: int, id: String) -> float:
	return maxf(0.0, float(power_ready[team].get(id, 0.0)) - sim_time)


func launch_power(team: int, id: String, target: Vector3) -> void:
	if power_cooldown_left(team, id) > 0.0: return
	var p: Dictionary = UnitDefs.POWERS[id]
	power_ready[team][id] = sim_time + float(p.cooldown)
	var edge_z := map_bounds.end.y + 120.0 if team == 0 else map_bounds.position.y - 120.0
	var start := Vector3(target.x * 0.7, 0, edge_z)
	var dir := Vector3(target.x - start.x, 0, target.z - start.z).normalized()
	var node := Node3D.new()
	add_child(node)
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
		f.pos += f.dir * float(p.speed) * dt
		f.node.position = f.pos
		var along: float = (f.pos - f.target).dot(f.dir)   # <0 before the target, >0 after
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
		if b.pos.y <= 0.3:
			var p := Vector3(b.pos.x, 0.2, b.pos.z)
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
	if u.team == 0: losses += 1
	else: kills += 1
	if u.domain == "ground":
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
		if u.rotor: u.rotor.visible = false
	if u in commander.selected:
		commander.selected.erase(u)
		commander.selection_changed.emit()
	hud.flash_message(("Enemy %s destroyed" if u.team != 0 else "%s lost") % u.def.name)


func _update_debris(dt: float) -> void:
	for d in debris.duplicate():
		var n: Node3D = d.node
		d.vel.y -= 22.0 * dt
		n.global_position += d.vel * dt
		n.rotation += d.spin * dt
		if n.global_position.y <= 0.4 and d.vel.y < 0:
			n.global_position.y = 0.4
			if d.crash:
				FX.explosion(self, n.global_position, 0.9)
				var sp := n.get_node_or_null("Sprite") as Sprite3D
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
		var vis := false
		for f in units:
			if f.team == 0 and not f.dead and f.flat_dist(u.position) <= f.def.sight:
				vis = true; break
		if not vis:
			for z in reveal_zones:
				if z.team == 0 and _dist_to_segment(u.position, z.a, z.b) < z.w * 0.5:
					vis = true; break
		seen[u.uid] = vis
		u.visible = vis


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

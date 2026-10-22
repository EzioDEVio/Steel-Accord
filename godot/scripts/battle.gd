# Steel Accord - G1 battle: map, navigation, fixed-step simulation, command queue, combat resolution.
# All gameplay state changes happen in sim_tick() at a fixed 30 Hz; player/AI orders enter through issue()
# and are executed at the start of the next tick and logged with their tick number (replay groundwork).
class_name Battle
extends Node3D

const TICK_HZ := 30
const MAP_HALF := 150.0

var map_bounds := Rect2(-MAP_HALF, -MAP_HALF, MAP_HALF * 2, MAP_HALF * 2)
var units: Array[Unit] = []
var by_id := {}
var obstacles_2d: Array[Vector3] = []   # x, z, radius (for minimap/spawn checks)
var rng := RandomNumberGenerator.new()
var sim_time := 0.0
var tick_n := 0
var pending: Array = []
var command_log: Array = []
var shells: Array = []
var debris: Array = []
var seen := {}
var nav_map: RID
var nav_ready := false
var game_over := false
var ai: EnemyAI
var props := {}

var camera: RTSCamera
var commander: Commander
var hud: HUD


func _ready() -> void:
	rng.seed = 20261021
	Engine.physics_ticks_per_second = TICK_HZ
	await World.environment(self)
	await World.terrain(self, 175.0, 0.0)
	props = World.props()
	_build_map()
	await _bake_nav()
	_spawn_forces()
	camera = RTSCamera.new()
	camera.bounds = map_bounds.grow(-10)
	add_child(camera)
	camera.focus(Vector3(0, 0, 105))
	commander = Commander.new()
	commander.battle = self; commander.camera = camera
	add_child(commander)
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = HUD.new()
	hud.battle = self; hud.commander = commander; hud.camera = camera
	layer.add_child(hud)
	ai = EnemyAI.new(self, 1, 30.0)
	hud.flash_message("Enemy armour reported to the north. Destroy all hostile units.")
	if "test" in _args():
		var t: Node = load("res://scripts/autotest.gd").new()
		t.battle = self
		add_child(t)


func _args() -> Dictionary:
	var d := {}
	for a in OS.get_cmdline_user_args():
		var kv := a.split("=")
		d[kv[0]] = kv[1] if kv.size() > 1 else ""
	return d


# ------------------------------------------------------------------ map
func _build_map() -> void:
	# rock outcrops forming three approach lanes, plus scattered boulders
	var outcrops := [Vector3(-62, 0, 0), Vector3(58, 0, -8), Vector3(-10, 0, -55), Vector3(14, 0, 52), Vector3(-110, 0, 70), Vector3(105, 0, -75)]
	var k := 0
	for c in outcrops:
		for i in 7:
			var a := rng.randf() * TAU
			var d := rng.randf_range(0.0, 9.0)
			var s := rng.randf_range(2.6, 5.0)
			var p: Vector3 = c + Vector3(cos(a) * d, 0, sin(a) * d)
			World.rock(self, props["Rock%d" % (k % 6)], p, s, rng.randf() * TAU)
			obstacles_2d.append(Vector3(p.x, p.z, s * 1.4))
			k += 1
	for i in 40:
		var p := Vector3(rng.randf_range(-140, 140), 0, rng.randf_range(-140, 140))
		if absf(p.z) > 95 and absf(p.x) < 50: continue   # keep start areas clear
		var s := rng.randf_range(0.6, 1.6)
		World.rock(self, props["Rock%d" % (i % 6)], p, s, rng.randf() * TAU)
		if s > 1.1: obstacles_2d.append(Vector3(p.x, p.z, s * 1.3))
	for i in 90:
		var p := Vector3(rng.randf_range(-145, 145), 0, rng.randf_range(-145, 145))
		if absf(p.z) > 90 and absf(p.x) < 55: continue
		World.bush(self, props["Bush%d" % (i % 4)], p, rng.randf_range(0.7, 1.6), rng.randf() * TAU,
			Color(0.85, 0.9, 0.8).lerp(Color(1.15, 1.1, 0.85), rng.randf()))
	World.grass(self, Rect2(-160, -160, 320, 320), 160000, rng, func(p): return _in_obstacle(p, 1.0))


func _in_obstacle(p: Vector3, margin: float) -> bool:
	for o in obstacles_2d:
		if Vector2(p.x - o.x, p.z - o.y).length() < o.z + margin: return true
	return false


func _bake_nav() -> void:
	var nm := NavigationMesh.new()
	nm.agent_radius = 2.6; nm.agent_height = 3.0; nm.agent_max_climb = 0.6; nm.agent_max_slope = 30.0
	nm.cell_size = 0.5; nm.cell_height = 0.25
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_MESH_INSTANCES
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
	await get_tree().physics_frame
	await get_tree().physics_frame
	nav_ready = NavigationServer3D.map_get_iteration_id(nav_map) > 0
	print("NAV polygons=", nm.get_polygon_count(), " ready=", nav_ready)


func find_path(from: Vector3, to: Vector3) -> PackedVector3Array:
	if nav_ready:
		var p := NavigationServer3D.map_get_path(nav_map, from, to, true)
		if p.size() >= 2: return p
	return PackedVector3Array([from, to])


func _spawn_forces() -> void:
	for i in 6:
		_spawn("vanguard", 0, Vector3(-20 + (i % 3) * 20, 0, 108 + (i / 3) * 12), 0.0)
	for i in 5:
		_spawn("vanguard", 1, Vector3(-24 + i * 12, 0, -108 - (i % 2) * 10), PI)


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
	var ids: Array = cmd.get("ids", [])
	for i in ids.size():
		var u: Unit = by_id.get(ids[i])
		if u == null or u.dead: continue
		match cmd.type:
			"move": u.order_move(cmd.points[i])
			"attack_move": u.order_attack_move(cmd.points[i])
			"attack":
				var t: Unit = by_id.get(cmd.target)
				if t and not t.dead: u.order_attack(t)
			"stop": u.order_stop()


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
	_update_shells(dt)
	_update_debris(dt)
	_update_visibility()
	sim_time += dt
	tick_n += 1
	_check_end()


func _separate() -> void:
	var live := units.filter(func(u): return not u.dead)
	for i in live.size():
		var a: Unit = live[i]
		for j in range(i + 1, live.size()):
			var b: Unit = live[j]
			var d := Vector2(b.position.x - a.position.x, b.position.z - a.position.z)
			var min_d: float = (a.def.radius + b.def.radius) * 0.95
			var l := d.length()
			if l < min_d and l > 0.001:
				var push := (min_d - l) * 0.5 * d / l
				a.position -= Vector3(push.x, 0, push.y)
				b.position += Vector3(push.x, 0, push.y)
		# keep out of rock outcrops and inside the map
		for o in obstacles_2d:
			var d2 := Vector2(a.position.x - o.x, a.position.z - o.y)
			var r: float = o.z + a.def.radius * 0.6
			if d2.length() < r and d2.length() > 0.001:
				var n := d2.normalized() * r
				a.position = Vector3(o.x + n.x, 0, o.y + n.y)
		a.position.x = clampf(a.position.x, map_bounds.position.x, map_bounds.end.x)
		a.position.z = clampf(a.position.z, map_bounds.position.y, map_bounds.end.y)


func find_enemy_near(u: Unit, r: float) -> Unit:
	var best: Unit = null
	var bd := r
	for o in units:
		if o.dead or o.team == u.team: continue
		var d := u.flat_dist(o.position)
		if d < bd: bd = d; best = o
	return best


func fire_shell(shooter: Unit, target: Unit) -> void:
	var from := shooter.muzzle_pos()
	var dist := from.distance_to(target.global_position)
	var flight: float = dist / shooter.def.proj_speed
	var aim: Vector3 = target.global_position + target.vel * flight + Vector3.UP * 1.3
	var sc: float = shooter.def.spread * dist / shooter.def.range
	aim += Vector3(rng.randf_range(-sc, sc), rng.randf_range(-sc, sc) * 0.4, rng.randf_range(-sc, sc))
	var dir: Vector3 = (aim - from).normalized()
	var mi := FX.tracer_mesh()
	add_child(mi)
	mi.global_position = from
	mi.look_at(from + dir, Vector3.UP)
	mi.reset_physics_interpolation()
	shells.append({"node": mi, "pos": from, "dir": dir, "left": from.distance_to(aim), "speed": shooter.def.proj_speed,
		"shooter": shooter, "target": target, "dmg": shooter.def.damage})
	FX.muzzle_flash(self, from, dir)


func _update_shells(dt: float) -> void:
	for s in shells.duplicate():
		var step: float = s.speed * dt
		if step >= s.left:
			var p: Vector3 = s.pos + s.dir * s.left
			var t: Unit = s.target
			var hit: bool = t != null and is_instance_valid(t) and not t.dead and Vector2(p.x - t.position.x, p.z - t.position.z).length() < t.def.radius * 1.35
			if hit:
				t.take_damage(s.dmg * rng.randf_range(0.85, 1.15), s.shooter)
				FX.impact(self, p, true)
			else:
				FX.impact(self, Vector3(p.x, 0.1, p.z), false)
			s.node.queue_free()
			shells.erase(s)
		else:
			s.pos += s.dir * step
			s.left -= step
			s.node.global_position = s.pos


func on_unit_died(u: Unit) -> void:
	FX.explosion(self, u.global_position, true)
	FX.wreck_fire(u)
	if u.turret:
		var t := u.turret
		var xf := t.global_transform
		t.get_parent().remove_child(t)
		add_child(t)
		t.global_transform = xf
		t.reset_physics_interpolation()
		debris.append({"node": t, "vel": Vector3(rng.randf_range(-3, 3), rng.randf_range(9, 13), rng.randf_range(-3, 3)),
			"spin": Vector3(rng.randf_range(-3, 3), rng.randf_range(-4, 4), rng.randf_range(-3, 3))})
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
			debris.erase(d)


func _update_visibility() -> void:
	for u in units:
		if u.team == 0 or u.dead:
			if u.dead and not seen.get(u.uid, false): u.visible = false
			continue
		var vis := false
		for f in units:
			if f.team == 0 and not f.dead and f.flat_dist(u.position) <= f.def.sight:
				vis = true; break
		seen[u.uid] = vis
		u.visible = vis


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
	elif alive_count(0) == 0:
		game_over = true
		hud.banner = "DEFEAT"; hud.banner_color = Color(1.0, 0.4, 0.35)
		print("RESULT defeat t=%.1f red_left=%d" % [sim_time, alive_count(1)])

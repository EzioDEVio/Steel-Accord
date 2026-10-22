# Steel Accord - battle: map, navigation, fixed-step simulation, command queue, combat resolution, support powers.
# All gameplay state changes happen in sim_tick() at a fixed 30 Hz; player/AI orders enter through issue()
# and are executed at the start of the next tick and logged with their tick number (replay groundwork).
class_name Battle
extends Node3D

const TICK_HZ := 30
const MAP_HALF := 150.0
const PAD_POSITIONS := [Vector3(70, 0, 118), Vector3(88, 0, 118), Vector3(106, 0, 118), Vector3(70, 0, 136), Vector3(88, 0, 136), Vector3(106, 0, 136), Vector3(124, 0, 127)]

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

var camera: RTSCamera
var commander: Commander
var hud: HUD


func _ready() -> void:
	args = _args()
	rng.seed = 20261021
	Engine.physics_ticks_per_second = TICK_HZ
	await World.environment(self)
	await World.terrain(self, 175.0, 0.0)
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
	camera.focus(Vector3(20, 0, 67.0 if "close" in args else 105.0))
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
	if "evidence" in args:
		var ev: Node = load("res://scripts/evidence.gd").new()
		ev.battle = self
		add_child(ev)
	elif "test" in args:
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
		if absf(p.z) > 95 and absf(p.x) < 50: continue
		if p.z > 100 and p.x > 55: continue   # keep the air pads clear
		var s := rng.randf_range(0.6, 1.6)
		World.rock(self, props["Rock%d" % (i % 6)], p, s, rng.randf() * TAU)
		if s > 1.1: obstacles_2d.append(Vector3(p.x, p.z, s * 1.3))
	for i in 90:
		var p := Vector3(rng.randf_range(-145, 145), 0, rng.randf_range(-145, 145))
		if absf(p.z) > 90 and absf(p.x) < 55: continue
		if p.z > 100 and p.x > 55: continue
		World.bush(self, props["Bush%d" % (i % 4)], p, rng.randf_range(0.7, 1.6), rng.randf() * TAU,
			Color(0.85, 0.9, 0.8).lerp(Color(1.15, 1.1, 0.85), rng.randf()))
	_build_pads()
	var tries := 50000 if "lite" in args else 160000
	World.grass(self, Rect2(-160, -160, 320, 320), tries, rng, func(p): return _in_obstacle(p, 1.0) or _on_pad(p))


func _build_pads() -> void:
	var con := StandardMaterial3D.new(); con.albedo_color = Color(0.42, 0.42, 0.40); con.roughness = 0.85
	var mark := StandardMaterial3D.new(); mark.albedo_color = Color(0.85, 0.82, 0.6); mark.roughness = 0.8
	for p: Vector3 in PAD_POSITIONS:
		var slab := MeshInstance3D.new()
		var b := BoxMesh.new(); b.size = Vector3(15, 0.3, 15); b.material = con
		slab.mesh = b; slab.position = p + Vector3(0, 0.1, 0)
		add_child(slab)
		var ring := MeshInstance3D.new()
		var t := TorusMesh.new(); t.inner_radius = 5.0; t.outer_radius = 5.4; t.material = mark
		ring.mesh = t; ring.scale = Vector3(1, 0.02, 1); ring.position = p + Vector3(0, 0.27, 0)
		add_child(ring)


func _on_pad(p: Vector3) -> bool:
	for q: Vector3 in PAD_POSITIONS:
		if absf(p.x - q.x) < 8.5 and absf(p.z - q.z) < 8.5: return true
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
	var zb := 70.0 if "close" in args else 108.0
	var zr := -75.0 if "close" in args else -108.0
	for i in 6:
		_spawn("vanguard", 0, Vector3(-20 + (i % 3) * 20, 0, zb + (i / 3) * 12), 0.0)
	for i in 7:
		_spawn("vanguard", 1, Vector3(-36 + i * 12, 0, zr - (i % 2) * 10), PI)
	# air wing on the pads (south-east). "airshow" adds every controllable aircraft type.
	var wing := ["f16", "f16", "ah64", "a10"]
	if "airshow" in args: wing = ["f16", "fa18", "f22", "a10", "ah64", "uh60", "ch47"]
	if "noair" in args: wing = []
	for i in wing.size():
		var u := _spawn(wing[i], 0, PAD_POSITIONS[i], 0.0)
		if u.domain == "jet":
			u.state = Unit.S.LANDED; u.altitude = 0.4; u.speed_cur = 0.0; u.body.position.y = 0.4


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
		if u.state == Unit.S.LANDED and cmd.type in ["move", "attack_move", "attack", "force_ground", "guard"]:
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
			node = FX.tracer_mesh(0.05, 1.6)
			if shooter.domain == "ground" or rng.randf() < 0.3: FX.small_flash(self, from)
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
		if direct: t.take_damage(s.dmg * rng.randf_range(0.85, 1.15), s.shooter)
	if s.splash > 0.0:
		for o in units:
			if o.dead or o == t or o.domain == "jet": continue
			if o.domain == "heli" and not ("heli" in s.targets): continue
			var d := o.world_center().distance_to(p)
			if d < s.splash:
				o.take_damage(s.dmg * 0.5 * (1.0 - d / s.splash), s.shooter)
	var ground := p.y < 1.5
	if s.kind == "bullet":
		FX.bullet_hit(self, Vector3(p.x, maxf(p.y, 0.1), p.z), direct)
	elif direct or not ground:
		FX.impact(self, p, true)
	else:
		FX.impact(self, Vector3(p.x, 0.1, p.z), false)


# ------------------------------------------------------------------ support powers
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
			FX.explosion(self, p, b.splash > 10.0)
			for o in units:
				if o.dead or o.domain == "jet": continue
				var d := o.world_center().distance_to(p)
				if d < b.splash: o.take_damage(b.dmg * (1.0 - 0.6 * d / b.splash), null)
			b.node.queue_free()
			bombs.erase(b)


# ------------------------------------------------------------------ deaths and visibility
func on_unit_died(u: Unit) -> void:
	if u.domain == "ground":
		FX.explosion(self, u.global_position, true)
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
		FX.explosion(self, u.world_center(), false)
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
				FX.explosion(self, n.global_position, true)
				var sp := n.get_node_or_null("Sprite") as Sprite3D
				if sp: sp.modulate = Color(0.12, 0.11, 0.1)
				FX.wreck_fire(n)
			debris.erase(d)


func _update_visibility() -> void:
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
	elif alive_count(0) == 0:
		game_over = true
		hud.banner = "DEFEAT"; hud.banner_color = Color(1.0, 0.4, 0.35)
		print("RESULT defeat t=%.1f red_left=%d" % [sim_time, alive_count(1)])

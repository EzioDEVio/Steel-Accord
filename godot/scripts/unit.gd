# Steel Accord - a combat unit (ground vehicle). Simulated only from Battle.sim_tick (fixed step).
class_name Unit
extends Node3D

enum S { IDLE, MOVE, ATTACK, ATTACK_MOVE }

var uid := 0
var team := 0
var kind := ""
var def: Dictionary
var hp := 1.0
var battle: Node
var dead := false
var selected := false

var state := S.IDLE
var goal := Vector3.ZERO
var path := PackedVector3Array()
var path_i := 0
var repath_t := 0.0
var target: Unit = null
var forced_target := false

var heading := 0.0          # yaw, radians; forward = -Z rotated by heading
var speed_cur := 0.0
var vel := Vector3.ZERO
var turret_yaw := 0.0
var reload_t := 0.0
var recoil := 0.0

var model: Node3D
var turret: Node3D
var gun: Node3D
var muzzle: Node3D
var ring: MeshInstance3D
var mats: Array = []
var gun_rest := Vector3.ZERO


func setup(b: Node, unit_kind: String, t: int, id: int, pos: Vector3, yaw: float) -> void:
	battle = b; kind = unit_kind; def = UnitDefs.DEFS[unit_kind]; team = t; uid = id
	hp = def.hp
	name = "%s_%d" % [unit_kind, id]
	model = load(def.model).instantiate()
	add_child(model)
	mats = UnitArt.apply(model, def.ao_prefix, UnitDefs.TEAM_COLORS[team], id)
	turret = model.find_child("Turret", true, false) as Node3D
	gun = model.find_child("Gun", true, false) as Node3D
	muzzle = model.find_child("Muzzle", true, false) as Node3D
	if gun: gun_rest = gun.position
	ring = _make_ring()
	add_child(ring)
	position = pos
	heading = yaw
	rotation.y = heading
	_add_contact_shadow()


func _make_ring() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = def.radius * 1.35; t.outer_radius = def.radius * 1.35 + 0.35; t.rings = 40; t.ring_segments = 4
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0.35, 1.0, 0.45) if team == 0 else Color(1.0, 0.3, 0.25)
	m.no_depth_test = false
	t.material = m
	mi.mesh = t
	mi.scale = Vector3(1, 0.04, 1)
	mi.position.y = 0.12
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.visible = false
	return mi


func _add_contact_shadow() -> void:
	var g := GradientTexture2D.new()
	g.fill = GradientTexture2D.FILL_RADIAL; g.fill_from = Vector2(0.5, 0.5); g.fill_to = Vector2(1.0, 0.5)
	var gr := Gradient.new(); gr.set_color(0, Color(0, 0, 0, 0.75)); gr.set_color(1, Color(0, 0, 0, 0))
	g.gradient = gr; g.width = 64; g.height = 64
	var d := Decal.new()
	d.texture_albedo = g; d.size = Vector3(4.6, 2.0, 8.6); d.position = Vector3(0, 0.3, 0)
	d.modulate = Color(1, 1, 1, 0.8)
	add_child(d)


func set_selected(v: bool) -> void:
	selected = v
	if ring: ring.visible = v and not dead


func forward() -> Vector3:
	return Vector3(-sin(heading), 0, -cos(heading))


func flat_dist(p: Vector3) -> float:
	return Vector2(p.x - position.x, p.z - position.z).length()


# ------------------------------------------------------------------ orders (called by Battle when executing commands)
func order_move(p: Vector3) -> void:
	state = S.MOVE; goal = p; target = null; forced_target = false
	_plan(p)


func order_attack_move(p: Vector3) -> void:
	state = S.ATTACK_MOVE; goal = p; target = null; forced_target = false
	_plan(p)


func order_attack(t: Unit) -> void:
	state = S.ATTACK; target = t; forced_target = true
	path = PackedVector3Array(); path_i = 0; repath_t = 0.0


func order_stop() -> void:
	state = S.IDLE; target = null; forced_target = false
	path = PackedVector3Array(); path_i = 0


func _plan(p: Vector3) -> void:
	path = battle.find_path(position, p)
	path_i = 1 if path.size() > 1 else 0
	repath_t = 1.0


# ------------------------------------------------------------------ simulation
func sim_tick(dt: float) -> void:
	if dead: return
	reload_t = maxf(0.0, reload_t - dt)
	if target and (target.dead or not is_instance_valid(target)):
		target = null
		if state == S.ATTACK: state = S.IDLE
		forced_target = false
	if target and not forced_target and flat_dist(target.position) > def.sight * 1.1:
		target = null
	if target == null and state != S.MOVE:
		target = battle.find_enemy_near(self, def.sight if state != S.IDLE else def.range * 1.05)

	var moving := false
	match state:
		S.MOVE:
			moving = true
			if _follow(dt): state = S.IDLE; speed_cur = 0.0
		S.ATTACK_MOVE:
			if target and flat_dist(target.position) > def.range * 0.92:
				moving = true; _chase(dt)
			elif target == null:
				moving = true
				if _follow(dt): state = S.IDLE; speed_cur = 0.0
		S.ATTACK:
			if target and flat_dist(target.position) > def.range * 0.92:
				moving = true; _chase(dt)
		S.IDLE:
			pass
	if not moving:
		speed_cur = move_toward(speed_cur, 0.0, def.accel * 2.0 * dt)
		position += forward() * speed_cur * dt
	vel = forward() * speed_cur
	rotation.y = heading
	_aim_and_fire(dt)
	if gun:
		recoil = move_toward(recoil, 0.0, dt * 1.6)
		gun.position = gun_rest + Vector3(0, 0, recoil)


func _chase(dt: float) -> void:
	repath_t -= dt
	if repath_t <= 0.0 or path_i >= path.size():
		path = battle.find_path(position, target.position)
		path_i = 1 if path.size() > 1 else 0
		repath_t = 1.0
	_follow(dt)


## Follow the current path; returns true when the final point is reached.
func _follow(dt: float) -> bool:
	if path_i >= path.size():
		return true
	var p := path[path_i]
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var last := path_i == path.size() - 1
	if to.length() < (1.5 if last else 3.0):
		path_i += 1
		return path_i >= path.size()
	var want := atan2(-to.x, -to.z)
	var diff := wrapf(want - heading, -PI, PI)
	var step := deg_to_rad(def.turn_deg) * dt
	heading = wrapf(heading + clampf(diff, -step, step), -PI, PI)
	var align := clampf(cos(diff), 0.0, 1.0)
	var target_speed: float = def.speed * align * align
	if last: target_speed = minf(target_speed, maxf(2.0, to.length() * 1.2))
	speed_cur = move_toward(speed_cur, target_speed, def.accel * dt)
	position += forward() * speed_cur * dt
	return false


func _aim_and_fire(dt: float) -> void:
	if turret == null: return
	var want_local := 0.0
	var aiming := false
	if target and flat_dist(target.position) <= def.sight:
		var to := target.position - position
		want_local = wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
		aiming = true
	var diff := wrapf(want_local - turret_yaw, -PI, PI)
	var step := deg_to_rad(def.turret_turn_deg) * dt
	turret_yaw = wrapf(turret_yaw + clampf(diff, -step, step), -PI, PI)
	turret.rotation.y = turret_yaw
	if aiming and absf(diff) < deg_to_rad(3.0) and reload_t <= 0.0 and flat_dist(target.position) <= def.range:
		reload_t = def.reload
		recoil = 0.55
		battle.fire_shell(self, target)


func muzzle_pos() -> Vector3:
	return muzzle.global_position if muzzle else global_position + Vector3.UP * 2.2


func take_damage(amount: float, from: Unit) -> void:
	if dead: return
	hp -= amount
	if hp <= 0.0:
		hp = 0.0
		die()
	elif target == null and from and not from.dead and state != S.MOVE:
		target = from   # return fire


func die() -> void:
	dead = true
	set_selected(false)
	for m in mats:
		(m as ShaderMaterial).set_shader_parameter("burnt", 1.0)
	battle.on_unit_died(self)

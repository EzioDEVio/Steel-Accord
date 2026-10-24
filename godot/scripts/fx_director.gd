# Steel Accord - FX runtime: one node under the Battle that builds every combat effect off the simulation path.
# FX.* calls (often made inside the 30 Hz sim tick) only enqueue a Callable here; _process drains the queue with a
# per-frame budget, recycles particle emitters / lights / decals through pools, enforces the particle, light and
# decal caps of the graphics preset (FX.QUALITY) and thins or skips layers by camera distance and visibility.
# Purely visual: uses randf() (never battle.rng) and never changes gameplay state.
class_name FXDirector
extends Node3D

const POOL_MAX := 160
## Sprite size gain per material: the flipbook puffs / flames fill only part of their quad (look-dev tuned).
const SIZE_GAIN := {"smoke": 1.5, "dust": 1.5, "fire": 1.6, "spark": 1.0, "flash": 1.0}

static var _cur: FXDirector = null

var battle: Node = null
var t := 0.0
var q: Array = []              # [due time, Callable]
var active: Array = []         # emitters / nodes alive: {"n", "stop", "end", "cost", "pool", "tag"}
var lights: Array = []         # {"l", "t0", "dur", "e0", "flicker", "end"}
var decals: Array = []         # {"d", "t0", "life", "a0"}
var pool_p: Array = []
var pool_l: Array = []
var live_particles := 0
var stats := {"spawned": 0, "skipped_cap": 0, "skipped_lod": 0, "ops": 0, "peak_particles": 0, "peak_lights": 0}
var tag_log := {}              # layer tag -> count (tests)
var cam: Camera3D = null
var Q: Dictionary = FX.QUALITY.Medium
var _whistle_t := -99.0


static func get_for(n: Node) -> FXDirector:
	if is_instance_valid(_cur) and _cur.is_inside_tree() and not _cur.is_queued_for_deletion():
		return _cur
	if n == null or not n.is_inside_tree(): return null
	var host := n
	while host and not (host is Battle):
		host = host.get_parent()
	if host == null: host = n.get_tree().current_scene
	if host == null: return null
	var d := FXDirector.new()
	d.name = "FXDirector"
	d.battle = host if host is Battle else null
	host.add_child(d)
	_cur = d
	return d


func _ready() -> void:
	Q = FX.quality()
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF


func _exit_tree() -> void:
	if _cur == self: _cur = null


## Run `c` after `delay` seconds of game time (0 = next frame).
func later(delay: float, c: Callable) -> void:
	q.append([t + delay, c])


func _process(dt: float) -> void:
	t += dt
	Q = FX.quality()
	cam = get_viewport().get_camera_3d()
	# 1. queued effect requests (budgeted; very old visual requests are dropped)
	var budget := int(Q.ops)
	var i := 0
	while i < q.size() and budget > 0:
		var e: Array = q[i]
		if e[0] <= t:
			q.remove_at(i)
			if t - float(e[0]) < 1.0: (e[1] as Callable).call()
			stats.ops += 1
			budget -= 1
		else:
			i += 1
	# 2. emitters: stop, then recycle / free after their particles have died
	i = active.size() - 1
	while i >= 0:
		var a: Dictionary = active[i]
		var n: Variant = a.n
		if not is_instance_valid(n):
			live_particles -= int(a.cost)
			active.remove_at(i)
		elif a.stop >= 0.0 and t >= a.stop:
			if n is CPUParticles3D: (n as CPUParticles3D).emitting = false
			a.stop = -1.0
		elif t >= a.end:
			live_particles -= int(a.cost)
			active.remove_at(i)
			_release(n, a.pool)
		i -= 1
	# 3. light pulses and flickering fires
	i = lights.size() - 1
	while i >= 0:
		var L: Dictionary = lights[i]
		var l: Variant = L.l
		if not is_instance_valid(l):
			lights.remove_at(i)
		else:
			var k := (t - float(L.t0)) / float(L.dur)
			if L.flicker:
				var cool := clampf((float(L.end) - t) / maxf(1.0, float(L.end) - float(L.t0)), 0.0, 1.0)
				l.light_energy = float(L.e0) * cool * (0.75 + 0.25 * sin(t * 13.0 + float(L.t0)) * sin(t * 7.3))
				if t >= float(L.end): lights.remove_at(i); _release_light(l, L.pooled)
			elif k >= 1.0:
				lights.remove_at(i); _release_light(l, L.pooled)
			else:
				l.light_energy = float(L.e0) * pow(1.0 - k, 1.6)
		i -= 1
	# 4. scorch decals fade out at the end of their life
	if Engine.get_process_frames() % 10 == 0:
		i = decals.size() - 1
		while i >= 0:
			var D: Dictionary = decals[i]
			var dn: Variant = D.d
			var age := t - float(D.t0)
			if not is_instance_valid(dn):
				decals.remove_at(i)
			elif age > float(D.life):
				dn.queue_free(); decals.remove_at(i)
			elif age > float(D.life) - 10.0:
				dn.modulate.a = float(D.a0) * (float(D.life) - age) / 10.0
			i -= 1
	stats.peak_particles = maxi(stats.peak_particles, live_particles)
	stats.peak_lights = maxi(stats.peak_lights, lights.size())


# ------------------------------------------------------------------------------------------ LOD and caps
## 0 near, 1 mid, 2 far, 3 off screen.
func lod(pos: Vector3, margin := 6.0) -> int:
	if cam == null: return 0
	var d := cam.global_position.distance_to(pos)
	if not cam.is_position_in_frustum(pos) and not cam.is_position_in_frustum(pos + Vector3.UP * margin):
		return 3
	if d < float(Q.near): return 0
	if d < float(Q.far): return 1
	return 2


## prio 0 essential, 1 normal, 2 detail (not on Low, not far away).
func _count(n: float, prio: int, l: int) -> int:
	if prio >= 2 and (not Q.detail or l >= 2): return 0
	var c: float = n * float(Q.density) * float([1.0, 0.65, 0.4, 0.3][l])
	var room := int(Q.particles) - live_particles
	if room <= 0: return 0
	if c > room: c = room if prio == 0 else room * 0.5
	if c < 1.0 and prio == 0 and c > 0.0: c = 1.0
	return int(round(c))


## Particle count for an emitter attached to a wreck / ruin / falling aircraft, clipped to the remaining budget.
func budget(n: int) -> int:
	return clampi(n, 0, maxi(0, int(Q.particles) - live_particles))


func _acquire_p() -> CPUParticles3D:
	var p: CPUParticles3D
	while not pool_p.is_empty() and p == null:
		var c: Variant = pool_p.pop_back()
		if is_instance_valid(c): p = c
	if p == null:
		p = CPUParticles3D.new()
		p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(p)
	return p


func _release(n: Node, pooled: bool) -> void:
	if not pooled or not is_instance_valid(n) or n.get_parent() != self:
		if is_instance_valid(n): n.queue_free()
		return
	if n is CPUParticles3D and pool_p.size() < POOL_MAX:
		var p := n as CPUParticles3D
		p.emitting = false
		p.visible = false
		pool_p.append(p)
	else:
		n.queue_free()


func _release_light(l: OmniLight3D, pooled: bool) -> void:
	if pooled and pool_l.size() < 32 and l.get_parent() == self:
		l.visible = false
		pool_l.append(l)
	else:
		l.queue_free()


func _log(tag: String) -> void:
	tag_log[tag] = int(tag_log.get(tag, 0)) + 1


## One particle layer. s: mat, n, life, size, vel (Vector2), spread, dir, grav, damp (Vector2), ramp (Gradient),
## curve (Curve), expl, shape ("point" | "sphere" | "box" | "ring"), r, ext, flat, anim ("play" | "random"),
## rot (bool), lrand. Returns null when LOD / caps skip it.
func emit(pos: Vector3, s: Dictionary, prio := 1, l := -1, tag := "") -> CPUParticles3D:
	if l < 0: l = lod(pos)
	var n := _count(float(s.n), prio, l)
	if n < 1:
		stats.skipped_cap += 1
		return null
	var p := _acquire_p()
	var life: float = s.life
	var expl: float = s.get("expl", 0.92)
	p.amount = n
	p.lifetime = life
	p.one_shot = true
	p.explosiveness = expl
	p.randomness = 0.4
	p.lifetime_randomness = s.get("lrand", 0.3)
	p.local_coords = false
	p.fixed_fps = 0
	p.mesh = FX.quad(s.mat)
	var shape: String = s.get("shape", "point")
	match shape:
		"sphere": p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE; p.emission_sphere_radius = s.get("r", 1.0)
		"box": p.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX; p.emission_box_extents = s.get("ext", Vector3.ONE)
		"ring":
			p.emission_shape = CPUParticles3D.EMISSION_SHAPE_RING
			p.emission_ring_axis = Vector3.UP; p.emission_ring_height = 0.2
			p.emission_ring_radius = s.get("r", 1.0); p.emission_ring_inner_radius = float(s.get("r", 1.0)) * 0.6
		_: p.emission_shape = CPUParticles3D.EMISSION_SHAPE_POINT
	p.direction = s.get("dir", Vector3.UP)
	p.spread = s.get("spread", 30.0)
	p.flatness = s.get("flat", 0.0)
	var v: Vector2 = s.get("vel", Vector2(1, 3))
	p.initial_velocity_min = v.x; p.initial_velocity_max = v.y
	p.gravity = s.get("grav", Vector3(0, 1.0, 0))
	var dm: Vector2 = s.get("damp", Vector2(1, 2))
	p.damping_min = dm.x; p.damping_max = dm.y
	var sz: float = float(s.size) * float(SIZE_GAIN.get(s.mat, 1.0))
	p.scale_amount_min = sz * 0.7; p.scale_amount_max = sz * 1.3
	p.scale_amount_curve = s.get("curve", null)
	p.color_ramp = s.ramp
	p.color = Color.WHITE
	var anim: String = s.get("anim", "random")
	if anim == "play":
		p.anim_speed_min = 1.0; p.anim_speed_max = 1.0; p.anim_offset_min = 0.0; p.anim_offset_max = 0.12
	else:
		p.anim_speed_min = 0.0; p.anim_speed_max = 0.0; p.anim_offset_min = 0.0; p.anim_offset_max = 1.0
	var billboard: bool = s.mat != "debris"
	p.angle_min = 0.0 if not billboard else -180.0; p.angle_max = 0.0 if not billboard else 180.0
	p.angular_velocity_min = -30.0 if billboard else 0.0; p.angular_velocity_max = 30.0 if billboard else 0.0
	p.particle_flag_rotate_y = s.get("rot", false)
	p.particle_flag_align_y = false
	p.visible = true
	p.global_position = pos
	p.restart()
	p.emitting = true
	live_particles += n
	active.append({"n": p, "stop": -1.0, "end": t + life * (2.0 - expl) + 0.15, "cost": n, "pool": true})
	stats.spawned += 1
	if tag != "": _log(tag)
	return p


## Light pulse that fades out over `dur`. prio 2 lights are skipped on Low.
func light(pos: Vector3, energy: float, rng: float, dur: float, col := Color(1.0, 0.62, 0.28), prio := 1, tag := "light") -> OmniLight3D:
	if lights.size() >= int(Q.lights):
		stats.skipped_cap += 1
		return null
	if prio >= 2 and not Q.detail: return null
	var l: OmniLight3D = null
	while not pool_l.is_empty() and l == null:
		var c: Variant = pool_l.pop_back()
		if is_instance_valid(c): l = c
	if l == null:
		l = OmniLight3D.new()
		l.shadow_enabled = false
		add_child(l)
	l.visible = true
	l.light_color = col; l.light_energy = energy; l.omni_range = rng; l.omni_attenuation = 1.4
	l.global_position = pos
	lights.append({"l": l, "t0": t, "dur": dur, "e0": energy, "flicker": false, "pooled": true})
	_log(tag)
	return l


## Scorch / blast decal (ring buffer: the oldest is reused when the preset cap is reached).
func decal(pos: Vector3, size: float, kind := "scorch") -> Decal:
	var dn: Decal = null
	if decals.size() >= int(Q.decals):
		var old: Dictionary = decals.pop_front()
		if is_instance_valid(old.d): dn = old.d
	if dn == null:
		dn = Decal.new()
		dn.cull_mask = 1
		add_child(dn)
	dn.texture_albedo = FX.tex(kind)
	dn.size = Vector3(size, maxf(3.0, size * 0.5), size)
	dn.rotation = Vector3(0, randf() * TAU, 0)
	dn.global_position = pos
	dn.upper_fade = 0.3; dn.lower_fade = 0.3
	var a := randf_range(0.8, 1.0)
	dn.modulate = Color(1, 1, 1, a)
	dn.albedo_mix = 1.0
	decals.append({"d": dn, "t0": t, "life": float(Q.decal_life) * randf_range(0.8, 1.2), "a0": a})
	_log("scorch")
	return dn


## Keep a node alive (already under some parent) until `life`; counts its particles against the cap.
func adopt(n: Node3D, life: float, stop := 0.0) -> void:
	var xf := n.global_transform
	if n.get_parent() != self:
		n.get_parent().remove_child(n)
		add_child(n)
		n.global_transform = xf
	var cost := (n as CPUParticles3D).amount if n is CPUParticles3D else 0
	if stop <= 0.0 and n is CPUParticles3D: (n as CPUParticles3D).emitting = false
	live_particles += cost
	active.append({"n": n, "stop": t + stop if stop > 0.0 else -1.0, "end": t + life, "cost": cost, "pool": false})


## Track an emitter that stays attached to `host` (wreck, ruin): it stops emitting at `stop` and is freed at `end`.
func track(n: Node, stop: float, end: float) -> void:
	var cost := (n as CPUParticles3D).amount if n is CPUParticles3D else 0
	live_particles += cost
	active.append({"n": n, "stop": t + stop, "end": t + end, "cost": cost, "pool": false})


func ground_at(pos: Vector3) -> float:
	return battle.ground_h(pos.x, pos.z) if battle else 0.0


func shake(pos: Vector3, amount: float) -> void:
	if amount <= 0.0 or battle == null or not bool(Game.settings.get("camera_shake", true)): return
	if battle._automated() and not ("shake" in battle.args): return
	var c: Node = battle.get("camera")
	if c == null or not c.has_method("add_shake"): return
	var d := Vector2(c.global_position.x - pos.x, c.global_position.z - pos.z).length()
	c.add_shake(amount * clampf(1.0 - d / 260.0, 0.0, 1.0))
	_log("shake")


# ------------------------------------------------------------------------------------------ explosions
func explosion(pos: Vector3, size: String, k := 1.0, sound := true) -> void:
	var c: Dictionary = FX.SIZES[size]
	var r: float = float(c.r) * k
	var sr := sqrt(r)
	var l := lod(pos, 10.0 + r * 4.0)
	var gy := ground_at(pos)
	var on_ground := pos.y - gy < 3.0 + r
	if sound:
		SFX.play(self, "explosion_big", pos, {"small": -12.0, "medium": -6.0, "large": -2.0, "huge": 2.0}[size],
			{"small": 1.55, "medium": 1.3, "large": 1.05, "huge": 0.85}[size] * randf_range(0.94, 1.06))
	if on_ground: decal(Vector3(pos.x, gy, pos.z), float(c.scorch) * k * randf_range(0.85, 1.15))
	if l == 3:
		# off screen: only the smoke column of a big blast can drift into view
		stats.skipped_lod += 1
		if size in ["large", "huge"]: later(0.1, emit.bind(pos + Vector3.UP * r, _blast_smoke(c, r, sr), 0, 2, "smoke"))
		return
	# flash: light pulse + a white-hot star for a frame or two
	light(pos + Vector3.UP * r, float(c.light[0]) * k, float(c.light[1]) * k, 0.25 + 0.12 * r, Color(1.0, 0.66, 0.32), 1 if size != "small" else 2)
	emit(pos + Vector3.UP * r * 0.5, {"mat": "flash", "n": 2 + int(r), "life": 0.12, "size": r * 2.6, "vel": Vector2(0, 0.5), "spread": 180.0,
		"grav": Vector3.ZERO, "ramp": FX.ramp("flash"), "expl": 1.0, "lrand": 0.0}, 0, l, "flash")
	# fireball: flipbook fire expanding and rising
	emit(pos + Vector3.UP * r * 0.45, {"mat": "fire", "n": c.fire, "life": 0.75 + 0.18 * sr, "size": r * 1.5, "vel": Vector2(1.0, 4.0) * sr, "spread": 80.0,
		"grav": Vector3(0, 3.0 * sr, 0), "damp": Vector2(2.0, 4.0), "shape": "sphere", "r": r * 0.45, "anim": "play",
		"ramp": FX.ramp("fireball"),
		"curve": FX.curve("fireball"), "expl": 0.95, "lrand": 0.35}, 0, l, "fireball")
	# smoke column rolling up out of the fireball (starts a moment later, fire-lit at first)
	later(0.1, emit.bind(pos + Vector3.UP * r * 0.7, _blast_smoke(c, r, sr), 0, l, "smoke"))
	# sparks and embers
	emit(pos + Vector3.UP * r * 0.4, {"mat": "spark", "n": c.sparks, "life": 0.7 + 0.2 * sr, "size": 0.22 * sr, "vel": Vector2(9.0, 22.0) * sr, "spread": 85.0,
		"grav": Vector3(0, -14, 0), "damp": Vector2(0.5, 1.5), "ramp": FX.ramp("sparks"),
		"expl": 1.0, "lrand": 0.5}, 1, l, "sparks")
	if int(c.embers) > 0:
		emit(pos + Vector3.UP * r, {"mat": "spark", "n": c.embers, "life": 2.6, "size": 0.18 * sr, "vel": Vector2(2.0, 6.0) * sr, "spread": 70.0,
			"grav": Vector3(0.6, 0.8, 0.2), "damp": Vector2(0.8, 1.6), "ramp": FX.ramp("embers"),
			"expl": 0.8, "lrand": 0.5}, 2, l, "embers")
	# debris chunks thrown out and falling back
	if int(c.debris) > 0 and on_ground:
		emit(pos + Vector3.UP * 0.4, {"mat": "debris", "n": c.debris, "life": 1.3, "size": 0.28 * sr, "vel": Vector2(7.0, 15.0) * sr, "spread": 55.0,
			"grav": Vector3(0, -24, 0), "damp": Vector2(0.1, 0.3), "rot": true, "ramp": FX.ramp("debris"),
			"curve": FX.curve("debris"), "expl": 1.0, "lrand": 0.2}, 1, l, "debris")
	# ground dust ring racing outward, and a low dust skirt
	if on_ground:
		var gp := Vector3(pos.x, gy + 0.4, pos.z)
		if int(c.ring) > 0:
			emit(gp, {"mat": "dust", "n": c.ring, "life": 1.8 + 0.3 * sr, "size": r * 1.3, "vel": Vector2(7.0, 13.0) * sr, "spread": 180.0, "flat": 1.0,
				"dir": Vector3(1, 0, 0), "grav": Vector3(0, 0.5, 0), "damp": Vector2(5.0, 7.0), "shape": "ring", "r": r * 0.4,
				"ramp": FX.ramp("dust_ring"),
				"curve": FX.curve("dust_grow"), "expl": 1.0, "lrand": 0.3}, 1, l, "dust_ring")
		emit(gp, {"mat": "dust", "n": c.dust, "life": 2.6 + 0.4 * sr, "size": r * 1.5, "vel": Vector2(1.5, 5.0) * sr, "spread": 60.0,
			"grav": Vector3(0.5, 0.6, 0.2), "damp": Vector2(1.5, 3.0), "shape": "sphere", "r": r * 0.6,
			"ramp": FX.ramp("dust"),
			"curve": FX.curve("dust_grow"), "expl": 0.9, "lrand": 0.3}, 0 if size == "small" else 1, l, "dust")
		if c.get("shock", false) or (size == "large" and Q.detail and l <= 1): _shock_ring(gp, r * (6.0 if c.get("shock", false) else 3.5))
	shake(pos, float(c.shake) * k)


func _blast_smoke(c: Dictionary, r: float, sr: float) -> Dictionary:
	return {"mat": "smoke", "n": c.smoke, "life": c.smoke_life, "size": r * 1.9, "vel": Vector2(1.2, 3.6) * sr,
		"spread": 28.0, "grav": Vector3(0.7, 1.6 * sr, 0.25), "damp": Vector2(0.8, 1.6), "shape": "sphere", "r": r * 0.5,
		"ramp": FX.ramp("blast_smoke"), "curve": FX.curve("smoke_grow"), "expl": 0.55, "lrand": 0.3}


func _shock_ring(pos: Vector3, radius: float) -> void:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new(); pm.size = Vector2(2, 2)
	var m := (FX.mat("ring") as StandardMaterial3D).duplicate() as StandardMaterial3D
	m.vertex_color_use_as_albedo = false
	m.albedo_color = Color(0.85, 0.8, 0.7, 0.55)
	pm.material = m
	mi.mesh = pm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.global_position = pos + Vector3.UP * 0.6
	mi.scale = Vector3.ONE * radius * 0.15
	var tw := mi.create_tween().set_parallel(true)
	tw.tween_property(mi, "scale", Vector3(radius, 1, radius), 0.45).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	tw.tween_property(m, "albedo_color:a", 0.0, 0.45).set_ease(Tween.EASE_IN)
	tw.chain().tween_callback(mi.queue_free)
	_log("shock")


# ------------------------------------------------------------------------------------------ impacts
func impact(pos: Vector3, kind: String, surface: String) -> void:
	match kind:
		"bomb": explosion(pos, "large", 1.0); return
		"arty":
			if surface == "armour": _armour_hit(pos, 1.4)
			explosion(pos, "large", 0.85); return
		"shell", "rocket":
			if surface == "armour" or surface == "air":
				_armour_hit(pos, 1.0)
				explosion(pos, "small", 1.1, true)
			else:
				explosion(pos, "medium", 0.95 if kind == "shell" else 1.0)
				if surface == "structure": _chips(pos, 1.6)
			return
	var l := lod(pos, 3.0)
	if l == 3:
		stats.skipped_lod += 1
		return
	var heavy := kind == "cannon"
	var hs := 1.8 if heavy else 1.0
	match surface:
		"armour", "air":
			emit(pos, {"mat": "spark", "n": 7 * hs, "life": 0.3, "size": 0.2 * hs, "vel": Vector2(5.0, 13.0), "spread": 75.0, "grav": Vector3(0, -12, 0),
				"damp": Vector2(0.5, 1.0), "ramp": FX.ramp("sparks"), "expl": 1.0, "lrand": 0.4}, 0, l, "spark_hit")
			emit(pos, {"mat": "flash", "n": 1, "life": 0.06, "size": 0.7 * hs, "vel": Vector2.ZERO, "spread": 0.0, "grav": Vector3.ZERO,
				"ramp": FX.ramp("flash"), "expl": 1.0, "lrand": 0.0}, 1, l, "flash")
			if heavy: light(pos + Vector3.UP, 2.5, 7.0, 0.1, Color(1, 0.7, 0.35), 2)
		"structure":
			_chips(pos, hs)
		_:
			var gy := ground_at(pos)
			var gp := Vector3(pos.x, maxf(pos.y, gy + 0.1), pos.z)
			emit(gp, {"mat": "dust", "n": (5 if heavy else 3), "life": 1.1 * hs, "size": 0.9 * hs, "vel": Vector2(1.5, 5.0) * hs, "spread": 25.0,
				"grav": Vector3(0.3, -1.5, 0.1), "damp": Vector2(1.5, 3.0), "ramp": FX.ramp("puff"),
				"curve": FX.curve("dust_grow"), "expl": 1.0, "lrand": 0.3}, 0, l, "dust_hit")
			if heavy:
				emit(gp, {"mat": "debris", "n": 4, "life": 0.7, "size": 0.12, "vel": Vector2(4.0, 9.0), "spread": 35.0, "grav": Vector3(0, -22, 0),
					"damp": Vector2(0.1, 0.2), "rot": true, "ramp": FX.ramp("debris"), "curve": FX.curve("debris"), "expl": 1.0, "lrand": 0.2}, 2, l, "debris")
				emit(gp, {"mat": "spark", "n": 4, "life": 0.25, "size": 0.25, "vel": Vector2(3.0, 9.0), "spread": 60.0, "grav": Vector3(0, -10, 0),
					"ramp": FX.ramp("sparks"), "expl": 1.0, "lrand": 0.4}, 2, l, "spark_hit")
				light(gp + Vector3.UP, 2.0, 6.0, 0.08, Color(1, 0.7, 0.35), 2)


func _armour_hit(pos: Vector3, s: float) -> void:
	var l := lod(pos, 4.0)
	emit(pos, {"mat": "spark", "n": 16 * s, "life": 0.45, "size": 0.26, "vel": Vector2(7.0, 18.0) * s, "spread": 80.0, "grav": Vector3(0, -14, 0),
		"damp": Vector2(0.5, 1.0), "ramp": FX.ramp("sparks"), "expl": 1.0, "lrand": 0.4}, 0, l, "spark_hit")
	light(pos + Vector3.UP * 0.5, 6.0 * s, 10.0, 0.18, Color(1, 0.75, 0.4), 1)


func _chips(pos: Vector3, s: float) -> void:
	var l := lod(pos, 4.0)
	emit(pos, {"mat": "debris", "n": 5 * s, "life": 0.8, "size": 0.12 * s, "vel": Vector2(4.0, 9.0), "spread": 70.0, "grav": Vector3(0, -22, 0),
		"damp": Vector2(0.1, 0.2), "rot": true, "ramp": FX.ramp("chips"),
		"curve": FX.curve("debris"), "expl": 1.0, "lrand": 0.2}, 1, l, "chips")
	emit(pos, {"mat": "dust", "n": 3 * s, "life": 1.4, "size": 1.0 * s, "vel": Vector2(1.0, 3.0), "spread": 60.0, "grav": Vector3(0.2, -0.5, 0.1),
		"damp": Vector2(1.5, 3.0), "ramp": FX.ramp("concrete_dust"),
		"curve": FX.curve("dust_grow"), "expl": 1.0, "lrand": 0.3}, 0, l, "dust_hit")


# ------------------------------------------------------------------------------------------ weapons
func muzzle(pos: Vector3, dir: Vector3, kind: String) -> void:
	var c: Dictionary = FX.MUZZLE.get(kind, FX.MUZZLE.mg)
	var l := lod(pos, 3.0)
	if l == 3:
		stats.skipped_lod += 1
		return
	var f: float = c.flash
	var fwd := dir.normalized() if dir.length() > 0.01 else Vector3.FORWARD
	emit(pos + fwd * f * 0.3, {"mat": "flash", "n": 2 if f < 2.0 else 4, "life": 0.07 if f < 2.0 else 0.12, "size": f, "vel": Vector2(f * 2.0, f * 5.0),
		"spread": 10.0, "dir": fwd, "grav": Vector3.ZERO, "damp": Vector2(8, 10), "ramp": FX.ramp("flash"), "expl": 1.0, "lrand": 0.0}, 0, l, "muzzle_flash")
	if float(c.light) > 0.0:
		light(pos + fwd * 0.5, float(c.light), 4.0 + f * 3.0, 0.08 + f * 0.03, Color(1.0, 0.7, 0.35), 1 if f >= 1.5 else 2)
	if int(c.smoke) > 0:
		var big := f >= 3.0
		emit(pos + fwd * f * 0.4, {"mat": "smoke", "n": c.smoke, "life": 1.6 if not big else 3.2, "size": f * (0.55 if not big else 0.9),
			"vel": Vector2(1.0, 4.0) * (1.0 if not big else 2.2), "spread": 50.0 if not big else 85.0, "dir": fwd, "grav": Vector3(0.3, 0.7, 0.1),
			"damp": Vector2(2.0, 4.0), "ramp": FX.ramp("gunsmoke"),
			"curve": FX.curve("smoke_grow"), "expl": 0.95, "lrand": 0.3}, 1 if big else 2, l, "muzzle_smoke")
	if int(c.ring) > 0:
		var gy := ground_at(pos)
		emit(Vector3(pos.x, gy + 0.3, pos.z) + fwd * 2.0, {"mat": "dust", "n": c.ring, "life": 1.6, "size": f * 0.7, "vel": Vector2(6.0, 11.0), "spread": 180.0,
			"flat": 1.0, "dir": Vector3(1, 0, 0), "grav": Vector3(0, 0.4, 0), "damp": Vector2(4.0, 6.0), "shape": "ring", "r": 1.5,
			"ramp": FX.ramp("dust_ring"), "curve": FX.curve("dust_grow"), "expl": 1.0, "lrand": 0.3}, 1, l, "muzzle_ring")
	if kind == "rocket":
		# AT launcher back-blast: flash and a cone of smoke and dust out of the rear of the tube
		var back := pos - fwd * 1.4
		emit(back, {"mat": "flash", "n": 2, "life": 0.1, "size": 1.6, "vel": Vector2(4.0, 8.0), "spread": 12.0, "dir": -fwd, "grav": Vector3.ZERO,
			"ramp": FX.ramp("flash"), "expl": 1.0, "lrand": 0.0}, 0, l, "backblast")
		emit(back, {"mat": "dust", "n": 12, "life": 1.8, "size": 1.4, "vel": Vector2(6.0, 14.0), "spread": 22.0, "dir": -fwd, "grav": Vector3(0.2, 0.3, 0.1),
			"damp": Vector2(3.0, 5.0), "ramp": FX.ramp("gunsmoke"), "curve": FX.curve("dust_grow"), "expl": 0.95, "lrand": 0.3}, 1, l, "backblast")


func whistle(pos: Vector3) -> void:
	if t - _whistle_t < 2.0: return
	_whistle_t = t
	SFX.play(self, "bomb_fall", pos, -10.0, 1.6)
	_log("whistle")


func build_ruin(root: Node3D, bkind: String, half: Vector2, seed_id: int, age: float) -> void:
	FXRuin.build(self, root, bkind, half, seed_id, age)
	_log("ruin")


# ------------------------------------------------------------------------------------------ deaths and wrecks
func unit_death(u: Node) -> void:
	if not is_instance_valid(u): return
	var vis: String = str(u.def.get("visual", "model"))
	var pos: Vector3 = u.global_position
	if vis == "infantry":
		emit(pos + Vector3.UP * 0.3, {"mat": "dust", "n": 4, "life": 1.4, "size": 1.0, "vel": Vector2(0.5, 2.0), "spread": 60.0, "grav": Vector3(0.2, 0.2, 0.1),
			"ramp": FX.ramp("puff"), "curve": FX.curve("dust_grow"), "expl": 1.0}, 1, -1, "dust_hit")
		return
	if u.domain == "ground":
		var s := clampf(float(u.def.get("length", 6.0)) / 7.0, 0.6, 1.3)
		explosion(pos + Vector3.UP * 0.8, "large", 0.85 * s)
		# secondary: ammunition / fuel cooks off a moment later
		later(randf_range(0.5, 1.1), explosion.bind(pos + Vector3(randf_range(-1, 1), 1.2, randf_range(-1, 1)), "medium", 0.8 * s, true))
		if Q.detail:
			later(randf_range(0.6, 1.4), emit.bind(pos + Vector3.UP * 1.5, {"mat": "spark", "n": 24, "life": 1.6, "size": 0.2, "vel": Vector2(6.0, 14.0),
				"spread": 30.0, "grav": Vector3(0, -9, 0), "damp": Vector2(0.4, 0.8), "ramp": FX.ramp("embers"), "expl": 0.5, "lrand": 0.4}, 2, -1, "cookoff"))
		wreck_fire(u.body, s, 50.0, Vector3(0, 1.3 * s, 0))
		return
	# aircraft: blast where it was hit, then it burns all the way down
	explosion(u.world_center(), "medium", 0.9)
	_burn_trail(u.body)


func _burn_trail(host: Node3D) -> void:
	if not is_instance_valid(host): return
	var fire := CPUParticles3D.new()
	fire.mesh = FX.quad("fire"); fire.amount = maxi(1, budget(int(28 * float(Q.density)))); fire.lifetime = 0.6; fire.local_coords = false
	fire.direction = Vector3.UP; fire.spread = 25.0; fire.initial_velocity_min = 0.5; fire.initial_velocity_max = 2.0
	fire.gravity = Vector3(0, 2, 0); fire.scale_amount_min = 1.0; fire.scale_amount_max = 1.8
	fire.anim_speed_min = 1.0; fire.anim_speed_max = 1.0; fire.angle_min = -180.0; fire.angle_max = 180.0
	fire.color_ramp = FX.ramp("fireball")
	fire.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	fire.set_meta("fx_burn", true)
	host.add_child(fire)
	fire.emitting = true
	var smoke := CPUParticles3D.new()
	smoke.mesh = FX.quad("smoke"); smoke.amount = maxi(1, budget(int(60 * float(Q.density)))); smoke.lifetime = 3.5; smoke.local_coords = false
	smoke.direction = Vector3.UP; smoke.spread = 15.0; smoke.initial_velocity_min = 0.3; smoke.initial_velocity_max = 1.2
	smoke.gravity = Vector3(0.4, 0.9, 0.2); smoke.scale_amount_min = 1.4; smoke.scale_amount_max = 2.2
	smoke.angle_min = -180.0; smoke.angle_max = 180.0; smoke.anim_offset_max = 1.0
	smoke.scale_amount_curve = FX.curve("smoke_grow")
	smoke.color_ramp = FX.ramp("wreck_smoke")
	smoke.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	smoke.set_meta("fx_burn", true)
	host.add_child(smoke)
	smoke.emitting = true
	track(fire, 12.0, 13.0)
	track(smoke, 12.0, 16.0)
	_log("burn_trail")


func crash(node: Node3D, pos: Vector3) -> void:
	if is_instance_valid(node):
		for c in node.get_children():
			if c.has_meta("fx_burn"): (c as CPUParticles3D).emitting = false
	_log("crash")
	explosion(pos, "large", 1.0)
	if is_instance_valid(node): wreck_fire(node, 1.0, 40.0, Vector3(0, 1.0, 0))


## Burning wreck: fire + embers + flickering light die down at ~40 % of the duration (cooling), smoke thins and
## stops at the end. Everything is freed afterwards; the blackened hull stays.
func wreck_fire(host: Node3D, size: float, duration: float, offset: Vector3) -> void:
	if not is_instance_valid(host) or not host.is_inside_tree(): return
	var dur := duration * float(Q.linger)
	var fire_end := dur * 0.4
	var fire := CPUParticles3D.new()
	fire.mesh = FX.quad("fire"); fire.amount = maxi(1, budget(maxi(4, int(14 * size * float(Q.density))))); fire.lifetime = 0.9; fire.local_coords = false
	fire.direction = Vector3.UP; fire.spread = 18.0; fire.initial_velocity_min = 0.6; fire.initial_velocity_max = 2.2
	fire.gravity = Vector3(0.3, 2.0, 0.1); fire.scale_amount_min = 0.9 * size; fire.scale_amount_max = 1.7 * size
	fire.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE; fire.emission_sphere_radius = 0.9 * size
	fire.anim_speed_min = 1.0; fire.anim_speed_max = 1.0; fire.angle_min = -180.0; fire.angle_max = 180.0
	fire.scale_amount_curve = FX.curve("flame")
	fire.color_ramp = FX.ramp("wreck_fire")
	fire.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	fire.position = offset
	host.add_child(fire)
	fire.emitting = true
	track(fire, fire_end, fire_end + 1.0)
	var smoke := CPUParticles3D.new()
	smoke.mesh = FX.quad("smoke"); smoke.amount = maxi(1, budget(maxi(6, int(30 * size * float(Q.density))))); smoke.lifetime = 6.0; smoke.local_coords = false
	smoke.direction = Vector3.UP; smoke.spread = 12.0; smoke.initial_velocity_min = 1.2; smoke.initial_velocity_max = 2.8
	smoke.gravity = Vector3(0.7, 0.9, 0.25); smoke.damping_min = 0.3; smoke.damping_max = 0.6
	smoke.scale_amount_min = 1.6 * size; smoke.scale_amount_max = 2.6 * size
	smoke.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE; smoke.emission_sphere_radius = 0.8 * size
	smoke.angle_min = -180.0; smoke.angle_max = 180.0; smoke.angular_velocity_min = -12.0; smoke.angular_velocity_max = 12.0; smoke.anim_offset_max = 1.0
	smoke.scale_amount_curve = FX.curve("smoke_grow")
	smoke.color_ramp = FX.ramp("wreck_smoke")
	smoke.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	smoke.position = offset + Vector3.UP * 0.6
	host.add_child(smoke)
	smoke.emitting = true
	track(smoke, dur, dur + 6.5)
	if Q.detail:
		var emb := CPUParticles3D.new()
		emb.mesh = FX.quad("spark"); emb.amount = maxi(1, budget(int(8 * size))); emb.lifetime = 2.0; emb.local_coords = false
		emb.direction = Vector3.UP; emb.spread = 30.0; emb.initial_velocity_min = 1.0; emb.initial_velocity_max = 3.0
		emb.gravity = Vector3(0.5, 1.0, 0.2); emb.scale_amount_min = 0.12; emb.scale_amount_max = 0.22
		emb.color_ramp = FX.ramp("embers")
		emb.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		emb.position = offset
		host.add_child(emb)
		emb.emitting = true
		track(emb, fire_end * 1.3, fire_end * 1.3 + 2.5)
	if lights.size() < int(Q.lights):
		var l := OmniLight3D.new()
		l.light_color = Color(1, 0.55, 0.2); l.light_energy = 2.6 * size; l.omni_range = 10.0 * size; l.shadow_enabled = false
		l.position = offset + Vector3.UP * 0.8
		host.add_child(l)
		lights.append({"l": l, "t0": t, "dur": fire_end, "e0": 2.6 * size, "flicker": true, "end": t + fire_end, "pooled": false})
	_log("wreck_fire")


## Structure destroyed: staggered blasts across the footprint, the model sinks and tilts into a dust cloud,
## debris bursts out. Runs from Building.die() (sim path) but only copies the model now; the rest is queued.
func collapse(b: Node) -> void:
	if not is_instance_valid(b): return
	var pos: Vector3 = b.global_position
	var half: Vector2 = b.half
	var yaw: float = b.rotation.y
	var h: float = float(b.get("model_h")) if b.get("model_h") != null else 8.0
	var area := half.x * half.y * 4.0
	var m3: Node3D = b.get("model3d")
	if m3 and is_instance_valid(m3) and m3.visible:
		var ghost := m3.duplicate(0) as Node3D
		add_child(ghost)
		ghost.global_transform = m3.global_transform
		for gi in ghost.find_children("*", "GeometryInstance3D", true, false):
			(gi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for li in ghost.find_children("*", "Light3D", true, false): li.queue_free()
		var tilt := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized() * deg_to_rad(randf_range(6.0, 13.0))
		var dur := 2.2 + minf(1.5, area / 600.0)
		var tw := ghost.create_tween().set_parallel(true)
		tw.tween_property(ghost, "position:y", ghost.position.y - h * 0.9, dur).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_QUAD).set_delay(0.25)
		tw.tween_property(ghost, "rotation", ghost.rotation + tilt, dur).set_ease(Tween.EASE_IN).set_delay(0.25)
		tw.chain().tween_callback(ghost.queue_free)
		_log("collapse")
	later(0.0, _collapse_fx.bind(pos, half, yaw, h, area))


func _collapse_fx(pos: Vector3, half: Vector2, yaw: float, h: float, area: float) -> void:
	var basis := Basis(Vector3.UP, yaw)
	var n_blasts := clampi(int(area / 180.0) + 2, 2, 5)
	for i in n_blasts:
		var o := basis * Vector3(randf_range(-half.x, half.x) * 0.7, randf_range(0.3, 0.7) * h, randf_range(-half.y, half.y) * 0.7)
		later(i * randf_range(0.18, 0.4), explosion.bind(pos + o, "large" if i > 0 or area < 500.0 else "huge", randf_range(0.8, 1.05), i < 2))
	var ext := Vector3(half.x, 1.0, half.y)
	var s := sqrt(area) / 18.0
	# dust cloud swallowing the collapse and rolling outward
	later(0.35, emit.bind(pos + Vector3.UP * h * 0.4, {"mat": "dust", "n": 30.0 * clampf(s, 0.7, 2.0), "life": 6.0, "size": 6.5 * clampf(s, 0.8, 1.6),
		"vel": Vector2(1.0, 4.0), "spread": 70.0, "grav": Vector3(0.5, 0.35, 0.2), "damp": Vector2(0.8, 1.6), "shape": "box", "ext": ext * 0.9,
		"ramp": FX.ramp("collapse_dust"),
		"curve": FX.curve("smoke_grow"), "expl": 0.6, "lrand": 0.3}, 0, -1, "collapse_dust"))
	later(0.6, emit.bind(Vector3(pos.x, pos.y + 0.6, pos.z), {"mat": "dust", "n": 26.0 * clampf(s, 0.8, 1.8), "life": 3.0, "size": 4.0,
		"vel": Vector2(8.0, 15.0), "spread": 180.0, "flat": 1.0, "dir": Vector3(1, 0, 0), "grav": Vector3(0, 0.4, 0), "damp": Vector2(3.0, 4.5),
		"shape": "ring", "r": maxf(half.x, half.y) * 0.9, "ramp": FX.ramp("collapse_dust"), "curve": FX.curve("dust_grow"), "expl": 1.0, "lrand": 0.3}, 1, -1, "dust_ring"))
	emit(pos + Vector3.UP * h * 0.5, {"mat": "debris", "n": 26.0 * clampf(s, 0.8, 1.8), "life": 1.6, "size": 0.5, "vel": Vector2(6.0, 15.0), "spread": 60.0,
		"grav": Vector3(0, -22, 0), "damp": Vector2(0.1, 0.3), "rot": true, "shape": "box", "ext": ext * 0.8, "ramp": FX.ramp("chips"),
		"curve": FX.curve("debris"), "expl": 0.9, "lrand": 0.2}, 1, -1, "debris")
	shake(pos, 0.5 * clampf(s, 0.6, 1.4))

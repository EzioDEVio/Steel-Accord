# Steel Accord - combat visual effects (muzzle flash, tracer, impacts, explosions, wreck smoke).
# All particle effects are CPU particles with soft procedural sprites; nodes free themselves.
class_name FX

static var _soft: GradientTexture2D


static func _sprite() -> GradientTexture2D:
	if _soft == null:
		_soft = GradientTexture2D.new()
		_soft.fill = GradientTexture2D.FILL_RADIAL
		_soft.fill_from = Vector2(0.5, 0.5); _soft.fill_to = Vector2(1.0, 0.5)
		var g := Gradient.new()
		g.set_color(0, Color(1, 1, 1, 1)); g.set_color(1, Color(1, 1, 1, 0))
		g.add_point(0.45, Color(1, 1, 1, 0.55))
		_soft.gradient = g; _soft.width = 64; _soft.height = 64
	return _soft


static func _mat(additive: bool) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED if additive else BaseMaterial3D.SHADING_MODE_PER_PIXEL
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	if additive: m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	m.albedo_texture = _sprite()
	m.disable_receive_shadows = true
	return m


static func _ramp(cols: Array) -> Gradient:
	var g := Gradient.new()
	g.set_color(0, cols[0]); g.set_color(1, cols[cols.size() - 1])
	for i in range(1, cols.size() - 1):
		g.add_point(float(i) / (cols.size() - 1), cols[i])
	return g


static func _particles(parent: Node, pos: Vector3, amount: int, life: float, additive: bool, size: float,
		vel: Vector2, spread: float, colors: Array, grav := Vector3(0, 1.5, 0), dir := Vector3.UP, scale_curve := true) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	var q := QuadMesh.new(); q.size = Vector2(size, size); q.material = _mat(additive)
	p.mesh = q
	p.amount = amount; p.lifetime = life; p.one_shot = true; p.explosiveness = 0.92
	p.direction = dir; p.spread = spread
	p.initial_velocity_min = vel.x; p.initial_velocity_max = vel.y
	p.gravity = grav; p.damping_min = 2.0; p.damping_max = 4.0
	p.scale_amount_min = 0.6; p.scale_amount_max = 1.4
	if scale_curve:
		var c := Curve.new(); c.add_point(Vector2(0, 0.4)); c.add_point(Vector2(0.3, 1.0)); c.add_point(Vector2(1, 1.6))
		p.scale_amount_curve = c
	p.color_ramp = _ramp(colors)
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	_free_later(p, life + 0.5)
	return p


static func _free_later(n: Node, t: float) -> void:
	n.get_tree().create_timer(t).timeout.connect(n.queue_free)


static func _flash(parent: Node, pos: Vector3, energy: float, rng: float, color: Color, t: float) -> void:
	var l := OmniLight3D.new()
	l.light_color = color; l.light_energy = energy; l.omni_range = rng
	l.shadow_enabled = false
	parent.add_child(l)
	l.global_position = pos
	var tw := l.create_tween()
	tw.tween_property(l, "light_energy", 0.0, t)
	tw.tween_callback(l.queue_free)


static func muzzle_flash(parent: Node, pos: Vector3, dir: Vector3) -> void:
	_flash(parent, pos, 8.0, 14.0, Color(1.0, 0.7, 0.35), 0.15)
	_particles(parent, pos, 10, 0.18, true, 1.6, Vector2(4, 10), 12.0,
		[Color(1, 0.95, 0.7, 1), Color(1, 0.55, 0.15, 0.8), Color(0.6, 0.2, 0.05, 0)], Vector3.ZERO, dir, false)
	_particles(parent, pos, 18, 1.8, false, 1.8, Vector2(1, 4), 35.0,
		[Color(0.75, 0.72, 0.66, 0.55), Color(0.6, 0.58, 0.55, 0.3), Color(0.5, 0.5, 0.5, 0)], Vector3(0, 0.6, 0), dir)


static func impact(parent: Node, pos: Vector3, hit_armour: bool) -> void:
	SFX.play(parent, "explosion_big", pos, -10.0 if hit_armour else -13.0, 1.45 if hit_armour else 1.6)
	_flash(parent, pos + Vector3.UP, 5.0 if hit_armour else 2.5, 10.0, Color(1.0, 0.65, 0.3), 0.2)
	if hit_armour:
		_particles(parent, pos, 16, 0.35, true, 0.7, Vector2(6, 16), 60.0,
			[Color(1, 0.9, 0.6, 1), Color(1, 0.5, 0.1, 0.6), Color(0.3, 0.1, 0, 0)], Vector3(0, -9, 0), Vector3.UP, false)
	_particles(parent, pos, 22, 1.6, false, 1.6, Vector2(2, 7), 40.0,
		[Color(0.42, 0.36, 0.27, 0.9), Color(0.38, 0.33, 0.26, 0.5), Color(0.35, 0.32, 0.28, 0)], Vector3(0, -3, 0))


## Explosion scaled by `s` (1.0 = vehicle kill, ~2 = heavy bomb). Fireball, sparks, rolling smoke, dust ring, scorch.
static func explosion(parent: Node, pos: Vector3, s := 1.0) -> void:
	SFX.play(parent, "explosion_big", pos, -4.0 + 4.0 * minf(s, 2.0), clampf(1.15 / sqrt(s), 0.75, 1.3))
	_flash(parent, pos + Vector3.UP * 2.0 * s, 18.0 * s, 30.0 * s, Color(1.0, 0.6, 0.25), 0.6 + 0.4 * s)
	_particles(parent, pos + Vector3.UP * 1.2 * s, int(30 + 24 * s), 0.8 + 0.3 * s, true, 3.2 * s, Vector2(3, 9) * s, 70.0,
		[Color(1, 0.95, 0.75, 1), Color(1, 0.6, 0.15, 0.9), Color(0.7, 0.2, 0.05, 0.5), Color(0.15, 0.05, 0.02, 0)], Vector3(0, 2, 0))
	_particles(parent, pos + Vector3.UP, int(20 + 20 * s), 1.2, true, 0.35 * maxf(1.0, s), Vector2(10, 22) * sqrt(s), 75.0,
		[Color(1, 0.8, 0.4, 1), Color(1, 0.4, 0.1, 0.8), Color(0.2, 0.05, 0, 0)], Vector3(0, -14, 0), Vector3.UP, false)
	_particles(parent, pos + Vector3.UP * 1.5 * s, int(26 + 24 * s), 3.5 + 1.5 * s, false, 4.5 * s, Vector2(1, 5) * sqrt(s), 60.0,
		[Color(0.12, 0.11, 0.1, 0.85), Color(0.2, 0.19, 0.18, 0.6), Color(0.35, 0.34, 0.33, 0)], Vector3(0, 2.2, 0))
	_particles(parent, pos + Vector3.UP * 0.3, int(16 + 16 * s), 2.2, false, 3.0 * s, Vector2(6, 12) * s, 85.0,
		[Color(0.45, 0.39, 0.3, 0.7), Color(0.42, 0.37, 0.3, 0.35), Color(0.4, 0.36, 0.3, 0)], Vector3(0, -1, 0), Vector3.UP)
	scorch(parent, pos, 7.0 * s)


static func scorch(parent: Node, pos: Vector3, size: float) -> void:
	var g := GradientTexture2D.new()
	g.fill = GradientTexture2D.FILL_RADIAL; g.fill_from = Vector2(0.5, 0.5); g.fill_to = Vector2(1.0, 0.5)
	g.gradient = _ramp([Color(0.02, 0.02, 0.02, 0.9), Color(0.05, 0.04, 0.03, 0.6), Color(0, 0, 0, 0)])
	var d := Decal.new()
	d.texture_albedo = g; d.size = Vector3(size, 3.0, size)
	parent.add_child(d)
	d.global_position = pos


## Persistent smoke + flicker light on a wreck.
static func wreck_fire(host: Node3D) -> void:
	var p := CPUParticles3D.new()
	var q := QuadMesh.new(); q.size = Vector2(2.4, 2.4); q.material = _mat(false)
	p.mesh = q; p.amount = 26; p.lifetime = 5.0; p.explosiveness = 0.0
	p.direction = Vector3.UP; p.spread = 12.0
	p.initial_velocity_min = 1.5; p.initial_velocity_max = 3.0
	p.gravity = Vector3(0.6, 0.8, 0.2)
	var c := Curve.new(); c.add_point(Vector2(0, 0.5)); c.add_point(Vector2(1, 3.0))
	p.scale_amount_curve = c
	p.color_ramp = _ramp([Color(0.08, 0.07, 0.06, 0.9), Color(0.18, 0.17, 0.16, 0.5), Color(0.3, 0.3, 0.3, 0)])
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	host.add_child(p)
	p.position = Vector3(0, 2.2, -0.5)
	p.emitting = true
	var f := CPUParticles3D.new()
	var fq := QuadMesh.new(); fq.size = Vector2(1.2, 1.2); fq.material = _mat(true)
	f.mesh = fq; f.amount = 14; f.lifetime = 0.7
	f.direction = Vector3.UP; f.spread = 20.0; f.initial_velocity_min = 1.0; f.initial_velocity_max = 2.5
	f.gravity = Vector3(0, 1, 0)
	f.color_ramp = _ramp([Color(1, 0.8, 0.4, 0.9), Color(1, 0.4, 0.1, 0.6), Color(0.3, 0.1, 0, 0)])
	f.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	host.add_child(f)
	f.position = Vector3(0, 1.9, -1.2)
	f.emitting = true
	var l := OmniLight3D.new()
	l.light_color = Color(1, 0.55, 0.2); l.light_energy = 2.5; l.omni_range = 9.0
	host.add_child(l)
	l.position = Vector3(0, 2.5, -1.0)


static func tracer_mesh(width := 0.12, length := 4.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := BoxMesh.new(); b.size = Vector3(width, width, length)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(1.0, 0.75, 0.35)
	m.emission_enabled = true; m.emission = Color(1.0, 0.6, 0.2); m.emission_energy_multiplier = 4.0
	b.material = m
	mi.mesh = b
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


## Missile / rocket body with motor glow and a smoke trail (trail particles are emitted in world space).
static func missile_node(guided: bool) -> Node3D:
	var n := Node3D.new()
	var body := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = 0.09; c.bottom_radius = 0.09; c.height = 1.6 if guided else 1.1; c.radial_segments = 8
	var m := StandardMaterial3D.new(); m.albedo_color = Color(0.78, 0.78, 0.74); m.roughness = 0.5
	c.material = m
	body.mesh = c; body.rotation.x = PI / 2
	n.add_child(body)
	var glow := MeshInstance3D.new()
	var q := QuadMesh.new(); q.size = Vector2(0.9, 0.9); q.material = _mat(true)
	(q.material as StandardMaterial3D).billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	(q.material as StandardMaterial3D).albedo_color = Color(1, 0.75, 0.4)
	glow.mesh = q; glow.position.z = 0.9
	n.add_child(glow)
	var p := CPUParticles3D.new()
	var tq := QuadMesh.new(); tq.size = Vector2(0.9, 0.9); tq.material = _mat(false)
	p.mesh = tq; p.amount = 40 if guided else 24; p.lifetime = 1.4
	p.local_coords = false
	p.direction = Vector3(0, 0, 1); p.spread = 8.0
	p.initial_velocity_min = 0.5; p.initial_velocity_max = 1.5
	p.gravity = Vector3(0, 0.6, 0)
	var cv := Curve.new(); cv.add_point(Vector2(0, 0.4)); cv.add_point(Vector2(1, 2.4))
	p.scale_amount_curve = cv
	p.color_ramp = _ramp([Color(0.85, 0.84, 0.8, 0.7), Color(0.7, 0.7, 0.68, 0.35), Color(0.6, 0.6, 0.6, 0)])
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.position.z = 0.9
	n.add_child(p)
	p.emitting = true
	return n


static func launch_puff(parent: Node, pos: Vector3) -> void:
	_flash(parent, pos, 3.0, 8.0, Color(1, 0.7, 0.4), 0.15)
	_particles(parent, pos, 10, 1.2, false, 1.4, Vector2(1, 3), 50.0,
		[Color(0.8, 0.8, 0.78, 0.6), Color(0.7, 0.7, 0.7, 0.3), Color(0.6, 0.6, 0.6, 0)], Vector3(0, 0.5, 0))


static func small_flash(parent: Node, pos: Vector3) -> void:
	_particles(parent, pos, 4, 0.08, true, 1.1, Vector2(2, 4), 20.0,
		[Color(1, 0.9, 0.6, 1), Color(1, 0.5, 0.1, 0)], Vector3.ZERO, Vector3.UP, false)


static func bullet_hit(parent: Node, pos: Vector3, armour: bool, heavy := false) -> void:
	if heavy:
		# aircraft cannon: sparks + a burst of dust per round so a strafing run reads as a line of impacts
		_flash(parent, pos + Vector3.UP, 2.5, 7.0, Color(1, 0.7, 0.35), 0.1)
		_particles(parent, pos, 8, 0.3, true, 0.5, Vector2(5, 12), 70.0,
			[Color(1, 0.9, 0.6, 1), Color(1, 0.5, 0.1, 0)], Vector3(0, -9, 0), Vector3.UP, false)
		_particles(parent, Vector3(pos.x, 0.2, pos.z), 10, 1.4, false, 1.8, Vector2(2, 6), 45.0,
			[Color(0.45, 0.39, 0.3, 0.85), Color(0.42, 0.37, 0.3, 0.4), Color(0.4, 0.36, 0.3, 0)], Vector3(0, -3, 0))
		return
	if armour:
		_particles(parent, pos, 5, 0.25, true, 0.35, Vector2(4, 9), 70.0,
			[Color(1, 0.9, 0.6, 1), Color(1, 0.5, 0.1, 0)], Vector3(0, -9, 0), Vector3.UP, false)
	else:
		_particles(parent, pos, 6, 0.9, false, 0.7, Vector2(1, 3), 35.0,
			[Color(0.45, 0.39, 0.3, 0.8), Color(0.42, 0.37, 0.3, 0)], Vector3(0, -4, 0))


## Falling bomb: olive body with tail fins and a light smoke trail so the drop is readable from the RTS camera.
static func bomb_node() -> Node3D:
	var n := Node3D.new()
	var mi := MeshInstance3D.new()
	var c := CapsuleMesh.new(); c.radius = 0.45; c.height = 3.2
	var m := StandardMaterial3D.new(); m.albedo_color = Color(0.36, 0.38, 0.28); m.roughness = 0.5
	c.material = m
	mi.mesh = c
	mi.rotation.x = PI / 2
	n.add_child(mi)
	var fin := MeshInstance3D.new()
	var fb := BoxMesh.new(); fb.size = Vector3(1.4, 0.06, 0.6); fb.material = m
	fin.mesh = fb; fin.position.z = 1.4
	n.add_child(fin)
	var fin2 := fin.duplicate() as MeshInstance3D
	fin2.rotation.z = PI / 2
	n.add_child(fin2)
	exhaust_trail(n, Vector3(0, 0, 1.6), 0.7, true)
	return n


## World-space smoke / contrail emitter attached to a moving node (offset in the node's local space; +Z is aft).
static func exhaust_trail(host: Node3D, offset: Vector3, width: float, contrail: bool) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	var q := QuadMesh.new(); q.size = Vector2(width, width); q.material = _mat(false)
	p.mesh = q
	p.amount = 60 if contrail else 36
	p.lifetime = 2.6 if contrail else 1.1
	p.local_coords = false
	p.direction = Vector3(0, 0, 1); p.spread = 5.0
	p.initial_velocity_min = 0.2; p.initial_velocity_max = 0.8
	p.gravity = Vector3(0, 0.3, 0)
	var cv := Curve.new(); cv.add_point(Vector2(0, 0.6)); cv.add_point(Vector2(1, 2.6 if contrail else 1.8))
	p.scale_amount_curve = cv
	var col := Color(0.95, 0.95, 0.95, 0.55) if contrail else Color(0.55, 0.53, 0.5, 0.35)
	p.color_ramp = _ramp([col, Color(col.r, col.g, col.b, col.a * 0.4), Color(col.r, col.g, col.b, 0)])
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.position = offset
	host.add_child(p)
	p.emitting = true
	if not contrail:
		var glow := MeshInstance3D.new()
		var gq := QuadMesh.new(); gq.size = Vector2(width * 1.6, width * 1.6); gq.material = _mat(true)
		(gq.material as StandardMaterial3D).billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		(gq.material as StandardMaterial3D).albedo_color = Color(1, 0.7, 0.4, 0.8)
		glow.mesh = gq; glow.position = offset
		glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		host.add_child(glow)
	return p


## Red target circle + crosshair on the ground for a called-in strike; fades out after `t` seconds (0 = 6 s).
static func target_marker(parent: Node, pos: Vector3, t: float) -> void:
	var n := Node3D.new()
	parent.add_child(n)
	n.global_position = pos + Vector3.UP * 0.25
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(1, 0.25, 0.15, 0.85); m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new(); tm.inner_radius = 9.0; tm.outer_radius = 9.8; tm.rings = 48; tm.ring_segments = 4; tm.material = m
	ring.mesh = tm; ring.scale = Vector3(1, 0.03, 1)
	n.add_child(ring)
	for k in 2:
		var bar := MeshInstance3D.new()
		var bm := BoxMesh.new(); bm.size = Vector3(22, 0.05, 0.6); bm.material = m
		bar.mesh = bm; bar.rotation.y = k * PI / 2
		n.add_child(bar)
	var tw := n.create_tween()
	tw.tween_interval(t if t > 0.0 else 6.0)
	tw.tween_property(m, "albedo_color:a", 0.0, 1.0)
	tw.tween_callback(n.queue_free)


static func order_marker(parent: Node, pos: Vector3, color: Color) -> void:
	var mi := MeshInstance3D.new()
	var t := TorusMesh.new(); t.inner_radius = 1.6; t.outer_radius = 2.0; t.rings = 24; t.ring_segments = 6
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = color; m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	t.material = m
	mi.mesh = t; mi.scale = Vector3(1, 0.05, 1)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	mi.global_position = pos + Vector3.UP * 0.15
	var tw := mi.create_tween().set_parallel(true)
	tw.tween_property(mi, "scale", Vector3(0.3, 0.05, 0.3), 0.6)
	tw.tween_property(m, "albedo_color:a", 0.0, 0.6)
	tw.chain().tween_callback(mi.queue_free)

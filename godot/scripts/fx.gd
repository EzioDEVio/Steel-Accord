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
	_flash(parent, pos + Vector3.UP, 5.0 if hit_armour else 2.5, 10.0, Color(1.0, 0.65, 0.3), 0.2)
	if hit_armour:
		_particles(parent, pos, 16, 0.35, true, 0.7, Vector2(6, 16), 60.0,
			[Color(1, 0.9, 0.6, 1), Color(1, 0.5, 0.1, 0.6), Color(0.3, 0.1, 0, 0)], Vector3(0, -9, 0), Vector3.UP, false)
	_particles(parent, pos, 22, 1.6, false, 1.6, Vector2(2, 7), 40.0,
		[Color(0.42, 0.36, 0.27, 0.9), Color(0.38, 0.33, 0.26, 0.5), Color(0.35, 0.32, 0.28, 0)], Vector3(0, -3, 0))


static func explosion(parent: Node, pos: Vector3, big := true) -> void:
	var s := 1.0 if big else 0.5
	_flash(parent, pos + Vector3.UP * 2.0, 18.0 * s, 30.0 * s, Color(1.0, 0.6, 0.25), 0.9)
	# fireball
	_particles(parent, pos + Vector3.UP * 1.2, int(36 * s), 0.9, true, 3.2 * s, Vector2(3, 9), 70.0,
		[Color(1, 0.95, 0.75, 1), Color(1, 0.6, 0.15, 0.9), Color(0.7, 0.2, 0.05, 0.5), Color(0.15, 0.05, 0.02, 0)], Vector3(0, 2, 0))
	# debris sparks
	_particles(parent, pos + Vector3.UP, int(30 * s), 1.2, true, 0.35, Vector2(10, 22), 75.0,
		[Color(1, 0.8, 0.4, 1), Color(1, 0.4, 0.1, 0.8), Color(0.2, 0.05, 0, 0)], Vector3(0, -14, 0), Vector3.UP, false)
	# rolling black smoke
	_particles(parent, pos + Vector3.UP * 1.5, int(40 * s), 4.5, false, 4.5 * s, Vector2(1, 5), 60.0,
		[Color(0.12, 0.11, 0.1, 0.85), Color(0.2, 0.19, 0.18, 0.6), Color(0.35, 0.34, 0.33, 0)], Vector3(0, 2.2, 0))
	# dust ring
	_particles(parent, pos + Vector3.UP * 0.3, int(24 * s), 2.2, false, 3.0 * s, Vector2(6, 12), 85.0,
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


static func tracer_mesh() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := BoxMesh.new(); b.size = Vector3(0.12, 0.12, 4.0)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(1.0, 0.75, 0.35)
	m.emission_enabled = true; m.emission = Color(1.0, 0.6, 0.2); m.emission_energy_multiplier = 4.0
	b.material = m
	mi.mesh = b
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


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

# Steel Accord - procedural ruins of destroyed structures (presentation only).
# A ruin is assembled from the original ruin kit (assets/fx/ruin_kit.glb, tools/art/fx_ruin_kit.py): broken wall
# stubs with jagged tops along the footprint edge, corner stubs, snapped columns, fallen roof slabs at angles with
# exposed rebar, bent steel beams, rubble mounds and scattered blocks, drawn as one MultiMesh per piece type.
# Pieces are tinted with colours sampled from the destroyed building's own textures (FXRuin.palette), so each kind
# of building leaves a distinct ruin. A scorched ash decal lies under it and smoke / fire linger for a while
# (longer for larger buildings). The layout comes from a RandomNumberGenerator seeded with the building uid, so
# a saved game rebuilds the same ruin. Gameplay rules (rubble does not block movement, a Dozer can rebuild on it)
# live in battle.gd and are unchanged.
class_name FXRuin

const WALLS := ["wall_a", "wall_b", "wall_c"]
const CHUNKS := ["chunk_a", "chunk_b", "chunk_c", "chunk_d"]

static var _pal := {}
static var _mats_set := false
static var _conc: StandardMaterial3D
static var _rebar: StandardMaterial3D


## Colours of a building kind sampled from its 3D model: {"wall", "trim", "dark", "h" (model height), "src"}.
static func palette(bkind: String) -> Dictionary:
	if _pal.has(bkind): return _pal[bkind]
	var res := {"wall": Color(0.62, 0.6, 0.56), "trim": Color(0.46, 0.45, 0.42), "dark": Color(0.24, 0.23, 0.22), "h": 8.0, "src": "default"}
	var path := str(BuildingDefs.DEFS.get(bkind, {}).get("model3d", ""))
	if path != "" and ResourceLoader.exists(path):
		var inst: Node3D = (load(path) as PackedScene).instantiate()
		var samples: Array = []     # [luminance, Color, weight]
		var top := 0.0
		for mi in inst.find_children("*", "MeshInstance3D", true, false):
			var m := mi as MeshInstance3D
			if m.mesh == null or String(m.name).begins_with("Light_"): continue
			var xf := Transform3D.IDENTITY
			var nd: Node = m
			while nd and nd != inst:
				xf = (nd as Node3D).transform * xf
				nd = nd.get_parent()
			top = maxf(top, (xf * m.mesh.get_aabb()).end.y)
			for si in m.mesh.get_surface_count():
				var mt: Material = m.get_surface_override_material(si)
				if mt == null: mt = m.mesh.surface_get_material(si)
				_sample(mt, float(m.mesh.surface_get_array_len(si)), samples)
		inst.free()
		if top > 0.5: res.h = top
		if samples.size() >= 8:
			samples.sort_custom(func(a, b): return a[0] < b[0])
			var tot := 0.0
			for s in samples: tot += s[2]
			res.dark = _band(samples, tot, 0.0, 0.12)
			res.trim = _band(samples, tot, 0.12, 0.4)
			res.wall = _band(samples, tot, 0.4, 0.92)
			res.src = path
	# dust and soot settle on everything: desaturate a little and darken
	for k in ["wall", "trim", "dark"]:
		var c: Color = res[k]
		var g := c.get_luminance()
		res[k] = Color(lerpf(c.r, g, 0.25), lerpf(c.g, g, 0.25), lerpf(c.b, g, 0.25)) * 0.9
	_pal[bkind] = res
	return res


static func _sample(mt: Material, weight: float, out: Array) -> void:
	if not (mt is BaseMaterial3D): return
	var bm := mt as BaseMaterial3D
	var base := bm.albedo_color
	var tx := bm.albedo_texture
	var img: Image = tx.get_image() if tx else null
	if img == null or img.is_empty():
		out.append([base.get_luminance(), base, weight])
		return
	img = img.duplicate()
	if img.is_compressed() and img.decompress() != OK:
		out.append([base.get_luminance(), base, weight])
		return
	img.resize(24, 24, Image.INTERPOLATE_BILINEAR)
	var w := weight / 576.0
	for y in 24:
		for x in 24:
			var c := img.get_pixel(x, y)
			if c.a < 0.5: continue
			c = Color(c.r * base.r, c.g * base.g, c.b * base.b)
			out.append([c.get_luminance(), c, w])


## Weighted mean colour of the samples between two cumulative-weight fractions (samples sorted by luminance).
static func _band(samples: Array, tot: float, a: float, b: float) -> Color:
	var acc := 0.0
	var sum := Color(0, 0, 0, 0)
	var ws := 0.0
	for s in samples:
		var f := acc / tot
		acc += s[2]
		if f < a or f > b: continue
		sum += s[1] * s[2]
		ws += s[2]
	if ws <= 0.0: return samples[int(samples.size() * (a + b) * 0.5)][1]
	return Color(sum.r / ws, sum.g / ws, sum.b / ws)


static func _materials() -> void:
	if _mats_set: return
	_mats_set = true
	_conc = StandardMaterial3D.new()
	_conc.albedo_texture = FX.tex("concrete_detail")
	_conc.uv1_triplanar = true
	_conc.uv1_scale = Vector3(0.45, 0.45, 0.45)
	_conc.vertex_color_use_as_albedo = true
	_conc.roughness = 0.96
	_rebar = StandardMaterial3D.new()
	_rebar.albedo_color = Color(0.3, 0.17, 0.1)
	_rebar.metallic = 0.4
	_rebar.roughness = 0.7
	for id in WALLS + CHUNKS + ["corner_a", "slab_a", "slab_b", "beam_a", "column_a", "mound_a", "mound_b"]:
		var m: Mesh = FX.kit_mesh(id)
		if m == null: continue
		for si in m.get_surface_count():
			var src := m.surface_get_material(si)
			var nm := String(src.resource_name) if src else ""
			m.surface_set_material(si, _rebar if nm.contains("Rebar") else _conc)


## Fill `root` (positioned at the footprint centre, rotated by the building yaw) with a ruin. `age` = seconds since
## the destruction (a loaded game): smoke and fire only linger for what is left of their time.
static func build(d: FXDirector, root: Node3D, bkind: String, half: Vector2, seed_id: int, age: float) -> void:
	if not is_instance_valid(root): return
	_materials()
	var pal := palette(bkind)
	var r := RandomNumberGenerator.new()
	r.seed = seed_id * 7919 + 17
	var hs := clampf(float(pal.h) / 9.0, 0.45, 1.5)
	var area := half.x * half.y * 4.0
	var items := {}       # piece id -> [[Transform3D, Color], ...]
	var ix := maxf(half.x - 0.6, 1.0)
	var iz := maxf(half.y - 0.6, 1.0)
	var soot := func() -> float: return r.randf_range(0.5, 1.0)
	# 1. wall stubs along the four edges (4 m segments, about 60 % still standing)
	var edges := [[Vector3(-ix, 0, iz), Vector3(ix, 0, iz)], [Vector3(ix, 0, iz), Vector3(ix, 0, -iz)],
		[Vector3(ix, 0, -iz), Vector3(-ix, 0, -iz)], [Vector3(-ix, 0, -iz), Vector3(-ix, 0, iz)]]
	for e in edges:
		var a: Vector3 = e[0]
		var b: Vector3 = e[1]
		var ln := a.distance_to(b)
		var nseg := maxi(1, int(round(ln / 4.0)))
		var seg := ln / nseg
		var ang := atan2(-(b - a).z, (b - a).x)
		for k in nseg:
			if r.randf() > 0.6: continue
			var c := a.lerp(b, (k + 0.5) / nseg) + Vector3(r.randf_range(-0.2, 0.2), 0, r.randf_range(-0.2, 0.2))
			var bas := Basis(Vector3.UP, ang + r.randf_range(-0.06, 0.06)) * Basis(Vector3.RIGHT, r.randf_range(-0.1, 0.1))
			bas = bas * Basis.from_scale(Vector3(seg / 4.0 * r.randf_range(0.8, 1.02), hs * r.randf_range(0.5, 1.1), 1.0))
			_add(items, WALLS[r.randi() % 3], Transform3D(bas, c), pal.wall * soot.call())
	for i in 4:
		if r.randf() < 0.5:
			var cx := ix if i % 2 == 0 else -ix
			var cz := iz if i < 2 else -iz
			var bas := Basis(Vector3.UP, float(i) * PI / 2.0 + r.randf_range(-0.1, 0.1)) * Basis.from_scale(Vector3(1, hs * r.randf_range(0.6, 1.0), 1))
			_add(items, "corner_a", Transform3D(bas, Vector3(cx, 0, cz)), pal.wall * soot.call())
	# 2. rubble mounds inside the footprint
	var nm := clampi(int(area / 140.0) + 1, 1, 6)
	var ms := clampf(minf(half.x, half.y) / 3.4, 0.5, 1.7)
	for i in nm:
		var p := Vector3(r.randf_range(-ix, ix) * 0.6, -0.15, r.randf_range(-iz, iz) * 0.6)
		var bas := Basis(Vector3.UP, r.randf() * TAU) * Basis.from_scale(Vector3(ms * r.randf_range(0.7, 1.1), clampf(hs, 0.6, 1.3) * r.randf_range(0.6, 1.0), ms * r.randf_range(0.7, 1.1)))
		_add(items, "mound_a" if i % 2 == 0 else "mound_b", Transform3D(bas, p), pal.trim.lerp(pal.wall, r.randf()) * soot.call())
	# 3. fallen roof slabs leaning at angles, and bent beams
	var ns := clampi(int(area / 100.0) + 1, 1, 8)
	for i in ns:
		var p := Vector3(r.randf_range(-ix, ix) * 0.75, r.randf_range(0.2, 1.3) * hs, r.randf_range(-iz, iz) * 0.75)
		var bas := Basis(Vector3.UP, r.randf() * TAU) * Basis(Vector3.RIGHT, r.randf_range(0.25, 0.65)) * Basis(Vector3.FORWARD, r.randf_range(-0.2, 0.2))
		bas = bas * Basis.from_scale(Vector3.ONE * clampf(minf(half.x, half.y) / 5.0, 0.5, 1.2) * r.randf_range(0.75, 1.05))
		_add(items, "slab_a" if r.randf() < 0.5 else "slab_b", Transform3D(bas, p), (pal.trim if r.randf() < 0.5 else pal.wall) * soot.call())
	for i in clampi(int(area / 160.0), 0, 5):
		var p := Vector3(r.randf_range(-ix, ix) * 0.7, r.randf_range(0.1, 1.0) * hs, r.randf_range(-iz, iz) * 0.7)
		var bas := Basis(Vector3.UP, r.randf() * TAU) * Basis(Vector3.FORWARD, r.randf_range(-0.35, 0.35))
		_add(items, "beam_a", Transform3D(bas * Basis.from_scale(Vector3.ONE * r.randf_range(0.7, 1.1)), p), Color.WHITE)
	for i in clampi(int(area / 200.0), 0, 4):
		var p := Vector3(r.randf_range(-ix, ix) * 0.8, 0, r.randf_range(-iz, iz) * 0.8)
		var bas := Basis(Vector3.UP, r.randf() * TAU) * Basis(Vector3.RIGHT, r.randf_range(-0.12, 0.12))
		_add(items, "column_a", Transform3D(bas * Basis.from_scale(Vector3(1, hs * r.randf_range(0.6, 1.1), 1)), p), pal.trim * soot.call())
	# 4. scattered blocks, some spilled past the footprint edge
	var nch := clampi(int(area / 6.0), 12, 90)
	if not FX.quality().detail: nch = int(nch * 0.6)
	for i in nch:
		var p := Vector3(r.randf_range(-ix - 1.8, ix + 1.8), 0, r.randf_range(-iz - 1.8, iz + 1.8))
		p.y = r.randf_range(-0.2, 0.1)
		var bas := Basis.from_euler(Vector3(r.randf_range(-0.6, 0.6), r.randf() * TAU, r.randf_range(-0.6, 0.6)))
		var sc := r.randf_range(0.35, 1.5)
		var col: Color = [pal.wall, pal.trim, pal.dark, pal.wall][r.randi() % 4]
		_add(items, CHUNKS[r.randi() % 4], Transform3D(bas * Basis.from_scale(Vector3(sc, sc * r.randf_range(0.6, 1.0), sc)), p), col * soot.call())
	# MultiMesh per piece type
	var total := 0
	var xz := PackedVector2Array()
	var shadows := FX.preset() != "Low"
	for id in items:
		var mesh: Mesh = FX.kit_mesh(id)
		if mesh == null: continue
		var list: Array = items[id]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = mesh
		mm.instance_count = list.size()
		for i in list.size():
			mm.set_instance_transform(i, list[i][0])
			mm.set_instance_color(i, list[i][1])
			xz.append(Vector2(list[i][0].origin.x, list[i][0].origin.z))
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "Ruin_" + id
		mmi.multimesh = mm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(mmi)
		total += list.size()
	root.set_meta("pieces", total)
	root.set_meta("piece_xz", xz)
	root.set_meta("palette", pal)
	# scorched ash under the ruin
	var dec := Decal.new()
	dec.name = "RuinAsh"
	dec.texture_albedo = FX.tex("ruin_ash")
	dec.size = Vector3(half.x * 2.0 + 5.0, 8.0, half.y * 2.0 + 5.0)
	dec.upper_fade = 0.2; dec.lower_fade = 0.2
	root.add_child(dec)
	var sc2 := Decal.new()
	sc2.texture_albedo = FX.tex("scorch")
	var sz := maxf(half.x, half.y) * 2.6 + 6.0
	sc2.size = Vector3(sz, 8.0, sz)
	sc2.rotation.y = r.randf() * TAU
	sc2.modulate = Color(1, 1, 1, 0.8)
	root.add_child(sc2)
	_linger(d, root, half, area, hs, age, r)


## Lingering smoke plumes and small fires; larger buildings burn longer. Freed when done.
static func _linger(d: FXDirector, root: Node3D, half: Vector2, area: float, hs: float, age: float, r: RandomNumberGenerator) -> void:
	var dur := clampf(30.0 + area * 0.06, 30.0, 120.0) * float(d.Q.linger)
	var left := dur - age
	if left < 3.0: return
	var dens := float(d.Q.density)
	var plumes := clampi(1 + int(area / 300.0), 1, 3)
	for i in plumes:
		var p := Vector3(r.randf_range(-half.x, half.x) * 0.5, 1.2 * hs, r.randf_range(-half.y, half.y) * 0.5)
		var sm := CPUParticles3D.new()
		sm.mesh = FX.quad("smoke"); sm.amount = maxi(1, d.budget(maxi(8, int(34 * dens)))); sm.lifetime = 8.0; sm.local_coords = false
		sm.direction = Vector3.UP; sm.spread = 14.0; sm.initial_velocity_min = 1.2; sm.initial_velocity_max = 2.6
		sm.gravity = Vector3(0.8, 0.8, 0.3); sm.damping_min = 0.2; sm.damping_max = 0.5
		sm.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE; sm.emission_sphere_radius = 1.6
		sm.scale_amount_min = 2.8; sm.scale_amount_max = 4.2
		sm.angle_min = -180.0; sm.angle_max = 180.0; sm.angular_velocity_min = -8.0; sm.angular_velocity_max = 8.0; sm.anim_offset_max = 1.0
		sm.scale_amount_curve = FX.curve("smoke_grow")
		sm.color_ramp = FX.ramp("wreck_smoke")
		sm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		sm.position = p
		root.add_child(sm)
		sm.emitting = true
		d.track(sm, left, left + 8.5)
	var fire_left := left * 0.45
	if fire_left < 2.0: return
	for i in clampi(1 + int(area / 250.0), 1, 3):
		var p := Vector3(r.randf_range(-half.x, half.x) * 0.6, 0.6 * hs, r.randf_range(-half.y, half.y) * 0.6)
		var f := CPUParticles3D.new()
		f.mesh = FX.quad("fire"); f.amount = maxi(1, d.budget(maxi(4, int(12 * dens)))); f.lifetime = 0.9; f.local_coords = false
		f.direction = Vector3.UP; f.spread = 20.0; f.initial_velocity_min = 0.6; f.initial_velocity_max = 2.0
		f.gravity = Vector3(0.3, 2.0, 0.1); f.scale_amount_min = 1.0; f.scale_amount_max = 1.9
		f.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE; f.emission_sphere_radius = 1.2
		f.anim_speed_min = 1.0; f.anim_speed_max = 1.0; f.angle_min = -180.0; f.angle_max = 180.0
		f.scale_amount_curve = FX.curve("flame")
		f.color_ramp = FX.ramp("wreck_fire")
		f.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		f.position = p
		root.add_child(f)
		f.emitting = true
		d.track(f, fire_left, fire_left + 1.0)
		if i == 0 and d.lights.size() < int(d.Q.lights):
			var l := OmniLight3D.new()
			l.light_color = Color(1, 0.55, 0.2); l.light_energy = 3.0; l.omni_range = 14.0; l.shadow_enabled = false
			l.position = p + Vector3.UP
			root.add_child(l)
			d.lights.append({"l": l, "t0": d.t, "dur": fire_left, "e0": 3.0, "flicker": true, "end": d.t + fire_left, "pooled": false})


static func _add(items: Dictionary, id: String, xf: Transform3D, col: Color) -> void:
	if not items.has(id): items[id] = []
	items[id].append([xf, Color(col.r, col.g, col.b, 1.0)])

# Steel Accord - combat visual effects: explosions, weapon effects, impacts, deaths, wrecks and ruins.
#
# ---------------------------------------------------------------------------------------------- FX API
# All functions are static. `parent` is the Battle node (or any node inside the battle scene). Effects are
# presentation only: callers on the simulation path only enqueue a request; FXDirector (fx_director.gd, one node
# under the Battle) builds the particles in _process with pooling, particle / light / decal caps, distance and
# off-screen LOD and the Low / Medium / High graphics preset. No effect touches battle.rng or gameplay state.
#
#   FX.explosion(parent, pos, s := 1.0, size := "")
#       Layered blast: flash + light pulse, fireball (flipbook) rolling into a smoke column, sparks and embers,
#       debris chunks with gravity, ground dust ring, shock ring (huge), scorch decal, camera shake (large, huge;
#       Options toggle). `size` = "small" (grenade) | "medium" (tank shell, rocket) | "large" (bomb, vehicle death)
#       | "huge" (strategic bomb). Without `size` the legacy scale `s` picks one (<0.7 small, <1.0 medium,
#       <1.9 large, else huge) and also scales within the size. Airbursts (> 3 m above ground) skip ring + scorch.
#   FX.impact_kind(parent, pos, kind, surface := "ground")
#       Projectile impact. kind = "bullet" | "cannon" (20-40 mm) | "shell" (tank / 105 mm) | "rocket" | "bomb"
#       | "arty" (howitzer). surface = "ground" (dust) | "armour" (sparks) | "structure" (concrete chips + dust)
#       | "infantry" (dust puff, no gore) | "air". This is the entry point for new weapons (e.g. AC-130 guns).
#   FX.muzzle(parent, pos, dir, kind)
#       Muzzle effect sized per weapon: "rifle" | "mg" | "autocannon" | "air_cannon" | "tank" (flash, blast
#       cloud, ground dust ring) | "howitzer" | "rocket" (AT launch with back-blast) | "missile" (launch puff).
#   FX.muzzle_kind(shooter, w) -> String      classifies a weapon dictionary for FX.muzzle / tracer_node.
#   FX.tracer_node(kind, lit) -> Node3D       projectile visual; lit = false gives an invisible round (tracers
#                                             are drawn on a fraction of rounds, chosen by the caller).
#   FX.missile_node(guided) -> Node3D         rocket / missile body with motor flame, glow and lingering trail.
#   FX.bomb_node() -> Node3D                  falling bomb with a light smoke trail.
#   FX.detach_trails(node)                    call before freeing a projectile: its smoke trail stays and fades.
#   FX.exhaust_trail(host, offset, width, contrail) -> CPUParticles3D   (aircraft exhaust / contrails)
#   FX.incoming(parent, pos, delay)           artillery whistle that ends at the impact (rate limited).
#   FX.unit_death(parent, u)                  vehicle: blast + delayed secondary + burning wreck that cools;
#                                             aircraft: burning trail while falling (FX.crash on impact);
#                                             infantry: small dust puff (the body falls / fades, no gore).
#   FX.crash(parent, node, pos)               aircraft wreck hits the ground: large blast + wreck fire.
#   FX.wreck_fire(host, size := 1.0, duration := 45.0)   burning wreck: fire + flicker light (cools), smoke.
#   FX.collapse(parent, b)                    structure destruction: staggered blasts, model sinks and tilts,
#                                             dust cloud, debris burst, camera shake. The ruin itself is FXRuin.
#   FX.ruin(parent, root, bkind, half, seed, age)  persistent ruin of a structure (FXRuin, fx_ruin.gd).
#   FX.scorch(parent, pos, size)              scorch decal (pooled ring buffer, fades out).
#   Legacy wrappers kept for other callers: muzzle_flash, small_flash, impact, bullet_hit, launch_puff,
#   tracer_mesh, target_marker, order_marker.
# -------------------------------------------------------------------------------------------------------
class_name FX

const DIR := "res://assets/fx/"

## Explosion sizes. r = radius scale (m); counts are particles at High density, before LOD and caps.
const SIZES := {
	"small": {"r": 0.9, "s": 0.5, "fire": 5, "smoke": 5, "smoke_life": 2.4, "sparks": 8, "embers": 0, "debris": 3, "ring": 0, "dust": 6,
		"scorch": 2.6, "light": [5.0, 9.0], "shake": 0.0},
	"medium": {"r": 1.6, "s": 0.9, "fire": 10, "smoke": 10, "smoke_life": 4.0, "sparks": 18, "embers": 4, "debris": 7, "ring": 12, "dust": 10,
		"scorch": 5.0, "light": [10.0, 18.0], "shake": 0.0},
	"large": {"r": 2.8, "s": 1.4, "fire": 18, "smoke": 18, "smoke_life": 6.5, "sparks": 32, "embers": 10, "debris": 14, "ring": 22, "dust": 16,
		"scorch": 8.5, "light": [18.0, 32.0], "shake": 0.3},
	"huge": {"r": 4.6, "s": 2.2, "fire": 30, "smoke": 30, "smoke_life": 9.0, "sparks": 50, "embers": 18, "debris": 24, "ring": 36, "dust": 26,
		"scorch": 14.0, "light": [26.0, 60.0], "shake": 0.75, "shock": true},
}

## Muzzle effects per weapon class: flash size (m), light energy (0 = none), smoke puffs, ground dust ring.
const MUZZLE := {
	"rifle": {"flash": 0.7, "light": 0.0, "smoke": 2, "ring": 0, "every": 4},
	"mg": {"flash": 1.0, "light": 2.0, "smoke": 2, "ring": 0, "every": 3},
	"autocannon": {"flash": 1.6, "light": 4.0, "smoke": 4, "ring": 0, "every": 2},
	"air_cannon": {"flash": 2.2, "light": 4.0, "smoke": 3, "ring": 0, "every": 2},
	"tank": {"flash": 3.6, "light": 10.0, "smoke": 14, "ring": 14, "every": 1},
	"howitzer": {"flash": 4.6, "light": 14.0, "smoke": 20, "ring": 18, "every": 1},
	"rocket": {"flash": 1.6, "light": 4.0, "smoke": 8, "ring": 0, "every": 1},
	"missile": {"flash": 1.2, "light": 3.0, "smoke": 8, "ring": 0, "every": 1},
}

## Per-preset effect budget. density scales counts; caps bound what is alive at once.
const QUALITY := {
	"Low": {"density": 0.45, "particles": 1600, "lights": 4, "decals": 24, "ops": 24, "detail": false, "lit_smoke": false,
		"soft": false, "near": 120.0, "far": 220.0, "linger": 0.5, "decal_life": 45.0},
	"Medium": {"density": 0.75, "particles": 4000, "lights": 10, "decals": 60, "ops": 48, "detail": true, "lit_smoke": false,
		"soft": false, "near": 150.0, "far": 300.0, "linger": 0.8, "decal_life": 90.0},
	"High": {"density": 1.0, "particles": 8000, "lights": 20, "decals": 120, "ops": 80, "detail": true, "lit_smoke": false,
		"soft": true, "near": 180.0, "far": 380.0, "linger": 1.0, "decal_life": 150.0},
}

## Colour ramps (over particle life) and size curves, by id.
const RAMPS := {
	"blast_smoke": [Color(0.45, 0.3, 0.18, 0.0), Color(0.16, 0.14, 0.12, 0.92), Color(0.24, 0.23, 0.22, 0.7), Color(0.36, 0.35, 0.34, 0.32), Color(0.42, 0.41, 0.4, 0)],
	"chips": [Color(0.62, 0.6, 0.56, 1), Color(0.55, 0.53, 0.5, 1)],
	"collapse_dust": [Color(0.6, 0.55, 0.47, 0.0), Color(0.56, 0.51, 0.44, 0.85), Color(0.55, 0.51, 0.45, 0.5), Color(0.55, 0.52, 0.47, 0)],
	"concrete_dust": [Color(0.7, 0.68, 0.64, 0.0), Color(0.68, 0.66, 0.62, 0.75), Color(0.66, 0.65, 0.62, 0)],
	"debris": [Color(0.35, 0.31, 0.27, 1), Color(0.3, 0.27, 0.24, 1)],
	"dust": [Color(0.55, 0.48, 0.38, 0.0), Color(0.52, 0.46, 0.37, 0.7), Color(0.5, 0.45, 0.38, 0.3), Color(0.5, 0.46, 0.4, 0)],
	"dust_ring": [Color(0.62, 0.55, 0.44, 0.0), Color(0.6, 0.53, 0.42, 0.75), Color(0.58, 0.52, 0.43, 0.35), Color(0.56, 0.51, 0.44, 0)],
	"embers": [Color(1, 0.8, 0.4, 1), Color(1, 0.4, 0.05, 0.9), Color(0.5, 0.1, 0.0, 0)],
	"fireball": [Color(1, 1, 1, 1), Color(1, 0.9, 0.8, 0.95), Color(1, 0.7, 0.5, 0.6), Color(0.6, 0.3, 0.2, 0)],
	"flash": [Color(1, 1, 0.9, 1), Color(1, 0.8, 0.4, 0.8), Color(1, 0.5, 0.1, 0)],
	"gunsmoke": [Color(0.8, 0.78, 0.74, 0.0), Color(0.72, 0.7, 0.66, 0.55), Color(0.7, 0.69, 0.66, 0.25), Color(0.7, 0.7, 0.68, 0)],
	"motor": [Color(1, 0.95, 0.8, 1), Color(1, 0.6, 0.2, 0.6), Color(1, 0.3, 0.05, 0)],
	"puff": [Color(0.56, 0.49, 0.38, 0.0), Color(0.52, 0.46, 0.36, 0.8), Color(0.5, 0.45, 0.37, 0)],
	"sparks": [Color(1, 0.95, 0.75, 1), Color(1, 0.6, 0.15, 1), Color(0.8, 0.2, 0.0, 0)],
	"trail": [Color(1.0, 0.85, 0.6, 0.0), Color(0.86, 0.85, 0.82, 0.62), Color(0.8, 0.8, 0.78, 0.3), Color(0.75, 0.75, 0.74, 0)],
	"wreck_fire": [Color(1, 1, 1, 0.0), Color(1, 0.95, 0.85, 0.95), Color(1, 0.7, 0.45, 0.5), Color(0.5, 0.2, 0.1, 0)],
	"wreck_smoke": [Color(0.1, 0.09, 0.08, 0.0), Color(0.09, 0.085, 0.08, 0.85), Color(0.2, 0.19, 0.18, 0.5), Color(0.3, 0.3, 0.3, 0)],
}
const CURVES := {
	"debris": [Vector2(0, 1.0), Vector2(0.85, 1.0), Vector2(1, 0.0)],
	"dust_grow": [Vector2(0, 0.4), Vector2(1, 1.8)],
	"fireball": [Vector2(0, 0.45), Vector2(0.25, 1.0), Vector2(1, 1.45)],
	"flame": [Vector2(0, 0.5), Vector2(0.3, 1.0), Vector2(1, 0.4)],
	"smoke_grow": [Vector2(0, 0.5), Vector2(0.3, 1.1), Vector2(1, 2.4)],
	"trail": [Vector2(0, 0.35), Vector2(0.25, 1.0), Vector2(1, 2.8)],
}

static var _tex := {}
static var _mats := {}
static var _quads := {}
static var _ramps := {}
static var _curves := {}
static var _soft: GradientTexture2D
static var _kit: Dictionary = {}


static func quality() -> Dictionary:
	return QUALITY.get(str(Game.settings.get("graphics", "Medium")), QUALITY.Medium)


static func preset() -> String:
	var g := str(Game.settings.get("graphics", "Medium"))
	return g if QUALITY.has(g) else "Medium"


static func tex(id: String) -> Texture2D:
	if not _tex.has(id):
		_tex[id] = load(DIR + id + ".png")
	return _tex[id]


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


## Shared materials (one per kind and preset): smoke, dust, fire, spark, flash, soft, debris, ring, tracer.
static func mat(kind: String) -> Material:
	var q := quality()
	var key := "%s|%s" % [kind, preset()]
	if _mats.has(key): return _mats[key]
	var m := StandardMaterial3D.new()
	m.vertex_color_use_as_albedo = true
	m.disable_receive_shadows = true
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.billboard_keep_scale = true   # without it particle scale_amount / scale curves are ignored by the billboard
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	match kind:
		"smoke", "dust":
			m.albedo_texture = tex("smoke_atlas" if kind == "smoke" else "dust_atlas")
			m.particles_anim_h_frames = 4; m.particles_anim_v_frames = 4; m.particles_anim_loop = false
			if q.lit_smoke: m.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL; m.roughness = 1.0
			if q.soft: m.proximity_fade_enabled = true; m.proximity_fade_distance = 1.6
		"fire":
			m.albedo_texture = tex("fire_atlas")
			m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
			m.particles_anim_h_frames = 4; m.particles_anim_v_frames = 4; m.particles_anim_loop = false
		"spark":
			m.albedo_texture = tex("spark"); m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		"flash":
			m.albedo_texture = tex("flash"); m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		"soft":
			m.albedo_texture = _sprite(); m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
		"softmix":
			m.albedo_texture = _sprite()
		"debris":
			m.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
			m.billboard_mode = BaseMaterial3D.BILLBOARD_DISABLED
			m.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
			m.disable_receive_shadows = false
			m.albedo_texture = tex("concrete_detail"); m.uv1_triplanar = true; m.uv1_scale = Vector3(2, 2, 2)
			m.roughness = 1.0
		"ring":
			m.albedo_texture = tex("ring")
			m.billboard_mode = BaseMaterial3D.BILLBOARD_DISABLED
			m.cull_mode = BaseMaterial3D.CULL_DISABLED
		"tracer":
			m.vertex_color_use_as_albedo = false
			m.billboard_mode = BaseMaterial3D.BILLBOARD_DISABLED
			m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
			m.albedo_color = Color(1.0, 0.72, 0.35)
	_mats[key] = m
	return m


## Unit quad (or debris chunk mesh) carrying the shared material; particle size comes from the scale range.
static func quad(kind: String) -> Mesh:
	var key := "%s|%s" % [kind, preset()]
	if _quads.has(key): return _quads[key]
	var mesh: Mesh
	if kind == "debris":
		var src: Mesh = kit_mesh("chunk_a")
		if src:
			var am := ArrayMesh.new()
			am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, src.surface_get_arrays(0))
			am.surface_set_material(0, mat("debris"))
			mesh = am
		else:
			var b := BoxMesh.new(); b.size = Vector3(1, 0.7, 0.8); b.material = mat("debris"); mesh = b
	else:
		var q := QuadMesh.new(); q.size = Vector2(1, 1); q.material = mat(kind)
		mesh = q
	_quads[key] = mesh
	return mesh


## Ruin kit pieces (assets/fx/ruin_kit.glb): name -> Mesh, loaded once.
static func kit_mesh(id: String) -> Mesh:
	if _kit.is_empty():
		var path := DIR + "ruin_kit.glb"
		if ResourceLoader.exists(path):
			var inst: Node = (load(path) as PackedScene).instantiate()
			for mi in inst.find_children("*", "MeshInstance3D", true, false):
				_kit[String(mi.name)] = (mi as MeshInstance3D).mesh
			inst.free()
		_kit["_loaded"] = null
	return _kit.get(id)


static func ramp(id: String) -> Gradient:
	if _ramps.has(id): return _ramps[id]
	var g := _ramp(RAMPS[id])
	_ramps[id] = g
	return g


static func curve(id: String) -> Curve:
	if _curves.has(id): return _curves[id]
	var c := Curve.new()
	c.max_value = 4.0
	for p in CURVES[id]: c.add_point(p)
	_curves[id] = c
	return c


static func _ramp(cols: Array) -> Gradient:
	var g := Gradient.new()
	g.set_color(0, cols[0]); g.set_color(1, cols[cols.size() - 1])
	for i in range(1, cols.size() - 1):
		g.add_point(float(i) / (cols.size() - 1), cols[i])
	return g


static func director(parent: Node) -> FXDirector:
	return FXDirector.get_for(parent)


# ---------------------------------------------------------------------------------------- explosions
static func size_of(s: float) -> String:
	if s < 0.7: return "small"
	if s < 1.0: return "medium"
	if s < 1.9: return "large"
	return "huge"


static func explosion(parent: Node, pos: Vector3, s := 1.0, size := "") -> void:
	var sz := size if SIZES.has(size) else size_of(s)
	var k := 1.0 if size != "" else clampf(s / float(SIZES[sz].s), 0.8, 1.25)
	var d := director(parent)
	if d: d.later(0.0, d.explosion.bind(pos, sz, k, true))


static func scorch(parent: Node, pos: Vector3, size: float) -> void:
	var d := director(parent)
	if d: d.later(0.0, d.decal.bind(pos, size, "scorch"))


# ---------------------------------------------------------------------------------------- impacts
static func impact_kind(parent: Node, pos: Vector3, kind: String, surface := "ground") -> void:
	var d := director(parent)
	if d: d.later(0.0, d.impact.bind(pos, kind, surface))


static func impact(parent: Node, pos: Vector3, hit_armour: bool) -> void:
	impact_kind(parent, pos, "shell", "armour" if hit_armour else "ground")


static func bullet_hit(parent: Node, pos: Vector3, armour: bool, heavy := false) -> void:
	impact_kind(parent, pos, "cannon" if heavy else "bullet", "armour" if armour else "ground")


# ---------------------------------------------------------------------------------------- weapons
static func muzzle_kind(shooter: Node, w: Dictionary) -> String:
	var id := str(w.get("id", ""))
	match str(w.get("proj", "")):
		"arty": return "howitzer"
		"rocket": return "rocket"
		"missile": return "rocket" if shooter != null and shooter.def.get("visual") == "infantry" else "missile"
		"shell": return "autocannon" if float(w.get("damage", 100.0)) < 60.0 else "tank"
	if id == "gau_cannon" or (shooter != null and shooter.is_air() and float(w.get("damage", 0.0)) >= 15.0): return "air_cannon"
	if shooter != null and shooter.def.get("visual") == "infantry" and not id in ["m249", "m240"]: return "rifle"
	return "mg"


static func tracer_every(kind: String) -> int:
	return int(MUZZLE.get(kind, MUZZLE.mg).every)


static func muzzle(parent: Node, pos: Vector3, dir: Vector3, kind: String) -> void:
	var d := director(parent)
	if d: d.later(0.0, d.muzzle.bind(pos, dir, kind))


static func muzzle_flash(parent: Node, pos: Vector3, dir: Vector3) -> void:
	muzzle(parent, pos, dir, "tank")


static func small_flash(parent: Node, pos: Vector3) -> void:
	muzzle(parent, pos, Vector3.FORWARD, "mg")


static func launch_puff(parent: Node, pos: Vector3) -> void:
	muzzle(parent, pos, Vector3.UP, "missile")


static func incoming(parent: Node, pos: Vector3, delay: float) -> void:
	var d := director(parent)
	if d: d.later(maxf(0.0, delay), d.whistle.bind(pos))


static var _tracers := {}


## Glowing tracer streak (shared mesh per kind); lit = false returns an empty node (round without tracer).
static func tracer_node(kind: String, lit := true) -> Node3D:
	if not lit: return Node3D.new()
	var dims: Vector2 = {"rifle": Vector2(0.05, 2.0), "mg": Vector2(0.08, 3.2), "autocannon": Vector2(0.14, 4.0),
		"air_cannon": Vector2(0.2, 6.0), "tank": Vector2(0.14, 3.0), "howitzer": Vector2(0.12, 1.6)}.get(kind, Vector2(0.1, 3.0))
	return tracer_mesh(dims.x, dims.y)


static func tracer_mesh(width := 0.12, length := 4.0) -> MeshInstance3D:
	var key := "%.2f|%.2f" % [width, length]
	if not _tracers.has(key):
		var b := BoxMesh.new(); b.size = Vector3(width, width, length)
		b.material = mat("tracer")
		_tracers[key] = b
	var mi := MeshInstance3D.new()
	mi.mesh = _tracers[key]
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


static var _missile_body := {}
static var _glows := {}


## Camera-facing additive glow quad, shared per size and colour.
static func glow_mesh(size: float, col: Color) -> QuadMesh:
	var key := "%.2f|%s|%s" % [size, col.to_html(), preset()]
	if not _glows.has(key):
		var gq := QuadMesh.new(); gq.size = Vector2(size, size)
		var gm := mat("soft").duplicate() as StandardMaterial3D
		gm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		gm.vertex_color_use_as_albedo = false
		gm.albedo_color = col
		gq.material = gm
		_glows[key] = gq
	return _glows[key]


## Missile / rocket body with motor flame + glow and a lingering smoke trail (world-space particles).
static func missile_node(guided: bool) -> Node3D:
	var n := Node3D.new()
	var key := "g" if guided else "r"
	if not _missile_body.has(key):
		var c := CylinderMesh.new()
		c.top_radius = 0.09; c.bottom_radius = 0.09; c.height = 1.6 if guided else 1.1; c.radial_segments = 8; c.rings = 1
		var m := StandardMaterial3D.new(); m.albedo_color = Color(0.78, 0.78, 0.74); m.roughness = 0.5
		c.material = m
		_missile_body[key] = c
	var body := MeshInstance3D.new()
	body.mesh = _missile_body[key]; body.rotation.x = PI / 2
	body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	n.add_child(body)
	# motor: bright additive core + flame tongue (flash sprite) + glow
	var flame := CPUParticles3D.new()
	flame.mesh = quad("flash"); flame.amount = 6; flame.lifetime = 0.08; flame.local_coords = true
	flame.direction = Vector3(0, 0, 1); flame.spread = 4.0; flame.initial_velocity_min = 6.0; flame.initial_velocity_max = 10.0
	flame.gravity = Vector3.ZERO; flame.scale_amount_min = 0.7; flame.scale_amount_max = 1.1
	flame.color_ramp = ramp("motor")
	flame.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	flame.position.z = 0.8 if guided else 0.55
	n.add_child(flame)
	flame.emitting = true
	var glow := MeshInstance3D.new()
	glow.mesh = glow_mesh(1.1, Color(1, 0.7, 0.35, 0.9)); glow.position.z = flame.position.z
	glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	n.add_child(glow)
	var q := quality()
	var p := CPUParticles3D.new()
	p.mesh = quad("smoke")
	p.lifetime = (3.2 if guided else 2.4) * (0.6 if preset() == "Low" else 1.0)
	p.amount = int((70 if guided else 48) * float(q.density))
	p.local_coords = false
	p.direction = Vector3(0, 0, 1); p.spread = 6.0
	p.initial_velocity_min = 0.3; p.initial_velocity_max = 1.2
	p.gravity = Vector3(0.35, 0.5, 0.15)
	p.damping_min = 0.5; p.damping_max = 1.0
	p.angle_min = 0.0; p.angle_max = 360.0
	p.anim_offset_max = 1.0
	p.scale_amount_min = 0.7; p.scale_amount_max = 1.1
	p.scale_amount_curve = curve("trail")
	p.color_ramp = ramp("trail")
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.position.z = flame.position.z + 0.2
	p.set_meta("fx_trail", true)
	n.add_child(p)
	p.emitting = true
	return n


## Projectile reached its target: hand its smoke trail to the director so the trail lingers and fades.
static func detach_trails(node: Node) -> void:
	if node == null or not is_instance_valid(node) or not node.is_inside_tree(): return
	var d := director(node)
	if d == null: return
	for c in node.get_children():
		if c is CPUParticles3D and c.has_meta("fx_trail"):
			d.adopt(c, c.lifetime + 0.2)


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
	var t := exhaust_trail(n, Vector3(0, 0, 1.6), 0.7, true)
	t.set_meta("fx_trail", true)
	return n


## World-space smoke / contrail emitter attached to a moving node (offset in the node's local space; +Z is aft).
static func exhaust_trail(host: Node3D, offset: Vector3, width: float, contrail: bool) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.mesh = quad("smoke")
	p.amount = int((60 if contrail else 36) * maxf(0.5, float(quality().density)))
	p.lifetime = 2.6 if contrail else 1.1
	p.local_coords = false
	p.direction = Vector3(0, 0, 1); p.spread = 5.0
	p.initial_velocity_min = 0.2; p.initial_velocity_max = 0.8
	p.gravity = Vector3(0, 0.3, 0)
	p.angle_max = 360.0; p.anim_offset_max = 1.0
	p.scale_amount_min = width * 0.8; p.scale_amount_max = width * 1.2
	var cv := Curve.new(); cv.max_value = 4.0; cv.add_point(Vector2(0, 0.6)); cv.add_point(Vector2(1, 2.6 if contrail else 1.8))
	p.scale_amount_curve = cv
	var col := Color(0.95, 0.95, 0.95, 0.55) if contrail else Color(0.55, 0.53, 0.5, 0.35)
	p.color_ramp = _ramp([col, Color(col.r, col.g, col.b, col.a * 0.4), Color(col.r, col.g, col.b, 0)])
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	p.position = offset
	host.add_child(p)
	p.emitting = true
	if not contrail:
		var glow := MeshInstance3D.new()
		glow.mesh = glow_mesh(width * 1.6, Color(1, 0.7, 0.4, 0.8)); glow.position = offset
		glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		host.add_child(glow)
	return p


# ---------------------------------------------------------------------------------------- deaths and wrecks
static func unit_death(parent: Node, u: Node) -> void:
	var d := director(parent)
	if d: d.later(0.0, d.unit_death.bind(u))


static func crash(parent: Node, node: Node3D, pos: Vector3) -> void:
	var d := director(parent)
	if d: d.later(0.0, d.crash.bind(node, pos))


## Burning wreck on `host`: fire with a flickering light that dies down after ~40 % of `duration`, smoke that
## thins out and stops at `duration` (scaled by the preset). size 1 = tank.
static func wreck_fire(host: Node3D, size := 1.0, duration := 45.0) -> void:
	var d := director(host)
	if d: d.later(0.0, d.wreck_fire.bind(host, size, duration, Vector3(0, 1.4 * size, 0)))


static func collapse(parent: Node, b: Node) -> void:
	var d := director(parent)
	if d: d.collapse(b)   # the model copy is taken now (the building hides its model right after); effects queue


## Build the persistent ruin of a structure into `root` (see FXRuin). Queued: the ruin appears next frame.
static func ruin(parent: Node, root: Node3D, bkind: String, half: Vector2, seed_id: int, age := 0.0) -> void:
	var d := director(parent)
	if d: d.later(0.0, d.build_ruin.bind(root, bkind, half, seed_id, age))


# ---------------------------------------------------------------------------------------- markers (UI)
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

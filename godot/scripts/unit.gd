# Steel Accord - a combat unit: ground vehicle, helicopter or jet. Simulated only from Battle.sim_tick (fixed step).
# Orders: move (with queued waypoints), attack unit, attack-move, guard area / guard unit, force-fire ground, stop,
# return-to-base (jets). Aircraft are sprite-based (top-down concept art on a horizontal quad) - see UnitDefs.
class_name Unit
extends Node3D

enum S { IDLE, MOVE, ATTACK, ATTACK_MOVE, GUARD, FORCE_GROUND, RETURN, LANDED, BUILD, HAUL }

var uid := 0
var team := 0
var kind := ""
var def: Dictionary
var domain := "ground"        # ground | heli | jet  (also the targeting layer)
var hp := 1.0
var battle: Node
var dead := false
var selected := false

var state := S.IDLE
var goal := Vector3.ZERO
var queue: Array = []         # further waypoints after the current move (Vector3)
var path := PackedVector3Array()
var path_i := 0
var repath_t := 0.0
var target: Unit = null
var forced_target := false
var force_pos := Vector3.ZERO
var guard_pos := Vector3.ZERO
var guard_unit: Unit = null
var home := Vector3.ZERO      # aircraft pad / rearm point

var heading := 0.0
var speed_cur := 0.0
var vel := Vector3.ZERO
var turret_yaw := 0.0
var recoil := 0.0
var altitude := 0.0
var bank := 0.0
var w_reload: Array = []
var w_ammo: Array = []
var rearm_t := 0.0
var airborne := true
var run_out_t := 0.0
var ret_phase := 0
var site: Node = null          # dozer: structure under construction
var haul_depot: Node = null    # hauler: supply depot it delivers to
var haul_phase := 0            # 0 fly to pile, 1 loading, 2 fly to depot, 3 unloading
var haul_t := 0.0
var cargo := 0
var haul_pile: Dictionary = {}
var idle_t := 0.0

var model: Node3D
var body: Node3D              # visual root (lifted for aircraft)
var turret: Node3D
var gun: Node3D
var muzzle: Node3D
var rotor: Node3D
var rotors: Array[Node3D] = []
var engine_snd: AudioStreamPlayer3D
var flyby_t := 0.0
var takeoff_snd := false
var ring: MeshInstance3D
var mats: Array = []
var gun_rest := Vector3.ZERO


func setup(b: Node, unit_kind: String, t: int, id: int, pos: Vector3, yaw: float) -> void:
	battle = b; kind = unit_kind; def = UnitDefs.def_of(unit_kind); team = t; uid = id
	domain = def.get("domain", "ground")
	hp = def.hp
	name = "%s_%d" % [unit_kind, id]
	for w in def.weapons:
		w_reload.append(0.0)
		w_ammo.append(int(w.get("ammo", -1)))
	body = Node3D.new()
	add_child(body)
	var visual: String = def.get("visual", "model")
	var m3: String = str(def.get("model3d", ""))
	if m3 != "" and ResourceLoader.exists(m3):
		_build_model3d(m3)
		if domain != "ground": altitude = def.altitude
	elif visual == "vehicle_art" or visual == "infantry":
		_build_card_visual(visual)
	elif domain == "ground":
		model = load(def.model).instantiate()
		body.add_child(model)
		mats = UnitArt.apply(model, def.ao_prefix, UnitDefs.TEAM_COLORS[team], id)
		turret = model.find_child("Turret", true, false) as Node3D
		gun = model.find_child("Gun", true, false) as Node3D
		muzzle = model.find_child("Muzzle", true, false) as Node3D
		if gun: gun_rest = gun.position
		_add_contact_shadow()
	else:
		_build_sprite()
		altitude = def.altitude
	_apply_scale_guide()
	ring = _make_ring()
	if domain == "ground":
		add_child(ring)
	else:
		body.add_child(ring)   # aircraft: ring flies with the airframe so it surrounds what the player sees
		ring.position.y = -0.2
	position = pos
	home = pos
	heading = yaw
	rotation.y = heading
	body.position.y = altitude
	if domain == "jet":
		speed_cur = def.min_speed


# ---- real 3D unit models (pilot set). Origin at ground contact; parts driven from movement (presentation only).
var wheels: Array[Node3D] = []
var wheel_r := 0.4
var track_mats: Array = []
var track_m_per_v := 1.0
var anim: AnimationPlayer
var anim_cur := ""
var _last_vis_pos := Vector3.ZERO
var stride := {"walk": 1.4, "run": 4.5}


func _build_model3d(path: String) -> void:
	model = (load(path) as PackedScene).instantiate()
	body.add_child(model)
	for n in model.find_children("*", "Node3D", true, false):
		var nm := String(n.name)
		if nm.begins_with("Wheel") or nm.begins_with("Sprocket") or nm.begins_with("Idler"):
			wheels.append(n)
		if nm == "RotorFront" or nm == "RotorRear":
			n.set_meta("dir", 1.0 if nm == "RotorFront" else -1.0)
			rotors.append(n)
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			for si in mi.mesh.get_surface_count():
				var mat := mi.get_active_material(si)
				if mat and mat.resource_name.begins_with("SA_Team") and mat is BaseMaterial3D:
					var tm := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
					tm.albedo_color = UnitDefs.TEAM_COLORS[team].lightened(0.15)
					mi.set_surface_override_material(si, tm)
				if mat and mat.resource_name.begins_with("SA_TrackScroll") and mat is BaseMaterial3D:
					var dm := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
					mi.set_surface_override_material(si, dm)
					track_mats.append(dm)
	if not rotors.is_empty(): rotor = rotors[0]
	track_m_per_v = float(def.get("track_m_per_v", 1.0))
	wheel_r = float(def.get("wheel_radius", 0.0))
	if wheel_r <= 0.0:
		wheel_r = 0.4
		for w in wheels:
			if w is MeshInstance3D:
				wheel_r = maxf(0.1, (w as MeshInstance3D).get_aabb().size.y * 0.5); break
	var aps := model.find_children("*", "AnimationPlayer", true, false)
	if not aps.is_empty():
		anim = aps[0]
		for k in ["idle", "walk", "run", "aim", "fire", "crouch_fire"]:
			if anim.has_animation(k): anim.get_animation(k).loop_mode = Animation.LOOP_LINEAR
		stride = def.get("stride", stride)
		_play("idle")
	if domain == "ground": _add_team_marker()
	_last_vis_pos = position


func _play(a: String, spd := 1.0) -> void:
	if anim == null or not anim.has_animation(a): return
	if anim_cur != a:
		anim.play(a, 0.15)
		anim_cur = a
	anim.speed_scale = spd


## Presentation for 3D models (every rendered frame): wheels turn and tracks scroll by distance travelled; infantry
## animation follows what the soldier is doing, with walk/run playback matched to ground speed.
func _update_model3d(dt: float) -> void:
	var moved := (global_position - _last_vis_pos)
	moved.y = 0.0
	var dist := moved.length() * (1.0 if moved.dot(forward()) >= 0.0 else -1.0)
	_last_vis_pos = global_position
	if absf(dist) > 5.0: dist = 0.0      # teleport / spawn
	for w in wheels: w.rotate_object_local(Vector3.RIGHT, -dist / maxf(wheel_r * vis_scale, 0.05))
	for m in track_mats: (m as BaseMaterial3D).uv1_offset.y -= dist / (track_m_per_v * vis_scale)
	if anim:
		var spd := speed_cur
		if dead: _play("die")
		elif spd > 0.3:
			var k := "run" if spd > def.speed * 0.6 else "walk"
			_play(k, spd / (float(stride.get(k, 1.4)) * vis_scale))
		elif target != null: _play("fire")
		else: _play("idle")


var vis: Node3D               # visual root under body, carries the scale-guide factor
var vis_scale := 1.0


## World-scale guide (docs/SCALE_GUIDE.md): art is authored at real size; the game draws each class at a fixed factor
## so that structures stay dominant. Hit / selection radius follow the drawn size.
func _apply_scale_guide() -> void:
	vis_scale = UnitDefs.scale_for(def)
	vis = Node3D.new()
	vis.name = "Vis"
	for c in body.get_children():
		body.remove_child(c)
		vis.add_child(c)
	body.add_child(vis)
	vis.scale = Vector3.ONE * vis_scale
	if def.get("visual", "") != "infantry":
		def = def.duplicate()
		def.radius = float(def.radius) * vis_scale


var card_sprite: Sprite3D
var views := {}               # view name -> [Texture2D, faces_right: bool]
var anim_t := 0.0


## Ground units from the supplied concept art: a camera-facing card. Vehicles pick the front 3/4, side or rear 3/4
## view (mirrored as needed) from the angle between their heading and the camera; infantry pick a pose from what
## they are doing and face their movement direction.
func _build_card_visual(visual: String) -> void:
	var s := Sprite3D.new()
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	s.shaded = false
	s.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
	s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	s.centered = true
	s.name = "Sprite"
	body.add_child(s)
	card_sprite = s
	model = s
	if visual == "vehicle_art":
		var a: Dictionary = UsArt.vehicle(def.art)
		for vn in ["front34", "side", "rear34"]:
			var v: Dictionary = a.get(vn, {})
			if v.has("path"): views[vn] = [load(v.path), v.faces == "right"]
		var side_w := float((views["side"][0] as Texture2D).get_width()) if views.has("side") else 400.0
		s.pixel_size = float(def.length) / side_w * 1.05
		if a.has("icon"): def = def.duplicate(); def["icon"] = a.icon
	else:
		var a: Dictionary = UsArt.infantry(def.art)
		for pn in a.get("poses", {}):
			views[pn] = [load(a.poses[pn]), true]
		s.pixel_size = 1.0 / float(a.get("px_per_m", 280.0))     # life size; the scale guide enlarges infantry
		if a.has("icon"): def = def.duplicate(); def["icon"] = a.icon
	_add_team_marker()
	_update_card(0.0)


## Team-coloured ellipse under card units: a contact shadow with a coloured rim (readable on any terrain).
func _add_team_marker() -> void:
	var r: float = def.radius * (1.2 if def.get("visual") == "infantry" else 1.05)
	var mi := MeshInstance3D.new()
	var q := QuadMesh.new(); q.size = Vector2(r * 2.0, r * 2.0); q.orientation = PlaneMesh.FACE_Y
	var g := GradientTexture2D.new()
	g.fill = GradientTexture2D.FILL_RADIAL; g.fill_from = Vector2(0.5, 0.5); g.fill_to = Vector2(1.0, 0.5)
	var gr := Gradient.new()
	var tc: Color = UnitDefs.TEAM_COLORS[team].lightened(0.2)
	gr.set_color(0, Color(0, 0, 0, 0.55)); gr.set_color(1, Color(0, 0, 0, 0))
	gr.add_point(0.74, Color(0, 0, 0, 0.3)); gr.add_point(0.8, Color(tc.r, tc.g, tc.b, 0.75)); gr.add_point(0.86, Color(tc.r, tc.g, tc.b, 0.0))
	g.gradient = gr; g.width = 64; g.height = 64
	var m := StandardMaterial3D.new()
	m.albedo_texture = g; m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	q.material = m
	mi.mesh = q
	mi.position.y = 0.12
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.scale = Vector3(1.0, 1.0, 1.0 if def.get("visual") == "infantry" else 1.35)
	body.add_child(mi)


## Presentation only (called every rendered frame): choose the view / pose and mirroring.
func _update_card(dt: float) -> void:
	if card_sprite == null or views.is_empty(): return
	var cam := get_viewport().get_camera_3d() if is_inside_tree() else null
	var right := Vector3.RIGHT
	var away := Vector3.FORWARD
	if cam:
		right = cam.global_basis.x; right.y = 0.0; right = right.normalized()
		away = -cam.global_basis.z; away.y = 0.0; away = away.normalized()
	var f := forward()
	var sx := f.dot(right)            # +: nose points screen-right
	var sz := f.dot(away)             # +: nose points away from the camera
	var key := ""
	var want_right := sx >= 0.0
	if def.get("visual") == "vehicle_art":
		if sz < -0.38: key = "front34"
		elif sz > 0.38: key = "rear34"
		else: key = "side"
		if not views.has(key): key = views.keys()[0]
		# rear 3/4: the image's "faces" is the nose direction, which for a rear view points away-left/right
	else:
		anim_t += dt
		var moving := speed_cur > 0.4
		var firing := target != null and not moving
		var at4 := views.has("carry_stand")
		if moving:
			var fr := int(anim_t * (3.2 if speed_cur > def.speed * 0.6 else 2.4)) % 2
			if at4: key = "carry_walk" if fr == 0 else "carry_run"
			else: key = "walk" if fr == 0 else "run"
		elif firing:
			key = "aim_kneel" if at4 else "kneel"
		else:
			key = "carry_stand" if at4 else "stand"
		if dead: key = "prone" if views.has("prone") else key
		if not views.has(key): key = views.keys()[0]
	var v: Array = views[key]
	var tex: Texture2D = v[0]
	if card_sprite.texture != tex:
		card_sprite.texture = tex
		card_sprite.offset = Vector2(0, tex.get_height() * 0.5)   # stand on the ground point
	card_sprite.flip_h = (v[1] as bool) != want_right


func _process(dt: float) -> void:
	if card_sprite: _update_card(dt)
	elif anim or not wheels.is_empty() or not track_mats.is_empty(): _update_model3d(dt)


## Aircraft visual: the supplied top-down art on a horizontal, lit, shadow-casting quad (sprite-based, not a 3D model).
func _build_sprite() -> void:
	var tex: Texture2D = load(def.sprite)
	var s := Sprite3D.new()
	s.texture = tex
	s.axis = Vector3.AXIS_Y
	s.pixel_size = float(def.length) / float(tex.get_height()) * 1.08   # silhouette fills ~92% of the canvas
	s.shaded = true
	s.double_sided = true
	s.alpha_cut = SpriteBase3D.ALPHA_CUT_DISCARD
	s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	s.name = "Sprite"
	body.add_child(s)
	model = s
	if domain == "jet":
		FX.exhaust_trail(body, Vector3(0, 0.2, float(def.length) * 0.47), 0.9, false)
	if domain == "heli":
		_build_rotors(s, tex)


static var _blade_tex := {}


## Main rotor: the supplied airframe art has its blades baked in, which cannot spin. When the art importer has produced a
## blade-free airframe (assets/us/rotors/<id>_body.png) the sprite is swapped for it; separate blade discs then rotate.
func _build_rotors(s: Sprite3D, tex: Texture2D) -> void:
	var info: Dictionary = UsArt.rotor(kind)
	var n_bl := int(def.get("blades", 4))
	if info.is_empty():
		# fallback: procedural blades over the original sprite (its baked blades stay visible underneath)
		var n_h := 2 if def.get("rotor_twin", false) else 1
		for i in n_h:
			var z := 0.0 if n_h == 1 else (-0.36 if i == 0 else 0.36) * float(def.length)
			_add_rotor(Vector3(0, 0.6 + 0.15 * i, z), blade_texture(n_bl), def.rotor * 2.0, Vector3.ZERO, 1.0 if i == 0 else -1.0)
		rotor = rotors[0]
		return
	var bt: Texture2D = load(info.body)
	s.texture = bt
	s.pixel_size = float(def.length) / float(bt.get_height()) * 1.08
	var px := s.pixel_size
	var sz: Array = info.size_px
	var blade_files: Array = info.get("blades_per_hub", [info.blades])
	for i in info.hubs_px.size():
		var h: Array = info.hubs_px[i]
		var hub := Vector3((float(h[0]) - float(sz[0]) * 0.5) * px, 0.0, (float(h[1]) - float(sz[1]) * 0.5) * px)
		var btex: Texture2D = load(blade_files[mini(i, blade_files.size() - 1)])
		# the blade image shares the airframe canvas: offset the quad so it turns about this hub
		_add_rotor(hub + Vector3(0, 0.5 + 0.12 * i, 0), btex, float(sz[0]) * px, -hub, 1.0 if i == 0 else -1.0)
		# faint motion-blur disc so the spin reads at RTS zoom
		_add_rotor(hub + Vector3(0, 0.45 + 0.12 * i, 0), blade_texture(n_bl), def.rotor * 2.0, Vector3.ZERO, 1.0 if i == 0 else -1.0, 0.55)
	rotor = rotors[0]


func _add_rotor(pos: Vector3, t: Texture2D, size_m: float, offset: Vector3, dir: float, alpha := 1.0) -> void:
	var r := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(size_m, size_m)
	q.orientation = PlaneMesh.FACE_Y
	q.center_offset = offset
	var m := StandardMaterial3D.new()
	m.albedo_texture = t
	m.albedo_color = Color(1, 1, 1, alpha)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA if alpha < 1.0 else BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.roughness = 0.8
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	q.material = m
	r.mesh = q
	r.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF if alpha < 1.0 else GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	r.position = pos
	r.set_meta("dir", dir)
	body.add_child(r)
	rotors.append(r)


## Procedural blade disc: n dark tapered blades with a soft motion-blur wake trailing each blade, a faint disc, a hub.
static func blade_texture(n: int) -> Texture2D:
	if _blade_tex.has(n): return _blade_tex[n]
	var S := 256
	var img := Image.create(S, S, true, Image.FORMAT_RGBA8)
	var c := S * 0.5
	for y in S:
		for x in S:
			var dx := (x + 0.5 - c) / c
			var dy := (y + 0.5 - c) / c
			var rr := sqrt(dx * dx + dy * dy)
			if rr > 1.0: img.set_pixel(x, y, Color(0, 0, 0, 0)); continue
			var ang := atan2(dy, dx)
			var a := 0.05 * smoothstep(1.0, 0.9, rr)          # faint disc
			var best := 0.0
			for b in n:
				var d := wrapf(ang - TAU * b / n, -PI, PI)      # angle past blade b
				var half_w := (0.055 - 0.02 * rr) / maxf(rr, 0.08)   # blade chord in radians (tapers outward)
				if absf(d) < half_w:
					best = 1.0
				elif d < 0.0 and d > -0.9:
					best = maxf(best, 0.42 * pow(1.0 + d / 0.9, 2.2))   # wake behind the blade
			a = maxf(a, best * smoothstep(1.0, 0.95, rr) * smoothstep(0.06, 0.12, rr))
			var col := Color(0.07, 0.075, 0.07, a)
			if rr < 0.08: col = Color(0.12, 0.12, 0.11, 1.0)
			img.set_pixel(x, y, col)
	img.generate_mipmaps()
	var t := ImageTexture.create_from_image(img)
	_blade_tex[n] = t
	return t


func _make_ring() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var t := TorusMesh.new()
	var r: float = def.radius * (1.35 if domain == "ground" else 1.1)
	t.inner_radius = r; t.outer_radius = r + 0.35; t.rings = 40; t.ring_segments = 4
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0.35, 1.0, 0.45) if team == 0 else Color(1.0, 0.3, 0.25)
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
	body.add_child(d)


func set_selected(v: bool) -> void:
	selected = v
	if ring: ring.visible = v and not dead


func is_air() -> bool:
	return domain != "ground"


func forward() -> Vector3:
	return Vector3(-sin(heading), 0, -cos(heading))


func flat_dist(p: Vector3) -> float:
	return Vector2(p.x - position.x, p.z - position.z).length()


func world_center() -> Vector3:
	return global_position + Vector3.UP * (altitude + (1.4 if domain == "ground" else 0.5))


func can_target(o: Unit) -> bool:
	for w in def.weapons:
		if o.domain in w.targets: return true
	return false


func max_range_vs(o: Unit) -> float:
	var r := 0.0
	for w in def.weapons:
		if o.domain in w.targets: r = maxf(r, w.range)
	return r


func has_ammo() -> bool:
	if def.weapons.is_empty(): return false
	for i in w_ammo.size():
		if w_ammo[i] != 0: return true
	return false


# ------------------------------------------------------------------ orders (executed by Battle at tick start)
func _clear() -> void:
	target = null; forced_target = false; guard_unit = null; queue.clear()


func order_move(p: Vector3, append := false) -> void:
	if append and state == S.MOVE:
		queue.append(p); return
	_clear(); state = S.MOVE; goal = p; _plan(p)


func order_attack_move(p: Vector3) -> void:
	_clear(); state = S.ATTACK_MOVE; goal = p; _plan(p)


func order_attack(t: Unit) -> void:
	if not can_target(t): return
	_clear(); state = S.ATTACK; target = t; forced_target = true
	path = PackedVector3Array(); path_i = 0; repath_t = 0.0


func order_force_ground(p: Vector3) -> void:
	_clear(); state = S.FORCE_GROUND; force_pos = p; goal = p
	path = PackedVector3Array(); path_i = 0; repath_t = 0.0


func order_guard(p: Vector3, u: Unit = null) -> void:
	_clear(); state = S.GUARD; guard_pos = p; guard_unit = u; goal = p; _plan(p)


## Dozer: go to the site and construct it.
func order_build(b: Node) -> void:
	_clear(); state = S.BUILD; site = b; goal = b.position; _plan(_site_approach())


func _site_approach() -> Vector3:
	var to: Vector3 = position - site.position
	to.y = 0.0
	if to.length() < 0.1: to = Vector3(0, 0, 1)
	to = to.normalized()
	return site.position + to * (absf(to.x) * site.half.x + absf(to.z) * site.half.y + 3.0)


## Supply hauler (CH-47): loops pile -> depot automatically until given another order.
func start_haul(depot: Node) -> void:
	_clear(); state = S.HAUL; haul_depot = depot; haul_phase = 0 if cargo == 0 else 2; haul_pile = {}


func order_stop() -> void:
	_clear(); state = S.IDLE
	path = PackedVector3Array(); path_i = 0
	if domain == "jet": goal = position


func order_return() -> void:
	if domain == "ground" or state == S.LANDED: return
	_clear(); state = S.RETURN; goal = home; ret_phase = 0


func _plan(p: Vector3) -> void:
	if domain == "ground":
		path = battle.find_path(position, p)
	else:
		path = PackedVector3Array([position, p])
	path_i = 1 if path.size() > 1 else 0
	repath_t = 1.0


# ------------------------------------------------------------------ simulation
func sim_tick(dt: float) -> void:
	if dead: return
	for i in w_reload.size(): w_reload[i] = maxf(0.0, w_reload[i] - dt)
	if target and (target.dead or not is_instance_valid(target)):
		target = null; forced_target = false
		if state == S.ATTACK: state = S.IDLE
	if target and not forced_target and flat_dist(target.position) > def.sight * 1.2:
		target = null
	if domain == "jet":
		_jet_tick(dt)
	else:
		_surface_tick(dt)
	rotation.y = heading
	_fire_weapons()
	if gun:
		recoil = move_toward(recoil, 0.0, dt * 1.6)
		gun.position = gun_rest + Vector3(0, 0, recoil)
	var spin := 4.0 if state == S.LANDED else 11.0
	for r in rotors: r.rotation.y += dt * spin * float(r.get_meta("dir"))
	_engine_audio(dt)
	body.position.y = altitude
	body.rotation.z = bank


## Engine / rotor loops and jet pass sounds. Presentation only: never feeds back into the simulation.
func _engine_audio(dt: float) -> void:
	if engine_snd == null and domain in ["heli", "ground"] and def.get("visual") != "infantry":
		engine_snd = SFX.loop(body, "heli_loop" if domain == "heli" else "tank_loop", -30.0)
	if engine_snd:
		var base := SFX.volume_db()
		if domain == "heli":
			var landed := state == S.LANDED
			engine_snd.volume_db = base + (-15.0 if landed else -5.0)
			engine_snd.pitch_scale = 0.85 if landed else 1.0
		else:
			var f := clampf(speed_cur / float(def.speed), 0.0, 1.0)
			engine_snd.volume_db = base - 20.0 + 13.0 * f
			engine_snd.pitch_scale = 0.85 + 0.25 * f
	if domain == "jet":
		if state == S.LANDED:
			takeoff_snd = false
		elif not airborne and not takeoff_snd:
			takeoff_snd = true
			SFX.play(body, "jet_takeoff", global_position, -2.0, 1.0, true)
			flyby_t = 9.0
		elif airborne:
			flyby_t -= dt
			if flyby_t <= 0.0:
				flyby_t = 10.0 + float(uid % 5) * 1.3
				SFX.play(body, "jet_flyby", global_position, -3.0, 0.95 + 0.02 * float(uid % 5), true)


func _acquire(r: float) -> void:
	if target == null and def.weapons.size() > 0:
		target = battle.find_enemy_near(self, r)


## Ground vehicles and helicopters.
func _surface_tick(dt: float) -> void:
	var moving := false
	if domain == "heli" and state in [S.LANDED, S.RETURN]:
		_heli_pad(dt)
		return
	if state == S.HAUL:
		_haul_tick(dt)
		return
	if state == S.BUILD:
		var mv := _build_tick(dt)
		vel = forward() * speed_cur
		if not mv: speed_cur = 0.0
		return
	# idle haulers go back to work after a short pause (a depot must exist)
	if def.get("hauler", false):
		idle_t = idle_t + dt if state == S.IDLE else 0.0
		if idle_t > 4.0 and not battle.structures(team, "supply_depot").is_empty():
			start_haul(null)
	match state:
		S.IDLE:
			_acquire(def.sight * 0.8 if domain == "heli" else max_range_any() * 1.05)
		S.MOVE:
			moving = true
			if _follow(dt):
				if queue.is_empty(): state = S.IDLE; speed_cur = 0.0
				else: goal = queue.pop_front(); _plan(goal)
		S.ATTACK_MOVE:
			_acquire(def.sight)
			if target and flat_dist(target.position) > max_range_vs(target) * 0.92:
				moving = true; _chase(dt)
			elif target == null:
				moving = true
				if _follow(dt): state = S.IDLE; speed_cur = 0.0
		S.ATTACK:
			if target and flat_dist(target.position) > max_range_vs(target) * 0.92:
				moving = true; _chase(dt)
			elif target:
				_face(target.position, dt)
		S.FORCE_GROUND:
			if flat_dist(force_pos) > max_range_any() * 0.9:
				moving = true; _steer_to(force_pos, dt)
			else:
				_face(force_pos, dt)
		S.GUARD:
			if guard_unit and not guard_unit.dead: guard_pos = guard_unit.position
			var leash: float = def.sight * 1.3
			if target and flat_dist(guard_pos) > leash:
				target = null   # do not chase beyond the leash
			if target == null:
				var t: Unit = battle.find_enemy_near_point(self, guard_pos, def.sight)
				if t: target = t
			if target and flat_dist(target.position) > max_range_vs(target) * 0.92:
				moving = true; _chase(dt)
			elif target == null and flat_dist(guard_pos) > 6.0:
				moving = true
				if path_i >= path.size() or repath_t <= 0.0: _plan(guard_pos)
				repath_t -= dt
				_follow(dt)
	if not moving:
		speed_cur = move_toward(speed_cur, 0.0, def.accel * 2.0 * dt)
		position += forward() * speed_cur * dt
		bank = move_toward(bank, 0.0, dt)
	vel = forward() * speed_cur
	if domain == "heli":
		altitude = move_toward(altitude, def.altitude, dt * 5.0)   # lift-off / cruise height
		body.rotation.x = -clampf(speed_cur / def.speed, 0.0, 1.0) * 0.12   # nose-down when cruising
	_aim_turret(dt)


## Helicopter return: fly to the pad, hover, descend vertically onto the pad centre, then sit with rotors idling.
func _heli_pad(dt: float) -> void:
	target = null
	if state == S.LANDED:
		speed_cur = 0.0; vel = Vector3.ZERO; bank = 0.0
		altitude = move_toward(altitude, 0.4, dt * 4.0)
		position = position.move_toward(home, dt * 2.0)
		heading = lerp_angle(heading, 0.0, minf(1.0, dt * 2.0))
		body.rotation.x = 0.0
		return
	var d := flat_dist(home)
	if d > 1.5:
		altitude = move_toward(altitude, def.altitude, dt * 5.0)
		_steer_to(home, dt)
		vel = forward() * speed_cur
	else:
		speed_cur = 0.0; vel = Vector3.ZERO
		position = position.move_toward(Vector3(home.x, 0, home.z), dt * 3.0)
		heading = lerp_angle(heading, 0.0, minf(1.0, dt * 2.0))
		altitude = move_toward(altitude, 0.4, dt * 3.5)
		if altitude <= 0.45: state = S.LANDED
	body.rotation.x = -clampf(speed_cur / def.speed, 0.0, 1.0) * 0.12


func _build_tick(dt: float) -> bool:
	if site == null or site.dead or site.built:
		site = null; state = S.IDLE; speed_cur = 0.0
		return false
	if site.footprint_dist(position) > 7.0 and not (path_i >= path.size() and site.footprint_dist(position) < 10.0):
		if path_i >= path.size() or repath_t <= 0.0:
			_plan(_site_approach()); repath_t = 2.0
		repath_t -= dt
		_follow(dt)
		return true
	speed_cur = 0.0
	_face(site.position, dt)
	if site.construct(dt):
		site = null; state = S.IDLE
	return false


func _haul_tick(dt: float) -> void:
	if haul_depot == null or haul_depot.dead:
		var deps: Array = battle.structures(team, "supply_depot")
		if deps.is_empty(): state = S.IDLE; return
		haul_depot = deps[0]
	match haul_phase:
		0:
			if haul_pile.is_empty() or int(haul_pile.cash) <= 0:
				haul_pile = battle.nearest_pile(haul_depot.position)
				if haul_pile.is_empty(): state = S.IDLE; return
			altitude = move_toward(altitude, def.altitude, dt * 5.0)
			if flat_dist(haul_pile.pos) > 3.0:
				_steer_to(haul_pile.pos, dt)
			else:
				speed_cur = move_toward(speed_cur, 0.0, def.accel * 2.0 * dt)
				haul_phase = 1; haul_t = BuildingDefs.HAUL_LOAD_TIME
		1:
			speed_cur = move_toward(speed_cur, 0.0, def.accel * 2.0 * dt)
			altitude = move_toward(altitude, 4.0, dt * 4.0)
			haul_t -= dt
			if haul_t <= 0.0:
				var take := mini(BuildingDefs.HAUL_LOAD, int(haul_pile.cash))
				haul_pile.cash = int(haul_pile.cash) - take
				cargo = take
				haul_phase = 2
		2:
			altitude = move_toward(altitude, def.altitude, dt * 5.0)
			var drop: Vector3 = haul_depot.position
			if flat_dist(drop) > 3.0:
				_steer_to(drop, dt)
			else:
				haul_phase = 3; haul_t = BuildingDefs.HAUL_UNLOAD_TIME
		3:
			speed_cur = move_toward(speed_cur, 0.0, def.accel * 2.0 * dt)
			altitude = move_toward(altitude, 6.0, dt * 4.0)
			haul_t -= dt
			if haul_t <= 0.0:
				battle.deliver(team, cargo)
				cargo = 0
				haul_phase = 0
	vel = forward() * speed_cur
	body.rotation.x = -clampf(speed_cur / def.speed, 0.0, 1.0) * 0.12


func weapons_ready() -> bool:
	if domain == "jet": return airborne and state != S.RETURN
	if domain == "heli": return state != S.RETURN and state != S.LANDED and altitude >= def.altitude * 0.6
	return true


func max_range_any() -> float:
	var r := 0.0
	for w in def.weapons: r = maxf(r, w.range)
	return r


func _chase(dt: float) -> void:
	if domain != "ground":
		_steer_to(target.position, dt); return
	repath_t -= dt
	if repath_t <= 0.0 or path_i >= path.size():
		path = battle.find_path(position, target.position)
		path_i = 1 if path.size() > 1 else 0
		repath_t = 1.0
	_follow(dt)


func _face(p: Vector3, dt: float) -> void:
	if turret and domain == "ground": return   # turreted units aim the turret, not the hull
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var diff := wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
	var step := deg_to_rad(def.turn_deg) * dt
	heading = wrapf(heading + clampf(diff, -step, step), -PI, PI)


func _steer_to(p: Vector3, dt: float) -> void:
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var want := atan2(-to.x, -to.z)
	var diff := wrapf(want - heading, -PI, PI)
	var step := deg_to_rad(def.turn_deg) * dt
	heading = wrapf(heading + clampf(diff, -step, step), -PI, PI)
	var align := clampf(cos(diff), 0.0, 1.0)
	var ts: float = def.speed * align * align
	ts = minf(ts, maxf(2.0, to.length() * 1.2))
	speed_cur = move_toward(speed_cur, ts, def.accel * dt)
	position += forward() * speed_cur * dt
	bank = move_toward(bank, clampf(diff, -0.4, 0.4) * (0.6 if domain == "heli" else 0.0), dt)


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
	_steer_to(p, dt)
	return false


## Jets never stop in the air. Phases: take-off roll from the pad -> climb -> orbit / move / attack runs ->
## return pattern (approach point south of the pad, aligned final, touchdown on the pad centre facing north) ->
## landed and rearming. Attack runs: fly in, fire while the target is inside the weapon window, overfly,
## extend straight for a moment, then turn back for another pass (no endless circling inside the turn radius).
func _jet_tick(dt: float) -> void:
	if state == S.LANDED:
		airborne = false
		speed_cur = 0.0
		altitude = move_toward(altitude, 0.4, dt * 8.0)
		position = position.move_toward(home, dt * 6.0)
		heading = lerp_angle(heading, 0.0, minf(1.0, dt * 3.0))
		bank = 0.0
		rearm_t -= dt
		if rearm_t <= 0.0:
			rearm_t = 1.5
			for i in w_ammo.size():
				var full := int(def.weapons[i].get("ammo", -1))
				if full > 0 and w_ammo[i] < full: w_ammo[i] += 1; break
		vel = Vector3.ZERO
		return
	if not airborne:
		# take-off roll straight down the pad heading, lift off at 80 % of minimum flying speed
		bank = 0.0
		speed_cur = move_toward(speed_cur, def.speed, def.accel * 1.4 * dt)
		position += forward() * speed_cur * dt
		altitude = move_toward(altitude, 0.4 + maxf(0.0, speed_cur - def.min_speed * 0.6) * 0.4, dt * 6.0)
		if speed_cur >= def.min_speed * 0.8: airborne = true
		vel = forward() * speed_cur
		return
	if not has_ammo() and state != S.RETURN:
		_clear(); state = S.RETURN; goal = home; ret_phase = 0
	altitude = move_toward(altitude, def.altitude, dt * maxf(4.0, speed_cur * 0.3))
	var steer := goal
	var throttle: float = def.speed
	var min_v: float = def.min_speed
	match state:
		S.IDLE, S.MOVE:
			if state == S.MOVE and flat_dist(goal) < 25.0:
				if queue.is_empty(): state = S.IDLE
				else: goal = queue.pop_front()
			steer = _orbit_point(goal, 60.0) if state == S.IDLE else goal
			if state == S.IDLE: _acquire(def.sight * 0.7)
			if state == S.IDLE and target: state = S.ATTACK
		S.ATTACK_MOVE:
			_acquire(def.sight)
			steer = _run_steer(target.position, dt) if target else goal
			if target == null and flat_dist(goal) < 25.0: state = S.IDLE
		S.ATTACK:
			if target: steer = _run_steer(target.position, dt)
			else: state = S.IDLE
		S.FORCE_GROUND:
			steer = _run_steer(force_pos, dt)
		S.GUARD:
			if guard_unit and not guard_unit.dead: guard_pos = guard_unit.position
			if target == null: target = battle.find_enemy_near_point(self, guard_pos, def.sight)
			steer = _run_steer(target.position, dt) if target else _orbit_point(guard_pos, 60.0)
		S.RETURN:
			var approach := home + Vector3(0, 0, 110.0)       # line up south of the pad, land heading north
			if ret_phase == 0:
				steer = approach
				if flat_dist(approach) < 35.0: ret_phase = 1
			else:
				steer = home
				var d := flat_dist(home)
				var to_pad := Vector3(home.x - position.x, 0, home.z - position.z)
				var err := absf(wrapf(atan2(-to_pad.x, -to_pad.z) - heading, -PI, PI))
				if d > 25.0 and err > deg_to_rad(60.0):
					ret_phase = 0                                 # overshot or badly aligned: go around
				altitude = move_toward(altitude, def.altitude * clampf((d - 4.0) / 110.0, 0.0, 1.0) + 0.4, dt * 12.0)
				throttle = clampf(d * 0.32, 5.0, def.speed * 0.75)
				min_v = 3.0
				if d < 3.0:
					position = Vector3(home.x, 0, home.z); heading = 0.0
					state = S.LANDED; rearm_t = 1.5; speed_cur = 0.0; airborne = false
					return
	var to := Vector3(steer.x - position.x, 0, steer.z - position.z)
	var diff := wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
	var step := deg_to_rad(def.turn_deg) * dt
	var turn := clampf(diff, -step, step)
	heading = wrapf(heading + turn, -PI, PI)
	throttle = maxf(min_v, throttle * (1.0 - absf(diff) / PI * 0.4))
	speed_cur = move_toward(speed_cur, throttle, def.accel * dt)
	position += forward() * speed_cur * dt
	bank = move_toward(bank, (turn / maxf(step, 1e-4)) * 0.55, dt * 1.8)
	vel = forward() * speed_cur


## Steering for an attack run on point p: run in, overfly, extend, come back around.
func _run_steer(p: Vector3, dt: float) -> Vector3:
	if run_out_t > 0.0:
		run_out_t -= dt
		return position + forward() * 100.0
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var d := to.length()
	var err := absf(wrapf(atan2(-to.x, -to.z) - heading, -PI, PI))
	var turn_r: float = def.speed / deg_to_rad(def.turn_deg)
	if d < 25.0 or (d < turn_r * 1.6 and err > deg_to_rad(70.0)):
		run_out_t = turn_r * 2.2 / maxf(speed_cur, 1.0)   # extend far enough to turn back onto the target
		return position + forward() * 100.0
	return p


func _orbit_point(c: Vector3, r: float) -> Vector3:
	# a point ahead on the circle around c, so the jet settles into a left-hand orbit
	var rel := Vector3(position.x - c.x, 0, position.z - c.z)
	var ang := atan2(rel.z, rel.x) + 0.9
	return c + Vector3(cos(ang), 0, sin(ang)) * r


func _aim_turret(dt: float) -> void:
	if turret == null: return
	var want_local := 0.0
	var aim_at: Variant = null
	if target and flat_dist(target.position) <= def.sight: aim_at = target.position
	elif state == S.FORCE_GROUND: aim_at = force_pos
	if aim_at != null:
		var to: Vector3 = aim_at - position
		want_local = wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
	var diff := wrapf(want_local - turret_yaw, -PI, PI)
	var step := deg_to_rad(def.turret_turn_deg) * dt
	turret_yaw = wrapf(turret_yaw + clampf(diff, -step, step), -PI, PI)
	turret.rotation.y = turret_yaw


func _fire_weapons() -> void:
	if not weapons_ready(): return
	var tpos: Variant = null
	var tunit: Unit = null
	if state == S.FORCE_GROUND:
		tpos = force_pos
	elif target and not target.dead:
		tunit = target; tpos = target.position
	if tpos == null: return
	for i in def.weapons.size():
		var w: Dictionary = def.weapons[i]
		if w_reload[i] > 0.0 or w_ammo[i] == 0: continue
		if tunit and not (tunit.domain in w.targets): continue
		if tunit == null and not ("ground" in w.targets): continue
		var d := flat_dist(tpos)
		if d > w.range: continue
		var to: Vector3 = tpos - position
		var bearing := atan2(-to.x, -to.z)
		var facing_err: float
		if w.get("turret", false) and turret:
			facing_err = absf(wrapf(bearing - heading - turret_yaw, -PI, PI))
			if facing_err > deg_to_rad(3.0): continue
		else:
			facing_err = absf(wrapf(bearing - heading, -PI, PI))
			if facing_err > deg_to_rad(w.get("facing_deg", 15.0)): continue
		w_reload[i] = w.reload
		if w_ammo[i] > 0: w_ammo[i] -= 1
		if w.id == "120mm": recoil = 0.55
		battle.fire(self, w, tunit, tpos)


func muzzle_pos() -> Vector3:
	if muzzle: return muzzle.global_position
	return global_position + Vector3.UP * (altitude - 0.3) + forward() * float(def.get("length", 4.0)) * 0.25


func take_damage(amount: float, from: Unit) -> void:
	if dead: return
	hp -= amount
	if hp <= 0.0:
		hp = 0.0
		die()
	elif target == null and from and not from.dead and can_target(from) and state in [S.IDLE, S.GUARD]:
		target = from   # return fire


func die() -> void:
	dead = true
	set_selected(false)
	for m in mats:
		(m as ShaderMaterial).set_shader_parameter("burnt", 1.0)
	battle.on_unit_died(self)

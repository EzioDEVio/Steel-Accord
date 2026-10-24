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
var vet_xp := 0.0            # veterancy (see Veterancy)
var vet_rank := 0
var bank := 0.0
var w_reload: Array = []
var w_ammo: Array = []
var rearm_t := 0.0
var airborne := true
var run_out_t := 0.0
var ret_phase := 0
var site: Node = null          # dozer: structure under construction
var has_runway := false        # jets: airfield with a runway (taxi out, roll along it, land on it, taxi back)
var taxi_out: Array = []       # jets: waypoints pad -> taxiway -> runway take-off end (from the airfield)
var taxi_in: Array = []        # jets: runway -> taxiway -> pad
var taxi_i := 0
var rw_start := Vector3.ZERO
var rw_end := Vector3.ZERO
var park_heading := 0.0
var taxi_phase := 0            # ground: 0 taxi to runway start, 1 take-off roll | landing: 2 rollout, 3 taxi to pad
var haul_depot: Node = null    # hauler: supply depot it delivers to
var haul_phase := 0            # 0 fly to pile, 1 loading, 2 fly to depot, 3 unloading
var haul_t := 0.0
var cargo := 0
var haul_pile: Dictionary = {}
var idle_t := 0.0
# ---- movement (B3): local avoidance, group moves, clean arrival, stuck detection, boarding approach
var grp := 0                   # group-move id (0 = none); members share grp_speed while moving together
var grp_speed := 0.0           # slowest member's speed (m/s), 0 = no cap
var grp_lag := false           # behind the rest of its group: may use full speed to catch up
var stuck_t := 0.0             # seconds without progress toward the current waypoint
var stuck_n := 0               # repaths made in this move without reaching the goal
var prog_best := 1e9           # best distance to the current waypoint so far
var arrive_t := 0.0            # seconds spent close to a crowded goal
var hold_t := 0.0              # transport: braking so that passengers can board
var hold_sum := 0.0            # seconds held recently (bounded so a transport is never pinned)
var nudge_pos := Vector3.INF   # idle unit stepping aside for a passing friendly
var nudge_t := 0.0
var rest_pos := Vector3.INF    # where an idle unit settled (it walks back there after stepping aside)
var back_t := 0.0              # seconds until it walks back
var back_n := 0                # walk-back attempts postponed by passing traffic
var av_ang := 0.0              # last avoidance heading offset (hysteresis against left/right dithering)
var alt_layer := -1            # aircraft altitude layer (-1: from the unit id)
var board_slot := 0            # boarding infantry: approach slot around the transport
var climb_t := 0.0             # jet: climbing over a conflicting jet (s left)
var climb_y := 0.0             # jet: absolute height to clear it by
var board_t := 0.0             # boarding infantry: seconds spent pressed against a crowded transport
var _body_r := -1.0

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
var team_marker: MeshInstance3D   # team-coloured ellipse under ground units; hidden while the selection ring shows
var _vtop := -1.0                 # height of the model's top above the unit origin (for health bars), measured once
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
		mats = UnitArt.apply(model, def.ao_prefix, UnitDefs.team_color(team), id)
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
var exhausts: Array = []
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
	_apply_grooming()
	for n in model.find_children("*", "Node3D", true, false):
		var nm := String(n.name)
		if nm.begins_with("Wheel") or nm.begins_with("Sprocket") or nm.begins_with("Idler"):
			wheels.append(n)
		if nm in ["RotorFront", "RotorRear", "RotorMain"]:
			n.set_meta("dir", -1.0 if nm == "RotorRear" else 1.0)
			n.set_meta("axis", Vector3.UP)
			rotors.append(n)
		elif nm == "RotorTail":
			n.set_meta("dir", 4.0); n.set_meta("axis", Vector3.RIGHT)
			rotors.append(n)
		elif nm.begins_with("Prop") and nm.substr(4).is_valid_int():
			n.set_meta("dir", 3.0); n.set_meta("axis", Vector3.BACK)
			rotors.append(n)
		elif nm.begins_with("Exhaust") and domain == "jet":
			exhausts.append(n)
		if n is MeshInstance3D:
			var mi := n as MeshInstance3D
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			for si in mi.mesh.get_surface_count():
				var mat := mi.get_active_material(si)
				if mat and mat.resource_name.begins_with("SA_Ghillie") and mat is BaseMaterial3D:
					var gm := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
					gm.cull_mode = BaseMaterial3D.CULL_DISABLED
					mi.set_surface_override_material(si, gm)
				if mat and mat.resource_name.begins_with("SA_Team") and mat is BaseMaterial3D:
					var tm := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
					tm.albedo_color = UnitDefs.team_color(team).lightened(0.15)
					mi.set_surface_override_material(si, tm)
				if mat and mat.resource_name.begins_with("SA_TrackScroll") and mat is BaseMaterial3D:
					var dm := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
					mi.set_surface_override_material(si, dm)
					track_mats.append(dm)
	if not rotors.is_empty(): rotor = rotors[0]
	turret = model.find_child("Turret", true, false) as Node3D
	gun = model.find_child("Gun", true, false) as Node3D
	muzzle = model.find_child("Muzzle", true, false) as Node3D
	if gun: gun_rest = gun.position
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
	for e in exhausts:       # jet engine trails from the model's nozzle points
		FX.exhaust_trail(model, (e as Node3D).position, 0.7, false)
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
		elif para_alt > 0.0: _play("para_descend")
		elif anim_cur == "para_land" and anim.is_playing(): pass
		elif spd > 0.3:
			var k := "run" if spd > def.speed * 0.6 else "walk"
			_play(k, spd / (float(stride.get(k, 1.4)) * vis_scale))
		elif target != null: _play("fire" if battle.sim_time - last_fire_t < 0.7 else "aim")
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
	var tc: Color = UnitDefs.team_color(team).lightened(0.2)
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
	team_marker = mi


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
	# same size as the team marker it replaces while selected (one ring per unit, never two)
	var r: float = def.radius * ((1.2 if def.get("visual") == "infantry" else 1.05) if domain == "ground" else 1.1)
	t.inner_radius = r * 0.86; t.outer_radius = r; t.rings = 48; t.ring_segments = 4
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0.45, 1.0, 0.55)
	t.material = m
	mi.mesh = t
	mi.scale = Vector3(1, 0.04, 1.0 if def.get("visual") == "infantry" or domain != "ground" else 1.35)
	mi.position.y = 0.14
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
	if team_marker: team_marker.visible = not (v and not dead)


## Point just above the model for the health bar / rank / group number (measured from the meshes once).
## Spacing radius used when units push apart: infantry models are drawn larger than their hit radius.
func sep_r() -> float:
	return body_r()


## Ground-plane radius of the drawn model, used for avoidance, spacing and formation slots. Infantry: hit radius at
## the infantry draw scale. Vehicles: between half width and half length of the drawn hull (a circle cannot be both).
## Helicopters: the rotor disc (twin-rotor: half the airframe). Jets: half the drawn length.
func body_r() -> float:
	if _body_r < 0.0:
		if def.get("visual") == "infantry":
			_body_r = float(def.radius) * 1.3
		elif domain == "heli":
			_body_r = maxf(float(def.radius), float(def.get("rotor", 0.0)) * vis_scale)
			if def.get("rotor_twin", false): _body_r = maxf(_body_r, float(def.get("length", 0.0)) * vis_scale * 0.5)
		elif domain == "jet":
			_body_r = float(def.get("length", 8.0)) * vis_scale * 0.5
		else:
			_body_r = maxf(float(def.radius), 0.5 * (half_len() + float(def.radius)))
	return _body_r


## Hull model for avoidance and the separation safety net: a ground vehicle is two circles along its hull (front and
## rear, radius a little over half the drawn width), so long vehicles keep their full length clear nose to tail yet can
## still park side by side; everything else is a single circle of body_r().
var _sub_r := -1.0
var _sub_off := 0.0


func sub_r() -> float:
	if _sub_r < 0.0:
		if domain == "ground" and def.get("visual") != "infantry":
			_sub_r = maxf(half_wid() * 1.25, 0.8)
			_sub_off = maxf(0.0, half_len() - half_wid() * 0.9)
		else:
			_sub_r = body_r(); _sub_off = 0.0
	return _sub_r


func sub_off() -> float:
	if _sub_r < 0.0: sub_r()
	return _sub_off


## Reach of the hull model from the unit's centre.
func ext_r() -> float:
	return sub_off() + sub_r()


## Hull circle centres (ground plane, world) for the current heading.
func hull_pts() -> PackedVector2Array:
	var c := Vector2(position.x, position.z)
	var o := sub_off()
	if o <= 0.0: return PackedVector2Array([c])
	var f := Vector2(-sin(heading), -cos(heading)) * o
	return PackedVector2Array([c + f, c - f])


## Side clearance asked of planned straight lines: vehicles keep their hull off rocks and corners.
func path_clearance() -> float:
	return sub_r() if domain == "ground" and def.get("visual") != "infantry" else 0.0


## Drawn hull half length / half width (ground vehicles; boarding contact and test geometry).
func half_len() -> float:
	return maxf(float(def.get("length", 0.0)) * vis_scale * 0.5, float(def.radius))


func half_wid() -> float:
	return float(def.radius) * 0.78


func bar_anchor() -> Vector3:
	if is_air(): return world_center() + Vector3.UP * 2.5
	if _vtop < 0.0:
		_vtop = float(def.get("height", 2.0))
		var inv := global_transform.affine_inverse()
		var top := -INF
		for n in find_children("*", "VisualInstance3D", true, false):
			if n == ring or n == team_marker or n is Decal or not (n as Node3D).is_visible_in_tree(): continue
			var bb: AABB = (inv * (n as VisualInstance3D).global_transform) * (n as VisualInstance3D).get_aabb()
			top = maxf(top, bb.end.y)
		if top > 0.2 and top < 60.0: _vtop = top
	return global_position + Vector3.UP * (_vtop + 0.6)


func is_air() -> bool:
	return domain != "ground"


func forward() -> Vector3:
	return Vector3(-sin(heading), 0, -cos(heading))


## Iranian infantry models carry separate Beard and Moustache meshes: soldiers get a deterministic mix of full beard,
## moustache only and clean-shaven (by unit id, so it is identical in every replay). IRGC operators are bearded.
func _apply_grooming() -> void:
	var beard := model.find_child("Beard", true, false) as Node3D
	var tache := model.find_child("Moustache", true, false) as Node3D
	if beard == null and tache == null: return
	var v := 0 if kind == "irgc_sf" else (uid * 7 + 3) % 5     # 0-2 full beard, 3 moustache only, 4 clean-shaven
	if beard: beard.visible = v <= 2
	if tache: tache.visible = v <= 3
	set_meta("grooming", ["beard", "beard", "beard", "moustache", "shaven"][v])


## Terrain movement class for heightfield maps: "infantry", "wheeled" or "tracked" (slope limits and costs differ).
func move_class() -> String:
	if def.has("move_class"): return str(def.move_class)
	if def.get("visual") == "infantry": return "infantry"
	return "tracked" if def.has("track_m_per_v") or kind in UnitDefs.TRACKED else "wheeled"


## Sight radius including the team's battle plan (Recon).
func sight_r() -> float:
	return float(def.sight) * (battle.sight_mult(team) if team >= 0 and team < 2 else 1.0)


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
	grp = 0; grp_speed = 0.0; grp_lag = false; nudge_t = 0.0


## Boarding: walk straight to a point next to the transport (no grid path: the last metres to a hull or a door are
## open ground even where the grid cell is blocked by the structure's padding). Keeps board_target.
func order_approach(p: Vector3) -> void:
	_clear(); state = S.MOVE; goal = p
	path = PackedVector3Array([position, p]); path_i = 1
	repath_t = 1.0; stuck_t = 0.0; stuck_n = 0; prog_best = 1e9; arrive_t = 0.0


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
	return site.position + to * (site.reach_along(to) + 3.0)     # oriented footprint (placement rotation)


## Supply hauler (CH-47): loops pile -> depot automatically until given another order.
func start_haul(depot: Node) -> void:
	_clear(); state = S.HAUL; haul_depot = depot; haul_phase = 0 if cargo == 0 else 2; haul_pile = {}


func order_stop() -> void:
	_clear(); state = S.IDLE
	rest_pos = position; back_t = 0.0
	path = PackedVector3Array(); path_i = 0
	if domain == "jet": goal = position


func order_return() -> void:
	if domain == "ground" or state == S.LANDED: return
	_clear(); state = S.RETURN; goal = home; ret_phase = 0


## Movement profiling ("prof" argument): time in local avoidance and path planning, printed with the PROF line.
static var prof_on := false
static var prof_av_us := 0
static var prof_av_n := 0
static var prof_path_us := 0
static var prof_path_n := 0


func _find_path(p: Vector3) -> PackedVector3Array:
	var t0 := Time.get_ticks_usec() if prof_on else 0
	var r: PackedVector3Array = battle.find_path(position, p, move_class(), path_clearance())
	if prof_on: prof_path_us += Time.get_ticks_usec() - t0; prof_path_n += 1
	return r


func _plan(p: Vector3) -> void:
	if domain == "ground":
		path = _find_path(p)
	else:
		path = PackedVector3Array([position, p])
	path_i = 1 if path.size() > 1 else 0
	repath_t = 1.0
	stuck_t = 0.0; stuck_n = 0; prog_best = 1e9; arrive_t = 0.0


# ------------------------------------------------------------------ simulation
func sim_tick(dt: float) -> void:
	if dead: return
	if _para_tick(dt): return
	for i in w_reload.size(): w_reload[i] = maxf(0.0, w_reload[i] - dt)
	if target and (target.dead or not is_instance_valid(target)):
		target = null; forced_target = false
		if state == S.ATTACK: state = S.IDLE
	if target and not forced_target and flat_dist(target.position) > sight_r() * 1.2:
		target = null
	if domain == "jet":
		_jet_tick(dt)
	else:
		_surface_tick(dt)
	rotation.y = heading
	_fire_weapons()
	if def.has("heal"): _heal_aura(dt)
	if state == S.LANDED and hp < def.hp: hp = minf(def.hp, hp + def.hp * 0.03 * dt)   # serviced on its pad
	if vet_rank == 3 and hp < def.hp: hp = minf(def.hp, hp + def.hp * Veterancy.HEROIC_REPAIR * dt)
	if gun:
		recoil = move_toward(recoil, 0.0, dt * 1.6)
		gun.position = gun_rest + Vector3(0, 0, recoil)
	var spin := 4.0 if state == S.LANDED else 11.0
	for r in rotors:
		var ax: Vector3 = r.get_meta("axis", Vector3.UP)
		r.rotate_object_local(ax, dt * spin * float(r.get_meta("dir")))
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
	# idle scans are staggered: each unit looks for targets every 6th tick (0.2 s), not every tick
	if target == null and def.weapons.size() > 0 and (battle.tick_n + uid) % 6 == 0:
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
			_acquire(sight_r() * 0.8 if domain == "heli" else max_range_any() * 1.05)
			if nudge_t > 0.0:      # step aside for a passing friendly, then stand again
				nudge_t -= dt
				if flat_dist(nudge_pos) > 0.35 and nudge_t > 0.0:
					moving = true; _steer_to(nudge_pos, dt, 0.6)
				elif nudge_pos == rest_pos:     # back on its spot (or as close as it got): stay
					nudge_t = 0.0; back_t = 0.0; rest_pos = position
				else:
					nudge_t = 0.0; back_t = 1.5
			elif back_t > 0.0:     # once the way is clear again: go back to the spot it was given
				back_t -= dt
				if back_t <= 0.0 and rest_pos != Vector3.INF and flat_dist(rest_pos) > 1.5:
					if _movers_near(rest_pos, body_r() + 9.0) or _occupied(rest_pos):
						back_n += 1
						back_t = 1.0 if back_n < 8 else 0.0
						if back_n >= 8: rest_pos = position      # traffic never cleared: this is the spot now
					else:
						back_n = 0
						nudge_pos = rest_pos; nudge_t = 5.0
		S.MOVE:
			moving = true
			if _follow(dt):
				if queue.is_empty(): state = S.IDLE; speed_cur = 0.0; rest_pos = position; back_t = 0.0
				else: goal = queue.pop_front(); _plan(goal)
		S.ATTACK_MOVE:
			_acquire(sight_r())
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
			var leash: float = sight_r() * 1.3
			if target and flat_dist(guard_pos) > leash:
				target = null   # do not chase beyond the leash
			if target == null:
				var t: Unit = battle.find_enemy_near_point(self, guard_pos, sight_r())
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
	if hold_t > 0.0: hold_t -= dt; hold_sum += dt
	else: hold_sum = maxf(0.0, hold_sum - dt * 0.5)
	if domain == "heli":
		var want_alt: float = 1.6 if (unload_pending or _loading_nearby()) and speed_cur < 2.0 else cruise_alt()
		altitude = move_toward(altitude, want_alt, dt * 5.0)   # lift-off / cruise height (low hover to load / unload)
		if unload_pending and can_exchange():
			unload_pending = false
			battle.unload_all(self)
		body.rotation.x = -clampf(speed_cur / def.speed, 0.0, 1.0) * 0.12   # nose-down when cruising
	_aim_turret(dt)


## Helicopter return: fly to the pad, hover, descend vertically onto the pad centre, then sit with rotors idling.
func _heli_pad(dt: float) -> void:
	target = null
	if state == S.LANDED:
		speed_cur = 0.0; vel = Vector3.ZERO; bank = 0.0
		altitude = move_toward(altitude, ground_alt(), dt * 4.0)
		position = position.move_toward(home, dt * 2.0)
		heading = lerp_angle(heading, 0.0, minf(1.0, dt * 2.0))
		body.rotation.x = 0.0
		return
	var d := flat_dist(home)
	if d > 1.5:
		altitude = move_toward(altitude, cruise_alt(), dt * 5.0)
		_steer_to(home, dt)
		vel = forward() * speed_cur
	else:
		speed_cur = 0.0; vel = Vector3.ZERO
		position = position.move_toward(Vector3(home.x, 0, home.z), dt * 3.0)
		heading = lerp_angle(heading, 0.0, minf(1.0, dt * 2.0))
		altitude = move_toward(altitude, ground_alt(), dt * 3.5)
		if altitude <= ground_alt() + 0.05: state = S.LANDED
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
				battle.deliver(team, int(round(cargo * battle.income_mult(team))))
				cargo = 0
				haul_phase = 0
	vel = forward() * speed_cur
	body.rotation.x = -clampf(speed_cur / def.speed, 0.0, 1.0) * 0.12


var heal_t := 0.0
var last_fire_t := -99.0
# ---- transports (data-configured: def.transport = {capacity, accepts}); passengers leave battle.units while aboard
var passengers: Array = []      # Unit nodes aboard
var board_target: Unit = null   # infantry: the transport it is walking to
var unload_pending := false     # helicopter: descend, then unload everyone


func _loading_nearby() -> bool:
	if not is_transport() or state in [S.MOVE, S.RETURN, S.HAUL, S.LANDED] or speed_cur > 2.0: return false
	for u in battle.units:
		if u.board_target == self and u.flat_dist(position) < 25.0: return true
	return false


# ---- paratroopers: descend under a canopy, then land and fight
var para_alt := 0.0
var canopy: Node3D
const PARA_MODEL := "res://assets/units3d/paratrooper/parachute_personnel.glb"


func start_parachute(h: float) -> void:
	para_alt = h
	var ps: PackedScene = load(PARA_MODEL) if ResourceLoader.exists(PARA_MODEL) else null
	if ps:
		canopy = ps.instantiate()
		canopy.position.y = 2.0
	else:
		canopy = MeshInstance3D.new()
		var sm := SphereMesh.new(); sm.radius = 2.6; sm.height = 1.8; sm.is_hemisphere = true
		var m := StandardMaterial3D.new(); m.albedo_color = Color(0.42, 0.45, 0.33)
		sm.material = m
		(canopy as MeshInstance3D).mesh = sm
		canopy.position.y = 5.5
	vis.add_child(canopy)
	body.position.y = para_alt
	_play("para_descend")


func _para_tick(dt: float) -> bool:
	if para_alt <= 0.0: return false
	para_alt = maxf(0.0, para_alt - 4.5 * dt)
	position += vel * dt
	body.position.y = para_alt
	if para_alt <= 0.0:
		if canopy: canopy.queue_free(); canopy = null
		_play("para_land")
		order_stop()
	return true


func is_transport() -> bool:
	return def.has("transport")


func capacity_left() -> int:
	return int(def.transport.capacity) - passengers.size() if is_transport() else 0


func accepts(u: Unit) -> bool:
	if not is_transport() or u.dead: return false
	# civilian buildings: anyone may enter an empty one; occupied ones only take the occupiers' side
	if u.team != team and not (self is Building and team < 0): return false
	return "infantry" in def.transport.accepts and u.def.get("visual", "") == "infantry"


## Heli transports load and unload only while hovering low and slow (fast-rope); ground ones when stopped.
func can_exchange() -> bool:
	if domain == "heli": return altitude <= 3.0 and speed_cur < 2.0
	return speed_cur < 1.5


## Support units (ambulance, medic): restore health to nearby friendly units of the listed kinds.
func _heal_aura(dt: float) -> void:
	heal_t -= dt
	if heal_t > 0.0: return
	heal_t = 1.0
	var h: Dictionary = def.heal
	for u in battle.units:
		if u == self or u.dead or u.team != team or u.hp >= u.def.hp: continue
		if u is Building and not (u as Building).built: continue
		var kind_ok := false
		for t in h.targets:
			if t == "structure" and u is Building: kind_ok = true
			if u is Building: continue
			if t == "infantry" and u.def.get("visual", "") == "infantry": kind_ok = true
			if t == "vehicle" and u.domain == "ground" and u.def.get("visual", "") != "infantry": kind_ok = true
		if kind_ok and flat_dist(u.position) <= float(h.radius):
			var before: float = u.hp
			u.hp = minf(u.def.hp, u.hp + u.def.hp * float(h.per_s))
			add_xp((u.hp - before) / 20.0)      # support units are promoted for healing / repairing


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
		path = _find_path(target.position)
		path_i = 1 if path.size() > 1 else 0
		repath_t = 1.0
	_follow(dt)


func _face(p: Vector3, dt: float) -> void:
	if turret and domain == "ground": return   # turreted units aim the turret, not the hull
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var diff := wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
	var step := deg_to_rad(def.turn_deg) * dt
	heading = wrapf(heading + clampf(diff, -step, step), -PI, PI)


## Turn toward p and drive. The preferred velocity (toward p at the unit's speed, capped by its group's speed and
## slowed on the approach) is corrected by local avoidance before the unit turns and accelerates.
func _steer_to(p: Vector3, dt: float, speed_k := 1.0) -> void:
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var dist := to.length()
	var top: float = def.speed
	if domain == "ground": top *= battle.terrain_speed_mult(self) * battle.speed_mult(self)
	var pref := top * speed_k
	if grp_speed > 0.0 and not grp_lag and target == null and state in [S.MOVE, S.ATTACK_MOVE]:
		pref = minf(pref, grp_speed * top / float(def.speed))
	pref = minf(pref, maxf(2.0, dist * 1.2))
	var want_v := Vector2(to.x, to.z) / maxf(dist, 1e-4)
	if dist > 0.05:
		var t_av := Time.get_ticks_usec() if prof_on else 0
		var av := _avoid(want_v, pref)
		if prof_on: prof_av_us += Time.get_ticks_usec() - t_av; prof_av_n += 1
		want_v = Vector2(av.x, av.y); pref = av.z
	if hold_t > 0.0: pref = 0.0
	if pref < 0.0:       # backing off (avoidance): keep the heading, drive in reverse
		speed_cur = move_toward(speed_cur, pref, def.accel * dt)
		position += forward() * speed_cur * dt
		return
	var want := atan2(-want_v.x, -want_v.y)
	var diff := wrapf(want - heading, -PI, PI)
	var step := deg_to_rad(def.turn_deg) * dt
	heading = wrapf(heading + clampf(diff, -step, step), -PI, PI)
	var align := clampf(cos(diff), 0.0, 1.0)
	var ts: float = pref * align * align
	speed_cur = move_toward(speed_cur, ts, def.accel * dt)
	position += forward() * speed_cur * dt
	bank = move_toward(bank, clampf(diff, -0.4, 0.4) * (0.6 if domain == "heli" else 0.0), dt)


## Follow the current path; returns true when the final point is reached. Arrival is clean: a unit whose goal is
## crowded accepts the spot it reached after a short wait instead of circling, and a unit that makes no progress for
## 1.5 s re-plans its route from where it stands (it gives up after repeated failures).
func _follow(dt: float) -> bool:
	if path_i >= path.size():
		return true
	var p := path[path_i]
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var d := to.length()
	var last := path_i == path.size() - 1
	var inf: bool = def.get("visual") == "infantry"
	var tol := (1.0 if inf else 1.5) if last else maxf(3.0, body_r() + 1.5)
	var passed := false
	if not last and d < 10.0:      # deflected past a corner waypoint: carry on to the next one
		var nx := path[path_i + 1]
		passed = (position.x - p.x) * (nx.x - p.x) + (position.z - p.z) * (nx.z - p.z) > 0.0
		if passed and domain == "ground":
			var g: GridNav = battle.navs.get(move_class(), battle.gnav)
			passed = g == null or g.line_clear(position, nx)
	if d < tol or passed:
		path_i += 1; prog_best = 1e9; stuck_t = 0.0
		return path_i >= path.size()
	if d < prog_best - 0.5:
		if prog_best < 1e8: stuck_n = maxi(0, stuck_n - 1)     # real progress pays back earlier stalls
		prog_best = d; stuck_t = 0.0
	else:
		stuck_t += dt
	if last:
		var slack := body_r() * 2.0 + 2.5
		if d < slack and speed_cur < float(def.speed) * 0.3: arrive_t += dt
		else: arrive_t = maxf(0.0, arrive_t - dt)
		if arrive_t > 0.8:
			arrive_t = 0.0; path_i = path.size()
			return true
	if stuck_t > 1.5:
		stuck_t = 0.0; prog_best = 1e9; stuck_n += 1
		if "movedbg" in battle.args:
			var near: Array = []
			for o in battle.units:
				if o != self and not o.dead and o.domain == domain and o.flat_dist(position) < 12.0:
					near.append("%s#%d@%.1f st%d v%.1f" % [o.kind, o.uid, o.flat_dist(position), o.state, o.speed_cur])
			var rocks: Array = []
			for o in battle.obstacles_2d:
				var dd := Vector2(o.x - position.x, o.y - position.z).length()
				if dd < 25.0: rocks.append("rock(%.1f,%.1f r%.1f)@%.1f" % [o.x, o.y, o.z, dd])
			var g: GridNav = battle.navs.get(move_class(), battle.gnav)
			printerr("STUCK t=%.1f %s#%d n=%d pos=(%.1f,%.1f) h=%.2f spd=%.2f d=%.1f wp=(%.1f,%.1f) goal=(%.1f,%.1f) clear=%s av=%s wait=%.1f near: %s | %s" % [battle.sim_time, kind, uid, stuck_n,
				position.x, position.z, heading, speed_cur, d, p.x, p.z, goal.x, goal.z, str(g.line_clear(position, p) if g else true), str(av_last), av_wait, ", ".join(near), ", ".join(rocks)])
		var gp := path[path.size() - 1]
		if (stuck_n >= 2 and flat_dist(gp) < arrive_slack()) or stuck_n >= 10:
			path_i = path.size()              # close enough, or unreachable from here: stop instead of pushing
			return true
		if domain == "ground" and board_target == null:
			path = _find_path(gp)
			path_i = 1 if path.size() > 1 else 0
			if path_i >= path.size(): return true
			p = path[path_i]
	_steer_to(p, dt)
	return false


## Distance from a crowded goal at which a blocked unit accepts where it stands (about one body length).
func arrive_slack() -> float:
	return 4.0 + body_r() * 3.0


## Local avoidance (sampled reciprocal velocity obstacles). Candidate velocities around the preferred one are scored
## by deviation from it plus a penalty that grows as the time to first contact with any neighbour shrinks; moving
## neighbours share the avoidance (reciprocal), standing ones are treated as fixed and friendly idle ones are asked to
## step aside. Ground units also avoid structures, rocks and blocked terrain. A slight keep-right bias and hysteresis
## stop two units from mirroring each other. Returns (direction x, direction z, speed).
const AV_ANGS := [0.0, 0.4, -0.4, 0.8, -0.8, 1.25, -1.25, 1.75, -1.75, 2.4, -2.4]
const AV_SPD := [1.0, 0.55]


var av_last := Vector2(0.0, 1.0)   # last avoidance result: heading offset (rad), speed factor (negative: reversing)
var av_wait := 0.0                 # seconds spent slowed or stopped by avoidance (impatience)


func _avoid(want: Vector2, pref: float) -> Vector3:
	if domain == "jet" or pref <= 0.0: return Vector3(want.x, want.y, pref)
	# full evaluation every other tick (staggered by unit id); in between the last correction is reused relative to
	# the current preferred direction (avoidance reacts within 1/15 s)
	var every := 3 if pref < 6.0 else 2      # slow units (infantry) re-evaluate every 3rd tick, faster ones every 2nd
	if (battle.tick_n + uid) % every != 0:
		var d0 := want.rotated(av_last.x) if av_last.x != 0.0 else want
		return Vector3(d0.x, d0.y, pref * av_last.y)
	var me := Vector2(position.x, position.z)
	var r := body_r()
	var ground := domain == "ground"
	var H := clampf(maxf(speed_cur, pref) / maxf(float(def.accel), 1.0) + 1.0, 1.2, 3.0)
	var look := minf(r + 2.0 + (pref + 2.0) * H, 18.0)
	var vme := Vector2(vel.x, vel.z)
	var P := PackedVector2Array(); var V := PackedVector2Array(); var RR := PackedFloat32Array(); var REC := PackedByteArray()
	var msr := sub_r()
	var mo := sub_off()
	var mext := mo + msr
	var mcs := PackedVector2Array([Vector2.ZERO])
	if mo > 0.0:
		var mf := Vector2(-sin(heading), -cos(heading)) * mo
		mcs = PackedVector2Array([mf, -mf])
	var passing := state != S.IDLE and (board_target != null or flat_dist(goal) > r + 3.0)
	var margin := 0.25 if ground else 1.0
	var nb: Dictionary = battle.nbr_ground if ground else battle.nbr_heli
	var cs: float = battle.NB_CELL
	var kx := floori(me.x / cs); var kz := floori(me.y / cs)
	var span := ceili(look / cs)
	for dz in range(-span, span + 1):
		for dx in range(-span, span + 1):
			var cell: Variant = nb.get(Vector2i(kx + dx, kz + dz))
			if cell == null: continue
			for o: Unit in cell:
				if o == self or o == board_target or (o.board_target == self and is_transport()): continue
				var pp := Vector2(o.position.x - me.x, o.position.z - me.y)
				var oo: float = o._sub_off
				var osr: float = o._sub_r
				var dl := pp.length()
				var ov := Vector2(o.vel.x, o.vel.z)
				var ovl := ov.length()
				# out of reach within the horizon even if both close at full speed: ignore
				if dl - mext - oo - osr > (maxf(pref, absf(speed_cur)) + ovl) * H + 1.0: continue
				var mv := ovl > 0.5 or (o.state != S.IDLE and o.path_i < o.path.size())
				if not mv and passing and o.team == team and o.state == S.IDLE and o.hold_t <= 0.0:
					# friendly standing in the corridor ahead: ask it to step aside
					var Rb := r + o._body_r + 0.55
					var along := pp.dot(want)
					if along > -0.5 and along < r + o._body_r + 6.0 and absf(pp.cross(want)) < Rb:
						o.request_nudge(want, me, Rb)
				var R := msr + osr + margin
				var rec := 1 if mv else 0
				if oo <= 0.0 and mo <= 0.0:
					P.append(pp); V.append(ov); RR.append(R); REC.append(rec)
				else:
					var of := Vector2(-sin(o.heading), -cos(o.heading)) * oo
					for mc in mcs:
						if oo <= 0.0:
							P.append(pp - mc); V.append(ov); RR.append(R); REC.append(rec)
						else:
							P.append(pp + of - mc); V.append(ov); RR.append(R); REC.append(rec)
							P.append(pp - of - mc); V.append(ov); RR.append(R); REC.append(rec)
	if ground:
		for bv in battle.nbr_blds.get(Vector2i(kx, kz), []):
			if not is_instance_valid(bv): continue   # sold / destroyed since the neighbour grid was built
			var b: Unit = bv
			if b == board_target or b.dead: continue
			for mc in mcs:
				var cp: Vector2 = battle.footprint_closest(b, me + mc)
				var pp := cp - me - mc
				if pp.length() > minf(look, pref * H + msr + 1.5): continue
				P.append(pp); V.append(Vector2.ZERO); RR.append(msr + 0.3); REC.append(0)
		var og: Dictionary = battle._obstacle_grid()
		var oc: Variant = og.get(Vector2i(floori(me.x / 16.0), floori(me.y / 16.0)))
		if oc != null:
			for o in oc:
				var pr := Vector2(o.x - me.x, o.y - me.y)
				if pr.length() - o.z - mext > pref * H + 1.5: continue
				for mc in mcs:
					P.append(pr - mc); V.append(Vector2.ZERO); RR.append(o.z * 0.75 + msr + 0.1); REC.append(0)
	if P.is_empty():
		av_ang = 0.0; av_last = Vector2(0.0, 1.0)
		return Vector3(want.x, want.y, pref)
	var n := P.size()
	# the preferred velocity first: if it is free there is nothing to do
	var tp := _ttc_min(P, V, RR, REC, want * pref, vme, n, H)
	if tp >= H:
		av_ang *= 0.8; av_last = Vector2(0.0, 1.0); av_wait = maxf(0.0, av_wait - 2.0 * float(every) / 30.0)
		return Vector3(want.x, want.y, pref)
	var nav: GridNav = battle.navs.get(move_class(), battle.gnav) if ground else null
	var best := Vector3(want.x, want.y, pref)
	var best_c := 1.5 * (1.0 / maxf(tp, 0.02) - 1.0 / H)
	# vehicles never steer more than ~70 degrees off their route (no running away from an oncoming crowd): when
	# boxed in they slow, wait, or back off instead
	var amax := 1.3 if (ground and def.get("visual") != "infantry") else 3.0
	for ai in range(1, AV_ANGS.size()):
		var a: float = AV_ANGS[ai]
		if absf(a) > amax: break
		var dir := want.rotated(a)
		var base_c := 0.0
		if a < 0.0: base_c += 0.04             # keep right
		if av_ang != 0.0 and signf(a) != signf(av_ang): base_c += 0.25
		if base_c + 2.0 * sin(absf(a) * 0.5) * 0.45 >= best_c: continue    # even the slower sample costs more
		if nav:
			var probe := Vector3(me.x + dir.x * (r + 2.0), 0, me.y + dir.y * (r + 2.0))
			if nav.blocked_at(probe): continue
		for si in AV_SPD.size():
			var s: float = pref * AV_SPD[si]
			var v := dir * s
			var c := base_c + (want * pref - v).length() / maxf(pref, 0.5)
			if c >= best_c: continue
			var t := _ttc_min(P, V, RR, REC, v, vme, n, H)
			if t < H: c += 1.5 * (1.0 / maxf(t, 0.02) - 1.0 / H)
			if c < best_c: best_c = c; best = Vector3(dir.x, dir.y, s)
	# slowing down on the preferred heading, or standing still (yield), are candidates too; waiting grows more
	# expensive the longer it lasts (impatience), so two units never wait for each other forever
	for k: float in [0.55, 0.0]:
		var c1 := 1.0 - k + av_wait * (0.9 if k == 0.0 else 0.5)
		if c1 >= best_c: continue
		var t1 := _ttc_min(P, V, RR, REC, want * pref * k, vme, n, H)
		if t1 < H: c1 += 1.5 * (1.0 / maxf(t1, 0.02) - 1.0 / H)
		if c1 < best_c: best = Vector3(want.x, want.y, pref * k); best_c = c1
	# a vehicle boxed in for a while may back off a few metres (it cannot turn on the spot)
	var f := Vector2(-sin(heading), -cos(heading))
	if ground and av_wait > 0.8 and absf(speed_cur) < 1.0 and def.get("visual") != "infantry":
		var vr := -f * float(def.speed) * 0.35
		var cr := 1.2 + 1.5 * (1.0 / maxf(_ttc_min(P, V, RR, REC, vr, vme, n, H), 0.02) - 1.0 / H)
		var back := Vector3(position.x - f.x * (ext_r() + 1.5), 0, position.z - f.y * (ext_r() + 1.5))
		if cr < best_c and (nav == null or not nav.blocked_at(back)):
			av_wait = maxf(0.0, av_wait - 0.2)
			av_last = Vector2(want.angle_to(f), -0.35 * float(def.speed) / pref)
			return Vector3(f.x, f.y, -float(def.speed) * 0.35)
	var ang := want.angle_to(Vector2(best.x, best.y))
	av_ang = ang if absf(ang) > 0.05 else av_ang * 0.8
	av_last = Vector2(ang if absf(ang) > 0.01 else 0.0, best.z / pref)
	if best.z < pref * 0.3: av_wait += float(every) / 30.0
	else: av_wait = maxf(0.0, av_wait - 2.0 * float(every) / 30.0)
	return best


## Earliest time (s, capped at H) at which velocity v brings this unit into contact with any listed neighbour.
## Reciprocal neighbours (moving) are assumed to take half of the avoidance; overlapping pairs only forbid closing.
static func _ttc_min(P: PackedVector2Array, V: PackedVector2Array, RR: PackedFloat32Array, REC: PackedByteArray, v: Vector2, vme: Vector2, n: int, H: float) -> float:
	var tmin := H
	for i in n:
		var w := (v * 2.0 - vme - V[i]) if REC[i] == 1 else (v - V[i])
		var p := P[i]
		var R := RR[i]
		var b := p.dot(w)
		var c := p.length_squared() - R * R
		if c < 0.0:      # already touching: only forbid moving further in (sliding past along the contact is allowed)
			if b > 0.25 * p.length() * w.length(): return 0.0
			continue
		if b <= 0.0: continue
		var a := w.length_squared()
		var disc := b * b - a * c
		if disc < 0.0: continue
		var t := (b - sqrt(disc)) / a
		if t < tmin: tmin = t
	return tmin


## A moving friendly unit needs to pass: step out of its corridor (to the side it is already on) if the ground
## there is free, otherwise to the other side; an idle unit never wanders further than that.
func request_nudge(dir: Vector2, src: Vector2, need: float) -> void:
	if (nudge_t > 0.0 and back_t > 0.0) or speed_cur > 1.5 or state != S.IDLE or (self is Building): return
	if nudge_t > 0.0 and nudge_pos == rest_pos: nudge_t = 0.0      # walking back: give way first
	elif nudge_t > 0.0: return
	var me := Vector2(position.x, position.z)
	var rel := me - src
	var side := Vector2(-dir.y, dir.x)
	var lat := rel.dot(side)
	var s := signf(lat)
	if s == 0.0: s = 1.0 if uid % 2 == 0 else -1.0
	var nav: GridNav = battle.navs.get(move_class(), battle.gnav) if domain == "ground" else null
	for k in 2:
		var sg := s if k == 0 else -s
		var amt := need - absf(lat) + 1.2 if k == 0 else need + absf(lat) + 1.2
		var tgt := me + side * sg * amt + dir * 0.8
		var p3 := Vector3(tgt.x, position.y, tgt.y)
		if (nav == null or not nav.blocked_at(p3)) and battle.map_bounds.has_point(tgt):
			nudge_pos = p3; nudge_t = 2.5; back_t = 0.0
			return


## Any other unit of this layer moving within r of p (traffic that a unit returning to p would get in the way of).
func _movers_near(p: Vector3, r: float) -> bool:
	var nb: Dictionary = battle.nbr_ground if domain == "ground" else battle.nbr_heli
	var cs: float = battle.NB_CELL
	var kx := floori(p.x / cs); var kz := floori(p.z / cs)
	var span := ceili(r / cs)
	for dz in range(-span, span + 1):
		for dx in range(-span, span + 1):
			var cell: Variant = nb.get(Vector2i(kx + dx, kz + dz))
			if cell == null: continue
			for o: Unit in cell:
				if o == self or o.state == S.IDLE: continue
				if o.speed_cur > 0.3 and Vector2(o.position.x - p.x, o.position.z - p.z).length() < r: return true
	return false


## Another unit of this layer standing on p (within the two bodies' radii).
func _occupied(p: Vector3) -> bool:
	var nb: Dictionary = battle.nbr_ground if domain == "ground" else battle.nbr_heli
	var cs: float = battle.NB_CELL
	var kx := floori(p.x / cs); var kz := floori(p.z / cs)
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			var cell: Variant = nb.get(Vector2i(kx + dx, kz + dz))
			if cell == null: continue
			for o: Unit in cell:
				if o == self: continue
				if Vector2(o.position.x - p.x, o.position.z - p.z).length() < (body_r() + o._body_r) * 0.9: return true
	return false


## Hover / cruise height: helicopters and jets are spread over a few altitude layers so airframes never intersect.
func cruise_alt() -> float:
	var n := 4 if domain == "jet" else 3
	var l := alt_layer if alt_layer >= 0 else uid % n
	return float(def.altitude) + float(l % n) * (3.5 if domain == "jet" else 1.5)


## Jets never stop in the air. Phases: take-off roll from the pad -> climb -> orbit / move / attack runs ->
## return pattern (approach point south of the pad, aligned final, touchdown on the pad centre facing north) ->
## landed and rearming. Attack runs: fly in, fire while the target is inside the weapon window, overfly,
## extend straight for a moment, then turn back for another pass (no endless circling inside the turn radius).
func _jet_tick(dt: float) -> void:
	if state == S.LANDED:
		airborne = false
		speed_cur = 0.0
		taxi_phase = 0
		taxi_i = 0
		altitude = move_toward(altitude, ground_alt(), dt * 8.0)
		position = position.move_toward(home, dt * 6.0)
		heading = lerp_angle(heading, park_heading, minf(1.0, dt * 3.0))
		bank = 0.0
		rearm_t -= dt
		if rearm_t <= 0.0:
			rearm_t = 1.5
			for i in w_ammo.size():
				var full := int(def.weapons[i].get("ammo", -1))
				if full > 0 and w_ammo[i] < full: w_ammo[i] += 1; break
		vel = Vector3.ZERO
		return
	if not airborne and has_runway and taxi_phase >= 2:
		_runway_landing_ground(dt)
		return
	if not airborne and has_runway and taxi_phase == 0:
		# taxi from the parking spot to the runway threshold, then line up on the runway heading
		bank = 0.0
		altitude = ground_alt()
		while taxi_i < taxi_out.size() - 1 and flat_dist(taxi_out[taxi_i]) < 3.0: taxi_i += 1
		var tgt: Vector3 = taxi_out[taxi_i] if taxi_i < taxi_out.size() else rw_start
		if taxi_i < taxi_out.size() - 1 or flat_dist(rw_start) > 2.0:
			_taxi_to(tgt, dt)
		else:
			position = Vector3(rw_start.x, 0, rw_start.z)
			heading = _runway_heading()
			speed_cur = 0.0
			taxi_phase = 1
			taxi_i = 0
		vel = forward() * speed_cur
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
	altitude = move_toward(altitude, maxf(cruise_alt(), climb_y - position.y) if climb_t > 0.0 else cruise_alt(), dt * (45.0 if climb_t > 0.0 else maxf(6.0, speed_cur * 0.3)))
	var steer := goal
	var throttle: float = def.speed
	var min_v: float = def.min_speed
	match state:
		S.IDLE, S.MOVE:
			if state == S.MOVE and flat_dist(goal) < 25.0:
				if queue.is_empty(): state = S.IDLE
				else: goal = queue.pop_front()
			steer = _orbit_point(goal, 60.0) if state == S.IDLE else goal
			if state == S.IDLE: _acquire(sight_r() * 0.7)
			if state == S.IDLE and target: state = S.ATTACK
		S.ATTACK_MOVE:
			_acquire(sight_r())
			steer = _run_steer(target.position, dt) if target else goal
			if target == null and flat_dist(goal) < 25.0: state = S.IDLE
		S.ATTACK:
			if target: steer = _run_steer(target.position, dt)
			else: state = S.IDLE
		S.FORCE_GROUND:
			steer = _run_steer(force_pos, dt)
		S.GUARD:
			if guard_unit and not guard_unit.dead: guard_pos = guard_unit.position
			if target == null: target = battle.find_enemy_near_point(self, guard_pos, sight_r())
			steer = _run_steer(target.position, dt) if target else _orbit_point(guard_pos, 60.0)
		S.RETURN when has_runway:
			# land on the runway: long final aligned with it, touch down at the threshold, roll out, taxi back
			var rdir := (rw_end - rw_start).normalized()
			var approach := rw_start - rdir * 120.0
			if ret_phase == 0:
				steer = approach
				if flat_dist(approach) < 35.0: ret_phase = 1
			else:
				steer = rw_start + rdir * 6.0
				var d := flat_dist(rw_start)
				var to_thr := Vector3(rw_start.x - position.x, 0, rw_start.z - position.z)
				var err := absf(wrapf(atan2(-to_thr.x, -to_thr.z) - heading, -PI, PI))
				if d > 25.0 and err > deg_to_rad(60.0):
					ret_phase = 0                                 # badly aligned: go around
				altitude = move_toward(altitude, def.altitude * clampf((d - 2.0) / 120.0, 0.0, 1.0) + ground_alt(), dt * 12.0)
				throttle = clampf(d * 0.3, def.min_speed * 0.5, def.speed * 0.75)
				min_v = 4.0
				if d < 6.0 or (to_thr.dot(rdir) < 0.0 and d < 20.0):
					airborne = false; taxi_phase = 2; altitude = ground_alt()
					position = Vector3(position.x, 0, position.z)
					heading = _runway_heading()
					return
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
	if state != S.RETURN or ret_phase == 0: steer = _jet_separate(steer, dt)
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


func ground_alt() -> float:
	return 0.0 if vis and def.has("model3d") and ResourceLoader.exists(str(def.model3d)) else 0.4


func _runway_heading() -> float:
	var d := rw_end - rw_start
	return atan2(-d.x, -d.z)


## Ground movement for jets: slow taxi with tight turns.
func _taxi_to(p: Vector3, dt: float) -> void:
	var to := Vector3(p.x - position.x, 0, p.z - position.z)
	var diff := wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
	var step := deg_to_rad(110.0) * dt
	heading = wrapf(heading + clampf(diff, -step, step), -PI, PI)
	var ts := 7.0 * clampf(cos(diff), 0.15, 1.0)
	ts = minf(ts, maxf(1.5, to.length() * 1.5))
	speed_cur = move_toward(speed_cur, ts, 6.0 * dt)
	position += forward() * speed_cur * dt


## After touchdown: brake along the runway, then taxi to the parking spot and park.
func _runway_landing_ground(dt: float) -> void:
	bank = 0.0
	if state != S.RETURN and taxi_phase == 3:
		taxi_phase = 0          # new orders while taxiing in: turn round and take off again
		taxi_i = 0
		return
	altitude = ground_alt()
	if taxi_phase == 2:
		speed_cur = move_toward(speed_cur, 7.0, def.accel * 1.2 * dt)
		position += forward() * speed_cur * dt
		var along := (position - rw_start).dot((rw_end - rw_start).normalized())
		if speed_cur <= 7.5 or along > (rw_end - rw_start).length() * 0.8:
			taxi_phase = 3
			taxi_i = 0
	else:
		while taxi_i < taxi_in.size() - 1 and flat_dist(taxi_in[taxi_i]) < 3.0: taxi_i += 1
		if taxi_i < taxi_in.size() - 1:
			_taxi_to(taxi_in[taxi_i], dt)
		elif flat_dist(home) > 1.5:
			_taxi_to(home, dt)
		else:
			position = Vector3(home.x, 0, home.z)
			state = S.LANDED; rearm_t = 1.5; speed_cur = 0.0; taxi_phase = 0
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


## Jet-vs-jet separation in flight: predict the closest approach to every airborne jet near this one's altitude over
## the next 2.5 s; if it falls inside the safety distance, bend the steering point away from it. Jets of one group
## fly on separate altitude layers (cruise_alt), so this only has to act between jets sharing a layer.
func _jet_separate(steer: Vector3, dt: float) -> Vector3:
	var me := Vector2(position.x, position.z)
	var v := Vector2(vel.x, vel.z)
	var push := Vector2.ZERO
	var my_y := position.y + altitude
	climb_t = maxf(0.0, climb_t - dt)
	for o: Unit in battle.air_jets:
		if o == self or o.dead or not o.airborne: continue
		var p := Vector2(o.position.x, o.position.z) - me
		if p.length_squared() > 200.0 * 200.0: continue
		var dv := (o.position.y + o.altitude) - my_y
		if absf(dv) > 6.0: continue
		var w := v - Vector2(o.vel.x, o.vel.z)
		var t := clampf(p.dot(w) / maxf(w.length_squared(), 1e-3), 0.0, 2.5)
		var miss := p - w * t
		var need := (body_r() + o.body_r()) * 1.8
		var ml := miss.length()
		if ml < need:
			var away := -miss / ml if ml > 0.01 else Vector2(-v.y, v.x).normalized() * (1.0 if uid > o.uid else -1.0)
			push += away * (need - ml) / need
			# over hills each jet follows its own terrain look-ahead, so layers can close up: the higher id climbs over
			if uid > o.uid and absf(dv) < 4.0:
				climb_t = 1.5
				climb_y = maxf(climb_y if climb_t > 0.0 else -INF, o.position.y + o.altitude + 4.5)
	if push == Vector2.ZERO: return steer
	var sd := Vector2(steer.x, steer.z) - me
	var dir := (sd.normalized() if sd.length() > 0.1 else Vector2(-sin(heading), -cos(heading))) + push * 2.0
	dir = dir.normalized() * maxf(sd.length(), 60.0)
	return Vector3(me.x + dir.x, 0, me.y + dir.y)


func _aim_turret(dt: float) -> void:
	if turret == null: return
	var want_local := 0.0
	var aim_at: Variant = null
	if target and flat_dist(target.position) <= sight_r(): aim_at = target.position
	elif state == S.FORCE_GROUND: aim_at = force_pos
	if aim_at != null:
		var to: Vector3 = aim_at - position
		want_local = wrapf(atan2(-to.x, -to.z) - heading, -PI, PI)
	var diff := wrapf(want_local - turret_yaw, -PI, PI)
	var step := deg_to_rad(float(def.get("turret_turn_deg", 120.0))) * dt
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
		if d > w.range or d < float(w.get("min_range", 0.0)): continue
		var to: Vector3 = tpos - position
		var bearing := atan2(-to.x, -to.z)
		var facing_err: float
		if w.get("turret", false) and turret:
			facing_err = absf(wrapf(bearing - heading - turret_yaw, -PI, PI))
			if facing_err > deg_to_rad(3.0): continue
		else:
			facing_err = absf(wrapf(bearing - heading, -PI, PI))
			if facing_err > deg_to_rad(w.get("facing_deg", 15.0)): continue
		w_reload[i] = w.reload * Veterancy.mult(self, "reload")
		if w_ammo[i] > 0: w_ammo[i] -= 1
		if w.proj in ["shell", "arty"]: recoil = 0.55
		last_fire_t = battle.sim_time
		battle.fire(self, w, tunit, tpos)


func muzzle_pos() -> Vector3:
	if muzzle: return muzzle.global_position
	return global_position + Vector3.UP * (altitude - 0.3) + forward() * float(def.get("length", 4.0)) * 0.25


func take_damage(amount: float, from: Unit) -> void:
	if dead: return
	amount *= Veterancy.mult(self, "taken") * battle.taken_mult(self)
	hp -= amount
	if hp <= 0.0:
		hp = 0.0
		die()
		if from and not from.dead and from.team != team and from.team >= 0: from.add_xp(Veterancy.kill_xp(self))
	elif target == null and from and not from.dead and can_target(from) and state in [S.IDLE, S.GUARD]:
		target = from   # return fire


func add_xp(x: float) -> void:
	if x <= 0.0 or dead or not Veterancy.eligible(self): return
	vet_xp += x * battle.xp_mult(team)
	while vet_rank < Veterancy.RANKS.size() - 1 and vet_xp >= Veterancy.XP_TO_RANK[vet_rank + 1]:
		vet_rank += 1
		battle.on_promoted(self)


func die() -> void:
	dead = true
	set_selected(false)
	for m in mats:
		(m as ShaderMaterial).set_shader_parameter("burnt", 1.0)
	battle.on_unit_died(self)

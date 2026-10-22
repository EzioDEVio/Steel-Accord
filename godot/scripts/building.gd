# Steel Accord - a structure: constructed by a Dozer, consumes or generates power, produces units through a queue,
# optionally fights (Defense Tower). It is a Unit for selection, targeting, damage and fog purposes, but never moves.
# Visual: the supplied building concept art as a camera-facing card standing on the footprint's camera-side edge
# (see shaders/structure.gdshader). Footprints block the pathfinding grid while the structure stands.
class_name Building
extends Unit

var bkind := ""
var bdef: Dictionary
var progress := 1.0          # construction 0..1
var built := true
var prod_queue: Array = []   # unit kinds
var prod_left := 0.0
var rally := Vector3.ZERO
var has_rally := false
var card: MeshInstance3D
var card_mat: ShaderMaterial
var outline: MeshInstance3D
var art: Dictionary
var half := Vector2.ONE
var pads: Array = []         # airfield: [{"pos": Vector3, "uid": int}]
var build_snd: AudioStreamPlayer3D
var builder_seen_t := 0.0    # sim time when a dozer last worked on it
var ever_seen := false
var _depth_px := 0.0

const STRUCTURE_SHADER := preload("res://shaders/structure.gdshader")


func setup_structure(b: Node, building_kind: String, t: int, id: int, pos: Vector3, start_built: bool) -> void:
	battle = b; bkind = building_kind; bdef = BuildingDefs.DEFS[building_kind]; team = t; uid = id
	kind = building_kind
	domain = "ground"
	half = bdef.size * 0.5
	def = {"name": bdef.name, "hp": bdef.hp, "radius": maxf(half.x, half.y) * 0.8, "height": 6.0, "sight": bdef.sight,
		"speed": 0.0, "accel": 0.0, "turn_deg": 0.0, "weapons": bdef.get("weapons", []), "structure": true,
		"icon": "", "armor": "structure", "visual": "structure"}
	hp = bdef.hp if start_built else bdef.hp * 0.1
	progress = 1.0 if start_built else 0.0
	built = start_built
	name = "%s_%d" % [building_kind, id]
	for w in def.weapons:
		w_reload.append(0.0)
		w_ammo.append(-1)
	body = Node3D.new()
	add_child(body)
	position = pos
	home = pos
	rally = pos + Vector3(0, 0, half.y + 10.0) * (1.0 if team == 0 else -1.0)
	art = UsArt.building(bdef.art)
	if not art.is_empty():
		def.icon = art.get("icon", "")
	_build_card()
	_build_outline()
	ring = _make_ring()
	add_child(ring)
	if bdef.has("pads"):
		for i in int(bdef.pads):
			var px := (float(i) - (int(bdef.pads) - 1) * 0.5) * 30.0
			var dz := (half.y + 18.0) * (1.0 if team == 0 else -1.0)
			pads.append({"pos": pos + Vector3(px, 0, dz), "uid": -1})
	battle.gnav.set_structure(position, half + Vector2(1.0, 1.0), true)


func _build_card() -> void:
	card = MeshInstance3D.new()
	var q := QuadMesh.new()
	card_mat = ShaderMaterial.new()
	card_mat.shader = STRUCTURE_SHADER
	var tex: Texture2D = null
	if not art.is_empty() and ResourceLoader.exists(str(art.get("main", ""))):
		tex = load(art.main)
	if tex == null:
		# no art yet: a plain grey card so the structure is still visible and selectable
		var img := Image.create(64, 48, false, Image.FORMAT_RGBA8)
		img.fill(Color(0.45, 0.45, 0.42, 1.0))
		tex = ImageTexture.create_from_image(img)
	var wpx := float(tex.get_width()); var hpx := float(tex.get_height())
	var base_px := float(art.get("base_width_px", wpx * 0.8))
	var anchor: Array = art.get("anchor_px", [wpx * 0.5, hpx * 0.75])
	var px: float = bdef.size.x / maxf(base_px, 1.0)            # metres per art pixel
	# the card pivots on the footprint edge nearest the camera: the anchor (footprint centre in the art) sits
	# above that edge by half the footprint depth as the art's steep high-angle view draws it
	_depth_px = bdef.size.y * 0.5 / px * 0.62
	var pivot := Vector2(float(anchor[0]), float(anchor[1]) + _depth_px)
	q.size = Vector2(wpx, hpx) * px
	q.center_offset = Vector3((wpx * 0.5 - pivot.x) * px, (pivot.y - hpx * 0.5) * px, 0.0)
	q.material = card_mat
	card_mat.set_shader_parameter("art", tex)
	card_mat.set_shader_parameter("art_px", Vector2(wpx, hpx))
	card_mat.set_shader_parameter("team_color", UnitDefs.TEAM_COLORS[team])
	card_mat.set_shader_parameter("team_tint", 0.0 if team == 0 else 0.12)
	card_mat.set_shader_parameter("progress", progress)
	card_mat.set_shader_parameter("fog_xz", Vector2(position.x, position.z))
	card.mesh = q
	card.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	card.extra_cull_margin = 40.0
	body.add_child(card)
	model = card


## Team-coloured footprint outline on the ground (also the readable team marker for both sides).
func _build_outline() -> void:
	outline = MeshInstance3D.new()
	var im := ImmediateMesh.new()
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = UnitDefs.TEAM_COLORS[team].lightened(0.25)
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLES, m)
	var w := 0.5
	for e in [[Vector2(-half.x, -half.y), Vector2(half.x, -half.y)], [Vector2(half.x, -half.y), Vector2(half.x, half.y)],
			[Vector2(half.x, half.y), Vector2(-half.x, half.y)], [Vector2(-half.x, half.y), Vector2(-half.x, -half.y)]]:
		var a: Vector2 = e[0]; var b: Vector2 = e[1]
		var n := (b - a).normalized().orthogonal() * w
		for v in [a - n, b - n, b + n, a - n, b + n, a + n]:
			im.surface_add_vertex(Vector3(v.x, 0.15, v.y))
	im.surface_end()
	outline.mesh = im
	outline.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(outline)


func _process(_dt: float) -> void:
	if card == null: return
	# keep the card on the footprint edge that faces the camera
	var cam := get_viewport().get_camera_3d()
	if cam:
		var to_cam := cam.global_position - global_position
		to_cam.y = 0.0
		if to_cam.length() > 0.01:
			to_cam = to_cam.normalized()
			var reach := absf(to_cam.x) * half.x + absf(to_cam.z) * half.y
			card.position = to_cam * reach * 0.9 + Vector3(0, 0.2, 0)
	card_mat.set_shader_parameter("progress", progress)
	card_mat.set_shader_parameter("highlight", 1.0 if selected else 0.0)


func _make_ring() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = Vector3(bdef.size.x + 2.0, 0.1, bdef.size.y + 2.0)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0.35, 1.0, 0.45, 0.35) if team == 0 else Color(1.0, 0.3, 0.25, 0.35)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	b.material = m
	mi.mesh = b
	mi.position.y = 0.1
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.visible = false
	return mi


func world_center() -> Vector3:
	return global_position + Vector3.UP * 3.0


func muzzle_pos() -> Vector3:
	return global_position + Vector3.UP * 9.0


func footprint_dist(p: Vector3) -> float:
	var dx := maxf(0.0, absf(p.x - position.x) - half.x)
	var dz := maxf(0.0, absf(p.z - position.z) - half.y)
	return Vector2(dx, dz).length()


# ------------------------------------------------------------------ simulation
func sim_tick(dt: float) -> void:
	if dead: return
	var powered: bool = battle.power_ok(team)
	if build_snd and battle.sim_time - builder_seen_t > 0.5:
		build_snd.queue_free(); build_snd = null
	if not built: return
	# weapons (towers): auto-acquire, no hull to turn
	if not def.weapons.is_empty():
		for i in w_reload.size(): w_reload[i] = maxf(0.0, w_reload[i] - dt * (1.0 if powered else 0.4))
		if target and (target.dead or flat_dist(target.position) > def.weapons[0].range):
			target = null
		if target == null:
			target = battle.find_enemy_near(self, def.weapons[0].range)
		_fire_weapons()
	# production
	if not prod_queue.is_empty():
		prod_left -= dt * (1.0 if powered else BuildingDefs.LOW_POWER_RATE)
		if prod_left <= 0.0:
			var k: String = prod_queue.pop_front()
			battle.spawn_produced(self, k)
			if not prod_queue.is_empty():
				prod_left = float(BuildingDefs.UNIT_COST[prod_queue[0]][1])


func weapons_ready() -> bool:
	return built


## Called by a dozer each tick it works on the site. Returns true when construction completes.
func construct(dt: float) -> bool:
	if built: return true
	builder_seen_t = battle.sim_time
	if build_snd == null:
		build_snd = SFX.loop(self, "construction_loop", -8.0)
	var rate := (1.0 if battle.power_ok(team) or bdef.power > 0 else BuildingDefs.LOW_POWER_RATE) / float(bdef.build_time)
	progress = minf(1.0, progress + dt * rate)
	hp = minf(bdef.hp, hp + bdef.hp * 0.9 * dt * rate)
	if progress >= 1.0:
		built = true
		battle.on_structure_built(self)
		if build_snd: build_snd.queue_free(); build_snd = null
	return built


func queue_unit(k: String) -> void:
	if prod_queue.is_empty():
		prod_left = float(BuildingDefs.UNIT_COST[k][1])
	prod_queue.append(k)


func cancel_last() -> String:
	if prod_queue.is_empty(): return ""
	var k: String = prod_queue.pop_back()
	if prod_queue.is_empty(): prod_left = 0.0
	return k


func free_pad() -> int:
	for i in pads.size():
		var u: Unit = battle.by_id.get(int(pads[i].uid))
		if u == null or u.dead: return i
	return -1


func take_damage(amount: float, from: Unit) -> void:
	if dead: return
	hp -= amount
	if hp <= 0.0:
		hp = 0.0
		die()


func die() -> void:
	dead = true
	set_selected(false)
	card_mat.set_shader_parameter("burnt", 1.0)
	if build_snd: build_snd.queue_free(); build_snd = null
	battle.gnav.set_structure(position, half + Vector2(1.0, 1.0), false)
	outline.visible = false
	battle.on_unit_died(self)

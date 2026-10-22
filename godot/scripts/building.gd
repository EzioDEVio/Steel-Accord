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
var repairing := false
var repair_debt := 0.0        # cash owed for repairs, charged in whole dollars
var repair_blocked := ""      # why repair is paused ("" = running)
var sold := false
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
	rally = pos + front_dir() * (half.y + 10.0)
	art = UsArt.building(bdef.art)
	if not art.is_empty():
		def.icon = art.get("icon", "")
	_build_card()
	_build_outline()
	ring = _make_ring()
	add_child(ring)
	if bdef.has("pads"):
		for p in pad_positions(pos, bdef):
			pads.append({"pos": p, "uid": -1})
		_build_pads()
	battle.gnav.set_structure(position, half + Vector2(1.0, 1.0), true)


## Structures face the map centre (their doors, exits and the airfield apron are on that side).
func front_dir() -> Vector3:
	return Vector3(0, 0, -1) if position.z > 0.0 else Vector3(0, 0, 1)


const PAD_SIZE := 16.0
const PAD_STEP := 18.0


## Airfield parking pads: a 2 x 2 apron directly in front of the structure (local space -> world).
static func pad_positions(pos: Vector3, d: Dictionary) -> Array:
	var fwd := Vector3(0, 0, -1) if pos.z > 0.0 else Vector3(0, 0, 1)
	var right := Vector3(-fwd.z, 0, fwd.x)
	var h: Vector2 = d.size * 0.5
	var out: Array = []
	for i in int(d.get("pads", 0)):
		var row := i / 2
		var col := i % 2
		out.append(pos + fwd * (h.y + 2.0 + PAD_SIZE * 0.5 + row * PAD_STEP) + right * ((col - 0.5) * PAD_STEP))
	return out


## Rectangle (centre, half size) covered by the apron, for placement checks.
static func apron_rect(pos: Vector3, d: Dictionary) -> Array:
	var ps := pad_positions(pos, d)
	if ps.is_empty(): return []
	var c := Vector3.ZERO
	for p in ps: c += p
	c /= ps.size()
	return [c, Vector2(PAD_STEP * 0.5 + PAD_SIZE * 0.5, PAD_STEP * 0.5 + PAD_SIZE * 0.5)]


func _build_pads() -> void:
	var con := StandardMaterial3D.new(); con.albedo_color = Color(0.46, 0.46, 0.44); con.roughness = 0.85
	var mark := StandardMaterial3D.new(); mark.albedo_color = Color(0.85, 0.8, 0.45); mark.roughness = 0.8
	for p in pads:
		var slab := MeshInstance3D.new()
		var b := BoxMesh.new(); b.size = Vector3(PAD_SIZE, 0.25, PAD_SIZE); b.material = con
		slab.mesh = b
		slab.position = p.pos - position + Vector3(0, 0.08, 0)
		add_child(slab)
		var ring_m := MeshInstance3D.new()
		var t := TorusMesh.new(); t.inner_radius = 5.2; t.outer_radius = 5.7; t.material = mark
		ring_m.mesh = t; ring_m.scale = Vector3(1, 0.02, 1)
		ring_m.position = p.pos - position + Vector3(0, 0.22, 0)
		add_child(ring_m)


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
	_repair_tick(dt)
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


## Repair: restores REPAIR_RATE of max health per second at REPAIR_COST_FRACTION of the build cost for a full repair,
## paid as it goes. Pauses (and says why) when the owner runs out of cash; stops when full.
const REPAIR_RATE := 0.04
const REPAIR_COST_FRACTION := 0.5


func repair_cost_per_s() -> float:
	return float(bdef.cost) * REPAIR_COST_FRACTION * REPAIR_RATE


func _repair_tick(dt: float) -> void:
	if not repairing: return
	if hp >= bdef.hp:
		hp = bdef.hp; repairing = false; repair_blocked = ""
		return
	var heal: float = minf(bdef.hp * REPAIR_RATE * dt, bdef.hp - hp)
	var cost: float = heal / bdef.hp * float(bdef.cost) * REPAIR_COST_FRACTION
	if float(battle.cash[team]) < repair_debt + cost:
		if repair_blocked == "" and team == 0 and battle.hud: battle.hud.flash_message("Repair paused: not enough cash")
		repair_blocked = "Not enough cash"
		return
	repair_blocked = ""
	hp += heal
	repair_debt += cost
	var whole := int(repair_debt)
	if whole > 0:
		battle.cash[team] -= whole
		repair_debt -= whole


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
	repairing = false
	battle.on_unit_died(self)
	if not sold and built:
		battle.add_rubble(self)
		card.visible = false
	visible = false if sold else visible

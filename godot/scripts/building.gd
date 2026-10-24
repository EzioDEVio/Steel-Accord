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
var drop_t := 25.0          # first supply drop 25 s after completion
var research_id := ""        # upgrade being researched here (Upgrades.DEFS)
var research_left := 0.0
var _depth_px := 0.0
var yaw := 0.0               # facing chosen at placement (radians about +Y; 0 = model front toward +Z, as authored)
var seg_scale := 1.0         # walls: length factor of this segment (a drawn line is split into equal segments)
var wall_run := 0            # walls: segments drawn in one drag share a run id
var gar_target: Unit = null  # occupied civic building: enemy the occupants were ordered to attack
var retaliate: Unit = null   # occupied civic building: last enemy that damaged it (occupants return fire)
var retaliate_t := -99.0
var flag_node: Node3D = null # occupied civic building: flagpole with the occupier's flag (presentation)
var flag_team := -9

const STRUCTURE_SHADER := preload("res://shaders/structure.gdshader")


func setup_structure(b: Node, building_kind: String, t: int, id: int, pos: Vector3, start_built: bool, yaw_r := 0.0, sx := 1.0) -> void:
	battle = b; bkind = building_kind; bdef = BuildingDefs.DEFS[building_kind]; team = t; uid = id
	kind = building_kind
	domain = "ground"
	yaw = wrapf(yaw_r, -PI, PI)
	seg_scale = sx if is_wall() else 1.0
	half = Vector2(bdef.size.x * 0.5 * seg_scale, bdef.size.y * 0.5)
	rotation.y = yaw
	heading = yaw
	def = {"name": Nations.label(b.nation_of(t), building_kind, bdef.name), "hp": bdef.hp, "radius": maxf(half.x, half.y) * 0.8, "height": 6.0, "sight": bdef.sight,
		"speed": 0.0, "accel": 0.0, "turn_deg": 0.0, "weapons": bdef.get("weapons", []), "structure": true,
		"icon": "", "armor": "structure", "visual": "structure"}
	if bdef.has("transport"): def["transport"] = bdef.transport      # civilian buildings: infantry occupy them
	hp = bdef.hp if start_built else bdef.hp * 0.1
	progress = 1.0 if start_built else 0.0
	built = start_built
	name = "%s_%d" % [building_kind, id]
	for w in def.weapons:
		w_reload.append(0.0)
		w_ammo.append(-1)
	body = Node3D.new()
	add_child(body)
	body.scale.x = seg_scale
	position = pos
	home = pos
	rally = pos + front_dir() * (reach_along(front_dir()) + 10.0)
	art = UsArt.building(bdef.art)
	if not art.is_empty():
		def.icon = art.get("icon", "")
	var m3: String = str(bdef.get("model3d", ""))
	if m3 != "" and ResourceLoader.exists(m3):
		_build_model(m3)
	else:
		_build_card()
	_build_outline()
	ring = _make_ring()
	add_child(ring)
	if bdef.has("pads"):
		if not model_pads.is_empty():
			for p in model_pads: pads.append({"pos": p, "uid": -1})
		else:
			for p in pad_positions(pos, bdef):
				pads.append({"pos": p, "uid": -1})
			_build_pads()
	nav_block(true)


## Marks (or clears) this structure's oriented footprint, grown by 1 m, on the navigation grids.
func nav_block(on: bool) -> void:
	battle.nav_set_structure(position, half + Vector2(1.0, 1.0), on, yaw)


func is_civic() -> bool:
	return bdef.get("civic", false)


func is_wall() -> bool:
	return bdef.get("wall", false)


# ---- oriented footprint (the structure's local X / Z axes are rotated by `yaw` about +Y)
## World point -> footprint-local (x, z) relative to `center` for a box rotated by yaw_r.
static func to_local_xz(center: Vector3, yaw_r: float, p: Vector3) -> Vector2:
	var dx := p.x - center.x; var dz := p.z - center.z
	var c := cos(yaw_r); var s := sin(yaw_r)
	return Vector2(dx * c - dz * s, dx * s + dz * c)


static func local_to_world(center: Vector3, yaw_r: float, l: Vector2) -> Vector3:
	var c := cos(yaw_r); var s := sin(yaw_r)
	return Vector3(center.x + l.x * c + l.y * s, center.y, center.z - l.x * s + l.y * c)


## Half extents of the axis-aligned box that encloses a rotated footprint (terrain checks and flattening).
static func aabb_half(h: Vector2, yaw_r: float) -> Vector2:
	var c := absf(cos(yaw_r)); var s := absf(sin(yaw_r))
	return Vector2(h.x * c + h.y * s, h.x * s + h.y * c)


## Separating-axis test between two oriented footprints.
static func obb_overlap(c1: Vector3, h1: Vector2, y1: float, c2: Vector3, h2: Vector2, y2: float) -> bool:
	var axes := [Vector2(cos(y1), -sin(y1)), Vector2(sin(y1), cos(y1)), Vector2(cos(y2), -sin(y2)), Vector2(sin(y2), cos(y2))]
	var d := Vector2(c2.x - c1.x, c2.z - c1.z)
	for a: Vector2 in axes:
		var r1 := h1.x * absf(axes[0].dot(a)) + h1.y * absf(axes[1].dot(a))
		var r2 := h2.x * absf(axes[2].dot(a)) + h2.y * absf(axes[3].dot(a))
		if absf(d.dot(a)) >= r1 + r2: return false
	return true


## The four footprint corners in world space (minimap, debugging).
static func corners(center: Vector3, h: Vector2, yaw_r: float) -> Array:
	return [local_to_world(center, yaw_r, Vector2(-h.x, -h.y)), local_to_world(center, yaw_r, Vector2(h.x, -h.y)),
		local_to_world(center, yaw_r, Vector2(h.x, h.y)), local_to_world(center, yaw_r, Vector2(-h.x, h.y))]


func local_xz(p: Vector3) -> Vector2:
	return to_local_xz(position, yaw, p)


func contains_xz(p: Vector3, margin := 0.0) -> bool:
	var l := local_xz(p)
	return absf(l.x) < half.x + margin and absf(l.y) < half.y + margin


## Ground units overlapping the footprint (plus radius r) are moved out along the shallowest local axis.
func push_out(p: Vector3, r: float) -> Vector3:
	var l := local_xz(p)
	var ex := half.x + r - absf(l.x)
	var ez := half.y + r - absf(l.y)
	if ex <= 0.0 or ez <= 0.0: return p
	if ex < ez: l.x += signf(l.x if l.x != 0.0 else 1.0) * ex
	else: l.y += signf(l.y if l.y != 0.0 else 1.0) * ez
	var w := local_to_world(position, yaw, l)
	return Vector3(w.x, p.y, w.z)


## Distance from the centre to the footprint edge along a world direction (support of the oriented box).
func reach_along(dir: Vector3) -> float:
	var l := to_local_xz(Vector3.ZERO, yaw, Vector3(dir.x, 0, dir.z))
	return absf(l.x) * half.x + absf(l.y) * half.y


## The two ends of a wall segment (world, on its centre line).
func wall_ends() -> Array:
	return [local_to_world(position, yaw, Vector2(-half.x, 0)), local_to_world(position, yaw, Vector2(half.x, 0))]


## Firing position for occupant i (model ports, else points round the roof edge).
func port(i: int) -> Vector3:
	if not ports.is_empty(): return ports[i % ports.size()]
	var a := TAU * float(i) / 8.0
	return position + Vector3(cos(a) * half.x * 0.9, model_h * 0.6, sin(a) * half.y * 0.9)


## Default exit / rally side: toward the map centre for an unrotated structure, turned with the structure's yaw.
func front_dir() -> Vector3:
	var d := Vector3(0, 0, -1) if position.z > 0.0 else Vector3(0, 0, 1)
	return Basis(Vector3.UP, yaw) * d


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


## Airfield taxi route for pad i (world points, y = 0), built in the airfield's local space so a rotated airfield
## works. Out: lane abeam the pad -> hold-short line -> runway centreline at the lane -> RunwayEnd (the '27' end,
## where jets turn round for a take-off roll toward '09'). In: runway at the lane -> hold-short -> lane abeam the
## pad -> pad. The lane runs between the pad columns, so jets never cross the hangar or the tower.
const HOLD_SHORT := 12.5    # hold-short point: metres from the runway centreline back along the lane

func taxi_route(i: int, out: bool) -> Array:
	if runway.size() != 2 or i < 0 or i >= pads.size(): return []
	var ls: Vector3 = to_local(runway[0])
	var le: Vector3 = to_local(runway[1])
	var lane_x := 0.0
	for p in pads: lane_x += to_local(p.pos).x
	lane_x /= pads.size()
	var lp: Vector3 = to_local(pads[i].pos)
	var a := Vector3(lane_x, 0, lp.z)        # lane abeam the pad
	var b := Vector3(lane_x, 0, ls.z)        # lane meets the runway centreline
	var h := b + Vector3(0, 0, signf(lp.z - ls.z) * HOLD_SHORT)
	var pts: Array = [a, h, b, Vector3(le.x, 0, le.z)] if out else [b, h, a, Vector3(lp.x, 0, lp.z)]
	return pts.map(func(q): var g: Vector3 = to_global(q); return Vector3(g.x, 0, g.z))


## Rectangle (centre, half size) covered by the apron, for placement checks.
static func apron_rect(pos: Vector3, d: Dictionary) -> Array:
	if ResourceLoader.exists(str(d.get("model3d", "_"))): return []   # 3D airfield: pads are inside its footprint
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
		slab.position = to_local(p.pos) + Vector3(0, 0.08, 0)
		add_child(slab)
		var ring_m := MeshInstance3D.new()
		var t := TorusMesh.new(); t.inner_radius = 5.2; t.outer_radius = 5.7; t.material = mark
		ring_m.mesh = t; ring_m.scale = Vector3(1, 0.02, 1)
		ring_m.position = to_local(p.pos) + Vector3(0, 0.22, 0)
		add_child(ring_m)


# ---- real 3D structure (pilot: Supply Depot). Origin = centre of the foundation at ground level.
const REVEAL_SHADER := preload("res://shaders/build_reveal.gdshader")
var model3d: Node3D
var mesh_list: Array = []        # [MeshInstance3D, surface, original material]
var reveal_mats: Array = []
var model_h := 8.0
var revealing := false


func _build_model(path: String) -> void:
	model3d = (load(path) as PackedScene).instantiate()
	body.add_child(model3d)      # authored with its front (doors, bays, apron) toward +Z: the default camera side
	model = model3d
	_collect_model_nodes()
	var top := 0.0
	for mi in model3d.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if String(m.name).begins_with("Light_"): continue
		m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		top = maxf(top, (m.get_aabb().end.y) * m.global_transform.basis.get_scale().y if m.is_inside_tree() else m.get_aabb().end.y)
		for si in m.mesh.get_surface_count():
			mesh_list.append([m, si, m.get_active_material(si)])
	model_h = maxf(top, 3.0)
	if is_wall(): tint_team(model3d)
	if not built: _set_reveal(true)


## Walls: the model's team-marker surfaces (material "SA_Team") take the owner's colour.
func tint_team(n: Node) -> void:
	var tm := StandardMaterial3D.new()
	tm.albedo_color = UnitDefs.team_color(team); tm.roughness = 0.7; tm.resource_name = "team_tint"
	for mi in n.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if m.mesh == null: continue
		for si in m.mesh.get_surface_count():
			var sm := m.mesh.surface_get_material(si)
			if sm and sm.resource_name.begins_with("SA_Team"):
				m.set_surface_override_material(si, tm)
				for e in mesh_list:
					if e[0] == m and e[1] == si: e[2] = tm


# ---- named nodes inside structure models (see docs/M1_STRUCTURES_*.md)
var model_pads: Array = []          # airfield parking spots (world)
var runway := []                    # [start, end] world points, airfield only
var exit_node: Node3D
var ports: Array = []               # civilian buildings: window / roof positions occupants fire from (world)
var door_pos := Vector3.INF
var repair_bay: Node3D
var drop_point: Node3D
var radar_dish: Node3D
var b_turret: Node3D
var b_muzzle: Node3D
var lights := {"status": [], "beacon": [], "flood": [], "runway": []}   # [MeshInstance3D, StandardMaterial3D]
var light_t := 0.0
var turret_off := INF


func _collect_model_nodes() -> void:
	var pad_nodes := {}
	for n in model3d.find_children("*", "Node3D", true, false):
		var nm := String(n.name)
		if nm.begins_with("Pad") and nm.substr(3).is_valid_int(): pad_nodes[int(nm.substr(3))] = n
		elif nm == "RunwayStart": runway.resize(2); runway[0] = (n as Node3D).global_position
		elif nm == "RunwayEnd": runway.resize(2); runway[1] = (n as Node3D).global_position
		elif nm == "Exit": exit_node = n
		elif nm == "RepairBay": repair_bay = n
		elif nm == "DropPoint": drop_point = n
		elif nm == "RadarDish": radar_dish = n
		elif nm == "Turret": b_turret = n
		elif nm == "Muzzle": b_muzzle = n
		elif nm.begins_with("Port") and nm.substr(4).is_valid_int(): ports.append((n as Node3D).global_position)
		elif nm == "Door": door_pos = (n as Node3D).global_position
		elif nm.begins_with("Light_") and n is MeshInstance3D:
			var mi := n as MeshInstance3D
			var src := mi.get_active_material(0)
			var m := StandardMaterial3D.new()
			m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			m.emission_enabled = true
			mi.set_surface_override_material(0, m)
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			var group := "status"
			if nm.begins_with("Light_Beacon"): group = "beacon"
			elif nm.begins_with("Light_Flood"): group = "flood"
			elif nm.begins_with("Light_Runway"): group = "runway"
			lights[group].append([mi, m])
	var keys := pad_nodes.keys()
	keys.sort()
	for k in keys: model_pads.append((pad_nodes[k] as Node3D).global_position * Vector3(1, 0, 1))
	if runway.size() == 2 and (runway[0] == null or runway[1] == null): runway = []


## War Factory repair bay: stationary damaged vehicles near it regain 4 % health per second (2 % when under-powered).
func repair_point() -> Vector3:
	if repair_bay: return repair_bay.global_position * Vector3(1, 0, 1)
	var ep := exit_point()
	return ep if ep != Vector3.INF else position + front_dir() * (half.y + 6.0)


var servicing := false


func _service_vehicles(dt: float, powered: bool) -> void:
	var rp := repair_point()
	servicing = false
	for u in battle.units:
		if u.dead or u.team != team or u is Building or u.domain != "ground" or u.def.get("visual", "") == "infantry": continue
		if u.hp >= u.def.hp or u.speed_cur > 0.5 or u.flat_dist(rp) > 14.0: continue
		u.hp = minf(u.def.hp, u.hp + u.def.hp * (0.04 if powered else 0.02) * dt)
		servicing = true


func drop_point_world() -> Vector3:
	return drop_point.global_position * Vector3(1, 0, 1) if drop_point else position


## Units this structure offers to its owner's nation.
func produces_list() -> Array:
	return Nations.produces(battle.nation_of(team), bkind, bdef.produces)


func exit_point() -> Vector3:
	return exit_node.global_position * Vector3(1, 0, 1) if exit_node else Vector3.INF


## Status lights (presentation only): green = idle and powered, blinking amber = busy (producing, building,
## repairing), blinking red = damaged below half health or the base is under-powered. Beacons blink red,
## flood lights stay on, runway edge lights chase toward the take-off end.
func _update_lights(dt: float) -> void:
	light_t += dt
	var busy := not prod_queue.is_empty() or repairing or not built or revealing or servicing
	var bad: bool = hp < bdef.hp * 0.5 or (bdef.power < 0 and not battle.power_ok(team))
	var col := Color(0.25, 1.0, 0.35)
	var on := true
	if bad:
		col = Color(1.0, 0.15, 0.1); on = fmod(light_t, 0.6) < 0.3
	elif busy:
		col = Color(1.0, 0.7, 0.1); on = fmod(light_t, 0.9) < 0.55
	for e in lights.status:
		(e[1] as StandardMaterial3D).albedo_color = col if on else col * 0.15
		(e[1] as StandardMaterial3D).emission = col if on else Color.BLACK
		(e[1] as StandardMaterial3D).emission_energy_multiplier = 3.0
	var bon := fmod(light_t + float(uid) * 0.37, 1.4) < 0.25
	for e in lights.beacon:
		(e[1] as StandardMaterial3D).albedo_color = Color(1, 0.1, 0.05) if bon else Color(0.25, 0.02, 0.02)
		(e[1] as StandardMaterial3D).emission = Color(1, 0.1, 0.05) if bon else Color.BLACK
		(e[1] as StandardMaterial3D).emission_energy_multiplier = 4.0
	for e in lights.flood:
		(e[1] as StandardMaterial3D).albedo_color = Color(1.0, 0.95, 0.8)
		(e[1] as StandardMaterial3D).emission = Color(1.0, 0.93, 0.75)
		(e[1] as StandardMaterial3D).emission_energy_multiplier = 2.0
	var n: int = lights.runway.size()
	for i in n:
		var lit := int(light_t * 8.0) % maxi(n, 1) == i or i % 2 == 0
		var c := Color(1.0, 0.95, 0.6) if lit else Color(0.5, 0.45, 0.25)
		(lights.runway[i][1] as StandardMaterial3D).albedo_color = c
		(lights.runway[i][1] as StandardMaterial3D).emission = c
		(lights.runway[i][1] as StandardMaterial3D).emission_energy_multiplier = 2.5 if lit else 0.5
	for g in lights:
		for e in lights[g]: (e[0] as MeshInstance3D).visible = built


func _set_reveal(on: bool) -> void:
	revealing = on
	for e in mesh_list:
		var m: MeshInstance3D = e[0]
		if String(m.name).begins_with("Light_"): continue
		if on:
			var src: Material = e[2]
			var sm := ShaderMaterial.new()
			sm.shader = REVEAL_SHADER
			if src is BaseMaterial3D:
				sm.set_shader_parameter("albedo_tex", (src as BaseMaterial3D).albedo_texture)
				sm.set_shader_parameter("albedo_col", (src as BaseMaterial3D).albedo_color)
			m.set_surface_override_material(e[1], sm)
			reveal_mats.append(sm)
		else:
			var keep: Material = e[2]
			m.set_surface_override_material(e[1], keep if keep and keep.resource_name == "team_tint" else null)
	if not on: reveal_mats.clear()


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
	card_mat.set_shader_parameter("team_color", UnitDefs.team_color(team))
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
	m.albedo_color = UnitDefs.team_color(team).lightened(0.25)
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
	if model3d:
		_update_lights(_dt)
		if radar_dish and built and not dead and battle.power_ok(team): radar_dish.rotate_y(_dt * 0.9)
		if b_turret and target and is_instance_valid(target) and not target.dead:
			var to: Vector3 = target.global_position - b_turret.global_position
			if turret_off == INF and b_muzzle:
				var ml: Vector3 = b_turret.to_local(b_muzzle.global_position)
				turret_off = atan2(ml.x, ml.z)
			var want := atan2(to.x, to.z) - (turret_off if turret_off != INF else 0.0)
			var cur := b_turret.global_rotation.y
			b_turret.global_rotation.y = lerp_angle(cur, want, minf(1.0, _dt * 5.0))
		if revealing:
			if built: _set_reveal(false)
			else:
				for sm in reveal_mats: (sm as ShaderMaterial).set_shader_parameter("build_y", global_position.y + model_h * progress)
		return
	if card == null: return
	# keep the card on the footprint edge that faces the camera
	var cam := get_viewport().get_camera_3d()
	if cam:
		var to_cam := cam.global_position - global_position
		to_cam.y = 0.0
		if to_cam.length() > 0.01:
			to_cam = to_cam.normalized()
			var reach := reach_along(to_cam)
			card.global_position = global_position + to_cam * reach * 0.9 + Vector3(0, 0.2, 0)
	card_mat.set_shader_parameter("progress", progress)
	card_mat.set_shader_parameter("highlight", 1.0 if selected else 0.0)


func _make_ring() -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = Vector3(half.x * 2.0 + 2.0, 0.1, half.y * 2.0 + 2.0)
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
	if b_muzzle: return b_muzzle.global_position
	return global_position + Vector3.UP * 9.0


func footprint_dist(p: Vector3) -> float:
	var l := local_xz(p)
	return Vector2(maxf(0.0, absf(l.x) - half.x), maxf(0.0, absf(l.y) - half.y)).length()


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
	if bdef.get("repair", false): _service_vehicles(dt, powered)
	# supply drop zone: periodic C-130 airdrop (paused while under-powered)
	if bdef.has("drop") and powered:
		drop_t -= dt
		if drop_t <= 0.0:
			drop_t = float(bdef.drop.every)
			battle.launch_supply_drop(self)
	# research (one at a time per structure; half speed under low power)
	if research_id != "":
		research_left -= dt * (1.0 if powered else BuildingDefs.LOW_POWER_RATE)
		if research_left <= 0.0:
			var id := research_id
			research_id = ""; research_left = 0.0
			battle.complete_upgrade(team, id)
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
		battle.spend(team, whole)
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
	if is_civic() and not passengers.is_empty() and from and is_instance_valid(from) and not from.dead and from.team >= 0 and from.team != team:
		retaliate = from; retaliate_t = battle.sim_time     # occupants return fire (battle._update_garrisons)
	hp -= amount
	if hp <= 0.0:
		hp = 0.0
		die()


func die() -> void:
	dead = true
	set_selected(false)
	if card_mat: card_mat.set_shader_parameter("burnt", 1.0)
	if build_snd: build_snd.queue_free(); build_snd = null
	nav_block(false)
	outline.visible = false
	set_flag_team(-1)
	repairing = false
	battle.on_unit_died(self)
	if not sold and built:
		battle.add_rubble(self)
		if card: card.visible = false
		if model3d: model3d.visible = false
	visible = false if sold else visible


# ---- occupation flag (civic buildings): a short pole on the roof flying the occupier's national flag, with a pennant
# in the occupier's team colour under it. Presentation only; battle._update_civic_flags decides which side is shown.
const FLAG_SCALE := 0.62
var _roof_local := Vector3.INF


func set_flag_team(t: int) -> void:
	if t == flag_team: return
	flag_team = t
	if flag_node and is_instance_valid(flag_node): flag_node.queue_free()
	flag_node = null
	if t < 0 or dead: return
	var root := Node3D.new()
	root.name = "OccupationFlag"
	root.position = roof_point()
	add_child(root)
	var path := str(Nations.DEFS.get(battle.nation_of(t), {}).get("flag", ""))
	if path != "" and ResourceLoader.exists(path):
		var f: Node3D = (load(path) as PackedScene).instantiate()
		f.scale = Vector3.ONE * FLAG_SCALE
		f.name = "NationFlag"
		root.add_child(f)
		battle.play_loop(f, "wave")
	else:   # no flag model for this nation: a plain pole (the pennant still shows the side)
		var pole := MeshInstance3D.new()
		var cm := CylinderMesh.new(); cm.top_radius = 0.04; cm.bottom_radius = 0.05; cm.height = 5.0
		pole.mesh = cm; pole.position.y = 2.5
		root.add_child(pole)
	var col: Color = UnitDefs.team_color(t)
	var im := ImmediateMesh.new()
	var m := StandardMaterial3D.new()
	m.albedo_color = col; m.emission_enabled = true; m.emission = col; m.emission_energy_multiplier = 0.35
	m.cull_mode = BaseMaterial3D.CULL_DISABLED; m.roughness = 0.8
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLES, m)
	for v in [Vector3(0.05, 3.85, 0), Vector3(0.05, 3.0, 0), Vector3(1.75, 3.42, 0)]:
		im.surface_set_normal(Vector3(0, 0, 1)); im.surface_add_vertex(v)
	im.surface_end()
	var pen := MeshInstance3D.new()
	pen.mesh = im; pen.name = "TeamPennant"
	root.add_child(pen)
	root.set_meta("team_color", col)
	flag_node = root


## Where the occupation flag stands (structure-local): the model's "FlagPole" empty when it has one, otherwise the
## highest model surface under a spot near a rear corner of the roof (measured once from the meshes).
func roof_point() -> Vector3:
	if _roof_local != Vector3.INF: return _roof_local
	var fp: Node3D = model3d.find_child("FlagPole", true, false) as Node3D if model3d else null
	if fp:
		_roof_local = to_local(fp.global_position)
		return _roof_local
	_roof_local = Vector3(-half.x * 0.55, model_h, -half.y * 0.5)
	for cand in [Vector2(-0.55, -0.5), Vector2(0.55, -0.5), Vector2(-0.5, 0.35), Vector2(0.0, 0.0)]:
		var lp := Vector3(cand.x * half.x, 0, cand.y * half.y)
		var h := _model_top_at(lp)
		if h > 0.5:
			_roof_local = Vector3(lp.x, h, lp.z)
			break
	return _roof_local


func _model_top_at(lp: Vector3) -> float:
	if model3d == null: return -1.0
	var inv := global_transform.affine_inverse()
	var top := -1.0
	var from := Vector3(lp.x, 200.0, lp.z)
	for mi in model3d.find_children("*", "MeshInstance3D", true, false):
		var m := mi as MeshInstance3D
		if String(m.name).begins_with("Light_") or m.mesh == null: continue
		var xf: Transform3D = inv * m.global_transform
		var f := m.mesh.get_faces()
		for i in range(0, f.size(), 3):
			var a: Vector3 = xf * f[i]; var b: Vector3 = xf * f[i + 1]; var c: Vector3 = xf * f[i + 2]
			if lp.x < minf(a.x, minf(b.x, c.x)) or lp.x > maxf(a.x, maxf(b.x, c.x)): continue
			if lp.z < minf(a.z, minf(b.z, c.z)) or lp.z > maxf(a.z, maxf(b.z, c.z)): continue
			var hit: Variant = Geometry3D.ray_intersects_triangle(from, Vector3.DOWN, a, b, c)
			if hit != null: top = maxf(top, (hit as Vector3).y)
	return top

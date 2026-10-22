# Steel Accord - local player command input (mouse-first, C&C-style).
#
# CLASSIC scheme (default):
#   Left click unit ............ select (Shift: add/remove, double-click: all of that type on screen)
#   Left drag .................. box select
#   Left click ground / enemy .. with units selected: move / attack (Ctrl: force-fire, Alt: add waypoint)
#   Right click ................ deselect / cancel the active command mode
#   Right drag ................. scroll the map
# ALTERNATE scheme: left click / drag only selects; right click commands; right drag still scrolls.
# Command modes (set by command-card buttons or hotkeys) consume the next left click:
#   attack-move (A), guard (G), force-fire (F), waypoint (W), support power (button only).
# Other: S stop, X scatter, R return-to-base (jets), Ctrl+A select all, Ctrl+1..9 / 1..9 groups, Esc cancel.
class_name Commander
extends Node

signal selection_changed

var battle: Node
var camera: RTSCamera
var team := 0
var scheme := "classic"
var selected: Array[Unit] = []
var groups := {}
var mode := ""                  # "", attack_move, guard, force, waypoint, power:<id>, place:<structure>
var sel_building: Building = null   # a single selected own structure (production / rally / sell)
var ghost: Node3D = null            # placement preview
var ghost_mat: ShaderMaterial
var ghost_ok := false
var ghost_reason := ""
var ghost_pos := Vector3.ZERO
var dragging := false
var drag_from := Vector2.ZERO
var drag_to := Vector2.ZERO
var rdown := false
var rdrag := false
var rfrom := Vector2.ZERO
var hover: Unit = null
var _last_click_t := -1.0
var _last_group := -1
var _last_group_t := -1.0

# kept for tests / HUD compatibility
var attack_mode: bool:
	get: return mode == "attack_move"


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		var mb := e as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				dragging = true; drag_from = mb.position; drag_to = mb.position
			elif dragging:
				dragging = false
				drag_to = mb.position
				_left_release(mb)
		elif mb.button_index == MOUSE_BUTTON_RIGHT:
			if mb.pressed:
				rdown = true; rdrag = false; rfrom = mb.position
			elif rdown:
				rdown = false
				if not rdrag: _right_click(mb)
				rdrag = false
	elif e is InputEventMouseMotion:
		var mm := e as InputEventMouseMotion
		if dragging: drag_to = mm.position
		if rdown:
			if rdrag or mm.position.distance_to(rfrom) > 8.0:
				rdrag = true
				camera.drag_pan(mm.relative)
		hover = unit_at(mm.position)
		_update_cursor()
	elif e is InputEventKey and e.pressed and not e.echo:
		_key(e as InputEventKey)


func _key(k: InputEventKey) -> void:
	var has_sel := not live_selection().is_empty()
	match k.keycode:
		KEY_A:
			if k.ctrl_pressed: select_all()
			elif has_sel: set_mode("attack_move")
		KEY_G:
			if has_sel: set_mode("guard")
		KEY_F:
			if has_sel: set_mode("force")
		KEY_W:
			if has_sel: set_mode("waypoint")
		KEY_S:
			if has_sel: cmd_stop()
		KEY_X:
			if has_sel: cmd_scatter()
		KEY_R:
			if has_sel: cmd_return()
		KEY_ESCAPE:
			if mode != "": set_mode("")
			elif not live_selection().is_empty(): _set_selection([])
			else: battle.open_menu()
		KEY_F10:
			battle.open_menu()
		_:
			if k.keycode >= KEY_1 and k.keycode <= KEY_9:
				var g := int(k.keycode - KEY_0)
				if k.ctrl_pressed: groups[g] = selected.duplicate()
				else: _recall(g)


func set_mode(m: String) -> void:
	mode = m
	if ghost:
		ghost.queue_free(); ghost = null
	if m.begins_with("place:"):
		_make_ghost(m.substr(6))
	_update_cursor()


func dozers() -> Array:
	return live_selection().filter(func(u): return u.def.get("builder", false))


## Placement preview: the structure's own art in a dithered green / red card plus its footprint.
func _make_ghost(k: String) -> void:
	var d: Dictionary = BuildingDefs.DEFS[k]
	ghost = Node3D.new()
	battle.add_child(ghost)
	var b := BoxMesh.new()
	b.size = Vector3(d.size.x, 0.2, d.size.y)
	var fm := StandardMaterial3D.new()
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	fm.albedo_color = Color(0.3, 1.0, 0.4, 0.35)
	fm.no_depth_test = true          # the footprint stays visible over structures it overlaps (shows why it is blocked)
	fm.render_priority = 10
	b.material = fm
	var foot := MeshInstance3D.new()
	foot.mesh = b; foot.name = "Foot"; foot.position.y = 0.15
	ghost.add_child(foot)
	var art := UsArt.building(d.art)
	if not art.is_empty():
		var tex: Texture2D = load(art.main)
		var q := QuadMesh.new()
		var px: float = d.size.x / float(art.base_width_px)
		var w := float(tex.get_width()); var h := float(tex.get_height())
		var pivot := Vector2(float(art.anchor_px[0]), float(art.anchor_px[1]) + d.size.y * 0.5 / px * 0.62)
		q.size = Vector2(w, h) * px
		q.center_offset = Vector3((w * 0.5 - pivot.x) * px, (pivot.y - h * 0.5) * px, 0.0)
		ghost_mat = ShaderMaterial.new()
		ghost_mat.shader = Building.STRUCTURE_SHADER
		ghost_mat.set_shader_parameter("art", tex)
		ghost_mat.set_shader_parameter("ghost", 1.0)
		q.material = ghost_mat
		var c := MeshInstance3D.new()
		c.mesh = q; c.name = "Card"
		c.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		ghost.add_child(c)
	ghost.set_meta("kind", k)


var mouse_override := Vector2(-1, -1)   # automated tests position the virtual cursor here


func _process(_dt: float) -> void:
	if ghost == null: return
	var mp := mouse_override if mouse_override.x >= 0.0 else get_viewport().get_mouse_position()
	var g: Variant = camera.ground_at(mp)
	if g == null: return
	var k: String = ghost.get_meta("kind")
	ghost_pos = Vector3(snappedf(g.x, 2.0), 0, snappedf(g.z, 2.0))
	ghost.position = ghost_pos
	var c := ghost.get_node_or_null("Card") as Node3D
	if c:
		var to_cam: Vector3 = camera.cam.global_position - ghost_pos
		to_cam.y = 0.0
		to_cam = to_cam.normalized()
		var hs: Vector2 = BuildingDefs.DEFS[k].size * 0.5
		c.position = to_cam * (absf(to_cam.x) * hs.x + absf(to_cam.z) * hs.y) * 0.9
	ghost_reason = battle.placement_problem(team, k, ghost_pos)
	if dozers().is_empty(): ghost_reason = "Select a Dozer"
	ghost_ok = ghost_reason == ""
	var col := Color(0.4, 1.0, 0.5) if ghost_ok else Color(1.0, 0.35, 0.3)
	if ghost_mat: ghost_mat.set_shader_parameter("ghost_color", col)
	var fm := ((ghost.get_node("Foot") as MeshInstance3D).mesh as BoxMesh).material as StandardMaterial3D
	fm.albedo_color = Color(col.r, col.g, col.b, 0.35)


func live_selection() -> Array:
	return selected.filter(func(u): return is_instance_valid(u) and not u.dead)


func _ids() -> Array:
	var a := []
	for u in live_selection(): a.append(u.uid)
	return a


func _is_double() -> bool:
	var t := Time.get_ticks_msec() / 1000.0
	var d := t - _last_click_t < 0.35
	_last_click_t = t
	return d


func _update_cursor() -> void:
	var shape := Input.CURSOR_ARROW
	if mode.begins_with("place:"):
		shape = Input.CURSOR_ARROW
	elif mode != "" or (hover and hover.team != team and not selected.is_empty()):
		shape = Input.CURSOR_CROSS
	elif hover and hover.team == team:
		shape = Input.CURSOR_POINTING_HAND
	elif rdrag:
		shape = Input.CURSOR_MOVE
	Input.set_default_cursor_shape(shape)


## Unit nearest the cursor within its on-screen footprint.
func unit_at(screen: Vector2) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(team, u): continue
		var c := u.world_center()
		if camera.cam.is_position_behind(c): continue
		var sp := camera.cam.unproject_position(c)
		var edge := camera.cam.unproject_position(c + camera.cam.global_basis.x * u.def.radius * 1.2)
		var r := maxf(14.0, sp.distance_to(edge))
		var d := sp.distance_to(screen)
		if u is Building: continue
		if d < r and d < best_d:
			best = u; best_d = d
	if best: return best
	return building_at(screen)


## Structures are picked by the ground point under the cursor: inside the footprint, or in the strip behind it
## (away from the camera) that the standing art covers on screen.
func building_at(screen: Vector2) -> Building:
	var g: Variant = camera.ground_at(screen)
	if g == null: return null
	var away := -camera.cam.global_basis.z
	away.y = 0.0; away = away.normalized()
	for u in battle.units:
		if not (u is Building) or u.dead or not battle.is_visible_to(team, u): continue
		var b: Building = u
		for k in 4:
			var q: Vector3 = g - away * (float(k) * maxf(b.half.x, b.half.y) * 0.45)
			if absf(q.x - b.position.x) < b.half.x + 1.0 and absf(q.z - b.position.z) < b.half.y + 1.0:
				return b
	return null


# ------------------------------------------------------------------ mouse
func _left_release(mb: InputEventMouseButton) -> void:
	var p := mb.position
	var is_click := drag_from.distance_to(drag_to) < 6.0
	if mode != "":
		if is_click: _apply_mode(p, mb)
		return
	if not is_click:
		_box_select(Rect2(drag_from, Vector2.ZERO).expand(drag_to), mb.shift_pressed)
		return
	var u := unit_at(p)
	var own := u != null and u.team == team
	# dozer + own unfinished structure: (re)start construction
	if own and u is Building and not u.built and not dozers().is_empty():
		battle.issue({"type": "build", "team": team, "ids": dozers().map(func(d): return d.uid), "site": u.uid})
		FX.order_marker(battle, u.position, Color(1, 0.8, 0.3, 0.9))
		return
	# dozer + click on own rubble: rebuild the same structure there (normal cost, prerequisites and build time)
	if u == null and not dozers().is_empty() and scheme == "classic":
		var gr: Variant = camera.ground_at(p)
		if gr != null:
			var rb: Dictionary = battle.rubble_at(gr, team)
			if not rb.is_empty():
				var why: String = battle.placement_problem(team, rb.kind, rb.pos)
				if why == "":
					battle.issue({"type": "place", "team": team, "id": rb.kind, "pos": rb.pos, "builder": dozers()[0].uid})
					FX.order_marker(battle, rb.pos, Color(1, 0.8, 0.3, 0.9))
				elif battle.hud:
					battle.hud.flash_message("Cannot rebuild %s: %s" % [BuildingDefs.DEFS[rb.kind].name, why])
				return
	# selected structure: click ground (classic) sets its rally point
	if scheme == "classic" and sel_building and live_selection().is_empty() and u == null:
		_set_rally(p)
		return
	if scheme == "classic" and not live_selection().is_empty() and not own and not mb.shift_pressed:
		_command_at(p, mb.ctrl_pressed, mb.alt_pressed)
		return
	if scheme == "classic" and not live_selection().is_empty() and own and mb.ctrl_pressed:
		_command_at(p, true, false)   # Ctrl+click on own unit = force-fire (attack friendly)
		return
	_click_select(p, mb.shift_pressed, mb.double_click or _is_double())


func _set_rally(p: Vector2) -> void:
	var g: Variant = camera.ground_at(p)
	if g == null or sel_building == null or sel_building.bdef.produces.is_empty(): return
	battle.issue({"type": "rally", "team": team, "id": sel_building.uid, "pos": g})
	FX.order_marker(battle, g, Color(0.5, 0.8, 1.0, 0.9))


func _right_click(mb: InputEventMouseButton) -> void:
	if mode != "":
		set_mode(""); return
	if scheme == "alternate" and sel_building and live_selection().is_empty():
		_set_rally(mb.position); return
	if scheme == "classic":
		_set_selection([])
	else:
		_command_at(mb.position, mb.ctrl_pressed, mb.alt_pressed)


func _apply_mode(p: Vector2, mb: InputEventMouseButton) -> void:
	var g: Variant = camera.ground_at(p)
	var u := unit_at(p)
	var m := mode
	if not mb.shift_pressed: set_mode("")   # Shift keeps the mode active for repeated orders
	if m.begins_with("place:"):
		var dz := dozers()
		if ghost_ok and not dz.is_empty():
			battle.issue({"type": "place", "team": team, "id": m.substr(6), "pos": ghost_pos, "builder": dz[0].uid})
			FX.order_marker(battle, ghost_pos, Color(1, 0.8, 0.3, 0.9))
		else:
			if battle.hud: battle.hud.flash_message("Cannot build here: " + ghost_reason)
			set_mode(m)   # keep placing
		return
	if m.begins_with("power:"):
		if g != null:
			battle.issue({"type": "power", "team": team, "id": m.substr(6), "pos": g})
			FX.order_marker(battle, g, Color(1, 0.8, 0.2, 0.9))
		return
	if live_selection().is_empty() or g == null: return
	match m:
		"attack_move":
			battle.issue({"type": "attack_move", "ids": _ids(), "points": formation(g)})
			FX.order_marker(battle, g, Color(1, 0.55, 0.2, 0.9))
		"guard":
			var gu := u.uid if (u and u.team == team) else -1
			var gp: Vector3 = u.position if gu != -1 else g
			battle.issue({"type": "guard", "ids": _ids(), "points": formation(gp, 5.0), "unit": gu})
			FX.order_marker(battle, gp, Color(0.4, 0.7, 1.0, 0.9))
		"force":
			_command_at(p, true, false)
		"waypoint":
			battle.issue({"type": "move", "ids": _ids(), "points": formation(g), "append": true})
			FX.order_marker(battle, g, Color(0.6, 1, 0.8, 0.9))
			set_mode("waypoint")   # waypoint mode stays on until right click / Esc


func _command_at(p: Vector2, force := false, waypoint := false) -> void:
	if live_selection().is_empty(): return
	var u := unit_at(p)
	if u and (u.team != team or force):
		battle.issue({"type": "attack", "ids": _ids(), "target": u.uid})
		FX.order_marker(battle, u.global_position, Color(1, 0.25, 0.2, 0.9))
		return
	var g: Variant = camera.ground_at(p)
	if g == null: return
	if force:
		battle.issue({"type": "force_ground", "ids": _ids(), "pos": g})
		FX.order_marker(battle, g, Color(1, 0.2, 0.1, 0.9))
		return
	battle.issue({"type": "move", "ids": _ids(), "points": formation(g), "append": waypoint})
	FX.order_marker(battle, g, Color(0.4, 1, 0.5, 0.9))


# ------------------------------------------------------------------ selection
func _set_selection(arr: Array) -> void:
	for u in selected:
		if is_instance_valid(u): u.set_selected(false)
	selected.clear()
	if sel_building and is_instance_valid(sel_building): sel_building.set_selected(false)
	sel_building = null
	var only_b: Array = arr.filter(func(x): return x is Building)
	if not only_b.is_empty() and only_b.size() == arr.size():
		sel_building = only_b[0]
		sel_building.set_selected(true)
		if mode != "" and not mode.begins_with("power:"): set_mode("")
		selection_changed.emit()
		return
	for u in arr:
		if u is Building: continue
		if not u.dead:
			selected.append(u); u.set_selected(true)
	if mode != "" and not mode.begins_with("power:"): set_mode("")
	selection_changed.emit()


func select_all() -> void:
	_set_selection(battle.units.filter(func(u): return u.team == team and not u.dead and not (u is Building)))


func _click_select(p: Vector2, add: bool, dbl: bool) -> void:
	var u := unit_at(p)
	if u == null or u.team != team:
		if not add: _set_selection([])
		return
	if u is Building:
		_set_selection([u])
		return
	if dbl:
		var same: Array = []
		var vp := camera.get_viewport().get_visible_rect()
		for o: Unit in battle.units:
			if o.team == team and not o.dead and o.kind == u.kind and vp.has_point(camera.cam.unproject_position(o.global_position)):
				same.append(o)
		_set_selection(same)
		return
	var arr: Array = selected.duplicate() if add else []
	if add and u in arr: arr.erase(u)
	else: arr.append(u)
	_set_selection(arr)


func _box_select(r: Rect2, add: bool) -> void:
	var arr: Array = selected.duplicate() if add else []
	for u: Unit in battle.units:
		if u.team != team or u.dead or u in arr or u is Building: continue
		var c := u.world_center()
		if camera.cam.is_position_behind(c): continue
		if r.grow(6.0).has_point(camera.cam.unproject_position(c)):
			arr.append(u)
	_set_selection(arr)


func _recall(g: int) -> void:
	var arr: Array = groups.get(g, [])
	arr = arr.filter(func(u): return is_instance_valid(u) and not u.dead)
	if arr.is_empty(): return
	var t := Time.get_ticks_msec() / 1000.0
	if _last_group == g and t - _last_group_t < 0.45:
		var c := Vector3.ZERO
		for u in arr: c += u.global_position
		camera.focus(c / arr.size())
	_last_group = g; _last_group_t = t
	_set_selection(arr)


# ------------------------------------------------------------------ immediate commands (keys and command card)
func cmd_stop() -> void:
	battle.issue({"type": "stop", "ids": _ids()})


func cmd_scatter() -> void:
	var c := Vector3.ZERO
	var live := live_selection()
	for u in live: c += u.position
	battle.issue({"type": "scatter", "ids": _ids(), "center": c / maxi(1, live.size())})


func cmd_return() -> void:
	battle.issue({"type": "return", "ids": _ids()})


## Grid formation centred on `dest`, facing the direction of travel; slots matched left-to-right.
func formation(dest: Vector3, spacing := 7.5) -> Array:
	var live: Array = live_selection()
	var n := live.size()
	if n == 0: return []
	var c := Vector3.ZERO
	for u in live: c += u.global_position
	c /= n
	var fwd := Vector3(dest.x - c.x, 0, dest.z - c.z)
	fwd = fwd.normalized() if fwd.length() > 0.5 else Vector3(0, 0, -1)
	var right := Vector3(-fwd.z, 0, fwd.x)
	var cols := int(ceil(sqrt(n)))
	var rows := int(ceil(float(n) / cols))
	var slots: Array = []
	for i in n:
		var col := i % cols
		var row := i / cols
		slots.append(dest + right * (col - (cols - 1) / 2.0) * spacing - fwd * (row - (rows - 1) / 2.0) * spacing)
	var order := range(n)
	order.sort_custom(func(a, b): return live[a].global_position.dot(right) < live[b].global_position.dot(right))
	slots.sort_custom(func(a, b): return a.dot(right) < b.dot(right))
	var pts: Array = []
	pts.resize(n)
	for i in n:
		pts[order[i]] = slots[i]
	return pts

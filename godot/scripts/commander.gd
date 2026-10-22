# Steel Accord - local player command input.
# Left click / drag: select (Shift adds, double-click selects same type on screen).
# Right click: move, or attack when over an enemy. A then left click: attack-move. S: stop.
# Ctrl+1..9: assign group; 1..9: recall (press twice to centre the camera). Esc: cancel / deselect.
class_name Commander
extends Node

signal selection_changed

var battle: Node
var camera: RTSCamera
var team := 0
var selected: Array[Unit] = []
var groups := {}
var attack_mode := false
var dragging := false
var drag_from := Vector2.ZERO
var drag_to := Vector2.ZERO
var hover: Unit = null
var _last_click_t := -1.0
var _last_group := -1
var _last_group_t := -1.0


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		var mb := e as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				dragging = true; drag_from = mb.position; drag_to = mb.position
			elif dragging:
				dragging = false
				drag_to = mb.position
				if attack_mode:
					_attack_move_at(mb.position)
					attack_mode = false
				elif drag_from.distance_to(drag_to) < 6.0:
					_click_select(mb.position, mb.shift_pressed, mb.double_click or _is_double())
				else:
					_box_select(Rect2(drag_from, Vector2.ZERO).expand(drag_to), mb.shift_pressed)
		elif mb.button_index == MOUSE_BUTTON_RIGHT and mb.pressed:
			if attack_mode:
				attack_mode = false
			else:
				_command_at(mb.position)
	elif e is InputEventMouseMotion:
		var mm := e as InputEventMouseMotion
		if dragging: drag_to = mm.position
		hover = unit_at(mm.position)
		_update_cursor()
	elif e is InputEventKey and e.pressed and not e.echo:
		var k := e as InputEventKey
		if k.keycode == KEY_A and not selected.is_empty():
			attack_mode = true; _update_cursor()
		elif k.keycode == KEY_S and not selected.is_empty():
			battle.issue({"type": "stop", "ids": _ids()})
		elif k.keycode == KEY_ESCAPE:
			if attack_mode: attack_mode = false
			else: _set_selection([])
			_update_cursor()
		elif k.keycode >= KEY_1 and k.keycode <= KEY_9:
			var g := int(k.keycode - KEY_0)
			if k.ctrl_pressed:
				groups[g] = selected.duplicate()
			else:
				_recall(g)


func _is_double() -> bool:
	var t := Time.get_ticks_msec() / 1000.0
	var d := t - _last_click_t < 0.35
	_last_click_t = t
	return d


func _ids() -> Array:
	var a := []
	for u in selected:
		if not u.dead: a.append(u.uid)
	return a


func _update_cursor() -> void:
	var shape := Input.CURSOR_ARROW
	if attack_mode or (hover and hover.team != team and not selected.is_empty()):
		shape = Input.CURSOR_CROSS
	elif hover and hover.team == team:
		shape = Input.CURSOR_POINTING_HAND
	Input.set_default_cursor_shape(shape)


## Unit nearest the cursor within its on-screen footprint.
func unit_at(screen: Vector2) -> Unit:
	var best: Unit = null
	var best_d := INF
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(team, u): continue
		var c := u.global_position + Vector3.UP * 1.4
		if camera.cam.is_position_behind(c): continue
		var sp := camera.cam.unproject_position(c)
		var edge := camera.cam.unproject_position(c + camera.cam.global_basis.x * u.def.radius * 1.2)
		var r := maxf(14.0, sp.distance_to(edge))
		var d := sp.distance_to(screen)
		if d < r and d < best_d:
			best = u; best_d = d
	return best


func _set_selection(arr: Array) -> void:
	for u in selected:
		if is_instance_valid(u): u.set_selected(false)
	selected.clear()
	for u in arr:
		if not u.dead:
			selected.append(u); u.set_selected(true)
	selection_changed.emit()


func _click_select(p: Vector2, add: bool, dbl: bool) -> void:
	var u := unit_at(p)
	if u == null or u.team != team:
		if not add: _set_selection([])
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
		if u.team != team or u.dead or u in arr: continue
		var c := u.global_position + Vector3.UP * 1.2
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


func _command_at(p: Vector2) -> void:
	if selected.is_empty(): return
	var u := unit_at(p)
	if u and u.team != team:
		battle.issue({"type": "attack", "ids": _ids(), "target": u.uid})
		FX.order_marker(battle, u.global_position, Color(1, 0.25, 0.2, 0.9))
		return
	var g: Variant = camera.ground_at(p)
	if g == null: return
	battle.issue({"type": "move", "ids": _ids(), "points": formation(g)})
	FX.order_marker(battle, g, Color(0.4, 1, 0.5, 0.9))


func _attack_move_at(p: Vector2) -> void:
	if selected.is_empty(): return
	var g: Variant = camera.ground_at(p)
	if g == null: return
	battle.issue({"type": "attack_move", "ids": _ids(), "points": formation(g)})
	FX.order_marker(battle, g, Color(1, 0.55, 0.2, 0.9))


## Grid formation centred on `dest`, facing the direction of travel; slots matched left-to-right.
func formation(dest: Vector3) -> Array:
	var live: Array = selected.filter(func(u): return not u.dead)
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
	var sp := 7.5
	var slots: Array = []
	for i in n:
		var col := i % cols
		var row := i / cols
		slots.append(dest + right * (col - (cols - 1) / 2.0) * sp - fwd * (row - (rows - 1) / 2.0) * sp)
	var order := range(n)
	order.sort_custom(func(a, b): return live[a].global_position.dot(right) < live[b].global_position.dot(right))
	slots.sort_custom(func(a, b): return a.dot(right) < b.dot(right))
	var pts: Array = []
	pts.resize(n)
	for i in n:
		pts[order[i]] = slots[i]
	return pts

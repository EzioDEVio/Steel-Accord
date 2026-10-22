# Steel Accord - in-game HUD: selection box, health bars, minimap, selection panel, status and help.
class_name HUD
extends Control

const PANEL := Color(0.05, 0.07, 0.08, 0.82)
const EDGE := Color(0.55, 0.68, 0.62, 0.9)
const ACCENT := Color(0.42, 0.95, 0.6)
const MINIMAP := Rect2(14, 0, 210, 210)   # y set in _ready (anchored bottom-left)

var battle: Node
var commander: Commander
var camera: RTSCamera
var show_help := true
var banner := ""
var banner_color := Color.WHITE
var msg := ""
var msg_t := 0.0
var font: Font
var mini_rect := MINIMAP


var mini_ctl: Control


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE   # world clicks go to Commander via _unhandled_input
	font = ThemeDB.fallback_font
	mini_ctl = Control.new()
	mini_ctl.mouse_filter = Control.MOUSE_FILTER_STOP
	mini_ctl.gui_input.connect(_mini_input)
	add_child(mini_ctl)


func flash_message(t: String) -> void:
	msg = t; msg_t = 4.0


func _process(dt: float) -> void:
	size = get_viewport_rect().size   # CanvasLayer children don't inherit a parent rect; track the window
	position = Vector2.ZERO
	msg_t = maxf(0.0, msg_t - dt)
	mini_rect = Rect2(14, size.y - 224, 210, 210)
	mini_ctl.position = mini_rect.position; mini_ctl.size = mini_rect.size
	queue_redraw()


func _mini_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		var p := _mini_to_world(e.position + mini_rect.position)
		if (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
			camera.focus(p)
		elif (e as InputEventMouseButton).button_index == MOUSE_BUTTON_RIGHT and not commander.selected.is_empty():
			battle.issue({"type": "move", "ids": commander._ids(), "points": commander.formation(p)})
		mini_ctl.accept_event()


func _unhandled_key_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and (e as InputEventKey).keycode == KEY_F1:
		show_help = not show_help


func _mini_to_world(p: Vector2) -> Vector3:
	var b: Rect2 = battle.map_bounds
	var t := (p - mini_rect.position) / mini_rect.size
	return Vector3(b.position.x + t.x * b.size.x, 0, b.position.y + t.y * b.size.y)


func _world_to_mini(w: Vector3) -> Vector2:
	var b: Rect2 = battle.map_bounds
	return mini_rect.position + Vector2((w.x - b.position.x) / b.size.x, (w.z - b.position.y) / b.size.y) * mini_rect.size


func _panel(r: Rect2) -> void:
	draw_rect(r, PANEL)
	draw_rect(r, EDGE, false, 1.0)
	draw_line(r.position + Vector2(0, 2), r.position + Vector2(18, 2), ACCENT, 2.0)


func _text(p: Vector2, t: String, sz := 14, col := Color(0.88, 0.92, 0.9)) -> void:
	draw_string(font, p, t, HORIZONTAL_ALIGNMENT_LEFT, -1, sz, col)


func _draw() -> void:
	if battle == null: return
	var cam := camera.cam
	# health bars (selected, damaged or hovered)
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(commander.team, u): continue
		if not (u.selected or u.hp < u.def.hp or u == commander.hover): continue
		var top: Vector3 = u.global_position + Vector3.UP * (u.def.height + 1.2)
		if cam.is_position_behind(top): continue
		var sp := cam.unproject_position(top)
		var w := 46.0
		var r := Rect2(sp - Vector2(w / 2, 0), Vector2(w, 5))
		var f: float = u.hp / u.def.hp
		draw_rect(r.grow(1), Color(0, 0, 0, 0.75))
		var col := Color(0.3, 0.9, 0.4) if f > 0.6 else (Color(0.95, 0.8, 0.2) if f > 0.3 else Color(0.95, 0.25, 0.2))
		draw_rect(Rect2(r.position, Vector2(w * f, 5)), col)
		draw_rect(Rect2(r.position - Vector2(0, 4), Vector2(w, 2)), UnitDefs.TEAM_COLORS[u.team].lightened(0.25))
	# drag box
	if commander.dragging and commander.drag_from.distance_to(commander.drag_to) > 6.0 and not commander.attack_mode:
		var r := Rect2(commander.drag_from, Vector2.ZERO).expand(commander.drag_to)
		draw_rect(r, Color(0.4, 1.0, 0.55, 0.12))
		draw_rect(r, Color(0.4, 1.0, 0.55, 0.9), false, 1.5)
	_draw_minimap()
	_draw_selection_panel()
	_draw_status()
	if show_help: _draw_help()
	if commander.attack_mode:
		_text(get_local_mouse_position() + Vector2(18, 26), "ATTACK-MOVE", 13, Color(1, 0.6, 0.3))
	if banner != "":
		var s := font.get_string_size(banner, HORIZONTAL_ALIGNMENT_LEFT, -1, 64)
		var p := Vector2((size.x - s.x) / 2, size.y * 0.38)
		draw_rect(Rect2(0, p.y - 66, size.x, 96), Color(0, 0, 0, 0.55))
		draw_string(font, p, banner, HORIZONTAL_ALIGNMENT_LEFT, -1, 64, banner_color)


func _draw_minimap() -> void:
	_panel(mini_rect.grow(4))
	draw_rect(mini_rect, Color(0.17, 0.22, 0.11))
	for o in battle.obstacles_2d:
		draw_circle(_world_to_mini(Vector3(o.x, 0, o.y)), maxf(1.5, o.z / battle.map_bounds.size.x * mini_rect.size.x), Color(0.35, 0.33, 0.3))
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(commander.team, u): continue
		var p := _world_to_mini(u.global_position)
		draw_rect(Rect2(p - Vector2(2.5, 2.5), Vector2(5, 5)), UnitDefs.TEAM_COLORS[u.team].lightened(0.35 if u.selected else 0.1))
	# camera footprint
	var vs := camera.get_viewport().get_visible_rect().size
	var pts := PackedVector2Array()
	for c in [Vector2(0, 0), Vector2(vs.x, 0), Vector2(vs.x, vs.y), Vector2(0, vs.y), Vector2(0, 0)]:
		var g: Variant = camera.ground_at(c)
		if g == null: g = camera.position
		var mp := _world_to_mini(g)
		pts.append(Vector2(clampf(mp.x, mini_rect.position.x, mini_rect.end.x), clampf(mp.y, mini_rect.position.y, mini_rect.end.y)))
	draw_polyline(pts, Color(1, 1, 1, 0.8), 1.0)


func _draw_selection_panel() -> void:
	var r := Rect2(240, size.y - 96, 420, 82)
	_panel(r)
	var sel := commander.selected.filter(func(u): return not u.dead)
	if sel.is_empty():
		_text(r.position + Vector2(14, 30), "No units selected", 15, Color(0.6, 0.65, 0.62))
		_text(r.position + Vector2(14, 54), "Drag a box or click a unit to select", 12, Color(0.5, 0.55, 0.52))
		return
	var counts := {}
	var hp := 0.0
	var mx := 0.0
	for u in sel:
		counts[u.def.name] = counts.get(u.def.name, 0) + 1
		hp += u.hp; mx += u.def.hp
	var line := ""
	for k in counts: line += "%d x %s   " % [counts[k], k]
	_text(r.position + Vector2(14, 28), line, 16)
	_text(r.position + Vector2(14, 50), sel[0].def.role, 12, Color(0.65, 0.72, 0.68))
	var bar := Rect2(r.position + Vector2(14, 60), Vector2(390, 8))
	draw_rect(bar, Color(0, 0, 0, 0.6))
	draw_rect(Rect2(bar.position, Vector2(bar.size.x * hp / mx, 8)), Color(0.3, 0.9, 0.4))


func _draw_status() -> void:
	var r := Rect2(size.x / 2 - 170, 10, 340, 34)
	_panel(r)
	var a: int = battle.alive_count(0)
	var b: int = battle.alive_count(1)
	_text(r.position + Vector2(16, 23), "BLUE %d" % a, 16, UnitDefs.TEAM_COLORS[0].lightened(0.45))
	_text(r.position + Vector2(140, 23), "%02d:%02d" % [int(battle.sim_time) / 60, int(battle.sim_time) % 60], 16)
	_text(r.position + Vector2(250, 23), "RED %d" % b, 16, UnitDefs.TEAM_COLORS[1].lightened(0.45))
	if msg_t > 0.0:
		var s := font.get_string_size(msg, HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
		_text(Vector2((size.x - s.x) / 2, 70), msg, 16, Color(1, 0.85, 0.5, minf(1.0, msg_t)))


func _draw_help() -> void:
	var lines := [
		"STEEL ACCORD  -  G1 combat prototype",
		"Left drag / click: select   Shift: add   Double-click: same type",
		"Right click: move  /  attack enemy",
		"A + left click: attack-move     S: stop     Esc: cancel",
		"Ctrl+1..9: set group   1..9: select group (twice: jump)",
		"Arrows / screen edge / middle drag: pan   Wheel: zoom",
		", .: rotate   Home: reset view   F1: hide help",
	]
	var r := Rect2(size.x - 430, 10, 416, 22 + lines.size() * 18)
	_panel(r)
	for i in lines.size():
		_text(r.position + Vector2(12, 24 + i * 18), lines[i], 13 if i else 14, ACCENT if i == 0 else Color(0.82, 0.86, 0.84))

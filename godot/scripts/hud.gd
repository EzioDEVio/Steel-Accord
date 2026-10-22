# Steel Accord - in-game HUD: clickable command card, support-power buttons, mouse-scheme toggle, selection panel
# with portraits, minimap, health bars, waypoint lines, selection box, status and help.
class_name HUD
extends Control

const PANEL := Color(0.05, 0.07, 0.08, 0.86)
const EDGE := Color(0.55, 0.68, 0.62, 0.9)
const ACCENT := Color(0.42, 0.95, 0.6)

var battle: Node
var commander: Commander
var camera: RTSCamera
var show_help := false
var banner := ""
var banner_color := Color.WHITE
var msg := ""
var msg_t := 0.0
var font: Font
var mini_rect := Rect2()
var mini_ctl: Control
var card: Control
var card_buttons := {}
var power_box: Control
var power_buttons := {}
var scheme_btn: Button
var help_btn: Button
var menu_btn: Button
var portraits := {}


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE   # world clicks go to Commander via _unhandled_input
	font = ThemeDB.fallback_font
	mini_ctl = Control.new()
	mini_ctl.mouse_filter = Control.MOUSE_FILTER_STOP
	mini_ctl.gui_input.connect(_mini_input)
	add_child(mini_ctl)
	_build_card()
	_build_powers()
	scheme_btn = _button("Mouse: Classic", func(): _toggle_scheme(), Vector2(190, 30))
	add_child(scheme_btn)
	scheme_btn.tooltip_text = "Classic: left click selects AND commands, right click deselects, right drag scrolls.\nAlternate: left click selects, right click commands."
	help_btn = _button("Controls (F1)", func(): show_help = not show_help, Vector2(130, 30))
	add_child(help_btn)
	menu_btn = _button("Menu (F10)", func(): battle.open_menu(), Vector2(120, 30))
	add_child(menu_btn)


func _style(c: Color, border: Color) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = c; s.border_color = border
	s.set_border_width_all(1); s.set_corner_radius_all(3)
	s.content_margin_left = 6; s.content_margin_right = 6; s.content_margin_top = 3; s.content_margin_bottom = 3
	return s


func _button(text: String, cb: Callable, sz: Vector2) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = sz
	b.size = sz
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_stylebox_override("normal", _style(Color(0.10, 0.14, 0.15, 0.95), Color(0.35, 0.45, 0.42)))
	b.add_theme_stylebox_override("hover", _style(Color(0.16, 0.24, 0.22, 0.98), ACCENT))
	b.add_theme_stylebox_override("pressed", _style(Color(0.22, 0.34, 0.28, 1.0), ACCENT))
	b.add_theme_stylebox_override("disabled", _style(Color(0.08, 0.09, 0.1, 0.8), Color(0.2, 0.22, 0.22)))
	b.add_theme_color_override("font_color", Color(0.86, 0.92, 0.88))
	b.add_theme_color_override("font_disabled_color", Color(0.4, 0.43, 0.42))
	b.add_theme_font_size_override("font_size", 13)
	b.pressed.connect(cb)
	return b


func _build_card() -> void:
	card = Control.new()
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(card)
	var defs := [
		["attack_move", "Attack-Move  A", "Move and engage anything met on the way", func(): commander.set_mode("attack_move")],
		["guard", "Guard  G", "Guard an area or a friendly unit: engage intruders, then return", func(): commander.set_mode("guard")],
		["force", "Force Fire  F", "Fire at the ground or any unit (also Ctrl+click)", func(): commander.set_mode("force")],
		["waypoint", "Waypoints  W", "Click a chain of points; right click ends (also Alt+click)", func(): commander.set_mode("waypoint")],
		["stop", "Stop  S", "Stop and hold position", func(): commander.cmd_stop()],
		["scatter", "Scatter  X", "Spread out from each other", func(): commander.cmd_scatter()],
		["return", "Return to Pad  R", "Aircraft: fly back and land on their own pad (jets rearm there)", func(): commander.cmd_return()],
		["select_all", "Select All  Ctrl+A", "Select every unit you own", func(): commander.select_all()],
	]
	for i in defs.size():
		var d: Array = defs[i]
		var b := _button(d[1], d[3], Vector2(150, 30))
		b.tooltip_text = d[2]
		b.position = Vector2((i % 4) * 154, (i / 4) * 34)
		card.add_child(b)
		card_buttons[d[0]] = b


func _build_powers() -> void:
	power_box = Control.new()
	power_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(power_box)
	var i := 0
	for id in UnitDefs.POWERS:
		var p: Dictionary = UnitDefs.POWERS[id]
		var b := _button("", func(): commander.set_mode("power:" + id), Vector2(186, 62))
		b.tooltip_text = "%s - click the button, then click the target on the map.\nCooldown %d s (PROVISIONAL)" % [p.name, int(p.cooldown)]
		var icon := TextureRect.new()
		icon.texture = load(p.icon)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.position = Vector2(4, 6); icon.size = Vector2(72, 50)
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(icon)
		var l := Label.new()
		l.name = "L"
		l.position = Vector2(80, 4); l.size = Vector2(104, 56)
		l.add_theme_font_size_override("font_size", 11)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(l)
		b.position = Vector2(0, i * 66)
		power_box.add_child(b)
		power_buttons[id] = b
		i += 1


func _toggle_scheme() -> void:
	commander.scheme = "alternate" if commander.scheme == "classic" else "classic"
	scheme_btn.text = "Mouse: " + commander.scheme.capitalize()
	flash_message("Mouse scheme: %s" % ("left click commands, right click deselects" if commander.scheme == "classic" else "right click commands"))


func flash_message(t: String) -> void:
	msg = t; msg_t = 4.0


func _process(dt: float) -> void:
	size = get_viewport_rect().size
	position = Vector2.ZERO
	msg_t = maxf(0.0, msg_t - dt)
	mini_rect = Rect2(14, size.y - 224, 210, 210)
	mini_ctl.position = mini_rect.position; mini_ctl.size = mini_rect.size
	card.position = Vector2(maxf(632.0, size.x - 4 * 154 - 200), size.y - 82)
	power_box.position = Vector2(size.x - 198, size.y - 4 * 66 - 96)
	scheme_btn.position = Vector2(14, 10)
	help_btn.position = Vector2(210, 10)
	menu_btn.position = Vector2(346, 10)
	var live := commander.live_selection()
	card.visible = not live.is_empty()
	var any_air := live.any(func(u): return u.is_air())
	card_buttons["return"].disabled = not any_air
	for id in power_buttons:
		var b: Button = power_buttons[id]
		var left: float = battle.power_cooldown_left(commander.team, id)
		var l := b.get_node("L") as Label
		l.text = "%s\n%s" % [UnitDefs.POWERS[id].name, "READY" if left <= 0.0 else "%d s" % int(ceil(left))]
		l.add_theme_color_override("font_color", ACCENT if left <= 0.0 else Color(0.7, 0.72, 0.7))
		b.disabled = left > 0.0
	queue_redraw()


func _mini_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed:
		var p := _mini_to_world(e.position + mini_rect.position)
		if (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
			if commander.mode.begins_with("power:") or (commander.mode != "" and not commander.selected.is_empty()):
				var fake := InputEventMouseButton.new()
				commander.camera.focus(p)   # bring the target into view, then apply the order there
				commander._apply_mode(commander.camera.cam.unproject_position(p), fake)
			else:
				camera.focus(p)
		elif (e as InputEventMouseButton).button_index == MOUSE_BUTTON_RIGHT and not commander.selected.is_empty():
			battle.issue({"type": "move", "ids": commander._ids(), "points": commander.formation(p)})
		mini_ctl.accept_event()
	elif e is InputEventMouseMotion and (e as InputEventMouseMotion).button_mask & MOUSE_BUTTON_MASK_LEFT:
		camera.focus(_mini_to_world(e.position + mini_rect.position))
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


func _portrait(u: Unit) -> Texture2D:
	if not u.def.has("icon"): return null
	if not portraits.has(u.kind): portraits[u.kind] = load(u.def.icon)
	return portraits[u.kind]


func _draw() -> void:
	if battle == null: return
	var cam := camera.cam
	_draw_waypoints()
	# health bars (selected, damaged or hovered)
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(commander.team, u): continue
		if not (u.selected or u.hp < u.def.hp or u == commander.hover): continue
		var top: Vector3 = u.world_center() + Vector3.UP * (u.def.height + 1.5)
		if cam.is_position_behind(top): continue
		var sp := cam.unproject_position(top)
		var w := 46.0
		var r := Rect2(sp - Vector2(w / 2, 0), Vector2(w, 5))
		var f: float = u.hp / u.def.hp
		draw_rect(r.grow(1), Color(0, 0, 0, 0.75))
		var col := Color(0.3, 0.9, 0.4) if f > 0.6 else (Color(0.95, 0.8, 0.2) if f > 0.3 else Color(0.95, 0.25, 0.2))
		draw_rect(Rect2(r.position, Vector2(w * f, 5)), col)
		draw_rect(Rect2(r.position - Vector2(0, 4), Vector2(w, 2)), UnitDefs.TEAM_COLORS[u.team].lightened(0.25))
		if u.selected and u.domain == "jet":
			_text(sp + Vector2(-w / 2, 18), _ammo_text(u), 11, Color(1, 0.85, 0.5))
	if commander.dragging and commander.drag_from.distance_to(commander.drag_to) > 6.0 and commander.mode == "":
		var r := Rect2(commander.drag_from, Vector2.ZERO).expand(commander.drag_to)
		draw_rect(r, Color(0.4, 1.0, 0.55, 0.12))
		draw_rect(r, Color(0.4, 1.0, 0.55, 0.9), false, 1.5)
	_draw_minimap()
	_draw_selection_panel()
	_draw_status()
	if show_help: _draw_help()
	if commander.mode != "":
		var label: String = {"attack_move": "ATTACK-MOVE", "guard": "GUARD - click ground or a friendly unit", "force": "FORCE FIRE",
			"waypoint": "WAYPOINTS - right click to finish"}.get(commander.mode, "")
		if commander.mode.begins_with("power:"): label = String(UnitDefs.POWERS[commander.mode.substr(6)].name).to_upper() + " - click target"
		_text(get_local_mouse_position() + Vector2(18, 26), label, 13, Color(1, 0.65, 0.3))
	if banner != "":
		var s := font.get_string_size(banner, HORIZONTAL_ALIGNMENT_LEFT, -1, 64)
		var p := Vector2((size.x - s.x) / 2, size.y * 0.38)
		draw_rect(Rect2(0, p.y - 66, size.x, 96), Color(0, 0, 0, 0.55))
		draw_string(font, p, banner, HORIZONTAL_ALIGNMENT_LEFT, -1, 64, banner_color)


func _ammo_text(u: Unit) -> String:
	if u.state == Unit.S.LANDED: return "REARMING" if not _full(u) else "ON PAD"
	var parts := []
	for i in u.w_ammo.size():
		if u.w_ammo[i] >= 0: parts.append("%d/%d" % [u.w_ammo[i], int(u.def.weapons[i].ammo)])
	return "AMMO " + " ".join(parts)


func _full(u: Unit) -> bool:
	for i in u.w_ammo.size():
		var full := int(u.def.weapons[i].get("ammo", -1))
		if full > 0 and u.w_ammo[i] < full: return false
	return true


func _draw_waypoints() -> void:
	var cam := camera.cam
	for u: Unit in commander.live_selection():
		if u.state != Unit.S.MOVE or u.queue.is_empty(): continue
		var pts: Array = [u.position, u.goal] + u.queue
		for i in pts.size() - 1:
			var a: Vector3 = pts[i]
			var b: Vector3 = pts[i + 1]
			if cam.is_position_behind(a) or cam.is_position_behind(b): continue
			draw_line(cam.unproject_position(a + Vector3.UP * 0.3), cam.unproject_position(b + Vector3.UP * 0.3), Color(0.5, 1, 0.7, 0.7), 1.5)
			draw_circle(cam.unproject_position(b + Vector3.UP * 0.3), 4.0, Color(0.5, 1, 0.7, 0.9))


func _draw_minimap() -> void:
	_panel(mini_rect.grow(4))
	draw_rect(mini_rect, Color(0.17, 0.22, 0.11))
	for o in battle.obstacles_2d:
		draw_circle(_world_to_mini(Vector3(o.x, 0, o.y)), maxf(1.5, o.z / battle.map_bounds.size.x * mini_rect.size.x), Color(0.35, 0.33, 0.3))
	for q: Vector3 in battle.PAD_POSITIONS:
		draw_rect(Rect2(_world_to_mini(q) - Vector2(4, 4), Vector2(8, 8)), Color(0.5, 0.5, 0.48))
	if battle.fog_mini_tex:
		# fog texture covers FOG_RECT; draw only the part that lies inside the playable map
		var fr: Rect2 = battle.FOG_RECT
		var mb: Rect2 = battle.map_bounds
		var px := float(battle.FOG_N) / fr.size.x
		var src := Rect2((mb.position.x - fr.position.x) * px, (mb.position.y - fr.position.y) * px, mb.size.x * px, mb.size.y * px)
		draw_texture_rect_region(battle.fog_mini_tex, mini_rect, src)
	for z in battle.reveal_zones:
		draw_line(_world_to_mini(z.a), _world_to_mini(z.b), Color(1, 1, 0.6, 0.25), z.w / battle.map_bounds.size.x * mini_rect.size.x)
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(commander.team, u): continue
		var p := _world_to_mini(u.global_position)
		var c: Color = UnitDefs.TEAM_COLORS[u.team].lightened(0.35 if u.selected else 0.1)
		if u.domain == "ground":
			draw_rect(Rect2(p - Vector2(2.5, 2.5), Vector2(5, 5)), c)
		else:
			draw_colored_polygon(PackedVector2Array([p + Vector2(0, -4), p + Vector2(3.5, 3), p + Vector2(-3.5, 3)]), c)
	var vs := camera.get_viewport().get_visible_rect().size
	var pts := PackedVector2Array()
	for c in [Vector2(0, 0), Vector2(vs.x, 0), Vector2(vs.x, vs.y), Vector2(0, vs.y), Vector2(0, 0)]:
		var g: Variant = camera.ground_at(c)
		if g == null: g = camera.position
		var mp := _world_to_mini(g)
		pts.append(Vector2(clampf(mp.x, mini_rect.position.x, mini_rect.end.x), clampf(mp.y, mini_rect.position.y, mini_rect.end.y)))
	draw_polyline(pts, Color(1, 1, 1, 0.8), 1.0)


func _draw_selection_panel() -> void:
	var r := Rect2(240, size.y - 104, 380, 90)
	_panel(r)
	var sel := commander.live_selection()
	if sel.is_empty():
		_text(r.position + Vector2(14, 30), "No units selected", 15, Color(0.6, 0.65, 0.62))
		_text(r.position + Vector2(14, 54), "Drag a box or click a unit. Right drag scrolls.", 12, Color(0.5, 0.55, 0.52))
		return
	var counts := {}
	var hp := 0.0
	var mx := 0.0
	for u in sel:
		counts[u.def.name] = counts.get(u.def.name, 0) + 1
		hp += u.hp; mx += u.def.hp
	var tex := _portrait(sel[0])
	var x0 := 14.0
	if tex:
		draw_texture_rect(tex, Rect2(r.position + Vector2(8, 8), Vector2(118, 74)), false)
		x0 = 134.0
	var y := 26.0
	for k in counts:
		_text(r.position + Vector2(x0, y), "%d x %s" % [counts[k], k], 14)
		y += 17.0
		if y > 60: break
	_text(r.position + Vector2(x0, 66), sel[0].def.role, 11, Color(0.65, 0.72, 0.68))
	var bar := Rect2(r.position + Vector2(x0, 74), Vector2(r.size.x - x0 - 12, 7))
	draw_rect(bar, Color(0, 0, 0, 0.6))
	draw_rect(Rect2(bar.position, Vector2(bar.size.x * hp / mx, 7)), Color(0.3, 0.9, 0.4))


func _draw_status() -> void:
	var r := Rect2(size.x / 2 - 170, 10, 340, 34)
	_panel(r)
	_text(r.position + Vector2(16, 23), "BLUE %d" % battle.alive_count(0), 16, UnitDefs.TEAM_COLORS[0].lightened(0.45))
	_text(r.position + Vector2(140, 23), "%02d:%02d" % [int(battle.sim_time) / 60, int(battle.sim_time) % 60], 16)
	_text(r.position + Vector2(250, 23), "RED %d" % battle.alive_count(1), 16, UnitDefs.TEAM_COLORS[1].lightened(0.45))
	if msg_t > 0.0:
		var s := font.get_string_size(msg, HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
		_text(Vector2((size.x - s.x) / 2, 70), msg, 16, Color(1, 0.85, 0.5, minf(1.0, msg_t)))


func _draw_help() -> void:
	var lines := [
		"STEEL ACCORD - controls (mouse: %s)" % commander.scheme.capitalize(),
		"Left click unit: select   Left drag: box select   Double-click: all of type",
		"Left click ground/enemy (Classic): move / attack    Right click: deselect",
		"Right drag: scroll map   Wheel: zoom   Middle drag: rotate/tilt",
		"Command card buttons or keys: A attack-move  G guard  F force fire",
		"  W waypoints  S stop  X scatter  R aircraft return to pad",
		"Ctrl+click: force fire   Alt+click: add waypoint   Shift: keep mode",
		"Ctrl+A select all   Ctrl+1..9 set group   1..9 recall (twice: jump)",
		"Support powers (right column): click, then click a target",
		"Minimap: left click/drag moves camera, right click moves units",
		"Esc (nothing selected) or F10: pause menu - Resume, Restart, Options, Main Menu, Exit",
	]
	var r := Rect2(size.x / 2 - 260, 54, 520, 22 + lines.size() * 18)
	_panel(r)
	for i in lines.size():
		_text(r.position + Vector2(12, 24 + i * 18), lines[i], 13 if i else 14, ACCENT if i == 0 else Color(0.82, 0.86, 0.84))

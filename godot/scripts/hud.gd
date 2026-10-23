# Steel Accord - in-game HUD. One control bar along the bottom of the screen (same pattern as classic RTS command bars,
# with our own art): radar on the left, a column of small buttons (menu, controls, find builder, mouse scheme), the
# 2 x 7 command grid in the middle (EconPanel) and the selection panel on the right (UnitPanel). The cash tab and the
# power gauge sit on the top edge of the bar. Above the world: health bars, rank chevrons and control-group numbers
# over units, waypoint lines, the selection box, score / clock, messages and help. Support powers: right edge.
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
var econ: EconPanel
var inspector: Inspector
var layer: CanvasLayer
var ui_scale := 1.0     # HUD scale: 1.0 up to 1080p, larger on 1440p / 4K (Options: UI scale)
var prod_strip: VBoxContainer
var _strip_sig := ""
var unit_panel: UnitPanel
var find_btn: Button
var details_open := false        # Details panel (full inspector text) above the selection panel
var bar_rect := Rect2()          # the control bar, in HUD units
var grid_rect := Rect2()
var panel_rect := Rect2()
var cash_rect := Rect2()
var power_rect := Rect2()
const BAR_H := 184.0
const BAR_MIN_W := 1404.0
const BAR_MAX_W := 1620.0


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
	menu_btn = icon_button("menu", "Menu (F10 / Esc) - pause, options, restart, exit", func(): battle.open_menu(), Vector2(38, 38))
	add_child(menu_btn)
	help_btn = _button("?", func(): show_help = not show_help, Vector2(38, 38))
	help_btn.add_theme_font_size_override("font_size", 18)
	help_btn.tooltip_text = "Controls and hotkeys (F1)"
	add_child(help_btn)
	find_btn = icon_button("find_builder", "Find builder (. key) - select the next builder and centre the camera on it", func(): commander.find_builder(), Vector2(38, 38))
	add_child(find_btn)
	scheme_btn = _button("Mouse: Classic", func(): _toggle_scheme(), Vector2(38, 38))
	scheme_btn.add_theme_font_size_override("font_size", 10)
	scheme_btn.tooltip_text = "Mouse scheme. Classic: left click selects AND commands, right click deselects, right drag scrolls.\nAlternate: left click selects, right click commands."
	add_child(scheme_btn)
	prod_strip = VBoxContainer.new()
	prod_strip.add_theme_constant_override("separation", 3)
	prod_strip.position = Vector2(14, 14)
	add_child(prod_strip)
	econ = EconPanel.new()
	econ.battle = battle; econ.commander = commander; econ.hud = self
	add_child(econ)
	inspector = Inspector.new()
	inspector.battle = battle; inspector.commander = commander; inspector.hud = self
	add_child(inspector)
	unit_panel = UnitPanel.new()
	unit_panel.battle = battle; unit_panel.commander = commander; unit_panel.hud = self
	add_child(unit_panel)


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


## Unit orders now live in the command grid (EconPanel fills card_buttons); this keeps an empty node for old callers.
func _build_card() -> void:
	card = Control.new()
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.visible = false
	add_child(card)


## Square button with one of the UI pictograms (assets/ui/icons/<id>.png).
func icon_button(id: String, tip: String, cb: Callable, sz: Vector2) -> Button:
	var b := _button("", cb, sz)
	b.tooltip_text = tip
	var path := "res://assets/ui/icons/%s.png" % id
	if ResourceLoader.exists(path):
		var ic := TextureRect.new()
		ic.texture = load(path)
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ic.position = Vector2(4, 4); ic.size = sz - Vector2(8, 8)
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(ic)
	return b


func _build_powers() -> void:
	power_box = Control.new()
	power_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(power_box)
	var i := 0
	var nat: String = battle.nation_of(commander.team)
	for id in Nations.powers(nat):
		var p: Dictionary = UnitDefs.POWERS[id]
		var b := _button("", func(): commander.set_mode("power:" + id), Vector2(186, 62))
		b.add_theme_stylebox_override("normal", _style(Color(0.07, 0.1, 0.11, 0.95), Color(0.86, 0.66, 0.22).darkened(0.25)))
		b.tooltip_text = "%s - click the button, then click the target on the map.\nCooldown %d s (PROVISIONAL)" % [battle.lbl(commander.team, id, p.name), int(p.cooldown)]
		var icon := TextureRect.new()
		icon.texture = load(Nations.power_icon(nat, id))
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
	_scheme_label()
	flash_message("Mouse scheme: %s" % ("left click commands, right click deselects" if commander.scheme == "classic" else "right click commands"))


## Auto: 1.0 up to 1080 lines, then proportional (1440p -> 1.33, 2160p -> 2.0). A fixed value from Options wins.
func _wanted_scale() -> float:
	var fixed: float = float(Game.settings.get("ui_scale", 0.0))
	var vs := get_viewport().get_visible_rect().size
	var k := fixed if fixed > 0.0 else maxf(1.0, vs.y / 1080.0)
	return minf(k, vs.x / (BAR_MIN_W + 16.0))   # the control bar always fits the screen width


func _scheme_label() -> void:
	scheme_btn.text = "L" if commander.scheme == "classic" else "R"
	scheme_btn.tooltip_text = "Mouse scheme: %s (click to switch)\nClassic: left click selects AND commands, right click deselects, right drag scrolls.\nAlternate: left click selects, right click commands." % commander.scheme.capitalize()


func flash_message(t: String) -> void:
	msg = t; msg_t = 4.0


func _process(dt: float) -> void:
	ui_scale = _wanted_scale()
	if layer: layer.scale = Vector2(ui_scale, ui_scale)
	size = get_viewport_rect().size / ui_scale
	position = Vector2.ZERO
	msg_t = maxf(0.0, msg_t - dt)
	_layout()
	if scheme_btn.text.length() > 1: _scheme_label()
	_update_prod_strip()
	for id in power_buttons:
		var b: Button = power_buttons[id]
		var left: float = battle.power_cooldown_left(commander.team, id)
		var l := b.get_node("L") as Label
		var pname: String = battle.lbl(commander.team, id, UnitDefs.POWERS[id].name)
		l.text = "%s\n%s" % [pname, "READY" if left <= 0.0 else "%d s" % int(ceil(left))]
		l.add_theme_color_override("font_color", ACCENT if left <= 0.0 else Color(0.7, 0.72, 0.7))
		var why: String = battle.power_problem(commander.team, id)
		b.disabled = left > 0.0 or why != ""
		if why != "": l.text = "%s\n%s" % [pname, why]
	queue_redraw()


## Control bar geometry (HUD units). Width grows with the screen up to BAR_MAX_W, centred.
func _layout() -> void:
	var w := clampf(size.x - 16.0, BAR_MIN_W, BAR_MAX_W)
	bar_rect = Rect2((size.x - w) / 2.0, size.y - BAR_H, w, BAR_H)
	var o := bar_rect.position
	mini_rect = Rect2(o + Vector2(14, 18), Vector2(154, 154))
	mini_ctl.position = mini_rect.position; mini_ctl.size = mini_rect.size
	var bx := o.x + 178.0
	for i in 4:
		var bt: Button = [menu_btn, help_btn, find_btn, scheme_btn][i]
		bt.position = Vector2(bx, o.y + 18 + i * 39)
		bt.size = Vector2(36, 36)
	grid_rect = Rect2(o + Vector2(230, 22), econ.size)
	econ.position = grid_rect.position
	panel_rect = Rect2(grid_rect.end.x + 18, o.y + 18, bar_rect.end.x - grid_rect.end.x - 32, BAR_H - 26)
	unit_panel.position = panel_rect.position
	unit_panel.size = panel_rect.size
	cash_rect = Rect2(grid_rect.get_center().x - 120, o.y - 30, 240, 32)
	power_rect = Rect2(grid_rect.position.x, o.y + 6, bar_rect.end.x - 14 - grid_rect.position.x, 8)
	power_box.position = Vector2(size.x - 198, 56)
	if inspector:
		var ih: float = inspector.get_combined_minimum_size().y
		inspector.position = Vector2(bar_rect.end.x - inspector.W - 12, bar_rect.position.y - 40 - ih)


## Persistent production strip: one row per producer with work queued (or a structure under construction).
## Click a row: select that structure and centre the camera on it.
func _update_prod_strip() -> void:
	if battle.scenario != "base": return
	var rows: Array = []
	for b in battle.structures(commander.team, "", false):
		if not b.built or not b.prod_queue.is_empty(): rows.append(b)
	var sig := ",".join(rows.map(func(b): return "%d:%d:%s" % [b.uid, b.prod_queue.size(), str(b.built)]))
	if sig != _strip_sig:
		_strip_sig = sig
		for c in prod_strip.get_children(): c.queue_free()
		for b in rows:
			var bb: Building = b
			var btn := _button("", func(): commander._set_selection([bb]); camera.focus(bb.position), Vector2(230, 24))
			btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
			btn.add_theme_font_size_override("font_size", 11)
			btn.set_meta("b", bb)
			prod_strip.add_child(btn)
	for c in prod_strip.get_children():
		var bm: Variant = c.get_meta("b")
		if c.is_queued_for_deletion() or not is_instance_valid(bm): continue
		var b: Building = bm
		if b.dead: continue
		if b.built and b.prod_queue.is_empty(): continue
		if not b.built:
			c.text = "%s  building %d%%" % [b.def.name, int(b.progress * 100.0)]
		else:
			var k: String = b.prod_queue[0]
			var total := float(BuildingDefs.UNIT_COST[k][1])
			var pct := int(100.0 * (1.0 - b.prod_left / total))
			var state := "" if battle.power_ok(commander.team) else "  (low power)"
			c.text = "%s: %s %d%%%s%s" % [b.def.name, UnitDefs.def_of(k).name.split(" (")[0], pct,
				("  +%d" % (b.prod_queue.size() - 1)) if b.prod_queue.size() > 1 else "", state]


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
	if str(u.def.get("icon", "")) == "": return null
	if not portraits.has(u.kind): portraits[u.kind] = load(u.def.icon)
	return portraits[u.kind]


## Rank badge: one to three gold chevrons (Veteran / Elite / Heroic).
func _draw_chevrons(p: Vector2, rank: int) -> void:
	var gold := Color(1.0, 0.82, 0.3) if rank < 3 else Color(1.0, 0.55, 0.25)
	for i in rank:
		var y := p.y - i * 4.0
		var pts := PackedVector2Array([p + Vector2(-5, y - p.y), p + Vector2(0, y - p.y + 4), p + Vector2(5, y - p.y)])
		draw_polyline(pts, Color(0, 0, 0, 0.8), 3.5)
		draw_polyline(pts, gold, 2.0)


func _draw() -> void:
	if battle == null: return
	var cam := camera.cam
	_draw_waypoints()
	# health bars (selected, damaged or hovered)
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(commander.team, u): continue
		var show_bar: bool = u.selected or u.hp < u.def.hp or u == commander.hover
		if not show_bar and u.vet_rank == 0: continue
		var top: Vector3 = u.bar_anchor()
		if cam.is_position_behind(top): continue
		var sp := cam.unproject_position(top) / ui_scale
		var w := 40.0 if u.def.get("visual") == "infantry" else (56.0 if not (u is Building) else 90.0)
		if u.vet_rank > 0: _draw_chevrons(sp + Vector2(-w / 2 - 10, 1), u.vet_rank)
		var g := group_of(u) if (u.selected or u == commander.hover) else -1
		if g >= 0:
			draw_rect(Rect2(sp + Vector2(w / 2 + 3, -6), Vector2(13, 13)), Color(0, 0, 0, 0.75))
			draw_string(font, sp + Vector2(w / 2 + 3, 5), str(g), HORIZONTAL_ALIGNMENT_CENTER, 13, 11, Color(0.75, 1.0, 0.85))
		if not show_bar: continue
		var r := Rect2(sp - Vector2(w / 2, 0), Vector2(w, 5))
		var f: float = u.hp / u.def.hp
		draw_rect(r.grow(1), Color(0, 0, 0, 0.75))
		var col := Color(0.3, 0.9, 0.4) if f > 0.6 else (Color(0.95, 0.8, 0.2) if f > 0.3 else Color(0.95, 0.25, 0.2))
		draw_rect(Rect2(r.position, Vector2(w * f, 5)), col)
		draw_rect(Rect2(r.position - Vector2(0, 4), Vector2(w, 2)), UnitDefs.team_color(u.team).lightened(0.25))
		if u.selected and u.domain == "jet":
			_text(sp + Vector2(-w / 2, 18), _ammo_text(u), 11, Color(1, 0.85, 0.5))
	# occupied civilian buildings: owner colour and head count, always shown
	for u: Unit in battle.units:
		if not (u is Building) or u.dead or u.passengers.is_empty() or not (u as Building).is_civic() or not battle.is_visible_to(commander.team, u): continue
		var tp: Vector3 = u.bar_anchor()
		if cam.is_position_behind(tp): continue
		var bp := cam.unproject_position(tp) / ui_scale + Vector2(0, -14)
		var txt := "%d/%d" % [u.passengers.size(), int(u.def.transport.capacity)]
		var tc: Color = UnitDefs.team_color(u.team)
		draw_rect(Rect2(bp - Vector2(24, 9), Vector2(48, 18)), Color(0, 0, 0, 0.7))
		draw_rect(Rect2(bp - Vector2(24, 9), Vector2(6, 18)), tc)
		_text(bp + Vector2(-15, 5), txt, 12, Color(1, 1, 1))
		if float((u as Building).bdef.get("garrison_heal", 0.0)) > 0.0: _text(bp + Vector2(15, 5), "+", 14, Color(0.5, 1.0, 0.6))
	if commander.dragging and commander.drag_from.distance_to(commander.drag_to) > 6.0 and commander.mode == "":
		var r := Rect2(commander.drag_from / ui_scale, Vector2.ZERO).expand(commander.drag_to / ui_scale)
		draw_rect(r, Color(0.4, 1.0, 0.55, 0.12))
		draw_rect(r, Color(0.4, 1.0, 0.55, 0.9), false, 1.5)
	_draw_bar()
	_draw_minimap()
	_draw_status()
	_draw_fps()
	if show_help: _draw_help()
	if commander.mode != "":
		var label: String = {"attack_move": "ATTACK-MOVE", "guard": "GUARD - click ground or a friendly unit", "force": "FORCE FIRE",
			"waypoint": "WAYPOINTS - right click to finish"}.get(commander.mode, "")
		if commander.mode.begins_with("place:"):
			label = "PLACE %s - %s" % [battle.bname(commander.team, commander.mode.substr(6)).to_upper(), "click to build" if commander.ghost_ok else commander.ghost_reason]
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
			draw_line(cam.unproject_position(a + Vector3.UP * 0.3) / ui_scale, cam.unproject_position(b + Vector3.UP * 0.3) / ui_scale, Color(0.5, 1, 0.7, 0.7), 1.5)
			draw_circle(cam.unproject_position(b + Vector3.UP * 0.3) / ui_scale, 4.0, Color(0.5, 1, 0.7, 0.9))


func _draw_minimap() -> void:
	draw_rect(mini_rect.grow(3), Color(0.02, 0.03, 0.03, 0.95))
	if battle.terrain:
		if battle.minimap_tex == null: battle.minimap_tex = battle.make_minimap_texture()
		draw_texture_rect(battle.minimap_tex, mini_rect, false)
	else:
		draw_rect(mini_rect, Color(0.17, 0.22, 0.11))
		for o in battle.obstacles_2d:
			draw_circle(_world_to_mini(Vector3(o.x, 0, o.y)), maxf(1.5, o.z / battle.map_bounds.size.x * mini_rect.size.x), Color(0.35, 0.33, 0.3))
	for pl in battle.piles:
		if pl.cash > 0: draw_circle(_world_to_mini(pl.pos), 3.5, Color(0.95, 0.8, 0.3))
	for e in battle.derricks:
		var dc: Color = UnitDefs.team_color(e.owner).lightened(0.3) if e.owner >= 0 else Color(0.9, 0.9, 0.85)
		var dp := _world_to_mini(e.pos)
		draw_rect(Rect2(dp - Vector2(3.5, 3.5), Vector2(7, 7)), Color(0.05, 0.05, 0.05))
		draw_rect(Rect2(dp - Vector2(2.5, 2.5), Vector2(5, 5)), dc)
	for q: Vector3 in (battle.PAD_POSITIONS if battle.scenario == "army" else []):
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
	var radar_ok: bool = battle.scenario != "base" or battle.radar_online(commander.team)
	for u: Unit in battle.units:
		if u.dead or not battle.is_visible_to(commander.team, u): continue
		if u.team != commander.team and not radar_ok and not (u is Building): continue
		var p := _world_to_mini(u.global_position)
		var c: Color = UnitDefs.team_color(u.team).lightened(0.35 if u.selected else 0.1)
		if u is Building:
			var hs: Vector2 = (u as Building).half / battle.map_bounds.size.x * mini_rect.size.x
			draw_rect(Rect2(p - hs, hs * 2.0).grow(0.5), c)
		elif u.domain == "ground":
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


## The control bar frame: a bevelled gunmetal plate with recessed wells for the radar, buttons, grid and panel,
## the cash tab on its top edge and the power gauge along it.
func _draw_bar() -> void:
	var r := bar_rect
	if r.size.x < 100.0: return   # not laid out yet (first frame)
	var cut := 18.0
	var plate := PackedVector2Array([r.position + Vector2(cut, 0), Vector2(r.end.x - cut, r.position.y), Vector2(r.end.x, r.position.y + cut),
		r.end, Vector2(r.position.x, r.end.y), r.position + Vector2(0, cut)])
	draw_colored_polygon(plate, Color(0.085, 0.105, 0.115, 0.97))
	var edge := plate.duplicate(); edge.append(plate[0])
	draw_polyline(edge, Color(0.36, 0.46, 0.45), 1.5)
	draw_line(r.position + Vector2(cut + 4, 3), Vector2(r.end.x - cut - 4, r.position.y + 3), Color(0.42, 0.95, 0.6, 0.35), 1.0)
	for well in [Rect2(r.position.x + 8, r.position.y + 12, 166, 166), Rect2(r.position.x + 174, r.position.y + 12, 46, 166),
			grid_rect.grow(6), panel_rect.grow(4)]:
		draw_rect(well, Color(0.035, 0.05, 0.055, 0.96))
		draw_rect(well, Color(0.2, 0.27, 0.27), false, 1.0)
	# the 14 grid slots, drawn empty underneath the tiles so the grid keeps its shape
	for i in EconPanel.SLOTS:
		var sp := grid_rect.position + Vector2((i % EconPanel.COLS) * (EconPanel.TILE.x + EconPanel.GAP), (i / EconPanel.COLS) * (EconPanel.TILE.y + EconPanel.GAP))
		draw_rect(Rect2(sp, EconPanel.TILE), Color(0.06, 0.08, 0.09, 0.9))
		draw_rect(Rect2(sp, EconPanel.TILE), Color(0.16, 0.21, 0.21), false, 1.0)
	# cash tab
	var t: int = commander.team
	if battle.scenario == "base":
		var c := cash_rect
		var tab := PackedVector2Array([c.position + Vector2(14, 0), Vector2(c.end.x - 14, c.position.y), Vector2(c.end.x, c.end.y), Vector2(c.position.x, c.end.y)])
		draw_colored_polygon(tab, Color(0.085, 0.105, 0.115, 0.97))
		var te := tab.duplicate(); te.append(tab[0])
		draw_polyline(te, Color(0.36, 0.46, 0.45), 1.5)
		var cs := "$ %s" % _thousands(battle.cash[t])
		draw_string(font, Vector2(c.position.x, c.position.y + 23), cs, HORIZONTAL_ALIGNMENT_CENTER, c.size.x - 70, 19, Color(0.98, 0.86, 0.4))
		var tr: Vector2 = battle.cash_trend(t)
		draw_string(font, Vector2(c.end.x - 82, c.position.y + 14), "+%d/min" % int(tr.x), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(0.6, 0.95, 0.6))
		draw_string(font, Vector2(c.end.x - 82, c.position.y + 26), "-%d/min" % int(tr.y), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(1.0, 0.6, 0.5))
		# power gauge: generated capacity vs use
		var g: int = battle.power_gen(t); var u: int = battle.power_use(t)
		var pr := power_rect
		draw_rect(pr, Color(0.02, 0.03, 0.03))
		var cap := float(maxi(maxi(g, u), 1))
		var ok := g >= u
		draw_rect(Rect2(pr.position, Vector2(pr.size.x * float(u) / cap, pr.size.y)), Color(0.35, 0.85, 0.45) if ok else Color(0.95, 0.35, 0.25))
		if g > 0 and g < cap: draw_line(Vector2(pr.position.x + pr.size.x * g / cap, pr.position.y - 2), Vector2(pr.position.x + pr.size.x * g / cap, pr.end.y + 2), Color(1, 1, 1), 2.0)
		var ptxt := "Power %d / %d%s" % [u, g, "" if ok else "  LOW POWER - half-speed production"]
		var pw := font.get_string_size(ptxt, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
		var pp := Vector2(c.end.x + 12, c.position.y + 6)
		draw_rect(Rect2(pp, Vector2(pw + 14, 20)), Color(0.05, 0.07, 0.08, 0.92))
		draw_string(font, pp + Vector2(7, 15), ptxt, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.6, 0.95, 0.6) if ok else Color(1.0, 0.45, 0.35))
		var pl: String = battle.plan[t]
		if pl != "" or battle.plan_pending[t] != "":
			var ptx: String = "Plan: " + (battle.lbl(t, pl, Upgrades.PLANS[pl].name) if pl != "" else "switching...")
			var qw := font.get_string_size(ptx, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
			var qp := Vector2(c.position.x - qw - 26, c.position.y + 6)
			draw_rect(Rect2(qp, Vector2(qw + 14, 20)), Color(0.05, 0.07, 0.08, 0.92))
			draw_string(font, qp + Vector2(7, 15), ptx, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.95, 0.85, 0.55))
	# one-line context from the command grid (builder hint, construction, transport load)
	if econ.visible and econ.info != "":
		var iw := minf(font.get_string_size(econ.info, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x + 16, grid_rect.size.x + 260)
		var ip := Vector2(grid_rect.position.x - 6, r.position.y - (58.0 if battle.scenario == "base" else 24.0))
		draw_rect(Rect2(ip, Vector2(iw, 20)), Color(0.05, 0.07, 0.08, 0.88))
		draw_string(font, ip + Vector2(8, 15), econ.info, HORIZONTAL_ALIGNMENT_LEFT, iw - 12, 12, Color(0.85, 0.9, 0.87))


func _thousands(n: int) -> String:
	var s := str(absi(n))
	var out := ""
	while s.length() > 3:
		out = "," + s.substr(s.length() - 3) + out
		s = s.substr(0, s.length() - 3)
	return ("-" if n < 0 else "") + s + out


## Rank chevrons drawn on any canvas (portraits use this too).
func draw_rank_badge(c: CanvasItem, p: Vector2, rank: int) -> void:
	var gold := Color(1.0, 0.82, 0.3) if rank < 3 else Color(1.0, 0.55, 0.25)
	c.draw_rect(Rect2(p - Vector2(11, 6 + rank * 5), Vector2(22, 10 + rank * 5)), Color(0, 0, 0, 0.6))
	for i in rank:
		var y := -i * 5.0
		var pts := PackedVector2Array([p + Vector2(-7, y - 3), p + Vector2(0, y + 2), p + Vector2(7, y - 3)])
		c.draw_polyline(pts, Color(0, 0, 0, 0.9), 4.0)
		c.draw_polyline(pts, gold, 2.4)


## Control group (Ctrl+number) that holds this unit, or -1.
func group_of(u: Unit) -> int:
	for g in commander.groups:
		if u in commander.groups[g]: return g
	return -1


## The group whose living members are exactly these units, or -1.
func group_of_all(objs: Array) -> int:
	var g := group_of(objs[0]) if not objs.is_empty() else -1
	if g < 0: return -1
	var live: Array = commander.groups[g].filter(func(x): return is_instance_valid(x) and not x.dead)
	return g if live.size() == objs.size() and objs.all(func(x): return x in live) else -1


func _draw_fps() -> void:
	if not bool(Game.settings.get("show_fps", false)): return
	var t := "%d FPS  %.1f ms" % [Engine.get_frames_per_second(), 1000.0 / maxf(1.0, Engine.get_frames_per_second())]
	draw_rect(Rect2(size.x - 130, 8, 120, 22), Color(0, 0, 0, 0.55))
	_text(Vector2(size.x - 124, 24), t, 13, Color(0.75, 1.0, 0.8))


func _draw_status() -> void:
	var r := Rect2(size.x / 2 - 170, 10, 340, 34)
	_panel(r)
	_text(r.position + Vector2(16, 23), "%s %d" % [UnitDefs.team_name(0).to_upper(), battle.alive_count(0)], 16, UnitDefs.team_color(0).lightened(0.45))
	_text(r.position + Vector2(140, 23), "%02d:%02d" % [int(battle.sim_time) / 60, int(battle.sim_time) % 60], 16)
	_text(r.position + Vector2(250, 23), "%s %d" % [UnitDefs.team_name(1).to_upper(), battle.alive_count(1)], 16, UnitDefs.team_color(1).lightened(0.45))
	if msg_t > 0.0:
		var s := font.get_string_size(msg, HORIZONTAL_ALIGNMENT_LEFT, -1, 16)
		var mp := Vector2((size.x - s.x) / 2, 72)
		draw_rect(Rect2(mp - Vector2(10, 18), Vector2(s.x + 20, 26)), Color(0, 0, 0, 0.45 * minf(1.0, msg_t)))
		_text(mp, msg, 16, Color(1, 0.85, 0.5, minf(1.0, msg_t)))


func _draw_help() -> void:
	var lines := [
		"STEEL ACCORD - controls (mouse: %s)" % commander.scheme.capitalize(),
		"Left click unit: select   Left drag: box select   Double-click: all of type",
		"Left click ground/enemy (Classic): move / attack    Right click: deselect",
		"Right drag: scroll map   Wheel: zoom   Middle drag: rotate/tilt",
		"Command grid tiles or keys: A attack-move  G guard  F force fire",
		"  W waypoints  S stop  X scatter  R aircraft return to pad",
		"Ctrl+click: force fire   Alt+click: add waypoint   Shift: keep mode",
		"Ctrl+A select all   Ctrl+0..9 set group (number shows over units)   0..9 recall (twice: jump)",
		"Q all combat units on screen (twice: whole map)   E same type on screen (twice: map)   H Command Center",
		". find builder   I details panel   Space: centre on selection",
		"Support powers (right edge): click, then click a target",
		"Minimap: left click/drag moves camera, right click moves units",
		"Esc (nothing selected) or F10: pause menu - Resume, Restart, Options, Main Menu, Exit",
	]
	var r := Rect2(size.x / 2 - 260, 54, 520, 22 + lines.size() * 18)
	_panel(r)
	for i in lines.size():
		_text(r.position + Vector2(12, 24 + i * 18), lines[i], 13 if i else 14, ACCENT if i == 0 else Color(0.82, 0.86, 0.84))

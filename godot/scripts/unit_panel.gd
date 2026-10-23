# Steel Accord - right side of the control bar: what is selected.
# Single unit: portrait with rank chevrons and group number, name, owner, health, current state, and a row of
#   status tiles - every research that applies to this unit (lit = installed, dim = not yet; tooltip says where it is
#   researched) plus the active battle plan when it affects the unit.
# Structure: portrait, name, health, operational / construction / low power / repair state, and its build queue
#   (up to 9 tiles; the first shows progress; research in progress is an amber tile). Click a queue tile: cancel.
# Group: one tile per unit type with its count (click: select only that type).
# The "i" button opens the Details panel (the full inspector text).
class_name UnitPanel
extends Control

const PORTRAIT := Vector2(128, 96)
const CAMEO := Vector2(46, 40)
var battle: Node
var commander: Commander
var hud: Control
var details_btn: Button
var row: Control
var _sig := ""
var subject: Unit = null
var objs: Array = []


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	row = Control.new()
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	row.position = Vector2(0, PORTRAIT.y + 10)
	add_child(row)
	details_btn = hud.icon_button("details", "Details (I) - full information about the selection", func(): hud.details_open = not hud.details_open, Vector2(30, 30))
	add_child(details_btn)


func _tex(p: String) -> Texture2D:
	return hud.econ.tex(p)


func portrait_of(u: Unit) -> Texture2D:
	if u is Building: return _tex(EconPanel.building_icon_path((u as Building).bkind))
	return _tex(EconPanel.unit_icon_path(u.kind))


func _process(_dt: float) -> void:
	details_btn.position = Vector2(size.x - 32, 0)
	var sel: Array = commander.live_selection()
	var sb: Building = commander.sel_building
	objs = sel.duplicate()
	if objs.is_empty() and sb and is_instance_valid(sb) and not sb.dead: objs = [sb]
	subject = objs[0] if objs.size() == 1 else null
	details_btn.visible = not objs.is_empty()
	var sig := ",".join(objs.map(func(u): return str(u.uid)))
	if subject is Building:
		var b := subject as Building
		sig += "|q" + ",".join(b.prod_queue) + "|r" + b.research_id + "|" + str(b.built) + "|p" + ",".join(b.pads.map(func(p): return str(p.uid)))
	elif subject:
		sig += "|u%d" % battle.upgrades[subject.team].size() + battle.plan[subject.team] if subject.team >= 0 and subject.team < 2 else ""
	if sig != _sig:
		_sig = sig
		for c in row.get_children(): c.queue_free()
		if subject is Building: _build_queue(subject as Building)
		elif subject: _build_cameos(subject)
		elif objs.size() > 1: _build_roster()
	queue_redraw()
	for c in row.get_children():
		if c.has_node("Overlay"): (c.get_node("Overlay") as Control).queue_redraw()


func _small(tip: String, icon: Texture2D, i: int, cb: Callable, sz := CAMEO) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = sz; b.size = sz
	b.position = Vector2(i * (sz.x + 4), 0)
	b.tooltip_text = tip
	var st := StyleBoxFlat.new()
	st.bg_color = Color(0.06, 0.08, 0.09, 0.97); st.border_color = Color(0.32, 0.4, 0.4); st.set_border_width_all(1)
	b.add_theme_stylebox_override("normal", st)
	var sh := st.duplicate() as StyleBoxFlat; sh.border_color = Color(0.7, 0.95, 0.8)
	b.add_theme_stylebox_override("hover", sh)
	b.add_theme_stylebox_override("pressed", sh)
	b.add_theme_stylebox_override("disabled", st)
	if icon:
		var ic := TextureRect.new()
		ic.name = "Icon"
		ic.texture = icon
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ic.position = Vector2(3, 3); ic.size = sz - Vector2(6, 6)
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(ic)
	b.pressed.connect(cb)
	row.add_child(b)
	return b


## Status tiles for one unit: the research that applies to it (lit when installed) and the battle plan.
func _build_cameos(u: Unit) -> void:
	if u.team < 0 or u.team > 1: return
	var i := 0
	for id in Upgrades.DEFS:
		if i >= 5: break
		if not Upgrades.applies(id, u): continue
		var d: Dictionary = Upgrades.DEFS[id]
		var have: bool = battle.has_upgrade(u.team, id)
		var nm: String = battle.lbl(u.team, id, d.name)
		var at: String = battle.bname(u.team, d.at)
		var c := _small("%s - %s\n%s" % [nm, "installed" if have else "not researched yet (research at the %s)" % at, d.desc],
			_tex(EconPanel.ICON_DIR + id + ".png"), i, func(): pass)
		c.modulate = Color(1, 1, 1, 1) if have else Color(0.42, 0.42, 0.42, 0.85)
		i += 1
	var pl: String = battle.plan[u.team]
	if pl != "" and u.domain == "ground" and not (u is Building):
		var pd: Dictionary = Upgrades.PLANS[pl]
		_small("Battle plan %s - active\n%s" % [battle.lbl(u.team, pl, pd.name), pd.desc], _tex(EconPanel.ICON_DIR + pl + ".png"), i, func(): pass)


## Build queue of a structure (research first when one is running).
func _build_queue(b: Building) -> void:
	var team: int = b.team
	var bid := b.uid
	var i := 0
	if b.research_id != "":
		var id := b.research_id
		var t := _small("%s - researching; click to cancel (full refund)" % battle.lbl(team, id, Upgrades.DEFS[id].name),
			_tex(EconPanel.ICON_DIR + id + ".png"), i, func(): battle.issue({"type": "cancel_research", "team": team, "id": bid}), Vector2(52, 40))
		_add_progress(t, func(): return 1.0 - b.research_left / float(Upgrades.DEFS[b.research_id].time) if b.research_id != "" else -1.0)
		i += 1
	for qi in b.prod_queue.size():
		if i >= 9: break
		var k: String = b.prod_queue[qi]
		var t := _small("%s - click to cancel the last queued unit (refund)" % UnitDefs.def_of(k).name, _tex(EconPanel.unit_icon_path(k)), i,
			func(): battle.issue({"type": "cancel_unit", "team": team, "id": bid}), Vector2(52, 40))
		if qi == 0:
			_add_progress(t, func(): return (1.0 - b.prod_left / float(BuildingDefs.UNIT_COST[b.prod_queue[0]][1])) if not b.prod_queue.is_empty() else -1.0)
		i += 1
	# Airfield pads: one tile per pad with the aircraft on it (or empty), after the queue
	if not b.pads.is_empty():
		i = maxi(i, 9 - b.pads.size())
		for pi in b.pads.size():
			var pu: Unit = battle.by_id.get(int(b.pads[pi].uid))
			var occ: bool = pu != null and not pu.dead
			var tip := "Pad %d - %s" % [pi + 1, ("%s, %s" % [pu.def.name, hud.inspector._state(pu)]) if occ else "free"]
			var t := _small(tip, _tex(EconPanel.unit_icon_path(pu.kind)) if occ else null, i, func(): if occ: commander._set_selection([pu]), Vector2(52, 40))
			var n := pi + 1
			var ov := Control.new()
			ov.mouse_filter = Control.MOUSE_FILTER_IGNORE
			ov.size = t.size
			ov.draw.connect(func():
				ov.draw_string(ThemeDB.fallback_font, Vector2(3, 12), "P%d" % n, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(0.75, 0.85, 0.82))
				if not occ: ov.draw_string(ThemeDB.fallback_font, Vector2(0, 30), "free", HORIZONTAL_ALIGNMENT_CENTER, ov.size.x, 11, Color(0.5, 0.56, 0.54)))
			t.add_child(ov)
			i += 1


func _add_progress(t: Button, f: Callable) -> void:
	var ov := Control.new()
	ov.name = "Overlay"
	ov.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ov.size = t.size
	ov.draw.connect(func():
		var p: float = f.call()
		if p < 0.0: return
		ov.draw_rect(Rect2(0, ov.size.y - 6, ov.size.x, 6), Color(0, 0, 0, 0.7))
		ov.draw_rect(Rect2(0, ov.size.y - 6, ov.size.x * clampf(p, 0.0, 1.0), 6), Color(0.4, 0.95, 0.55)))
	t.add_child(ov)


## Group: one tile per unit type with its count; click selects only that type.
func _build_roster() -> void:
	var by := {}
	var order: Array = []
	for u in objs:
		if not by.has(u.kind): by[u.kind] = []; order.append(u.kind)
		by[u.kind].append(u)
	var i := 0
	for k in order:
		if i >= 9: break
		var arr: Array = by[k]
		var t := _small("%d x %s - click to select only these" % [arr.size(), arr[0].def.name], _tex(EconPanel.unit_icon_path(k)), i,
			func(): commander._set_selection(arr), Vector2(52, 40))
		var n := arr.size()
		var ov := Control.new()
		ov.mouse_filter = Control.MOUSE_FILTER_IGNORE
		ov.size = t.size
		ov.draw.connect(func():
			ov.draw_rect(Rect2(ov.size.x - 20, ov.size.y - 15, 19, 14), Color(0, 0, 0, 0.75))
			ov.draw_string(ThemeDB.fallback_font, Vector2(ov.size.x - 20, ov.size.y - 4), str(n), HORIZONTAL_ALIGNMENT_CENTER, 19, 11, Color(1, 1, 1)))
		t.add_child(ov)
		i += 1


# ------------------------------------------------------------------ drawing
func _draw() -> void:
	var f: Font = ThemeDB.fallback_font
	var pr := Rect2(Vector2.ZERO, PORTRAIT)
	draw_rect(pr, Color(0.03, 0.05, 0.06, 0.95))
	draw_rect(pr, Color(0.3, 0.4, 0.4), false, 1.0)
	if objs.is_empty():
		draw_string(f, Vector2(PORTRAIT.x + 12, 26), "Nothing selected", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.6, 0.66, 0.64))
		draw_string(f, Vector2(PORTRAIT.x + 12, 48), "Click a unit or structure, or drag a box.", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.5, 0.56, 0.54))
		draw_string(f, Vector2(PORTRAIT.x + 12, 66), "Ctrl+1..9 makes a group; 1..9 recalls it.", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.5, 0.56, 0.54))
		return
	var u: Unit = objs[0]
	var t := portrait_of(u)
	if t:
		var ts := t.get_size()
		var k := maxf(PORTRAIT.x / ts.x, PORTRAIT.y / ts.y)
		var src_sz := PORTRAIT / k
		draw_texture_rect_region(t, Rect2(Vector2(1, 1), PORTRAIT - Vector2(2, 2)), Rect2((ts - src_sz) / 2.0, src_sz))
	var x0 := PORTRAIT.x + 12
	var w := size.x - x0 - 40
	if subject:
		if u.vet_rank > 0: hud.draw_rank_badge(self, Vector2(16, 18), u.vet_rank)
		var g: int = hud.group_of(u)
		if g >= 0: _group_badge(Vector2(PORTRAIT.x - 22, 4), g)
		var nm: String = battle.bname(u.team, (u as Building).bkind) if u is Building else str(u.def.name)
		draw_string(f, Vector2(x0, 18), nm, HORIZONTAL_ALIGNMENT_LEFT, w, 17, Color(0.95, 0.97, 0.95))
		var who := "You" if u.team == commander.team else ("Enemy" if u.team >= 0 else "Neutral")
		var cls: String = "Structure" if u is Building else str(u.def.get("role", "")).split(" - ")[0]
		draw_string(f, Vector2(x0, 36), "%s  |  %s (%s)" % [cls, who, Nations.name_of(battle.nation_of(u.team)) if u.team >= 0 and u.team < 2 else ""], HORIZONTAL_ALIGNMENT_LEFT, w, 12, Color(0.62, 0.72, 0.69))
		_hp_bar(Rect2(x0, 44, w, 14), u.hp, u.def.hp)
		var state: String = hud.inspector._state(u) if not (u is Building) else _bstate(u as Building)
		draw_string(f, Vector2(x0, 76), state, HORIZONTAL_ALIGNMENT_LEFT, w + 30, 13, Color(0.85, 0.9, 0.86))
		if not (u is Building) and Veterancy.eligible(u):
			var nxt := u.vet_rank + 1
			var vt: String = Veterancy.RANKS[u.vet_rank] + ("  -  XP %d / %d to %s" % [int(u.vet_xp), Veterancy.XP_TO_RANK[nxt], Veterancy.RANKS[nxt]] if nxt < Veterancy.RANKS.size() else "  -  top rank")
			draw_string(f, Vector2(x0, 94), vt, HORIZONTAL_ALIGNMENT_LEFT, w + 30, 12, Color(1.0, 0.84, 0.4) if u.vet_rank > 0 else Color(0.6, 0.66, 0.64))
		elif u is Building and (u as Building).built:
			var bb := u as Building
			var pads_txt := ""
			if not bb.pads.is_empty(): pads_txt = "   Pads %d / %d in use" % [bb.pads.filter(func(p): return battle.by_id.has(int(p.uid)) and not battle.by_id[int(p.uid)].dead).size(), bb.pads.size()]
			draw_string(f, Vector2(x0, 94), "Power %+d%s%s" % [bb.bdef.power, ("   Queue: %d" % bb.prod_queue.size()) if not bb.prod_queue.is_empty() else "", pads_txt], HORIZONTAL_ALIGNMENT_LEFT, w + 30, 12, Color(0.6, 0.66, 0.64))
	else:
		var hp := 0.0; var mx := 0.0
		for o in objs: hp += o.hp; mx += o.def.hp
		draw_string(f, Vector2(x0, 18), "%d selected" % objs.size(), HORIZONTAL_ALIGNMENT_LEFT, w, 17, Color(0.95, 0.97, 0.95))
		var g2: int = hud.group_of_all(objs)
		draw_string(f, Vector2(x0, 36), ("Group %d" % g2) if g2 >= 0 else "Ctrl+1..9 to make this a group", HORIZONTAL_ALIGNMENT_LEFT, w, 12, Color(0.62, 0.72, 0.69))
		_hp_bar(Rect2(x0, 44, w, 14), hp, mx)
		var vets := objs.filter(func(o): return o.vet_rank > 0).size()
		draw_string(f, Vector2(x0, 76), "%d type%s  -  %d veteran%s" % [_types(), "" if _types() == 1 else "s", vets, "" if vets == 1 else "s"], HORIZONTAL_ALIGNMENT_LEFT, w + 30, 13, Color(0.85, 0.9, 0.86))


func _types() -> int:
	var s := {}
	for o in objs: s[o.kind] = true
	return s.size()


func _bstate(b: Building) -> String:
	if not b.built: return "Under construction %d%%" % int(b.progress * 100.0)
	var parts: Array = ["Operational"]
	if b.bdef.power < 0 and not battle.power_ok(b.team): parts = ["Low power - working at half speed"]
	if b.repairing: parts.append("repairing" + ((" (paused: %s)" % b.repair_blocked) if b.repair_blocked != "" else ""))
	if not b.prod_queue.is_empty(): parts.append("building " + str(UnitDefs.def_of(b.prod_queue[0]).name).split(" (")[0])
	if b.research_id != "": parts.append("researching " + battle.lbl(b.team, b.research_id, Upgrades.DEFS[b.research_id].name))
	return ", ".join(parts)


func _hp_bar(r: Rect2, hp: float, mx: float) -> void:
	draw_rect(r, Color(0, 0, 0, 0.65))
	var fr := clampf(hp / maxf(1.0, mx), 0.0, 1.0)
	var col := Color(0.3, 0.9, 0.4) if fr > 0.6 else (Color(0.95, 0.8, 0.2) if fr > 0.3 else Color(0.95, 0.25, 0.2))
	draw_rect(Rect2(r.position, Vector2(r.size.x * fr, r.size.y)), col)
	draw_rect(r, Color(0.3, 0.38, 0.38), false, 1.0)
	draw_string(ThemeDB.fallback_font, r.position + Vector2(6, 11), "%d / %d" % [int(hp), int(mx)], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0, 0, 0, 0.9))


func _group_badge(p: Vector2, g: int) -> void:
	draw_rect(Rect2(p, Vector2(18, 18)), Color(0.05, 0.07, 0.08, 0.95))
	draw_rect(Rect2(p, Vector2(18, 18)), Color(0.55, 0.95, 0.7), false, 1.0)
	draw_string(ThemeDB.fallback_font, p + Vector2(0, 14), str(g), HORIZONTAL_ALIGNMENT_CENTER, 18, 13, Color(0.75, 1.0, 0.85))

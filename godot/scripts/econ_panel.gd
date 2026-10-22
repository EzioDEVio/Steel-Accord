# Steel Accord - economy side of the command card: Dozer build menu, structure production menu with queue,
# construction progress, cancel and sell. Every button issues a real command through Battle.issue().
class_name EconPanel
extends Control

const BTN := Vector2(118, 60)
const COLS := 5
const GRID_Y := 34.0          # production / build grid starts below the action row
var height := 0.0             # laid-out height (HUD anchors the panel to the bottom of the screen)

var battle: Node
var commander: Commander
var hud: Control
var buttons := {}          # key -> Button
var queue_box: Control
var info: Label
var _sig := ""
var icons := {}


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	queue_box = Control.new()
	queue_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(queue_box)
	info = Label.new()
	info.add_theme_font_size_override("font_size", 12)
	info.add_theme_color_override("font_color", Color(0.85, 0.9, 0.87))
	info.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(info)


func _icon(path: String) -> Texture2D:
	if path == "" or not ResourceLoader.exists(path): return null
	if not icons.has(path): icons[path] = load(path)
	return icons[path]


func _make(key: String, title: String, cost: int, icon_path: String, cb: Callable, pos: Vector2, tip: String) -> Button:
	var b: Button = hud._button("", cb, BTN)
	b.position = pos
	b.tooltip_text = tip
	var t := _icon(icon_path)
	if t:
		var ic := TextureRect.new()
		ic.texture = t
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ic.position = Vector2(4, 3); ic.size = Vector2(BTN.x - 8, 37)
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(ic)
	var l := Label.new()
	l.text = "%s  $%d" % [title, cost] if cost > 0 else title
	l.add_theme_font_size_override("font_size", 10)
	l.position = Vector2(2, 41); l.size = Vector2(BTN.x - 4, 18)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.clip_text = true
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(l)
	add_child(b)
	buttons[key] = b
	return b


func _clear() -> void:
	for k in buttons: buttons[k].queue_free()
	buttons.clear()


func _process(_dt: float) -> void:
	if battle == null: return
	var team: int = commander.team
	var b: Building = commander.sel_building if is_instance_valid(commander.sel_building) and not commander.sel_building.dead else null
	var dz: Array = commander.dozers()
	var sig := ""
	var trs: Array = commander.live_selection().filter(func(x): return x.is_transport())
	if b: sig = "b%d:%s" % [b.uid, str(b.built)]
	elif not dz.is_empty(): sig = "dozer"
	elif trs.size() == 1: sig = "tr%d:%d" % [trs[0].uid, trs[0].passengers.size()]
	if sig != _sig:
		_sig = sig
		_clear()
		if b: _build_structure_menu(b)
		elif sig == "dozer": _build_dozer_menu()
		elif sig.begins_with("tr"): _build_transport_menu(trs[0])
	visible = sig != ""
	if not visible: return
	# live state: affordability / requirements, queue, progress
	if sig.begins_with("tr"):
		var tr: Unit = trs[0]
		info.text = "%s - passengers %d / %d. Select infantry and click this vehicle to board.%s" % [tr.def.name,
			tr.passengers.size(), int(tr.def.transport.capacity), "  Unloading..." if tr.unload_pending else ""]
		info.position = Vector2(0, -18)
		_draw_queue([])
	elif sig == "dozer":
		for k in BuildingDefs.BUILD_MENU:
			var why := ""
			if not battle.requirements_met(team, k):
				why = "Requires " + ", ".join(BuildingDefs.DEFS[k].requires.map(func(x): return BuildingDefs.DEFS[x].name))
			elif battle.cash[team] < int(BuildingDefs.DEFS[k].cost): why = "Not enough cash"
			buttons[k].disabled = why != ""
			buttons[k].tooltip_text = "%s - $%d, %d s, power %+d\n%s%s" % [BuildingDefs.DEFS[k].name, BuildingDefs.DEFS[k].cost,
				int(BuildingDefs.DEFS[k].build_time), int(BuildingDefs.DEFS[k].power), BuildingDefs.DEFS[k].desc, ("\n" + why) if why != "" else ""]
		info.text = "DOZER - choose a structure, then click the map to place it (Esc / right click cancels)."
		info.position = Vector2(0, 8)
		_draw_queue([])
	elif b:
		if not b.built:
			info.text = "%s - under construction %d%%  (a Dozer must work on it)" % [b.bdef.name, int(b.progress * 100.0)]
		else:
			var pw: int = b.bdef.power
			info.text = "%s   power %+d   %s" % [b.bdef.name, pw, "" if b.bdef.produces.is_empty() else "Click the map to set the rally point."]
		info.position = Vector2(2 * (BTN.x + 4) + 6, 6) if b.built else Vector2(270, 6)
		for k in b.bdef.produces:
			if not buttons.has(k): continue
			var why: String = battle.produce_problem(b, k)
			buttons[k].disabled = why != "" and why != "Queue full"
			var d: Dictionary = UnitDefs.def_of(k)
			buttons[k].tooltip_text = "%s - $%d, %d s\n%s%s" % [d.name, BuildingDefs.UNIT_COST[k][0], int(BuildingDefs.UNIT_COST[k][1]),
				d.get("role", ""), ("\n" + why) if why != "" else ""]
		if buttons.has("sell"): buttons["sell"].disabled = not b.built or b.bkind == "command_center"
		if buttons.has("repair"):
			var rb: Button = buttons["repair"]
			var full: bool = b.hp >= b.bdef.hp
			rb.disabled = full and not b.repairing
			rb.text = "Stop repair" if b.repairing else ("Full health" if full else "Repair")
			rb.tooltip_text = "Restores %d%% health per second for $%.0f per second (half the build cost for a full repair).%s" % [
				int(Building.REPAIR_RATE * 100.0), b.repair_cost_per_s(), ("\nPaused: " + b.repair_blocked) if b.repair_blocked != "" else ""]
			if b.repairing:
				info.text += "   REPAIRING" + ((" - paused: " + b.repair_blocked) if b.repair_blocked != "" else "")
		_draw_queue(b.prod_queue)


func _build_dozer_menu() -> void:
	var i := 0
	for k in BuildingDefs.BUILD_MENU:
		var d: Dictionary = BuildingDefs.DEFS[k]
		var art := UsArt.building(d.art)
		var cb := func(): commander.set_mode("place:" + k)
		_make(k, d.name, int(d.cost), str(art.get("icon", "")), cb, _cell(i), "")
		i += 1
	height = _cell(i - 1).y + BTN.y


func _build_structure_menu(b: Building) -> void:
	var team: int = commander.team
	var i := 0
	if not b.built:
		var cancel := func(): battle.issue({"type": "cancel_build", "team": team, "id": b.uid})
		var cb: Button = hud._button("Cancel construction (full refund)", cancel, Vector2(260, 30))
		cb.tooltip_text = "Stop construction and get the full cost back"
		add_child(cb); buttons["cancel"] = cb
		height = 30.0
		return
	for k in b.bdef.produces:
		var d: Dictionary = UnitDefs.def_of(k)
		var icon: String = str(d.get("icon", ""))
		if d.get("visual", "") == "vehicle_art": icon = str(UsArt.vehicle(d.art).get("icon", ""))
		elif d.get("visual", "") == "infantry": icon = str(UsArt.infantry(d.art).get("icon", ""))
		var cb := func(): battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": k})
		var nm: String = d.name.split(" (")[0]
		_make(k, nm, int(BuildingDefs.UNIT_COST[k][0]), icon, cb, _cell(i), "")
		i += 1
	# action row: Repair / Sell
	var rep := func(): battle.issue({"type": "repair", "team": team, "id": b.uid, "on": not b.repairing})
	var rb: Button = hud._button("Repair", rep, Vector2(BTN.x, 28))
	rb.position = Vector2(0, 0)
	add_child(rb)
	buttons["repair"] = rb
	var sell := func(): battle.issue({"type": "sell", "team": team, "id": b.uid})
	var sb: Button = hud._button("Sell (50%)", sell, Vector2(BTN.x, 28))
	sb.position = Vector2(BTN.x + 4, 0)
	sb.tooltip_text = "Sell this structure for half its cost (scaled by damage)"
	add_child(sb)
	buttons["sell"] = sb
	height = (_cell(i - 1).y + BTN.y if i > 0 else GRID_Y) + 32.0


func _build_transport_menu(tr: Unit) -> void:
	var team: int = commander.team
	var ua := func(): battle.issue({"type": "unload", "team": team, "ids": [tr.uid]})
	var ub: Button = hud._button("Unload all  D", ua, Vector2(BTN.x + 30, 28))
	ub.disabled = tr.passengers.is_empty()
	ub.tooltip_text = "Passengers get out around the vehicle (helicopters hover low first)"
	add_child(ub); buttons["unload"] = ub
	var i := 0
	for p in tr.passengers:
		var pu: Unit = p
		var one := func(): battle.issue({"type": "unload_one", "team": team, "id": tr.uid, "passenger": pu.uid})
		var icon := str(UsArt.infantry(pu.def.get("art", "")).get("icon", ""))
		_make("p%d" % pu.uid, pu.def.name, 0, icon, one, _cell(i), "Unload this soldier")
		i += 1
	height = (_cell(i - 1).y + BTN.y) if i > 0 else 30.0


func _cell(i: int) -> Vector2:
	return Vector2((i % COLS) * (BTN.x + 4), GRID_Y + (i / COLS) * (BTN.y + 4))


## Production queue: one small tile per queued unit; the first shows progress. Click a tile: cancel the last (refund).
var _qsig := ""


func _draw_queue(q: Array) -> void:
	var b: Building = commander.sel_building
	var qs := "%s|%s" % [str(b.uid if b else -1), ",".join(q)]
	if qs == _qsig:
		if b and not q.is_empty() and queue_box.get_child_count() > 0:
			var total := float(BuildingDefs.UNIT_COST[q[0]][1])
			(queue_box.get_child(0) as Button).text = "%s %d%%" % [str(q[0]).substr(0, 4), int(100.0 * (1.0 - b.prod_left / total))]
		return
	_qsig = qs
	for c in queue_box.get_children(): c.queue_free()
	queue_box.position = Vector2(0, height - 28.0)
	for i in q.size():
		var t := Button.new()
		t.focus_mode = Control.FOCUS_NONE
		t.custom_minimum_size = Vector2(54, 26); t.size = Vector2(54, 26)
		t.position = Vector2(i * 58, 0)
		t.add_theme_font_size_override("font_size", 10)
		var label: String = str(q[i]).substr(0, 7)
		if i == 0 and b:
			var total := float(BuildingDefs.UNIT_COST[q[0]][1])
			label = "%s %d%%" % [label.substr(0, 4), int(100.0 * (1.0 - b.prod_left / total))]
		t.text = label
		t.tooltip_text = "Click to cancel the last queued unit (refund)"
		var team: int = commander.team
		var bid := b.uid
		t.pressed.connect(func(): battle.issue({"type": "cancel_unit", "team": team, "id": bid}))
		queue_box.add_child(t)

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
	if t == null:      # text-only buttons (research, plans): wrap over the whole button
		l.position = Vector2(3, 3); l.size = Vector2(BTN.x - 6, BTN.y - 6)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.add_theme_font_size_override("font_size", 11)
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
	if b: sig = "b%d:%s:%s" % [b.uid, str(b.built), tab]
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
				why = "Requires " + ", ".join(BuildingDefs.DEFS[k].requires.map(func(x): return battle.bname(team, x)))
			elif battle.cash[team] < int(BuildingDefs.DEFS[k].cost): why = "Not enough cash"
			buttons[k].disabled = why != ""
			buttons[k].tooltip_text = "%s - $%d, %d s, power %+d\n%s%s" % [battle.bname(team, k), BuildingDefs.DEFS[k].cost,
				int(BuildingDefs.DEFS[k].build_time), int(BuildingDefs.DEFS[k].power), BuildingDefs.DEFS[k].desc, ("\n" + why) if why != "" else ""]
		info.text = "DOZER - choose a structure, then click the map to place it (Esc / right click cancels)."
		info.position = Vector2(0, 8)
		_draw_queue([])
	elif b:
		if not b.built:
			info.text = "%s - under construction %d%%  (a Dozer must work on it)" % [b.def.name, int(b.progress * 100.0)]
		else:
			var pw: int = b.bdef.power
			var extra := ""
			if not b.pads.is_empty():
				var used := 0
				for p in b.pads:
					var pu: Unit = battle.by_id.get(int(p.uid))
					if pu and not pu.dead: used += 1
				extra += "  pads %d/%d" % [used, b.pads.size()]
			if b.bkind == "supply_depot":
				var hauling := 0
				for u in battle.units:
					if u.team == team and not u.dead and u.state == Unit.S.HAUL: hauling += 1
				var stock := 0
				for pl in battle.piles: stock += int(pl.cash)
				extra += "  CH-47s hauling %d  piles $%d" % [hauling, stock]
			if b.bdef.has("drop"): extra += "  next drop %d s" % int(b.drop_t)
			if b.bdef.power < 0 and not battle.power_ok(team): extra += "  LOW POWER"
			info.text = "%s  %+d power%s" % [b.def.name, pw, extra]
		info.position = Vector2(0, -18) if b.built else Vector2(270, 6)
		for k in b.produces_list():
			if not buttons.has(k): continue
			var why: String = battle.produce_problem(b, k)
			buttons[k].disabled = why != "" and why != "Queue full"
			var d: Dictionary = UnitDefs.def_of(k)
			buttons[k].tooltip_text = "%s - $%d, %d s\n%s%s" % [d.name, BuildingDefs.UNIT_COST[k][0], int(BuildingDefs.UNIT_COST[k][1]),
				d.get("role", ""), ("\n" + why) if why != "" else ""]
			if Nations.is_placeholder(battle.nation_of(team), k): buttons[k].tooltip_text += "\n(Shared placeholder model until the Iran art pack arrives)"
		for key in buttons:
			if key.begins_with("up:"):
				var id: String = key.substr(3)
				var d: Dictionary = Upgrades.DEFS[id]
				var why: String = battle.research_problem(b, id)
				var bt: Button = buttons[key]
				var state := ""
				if battle.has_upgrade(team, id): state = "INSTALLED"
				elif b.research_id == id: state = "%d%% - click to cancel" % int(100.0 * (1.0 - b.research_left / float(d.time)))
				elif battle.researching_at(team, id): state = "researching elsewhere"
				bt.disabled = state == "" and why != ""
				if state == "INSTALLED": bt.disabled = true
				var lab := bt.get_child(bt.get_child_count() - 1) as Label
				var un: String = battle.lbl(team, id, d.name)
				lab.text = ("%s  %s" % [un, state]) if state != "" else "%s  $%d" % [un, int(d.cost)]
				bt.tooltip_text = "%s - $%d, %d s research\n%s\nAffects: %s%s" % [un, int(d.cost), int(d.time), d.desc,
					Upgrades.SCOPE_TEXT[d.scope], ("\n" + why) if why != "" and state == "" else ""]
			elif key.begins_with("plan:"):
				var pid: String = key.substr(5)
				var pd: Dictionary = Upgrades.PLANS[pid]
				var why2: String = battle.plan_problem(team, pid)
				var pb: Button = buttons[key]
				var st2 := "ACTIVE" if battle.plan[team] == pid else ("preparing %d s" % int(ceil(battle.plan_switch_t[team] - battle.sim_time)) if battle.plan_pending[team] == pid else "")
				pb.disabled = why2 != ""
				var lab2 := pb.get_child(pb.get_child_count() - 1) as Label
				var pn: String = battle.lbl(team, pid, pd.name)
				lab2.text = "%s %s" % [pn, st2]
				pb.tooltip_text = "Battle plan %s: %s\nOne plan at a time; switching takes %d s (no plan while switching).%s" % [pn, pd.desc,
					int(Upgrades.PLAN_SWITCH_S), ("\n" + why2) if why2 != "" and st2 == "" else ""]
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
		_make(k, battle.bname(commander.team, k), int(d.cost), str(art.get("icon", "")), cb, _cell(i), "")
		i += 1
	height = _cell(i - 1).y + BTN.y


## Structure command card. Production and research are separate tabs (never one mixed row); the action row holds
## Repair / Sell and the tab switches. Only real options appear (nation roster, research located here).
var tab := "production"


func _research_ids(b: Building) -> Array:
	var out: Array = []
	for id in Upgrades.DEFS:
		if Upgrades.DEFS[id].at == b.bkind: out.append(id)
	return out


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
	var prod: Array = b.produces_list()
	var res: Array = _research_ids(b)
	var has_plans: bool = b.bkind == "command_center"
	var n_up: int = res.size() + (Upgrades.PLANS.size() if has_plans else 0)
	if prod.is_empty() and n_up > 0: tab = "upgrades"
	elif n_up == 0: tab = "production"
	if tab == "production":
		if prod.is_empty() and not b.bdef.produces.is_empty():
			var note := Label.new()
			note.text = "Nothing to build here yet for %s." % Nations.name_of(battle.nation_of(team))
			note.position = Vector2(4, GRID_Y + 2)
			note.add_theme_font_size_override("font_size", 12)
			add_child(note); buttons["_note"] = note
		for k in prod:
			var d: Dictionary = UnitDefs.def_of(k)
			var icon: String = str(d.get("icon", ""))
			if icon == "" and d.get("visual", "") == "vehicle_art": icon = str(UsArt.vehicle(d.art).get("icon", ""))
			elif icon == "" and d.get("visual", "") == "infantry": icon = str(UsArt.infantry(d.art).get("icon", ""))
			var cb := func(): battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": k})
			var nm: String = d.name.split(" (")[0]
			_make(k, nm, int(BuildingDefs.UNIT_COST[k][0]), icon, cb, _cell(i), "")
			i += 1
	else:
		for id in res:
			var uid: String = id
			var cbr := func():
				if b.research_id == uid: battle.issue({"type": "cancel_research", "team": team, "id": b.uid})
				else: battle.issue({"type": "research", "team": team, "id": b.uid, "upgrade": uid})
			_make("up:" + id, battle.lbl(team, id, Upgrades.DEFS[id].name), int(Upgrades.DEFS[id].cost), "", cbr, _cell(i), "")
			i += 1
		if has_plans:
			for pid in Upgrades.PLANS:
				var pp: String = pid
				_make("plan:" + pid, battle.lbl(team, pid, Upgrades.PLANS[pid].name), 0, "", func(): battle.issue({"type": "plan", "team": team, "plan": pp}), _cell(i), "")
				i += 1
	# action row: Repair / Sell, then the Production / Upgrades tabs when the structure has both
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
	if not prod.is_empty() and n_up > 0:
		var x0 := 2 * (BTN.x + 4) + 12
		for t in [["production", "Production (%d)" % prod.size()], ["upgrades", ("Upgrades & Plans (%d)" if has_plans else "Upgrades (%d)") % n_up]]:
			var tid: String = t[0]
			var tb: Button = hud._button(t[1], func(): tab = tid; _sig = "", Vector2(150, 28))
			tb.position = Vector2(x0, 0)
			tb.tooltip_text = "Show what this structure can %s" % ("build" if tid == "production" else "research")
			if tab == tid:
				tb.add_theme_stylebox_override("normal", hud._style(Color(0.18, 0.32, 0.27, 1.0), hud.ACCENT))
			add_child(tb); buttons["tab:" + tid] = tb
			x0 += 154
	height = (_cell(i - 1).y + BTN.y if i > 0 else GRID_Y + 24.0) + 32.0


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

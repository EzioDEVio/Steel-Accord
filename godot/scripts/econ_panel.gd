# Steel Accord - command grid of the control bar: 2 rows x 7 square tiles, the same place for every selection.
# - Builder selected: the structures it can place.
# - Structure selected: what it produces (unit tiles), then what it researches (amber tiles) and battle plans (teal),
#   with Repair and Sell fixed in the last two slots. More than 12 entries -> the 12th tile turns to the next page.
# - Combat units selected: orders (attack-move, guard, force fire, waypoints, stop, scatter, return, unload,
#   select all) and, for a single transport, one tile per passenger (click: that soldier gets out).
# Every tile issues a real command through Battle.issue() or the Commander; nothing is decorative.
# Tiles carry a hotkey letter (orders), a cost (production / research), a queued count, a progress sweep and an
# installed tick, drawn by an overlay. Tooltips give the full name, cost, time, requirements and effect.
class_name EconPanel
extends Control

const TILE := Vector2(88, 68)
const GAP := 6.0
const COLS := 7
const ROWS := 2
const SLOTS := COLS * ROWS
const CAT_BORDER := {
	"unit": Color(0.42, 0.55, 0.6), "build": Color(0.42, 0.55, 0.6), "order": Color(0.45, 0.62, 0.78),
	"upgrade": Color(0.86, 0.66, 0.22), "plan": Color(0.3, 0.75, 0.66), "repair": Color(0.45, 0.7, 0.42),
	"sell": Color(0.8, 0.4, 0.33), "cancel": Color(0.8, 0.4, 0.33), "page": Color(0.6, 0.64, 0.66), "passenger": Color(0.45, 0.62, 0.78)}
const ICON_DIR := "res://assets/ui/icons/"

var battle: Node
var commander: Commander
var hud: Control
var buttons := {}          # key -> Button (tests and the HUD press these by key)
var height := TILE.y * ROWS + GAP
var info := ""             # one-line context text, shown by the HUD above the grid
var page := 0
var tab := "production"    # kept for old capture scripts; the grid shows everything (no tabs)
var _sig := ""
var _tex := {}


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = Vector2(COLS * TILE.x + (COLS - 1) * GAP, height)


func tex(path: String) -> Texture2D:
	if path == "" or not ResourceLoader.exists(path): return null
	if not _tex.has(path): _tex[path] = load(path)
	return _tex[path]


## Icon of a unit kind (its own icon, else the shared art pack's).
static func unit_icon_path(k: String) -> String:
	var d: Dictionary = UnitDefs.def_of(k)
	var icon: String = str(d.get("icon", ""))
	if icon == "" and d.get("visual", "") == "vehicle_art": icon = str(UsArt.vehicle(d.art).get("icon", ""))
	elif icon == "" and d.get("visual", "") == "infantry": icon = str(UsArt.infantry(d.get("art", "")).get("icon", ""))
	return icon


static func building_icon_path(k: String) -> String:
	return str(UsArt.building(BuildingDefs.DEFS[k].art).get("icon", ""))


func _cell(i: int) -> Vector2:
	return Vector2((i % COLS) * (TILE.x + GAP), (i / COLS) * (TILE.y + GAP))


func _tile_style(bg: Color, border: Color, w := 1) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg; s.border_color = border
	s.set_border_width_all(w); s.set_corner_radius_all(2)
	return s


## One grid tile. cat picks the border colour; icon fills the tile (unit art) or sits centred (pictograms).
func _tile(key: String, slot: int, cat: String, icon_path: String, tip: String, cb: Callable, meta := {}) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.custom_minimum_size = TILE; b.size = TILE
	b.position = _cell(slot)
	b.tooltip_text = tip
	var bc: Color = CAT_BORDER.get(cat, Color(0.4, 0.5, 0.5))
	b.add_theme_stylebox_override("normal", _tile_style(Color(0.07, 0.1, 0.11, 0.97), bc.darkened(0.15)))
	b.add_theme_stylebox_override("hover", _tile_style(Color(0.12, 0.17, 0.18, 1.0), bc.lightened(0.35), 2))
	b.add_theme_stylebox_override("pressed", _tile_style(Color(0.16, 0.24, 0.22, 1.0), Color(0.9, 1.0, 0.9), 2))
	b.add_theme_stylebox_override("disabled", _tile_style(Color(0.05, 0.06, 0.07, 0.97), Color(0.2, 0.22, 0.22)))
	b.pressed.connect(cb)
	var t := tex(icon_path)
	var art := cat in ["unit", "build", "passenger"]
	if t:
		var ic := TextureRect.new()
		ic.name = "Icon"
		ic.texture = t
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED if art else TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		var pad := 3.0 if art else 10.0
		ic.position = Vector2(pad, pad); ic.size = TILE - Vector2(pad, pad) * 2.0
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		ic.clip_contents = true
		b.add_child(ic)
	var m := {"cat": cat, "title": tip.split(" - ")[0].split("\n")[0], "hot": "", "cost": 0, "count": 0, "prog": -1.0,
		"done": false, "badge": "", "has_icon": t != null}
	m.merge(meta, true)
	b.set_meta("tile", m)
	var ov := Control.new()
	ov.name = "Overlay"
	ov.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ov.size = TILE
	ov.draw.connect(_draw_overlay.bind(b, ov))
	b.add_child(ov)
	add_child(b)
	buttons[key] = b
	return b


func _tset(b: Button, k: String, v: Variant) -> void:
	var m: Dictionary = b.get_meta("tile")
	if m.get(k) != v:
		m[k] = v
		(b.get_node("Overlay") as Control).queue_redraw()


func _draw_overlay(b: Button, ov: Control) -> void:
	var m: Dictionary = b.get_meta("tile")
	var f: Font = ThemeDB.fallback_font
	var dim := b.disabled
	if not m.has_icon:   # no art: the name, centred
		ov.draw_string(f, Vector2(4, TILE.y / 2 + 4), str(m.title), HORIZONTAL_ALIGNMENT_CENTER, TILE.x - 8, 11, Color(0.85, 0.9, 0.88))
	var p: float = m.prog
	if p >= 0.0 and p < 1.0:   # progress: the unfinished part is shaded, clockwise from 12 o'clock
		var c := TILE / 2.0
		var pts := PackedVector2Array([c])
		var a0 := -PI / 2.0 + p * TAU
		var steps := 28
		for i in steps + 1:
			var a := a0 + (TAU - p * TAU) * float(i) / steps
			pts.append(c + Vector2(cos(a), sin(a)) * 70.0)
		var box := PackedVector2Array([Vector2.ZERO, Vector2(TILE.x, 0), TILE, Vector2(0, TILE.y)])
		for poly in Geometry2D.intersect_polygons(pts, box):
			ov.draw_colored_polygon(poly, Color(0, 0, 0, 0.55))
		ov.draw_string(f, Vector2(0, TILE.y / 2 + 6), "%d%%" % int(p * 100.0), HORIZONTAL_ALIGNMENT_CENTER, TILE.x, 15, Color(1, 1, 1))
	if m.done:
		ov.draw_rect(Rect2(Vector2.ZERO, TILE), Color(0.1, 0.3, 0.15, 0.35))
		var q := Vector2(TILE.x - 22, 6)
		ov.draw_circle(q + Vector2(8, 8), 9.0, Color(0.1, 0.45, 0.2))
		ov.draw_polyline(PackedVector2Array([q + Vector2(3, 8), q + Vector2(7, 12), q + Vector2(13, 4)]), Color(1, 1, 1), 2.2)
	if str(m.hot) != "":
		ov.draw_rect(Rect2(2, 2, 16, 16), Color(0, 0, 0, 0.6))
		ov.draw_string(f, Vector2(2, 15), str(m.hot), HORIZONTAL_ALIGNMENT_CENTER, 16, 12, Color(1, 0.9, 0.55) if not dim else Color(0.5, 0.5, 0.5))
	if int(m.cost) > 0 and not m.done:
		var s := "$%d" % int(m.cost)
		var w := f.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x + 6
		ov.draw_rect(Rect2(TILE.x - w - 2, TILE.y - 16, w, 14), Color(0, 0, 0, 0.65))
		ov.draw_string(f, Vector2(TILE.x - w + 1, TILE.y - 5), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0.95, 0.85, 0.4) if not dim else Color(0.55, 0.52, 0.45))
	if int(m.count) > 0:
		ov.draw_circle(Vector2(TILE.x - 11, 11), 9.5, Color(0.1, 0.12, 0.13, 0.95))
		ov.draw_arc(Vector2(TILE.x - 11, 11), 9.5, 0, TAU, 20, Color(0.5, 0.95, 0.65), 1.5)
		ov.draw_string(f, Vector2(TILE.x - 21, 15), str(int(m.count)), HORIZONTAL_ALIGNMENT_CENTER, 20, 12, Color(1, 1, 1))
	if str(m.badge) != "":
		ov.draw_rect(Rect2(2, TILE.y - 16, TILE.x - 4, 14), Color(0, 0, 0, 0.65))
		ov.draw_string(f, Vector2(2, TILE.y - 5), str(m.badge), HORIZONTAL_ALIGNMENT_CENTER, TILE.x - 4, 10, Color(0.6, 1.0, 0.75))


func _clear() -> void:
	for k in buttons: buttons[k].queue_free()
	buttons.clear()


# ------------------------------------------------------------------ what the grid shows
func _process(_dt: float) -> void:
	if battle == null: return
	var team: int = commander.team
	var b: Building = commander.sel_building if is_instance_valid(commander.sel_building) and not commander.sel_building.dead else null
	var live: Array = commander.live_selection()
	var dz: Array = commander.dozers()
	var trs: Array = live.filter(func(x): return x.is_transport())
	var sig := ""
	if b and b.is_civic(): sig = "civ%d:%d" % [b.uid, b.passengers.size()]
	elif b: sig = "b%d:%s:%d" % [b.uid, str(b.built), page]
	elif not dz.is_empty(): sig = "dozer"
	elif not live.is_empty():
		sig = "units:%s" % str(live.any(func(u): return u.is_air()))
		if trs.size() == 1 and live.size() == 1: sig = "tr%d:%d" % [trs[0].uid, trs[0].passengers.size()]
	if sig != _sig:
		_sig = sig
		_clear()
		if b and b.is_civic(): _build_civic(b)
		elif b: _build_structure(b)
		elif sig == "dozer": _build_dozer()
		elif sig != "": _build_orders(live, trs[0] if sig.begins_with("tr") else null)
	visible = sig != ""
	info = ""
	if not visible: return
	if b and b.is_civic():
		var heal: float = float(b.bdef.get("garrison_heal", 0.0))
		info = "%s - %d / %d inside. They fire from the windows (+15%% range) and cannot be hit until it falls.%s" % [b.def.name,
			b.passengers.size(), int(b.def.transport.capacity), (" Occupants heal %d%% per second." % int(heal * 100.0)) if heal > 0.0 else ""]
		if buttons.has("unload"): buttons["unload"].disabled = b.passengers.is_empty()
	elif b: _update_structure(b, team)
	elif sig == "dozer": _update_dozer(team)
	else: _update_orders(live)


# ---- builder
func _build_dozer() -> void:
	var team: int = commander.team
	var i := 0
	for k in BuildingDefs.BUILD_MENU:
		var kk: String = k
		_tile(k, i, "build", building_icon_path(k), battle.bname(team, k), func(): commander.set_mode("place:" + kk), {"cost": int(BuildingDefs.DEFS[k].cost)})
		i += 1


func _update_dozer(team: int) -> void:
	for k in BuildingDefs.BUILD_MENU:
		var why := ""
		if not battle.requirements_met(team, k):
			why = "Requires " + ", ".join(BuildingDefs.DEFS[k].requires.map(func(x): return battle.bname(team, x)))
		elif battle.cash[team] < int(BuildingDefs.DEFS[k].cost): why = "Not enough cash"
		var bt: Button = buttons[k]
		bt.disabled = why != ""
		var d: Dictionary = BuildingDefs.DEFS[k]
		bt.tooltip_text = "%s - $%d, %d s, power %+d\n%s%s" % [battle.bname(team, k), d.cost, int(d.build_time), int(d.power), d.desc, ("\n" + why) if why != "" else ""]
	info = "Builder - choose a structure, then click the map to place it (Esc or right click cancels)."


# ---- structures
func _research_ids(b: Building) -> Array:
	var out: Array = []
	for id in Upgrades.DEFS:
		if Upgrades.DEFS[id].at == b.bkind: out.append(id)
	return out


func _build_structure(b: Building) -> void:
	var team: int = commander.team
	if not b.built:
		var bid := b.uid
		_tile("cancel", SLOTS - 1, "cancel", ICON_DIR + "cancel.png", "Cancel construction - full refund",
			func(): battle.issue({"type": "cancel_build", "team": team, "id": bid}))
		return
	var prod: Array = []      # [key, cat, icon, title, callable, meta]
	var fixed: Array = []     # research and plans: always on screen, just left of Repair / Sell
	for k in b.produces_list():
		var kk: String = k
		prod.append([k, "unit", unit_icon_path(k), str(UnitDefs.def_of(k).name).split(" (")[0],
			func(): battle.issue({"type": "produce", "team": team, "id": b.uid, "kind": kk}), {"cost": int(BuildingDefs.UNIT_COST[k][0])}])
	for id in _research_ids(b):
		var uid: String = id
		fixed.append(["up:" + id, "upgrade", ICON_DIR + id + ".png", battle.lbl(team, id, Upgrades.DEFS[id].name),
			func():
				if b.research_id == uid: battle.issue({"type": "cancel_research", "team": team, "id": b.uid})
				else: battle.issue({"type": "research", "team": team, "id": b.uid, "upgrade": uid}),
			{"cost": int(Upgrades.DEFS[id].cost)}])
	if b.bkind == "command_center":
		for pid in Upgrades.PLANS:
			var pp: String = pid
			fixed.append(["plan:" + pid, "plan", ICON_DIR + pid + ".png", battle.lbl(team, pid, Upgrades.PLANS[pid].name),
				func(): battle.issue({"type": "plan", "team": team, "plan": pp}), {}])
	var cap := SLOTS - 2 - fixed.size()          # slots left for production
	var pages := 1 if prod.size() <= cap else int(ceil(float(prod.size()) / (cap - 1)))
	page = page % pages
	var per := cap if pages == 1 else cap - 1
	var shown := prod.slice(page * per, page * per + per)
	for i in shown.size():
		var e: Array = shown[i]
		_tile(e[0], i, e[1], e[2], e[3], e[4], e[5])
	if pages > 1:
		_tile("page", cap - 1, "page", "", "More units - page %d of %d" % [page + 1, pages], func(): page += 1; _sig = "",
			{"badge": "%d / %d" % [page + 1, pages], "title": "More  >"})
	for i in fixed.size():
		var e: Array = fixed[i]
		_tile(e[0], SLOTS - 2 - fixed.size() + i, e[1], e[2], e[3], e[4], e[5])
	var bid := b.uid
	_tile("repair", SLOTS - 2, "repair", ICON_DIR + "repair.png", "Repair", func(): battle.issue({"type": "repair", "team": team, "id": bid, "on": not b.repairing}))
	_tile("sell", SLOTS - 1, "sell", ICON_DIR + "sell.png", "Sell - half its cost back (scaled by damage)", func(): battle.issue({"type": "sell", "team": team, "id": bid}))


func _update_structure(b: Building, team: int) -> void:
	if not b.built:
		info = "%s - under construction %d%% (a builder must work on it)" % [battle.bname(team, b.bkind), int(b.progress * 100.0)]
		return
	var counts := {}
	for q in b.prod_queue: counts[q] = counts.get(q, 0) + 1
	var total0 := float(BuildingDefs.UNIT_COST[b.prod_queue[0]][1]) if not b.prod_queue.is_empty() else 1.0
	for k in b.produces_list():
		if not buttons.has(k): continue
		var bt: Button = buttons[k]
		var why: String = battle.produce_problem(b, k)
		bt.disabled = why != "" and why != "Queue full"
		var d: Dictionary = UnitDefs.def_of(k)
		bt.tooltip_text = "%s - $%d, %d s\n%s%s" % [d.name, BuildingDefs.UNIT_COST[k][0], int(BuildingDefs.UNIT_COST[k][1]),
			d.get("role", ""), ("\n" + why) if why != "" else ""]
		if Nations.is_placeholder(battle.nation_of(team), k): bt.tooltip_text += "\n(Shared placeholder model until the Iran art pack arrives)"
		_tset(bt, "count", counts.get(k, 0))
		_tset(bt, "prog", (1.0 - b.prod_left / total0) if (not b.prod_queue.is_empty() and b.prod_queue[0] == k) else -1.0)
	for key in buttons:
		var bt: Button = buttons[key]
		if key.begins_with("up:"):
			var id: String = key.substr(3)
			var d: Dictionary = Upgrades.DEFS[id]
			var why: String = battle.research_problem(b, id)
			var un: String = battle.lbl(team, id, d.name)
			var done: bool = battle.has_upgrade(team, id)
			var here: bool = b.research_id == id
			var state := "Installed" if done else ("Researching %d%% - click to cancel (full refund)" % int(100.0 * (1.0 - b.research_left / float(d.time))) if here else
				("Researching at another structure" if battle.researching_at(team, id) else ""))
			bt.disabled = done or (state == "" and why != "")
			_tset(bt, "done", done)
			_tset(bt, "prog", (1.0 - b.research_left / float(d.time)) if here else -1.0)
			bt.tooltip_text = "%s - $%d, %d s research\n%s\nAffects: %s%s" % [un, int(d.cost), int(d.time), d.desc,
				Upgrades.SCOPE_TEXT[d.scope], ("\n" + state) if state != "" else (("\n" + why) if why != "" else "")]
		elif key.begins_with("plan:"):
			var pid: String = key.substr(5)
			var pd: Dictionary = Upgrades.PLANS[pid]
			var why2: String = battle.plan_problem(team, pid)
			var pn: String = battle.lbl(team, pid, pd.name)
			var active: bool = battle.plan[team] == pid
			var pending: bool = battle.plan_pending[team] == pid
			bt.disabled = why2 != ""
			_tset(bt, "done", active)
			_tset(bt, "badge", "ACTIVE" if active else ("%d s" % int(ceil(battle.plan_switch_t[team] - battle.sim_time)) if pending else ""))
			bt.tooltip_text = "Battle plan: %s\n%s\nOne plan at a time; switching takes %d s (no plan while switching).%s" % [pn, pd.desc,
				int(Upgrades.PLAN_SWITCH_S), ("\n" + why2) if why2 != "" and not active else ""]
	if buttons.has("sell"):
		buttons["sell"].disabled = b.bkind == "command_center"
		buttons["sell"].tooltip_text = "Sell - half its cost back (scaled by damage)" if b.bkind != "command_center" else "The Command Center cannot be sold"
	if buttons.has("repair"):
		var rb: Button = buttons["repair"]
		var full: bool = b.hp >= b.bdef.hp
		rb.disabled = full and not b.repairing
		_tset(rb, "badge", "STOP" if b.repairing else ("FULL" if full else ""))
		rb.tooltip_text = "%s\nRestores %d%% health per second for $%.0f per second (half the build cost for a full repair).%s" % [
			"Stop repairing" if b.repairing else ("Repair (already at full health)" if full else "Repair"),
			int(Building.REPAIR_RATE * 100.0), b.repair_cost_per_s(), ("\nPaused: " + b.repair_blocked) if b.repair_blocked != "" else ""]


# ---- civilian building held by us: get everyone out, or one soldier at a time
func _build_civic(b: Building) -> void:
	var team: int = commander.team
	var bid := b.uid
	_tile("unload", 0, "order", ICON_DIR + "unload.png", "Evacuate (D) - everyone leaves the building", func(): battle.issue({"type": "unload", "team": team, "ids": [bid]}), {"hot": "D"})
	var slot := 1
	for p in b.passengers:
		if slot >= SLOTS: break
		var pu: Unit = p
		_tile("p%d" % pu.uid, slot, "passenger", unit_icon_path(pu.kind), "%s (%d / %d health) - click: this soldier leaves" % [pu.def.name, int(pu.hp), int(pu.def.hp)],
			func(): battle.issue({"type": "unload_one", "team": team, "id": bid, "passenger": pu.uid}))
		slot += 1


# ---- units
const ORDERS := [
	["attack_move", "A", "Attack-Move (A) - move and engage anything met on the way"],
	["guard", "G", "Guard (G) - guard an area or a friendly unit: engage intruders, then return"],
	["force", "F", "Force Fire (F, or Ctrl+click) - fire at the ground or any unit"],
	["waypoint", "W", "Waypoints (W, or Alt+click) - click a chain of points; right click ends"],
	["stop", "S", "Stop (S) - stop and hold position"],
	["scatter", "X", "Scatter (X) - spread out from each other"],
	["return", "R", "Return to Pad (R) - aircraft fly back and land on their own pad (jets rearm there)"],
]


func _build_orders(live: Array, tr: Unit) -> void:
	var cbs := {"attack_move": func(): commander.set_mode("attack_move"), "guard": func(): commander.set_mode("guard"),
		"force": func(): commander.set_mode("force"), "waypoint": func(): commander.set_mode("waypoint"),
		"stop": func(): commander.cmd_stop(), "scatter": func(): commander.cmd_scatter(), "return": func(): commander.cmd_return()}
	var any_air: bool = live.any(func(u): return u.is_air())
	var slot := 0
	for o in ORDERS:
		if o[0] == "return" and not any_air: continue
		var t := _tile(o[0], slot, "order", ICON_DIR + o[0] + ".png", o[2], cbs[o[0]], {"hot": o[1]})
		hud.card_buttons[o[0]] = t
		slot += 1
	var team: int = commander.team
	if tr:
		var trid := tr.uid
		_tile("unload", slot, "order", ICON_DIR + "unload.png", "Unload all (D) - passengers get out around the vehicle", func(): battle.issue({"type": "unload", "team": team, "ids": [trid]}), {"hot": "D"})
		slot += 1
	_tile("select_all", SLOTS - 1, "order", ICON_DIR + "select_all.png", "Select All (Ctrl+A) - every unit you own", func(): commander.select_all(), {"hot": ""})
	hud.card_buttons["select_all"] = buttons["select_all"]
	if tr:
		for p in tr.passengers:
			if slot >= SLOTS - 1: break
			var pu: Unit = p
			var trid2 := tr.uid
			_tile("p%d" % pu.uid, slot, "passenger", unit_icon_path(pu.kind), "%s - click to unload this soldier" % pu.def.name,
				func(): battle.issue({"type": "unload_one", "team": team, "id": trid2, "passenger": pu.uid}))
			slot += 1


func _update_orders(live: Array) -> void:
	if buttons.has("return"): buttons["return"].disabled = not live.any(func(u): return u.is_air())
	if buttons.has("unload"):
		var tr: Unit = live[0]
		buttons["unload"].disabled = tr.passengers.is_empty()
		info = "%s - passengers %d / %d. Select infantry and click this vehicle to board.%s" % [tr.def.name,
			tr.passengers.size(), int(tr.def.transport.capacity), "  Unloading..." if tr.unload_pending else ""]
	for k in ["attack_move", "guard", "force", "waypoint"]:
		if buttons.has(k): _tset(buttons[k], "done", commander.mode == k)

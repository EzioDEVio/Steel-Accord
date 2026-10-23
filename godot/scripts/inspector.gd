# Steel Accord - universal object inspector (M7). Left-click any of your units or structures: this panel shows what
# the object is and what it is doing, from live simulation state only (no fields for systems the game lacks).
# - Unit: role, owner/nation, health, current order, weapons (range, damage, reload, targets), armour class,
#   speed / sight, veterancy rank + XP + earned bonuses, transport passengers, aircraft pad / ammo state.
# - Structure: purpose, power, construction / operational / low-power / repair state, production queue with progress
#   and ETA, rally point, Airfield pads, Supply Depot haulers and pile stock, drop timer, service bay, weapons.
# - Group: counts by type and total health; click a roster row to inspect (and select) that unit type.
# Pin keeps the last single object shown after the selection changes; Close hides it until the next selection.
# Combat is never paused by the panel.
class_name Inspector
extends PanelContainer

const W := 392.0
var battle: Node
var commander: Commander
var hud: Node
var title: Label
var sub: Label
var body: RichTextLabel
var roster: VBoxContainer
var pin_btn: Button
var close_btn: Button
var hp_bar: Control
var portrait: TextureRect
var _icons := {}
var pinned: Unit = null
var closed_sig := ""
var _sig := ""
var _t := 0.0
var subject: Unit = null       # what the panel currently describes (single object), for the health bar
var group: Array = []


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.05, 0.08, 0.09, 0.88); sb.border_color = Color(0.3, 0.42, 0.4)
	sb.set_border_width_all(1); sb.set_corner_radius_all(4)
	sb.content_margin_left = 10; sb.content_margin_right = 10; sb.content_margin_top = 6; sb.content_margin_bottom = 8
	add_theme_stylebox_override("panel", sb)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 3)
	add_child(v)
	var top := HBoxContainer.new()
	v.add_child(top)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(56, 36)
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	top.add_child(portrait)
	title = Label.new()
	title.add_theme_font_size_override("font_size", 16)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.clip_text = true
	top.add_child(title)
	pin_btn = hud._button("Pin", func(): _toggle_pin(), Vector2(46, 22))
	pin_btn.tooltip_text = "Keep showing this object after the selection changes"
	top.add_child(pin_btn)
	close_btn = hud._button("x", func(): closed_sig = _sig; pinned = null, Vector2(26, 22))
	close_btn.tooltip_text = "Hide the inspector until you select something else"
	top.add_child(close_btn)
	sub = Label.new()
	sub.add_theme_font_size_override("font_size", 12)
	sub.add_theme_color_override("font_color", Color(0.65, 0.75, 0.72))
	v.add_child(sub)
	hp_bar = Control.new()
	hp_bar.custom_minimum_size = Vector2(W - 20, 12)
	hp_bar.draw.connect(_draw_hp)
	v.add_child(hp_bar)
	body = RichTextLabel.new()
	body.bbcode_enabled = true
	body.fit_content = true
	body.scroll_active = false
	body.custom_minimum_size = Vector2(W - 20, 0)
	body.add_theme_font_size_override("normal_font_size", 12)
	body.add_theme_font_size_override("bold_font_size", 12)
	body.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(body)
	roster = VBoxContainer.new()
	roster.add_theme_constant_override("separation", 2)
	v.add_child(roster)
	custom_minimum_size = Vector2(W, 0)


func _toggle_pin() -> void:
	if pinned: pinned = null
	elif subject and not subject.dead: pinned = subject
	pin_btn.text = "Unpin" if pinned else "Pin"


func _draw_hp() -> void:
	var r := Rect2(Vector2.ZERO, hp_bar.size)
	hp_bar.draw_rect(r, Color(0, 0, 0, 0.6))
	var hp := 0.0; var mx := 0.0
	for u in ([subject] if subject else group):
		if u and is_instance_valid(u) and not u.dead: hp += u.hp; mx += u.def.hp
	if mx <= 0.0: return
	var f := hp / mx
	var col := Color(0.3, 0.9, 0.4) if f > 0.6 else (Color(0.95, 0.8, 0.2) if f > 0.3 else Color(0.95, 0.25, 0.2))
	hp_bar.draw_rect(Rect2(r.position, Vector2(r.size.x * f, r.size.y)), col)
	var t := "%d / %d" % [int(hp), int(mx)]
	hp_bar.draw_string(ThemeDB.fallback_font, Vector2(6, 10), t, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0, 0, 0, 0.9))


func _process(dt: float) -> void:
	var sel: Array = commander.live_selection()
	var sb: Building = commander.sel_building
	var objs: Array = sel.duplicate()
	if objs.is_empty() and sb and is_instance_valid(sb) and not sb.dead: objs = [sb]
	if pinned and (not is_instance_valid(pinned) or pinned.dead):
		pinned = null; pin_btn.text = "Pin"
	if pinned: objs = [pinned]
	var sig := ",".join(objs.map(func(u): return str(u.uid)))
	if sig != closed_sig: closed_sig = ""
	visible = not objs.is_empty() and closed_sig == ""
	if not visible:
		_sig = sig
		return
	_t -= dt
	if sig == _sig and _t > 0.0:
		hp_bar.queue_redraw()
		return
	_t = 0.25
	if sig != _sig: _rebuild_roster(objs)
	_sig = sig
	portrait.texture = _icon_for(objs[0])
	portrait.visible = portrait.texture != null
	if objs.size() == 1:
		subject = objs[0]; group = []
		_describe(subject)
	else:
		subject = null; group = objs
		_describe_group(objs)
	hp_bar.queue_redraw()
	size = Vector2(W, 0)      # shrink to content; HUD anchors the bottom edge


# ------------------------------------------------------------------ text helpers
func _h(t: String) -> String:
	return "[color=#8fd3b4][b]%s[/b][/color]\n" % t


func _kv(k: String, v: String) -> String:
	return "[color=#9aa7a3]%s:[/color] %s\n" % [k, v]


func _owner(u: Unit) -> String:
	var nat: String = battle.nation_of(u.team) if u.team >= 0 else ""
	var who := "You" if u.team == commander.team else ("Enemy" if u.team >= 0 else "Neutral")
	return "%s - %s%s" % [who, UnitDefs.team_name(u.team) if u.team >= 0 else "", (" (%s)" % Nations.name_of(nat)) if nat != "" else ""]


const TARGET_NAMES := {"ground": "ground", "heli": "helicopters", "jet": "jets"}


func _weapons(u: Unit) -> String:
	var out := ""
	for w in u.def.get("weapons", []):
		var tg: Array = w.get("targets", []).map(func(t): return TARGET_NAMES.get(t, t))
		var mr: float = float(w.get("min_range", 0.0))
		out += "  %s  [color=#c9d4cf]range %d m%s, dmg %d%s, reload %.1f s[/color]  vs %s\n" % [
			battle.lbl(u.team, "w:" + str(w.id), str(w.id).replace("_", " ")), int(w.range), (" (min %d)" % int(mr)) if mr > 0.0 else "", int(w.damage),
			(" splash %.0f m" % float(w.splash)) if float(w.get("splash", 0.0)) > 0.0 else "",
			float(w.reload) * Veterancy.mult(u, "reload"), ", ".join(tg)]
	return out


func _state(u: Unit) -> String:
	if u.dead: return "destroyed"
	if u.para_alt > 0.0: return "parachuting in"
	match u.state:
		Unit.S.IDLE: return ("engaging %s" % u.target.def.name) if u.target and not u.target.dead else "idle"
		Unit.S.MOVE: return "moving"
		Unit.S.ATTACK: return "attacking %s" % (u.target.def.name if u.target and not u.target.dead else "target")
		Unit.S.ATTACK_MOVE: return "attack-moving"
		Unit.S.GUARD: return "guarding"
		Unit.S.FORCE_GROUND: return "force-firing"
		Unit.S.RETURN: return "returning to pad"
		Unit.S.LANDED: return "parked on pad" + (" - repairing" if u.hp < u.def.hp else "") + (" - rearming" if u.w_ammo.any(func(a): return a == 0) else "")
		Unit.S.BUILD:
			var s: Variant = u.site
			if s and is_instance_valid(s) and not s.dead:
				return ("building %s (%d%%)" % [s.def.name, int(s.progress * 100.0)]) if not s.built else "repairing %s" % s.def.name
			return "building"
		Unit.S.HAUL: return "hauling supplies" + (" ($%d aboard)" % u.cargo if u.cargo > 0 else "")
	return "-"


# ------------------------------------------------------------------ single unit
func _describe(u: Unit) -> void:
	if u is Building:
		_describe_building(u as Building)
		return
	title.text = u.def.name
	var cls := str(u.def.get("category", "Infantry" if u.def.get("visual") == "infantry" else u.domain.capitalize()))
	sub.text = "%s  |  %s" % [cls, _owner(u)]
	var t := ""
	if u.def.has("role"): t += "[color=#c9d4cf]%s[/color]\n" % u.def.role
	t += _kv("Status", _state(u))
	if Nations.is_placeholder(battle.nation_of(u.team), u.kind): t += "[color=#d9b36c]Shared placeholder model until this nation's art pack[/color]\n"
	if u.def.has("weapons") and not u.def.weapons.is_empty():
		t += _h("Weapons") + _weapons(u)
	t += _kv("Armour", UnitDefs.armor_of(u.def)) + _kv("Speed / sight", "%d m/s, %d m" % [int(u.def.speed), int(u.def.sight)])
	if u.def.has("heal"):
		var h: Dictionary = u.def.heal
		t += _kv("Support", "heals %s within %d m (%d%%/s)" % [", ".join(h.targets), int(h.radius), int(float(h.per_s) * 100.0)])
	if u.domain == "jet" and u.def.has("weapons"):
		t += _kv("Ammunition", ", ".join(range(u.w_ammo.size()).map(func(i): return "%s %d" % [str(u.def.weapons[i].id), u.w_ammo[i]])))
	if u.is_transport():
		var cap: int = int(u.def.transport.capacity)
		t += _h("Passengers %d / %d" % [u.passengers.size(), cap])
		if u.passengers.is_empty(): t += "  empty - select infantry and click this vehicle to board\n"
		for p in u.passengers: t += "  %s  %d%%\n" % [p.def.name, int(p.hp / p.def.hp * 100.0)]
	if u.domain in ["jet", "heli"] and u.home != Vector3.ZERO and not u.def.get("hauler", false):
		t += _kv("Airfield pad", "assigned (R returns, repairs and rearms there)")
	t += _upgrade_lines(u)
	if Veterancy.eligible(u):
		t += _h("Veterancy: %s" % Veterancy.RANKS[u.vet_rank])
		var nx := Veterancy.next_xp(u)
		t += "  XP %d%s\n" % [int(u.vet_xp), (" / %d to %s" % [int(nx), Veterancy.RANKS[u.vet_rank + 1]]) if nx > 0.0 else " (top rank)"]
		var bl := Veterancy.bonus_lines(u)
		if not bl.is_empty(): t += "  Bonuses: " + ", ".join(bl) + "\n"
	body.text = t.strip_edges()


## Upgrades that can affect this unit: Installed / Researching / Available / Locked (with the reason).
func _upgrade_lines(u: Unit) -> String:
	if u.team < 0 or u.team > 1: return ""
	var lines := ""
	for id in Upgrades.DEFS:
		if not Upgrades.applies(id, u): continue
		var d: Dictionary = Upgrades.DEFS[id]
		var st := ""
		if battle.has_upgrade(u.team, id): st = "[color=#7fe08f]Installed[/color]"
		else:
			var rb: Building = battle.researching_at(u.team, id)
			if rb: st = "Researching %d%%" % int(100.0 * (1.0 - rb.research_left / float(d.time)))
			else:
				var at: Array = battle.structures(u.team, d.at)
				if at.is_empty(): st = "[color=#d9b36c]Locked[/color] - needs a %s" % battle.bname(u.team, d.at)
				else:
					var why: String = battle.research_problem(at[0], id)
					st = "Available at the %s ($%d)" % [battle.bname(u.team, d.at), int(d.cost)] if why == "" or why == "Not enough cash" or why == "This building is researching" \
						else "[color=#d9b36c]Locked[/color] - %s" % why
		lines += "  %s: %s\n" % [battle.lbl(u.team, id, d.name), st]
	var pl: String = battle.plan[u.team]
	if pl != "" and (u.domain == "ground" or pl == "recon"):
		lines += "  Battle plan %s: %s\n" % [battle.lbl(u.team, pl, Upgrades.PLANS[pl].name), Upgrades.PLANS[pl].desc]
	return (_h("Upgrades") + lines) if lines != "" else ""


# ------------------------------------------------------------------ structures
func _describe_building(b: Building) -> void:
	title.text = b.def.name
	sub.text = "Structure  |  %s" % _owner(b)
	var t := _h("Overview") + "[color=#c9d4cf]%s[/color]\n" % b.bdef.desc
	var pw: int = int(b.bdef.power)
	var powered: bool = battle.power_ok(b.team) if b.team >= 0 else true
	var st := ""
	if not b.built: st = "under construction %d%%" % int(b.progress * 100.0)
	elif b.repairing: st = "operational - repairing" + ((" (paused: %s)" % b.repair_blocked) if b.repair_blocked != "" else "")
	else: st = "operational"
	if b.built and pw < 0 and not powered: st += " - LOW POWER (half speed)"
	t += _kv("Status", st)
	if pw != 0: t += _kv("Power", "%+d  (base: %d used / %d generated)" % [pw, battle.power_use(b.team), battle.power_gen(b.team)])
	var req: Array = b.bdef.get("requires", [])
	if not req.is_empty(): t += _kv("Requires", ", ".join(req.map(func(x): return battle.bname(b.team, x))))
	if not b.def.weapons.is_empty(): t += _h("Weapons") + _weapons(b)
	# production
	var plist: Array = b.produces_list()
	if b.built and not plist.is_empty():
		t += _h("Production")
		if b.prod_queue.is_empty(): t += "  idle - %d unit types available\n" % plist.size()
		else:
			var rate: float = 1.0 if powered else BuildingDefs.LOW_POWER_RATE
			var total := float(BuildingDefs.UNIT_COST[b.prod_queue[0]][1])
			var done := clampf(1.0 - b.prod_left / total, 0.0, 1.0)
			t += "  %s  %d%%  ETA %d s%s\n" % [UnitDefs.def_of(b.prod_queue[0]).name, int(done * 100.0), int(ceil(b.prod_left / rate)), "" if powered else " (low power)"]
			if b.prod_queue.size() > 1:
				var rest := {}
				for i in range(1, b.prod_queue.size()): rest[b.prod_queue[i]] = int(rest.get(b.prod_queue[i], 0)) + 1
				t += "  queued: " + ", ".join(rest.keys().map(func(k): return "%d x %s" % [rest[k], UnitDefs.def_of(k).name])) + "\n"
		if b.has_rally: t += _kv("Rally point", "set (%d m away)" % int(b.flat_dist(b.rally)))
	elif b.built and not b.bdef.produces.is_empty() and plist.is_empty():
		t += _kv("Production", "nothing to build here yet for %s" % Nations.name_of(battle.nation_of(b.team)))
	# services: what this structure does for the base right now
	var svc := ""
	if b.bkind == "command_center":
		var bl: Array = battle.units.filter(func(u): return u.team == b.team and not u.dead and u.def.get("builder", false))
		var busy: int = bl.filter(func(u): return u.state == Unit.S.BUILD).size()
		svc += _kv("Builders", "%d (%d working, %d available) - %d structure types to build" % [bl.size(), busy, bl.size() - busy, BuildingDefs.BUILD_MENU.size()])
	if b.bdef.get("repair", false): svc += _kv("Repair bay", "servicing a vehicle" if b.servicing else "free - send damaged vehicles here")
	if b.bkind == "radar": svc += _kv("Radar", "online" if battle.radar_online(b.team) else "offline (low power)")
	if b.bdef.has("drop"): svc += _kv("Next supply drop", ("%d s" % int(b.drop_t)) if powered else "paused (low power)")
	if b.bkind == "supply_depot":
		var hauling := 0
		var hname := ""
		for u in battle.units:
			if u.team == b.team and not u.dead and u.def.get("hauler", false):
				hauling += 1; hname = u.def.name.split(" (")[0]
		var stock := 0
		for pl in battle.piles: stock += int(pl.cash)
		svc += _kv("Supply", "%d %s haulers, piles hold $%d, delivered $%d" % [hauling, hname if hname != "" else "supply", stock, battle.income[b.team] - battle.drop_income[b.team] - battle.derrick_income[b.team]])
	if svc != "": t += _h("Services") + svc
	# airfield pads
	if not b.pads.is_empty():
		t += _h("Pads %d / %d in use" % [b.pads.filter(func(p): return p.uid >= 0).size(), b.pads.size()])
		for i in b.pads.size():
			var p: Dictionary = b.pads[i]
			var a: Unit = battle.by_id.get(p.uid) if p.uid >= 0 else null
			if a and not a.dead: t += "  Pad %d: %s - %s\n" % [i + 1, a.def.name, _state(a)]
			else: t += "  Pad %d: free\n" % (i + 1)
	var res := ""
	for id in Upgrades.DEFS:
		if Upgrades.DEFS[id].at != b.bkind: continue
		var d: Dictionary = Upgrades.DEFS[id]
		var rst := ""
		if battle.has_upgrade(b.team, id): rst = "Installed"
		elif b.research_id == id: rst = "Researching %d%%, %d s left" % [int(100.0 * (1.0 - b.research_left / float(d.time))), int(ceil(b.research_left))]
		else:
			var why: String = battle.research_problem(b, id)
			rst = ("Available ($%d, %d s)" % [int(d.cost), int(d.time)]) if why == "" else "Locked - %s" % why
		res += "  %s: %s\n    %s\n" % [battle.lbl(b.team, id, d.name), rst, d.desc]
	if res != "": t += _h("Upgrades") + res
	if b.bkind == "command_center":
		var tm: int = b.team
		var cur: String = battle.plan[tm]
		var pend: String = battle.plan_pending[tm]
		var ptxt: String = battle.lbl(tm, cur, Upgrades.PLANS[cur].name) if cur != "" else "none"
		if pend != "": ptxt += "  (switching to %s in %d s)" % [battle.lbl(tm, pend, Upgrades.PLANS[pend].name), int(ceil(battle.plan_switch_t[tm] - battle.sim_time))]
		var why3: String = battle.plan_problem(tm, "assault")
		t += _kv("Battle plan", ptxt + (("  - " + why3) if why3.begins_with("Requires") else ""))
	body.text = t.strip_edges()


# ------------------------------------------------------------------ group
func _describe_group(objs: Array) -> void:
	title.text = "%d selected" % objs.size()
	var cats := {}
	for u in objs: cats[u.def.get("category", u.domain.capitalize())] = true
	sub.text = ", ".join(cats.keys())
	var t := ""
	var vets := objs.filter(func(u): return u.vet_rank > 0).size()
	if vets > 0: t += _kv("Veterans", "%d" % vets)
	var tr := objs.filter(func(u): return u.is_transport())
	if not tr.is_empty(): t += _kv("Transports", "%d (D unloads)" % tr.size())
	t += "[color=#9aa7a3]Click a row to inspect that unit type.[/color]"
	body.text = t


func _rebuild_roster(objs: Array) -> void:
	for c in roster.get_children(): c.queue_free()
	if objs.size() <= 1: return
	var by := {}
	for u in objs:
		if not by.has(u.kind): by[u.kind] = []
		by[u.kind].append(u)
	var n := 0
	for k in by:
		var arr: Array = by[k]
		var b: Button = hud._button("%d x %s" % [arr.size(), arr[0].def.name], func(): commander._set_selection(arr), Vector2(W - 20, 24))
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.tooltip_text = "Select only these units"
		roster.add_child(b)
		n += 1
		if n >= 8: break


## Portrait: the unit's icon (nation-specific when it has one), the structure's build icon otherwise.
func _icon_for(u: Unit) -> Texture2D:
	var path := ""
	if u is Building: path = str(UsArt.building((u as Building).bdef.art).get("icon", ""))
	else:
		path = str(u.def.get("icon", ""))
		if path == "" and u.def.get("visual") == "infantry": path = str(UsArt.infantry(u.def.get("art", "")).get("icon", ""))
		elif path == "" and u.def.has("art"): path = str(UsArt.vehicle(u.def.art).get("icon", ""))
	if path == "" or not ResourceLoader.exists(path): return null
	if not _icons.has(path): _icons[path] = load(path)
	return _icons[path]

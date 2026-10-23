# Steel Accord - main menu. Every button here works; features that don't exist yet are not shown.
extends Control

var content: VBoxContainer
var side: PanelContainer
var ui_root: Control   # menu panels; scaled with the screen height like the in-game HUD (1440p x1.33, 4K x2)


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	# automated runs (tests / diagnostics / evidence) skip the menu
	for a in OS.get_cmdline_user_args():
		if a in ["test", "airdiag", "evidence", "uishots", "vischeck", "basetest", "baseshots", "pilotshots", "m1shots", "maptest", "mapshots"] or a.begins_with("test"):
			Game.call_deferred("start_match")
			return
	var bg := TextureRect.new()
	bg.texture = load("res://assets/ui/menu_bg.png")
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.35)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(shade)
	ui_root = Control.new()
	ui_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(ui_root)
	var left := VBoxContainer.new()
	left.position = Vector2(70, 80)
	left.add_theme_constant_override("separation", 12)
	ui_root.add_child(left)
	left.add_child(UIKit.label("STEEL ACCORD", 64, Color(0.95, 0.97, 0.95)))
	left.add_child(UIKit.label("Development build B1.7 - USA and Iran", 16, UIKit.ACCENT))
	var spacer := Control.new(); spacer.custom_minimum_size = Vector2(0, 30)
	left.add_child(spacer)
	left.add_child(UIKit.button("Skirmish", func(): _show_skirmish()))
	left.add_child(UIKit.button("Options", func(): _show_options()))
	left.add_child(UIKit.button("Controls", func(): _show_controls()))
	left.add_child(UIKit.button("Credits", func(): _show_credits()))
	left.add_child(UIKit.button("Exit", func(): Game.quit()))
	side = UIKit.panel(Vector2(520, 420))
	side.position = Vector2(500, 170)
	ui_root.add_child(side)
	content = VBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	side.add_child(content)
	if not Game.last_result.is_empty():
		_show_last_result()
	else:
		_show_skirmish()
	if "menushot" in OS.get_cmdline_user_args():
		for i in 8: await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var out := "/tmp/sa_menu.png"
		for a in OS.get_cmdline_user_args():
			if a.begins_with("out="): out = a.substr(4)
		get_viewport().get_texture().get_image().save_png(out)
		get_tree().quit()


func _process(_dt: float) -> void:
	if ui_root == null: return
	var fixed: float = float(Game.settings.get("ui_scale", 0.0))
	var k: float = fixed if fixed > 0.0 else maxf(1.0, get_viewport_rect().size.y / 1080.0)
	ui_root.scale = Vector2(k, k)


func _clear() -> void:
	for c in content.get_children(): c.queue_free()


func _show_skirmish() -> void:
	_clear()
	side.position = Vector2(560, 230)
	content.add_child(UIKit.label("SKIRMISH SETUP", 22, UIKit.ACCENT))
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 26)
	content.add_child(cols)
	var leftc := VBoxContainer.new(); leftc.add_theme_constant_override("separation", 10)
	var rightc := VBoxContainer.new(); rightc.add_theme_constant_override("separation", 8)
	cols.add_child(leftc); cols.add_child(rightc)
	# ---- players: slot, army (nation), colour, team, controller
	leftc.add_child(UIKit.label("PLAYERS", 15, Color(0.75, 0.82, 0.78)))
	var grid := GridContainer.new()
	grid.columns = 5
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 6)
	leftc.add_child(grid)
	for h in ["Slot", "Army", "Colour", "Team", "Control"]:
		grid.add_child(UIKit.label(h, 12, Color(0.6, 0.66, 0.63)))
	var nat_names: Array = Nations.ORDER.map(func(n): return Nations.name_of(n))
	var col_names: Array = UnitDefs.TEAM_NAMES.duplicate()
	for t in 2:
		var tt := t
		grid.add_child(UIKit.label("Player %d" % (t + 1), 15))
		var on := UIKit.option(nat_names, Nations.name_of(str(Game.settings.get("nation%d" % t, "usa"))), func(x):
			Game.settings["nation%d" % tt] = Nations.ORDER[nat_names.find(x)]
			Game.save())
		on.custom_minimum_size = Vector2(150, 32)
		grid.add_child(on)
		var oc := UIKit.option(col_names, col_names[UnitDefs.team_color_index(t)], func(x):
			var ci: int = col_names.find(x)
			if ci == UnitDefs.team_color_index(1 - tt): Game.settings["color%d" % (1 - tt)] = UnitDefs.team_color_index(tt)   # swap, never equal
			Game.settings["color%d" % tt] = ci
			Game.save()
			_show_skirmish())
		oc.custom_minimum_size = Vector2(100, 32)
		var sw := ColorRect.new(); sw.color = UnitDefs.team_color(t); sw.custom_minimum_size = Vector2(14, 14)
		var cb := HBoxContainer.new(); cb.add_child(sw); cb.add_child(oc)
		grid.add_child(cb)
		grid.add_child(UIKit.label("Team %d" % (t + 1), 15))
		if t == 0:
			grid.add_child(UIKit.label("You", 15, UIKit.ACCENT))
		else:
			var od := UIKit.option(["Easy", "Normal", "Hard"], Game.settings.difficulty, func(x):
				Game.settings.difficulty = x
				Game.save())
			od.custom_minimum_size = Vector2(110, 32)
			od.tooltip_text = "Computer opponent.\nEasy: attacks late with a big wave; its weapons deal 80% damage.\nNormal: 100%.\nHard: thinks faster, attacks early; its weapons deal 115% damage."
			grid.add_child(od)
	leftc.add_child(UIKit.label("Two players, one vs one (more slots and allied teams arrive with multiplayer).", 11, Color(0.55, 0.6, 0.58)))
	# ---- match settings
	leftc.add_child(UIKit.label("MATCH", 15, Color(0.75, 0.82, 0.78)))
	var cash_opts := {"$5,000": 5000, "$10,000": 10000, "$20,000": 20000}
	var cur_cash := "$10,000"
	for k in cash_opts:
		if int(cash_opts[k]) == int(Game.settings.get("start_cash", 10000)): cur_cash = k
	leftc.add_child(_row("Starting cash", UIKit.option(cash_opts.keys(), cur_cash, func(x):
		Game.settings["start_cash"] = cash_opts[x]
		Game.save())))
	var spd := {"Slow (75%)": 0.75, "Normal": 1.0, "Fast (125%)": 1.25}
	var cur_spd := "Normal"
	for k in spd:
		if is_equal_approx(float(spd[k]), float(Game.settings.get("game_speed", 1.0))): cur_spd = k
	leftc.add_child(_row("Game speed", UIKit.option(spd.keys(), cur_spd, func(x):
		Game.settings["game_speed"] = spd[x]
		Game.save())))
	leftc.add_child(_row("Victory", UIKit.label("Destroy every enemy structure and unit", 14)))
	leftc.add_child(_row("Start", UIKit.label("Command Center + one builder", 14)))
	# ---- map: choice, preview, facts
	rightc.add_child(UIKit.label("MAP", 15, Color(0.75, 0.82, 0.78)))
	var maps: Array = Game.MAPS.keys().filter(func(m): return m == "proving_ground" or TerrainMap.exists(m))
	var labels: Array = maps.map(func(m): return Game.MAPS[m])
	if not (Game.settings.get("map", "") in maps): Game.settings.map = "proving_ground"
	var om := UIKit.option(labels, Game.MAPS[Game.settings.map], func(x):
		Game.settings.map = maps[labels.find(x)]
		Game.save()
		_show_skirmish())
	om.custom_minimum_size = Vector2(300, 34)
	rightc.add_child(om)
	var prev := TextureRect.new()
	var pp := "res://maps/%s/preview.png" % Game.settings.map
	if ResourceLoader.exists(pp): prev.texture = load(pp)
	prev.custom_minimum_size = Vector2(300, 300)
	prev.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	prev.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	rightc.add_child(prev)
	rightc.add_child(UIKit.label(MAP_FACTS.get(Game.settings.map, ""), 12, Color(0.7, 0.76, 0.73)))
	# ---- launch / back
	var bar := HBoxContainer.new()
	bar.add_theme_constant_override("separation", 14)
	bar.add_child(UIKit.button("Start Match", func(): Game.start_match(), Vector2(240, 46), 19))
	bar.add_child(UIKit.button("Back", func(): _show_home(), Vector2(140, 46), 17))
	content.add_child(bar)


const MAP_FACTS := {
	"proving_ground": "600 x 600 m flat test range. 2 players. 5 supply piles.\nBlue/red dots: starts. Yellow: supply piles.",
	"zagros_basin": "1200 x 1200 m foothills and dry basin. 2 players.\n7 supply piles (yellow), 4 oil derricks (purple),\n3 passes between the bases. Blue/red: starts.",
}


func _row(name: String, ctl: Control) -> HBoxContainer:
	var r := HBoxContainer.new()
	var l := UIKit.label(name, 14)
	l.custom_minimum_size = Vector2(120, 0)
	r.add_child(l); r.add_child(ctl)
	return r


func _show_home() -> void:
	_clear()
	side.position = Vector2(500, 170)
	content.add_child(UIKit.label("STEEL ACCORD", 22, UIKit.ACCENT))
	content.add_child(UIKit.label("Choose Skirmish to set up a match against the computer.", 14))


func _show_options() -> void:
	_clear()
	side.position = Vector2(500, 170)
	content.add_child(UIKit.options_box())


func _show_controls() -> void:
	_clear()
	side.position = Vector2(500, 170)
	content.add_child(UIKit.label("CONTROLS", 22, UIKit.ACCENT))
	for t in [
		"Left click unit: select     Left drag: box select     Double-click: all of that type",
		"Classic mouse: left click ground = move, left click enemy = attack, right click = deselect",
		"Right drag: scroll map     Wheel: zoom     Middle drag: rotate / tilt",
		"Command bar (bottom): Attack-Move, Guard, Force Fire, Waypoints, Stop, Scatter, Return, Select All",
		"Keys: A attack-move  G guard  F force fire  W waypoints  S stop  X scatter  R return to pad",
		"Ctrl+click force fire   Alt+click waypoint   Ctrl+A select all   Ctrl+1..9 / 1..9 groups",
		"Base: select the Dozer, pick a structure on the build panel, click the map to place it",
		"Select a structure to queue units (click the queue to cancel); click the map to set its rally point",
		"CH-47s from the Supply Depot haul cash from supply piles automatically. Keep Power above use.",
		"Support powers (right): click a power, then click the target on the map",
		"Esc: cancel / deselect / pause menu     F10: pause menu     F1: controls overlay",
	]:
		var l := UIKit.label(t, 13)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD
		l.custom_minimum_size = Vector2(500, 0)
		content.add_child(l)


func _show_credits() -> void:
	_clear()
	side.position = Vector2(500, 170)
	content.add_child(UIKit.label("CREDITS", 22, UIKit.ACCENT))
	for t in [
		"Steel Accord - original RTS by Mohammed Aldaraji (EzioDEVio).",
		"Design, programming and procedural art: Claude (Anthropic) as development lead.",
		"Engine: Godot 4.5 (MIT licence). 3D art scripted in Blender (bpy).",
		"U.S. aircraft, vehicle, structure and personnel concept art: AI-generated, supplied by the client (development use; release review pending).",
		"Sound effects: Pixabay contributors (Pixabay Content License), selected by the client; trimmed and mixed for the game.",
		"Not affiliated with or endorsed by Electronic Arts. No Command & Conquer assets are used.",
	]:
		var l := UIKit.label(t, 13)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD
		l.custom_minimum_size = Vector2(500, 0)
		content.add_child(l)


func _show_last_result() -> void:
	_clear()
	side.position = Vector2(500, 170)
	var r := Game.last_result
	content.add_child(UIKit.label("LAST MATCH: " + str(r.get("result", "")), 22, UIKit.ACCENT))
	content.add_child(UIKit.label("Duration %s   Enemy destroyed %d   Units lost %d" % [r.get("time", "-"), r.get("kills", 0), r.get("losses", 0)], 15))
	var again := func():
		Game.last_result = {}
		_show_skirmish()
	content.add_child(UIKit.button("New Skirmish", again))

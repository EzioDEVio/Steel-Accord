# Steel Accord - main menu. Every button here works; features that don't exist yet are not shown.
extends Control

var content: VBoxContainer
var side: PanelContainer


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
	var left := VBoxContainer.new()
	left.position = Vector2(70, 80)
	left.add_theme_constant_override("separation", 12)
	add_child(left)
	left.add_child(UIKit.label("STEEL ACCORD", 64, Color(0.95, 0.97, 0.95)))
	left.add_child(UIKit.label("Development build B1.2 - base-building prototype", 16, UIKit.ACCENT))
	var spacer := Control.new(); spacer.custom_minimum_size = Vector2(0, 30)
	left.add_child(spacer)
	left.add_child(UIKit.button("Skirmish", func(): _show_skirmish()))
	left.add_child(UIKit.button("Options", func(): _show_options()))
	left.add_child(UIKit.button("Controls", func(): _show_controls()))
	left.add_child(UIKit.button("Credits", func(): _show_credits()))
	left.add_child(UIKit.button("Exit", func(): Game.quit()))
	side = UIKit.panel(Vector2(520, 420))
	side.position = Vector2(500, 170)
	add_child(side)
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
		get_viewport().get_texture().get_image().save_png("/home/claude/sa/ui/menu.png")
		get_tree().quit()


func _clear() -> void:
	for c in content.get_children(): c.queue_free()


func _show_skirmish() -> void:
	_clear()
	content.add_child(UIKit.label("SKIRMISH", 22, UIKit.ACCENT))
	var maps: Array = Game.MAPS.keys().filter(func(m): return m == "proving_ground" or TerrainMap.exists(m))
	var labels: Array = maps.map(func(m): return Game.MAPS[m])
	if not (Game.settings.get("map", "") in maps): Game.settings.map = "proving_ground"
	var rm := HBoxContainer.new()
	rm.add_child(UIKit.label("Map  ", 15))
	var om := UIKit.option(labels, Game.MAPS[Game.settings.map], func(x):
		Game.settings.map = maps[labels.find(x)]
		Game.save())
	om.custom_minimum_size = Vector2(380, 34)
	rm.add_child(om)
	content.add_child(rm)
	var nat_names: Array = Nations.ORDER.map(func(n): return Nations.name_of(n))
	for t in 2:
		var rn := HBoxContainer.new()
		rn.add_child(UIKit.label(("You (Blue)  " if t == 0 else "AI (Red)    "), 15))
		var key := "nation%d" % t
		var tt := t
		rn.add_child(UIKit.option(nat_names, Nations.name_of(str(Game.settings.get(key, "usa"))), func(x):
			Game.settings["nation%d" % tt] = Nations.ORDER[nat_names.find(x)]
			Game.save()))
		content.add_child(rn)
	content.add_child(UIKit.label("Start: Command Center, one Dozer, $10,000. Destroy every enemy structure and unit.", 13))
	content.add_child(UIKit.label("Iran: own infantry (incl. IRGC Special Forces); vehicles are shared placeholders until the Iran art pack.", 12, Color(0.6, 0.66, 0.63)))
	var r := HBoxContainer.new()
	r.add_child(UIKit.label("AI difficulty  ", 15))
	var set_diff := func(x):
		Game.settings.difficulty = x
		Game.save()
	r.add_child(UIKit.option(["Easy", "Normal", "Hard"], Game.settings.difficulty, set_diff))
	content.add_child(r)
	content.add_child(UIKit.label("Easy: AI attacks late with a big wave.  Hard: thinks faster, attacks early.", 12, Color(0.6, 0.66, 0.63)))
	var sp := Control.new(); sp.custom_minimum_size = Vector2(0, 12)
	content.add_child(sp)
	content.add_child(UIKit.button("Start Match", func(): Game.start_match(), Vector2(260, 46), 19))


func _show_options() -> void:
	_clear()
	content.add_child(UIKit.options_box())


func _show_controls() -> void:
	_clear()
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
	var r := Game.last_result
	content.add_child(UIKit.label("LAST MATCH: " + str(r.get("result", "")), 22, UIKit.ACCENT))
	content.add_child(UIKit.label("Duration %s   Enemy destroyed %d   Units lost %d" % [r.get("time", "-"), r.get("kills", 0), r.get("losses", 0)], 15))
	var again := func():
		Game.last_result = {}
		_show_skirmish()
	content.add_child(UIKit.button("New Skirmish", again))

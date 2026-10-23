# Steel Accord - in-match pause menu (Esc with nothing selected, F10, or the Menu button) and end-of-match screen.
# Pauses the whole simulation while open. All buttons are functional.
class_name PauseMenu
extends CanvasLayer

var battle: Node
var root: Control
var box: VBoxContainer
var end_mode := false


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(root)
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.5)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)
	var p: PanelContainer = UIKit.panel(Vector2(600, 0))
	center.add_child(p)
	box = VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	p.add_child(box)
	visible = false


func _clear() -> void:
	for c in box.get_children(): c.queue_free()


func open_pause() -> void:
	if end_mode: return
	_clear()
	box.add_child(UIKit.label("PAUSED", 28, UIKit.ACCENT))
	box.add_child(UIKit.button("Resume", func(): close()))
	if battle.scenario == "base":
		box.add_child(UIKit.button("Save Game", func(): _save()))
		box.add_child(UIKit.button("Load Game", func(): _load_list()))
	box.add_child(UIKit.button("Restart Match", func(): Game.restart_match()))
	box.add_child(UIKit.button("Options", func(): _options()))
	box.add_child(UIKit.button("Main Menu", func(): Game.main_menu()))
	box.add_child(UIKit.button("Exit to Desktop", func(): Game.quit()))
	visible = true
	get_tree().paused = true


func _save() -> void:
	var name := "save_" + Time.get_datetime_string_from_system(false, false).replace(":", "").replace("-", "").replace("T", "_")
	var ok := SaveGame.write("%s/%s.sav" % [SaveGame.DIR, name], SaveGame.capture(battle))
	_clear()
	box.add_child(UIKit.label("Game saved" if ok else "Could not write the save file", 22, UIKit.ACCENT if ok else Color(1, 0.4, 0.35)))
	box.add_child(UIKit.label(name, 13))
	box.add_child(UIKit.button("Back", func(): open_pause()))


func _load_list() -> void:
	_clear()
	box.add_child(UIKit.label("LOAD GAME", 24, UIKit.ACCENT))
	var saves := SaveGame.list_saves()
	if saves.is_empty(): box.add_child(UIKit.label("No saved games yet.", 14))
	for sv in saves.slice(0, 8):
		var path: String = sv.path
		var b := UIKit.button(SaveGame.describe(sv.meta), func(): SaveGame.load_into_new_match(SaveGame.read(path)))
		b.custom_minimum_size = Vector2(560, 34)
		b.add_theme_font_size_override("font_size", 12)
		box.add_child(b)
	box.add_child(UIKit.button("Back", func(): open_pause()))


func _options() -> void:
	_clear()
	box.add_child(UIKit.options_box(func(): battle.apply_settings()))
	box.add_child(UIKit.button("Back", func(): open_pause()))


func close() -> void:
	visible = false
	get_tree().paused = false


func open_end(victory: bool, stats: Dictionary) -> void:
	end_mode = true
	_clear()
	box.add_child(UIKit.label("VICTORY" if victory else "DEFEAT", 44, Color(0.5, 1.0, 0.6) if victory else Color(1.0, 0.4, 0.35)))
	box.add_child(UIKit.label("Match time %s" % stats.time, 16))
	box.add_child(UIKit.label("Enemy units destroyed: %d" % stats.kills, 16))
	box.add_child(UIKit.label("Your units lost: %d" % stats.losses, 16))
	var sp := Control.new(); sp.custom_minimum_size = Vector2(0, 8)
	box.add_child(sp)
	box.add_child(UIKit.button("Play Again", func(): Game.restart_match()))
	box.add_child(UIKit.button("Main Menu", func(): Game.main_menu()))
	box.add_child(UIKit.button("Exit to Desktop", func(): Game.quit()))
	visible = true


func _unhandled_key_input(e: InputEvent) -> void:
	if not visible or end_mode: return
	if e is InputEventKey and e.pressed and not e.echo and (e as InputEventKey).keycode in [KEY_ESCAPE, KEY_F10]:
		close()
		get_viewport().set_input_as_handled()

# Steel Accord - global game state (autoload "Game"): match settings chosen in the menus and player options.
extends Node

const DIFFICULTY := {
	"Easy": {"attack_after": 75.0, "damage_mult": 0.8},
	"Normal": {"attack_after": 35.0, "damage_mult": 1.0},
	"Hard": {"attack_after": 15.0, "damage_mult": 1.15},
}

var settings := {
	"difficulty": "Normal",
	"air_wing": true,
	"mouse_scheme": "classic",
	"edge_pan": true,
	"fullscreen": false,
	"cam_speed": 1.0,
	"map": "proving_ground",
	"nation0": "usa",
	"nation1": "iran",
}

## Skirmish maps offered in the menu (id -> label). Heightfield maps live in res://maps/<id>/.
const MAPS := {"proving_ground": "Proving Ground (flat test range, 600 m)", "zagros_basin": "Zagros Basin (foothills, oil derricks)"}
var last_result := {}


func _ready() -> void:
	_load()
	apply_display()


func apply_display() -> void:
	if DisplayServer.get_name() == "headless": return
	var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if settings.fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != mode:
		DisplayServer.window_set_mode(mode)


func save() -> void:
	var f := FileAccess.open("user://settings.json", FileAccess.WRITE)
	if f: f.store_string(JSON.stringify(settings))


func _load() -> void:
	if not FileAccess.file_exists("user://settings.json"): return
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string("user://settings.json"))
	if d is Dictionary:
		for k in d:
			if settings.has(k): settings[k] = d[k]


func start_match() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file("res://scenes/battle.tscn")


func restart_match() -> void:
	get_tree().paused = false
	get_tree().reload_current_scene()


func main_menu() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func quit() -> void:
	save()
	get_tree().quit()

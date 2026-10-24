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
	"ui_scale": 0.0,
	"sfx_volume": 0.8,
	"color0": 0,
	"color1": 1,
	"start_cash": 10000,
	"game_speed": 1.0,
	"graphics": "Medium",     # Low / Medium / High: shadows, ambient occlusion, anti-aliasing, 3D render scale
	"show_fps": false,
	"camera_shake": true,     # small camera shake on large explosions (never in automated tests)
	"strike_cam": "Picture-in-picture",   # Off / Picture-in-picture / Full screen: cinematic view of the player's bomber strikes
}

## Skirmish maps offered in the menu (id -> label). Heightfield maps live in res://maps/<id>/.
const MAPS := {"proving_ground": "Proving Ground (flat test range, 600 m)", "zagros_basin": "Zagros Basin (foothills, oil derricks)"}
var last_result := {}
var pending_load := {}      # a saved game the next battle rebuilds (SaveGame.load_into_new_match)


func _ready() -> void:
	_load()
	apply_display()


func apply_display() -> void:
	if DisplayServer.get_name() == "headless": return
	var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if settings.fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != mode:
		DisplayServer.window_set_mode(mode)
	apply_graphics()


## Graphics quality presets. High is the previous fixed setup (8192 px soft shadows, SSAO, glow, 2x MSAA).
const GRAPHICS := {
	"Low": {"shadow": 2048, "soft": 1, "ssao": false, "glow": false, "msaa": 0, "fxaa": true, "scale": 0.77, "shadow_dist": 160.0},
	"Medium": {"shadow": 4096, "soft": 2, "ssao": true, "glow": true, "msaa": 0, "fxaa": true, "scale": 1.0, "shadow_dist": 200.0},
	"High": {"shadow": 8192, "soft": 3, "ssao": true, "glow": true, "msaa": 1, "fxaa": true, "scale": 1.0, "shadow_dist": 220.0},
}
var world_env: Environment = null     # set by World.environment()
var world_sun: DirectionalLight3D = null


func apply_graphics() -> void:
	var g: Dictionary = GRAPHICS.get(str(settings.get("graphics", "Medium")), GRAPHICS.Medium)
	RenderingServer.directional_shadow_atlas_set_size(int(g.shadow), true)
	RenderingServer.directional_soft_shadow_filter_set_quality(int(g.soft))
	var vp := get_viewport()
	vp.msaa_3d = Viewport.MSAA_2X if int(g.msaa) == 1 else Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if g.fxaa else Viewport.SCREEN_SPACE_AA_DISABLED
	vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if float(g.scale) < 1.0 else Viewport.SCALING_3D_MODE_BILINEAR
	vp.scaling_3d_scale = float(g.scale)
	if world_env and is_instance_valid(world_env):
		world_env.ssao_enabled = g.ssao
		world_env.glow_enabled = g.glow
	if world_sun and is_instance_valid(world_sun):
		world_sun.directional_shadow_max_distance = float(g.shadow_dist)


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
	Engine.time_scale = 1.0
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func quit() -> void:
	save()
	get_tree().quit()

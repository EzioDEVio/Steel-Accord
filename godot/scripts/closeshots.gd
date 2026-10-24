# Steel Accord - close-up camera review (run with: -- closeshots nation1=iran noai out=/dir res=1920x1080).
# Lines up U.S. and Iranian units and structures on the Proving Ground and photographs each one with the deep-zoom
# close-up camera, to judge which models hold up at close range. Not part of gameplay.
extends Node

var battle: Node
var out := "user://test_output/sa_closeshots"
var res := Vector2i(1920, 1080)
const KINDS := ["rifleman", "ranger", "at4", "medic", "abrams", "bradley", "stryker", "hmmwv_50cal", "m777", "ah64",
	"ch47"]


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="): out = a.substr(4)
		if a.begins_with("res="):
			var p := a.substr(4).split("x")
			res = Vector2i(int(p[0]), int(p[1]))
	DirAccess.make_dir_recursive_absolute(out)
	_run()


func _wait(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().physics_frame


func _shot(tag: String) -> void:
	for i in 4: await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, tag])
	printerr("SHOT ", tag)


func _run() -> void:
	DisplayServer.window_set_size(res)
	get_tree().root.size = res
	RenderingServer.global_shader_parameter_set("fog_on", 0.0)
	await _wait(0.3)
	var cam: RTSCamera = battle.camera
	battle.hud.visible = false
	var shots: Array = []
	for t in 2:
		var z := 120.0 if t == 0 else 60.0
		var x := -100.0
		for k in KINDS:
			var kind: String = Nations.swap_unit(battle.nation_of(t), k)
			if UnitDefs.def_of(kind).is_empty(): continue
			var u: Unit = battle._spawn(kind, t, Vector3(x, 0, z), 0.6)
			shots.append([u, "%d_%s" % [t, kind]])
			x += 22.0
	for k in ["command_center", "war_factory"]:
		var b: Building = battle.add_structure(k, 0, Vector3(-60.0 + (0.0 if k == "command_center" else 80.0), 0, 20.0), true)
		shots.append([b, "0_" + k])
	await _wait(3.0)
	for s in shots:
		var u: Unit = s[0]
		var close: float = 11.0 if u.def.get("visual", "") == "infantry" else (24.0 if u is Building else 15.0)
		cam.yaw = deg_to_rad(35.0)
		cam.zoom = close; cam.zoom_goal = close
		cam.focus(u.position)
		cam._apply()
		await _wait(0.4)
		await _shot("close_" + s[1])
	cam.zoom = 70.0; cam.zoom_goal = 70.0; cam.focus(Vector3(-40, 0, 90)); cam._apply()
	await _wait(0.4)
	await _shot("rts_reference")
	get_tree().quit()

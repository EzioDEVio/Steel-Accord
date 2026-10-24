# Steel Accord - RTS camera rig: pivot on the ground, camera on a pitched boom.
# Right-drag (via Commander) / arrow keys / screen edge pan, mouse wheel zoom, middle-drag rotate,
# comma/period rotate, Home resets.
# Close-up: below the normal RTS range (CLOSE_START) the wheel keeps zooming down to ground level; the camera
# flattens toward the horizon, aims at chest height and never dips below the terrain.
class_name RTSCamera
extends Node3D

var cam: Camera3D
var zoom := 70.0
var zoom_min := 9.0    # close-up limit (see CLOSE_START)
const CLOSE_START := 44.0   # above this the classic RTS view; below it the close-up blend
const CLOSE_PITCH := 14.0   # pitch at the closest zoom
var zoom_goal := 70.0   # the wheel moves the goal; zoom eases toward it
var _zoom_seen := 70.0
var zoom_max := 230.0
var pitch_deg := 52.0
var yaw := 0.0
var bounds := Rect2(-150, -150, 300, 300)
var edge_pan := true
var speed_mult := 1.0
var _mid_drag := false
var terrain: TerrainMap = null   # heightfield maps: the pivot follows the ground and picking ray-marches the terrain


func _ready() -> void:
	cam = Camera3D.new()
	cam.fov = 40.0
	cam.near = 0.1
	cam.far = 1500.0
	cam.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	add_child(cam)
	cam.current = true
	_apply()


## 0 in the classic RTS range, rising to 1 at the closest zoom.
func closeness() -> float:
	return clampf((CLOSE_START - zoom) / (CLOSE_START - zoom_min), 0.0, 1.0)


func _apply() -> void:
	rotation.y = yaw
	var c := closeness()
	var p := deg_to_rad(lerpf(pitch_deg, CLOSE_PITCH, smoothstep(0.0, 1.0, c)))
	var aim_h := 1.6 * c   # look at chest height instead of the ground when close
	cam.position = Vector3(0, sin(p) * zoom + aim_h, cos(p) * zoom)
	cam.rotation = Vector3(-p, 0, 0)
	_zoom_seen = zoom
	_keep_above_ground()


## The camera must never go into a hillside: lift it (and tilt down to keep the same aim point) when needed.
func _keep_above_ground() -> void:
	if terrain == null or not is_inside_tree(): return
	var g := cam.global_position
	var floor_h := terrain.height_at(g.x, g.z) + 1.2
	if g.y < floor_h:
		var aim := global_position + Vector3(0, 1.6 * closeness(), 0)
		cam.global_position = Vector3(g.x, floor_h, g.z)
		cam.look_at(aim, Vector3.UP)


func focus(p: Vector3, instant := true) -> void:
	var x := clampf(p.x, bounds.position.x, bounds.end.x)
	var z := clampf(p.z, bounds.position.y, bounds.end.y)
	var y := position.y if not instant else _pivot_h(x, z)
	position = Vector3(x, y, z)


## Pivot height: terrain averaged over a few metres around the focus so the view does not jitter over small bumps.
func _pivot_h(x: float, z: float) -> float:
	if terrain == null: return 0.0
	var h := 0.0
	for o in [Vector2.ZERO, Vector2(12, 0), Vector2(-12, 0), Vector2(0, 12), Vector2(0, -12)]:
		h += terrain.height_at(x + o.x, z + o.y)
	return h / 5.0


## Camera shake from large blasts (FX). Decays quickly; purely visual (Options: "Camera shake").
var shake := 0.0


func add_shake(amount: float) -> void:
	shake = minf(1.2, shake + amount)


func _process(dt: float) -> void:
	if shake > 0.0:
		shake = move_toward(shake, 0.0, dt * 2.2)
		var a := shake * shake * 1.4
		cam.h_offset = randf_range(-a, a)
		cam.v_offset = randf_range(-a, a) * 0.7
	elif cam.h_offset != 0.0 or cam.v_offset != 0.0:
		cam.h_offset = 0.0; cam.v_offset = 0.0
	var mv := Vector2.ZERO
	if Input.is_key_pressed(KEY_LEFT): mv.x -= 1
	if Input.is_key_pressed(KEY_RIGHT): mv.x += 1
	if Input.is_key_pressed(KEY_UP): mv.y -= 1
	if Input.is_key_pressed(KEY_DOWN): mv.y += 1
	if edge_pan and DisplayServer.window_is_focused():
		var vp := get_viewport()
		var m := vp.get_mouse_position()
		var s := vp.get_visible_rect().size
		if m.x >= 0 and m.y >= 0 and m.x <= s.x and m.y <= s.y:
			if m.x < 6: mv.x -= 1
			elif m.x > s.x - 6: mv.x += 1
			if m.y < 6: mv.y -= 1
			elif m.y > s.y - 6: mv.y += 1
	if mv != Vector2.ZERO:
		var spd := zoom * 1.1 * dt * speed_mult
		var right := Vector3(cos(yaw), 0, -sin(yaw))
		var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
		focus(position + (right * mv.x - fwd * mv.y).normalized() * spd, false)
	if zoom != _zoom_seen: zoom_goal = zoom   # set directly by code (tests, save load): adopt it
	if absf(zoom_goal - zoom) > 0.01:
		zoom = lerpf(zoom, zoom_goal, minf(1.0, dt * 10.0))
		if absf(zoom_goal - zoom) < 0.05: zoom = zoom_goal
		_apply()
	if terrain:
		var c := closeness()
		var ph := _pivot_h(position.x, position.z) if c < 0.5 else terrain.height_at(position.x, position.z)
		position.y = lerpf(position.y, ph, minf(1.0, dt * 6.0))
		if c > 0.0: _keep_above_ground()
	if Input.is_key_pressed(KEY_COMMA): yaw += dt * 1.5; _apply()
	if Input.is_key_pressed(KEY_PERIOD): yaw -= dt * 1.5; _apply()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		var mb := e as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			zoom_goal = maxf(zoom_min, zoom_goal * (0.84 if zoom_goal < CLOSE_START else 0.9))
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			zoom_goal = minf(zoom_max, zoom_goal * (1.19 if zoom_goal < CLOSE_START else 1.1))
		elif mb.button_index == MOUSE_BUTTON_MIDDLE:
			_mid_drag = mb.pressed
	elif e is InputEventMouseMotion and _mid_drag:
		var mm := e as InputEventMouseMotion
		yaw -= mm.relative.x * 0.006
		pitch_deg = clampf(pitch_deg + mm.relative.y * 0.15, 35.0, 75.0)
		_apply()
	elif e is InputEventKey and e.pressed and (e as InputEventKey).keycode == KEY_HOME:
		yaw = 0.0; zoom = 70.0; zoom_goal = 70.0; pitch_deg = 52.0; _apply()


## Grab-and-drag scrolling: the map follows the mouse (used for right-drag).
func drag_pan(rel: Vector2) -> void:
	var k := zoom * 0.0022
	var right := Vector3(cos(yaw), 0, -sin(yaw))
	var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
	focus(position - right * rel.x * k + fwd * rel.y * k, false)


## Ground point under a screen position (terrain surface, or the y = 0 plane on flat maps), or null.
func ground_at(screen: Vector2) -> Variant:
	var o := cam.project_ray_origin(screen)
	var d := cam.project_ray_normal(screen)
	if terrain: return terrain.raycast(o, d, cam.far)
	if absf(d.y) < 1e-4: return null
	var t := -o.y / d.y
	if t < 0: return null
	return o + d * t

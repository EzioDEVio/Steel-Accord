# Steel Accord - strike camera (B3): a cinematic view of one of the player's bomber strikes.
# A SubViewport sharing the battle's World3D (so it shows the real fight) with its own Camera3D, shown in a framed
# inset (~30% of the screen width, labelled with the power name) or temporarily full screen. The main RTS camera and
# all input stay with the player in picture-in-picture mode; full-screen mode hides the HUD until the strike is over
# (Space skips). Shots: chase the lead bomber -> swing under it to watch the bay open and the bombs fall out ->
# follow the bombs down -> hold on the impacts, then close a few seconds later. Presentation only (reads sim state).
class_name StrikeCam
extends CanvasLayer

var battle: Node
var director: Node
var group: Array = []
var title := ""
var full := false

var vp: SubViewport
var cam: Camera3D
var frame: Panel
var view: SubViewportContainer
var label: Label
var phase := "chase"
var hold_until := -1.0
var impact_c := Vector3.ZERO
var _look := Vector3.ZERO
var _started := false
var _hud_was := true
const PIP_FRAC := 0.3


func _ready() -> void:
	layer = 20 if full else 4
	process_mode = Node.PROCESS_MODE_ALWAYS   # keeps its layout and framing while the game is paused
	frame = Panel.new()
	var st := StyleBoxFlat.new()
	st.bg_color = Color(0.03, 0.04, 0.05, 0.92)
	st.border_color = Color(0.86, 0.66, 0.22)
	st.set_border_width_all(2); st.set_corner_radius_all(3)
	frame.add_theme_stylebox_override("panel", st)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(frame)
	view = SubViewportContainer.new()
	view.stretch = true
	view.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(view)
	vp = SubViewport.new()
	vp.world_3d = battle.get_viewport().world_3d      # the real battle, not a copy
	vp.own_world_3d = false
	vp.handle_input_locally = false
	vp.gui_disable_input = true
	vp.msaa_3d = Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
	view.add_child(vp)
	cam = Camera3D.new()
	cam.fov = 48.0
	cam.near = 0.5
	cam.far = 2500.0
	vp.add_child(cam)
	cam.current = true
	label = Label.new()
	label.text = "STRIKE CAM  -  " + title.to_upper() + ("    [Space] skip" if full else "")
	label.add_theme_font_size_override("font_size", 14)
	label.add_theme_color_override("font_color", Color(0.95, 0.85, 0.55))
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(label)
	if full and battle.hud:
		_hud_was = battle.hud.visible
		battle.hud.visible = false
	_layout()


func _layout() -> void:
	var s: Vector2 = battle.get_viewport().get_visible_rect().size
	var r: Rect2
	if full:
		r = Rect2(Vector2.ZERO, s)
	else:
		var w := roundf(s.x * PIP_FRAC)
		var h := roundf(w * 9.0 / 16.0) + 24.0
		var hs: float = battle.hud.ui_scale if battle.hud else 1.0
		r = Rect2(Vector2(s.x - w - 206.0 * hs, 58.0 * hs), Vector2(w, h))   # left of the support-power column
	frame.position = r.position
	frame.size = r.size
	label.position = Vector2(10, 3)
	view.position = Vector2(3, 0 if full else 22)
	view.size = r.size - Vector2(6, 3 if full else 25)
	if full: label.position = Vector2(24, 18)


func is_open() -> bool:
	return is_inside_tree()


func _lead() -> Dictionary:
	for f in group:
		if is_instance_valid(f.node) and f in battle.flights: return f
	return {}


func _process(dt: float) -> void:
	_layout()
	var f := _lead()
	var want_pos: Vector3
	var want_look: Vector3
	# live bombs of the whole group (the lead's first, the rest as they come)
	var live: Array = []
	var landed: Array = []
	for g in group:
		for b in g.released:
			if b.has("impact"): landed.append(b.impact)
			elif is_instance_valid(b.node): live.append(b.pos)
	if phase == "chase" and not f.is_empty() and f.doors > 0.05: phase = "bay"
	if phase == "bay" and not live.is_empty() and battle.sim_time - float(group[0].last_rel) > 0.9: phase = "bombs"
	if phase in ["bay", "chase"] and f.is_empty() and not live.is_empty(): phase = "bombs"
	if phase == "bombs" and live.is_empty() and not landed.is_empty():
		phase = "impact"
		impact_c = _centroid(landed)
		hold_until = battle.sim_time + 3.5
	if f.is_empty() and live.is_empty() and landed.is_empty() and phase != "impact":
		_close(); return
	match phase:
		"chase", "bay":
			if f.is_empty(): return
			var p: Vector3 = f.model.global_position
			var d: Vector3 = f.dir; var rt: Vector3 = f.right
			var L: float = float(f.bd.length)
			if phase == "chase":
				want_pos = p - d * (L * 1.25) + Vector3.UP * (L * 0.32) + rt * (L * 0.4)
				want_look = p + d * (L * 0.35)
			else:
				var bay := _bay_point(f)
				want_pos = bay + rt * (L * 0.55) + Vector3.DOWN * (L * 0.22) + d * (L * 0.12)
				want_look = bay + Vector3.DOWN * 3.0
		"bombs":
			var c := _centroid(live)
			var d2: Vector3 = group[0].dir; var rt2: Vector3 = group[0].right
			want_pos = c - d2 * 26.0 + rt2 * 30.0 + Vector3.UP * 8.0
			want_look = c + Vector3.DOWN * 6.0
		"impact":
			var d3: Vector3 = group[0].dir; var rt3: Vector3 = group[0].right
			want_pos = impact_c - d3 * 70.0 + rt3 * 55.0 + Vector3.UP * 45.0
			want_look = impact_c
			if battle.sim_time >= hold_until:
				_close(); return
	if not _started:
		cam.global_position = want_pos
		_look = want_look
		_started = true
	var k := 1.0 - exp(-dt * (2.2 if phase != "bombs" else 3.5))
	cam.global_position = cam.global_position.lerp(want_pos, k)
	_look = _look.lerp(want_look, k)
	if cam.global_position.distance_to(_look) > 0.5:
		cam.look_at(_look, Vector3.UP)


func _bay_point(f: Dictionary) -> Vector3:
	var a := f.model.find_child("Bay0a", false, false) as Node3D
	var b := f.model.find_child("Bay%db" % (int(f.bd.bays) - 1), false, false) as Node3D
	if a and b: return (a.global_position + b.global_position) * 0.5
	return f.model.global_position


func _centroid(ps: Array) -> Vector3:
	var c := Vector3.ZERO
	for p in ps: c += p
	return c / float(maxi(ps.size(), 1))


func _unhandled_input(e: InputEvent) -> void:
	if full and e is InputEventKey and e.pressed and (e as InputEventKey).keycode == KEY_SPACE:
		get_viewport().set_input_as_handled()
		_close()


func _close() -> void:
	if is_queued_for_deletion(): return
	if full and battle.hud: battle.hud.visible = _hud_was
	if director: director.on_cam_closed()
	queue_free()

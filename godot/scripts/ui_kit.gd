# Steel Accord - shared UI styling helpers (menus, pause screen, end screen, HUD buttons).
class_name UIKit

const ACCENT := Color(0.42, 0.95, 0.6)
const TEXT := Color(0.86, 0.92, 0.88)
const PANEL_BG := Color(0.05, 0.07, 0.08, 0.92)


static func style(c: Color, border: Color, radius := 3) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = c; s.border_color = border
	s.set_border_width_all(1); s.set_corner_radius_all(radius)
	s.content_margin_left = 10; s.content_margin_right = 10; s.content_margin_top = 6; s.content_margin_bottom = 6
	return s


static func button(text: String, cb: Callable, size := Vector2(260, 42), font_size := 17) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = size
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_stylebox_override("normal", style(Color(0.10, 0.14, 0.15, 0.95), Color(0.35, 0.45, 0.42)))
	b.add_theme_stylebox_override("hover", style(Color(0.16, 0.24, 0.22, 0.98), ACCENT))
	b.add_theme_stylebox_override("pressed", style(Color(0.22, 0.34, 0.28, 1.0), ACCENT))
	b.add_theme_stylebox_override("disabled", style(Color(0.08, 0.09, 0.1, 0.8), Color(0.2, 0.22, 0.22)))
	b.add_theme_color_override("font_color", TEXT)
	b.add_theme_color_override("font_hover_color", Color(1, 1, 1))
	b.add_theme_color_override("font_disabled_color", Color(0.4, 0.43, 0.42))
	b.add_theme_font_size_override("font_size", font_size)
	if cb.is_valid(): b.pressed.connect(cb)
	return b


static func panel(min_size: Vector2) -> PanelContainer:
	var p := PanelContainer.new()
	p.custom_minimum_size = min_size
	var s := style(PANEL_BG, Color(0.55, 0.68, 0.62, 0.9), 4)
	s.content_margin_left = 22; s.content_margin_right = 22; s.content_margin_top = 18; s.content_margin_bottom = 18
	p.add_theme_stylebox_override("panel", s)
	return p


static func label(text: String, size := 16, color := TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


static func option(items: Array, current: String, cb: Callable) -> OptionButton:
	var o := OptionButton.new()
	for i in items.size():
		o.add_item(items[i])
		if items[i] == current: o.select(i)
	o.focus_mode = Control.FOCUS_NONE
	o.custom_minimum_size = Vector2(200, 34)
	o.add_theme_stylebox_override("normal", style(Color(0.10, 0.14, 0.15, 0.95), Color(0.35, 0.45, 0.42)))
	o.add_theme_stylebox_override("hover", style(Color(0.16, 0.24, 0.22, 0.98), ACCENT))
	o.item_selected.connect(func(i): cb.call(items[i]))
	return o


static func check(text: String, on: bool, cb: Callable) -> CheckBox:
	var c := CheckBox.new()
	c.text = text
	c.button_pressed = on
	c.focus_mode = Control.FOCUS_NONE
	c.add_theme_color_override("font_color", TEXT)
	c.add_theme_font_size_override("font_size", 15)
	c.toggled.connect(cb)
	return c


## Options rows shared by the main menu and the pause menu. Changes apply immediately and are saved.
static func options_box(on_change: Callable = Callable()) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	v.add_child(label("OPTIONS", 20, ACCENT))
	var notify := func():
		Game.save()
		if on_change.is_valid(): on_change.call()
	var set_scheme := func(x):
		Game.settings.mouse_scheme = x
		notify.call()
	var set_edge := func(on):
		Game.settings.edge_pan = on
		notify.call()
	var set_full := func(on):
		Game.settings.fullscreen = on
		Game.apply_display()
		notify.call()
	var set_speed := func(x):
		Game.settings.cam_speed = x
		notify.call()
	var row := HBoxContainer.new()
	row.add_child(label("Mouse scheme  ", 15))
	row.add_child(option(["classic", "alternate"], Game.settings.mouse_scheme, set_scheme))
	v.add_child(row)
	v.add_child(label("Classic: left click selects and commands, right click deselects.\nAlternate: right click commands.", 12, Color(0.6, 0.66, 0.63)))
	v.add_child(check("Scroll at screen edges", Game.settings.edge_pan, set_edge))
	v.add_child(check("Fullscreen", Game.settings.fullscreen, set_full))
	var row2 := HBoxContainer.new()
	row2.add_child(label("Camera speed  ", 15))
	var sl := HSlider.new()
	sl.min_value = 0.5; sl.max_value = 2.0; sl.step = 0.1; sl.value = Game.settings.cam_speed
	sl.custom_minimum_size = Vector2(200, 24)
	sl.focus_mode = Control.FOCUS_NONE
	sl.value_changed.connect(set_speed)
	row2.add_child(sl)
	v.add_child(row2)
	var row4 := HBoxContainer.new()
	row4.add_child(label("Effects volume  ", 15))
	var vs := HSlider.new()
	vs.min_value = 0.0; vs.max_value = 1.0; vs.step = 0.05; vs.value = float(Game.settings.get("sfx_volume", 0.8))
	vs.custom_minimum_size = Vector2(200, 24)
	vs.focus_mode = Control.FOCUS_NONE
	vs.value_changed.connect(func(x):
		Game.settings["sfx_volume"] = x
		notify.call())
	row4.add_child(vs)
	v.add_child(row4)
	var scales := {"Auto": 0.0, "100%": 1.0, "125%": 1.25, "150%": 1.5, "200%": 2.0}
	var cur := "Auto"
	for k in scales:
		if is_equal_approx(float(scales[k]), float(Game.settings.get("ui_scale", 0.0))): cur = k
	var set_scale := func(x):
		Game.settings["ui_scale"] = scales[x]
		notify.call()
	var row3 := HBoxContainer.new()
	row3.add_child(label("Interface size  ", 15))
	row3.add_child(option(scales.keys(), cur, set_scale))
	v.add_child(row3)
	var row5 := HBoxContainer.new()
	row5.add_child(label("Graphics quality  ", 15))
	row5.add_child(option(["Low", "Medium", "High"], str(Game.settings.get("graphics", "Medium")), func(x):
		Game.settings["graphics"] = x
		Game.apply_graphics()
		notify.call()))
	v.add_child(row5)
	v.add_child(label("Low: smaller shadows, no ambient occlusion or glow, 3D drawn at 77% and upscaled (FSR).\nHigh: largest soft shadows and 2x anti-aliasing (needs a strong graphics card).\nEffects: Low draws the fewest particle layers, lights and scorch marks; High the full set.", 12, Color(0.6, 0.66, 0.63)))
	var row6 := HBoxContainer.new()
	row6.add_child(label("Strike camera  ", 15))
	row6.add_child(option(["Off", "Picture-in-picture", "Full screen"], str(Game.settings.get("strike_cam", "Picture-in-picture")), func(x):
		Game.settings["strike_cam"] = x
		notify.call()))
	v.add_child(row6)
	v.add_child(check("Show frame rate (FPS)", bool(Game.settings.get("show_fps", false)), func(on):
		Game.settings["show_fps"] = on
		notify.call()))
	v.add_child(check("Camera shake on large explosions", bool(Game.settings.get("camera_shake", true)), func(on):
		Game.settings["camera_shake"] = on
		notify.call()))
	return v

# Steel Accord - applies the unit material system (shaders/unit.gdshader) to an imported model.
class_name UnitArt

const UNIT_SHADER := preload("res://shaders/unit.gdshader")

# palette (sRGB): base colour, roughness, metallic, shader kind
const PALETTE := {
	"SA_Paint": [Color(0.26, 0.30, 0.17), 0.62, 0.0, 1],
	"SA_Metal": [Color(0.14, 0.14, 0.13), 0.5, 0.7, 0],
	"SA_Rubber": [Color(0.07, 0.07, 0.07), 0.92, 0.0, 3],
	"SA_Track": [Color(0.20, 0.18, 0.16), 0.6, 0.6, 3],
	"SA_Glass": [Color(0.04, 0.06, 0.07), 0.05, 0.3, 5],
	"SA_Team": [Color(1, 1, 1), 0.7, 0.0, 2],
	"SA_Decal": [Color(0.78, 0.76, 0.68), 0.7, 0.0, 4],
	"SA_Canvas": [Color(0.36, 0.33, 0.23), 0.95, 0.0, 4],
	"SA_Skin": [Color(0.55, 0.40, 0.31), 0.7, 0.0, 4],
	"SA_Concrete": [Color(0.40, 0.39, 0.36), 0.9, 0.0, 4],
}


static func material_for(src: Material, ao: Texture2D, team: Color, seed_idx: int) -> ShaderMaterial:
	var key := src.resource_name if src else "SA_Paint"
	var e: Array = PALETTE.get(key, PALETTE["SA_Paint"])
	var m := ShaderMaterial.new()
	m.shader = UNIT_SHADER
	m.set_shader_parameter("base_color", e[0])
	m.set_shader_parameter("roughness_v", e[1])
	m.set_shader_parameter("metallic_v", e[2])
	m.set_shader_parameter("kind", e[3])
	m.set_shader_parameter("team_color", team)
	m.set_shader_parameter("camo_offset", Vector3(seed_idx * 13.7, seed_idx * 5.1, seed_idx * 9.3))
	m.set_shader_parameter("ao_tex", ao)
	return m


## Replaces every surface material under `n`; returns the list of created materials (for later effects, e.g. burnt).
static func apply(n: Node, ao_prefix: String, team: Color, seed_idx: int, out: Array = [], root: Node = null) -> Array:
	if root == null: root = n
	if n is MeshInstance3D:
		var mi := n as MeshInstance3D
		# height of this mesh's origin above the model root, so dust is measured from the ground for every segment
		var y_off := 0.0
		var p: Node = mi
		while p != root and p is Node3D:
			y_off += (p as Node3D).position.y
			p = p.get_parent()
		var spinning := mi.name.ends_with("Rotor")
		var ao_path := "%s%s_ao.png" % [ao_prefix, mi.name.to_lower()]
		var ao: Texture2D = load(ao_path) if ResourceLoader.exists(ao_path) else null
		for i in mi.mesh.get_surface_count():
			var m := material_for(mi.mesh.surface_get_material(i), ao, team, seed_idx)
			m.set_shader_parameter("y_offset", y_off)
			m.set_shader_parameter("dust_amount", 0.15 if spinning else 1.0)
			mi.set_surface_override_material(i, m)
			out.append(m)
	for c in n.get_children():
		apply(c, ao_prefix, team, seed_idx, out, root)
	return out

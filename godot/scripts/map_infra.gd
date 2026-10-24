# Steel Accord - map infrastructure that is generated from map.json at load (B3): paved road carriageways (asphalt,
# lane markings, kerbs), railway track (ballast bed, sleepers, rails) and power-line conductors between pylons.
# Everything is draped on the heightfield in the vertex shader (road_surface / rail_drape read the terrain's height
# texture), so the geometry follows later terrain edits (building pads) without rebuilding.
# Draw calls: one mesh for all road strips, one per track part (ballast, rails) and one MultiMesh for every sleeper,
# one mesh for all conductors. Landmark models (portals, bridges, rolling stock, ...) are ordinary map props.
class_name MapInfra
extends Node3D

const ROAD_SHADER := preload("res://shaders/road_surface.gdshader")
const RAIL_SHADER := preload("res://shaders/rail_drape.gdshader")
const SLEEPER_SPACING := 0.65
const GAUGE := 1.435

var tm: TerrainMap
var stats := {}                  # counts for tests / reports
var sleeper_xz: PackedVector2Array = PackedVector2Array()
var rail_lines: Array = []       # [PackedVector2Array] smoothed centre lines (main lines and sidings)
var wire_points: Array = []      # [[a, b]] attachment pairs actually strung (world)


func build(t: TerrainMap) -> void:
	tm = t
	name = "MapInfra"
	var t0 := Time.get_ticks_msec()
	_build_roads()
	_build_rail()
	_build_wires()
	stats["build_ms"] = Time.get_ticks_msec() - t0
	print("MAP infra: %s" % str(stats))


func _mat(shader: Shader) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = shader
	m.set_shader_parameter("hmap", tm.mat.get_shader_parameter("hmap"))
	m.set_shader_parameter("hmap_info", tm.mat.get_shader_parameter("hmap_info"))
	m.set_shader_parameter("n_detail", tm.mat.get_shader_parameter("n_detail"))
	return m


func _world_aabb() -> AABB:
	var h := tm.half_size()
	return AABB(Vector3(-h, -5.0, -h), Vector3(2.0 * h, float(tm.data.get("height_scale", 80.0)) + 20.0, 2.0 * h))


## Centripetal-free uniform Catmull-Rom through pts, resampled every `spacing` metres.
static func smooth_line(pts: Array, spacing: float) -> PackedVector2Array:
	var P := PackedVector2Array()
	for q in pts: P.append(Vector2(float(q[0]), float(q[1])))
	if P.size() < 2: return P
	var dense := PackedVector2Array()
	for i in P.size() - 1:
		var p0 := P[maxi(i - 1, 0)] if i > 0 else P[0] * 2.0 - P[1]
		var p1 := P[i]; var p2 := P[i + 1]
		var p3 := P[i + 2] if i + 2 < P.size() else P[i + 1] * 2.0 - P[i]
		var n := maxi(2, int(p1.distance_to(p2) / 1.0))
		for k in n:
			var t := float(k) / n; var t2 := t * t; var t3 := t2 * t
			dense.append(0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3))
	dense.append(P[P.size() - 1])
	var out := PackedVector2Array([dense[0]])
	var acc := 0.0
	for i in range(1, dense.size()):
		acc += dense[i].distance_to(dense[i - 1])
		if acc >= spacing or i == dense.size() - 1:
			out.append(dense[i]); acc = 0.0
	return out


static func _tangent(L: PackedVector2Array, i: int) -> Vector2:
	var a := L[maxi(i - 1, 0)]; var b := L[mini(i + 1, L.size() - 1)]
	return (b - a).normalized()


# ------------------------------------------------------------------ roads
func _build_roads() -> void:
	if not tm.data.has("surface_file"): return          # older maps: roads are drawn by the terrain shader only
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n_roads := 0; var length := 0.0
	var prio := {"main": 0.03, "street": 0.0, "track": 0.0}
	for r in tm.data.get("roads", []):
		if str(r.get("surface", "paved")) != "paved": continue
		var w := float(r.get("width_m", 7.0))
		var L := smooth_line(r.get("points", []), 2.5)
		if L.size() < 2: continue
		n_roads += 1
		var col := Color(1.0 if r.get("kerbs", false) else 0.0, 1.0 if r.get("markings", false) else 0.0, w / 20.0)
		var lift := float(prio.get(str(r.get("cls", "main")), 0.0))
		var across := [-0.5, -0.5 + 0.35 / w, -0.25, 0.0, 0.25, 0.5 - 0.35 / w, 0.5]
		var v := 0.0
		var rows: Array = []
		for i in L.size():
			if i > 0: v += L[i].distance_to(L[i - 1])
			var t := _tangent(L, i)
			var side := Vector2(-t.y, t.x)
			var row := []
			for a in across:
				var p: Vector2 = L[i] + side * (a * w)
				row.append([Vector3(p.x, lift, p.y), Vector2(a * w, v)])
			rows.append(row)
		length += v
		for i in rows.size() - 1:
			for k in across.size() - 1:
				var q: Array = [rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]]
				for idx in [0, 2, 1, 0, 3, 2]:
					st.set_color(col); st.set_uv(q[idx][1]); st.set_normal(Vector3.UP); st.add_vertex(q[idx][0])
	var mi := MeshInstance3D.new()
	mi.name = "RoadSurface"
	mi.mesh = st.commit()
	mi.material_override = _mat(ROAD_SHADER)
	mi.custom_aabb = _world_aabb()
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	stats["paved_roads"] = n_roads
	stats["paved_km"] = snappedf(length / 1000.0, 0.01)


# ------------------------------------------------------------------ railway
func _build_rail() -> void:
	var rail: Dictionary = tm.data.get("rail", {})
	var lines: Array = rail.get("lines", []) + rail.get("sidings", [])
	if lines.is_empty(): return
	var ballast := SurfaceTool.new(); ballast.begin(Mesh.PRIMITIVE_TRIANGLES)
	var steel := SurfaceTool.new(); steel.begin(Mesh.PRIMITIVE_TRIANGLES)
	var xfs: Array[Transform3D] = []
	# ballast cross-section (offset across, height above the formation) and rail profile (head 0.07 m, foot 0.13 m)
	var bprof := [Vector2(-2.3, -0.05), Vector2(-1.65, 0.33), Vector2(1.65, 0.33), Vector2(2.3, -0.05)]
	var rprof := [Vector2(-0.065, 0.5), Vector2(-0.02, 0.52), Vector2(-0.035, 0.62), Vector2(-0.035, 0.67), Vector2(0.035, 0.67), Vector2(0.035, 0.62), Vector2(0.02, 0.52), Vector2(0.065, 0.5)]
	var total := 0.0
	for ln in lines:
		var L := smooth_line(ln.get("points", []), 1.5)
		if L.size() < 2: continue
		rail_lines.append(L)
		_extrude(ballast, L, bprof, 0.0)
		for s in [-1.0, 1.0]:
			_extrude(steel, L, rprof, s * GAUGE * 0.5 + s * 0.035)
		# sleepers every 0.65 m along the line
		var acc := 0.0
		var next := SLEEPER_SPACING * 0.5
		for i in range(1, L.size()):
			var seg := L[i].distance_to(L[i - 1])
			var d := L[i] - L[i - 1]
			while next <= acc + seg:
				var p := L[i - 1] + d * ((next - acc) / seg)
				var t := d.normalized()
				var b := Basis(Vector3.UP, atan2(t.x, t.y))       # local Z along the track, X across
				xfs.append(Transform3D(b, Vector3(p.x, 0.41, p.y)))
				sleeper_xz.append(p)
				next += SLEEPER_SPACING
			acc += seg
		total += acc
	var bm := MeshInstance3D.new(); bm.name = "RailBallast"; bm.mesh = ballast.commit()
	var mb := _mat(RAIL_SHADER); mb.set_shader_parameter("kind", 0); mb.set_shader_parameter("base_color", Color(0.47, 0.45, 0.42))
	bm.material_override = mb; bm.custom_aabb = _world_aabb(); bm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(bm)
	var sm := MeshInstance3D.new(); sm.name = "Rails"; sm.mesh = steel.commit()
	var ms := _mat(RAIL_SHADER); ms.set_shader_parameter("kind", 1)
	sm.material_override = ms; sm.custom_aabb = _world_aabb(); sm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sm)
	var box := BoxMesh.new(); box.size = Vector3(2.6, 0.16, 0.26)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = box
	mm.instance_count = xfs.size()
	for i in xfs.size(): mm.set_instance_transform(i, xfs[i])
	var mmi := MultiMeshInstance3D.new(); mmi.name = "RailSleepers"; mmi.multimesh = mm
	var mk := _mat(RAIL_SHADER); mk.set_shader_parameter("kind", 2); mk.set_shader_parameter("base_color", Color(0.55, 0.53, 0.50))
	mmi.material_override = mk; mmi.custom_aabb = _world_aabb(); mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)
	stats["rail_lines"] = lines.size()
	stats["rail_m"] = int(total)
	stats["sleepers"] = xfs.size()


## Extrudes a 2D cross-section (x across, y height above ground) along a centre line, offset `off` across.
func _extrude(st: SurfaceTool, L: PackedVector2Array, prof: Array, off: float) -> void:
	var rows: Array = []
	for i in L.size():
		var t := _tangent(L, i)
		var side := Vector2(-t.y, t.x)
		var row := []
		for q: Vector2 in prof:
			var p: Vector2 = L[i] + side * (q.x + off)
			row.append(Vector3(p.x, q.y, p.y))
		rows.append(row)
	for i in rows.size() - 1:
		for k in prof.size() - 1:
			var a: Vector3 = rows[i][k]; var b: Vector3 = rows[i][k + 1]; var c: Vector3 = rows[i + 1][k + 1]; var d: Vector3 = rows[i + 1][k]
			var nrm := (b - a).cross(d - a).normalized()
			if nrm.y < 0.0 and absf(nrm.y) > 0.2: nrm = -nrm
			for p in [a, c, b, a, d, c]:
				st.set_normal(nrm); st.add_vertex(p)


# ------------------------------------------------------------------ power lines
func _build_wires() -> void:
	var lines: Array = tm.data.get("power_lines", [])
	if lines.is_empty(): return
	var path := str(tm.data.get("prop_types", {}).get("pylon", {}).get("glb", "res://assets/units3d/props/pylon.glb"))
	if not ResourceLoader.exists(path): return
	var sc: Node3D = (load(path) as PackedScene).instantiate()
	var att: Array[Vector3] = []
	for nm in ["Wire_0", "Wire_1", "Wire_2", "Earth_0", "Earth_1"]:
		var e: Node3D = sc.find_child(nm, true, false)
		if e: att.append(_local_pos(sc, e))
	sc.free()
	if att.is_empty(): return
	# pylon transforms: match each power-line point to its prop (yaw, scale)
	var props := {}
	for pr in tm.data.get("props", []):
		if str(pr.get("type", "")) == "pylon": props[Vector2i(roundi(float(pr.pos[0]) * 10), roundi(float(pr.pos[1]) * 10))] = pr
	var st := SurfaceTool.new(); st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var spans := 0
	for line in lines:
		var tops: Array = []
		for q in line:
			var pr: Dictionary = props.get(Vector2i(roundi(float(q[0]) * 10), roundi(float(q[1]) * 10)), {})
			var yaw := deg_to_rad(float(pr.get("yaw_deg", 0.0))); var s := float(pr.get("scale", 1.0))
			var o := Vector3(float(q[0]), tm.height_at(float(q[0]), float(q[1])), float(q[1]))
			var xf := Transform3D(Basis(Vector3.UP, yaw).scaled(Vector3.ONE * s), o)
			var pts: Array = []
			for a in att: pts.append(xf * a)
			tops.append(pts)
		for i in tops.size() - 1:
			var A: Array = tops[i]; var B: Array = tops[i + 1]
			var dir: Vector3 = (B[0] as Vector3) - (A[0] as Vector3); dir.y = 0.0; dir = dir.normalized()
			var lat := Vector3(-dir.z, 0, dir.x)
			# pair conductors by their lateral position (mirrored pylons are turned 180 degrees)
			var ia := range(A.size()); var ib := range(B.size())
			ia.sort_custom(func(x, y): return (A[x] as Vector3).dot(lat) + (A[x] as Vector3).y * 0.001 < (A[y] as Vector3).dot(lat) + (A[y] as Vector3).y * 0.001)
			ib.sort_custom(func(x, y): return (B[x] as Vector3).dot(lat) + (B[x] as Vector3).y * 0.001 < (B[y] as Vector3).dot(lat) + (B[y] as Vector3).y * 0.001)
			for k in ia.size():
				var a: Vector3 = A[ia[k]]; var b: Vector3 = B[ib[k]]
				_catenary(st, a, b, 0.025 * a.distance_to(b), 0.045 if a.y < b.y + 3.0 and k < 3 else 0.03)
				wire_points.append([a, b])
			spans += 1
	var mi := MeshInstance3D.new(); mi.name = "PowerWires"; mi.mesh = st.commit()
	var m := StandardMaterial3D.new(); m.albedo_color = Color(0.16, 0.16, 0.17); m.roughness = 0.5; m.metallic = 0.6
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	stats["wire_spans"] = spans


func _local_pos(root: Node3D, n: Node3D) -> Vector3:
	var xf := Transform3D.IDENTITY
	var c: Node = n
	while c != null and c != root:
		xf = (c as Node3D).transform * xf
		c = c.get_parent()
	return xf.origin


## Sagging conductor a -> b as a thin three-sided tube (12 segments, parabolic sag).
func _catenary(st: SurfaceTool, a: Vector3, b: Vector3, sag: float, r: float) -> void:
	var n := 12
	var pts: Array[Vector3] = []
	for i in n + 1:
		var t := float(i) / n
		pts.append(a.lerp(b, t) - Vector3(0, 4.0 * sag * t * (1.0 - t), 0))
	var d := (b - a).normalized()
	var u := d.cross(Vector3.UP).normalized() * r
	var w := d.cross(u).normalized() * r
	var ring := [u, -u * 0.5 + w * 0.866, -u * 0.5 - w * 0.866]
	for i in n:
		for k in 3:
			var p0: Vector3 = pts[i] + ring[k]; var p1: Vector3 = pts[i] + ring[(k + 1) % 3]
			var q0: Vector3 = pts[i + 1] + ring[k]; var q1: Vector3 = pts[i + 1] + ring[(k + 1) % 3]
			var nrm: Vector3 = (ring[k] + ring[(k + 1) % 3]).normalized()
			for p in [p0, q1, p1, p0, q0, q1]:
				st.set_normal(nrm); st.add_vertex(p)

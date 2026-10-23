# Steel Accord - heightfield terrain for data-driven maps (maps/<id>/map.json + height.r16 + splat.png).
# One authoritative height function (bilinear over a 16-bit grid) is used by the renderer, unit grounding, building
# placement / flattening, camera picking and the slope-aware pathfinding grid, so nothing floats or sinks.
# Rendered as square chunks so a local edit (flattening a building pad) only rebuilds the chunks it touches.
# Decision record: docs/adr/ADR-0008-terrain-heightfield.md (built-in heightfield instead of the Terrain3D GDExtension).
class_name TerrainMap
extends Node3D

const SHADER := preload("res://shaders/terrain_map.gdshader")
const CHUNK_CELLS := 50            # quads per chunk side

var map_dir := ""
var data: Dictionary = {}
var n := 601                       # samples per side
var step := 2.0                    # metres between samples
var origin := Vector2(-600, -600)  # world x,z of sample (0,0)
var heights := PackedFloat32Array()
var splat: Image
var road_mask: Image
var mat: ShaderMaterial
var chunks := {}                   # Vector2i -> MeshInstance3D
var slope_grid := PackedFloat32Array()   # per sample: steepest slope (deg) to any neighbour (conservative for nav)
var splat_bytes := PackedByteArray()     # RGBA8, n x n (resampled to the height grid)
var road_bytes := PackedByteArray()      # L8, n x n


static func exists(id: String) -> bool:
	return FileAccess.file_exists("res://maps/%s/map.json" % id)


func load_map(id: String) -> bool:
	map_dir = "res://maps/%s" % id
	var js: Variant = JSON.parse_string(FileAccess.get_file_as_string(map_dir + "/map.json"))
	if not (js is Dictionary): return false
	data = js
	var size: Array = data.get("size_m", [1200, 1200])
	var hs: float = float(data.get("height_scale", 80.0))
	var raw := FileAccess.get_file_as_bytes(map_dir + "/height.r16")
	n = int(round(sqrt(raw.size() / 2.0)))
	if n * n * 2 != raw.size() or n < 2: return false
	step = float(size[0]) / float(n - 1)
	origin = Vector2(-float(size[0]) * 0.5, -float(size[1]) * 0.5)
	heights.resize(n * n)
	for i in n * n:
		heights[i] = float(raw.decode_u16(i * 2)) / 65535.0 * hs
	splat = _load_image(map_dir + "/splat.png")
	if splat:
		if splat.get_format() != Image.FORMAT_RGBA8: splat.convert(Image.FORMAT_RGBA8)
		var sc := splat.duplicate() as Image
		if sc.get_width() != n: sc.resize(n, n, Image.INTERPOLATE_BILINEAR)
		splat_bytes = sc.get_data()
	_bake_roads()
	road_bytes = road_mask.get_data()
	_bake_slopes()
	return true


func _bake_slopes() -> void:
	slope_grid.resize(n * n)
	for iz in n:
		for ix in n:
			var h := _h(ix, iz)
			var sx := maxf(absf(_h(ix + 1, iz) - h), absf(h - _h(ix - 1, iz))) / step
			var sz := maxf(absf(_h(ix, iz + 1) - h), absf(h - _h(ix, iz - 1))) / step
			slope_grid[iz * n + ix] = rad_to_deg(atan(sqrt(sx * sx + sz * sz)))


## Steepest baked slope among the height samples inside a square of half-size r around (x, z).
func max_slope_in(x: float, z: float, r: float) -> float:
	var x0 := clampi(int(floor((x - r - origin.x) / step)), 0, n - 1); var x1 := clampi(int(ceil((x + r - origin.x) / step)), 0, n - 1)
	var z0 := clampi(int(floor((z - r - origin.y) / step)), 0, n - 1); var z1 := clampi(int(ceil((z + r - origin.y) / step)), 0, n - 1)
	var m := 0.0
	for iz in range(z0, z1 + 1):
		for ix in range(x0, x1 + 1):
			m = maxf(m, slope_grid[iz * n + ix])
	return m


## splat.png is imported with the "Image" importer (exact pixels, no VRAM compression) so it reads the same in the
## editor and in an exported build.
func _load_image(path: String) -> Image:
	if ResourceLoader.exists(path):
		var r: Resource = load(path)
		if r is Image: return r
		if r is Texture2D:
			var im: Image = (r as Texture2D).get_image()
			if im.is_compressed(): im.decompress()
			return im
	if FileAccess.file_exists(path): return Image.load_from_file(path)
	return null


func half_size() -> float:
	return -origin.x


# ------------------------------------------------------------------ queries
func _h(ix: int, iz: int) -> float:
	return heights[clampi(iz, 0, n - 1) * n + clampi(ix, 0, n - 1)]


func height_at(x: float, z: float) -> float:
	var fx := (x - origin.x) / step
	var fz := (z - origin.y) / step
	var ix := int(floor(fx)); var iz := int(floor(fz))
	var tx := fx - ix; var tz := fz - iz
	var a := lerpf(_h(ix, iz), _h(ix + 1, iz), tx)
	var b := lerpf(_h(ix, iz + 1), _h(ix + 1, iz + 1), tx)
	return lerpf(a, b, tz)


func normal_at(x: float, z: float) -> Vector3:
	var e := step
	var hx := height_at(x + e, z) - height_at(x - e, z)
	var hz := height_at(x, z + e) - height_at(x, z - e)
	return Vector3(-hx, 2.0 * e, -hz).normalized()


func slope_deg_at(x: float, z: float) -> float:
	return rad_to_deg(acos(clampf(normal_at(x, z).y, -1.0, 1.0)))


## Height range and steepest slope over a footprint (for building placement).
func footprint_stats(center: Vector3, half: Vector2) -> Vector3:
	# reads the height and slope grids directly (no interpolation): placement checks run every frame for the ghost
	# and many times per AI decision, so this must stay cheap
	var x0 := clampi(int(floor((center.x - half.x - origin.x) / step)), 0, n - 1); var x1 := clampi(int(ceil((center.x + half.x - origin.x) / step)), 0, n - 1)
	var z0 := clampi(int(floor((center.z - half.y - origin.y) / step)), 0, n - 1); var z1 := clampi(int(ceil((center.z + half.y - origin.y) / step)), 0, n - 1)
	var lo := INF; var hi := -INF; var smax := 0.0; var sum := 0.0; var cnt := 0
	for iz in range(z0, z1 + 1):
		var row := iz * n
		for ix in range(x0, x1 + 1):
			var h: float = heights[row + ix]
			lo = minf(lo, h); hi = maxf(hi, h); sum += h; cnt += 1
			smax = maxf(smax, slope_grid[row + ix])
	return Vector3(hi - lo, smax, sum / maxf(cnt, 1))


## Ray-march a camera ray against the heightfield; returns the hit point or null.
func raycast(o: Vector3, d: Vector3, max_dist := 3000.0) -> Variant:
	var t := 0.0
	var dt := 4.0
	var prev_above := o.y - height_at(o.x, o.z)
	while t < max_dist:
		t += dt
		var p := o + d * t
		var above := p.y - height_at(p.x, p.z)
		if above <= 0.0:
			# refine by bisection between t - dt and t
			var a := t - dt; var b := t
			for i in 12:
				var m := (a + b) * 0.5
				var q := o + d * m
				if q.y - height_at(q.x, q.z) > 0.0: a = m
				else: b = m
			return o + d * b
		prev_above = above
		dt = clampf(above * 0.5, 0.5, 8.0)
	return null


# ------------------------------------------------------------------ editing
## Flattens a rectangle (plus a smooth skirt) to height h and rebuilds the affected chunks.
func flatten(center: Vector3, half: Vector2, h: float, skirt := 6.0) -> void:
	var x0 := int(floor((center.x - half.x - skirt - origin.x) / step))
	var x1 := int(ceil((center.x + half.x + skirt - origin.x) / step))
	var z0 := int(floor((center.z - half.y - skirt - origin.y) / step))
	var z1 := int(ceil((center.z + half.y + skirt - origin.y) / step))
	for iz in range(maxi(z0, 0), mini(z1, n - 1) + 1):
		for ix in range(maxi(x0, 0), mini(x1, n - 1) + 1):
			var wx := origin.x + ix * step; var wz := origin.y + iz * step
			var dx := maxf(0.0, absf(wx - center.x) - half.x)
			var dz := maxf(0.0, absf(wz - center.z) - half.y)
			var d := Vector2(dx, dz).length()
			var w := 1.0 - smoothstep(0.0, skirt, d)
			var i := iz * n + ix
			heights[i] = lerpf(heights[i], h, w)
	for iz in range(maxi(z0 - 1, 0), mini(z1 + 1, n - 1) + 1):
		for ix in range(maxi(x0 - 1, 0), mini(x1 + 1, n - 1) + 1):
			var hh := _h(ix, iz)
			var sx := maxf(absf(_h(ix + 1, iz) - hh), absf(hh - _h(ix - 1, iz))) / step
			var sz := maxf(absf(_h(ix, iz + 1) - hh), absf(hh - _h(ix, iz - 1))) / step
			slope_grid[iz * n + ix] = rad_to_deg(atan(sqrt(sx * sx + sz * sz)))
	if is_inside_tree():
		var c0 := Vector2i(maxi(x0, 0) / CHUNK_CELLS, maxi(z0, 0) / CHUNK_CELLS)
		var c1 := Vector2i(mini(x1, n - 1) / CHUNK_CELLS, mini(z1, n - 1) / CHUNK_CELLS)
		for cz in range(c0.y, c1.y + 1):
			for cx in range(c0.x, c1.x + 1):
				_build_chunk(Vector2i(cx, cz))


# ------------------------------------------------------------------ rendering
func build_visual() -> void:
	mat = ShaderMaterial.new()
	mat.shader = SHADER
	var t0 := Time.get_ticks_msec()
	# unique macro layer over the whole map (512 px over 1200 m = 2.3 m/px): R ~350 m, G ~100 m, B ~30 m, A ~60 m
	mat.set_shader_parameter("n_macro", _noise_rgba(512, false, [[101, 0.0067, 3], [102, 0.023, 3], [103, 0.075, 2], [104, 0.04, 2]], false))
	# seamless detail tile (19 m per tile = 3.7 cm/px): R ~6 m, G ~2 m, B ~0.7 m, A cellular clusters ~3 m
	mat.set_shader_parameter("n_detail", _noise_rgba(512, true, [[111, 0.006, 4], [112, 0.018, 4], [113, 0.05, 3], [114, 0.012, 1, FastNoiseLite.TYPE_CELLULAR]], true))
	mat.set_shader_parameter("n_normal", await World.noise_tex(0.05, 19, 512, true, 4))
	print("TERRAIN noise textures %d ms" % (Time.get_ticks_msec() - t0))
	if splat: mat.set_shader_parameter("splat", ImageTexture.create_from_image(splat))
	if road_mask: mat.set_shader_parameter("roads", ImageTexture.create_from_image(road_mask))
	mat.set_shader_parameter("map_rect", Vector4(origin.x, origin.y, step * (n - 1), step * (n - 1)))
	var nc := int(ceil(float(n - 1) / CHUNK_CELLS))
	for cz in nc:
		for cx in nc:
			_build_chunk(Vector2i(cx, cz))
	# a wide skirt plane beyond the map edge so the horizon is not empty
	var skirt := MeshInstance3D.new()
	var pm := PlaneMesh.new(); pm.size = Vector2(half_size() * 6.0, half_size() * 6.0)
	var sm := StandardMaterial3D.new(); sm.albedo_color = Color(0.42, 0.36, 0.27); sm.roughness = 1.0
	pm.material = sm
	skirt.mesh = pm
	skirt.position.y = -1.5
	add_child(skirt)


## Packs up to four FastNoiseLite layers ([seed, frequency per pixel, octaves, optional noise type]) into one RGBA8
## texture, so the terrain shader reads four independent noises with one tap. Generated at load: no shipped images.
static func _noise_rgba(size: int, seamless: bool, layers: Array, mipmaps: bool) -> ImageTexture:
	var ch: Array[PackedByteArray] = []
	for L in layers:
		var fn := FastNoiseLite.new()
		fn.seed = L[0]; fn.frequency = L[1]; fn.fractal_octaves = L[2]
		if L.size() > 3:
			fn.noise_type = L[3]
			if fn.noise_type == FastNoiseLite.TYPE_CELLULAR:
				fn.cellular_return_type = FastNoiseLite.RETURN_DISTANCE2_DIV
				fn.fractal_type = FastNoiseLite.FRACTAL_NONE
		var im: Image = fn.get_seamless_image(size, size, false, false, 0.15) if seamless else fn.get_image(size, size)
		if im.get_format() != Image.FORMAT_L8: im.convert(Image.FORMAT_L8)
		ch.append(im.get_data())
	while ch.size() < 4: ch.append(ch[0])
	var c0 := ch[0]; var c1 := ch[1]; var c2 := ch[2]; var c3 := ch[3]
	var buf := PackedByteArray(); buf.resize(size * size * 4)
	for i in size * size:
		var j := i * 4
		buf[j] = c0[i]; buf[j + 1] = c1[i]; buf[j + 2] = c2[i]; buf[j + 3] = c3[i]
	var img := Image.create_from_data(size, size, false, Image.FORMAT_RGBA8, buf)
	if mipmaps: img.generate_mipmaps()
	return ImageTexture.create_from_image(img)


func _build_chunk(c: Vector2i) -> void:
	var ix0 := c.x * CHUNK_CELLS; var iz0 := c.y * CHUNK_CELLS
	var ix1 := mini(ix0 + CHUNK_CELLS, n - 1); var iz1 := mini(iz0 + CHUNK_CELLS, n - 1)
	if ix1 <= ix0 or iz1 <= iz0: return
	var w := ix1 - ix0 + 1; var d := iz1 - iz0 + 1
	var verts := PackedVector3Array(); verts.resize(w * d)
	var norms := PackedVector3Array(); norms.resize(w * d)
	var uvs := PackedVector2Array(); uvs.resize(w * d)
	for jz in d:
		for jx in w:
			var ix := ix0 + jx; var iz := iz0 + jz
			var wx := origin.x + ix * step; var wz := origin.y + iz * step
			var k := jz * w + jx
			verts[k] = Vector3(wx, _h(ix, iz), wz)
			var hx := _h(ix + 1, iz) - _h(ix - 1, iz)
			var hz := _h(ix, iz + 1) - _h(ix, iz - 1)
			norms[k] = Vector3(-hx, 2.0 * step, -hz).normalized()
			uvs[k] = Vector2(float(ix) / (n - 1), float(iz) / (n - 1))
	var idx := PackedInt32Array()
	idx.resize((w - 1) * (d - 1) * 6)
	var q := 0
	for jz in d - 1:
		for jx in w - 1:
			var a := jz * w + jx; var b := a + 1; var cc := a + w; var dd := cc + 1
			idx[q] = a; idx[q + 1] = b; idx[q + 2] = cc
			idx[q + 3] = b; idx[q + 4] = dd; idx[q + 5] = cc
			q += 6
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_INDEX] = idx
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	am.surface_set_material(0, mat)
	var mi: MeshInstance3D = chunks.get(c)
	if mi == null:
		mi = MeshInstance3D.new()
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		add_child(mi)
		chunks[c] = mi
	mi.mesh = am


## Rasterises the road polylines of map.json into a mask texture (same grid as the heightfield).
func _bake_roads() -> void:
	var buf := PackedByteArray(); buf.resize(n * n)
	for r in data.get("roads", []):
		var pts: Array = r.get("points", [])
		var wd: float = float(r.get("width_m", 8.0))
		for i in pts.size() - 1:
			var a := Vector2(pts[i][0], pts[i][1]); var b := Vector2(pts[i + 1][0], pts[i + 1][1])
			var segs := int(ceil(a.distance_to(b) / (step * 0.5)))
			for s in segs + 1:
				var p := a.lerp(b, float(s) / maxf(segs, 1))
				var rad := int(ceil(wd * 0.5 / step))
				var cx := int(round((p.x - origin.x) / step)); var cz := int(round((p.y - origin.y) / step))
				for dz in range(-rad, rad + 1):
					for dx in range(-rad, rad + 1):
						var x := cx + dx; var z := cz + dz
						if x < 0 or z < 0 or x >= n or z >= n: continue
						var dist := Vector2(dx, dz).length() * step
						var v := int(clampf(1.0 - (dist - wd * 0.3) / (wd * 0.4), 0.0, 1.0) * 255.0)
						if v > buf[z * n + x]: buf[z * n + x] = v
	# two box-blur passes soften the 2 m raster so road edges are not stair-stepped
	for pass_i in 2:
		var src := buf.duplicate()
		for z in range(1, n - 1):
			for x in range(1, n - 1):
				var acc := 0
				for dz in [-1, 0, 1]:
					var row: int = (z + dz) * n
					acc += src[row + x - 1] + src[row + x] + src[row + x + 1]
				buf[z * n + x] = acc / 9
	road_mask = Image.create_from_data(n, n, false, Image.FORMAT_L8, buf)


## Fraction of road at a world point (pathfinding cost / wheeled speed).
func road_at(x: float, z: float) -> float:
	var ix := clampi(int(round((x - origin.x) / step)), 0, n - 1)
	var iz := clampi(int(round((z - origin.y) / step)), 0, n - 1)
	return road_bytes[iz * n + ix] / 255.0


## Splat weights at a world point: x rock, y gravel, z scrub, w riverbed (sand = rest).
func splat_at(x: float, z: float) -> Color:
	if splat_bytes.is_empty(): return Color(0, 0, 0, 0)
	var ix := clampi(int(round((x - origin.x) / step)), 0, n - 1)
	var iz := clampi(int(round((z - origin.y) / step)), 0, n - 1)
	var i := (iz * n + ix) * 4
	return Color(splat_bytes[i] / 255.0, splat_bytes[i + 1] / 255.0, splat_bytes[i + 2] / 255.0, splat_bytes[i + 3] / 255.0)


## Movement cost of the ground at a point for a cost table {"sand", "gravel", "rock", "riverbed", "scrub", "road"}:
## splat-weighted material cost (sand = the remainder), blended toward the road cost by the road mask.
func material_cost(x: float, z: float, cost: Dictionary) -> float:
	var sp := splat_at(x, z)
	var sand := clampf(1.0 - sp.r - sp.g - sp.b - sp.a, 0.0, 1.0)
	var w := sand * float(cost.get("sand", 1.0)) + sp.r * float(cost.get("rock", 1.0)) + sp.g * float(cost.get("gravel", 1.0)) \
		+ sp.b * float(cost.get("scrub", 1.0)) + sp.a * float(cost.get("riverbed", 1.0))
	w /= maxf(sand + sp.r + sp.g + sp.b + sp.a, 0.001)
	return lerpf(w, float(cost.get("road", 1.0)), clampf(road_at(x, z) * 1.5, 0.0, 1.0))

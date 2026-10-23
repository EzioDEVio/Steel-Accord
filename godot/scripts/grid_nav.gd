# Steel Accord - deterministic grid pathfinding for surface units (AStarGrid2D, 2 m cells).
# Replaces the baked navigation mesh so that structures placed during a match update pathing instantly and
# identically on every run (no asynchronous re-bake). Paths are string-pulled with a grid line-of-sight test.
class_name GridNav
extends RefCounted

var CELL := 2.0
var origin := Vector2(-330, -330)
var n := 330
var astar := AStarGrid2D.new()
var static_solid := {}      # Vector2i -> true (terrain obstacles)
var owners := {}            # Vector2i -> count of structures covering the cell


var move_class := "any"
var slope_cells := 0         # cells made impassable by terrain slope (diagnostics)


func _init(half_size: float, cell := 2.0) -> void:
	CELL = cell
	n = int(ceil(half_size * 2.0 / CELL))
	origin = Vector2(-half_size, -half_size)
	astar.region = Rect2i(0, 0, n, n)
	astar.cell_size = Vector2(CELL, CELL)
	astar.diagonal_mode = AStarGrid2D.DIAGONAL_MODE_ONLY_IF_NO_OBSTACLES
	astar.default_compute_heuristic = AStarGrid2D.HEURISTIC_OCTILE
	astar.default_estimate_heuristic = AStarGrid2D.HEURISTIC_OCTILE
	astar.jumping_enabled = true
	astar.update()


func cell_of(p: Vector3) -> Vector2i:
	return Vector2i(clampi(int(floor((p.x - origin.x) / CELL)), 0, n - 1), clampi(int(floor((p.z - origin.y) / CELL)), 0, n - 1))


func center_of(c: Vector2i) -> Vector3:
	return Vector3(origin.x + (c.x + 0.5) * CELL, 0, origin.y + (c.y + 0.5) * CELL)


func is_blocked(c: Vector2i) -> bool:
	if c.x < 0 or c.y < 0 or c.x >= n or c.y >= n: return true
	return astar.is_point_solid(c)


func blocked_at(p: Vector3) -> bool:
	return is_blocked(cell_of(p))


## Marks a world-space rectangle (centre, half extents, yaw) as terrain obstacle, grown by `grow` metres.
func block_box(center: Vector3, half: Vector2, yaw: float, grow: float) -> void:
	for c in _cells_in_box(center, half + Vector2(grow, grow), yaw):
		static_solid[c] = true
		astar.set_point_solid(c, true)


func block_circle(center: Vector3, r: float) -> void:
	var c0 := cell_of(center - Vector3(r, 0, r)); var c1 := cell_of(center + Vector3(r, 0, r))
	for y in range(c0.y, c1.y + 1):
		for x in range(c0.x, c1.x + 1):
			var c := Vector2i(x, y)
			if center_of(c).distance_to(Vector3(center.x, 0, center.z)) <= r:
				static_solid[c] = true
				astar.set_point_solid(c, true)


## Structure footprints are reference counted so overlapping walls / removal behave. `yaw` rotates the footprint
## (placement rotation). Thin footprints are widened to 0.75 cell per side so a diagonal wall still rasterises to a
## 4-connected band of cells (no corner gaps a path could slip through).
func set_structure(center: Vector3, half: Vector2, on: bool, yaw := 0.0) -> void:
	var h := Vector2(maxf(half.x, CELL * 0.75), maxf(half.y, CELL * 0.75))
	for c in _cells_in_box(center, h, yaw):
		var k: int = int(owners.get(c, 0)) + (1 if on else -1)
		if k <= 0: owners.erase(c)
		else: owners[c] = k
		astar.set_point_solid(c, k > 0 or static_solid.has(c))


func box_free(center: Vector3, half: Vector2, yaw := 0.0) -> bool:
	for c in _cells_in_box(center, half, yaw):
		if is_blocked(c): return false
	return true


## Like box_free, but ignores structures (terrain obstacles, slopes and props only).
func box_free_static(center: Vector3, half: Vector2, yaw := 0.0) -> bool:
	for c in _cells_in_box(center, half, yaw):
		if c.x < 0 or c.y < 0 or c.x >= n or c.y >= n or static_solid.has(c): return false
	return true


func _cells_in_box(center: Vector3, half: Vector2, yaw: float) -> Array:
	var out: Array = []
	var r := half.length()
	var c0 := cell_of(center - Vector3(r, 0, r)); var c1 := cell_of(center + Vector3(r, 0, r))
	var cs := cos(yaw); var sn := sin(yaw)
	for y in range(c0.y, c1.y + 1):
		for x in range(c0.x, c1.x + 1):
			var p := center_of(Vector2i(x, y)) - Vector3(center.x, 0, center.z)
			var lx := p.x * cs - p.z * sn
			var lz := p.x * sn + p.z * cs
			if absf(lx) <= half.x and absf(lz) <= half.y:
				out.append(Vector2i(x, y))
	return out


func nearest_free(c: Vector2i) -> Vector2i:
	if not is_blocked(c): return c
	for r in range(1, 40):
		var best := Vector2i(-1, -1); var bd := INF
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				if absi(dx) != r and absi(dy) != r: continue
				var q := c + Vector2i(dx, dy)
				if not is_blocked(q):
					var d := float(dx * dx + dy * dy)
					if d < bd: bd = d; best = q
		if best.x >= 0: return best
	return c


func line_clear(a: Vector3, b: Vector3) -> bool:
	var d := Vector2(b.x - a.x, b.z - a.z)
	var steps := int(ceil(d.length() / (CELL * 0.5)))
	for i in range(1, steps):
		var t := float(i) / steps
		if blocked_at(a.lerp(b, t)): return false
	return true


func find_path(from: Vector3, to: Vector3) -> PackedVector3Array:
	var a := nearest_free(cell_of(from))
	var b := nearest_free(cell_of(to))
	var goal := to if not blocked_at(to) else center_of(b)
	if line_clear(from, goal): return PackedVector3Array([from, goal])
	var ids := astar.get_id_path(a, b)
	if ids.is_empty(): return PackedVector3Array([from, goal])
	var raw: Array[Vector3] = [from]
	for i in range(1, ids.size() - 1): raw.append(center_of(ids[i]))
	raw.append(goal)
	# string pulling, forward and greedy: from each anchor walk ahead while the straight line stays clear.
	# (The old backward scan from the end of the path was quadratic and stalled the game on long routes.)
	var out := PackedVector3Array([from])
	var i := 0
	var n := raw.size()
	while i < n - 1:
		var j := i + 1
		while j + 1 < n and j - i < 48 and line_clear(raw[i], raw[j + 1]): j += 1
		out.append(raw[j]); i = j
	return out


## Heightfield maps: cells steeper than `max_slope_deg` become impassable for this movement class; passable cells
## cost the class's material cost (map.json "movement".<class>.cost) and more the steeper they are (A* weights;
## jumping is disabled so weights count).
func apply_terrain(tm: TerrainMap, cls: String, rules: Dictionary) -> void:
	move_class = cls
	astar.jumping_enabled = false
	var max_s: float = float(rules.get("max_slope_deg", 30.0))
	var k_slope: float = float(rules.get("slope_cost", 1.0))
	var cost: Dictionary = rules.get("cost", {})
	for y in n:
		for x in n:
			var c := Vector2i(x, y)
			var p := center_of(c)
			# steepest baked sample slope inside the cell, so a narrow cliff band is not skipped
			var s := tm.max_slope_in(p.x, p.z, CELL * 0.5)
			if s > max_s:
				static_solid[c] = true
				astar.set_point_solid(c, true)
				slope_cells += 1
				continue
			var w := tm.material_cost(p.x, p.z, cost) * (1.0 + k_slope * (s / max_s) * (s / max_s))
			astar.set_point_weight_scale(c, maxf(w, 0.2))


## Walls / boundaries supplied as polylines (map.json "blockers").
func block_segment(a: Vector3, b: Vector3, r: float) -> void:
	var steps := int(ceil(a.distance_to(b) / (CELL * 0.5))) + 1
	for i in steps + 1:
		block_circle(a.lerp(b, float(i) / steps), r)


## A* travel cost between two points (cell steps x terrain weight, metres): the quantity the planner minimises, so
## it is the fair measure of how far a site is for a movement class (string-pulled lengths depend on tie-breaking).
func path_cost(from: Vector3, to: Vector3) -> float:
	var ids := astar.get_id_path(nearest_free(cell_of(from)), nearest_free(cell_of(to)))
	var c := 0.0
	for i in range(1, ids.size()):
		var step := Vector2(ids[i] - ids[i - 1]).length() * CELL
		c += step * astar.get_point_weight_scale(ids[i])
	return c

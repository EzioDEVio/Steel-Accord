# Steel Accord - VFX regression checks (headless OK):  godot --headless --path godot --fixed-fps 30 -- army noair vfxtest out=/dir
# 1. every explosion size spawns its layers; after their lifetime the emitters / lights are recycled and the node
#    count returns to the warmed-up baseline (no leaks); Low draws fewer layers than High
# 2. impact kinds and muzzle kinds spawn and free
# 3. destroying a structure (command centre, civic block) gives a collapse and a ruin with >= N pieces inside its
#    footprint; rubble does not block movement; the ruin survives save -> load with the same pieces
# 4. vehicle / aircraft / infantry deaths: secondary blast, burning wreck that cools and stops, crash, no gore
# 5. particle and light caps hold under a mass barrage
extends Node

var battle: Node
var out := "user://test_output/vfxtest"
var checks: Array = []


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="): out = a.substr(4)
	DirAccess.make_dir_recursive_absolute(out)
	_run()


func _log(name: String, ok: bool, detail := "") -> void:
	checks.append([name, ok, detail])
	printerr("TEST %s %s %s" % [name, "PASS" if ok else "FAIL", detail])


func _wait_sim(t: float) -> void:
	var end: float = battle.sim_time + t
	while battle.sim_time < end:
		await get_tree().process_frame


func _frames(n := 3) -> void:
	for i in n: await get_tree().process_frame


func _look(p: Vector3, zoom := 60.0) -> void:
	var cam: RTSCamera = battle.camera
	cam.zoom = zoom; cam._apply()
	cam.focus(p)


func _nodes() -> int:
	return int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))


func _structure(kind: String, team: int, p: Vector3) -> Building:
	var b := Building.new()
	battle.add_child(b)
	b.setup_structure(battle, kind, team, battle.new_uid(), battle.grounded(p), true)
	battle.units.append(b)
	battle.by_id[b.uid] = b
	return b


func _quiet(d: FXDirector) -> bool:
	return d.active.is_empty() and d.lights.is_empty() and d.q.is_empty() and d.live_particles == 0


func _run() -> void:
	await _wait_sim(0.5)
	battle.ai = null
	battle.camera.edge_pan = false
	Game.settings["graphics"] = "Medium"
	var P := Vector3(-150, 0, 40)
	_look(P, 60.0)
	FX.explosion(battle, battle.grounded(P), 1.0)   # creates the director
	await _frames(2)
	var d: FXDirector = battle.get_node_or_null("FXDirector")
	_log("director", d != null, "FXDirector under the battle")
	if d == null:
		_finish(); return
	await _wait_sim(12.0)

	# ---- 1. explosion layers per size, then recycled
	var want := {"small": ["flash", "fireball", "smoke", "sparks", "dust", "scorch"],
		"medium": ["flash", "fireball", "smoke", "sparks", "debris", "dust_ring", "dust", "scorch", "light"],
		"large": ["flash", "fireball", "smoke", "sparks", "embers", "debris", "dust_ring", "dust", "scorch", "light"],
		"huge": ["flash", "fireball", "smoke", "sparks", "embers", "debris", "dust_ring", "dust", "scorch", "light", "shock"]}
	# warm-up: the same 3-round barrage as the repeat check below fills the emitter / light pools; baseline after it
	for r in 3:
		for sz in want: FX.explosion(battle, battle.grounded(P) + Vector3(r * 5, 0.2, 0), 1.0, sz)
		await _wait_sim(0.5)
	await _wait_sim(14.0)
	var base_nodes := _nodes()
	var base_decals := d.decals.size()
	for sz in want:
		d.tag_log.clear()
		FX.explosion(battle, battle.grounded(P) + Vector3(0, 0.2, 0), 1.0, sz)
		await _wait_sim(0.4)
		var miss: Array = []
		for tg in want[sz]:
			if not d.tag_log.has(tg): miss.append(tg)
		_log("explosion_layers_" + sz, miss.is_empty(), "layers %s; missing %s; live particles %d" % [str(d.tag_log.keys()), str(miss), d.live_particles])
	await _wait_sim(14.0)
	var new_decals := d.decals.size() - base_decals
	_log("explosion_freed", _quiet(d) and _nodes() <= base_nodes + new_decals,
		"active emitters %d, lights %d, live particles %d; nodes %d -> %d (+%d new scorch decals allowed), pooled emitters %d" % [d.active.size(), d.lights.size(),
		d.live_particles, base_nodes, _nodes(), new_decals, d.pool_p.size()])
	# repeated rounds must not grow the node count beyond the decal cap
	for r in 3:
		for sz in want: FX.explosion(battle, battle.grounded(P) + Vector3(r * 5, 0.2, 0), 1.0, sz)
		await _wait_sim(0.5)
	await _wait_sim(14.0)
	var grown := _nodes() - base_nodes - (d.decals.size() - base_decals)
	_log("no_leak_repeat", _quiet(d) and grown <= 0, "3 more rounds: node growth beyond new decals = %d" % grown)
	# presets: Low draws fewer layers / particles than High
	var counts := {}
	for g in ["Low", "High"]:
		Game.settings["graphics"] = g
		d.tag_log.clear()
		var before: int = d.stats.spawned
		var p0 := d.live_particles
		FX.explosion(battle, battle.grounded(P) + Vector3(0, 0.2, 0), 1.0, "large")
		await _wait_sim(0.4)
		counts[g] = [d.stats.spawned - before, d.live_particles - p0, d.tag_log.keys().size()]
		await _wait_sim(10.0)
	Game.settings["graphics"] = "Medium"
	_log("preset_scaling", counts.Low[1] < counts.High[1] and counts.Low[2] <= counts.High[2],
		"large blast: Low %d layers / %d particles, High %d layers / %d particles" % [counts.Low[0], counts.Low[1], counts.High[0], counts.High[1]])
	# off screen small effects are skipped (scorch still placed)
	var sk: int = d.stats.skipped_lod
	FX.impact_kind(battle, Vector3(250, 0.2, -250), "bullet", "ground")
	FX.explosion(battle, battle.grounded(Vector3(250, 0, -250)), 1.0, "small")
	await _frames(3)
	_log("offscreen_lod", d.stats.skipped_lod >= sk + 2, "off-screen effects skipped: %d" % (d.stats.skipped_lod - sk))

	# ---- 2. impacts and muzzles
	d.tag_log.clear()
	var surf := {"bullet": ["ground", "armour", "structure", "infantry"], "cannon": ["ground", "armour"], "shell": ["ground", "armour"],
		"rocket": ["ground", "structure"], "arty": ["ground"], "bomb": ["ground"]}
	var i := 0
	for k in surf:
		for s in surf[k]:
			FX.impact_kind(battle, battle.grounded(P + Vector3(-12 + (i % 6) * 5, 0, (i / 6) * 5)) + Vector3(0, 0.3, 0), k, s)
			i += 1
	for mk in FX.MUZZLE:
		FX.muzzle(battle, battle.grounded(P) + Vector3(0, 2, 0), Vector3(0, 0, -1), mk)
	await _wait_sim(0.3)
	var need := ["dust_hit", "spark_hit", "chips", "muzzle_flash", "muzzle_ring", "backblast", "fireball"]
	var miss2 := need.filter(func(x): return not d.tag_log.has(x))
	_log("impacts_and_muzzles", miss2.is_empty(), "tags %s; missing %s" % [str(d.tag_log.keys()), str(miss2)])
	await _wait_sim(14.0)
	_log("impacts_freed", _quiet(d), "active %d lights %d" % [d.active.size(), d.lights.size()])

	# ---- 3. structure destruction, ruin, save/load
	var C := Vector3(-150, 0, -90)
	_look(C, 85.0)
	var cc := _structure("command_center", 0, C)
	await _wait_sim(0.5)
	d.tag_log.clear()
	cc.take_damage(cc.hp + 100.0, null)
	await _frames(4)
	var rb: Dictionary = battle.rubble_at(C, 0)
	var node: Node3D = rb.get("node")
	var pieces := int(node.get_meta("pieces", 0)) if node else 0
	var inside := 0
	var half: Vector2 = cc.half
	if node:
		for v in node.get_meta("piece_xz", PackedVector2Array()):
			if absf(v.x) <= half.x + 2.5 and absf(v.y) <= half.y + 2.5: inside += 1
	_log("cc_ruin", pieces >= 60 and inside == pieces and d.tag_log.has("collapse") and d.tag_log.has("ruin"),
		"pieces %d (all within footprint %.0fx%.0f m + 2.5 m spill: %d), collapse=%s ruin=%s" % [pieces, half.x * 2, half.y * 2, inside, d.tag_log.has("collapse"), d.tag_log.has("ruin")])
	var kinds: Array = []
	if node:
		for c in node.get_children():
			if c is MultiMeshInstance3D: kinds.append(String(c.name).trim_prefix("Ruin_"))
	var has_all := ["wall_", "slab_", "mound_", "chunk_"].all(func(pre): return kinds.any(func(k): return k.begins_with(pre)))
	_log("ruin_parts", has_all and node.get_node_or_null("RuinAsh") != null, "piece types %s, ash decal %s" % [str(kinds), str(node.get_node_or_null("RuinAsh") != null)])
	var pal: Dictionary = node.get_meta("palette", {}) if node else {}
	_log("ruin_tinted_from_model", str(pal.get("src", "default")) != "default", "palette from %s: wall %s trim %s" % [str(pal.get("src")), str(pal.get("wall")), str(pal.get("trim"))])
	_log("ruin_not_blocking", not battle.gnav.blocked_at(C + Vector3(3, 0, 3)), "")
	var A := Vector3(-40, 0, -90)
	var civ: Building = battle.add_civic("civ_apartment", A, false)
	var civ_pieces := 0
	var civ_pal := {}
	if civ:
		await _wait_sim(0.3)
		civ.take_damage(civ.hp + 100.0, null)
		await _frames(4)
		var crb: Dictionary = battle.rubble_at(A, -2)
		if crb.has("node"):
			civ_pieces = int(crb.node.get_meta("pieces", 0))
			civ_pal = crb.node.get_meta("palette", {})
	_log("civic_ruin", civ_pieces >= 30 and str(civ_pal.get("wall")) != str(pal.get("wall")),
		"apartment ruin pieces %d, wall colour %s vs command centre %s" % [civ_pieces, str(civ_pal.get("wall")), str(pal.get("wall"))])
	# linger: smoke / fire emitters attached to the ruin exist now
	var lingering := 0
	if node:
		for c in node.get_children(): if c is CPUParticles3D: lingering += 1
	_log("ruin_smoke", lingering >= 2, "%d smoke / fire emitters on the ruin" % lingering)
	# save -> load: same ruins, same pieces
	var sig0: Array = battle.rubble.map(func(r): return [r.kind, r.seed, int(r.node.get_meta("pieces", 0)) if is_instance_valid(r.node) else -1,
		(r.node.get_meta("piece_xz", PackedVector2Array()) as PackedVector2Array).slice(0, 5) if is_instance_valid(r.node) else []])
	var path := out + "/vfx_ruin.sav"
	SaveGame.write(path, SaveGame.capture(battle))
	SaveGame.restore(battle, SaveGame.read(path))
	await _frames(5)
	var sig1: Array = battle.rubble.map(func(r): return [r.kind, r.seed, int(r.node.get_meta("pieces", 0)) if is_instance_valid(r.node) else -1,
		(r.node.get_meta("piece_xz", PackedVector2Array()) as PackedVector2Array).slice(0, 5) if is_instance_valid(r.node) else []])
	_log("ruin_save_load", sig0.size() >= 2 and str(sig0) == str(sig1), "%d ruins; before %s; after %s" % [sig0.size(), str(sig0.map(func(x): return x.slice(0, 3))), str(sig1.map(func(x): return x.slice(0, 3)))])
	var ra: Dictionary = battle.rubble_at(C, 0)
	_log("rebuild_clears_ruin", true if ra.is_empty() else _clear_ok(ra), "")

	# ---- 4. deaths
	_look(P, 60.0)
	var tank: Unit = battle._spawn("vanguard", 1, P + Vector3(0, 0, -8), PI)
	var heli: Unit = battle._spawn("ah64", 0, P + Vector3(16, 0, 0), 0.0)
	var inf: Unit = battle._spawn("rifleman", 1, P + Vector3(-12, 0, 0), PI)
	await _wait_sim(0.3)
	d.tag_log.clear()
	tank.take_damage(tank.hp + 50.0, null)
	inf.take_damage(inf.hp + 50.0, null)
	await _wait_sim(1.6)
	var fb := int(d.tag_log.get("fireball", 0))
	_log("vehicle_death", fb >= 2 and d.tag_log.has("wreck_fire"), "fireballs %d (blast + secondary), wreck fire %s" % [fb, str(d.tag_log.has("wreck_fire"))])
	var wreck_emitters := tank.body.find_children("*", "CPUParticles3D", true, false).size()
	_log("infantry_death_no_gore", d.tag_log.has("dust_hit"), "dust puff only; body fades after 3 s")
	d.tag_log.clear()
	heli.altitude = 25.0; heli.body.position.y = 25.0
	heli.take_damage(heli.hp + 50.0, null)
	await _frames(3)
	var trail := d.tag_log.has("burn_trail")
	await _wait_sim(4.0)
	_log("aircraft_death", trail and int(d.tag_log.get("fireball", 0)) >= 2 and d.tag_log.has("wreck_fire"),
		"burning trail %s, blasts %d (air + crash), wreck fire %s" % [str(trail), int(d.tag_log.get("fireball", 0)), str(d.tag_log.has("wreck_fire"))])
	# the wreck fire cools and stops (Medium: 50 s x 0.8)
	await _wait_sim(48.0)
	var left := tank.body.find_children("*", "CPUParticles3D", true, false).size() if is_instance_valid(tank) else 0
	_log("wreck_cools_and_stops", wreck_emitters >= 2 and left == 0, "wreck emitters %d -> %d after 50 s" % [wreck_emitters, left])

	# ---- 5. caps under a mass barrage
	var peak := 0
	var peak_l := 0
	d.stats.peak_particles = 0
	for k in 40:
		for j in 8:
			var p: Vector3 = battle.grounded(P + Vector3(randf_range(-40, 40), 0, randf_range(-30, 30))) + Vector3(0, 0.3, 0)
			FX.explosion(battle, p, 1.0, ["medium", "large", "huge"][j % 3])
			FX.impact_kind(battle, p, "bullet", "ground")
		await _frames(1)
		peak = maxi(peak, d.live_particles)
		peak_l = maxi(peak_l, d.lights.size())
	await _wait_sim(2.0)
	_log("particle_cap_holds", d.stats.peak_particles <= int(d.Q.particles) and peak_l <= int(d.Q.lights),
		"320 blasts + 320 impacts in 40 frames: peak particles %d (cap %d), peak lights %d (cap %d), skipped %d" % [d.stats.peak_particles, int(d.Q.particles), peak_l, int(d.Q.lights), d.stats.skipped_cap])
	_log("decal_cap_holds", d.decals.size() <= int(d.Q.decals), "scorch decals %d (cap %d)" % [d.decals.size(), int(d.Q.decals)])
	_finish()


func _clear_ok(ra: Dictionary) -> bool:
	battle._clear_rubble(ra.pos, ra.half)
	return battle.rubble_at(ra.pos, 0).is_empty()


func _finish() -> void:
	var passed := checks.filter(func(c): return c[1]).size()
	printerr("TEST DONE %d/%d" % [passed, checks.size()])
	print("RESULT %d/%d" % [passed, checks.size()])
	var f := FileAccess.open(out + "/vfxtest_result.txt", FileAccess.WRITE)
	if f:
		for c in checks: f.store_line("%s %s %s" % [c[0], "PASS" if c[1] else "FAIL", c[2]])
		f.store_line("RESULT %d/%d" % [passed, checks.size()])
	await get_tree().create_timer(0.3).timeout
	get_tree().quit()

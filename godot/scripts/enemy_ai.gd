# Steel Accord - G1 opponent behaviour (deterministic: driven only by sim ticks and state).
# Holds a defensive position until it sees the enemy or its timer expires, then attack-moves as a group
# toward the nearest known enemy cluster, regrouping stragglers. Replaced by the full skirmish AI in G3.
class_name EnemyAI
extends RefCounted

var battle: Node
var team := 1
var think_t := 0.0
var attack_after := 25.0
var attacking := false


func _init(b: Node, t: int, delay: float) -> void:
	battle = b; team = t; attack_after = delay


func tick(dt: float) -> void:
	think_t -= dt
	if think_t > 0.0: return
	think_t = 2.0
	var mine: Array = battle.units.filter(func(u): return u.team == team and not u.dead)
	var foes: Array = battle.units.filter(func(u): return u.team != team and not u.dead)
	if mine.is_empty() or foes.is_empty(): return
	var engaged := mine.any(func(u): return u.target != null)
	if not attacking and (battle.sim_time >= attack_after or engaged):
		attacking = true
	if not attacking: return
	# target: centroid of the enemy units nearest to our centroid
	var c := Vector3.ZERO
	for u in mine: c += u.position
	c /= mine.size()
	foes.sort_custom(func(a, b): return a.position.distance_squared_to(c) < b.position.distance_squared_to(c))
	var tgt := Vector3.ZERO
	var k := mini(3, foes.size())
	for i in k: tgt += foes[i].position
	tgt /= k
	var idle_ids: Array = []
	for u in mine:
		if u.state == Unit.S.IDLE and u.target == null:
			idle_ids.append(u.uid)
	if idle_ids.is_empty(): return
	var pts: Array = []
	for i in idle_ids.size():
		var ang := TAU * i / idle_ids.size()
		pts.append(tgt + Vector3(cos(ang), 0, sin(ang)) * 6.0)
	battle.issue({"type": "attack_move", "ids": idle_ids, "points": pts})

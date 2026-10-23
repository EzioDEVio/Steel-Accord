# Steel Accord - per-unit veterancy (individual promotion; separate from any player-wide commander rank).
# Units earn XP for kills (victim value) and support units for meaningful support (healing / repairing).
# Bonuses are class-appropriate and data-driven; every bonus is applied in the simulation and listed in the
# inspector. Thresholds and multipliers are PROVISIONAL.
class_name Veterancy

const RANKS := ["Recruit", "Veteran", "Elite", "Heroic"]
const XP_TO_RANK := [0.0, 100.0, 250.0, 500.0]

## Per class and rank: damage dealt, damage taken, weapon reload time. Heroic units also self-repair.
const BONUS := {
	"infantry": {"dmg": [1.0, 1.10, 1.20, 1.30], "taken": [1.0, 0.90, 0.85, 0.80], "reload": [1.0, 1.0, 0.92, 0.85]},
	"vehicle": {"dmg": [1.0, 1.05, 1.10, 1.20], "taken": [1.0, 0.85, 0.75, 0.65], "reload": [1.0, 0.95, 0.90, 0.85]},
	"aircraft": {"dmg": [1.0, 1.10, 1.20, 1.30], "taken": [1.0, 0.90, 0.85, 0.80], "reload": [1.0, 0.90, 0.80, 0.70]},
}
const HEROIC_REPAIR := 0.01        # fraction of max health per second at Heroic


static func vclass(u: Unit) -> String:
	if u.def.get("visual") == "infantry": return "infantry"
	if u.domain in ["jet", "heli"]: return "aircraft"
	return "vehicle"


## Units that can be promoted: combat units and healers / repairers. Builders, haulers and structures cannot.
static func eligible(u: Unit) -> bool:
	if u is Building or u.def.get("builder", false) or u.def.get("hauler", false): return false
	return not u.def.get("weapons", []).is_empty() or u.def.has("heal")


static func value_of(u: Unit) -> float:
	if u is Building: return float((u as Building).bdef.cost)
	if BuildingDefs.UNIT_COST.has(u.kind): return float(BuildingDefs.UNIT_COST[u.kind][0])
	return u.def.hp


static func kill_xp(victim: Unit) -> float:
	return value_of(victim) / 10.0


static func mult(u: Unit, key: String) -> float:
	if u == null or u.vet_rank == 0: return 1.0
	return float(BONUS[vclass(u)][key][u.vet_rank])


static func next_xp(u: Unit) -> float:
	return XP_TO_RANK[u.vet_rank + 1] if u.vet_rank < RANKS.size() - 1 else -1.0


## Plain-language list of the bonuses this unit currently has.
static func bonus_lines(u: Unit) -> Array:
	if u.vet_rank == 0: return []
	var b: Dictionary = BONUS[vclass(u)]
	var out: Array = []
	var r := u.vet_rank
	if b.dmg[r] != 1.0: out.append("+%d%% damage" % int(round((b.dmg[r] - 1.0) * 100.0)))
	if b.taken[r] != 1.0: out.append("-%d%% damage taken" % int(round((1.0 - b.taken[r]) * 100.0)))
	if b.reload[r] != 1.0: out.append("%d%% faster reload" % int(round((1.0 - b.reload[r]) * 100.0)))
	if r == 3: out.append("self-repair %d%%/s" % int(HEROIC_REPAIR * 100.0))
	return out

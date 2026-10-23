# Steel Accord - researched upgrades and battle plans (M8). One authoritative table: the econ panel, the inspector,
# the AI and the simulation all read it. Each upgrade is researched once per team at one structure, costs cash up
# front (refunded on cancel), takes research time (half speed under low power) and has a real effect in the
# simulation on the units it lists. Values are PROVISIONAL first-pass tuning.
class_name Upgrades

const DEFS := {
	"adv_armor": {"name": "Advanced Combat Armor", "at": "barracks", "cost": 1000, "time": 30.0, "requires": ["barracks"],
		"scope": "infantry", "effect": {"taken": 0.85},
		"desc": "Improved body armour and plates for all infantry: -15% damage taken."},
	"composite_armor": {"name": "Composite Armor", "at": "war_factory", "cost": 1500, "time": 40.0, "requires": ["war_factory"],
		"scope": "armored", "effect": {"taken": 0.85},
		"desc": "Add-on composite armour for tracked and armoured vehicles: -15% damage taken."},
	"guided_munitions": {"name": "Guided Munitions", "at": "airfield", "cost": 1500, "time": 40.0, "requires": ["airfield"],
		"scope": "air_ground", "effect": {"dmg_ground": 1.15},
		"desc": "Precision-guided air-to-ground weapons: +15% damage against ground targets for aircraft with ground attack."},
	"supply_efficiency": {"name": "Supply Line Efficiency", "at": "supply_depot", "cost": 1200, "time": 35.0, "requires": ["supply_depot"],
		"scope": "economy", "effect": {"income": 1.10},
		"desc": "+10% cash from CH-47 deliveries, Supply Drop Zone crates and oil derricks (each source counted once)."},
	"adv_training": {"name": "Advanced Training", "at": "command_center", "cost": 1500, "time": 45.0, "requires": ["war_factory"],
		"scope": "veterans", "effect": {"xp": 1.5},
		"desc": "Combat units and medics earn veterancy 50% faster. Does not grant ranks by itself."},
}

## Battle plans: chosen at the Command Center once Advanced Training is researched; one active at a time, with a
## switching delay so plans cannot be toggled mid-fight.
const PLANS := {
	"assault": {"name": "Assault", "effect": {"dmg": 1.10}, "desc": "Ground units deal +10% damage."},
	"fortify": {"name": "Fortify", "effect": {"taken": 0.90, "speed": 0.95}, "desc": "Ground units take -10% damage but move 5% slower."},
	"recon": {"name": "Recon", "effect": {"sight": 1.20}, "desc": "All units see 20% further."},
}
const PLAN_REQUIRES := "adv_training"
const PLAN_SWITCH_S := 15.0

const SCOPE_TEXT := {"infantry": "all infantry", "armored": "tracked and armoured vehicles", "air_ground": "aircraft with ground-attack weapons",
	"economy": "supply income", "veterans": "units that can earn veterancy"}


## Does upgrade `id` affect unit `u`? (Economy upgrades affect no unit.)
static func applies(id: String, u: Unit) -> bool:
	if u is Building: return false
	match str(DEFS[id].scope):
		"infantry": return u.def.get("visual") == "infantry"
		"armored": return u.domain == "ground" and u.def.get("visual") != "infantry" and (u.move_class() == "tracked" or str(u.def.get("armor", "")) == "heavy" or u.def.get("category", "") in ["Armor", "Transport", "Artillery"])
		"air_ground": return u.is_air() and u.def.get("weapons", []).any(func(w): return "ground" in w.targets)
		"veterans": return Veterancy.eligible(u)
	return false


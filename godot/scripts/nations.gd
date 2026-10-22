# Steel Accord - playable nations. A nation chooses the flag, the display name and which units each structure offers.
# Structures are shared for now; Iran's infantry is its own (3D models with mixed shaved / bearded grooming and the
# IRGC special unit). Vehicles and aircraft for Iran wait for the Iran concept pack: until then the War Factory
# offers the shared development vehicles as clearly-labelled placeholders and the Airfield offers no aircraft yet
# (the shared aircraft carry U.S. insignia painted into their textures, which must stay U.S.-only). The Supply
# Depot's CH-47 hauler is the one shared aircraft kept for Iran so its economy works; it is marked placeholder. The setting is fictional; no nation is cast as the villain.
class_name Nations

const DEFS := {
	"usa": {"name": "United States", "short": "USA", "flag": "res://assets/units3d/props/flag_usa.glb", "produces": {}, "powers": []},
	"iran": {
		"name": "Iran", "short": "IRN", "flag": "res://assets/units3d/props/flag_iran.glb",
		"produces": {
			"barracks": ["ir_rifleman", "ir_rpg", "ir_mg", "ir_medic", "ir_sniper", "ir_engineer", "irgc_sf"],
			"war_factory": ["hmmwv_50cal", "mrap", "m113", "bradley", "abrams", "avenger", "paladin"],
			"airfield": [],
		},
		"unit_swap": {"paratrooper": "ir_paratrooper", "rifleman": "ir_rifleman", "at4": "ir_rpg", "m240_gunner": "ir_mg",
			"saw_gunner": "ir_mg", "medic": "ir_medic", "sniper": "ir_sniper", "eod_engineer": "ir_engineer", "special_forces": "irgc_sf",
			"ranger": "irgc_sf"},
		"placeholder": ["hmmwv_50cal", "mrap", "m113", "bradley", "abrams", "avenger", "paladin", "ch47", "dozer"],
	},
}

## Display order in the menus.
const ORDER := ["usa", "iran"]


static func exists(id: String) -> bool:
	return DEFS.has(id)


static func name_of(id: String) -> String:
	return str(DEFS.get(id, DEFS.usa).name)


## Units a structure offers for this nation (the U.S. list is the structure's own list in BuildingDefs).
static func produces(nation: String, bkind: String, base: Array) -> Array:
	var d: Dictionary = DEFS.get(nation, DEFS.usa)
	return d.produces.get(bkind, base)


## Nation-specific replacement of a shared unit kind (e.g. the paratroopers dropped by the support power).
static func swap_unit(nation: String, kind: String) -> String:
	var d: Dictionary = DEFS.get(nation, DEFS.usa)
	return str(d.get("unit_swap", {}).get(kind, kind))


## True when this nation uses a shared development model until its own art exists (shown in tooltips).
static func is_placeholder(nation: String, kind: String) -> bool:
	return kind in DEFS.get(nation, DEFS.usa).get("placeholder", [])


## A U.S.-keyed list (AI build mixes) translated to this nation and filtered to what `bkind` can actually produce.
static func mix(nation: String, bkind: String, base_list: Array, us_mix: Array) -> Array:
	var can := produces(nation, bkind, base_list)
	var out: Array = []
	for k in us_mix:
		var n := swap_unit(nation, k)
		if n in can: out.append(n)
	return out

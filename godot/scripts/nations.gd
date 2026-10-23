# Steel Accord - playable nations. A nation chooses the flag, the display name and which units each structure offers.
# Structures are shared for now; Iran's infantry is its own (3D models with mixed shaved / bearded grooming and the
# IRGC special unit). Iran's War Factory builds its own vehicles (Boragh, BMP-2, T-72S, Karrar) plus two clearly
# labelled shared placeholders (Avenger AA, Paladin artillery) until wave 2 (Khordad-3 / Raad-1) is integrated.
# Iranian aircraft (F-14, F-4, Su-24, AH-1J, CH-47C hauler, C-130 for drops) have their own models and markings;
# U.S. aircraft keep the U.S. star and are never used for Iran. The setting is fictional; no nation is cast as the villain.
class_name Nations

const DEFS := {
	"usa": {"name": "United States", "short": "USA", "flag": "res://assets/units3d/props/flag_usa.glb", "produces": {},
		"powers": ["carpet", "supersonic", "stealth", "paradrop", "recon"]},
	"iran": {
		"name": "Iran", "short": "IRN", "flag": "res://assets/units3d/props/flag_iran.glb",
		"produces": {
			"barracks": ["ir_rifleman", "ir_rpg", "ir_mg", "ir_medic", "ir_sniper", "ir_engineer", "irgc_sf"],
			"war_factory": ["ir_boragh", "ir_bmp2", "ir_t72s", "ir_karrar", "avenger", "paladin"],
			"command_center": ["ir_engineer_dozer"],
			"airfield": ["ir_f14", "ir_f4", "ir_su24", "ir_ah1j"],
			"supply_depot": ["ir_ch47"],
		},
		"unit_swap": {"paratrooper": "ir_paratrooper", "rifleman": "ir_rifleman", "at4": "ir_rpg", "m240_gunner": "ir_mg",
			"saw_gunner": "ir_mg", "medic": "ir_medic", "sniper": "ir_sniper", "eod_engineer": "ir_engineer", "special_forces": "irgc_sf",
			"ranger": "irgc_sf", "ch47": "ir_ch47", "dozer": "ir_engineer_dozer", "abrams": "ir_karrar", "bradley": "ir_bmp2", "stryker": "ir_boragh",
			"m113": "ir_bmp2", "hmmwv_50cal": "ir_boragh", "f16": "ir_f4", "a10": "ir_su24", "ah64": "ir_ah1j", "f22": "ir_f14", "fa18": "ir_su24"},
		"c130_model": "res://assets/units3d/ir_c130/ir_c130.glb",
		"powers": ["shahed", "paradrop"],
		"power_icons": {"paradrop": "res://assets/iran/icons/ir_c130_icon.png"},
		# Iran's own terminology for shared structures, research and battle plans (same mechanics, own names)
		"labels": {
			"command_center": "Command Headquarters", "power_plant": "Power Station", "barracks": "Garrison Barracks",
			"supply_depot": "Logistics Depot", "war_factory": "Armour Works", "airfield": "Air Base", "defense_tower": "Missile Post",
			# weapon display names (key "w:<weapon id>"; fictional, generic)
			"w:m4": "Assault rifle", "w:m4_medic": "Assault rifle", "w:m4_para": "Assault rifle", "w:m4_ranger": "Assault carbine",
			"w:at4": "RPG launcher", "w:m249": "PKM machine gun", "w:m240": "PKM machine gun", "w:mk17": "Marksman rifle",
			"w:120mm": "125mm main gun", "w:m2_cupola": "12.7mm cupola MG", "w:25mm": "30mm autocannon", "w:m2_apc": "12.7mm MG",
			"w:rws_stryker": "12.7mm remote MG", "w:tow": "ATGM", "w:atgm": "ATGM", "w:aim120": "Air-to-air missiles",
			"w:aam": "Air-to-air missiles", "w:agm": "Guided missiles", "w:agm_heavy": "Heavy guided missiles", "w:sdb": "Guided bombs",
			"w:jdam": "Guided bombs", "w:gau_cannon": "Autocannon", "w:rockets": "Rocket pods", "w:door_guns": "Door guns",
			"drop_zone": "Airdrop Zone", "radar": "Radar Station", "hesco": "Earth Barrier",
			"adv_armor": "Infantry Body Armour", "composite_armor": "Reactive Armour Kits", "guided_munitions": "Precision Strike Kits",
			"supply_efficiency": "Logistics Network", "adv_training": "Combat Training Programme",
			"assault": "Offensive Doctrine", "fortify": "Defensive Doctrine", "recon": "Reconnaissance Doctrine",
			"paradrop": "Airborne Insertion",
		},
		"placeholder": ["avenger", "paladin"],
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


## Support powers this nation can call (each uses that nation's own aircraft).
static func powers(nation: String) -> Array:
	return DEFS.get(nation, DEFS.usa).get("powers", [])


static func power_icon(nation: String, id: String) -> String:
	return str(DEFS.get(nation, DEFS.usa).get("power_icons", {}).get(id, UnitDefs.POWERS[id].icon))


## Nation-specific display name for a structure, upgrade, battle plan or power id (falls back to the shared name).
static func label(nation: String, id: String, fallback: String) -> String:
	return str(DEFS.get(nation, DEFS.usa).get("labels", {}).get(id, fallback))

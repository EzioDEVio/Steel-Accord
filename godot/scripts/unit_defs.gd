# Steel Accord - unit, weapon and support-power definitions (data).
# Values marked PROVISIONAL are first-pass tuning, not balanced. Real-world aircraft names are the client's
# working labels for the supplied concept art; see content/manifest/aircraft.json for release-review status.
class_name UnitDefs

const TEAM_COLORS := [Color(0.12, 0.30, 0.72), Color(0.70, 0.13, 0.10), Color(0.15, 0.55, 0.25), Color(0.75, 0.6, 0.1)]
const TEAM_NAMES := ["Blue", "Red", "Green", "Gold"]


## Colour of a team: the player's choice from the Skirmish screen (automated runs keep the defaults).
static func team_color(t: int) -> Color:
	if t < 0 or t > 1: return Color(0.6, 0.6, 0.6)
	return TEAM_COLORS[team_color_index(t)]


static func team_color_index(t: int) -> int:
	if t < 0 or t > 1: return t
	return clampi(int(Game.settings.get("color%d" % t, t)), 0, TEAM_COLORS.size() - 1)


static func team_name(t: int) -> String:
	return TEAM_NAMES[team_color_index(t)] if t >= 0 and t <= 1 else "Neutral"

# weapon "targets": which movement layers it can engage: ground, heli, jet
const W_TANK_GUN := {"id": "120mm", "range": 60.0, "reload": 2.4, "damage": 170.0, "splash": 2.5, "proj": "shell",
	"speed": 260.0, "spread": 1.4, "targets": ["ground"], "turret": true}
const W_RWS := {"id": "rws_mg", "range": 45.0, "reload": 0.3, "damage": 9.0, "splash": 0.0, "proj": "bullet",
	"speed": 400.0, "spread": 1.0, "targets": ["ground", "heli"], "turret": true}

## Tracked vehicles (heightfield maps: steeper climbs than wheels, no road bonus).
const TRACKED := ["dozer", "vanguard", "abrams", "bradley", "m113", "paladin"]

const DEFS := {
	"vanguard": {
		"name": "Vanguard MBT", "role": "Main battle tank - anti-armour", "domain": "ground",
		"model": "res://assets/units/vanguard.glb", "ao_prefix": "res://assets/units/vanguard_",
		"hp": 900.0, "speed": 9.0, "accel": 7.0, "turn_deg": 85.0, "turret_turn_deg": 120.0,
		"radius": 2.4, "height": 2.9, "sight": 80.0, "cost": 900, "armor": "heavy",
		"weapons": [W_TANK_GUN, W_RWS],
	},
	# ---------------- aircraft (sprite-based; PROVISIONAL values) ----------------
	"f16": {
		"name": "F-16 (multirole fighter)", "role": "Multirole jet - missile strikes; rearms at its pad", "domain": "jet",
		"sprite": "res://assets/aircraft/f16/f16_top.png", "model3d": "res://assets/units3d/f16/f16.glb", "icon": "res://assets/aircraft/f16/f16_icon.png", "length": 15.1,
		"hp": 320.0, "speed": 52.0, "min_speed": 30.0, "accel": 20.0, "turn_deg": 72.0, "altitude": 16.0,
		"radius": 4.0, "height": 1.0, "sight": 95.0, "cost": 1400, "provisional": true,
		"weapons": [{"id": "agm", "range": 115.0, "reload": 1.2, "damage": 240.0, "splash": 4.0, "proj": "missile",
			"speed": 150.0, "spread": 0.5, "targets": ["ground", "heli"], "ammo": 4, "facing_deg": 22.0}],
	},
	"fa18": {
		"name": "F/A-18 (strike fighter)", "role": "Strike jet - heavier missile load, slower", "domain": "jet",
		"sprite": "res://assets/aircraft/fa18/fa18_top.png", "model3d": "res://assets/units3d/fa18/fa18.glb", "icon": "res://assets/aircraft/fa18/fa18_icon.png", "length": 17.1,
		"hp": 380.0, "speed": 48.0, "min_speed": 28.0, "accel": 18.0, "turn_deg": 66.0, "altitude": 16.0,
		"radius": 4.4, "height": 1.0, "sight": 95.0, "cost": 1600, "provisional": true,
		"weapons": [{"id": "agm_heavy", "range": 110.0, "reload": 1.0, "damage": 220.0, "splash": 5.0, "proj": "missile",
			"speed": 140.0, "spread": 0.6, "targets": ["ground", "heli"], "ammo": 6, "facing_deg": 22.0}],
	},
	"f35": {
		"name": "F-35 (stealth multirole)", "role": "Stealth multirole jet - precision strikes, hard to intercept", "domain": "jet",
		"sprite": "res://assets/aircraft/f16/f16_top.png", "model3d": "res://assets/units3d/f35/f35.glb",
		"icon": "res://assets/aircraft/f16/f16_icon.png", "length": 15.7,
		"hp": 360.0, "speed": 55.0, "min_speed": 30.0, "accel": 22.0, "turn_deg": 75.0, "altitude": 17.0,
		"radius": 4.2, "height": 1.0, "sight": 110.0, "cost": 2000, "provisional": true,
		"weapons": [{"id": "jdam", "range": 120.0, "reload": 1.4, "damage": 280.0, "splash": 5.0, "proj": "missile",
			"speed": 150.0, "spread": 0.4, "targets": ["ground"], "ammo": 4, "facing_deg": 24.0},
			{"id": "aim120", "range": 130.0, "reload": 1.0, "damage": 240.0, "splash": 2.0, "proj": "missile",
			"speed": 190.0, "spread": 0.3, "targets": ["heli", "jet"], "ammo": 2, "facing_deg": 30.0}],
	},
	"f22": {
		"name": "F-22 (air superiority)", "role": "Air-superiority jet - hunts aircraft, weak vs ground", "domain": "jet",
		"sprite": "res://assets/aircraft/f22/f22_top.png", "model3d": "res://assets/units3d/f22/f22.glb", "icon": "res://assets/aircraft/f22/f22_icon.png", "length": 18.9,
		"hp": 420.0, "speed": 60.0, "min_speed": 34.0, "accel": 24.0, "turn_deg": 85.0, "altitude": 18.0,
		"radius": 4.6, "height": 1.0, "sight": 120.0, "cost": 2200, "provisional": true,
		"weapons": [{"id": "aam", "range": 130.0, "reload": 0.9, "damage": 260.0, "splash": 2.0, "proj": "missile",
			"speed": 190.0, "spread": 0.3, "targets": ["heli", "jet"], "ammo": 6, "facing_deg": 30.0},
			{"id": "sdb", "range": 90.0, "reload": 2.0, "damage": 160.0, "splash": 5.0, "proj": "missile",
			"speed": 120.0, "spread": 0.8, "targets": ["ground"], "ammo": 2, "facing_deg": 18.0}],
	},
	"a10": {
		"name": "A-10 (ground attack)", "role": "Close air support - cannon strafing runs, tough airframe", "domain": "jet",
		"sprite": "res://assets/aircraft/a10/a10_top.png", "model3d": "res://assets/units3d/a10/a10.glb", "icon": "res://assets/aircraft/a10/a10_icon.png", "length": 16.3,
		"hp": 650.0, "speed": 38.0, "min_speed": 22.0, "accel": 14.0, "turn_deg": 60.0, "altitude": 12.0,
		"radius": 4.6, "height": 1.0, "sight": 85.0, "cost": 1700, "provisional": true,
		"weapons": [{"id": "gau_cannon", "range": 90.0, "reload": 0.1, "damage": 20.0, "splash": 1.5, "proj": "bullet",
			"speed": 520.0, "spread": 2.5, "targets": ["ground", "heli"], "ammo": 80, "facing_deg": 14.0, "vs": {"heavy": 0.9, "light": 1.0, "structure": 0.5}}],
	},
	"ah64": {
		"name": "AH-64 (attack helicopter)", "role": "Attack helicopter - rockets and guided missiles vs armour", "domain": "heli",
		"sprite": "res://assets/aircraft/ah64/ah64_top.png", "model3d": "res://assets/units3d/ah64/ah64.glb", "icon": "res://assets/aircraft/ah64/ah64_icon.png", "length": 17.7,
		"hp": 520.0, "speed": 20.0, "accel": 10.0, "turn_deg": 110.0, "altitude": 9.0, "rotor": 7.3,
		"radius": 3.5, "height": 1.0, "sight": 85.0, "cost": 1500, "provisional": true,
		"weapons": [{"id": "atgm", "range": 70.0, "reload": 2.2, "damage": 200.0, "splash": 2.0, "proj": "missile",
			"speed": 110.0, "spread": 0.4, "targets": ["ground"], "facing_deg": 25.0},
			{"id": "rockets", "range": 55.0, "reload": 0.35, "damage": 35.0, "splash": 3.0, "proj": "rocket",
			"speed": 120.0, "spread": 3.0, "targets": ["ground"], "facing_deg": 15.0}],
	},
	"uh60": {
		"name": "UH-60 (utility helicopter)", "role": "Air-assault transport - carries 8 infantry, door guns; hover low to load / unload", "transport": {"capacity": 8, "accepts": ["infantry"]}, "domain": "heli",
		"sprite": "res://assets/aircraft/uh60/uh60_top.png", "model3d": "res://assets/units3d/uh60/uh60.glb", "icon": "res://assets/aircraft/uh60/uh60_icon.png", "length": 19.8,
		"hp": 450.0, "speed": 24.0, "accel": 11.0, "turn_deg": 100.0, "altitude": 8.0, "rotor": 8.2,
		"radius": 3.8, "height": 1.0, "sight": 75.0, "cost": 900, "provisional": true,
		"weapons": [{"id": "door_guns", "range": 40.0, "reload": 0.25, "damage": 7.0, "splash": 0.0, "proj": "bullet",
			"speed": 400.0, "spread": 2.0, "targets": ["ground", "heli"], "facing_deg": 120.0}],
	},
	"ch47": {
		"name": "CH-47 (heavy-lift helicopter)", "role": "Heavy transport - unarmed (supply/vehicle lift arrives with the economy)", "domain": "heli",
		"sprite": "res://assets/aircraft/ch47/ch47_top.png", "model3d": "res://assets/units3d/ch47/ch47.glb", "icon": "res://assets/aircraft/ch47/ch47_icon.png", "length": 30.1,
		"hp": 700.0, "speed": 18.0, "accel": 7.0, "turn_deg": 70.0, "altitude": 10.0, "rotor": 9.1, "rotor_twin": true, "blades": 3,
		"radius": 5.0, "height": 1.0, "sight": 70.0, "cost": 1200, "provisional": true, "hauler": true,
		"weapons": [],
	},
}

# armour classes and how much each projectile family hurts them (weapons may override with "vs"). PROVISIONAL.
const ARMOR_MULT := {
	"bullet": {"infantry": 1.0, "light": 0.5, "heavy": 0.1, "air": 0.5, "structure": 0.15},
	"shell": {"infantry": 0.5, "light": 1.0, "heavy": 1.0, "air": 1.0, "structure": 0.8},
	"arty": {"infantry": 0.9, "light": 1.0, "heavy": 0.8, "air": 0.0, "structure": 1.2},
	"rocket": {"infantry": 0.35, "light": 1.0, "heavy": 1.0, "air": 1.0, "structure": 0.8},
	"missile": {"infantry": 0.35, "light": 1.0, "heavy": 1.0, "air": 1.0, "structure": 0.8},
}


## World-scale guide: factor applied to the drawn size of each class (art is authored at real size). See docs/SCALE_GUIDE.md.
const SCALE := {"structure": 1.0, "vehicle": 0.8, "aircraft": 0.6, "infantry": 1.3, "bomber": 1.0}   # bomber: support-power strategic bombers (real size)


static func scale_for(d: Dictionary) -> float:
	if d.get("visual", "") == "infantry": return SCALE.infantry
	if d.get("visual", "") == "structure": return SCALE.structure
	if str(d.get("domain", "ground")) in ["jet", "heli"]: return SCALE.aircraft
	return SCALE.vehicle


static func def_of(k: String) -> Dictionary:
	if DEFS.has(k): return DEFS[k]
	if BASE_UNITS.has(k): return BASE_UNITS[k]
	return derived(k)


## Iranian units derived from a base type. Infantry: same movement, animation set and mechanics as the U.S. counterpart (the user's direction), with
## their own 3D models, names and small stat differences. PROVISIONAL values.
const IRAN_DERIVED := {
	"ir_rifleman": ["rifleman", {"name": "Artesh Rifleman", "role": "Infantry - effective vs infantry, weak vs armour", "weapon_id": "g3"}],
	"ir_rpg": ["at4", {"name": "RPG Gunner", "role": "Anti-tank rocket launcher - effective vs vehicles", "weapon_id": "rpg7"}],
	"ir_mg": ["m240_gunner", {"name": "PKM Machine Gunner", "role": "Belt-fed machine gun - heavy anti-infantry fire", "weapon_id": "pkm"}],
	"ir_medic": ["medic", {"name": "Combat Medic", "role": "Heals nearby infantry; light carbine"}],
	"ir_sniper": ["sniper", {"name": "Marksman", "role": "Long-range marksman - deadly vs infantry", "weapon_id": "sniper_rifle"}],
	"ir_engineer": ["eod_engineer", {"name": "Combat Engineer", "role": "Repairs nearby friendly vehicles and structures; unarmed"}],
	"irgc_sf": ["special_forces", {"name": "IRGC Special Forces", "role": "Elite IRGC operator - tough, long-range rifle, high damage",
		"hp": 190.0, "sight": 72.0, "weapon_id": "irgc_rifle", "damage_mult": 1.1}],
	"ir_paratrooper": ["paratrooper", {"name": "Airborne Rifleman", "role": "Airborne rifleman - arrives by parachute"}],
	# Iranian aircraft (wave 1): own 3D models with Iranian roundels / fin flash; mechanics follow the base type
	"ir_f14": ["f22", {"name": "F-14 (interceptor)", "role": "Long-range interceptor - hunts aircraft, light ground strike", "length": 19.1, "hp": 400.0, "speed": 54.0}],
	"ir_f4": ["f16", {"name": "F-4 (fighter-bomber)", "role": "Fighter-bomber - missile strikes on ground targets; rearms at its pad", "length": 19.2, "hp": 380.0, "speed": 48.0}],
	"ir_su24": ["fa18", {"name": "Su-24 (strike aircraft)", "role": "Strike jet - heavy ground-attack missile load", "length": 22.6, "hp": 450.0, "speed": 46.0}],
	"ir_ah1j": ["ah64", {"name": "AH-1J (attack helicopter)", "role": "Attack helicopter - rockets and guided missiles vs armour", "length": 14.3, "hp": 440.0, "rotor": 6.7}],
	# Iranian ground vehicles (wave 1)
	"ir_karrar": ["abrams", {"name": "Karrar (main battle tank)", "role": "Main battle tank - anti-armour", "track_m_per_v": 0.8956, "length": 9.5}],
	"ir_t72s": ["abrams", {"name": "T-72S (main battle tank)", "role": "Older main battle tank with reactive armour - cheaper, lighter", "track_m_per_v": 0.8956, "length": 9.5, "hp": 760.0}],
	"ir_bmp2": ["bradley", {"name": "BMP-2 (infantry fighting vehicle)", "role": "IFV - 30 mm autocannon vs light targets, ATGM vs armour; carries 7", "track_m_per_v": 0.8355, "length": 6.72,
		"transport": {"capacity": 7, "accepts": ["infantry"]}}],
	"ir_boragh": ["stryker", {"name": "Boragh (8x8 APC)", "role": "Wheeled infantry carrier - remote machine gun, fast; carries 8", "length": 7.6,
		"transport": {"capacity": 8, "accepts": ["infantry"]}}],
	"ir_engineer_dozer": ["dozer", {"name": "Engineer Dozer", "role": "Builder - constructs and rebuilds structures. Light machine gun mount (unarmed).", "track_m_per_v": 0.8956, "length": 7.6}],
	"ir_ch47": ["ch47", {"name": "CH-47C (heavy-lift helicopter)", "role": "Supply hauler - carries cash from supply piles to the Supply Depot"}],
}
static var _derived := {}


static func derived(k: String) -> Dictionary:
	if _derived.has(k): return _derived[k]
	if not IRAN_DERIVED.has(k):
		push_error("unknown unit kind " + k)
		return BASE_UNITS.rifleman
	var e: Array = IRAN_DERIVED[k]
	var d: Dictionary = def_of(e[0]).duplicate(true)
	var o: Dictionary = e[1]
	for key in o:
		if key in ["weapon_id", "damage_mult"]: continue
		d[key] = o[key]
	var path := "res://assets/units3d/%s/%s.glb" % [k, k]
	if ResourceLoader.exists(path): d["model3d"] = path
	var icon := "res://assets/iran/icons/%s_icon.png" % k
	if ResourceLoader.exists(icon): d["icon"] = icon
	for w in d.get("weapons", []):
		if o.has("weapon_id"): w["id"] = o.weapon_id
		if o.has("damage_mult"): w["damage"] = float(w.damage) * float(o.damage_mult)
	d["nation"] = "iran"
	d["base_kind"] = e[0]
	_derived[k] = d
	return d


static func all_kinds() -> Array:
	return DEFS.keys() + BASE_UNITS.keys() + IRAN_DERIVED.keys()


static func armor_of(d: Dictionary) -> String:
	if d.has("armor"): return d.armor
	match str(d.get("domain", "ground")):
		"jet", "heli": return "air"
	return "heavy"


# ---------------- B1.2 base-loop units: supplied U.S. concept art as camera-facing cards (PROVISIONAL values) ----------------
const BASE_UNITS := {
	"dozer": {
		"name": "M88 Dozer", "role": "Builder - constructs structures. Unarmed.", "domain": "ground", "visual": "vehicle_art",
		"art": "m88", "model3d": "res://assets/units3d/m88/m88.glb", "track_m_per_v": 0.9573, "length": 8.3, "hp": 600.0, "speed": 8.0, "accel": 6.0, "turn_deg": 90.0, "radius": 2.6,
		"height": 3.0, "sight": 50.0, "armor": "heavy", "builder": true, "weapons": [],
	},
	"rifleman": {
		"name": "Rifleman", "role": "Infantry - effective vs infantry, weak vs armour", "domain": "ground", "visual": "infantry",
		"art": "rifleman", "model3d": "res://assets/units3d/rifleman/rifleman.glb", "hp": 120.0, "speed": 4.5, "accel": 12.0, "turn_deg": 360.0, "radius": 0.7, "height": 1.8,
		"sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "m4", "range": 34.0, "reload": 0.9, "damage": 12.0, "splash": 0.0, "proj": "bullet",
			"speed": 350.0, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40.0}],
	},
	"saw_gunner": {
		"name": "SAW Gunner", "role": "Squad automatic weapon - suppresses infantry", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "saw_gunner", "model3d": "res://assets/units3d/saw_gunner/saw_gunner.glb", "hp": 130.0, "speed": 4.3, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "m249", "range": 38.0, "reload": 0.25, "damage": 9.0, "splash": 0.0, "proj": "bullet", "speed": 350, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40}],
	},
	"m240_gunner": {
		"name": "M240 Gunner", "role": "Medium machine gun - heavy anti-infantry fire, slower", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "m240_gunner", "model3d": "res://assets/units3d/m240_gunner/m240_gunner.glb", "hp": 140.0, "speed": 3.8, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "m240", "range": 42.0, "reload": 0.30, "damage": 13.0, "splash": 0.0, "proj": "bullet", "speed": 350, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40}],
	},
	"medic": {
		"name": "Medic", "role": "Heals nearby infantry; light carbine", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "medic", "model3d": "res://assets/units3d/medic/medic.glb", "hp": 110.0, "speed": 4.6, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 55.0, "armor": "infantry", "heal": {"radius": 14.0, "per_s": 0.05, "targets": ["infantry"]},
		"weapons": [{"id": "m4_medic", "range": 30.0, "reload": 1.10, "damage": 8.0, "splash": 0.0, "proj": "bullet", "speed": 350, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40}],
	},
	"sniper": {
		"name": "Sniper", "role": "Long-range marksman - deadly vs infantry, useless vs armour", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "sniper", "model3d": "res://assets/units3d/sniper/sniper.glb", "hp": 90.0, "speed": 4.0, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 95.0, "armor": "infantry",
		"weapons": [{"id": "m110", "range": 78.0, "reload": 3.50, "damage": 110.0, "splash": 0.0, "proj": "bullet", "speed": 600, "spread": 0.3, "targets": ["ground"], "facing_deg": 30}],
	},
	"eod_engineer": {
		"name": "EOD Engineer", "role": "Field engineer - repairs nearby friendly vehicles and structures; unarmed", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "eod_engineer", "model3d": "res://assets/units3d/eod_engineer/eod_engineer.glb", "hp": 130.0, "speed": 3.8, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 50.0, "armor": "infantry", "heal": {"radius": 16.0, "per_s": 0.02, "targets": ["vehicle", "structure"]},
		"weapons": [],
	},
	"ranger": {
		"name": "Ranger", "role": "Elite rifleman - tougher and more accurate", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "ranger", "model3d": "res://assets/units3d/ranger/ranger.glb", "hp": 150.0, "speed": 4.8, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 60.0, "armor": "infantry",
		"weapons": [{"id": "m4_ranger", "range": 36.0, "reload": 0.80, "damage": 15.0, "splash": 0.0, "proj": "bullet", "speed": 350, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40}],
	},
	"special_forces": {
		"name": "Special Forces", "role": "Elite operator - long-range carbine, high damage", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "special_forces", "model3d": "res://assets/units3d/special_forces/special_forces.glb", "hp": 170.0, "speed": 5.0, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 70.0, "armor": "infantry",
		"weapons": [{"id": "mk17", "range": 42.0, "reload": 0.70, "damage": 20.0, "splash": 0.0, "proj": "bullet", "speed": 350, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40}],
	},
	"paratrooper": {
		"name": "Paratrooper", "role": "Airborne rifleman - arrives by parachute", "category": "Infantry", "domain": "ground", "visual": "infantry",
		"art": "rifleman", "model3d": "res://assets/units3d/paratrooper/paratrooper.glb", "hp": 130.0, "speed": 4.5, "accel": 12.0, "turn_deg": 360.0,
		"radius": 0.7, "height": 1.8, "sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "m4_para", "range": 34.0, "reload": 0.90, "damage": 12.0, "splash": 0.0, "proj": "bullet", "speed": 350, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40}],
	},
	"at4": {
		"name": "AT4 Gunner", "role": "Anti-tank infantry - shoulder-fired rockets vs vehicles", "domain": "ground", "visual": "infantry",
		"art": "at4", "model3d": "res://assets/units3d/at4/at4.glb", "hp": 120.0, "speed": 4.2, "accel": 12.0, "turn_deg": 360.0, "radius": 0.7, "height": 1.8,
		"sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "at4", "range": 42.0, "reload": 3.5, "damage": 160.0, "splash": 1.5, "proj": "rocket",
			"speed": 90.0, "spread": 1.0, "targets": ["ground"], "facing_deg": 25.0}],
	},
	"hmmwv_50cal": {
		"name": "HMMWV .50 cal", "role": "Fast scout - heavy machine gun vs infantry and helicopters", "domain": "ground",
		"visual": "vehicle_art", "art": "hmmwv_50cal", "model3d": "res://assets/units3d/hmmwv_50cal/hmmwv_50cal.glb", "category": "Scout", "length": 4.6, "hp": 420.0, "speed": 16.0, "accel": 10.0,
		"turn_deg": 120.0, "radius": 1.8, "height": 2.2, "sight": 75.0, "armor": "light",
		"weapons": [{"id": "m2", "range": 45.0, "reload": 0.18, "damage": 8.0, "splash": 0.0, "proj": "bullet",
			"speed": 420.0, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 360.0}],
	},
	"abrams": {
		"name": "M1A2 Abrams", "role": "Main battle tank - anti-armour", "category": "Armor", "domain": "ground",
		"visual": "vehicle_art", "art": "abrams", "model3d": "res://assets/units3d/abrams/abrams.glb", "length": 7.9,
		"hp": 1000.0, "speed": 10.0, "accel": 7.0, "turn_deg": 80.0, "turret_turn_deg": 110.0, "radius": 2.6, "height": 2.9,
		"sight": 80.0, "armor": "heavy",
		"weapons": [{"id": "120mm", "range": 62.0, "reload": 2.4, "damage": 180.0, "splash": 2.5, "proj": "shell",
			"speed": 260.0, "spread": 1.3, "targets": ["ground"], "turret": true},
			{"id": "m2_cupola", "range": 45.0, "reload": 0.3, "damage": 8.0, "splash": 0.0, "proj": "bullet",
			"speed": 400.0, "spread": 1.0, "targets": ["ground", "heli"], "facing_deg": 360.0}],
	},
	"bradley": {
		"name": "M2A3 Bradley", "role": "Infantry fighting vehicle - 25 mm cannon vs light targets, TOW vs armour", "category": "Armor",
		"transport": {"capacity": 6, "accepts": ["infantry"]}, "domain": "ground", "visual": "vehicle_art", "art": "bradley", "model3d": "res://assets/units3d/bradley/bradley.glb",
		"length": 6.6, "hp": 700.0, "speed": 12.0, "accel": 8.0, "turn_deg": 90.0, "turret_turn_deg": 120.0, "radius": 2.3,
		"height": 2.9, "sight": 80.0, "armor": "heavy",
		"weapons": [{"id": "25mm", "range": 55.0, "reload": 0.5, "damage": 22.0, "splash": 1.0, "proj": "shell",
			"speed": 320.0, "spread": 1.4, "targets": ["ground", "heli"], "turret": true},
			{"id": "tow", "range": 70.0, "reload": 6.0, "damage": 200.0, "splash": 1.5, "proj": "missile",
			"speed": 110.0, "spread": 0.4, "targets": ["ground"], "turret": true}],
	},
	"paladin": {
		"name": "M109A7 Paladin", "role": "Self-propelled artillery - long range, splash, cannot hit close or moving air", "category": "Artillery",
		"domain": "ground", "visual": "vehicle_art", "art": "paladin", "model3d": "res://assets/units3d/paladin/paladin.glb",
		"length": 6.8, "hp": 600.0, "speed": 8.5, "accel": 5.0, "turn_deg": 70.0, "turret_turn_deg": 50.0, "radius": 2.3,
		"height": 3.2, "sight": 70.0, "armor": "heavy",
		"weapons": [{"id": "155mm", "range": 190.0, "min_range": 35.0, "reload": 6.5, "damage": 230.0, "splash": 9.0,
			"proj": "arty", "speed": 90.0, "spread": 6.0, "targets": ["ground"], "turret": true}],
	},
	"m777": {
		"name": "M777 Howitzer", "role": "Towed artillery - longest range, very slow, fragile", "category": "Artillery",
		"domain": "ground", "visual": "vehicle_art", "art": "m777", "model3d": "res://assets/units3d/m777/m777.glb",
		"length": 9.5, "hp": 380.0, "speed": 3.0, "accel": 2.0, "turn_deg": 40.0, "turret_turn_deg": 30.0, "radius": 2.6,
		"height": 2.6, "sight": 60.0, "armor": "light",
		"weapons": [{"id": "155mm_towed", "range": 230.0, "min_range": 45.0, "reload": 8.0, "damage": 260.0, "splash": 10.0,
			"proj": "arty", "speed": 95.0, "spread": 7.0, "targets": ["ground"], "turret": true}],
	},
	"m113": {
		"name": "M113 APC", "role": "Armoured personnel carrier - machine gun", "category": "Transport", "transport": {"capacity": 8, "accepts": ["infantry"]}, "domain": "ground",
		"visual": "vehicle_art", "art": "m113", "model3d": "res://assets/units3d/m113/m113.glb", "length": 4.9,
		"hp": 520.0, "speed": 13.0, "accel": 8.0, "turn_deg": 100.0, "radius": 1.9, "height": 2.5, "sight": 65.0, "armor": "heavy",
		"weapons": [{"id": "m2_apc", "range": 45.0, "reload": 0.2, "damage": 8.0, "splash": 0.0, "proj": "bullet",
			"speed": 400.0, "spread": 1.2, "targets": ["ground", "heli"], "turret": true}],
	},
	"stryker": {
		"name": "M1126 Stryker", "role": "Wheeled infantry carrier - remote machine gun, fast", "category": "Transport", "transport": {"capacity": 9, "accepts": ["infantry"]}, "domain": "ground",
		"visual": "vehicle_art", "art": "stryker", "model3d": "res://assets/units3d/stryker/stryker.glb", "length": 6.95,
		"hp": 600.0, "speed": 16.0, "accel": 9.0, "turn_deg": 90.0, "radius": 2.2, "height": 2.6, "sight": 70.0, "armor": "light",
		"weapons": [{"id": "rws_stryker", "range": 48.0, "reload": 0.2, "damage": 9.0, "splash": 0.0, "proj": "bullet",
			"speed": 420.0, "spread": 1.1, "targets": ["ground", "heli"], "turret": true}],
	},
	"mrap": {
		"name": "M-ATV MRAP", "role": "Mine-resistant patrol vehicle - machine gun, tough for its size", "category": "Scout", "transport": {"capacity": 4, "accepts": ["infantry"]}, "domain": "ground",
		"visual": "vehicle_art", "art": "mrap", "model3d": "res://assets/units3d/mrap/mrap.glb", "length": 6.3,
		"hp": 560.0, "speed": 15.0, "accel": 9.0, "turn_deg": 110.0, "radius": 2.0, "height": 2.7, "sight": 75.0, "armor": "light",
		"weapons": [{"id": "rws_mrap", "range": 46.0, "reload": 0.2, "damage": 8.5, "splash": 0.0, "proj": "bullet",
			"speed": 420.0, "spread": 1.1, "targets": ["ground", "heli"], "turret": true}],
	},
	"hmmwv_tow": {
		"name": "HMMWV TOW", "role": "Tank hunter - wire-guided missiles vs armour", "category": "Scout", "domain": "ground",
		"visual": "vehicle_art", "art": "hmmwv_tow", "model3d": "res://assets/units3d/hmmwv_tow/hmmwv_tow.glb", "length": 4.6,
		"hp": 400.0, "speed": 15.0, "accel": 10.0, "turn_deg": 120.0, "radius": 1.8, "height": 2.4, "sight": 80.0, "armor": "light",
		"weapons": [{"id": "tow_hmmwv", "range": 75.0, "reload": 4.5, "damage": 190.0, "splash": 1.5, "proj": "missile",
			"speed": 110.0, "spread": 0.4, "targets": ["ground"], "turret": true}],
	},
	"hmmwv_medical": {
		"name": "HMMWV Ambulance", "role": "Support - heals nearby infantry and repairs nothing; unarmed", "category": "Support",
		"domain": "ground", "visual": "vehicle_art", "art": "hmmwv_medical", "model3d": "res://assets/units3d/hmmwv_medical/hmmwv_medical.glb",
		"length": 5.1, "hp": 380.0, "speed": 15.0, "accel": 10.0, "turn_deg": 120.0, "radius": 1.9, "height": 2.6, "sight": 60.0,
		"armor": "light", "heal": {"radius": 18.0, "per_s": 0.04, "targets": ["infantry"]}, "weapons": [],
	},
	"hmmwv": {
		"name": "HMMWV", "role": "Fast unarmed scout", "category": "Scout", "transport": {"capacity": 5, "accepts": ["infantry"]}, "domain": "ground",
		"visual": "vehicle_art", "art": "hmmwv", "model3d": "res://assets/units3d/hmmwv/hmmwv.glb", "length": 4.6,
		"hp": 360.0, "speed": 18.0, "accel": 11.0, "turn_deg": 130.0, "radius": 1.8, "height": 2.0, "sight": 95.0, "armor": "light",
		"weapons": [],
	},
	"avenger": {
		"name": "Avenger AA", "role": "Air defence - missiles vs helicopters and jets only", "domain": "ground",
		"visual": "vehicle_art", "art": "avenger", "model3d": "res://assets/units3d/avenger/avenger.glb", "category": "Anti-air", "length": 4.95, "hp": 400.0, "speed": 13.0, "accel": 8.0,
		"turn_deg": 110.0, "radius": 1.8, "height": 2.6, "sight": 90.0, "armor": "light",
		"weapons": [{"id": "stinger", "range": 95.0, "reload": 1.5, "damage": 130.0, "splash": 1.0, "proj": "missile",
			"speed": 170.0, "spread": 0.3, "targets": ["heli", "jet"], "facing_deg": 360.0}],
	},
}

# Support powers (bombers / recon fly in from the owner's map edge). PROVISIONAL. Altitudes are game-scale
# (kept below the closest camera height so aircraft stay visible), not real flight levels. In the full game these are
# unlocked by rank (experience) - see docs/MECHANICS_REFERENCE_AUDIT.md; here they are available on cooldown.
const POWERS := {
	"carpet": {"name": "Carpet Bombing", "model3d": "res://assets/units3d/b52_hd/b52_hd.glb", "aircraft": "b52", "sprite": "res://assets/aircraft/b52/b52_top.png",
		"icon": "res://assets/aircraft/b52/b52_icon.png", "length": 48.5, "cooldown": 90.0, "speed": 70.0, "altitude": 46.0,
		"bombs": 22, "spacing": 4.0, "damage": 70.0, "splash": 8.0},
	"supersonic": {"name": "Supersonic Strike", "model3d": "res://assets/units3d/b1_hd/b1_hd.glb", "aircraft": "b1", "sprite": "res://assets/aircraft/b1/b1_top.png",
		"icon": "res://assets/aircraft/b1/b1_icon.png", "length": 44.5, "cooldown": 75.0, "speed": 120.0, "altitude": 42.0,
		"bombs": 6, "spacing": 8.0, "damage": 180.0, "splash": 8.0},
	"stealth": {"name": "Stealth Precision Strike", "model3d": "res://assets/units3d/b2_hd/b2_hd.glb", "aircraft": "b2", "sprite": "res://assets/aircraft/b2/b2_top.png",
		"icon": "res://assets/aircraft/b2/b2_icon.png", "length": 21.0, "cooldown": 120.0, "speed": 80.0, "altitude": 50.0,
		"bombs": 2, "spacing": 3.0, "damage": 550.0, "splash": 13.0},
	# Squadrons (B3): separate long-cooldown powers, available a few minutes into a skirmish ("first_ready", s of game
	# time) and from an Airfield in the base game. Formation offsets are in the flight frame: "lat" metres to the right
	# of the run, "back" metres behind the lead, "up" metres above the type's cruise altitude; "aim" shifts the aim point
	# along the run. Each aircraft bombs along its own track.
	"stealth_squadron": {"name": "Stealth Squadron", "model3d": "res://assets/units3d/b2_hd/b2_hd.glb", "aircraft": "b2",
		"icon": "res://assets/ui/powers/stealth_squadron.png", "cooldown": 240.0, "first_ready": 300.0, "speed": 80.0, "requires": "airfield",
		"wing": [
			{"type": "b2", "lat": -22.0, "back": 0.0, "up": 0.0, "aim": -18.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0},
			{"type": "b2", "lat": 0.0, "back": 46.0, "up": 5.0, "aim": 0.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0},
			{"type": "b2", "lat": 22.0, "back": 92.0, "up": 10.0, "aim": 18.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0}]},
	"stealth_squadron_heavy": {"name": "Heavy Stealth Squadron", "model3d": "res://assets/units3d/b2_hd/b2_hd.glb", "aircraft": "b2",
		"icon": "res://assets/ui/powers/stealth_squadron_heavy.png", "cooldown": 420.0, "first_ready": 540.0, "speed": 80.0, "requires": "airfield",
		"wing": [
			{"type": "b2", "lat": -44.0, "back": 0.0, "up": 0.0, "aim": -36.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0},
			{"type": "b2", "lat": -22.0, "back": 46.0, "up": 5.0, "aim": -18.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0},
			{"type": "b2", "lat": 0.0, "back": 92.0, "up": 10.0, "aim": 0.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0},
			{"type": "b2", "lat": 22.0, "back": 138.0, "up": 15.0, "aim": 18.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0},
			{"type": "b2", "lat": 44.0, "back": 184.0, "up": 20.0, "aim": 36.0, "bombs": 1, "damage": 900.0, "splash": 13.0, "spacing": 0.0}]},
	"strike_package": {"name": "Strategic Strike Package", "model3d": "res://assets/units3d/b52_hd/b52_hd.glb", "aircraft": "b2",
		"icon": "res://assets/ui/powers/strike_package.png", "cooldown": 480.0, "first_ready": 600.0, "speed": 80.0, "requires": "airfield",
		"wing": [
			{"type": "b2", "lat": 0.0, "back": 0.0, "up": 0.0, "aim": 0.0, "bombs": 2, "damage": 550.0, "splash": 13.0, "spacing": 3.0},
			{"type": "b1", "lat": -38.0, "back": 75.0, "up": 0.0, "aim": 0.0, "bombs": 6, "damage": 150.0, "splash": 8.0, "spacing": 12.0},
			{"type": "b1", "lat": 38.0, "back": 75.0, "up": 0.0, "aim": 0.0, "bombs": 6, "damage": 150.0, "splash": 8.0, "spacing": 12.0},
			{"type": "b52", "lat": -34.0, "back": 165.0, "up": 0.0, "aim": 0.0, "bombs": 22, "damage": 60.0, "splash": 8.0, "spacing": 4.0},
			{"type": "b52", "lat": 34.0, "back": 165.0, "up": 0.0, "aim": 0.0, "bombs": 22, "damage": 60.0, "splash": 8.0, "spacing": 4.0}]},
	"paradrop": {"name": "Paratroopers", "model3d": "res://assets/units3d/c130/c130.glb", "aircraft": "c130", "sprite": "res://assets/aircraft/c130/c130_top.png",
		"icon": "res://assets/aircraft/c130/c130_top.png", "length": 40.4, "cooldown": 150.0, "speed": 60.0, "altitude": 36.0,
		"troops": 6, "unit": "paratrooper", "requires": "airfield"},
	"shahed": {"name": "Shahed Drone Strike", "model3d": "res://assets/units3d/ir_shahed/ir_shahed.glb", "aircraft": "ir_shahed",
		"icon": "res://assets/iran/icons/ir_shahed_icon.png", "length": 3.3, "cooldown": 100.0, "speed": 45.0, "altitude": 22.0,
		"drones": 4, "damage": 240.0, "splash": 7.0},
	"recon": {"name": "Recon Overflight", "model3d": "res://assets/units3d/sr71/sr71.glb", "aircraft": "sr71", "sprite": "res://assets/aircraft/sr71/sr71_top.png",
		"icon": "res://assets/aircraft/sr71/sr71_icon.png", "length": 32.7, "cooldown": 60.0, "speed": 160.0, "altitude": 36.0,
		"reveal_width": 70.0, "reveal_time": 25.0},
}

## Strategic bombers flown by the support powers (strikes.gd). Real-size HD models (SCALE.bomber) with bomb-bay doors
## Door<i>L/R, stow lines Bay<i>a/b, pylon stations PB<n> (B-52) and B-1 wings WingL/R. Altitudes are above the local
## ground and above every other aircraft (jets cruise at <= 36 m). stow = [columns, tiers, column spacing, tier spacing].
const BOMBERS := {
	"b52": {"name": "B-52", "model3d": "res://assets/units3d/b52_hd/b52_hd.glb", "length": 48.5, "span": 56.4, "speed": 70.0,
		"altitude": 46.0, "bays": 1, "bay_cap": 10, "stow": [2, 2, 0.36, 0.42], "bomb": "gp", "bomb_scale": 0.6, "door_deg": 95.0},
	"b1": {"name": "B-1", "model3d": "res://assets/units3d/b1_hd/b1_hd.glb", "length": 44.5, "span": 41.8, "speed": 120.0,
		"altitude": 42.0, "bays": 3, "bay_cap": 6, "stow": [2, 1, 0.5, 0.0], "bomb": "gp", "bomb_scale": 0.8, "door_deg": 90.0,
		"sweep_deg": 30.0},
	"b2": {"name": "B-2", "model3d": "res://assets/units3d/b2_hd/b2_hd.glb", "length": 21.0, "span": 52.4, "speed": 80.0,
		"altitude": 50.0, "bays": 2, "bay_cap": 2, "stow": [1, 1, 0.0, 0.0], "bomb": "pen", "bomb_scale": 1.0, "door_deg": 100.0},
}

# Steel Accord - unit, weapon and support-power definitions (data).
# Values marked PROVISIONAL are first-pass tuning, not balanced. Real-world aircraft names are the client's
# working labels for the supplied concept art; see content/manifest/aircraft.json for release-review status.
class_name UnitDefs

const TEAM_COLORS := [Color(0.12, 0.30, 0.72), Color(0.70, 0.13, 0.10), Color(0.15, 0.55, 0.25), Color(0.75, 0.6, 0.1)]
const TEAM_NAMES := ["Blue", "Red", "Green", "Gold"]

# weapon "targets": which movement layers it can engage: ground, heli, jet
const W_TANK_GUN := {"id": "120mm", "range": 60.0, "reload": 2.4, "damage": 170.0, "splash": 2.5, "proj": "shell",
	"speed": 260.0, "spread": 1.4, "targets": ["ground"], "turret": true}
const W_RWS := {"id": "rws_mg", "range": 45.0, "reload": 0.3, "damage": 9.0, "splash": 0.0, "proj": "bullet",
	"speed": 400.0, "spread": 1.0, "targets": ["ground", "heli"], "turret": true}

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
		"sprite": "res://assets/aircraft/f16/f16_top.png", "icon": "res://assets/aircraft/f16/f16_icon.png", "length": 15.1,
		"hp": 320.0, "speed": 52.0, "min_speed": 30.0, "accel": 20.0, "turn_deg": 72.0, "altitude": 16.0,
		"radius": 4.0, "height": 1.0, "sight": 95.0, "cost": 1400, "provisional": true,
		"weapons": [{"id": "agm", "range": 115.0, "reload": 1.2, "damage": 240.0, "splash": 4.0, "proj": "missile",
			"speed": 150.0, "spread": 0.5, "targets": ["ground", "heli"], "ammo": 4, "facing_deg": 22.0}],
	},
	"fa18": {
		"name": "F/A-18 (strike fighter)", "role": "Strike jet - heavier missile load, slower", "domain": "jet",
		"sprite": "res://assets/aircraft/fa18/fa18_top.png", "icon": "res://assets/aircraft/fa18/fa18_icon.png", "length": 17.1,
		"hp": 380.0, "speed": 48.0, "min_speed": 28.0, "accel": 18.0, "turn_deg": 66.0, "altitude": 16.0,
		"radius": 4.4, "height": 1.0, "sight": 95.0, "cost": 1600, "provisional": true,
		"weapons": [{"id": "agm_heavy", "range": 110.0, "reload": 1.0, "damage": 220.0, "splash": 5.0, "proj": "missile",
			"speed": 140.0, "spread": 0.6, "targets": ["ground", "heli"], "ammo": 6, "facing_deg": 22.0}],
	},
	"f22": {
		"name": "F-22 (air superiority)", "role": "Air-superiority jet - hunts aircraft, weak vs ground", "domain": "jet",
		"sprite": "res://assets/aircraft/f22/f22_top.png", "icon": "res://assets/aircraft/f22/f22_icon.png", "length": 18.9,
		"hp": 420.0, "speed": 60.0, "min_speed": 34.0, "accel": 24.0, "turn_deg": 85.0, "altitude": 18.0,
		"radius": 4.6, "height": 1.0, "sight": 120.0, "cost": 2200, "provisional": true,
		"weapons": [{"id": "aam", "range": 130.0, "reload": 0.9, "damage": 260.0, "splash": 2.0, "proj": "missile",
			"speed": 190.0, "spread": 0.3, "targets": ["heli", "jet"], "ammo": 6, "facing_deg": 30.0},
			{"id": "sdb", "range": 90.0, "reload": 2.0, "damage": 160.0, "splash": 5.0, "proj": "missile",
			"speed": 120.0, "spread": 0.8, "targets": ["ground"], "ammo": 2, "facing_deg": 18.0}],
	},
	"a10": {
		"name": "A-10 (ground attack)", "role": "Close air support - cannon strafing runs, tough airframe", "domain": "jet",
		"sprite": "res://assets/aircraft/a10/a10_top.png", "icon": "res://assets/aircraft/a10/a10_icon.png", "length": 16.3,
		"hp": 650.0, "speed": 38.0, "min_speed": 22.0, "accel": 14.0, "turn_deg": 60.0, "altitude": 12.0,
		"radius": 4.6, "height": 1.0, "sight": 85.0, "cost": 1700, "provisional": true,
		"weapons": [{"id": "gau_cannon", "range": 90.0, "reload": 0.1, "damage": 20.0, "splash": 1.5, "proj": "bullet",
			"speed": 520.0, "spread": 2.5, "targets": ["ground", "heli"], "ammo": 80, "facing_deg": 14.0, "vs": {"heavy": 0.9, "light": 1.0, "structure": 0.5}}],
	},
	"ah64": {
		"name": "AH-64 (attack helicopter)", "role": "Attack helicopter - rockets and guided missiles vs armour", "domain": "heli",
		"sprite": "res://assets/aircraft/ah64/ah64_top.png", "icon": "res://assets/aircraft/ah64/ah64_icon.png", "length": 17.7,
		"hp": 520.0, "speed": 20.0, "accel": 10.0, "turn_deg": 110.0, "altitude": 9.0, "rotor": 7.3,
		"radius": 3.5, "height": 1.0, "sight": 85.0, "cost": 1500, "provisional": true,
		"weapons": [{"id": "atgm", "range": 70.0, "reload": 2.2, "damage": 200.0, "splash": 2.0, "proj": "missile",
			"speed": 110.0, "spread": 0.4, "targets": ["ground"], "facing_deg": 25.0},
			{"id": "rockets", "range": 55.0, "reload": 0.35, "damage": 35.0, "splash": 3.0, "proj": "rocket",
			"speed": 120.0, "spread": 3.0, "targets": ["ground"], "facing_deg": 15.0}],
	},
	"uh60": {
		"name": "UH-60 (utility helicopter)", "role": "Transport helicopter - door guns (troop carrying arrives with infantry)", "domain": "heli",
		"sprite": "res://assets/aircraft/uh60/uh60_top.png", "icon": "res://assets/aircraft/uh60/uh60_icon.png", "length": 19.8,
		"hp": 450.0, "speed": 24.0, "accel": 11.0, "turn_deg": 100.0, "altitude": 8.0, "rotor": 8.2,
		"radius": 3.8, "height": 1.0, "sight": 75.0, "cost": 900, "provisional": true,
		"weapons": [{"id": "door_guns", "range": 40.0, "reload": 0.25, "damage": 7.0, "splash": 0.0, "proj": "bullet",
			"speed": 400.0, "spread": 2.0, "targets": ["ground", "heli"], "facing_deg": 120.0}],
	},
	"ch47": {
		"name": "CH-47 (heavy-lift helicopter)", "role": "Heavy transport - unarmed (supply/vehicle lift arrives with the economy)", "domain": "heli",
		"sprite": "res://assets/aircraft/ch47/ch47_top.png", "icon": "res://assets/aircraft/ch47/ch47_icon.png", "length": 30.1,
		"hp": 700.0, "speed": 18.0, "accel": 7.0, "turn_deg": 70.0, "altitude": 10.0, "rotor": 9.1, "rotor_twin": true, "blades": 3,
		"radius": 5.0, "height": 1.0, "sight": 70.0, "cost": 1200, "provisional": true, "hauler": true,
		"weapons": [],
	},
}

# armour classes and how much each projectile family hurts them (weapons may override with "vs"). PROVISIONAL.
const ARMOR_MULT := {
	"bullet": {"infantry": 1.0, "light": 0.5, "heavy": 0.1, "air": 0.5, "structure": 0.15},
	"shell": {"infantry": 0.5, "light": 1.0, "heavy": 1.0, "air": 1.0, "structure": 0.8},
	"rocket": {"infantry": 0.35, "light": 1.0, "heavy": 1.0, "air": 1.0, "structure": 0.8},
	"missile": {"infantry": 0.35, "light": 1.0, "heavy": 1.0, "air": 1.0, "structure": 0.8},
}


## World-scale guide: factor applied to the drawn size of each class (art is authored at real size). See docs/SCALE_GUIDE.md.
const SCALE := {"structure": 1.0, "vehicle": 0.8, "aircraft": 0.6, "infantry": 1.3}


static func scale_for(d: Dictionary) -> float:
	if d.get("visual", "") == "infantry": return SCALE.infantry
	if d.get("visual", "") == "structure": return SCALE.structure
	if str(d.get("domain", "ground")) in ["jet", "heli"]: return SCALE.aircraft
	return SCALE.vehicle


static func def_of(k: String) -> Dictionary:
	return DEFS[k] if DEFS.has(k) else BASE_UNITS[k]


static func armor_of(d: Dictionary) -> String:
	if d.has("armor"): return d.armor
	match str(d.get("domain", "ground")):
		"jet", "heli": return "air"
	return "heavy"


# ---------------- B1.2 base-loop units: supplied U.S. concept art as camera-facing cards (PROVISIONAL values) ----------------
const BASE_UNITS := {
	"dozer": {
		"name": "M88 Dozer", "role": "Builder - constructs structures. Unarmed.", "domain": "ground", "visual": "vehicle_art",
		"art": "m88", "length": 8.3, "hp": 600.0, "speed": 8.0, "accel": 6.0, "turn_deg": 90.0, "radius": 2.6,
		"height": 3.0, "sight": 50.0, "armor": "heavy", "builder": true, "weapons": [],
	},
	"rifleman": {
		"name": "Rifleman", "role": "Infantry - effective vs infantry, weak vs armour", "domain": "ground", "visual": "infantry",
		"art": "rifleman", "hp": 120.0, "speed": 4.5, "accel": 12.0, "turn_deg": 360.0, "radius": 0.7, "height": 1.8,
		"sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "m4", "range": 34.0, "reload": 0.9, "damage": 12.0, "splash": 0.0, "proj": "bullet",
			"speed": 350.0, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 40.0}],
	},
	"at4": {
		"name": "AT4 Gunner", "role": "Anti-tank infantry - shoulder-fired rockets vs vehicles", "domain": "ground", "visual": "infantry",
		"art": "at4", "hp": 120.0, "speed": 4.2, "accel": 12.0, "turn_deg": 360.0, "radius": 0.7, "height": 1.8,
		"sight": 55.0, "armor": "infantry",
		"weapons": [{"id": "at4", "range": 42.0, "reload": 3.5, "damage": 160.0, "splash": 1.5, "proj": "rocket",
			"speed": 90.0, "spread": 1.0, "targets": ["ground"], "facing_deg": 25.0}],
	},
	"hmmwv_50cal": {
		"name": "HMMWV .50 cal", "role": "Fast scout - heavy machine gun vs infantry and helicopters", "domain": "ground",
		"visual": "vehicle_art", "art": "hmmwv_50cal", "length": 4.6, "hp": 420.0, "speed": 16.0, "accel": 10.0,
		"turn_deg": 120.0, "radius": 1.8, "height": 2.2, "sight": 75.0, "armor": "light",
		"weapons": [{"id": "m2", "range": 45.0, "reload": 0.18, "damage": 8.0, "splash": 0.0, "proj": "bullet",
			"speed": 420.0, "spread": 1.2, "targets": ["ground", "heli"], "facing_deg": 360.0}],
	},
	"avenger": {
		"name": "Avenger AA", "role": "Air defence - missiles vs helicopters and jets only", "domain": "ground",
		"visual": "vehicle_art", "art": "avenger", "length": 4.95, "hp": 400.0, "speed": 13.0, "accel": 8.0,
		"turn_deg": 110.0, "radius": 1.8, "height": 2.6, "sight": 90.0, "armor": "light",
		"weapons": [{"id": "stinger", "range": 95.0, "reload": 1.5, "damage": 130.0, "splash": 1.0, "proj": "missile",
			"speed": 170.0, "spread": 0.3, "targets": ["heli", "jet"], "facing_deg": 360.0}],
	},
}

# Support powers (bombers / recon fly in from the owner's map edge). PROVISIONAL. Altitudes are game-scale
# (kept below the closest camera height so aircraft stay visible), not real flight levels. In the full game these are
# unlocked by rank (experience) - see docs/MECHANICS_REFERENCE_AUDIT.md; here they are available on cooldown.
const POWERS := {
	"carpet": {"name": "Carpet Bombing", "aircraft": "b52", "sprite": "res://assets/aircraft/b52/b52_top.png",
		"icon": "res://assets/aircraft/b52/b52_icon.png", "length": 48.5, "cooldown": 90.0, "speed": 70.0, "altitude": 30.0,
		"bombs": 10, "spacing": 7.0, "damage": 150.0, "splash": 9.0},
	"supersonic": {"name": "Supersonic Strike", "aircraft": "b1", "sprite": "res://assets/aircraft/b1/b1_top.png",
		"icon": "res://assets/aircraft/b1/b1_icon.png", "length": 44.5, "cooldown": 75.0, "speed": 120.0, "altitude": 26.0,
		"bombs": 6, "spacing": 8.0, "damage": 180.0, "splash": 8.0},
	"stealth": {"name": "Stealth Precision Strike", "aircraft": "b2", "sprite": "res://assets/aircraft/b2/b2_top.png",
		"icon": "res://assets/aircraft/b2/b2_icon.png", "length": 21.0, "cooldown": 120.0, "speed": 80.0, "altitude": 32.0,
		"bombs": 1, "spacing": 0.0, "damage": 1100.0, "splash": 13.0},
	"recon": {"name": "Recon Overflight", "aircraft": "sr71", "sprite": "res://assets/aircraft/sr71/sr71_top.png",
		"icon": "res://assets/aircraft/sr71/sr71_icon.png", "length": 32.7, "cooldown": 60.0, "speed": 160.0, "altitude": 36.0,
		"reveal_width": 70.0, "reveal_time": 25.0},
}

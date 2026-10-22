# Steel Accord - structure definitions and economy constants for the B1.2 base loop (U.S. development side).
# Every number here is PROVISIONAL first-pass tuning, not balance. Art ids refer to res://assets/us/us_packs.json.
# power: positive = generated, negative = consumed. Cash is the only spendable resource; power is a capacity
# constraint (when consumption exceeds generation, production and construction slow down and radar goes dark).
class_name BuildingDefs

const START_CASH := 10000
const LOW_POWER_RATE := 0.5          # production / construction speed multiplier while under-powered
const SELL_REFUND := 0.5
const HAUL_LOAD := 300               # cash per CH-47 supply trip
const HAUL_LOAD_TIME := 3.0
const HAUL_UNLOAD_TIME := 2.0
const PILE_CASH := 20000             # per supply pile

const DEFS := {
	"command_center": {
		"name": "Command Center", "art": "command_center", "cost": 2000, "build_time": 40.0, "power": 0,
		"hp": 5000.0, "size": Vector2(26, 22), "sight": 90.0, "produces": ["dozer"], "requires": [],
		"desc": "Headquarters. Produces Dozers. Losing every structure and unit loses the match.", "buildable": false,
	},
	"power_plant": {
		"name": "Power Plant", "art": "power_plant", "cost": 800, "build_time": 12.0, "power": 10,
		"hp": 1500.0, "size": Vector2(18, 16), "sight": 50.0, "produces": [], "requires": [],
		"desc": "+10 power. Under-powered bases build and produce at half speed.",
	},
	"barracks": {
		"name": "Barracks", "art": "barracks", "cost": 500, "build_time": 15.0, "power": -1,
		"hp": 2000.0, "size": Vector2(20, 16), "sight": 60.0, "produces": ["rifleman", "at4"], "requires": ["power_plant"],
		"desc": "Trains infantry.",
	},
	"supply_depot": {
		"name": "Supply Depot", "art": "supply_depot", "model3d": "res://assets/units3d/supply_depot/supply_depot.glb", "cost": 1500, "build_time": 18.0, "power": -1,
		"hp": 2000.0, "size": Vector2(22, 18), "sight": 60.0, "produces": ["ch47"], "requires": ["power_plant"],
		"free_unit": "ch47", "desc": "Cash drop-off. Comes with one CH-47 that hauls supplies from the nearest pile.",
	},
	"war_factory": {
		"name": "War Factory", "art": "war_factory", "cost": 2000, "build_time": 25.0, "power": -2,
		"hp": 3000.0, "size": Vector2(28, 22), "sight": 60.0, "produces": ["hmmwv_50cal", "vanguard", "avenger"],
		"requires": ["supply_depot"], "desc": "Builds vehicles.",
	},
	"airfield": {
		"name": "Airfield", "art": "airfield", "cost": 1200, "build_time": 25.0, "power": -2,
		"hp": 2500.0, "size": Vector2(34, 26), "sight": 70.0, "produces": ["f16", "a10", "ah64"],
		"requires": ["war_factory"], "pads": 4, "desc": "Builds aircraft. Four parking pads; aircraft rearm on their pad.",
	},
	"defense_tower": {
		"name": "Defense Tower", "art": "defense_tower", "cost": 1000, "build_time": 15.0, "power": -2,
		"hp": 1800.0, "size": Vector2(8, 8), "sight": 95.0, "produces": [], "requires": ["barracks"],
		"weapons": [{"id": "tower_missile", "range": 85.0, "reload": 1.8, "damage": 140.0, "splash": 2.5, "proj": "missile",
			"speed": 140.0, "spread": 0.5, "targets": ["ground", "heli", "jet"], "facing_deg": 360.0}],
		"desc": "Missile tower: engages vehicles, infantry and aircraft. Fires slowly when under-powered.",
	},
	"hesco": {
		"name": "HESCO Barrier", "art": "hesco", "cost": 100, "build_time": 4.0, "power": 0,
		"hp": 1200.0, "size": Vector2(8, 4), "sight": 20.0, "produces": [], "requires": [],
		"desc": "Earth-filled barrier that blocks vehicles and infantry.",
	},
	"radar": {
		"name": "Radar", "art": "radar", "cost": 500, "build_time": 15.0, "power": -2,
		"hp": 1200.0, "size": Vector2(12, 12), "sight": 60.0, "produces": [], "requires": ["power_plant"],
		"desc": "Shows enemy units that your forces can see on the minimap. Needs power.",
	},
}

## Order of the dozer's build menu.
const BUILD_MENU := ["power_plant", "barracks", "supply_depot", "war_factory", "airfield", "defense_tower", "hesco", "radar"]

## Production cost / time for units (unit stats live in UnitDefs). PROVISIONAL.
const UNIT_COST := {
	"dozer": [1000, 10.0], "ch47": [1200, 14.0], "rifleman": [200, 5.0], "at4": [300, 7.0],
	"hmmwv_50cal": [700, 9.0], "vanguard": [900, 12.0], "avenger": [800, 10.0],
	"f16": [1400, 18.0], "a10": [1700, 20.0], "ah64": [1500, 16.0],
}

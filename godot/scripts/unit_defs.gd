# Steel Accord - unit definitions (data). Values are Steel Accord's own tuning.
class_name UnitDefs

const TEAM_COLORS := [Color(0.12, 0.30, 0.72), Color(0.70, 0.13, 0.10), Color(0.15, 0.55, 0.25), Color(0.75, 0.6, 0.1)]
const TEAM_NAMES := ["Blue", "Red", "Green", "Gold"]

const DEFS := {
	"vanguard": {
		"name": "Vanguard MBT",
		"role": "Main battle tank - anti-armour",
		"model": "res://assets/units/vanguard.glb",
		"ao_prefix": "res://assets/units/vanguard_",
		"hp": 900.0,
		"speed": 9.0,            # m/s
		"accel": 7.0,
		"turn_deg": 85.0,        # hull turn rate, deg/s
		"turret_turn_deg": 120.0,
		"radius": 2.4,           # footprint radius for separation / selection
		"height": 2.9,
		"sight": 80.0,
		"range": 60.0,
		"reload": 2.4,           # s
		"damage": 170.0,
		"spread": 1.4,           # m of aim scatter at max range
		"proj_speed": 260.0,
		"cost": 900,
	},
}

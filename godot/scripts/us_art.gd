# Steel Accord - read access to the imported U.S. art manifest (res://assets/us/us_packs.json, produced by
# tools/import_us_packs.py). Missing manifest or entries return {} so the game still runs on placeholder visuals.
class_name UsArt

const PATH := "res://assets/us/us_packs.json"
static var _data: Variant = null


static func data() -> Dictionary:
	if _data == null:
		_data = {}
		if FileAccess.file_exists(PATH):
			var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
			if d is Dictionary: _data = d
	return _data


static func rotor(id: String) -> Dictionary:
	var r: Dictionary = data().get("rotors", {})
	var e: Dictionary = r.get(id, {})
	if e.is_empty() or not ResourceLoader.exists(str(e.get("body", ""))): return {}
	return e


static func building(id: String) -> Dictionary:
	return data().get("buildings", {}).get(id, {})


static func vehicle(id: String) -> Dictionary:
	return data().get("vehicles", {}).get(id, {})


static func infantry(id: String) -> Dictionary:
	return data().get("infantry", {}).get(id, {})

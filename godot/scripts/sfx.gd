# Steel Accord - positional sound effects. Clips come from assets/audio (see content/manifest/audio.json for provenance).
# One-shots are spatial players that free themselves; a per-clip voice cap stops rapid weapons from stacking into noise.
class_name SFX

const CLIPS := {
	"a10_cannon": "res://assets/audio/a10_cannon.ogg",
	"rifle_burst": "res://assets/audio/rifle_burst.ogg",
	"mg_burst": "res://assets/audio/mg_burst.ogg",
	"explosion_big": "res://assets/audio/explosion_big.ogg",
	"rocket_launch": "res://assets/audio/rocket_launch.ogg",
	"sam_launch": "res://assets/audio/sam_launch.ogg",
	"bomb_fall": "res://assets/audio/bomb_fall.ogg",
	"jet_flyby": "res://assets/audio/jet_flyby.ogg",
	"jet_takeoff": "res://assets/audio/jet_takeoff.ogg",
	"heli_loop": "res://assets/audio/heli_loop.ogg",
	"tank_loop": "res://assets/audio/tank_loop.ogg",
	"construction_loop": "res://assets/audio/construction_loop.ogg",
	"radar_ping": "res://assets/audio/radar_ping.ogg",
}
const MAX_VOICES := {"explosion_big": 6, "mg_burst": 4, "rifle_burst": 4, "rocket_launch": 5, "a10_cannon": 3,
	"bomb_fall": 4, "jet_flyby": 3, "jet_takeoff": 2, "sam_launch": 3, "radar_ping": 2}

static var _cache := {}
static var _voices := {}      # clip id -> Array of live players
static var played := {}       # clip id -> count (test / diagnostics)


static func stream(id: String) -> AudioStream:
	if not _cache.has(id):
		var s: AudioStream = load(CLIPS[id])
		if s is AudioStreamOggVorbis: (s as AudioStreamOggVorbis).loop = id.ends_with("_loop")
		_cache[id] = s
	return _cache[id]


static func volume_db() -> float:
	var v: float = float(Game.settings.get("sfx_volume", 0.8))
	return linear_to_db(maxf(v, 0.001))


## Plays a one-shot at a world position (or attached to `parent` when `follow` is true). Returns the player or null.
static func play(parent: Node, id: String, pos: Vector3, db := 0.0, pitch := 1.0, follow := false) -> AudioStreamPlayer3D:
	if parent == null or not parent.is_inside_tree(): return null
	var live: Array = _voices.get(id, [])
	live = live.filter(func(p): return is_instance_valid(p) and p.playing)
	if live.size() >= int(MAX_VOICES.get(id, 4)):
		return null
	var p := AudioStreamPlayer3D.new()
	p.stream = stream(id)
	p.unit_size = 45.0
	p.max_distance = 520.0
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.volume_db = db + volume_db()
	p.pitch_scale = pitch
	p.panning_strength = 0.8
	parent.add_child(p)
	if not follow:
		p.top_level = true
		p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()
	live.append(p)
	_voices[id] = live
	played[id] = int(played.get(id, 0)) + 1
	return p


## Looping engine / ambience source attached to a node; caller adjusts volume_db / pitch_scale.
static func loop(parent: Node3D, id: String, db := 0.0) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.stream = stream(id)
	p.unit_size = 30.0
	p.max_distance = 360.0
	p.volume_db = db + volume_db()
	p.panning_strength = 0.8
	parent.add_child(p)
	p.play(randf() * 3.0)
	played[id] = int(played.get(id, 0)) + 1
	return p

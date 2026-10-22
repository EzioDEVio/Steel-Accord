"""Copies content/manifest/us_packs.json into the Godot project without the bulky provenance fields.
usage: python3 -I tools/export_game_manifest.py content/manifest/us_packs.json godot/assets/us/us_packs.json"""
import json, sys

def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in ("source", "blade_fit", "_about")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o

d = json.load(open(sys.argv[1]))
json.dump(strip(d), open(sys.argv[2], "w"), separators=(",", ":"))
print("ok")

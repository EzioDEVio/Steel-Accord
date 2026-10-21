#!/usr/bin/env python3
"""Steel Accord content validator (QA/build agent deliverable).

Checks the dev content tree + test map against the *pinned engine source*:
  * INI syntax/nesting, block types, field names, module names, enum tokens
  * cross-references (weapons, armor, locomotors, FX, OCLs, buttons, sets, images, strings)
  * W3D structure, HLOD/mesh naming, texture references
  * TGA formats (terrain tile rules from WorldHeightMap::countTiles)
  * .map structure, terrain classes, tile indices, start waypoints
  * asset manifest coverage + SHA-256 + license fields
  * a packed BIG (if given) contains exactly the dev tree
External references to the licensed base game are allowed only if listed in
BASE_GAME_REFS and are reported, so B2 can drive that list to zero.

usage: validate_content.py --engine <GeneralsGameCode checkout> [--big build/PZDev_B1.big]
exit code 0 = pass, 1 = errors.
"""
import argparse, glob, hashlib, json, os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import w3d, tga, big, mapformat

DEV = os.path.join(ROOT, "content", "dev")
MAPS = os.path.join(ROOT, "maps")

# Symbols we intentionally take from the licensed base game during B1 (private prototype).
BASE_GAME_REFS = {
    "commandset": {"AmericaCommandCenterCommandSet", "ChinaCommandCenterCommandSet",
                   "AmericaDozerCommandSet", "ChinaDozerCommandSet"},
    "side": {"America"},
    "faction": {"FactionCivilian"} | {"Faction" + f for f in ("America China GLA AmericaAirForceGeneral AmericaLaserGeneral AmericaSuperWeaponGeneral ChinaTankGeneral ChinaNukeGeneral ChinaInfantryGeneral GLADemolitionGeneral GLAToxinGeneral GLAStealthGeneral".split())},
    "object": {"SupplyDock", "SupplyWarehouse", "TechOilDerrick"},
}

MODULE_KEYS = ("Draw", "Body", "Behavior", "ClientUpdate")
errors, warnings, external = [], [], []


def err(m): errors.append(m)
def warn(m): warnings.append(m)


# --------------------------------------------------------------------------- engine index
def index_engine(eng):
    src = [f for f in glob.glob(os.path.join(eng, "GeneralsMD", "Code", "**", "*.*"), recursive=True)
           + glob.glob(os.path.join(eng, "Core", "**", "*.*"), recursive=True)
           if f.endswith((".cpp", ".h")) and os.sep + "Tools" + os.sep not in f]
    keys, modules = set(), set()
    for f in src:
        s = open(f, errors="ignore").read()
        keys.update(re.findall(r'\{\s*"([A-Za-z_][A-Za-z0-9_]*)"\s*,\s*[A-Za-z_:&]', s))
        if f.endswith(("ModuleFactory.cpp",)):
            modules.update(re.findall(r"addModule\(\s*([A-Za-z0-9_]+)\s*\)", s))

    def namelist(path, var):
        s = open(os.path.join(eng, path), errors="ignore").read()
        m = re.search(re.escape(var) + r"\s*\[\]\s*=\s*\{(.*?)\};", s, re.S)
        body = re.sub(r"//.*", "", m.group(1))
        body = re.sub(r"#if.*?#endif", lambda x: " ".join(re.findall(r'"[^"]+"', x.group(0))), body, flags=re.S)
        return set(re.findall(r'"([A-Z0-9_]+)"', body))

    blocks = set(re.findall(r'\{\s*"([A-Za-z]+)"\s*,\s*INI::parse',
                            open(os.path.join(eng, "Core/GameEngine/Source/Common/INI/INI.cpp")).read()))
    return dict(
        keys=keys, modules=modules, blocks=blocks,
        kindof=namelist("GeneralsMD/Code/GameEngine/Source/Common/System/KindOf.cpp", "KindOfMaskType::s_bitNameList"),
        damage=namelist("Core/GameEngine/Source/GameLogic/System/Damage.cpp", "DamageTypeFlags::s_bitNameList"),
        terrain=namelist("Core/GameEngine/Include/Common/TerrainTypes.h", "terrainTypeNames"),
        guicmd=namelist("Core/GameEngine/Include/GameClient/ControlBar.h", "TheGuiCommandNames"),
        death=namelist("Core/GameEngine/Include/GameLogic/Damage.h", "TheDeathNames"),
    )


# --------------------------------------------------------------------------- INI parsing
def parse_ini(path):
    """Returns list of top-level blocks: dict(type, name, lines=[(depth, ctx, key, value, lineno)])."""
    out, stack, cur = [], [], None
    for no, raw in enumerate(open(path, encoding="latin-1"), 1):
        line = raw.split(";")[0].strip()
        if not line or line.startswith("//"):
            continue
        if line.lower() == "end":
            if not stack:
                err(f"{rel(path)}:{no}: stray End"); continue
            stack.pop()
            if not stack:
                out.append(cur); cur = None
            continue
        if not stack:
            parts = line.split()
            cur = dict(type=parts[0], name=parts[1] if len(parts) > 1 else "", lines=[], file=path, line=no)
            stack.append(parts[0]); continue
        if "=" in line:
            k, v = [x.strip() for x in line.split("=", 1)]
            ctx = stack[-1]
            cur["lines"].append((len(stack), ctx, k, v, no))
            if k in MODULE_KEYS and cur["type"] == "Object":
                stack.append(f"{k}:{v.split()[0]}")
            elif k in ("ConditionState", "TransitionState"):   # 'Key = flags' that opens a sub-block
                stack.append(k)
            continue
        # bare word opens a sub-block (WeaponSet, DefaultConditionState, Tracer, CreateObject, ...)
        cur["lines"].append((len(stack), stack[-1], line.split()[0], None, no))
        stack.append(line.split()[0])
    if stack:
        err(f"{rel(path)}: unterminated block {stack}")
    return out


def rel(p): return os.path.relpath(p, ROOT)


def parse_str(path):
    labels, lines = {}, [l.rstrip("\n") for l in open(path, encoding="utf-8")]
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        if not l or l.startswith("//"):
            i += 1; continue
        label = l; i += 1
        text = []
        while i < len(lines) and lines[i].strip().upper() != "END":
            text.append(lines[i].strip()); i += 1
        if i >= len(lines): err(f"{rel(path)}: label {label} missing END")
        if not (text and text[0].startswith('"') and text[-1].endswith('"')):
            err(f"{rel(path)}: label {label} text must be quoted")
        labels[label] = " ".join(text); i += 1
    return labels


# --------------------------------------------------------------------------- checks
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--big")
    ap.add_argument("--skip-manifest", action="store_true", help="for mutation tests only")
    a = ap.parse_args()
    E = index_engine(a.engine)
    print(f"engine index: {len(E['keys'])} field names, {len(E['modules'])} modules, {len(E['kindof'])} KindOf")

    ini_files = sorted(glob.glob(os.path.join(DEV, "Data", "INI", "**", "*.ini"), recursive=True))
    map_inis = sorted(glob.glob(os.path.join(MAPS, "*", "map.ini")))
    blocks = [b for f in ini_files + map_inis for b in parse_ini(f)]
    defs = {}
    for b in blocks:
        if b["type"] not in E["blocks"]:
            err(f"{rel(b['file'])}:{b['line']}: unknown top-level block '{b['type']}'")
        is_override = b["file"] in map_inis
        key = (b["type"], b["name"])
        if key in defs and not is_override:
            err(f"duplicate definition {key}")
        if not is_override:
            defs[key] = b
    names = lambda t: {n for (tt, n) in defs if tt == t}
    # Strings resolve from the map.str of whichever map is being played, so every label used by
    # global content must exist in EVERY map's map.str (intersection), until B2 ships a global table.
    per_map = {s: parse_str(s) for s in glob.glob(os.path.join(MAPS, "*", "map.str"))}
    common = set.intersection(*(set(v) for v in per_map.values())) if per_map else set()
    strings = {k: v for d in per_map.values() for k, v in d.items() if k in common}

    def need(kind, name, where, base_kind=None):
        if name in names(kind):
            return
        if base_kind and name in BASE_GAME_REFS.get(base_kind, ()):
            external.append(f"{kind} '{name}' <- {where}"); return
        err(f"{where}: unresolved {kind} '{name}'")

    def need_str(label, where):
        if label not in strings:
            err(f"{where}: string label '{label}' missing from map.str")

    for b in blocks:
        where0 = f"{rel(b['file'])}"
        for depth, ctx, k, v, no in b["lines"]:
            where = f"{where0}:{no}"
            if v is not None and k not in E["keys"] and not (b["type"] == "CommandSet" and k.isdigit()):
                err(f"{where}: field '{k}' not found in engine FieldParse tables")
            if k in MODULE_KEYS and v:
                mod = v.split()[0]
                if mod not in E["modules"]:
                    err(f"{where}: module '{mod}' is not registered in a ModuleFactory")
                if len(v.split()) < 2:
                    err(f"{where}: module '{mod}' needs a ModuleTag")
            if k == "KindOf":
                for t in v.split():
                    if t not in E["kindof"]: err(f"{where}: KindOf '{t}' unknown")
            if k == "DamageType" and v not in E["damage"]:
                err(f"{where}: DamageType '{v}' unknown")
            if k == "DeathType" and v not in E["death"]:
                err(f"{where}: DeathType '{v}' unknown")
            if k == "Armor" and b["type"] == "Armor":
                dt, pct = v.split()
                if dt.upper() != "DEFAULT" and dt not in E["damage"]: err(f"{where}: armor damage type '{dt}' unknown")
                if not re.fullmatch(r"\d+%", pct): err(f"{where}: armor value '{pct}' must be N%")
            if k == "Class" and b["type"] == "Terrain" and v not in E["terrain"]:
                err(f"{where}: terrain class '{v}' unknown")
            if k == "Command" and b["type"] == "CommandButton" and v not in E["guicmd"]:
                err(f"{where}: GUI command '{v}' unknown")
            # cross references
            if k == "Weapon" and ctx == "WeaponSet": need("Weapon", v.split()[1], where)
            if k == "Armor" and ctx == "ArmorSet": need("Armor", v, where)
            if k == "Locomotor" and b["type"] == "Object": need("Locomotor", v.split()[1], where)
            if k == "CommandSet" and b["type"] == "Object": need("CommandSet", v, where)
            if k in ("ButtonImage", "SelectPortrait"): need("MappedImage", v, where)
            if k in ("DeathFX", "FireFX"): need("FXList", v, where)
            if k == "CreationList": need("ObjectCreationList", v, where)
            if k in ("TracerName", "ObjectNames"):
                for o in v.split(): need("Object", o, where)
            if k == "Object" and b["type"] == "CommandButton": need("Object", v, where)
            if k == "ProjectileObject" and v.upper() != "NONE": need("Object", v, where)
            if b["type"] == "CommandSet" and k.isdigit():
                need("CommandButton", v, where)
            if k in ("DisplayName", "TextLabel", "DescriptLabel"): need_str(v, where)
            if k == "Side":
                if v in BASE_GAME_REFS["side"]: external.append(f"side '{v}' <- {where}")
            if k == "Model" and v.upper() != "NONE":
                p = os.path.join(DEV, "Art", "W3D", v + ".W3D")
                if not os.path.exists(p): err(f"{where}: model file Art/W3D/{v}.W3D missing")
                else: check_w3d(p, v)
            if k == "Texture" and b["type"] == "MappedImage":
                check_tex(os.path.join(DEV, "Art", "Textures", v), where)
            if k == "Texture" and b["type"] == "Terrain":
                check_terrain_tga(os.path.join(DEV, "Art", "Terrain", v), where)
        if b["file"] in map_inis and b["type"] == "CommandSet":
            need("CommandSet", b["name"], rel(b["file"]), base_kind="commandset")
        if b["type"] == "MappedImage":
            kv = {k: v for _, _, k, v, _ in b["lines"]}
            m = re.match(r"Left:(\d+) Top:(\d+) Right:(\d+) Bottom:(\d+)", kv["Coords"])
            l, t, r, bt = map(int, m.groups())
            tw, th = int(kv["TextureWidth"]), int(kv["TextureHeight"])
            img = tga.load(os.path.join(DEV, "Art", "Textures", kv["Texture"]))
            if img.shape[1] != tw or img.shape[0] != th:
                err(f"{where0}: {b['name']} TextureWidth/Height {tw}x{th} != file {img.shape[1]}x{img.shape[0]}")
            if not (0 <= l < r < tw and 0 <= t < bt < th):
                err(f"{where0}: {b['name']} coords outside texture")

    for mp in glob.glob(os.path.join(MAPS, "*", "*.map")):
        check_map(mp, strings)
    if not a.skip_manifest:
        check_manifest()
    if a.big:
        check_big(a.big)

    print(f"\nINI blocks: {len(blocks)}  definitions: {len(defs)}  strings: {len(strings)}")
    for w in warnings: print("WARN ", w)
    print("\nExternal base-game references (B1 prototype only; must be zero for B2):")
    for x in sorted(set(external)): print("  -", x)
    for e in errors: print("ERROR", e)
    print("\nRESULT:", "PASS" if not errors else f"FAIL ({len(errors)} errors)")
    return 1 if errors else 0


def check_tex(path, where):
    if not os.path.exists(path):
        err(f"{where}: texture {rel(path)} missing"); return
    d = open(path, "rb").read(18)
    if d[2] != 2 or d[16] not in (24, 32): err(f"{where}: {rel(path)} must be uncompressed 24/32-bit TGA")


def check_terrain_tga(path, where):
    check_tex(path, where)
    if os.path.exists(path):
        w, h = struct.unpack_from("<HH", open(path, "rb").read(18), 12)
        if w % 64 or h % 64 or w // 64 > 10 or w != h:
            err(f"{where}: terrain texture {w}x{h} must be square, multiple of 64, <= 640")


def check_w3d(path, model):
    data = open(path, "rb").read()
    try:
        ch = w3d.walk(data)
    except ValueError as e:
        err(f"{rel(path)}: {e}"); return
    meshes, hlod_name, subs, texnames = [], None, [], []
    for d, t, s, sub, p in ch:
        if t == 0x01F:
            if s != 116: err(f"{rel(path)}: mesh header size {s} != 116")
            mn = p[8:24].split(b"\0")[0].decode(); cn = p[24:40].split(b"\0")[0].decode()
            meshes.append(f"{cn}.{mn}" if cn else mn)
            nt, nv = struct.unpack_from("<II", p, 40)
        if t == 0x020 and s % 32: err(f"{rel(path)}: triangle chunk not multiple of 32")
        if t == 0x701: hlod_name = p[8:24].split(b"\0")[0].decode()
        if t == 0x704: subs.append(p[4:36].split(b"\0")[0].decode())
        if t == 0x032: texnames.append(p.split(b"\0")[0].decode())
    if hlod_name != model.upper(): err(f"{rel(path)}: HLOD name '{hlod_name}' != model '{model}'")
    for s_ in subs:
        if s_ not in meshes: err(f"{rel(path)}: HLOD sub-object {s_} has no mesh")
    for tn in texnames:
        check_tex(os.path.join(DEV, "Art", "Textures", tn), rel(path))


def check_map(path, strings):
    m = mapformat.decode(open(path, "rb").read())
    hd, bl = m["height"], m["blend"]
    W, H, B = hd["width"], hd["height"], hd["border"]
    terr_defs = {}
    for f in glob.glob(os.path.join(DEV, "Data", "INI", "Terrain", "*.ini")):
        for b in parse_ini(f):
            terr_defs[b["name"]] = {k: v for _, _, k, v, _ in b["lines"]}["Texture"]
    for c in bl["classes"]:
        if c["name"] not in terr_defs:
            err(f"{rel(path)}: terrain class '{c['name']}' not defined in dev Terrain INI"); continue
        w_, h_ = struct.unpack_from("<HH", open(os.path.join(DEV, "Art", "Terrain", terr_defs[c["name"]]), "rb").read(18), 12)
        tiles = (min(w_, h_) // 64) ** 2
        if tiles < c["num"] or c["width"] ** 2 != c["num"]:
            err(f"{rel(path)}: class {c['name']} declares {c['num']} tiles, texture provides {tiles}")
    if max(t >> 2 for t in bl["tiles"]) >= bl["numBitmapTiles"]: err(f"{rel(path)}: tile index out of range")
    if sum(c["num"] for c in bl["classes"]) != bl["numBitmapTiles"]: err(f"{rel(path)}: numBitmapTiles mismatch")
    pw, ph = hd["boundaries"][0]
    wps = {dict((k, v) for k, t, v in o["props"]).get("waypointName"): o for o in m["objects"] if o["tmpl"] == "*Waypoints/Waypoint"}
    for need in ("Player_1_Start", "Player_2_Start"):
        o = wps.get(need)
        if not o: err(f"{rel(path)}: missing waypoint {need}"); continue
        if not (0 < o["x"] < pw * 10 and 0 < o["y"] < ph * 10): err(f"{rel(path)}: {need} outside playable area")
    world = {k: v for k, t, v in m["world"]}
    # User (non-official) maps must NOT carry a mapName tag: MapCache::addMap resolves it against the
    # global string table only and the list shows "MISSING: ..." (observed in client test, 2026-10-21).
    if "mapName" in world: err(f"{rel(path)}: remove WorldInfo mapName for user maps (shows MISSING in map list)")
    our_objects = set()
    for f in glob.glob(os.path.join(DEV, "Data", "INI", "Object", "*.ini")):
        our_objects |= {b["name"] for b in parse_ini(f) if b["type"] == "Object"}
    for o in m["objects"]:
        t = o["tmpl"]
        if t.startswith("*Waypoints/") or t in our_objects: continue
        if t in BASE_GAME_REFS["object"]: external.append(f"object '{t}' <- {rel(path)}")
        else: err(f"{rel(path)}: map object '{t}' unresolved")
        if not (0 < o["x"] < pw * 10 and 0 < o["y"] < ph * 10): err(f"{rel(path)}: object {t} outside playable area")
    names = {dict((k, v) for k, t, v in s["dict"]).get("playerName") for s in m["sides"]}
    for f in ("SkirmishAmerica", "SkirmishChina"):
        if f not in names: err(f"{rel(path)}: side '{f}' missing - skirmish AI would be idle")
    for s in m["sides"]:
        fac = dict((k, v) for k, t, v in s["dict"]).get("playerFaction")
        if fac:
            if fac in BASE_GAME_REFS["faction"]: external.append(f"faction '{fac}' <- {rel(path)} side list")
            else: err(f"{rel(path)}: side faction '{fac}' unresolved")
    if not os.path.exists(path[:-4] + ".tga"): warn(f"{rel(path)}: no preview .tga")
    print(f"map {rel(path)}: {W}x{H} border {B}, playable {pw}x{ph}, {len(m['objects'])} objects, waypoints {sorted(wps)}")


def check_manifest():
    man = json.load(open(os.path.join(ROOT, "content", "MANIFEST.json")))
    listed = {a["path"]: a for a in man["assets"]}
    files = [rel(f) for f in glob.glob(os.path.join(DEV, "**", "*"), recursive=True) if os.path.isfile(f)]
    files += [rel(f) for f in glob.glob(os.path.join(MAPS, "**", "*"), recursive=True) if os.path.isfile(f)]
    for f in files:
        a = listed.get(f.replace(os.sep, "/"))
        if not a: err(f"manifest: {f} not listed"); continue
        h = hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest()
        if a["sha256"] != h: err(f"manifest: {f} hash mismatch (regenerate manifest)")
        for fld in ("origin", "creator", "tool", "license", "ship_status"):
            if not a.get(fld): err(f"manifest: {f} missing '{fld}'")
    for p in listed:
        if not os.path.exists(os.path.join(ROOT, p)): err(f"manifest lists missing file {p}")


def check_big(path):
    entries = big.read(path)
    dev = {rel(f)[len("content/dev/"):].replace("/", "\\"): f for f in glob.glob(os.path.join(DEV, "**", "*"), recursive=True) if os.path.isfile(f)}
    if set(entries) != set(dev): err(f"BIG contents differ from dev tree: {set(entries) ^ set(dev)}")
    for n, d in entries.items():
        if n in dev and open(dev[n], "rb").read() != d: err(f"BIG entry {n} differs from source")
    print(f"BIG {rel(path)}: {len(entries)} entries OK")


if __name__ == "__main__":
    sys.exit(main())

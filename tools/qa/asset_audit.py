#!/usr/bin/env python3
"""Steel Accord QA - B2 shipped-asset provenance audit (read-only).

Walks every file that the Godot "Windows" export preset puts into the build, classifies it (code / data / asset),
and matches each asset to a provenance record:

  1. exact path in a manifest under content/manifest/*.json (audio, ui_icons, us_packs, aircraft) or content/MANIFEST.json
  2. folder-level manifest coverage (assets/us/** -> us_packs.json, assets/aircraft/** -> aircraft.json)
  3. textures that belong to a GLB (Godot-extracted "<glbstem>_<image>" files and the generator's own copies)
     inherit the GLB's record
  4. GLBs / maps with NO manifest entry get an *audit-derived* record from their generator script (the pipeline kit
     the script imports is read at run time). These are marked manifest_entry=false and are never "shippable":
     the project rule (docs/ARCHITECTURE.md) requires a manifest entry before ship status.

Status values: shippable / dev_only / unknown.  Nothing is modified; output is a JSON report.

Usage: python3 -I tools/qa/asset_audit.py [--repo /home/claude/pzh] [--export-log build/clean_b2/export.log]
                                          [--out build/reports/asset_audit_b2.json]
"""
import argparse
import collections
import fnmatch
import hashlib
import json
import os
import re
import struct
import sys

CODE_EXT = {".gd", ".gdshader", ".gdshaderinc", ".tscn", ".tres", ".godot"}
NATIVE_RES_EXT = {".gd", ".gdshader", ".gdshaderinc", ".tscn", ".tres", ".res", ".scn"}
NEVER_EXPORTED = {"export_presets.cfg"}

# ---------------------------------------------------------------------------------------------------- pipelines
# Pipeline classes, derived from the generator script headers (read during the audit):
#   projected  = albedo is a depth-tested projection of client-supplied AI concept art (DEV ONLY packs)
#   procedural = geometry and texture built in code; concept art only informed proportions / sampled palette colours
KIT_CLASS = {
    "vehkit": "projected", "airkit": "projected",
    "vehkit_ir": "procedural", "airkit_ir": "procedural",
    "bldkit": "procedural", "bldkit_b": "procedural", "prop_zb_common": "procedural", "inf_kit": "procedural",
}
# scripts that do not import a kit: class taken from their own docstring (quoted in 'evidence')
SCRIPT_CLASS = {
    "veh_m88_3d.py": ("projected", "docstring: texture is 'a normal-weighted blend of projections of the concept views'"),
    "air_ch47_3d.py": ("projected", "docstring: 'textured by depth-tested projection of those two views'"),
    "bld_supply_depot_3d.py": ("procedural", "docstring: 'procedurally modelled + texture-baked in Blender'"),
    "mbt_vanguard.py": ("procedural", "docstring: 'original main battle tank ... procedurally modelled in Blender'"),
    "heli_kite.py": ("procedural", "docstring: 'original tandem-seat attack helicopter ... procedurally modelled'"),
    "bld_command_post.py": ("procedural", "docstring: 'original HQ building ... procedurally modelled in Blender'"),
    "inf_rifleman.py": ("procedural", "G1 code-built rifleman (no image inputs)"),
    "env_props.py": ("procedural", "G1 code-built props (no image inputs)"),
    "prop_flag_3d.py": ("procedural", "code-built flag mesh with a drawn national-flag texture"),
}
# GLB path (relative to godot/) -> generator script in tools/art
def glb_generator(rel):
    stem = os.path.splitext(os.path.basename(rel))[0]
    fixed = {
        "assets/units/vanguard.glb": "mbt_vanguard.py", "assets/units/kite.glb": "heli_kite.py",
        "assets/units/rifleman.glb": "inf_rifleman.py", "assets/buildings/command_post.glb": "bld_command_post.py",
        "assets/props/props.glb": "env_props.py",
        "assets/units3d/rifleman/rifleman.glb": "inf_rifleman_rigged.py",
        "assets/units3d/paratrooper/parachute_personnel.glb": "inf_paratrooper_3d.py",
        "assets/units3d/paratrooper/paratrooper.glb": "inf_paratrooper_3d.py",
        "assets/units3d/at4/at4.glb": "inf_at4_3d.py",
        "assets/units3d/ir_shahed_rail/ir_shahed_rail.glb": "air_ir_shahed_3d.py",
    }
    if rel in fixed:
        return fixed[rel]
    if stem in ("hmmwv", "hmmwv_50cal", "hmmwv_medical", "hmmwv_tow", "avenger"):
        return "veh_hmmwv_3d.py"
    if stem in ("medic", "saw_gunner", "m240_gunner", "sniper", "ranger", "special_forces", "pilot", "eod_engineer"):
        return "inf_roster_3d.py"
    if stem in ("ir_rifleman", "ir_rpg", "ir_mg", "ir_sniper", "ir_medic", "ir_engineer", "ir_paratrooper", "irgc_sf"):
        return "inf_iran_3d.py"
    if stem in ("flag_iran", "flag_usa"):
        return "prop_flag_3d.py"
    for pat in ("air_%s_3d.py", "veh_%s_3d.py", "bld_%s_3d.py", "prop_%s.py"):
        if os.path.exists(os.path.join(ART_DIR, pat % stem)):
            return pat % stem
    return None


# real-world designs / names / insignia: release review flag (separate from licence)
REAL_WORLD = {
    "a10", "ac130", "ah64", "b1", "b2", "b52", "c130", "c17", "ch47", "f16", "f22", "f35", "fa18", "sr71", "uh60",
    "abrams", "bradley", "hmmwv", "hmmwv_50cal", "hmmwv_medical", "hmmwv_tow", "avenger", "m113", "m777", "m88",
    "mrap", "paladin", "stryker", "at4", "m240_gunner",
    "ir_ah1j", "ir_c130", "ir_ch47", "ir_f14", "ir_f4", "ir_shahed", "ir_shahed_rail", "ir_su24",
    "ir_bmp2", "ir_boragh", "ir_karrar", "ir_t72s", "irgc_sf",
}
INSIGNIA = {"flag_iran", "flag_usa", "ir_rifleman", "ir_rpg", "ir_mg", "ir_sniper", "ir_medic", "ir_engineer",
            "ir_paratrooper", "irgc_sf"}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def glb_images(p):
    b = open(p, "rb").read(1 << 22)
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(open(p, "rb").read(20 + n)[20:])
    return [i.get("name") for i in j.get("images", [])], j["asset"].get("generator", "")


def parse_preset(path, name="Windows"):
    cur, out = None, {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        m = re.match(r"\[(preset\.\d+)\]$", line)
        if m:
            cur = m.group(1)
            out[cur] = {}
            continue
        if cur and "=" in line:
            k, v = line.split("=", 1)
            out[cur][k] = v.strip().strip('"')
    for v in out.values():
        if v.get("name") == name:
            return v
    raise SystemExit("preset %s not found" % name)


def import_info(p):
    """importer name from a .import sidecar (None if no sidecar)."""
    imp = p + ".import"
    if not os.path.exists(imp):
        return None
    for line in open(imp, encoding="utf-8", errors="replace"):
        if line.startswith("importer="):
            return line.split("=", 1)[1].strip().strip('"')
    return "?"


# ---------------------------------------------------------------------------------------------------- manifests
def load_manifests(repo):
    idx = {}            # res path -> record
    mdir = os.path.join(repo, "content", "manifest")
    files_read = []

    def put(res, rec):
        idx.setdefault(res, rec)

    a = json.load(open(os.path.join(mdir, "audio.json")))
    files_read.append("content/manifest/audio.json")
    for cid, c in a["clips"].items():
        prov = c.get("provenance", "")
        st = c.get("status", "")
        status = "dev_only"     # neither "dev_only" nor "dev_ok; release needs..." is a release clearance
        lic = "Pixabay Content License" if "Pixabay Content License" in prov else "not stated"
        put(c["file"], {"manifest": "content/manifest/audio.json#clips." + cid, "licence": lic, "status": status,
                        "manifest_status": st, "provenance": prov, "source_file": c.get("source_file")})

    u = json.load(open(os.path.join(mdir, "ui_icons.json")))
    files_read.append("content/manifest/ui_icons.json")
    for it in u["items"]:
        put(it["path"], {"manifest": "content/manifest/ui_icons.json#" + it["id"], "licence": u.get("license"),
                         "status": "shippable" if u.get("status") == "shippable" else "unknown",
                         "manifest_status": u.get("status"), "provenance": u.get("method")})

    ac = json.load(open(os.path.join(mdir, "aircraft.json")))
    files_read.append("content/manifest/aircraft.json")
    for it in ac["aircraft"]:
        for role, res in (it.get("game_files") or {}).items():
            put(res, {"manifest": "content/manifest/aircraft.json#%s.%s" % (it["id"], role),
                      "licence": it.get("license_status"), "status": "dev_only",
                      "manifest_status": it.get("shipping_status"), "provenance": it.get("provenance")})

    up = json.load(open(os.path.join(mdir, "us_packs.json")))
    files_read.append("content/manifest/us_packs.json")
    about = up.get("_about", "")

    def walk(o, trail):
        if isinstance(o, dict):
            flags = o.get("flags")
            for k, v in o.items():
                walk(v, trail + [k] if not isinstance(v, (dict, list)) or k != "flags" else trail)
                if isinstance(v, str) and v.startswith("res://"):
                    put(v, {"manifest": "content/manifest/us_packs.json#" + ".".join(trail + [k]),
                            "licence": "AI-generated concept art supplied by client (generator terms; not cleared)",
                            "status": "dev_only", "manifest_status": "DEV ONLY" + (" flags=%s" % flags if flags else ""),
                            "provenance": about})
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, trail + [str(i)])
                if isinstance(v, str) and v.startswith("res://"):
                    put(v, {"manifest": "content/manifest/us_packs.json#" + ".".join(trail + [str(i)]),
                            "licence": "AI-generated concept art supplied by client (generator terms; not cleared)",
                            "status": "dev_only", "manifest_status": "DEV ONLY", "provenance": about})
    walk(up, [])

    # content/MANIFEST.json (Zero Hour-era B1 tree): indexed for completeness; it lists content/ and maps/ paths only
    top = json.load(open(os.path.join(repo, "content", "MANIFEST.json")))
    files_read.append("content/MANIFEST.json")
    for e in top.get("assets", []):
        put("repo://" + e["path"], {"manifest": "content/MANIFEST.json", "licence": e.get("license"),
                                    "status": "dev_only", "manifest_status": e.get("ship_status"),
                                    "provenance": e.get("origin")})
    folder_rules = [
        ("res://assets/us/", {"manifest": "content/manifest/us_packs.json (folder-level: assets/us/**)",
                              "licence": "AI-generated concept art supplied by client (generator terms; not cleared)",
                              "status": "dev_only", "manifest_status": "DEV ONLY", "provenance": about}),
        ("res://assets/aircraft/", {"manifest": "content/manifest/aircraft.json (folder-level: assets/aircraft/**)",
                                    "licence": ac["aircraft"][0].get("license_status"), "status": "dev_only",
                                    "manifest_status": "DEV ONLY", "provenance": ac["aircraft"][0].get("provenance")}),
    ]
    return idx, folder_rules, files_read


# ---------------------------------------------------------------------------------------------------- GLB records
def glb_record(godot, rel):
    script = glb_generator(rel)
    stem = os.path.splitext(os.path.basename(rel))[0]
    imgs, gen = glb_images(os.path.join(godot, rel))
    rec = {"manifest": None, "manifest_entry": False, "glb_generator_tag": gen, "embedded_images": imgs,
           "generator_script": ("tools/art/" + script) if script else None}
    if not script or not os.path.exists(os.path.join(ART_DIR, script)):
        rec.update(status="unknown", licence="unknown", provenance="no generator script found", evidence="none")
        return rec
    src = open(os.path.join(ART_DIR, script), encoding="utf-8").read()
    kits = sorted(set(re.findall(r"^\s*(?:import|from)\s+(vehkit_ir|vehkit|airkit_ir|airkit|bldkit_b|bldkit|"
                                 r"inf_kit|prop_zb_common)\b", src, re.M)))
    cls, ev = None, None
    for k in kits:
        cls = KIT_CLASS[k]
        ev = "imports %s (%s pipeline)" % (k, cls)
        if cls == "projected":
            break
    if cls is None and script in SCRIPT_CLASS:
        cls, ev = SCRIPT_CLASS[script]
    rec["pipeline"] = cls or "unclassified"
    rec["evidence"] = ev or "no kit import and no docstring rule"
    rec["stem_named_in_script"] = stem in src or stem.replace("ir_", "") in src
    if cls == "projected":
        rec.update(status="dev_only",
                   licence="derivative of client-supplied AI concept art (us_packs / aircraft packs, DEV ONLY)",
                   provenance="Blender script %s; albedo projected from client AI concept art" % script)
    elif cls == "procedural":
        rec.update(status="unknown", recommended_status="shippable once a manifest entry is written",
                   licence="project-original (code-generated); no licence recorded in a manifest",
                   provenance="Blender script %s; procedural geometry + texture" % script)
        if script in ("inf_kit.py",) or "inf_kit" in kits:
            rec["provenance"] += "; camo palette colours k-means-sampled from client AI concept art (colour values only)"
        if "vehkit_ir" in kits or "airkit_ir" in kits:
            rec["provenance"] += "; client AI concept panels used as visual reference only (not projected)"
    else:
        rec.update(status="unknown", licence="unknown", provenance="generator %s not classified" % script)
    flags = []
    if stem in REAL_WORLD:
        flags.append("depicts a real-world equipment design/name (trademark & design review)")
    if stem in INSIGNIA:
        flags.append("carries a national flag / insignia texture")
    if flags:
        rec["review_flags"] = flags
    return rec


OTHER_RULES = [
    # (fnmatch on rel path, record) - audit-derived records, never manifest entries
    ("assets/iran/icons/*.png", {"status": "unknown", "licence": "unknown (no record)",
        "provenance": "no generator script or manifest record found; visual inspection (ir_t72s, ir_rifleman): "
                      "appear to be renders of the project's own Iran GLBs", "manifest_entry": False}),
    ("assets/ui/menu_bg.png", {"status": "unknown", "licence": "unknown (no record)",
        "provenance": "no generator script or manifest record found; visual inspection: render of the original "
                      "'Vanguard' tank model on procedural terrain", "manifest_entry": False}),
    ("maps/zagros_basin/preview.png", {"status": "unknown", "recommended_status": "shippable once a manifest entry is written",
        "licence": "project-original (code-generated); no licence recorded in a manifest",
        "provenance": "tools/map/make_previews.py render of the synthetic map", "manifest_entry": False}),
    ("maps/proving_ground/preview.png", {"status": "unknown", "recommended_status": "shippable once a manifest entry is written",
        "licence": "project-original (code-generated); no licence recorded in a manifest",
        "provenance": "tools/map/make_previews.py", "manifest_entry": False}),
    ("maps/zagros_basin/*", {"status": "unknown", "recommended_status": "shippable once a manifest entry is written",
        "licence": "project-original (code-generated); no licence recorded in a manifest",
        "provenance": "tools/map/gen_zagros_basin.py; synthetic procedural terrain, no DEM used "
                      "(docs/MAP_ZAGROS_BASIN.md)", "manifest_entry": False}),
]


# ---------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/home/claude/pzh")
    ap.add_argument("--export-log", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)
    godot = os.path.join(repo, "godot")
    global ART_DIR
    ART_DIR = os.path.join(repo, "tools", "art")
    out = a.out or os.path.join(repo, "build", "reports", "asset_audit_b2.json")

    preset = parse_preset(os.path.join(godot, "export_presets.cfg"))
    inc = [s.strip() for s in preset.get("include_filter", "").split(",") if s.strip()]
    exc = [s.strip() for s in preset.get("exclude_filter", "").split(",") if s.strip()]

    idx, folder_rules, manifests_read = load_manifests(repo)

    # 1. walk
    exported, not_exported = [], []
    for root, dirs, files in os.walk(godot):
        relroot = os.path.relpath(root, godot)
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        if os.path.exists(os.path.join(root, ".gdignore")):
            dirs[:] = []
            for f in files:
                if f != ".gdignore":
                    not_exported.append({"path": os.path.normpath(os.path.join(relroot, f)), "reason": ".gdignore folder"})
            continue
        for f in sorted(files):
            rel = os.path.normpath(os.path.join(relroot, f))
            if f.startswith(".") or f.endswith(".import") or f.endswith(".uid"):
                continue
            if f in NEVER_EXPORTED:
                continue
            if any(fnmatch.fnmatch(rel, e) for e in exc):
                not_exported.append({"path": rel, "reason": "preset exclude_filter"})
                continue
            ext = os.path.splitext(f)[1].lower()
            imp = import_info(os.path.join(root, f))
            if f == "project.godot" or ext in NATIVE_RES_EXT or (imp and imp not in ("skip",)) or \
                    any(fnmatch.fnmatch(f, i) or fnmatch.fnmatch(rel, i) for i in inc):
                exported.append((rel, ext, imp))
            else:
                not_exported.append({"path": rel, "reason": "importer=skip (inspectable copy; the GLB embeds it)"
                                     if imp == "skip" else "not a resource and not in include_filter"})

    # GLB index per directory (for extracted / generator textures)
    glbs = {}
    for rel, ext, _ in exported:
        if ext == ".glb":
            d = os.path.dirname(rel)
            imgs, _g = glb_images(os.path.join(godot, rel))
            glbs.setdefault(d, []).append((os.path.splitext(os.path.basename(rel))[0], rel, imgs))
    glb_recs = {}

    # 2. classify
    entries = []
    for rel, ext, imp in exported:
        p = os.path.join(godot, rel)
        res = "res://" + rel
        e = {"path": "godot/" + rel, "res": res, "size": os.path.getsize(p), "importer": imp}
        if ext in CODE_EXT or rel == "project.godot":
            e.update(category="code", status="n/a (code)", manifest=None, licence="project code")
            entries.append(e)
            continue
        if ext == ".json" and not rel.startswith("maps/"):
            e.update(category="data", status="n/a (data)", manifest=None, licence="project data",
                     note="generator/QA metadata JSON shipped via include_filter *.json")
            entries.append(e)
            continue
        e["category"] = "asset"
        e["sha256"] = sha256(p)
        rec = None
        if res in idx:
            rec = dict(idx[res], manifest_entry=True, match="exact path")
        if rec is None and ext == ".glb":
            if rel not in glb_recs:
                glb_recs[rel] = glb_record(godot, rel)
            rec = dict(glb_recs[rel], match="GLB generator script (audit-derived)")
        if rec is None and ext in (".png", ".jpg", ".jpeg", ".webp"):
            d, base = os.path.dirname(rel), os.path.splitext(os.path.basename(rel))[0]
            best = None
            for stem, grel, imgs in glbs.get(d, []):
                if base == stem or base.startswith(stem + "_") or base in imgs:
                    if best is None or len(stem) > len(best[0]):
                        best = (stem, grel, imgs)
            if best:
                if best[1] not in glb_recs:
                    glb_recs[best[1]] = glb_record(godot, best[1])
                kind = "Godot-extracted GLB image" if base.startswith(best[0] + "_") and \
                    base[len(best[0]) + 1:] in best[2] else "generator output beside GLB"
                rec = dict(glb_recs[best[1]], match="%s -> %s" % (kind, "godot/" + best[1]), parent_glb="godot/" + best[1])
        if rec is None:
            for pre, r in folder_rules:
                if res.startswith(pre):
                    rec = dict(r, manifest_entry=True, match="folder-level")
                    break
        if rec is None:
            for pat, r in OTHER_RULES:
                if fnmatch.fnmatch(rel, pat):
                    rec = dict(r, manifest=None, match="audit rule %s" % pat)
                    break
        if rec is None:
            rec = {"status": "unknown", "licence": "unknown", "manifest": None, "manifest_entry": False,
                   "match": "none", "provenance": "no manifest entry and no audit rule"}
        rec.setdefault("manifest", None)
        e.update(rec)
        entries.append(e)

    # 3. cross-check against the export log
    xcheck = None
    if a.export_log and os.path.exists(a.export_log):
        raw = open(a.export_log, encoding="utf-8", errors="replace").read()
        raw = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        stored = set(re.findall(r"Storing File: (res://\S+)", raw))
        src = set()
        for s in stored:
            if s.startswith("res://.godot/"):
                continue
            for suf, rep in ((".import", ""), (".remap", ""), (".gdc", ".gd")):
                if s.endswith(suf):
                    s = s[: -len(suf)] + rep
                    break
            src.add(s)
        mine = {"res://" + r for r, _, _ in exported}
        xcheck = {"export_log": os.path.relpath(a.export_log, repo), "stored_entries": len(stored),
                  "source_paths_in_log": len(src),
                  "walked_but_not_in_log": sorted(mine - src - {"res://project.godot"}),
                  "in_log_but_not_walked": sorted(s for s in src - mine
                                                  if not s.endswith(".uid") and s not in ("res://project.binary",))}

    assets = [e for e in entries if e["category"] == "asset"]
    by_status = collections.Counter(e["status"] for e in assets)
    by_status_bytes = collections.Counter()
    for e in assets:
        by_status_bytes[e["status"]] += e["size"]
    lic = collections.defaultdict(lambda: {"files": 0, "bytes": 0, "statuses": collections.Counter()})
    for e in assets:
        L = lic[e.get("licence") or "unknown"]
        L["files"] += 1
        L["bytes"] += e["size"]
        L["statuses"][e["status"]] += 1
    report = {
        "audit": "Steel Accord B2 shipped-asset provenance audit",
        "tool": "tools/qa/asset_audit.py",
        "repo": repo,
        "export_preset": {k: preset.get(k) for k in ("name", "export_filter", "include_filter", "exclude_filter")},
        "manifests_read": manifests_read,
        "fonts": {"font_files_in_project": sorted(e["path"] for e in entries
                                                  if os.path.splitext(e["path"])[1].lower() in (".ttf", ".otf", ".woff", ".woff2", ".fnt")),
                  "note": "no font resources, no FontFile/SystemFont use in scripts or scenes; UI uses the Godot "
                          "built-in default theme font (Open Sans SemiBold, OFL-1.1, compiled into the engine per "
                          "Godot 4 source - not extracted/verified from this binary)"},
        "summary": {
            "files_exported": len(entries),
            "by_category": dict(collections.Counter(e["category"] for e in entries)),
            "assets_by_status": dict(by_status),
            "asset_bytes_by_status": dict(by_status_bytes),
            "assets_without_manifest_entry": sum(1 for e in assets if not e.get("manifest_entry")),
            "assets_with_review_flags": sum(1 for e in assets if e.get("review_flags")),
            "licence_table": {k: {"files": v["files"], "bytes": v["bytes"], "statuses": dict(v["statuses"])}
                              for k, v in sorted(lic.items(), key=lambda kv: -kv[1]["files"])},
        },
        "export_log_crosscheck": xcheck,
        "not_exported": not_exported,
        "files": entries,
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    s = report["summary"]
    print("exported files: %d %s" % (s["files_exported"], s["by_category"]))
    print("assets by status:", s["assets_by_status"])
    print("assets without manifest entry:", s["assets_without_manifest_entry"])
    if xcheck:
        print("export-log cross-check: walked-not-in-log=%d in-log-not-walked=%d" %
              (len(xcheck["walked_but_not_in_log"]), len(xcheck["in_log_but_not_walked"])))
    print("wrote", out)


ART_DIR = None
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Steel Accord - import the U.S. aircraft concept-art packs (AI-generated, supplied by the client).

usage: import_aircraft.py <extracted_pack_dir> [<extracted_pack_dir> ...]

For every aircraft:
  * picks the first *intact* copy of each source file across the packs (later packs listed first win),
  * copies the originals unchanged into art_source/us_aircraft/<id>/ (source of truth, never edited),
  * re-cuts the overhead "game view" from the 4-view contact sheet as one connected silhouette
    (the pack's own 768x512 crops clip long airframes and include stray parts of neighbouring views),
  * makes a portrait icon from the front three-quarter view (falls back to the side profile),
  * writes godot/assets/aircraft/<id>/{<id>_top.png, <id>_icon.png} and content/manifest/aircraft.json,
  * validates sizes, alpha and IDs; prints a report. Original archives are never modified.
"""
import hashlib, json, os, shutil, sys
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art_source", "us_aircraft")
OUT = os.path.join(ROOT, "godot", "assets", "aircraft")
MANIFEST = os.path.join(ROOT, "content", "manifest", "aircraft.json")

# id, pack folder name, reference length (m, nose-to-tail of the overhead silhouette incl. rotors for helicopters),
# intended role in Steel Accord. Lengths are approximate public figures used only to scale the sprite (provisional).
AIRCRAFT = [
    ("f16",  "F-16_Fighting_Falcon",        15.1, "unit:jet_multirole"),
    ("fa18", "F-A-18_Hornet",               17.1, "unit:jet_strike"),
    ("f22",  "F-22_Raptor",                 18.9, "unit:jet_air_superiority"),
    ("a10",  "A-10_Thunderbolt_II_Warthog", 16.3, "unit:jet_ground_attack"),
    ("ah64", "AH-64_Apache",                17.7, "unit:heli_attack"),
    ("uh60", "UH-60_Black_Hawk",            19.8, "unit:heli_transport"),
    ("ch47", "CH-47_Chinook",               30.1, "unit:heli_heavy_transport"),
    ("b52",  "B-52_Stratofortress",         48.5, "support_power:carpet_bombing"),
    ("b1",   "B-1_Lancer",                  44.5, "support_power:supersonic_strike"),
    ("b2",   "B-2_Spirit",                  21.0, "support_power:stealth_precision_strike"),
    ("sr71", "SR-71_Blackbird",             32.7, "support_power:recon_overflight"),
]
# Nose direction of each overhead view as drawn in the client's sheets (checked visually; they are not consistent).
# Sprites are rotated so that every airframe points nose-up (= forward in the engine).
NOSE = {"f16": "up", "f22": "up", "b1": "up", "b52": "up", "fa18": "down", "a10": "down", "b2": "down",
        "sr71": "down", "ch47": "down", "uh60": "down", "ah64": "left"}
VIEWS = ["overhead_game_view", "front_three_quarter", "side_profile", "rear_three_quarter"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def intact(p):
    try:
        im = Image.open(p); im.load()
        return im.mode == "RGBA"
    except Exception:
        return False


def find(packs, rel):
    for pk in packs:
        p = os.path.join(pk, rel)
        if os.path.exists(p) and intact(p):
            return p, pk
    return None, None


def cut_overhead(sheet: Image.Image, quadrant=True) -> Image.Image:
    """Largest connected silhouette (centre in the sheet's top-left quadrant when `quadrant`)."""
    a = np.array(sheet)[:, :, 3]
    h, w = a.shape
    mask = a > 16
    grown = ndimage.binary_dilation(mask, iterations=5)
    lab, n = ndimage.label(grown)
    best, best_area = 0, 0
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        cy, cx = ys.mean(), xs.mean()
        if (not quadrant or (cx < w / 2 and cy < h / 2)) and len(ys) > best_area:
            best, best_area = i, len(ys)
    keep = (lab == best) & (a > 0)
    arr = np.array(sheet).copy()
    arr[~keep] = 0
    ys, xs = np.nonzero(keep)
    pad = 6
    box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(w, xs.max() + pad + 1), min(h, ys.max() + pad + 1))
    out = Image.fromarray(arr).crop(box)
    # square canvas, aircraft centred (nose up = -Y in the image = forward)
    s = max(out.size)
    sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sq.paste(out, ((s - out.size[0]) // 2, (s - out.size[1]) // 2))
    return sq.resize((1024, 1024), Image.LANCZOS) if s > 1024 else sq


def icon_from(view: Image.Image) -> Image.Image:
    im = cut_overhead(view, quadrant=False)
    im = im.crop(im.getbbox())
    im.thumbnail((240, 150), Image.LANCZOS)
    out = Image.new("RGBA", (256, 160), (0, 0, 0, 0))
    out.paste(im, ((256 - im.size[0]) // 2, (160 - im.size[1]) // 2), im)
    return out


def main(packs):
    packs = list(reversed(packs))   # later packs take precedence when intact
    os.makedirs(SRC, exist_ok=True); os.makedirs(OUT, exist_ok=True); os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    entries, problems = [], []
    for aid, folder, length_m, role in AIRCRAFT:
        e = {"id": aid, "source_name": folder.replace("_", " "), "intended_use": role,
             "representation": "sprite (top-down billboard on a horizontal quad) + portrait icon; NOT a 3D model",
             "provenance": "AI-generated concept art supplied by client (ChatGPT image generation, Oct 2026); "
                           "packs US_Aircraft_Game_Assets.zip / US_Aircraft_Game_Assets_Expanded.zip",
             "license_status": "client-supplied; generator terms permit use by client - confirm before release",
             "shipping_status": "DEV ONLY - release review required: depicts real aircraft designs, real names "
                                "(manufacturer trademarks) and U.S. national insignia",
             "reference_length_m": length_m, "source_files": {}, "missing_or_corrupt": [], "game_files": {}}
        sdir = os.path.join(SRC, aid); os.makedirs(sdir, exist_ok=True)
        sheet_rel = f"contact_sheets/{folder}_4-view.png"
        p, pk = find(packs, sheet_rel)
        if p:
            shutil.copy2(p, os.path.join(sdir, os.path.basename(p)))
            e["source_files"]["contact_sheet"] = {"file": f"art_source/us_aircraft/{aid}/{os.path.basename(p)}",
                                                  "from_pack": os.path.basename(pk), "sha256": sha(p)}
        else:
            e["missing_or_corrupt"].append(sheet_rel)
        for v in VIEWS:
            rel = f"individual_views/{folder}/{folder}_{v}.png"
            vp, vpk = find(packs, rel)
            if vp:
                shutil.copy2(vp, os.path.join(sdir, os.path.basename(vp)))
                e["source_files"][v] = {"file": f"art_source/us_aircraft/{aid}/{os.path.basename(vp)}",
                                        "from_pack": os.path.basename(vpk), "sha256": sha(vp)}
            else:
                e["missing_or_corrupt"].append(rel)
        gdir = os.path.join(OUT, aid); os.makedirs(gdir, exist_ok=True)
        if p:
            top = cut_overhead(Image.open(p).convert("RGBA"))
            top = top.rotate({"up": 0, "down": 180, "left": -90, "right": 90}[NOSE[aid]], expand=False)
            e["source_nose_direction"] = NOSE[aid]
            bb = top.getbbox()
            top.save(os.path.join(gdir, f"{aid}_top.png"))
            e["game_files"]["sprite_top"] = f"res://assets/aircraft/{aid}/{aid}_top.png"
            e["sprite_px"] = top.size[0]
            e["silhouette_px"] = [bb[2] - bb[0], bb[3] - bb[1]]
            # metres per pixel so the nose-to-tail extent equals the reference length
            e["sprite_pixel_size_m"] = round(length_m / (bb[3] - bb[1]), 5)
        icon_src = e["source_files"].get("front_three_quarter") or e["source_files"].get("side_profile")
        if icon_src:
            icon_from(Image.open(os.path.join(ROOT, icon_src["file"])).convert("RGBA")).save(os.path.join(gdir, f"{aid}_icon.png"))
            e["game_files"]["icon"] = f"res://assets/aircraft/{aid}/{aid}_icon.png"
            e["icon_from"] = "front_three_quarter" if e["source_files"].get("front_three_quarter") else "side_profile"
        e["conversion_status"] = "sprite+icon generated" if len(e["game_files"]) == 2 else "INCOMPLETE"
        if e["missing_or_corrupt"]:
            problems.append(f"{aid}: missing/corrupt -> {e['missing_or_corrupt']}")
        entries.append(e)
    # validation
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), "duplicate aircraft IDs"
    for e in entries:
        for k, rp in e["game_files"].items():
            fp = os.path.join(ROOT, "godot", rp.replace("res://", ""))
            assert os.path.exists(fp), fp
            im = Image.open(fp)
            assert im.mode == "RGBA", fp
            a = np.array(im)[:, :, 3]
            assert (a == 0).any() and (a > 250).any(), f"{fp}: alpha looks wrong"
    json.dump({"pack": "U.S. aircraft concept art", "imported_by": "tools/import_aircraft.py", "aircraft": entries},
              open(MANIFEST, "w"), indent=2)
    print("imported", len(entries), "aircraft ->", os.path.relpath(MANIFEST, ROOT))
    for e in entries:
        print(f"  {e['id']:5s} {e['conversion_status']:24s} px/m={1/e.get('sprite_pixel_size_m',1):.1f}  icon:{e.get('icon_from','-')}")
    for pr in problems:
        print("  PROBLEM", pr)


if __name__ == "__main__":
    main(sys.argv[1:])

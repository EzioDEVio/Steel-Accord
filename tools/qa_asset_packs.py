#!/usr/bin/env python3
"""Steel Accord - quality check for client-supplied concept-art packs (read-only; never modifies the packs).

usage: qa_asset_packs.py <out.json> <pack_dir> [<pack_dir> ...]

Per PNG: opens fully (detects truncated files), mode/size, transparency coverage, how much of the subject touches
the crop edge (clipped art), number of large disconnected parts (stray fragments of neighbouring views), and a
dark-halo score (semi-transparent near-black fringe). Cross-checks each pack's manifest.csv against the files.
"""
import csv, glob, hashlib, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

VIEWS = ["overhead", "front_three_quarter", "side_profile", "rear_three_quarter", "overhead_game_view",
         "standing_ready", "walking", "running", "crouched_movement", "kneeling", "low_profile"]


def check(path):
    r = {"path": path, "ok": True}
    try:
        im = Image.open(path); im.load()
        r["size"] = list(im.size); r["mode"] = im.mode
        rgba = np.array(im.convert("RGBA"))
        a = rgba[:, :, 3]
        r["clear"] = round(float((a <= 5).mean()), 3)
        edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
        r["edge_touch"] = round(float((edge > 40).mean()), 4)
        lab, n = ndimage.label(ndimage.binary_dilation(a > 40, iterations=3))
        sizes = np.bincount(lab.ravel())[1:] if n else np.array([0])
        r["large_parts"] = int((sizes > 0.002 * a.size).sum())
        semi = (a > 10) & (a < 200)
        lum = rgba[:, :, :3].mean(axis=2)
        r["dark_halo"] = round(float(((lum < 30) & semi).sum() / max(1, (a > 10).sum())), 4)
        r["sha256"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    except Exception as e:
        r["ok"] = False; r["error"] = str(e)[:80]
    return r


def main(out, packs):
    report = {"packs": {}}
    for pk in packs:
        files = sorted(glob.glob(os.path.join(pk, "**", "*.png"), recursive=True))
        rows = [check(f) for f in files]
        rel = {os.path.relpath(r["path"], pk): r for r in rows}
        man_missing, man_listed = [], 0
        for m in glob.glob(os.path.join(pk, "**", "manifest.csv"), recursive=True):
            base = os.path.dirname(m)
            for row in csv.DictReader(open(m)):
                p = row.get("path") or row.get("sprite_path") or row.get("asset_path")
                if not p: continue
                man_listed += 1
                if not os.path.exists(os.path.join(base, p)): man_missing.append(p)
        crops = [r for r in rows if "contact" not in r["path"].lower()]
        report["packs"][os.path.basename(pk.rstrip("/"))] = {
            "png_files": len(rows),
            "contact_sheets": len(rows) - len(crops),
            "crops": len(crops),
            "corrupt": [os.path.relpath(r["path"], pk) for r in rows if not r["ok"]],
            "clipped_crops": [os.path.relpath(r["path"], pk) for r in crops if r["ok"] and r["edge_touch"] > 0.01],
            "multi_part_crops": [os.path.relpath(r["path"], pk) for r in crops if r["ok"] and r["large_parts"] > 1],
            "manifest_rows": man_listed, "manifest_missing_files": man_missing,
            "files": rows,
        }
    json.dump(report, open(out, "w"), indent=1)
    for name, p in report["packs"].items():
        print(f"{name}: {p['png_files']} png ({p['contact_sheets']} sheets, {p['crops']} crops) | corrupt {len(p['corrupt'])} | "
              f"clipped crops {len(p['clipped_crops'])} | multi-part crops {len(p['multi_part_crops'])} | "
              f"manifest rows {p['manifest_rows']}, missing {len(p['manifest_missing_files'])}")
        for c in p["corrupt"]: print("    CORRUPT", c)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

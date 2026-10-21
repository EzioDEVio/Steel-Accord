#!/usr/bin/env python3
"""B1.1 build (rev b): regenerate original assets, write manifest, pack dev BIG, validate, stage a Windows test kit.

usage: python3 tools/build_b1.py --engine /path/to/GeneralsGameCode
Output: build/PZDev_B1.big, build/stage_b1/ (+ build/PZ_B1_1_testkit.zip)
"""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import big

GEN = {
    "content/dev/Art/W3D/": "tools/gen_kestrel.py",
    "content/dev/Art/Textures/": "tools/gen_kestrel.py",
    "content/dev/Art/Terrain/": "tools/gen_testrange_map.py",
    "maps/PZ_TestRange/PZ_TestRange.": "tools/gen_testrange_map.py",
    "maps/PZ_HarborDivide/": "tools/gen_harbor_divide.py",
    "content/dev/Art/Terrain/pzdev_mud": "tools/gen_harbor_divide.py",
}


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def manifest():
    assets = []
    for base in ("content/dev", "maps"):
        for dp, _, fn in sorted(os.walk(os.path.join(ROOT, base))):
            for f in sorted(fn):
                rp = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                gen = next((g for pfx, g in GEN.items() if rp.startswith(pfx)), None)
                assets.append(dict(
                    path=rp, sha256=sha(os.path.join(ROOT, rp)),
                    origin="procedurally generated" if gen else "hand-authored text",
                    creator="Claude (AI technical lead) for Mohammed Aldaraji / Project Zero Hour",
                    tool=f"python3 {gen} (numpy, Pillow)" if gen else "text editor",
                    source=gen or rp,
                    prompt_or_inputs="deterministic script, fixed RNG seeds; no external images, models or samples",
                    license="Project-original; all rights reserved pending project license decision",
                    third_party_inputs="none",
                    ship_status="dev-only (B1 private prototype; references licensed base game data)",
                    history=[f"{datetime.date.today().isoformat()} created for B1.1"],
                ))
    out = dict(project="Project Zero Hour (working title)", milestone="B1.1",
               note="Every file under content/ and maps/ must be listed here; enforced by tools/validate_content.py",
               assets=assets)
    json.dump(out, open(os.path.join(ROOT, "content", "MANIFEST.json"), "w"), indent=1)
    return assets


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--engine", required=True); a = ap.parse_args()
    py = sys.executable
    for g in ("tools/gen_kestrel.py", "tools/gen_testrange_map.py", "tools/gen_harbor_divide.py"):
        subprocess.check_call([py, os.path.join(ROOT, g)])
    assets = manifest()
    bigp = os.path.join(ROOT, "build", "PZDev_B1.big")
    listing = big.pack(os.path.join(ROOT, "content", "dev"), bigp)
    print(f"packed {len(listing)} files -> {os.path.relpath(bigp, ROOT)} ({os.path.getsize(bigp)} bytes)")
    rc = subprocess.call([py, os.path.join(ROOT, "tools", "validate_content.py"), "--engine", a.engine, "--big", bigp])
    if rc:
        sys.exit("validation failed; not staging")

    st = os.path.join(ROOT, "build", "stage_b1")
    shutil.rmtree(st, ignore_errors=True)
    os.makedirs(os.path.join(st, "Maps"))
    shutil.copy(bigp, st)
    for mname in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        shutil.copytree(os.path.join(ROOT, "maps", mname), os.path.join(st, "Maps", mname))
    for f in ("install_b1.ps1", "TEST_B1_1.md"):
        shutil.copy(os.path.join(ROOT, "tests", "b1", f), st)
    sums = []
    for dp, _, fn in sorted(os.walk(st)):
        for f in sorted(fn):
            p = os.path.join(dp, f); sums.append(f"{sha(p)}  {os.path.relpath(p, st)}")
    open(os.path.join(st, "SHA256SUMS.txt"), "w").write("\n".join(sums) + "\n")
    z = os.path.join(ROOT, "build", "PZ_B1_1_testkit.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fn in os.walk(st):
            for f in fn:
                p = os.path.join(dp, f); zf.write(p, os.path.join("PZ_B1_1_testkit", os.path.relpath(p, st)))
    print("staged", os.path.relpath(st, ROOT), "and", os.path.relpath(z, ROOT))


if __name__ == "__main__":
    main()

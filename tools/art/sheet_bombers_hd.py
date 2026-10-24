"""Steel Accord - B3 review sheet of the three HD bombers (bpy 5.x, Cycles CPU), rendered from the exported GLBs.

Run:  python3 -I tools/art/sheet_bombers_hd.py [out.png]
Out:  docs/screens/b3_bombers_hd_sheet.png (1920 x 1116: 2 columns x 3 rows of 960 x 360 + title)
Left column: whole aircraft, bays open (B-1 wings fully swept). Right column: close-up detail.
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import bpy  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".png") else os.path.join(K.SCREENS, "b3_bombers_hd_sheet.png")
RES = (960, 360)

# (id, door angle, wing sweep, [(label, az, el, target, dist, lens)])
SHOTS = [
    ("b52", 95, 0, [("B-52-style HD: 3/4 from below, bay open, pylon racks", 140, -22, (0, -1, 3.0), 66, 45),
                    ("B-52-style HD: cockpit, nose and inboard pods", -48, 8, (-1.5, 18.5, 4.5), 22, 40)]),
    ("b1", 90, 38, [("B-1-style HD: wings swept, three bays open", 145, -24, (0, -2, 2.5), 58, 45),
                    ("B-1-style HD: nose, glazing and vanes", -52, 9, (0, 15.0, 4.2), 16, 40)]),
    ("b2", 100, 0, [("B-2-style HD: underside, both bays open", 160, -28, (0, -1, 1.5), 52, 45),
                    ("B-2-style HD: intakes, glazing, exhaust troughs", -150, 26, (-3.0, -1.0, 2.4), 20, 40)]),
]


def main():
    tmp = tempfile.mkdtemp(prefix="b3_sheet_")
    shots = []
    for aid, door, sweep, views in SHOTS:
        L.reset_scene()
        bpy.ops.import_scene.gltf(filepath=os.path.join(K.OUT3D, f"{aid}_hd", f"{aid}_hd.glb"))
        for o in bpy.data.objects:
            if o.name.startswith("Door"):
                o.rotation_mode = "XYZ"
                o.rotation_euler = (0, math.radians(door if o.name.endswith("L") else -door), 0)
            if o.name in ("WingL", "WingR"):
                o.rotation_mode = "XYZ"
                s = math.radians(sweep)
                o.rotation_euler = (0, 0, s if o.name == "WingL" else -s)
        cam = L.setup_preview_scene(ground=False)
        sc = bpy.context.scene
        sc.cycles.samples = 16
        w = sc.world
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.45, 0.53, 0.63, 1)
        w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
        for i, (lab, az, el, tgt, dist, lens) in enumerate(views):
            L.aim(cam, tgt, az, el, dist, lens=lens)
            cam.data.clip_start = 0.05; cam.data.clip_end = 1000
            p = os.path.join(tmp, f"{aid}_{i}.png")
            L.render(p, RES)
            shots.append((p, lab))
    L.contact_sheet(shots, OUT, cols=2, cell=RES, title="Steel Accord B3 - HD strategic bombers (exported GLBs, Cycles CPU review render; bays open)")
    for p, _ in shots:
        os.remove(p)
    os.rmdir(tmp)
    print("sheet", OUT)


if __name__ == "__main__":
    main()

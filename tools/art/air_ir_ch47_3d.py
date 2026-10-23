"""Steel Accord - Iran wave 1: CH-47C-style tandem-rotor heavy-lift helicopter (Iranian Supply Depot hauler).

Run:  python3 -I tools/art/air_ir_ch47_3d.py [out_dir] [--no-previews] [--quick] [--sheet png]
Out:  godot/assets/units3d/ir_ch47/ir_ch47.glb (+ ir_ch47_albedo.png, ir_ch47_blade.png), docs/screens/ir_ch47_sheet.png

Variant of the approved U.S. CH-47 (tools/art/air_ch47_3d.py, imported READ-ONLY; its file and output are
unchanged): identical geometry, dimensions and node names (Body, RotorFront, RotorRear; origins and spin
axes as the U.S. model). Only the surface differs: painted Iranian desert banded camouflage (sand / olive,
reference iran_pack panel 10), cockpit glazing and cabin windows, green / white / red roundels and an aft
pylon fin flash instead of the projected U.S. concept art; plain dark blades with yellow tips.
Addition: two thin SA_Team panels on the pylon tops (the U.S. model has none) so the owner is readable.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402
import air_ch47_3d as C  # noqa: E402  (read-only: build_ch47 and its constants)

K, L = A.K, A.L
import numpy as np  # noqa: E402

ID = "ir_ch47"


def painter():
    side = lambda P: (np.abs(P[:, 0]) > 0.75) & (P[:, 2] > 2.0)
    dec = []
    # cockpit side glazing (both sides) and the chin / front windscreen
    for sg in (-1, 1):
        dec.append(A.Poly([(7.62, 2.55), (7.45, 3.30), (6.95, 3.62), (6.05, 3.74), (5.75, 3.70), (5.75, 2.70)],
                          A.GLASS, "x", side=sg, slab=lambda P: (P[:, 1] > 5.6) & (np.abs(P[:, 0]) > 0.5)))
        dec.append(A.Poly([(5.70, 2.20), (5.70, 3.40), (5.20, 3.40), (5.20, 2.20)], (0.20, 0.22, 0.20), "x", side=sg,
                          slab=side))                                                   # crew door outline
        dec.append(A.Poly([(5.62, 2.80), (5.62, 3.32), (5.28, 3.32), (5.28, 2.80)], A.GLASS, "x", side=sg, slab=side))
        for y in (3.9, 2.4, 0.9, -0.6, -2.1):
            dec.append(A.Circle((y, 2.85), 0.21, A.GLASS, "x", side=sg, slab=side))
        dec.append(A.Roundel((-3.2, 2.75), 0.48, "x", side=sg, slab=side))
    dec.append(A.Poly([(-1.05, 2.45), (1.05, 2.45), (0.95, 3.30), (-0.95, 3.30)], A.GLASS, "y", side=1,
                      slab=lambda P: P[:, 1] > 7.0, min_n=0.25))
    dec.append(A.Poly([(-0.85, 1.35), (0.85, 1.35), (0.85, 2.05), (-0.85, 2.05)], A.GLASS, "y", side=1,
                      slab=lambda P: P[:, 1] > 6.6, min_n=0.25))                       # chin windows
    dec.append(A.Poly([(-0.04, 2.45), (0.04, 2.45), (0.04, 3.32), (-0.04, 3.32)], A.SAND, "y", side=1,
                      slab=lambda P: P[:, 1] > 7.0, min_n=0.25))                       # centre post
    # aft pylon fin flash (both sides)
    dec += A.fin_flash(-5.75, -6.95, 4.35, 5.05, 0.0, 0.0, lambda P: (np.abs(P[:, 0]) > 0.6) & (np.abs(P[:, 0]) < 1.0) &
                       (P[:, 2] > 4.1))
    zones = [(lambda P, N: (P[:, 2] < 0.83) & (np.abs(P[:, 0]) > 1.15), A.GEAR, None),     # wheels, struts, axles
             (lambda P, N: (np.abs(P[:, 0]) > 1.0) & (P[:, 1] < -7.35) & (P[:, 1] > -7.6) & (np.abs(P[:, 2] - 3.65) < 0.4),
              K.DARK, None)]                                                             # engine exhaust faces
    return dict(scheme="desert2", camo_scale=3.4, aniso=(0.30, 1.0, 0.30), zones=zones, decals=dec,
                panel=dict(dy=1.0, y0=0.3, lon_z=(1.55, 3.55), k=0.84), seed=5, grime=0.16)


def main():
    o = A.parse_args(ID)
    L.reset_scene()
    mat = L.image_material("SA_IR_CH47", None, rough=0.7)
    bmat = L.image_material("SA_IR_CH47_Blade", None, rough=0.85)
    bmat.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.25
    body, rotors = C.build_ch47(mat, bmat)
    Tm = K.Part("Team")
    Tm.box((0, -6.6, 5.70), (1.30, 1.6, 0.05))
    Tm.box((0, 4.35, 5.32), (1.20, 0.7, 0.05))
    objs = {"air": body, "team": Tm.build(K.team_material(), smooth=40)}
    bl = A.blade_png(o["out"], ID, rgb=(0.11, 0.11, 0.10), tip=(0.85, 0.72, 0.12))
    A.finish_ir(ID, o, mat, objs, {}, painter(), ((-2.5, -8.6, -0.1), (2.5, 8.6, 6.4)), (30.0, 18.4, 6.4),
                "Steel Accord Iran wave 1 - CH-47C-style heavy-lift helicopter (variant of the U.S. CH-47) - Cycles CPU preview",
                extra_export=[rotors["RotorFront"], rotors["RotorRear"]], blade=(bmat, bl, f"{ID}_blade"), ao=0.5)


if __name__ == "__main__":
    main()

"""Steel Accord - Iran wave 1: C-130-style four-turboprop tactical airlifter (Iranian variant).

Run:  python3 -I tools/art/air_ir_c130_3d.py [out_dir] [--no-previews] [--quick] [--sheet png]
Out:  godot/assets/units3d/ir_c130/ir_c130.glb (+ ir_c130_albedo.png, ir_c130_prop.png), docs/screens/ir_c130_sheet.png

Variant of the approved U.S. C-130 (tools/art/air_c130_3d.py, imported READ-ONLY; its file and output are
unchanged): identical airframe builder, frames and measurements, so the geometry, dimensions and node names
(Body, Prop0..3 = left outer, left inner, right inner, right outer; hub origins, shaft = local Z in Godot) and
the SA_Team fin cap are the same. Surface: painted Iranian desert camouflage (iran_pack panel 11), black nose
radome, flight-deck glazing, paratroop-door outlines, green / white / red roundels (wings, aft fuselage) and fin
flash; propellers dark with white / red tips. Used for supply drops and paratroopers.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit_ir as A  # noqa: E402
import air_c130_3d as C  # noqa: E402  (read-only: build(), make_props(), S, T, M)

K, L = A.K, A.L
import numpy as np  # noqa: E402

ID = "ir_c130"


def painter():
    S, T = C.S, C.T
    zw = float(S.z(C.M["zw_py"]))
    dih = math.tan(math.radians(2.5))
    side = lambda P: (np.abs(P[:, 0]) > 0.8) & (P[:, 2] > 0.6) & (P[:, 2] < 5.4)
    dec = []
    for sg in (-1, 1):
        dec.append(A.Poly([(13.15, 3.62), (12.55, 4.22), (11.65, 4.66), (10.95, 4.82), (10.95, 4.15), (12.2, 3.62)],
                          A.GLASS, "x", side=sg, slab=lambda P: (P[:, 1] > 10.5) & (np.abs(P[:, 0]) > 0.5)))
        for yp in (12.15, 11.45):
            dec.append(A.Poly([(yp + 0.04, 3.5), (yp - 0.04, 3.5), (yp - 0.04, 5.0), (yp + 0.04, 5.0)], A.SAND, "x",
                              side=sg, slab=lambda P: (P[:, 1] > 10.5) & (np.abs(P[:, 0]) > 0.5)))
        y0, y1, z0, z1, w = -6.0, -7.05, 0.95, 2.95, 0.035                        # paratroop door outline
        for pts in ([(y0, z0), (y1, z0), (y1, z0 + w), (y0, z0 + w)], [(y0, z1 - w), (y1, z1 - w), (y1, z1), (y0, z1)],
                    [(y0, z0), (y0 - w, z0), (y0 - w, z1), (y0, z1)], [(y1 + w, z0), (y1, z0), (y1, z1), (y1 + w, z1)]):
            dec.append(A.Poly(pts, (0.22, 0.20, 0.16), "x", side=sg, slab=side))
        dec.append(A.Roundel((-7.6, 3.85), 0.62, "x", side=sg, slab=side))
        xr = sg * 14.4
        for s2 in (1, -1):
            dec.append(A.Roundel((xr, 0.29), 0.78, "z", side=s2,
                                 slab=lambda P: (np.abs(P[:, 0]) > 11.0) &
                                 (np.abs(P[:, 2] - (zw + (np.abs(P[:, 0]) - 2.5) * dih)) < 0.6)))
    dec.append(A.Poly([(-1.0, 3.72), (1.0, 3.72), (0.9, 4.62), (-0.9, 4.62)], A.GLASS, "y", side=1,
                      slab=lambda P: P[:, 1] > 11.6, min_n=0.25))
    dec += A.fin_flash(-11.05, -12.65, 9.3, 10.5, -0.2, 0.0, lambda P: np.abs(P[:, 0]) < 0.3)
    zones = [(lambda P, N: P[:, 1] > 13.95, A.RADOME_BLACK, ("air",))]
    return dict(scheme="desert", camo_scale=6.0, flat={"gear": A.GEAR}, zones=zones, decals=dec,
                panel=dict(dy=1.5, dx=1.6, lon_z=(1.6, 4.4), keys=("air",), k=0.84), seed=6, grime=0.12)


def main():
    o = A.parse_args(ID)
    L.reset_scene()
    mat = L.image_material("SA_IR_C130", None, rough=0.65)
    pmat = L.image_material("SA_IR_C130_Prop", None, rough=0.6)
    objs, empties, hubs, _ = C.build(mat, C.S, C.T, C.M)
    props, _ = C.make_props(hubs, pmat, o["out"], ID)
    prop_png = A.prop_png_redwhite(o["out"], ID)
    A.finish_ir(ID, o, mat, objs, empties, painter(), ((-20.6, -15.5, -0.1), (20.6, 15.5, 12.8)), (29.8, 40.4, 12.6),
                "Steel Accord Iran wave 1 - C-130-style airlifter (variant of the U.S. C-130) - Cycles CPU preview",
                extra_export=props, blade=(pmat, prop_png, f"{ID}_prop"), cell=0.05)


if __name__ == "__main__":
    main()

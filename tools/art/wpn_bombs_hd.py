"""Steel Accord - B3 generic air-dropped weapons for the HD bomber strikes (bpy 5.x). Original, generic shapes.

Run:  python3 -I tools/art/wpn_bombs_hd.py
Out:  godot/assets/units3d/hd_bombs/gp_bomb.glb      generic low-drag general-purpose bomb, 2000-lb class proportions
                                                      (3.8 m, 0.46 m dia; the game scales it to 0.6 for 500-lb class)
      godot/assets/units3d/hd_bombs/penetrator.glb    generic guided penetrator (4.6 m, 0.40 m dia, tail guidance kit
                                                      with fins, mid-body strakes)
Flat PBR materials (no textures): olive drab body, yellow nose band, steel fuze / lugs, dark grey kit.
Origin at the centre of mass, nose = Blender +Y (Godot -Z).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import bpy  # noqa: E402

OUT = os.path.join(K.OUT3D, "hd_bombs")
PI = math.pi


def mat(name, rgb, rough, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def gp_bomb():
    olive = mat("SA_BombOlive", (0.18, 0.2, 0.12), 0.55)
    yellow = mat("SA_BombBand", (0.75, 0.55, 0.06), 0.5)
    steel = mat("SA_BombSteel", (0.55, 0.55, 0.56), 0.35, 0.9)
    Lb, r = 3.8, 0.23
    y0 = -Lb / 2
    B = K.Part("GPBody")
    prof = [(0, 0.12), (0.03, 0.2), (0.12, 0.55), (0.22, 0.86), (0.32, 1.0), (0.62, 1.0), (0.75, 0.93), (0.86, 0.72),
            (0.95, 0.4), (0.99, 0.16), (1.0, 0.08)]
    K.body_rev(B, (0, y0, 0), (0, y0 + Lb, 0), [(t, r * f) for t, f in prof], seg=28)
    for k in range(4):                                  # conical-fin tail assembly
        a = PI / 4 + k * PI / 2
        d = (math.cos(a), 0, math.sin(a))
        B.beam((d[0] * r * 0.25, y0 + 0.08, d[2] * r * 0.25), (d[0] * r * 1.08, y0 + 0.08, d[2] * r * 1.08), 0.62, 0.014, up=(0, 1, 0))
    K.body_rev(B, (0, y0 + 0.02, 0), (0, y0 + 0.18, 0), [(0, r * 1.05), (1, r * 1.05)], seg=24)   # fin ring
    body = B.build(olive, smooth=40)
    Y = K.Part("GPBand")
    yb = y0 + Lb * 0.86
    K.body_rev(Y, (0, yb, 0), (0, yb + 0.1, 0), [(0, r * 0.74), (1, r * 0.66)], seg=28)
    band = Y.build(yellow, smooth=40)
    S = K.Part("GPSteel")
    K.body_rev(S, (0, y0 + Lb - 0.02, 0), (0, y0 + Lb + 0.12, 0), [(0, 0.05), (0.7, 0.04), (1, 0.01)], seg=12)   # nose fuze
    for yl in (-0.38, 0.38):                            # suspension lugs
        S.box((0, yl, r + 0.03), (0.05, 0.12, 0.08))
    steel_o = S.build(steel, smooth=40)
    return K.join([body, band, steel_o], "Bomb")


def penetrator():
    olive = mat("SA_BombOlive", (0.18, 0.2, 0.12), 0.55)
    yellow = mat("SA_BombBand", (0.75, 0.55, 0.06), 0.5)
    kit = mat("SA_KitGrey", (0.2, 0.21, 0.22), 0.45, 0.2)
    steel = mat("SA_BombSteel", (0.55, 0.55, 0.56), 0.35, 0.9)
    Lb, r = 4.6, 0.2
    y0 = -Lb / 2
    B = K.Part("PenBody")
    prof = [(0.16, 1.0), (0.7, 1.0), (0.85, 0.88), (0.95, 0.55), (1.0, 0.2)]
    K.body_rev(B, (0, y0, 0), (0, y0 + Lb, 0), [(t, r * f) for t, f in prof], seg=28)
    for k in range(4):                                  # mid-body strakes
        a = PI / 4 + k * PI / 2
        d = (math.cos(a), 0, math.sin(a))
        B.beam((d[0] * r, y0 + Lb * 0.36, d[2] * r), (d[0] * r * 1.6, y0 + Lb * 0.52, d[2] * r * 1.6), 0.03, 0.012, up=(0, 1, 0))
        B.beam((d[0] * r, y0 + Lb * 0.36, d[2] * r), (d[0] * r, y0 + Lb * 0.66, d[2] * r), 0.02, 0.02, up=(0, 1, 0))
    body = B.build(olive, smooth=40)
    G = K.Part("PenKit")
    K.body_rev(G, (0, y0, 0), (0, y0 + Lb * 0.17, 0), [(0, r * 0.7), (0.2, r * 0.95), (1, r * 1.02)], seg=28)
    for k in range(4):                                  # cruciform control fins
        a = PI / 4 + k * PI / 2
        d = (math.cos(a), 0, math.sin(a))
        G.beam((d[0] * r * 0.8, y0 + 0.22, d[2] * r * 0.8), (d[0] * r * 2.6, y0 + 0.14, d[2] * r * 2.6), 0.32, 0.018, up=(0, 1, 0))
    kit_o = G.build(kit, smooth=40)
    Y = K.Part("PenBand")
    yb = y0 + Lb * 0.8
    K.body_rev(Y, (0, yb, 0), (0, yb + 0.08, 0), [(0, r * 1.01), (1, r * 1.01)], seg=28)
    band = Y.build(yellow, smooth=40)
    S = K.Part("PenSteel")
    for yl in (-0.5, 0.5):
        S.box((0, yl, r + 0.03), (0.05, 0.12, 0.08))
    steel_o = S.build(steel, smooth=40)
    return K.join([body, kit_o, band, steel_o], "Bomb")


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("gp_bomb", gp_bomb), ("penetrator", penetrator)):
        L.reset_scene()
        o = fn()
        L.export_glb([o], os.path.join(OUT, f"{name}.glb"))
        print(name, "tris", L.tri_count([o]))


if __name__ == "__main__":
    main()

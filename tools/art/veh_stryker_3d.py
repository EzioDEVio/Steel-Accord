"""Steel Accord M2 - Stryker-style 8x8 APC with remote weapon station, 3D (bpy 5.x).
Reuses the wheeled chassis builder of tools/art/veh_hmmwv_3d.py (pipeline tools/art/vehkit.py).

Run:  python3 tools/art/veh_stryker_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Measurements: stryker_side.png (nose left; px 15..755 = 6.95 m; ground py 434), stryker_top.png (py 10..737,
centre px 189, width squeezed sx 0.9). Wheels: WheelFL/FR, WheelML/MR, WheelM2L/M2R, WheelRL/RR; the first two
axles steer (SteerFL/FR, SteerML/MR empties).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
import veh_hmmwv_3d as hm  # noqa: E402
from vehkit import Part, PI  # noqa: E402


def turret_rws(ctx, V):
    """Remote weapon station: Turret = rotating base + sensor housing, Gun = cradle + MG."""
    S, T, mat, o = ctx.S, ctx.T, ctx.mat, ctx.objs
    rx, ry, rz = V["ring"]
    gy, gz = V["trunnion"]
    Tp = Part("Turret")
    Tp.cyl((rx, ry, rz + 0.05), 0.36, 0.1, seg=20)
    Tp.box((rx, ry - 0.05, rz + 0.3), (0.42, 0.62, 0.42))                       # pedestal / drive housing
    Tp.box((rx + 0.33, gy + 0.05, gz + 0.02), (0.18, 0.5, 0.36))                # sight / sensor box (right)
    Tp.box((rx + 0.33, gy + 0.31, gz + 0.06), (0.14, 0.04, 0.18))               # sensor window frame
    Tp.box((rx - 0.28, gy - 0.05, gz - 0.08), (0.22, 0.45, 0.3))                # ammo box (left)
    for s in (-1, 1):                                                           # cradle side plates
        Tp.box((rx + s * 0.16, gy, gz - 0.06), (0.04, 0.36, 0.34))
    tur = Tp.build(mat, bevel=0.0)
    vk.set_origin(tur, (rx, ry, rz))
    o["Turret"] = tur
    G = Part("Gun")
    my = V["muzzle_y"]
    G.box((rx, gy, gz), (0.18, 0.62, 0.17))
    G.cyl((rx, (gy + 0.31 + gy + 0.6) / 2, gz), 0.045, 0.29, (PI / 2, 0, 0), seg=10)
    G.cyl((rx, (gy + 0.6 + my) / 2, gz), 0.028, my - gy - 0.6, (PI / 2, 0, 0), seg=8)
    G.cyl((rx, my - 0.05, gz), 0.04, 0.1, (PI / 2, 0, 0), seg=8)
    gun = G.build(mat, bevel=0.0, smooth=40)
    vk.set_origin(gun, (rx, gy, gz)); vk.parent_to(gun, tur)
    o["Gun"] = gun
    o["Muzzle"] = vk.empty("Muzzle", (rx, my + 0.01, gz), parent=gun)
    tm = Part("TeamTurret")
    tm.box((rx - 0.39, gy - 0.05, gz - 0.02), (0.02, 0.35, 0.1))
    ctx.team.append(("Turret", tm))
    return ["Turret", "Gun"]


def V_stryker():
    S = vk.SideFrame(6.95 / 740.0, 385.0, 434.0)
    T = vk.TopFrame(6.95 / 727.0, 189.0, 373.5, sx=0.9)

    def extra(H, S, T):
        for s in (-1, 1):
            H.box((s * (T.x(347) + 0.05), S.y(390), S.z(300)), (0.1, 4.2, 0.06))          # rub rails
            for k in range(3):
                H.box((s * (T.x(347) + 0.06), S.y(560) - k * 0.5, S.z(235)), (0.12, 0.42, 0.42))  # stowage bins
        H.box((0.0, S.y(530), S.z(183) + 0.15), (1.5, 0.6, 0.3))                         # roof stowage
        H.box((0.0, S.y(40), S.z(300)), (1.9, 0.12, 0.3))                                 # bow plate
    wy = 369
    return dict(
        S=S, T=T, front_wheel=(175, wy), rear_wheel=(604, wy), wheel_r_px=65, arch_pad=5, wheel_scale=1.0,
        wheels=[("FL", (175, wy)), ("ML", (308, wy)), ("M2L", (471, wy)), ("RL", (604, wy))], steer=("F", "M"),
        body_clip=(0, 182, 770, 448), open_px=3, tyre_seg=30, hmmwv_details=False,
        plan=[(60, 10), (320, 10), (345, 60), (347, 700), (330, 737), (60, 737), (43, 700), (43, 60)],
        half_w=T.x(347), wheel_x=1.31, tyre_w=0.42, rim_frac=0.5, nose_px=15, tail_px=755, headlight_py=255,
        taillight_py=250, front_bumper=(14, 40, 310, 330), rear_bumper=(740, 757, 300, 330), mirror=None,
        rocker_py=330,
        ring=(0.35, S.y(400), S.z(183)), trunnion=(S.y(400), S.z(108)), muzzle_y=S.y(262),
        hull_extra=[extra],
        cams={"front34": -40.0, "rear34": 140.0},
        team_strips=[(S.y(600), S.y(730), S.z(205))],
        preview=dict(length=7.2, width=3.1, height=3.3, rts_dist=16, close_dist=12, close_az=-40),
        turret=turret_rws, side_only=[],
        notes=["Stryker: width squeezed to 2.6 m body / 3.0 m over tyres (concept top view 2.9 / 3.4 m)."],
    )


if __name__ == "__main__":
    hm.main("stryker", V_stryker(), "Stryker-style 8x8 APC with RWS")

"""Steel Accord M2 - MRAP (M-ATV-style) 3D (bpy 5.x). Reuses the wheeled chassis + shield-turret builders of
tools/art/veh_hmmwv_3d.py (pipeline tools/art/vehkit.py).

Run:  python3 tools/art/veh_mrap_3d.py [--out DIR] [--no-previews | --quick] [--previews DIR]
Measurements: mrap_side.png (nose left; px 15..760 = 6.3 m; ground py 476), mrap_top.png (py 12..711,
centre px 183). Turret = gunner's shield ring + MG on the roof (yaw), Gun = MG cradle (pitch).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vehkit as vk  # noqa: E402
import veh_hmmwv_3d as hm  # noqa: E402
from vehkit import PI  # noqa: E402


def V_mrap():
    S = vk.SideFrame(6.3 / 745.0, 387.5, 476.0)
    T = vk.TopFrame(6.3 / 699.0, 183.0, 361.5, sx=1.0)
    ring = (0.0, -0.45, S.z(156))

    def extra(H, S, T):
        # rear spare-tyre carrier frame, roof rails, side steps / armour bins
        H.box((0, S.y(712), S.z(250)), (1.4, 0.1, 0.9))
        for s in (-1, 1):
            H.box((s * 0.95, S.y(470), S.z(158) + 0.03), (0.06, 3.0, 0.06))
            H.box((s * (T.x(312) + 0.08), S.y(380), S.z(400)), (0.14, 1.6, 0.3))
            H.box((s * (T.x(312) + 0.05), S.y(380), S.z(355)), (0.1, 1.8, 0.05))
        H.cyl((0, S.y(730), S.z(250)), 0.5, 0.3, (PI / 2, 0, 0), seg=24)    # spare tyre
    return dict(
        S=S, T=T, front_wheel=(152, 396), rear_wheel=(608, 396), wheel_r_px=80, arch_pad=6,
        body_clip=(0, 158, 778, 488), open_px=3,
        plan=[(75, 14), (290, 14), (312, 60), (312, 700), (300, 711), (66, 711), (54, 700), (54, 60)],
        half_w=T.x(312), wheel_x=1.22, tyre_w=0.42, rim_frac=0.5, nose_px=15, tail_px=762, headlight_py=300,
        taillight_py=290, front_bumper=(12, 55, 330, 372), rear_bumper=(728, 765, 360, 395), mirror=(300, 235),
        rocker_py=392,
        ring=ring, trunnion=(S.y(430), S.z(112)), muzzle_y=S.y(318),
        shield_z=(S.z(58), S.z(70), S.z(84)), shield_r=1.05,
        hull_extra=[extra],
        cams={"front34": 40.0, "rear34": -140.0},
        team_strips=[(S.y(560), S.y(690), S.z(300))],
        preview=dict(length=6.6, width=2.9, height=3.5, rts_dist=15, close_dist=11, close_az=-40),
        turret=hm.turret_50cal,
        notes=["MRAP: roof weapon = shielded gunner ring with MG (concept shows a manned shield turret rather than "
               "an unmanned RWS); Turret yaws, Gun pitches."],
    )


if __name__ == "__main__":
    hm.main("mrap", V_mrap(), "MRAP (M-ATV style)")

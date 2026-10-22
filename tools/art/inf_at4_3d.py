"""Steel Accord - M1 infantry: AT4-style anti-armour gunner, rigged + animated (variant of the rifleman kit).

Run:  python3 tools/art/inf_at4_3d.py godot/assets/units3d/at4 [--previews docs/screens]
Out:  at4.glb (skinned body + Armature + `Launcher` on RightHand with `Muzzle` (front) and `Backblast` (rear) empties),
      at4_camo.png, at4_report.json; previews m1_inf_at4_{front,side,rts,anims}.png

Design: generic disposable shoulder-fired launcher tube (original; olive tube, black shock-absorber ends, flared
venturi, fold-up rear sight / fold-down front sight on the left, pistol grip + firing block, foregrip, shoulder pad,
one ammunition-type band). The gunner's own carbine is slung diagonally across a slim patrol pack. Same 17-bone
skeleton, rest pose, uniform and gear base as the rifleman. Camo palette: inf_palette.py --albedo at4
(k-means of the at4 concept, calibrated against the approved rifleman albedo).

Empties (children of `Launcher`): `Muzzle` at the front end, +Y along the bore (projectile direction);
`Backblast` at the rear end, rotated 180 deg about Z so its +Y points out of the venturi (exhaust direction).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inf_kit as K
from mathutils import Matrix, Vector as V, Quaternion

D = math.radians
PI = math.pi
OUT, PREV, ONLY_ANIMS = K.parse_args()

# python3 -I tools/art/inf_palette.py at4 --albedo
PALETTE = {"base": (151, 135, 102), "khaki": (117, 104, 77), "olive": (89, 91, 59), "brown": (93, 72, 56),
           "dark": (38, 31, 26), "cream": (191, 178, 146)}

# ------------------------------------------------------------------ launcher geometry (local: origin = shoulder
# contact point on the tube axis, +Y forward along the bore, +Z up; sights on the LEFT (-X) side)
TUBE_R = 0.042
REAR_Y, FRONT_Y = -0.43, 0.595
GRIP = V((0, 0.20, -0.09))             # pistol grip = where the right hand's rest grip lands (rifle grip shifted)


def build_launcher(R, w):
    O = "SA_Olive"
    cy = lambda y0, y1: ((y0 + y1) / 2, y1 - y0)
    c, dpt = cy(-0.385, 0.545)
    R.cyl(O, w, (0, c, 0), TUBE_R, dpt, (-PI / 2, 0, 0), seg=12)                          # main tube
    c, dpt = cy(REAR_Y, -0.38)
    R.cyl("SA_Rubber", w, (0, c, 0), 0.058, dpt, (-PI / 2, 0, 0), seg=12, r2=0.047)       # rear shock absorber / venturi
    R.cyl("SA_Metal", w, (0, REAR_Y - 0.002, 0), 0.044, 0.004, (-PI / 2, 0, 0), seg=10)   # venturi throat (dark)
    c, dpt = cy(0.54, FRONT_Y)
    R.cyl("SA_Rubber", w, (0, c, 0), 0.047, dpt, (-PI / 2, 0, 0), seg=12, r2=0.057)       # front shock absorber
    R.cyl("SA_Metal", w, (0, FRONT_Y + 0.002, 0), 0.043, 0.004, (-PI / 2, 0, 0), seg=10)  # bore (dark)
    R.cyl("SA_Marking", w, (0, 0.42, 0), TUBE_R + 0.0015, 0.026, (-PI / 2, 0, 0), seg=12)  # ammunition-type band
    for y in (0.03, 0.45):                                                                 # sight mounting bands
        R.cyl("SA_Olive", w, (0, y, 0), TUBE_R + 0.004, 0.018, (-PI / 2, 0, 0), seg=12)
    R.box("SA_Rubber", w, (0, 0.0, -0.05), (0.05, 0.13, 0.02))                             # shoulder pad
    R.box("SA_Rubber", w, GRIP, (0.032, 0.035, 0.09), (0.35, 0, 0))                       # pistol grip
    R.box("SA_Rubber", w, (0, 0.235, -0.047), (0.04, 0.11, 0.02))                          # grip housing
    R.box("SA_Rubber", w, (0.0, 0.22, 0.05), (0.034, 0.12, 0.02))                          # firing block on top
    R.box("SA_Metal", w, (0.022, 0.17, 0.062), (0.012, 0.045, 0.012), (0.3, 0, 0))         # cocking lever
    R.box("SA_Rubber", w, (0, 0.47, -0.075), (0.03, 0.035, 0.06), (0.2, 0, 0))             # foregrip
    R.box("SA_Olive", w, (-0.044, 0.035, 0.035), (0.014, 0.03, 0.04))                      # rear sight (folded up)
    R.box("SA_Metal", w, (-0.046, 0.035, 0.06), (0.018, 0.012, 0.014))                     # rear sight aperture
    R.box("SA_Olive", w, (-0.044, 0.45, 0.035), (0.012, 0.02, 0.035))                      # front sight post
    R.box("SA_Olive", w, (-0.036, 0.24, 0.032), (0.008, 0.40, 0.012))                      # sight cover rail
    for y in (-0.30, 0.50):                                                                # sling swivels
        R.box("SA_Metal", w, (0.0, y, -0.05), (0.008, 0.02, 0.016))


# rest placement: the launcher's pistol grip sits exactly where the rifle's grip is, so the shared bind pose holds it
W_REST = K.RIFLE_REST @ Matrix.Translation(V((0, 0.255, -0.085)) - GRIP)
weapon = K.Weapon("Launcher", build_launcher, W_REST, W_REST.translation.copy(), V((0, FRONT_Y, 0)),
                  empties={"Backblast": (V((0, REAR_Y, 0)), (0, 0, PI))},
                  aim_pocket=(0.19, 0.035, 1.555), kick=0.055, lift=0.012, rise=5.0,
                  lay=dict(gx=0.20, gy=0.12, grip=0.20, side=0.09, h=0.06), grip_local=GRIP)


def body_extra(B):
    # carbine slung diagonally across the patrol pack: butt high behind the right shoulder, muzzle down-left
    yd = V((-0.6, 0, -0.8)).normalized()
    M = K.axes_matrix(yd, V((-0.8, 0, 0.6)), V((0.21, -0.315, 1.47)))
    K.slung_carbine(B, M, "Chest")
    # sling running from the butt over the pack lid to the muzzle end (two straps)
    B.tube("SA_Rubber", "Chest", [V((0.21, -0.29, 1.47)), V((0.05, -0.27, 1.45)), V((-0.12, -0.25, 1.30))],
           [(0.012, 0.004)] * 3, seg=4)
    # spare round in a carry bag? no - the AT4 is single-shot; a small flare/smoke pouch on the left hip instead
    B.box("SA_CamoGear", "Hips", (-0.19, 0.04, 0.985), (0.045, 0.06, 0.09), (0, 0, 0.3))


# ------------------------------------------------------------------ poses
def carry(P, d, zhint):
    """Chest-space carry frame: launcher grip at P, bore along d, sight side up toward zhint."""
    Mw = K.axes_matrix(d, zhint, (0, 0, 0))
    return V(P), Mw.to_quaternion()


CARRY = carry((0.255, 0.11, 0.93), (-0.06, 0.86, -0.50), (0.85, 0.0, 0.55))


def hand_q(fingers, back):
    """Rotation (about the wrist) taking the rest left-hand frame to fingers/back-of-hand directions."""
    Rd = K.axes_matrix(fingers, back, (0, 0, 0)).to_3x3()
    return (Rd @ K.REST["LeftHand"].to_3x3().inverted()).to_quaternion()


def pose_extra(p):
    p["w_loc"], p["w_q"] = CARRY[0].copy(), CARRY[1].copy()
    p["lslide"], p["lroll"], p["ldrop"] = 0.0, 0.0, 0.0
    p["lgrip"] = 0.0                                  # one-handed side carry: left arm free
    p["lfree"] = V((-0.235, 0.05, 0.89)); p["lfree_q"] = hand_q((0.05, 0.25, -1), (-1, 0, 0.1))
    p["elbow_pole"] = {1: V((0.3, -0.4, -0.1)), -1: V((-0.3, -0.3, -0.2))}


def aim_extra(p, kneel):
    p["lgrip"] = 1.0
    p["lslide"], p["lroll"], p["ldrop"] = 0.03, 0.0, 0.02
    p["head"] = V((D(-6), D(12), D(14))) if not kneel else V((D(-4), D(12), D(14)))
    p["neck"] = V((D(-4), D(4), D(9)))
    p["elbow_pole"] = {1: V((0.5, -0.1, -0.35)), -1: V((-0.2, 0.1, -0.5))}


def die_hook(keys):
    k0, k1, k2, k3, k4, k5 = keys
    k1["rifle_rot"] = V((D(-10), 0, 0))           # tube front dips as the hit lands
    k2["rifle_rot"] = V((D(-5), D(10), D(-10)))
    k3["rifle_rot"] = V((D(10), D(15), D(-15)))


K.POSE_EXTRA = pose_extra
K.AIM_EXTRA = aim_extra
K.DIE_HOOK = die_hook


def act_idle(t):
    p = K.base_pose()
    b = math.sin(2 * PI * t)
    p["chest"] = V((D(1.2) * b, 0, 0)); p["spine"] = V((D(0.4) * b, 0, 0))
    p["head"] = V((D(-1.0) * b, 0, D(4) * math.sin(2 * PI * t + 1.0)))
    p["hips_pos"] = p["hips_pos"] + V((0.008 * math.sin(2 * PI * t + 0.5), 0, 0.003 * b))
    p["rifle_rot"] = V((D(1.2) * math.sin(2 * PI * t + 0.6), 0, 0))
    return p


def act_walk(t):
    p = K.base_pose()
    K.walk_legs(p, t)
    p["spine"] += V((D(-3), 0, 0)); p["head"] += V((D(3), 0, 0))
    p["rifle_rot"] = V((D(2.0) * math.sin(4 * PI * t), 0, D(1.5) * math.sin(2 * PI * t)))
    p["rifle_off"] = V((0, 0, 0.006 * math.sin(4 * PI * t)))
    c = math.cos(2 * PI * t)                          # left arm swings with the right leg
    p["lfree"] = V((-0.235, 0.05 + 0.13 * c, 0.90 + 0.03 * c * c))
    p["lfree_q"] = hand_q((0.0, 0.25 + 0.35 * c, -1), (-1, 0, 0.1))
    return p


def act_run(t):
    p = K.base_pose()
    K.run_legs(p, t)
    K.run_torso(p)
    # tube pulled in tighter and flatter while running, swinging with the stride
    p["rifle_rot"] = V((D(20) + D(4) * math.sin(4 * PI * t + 0.8), D(-3), D(-4) + D(3) * math.sin(2 * PI * t)))
    p["rifle_off"] = V((0.0, 0.02, 0.05))
    c = math.cos(2 * PI * t)                          # left arm pumping, elbow ~90 deg
    p["lfree"] = V((-0.22, 0.10 + 0.17 * c, 1.08 + 0.07 * c))
    p["lfree_q"] = hand_q((0.25, 1.0 - 0.2 * c, 0.4 + 0.5 * c), (-1, 0.1, 0.4))
    p["elbow_pole"] = {1: V((0.3, -0.4, -0.1)), -1: V((-0.2, -1.0, -0.2))}
    return p


def act_aim(t):
    p = K.aim_pose(K.base_pose())
    b = math.sin(2 * PI * t)
    p["chest"] += V((D(0.8) * b, 0, 0))
    p["aim_pitch"] = D(0.4) * math.sin(2 * PI * t + 0.4)
    p["aim_yaw"] = D(0.3) * math.sin(4 * PI * t)
    return p


def launch_curve(t):
    """0.6 s launch: hard kick in 0.04 s, short hold while the backblast clears, smooth recovery to the aim pose."""
    if t < 0.07:
        return math.sin(0.5 * PI * t / 0.07)
    if t < 0.2:
        return 1.0 - 0.25 * K.smoothstep((t - 0.07) / 0.13)
    u = (t - 0.2) / 0.8
    return 0.75 * (1 - K.smoothstep(u))


def lag_curve(t):
    return launch_curve(max(0.0, t - 0.05)) if t > 0.05 else 0.0


def launch(p, t, kneel=False):
    r, r2 = launch_curve(t), lag_curve(t)
    p["recoil"] = r
    p["chest"] += V((D(3.5) * r2, D(-1.0) * r2, D(1.0) * r2))
    p["spine"] += V((D(1.5) * r2, 0, 0))
    p["head"] += V((D(2.5) * r, 0, 0))
    if not kneel:
        p["hips_pos"] = p["hips_pos"] + V((0, -0.015 * r2, -0.008 * r2))
    return p


def act_fire(t):
    return launch(K.aim_pose(K.base_pose()), t)


def act_crouch_fire(t):
    return launch(K.kneel_pose(K.base_pose()), t, kneel=True)


def actions():
    return [("idle", act_idle, 3.0, True), ("walk", act_walk, K.WALK["Tc"], True), ("run", act_run, K.RUN["Tc"], True),
            ("aim", act_aim, 2.0, True), ("fire", act_fire, 0.6, True), ("crouch_fire", act_crouch_fire, 0.6, True),
            ("die", K.act_die, 1.5, False)]


role = K.Role("at4", body_name="AT4_Body", palette=PALETTE, camo_seed=1978, weapon=weapon,
              extra_mats={"SA_Olive": ((0.13, 0.14, 0.075), 0.65, 0.0), "SA_Marking": ((0.62, 0.50, 0.12), 0.6, 0.0)},
              body_opts=dict(pack="small"), body_extra=body_extra, actions=actions,
              report_extra={"notes": "fire/crouch_fire = one 0.6 s launch cycle that starts and ends in the aim pose "
                                     "(seamless, so it can loop or play once per shot)."})
K.build(role, OUT, PREV, ONLY_ANIMS)

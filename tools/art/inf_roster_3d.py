"""Steel Accord - M1 infantry roster: medic, saw_gunner, m240_gunner, sniper, eod_engineer, ranger, special_forces,
pilot. Each is a variant of the shared rifleman kit (inf_kit.py): same 17-bone skeleton and rest pose, same base
action names, hand item on RightHand with a `Muzzle` empty. (AT4 and paratrooper have their own scripts.)

Run:  python3 tools/art/inf_roster_3d.py <role> godot/assets/units3d/<role> [--previews docs/screens]

Palettes: python3 -I tools/art/inf_palette.py <role> --albedo (k-means of the role concept, calibrated against the
approved rifleman albedo); the values are baked in below so the build never reads the concept images.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inf_kit as K
import inf_weapons as Wp
import numpy as np
from mathutils import Matrix, Vector as V, Quaternion

ROLE = sys.argv.pop(1)               # after the kit import (its PYTHONHASHSEED re-exec keeps the full argv)
D = math.radians
PI = math.pi
OUT, PREV, ONLY_ANIMS = K.parse_args()

PAL = {
    "medic": {"dark": (38, 30, 23), "brown": (94, 72, 55), "olive": (90, 91, 60), "khaki": (119, 105, 80),
              "base": (154, 137, 105), "cream": (198, 183, 148)},
    "saw_gunner": {"dark": (37, 30, 23), "brown": (90, 67, 49), "olive": (86, 84, 51), "khaki": (110, 94, 67),
                   "base": (144, 124, 89), "cream": (189, 169, 129)},
    "m240_gunner": {"dark": (32, 27, 22), "brown": (86, 67, 47), "olive": (83, 85, 53), "khaki": (111, 99, 72),
                    "base": (148, 132, 97), "cream": (197, 181, 140)},
    "sniper": {"dark": (27, 24, 16), "brown": (75, 61, 40), "olive": (76, 81, 46), "khaki": (104, 97, 64),
               "base": (142, 132, 91), "cream": (194, 182, 142)},
    "eod_engineer": {"dark": (15, 14, 14), "brown": (51, 46, 41), "olive": (52, 61, 48), "khaki": (78, 78, 62),
                     "base": (111, 108, 81), "cream": (151, 149, 120)},
    "ranger": {"dark": (40, 33, 23), "brown": (98, 74, 53), "olive": (93, 93, 59), "khaki": (124, 107, 80),
               "base": (162, 142, 109), "cream": (211, 194, 159)},
    "special_forces": {"dark": (36, 31, 23), "brown": (94, 75, 56), "olive": (93, 93, 61), "khaki": (126, 108, 79),
                       "base": (168, 144, 106), "cream": (215, 193, 151)},
    "pilot": {"dark": (31, 31, 28), "brown": (80, 72, 61), "olive": (75, 87, 63), "khaki": (96, 97, 78),
              "base": (121, 118, 96), "cream": (151, 151, 135)},
}


def flatten(p, toward="khaki", k=0.85):
    """Plain fabric (flight suit): pull every camo layer toward one sampled colour, keeping a faint mottling."""
    c = p[toward]
    return {n: tuple(int(round(v[i] + (c[i] - v[i]) * k)) for i in range(3)) for n, v in p.items()}


# =============================================================================== shared pose helpers
def carry(P, d, zhint):
    return V(P), K.axes_matrix(d, zhint, (0, 0, 0)).to_quaternion()


def left_free(p, pos, fingers=(0.05, 0.25, -1), back=(-1, 0, 0.1)):
    p["lgrip"] = 0.0; p["lfree"] = V(pos); p["lfree_q"] = K.hand_q(fingers, back)


def left_swing(p, t):
    c = math.cos(2 * PI * t)                          # swings with the right leg
    left_free(p, (-0.235, 0.05 + 0.13 * c, 0.90 + 0.03 * c * c), (0.0, 0.25 + 0.35 * c, -1))


def left_pump(p, t):
    c = math.cos(2 * PI * t)
    left_free(p, (-0.22, 0.10 + 0.17 * c, 1.08 + 0.07 * c), (0.25, 1.0 - 0.2 * c, 0.4 + 0.5 * c), (-1, 0.1, 0.4))
    p["elbow_pole"][-1] = V((-0.2, -1.0, -0.2))


def burst(n):
    def f(t):
        return K.recoil_curve((t * n) % 1.0)
    return f


def fire_with(curve, kneel=False, chest=1.8):
    def act(t):
        p = K.kneel_pose(K.base_pose()) if kneel else K.aim_pose(K.base_pose())
        r = curve(t)
        p["recoil"] = r
        p["chest"] += V((D(chest) * r, 0, D(0.6) * r)); p["head"] += V((D(1.2) * r, 0, 0))
        if not kneel:
            p["hips_pos"] = p["hips_pos"] + V((0, -0.004 * r, 0))
        return p
    return act


def slow_curve(t):                    # single heavy shot: kick then a long settle (0.8 s clip)
    if t < 0.06:
        return math.sin(0.5 * PI * t / 0.06)
    u = (t - 0.06) / 0.94
    return (1 - K.smoothstep(u)) * (1 - u) ** 0.8


def std_actions(fire_fn=None, fire_len=0.3, crouch_fn=None, extra=()):
    return [("idle", K.act_idle, 3.0, True), ("walk", K.act_walk, K.WALK["Tc"], True),
            ("run", K.act_run, K.RUN["Tc"], True), ("aim", K.act_aim, 2.0, True),
            ("fire", fire_fn or K.act_fire, fire_len, True),
            ("crouch_fire", crouch_fn or K.act_crouch_fire, fire_len, True), ("die", K.act_die, 1.5, False)] + \
        list(extra)


def kneel_relaxed(p):
    """Kneeling (right knee down) without the aim: upright torso, weapon not shouldered."""
    a = K.AIM_EXTRA; K.AIM_EXTRA = None
    p = K.kneel_pose(p)
    K.AIM_EXTRA = a
    p["aim"] = 0.0
    p["hips_rot"] = V((D(4), 0, D(-10)))
    p["spine"] = V((D(-14), 0, 0)); p["chest"] = V((D(-8), 0, 0)); p["neck"] = V((D(-8), 0, 0))
    p["head"] = V((D(-14), 0, 0))
    p["elbow_pole"] = {1: V((0.3, -0.2, -0.3)), -1: V((-0.3, 0.05, -0.4))}
    return p


# =============================================================================== roles
def role_medic():
    def extra(B):
        # large aid bag on the back with a neutral team panel (NO medical emblem - client supplies one pre-release)
        B.box("SA_Camo", "Chest", (0, -0.245, 1.25), (0.32, 0.19, 0.40), (-0.06, 0, 0))
        B.box("SA_Camo", "Chest", (0, -0.25, 1.46), (0.30, 0.17, 0.05), (-0.12, 0, 0))
        B.box("SA_Team", "Chest", (0, -0.343, 1.25), (0.14, 0.006, 0.14), (-0.06, 0, 0))
        for s in (-1, 1):
            B.box("SA_Rubber", "Chest", (s * 0.15, -0.20, 1.25), (0.012, 0.15, 0.36), (-0.06, 0, 0))
        B.box("SA_CamoGear", "Hips", (-0.20, 0.03, 0.97), (0.06, 0.13, 0.13), (0, 0, 0.25))   # hip aid pouch
        B.box("SA_Team", "Hips", (-0.232, 0.03, 0.97), (0.004, 0.06, 0.06), (0, 0, 0.25))
        sh, el = K.SH[1], K.ELB[1]                                                              # wide armband (R)
        d1 = (el - sh).normalized()
        B.tube("SA_Team", "RightUpperArm", [sh + d1 * 0.05, sh + d1 * 0.17], [(0.066, 0.068)] * 2, seg=8, caps=False)

    def heal_pose(t):
        p = kneel_relaxed(K.base_pose())
        b = math.sin(4 * PI * t)                      # two compressions / dressing presses per loop
        p["spine"] = V((D(-26), 0, D(-4))); p["chest"] = V((D(-14) + D(3) * b, 0, 0))
        p["neck"] = V((D(-10), 0, 0)); p["head"] = V((D(-18), 0, D(6) * math.sin(2 * PI * t)))
        # carbine held in the right hand, muzzle down along the right thigh
        p["w_loc"], p["w_q"] = carry((0.24, 0.20, 1.00), (0.25, 0.45, -0.86), (0.9, 0.0, 0.3))
        left_free(p, (-0.06, 0.38, 1.07 - 0.03 * max(0.0, b)), (0.3, 0.9, -0.5), (0.0, 0.3, 1.0))
        p["elbow_pole"] = {1: V((0.4, -0.3, 0.0)), -1: V((-0.5, 0.0, -0.3))}
        return p

    K.GROUND_SOLVE = {"die", "heal"}
    return K.Role("medic", body_name="Medic_Body", palette=PAL["medic"], camo_seed=1979,
                  weapon=Wp.gun("Rifle", K.build_carbine, (0, 0.905, 0.008)),
                  body_opts=dict(pack=None), body_extra=extra,
                  actions=lambda: std_actions(extra=[("heal", heal_pose, 2.0, True)]),
                  report_extra={"notes": "Armband / bag panels are SA_Team neutral patches. NO medical emblem is "
                                         "modelled: the client must add an approved emblem before release. heal = "
                                         "kneeling treatment loop; the carbine stays in the right hand (muzzle down)."})


def role_saw():
    return K.Role("saw_gunner", body_name="SAW_Body", palette=PAL["saw_gunner"], camo_seed=1980,
                  weapon=Wp.gun("LMG", Wp.build_saw, (0, 0.97, 0.0), kick=0.028, lift=0.003, rise=2.5,
                                lay=dict(gx=0.24, gy=0.10, grip=0.255, side=0.085, h=0.06)),
                  extra_mats={"SA_Olive": ((0.16, 0.17, 0.10), 0.8, 0.0)},
                  actions=lambda: std_actions(fire_with(burst(3)), 0.3, fire_with(burst(3), kneel=True)),
                  report_extra={"notes": "fire/crouch_fire = 3-round burst cycle in 0.3 s (loop)."})


def role_m240():
    def extra(B):          # spare-barrel bag strapped diagonally on the assault pack
        M = K.axes_matrix(V((-0.5, 0, -0.86)), V((-0.86, 0, 0.5)), V((0.17, -0.335, 1.50)))
        B.xf = M
        B.cyl("SA_Olive", "Chest", (0, 0.32, 0), 0.04, 0.64, Wp.AXIS, seg=8)
        B.xf = None
    return K.Role("m240_gunner", body_name="M240_Body", palette=PAL["m240_gunner"], camo_seed=1981,
                  weapon=Wp.gun("MMG", Wp.build_m240, (0, 1.17, 0.0), kick=0.04, lift=0.004, rise=3.5,
                                lay=dict(gx=0.24, gy=0.10, grip=0.255, side=0.085, h=0.10)),
                  extra_mats={"SA_Olive": ((0.16, 0.17, 0.10), 0.8, 0.0)}, body_extra=extra,
                  actions=lambda: std_actions(fire_with(burst(3), chest=2.6), 0.35, fire_with(burst(3), kneel=True, chest=2.6)),
                  report_extra={"notes": "fire/crouch_fire = 3-round burst cycle in 0.35 s (loop); heavier kick."})


def role_sniper():
    def extra(B):
        # ghillie: ~380 strand cards rooted on uniform / gear / helmet faces, hanging outward + down
        bm = B.bm
        import bmesh
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ok = {K.MAT_ORDER.index(m) for m in ("SA_Camo", "SA_CamoGear")}
        faces = [f for f in bm.faces if f.material_index in ok]
        area = np.array([f.calc_area() for f in faces]); area /= area.sum()
        rng = np.random.default_rng(31)
        pick = rng.choice(len(faces), 380, p=area)
        dl = B.dl
        data = []
        for i in pick:
            f = faces[int(i)]
            c = f.calc_center_median(); n = f.normal.copy()
            v0 = min(f.verts, key=lambda v: (v.co - c).length)
            wts = {B.groups[g]: x for g, x in v0[dl].items()}
            data.append((c, n, wts))
        for k, (c, n, wts) in enumerate(data):
            j = V(rng.normal(0, 1, 3)) * 0.25
            d = (n * 0.55 + V((0, 0, -0.85)) + j).normalized()
            t = n.cross(d)
            if t.length < 1e-4:
                t = V((1, 0, 0))
            t.normalize()
            L = 0.07 + 0.08 * rng.random(); w = 0.03 + 0.015 * rng.random()
            r = c - n * 0.004
            m = ("SA_Ghillie", "SA_CamoGear", "SA_Ghillie2")[k % 3]
            B.quad(m, wts, [r - t * w / 2, r + t * w / 2, r + d * L + t * w * 0.25, r + d * L - t * w * 0.25])
    pal = PAL["sniper"]
    g1 = tuple(x / 255 for x in pal["olive"]); g2 = tuple(x / 255 for x in pal["khaki"])
    return K.Role("sniper", body_name="Sniper_Body", palette=pal, camo_seed=1982,
                  weapon=Wp.gun("SniperRifle", Wp.build_sniper, (0, 1.225, 0.0), kick=0.06, lift=0.006, rise=6.0),
                  extra_mats={"SA_Ghillie": (tuple(c ** 2.2 for c in g1), 0.95, 0.0),
                              "SA_Ghillie2": (tuple(c ** 2.2 for c in g2), 0.95, 0.0)},
                  body_opts=dict(pack="small", radio=False, nvg=False, hydration=False),
                  body_extra=extra,
                  actions=lambda: std_actions(fire_with(slow_curve, chest=2.5), 0.8, fire_with(slow_curve, kneel=True, chest=2.5)),
                  report_extra={"notes": "fire/crouch_fire = one heavy shot, 0.8 s (kick + settle); crouch_fire is "
                                         "kneeling. Ghillie strands are single-sided quads: keep the materials "
                                         "double-sided (cull disabled) in Godot."})


def role_ranger():
    def extra(B):
        HM = K.HM_HELMET
        B.box("SA_Rubber", "Head", HM + V((0, -0.08, 0.115)), (0.03, 0.03, 0.025))                 # strobe
        for k in (-1, 1):                                                                          # chest rig mags
            B.box("SA_CamoGear", "Chest", (k * 0.12, 0.215, 1.08), (0.07, 0.05, 0.10))
        B.cyl("SA_Rubber", "Chest", (-0.17, -0.10, 1.52), 0.006, 0.32, seg=4)                      # 2nd antenna
    return K.Role("ranger", body_name="Ranger_Body", palette=PAL["ranger"], camo_seed=1983,
                  weapon=Wp.gun("Rifle", Wp.build_carbine_ranger, (0, 0.905, 0.008)),
                  body_opts=dict(pack="small", helmet_mat="SA_Canvas"), body_extra=extra,
                  actions=lambda: std_actions(),
                  report_extra={"notes": "Rifleman actions; bare coyote helmet, slim pack, chest-rig mags, "
                                         "carbine with illuminator + magnifier."})


def role_sf():
    def extra(B):
        HM = K.HM_HELMET
        B.box("SA_Rubber", "Head", HM + V((0.10, 0.10, -0.05)), (0.01, 0.07, 0.01), (0, 0, 0.6))  # boom mic
        B.cyl("SA_Rubber", "Chest", (0.19, -0.08, 1.52), 0.006, 0.36, seg=4)                       # 2nd antenna
        B.box("SA_CamoGear", "Chest", (0.0, -0.17, 1.22), (0.22, 0.07, 0.24))                      # back panel
        B.box("SA_Team", "Chest", (0.0, -0.206, 1.30), (0.10, 0.004, 0.05))
    return K.Role("special_forces", body_name="SF_Body", palette=PAL["special_forces"], camo_seed=1984,
                  weapon=Wp.gun("Rifle", Wp.build_carbine_sf, (0, 0.75, 0.008)),
                  extra_mats={"SA_Green": ((0.17, 0.19, 0.13), 0.9, 0.0)},
                  body_opts=dict(pack=None, hydration=False, remap={"SA_CamoGear": "SA_Green"}),
                  body_extra=extra, actions=lambda: std_actions(),
                  report_extra={"notes": "Rifleman actions; solid ranger-green carrier/pouches (SA_Green), "
                                         "no pack, short suppressed carbine."})


# ------------------------------------------------------------------ pistol (pilot)
P_CARRY = carry((0.235, 0.12, 0.92), (0.0, 0.42, -0.91), (0.0, 0.91, 0.42))


def role_pilot():
    def extra(B):
        # survival vest over the flight suit
        B.loftz("SA_Vest", {"Chest": 0.85, "Spine": 0.15},
                [(1.10, 0.172, 0.118, 0.012, 0.6), (1.30, 0.196, 0.126, 0.02, 0.6), (1.42, 0.18, 0.108, 0.025, 0.65)],
                seg=12)
        for s in (-1, 1):
            B.box("SA_Vest", "Chest", (s * 0.09, 0.14, 1.22), (0.08, 0.04, 0.10))
            B.box("SA_Vest", "Chest", (s * 0.09, 0.145, 1.34), (0.07, 0.035, 0.07))
            B.box("SA_Vest", "Chest", (s * 0.10, 0.03, 1.462), (0.06, 0.22, 0.02))
        B.box("SA_Team", "Chest", (-0.09, 0.166, 1.355), (0.05, 0.004, 0.03))                       # name tape
        B.box("SA_Rubber", "Chest", (0.10, 0.165, 1.34), (0.03, 0.01, 0.05))                       # radio
        # flight helmet with visor housing and team stripe
        HM = K.HC_HEAD + V((0, -0.008, 0.02))
        K.helmet_shell(B, HM, "SA_Helmet", r=0.138, h=0.135, back_drop=0.07, top_h=0.138)
        B.tube("SA_Glass", "Head", [HM + V((-0.11, 0.07, -0.01)), HM + V((-0.06, 0.125, -0.012)),
                                    HM + V((0, 0.14, -0.012)), HM + V((0.06, 0.125, -0.012)),
                                    HM + V((0.11, 0.07, -0.01))], [(0.035, 0.006)] * 5, seg=4)
        B.box("SA_Helmet", "Head", HM + V((0, 0.13, 0.05)), (0.12, 0.03, 0.03), (-0.4, 0, 0))
        B.box("SA_Team", "Head", HM + V((0, -0.02, 0.135)), (0.03, 0.18, 0.006))
        # G-suit thigh panels
        for s in (-1, 1):
            hp, kn = K.HIP[s], K.KNEE[s]
            B.tube("SA_Vest", f"chain:leg{s}", [hp + (kn - hp) * 0.2, hp + (kn - hp) * 0.85],
                   [(0.10, 0.10), (0.078, 0.08)], seg=10)

    def pose_extra(p):
        p["w_loc"], p["w_q"] = P_CARRY[0].copy(), P_CARRY[1].copy()
        left_free(p, (-0.235, 0.05, 0.89))
        p["elbow_pole"] = {1: V((0.3, -0.4, -0.1)), -1: V((-0.3, -0.3, -0.2))}
        p["lslide"], p["lroll"], p["ldrop"] = 0.0, 0.0, 0.0

    def aim_extra(p, kneel):                  # two-handed, arms extended, support hand under the firing hand
        p["lgrip"] = 1.0
        p["lslide"], p["lroll"], p["ldrop"] = -0.17, D(-15), 0.05
        p["hips_rot"] = V((0, 0, D(-8))) if not kneel else p["hips_rot"]
        p["chest"] = V((D(-3), 0, D(3))); p["spine"] = V((D(-4), 0, D(-2)))
        p["head"] = V((D(-6), D(4), D(6))); p["neck"] = V((D(-3), 0, D(2)))
        p["elbow_pole"] = {1: V((0.4, -0.2, -0.5)), -1: V((-0.4, -0.2, -0.5))}

    K.POSE_EXTRA = pose_extra
    K.AIM_EXTRA = aim_extra

    def walk(t):
        p = K.act_walk(t); left_swing(p, t); return p

    def run(t):
        p = K.base_pose(); K.run_legs(p, t); K.run_torso(p)
        p["rifle_rot"] = V((D(25) + D(6) * math.sin(4 * PI * t), 0, 0))
        left_pump(p, t)
        return p

    acts = lambda: [("idle", K.act_idle, 3.0, True), ("walk", walk, K.WALK["Tc"], True), ("run", run, K.RUN["Tc"], True),
                    ("aim", K.act_aim, 2.0, True), ("fire", K.act_fire, 0.3, True),
                    ("crouch_fire", K.act_crouch_fire, 0.3, True), ("die", K.act_die, 1.5, False)]
    return K.Role("pilot", body_name="Pilot_Body", palette=flatten(PAL["pilot"]), camo_seed=1985,
                  weapon=Wp.gun("Pistol", Wp.build_pistol, (0, 0.405, -0.006), aim_pocket=(0.03, 0.33, 1.46),
                                kick=0.02, lift=0.008, rise=9.0, lay=dict(gx=0.22, gy=0.10, grip=0.255, side=0.085,
                                                                           h=0.03)),
                  extra_mats={"SA_Vest": ((0.16, 0.18, 0.12), 0.85, 0.0), "SA_Helmet": ((0.30, 0.32, 0.27), 0.5, 0.0)},
                  body_opts=dict(pack=None, radio=False, hydration=False, carrier="none", helmet=None,
                                 knee_pads=False, eyepro=False, beard=False),
                  body_extra=extra, actions=acts,
                  report_extra={"notes": "Flight suit (near-plain sage camo texture), survival vest, flight helmet "
                                         "with visor; pistol one-handed at the side when moving, two-handed aim."})


# ------------------------------------------------------------------ EOD (bomb suit + mine detector)
E_CARRY = carry((0.21, 0.24, 0.97), (0.0, 0.72, -0.69), (0.0, 0.69, 0.72))


def role_eod():
    def extra(B):
        A = "SA_CamoGear"
        # bomb suit: armoured torso + groin plate, high collar, padded sleeves / legs, big helmet + visor
        B.loftz(A, {"Chest": 0.8, "Spine": 0.2}, [(1.00, 0.20, 0.15, 0.02, 0.6), (1.20, 0.225, 0.17, 0.03, 0.55),
                                                  (1.40, 0.22, 0.16, 0.03, 0.6), (1.47, 0.17, 0.13, 0.03, 0.7)], seg=14)
        B.box(A, "Chest", (0, 0.19, 1.25), (0.34, 0.06, 0.36), (0.05, 0, 0))
        B.box(A, "Hips", (0, 0.16, 0.90), (0.22, 0.05, 0.16), (-0.1, 0, 0))
        B.loftz(A, "Chest", [(1.43, 0.17, 0.155, 0.02, 0.8), (1.58, 0.155, 0.145, 0.03, 0.8)], seg=12, caps=False)
        B.box("SA_Team", "Chest", (0, 0.222, 1.33), (0.12, 0.004, 0.06))
        B.box(A, "Chest", (0, -0.20, 1.24), (0.30, 0.10, 0.34))                                   # cooling unit / kit
        B.box("SA_Rubber", "Chest", (0, -0.255, 1.24), (0.24, 0.02, 0.26))
        for s in (-1, 1):
            sh, el, wr = K.SH[s], K.ELB[s], K.WRIST[s]
            d1, d2 = (el - sh).normalized(), (wr - el).normalized()
            B.ell(A, f"chain:arm{s}", sh + V((0, 0, 0.01)), (0.09, 0.09, 0.08), u=10, v=6)
            B.tube(A, f"chain:arm{s}", [sh + d1 * 0.02, el + d1 * 0.01], [(0.078, 0.08), (0.065, 0.068)], seg=8)
            B.tube(A, f"chain:arm{s}", [el + d2 * 0.02, wr - d2 * 0.04], [(0.066, 0.068), (0.054, 0.056)], seg=8)
            hp, kn, an = K.HIP[s], K.KNEE[s], K.ANKLE[s]
            e1, e2 = (kn - hp).normalized(), (an - kn).normalized()
            B.tube(A, f"chain:leg{s}", [hp + e1 * 0.05, kn - e1 * 0.03], [(0.115, 0.118), (0.09, 0.094)], seg=10)
            B.ell(A, f"{K.SIDE[s]}LowerLeg", kn + V((0, 0.05, -0.01)), (0.075, 0.05, 0.09), u=8, v=6)
            B.tube(A, f"chain:leg{s}", [kn + e2 * 0.06, an + V((0, 0, 0.14))], [(0.085, 0.09), (0.07, 0.074)], seg=10)
        HM = K.HC_HEAD + V((0, -0.01, 0.0))
        K.helmet_shell(B, HM, A, r=0.168, h=0.17, back_drop=0.09, top_h=0.172)
        B.box("SA_Glass", "Head", HM + V((0, 0.15, -0.01)), (0.20, 0.03, 0.16), (-0.15, 0, 0))
        B.box(A, "Head", HM + V((0, 0.15, -0.10)), (0.17, 0.05, 0.05))
        B.box("SA_Rubber", "Head", HM + V((0.0, 0.16, 0.08)), (0.05, 0.03, 0.03))                # lamp

    def pose_extra(p):
        p["w_loc"], p["w_q"] = E_CARRY[0].copy(), E_CARRY[1].copy()
        left_free(p, (-0.25, 0.04, 0.90))
        p["elbow_pole"] = {1: V((0.35, -0.4, -0.1)), -1: V((-0.4, -0.3, -0.2))}

    def aim_extra(p, kneel):                  # "aim" = search stance, no shouldering
        p["aim"] = 0.0
        p["hips_rot"] = V((D(6), 0, 0)) if not kneel else V((D(4), 0, D(-8)))
        p["spine"] = V((D(-10), 0, 0)); p["chest"] = V((D(-8), 0, 0))
        p["neck"] = V((D(-8), 0, 0)); p["head"] = V((D(-18), 0, 0))
        if not kneel:
            p["hips_pos"] = V((0, -0.03, 0.92))
            p["foot"] = {1: K.place_foot(0.17, -0.05, 0, 0, D(-12)), -1: K.place_foot(-0.17, 0.08, 0, 0, D(10))}
            p["knee_pole"] = {1: V((0.3, 1, 0.1)), -1: V((-0.3, 1, 0.1))}
        p["w_loc"], p["w_q"] = carry((0.20, 0.30, 0.98), (0.0, 0.62, -0.78), (0.0, 0.78, 0.62))
        p["elbow_pole"] = {1: V((0.35, -0.4, -0.1)), -1: V((-0.4, -0.3, -0.2))}

    K.POSE_EXTRA = pose_extra
    K.AIM_EXTRA = aim_extra

    def walk(t):
        p = K.base_pose(); K.walk_legs(p, t)
        p["spine"] += V((D(-3), 0, 0)); p["head"] += V((D(3), 0, 0))
        p["rifle_rot"] = V((D(2) * math.sin(4 * PI * t), 0, D(2) * math.sin(2 * PI * t)))
        left_swing(p, t)
        return p

    def run(t):                                   # heavy suit: a laboured jog (same stride timing as everyone)
        p = K.base_pose(); K.run_legs(p, t); K.run_torso(p)
        p["rifle_rot"] = V((D(30) + D(5) * math.sin(4 * PI * t), 0, 0))
        left_pump(p, t)
        return p

    def sweep(period_frac, amp, kneel=False):
        def act(t):
            p = kneel_relaxed(K.base_pose()) if kneel else K.aim_pose(K.base_pose())
            if kneel:
                aim_extra(p, True)
                p["w_loc"], p["w_q"] = carry((0.22, 0.28, 0.98), (0.0, 0.55, -0.83), (0.0, 0.83, 0.55))
            a = amp * math.sin(2 * PI * t * period_frac)
            p["rifle_rot"] = V((0, 0, a))
            p["chest"] += V((0, 0, a * 0.25)); p["head"] += V((0, 0, a * 0.5))
            return p
        return act

    def work(t):                                   # kneeling at a device: coil grounded at the right, left hand works
        p = kneel_relaxed(K.base_pose())
        b = math.sin(2 * PI * t)
        p["spine"] = V((D(-24), 0, D(4))); p["chest"] = V((D(-12), 0, D(4))); p["head"] = V((D(-22), 0, D(8)))
        p["w_loc"], p["w_q"] = carry((0.26, 0.24, 1.00), (0.40, 0.88, -0.25), (0.0, 0.25, 0.97))
        left_free(p, (-0.04 + 0.05 * b, 0.37, 1.07 + 0.02 * math.sin(6 * PI * t)), (0.4, 0.8, -0.6), (0.1, 0.4, 1.0))
        p["elbow_pole"] = {1: V((0.4, -0.3, 0.0)), -1: V((-0.5, 0.0, -0.3))}
        return p

    K.GROUND_SOLVE = {"die", "work", "crouch_fire", "aim", "fire"}
    K.WEAPON_SOLVE_ITERS = 40
    acts = lambda: [("idle", K.act_idle, 3.0, True), ("walk", walk, K.WALK["Tc"], True), ("run", run, K.RUN["Tc"], True),
                    ("aim", sweep(1, D(14)), 2.0, True), ("fire", sweep(1, D(26)), 1.0, True),
                    ("crouch_fire", sweep(1, D(20), kneel=True), 1.5, True), ("die", K.act_die, 1.5, False),
                    ("work", work, 2.0, True)]
    return K.Role("eod_engineer", body_name="EOD_Body", palette=PAL["eod_engineer"], camo_seed=1986,
                  weapon=Wp.gun("Detector", Wp.build_detector, (0, 1.30, -0.11),
                                lay=dict(gx=0.24, gy=0.10, grip=0.255, side=0.085, h=0.16)),
                  extra_mats={"SA_Olive": ((0.16, 0.17, 0.10), 0.8, 0.0)},
                  body_opts=dict(pack=None, radio=False, hydration=False, carrier="none", helmet=None,
                                 knee_pads=False, eyepro=False, armband=False, holster=False, mag_pouches=False),
                  body_extra=extra, actions=acts,
                  report_extra={"notes": "Hand item is a mine detector (object `Detector`); `Muzzle` = search-coil "
                                         "centre (effect / sweep point), not a gun bore. aim = slow search sweep, "
                                         "fire = fast sweep (1.0 s), crouch_fire = kneeling sweep (1.5 s), work = "
                                         "kneeling device work loop. Tool kit is the back unit (not hand-held)."})


ROLES = {"medic": role_medic, "saw_gunner": role_saw, "m240_gunner": role_m240, "sniper": role_sniper,
         "ranger": role_ranger, "special_forces": role_sf, "pilot": role_pilot, "eod_engineer": role_eod}
K.build(ROLES[ROLE](), OUT, PREV, ONLY_ANIMS)

"""Steel Accord - M1 infantry hand items (original, generic designs; Blender primitives only).

Every item uses the carbine's local frame (origin = butt / rear reference, +Y along the bore, +Z up) and puts its
pistol grip at (0, 0.255, -0.085), exactly where the approved rifle's grip is, so the shared bind pose holds it and the
rifleman aim / kneel / die solvers work unchanged. `Muzzle` empties are placed at the bore exit (+Y along the bore).
"""
import math
import inf_kit as K
from mathutils import Vector as V

PI = math.pi
D = math.radians
GRIP = (0, 0.255, -0.085)
AXIS = (-PI / 2, 0, 0)            # cylinder axis along +Y


def _grip(R, w):
    R.box("SA_Rubber", w, GRIP, (0.032, 0.035, 0.09), (0.35, 0, 0))


def build_saw(R, w):
    """Light machine gun: skeleton stock, tall receiver with feed cover + carry handle, soft 200-rd box pouch."""
    M, Rb, C = "SA_Metal", "SA_Rubber", "SA_Canvas"
    R.box(Rb, w, (0, 0.03, -0.035), (0.04, 0.06, 0.12))                       # butt pad
    R.box(M, w, (0, 0.10, -0.01), (0.03, 0.12, 0.03)); R.box(M, w, (0, 0.10, -0.075), (0.02, 0.12, 0.02))
    R.box(M, w, (0, 0.27, 0.0), (0.062, 0.26, 0.09))                           # receiver
    R.box(M, w, (0, 0.27, 0.058), (0.058, 0.22, 0.028))                        # feed cover
    R.box(M, w, (0, 0.26, 0.09), (0.03, 0.08, 0.02))                           # optic rail + small optic
    R.box(M, w, (0, 0.26, 0.115), (0.04, 0.09, 0.04))
    R.cyl("SA_Glass", w, (0, 0.307, 0.115), 0.016, 0.004, AXIS, seg=8)
    _grip(R, w)
    R.box(C, w, (-0.055, 0.33, -0.10), (0.085, 0.11, 0.12))                    # ammo pouch (left, under)
    R.box(Rb, w, (-0.052, 0.33, -0.035), (0.06, 0.06, 0.02))
    R.box(M, w, (0, 0.47, -0.005), (0.05, 0.16, 0.055))                        # handguard
    R.cyl(M, w, (0, 0.71, 0.0), 0.016, 0.42, AXIS, seg=8)                     # barrel
    R.box(M, w, (0, 0.66, 0.03), (0.028, 0.26, 0.012))                         # heat shield
    R.box(M, w, (0, 0.53, 0.075), (0.016, 0.03, 0.06)); R.box(M, w, (0, 0.53, 0.105), (0.016, 0.10, 0.014))  # handle
    R.cyl(M, w, (0, 0.94, 0.0), 0.022, 0.06, AXIS, seg=8)                     # flash hider
    for s in (-1, 1):                                                          # folded bipod
        R.box(M, w, (s * 0.014, 0.76, -0.03), (0.008, 0.26, 0.008))
    R.box(M, w, (0, 0.88, 0.035), (0.008, 0.01, 0.03))                         # front sight


def build_m240(R, w):
    """Medium machine gun: heavier, longer; belt pouch on the left, barrel carry handle, bipod folded forward."""
    M, Rb, C = "SA_Metal", "SA_Rubber", "SA_Canvas"
    R.box(Rb, w, (0, 0.02, -0.04), (0.045, 0.04, 0.13))
    R.box(M, w, (0, 0.11, -0.03), (0.042, 0.15, 0.10), (0.06, 0, 0))          # stock
    R.box(M, w, (0, 0.31, 0.0), (0.072, 0.30, 0.11))                           # receiver
    R.box(M, w, (0, 0.30, 0.07), (0.07, 0.17, 0.03))                           # feed cover
    R.box(M, w, (0, 0.24, 0.10), (0.035, 0.10, 0.03)); R.box(M, w, (0, 0.24, 0.13), (0.045, 0.11, 0.045))
    R.cyl("SA_Glass", w, (0, 0.297, 0.13), 0.018, 0.004, AXIS, seg=8)
    _grip(R, w)
    R.box(C, w, (-0.075, 0.33, -0.11), (0.10, 0.13, 0.14))                     # belt pouch
    R.box(M, w, (-0.045, 0.33, 0.035), (0.03, 0.05, 0.015), (0, 0.4, 0))      # belt into the feed tray
    R.box(M, w, (0, 0.52, -0.005), (0.058, 0.14, 0.07))                        # handguard / gas block
    R.cyl(M, w, (0, 0.80, 0.0), 0.019, 0.56, AXIS, seg=8)                     # barrel
    R.cyl(M, w, (0, 0.78, -0.035), 0.011, 0.44, AXIS, seg=6)                  # gas tube
    R.box(M, w, (0, 0.66, 0.065), (0.016, 0.03, 0.08)); R.box(M, w, (0, 0.66, 0.105), (0.016, 0.12, 0.016))
    R.cyl(M, w, (0, 1.11, 0.0), 0.025, 0.08, AXIS, seg=8)
    for s in (-1, 1):
        R.box(M, w, (s * 0.016, 0.88, -0.06), (0.009, 0.30, 0.009), (0.05, 0, 0))
    R.box(M, w, (0, 1.06, 0.04), (0.008, 0.012, 0.04))


def build_sniper(R, w):
    """Long precision rifle: adjustable stock with cheek rest, large scope, heavy barrel + suppressor."""
    M, Rb, C = "SA_Metal", "SA_Rubber", "SA_Canvas"
    R.box(Rb, w, (0, 0.015, -0.03), (0.04, 0.03, 0.14))
    R.box(C, w, (0, 0.10, -0.04), (0.045, 0.16, 0.10))                         # stock
    R.box(C, w, (0, 0.09, 0.025), (0.04, 0.12, 0.03))                          # cheek rest
    R.box(M, w, (0, 0.30, 0.0), (0.05, 0.26, 0.07))                            # receiver / chassis
    R.box(M, w, (0.035, 0.24, 0.02), (0.035, 0.012, 0.012)); R.ell(M, w, (0.055, 0.24, 0.02), (0.012, 0.012, 0.012), u=6, v=4)
    _grip(R, w)
    R.box(M, w, (0, 0.34, -0.06), (0.03, 0.06, 0.05))                          # magazine
    R.cyl(M, w, (0, 0.37, 0.085), 0.021, 0.30, AXIS, seg=10)                  # scope tube
    R.cyl(M, w, (0, 0.24, 0.085), 0.024, 0.05, AXIS, seg=10)
    R.cyl(M, w, (0, 0.53, 0.085), 0.029, 0.07, AXIS, seg=10)                  # objective bell
    R.cyl("SA_Glass", w, (0, 0.566, 0.085), 0.025, 0.004, AXIS, seg=10)
    R.cyl(M, w, (0, 0.37, 0.115), 0.012, 0.03, seg=6)                          # turret
    for y in (0.30, 0.43):
        R.box(M, w, (0, y, 0.05), (0.03, 0.02, 0.04))
    R.box(M, w, (0, 0.56, -0.005), (0.052, 0.26, 0.06))                        # handguard
    R.cyl(M, w, (0, 0.86, 0.0), 0.017, 0.36, AXIS, seg=8)                     # barrel
    R.cyl(M, w, (0, 1.12, 0.0), 0.025, 0.20, AXIS, seg=10)                    # suppressor
    for s in (-1, 1):
        R.box(M, w, (s * 0.013, 0.74, -0.04), (0.008, 0.22, 0.008))


def build_carbine_ranger(R, w):
    """Carbine variant: approved carbine + laser/illuminator box and magnifier."""
    K.build_carbine(R, w)
    R.box("SA_Canvas", w, (0, 0.60, 0.065), (0.035, 0.07, 0.035))
    R.box("SA_Metal", w, (0, 0.255, 0.095), (0.034, 0.07, 0.04))
    R.cyl("SA_Glass", w, (0, 0.29, 0.095), 0.013, 0.004, AXIS, seg=8)


def build_carbine_sf(R, w):
    """Short-barrelled suppressed carbine, coyote furniture."""
    M, Rb, C = "SA_Metal", "SA_Rubber", "SA_Canvas"
    R.box(C, w, (0, 0.012, -0.025), (0.042, 0.025, 0.13))
    R.box(C, w, (0, 0.07, -0.02), (0.038, 0.1, 0.11))
    R.box(M, w, (0, 0.07, 0.04), (0.03, 0.12, 0.03), (0.15, 0, 0))
    R.cyl(M, w, (0, 0.15, 0.01), 0.016, 0.14, AXIS, seg=6)
    R.box(M, w, (0, 0.32, 0.015), (0.045, 0.22, 0.05))
    R.box(M, w, (0, 0.31, -0.03), (0.04, 0.17, 0.045))
    R.box(M, w, (0, 0.36, -0.08), (0.036, 0.055, 0.07), (0.15, 0, 0))
    _grip(R, w)
    for k in range(4):
        R.box(C, w, (0, 0.375 + k * 0.012, -0.135 - k * 0.04), (0.03, 0.065, 0.046), (0.15 + k * 0.1, 0, 0))
    R.box(C, w, (0, 0.52, 0.008), (0.05, 0.19, 0.055))                         # short rail
    R.cyl(M, w, (0, 0.66, 0.008), 0.024, 0.18, AXIS, seg=8)                   # suppressor
    R.box(M, w, (0, 0.335, 0.065), (0.03, 0.06, 0.02))
    R.box(M, w, (0, 0.33, 0.09), (0.036, 0.07, 0.035))                          # red dot
    R.cyl("SA_Glass", w, (0, 0.366, 0.09), 0.014, 0.004, AXIS, seg=8)
    R.box(C, w, (0, 0.53, 0.06), (0.032, 0.06, 0.03))                          # laser box
    R.box(Rb, w, (0, 0.52, -0.04), (0.022, 0.03, 0.06))


def build_pistol(R, w):
    """Generic service pistol; grip in the shared grip position."""
    R.box("SA_Rubber", w, GRIP, (0.03, 0.035, 0.10), (0.35, 0, 0))
    R.box("SA_Metal", w, (0, 0.315, -0.022), (0.028, 0.18, 0.034))
    R.box("SA_Rubber", w, (0, 0.30, -0.048), (0.026, 0.12, 0.02))
    R.box("SA_Rubber", w, (0, 0.30, -0.068), (0.008, 0.04, 0.025))
    R.box("SA_Metal", w, (0, 0.395, -0.006), (0.006, 0.008, 0.008))


def build_detector(R, w):
    """Mine detector: arm cuff, grip, electronics box, telescopic shaft, search coil (flat when pitched 45 deg)."""
    M, Rb = "SA_Metal", "SA_Rubber"
    R.box(Rb, w, (0, 0.05, -0.10), (0.07, 0.10, 0.03), (-0.3, 0, 0))          # arm cuff
    R.cyl(M, w, (0, 0.62, -0.05), 0.013, 1.24, AXIS, seg=6)                   # shaft
    _grip(R, w)
    R.box("SA_Olive", w, (0, 0.18, -0.03), (0.06, 0.12, 0.06))                # electronics box
    R.box(Rb, w, (0, 0.20, 0.005), (0.04, 0.05, 0.01))
    R.cyl(M, w, (0, 0.80, -0.05), 0.017, 0.12, AXIS, seg=6)                   # telescopic joint
    R.cyl("SA_Olive", w, (0, 1.30, -0.11), 0.14, 0.03, (D(45), 0, 0), seg=14)  # search coil
    R.box(M, w, (0, 1.25, -0.075), (0.02, 0.07, 0.02), (D(45), 0, 0))


def gun(name, build, muzzle, **kw):
    kw.setdefault("grip_local", GRIP)
    return K.Weapon(name, build, K.RIFLE_REST, K.BUTT, V(muzzle), **kw)

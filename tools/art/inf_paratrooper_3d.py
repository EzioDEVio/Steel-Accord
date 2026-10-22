"""Steel Accord - M1 infantry: paratrooper (rifleman variant with jump harness) + personnel parachute.

Run:  python3 tools/art/inf_paratrooper_3d.py godot/assets/units3d/paratrooper [--previews docs/screens]
Out:  paratrooper.glb  - rifleman kit + parachute harness, reserve on the belly, main container on the back;
                         rifle on RightHand with `Muzzle`; empty `ChuteAttach` (child of the Chest bone) at the riser
                         connection point between the shoulders; actions idle/walk/run/aim/fire/crouch_fire/die plus
                         para_descend (loop, hanging under the canopy, legs together) and para_land (one-shot landing
                         roll that ends exactly in idle frame 0).
      parachute_personnel.glb - round military canopy: object `Canopy` (dome, 24 gores, apex vent) and object
                         `Rigging` (24 suspension lines, 4 risers). Origin = harness attachment point (riser ends meet
                         at x = +/-0.12 m), +Z up, +Y forward. Action `canopy_idle` (2 s loop, gentle breathing).
                         Attach it at the paratrooper's `ChuteAttach` node during para_descend.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inf_kit as K
import bpy, bmesh, json
import numpy as np
from mathutils import Matrix, Vector as V, Quaternion, Euler

D = math.radians
PI = math.pi
OUT, PREV, ONLY_ANIMS = K.parse_args()

# rifleman concept palette (the paratrooper has no separate concept; same uniform as the rifleman)
PALETTE = dict(K.RIFLEMAN_PALETTE)
ATTACH = V((0.0, 0.0, 1.49))           # riser connection midpoint, rest pose (chest-rigid)
CONN_X = 0.12


def body_extra(B):
    O, W = "SA_Olive", "SA_Webbing"
    # main container on the back (deployment bag already out), team panel on its top flap
    B.box(O, "Chest", (0, -0.215, 1.24), (0.30, 0.13, 0.40), (-0.05, 0, 0))
    B.box(O, "Chest", (0, -0.222, 1.45), (0.28, 0.12, 0.05), (-0.10, 0, 0))
    B.box("SA_Team", "Chest", (0, -0.226, 1.478), (0.15, 0.08, 0.006), (-0.10, 0, 0))
    # shoulder straps / main lift webs: back -> over the shoulder -> front, canopy release on top
    for s in (-1, 1):
        x = s * CONN_X
        B.tube(W, "Chest", [V((x, -0.15, 1.12)), V((x, -0.10, 1.44)), V((x, 0.0, 1.515)), V((x, 0.13, 1.47)),
                            V((s * 0.11, 0.236, 1.30)), V((s * 0.10, 0.236, 1.10))], [(0.024, 0.006)] * 6, seg=4)
        B.box("SA_Metal", "Chest", (x, 0.02, 1.522), (0.04, 0.05, 0.02))                    # canopy release
        # leg strap band around the top of each thigh
        hp, kn = K.HIP[s], K.KNEE[s]
        d1 = (kn - hp).normalized()
        B.tube(W, f"{K.SIDE[s]}UpperLeg", [hp + d1 * 0.13, hp + d1 * 0.17], [(0.099, 0.101)] * 2, seg=10, caps=False)
        B.tube(W, "Hips", [V((s * 0.10, 0.13, 1.04)), V((s * 0.105, 0.115, 0.93)), hp + d1 * 0.15 + V((0, 0.09, 0))],
               [(0.022, 0.006)] * 3, seg=4)
    B.tube(W, "Chest", [V((-0.12, 0.237, 1.33)), V((0.12, 0.237, 1.33))], [(0.006, 0.02)] * 2, seg=4)   # chest strap
    B.box("SA_Metal", "Chest", (0, 0.24, 1.33), (0.05, 0.012, 0.03))
    # reserve parachute on the belly (below the mag pouches), carry handle + team flap
    B.box(O, "Hips", (-0.02, 0.215, 0.975), (0.28, 0.095, 0.15))
    B.box(O, "Hips", (-0.02, 0.265, 0.975), (0.24, 0.012, 0.12))
    B.box("SA_Metal", "Hips", (0.10, 0.27, 0.99), (0.02, 0.02, 0.05))


def chute_attach(arm):
    return [K.bone_empty("ChuteAttach", "Chest", ATTACH)]


# ------------------------------------------------------------------ para actions
DESC_LIFT = [0.06]


def descend_pose(t):
    p = K.base_pose()
    sw = math.sin(2 * PI * t)
    p["hips_pos"] = V((0.0, 0.0, 0.958 + DESC_LIFT[0]))
    p["hips_rot"] = V((D(3) * sw, D(2.5) * math.sin(2 * PI * t + 0.7), 0))
    p["spine"] = V((D(-2), 0, 0)); p["chest"] = V((D(-1.5) * sw, 0, 0))
    p["neck"] = V((D(6), 0, 0)); p["head"] = V((D(14), 0, D(6) * math.sin(2 * PI * t + 1.4)))   # looking down
    hz = p["hips_pos"].z
    for s in (-1, 1):                                    # legs together, slightly bent, toes pointing down
        lag = D(4) * math.sin(2 * PI * t - 0.9)
        q = (Matrix.Rotation(D(4) * s, 3, "Z") @ Matrix.Rotation(D(-42) + lag, 3, "X")).to_quaternion()
        p["foot"][s] = {"ankle": V((s * 0.075, 0.05 + 0.03 * math.sin(2 * PI * t - 0.9), hz - 0.80)), "q": q}
    p["knee_pole"] = {1: V((0.05, 1, 0.0)), -1: V((-0.05, 1, 0.0))}
    # left hand up on the left riser, right hand keeps the rifle tucked at low ready
    p["lgrip"] = 0.0
    p["lfree"] = V((-0.21, 0.03, 1.80 + 0.01 * sw))
    p["lfree_q"] = K.hand_q((0.7, 0.3, 0.6), (-0.6, 0.6, -0.2))
    p["elbow_pole"] = {1: V((0.3, -0.2, -0.3)), -1: V((-0.6, 0.0, 0.1))}
    p["rifle_rot"] = V((D(-12), 0, D(4)))
    return p


def act_descend(t):
    return descend_pose(t)


def kneel_up(p):
    p = K.kneel_pose(p)
    p["aim"] = 0.0
    p["spine"] = V((D(-12), 0, 0)); p["chest"] = V((D(-4), 0, 0)); p["neck"] = V((0, 0, 0)); p["head"] = V((D(6), 0, 0))
    p["hips_rot"] = V((D(4), 0, D(-10)))
    p["elbow_pole"] = {1: V((0.3, -0.2, -0.3)), -1: V((-0.3, 0.05, -0.4))}
    return p


LAND_KEYS = []


def land_keys():
    k0 = descend_pose(0.0)
    k1 = K.base_pose()                                   # touchdown: feet and knees together, knees give
    k1["hips_pos"] = V((0.0, -0.03, 0.78)); k1["spine"] = V((D(-14), 0, 0)); k1["chest"] = V((D(-8), 0, 0))
    k1["head"] = V((D(6), 0, 0))
    k1["foot"] = {1: K.place_foot(0.07, 0.05, 0, 0, D(-3)), -1: K.place_foot(-0.07, 0.05, 0, 0, D(3))}
    k1["knee_pole"] = {1: V((0.05, 1, 0.0)), -1: V((-0.05, 1, 0.0))}
    k1["lgrip"] = 0.0; k1["lfree"] = V((-0.16, 0.12, 1.45)); k1["lfree_q"] = K.hand_q((0.6, 0.6, 0.3), (-0.5, 0.2, 0.8))
    k1["rifle_rot"] = V((D(-10), 0, D(4)))
    k2 = K.lerp(k1, k1, 0)                               # roll onto the right side: calf, thigh, hip, back
    k2["hips_pos"] = V((0.14, -0.08, 0.40)); k2["hips_rot"] = V((D(-10), D(55), D(-10)))
    k2["spine"] = V((D(-18), D(10), 0)); k2["chest"] = V((D(-14), D(8), 0)); k2["head"] = V((D(-10), D(-20), 0))
    k2["foot"] = {1: K.place_foot(0.24, 0.10, 0.02, D(10), D(-20)), -1: K.place_foot(0.10, 0.12, 0.10, D(20), D(-15))}
    k2["knee_pole"] = {1: V((0.6, 1, 0.3)), -1: V((0.5, 1, 0.4))}
    k3 = K.lerp(k2, k2, 0)                               # on the back/right shoulder, legs tucked over
    k3["hips_pos"] = V((0.30, -0.18, 0.20)); k3["hips_rot"] = V((D(20), D(80), D(-15)))
    k3["spine"] = V((D(-25), 0, 0)); k3["chest"] = V((D(-15), 0, 0)); k3["head"] = V((D(-25), D(-25), 0))
    k3["foot"] = {1: K.place_foot(0.55, 0.25, 0.25, D(20), D(-60)), -1: K.place_foot(0.45, 0.30, 0.35, D(20), D(-60))}
    k3["knee_pole"] = {1: V((0.3, 1, 0.8)), -1: V((0.3, 1, 0.8))}
    k4 = kneel_up(K.base_pose())                         # rolled back up onto one knee
    k4["lgrip"] = 0.4; k4["lfree"] = V((-0.25, 0.15, 1.05))
    k5 = K.base_pose()                                   # standing up
    k5["hips_pos"] = V((0.0, -0.02, 0.86)); k5["spine"] = V((D(-10), 0, 0)); k5["chest"] = V((D(-3), 0, 0))
    k5["foot"] = {1: K.place_foot(0.12, -0.05, 0, 0, D(-9)), -1: K.place_foot(-0.12, 0.10, 0, 0, D(7))}
    k6 = K.act_idle(0.0)
    return [(0.0, k0), (0.12, k1), (0.45, k2), (0.8, k3), (1.3, k4), (1.85, k5), (2.25, k6), (2.4, k6)]


def act_land(t):
    s = t * 2.4
    for (ta, a), (tb, b) in zip(LAND_KEYS, LAND_KEYS[1:]):
        if s <= tb:
            u = K.smoothstep((s - ta) / (tb - ta))
            return K.lerp(a, b, u)
    return LAND_KEYS[-1][1]


def actions():
    # calibrate the hanging height so the pointed toes just reach the ground plane (lowest point = 0)
    for _ in range(3):
        DESC_LIFT[0] -= K.pose_minz(descend_pose(0.0))
    LAND_KEYS[:] = land_keys()
    return K.rifleman_actions() + [("para_descend", act_descend, 2.0, True), ("para_land", act_land, 2.4, False)]


K.GROUND_SOLVE = {"die", "para_land"}
role = K.Role("paratrooper", body_name="Paratrooper_Body", palette=PALETTE, camo_seed=1977,
              extra_mats={"SA_Olive": ((0.16, 0.17, 0.10), 0.8, 0.0), "SA_Webbing": ((0.20, 0.19, 0.13), 0.9, 0.0)},
              body_opts=dict(pack=None, hydration=False), body_extra=body_extra, actions=actions,
              extra_objects=chute_attach,
              report_extra={"chute_attach_rest": list(ATTACH),
                            "chute_attach_para_descend_m": [0.0, 0.0, 1.525],
                            "chute_attach_at_1p3_scale_m": 1.98,
                            "notes": "para_descend loops (2 s); para_land is one-shot (2.4 s) and its last frame equals "
                                     "idle frame 0. Attach parachute_personnel.glb (origin = harness point) to the "
                                     "ChuteAttach node; detach/hide it when para_land starts. unit.gd currently puts the canopy at "
                                     "vis y=2.0, which matches the harness height (1.525 m x 1.3 infantry scale = "
                                     "1.98 m) if the canopy itself is not scaled."})
rep = K.build(role, OUT, PREV, ONLY_ANIMS)


# =============================================================================== personnel parachute (separate GLB)
def build_parachute(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 30
    from PIL import Image
    N, ROWS = 24, 6
    # gore panel texture: olive nylon, darker seams at the gore edges and the reinforcement bands
    n = 256
    u = np.linspace(0, 1, n, endpoint=False)
    uu, vv = np.meshgrid(u, u)
    img = np.zeros((n, n, 3)) + np.array((86, 88, 58), float)
    seam = np.exp(-((np.minimum(uu, 1 - uu)) / 0.012) ** 2)
    band = sum(np.exp(-((vv - b) / 0.01) ** 2) for b in (0.18, 0.5, 0.82))
    rng = np.random.default_rng(5)
    img = img * (1 - 0.35 * seam[..., None]) * (1 - 0.18 * band[..., None])
    img += (rng.standard_normal((n, n)) * 2.0)[..., None]
    tex = os.path.join(out, "parachute_gore.png")
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(tex)

    def pmat(name, rgb, rough, tex_=None):
        m = bpy.data.materials.new(name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
        if tex_:
            t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex_); t.image.pack()
            m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
        m.use_backface_culling = False
        return m
    m_can = pmat("SA_Canopy", (1, 1, 1), 0.8, tex)
    m_line = pmat("SA_Lines", (0.55, 0.55, 0.45), 0.9)
    m_web = pmat("SA_Webbing", (0.20, 0.19, 0.13), 0.9)

    # ---- canopy: 24 gores x 2 segments, scalloped billow between lines, apex vent
    SKIRT_Z, SKIRT_R, DOME_H, VENT_R = 5.4, 3.2, 1.9, 0.28
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new("UVMap")
    S = 2 * N
    rings = []
    for k in range(ROWS + 1):
        t = k / ROWS                                   # 0 = vent edge, 1 = skirt
        ang = (VENT_R / SKIRT_R) * (1 - t) + t         # fraction of the quarter arc
        r = SKIRT_R * math.sin(ang * PI / 2) ** 0.85
        z = SKIRT_Z + DOME_H * math.cos(ang * PI / 2)
        if k == ROWS:
            z -= 0.10
        ring = []
        for j in range(S):
            a = j * 2 * PI / S
            mid = j % 2                                # odd = middle of a gore -> billows outward
            rr = r * (1 + (0.05 if mid else 0.0) * (0.3 + 0.7 * t))
            zz = z + (0.06 * mid * (1 - t))
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz)))
        rings.append(ring)
    for k in range(ROWS):
        for j in range(S):
            f = bm.faces.new((rings[k][j], rings[k][(j + 1) % S], rings[k + 1][(j + 1) % S], rings[k + 1][j]))
            g = j // 2; h = j % 2
            for lp, (uu_, vv_) in zip(f.loops, ((h * 0.5, k / ROWS), ((h + 1) * 0.5, k / ROWS),
                                                ((h + 1) * 0.5, (k + 1) / ROWS), (h * 0.5, (k + 1) / ROWS))):
                lp[uvl].uv = (uu_, vv_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Canopy"); bm.to_mesh(me); bm.free(); me.materials.append(m_can)
    can = bpy.data.objects.new("Canopy", me); sc.collection.objects.link(can)
    for pl in me.polygons:
        pl.use_smooth = True

    # ---- rigging: 4 risers from the connectors, 6 suspension lines per riser to the skirt line points
    rb = K.Builder(["Rigging"])
    K.MATS.clear(); K.MATS.update({"SA_Lines": m_line, "SA_Webbing": m_web}); K.MAT_ORDER[:] = ["SA_Lines", "SA_Webbing"]
    K.scene = sc
    conf = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            base = V((sx * CONN_X, 0.0, 0.0))
            top = V((sx * 0.20, sy * 0.10, 0.62))
            conf[(sx, sy)] = top
            rb.tube("SA_Webbing", "Rigging", [base + V((0, sy * 0.012, 0)), top], [(0.022, 0.004)] * 2, seg=4)
    for j in range(N):
        a = (j + 0.5) * 2 * PI / N - PI                 # line attachment points on the skirt (gore seams)
        a = j * 2 * PI / N
        sk = V((SKIRT_R * math.cos(a), SKIRT_R * math.sin(a), SKIRT_Z - 0.10))
        key = (1 if sk.x >= 0 else -1, 1 if sk.y >= 0 else -1)
        rb.tube("SA_Lines", "Rigging", [conf[key], sk], [(0.007, 0.007)] * 2, seg=3, caps=False)
    rig = rb.to_object("Rigging")
    rig.vertex_groups.clear()
    # ---- canopy_idle: gentle breathing (object scale), 2 s loop
    can.animation_data_create()
    act = bpy.data.actions.new("canopy_idle"); can.animation_data.action = act
    for f in range(61):
        t = f / 60 if f < 60 else 0.0
        b = math.sin(2 * PI * t)
        can.scale = (1 + 0.025 * b, 1 + 0.025 * b, 1 - 0.03 * b)
        can.keyframe_insert("scale", frame=f)
    act.use_cyclic = True
    glb = os.path.join(out, "parachute_personnel.glb")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_animations=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True)
    tris = {o.name: sum(len(p_.vertices) - 2 for p_ in o.data.polygons) for o in (can, rig)}
    rep_ = {"triangles": tris, "skirt_radius_m": SKIRT_R, "skirt_height_m": SKIRT_Z - 0.10,
            "apex_height_m": SKIRT_Z + DOME_H, "origin": "harness attachment point (risers end at x=+/-0.12)",
            "actions": {"canopy_idle": {"length_s": 2.0, "loop": True}}}
    with open(os.path.join(out, "parachute_personnel_report.json"), "w") as fh:
        json.dump(rep_, fh, indent=1)
    print("PARACHUTE OK", tris)
    return can, rig


if not ONLY_ANIMS:
    build_parachute(OUT)

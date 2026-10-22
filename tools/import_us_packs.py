#!/usr/bin/env python3
"""Steel Accord - import the client's U.S. installation / ground-vehicle / personnel concept packs
(AI-generated, client-supplied) and split the existing helicopter top sprites into body + rotor blades.

usage: python3 -I tools/import_us_packs.py <installations_dir> <ground_dir> <personnel_dir>

  <installations_dir>  .../US_Installation_Game_Assets/US_Installation_Game_Assets
  <ground_dir>         .../US_Ground_Forces_Game_Assets__1_/US_Ground_Forces_Game_Assets
  <personnel_dir>      .../US_Armed_Forces_Personnel_Assets/US_Armed_Forces_Personnel_Assets

The input packs are read only and treated as untrusted data.  Output (deterministic, regenerated in full):
  godot/assets/us/{buildings,vehicles,infantry,rotors}/...
  content/manifest/us_packs.json
  docs/screens/import_{buildings,vehicles,infantry,rotors}.png   (verification contact sheets)

Method (see docs/ASSET_REVIEW_US_PACKS.md for why):
  * The pack's individual crops are exact cells of the contact sheets and clip many subjects, so every view is
    re-cut from the contact sheet as the single largest connected silhouette of its cell (alpha mask dilated a
    few px before labelling so thin parts stay attached; only original pixels of that component are kept).
    The component may extend past its cell.  Where a sheet file is truncated it is reassembled losslessly from
    its four intact cell crops.
  * Pad 8 px, RGBA, no resampling except to cap the longest side at 1024 (icons are downscaled by design).
"""
import hashlib, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "godot", "assets", "us")
RES = "res://assets/us"
MANIFEST = os.path.join(ROOT, "content", "manifest", "us_packs.json")
SCREENS = os.path.join(ROOT, "docs", "screens")
AIRCRAFT = os.path.join(ROOT, "godot", "assets", "aircraft")

PAD = 8
ALPHA_T = 16
DEV = "dev_only"
RED_CROSS = "red_cross_emblem_replace_before_release"
TM = "real_design_trademark_review"

# ----------------------------------------------------------------------------------------------- tables
# id -> (pack folder, display name)
BUILDINGS = [
    ("command_center", "Command_Center", "Command Center"),
    ("defense_tower", "Base_Defense_Tower", "Defense Tower"),
    ("airfield", "Airfield", "Airfield"),
    ("war_factory", "War_Factory", "War Factory"),
    ("barracks", "Barracks", "Barracks"),
    ("supply_depot", "Supply_Depot", "Supply Depot"),
    ("airdrop_zone", "Supply_Airdrop_Zone", "Supply Airdrop Zone"),
    ("construction_yard", "Engineer_Construction_Yard", "Engineer Construction Yard"),
    ("hesco", "HESCO_Defense_Position", "HESCO Defense Position"),
    ("radar", "Radar_Communications_Station", "Radar / Communications Station"),
    ("power_plant", "Power_Generator_Plant", "Power Generator Plant"),
    ("repair_bay", "Vehicle_Repair_Bay", "Vehicle Repair Bay"),
    ("field_hospital", "Field_Hospital", "Field Hospital"),
    ("gatehouse", "Perimeter_Gatehouse", "Perimeter Gatehouse"),
]
QUAD_VIEWS = {"overhead": (0, 0), "front_three_quarter": (768, 0), "side_profile": (0, 512), "rear_three_quarter": (768, 512)}
QUAD_W, QUAD_H = 768, 512

# id -> (pack folder, display name, hull length m, nose direction in the overhead, facing of front34 / side / rear34)
# Directions were determined by looking at every sheet (hood/grille/headlights/dozer blade = front; spare wheel,
# rear doors/ramp = rear; for the M777 the muzzle).  The pack does not use a consistent orientation.
VEHICLES = [
    ("abrams", "M1A2_Abrams", "M1A2 Abrams", 7.9, "left", ("right", "left", "right")),
    ("bradley", "M2A3_Bradley", "M2A3 Bradley", 6.6, "left", ("left", "left", "left")),
    ("paladin", "M109A7_Paladin", "M109A7 Paladin", 6.8, "right", ("right", "right", "left")),
    ("m777", "M777_Howitzer", "M777 Howitzer", 9.5, "left", ("left", "left", "right")),
    ("hmmwv", "HMMWV_Humvee", "HMMWV", 4.6, "down", ("left", "left", "left")),
    ("hmmwv_tow", "HMMWV_TOW", "HMMWV TOW", 4.6, "left", ("left", "left", "left")),
    ("hmmwv_50cal", "HMMWV_50cal", "HMMWV .50 cal", 4.6, "left", ("right", "right", "left")),
    ("hmmwv_medical", "HMMWV_Medical", "HMMWV Ambulance", 5.1, "down", ("left", "left", "left")),
    ("mrap", "MRAP_M-ATV", "MRAP M-ATV", 6.3, "left", ("right", "left", "left")),
    ("stryker", "M1126_Stryker_ICV", "M1126 Stryker ICV", 6.95, "left", ("left", "left", "right")),
    ("avenger", "M1097_Avenger", "M1097 Avenger", 4.95, "down", ("left", "left", "left")),
    ("m113", "M113_APC", "M113 APC", 4.9, "left", ("left", "left", "left")),
    ("m88", "M88A2_Hercules", "M88A2 Hercules", 8.3, "left", ("right", "left", "left")),
]
ROT_TO_UP = {"up": 0, "down": 180, "left": -90, "right": 90}   # PIL rotate() angle (counter-clockwise degrees)

# 6-pose sheets: 3 x 2 cells of 512 px, row-major.  Stated order (manifest) vs what we export.
POSE_CELLS = [(0, 0), (512, 0), (1024, 0), (0, 512), (512, 512), (1024, 512)]
STD_POSES = ["stand", "walk", "run", "crouch", "kneel", "prone"]
STD_LABELS = ["standing_ready", "walking", "running", "crouched_movement", "kneeling", "low_profile"]
# The AT4 sheet's real content (its manifest labels are wrong).
AT4_POSES = ["aim_stand", "aim_crouch", "aim_kneel", "carry_stand", "carry_walk", "carry_run"]
# id -> (pack folder, display name, facing per cell (in sheet order), reference pose for the 1.8 m height)
# Facing = the direction the figure looks / moves in, judged per pose by eye.  "L" poses are mirrored.
INFANTRY = [
    ("rifleman", "Army_Infantry_Rifleman", "Infantry Rifleman", "RRRRRR", "stand"),
    ("saw_gunner", "Army_M249_SAW_Gunner", "M249 SAW Gunner", "RRRRRR", "stand"),
    ("m240_gunner", "Army_M240B_Gunner", "M240B Machine Gunner", "RRRRRR", "stand"),
    ("at4", "Army_AT4_AntiArmor", "AT4 Anti-Armor", "RRRRRR", "carry_stand"),
    ("eod_engineer", "Army_EOD_Engineer", "EOD Engineer", "LLLLLL", "stand"),
    ("sniper", "Army_Sniper_Ghillie", "Sniper (Ghillie)", "RRRRRR", "stand"),
    ("ranger", "75th_Ranger_Rifleman", "Ranger Rifleman", "RRRRRL", "stand"),
    ("medic", "Army_Medic", "Combat Medic", "RRRRRR", "stand"),
    ("special_forces", "Army_Special_Forces", "Special Forces Operator", "RRRRRR", "stand"),
    ("pilot_helmet", "USAF_Pilot_Helmet", "Pilot (helmet)", "RRRRRR", "stand"),
    ("pilot", "USAF_Pilot_No_Helmet", "Pilot", "RRRLRR", "stand"),
    ("flightline", "USAF_Flightline_Support", "Flightline Crew", "RRRRRR", "stand"),
]
STAND_HEIGHT_M = 1.8


# ----------------------------------------------------------------------------------------------- helpers
def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def open_intact(p):
    try:
        im = Image.open(p)
        im.load()
        return im.convert("RGBA")
    except Exception:
        return None


def load_sheet(pack, sheet_rel, cells):
    """Return (RGBA sheet, source record).  `cells` = {label: (x, y, crop_rel)}; used to rebuild a truncated
    sheet from its crops (verified elsewhere to be exact cell copies)."""
    sp = os.path.join(pack, sheet_rel)
    im = open_intact(sp)
    rec = {"pack": os.path.basename(os.path.dirname(pack.rstrip("/"))) or os.path.basename(pack),
           "sheet": sheet_rel, "sheet_sha256": sha(sp) if os.path.exists(sp) else None}
    if im is not None:
        rec["method"] = "contact_sheet"
        return im, rec
    W = max(x for x, y, _ in cells.values()) + (QUAD_W if len(cells) == 4 else 512)
    H = max(y for x, y, _ in cells.values()) + (QUAD_H if len(cells) == 4 else 512)
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rec["method"] = "sheet_truncated_rebuilt_from_cell_crops"
    rec["crops"] = {}
    for lab, (x, y, crel) in cells.items():
        cp = os.path.join(pack, crel)
        c = open_intact(cp)
        if c is None:
            raise SystemExit(f"cannot rebuild {sheet_rel}: crop {crel} also unreadable")
        sheet.paste(c, (x, y))
        rec["crops"][lab] = {"file": crel, "sha256": sha(cp)}
    return sheet, rec


def _component(a, mask, box, dilate):
    if dilate:
        grown = ndimage.binary_dilation(mask, structure=np.ones((3, 3), bool), iterations=dilate)
    else:
        grown = mask
    lab, n = ndimage.label(grown)
    x0, y0, x1, y1 = box
    sub = lab[y0:y1, x0:x1][mask[y0:y1, x0:x1]]
    counts = np.bincount(sub, minlength=n + 1)
    counts[0] = 0
    best = int(np.argmax(counts))
    keep = (lab == best) & (a > 0)
    ys, xs = np.nonzero(keep)
    inside = ((xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)).mean()
    return keep, counts, best, inside


def cut(sheet, box, dilate=4):
    """Largest connected silhouette of `box` (x0,y0,x1,y1) in `sheet`; may extend outside the box.
    If that component spills mostly outside its cell (two views touching), retry with less dilation and as a
    last resort clip it to the cell.  Returns (RGBA image padded by PAD, info)."""
    arr = np.array(sheet)
    a = arr[:, :, 3]
    mask = a > ALPHA_T
    x0, y0, x1, y1 = box
    used = dilate
    clipped = False
    for d in range(dilate, -1, -1):
        keep, counts, best, inside = _component(a, mask, box, d)
        used = d
        if inside >= 0.8:
            break
    else:
        cellm = np.zeros_like(mask)
        cellm[y0:y1, x0:x1] = True
        keep &= cellm
        clipped = True
        inside = 1.0
    ys, xs = np.nonzero(keep)
    out = arr.copy()
    out[~keep] = 0
    bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    crop = out[by0:by1, bx0:bx1]
    h, w = crop.shape[:2]
    canvas = np.zeros((h + 2 * PAD, w + 2 * PAD, 4), np.uint8)
    canvas[PAD:PAD + h, PAD:PAD + w] = crop
    im = Image.fromarray(canvas)
    if max(im.size) > 1024:
        s = 1024 / max(im.size)
        im = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    # other (dropped) components inside the cell = stray fragments
    dropped = int(sum(1 for i in np.nonzero(counts)[0] if i != best))
    info = {"bbox_in_sheet": [int(bx0), int(by0), int(bx1), int(by1)], "fraction_inside_cell": round(float(inside), 4),
            "dilation_px": used, "clipped_to_cell": clipped,
            "dropped_fragments_in_cell": dropped, "touches_sheet_edge": bool(bx0 == 0 or by0 == 0 or
                                                                           bx1 == arr.shape[1] or by1 == arr.shape[0])}
    return im, info


def edge_flags(cuts):
    """Flag views whose silhouette touches the contact-sheet border (subject cut off in the source art)."""
    return [f"source_clipped_at_sheet_edge:{v}" for v, c in cuts.items() if c["touches_sheet_edge"]]


def fit_icon(im, w=256, h=160, margin=6):
    im = im.crop(im.getbbox())
    s = min((w - 2 * margin) / im.size[0], (h - 2 * margin) / im.size[1])
    im = im.resize((max(1, round(im.size[0] * s)), max(1, round(im.size[1] * s))), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(im, ((w - im.size[0]) // 2, (h - im.size[1]) // 2), im)
    return out


def save(im, *parts):
    p = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p, optimize=False)
    return f"{RES}/" + "/".join(parts)


def row_extents(alpha):
    m = alpha > ALPHA_T
    rows = m.any(1)
    left = np.where(rows, m.argmax(1), -1)
    right = np.where(rows, m.shape[1] - 1 - m[:, ::-1].argmax(1), -1)
    return rows, left, right


def base_anchor(im):
    """Estimate the ground footprint of a building drawn in a steep 3/4 view.
    The base slab's left/right edges stay visible along the whole footprint depth, so the contiguous band of
    rows around the widest row whose silhouette width is >= 80 % of that maximum is taken as the footprint
    depth (80 % tolerates the renders' perspective, which widens the front edge).  anchor = middle row of the
    band, horizontal centre of the silhouette there; base width = silhouette width at that row (median of the
    middle rows).  A heuristic: verified visually in docs/screens/import_buildings.png."""
    a = np.array(im)[:, :, 3]
    rows, left, right = row_extents(a)
    width = np.where(rows, right - left + 1, 0)
    wmax = width.max()
    i = int(np.argmax(width))
    ok = width >= 0.8 * wmax
    y0 = i
    while y0 > 0 and ok[y0 - 1]:
        y0 -= 1
    y1 = i
    while y1 < len(ok) - 1 and ok[y1 + 1]:
        y1 += 1
    y_mid = (y0 + y1) // 2
    mid = slice(max(y0, y_mid - 3), min(y1, y_mid + 3) + 1)
    cx = int(round(np.median((left[mid] + right[mid]) / 2)))
    bw = int(round(np.median(width[mid])))
    return [cx, int(y_mid)], bw, [int(y0), int(y1)]


def hull_length_px(top):
    """Nose-up top sprite: rows wider than 35 % of the widest row = hull (drops barrels/booms/antennas)."""
    a = np.array(top)[:, :, 3]
    rows, left, right = row_extents(a)
    width = np.where(rows, right - left + 1, 0)
    r = np.nonzero(width >= 0.35 * width.max())[0]
    return int(r.max() - r.min() + 1)


# ----------------------------------------------------------------------------------------------- buildings
def do_buildings(pack):
    res = {}
    for bid, folder, name in BUILDINGS:
        cells = {v: (x, y, f"individual_views/{folder}/{folder}_{v}.png") for v, (x, y) in QUAD_VIEWS.items()}
        sheet, src = load_sheet(pack, f"contact_sheets/{folder}_4view.png", cells)
        views = {}
        cuts = {}
        for v in ("overhead", "front_three_quarter"):
            x, y = QUAD_VIEWS[v]
            views[v], cuts[v] = cut(sheet, (x, y, x + QUAD_W, y + QUAD_H))
        main = views["overhead"]
        anchor, base_w, band = base_anchor(main)
        flags = [DEV]
        if bid == "field_hospital":
            flags.append(RED_CROSS)
        src["cuts"] = cuts
        flags += edge_flags(cuts)
        res[bid] = {
            "name": name,
            "main": save(main, "buildings", bid, f"{bid}_main.png"),
            "front": save(views["front_three_quarter"], "buildings", bid, f"{bid}_front.png"),
            "icon": save(fit_icon(views["front_three_quarter"]), "buildings", bid, f"{bid}_icon.png"),
            "main_px": list(main.size), "anchor_px": anchor, "base_width_px": base_w,
            "source": src, "flags": flags,
        }
        res[bid]["_band"] = band
        print(f"building {bid:18s} main {main.size} anchor {anchor} base_w {base_w} src {src['method']} "
              f"inside {cuts['overhead']['fraction_inside_cell']}/{cuts['front_three_quarter']['fraction_inside_cell']}")
    return res


# ----------------------------------------------------------------------------------------------- vehicles
def do_vehicles(pack):
    res = {}
    for vid, folder, name, length, nose, (f34, fside, r34) in VEHICLES:
        cells = {v: (x, y, f"individual_views/{folder}/{folder}_{v}.png") for v, (x, y) in QUAD_VIEWS.items()}
        sheet, src = load_sheet(pack, f"contact_sheets/{folder}_4view.png", cells)
        views, cuts = {}, {}
        for v, (x, y) in QUAD_VIEWS.items():
            views[v], cuts[v] = cut(sheet, (x, y, x + QUAD_W, y + QUAD_H))
        top = views["overhead"].rotate(ROT_TO_UP[nose], expand=True)
        flags = [DEV, TM]
        if vid == "hmmwv_medical":
            flags.append(RED_CROSS)
        src["cuts"] = cuts
        flags += edge_flags(cuts)
        res[vid] = {
            "name": name,
            "top": save(top, "vehicles", vid, f"{vid}_top.png"),
            "front34": {"path": save(views["front_three_quarter"], "vehicles", vid, f"{vid}_front34.png"), "faces": f34},
            "side": {"path": save(views["side_profile"], "vehicles", vid, f"{vid}_side.png"), "faces": fside},
            "rear34": {"path": save(views["rear_three_quarter"], "vehicles", vid, f"{vid}_rear34.png"), "faces": r34},
            "icon": save(fit_icon(views["front_three_quarter"]), "vehicles", vid, f"{vid}_icon.png"),
            "length_m": length,
            "source_nose_direction": nose,
            # extra (not required by the loader): top sprite size and the nose-to-tail hull extent in px
            # (barrels / booms / trails excluded) so the game can scale the hull, not the gun, to length_m.
            "top_px": list(top.size),
            "top_hull_length_px": hull_length_px(top),
            "flags": flags,
            "source": src,
        }
        print(f"vehicle {vid:14s} top {top.size} hull_px {res[vid]['top_hull_length_px']} "
              f"inside {[cuts[v]['fraction_inside_cell'] for v in QUAD_VIEWS]}")
    return res


# ----------------------------------------------------------------------------------------------- infantry
def head_torso_icon(stand):
    a = np.array(stand)[:, :, 3]
    ys, xs = np.nonzero(a > ALPHA_T)
    top, bot = ys.min(), ys.max()
    h = bot - top + 1
    crop_h = int(round(h * 0.42))
    head_rows = a[top:top + int(h * 0.12)] > ALPHA_T
    hx = int(round(np.nonzero(head_rows)[1].mean()))
    crop_w = int(round(crop_h * 1.6))
    x0 = hx - crop_w // 2
    box = (x0, top - 4, x0 + crop_w, top - 4 + crop_h)
    c = Image.new("RGBA", (crop_w, crop_h), (0, 0, 0, 0))
    c.paste(stand.crop(box), (0, 0))
    return c.resize((256, 160), Image.LANCZOS)


def do_infantry(pack):
    res = {}
    for iid, folder, name, facing, ref in INFANTRY:
        poses = AT4_POSES if iid == "at4" else STD_POSES
        cells = {STD_LABELS[i]: (x, y, f"individual_poses/{folder}/{folder}_{STD_LABELS[i]}.png")
                 for i, (x, y) in enumerate(POSE_CELLS)}
        sheet, src = load_sheet(pack, f"contact_sheets/{folder}_6pose_sheet.png", cells)
        ims, cuts, heights = {}, {}, {}
        for i, (x, y) in enumerate(POSE_CELLS):
            im, info = cut(sheet, (x, y, x + 512, y + 512))
            info["source_facing"] = "left" if facing[i] == "L" else "right"
            info["mirrored"] = facing[i] == "L"
            info["manifest_label"] = STD_LABELS[i]
            if facing[i] == "L":
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            ims[poses[i]] = im
            cuts[poses[i]] = info
            heights[poses[i]] = im.size[1] - 2 * PAD
        px_per_m = round(heights[ref] / STAND_HEIGHT_M, 3)
        flags = [DEV]
        if iid == "medic":
            flags.append(RED_CROSS)
        if iid == "at4":
            flags.append("at4_manifest_labels_corrected_from_sheet_content")
        src["cuts"] = cuts
        flags += edge_flags(cuts)
        res[iid] = {
            "name": name,
            "poses": {p: save(ims[p], "infantry", iid, f"{iid}_{p}.png") for p in poses},
            "icon": save(head_torso_icon(ims["carry_stand" if iid == "at4" else "stand"]), "infantry", iid, f"{iid}_icon.png"),
            "px_per_m": px_per_m,
            "flags": flags,
            "source": src,
        }
        print(f"infantry {iid:15s} px_per_m {px_per_m} heights {heights}")
    return res


# ----------------------------------------------------------------------------------------------- rotors
# Existing nose-up top sprites from tools/import_aircraft.py.  Per hub: approximate hub position and the screen
# angles (deg, image coords, 0 = +x, y down) of the blades that are actually drawn, read off the sprites.
# Hub positions are then refined as the least-squares intersection of the fitted blade centre lines.
ROTORS = {
    "ah64": [((381, 341), [44, 138, 227, 313])],
    "uh60": [((315, 255), [38, 139, 217, 322])],
    "ch47": [((305, 141), [38, 141]), ((305, 477), [33, 146])],
}


def split_rotor(a, hubs_cfg):
    """Return body RGBA, list of per-hub blade RGBA, refined hubs, per-blade info, residual note data.
    Blades are modelled as straight bars from the hub (fitted from blade pixels > 110 px from the hub, so the
    fuselage does not bias the fit).  Blade-bar pixels become transparent in the body EXCEPT where fuselage lies
    under the blade (fuselage on both sides of the bar, or inside the closed body silhouette near the hub): those
    pixels are kept as drawn (nothing is painted), so blade roots that cross the airframe remain in the body."""
    al = a[:, :, 3] > ALPHA_T
    H, W = al.shape
    ys, xs = np.nonzero(al)
    YY, XX = np.mgrid[0:H, 0:W]
    bars, hubs, info = [], [], []
    for hi, ((gx, gy), angs) in enumerate(hubs_cfg):
        lines = []
        r = np.hypot(xs - gx, ys - gy)
        ang = (np.degrees(np.arctan2(ys - gy, xs - gx)) + 360) % 360
        for A in angs:
            s = (np.abs((ang - A + 180) % 360 - 180) < 9) & (r > 110)
            for oj, ((ox, oy), _) in enumerate(hubs_cfg):
                if oj != hi:
                    s &= np.hypot(xs - ox, ys - oy) > r
            P = np.c_[xs[s], ys[s]].astype(float)
            m = P.mean(0)
            v = np.linalg.svd(P - m, full_matrices=False)[2][0]
            lines.append((m, v, P))
        M = np.zeros((2, 2)); b = np.zeros(2)
        for m, v, P in lines:
            nrm = np.eye(2) - np.outer(v, v); M += nrm; b += nrm @ m
        hub = np.linalg.solve(M, b)
        hubs.append(hub)
        hub_bars = []
        for m, v, P in lines:
            if np.dot(m - hub, v) < 0:
                v = -v
            nv = np.array([-v[1], v[0]])
            w = 2 * np.percentile(np.abs((P - hub) @ nv), 97)
            tip = ((P - hub) @ v).max()
            t = (XX - hub[0]) * v[0] + (YY - hub[1]) * v[1]
            p = (XX - hub[0]) * nv[0] + (YY - hub[1]) * nv[1]
            bar = (t > -0.3 * w) & (t < tip + 4) & (np.abs(p) <= w / 2 + 2)
            hub_bars.append((bar, nv, w))
            info.append({"hub": hi, "angle_deg": round(float(np.degrees(np.arctan2(v[1], v[0]))), 1),
                         "width_px": round(float(w), 1), "length_px": round(float(tip), 1)})
        wm = float(np.mean([x[2] for x in hub_bars]))
        disc = np.hypot(XX - hub[0], YY - hub[1]) <= 0.9 * wm
        bars.append((hub_bars, disc, hub, wm))
    blade_any = np.zeros_like(al)
    for hub_bars, disc, _, _ in bars:
        blade_any |= disc
        for bar, _, _ in hub_bars:
            blade_any |= bar
    blade_any &= al
    body0 = al & ~blade_any
    b1 = ndimage.binary_dilation(body0, iterations=1)
    keep = np.zeros_like(al)
    for hub_bars, disc, hub, wm in bars:
        # near the hub several bars overlap: use the closed body silhouette there
        rad = int(round(wm * 1.3))
        st = np.hypot(*np.mgrid[-rad:rad + 1, -rad:rad + 1]) <= rad
        closed = ndimage.binary_closing(np.pad(body0, rad + 2), structure=st)[rad + 2:-rad - 2, rad + 2:-rad - 2]
        near = np.hypot(XX - hub[0], YY - hub[1]) <= 2.2 * wm
        keep |= blade_any & closed & near
        # fuselage-edge notches where a bar crosses the outline: small closing everywhere
        r2 = int(round(wm * 0.6))
        st2 = np.hypot(*np.mgrid[-r2:r2 + 1, -r2:r2 + 1]) <= r2
        keep |= blade_any & ndimage.binary_closing(np.pad(body0, r2 + 2), structure=st2)[r2 + 2:-r2 - 2, r2 + 2:-r2 - 2]
        for bar, nv, w in hub_bars:
            yy, xx = np.nonzero(bar & al)
            off = w / 2 + 4
            ok = np.ones(len(yy), bool)
            for sg in (1, -1):
                qx = np.clip(np.round(xx + sg * off * nv[0]).astype(int), 0, W - 1)
                qy = np.clip(np.round(yy + sg * off * nv[1]).astype(int), 0, H - 1)
                ok &= b1[qy, qx]
            keep[yy[ok], xx[ok]] = True
    bodym = body0 | (blade_any & keep)
    lab, n = ndimage.label(ndimage.binary_dilation(bodym, iterations=2))
    cnt = np.bincount(lab[bodym], minlength=n + 1); cnt[0] = 0
    bodym &= lab == int(np.argmax(cnt))
    soft = (a[:, :, 3] > 0) & ~al      # anti-aliased fringe: follow whichever layer it touches
    body = a.copy()
    body[~(bodym | (soft & ndimage.binary_dilation(bodym, iterations=2)))] = 0
    layers = []
    for hi, (hub_bars, disc, hub, wm) in enumerate(bars):
        m = disc.copy()
        for bar, _, _ in hub_bars:
            m |= bar
        m &= al
        # pixels claimed by another hub's bars go to the nearer hub
        for oj, (_, _, oh, _) in enumerate(bars):
            if oj != hi:
                m &= np.hypot(XX - hub[0], YY - hub[1]) <= np.hypot(XX - oh[0], YY - oh[1])
        lay = a.copy()
        lay[~(m | (soft & ndimage.binary_dilation(m, iterations=2) & ~bodym))] = 0
        layers.append(lay)
    kept_px = int((blade_any & keep).sum())
    return body, layers, hubs, info, kept_px, int(blade_any.sum())


ROTOR_NOTES = {
    "ah64": "4-blade main rotor split. Blade roots that lie over the fuselage, stub wings and hub are kept in the "
            "body as drawn (no repainting); tail rotor left in the body.",
    "uh60": "4-blade main rotor split. Blade roots over the cabin roof stay in the body as drawn (no repainting); "
            "tail rotor left in the body.",
    "ch47": "Tandem rotors: blades contains both rotors; blades_front/blades_rear (extra files, same canvas) hold "
            "each rotor alone so they can spin about their own hub (counter-rotating). The source draws only TWO "
            "blades per rotor clear of the fuselage (~100 deg apart, not 3 at 120 deg). The rear rotor's third blade "
            "is painted along the fuselage spine and the front rotor's third blade is not drawn at all; the spine "
            "blade cannot be removed without repainting the fuselage, so it stays baked into the body and will be "
            "visible as a static blade under the spinning rotor. Use split only with that caveat, or fall back to "
            "the unsplit top sprite.",
}


def do_rotors():
    res = {}
    for rid, cfg in ROTORS.items():
        src = os.path.join(AIRCRAFT, rid, f"{rid}_top.png")
        a = np.array(Image.open(src).convert("RGBA"))
        body, layers, hubs, info, kept, total = split_rotor(a, cfg)
        blades = np.zeros_like(a)
        for lay in layers:
            blades = np.where(lay[:, :, 3:4] > blades[:, :, 3:4], lay, blades)
        e = {
            "body": save(Image.fromarray(body), "rotors", f"{rid}_body.png"),
            "blades": save(Image.fromarray(blades), "rotors", f"{rid}_blades.png"),
            "hubs_px": [[round(float(h[0]), 1), round(float(h[1]), 1)] for h in hubs],
            "size_px": [a.shape[1], a.shape[0]],
            "ok": rid != "ch47",
            "notes": ROTOR_NOTES[rid],
            "source": {"file": f"res://assets/aircraft/{rid}/{rid}_top.png", "sha256": sha(src)},
            "blade_fit": info,
            "blade_px_left_in_body": kept, "blade_bar_px": total,
        }
        if len(layers) > 1:
            names = ["front", "rear"]
            e["blades_per_hub"] = [save(Image.fromarray(l), "rotors", f"{rid}_blades_{names[i]}.png")
                                   for i, l in enumerate(layers)]
        res[rid] = e
        print(f"rotor {rid}: hubs {e['hubs_px']} blades {[(b['angle_deg'], b['width_px'], b['length_px']) for b in info]}"
              f" blade px kept in body {kept}/{total}")
    return res


def preview_rotors(r, font):
    tiles = []
    for rid, e in r.items():
        body = asset(e["body"])
        layers = [asset(p) for p in e.get("blades_per_hub", [e["blades"]])]
        comb = body.copy()
        for lay, h in zip(layers, e["hubs_px"]):
            comb.alpha_composite(lay.rotate(30, center=tuple(h), resample=Image.BICUBIC))

        def mk(d, P, s, hubs=e["hubs_px"]):
            for hx, hy in hubs:
                x, y = P(hx, hy)
                d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(255, 40, 40, 255), width=2)
        tiles.append(tile(body, (420, 440), f"{rid} body", font, [mk]))
        tiles.append(tile(asset(e["blades"]), (420, 440), f"{rid} blades", font, [mk]))
        tiles.append(tile(comb, (420, 440), f"{rid} body+blades @30deg", font, [mk]))
    grid(tiles, 3, os.path.join(SCREENS, "import_rotors.png"))


# ----------------------------------------------------------------------------------------------- previews
GREEN = (88, 128, 72, 255)


def label_font():
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, 14)
    return ImageFont.load_default()


def tile(im, size, label, font, marks=None, scale=None, bottom=False):
    """Composite `im` scaled to fit `size` on mid-green with a label. marks: list of draw callbacks in im px."""
    W, H = size
    t = Image.new("RGBA", (W, H), GREEN)
    s = scale if scale else min((W - 8) / im.size[0], (H - 26) / im.size[1], 1.0)
    sc = im.resize((max(1, round(im.size[0] * s)), max(1, round(im.size[1] * s))), Image.LANCZOS)
    ox, oy = (W - sc.size[0]) // 2, 22 + (H - 22 - sc.size[1]) // 2
    if bottom:   # feet on a common ground line
        oy = H - 6 - sc.size[1]
    t.alpha_composite(sc, (ox, oy))
    d = ImageDraw.Draw(t)
    if marks:
        for m in marks:
            m(d, lambda x, y: (ox + x * s, oy + y * s), s)
    d.rectangle([0, 0, W - 1, H - 1], outline=(40, 60, 30, 255))
    d.text((5, 3), label, fill=(255, 255, 255, 255), font=font)
    return t


def grid(tiles, cols, path):
    W, H = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    M = Image.new("RGBA", (W * cols, H * rows), (30, 40, 25, 255))
    for i, t in enumerate(tiles):
        M.paste(t, ((i % cols) * W, (i // cols) * H))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    M.convert("RGB").save(path)


def asset(res_path):
    return Image.open(os.path.join(OUT, res_path[len(RES) + 1:])).convert("RGBA")


def preview_buildings(b, font):
    tiles = []
    for bid, e in b.items():
        ax, ay = e["anchor_px"]
        bw = e["base_width_px"]
        y0, y1 = e["_band"]

        def mk(d, P, s, ax=ax, ay=ay, bw=bw, y0=y0, y1=y1):
            x, y = P(ax, ay)
            d.line([P(ax - bw / 2, ay), P(ax + bw / 2, ay)], fill=(255, 60, 60, 255), width=2)
            d.line([P(ax - bw / 2, y0), P(ax - bw / 2, y1)], fill=(255, 220, 0, 255), width=1)
            d.line([P(ax + bw / 2, y0), P(ax + bw / 2, y1)], fill=(255, 220, 0, 255), width=1)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 60, 60, 255))
        tiles.append(tile(asset(e["main"]), (330, 300), f"{bid} main (anchor/base)", font, [mk]))
        tiles.append(tile(asset(e["front"]), (330, 300), f"{bid} front", font))
        tiles.append(tile(asset(e["icon"]), (330, 300), f"{bid} icon", font))
    # 2 buildings per row
    grid(tiles, 6, os.path.join(SCREENS, "import_buildings.png"))


def preview_vehicles(v, font):
    tiles = []
    for vid, e in v.items():
        tiles.append(tile(asset(e["top"]), (300, 300), f"{vid} top", font))
        tiles.append(tile(asset(e["front34"]["path"]), (300, 300), f"front34 ->{e['front34']['faces']}", font))
        tiles.append(tile(asset(e["side"]["path"]), (300, 300), f"side ->{e['side']['faces']}", font))
        tiles.append(tile(asset(e["rear34"]["path"]), (300, 300), f"rear34 ->{e['rear34']['faces']}", font))
        tiles.append(tile(asset(e["icon"]), (300, 300), f"{vid} icon", font))
    grid(tiles, 5, os.path.join(SCREENS, "import_vehicles.png"))


def preview_infantry(inf, font):
    tiles = []
    for iid, e in inf.items():
        ppm = e["px_per_m"]
        ims = {p: asset(rp) for p, rp in e["poses"].items()}
        rs = min(min(182 / im.size[0], 212 / im.size[1]) for im in ims.values())   # one scale per role
        for p, im in ims.items():

            def mk(d, P, s, h=im.size[1], ppm=ppm):   # 1.8 m reference bar from the feet line
                d.line([P(4, h - PAD), P(4, h - PAD - 1.8 * ppm)], fill=(255, 220, 0, 255), width=2)
            tiles.append(tile(im, (190, 240), f"{iid} {p}", font, [mk], scale=rs, bottom=True))
        tiles.append(tile(asset(e["icon"]), (190, 240), f"{iid} icon", font))
    grid(tiles, 7, os.path.join(SCREENS, "import_infantry.png"))


# ----------------------------------------------------------------------------------------------- main
def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    inst, ground, pers = (os.path.abspath(p) for p in argv[1:])
    font = label_font()
    b = do_buildings(inst)
    v = do_vehicles(ground)
    inf = do_infantry(pers)
    r = do_rotors()
    preview_buildings(b, font)
    preview_vehicles(v, font)
    preview_infantry(inf, font)
    if r:
        preview_rotors(r, font)
    for e in b.values():
        e.pop("_band", None)
    man = {"_about": "Steel Accord - U.S. concept-pack sprites (AI-generated, client-supplied, DEV ONLY). "
                     "Generated by tools/import_us_packs.py; do not edit by hand.",
           "buildings": b, "vehicles": v, "infantry": inf, "rotors": r}
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w") as f:
        json.dump(man, f, indent=1, sort_keys=False)
        f.write("\n")
    print("wrote", MANIFEST)


if __name__ == "__main__":
    main(sys.argv)

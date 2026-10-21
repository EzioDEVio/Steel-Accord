#!/usr/bin/env python3
"""Generate 'Harbor Divide' — the first original 2-player map (B1 map per client directive).

Fictional industrial harbour. A north–south tidal channel splits the map.
  * Starts on raised west/east quays, point-symmetric (x,y) -> (1-x, 1-y)
  * Three crossings: wide centre causeway (contested), narrow north and south causeways
  * Each base: 2 safe supply docks; each side of the channel: 1 forward supply warehouse
  * Contested: 2 oil derricks beside the north/south crossings
  * Water: one engine water polygon over the channel; ground units cross only on causeways
Also runs a passability/fairness check (BFS on 10 ft cells: slope + water) and writes a report.

Outputs: maps/PZ_HarborDivide/{PZ_HarborDivide.map,.tga,map.ini,map.str}, terrain mud texture,
         build/previews/harbordivide_{blockout,paths}.png, build/reports/harbordivide_fairness.txt
"""
import math, os, sys, shutil
from collections import deque
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga, mapformat as M
from pzlib.datachunk import DICT_BOOL, DICT_INT, DICT_ASCII, DICT_UNICODE
from gen_kestrel import noise
import gen_testrange_map as TR

NAME = "PZ_HarborDivide"
MAPDIR = os.path.join(ROOT, "maps", NAME)
TERR = os.path.join(ROOT, "content", "dev", "Art", "Terrain")
PREV = os.path.join(ROOT, "build", "previews"); REP = os.path.join(ROOT, "build", "reports")
for d in (MAPDIR, TERR, PREV, REP):
    os.makedirs(d, exist_ok=True)

PLAY, BORDER = 300, 24
W = H = PLAY + 2 * BORDER
XY, HSCALE = 10.0, 0.625
LAND, QUAY, BED, CAUSE = 70, 80, 18, 62          # height units (x0.625 ft)
WATER_FT = 34                                      # water surface (ft) -> above BED, below CAUSE*0.625=38.75
CH_HALF = 0.075                                    # channel half-width (normalized)
STARTS = ((0.12, 0.30), (0.88, 0.70))
CROSSINGS = ((0.50, 0.040), (0.83, 0.018), (0.17, 0.018))   # (y, half-width) centre wide, north/south narrow
SUPPLIES = [   # listed as mirrored pairs (P1 side, P2 side)
    ("SupplyDock", 0.10, 0.12), ("SupplyDock", 0.90, 0.88),            # safe dock A
    ("SupplyDock", 0.26, 0.20), ("SupplyDock", 0.74, 0.80),            # safe dock B
    ("SupplyWarehouse", 0.33, 0.50), ("SupplyWarehouse", 0.67, 0.50),  # forward, each bank
    ("TechOilDerrick", 0.38, 0.86), ("TechOilDerrick", 0.62, 0.14),    # contested by crossings
]


def mirror(p): return (1 - p[0], 1 - p[1])


def mud_texture():
    S = 128
    n = noise(S, S, 5, seed=61); f = noise(S, S, 28, seed=62)
    img = np.array([0.30, 0.29, 0.25]) * (0.85 + 0.35 * (n[..., None] - 0.5) + 0.25 * (f[..., None] - 0.5))
    tga.save(os.path.join(TERR, "pzdev_mud.tga"), (np.clip(img, 0, 1) * 255).astype(np.uint8))


def heightfield():
    ys, xs = np.mgrid[0:H, 0:W].astype(float)
    px, py = (xs - BORDER) / PLAY, (ys - BORDER) / PLAY
    h = np.full((H, W), float(LAND))
    h += 4 * (noise(H, W, 6, seed=71) - 0.5)
    dx = np.abs(px - 0.5)
    # channel with sloped revetments (~0.03 wide)
    bank = np.clip((dx - CH_HALF) / 0.03, 0, 1)
    h = BED * (1 - bank) + h * bank
    # causeways across the channel (flat deck, ramped onto the banks)
    for cy, hw in CROSSINGS:
        on = np.clip(1 - (np.abs(py - cy) - hw) / 0.008, 0, 1) * (dx < CH_HALF + 0.04)
        h = h * (1 - on) + np.maximum(h, CAUSE) * on
    # quays: raised flat start platforms with ramps
    for s in STARTS:
        r = np.hypot(px - s[0], py - s[1])
        pad = np.clip(1 - (r - 0.10) / 0.05, 0, 1)
        h = h * (1 - pad) + QUAY * pad
    for _, sx, sy in SUPPLIES:
        r = np.hypot(px - sx, py - sy)
        w = np.clip(1 - (r - 0.022) / 0.025, 0, 1)
        cx, cy = int(round(BORDER + sx * PLAY)), int(round(BORDER + sy * PLAY))
        h = h * (1 - w) + h[cy, cx] * w
    h = np.clip(np.round(h), 2, 250).astype(np.uint8)
    # texture classes: 0 gravel, 1 concrete, 2 mud
    cls = np.zeros((H, W), np.int8)
    cls[dx < CH_HALF + 0.03] = 2
    for cy, hw in CROSSINGS:
        cls[(np.abs(py - cy) < hw + 0.004) & (dx < CH_HALF + 0.05)] = 1
    for s in STARTS:
        cls[np.hypot(px - s[0], py - s[1]) < 0.11] = 1
    for _, sx, sy in SUPPLIES:
        cls[np.hypot(px - sx, py - sy) < 0.022] = 1
    # quay edge strips along the channel (dockside concrete)
    cls[(np.abs(dx - (CH_HALF + 0.045)) < 0.008)] = 1
    return h, cls, px, py


def passability(h, px, py):
    """Cell (between vertices) is ground-passable if above water and slope <= 35 degrees."""
    z = h.astype(float) * HSCALE
    cz = (z[:-1, :-1] + z[1:, :-1] + z[:-1, 1:] + z[1:, 1:]) / 4
    span = np.maximum.reduce([z[:-1, :-1], z[1:, :-1], z[:-1, 1:], z[1:, 1:]]) - \
        np.minimum.reduce([z[:-1, :-1], z[1:, :-1], z[:-1, 1:], z[1:, 1:]])
    slope_ok = np.degrees(np.arctan(span / XY)) <= 35
    in_channel = (np.abs(px[:-1, :-1] - 0.5) < CH_HALF + 0.02)
    dry = ~((cz < WATER_FT) & in_channel)
    ok = slope_ok & dry
    ok[:BORDER] = ok[-BORDER:] = False; ok[:, :BORDER] = ok[:, -BORDER:] = False
    return ok


def bfs(ok, start):
    dist = np.full(ok.shape, -1, np.int32)
    q = deque([start]); dist[start] = 0
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < ok.shape[0] and 0 <= nx < ok.shape[1] and ok[ny, nx] and dist[ny, nx] < 0:
                dist[ny, nx] = dist[y, x] + 1; q.append((ny, nx))
    return dist


def cell(p): return (int(BORDER + p[1] * PLAY), int(BORDER + p[0] * PLAY))


def build():
    TR.terrain_textures(); mud_texture()
    # symmetry assertions on the design data
    assert all(abs(a - b) < 1e-9 for a, b in zip(mirror(STARTS[0]), STARTS[1]))
    for i in range(0, len(SUPPLIES), 2):
        assert np.allclose(mirror(SUPPLIES[i][1:]), SUPPLIES[i + 1][1:]), SUPPLIES[i]
    h, cls, px, py = heightfield()
    classes = [dict(first=0, num=4, width=2, legacy=0, name="PZDevGravel"),
               dict(first=4, num=4, width=2, legacy=0, name="PZDevConcrete"),
               dict(first=8, num=4, width=2, legacy=0, name="PZDevMud")]
    tiles = []
    for y in range(H):
        for x in range(W):
            c = classes[cls[y, x]]; w = c["width"]
            tiles.append(((c["first"] + (x // 2) % w + w * ((y // 2) % w)) << 2) + (x & 1) + 2 * (y & 1))
    n = W * H
    blend = dict(tiles=tiles, blend=[0] * n, extra=[0] * n, cliff=[0] * n, cliffState=bytes(((W + 7) // 8) * H),
                 numBitmapTiles=12, numBlendedTiles=1, numCliffInfo=1, classes=classes,
                 numEdgeTiles=0, edgeClasses=[], blendedTiles=[], cliffInfo=[])
    L = lambda a, d, p: list(a) + list(d) + list(p)
    key = L((0.36, 0.39, 0.45), (0.95, 0.90, 0.80), (-0.55, 0.45, -0.70))
    fill = L((0, 0, 0), (0.22, 0.26, 0.34), (0.60, -0.40, -0.60))
    off = L((0, 0, 0), (0, 0, 0), (0, 0, -1))
    lighting = M.lighting_blob(2, [dict(terrain=[key, off, off], objects=[key, fill, off])] * 4, 0x7F404858)

    S = lambda v: v * PLAY * XY
    objs = [TR.waypoint(1, "Player_1_Start", S(STARTS[0][0]), S(STARTS[0][1])),
            TR.waypoint(2, "Player_2_Start", S(STARTS[1][0]), S(STARTS[1][1])),
            TR.waypoint(3, "InitialCameraPosition", S(STARTS[0][0]), S(STARTS[0][1]))]
    for i, (t, sx, sy) in enumerate(SUPPLIES):
        objs.append(dict(x=S(sx), y=S(sy), z=0.0, angle=math.atan2(0.5 - sy, 0.5 - sx), flags=0, tmpl=t,
                         props=TR.dict_obj(f"{t} {i + 1}", "team")))
    x0, x1 = int(S(0.5 - CH_HALF - 0.035)), int(S(0.5 + CH_HALF + 0.035))
    y0, y1 = -BORDER * 10, int(S(1.0)) + BORDER * 10
    water = dict(name="HarborChannel", layer="", id=1, water=1, river=0, riverStart=0,
                 pts=[(x0, y0, WATER_FT), (x1, y0, WATER_FT), (x1, y1, WATER_FT), (x0, y1, WATER_FT)])
    m = dict(height=dict(width=W, height=H, border=BORDER, boundaries=[(PLAY, PLAY)], data=h.tobytes()),
             blend=blend, world=[("weather", DICT_INT, 0)],
             sides=[dict(dict=[("playerName", DICT_ASCII, ""), ("playerIsHuman", DICT_BOOL, False),
                               ("playerDisplayName", DICT_UNICODE, "Neutral"), ("playerFaction", DICT_ASCII, ""),
                               ("playerAllies", DICT_ASCII, ""), ("playerEnemies", DICT_ASCII, "")], build=[]),
                    dict(dict=[("playerName", DICT_ASCII, "PlyrCivilian"), ("playerIsHuman", DICT_BOOL, False),
                               ("playerDisplayName", DICT_UNICODE, "Civilian"), ("playerFaction", DICT_ASCII, "FactionCivilian"),
                               ("playerAllies", DICT_ASCII, ""), ("playerEnemies", DICT_ASCII, "")], build=[])],
             teams=[[("teamName", DICT_ASCII, "team"), ("teamOwner", DICT_ASCII, ""), ("teamIsSingleton", DICT_BOOL, True)],
                    [("teamName", DICT_ASCII, "teamPlyrCivilian"), ("teamOwner", DICT_ASCII, "PlyrCivilian"),
                     ("teamIsSingleton", DICT_BOOL, True)]],
             objects=objs, triggers=[water], lighting=lighting, waypointLinks=[])
    data = M.encode(m)
    open(os.path.join(MAPDIR, NAME + ".map"), "wb").write(data)
    assert M.decode(data)["blend"]["tiles"] == tiles

    # ---- pathfinding / fairness report
    ok = passability(h, px, py)
    d1, d2 = bfs(ok, cell(STARTS[0])), bfs(ok, cell(STARTS[1]))
    rep = [f"Harbor Divide fairness report  ({PLAY}x{PLAY} cells = {PLAY * 10} ft, water {WATER_FT} ft)",
           f"passable cells: {ok.sum()} / {ok.size}"]
    rep.append(f"P1 -> P2 shortest ground path: {d1[cell(STARTS[1])] * 10} ft ; P2 -> P1: {d2[cell(STARTS[0])] * 10} ft")
    for i in range(0, len(SUPPLIES), 2):
        a, b = SUPPLIES[i], SUPPLIES[i + 1]
        rep.append(f"{a[0]:16s} own: P1 {d1[cell(a[1:])] * 10:5d} ft  P2 {d2[cell(b[1:])] * 10:5d} ft   "
                   f"enemy's: P1 {d1[cell(b[1:])] * 10:5d}  P2 {d2[cell(a[1:])] * 10:5d}")
    # each crossing must be usable: block the other two and re-path
    for cy, hw in CROSSINGS:
        ok2 = ok.copy()
        for oy, ohw in CROSSINGS:
            if oy != cy:
                r0, r1 = int(BORDER + (oy - ohw - 0.02) * PLAY), int(BORDER + (oy + ohw + 0.02) * PLAY)
                c0, c1 = int(BORDER + (0.5 - CH_HALF) * PLAY), int(BORDER + (0.5 + CH_HALF) * PLAY)
                ok2[r0:r1, c0:c1] = False
        dd = bfs(ok2, cell(STARTS[0]))[cell(STARTS[1])]
        rep.append(f"route via crossing y={cy:.2f}: {'OK ' + str(dd * 10) + ' ft' if dd > 0 else 'BLOCKED'}")
    reach = d1[cell(STARTS[1])] > 0 and all(d1[cell(s[1:])] > 0 for s in SUPPLIES)
    rep.append("RESULT: " + ("PASS (all starts/resources reachable, symmetric)" if reach and
                             d1[cell(STARTS[1])] == d2[cell(STARTS[0])] else "CHECK"))
    open(os.path.join(REP, "harbordivide_fairness.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))

    # ---- previews
    z = h.astype(float)
    gx, gy = np.gradient(z, axis=1), np.gradient(z, axis=0)
    shade = np.clip(0.8 - (gx - gy) * 0.05, 0.35, 1.15)
    pal = np.array([[0.50, 0.44, 0.34], [0.62, 0.62, 0.60], [0.30, 0.29, 0.25]])
    col = pal[cls] * shade[..., None]
    wet = (z * HSCALE < WATER_FT) & (np.abs(px - 0.5) < CH_HALF + 0.03)
    col[wet] = col[wet] * 0.35 + np.array([0.10, 0.30, 0.42]) * 0.65
    img = Image.fromarray((np.clip(col[::-1], 0, 1) * 255).astype(np.uint8)).resize((600, 600), Image.NEAREST)
    d = ImageDraw.Draw(img); k = 600 / W
    P = lambda p: ((BORDER + p[0] * PLAY) * k, 600 - (BORDER + p[1] * PLAY) * k)
    d.rectangle([BORDER * k, BORDER * k, (W - BORDER) * k, (H - BORDER) * k], outline=(255, 255, 255))
    for t, sx, sy in SUPPLIES:
        cx, cy = P((sx, sy)); c = (255, 200, 60) if t == "TechOilDerrick" else (90, 200, 255)
        d.rectangle([cx - 6, cy - 6, cx + 6, cy + 6], fill=c, outline=(10, 20, 30))
    for i, s in enumerate(STARTS):
        cx, cy = P(s); d.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=(255, 230, 90), width=3)
        d.text((cx + 14, cy - 6), f"P{i + 1}", fill=(255, 240, 150))
    img.save(os.path.join(PREV, "harbordivide_blockout.png"))
    tga.save(os.path.join(MAPDIR, NAME + ".tga"), np.asarray(img.resize((128, 128), Image.BILINEAR).convert("RGBA")))
    # path heat map from P1
    heat = np.where(d1 >= 0, d1 / max(1, d1.max()), -1)
    hc = np.zeros(heat.shape + (3,)); hc[heat < 0] = (0.15, 0.05, 0.05)
    v = heat >= 0; hc[v] = np.stack([heat[v], 1 - heat[v], 0.3 + 0 * heat[v]], -1)
    Image.fromarray((hc[::-1] * 255).astype(np.uint8)).resize((600, 600), Image.NEAREST).save(
        os.path.join(PREV, "harbordivide_paths.png"))

    # map-scoped files: same B1 hook as the test range
    shutil.copy(os.path.join(ROOT, "maps", "PZ_TestRange", "map.ini"), os.path.join(MAPDIR, "map.ini"))
    shutil.copy(os.path.join(ROOT, "maps", "PZ_TestRange", "map.str"), os.path.join(MAPDIR, "map.str"))


if __name__ == "__main__":
    build()

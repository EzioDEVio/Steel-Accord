#!/usr/bin/env python3
"""Generate the original B1.1 test map 'PZ Test Range' (2 players) and its terrain textures.

Layout (playable 128x128 cells = 1280 ft, 16-cell border):
  * two raised concrete start pads in opposite corners (Player_1_Start SW, Player_2_Start NE)
  * a low gravel basin across the centre with a raised berm, crossed by two ramps
  * a concrete causeway through the middle (contested lane) and two flank lanes
  * symmetric under 180-degree rotation, so both starts are equidistant from every feature
No supplies yet (B1.1 only proves the unit loop; skirmish starting cash funds it).

Outputs:
  content/dev/Art/Terrain/pzdev_concrete.tga, pzdev_gravel.tga   (128x128, 2x2 tiles)
  maps/PZ_TestRange/PZ_TestRange.map (+ .tga preview, map.str written by build script)
  build/previews/testrange_*.png
"""
import math, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga, mapformat as M
from pzlib.datachunk import DICT_BOOL, DICT_INT, DICT_REAL, DICT_ASCII, DICT_UNICODE
from gen_kestrel import noise

TERR = os.path.join(ROOT, "content", "dev", "Art", "Terrain")
MAPDIR = os.path.join(ROOT, "maps", "PZ_TestRange")
PREV = os.path.join(ROOT, "build", "previews")
for d in (TERR, MAPDIR, PREV):
    os.makedirs(d, exist_ok=True)

PLAY, BORDER = 128, 16
W = H = PLAY + 2 * BORDER          # height-map vertices per side
XY = 10.0                          # MAP_XY_FACTOR (ft per cell)
HSCALE = 0.625                     # MAP_HEIGHT_SCALE (ft per height unit)


def terrain_textures():
    S = 128
    # concrete: slabs with expansion joints, tileable (joints on 64px grid)
    n = noise(S, S, 4, seed=31)
    c = 0.56 + 0.10 * (n - 0.5) + 0.05 * (noise(S, S, 16, seed=32) - 0.5)
    img = np.stack([c * 1.00, c * 0.99, c * 0.95], -1)
    for k in (0, 63, 64, 127):
        img[k, :] *= 0.72; img[:, k] *= 0.72
    stains = noise(S, S, 3, seed=33) > 0.66
    img[stains] *= 0.88
    tga.save(os.path.join(TERR, "pzdev_concrete.tga"), (np.clip(img, 0, 1) * 255).astype(np.uint8))
    # gravel / packed soil
    g = noise(S, S, 6, seed=41); fine = noise(S, S, 32, seed=42)
    base = np.array([0.47, 0.42, 0.33])
    img = base * (0.82 + 0.30 * (g[..., None] - 0.5) + 0.35 * (fine[..., None] - 0.5))
    pebbles = noise(S, S, 24, seed=43) > 0.72
    img[pebbles] = img[pebbles] * 1.18
    tga.save(os.path.join(TERR, "pzdev_gravel.tga"), (np.clip(img, 0, 1) * 255).astype(np.uint8))


def heightfield():
    """Heights in engine units (byte). Returns uint8 (H, W) and a concrete mask on cells."""
    ys, xs = np.mgrid[0:H, 0:W].astype(float)
    px, py = (xs - BORDER) / PLAY, (ys - BORDER) / PLAY        # 0..1 across playable area
    hgt = np.full((H, W), 64.0)                                # 40 ft base
    # central basin along the anti-diagonal (between the two starts)
    d_diag = (px + py - 1.0) / math.sqrt(2)                    # signed distance across basin
    basin = np.exp(-(d_diag / 0.16) ** 2)
    hgt -= 22 * basin
    # berm crest inside basin, cut by two ramps (flanks) + causeway (centre)
    berm = np.exp(-(d_diag / 0.035) ** 2) * 18
    along = (px - py) / math.sqrt(2)                           # position along the basin
    gaps = np.zeros_like(hgt)
    for c0, wdt in ((0.0, 0.07), (-0.42, 0.06), (0.42, 0.06)):
        gaps = np.maximum(gaps, np.exp(-((along - c0) / wdt) ** 2))
    hgt += berm * (1 - gaps)
    # start pads: raise and flatten around both starts
    for sx, sy in ((0.17, 0.17), (0.83, 0.83)):
        r = np.hypot(px - sx, py - sy)
        pad = np.clip(1 - (r - 0.12) / 0.08, 0, 1)
        hgt = hgt * (1 - pad) + 72 * pad
    # gentle rolling detail away from pads/causeway
    hgt += 3.0 * (noise(H, W, 5, seed=51) - 0.5) * (1 - np.exp(-(along / 0.1) ** 2))
    hgt = np.clip(hgt, 2, 250)
    # concrete mask (per cell): pads, causeway band, flank lanes
    conc = np.zeros((H, W), bool)
    for sx, sy in ((0.17, 0.17), (0.83, 0.83)):
        conc |= np.hypot(px - sx, py - sy) < 0.13
    conc |= (np.abs(along) < 0.045) & (np.abs(d_diag) < 0.40)
    for c0 in (-0.42, 0.42):
        conc |= (np.abs(along - c0) < 0.03) & (np.abs(d_diag) < 0.22)
    return np.round(hgt).astype(np.uint8), conc


def max_slope_deg(h):
    dz = np.maximum(np.abs(np.diff(h.astype(float), axis=0))[:, :-1], np.abs(np.diff(h.astype(float), axis=1))[:-1, :])
    return math.degrees(math.atan(dz.max() * HSCALE / XY))


def dict_obj(name, owner, extra=()):
    base = [("objectInitialHealth", DICT_INT, 100), ("objectEnabled", DICT_BOOL, True),
            ("objectIndestructible", DICT_BOOL, False), ("objectUnsellable", DICT_BOOL, False),
            ("objectPowered", DICT_BOOL, True), ("objectRecruitableAI", DICT_BOOL, True),
            ("objectTargetable", DICT_BOOL, False), ("originalOwner", DICT_ASCII, owner),
            ("uniqueID", DICT_ASCII, name), ("objectLayer", DICT_ASCII, "")]
    return base + list(extra)


def waypoint(wid, name, x, y):
    return dict(x=x, y=y, z=0.0, angle=0.0, flags=0, tmpl="*Waypoints/Waypoint",
                props=dict_obj(name, "team", [("waypointID", DICT_INT, wid), ("waypointName", DICT_ASCII, name)]))


def build():
    terrain_textures()
    hgt, conc = heightfield()
    # Blend tile data: class 0 = PZDevGravel (tiles 0..3), class 1 = PZDevConcrete (tiles 4..7)
    classes = [dict(first=0, num=4, width=2, legacy=0, name="PZDevGravel"),
               dict(first=4, num=4, width=2, legacy=0, name="PZDevConcrete")]
    tiles = []
    for y in range(H):
        for x in range(W):
            c = classes[1 if conc[y, x] else 0]
            w = c["width"]
            tiles.append(((c["first"] + (x // 2) % w + w * ((y // 2) % w)) << 2) + (x & 1) + 2 * (y & 1))
    n = W * H
    fw = (W + 7) // 8
    blend = dict(tiles=tiles, blend=[0] * n, extra=[0] * n, cliff=[0] * n, cliffState=bytes(fw * H),
                 numBitmapTiles=8, numBlendedTiles=1, numCliffInfo=1, classes=classes,
                 numEdgeTiles=0, edgeClasses=[], blendedTiles=[], cliffInfo=[])

    # lighting: neutral overcast-noon key light, slightly cool ambient (original values)
    def L(amb, dif, pos):
        return list(amb) + list(dif) + list(pos)
    key = L((0.38, 0.40, 0.44), (0.92, 0.88, 0.80), (-0.70, 0.30, -0.65))
    fill = L((0, 0, 0), (0.20, 0.24, 0.30), (0.60, -0.50, -0.62))
    off = L((0, 0, 0), (0, 0, 0), (0, 0, -1))
    slot = dict(terrain=[key, off, off], objects=[key, fill, off])
    lighting = M.lighting_blob(2, [slot] * 4, 0x7F404850)   # time of day 2 = afternoon

    S = lambda v: BORDER * 0 + v * PLAY * XY                 # playable-relative feet
    objects = [
        waypoint(1, "Player_1_Start", S(0.17), S(0.17)),
        waypoint(2, "Player_2_Start", S(0.83), S(0.83)),
        waypoint(3, "InitialCameraPosition", S(0.17), S(0.17)),
    ]
    m = dict(
        height=dict(width=W, height=H, border=BORDER, boundaries=[(PLAY, PLAY)], data=hgt.tobytes()),
        blend=blend,
        world=[("weather", DICT_INT, 0), ("mapName", DICT_ASCII, "MAP:PZTestRange")],
        sides=[
            dict(dict=[("playerName", DICT_ASCII, ""), ("playerIsHuman", DICT_BOOL, False),
                       ("playerDisplayName", DICT_UNICODE, "Neutral"), ("playerFaction", DICT_ASCII, ""),
                       ("playerAllies", DICT_ASCII, ""), ("playerEnemies", DICT_ASCII, "")], build=[]),
            dict(dict=[("playerName", DICT_ASCII, "PlyrCivilian"), ("playerIsHuman", DICT_BOOL, False),
                       ("playerDisplayName", DICT_UNICODE, "Civilian"), ("playerFaction", DICT_ASCII, "FactionCivilian"),
                       ("playerAllies", DICT_ASCII, ""), ("playerEnemies", DICT_ASCII, "")], build=[]),
        ],
        teams=[[("teamName", DICT_ASCII, "team"), ("teamOwner", DICT_ASCII, ""), ("teamIsSingleton", DICT_BOOL, True)],
               [("teamName", DICT_ASCII, "teamPlyrCivilian"), ("teamOwner", DICT_ASCII, "PlyrCivilian"),
                ("teamIsSingleton", DICT_BOOL, True)]],
        objects=objects, triggers=[], lighting=lighting, waypointLinks=[],
    )
    data = M.encode(m)
    path = os.path.join(MAPDIR, "PZ_TestRange.map")
    open(path, "wb").write(data)
    # round-trip check
    back = M.decode(data)
    assert back["height"]["data"] == m["height"]["data"] and back["blend"]["tiles"] == tiles
    print(f"map {W}x{H} ({PLAY} playable), {len(data)} bytes, height {hgt.min()}..{hgt.max()}, "
          f"max slope {max_slope_deg(hgt):.1f} deg, concrete cells {conc.sum()}")

    # preview: shaded relief + texture classes, start markers (also used as map preview .tga)
    gz = hgt.astype(float)
    gx = np.gradient(gz, axis=1); gy = np.gradient(gz, axis=0)
    shade = np.clip(0.75 - (gx - gy) * 0.06, 0.35, 1.1)
    colc = np.where(conc[..., None], [0.60, 0.60, 0.58], [0.50, 0.44, 0.34]) * shade[..., None]
    colc *= (0.75 + 0.35 * (gz[..., None] - gz.min()) / (gz.max() - gz.min() + 1e-6))
    img = Image.fromarray((np.clip(colc[::-1], 0, 1) * 255).astype(np.uint8)).resize((480, 480), Image.NEAREST)
    d = ImageDraw.Draw(img)
    k = 480 / W
    d.rectangle([BORDER * k, BORDER * k, (W - BORDER) * k, (H - BORDER) * k], outline=(255, 255, 255), width=1)
    for i, (sx, sy) in enumerate(((0.17, 0.17), (0.83, 0.83))):
        cx, cy = (BORDER + sx * PLAY) * k, 480 - (BORDER + sy * PLAY) * k
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], outline=(255, 210, 60), width=3)
        d.text((cx + 12, cy - 6), f"P{i + 1}", fill=(255, 230, 120))
    img.save(os.path.join(PREV, "testrange_blockout.png"))
    tgaimg = np.asarray(img.resize((128, 128), Image.BILINEAR).convert("RGBA"))
    tga.save(os.path.join(MAPDIR, "PZ_TestRange.tga"), tgaimg)


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""Steel Accord - procedural command-bar icon set (original work, project-owned).

Draws every icon at 512x512 from simple geometric primitives, adds a dark
outline per part, centres the glyph with ~12 px padding (at 128 px) and
downsamples with LANCZOS to 128x128 RGBA.

Outputs:
  godot/assets/ui/icons/<id>.png        128x128 icons
  godot/assets/ui/icons/_sheet.png      contact sheet (not imported by Godot)
  godot/assets/ui/icons/_sheet.png.import
  content/manifest/ui_icons.json        provenance manifest

Usage: python3 tools/art/make_ui_icons.py
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "godot", "assets", "ui", "icons")
MANIFEST = os.path.join(ROOT, "content", "manifest", "ui_icons.json")

S = 512             # working resolution
OUT = 128           # output resolution
PAD = 12 * S // OUT  # 48 px padding at working res
OUTLINE_PX = 7      # outline thickness at working res

GLYPH = (0xE8, 0xEE, 0xF0, 255)
DARK = (0x0E, 0x14, 0x18, 230)
ACCENT = {
    "orders": (0x8F, 0xB8, 0xD8, 255),
    "upgrades": (0xE7, 0xB3, 0x41, 255),
    "battle_plans": (0x4F, 0xC7, 0xB0, 255),
    "repair": (0x8E, 0xD0, 0x81, 255),
    "warn": (0xE0, 0x6A, 0x5A, 255),
}


# ---------------------------------------------------------------- primitives
class Part:
    """One coloured region; drawn as a mask then outlined."""

    def __init__(self, color, outline=True):
        self.color = color
        self.outline = outline
        self.mask = Image.new("L", (S, S), 0)
        self.d = ImageDraw.Draw(self.mask)

    # filled shapes
    def poly(self, pts, fill=255):
        self.d.polygon([tuple(p) for p in pts], fill=fill)
        return self

    def circle(self, c, r, fill=255):
        x, y = c
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        return self

    def ellipse(self, box, fill=255):
        self.d.ellipse(box, fill=fill)
        return self

    def rect(self, box, fill=255, radius=0):
        if radius:
            self.d.rounded_rectangle(box, radius=radius, fill=fill)
        else:
            self.d.rectangle(box, fill=fill)
        return self

    # strokes
    def line(self, a, b, w, fill=255, cap=True):
        self.d.line([tuple(a), tuple(b)], fill=fill, width=int(w))
        if cap:
            self.circle(a, w / 2, fill)
            self.circle(b, w / 2, fill)
        return self

    def polyline(self, pts, w, fill=255):
        for a, b in zip(pts, pts[1:]):
            self.line(a, b, w, fill)
        return self

    def ring(self, c, r, w, fill=255):
        x, y = c
        self.d.ellipse([x - r, y - r, x + r, y + r], outline=fill, width=int(w))
        return self

    def arc(self, c, r, w, a0, a1, fill=255, cap=True):
        """Arc stroke, angles in degrees (0 = +x, clockwise in screen space)."""
        x, y = c
        self.d.arc([x - r, y - r, x + r, y + r], a0, a1, fill=fill, width=int(w))
        if cap:
            for a in (a0, a1):
                rr = r - w / 2
                p = (x + rr * math.cos(math.radians(a)), y + rr * math.sin(math.radians(a)))
                self.circle(p, w / 2 - 1, fill)
        return self

    def cut(self, fn):
        """Run drawing calls that erase (fill=0)."""
        fn(self)
        return self


def arrow_head(tip, direction_deg, length, half_width):
    a = math.radians(direction_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    bx, by = tip[0] - dx * length, tip[1] - dy * length
    return [tip, (bx + px * half_width, by + py * half_width), (bx - px * half_width, by - py * half_width)]


def arrow(part, start, end, w, head_len, head_hw):
    ang = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
    a = math.radians(ang)
    shaft_end = (end[0] - math.cos(a) * head_len * 0.8, end[1] - math.sin(a) * head_len * 0.8)
    part.line(start, shaft_end, w)
    part.poly(arrow_head(end, ang, head_len, head_hw))
    return part


def crosshair(part, c, r, w, tick):
    x, y = c
    part.ring(c, r, w)
    part.rect([x - w / 2, y - r - tick, x + w / 2, y - r + tick * 0.9])
    part.rect([x - w / 2, y + r - tick * 0.9, x + w / 2, y + r + tick])
    part.rect([x - r - tick, y - w / 2, x - r + tick * 0.9, y + w / 2])
    part.rect([x + r - tick * 0.9, y - w / 2, x + r + tick, y + w / 2])
    part.circle(c, w * 0.55)
    return part


def octagon(c, r):
    return [(c[0] + r * math.cos(math.radians(22.5 + 45 * i)),
             c[1] + r * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]


def chevron(part, cx, cy, w, h, thick, point="up"):
    """Solid chevron polygon. point = up / right."""
    if point == "up":
        outer = [(cx - w / 2, cy + h / 2 - thick), (cx, cy - h / 2), (cx + w / 2, cy + h / 2 - thick),
                 (cx + w / 2, cy + h / 2), (cx, cy - h / 2 + thick), (cx - w / 2, cy + h / 2)]
        part.poly(outer)
    else:
        outer = [(cx - w / 2, cy - h / 2), (cx - w / 2 + thick, cy - h / 2), (cx + w / 2, cy),
                 (cx - w / 2 + thick, cy + h / 2), (cx - w / 2, cy + h / 2), (cx + w / 2 - thick, cy)]
        part.poly(outer)
    return part


# ---------------------------------------------------------------- icons
W = 46  # default stroke width


def icon_attack_move(acc):
    g = Part(GLYPH)
    arrow(g, (95, 420), (330, 185), W, 130, 90)
    a = Part(acc)
    crosshair(a, (395, 118), 62, 22, 26)
    return [g, a]


def shield_pts(cx, top, w, h):
    pts = [(cx - w / 2, top + h * 0.10), (cx - w * 0.18, top), (cx, top - h * 0.03),
           (cx + w * 0.18, top), (cx + w / 2, top + h * 0.10)]
    # right side curve down to point
    for i in range(1, 11):
        t = i / 10
        x = cx + (w / 2) * (1 - t ** 1.6)
        y = top + h * 0.10 + (h * 0.90) * (t ** 0.85)
        pts.append((x, y))
    for i in range(9, 0, -1):
        t = i / 10
        x = cx - (w / 2) * (1 - t ** 1.6)
        y = top + h * 0.10 + (h * 0.90) * (t ** 0.85)
        pts.append((x, y))
    return pts


def icon_guard(acc):
    g = Part(GLYPH).poly(shield_pts(256, 70, 330, 390))
    # inner bevel (dark) for depth
    d = Part(DARK, outline=False)
    d.poly(shield_pts(256, 108, 250, 300))
    g2 = Part(GLYPH, outline=False).poly(shield_pts(256, 122, 226, 270))
    # eye + pupil
    eye = Part(acc)
    eye.d.ellipse([170, 220, 342, 300], fill=255)
    pupil = Part(DARK, outline=False).circle((256, 260), 28)
    return [g, d, g2, eye, pupil]


def icon_force(acc):
    a = Part(acc)
    x, y, r, w, t = 256, 256, 165, 34, 52
    a.ring((x, y), r, w)
    a.rect([x - w / 2, y - r - t, x + w / 2, y - r + t])
    a.rect([x - w / 2, y + r - t, x + w / 2, y + r + t])
    a.rect([x - r - t, y - w / 2, x - r + t, y + w / 2])
    a.rect([x + r - t, y - w / 2, x + r + t, y + w / 2])
    g = Part(GLYPH)
    # ground mark: flattened (perspective) X at the reticle centre
    g.line((175, 215), (337, 297), W)
    g.line((337, 215), (175, 297), W)
    return [a, g]


def icon_waypoint(acc):
    pts = [(105, 420), (215, 270), (330, 330), (410, 150)]
    dots = Part(GLYPH)
    # dotted path along segments
    for p, q in zip(pts, pts[1:]):
        n = 4
        for i in range(1, n):
            t = i / n
            dots.circle((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), 13)
    nodes = Part(GLYPH)
    for p in pts[:3]:
        nodes.circle(p, 36)
    flag = Part(GLYPH)
    fx, fy = pts[3]
    flag.line((fx, fy + 40), (fx, fy - 105), 22)
    flag.circle((fx, fy + 40), 30)
    pennant = Part(acc).poly([(fx + 8, fy - 115), (fx + 105, fy - 80), (fx + 8, fy - 40)])
    return [dots, nodes, flag, pennant]


def icon_stop(acc):
    g = Part(GLYPH).poly(octagon((256, 256), 200))
    a = Part(acc).poly(octagon((256, 256), 158))
    bar = Part(GLYPH).rect([150, 228, 362, 284], radius=12)
    return [g, a, bar]


def icon_scatter(acc):
    g = Part(GLYPH)
    c = 256
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        s = (c + math.cos(a) * 90, c + math.sin(a) * 90)
        e = (c + math.cos(a) * 225, c + math.sin(a) * 225)
        arrow(g, s, e, 40, 95, 66)
    a = Part(acc).circle((c, c), 58)
    return [g, a]


def aircraft_pts(cx, cy, s):
    # top-down jet, nose up. coordinates in units scaled by s
    base = [(0, -1.0), (0.10, -0.75), (0.12, -0.25), (0.85, 0.20), (0.85, 0.36), (0.12, 0.18),
            (0.10, 0.62), (0.38, 0.86), (0.38, 0.98), (0.0, 0.90),
            (-0.38, 0.98), (-0.38, 0.86), (-0.10, 0.62), (-0.12, 0.18), (-0.85, 0.36),
            (-0.85, 0.20), (-0.12, -0.25), (-0.10, -0.75)]
    return [(cx + x * s, cy + y * s) for x, y in base]


def icon_return(acc):
    g = Part(GLYPH).poly(aircraft_pts(200, 270, 175))
    a = Part(acc)
    # U-turn arrow on the right: up the right side, over the top, pointing down-left
    a.arc((340, 230), 120, 40, 200, 360 + 90, cap=False)
    a.circle((340 + 0, 230 + 100), 20)
    a.poly(arrow_head((215, 260), 100, 95, 62))
    return [a, g]


def icon_select_all(acc):
    g = Part(GLYPH)
    x0, y0, x1, y1 = 70, 95, 442, 417
    w = 26
    # dashed rectangle: corners plus dashes
    def hdash(y):
        x = x0
        while x < x1:
            g.rect([x, y - w / 2, min(x + 52, x1), y + w / 2])
            x += 82
        g.rect([x1 - 52, y - w / 2, x1 + w / 2, y + w / 2])
    def vdash(x):
        y = y0
        while y < y1:
            g.rect([x - w / 2, y, x + w / 2, min(y + 52, y1)])
            y += 82
        g.rect([x - w / 2, y1 - 52, x + w / 2, y1 + w / 2])
    hdash(y0); hdash(y1); vdash(x0); vdash(x1)
    a = Part(acc)
    for (cx, cy) in [(180, 210), (332, 210), (256, 320)]:
        a.circle((cx, cy - 22), 34)            # head
        a.d.pieslice([cx - 58, cy + 10, cx + 58, cy + 110], 180, 360, fill=255)  # shoulders
    return [g, a]


def vehicle_side(part, x0, y0, scale=1.0):
    """APC/truck side profile, facing right. Returns wheel centres."""
    s = scale
    body = [(x0, y0 + 60 * s), (x0 + 30 * s, y0 + 10 * s), (x0 + 200 * s, y0 + 10 * s),
            (x0 + 230 * s, y0 - 40 * s), (x0 + 300 * s, y0 - 40 * s), (x0 + 340 * s, y0 + 20 * s),
            (x0 + 340 * s, y0 + 100 * s), (x0, y0 + 100 * s)]
    part.poly(body)
    return [(x0 + 70 * s, y0 + 110 * s), (x0 + 170 * s, y0 + 110 * s), (x0 + 270 * s, y0 + 110 * s)]


def icon_unload(acc):
    g = Part(GLYPH)
    wheels = vehicle_side(g, 120, 110, 0.95)
    win2 = Part(DARK, outline=False).rect([345, 80, 405, 100])
    wh = Part(GLYPH)
    for c in wheels:
        wh.circle(c, 40)
    hub = Part(DARK, outline=False)
    for c in wheels:
        hub.circle(c, 13)
    a = Part(acc)
    # out of the rear door, then down
    arrow(a, (75, 150), (75, 440), 46, 110, 80)
    return [g, win2, wh, hub, a]


def icon_rally(acc):
    g = Part(GLYPH)
    g.line((150, 80), (150, 400), 34)
    g.ellipse([80, 395, 220, 445])
    a = Part(acc)
    # waving flag
    top, bot = 90, 280
    pts_top = [(168 + i * 26, top + 22 * math.sin(i / 9 * math.pi * 1.6)) for i in range(10)]
    pts_bot = [(168 + i * 26, bot - 70 + 22 * math.sin(i / 9 * math.pi * 1.6)) for i in range(10)]
    a.poly(pts_top + list(reversed(pts_bot)))
    return [a, g]


def icon_find_builder(acc):
    g = Part(GLYPH)
    # tracks
    g.rect([130, 340, 440, 440], radius=50)
    # body + cab
    g.poly([(150, 340), (150, 255), (270, 255), (282, 165), (390, 165), (405, 255), (420, 340)])
    # push arm
    g.line((150, 310), (100, 310), 34, cap=False)
    # blade (curved)
    g.poly([(50, 225), (104, 225), (88, 275), (88, 395), (104, 445), (50, 445), (66, 395), (66, 275)])
    win = Part(DARK, outline=False).poly([(296, 188), (374, 188), (383, 245), (290, 245)])
    wheels = Part(DARK, outline=False)
    for x in (180, 285, 390):
        wheels.circle((x, 390), 24)
    a = Part(acc)
    a.ring((150, 135), 78, 30)
    a.line((205, 190), (245, 230), 38)
    lens_tint = Part((0x8F, 0xB8, 0xD8, 90), outline=False).circle((150, 135), 63)
    return [g, win, wheels, a, lens_tint]


def icon_menu(acc):
    g1 = Part(GLYPH).rect([80, 110, 432, 170], radius=30)
    a = Part(acc).rect([80, 226, 432, 286], radius=30)
    g3 = Part(GLYPH).rect([80, 342, 432, 402], radius=30)
    return [g1, a, g3]


def icon_details(acc):
    g = Part(GLYPH).ring((256, 256), 200, 40)
    a = Part(acc)
    a.circle((256, 150), 36)
    a.rect([222, 215, 290, 375], radius=14)
    a.rect([200, 345, 312, 380], radius=10)
    a.rect([200, 215, 260, 248], radius=10)
    return [g, a]


def icon_repair(acc):
    # wrench diagonal, head upper-right
    g = Part(GLYPH)
    g.line((120, 400), (300, 220), 58)
    a = Part(acc)
    hc = (330, 182)
    a.circle(hc, 105)
    # open jaw: cut a slot toward upper-right
    a.d.polygon([(hc[0] - 10, hc[1] + 10), (hc[0] + 40, hc[1] - 110), (hc[0] + 150, hc[1] - 110),
                 (hc[0] + 150, hc[1] + 0), (hc[0] + 110, hc[1] - 40)], fill=0)
    a.d.polygon([(hc[0] - 15, hc[1] + 15), (hc[0] + 30, hc[1] - 130), (hc[0] + 130, hc[1] - 30)], fill=0)
    a.d.ellipse([hc[0] - 38, hc[1] - 38, hc[0] + 28, hc[1] + 28], fill=0)
    # handle hole
    hole = Part(DARK, outline=False).circle((135, 385), 14)
    return [g, a, hole]


def icon_sell(acc):
    cx = 200
    parts = []
    for i, y in enumerate((380, 310, 240)):
        p = Part(GLYPH)
        p.rect([cx - 125, y - 10, cx + 125, y + 40])
        p.ellipse([cx - 125, y + 5, cx + 125, y + 70])
        p.ellipse([cx - 125, y - 40, cx + 125, y + 25])
        parts.append(p)
    mark = Part(DARK, outline=False).ellipse([cx - 70, 190, cx + 70, 225])
    a = Part(acc)
    arrow(a, (410, 90), (410, 330), 44, 110, 78)
    return parts + [mark, a]


def icon_cancel(acc):
    a = Part(acc).circle((256, 256), 205)
    inner = Part(DARK, outline=False).circle((256, 256), 160)
    g = Part(GLYPH)
    g.line((185, 185), (327, 327), 50)
    g.line((327, 185), (185, 327), 50)
    return [a, inner, g]


def icon_adv_armor(acc):
    g = Part(GLYPH)
    g.poly([(150, 70), (205, 70), (230, 140), (282, 140), (307, 70), (362, 70),
            (380, 150), (440, 190), (420, 300), (400, 300), (400, 440), (112, 440),
            (112, 300), (92, 300), (72, 190), (132, 150)])
    a = Part(acc)
    a.rect([178, 205, 334, 305], radius=12)
    a.rect([178, 325, 334, 405], radius=12)
    seam = Part(DARK, outline=False).rect([252, 205, 260, 405])
    return [g, a, seam]


def icon_composite_armor(acc):
    g = Part(GLYPH)
    # hull side (stubby, so the icon is not a thin strip)
    g.poly([(50, 270), (95, 215), (420, 215), (465, 270), (430, 420), (85, 420)])
    # turret + gun
    g.poly([(150, 215), (180, 120), (330, 120), (365, 215)])
    g.rect([330, 140, 480, 168])
    road = Part(DARK, outline=False)
    for x in (130, 205, 280, 355):
        road.circle((x, 385), 22)
    a = Part(acc)
    # layered plate block on hull side: 4 x 2 tiles
    for i in range(4):
        for j in range(2):
            x = 105 + i * 78
            y = 232 + j * 56
            a.rect([x, y, x + 68, y + 46], radius=5)
    return [g, road, a]


def icon_guided_munitions(acc):
    g = Part(GLYPH)
    # missile diagonal from lower-left to upper-right
    ang = -45
    cx, cy = 225, 290
    L = 300
    a_ = math.radians(ang)
    dx, dy = math.cos(a_), math.sin(a_)
    px, py = -dy, dx
    def P(u, v):
        return (cx + dx * u + px * v, cy + dy * u + py * v)
    body = [P(-L / 2, -24), P(L / 2 - 50, -24), P(L / 2, 0), P(L / 2 - 50, 24), P(-L / 2, 24)]
    g.poly(body)
    fins = Part(GLYPH)
    fins.poly([P(-L / 2, -24), P(-L / 2 + 70, -24), P(-L / 2 + 5, -85), P(-L / 2 - 30, -85)])
    fins.poly([P(-L / 2, 24), P(-L / 2 + 70, 24), P(-L / 2 + 5, 85), P(-L / 2 - 30, 85)])
    band = Part(DARK, outline=False).poly([P(L / 2 - 60, -26), P(L / 2 - 50, -26), P(L / 2 - 50, 26), P(L / 2 - 60, 26)])
    a = Part(acc)
    crosshair(a, (390, 122), 72, 24, 30)
    return [fins, g, band, a]


def icon_supply_efficiency(acc):
    a = Part(acc)
    c = (256, 256)
    a.arc(c, 215, 38, 200, 330, cap=False)
    a.arc(c, 215, 38, 20, 150, cap=False)
    # heads at 330 and 150 (clockwise)
    for end in (330, 150):
        r = 215 - 19
        tip_a = math.radians(end + 18)
        tip = (c[0] + r * math.cos(tip_a), c[1] + r * math.sin(tip_a))
        a.poly(arrow_head(tip, end + 18 + 90, 80, 52))
    g = Part(GLYPH).rect([150, 150, 362, 362], radius=10)
    # crate: framed panel with cross bracing
    return [a, g, Part(DARK, outline=False).rect([175, 175, 337, 337]),
            Part(GLYPH, outline=False).rect([187, 187, 325, 325]),
            Part(DARK, outline=False).line((192, 192), (320, 320), 14, cap=False),
            Part(DARK, outline=False).line((320, 192), (192, 320), 14, cap=False)]


def icon_adv_training(acc):
    g = Part(GLYPH)
    g.ring((256, 360), 120, 34)
    g.circle((256, 360), 40)
    a = Part(acc)
    chevron(a, 256, 90, 230, 90, 44, "up")
    chevron(a, 256, 160, 230, 90, 44, "up")
    a2 = Part(acc)
    chevron(a2, 256, 230, 230, 90, 44, "up")
    return [g, a, a2]


def icon_assault(acc):
    g = Part(GLYPH)
    chevron(g, 200, 256, 170, 320, 70, "right")
    a = Part(acc)
    chevron(a, 345, 256, 170, 320, 70, "right")
    return [g, a]


def icon_fortify(acc):
    # brick wall, 3 rows
    rows = [(330, 0), (385, 1), (440, 0)]
    bw, bh = 108, 48
    wall = Part(GLYPH)
    for y, off in rows:
        x = 40 - (bw // 2 if off else 0)
        while x < 472:
            wall.rect([max(x, 40), y - bh, min(x + bw - 8, 472), y - 6], radius=4)
            x += bw
    # battlements
    for x in (40, 150, 260, 370):
        wall.rect([x, 228, x + 62, 278], radius=4)
    a = Part(acc).poly(shield_pts(256, 80, 220, 270))
    inner = Part(DARK, outline=False).poly(shield_pts(256, 118, 140, 180))
    inner2 = Part(acc, outline=False).poly(shield_pts(256, 128, 120, 158))
    return [wall, a, inner, inner2]


def icon_recon(acc):
    g = Part(GLYPH)
    # two barrels
    g.rect([95, 150, 225, 380], radius=50)
    g.rect([287, 150, 417, 380], radius=50)
    g.rect([210, 180, 302, 290], radius=20)  # bridge
    g.rect([120, 110, 200, 170], radius=12)
    g.rect([312, 110, 392, 170], radius=12)
    a = Part(acc)
    a.circle((160, 330), 62)
    a.circle((352, 330), 62)
    glint = Part(GLYPH, outline=False)
    glint.circle((140, 310), 16)
    glint.circle((332, 310), 16)
    return [g, a, glint]


ICONS = [
    # id, category, accent key, fn, description
    ("attack_move", "orders", "orders", icon_attack_move, "Attack-move: forward arrow with a crosshair at the tip"),
    ("guard", "orders", "orders", icon_guard, "Guard: shield with an eye at its centre"),
    ("force", "orders", "orders", icon_force, "Force fire: crosshair over a ground X mark"),
    ("waypoint", "orders", "orders", icon_waypoint, "Waypoint: dotted path linking nodes to a flag"),
    ("stop", "orders", "orders", icon_stop, "Stop: octagon with a horizontal bar"),
    ("scatter", "orders", "orders", icon_scatter, "Scatter: four arrows pointing outward from a centre dot"),
    ("return", "orders", "orders", icon_return, "Return to base: top-down aircraft with a U-turn arrow"),
    ("select_all", "orders", "orders", icon_select_all, "Select all: three soldier figures inside a dashed selection box"),
    ("unload", "orders", "orders", icon_unload, "Unload: transport vehicle side view with a down arrow"),
    ("rally", "orders", "orders", icon_rally, "Rally point: flag on a pole"),
    ("find_builder", "orders", "orders", icon_find_builder, "Find builder: bulldozer silhouette with a magnifier"),
    ("menu", "orders", "orders", icon_menu, "Menu: three horizontal bars"),
    ("details", "orders", "orders", icon_details, "Details: circled info glyph (dot and bar)"),
    ("repair", "building_actions", "repair", icon_repair, "Repair: wrench"),
    ("sell", "building_actions", "warn", icon_sell, "Sell: coin stack with a downward arrow"),
    ("cancel", "building_actions", "warn", icon_cancel, "Cancel: X in a circle"),
    ("adv_armor", "upgrades", "upgrades", icon_adv_armor, "Advanced body armour: infantry vest with plate inserts"),
    ("composite_armor", "upgrades", "upgrades", icon_composite_armor, "Composite armour: layered plate tiles on a tank hull side"),
    ("guided_munitions", "upgrades", "upgrades", icon_guided_munitions, "Guided munitions: missile with a target reticle"),
    ("supply_efficiency", "upgrades", "upgrades", icon_supply_efficiency, "Supply efficiency: supply crate with circular arrows"),
    ("adv_training", "upgrades", "upgrades", icon_adv_training, "Advanced training: rank chevron stack over a target"),
    ("assault", "battle_plans", "battle_plans", icon_assault, "Assault plan: two forward chevrons"),
    ("fortify", "battle_plans", "battle_plans", icon_fortify, "Fortify plan: wall of blocks with a shield"),
    ("recon", "battle_plans", "battle_plans", icon_recon, "Recon plan: binoculars"),
]


# ---------------------------------------------------------------- render
def render(parts):
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    k = OUTLINE_PX * 2 + 1
    for p in parts:
        if p.mask.getbbox() is None:
            continue
        if p.outline:
            dil = p.mask.filter(ImageFilter.MaxFilter(k))
            ol = Image.new("RGBA", (S, S), DARK)
            # outline replaces what is under it (keeps internal separation crisp)
            canvas = Image.composite(ol, canvas, dil)
        if p.color[3] == 255:
            canvas = Image.composite(Image.new("RGBA", (S, S), p.color), canvas, p.mask)
        else:
            fill = Image.new("RGBA", (S, S), p.color[:3] + (0,))
            fill.putalpha(p.mask.point(lambda v, a=p.color[3]: v * a // 255))
            canvas = Image.alpha_composite(canvas, fill)
    return canvas


def fit(img):
    """Centre on bbox, scale so the larger side fits S-2*PAD (clamped)."""
    bbox = img.getchannel("A").getbbox()
    crop = img.crop(bbox)
    w, h = crop.size
    target = S - 2 * PAD
    scale = min(target / w, target / h)
    scale = max(0.6, min(scale, 1.35))
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    crop = crop.resize((nw, nh), Image.LANCZOS)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.alpha_composite(crop, ((S - nw) // 2, (S - nh) // 2))
    return out


def make_sheet(results):
    cols = 6
    cell_w, cell_h = 132, 116
    rows = math.ceil(len(results) / cols)
    sheet = Image.new("RGBA", (cols * cell_w + 16, rows * cell_h + 16), (0x10, 0x16, 0x1A, 255))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    for i, (iid, img) in enumerate(results):
        cx = 8 + (i % cols) * cell_w
        cy = 8 + (i // cols) * cell_h
        tx, ty = cx + (cell_w - 72) // 2, cy + 6
        d.rounded_rectangle([tx, ty, tx + 72, ty + 72], radius=6, fill=(0x1B, 0x25, 0x2B, 255))
        sheet.alpha_composite(img.resize((64, 64), Image.LANCZOS), (tx + 4, ty + 4))
        tw = d.textlength(iid, font=font)
        d.text((cx + (cell_w - tw) / 2, ty + 80), iid, fill=(0xC8, 0xD2, 0xD8, 255), font=font)
    return sheet


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    results, items = [], []
    for iid, cat, acc_key, fn, desc in ICONS:
        big = fit(render(fn(ACCENT[acc_key])))
        small = big.resize((OUT, OUT), Image.LANCZOS)
        path = os.path.join(OUT_DIR, iid + ".png")
        small.save(path, optimize=True)
        results.append((iid, small))
        items.append({"id": iid, "path": "res://assets/ui/icons/%s.png" % iid,
                      "category": cat, "description": desc})
        print("wrote", path)
    sheet_path = os.path.join(OUT_DIR, "_sheet.png")
    make_sheet(results).convert("RGB").save(sheet_path)
    with open(sheet_path + ".import", "w") as f:
        f.write('[remap]\nimporter="skip"\n')
    print("wrote", sheet_path)
    manifest = {
        "pack": "Command bar UI icons",
        "generator": "tools/art/make_ui_icons.py",
        "method": "procedural vector primitives drawn with Pillow at 512 px, outlined, LANCZOS-downsampled to 128 px RGBA",
        "license": "original work, project-owned",
        "status": "shippable",
        "palette": {"glyph": "#E8EEF0", "outline": "#0E1418 a230", "orders": "#8FB8D8",
                    "upgrades": "#E7B341", "battle_plans": "#4FC7B0", "repair": "#8ED081",
                    "sell_cancel": "#E06A5A"},
        "items": items,
    }
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")
    print("wrote", MANIFEST)


if __name__ == "__main__":
    main()

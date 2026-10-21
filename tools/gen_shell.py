#!/usr/bin/env python3
"""Generate the Steel Accord shell (front-end) for the standalone build: layouts, art, strings.

Writes into content/base:
  Window/IMECandidateWindow.wnd, Window/IMEStatusWindow.wnd   (text-input helper windows)
  Window/Menus/MainMenu.wnd                                   (title screen + main menu)
  Art/Textures/sa_shell_bg.tga   + Data/INI/MappedImages/HandCreated/SA_Shell.ini
  Data/Generals.str              (all GUI strings, original English text)
Window names/types/callbacks are the engine's interface contract (looked up by name in
Core/GameEngine/Source/GameClient/GUI/GUICallbacks/Menus/MainMenu.cpp); everything visual
and every word of text is original.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga
from pzlib.wnd import Win, layout, PALETTE
from gen_kestrel import noise

BASE = os.path.join(ROOT, "content", "base")
PREV = os.path.join(ROOT, "build", "previews")
FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

STRINGS = {}


def S(label, text):
    STRINGS[label] = text
    return label


# ------------------------------------------------------------------ art
def shell_background():
    W, H = 1024, 768
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]
    n = noise(H, W, 6, seed=201)
    base = np.array([0.07, 0.10, 0.13]) * (1 - y[..., None]) + np.array([0.13, 0.17, 0.20]) * y[..., None]
    img = base + 0.05 * (n[..., None] - 0.5)
    # brushed-steel diagonal bands
    band = np.sin((x * 9 + y * 4) * np.pi) ** 8
    img += band[..., None] * np.array([0.03, 0.04, 0.05])
    # warm horizon glow on the right
    glow = np.exp(-(((x - 0.78) / 0.30) ** 2 + ((y - 0.62) / 0.20) ** 2))
    img += glow[..., None] * np.array([0.28, 0.16, 0.06])
    pil = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)
    # stylised silhouette ridge (original): layered skyline of cranes/hills
    rng = np.random.default_rng(7)
    pts = [(0, 600)]
    for i in range(0, W + 32, 32):
        pts.append((i, 560 + int(25 * np.sin(i / 90) + rng.integers(-8, 8))))
    pts += [(W, H), (0, H)]
    d.polygon(pts, fill=(10, 13, 16))
    for cx in (640, 760, 880):
        d.line([(cx, 560), (cx, 420)], fill=(14, 18, 22), width=6)
        d.line([(cx - 60, 430), (cx + 90, 430)], fill=(14, 18, 22), width=5)
        d.line([(cx + 80, 430), (cx + 80, 470)], fill=(14, 18, 22), width=2)
    # title block
    big = ImageFont.truetype(FONT_FILE, 76)
    small = ImageFont.truetype(FONT_FILE, 20)
    d.text((372, 92), "STEEL ACCORD", font=big, fill=(0, 0, 0))
    d.text((368, 88), "STEEL ACCORD", font=big, fill=(226, 232, 236))
    d.rectangle([370, 182, 980, 186], fill=(255, 176, 64))
    d.text((372, 198), "MODERN REAL-TIME STRATEGY", font=small, fill=(150, 176, 190))
    d.text((372, 222), "DEVELOPMENT BUILD", font=ImageFont.truetype(FONT_FILE, 14), fill=(255, 176, 64))
    pil = pil.filter(ImageFilter.GaussianBlur(0.4))
    canvas = Image.new("RGB", (1024, 1024), (0, 0, 0)); canvas.paste(pil, (0, 0))
    os.makedirs(os.path.join(BASE, "Art", "Textures"), exist_ok=True)
    tga.save(os.path.join(BASE, "Art", "Textures", "sa_shell_bg.tga"), np.asarray(canvas))
    pil.save(os.path.join(PREV, "shell_background.png"))
    mi = os.path.join(BASE, "Data", "INI", "MappedImages", "HandCreated")
    os.makedirs(mi, exist_ok=True)
    open(os.path.join(mi, "SA_Shell.ini"), "w").write(
        "; Steel Accord - shell images (original, tools/gen_shell.py)\n"
        "MappedImage SAShellBackdrop\n  Texture = sa_shell_bg.tga\n  TextureWidth = 1024\n  TextureHeight = 1024\n"
        "  Coords = Left:0 Top:0 Right:1023 Bottom:767\n  Status = NONE\nEnd\n")


# ------------------------------------------------------------------ layouts
def btn(name, text_label, text, y, x=48, w=232, h=34, hidden=False):
    return Win("PUSHBUTTON", f"MainMenu.wnd:{name}", (x, y, x + w, y + h),
               status="ENABLED+IMAGE" + ("+HIDDEN" if hidden else ""),
               text=S(text_label, text), font=("Arial", 14, 1), header="MainButton")


def panel(name, inner, buttons):
    """MapBorderN (outer) / EarthMapN (inner) panels the engine shows and hides per menu state."""
    return Win("USER", f"MainMenu.wnd:{name}", (32, 250, 296, 560), status="ENABLED",
               system="PassSelectedButtonsToParentSystem",
               children=[Win("USER", f"MainMenu.wnd:{inner}", (36, 254, 292, 556), status="ENABLED",
                             system="PassSelectedButtonsToParentSystem", children=buttons)])


def main_menu():
    rows = lambda i: 262 + i * 44
    hidden_user = lambda n: Win("USER", f"MainMenu.wnd:{n}", (0, 0, 1, 1), status="ENABLED+HIDDEN+IMAGE")
    main = panel("MapBorder2", "EarthMap2", [
        btn("ButtonSinglePlayer", "GUI:SA_SinglePlayer", "SINGLE PLAYER", rows(0)),
        btn("ButtonMultiplayer", "GUI:SA_Multiplayer", "MULTIPLAYER", rows(1)),
        btn("ButtonLoadReplay", "GUI:SA_LoadReplay", "LOAD / REPLAY", rows(2)),
        btn("ButtonOptions", "GUI:SA_Options", "OPTIONS", rows(3)),
        btn("ButtonCredits", "GUI:SA_Credits", "CREDITS", rows(4)),
        btn("ButtonExit", "GUI:SA_Exit", "EXIT", rows(5)),
    ])
    single = panel("MapBorder", "EarthMap", [
        btn("ButtonSkirmish", "GUI:SA_Skirmish", "SKIRMISH", rows(0)),
        btn("ButtonUSA", "GUI:SA_Campaign", "CAMPAIGN (LATER)", rows(1), hidden=True),
        btn("ButtonChina", "GUI:SA_Campaign", "CAMPAIGN (LATER)", rows(2), hidden=True),
        btn("ButtonGLA", "GUI:SA_Campaign", "CAMPAIGN (LATER)", rows(3), hidden=True),
        btn("ButtonChallenge", "GUI:SA_Challenge", "CHALLENGE (LATER)", rows(4), hidden=True),
        btn("ButtonSingleBack", "GUI:SA_Back", "BACK", rows(5)),
    ])
    multi = panel("MapBorder1", "EarthMap1", [
        btn("ButtonNetwork", "GUI:SA_Network", "LOCAL NETWORK", rows(0)),
        btn("ButtonOnline", "GUI:SA_Online", "ONLINE (LATER)", rows(1), hidden=True),
        btn("ButtonMultiBack", "GUI:SA_Back", "BACK", rows(5)),
    ])
    loadrep = panel("MapBorder3", "EarthMap3", [
        btn("ButtonLoadGame", "GUI:SA_LoadGame", "LOAD GAME", rows(0)),
        btn("ButtonReplay", "GUI:SA_Replays", "REPLAYS", rows(1)),
        btn("ButtonLoadReplayBack", "GUI:SA_Back", "BACK", rows(5)),
    ])
    diff = panel("MapBorder4", "EarthMap4", [
        btn("ButtonEasy", "GUI:SA_Easy", "EASY", rows(0)),
        btn("ButtonMedium", "GUI:SA_Medium", "MEDIUM", rows(1)),
        btn("ButtonHard", "GUI:SA_Hard", "HARD", rows(2)),
        btn("ButtonDiffBack", "GUI:SA_Back", "BACK", rows(5)),
        Win("STATICTEXT", "MainMenu.wnd:StaticTextSelectDifficulty", (48, 228, 280, 252), status="ENABLED+HIDDEN",
            text=S("GUI:SA_SelectDifficulty", "SELECT DIFFICULTY"), extra=["STATICTEXTDATA = CENTERED: 1"]),
    ])
    extras = [hidden_user(n) for n in (
        "ShellMenuScheme", "GreenDot", "WinGrowMarker", "WinFactionTrainingSmall", "WinFactionTrainingMedium",
        "WinFactionTraining", "WinFactionSkirmishSmall", "WinFactionSkirmishMedium", "WinFactionSkirmish",
        "WinFactionUSSmall", "WinFactionUSMedium", "WinFactionUS", "WinFactionGLASmall", "WinFactionGLAMedium",
        "WinFactionGLA", "WinFactionChinaSmall", "WinFactionChinaMedium", "WinFactionChina")]
    extras.append(Win("USER", "MainMenu.wnd:Clock", (0, 0, 1, 1), status="ENABLED+HIDDEN", draw="W3DClockDraw"))
    for n in ("ButtonUSARecentSave", "ButtonUSALoadGame", "ButtonGLARecentSave", "ButtonGLALoadGame",
              "ButtonChinaRecentSave", "ButtonChinaLoadGame", "ButtonGetMapPack", "ButtonGetUpdate"):
        extras.append(Win("PUSHBUTTON", f"MainMenu.wnd:{n}", (0, 0, 1, 1), status="ENABLED+IMAGE+HIDDEN",
                          text=S("GUI:SA_Hidden", " ")))
    ruler = Win("USER", "MainMenu.wnd:MainMenuRuler", (0, 0, 800, 600), status="ENABLED+IMAGE")
    version = Win("STATICTEXT", "MainMenu.wnd:LabelVersion", (520, 572, 792, 592), status="ENABLED",
                  text=S("GUI:SA_Version", "Steel Accord dev build"), font=("Arial", 10, 0),
                  extra=["STATICTEXTDATA = CENTERED: 0"])
    logo = Win("USER", "MainMenu.wnd:Logo", (0, 0, 1, 1), status="ENABLED+HIDDEN+IMAGE")
    root = Win("USER", "MainMenu.wnd:MainMenuParent", (0, 0, 800, 600), status="ENABLED+IMAGE",
               system="MainMenuSystem", input="MainMenuInput",
               enabled=[("SAShellBackdrop", (255, 255, 255, 255), (0, 0, 0, 0))],
               children=[ruler, diff, multi, loadrep, single, main, version, logo] + extras)
    return layout(root, init="W3DMainMenuInit", update="MainMenuUpdate", shutdown="MainMenuShutdown")


def ime_windows():
    cand = Win("USER", "IMECandidateWindow.wnd:Candidate", (300, 300, 500, 420), status="DRAGABLE+ENABLED",
               system="IMECandidateWindowSystem", input="IMECandidateWindowInput", draw="IMECandidateMainDraw",
               children=[Win("USER", "IMECandidateWindow.wnd:TextArea", (304, 304, 480, 416), status="ENABLED",
                             draw="IMECandidateTextAreaDraw"),
                         Win("USER", "IMECandidateWindow.wnd:UpArrow", (482, 304, 496, 318), status="ENABLED+IMAGE"),
                         Win("USER", "IMECandidateWindow.wnd:DownArrow", (482, 402, 496, 416), status="ENABLED+IMAGE")])
    status = Win("USER", "IMEStatusWindow.wnd:IMEStatusWindow", (700, 560, 790, 590), status="DRAGABLE+ENABLED",
                 system="GameWinDefaultSystem", draw="GameWinDefaultDraw",
                 children=[Win("STATICTEXT", "IMEStatusWindow.wnd:Text", (704, 564, 786, 586), status="ENABLED+IMAGE",
                               text=S("GUI:SA_IME", " "), extra=["STATICTEXTDATA = CENTERED: 1"])])
    return layout(cand), layout(status)


def write(rel, text):
    p = os.path.join(BASE, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", newline="\n").write(text)


def main():
    os.makedirs(PREV, exist_ok=True)
    shell_background()
    write("Window/Menus/MainMenu.wnd", main_menu())
    c, s = ime_windows()
    write("Window/IMECandidateWindow.wnd", c)
    write("Window/IMEStatusWindow.wnd", s)
    S("GUI:SteelAccord", "STEEL ACCORD")
    import gen_hud
    gen_hud.main()
    STRINGS.update(gen_hud.HUD_STRINGS)
    lines = ["// Steel Accord - global string table (original text, English). Generated by tools/gen_shell.py", ""]
    auto = os.path.join(ROOT, "content", "base_src", "auto_layout_strings.str")
    if os.path.exists(auto):
        for blk in open(auto).read().split("\nEND\n"):
            ls = [l for l in blk.strip().splitlines() if l]
            if len(ls) >= 2 and ls[0] not in STRINGS: STRINGS[ls[0]] = ls[1].strip('"')
    for k in sorted(STRINGS):
        lines += [k, '"' + STRINGS[k].replace('"', "'") + '"', "END", ""]
    open(os.path.join(BASE, "Data", "Generals.str"), "w").write("\n".join(lines))
    print(f"shell: {len(STRINGS)} strings")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate the Steel Accord in-game HUD (command bar) for the standalone build.

Writes into content/base:
  Window/ControlBar.wnd, Window/ReplayControl.wnd
  Art/Textures/sa_hud.tga  + Data/INI/MappedImages/HandCreated/SA_Hud.ini
  Data/INI/ControlBarScheme.ini (one scheme per playable side + observer)
Layout (800x600 design space, scaled by the engine): radar left, command grid centre,
selection/production right, money and power above the grid. Names/types/callbacks are the
engine's ControlBar interface contract; geometry, art and colours are original.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga
from pzlib.wnd import Win, layout, PALETTE
from gen_kestrel import noise

BASE = os.path.join(ROOT, "content", "base")
PREV = os.path.join(ROOT, "build", "previews")
SIDES = ["USA", "China", "Observer", "Civilian"]
BAR_Y = 440
HUD_STRINGS = {"GUI:SA_DeleteBeacon": "DELETE", "GUI:SA_BeaconLabel": "Beacon message:", "GUI:SA_Clear": "CLEAR",
               "GUI:SA_Slower": "SLOWER", "GUI:SA_Faster": "FASTER", "GUI:SA_Pause": "PAUSE", "GUI:SA_Step": "STEP"}
CB = "ControlBar.wnd:"

# ------------------------------------------------------------------ art atlas (1024x256)
IMAGES = {}   # name -> (x0, y0, x1, y1) inclusive


def img(name, rect): IMAGES[name] = rect


def hud_art():
    W, H = 1024, 256
    pil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # --- bar background 800x160 at (0,0)
    y, x = np.mgrid[0:160, 0:800]
    n = noise(160, 800, 8, seed=301)
    base = np.array([0.10, 0.13, 0.16]) + 0.03 * (n[..., None] - 0.5)
    base = base * (1 - 0.25 * (y[..., None] / 160))
    bar = (np.clip(base, 0, 1) * 255).astype(np.uint8)
    bar = np.concatenate([bar, np.full((160, 800, 1), 245, np.uint8)], -1)
    b = Image.fromarray(bar, "RGBA"); d = ImageDraw.Draw(b)
    amber = (255, 176, 64, 255); steel = (96, 132, 150, 255); dark = (6, 9, 12, 255)
    d.rectangle([0, 0, 799, 3], fill=steel)                       # top rim
    d.rectangle([0, 4, 799, 5], fill=amber)
    for x0, x1 in ((4, 152), (178, 562), (564, 798)):             # recessed panels
        d.rectangle([x0, 8, x1, 156], fill=(8, 12, 16, 255), outline=steel)
        d.rectangle([x0 + 2, 10, x1 - 2, 12], fill=(30, 44, 56, 255))
    for i in range(8):                                            # vent slots
        d.rectangle([156, 20 + i * 16, 174, 26 + i * 16], fill=dark)
    pil.paste(b, (0, 0)); img("SAHudBar", (0, 0, 799, 159))
    # --- queue slot 64x52 at (800,0)
    q = Image.new("RGBA", (64, 52), (14, 20, 26, 255)); dq = ImageDraw.Draw(q)
    dq.rectangle([0, 0, 63, 51], outline=steel); dq.line([(8, 26), (56, 26)], fill=(40, 56, 68, 255))
    pil.paste(q, (800, 0)); img("SAQueueSlot", (800, 0, 863, 51))
    # --- right HUD emblem 96x96 at (864,0): original angular "accord" mark (two interlocking chevrons)
    e = Image.new("RGBA", (96, 96), (0, 0, 0, 0)); de = ImageDraw.Draw(e)
    de.polygon([(8, 70), (48, 14), (88, 70), (74, 70), (48, 34), (22, 70)], fill=(96, 132, 150, 200))
    de.polygon([(20, 84), (48, 46), (76, 84), (64, 84), (48, 62), (32, 84)], fill=(255, 176, 64, 200))
    pil.paste(e, (864, 0)); img("SAHudEmblem", (864, 0, 959, 95))
    # --- small 24x24 buttons (normal / hilite / pushed) row at y=100
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    glyphs = dict(Options="≡", Worker="W", Beacon="B", Chat="C", General="★", UAttack="A", MinMax="▾", MinMaxU="▴", GenBar="+")
    x = 0
    for key, ch in glyphs.items():
        for state, (fillc, edge) in dict(N=((22, 32, 40, 255), steel), H=((40, 58, 70, 255), amber),
                                          P=((12, 16, 20, 255), amber)).items():
            t = Image.new("RGBA", (24, 24), fillc); dt = ImageDraw.Draw(t)
            dt.rectangle([0, 0, 23, 23], outline=edge)
            dt.text((12, 12), ch, font=font, fill=(232, 236, 240, 255), anchor="mm")
            pil.paste(t, (x, 100)); img(f"SABtn{key}{state}", (x, 100, x + 23, 123)); x += 26
    # --- command marker, exp bar, power purchase, generic button frame
    m = Image.new("RGBA", (64, 52), (0, 0, 0, 0)); dm = ImageDraw.Draw(m)
    dm.rectangle([0, 0, 63, 51], outline=amber, width=2); pil.paste(m, (0, 140)); img("SACommandMarker", (0, 140, 63, 191))
    ex = Image.new("RGBA", (128, 8), (255, 176, 64, 220)); pil.paste(ex, (70, 140)); img("SAExpBar", (70, 140, 197, 147))
    pp = Image.new("RGBA", (16, 16), (90, 200, 120, 255)); pil.paste(pp, (70, 150)); img("SAPowerPurchase", (70, 150, 85, 165))
    # --- command glyphs 60x48 at y=196 (original vector marks)
    def glyph(kind):
        g = Image.new("RGBA", (60, 48), (24, 40, 52, 255)); dg = ImageDraw.Draw(g)
        dg.rectangle([0, 0, 59, 47], outline=(120, 190, 220, 255), width=2); Wc = (235, 235, 235, 255)
        if kind == "Stop":
            dg.regular_polygon((30, 24, 16), 8, rotation=22.5, fill=(200, 60, 50, 255), outline=Wc); dg.rectangle([20, 21, 40, 27], fill=Wc)
        elif kind == "Sell":
            dg.ellipse([16, 8, 44, 40], outline=(230, 200, 80, 255), width=3); dg.line([(30, 13), (30, 35)], fill=(230, 200, 80, 255), width=3)
        elif kind == "Rally":
            dg.line([(22, 8), (22, 40)], fill=Wc, width=3); dg.polygon([(23, 9), (44, 15), (23, 22)], fill=(90, 200, 120, 255))
        elif kind == "Cancel":
            dg.line([(18, 12), (42, 36)], fill=(220, 70, 60, 255), width=5); dg.line([(42, 12), (18, 36)], fill=(220, 70, 60, 255), width=5)
        elif kind == "Exit":
            dg.rectangle([14, 10, 32, 38], outline=Wc, width=2); dg.polygon([(30, 24), (46, 14), (46, 34)], fill=(110, 160, 182, 255))
        elif kind == "Evacuate":
            for k in range(3): dg.polygon([(14 + k * 12, 34), (20 + k * 12, 14), (26 + k * 12, 34)], fill=(110, 160, 182, 255))
        elif kind == "Beacon":
            dg.ellipse([22, 10, 38, 26], fill=(255, 176, 64, 255)); dg.line([(30, 26), (30, 40)], fill=Wc, width=3)
        return g
    for i, k in enumerate(("Stop", "Sell", "Rally", "Cancel", "Exit", "Evacuate", "Beacon")):
        pil.paste(glyph(k), (i * 62, 196)); img(f"SAGlyph{k}", (i * 62, 196, i * 62 + 59, 243))
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0)); canvas.alpha_composite(pil)
    tga.save(os.path.join(BASE, "Art", "Textures", "sa_hud.tga"), np.asarray(canvas))
    canvas.save(os.path.join(PREV, "hud_atlas.png"))
    lines = ["; Steel Accord - HUD images (original, tools/gen_hud.py)"]
    for k, (x0, y0, x1, y1) in IMAGES.items():
        lines += [f"MappedImage {k}", "  Texture = sa_hud.tga", "  TextureWidth = 1024", "  TextureHeight = 256",
                  f"  Coords = Left:{x0} Top:{y0} Right:{x1} Bottom:{y1}", "  Status = NONE", "End", ""]
    open(os.path.join(BASE, "Data", "INI", "MappedImages", "HandCreated", "SA_Hud.ini"), "w").write("\n".join(lines))


# ------------------------------------------------------------------ layout
def U(name, rect, status="ENABLED", system=None, input=None, draw=None, children=(), **kw):
    return Win("USER", CB + name if name else "", rect, status=status, system=system, input=input, draw=draw,
               children=children, **kw)


def B(name, rect, status="ENABLED+IMAGE+NOFOCUS+WRAP_CENTERED+ON_MOUSE_DOWN", **kw):
    P = PALETTE
    return Win("PUSHBUTTON", CB + name, rect, status=status, font=("Arial", 10, 1),
               enabled=[("NoImage", (16, 22, 28, 235), P["btn_border"])],
               hilite=[("NoImage", (36, 52, 64, 245), P["btn_hi_border"]), ("NoImage", (36, 52, 64, 245), P["btn_hi_border"])], **kw)


def T(name, rect, centered=1, **kw):
    return Win("STATICTEXT", CB + name, rect, status="ENABLED", font=("Arial", 11, 1),
               extra=[f"STATICTEXTDATA = CENTERED: {centered}"], **kw)


def control_bar():
    Y = BAR_Y
    center = (180, Y + 30, 560, Y + 156)
    cmd = []
    for i in range(14):
        col, row = i % 7, i // 7
        x0, y0 = 186 + col * 53, Y + 38 + row * 56
        cmd.append(B(f"ButtonCommand{i + 1:02d}", (x0, y0, x0 + 50, y0 + 50)))
    beacon = U("BeaconWindow", center, "ENABLED+HIDDEN+SEE_THRU", system="PassSelectedButtonsToParentSystem",
               input="BeaconWindowInput", draw="W3DNoDraw", children=[
                   B("ButtonDeleteBeacon", (190, Y + 110, 300, Y + 136), text="GUI:SA_DeleteBeacon"),
                   Win("ENTRYFIELD", CB + "EditBeaconText", (190, Y + 70, 550, Y + 96), status="ENABLED+IMAGE",
                       extra=["TEXTENTRYDATA = MAXLEN: 64, SECRETTEXT: 0, NUMERICALONLY: 0, ALPHANUMERICALONLY: 0, ASCIIONLY: 0"],
                       enabled=[("NoImage", (8, 12, 16, 255), PALETTE["btn_border"])]),
                   T("StaticTextBeaconLabel", (190, Y + 44, 550, Y + 64), centered=0, text="GUI:SA_BeaconLabel"),
                   B("ButtonClearBeaconText", (440, Y + 110, 550, Y + 136), text="GUI:SA_Clear")])
    underc = U("UnderConstructionWindow", center, "ENABLED+HIDDEN+SEE_THRU", system="PassSelectedButtonsToParentSystem",
               draw="W3DNoDraw", children=[B("ButtonCancelConstruction", (330, Y + 60, 410, Y + 110)),
                                           T("UnderConstructionDesc", (190, Y + 116, 550, Y + 140), centered=0)])
    obs_info = U("ObserverPlayerInfoWindow", center, "ENABLED+SEE_THRU", system="ControlBarObserverSystem", draw="W3DNoDraw",
                 children=[U("WinGeneralPortrait", (190, Y + 40, 250, Y + 100), "ENABLED+HIDDEN+IMAGE"),
                           U("WinFlag", (256, Y + 40, 300, Y + 70), "ENABLED+IMAGE"),
                           B("ButtonCancel", (500, Y + 40, 550, Y + 60), status="ENABLED+IMAGE+ON_MOUSE_DOWN")] +
                          [T(n, (310, Y + 40 + i * 16, 550, Y + 54 + i * 16)) for i, n in enumerate((
                              "StaticTextPlayerName", "StaticTextNumberOfBuildings", "StaticTextNumberOfUnits",
                              "StaticTextNumberOfUnitsKilled", "StaticTextNumberOfUnitsLost"))] +
                          [T(n, (190, Y + 104 + i * 12, 300, Y + 114 + i * 12)) for i, n in enumerate((
                              "StaticTextObsBuildings", "StaticTextObsUnits", "StaticTextObsUnitsLost", "StaticTextObsUnitsKilled"))])
    obs_list = U("ObserverPlayerListWindow", center, "ENABLED+HIDDEN+SEE_THRU", system="ControlBarObserverSystem",
                 draw="W3DNoDraw", children=[B(f"ButtonPlayer{i}", (186 + (i % 4) * 94, Y + 38 + (i // 4) * 56,
                                                                     230 + (i % 4) * 94, Y + 82 + (i // 4) * 56)) for i in range(8)] +
                 [T(f"StaticTextPlayer{i}", (232 + (i % 4) * 94, Y + 50 + (i // 4) * 56, 276 + (i % 4) * 94,
                                              Y + 70 + (i // 4) * 56), centered=0) for i in range(8)])
    ocl = U("OCLTimerWindow", center, "ENABLED+HIDDEN+SEE_THRU", system="PassSelectedButtonsToParentSystem", draw="W3DNoDraw",
            children=[B("OCLTimerSellButton", (190, Y + 60, 250, Y + 110)),
                      Win("PROGRESSBAR", CB + "OCLTimerProgressBar", (260, Y + 80, 550, Y + 96), status="ENABLED",
                          enabled=[("NoImage", (255, 176, 64, 255), PALETTE["btn_border"])]),
                      T("OCLTimerStaticText", (260, Y + 56, 550, Y + 76), centered=0)])
    center_bg = U("CenterBackground", center, "ENABLED+NOFOCUS", system="PassSelectedButtonsToParentSystem",
                  input="GameWinBlockInput", draw="W3DNoDraw",
                  children=[beacon, U("CommandWindow", center, "ENABLED+HIDDEN+SEE_THRU",
                                      system="PassSelectedButtonsToParentSystem", draw="W3DNoDraw", children=cmd),
                            underc, obs_info, obs_list, ocl])
    queue = [B("ButtonQueue01", (572, Y + 14, 636, Y + 66))]
    for i in range(8):
        x0, y0 = 642 + (i % 4) * 38, Y + 14 + (i // 4) * 28
        queue.append(B(f"ButtonQueue{i + 2:02d}", (x0, y0, x0 + 34, y0 + 26)))
    right = U("RightHUD", (564, Y + 8, 798, Y + 156), "ENABLED+NOFOCUS", system="PassSelectedButtonsToParentSystem",
              input="GameWinBlockInput", draw="W3DRightHUDDraw", children=[
                  U("ProductionQueueWindow", (566, Y + 10, 796, Y + 154), "ENABLED+NOFOCUS+SEE_THRU",
                    system="PassSelectedButtonsToParentSystem", input="GameWinDefaultInput", draw="W3DRightHUDDraw", children=queue),
                  U("WinUnitSelected", (566, Y + 10, 796, Y + 154), "ENABLED+NOFOCUS", input="GameWinBlockInput",
                    draw="W3DCommandBarGridDraw", children=[U("CameoWindow", (572, Y + 14, 668, Y + 90), draw="W3DGadgetPushButtonImageDraw")] +
                    [U(f"UnitUpgrade{i + 1}", (572 + i * 44, Y + 100, 612 + i * 44, Y + 132), "ENABLED+IMAGE",
                       input="GameWinBlockInput", draw="W3DGadgetPushButtonImageDraw") for i in range(5)])])
    small = lambda n, r, st="ENABLED+IMAGE+NOFOCUS": B(n, r, status=st)
    root = U("ControlBarParent", (0, Y, 800, 600), "ENABLED+BORDER+SEE_THRU", system="ControlBarSystem",
             input="ControlBarInput", draw="W3DGameWinDefaultDraw", children=[
                 U("Munkee", (0, Y, 800, 600), "ENABLED+IMAGE+NOINPUT+NOFOCUS", draw="W3DNoDraw"),
                 U("BackgroundMarker", (0, Y, 800, 600), "ENABLED+NOINPUT+NOFOCUS", draw="W3DCommandBarBackgroundDraw"),
                 U("BlockLeft", (0, Y, 178, 600), input="GameWinBlockInput", draw="W3DNoDraw"),
                 U("BlockCenter", (178, Y, 564, 600), input="GameWinBlockInput", draw="W3DNoDraw"),
                 U("BlockRight", (564, Y, 800, 600), input="GameWinBlockInput", draw="W3DNoDraw"),
                 center_bg,
                 U("LeftHUD", (8, Y + 10, 150, Y + 154), "ENABLED+NOFOCUS", system="GameWinDefaultSystem",
                   input="LeftHUDInput", draw="W3DLeftHUDDraw"),
                 U("GeneralsExp", (182, Y + 10, 320, Y + 16), "ENABLED+NOFOCUS", system="PassSelectedButtonsToParentSystem",
                   input="GameWinBlockInput", draw="W3DCommandBarGenExpDraw"),
                 U("ExpBarForeground", (182, Y + 10, 320, Y + 16), "ENABLED+IMAGE+NOFOCUS",
                   system="PassSelectedButtonsToParentSystem", input="GameWinBlockInput"),
                 right,
                 small("ButtonIdleWorker", (154, Y + 34, 176, Y + 56), "IMAGE+NOFOCUS"),
                 small("ButtonPlaceBeacon", (154, Y + 60, 176, Y + 82)),
                 small("PopupCommunicator", (154, Y + 86, 176, Y + 108)),
                 small("ButtonOptions", (154, Y + 8, 176, Y + 30)),
                 U("ForegroundMarker", (0, Y, 800, 600), "ENABLED+NOINPUT+NOFOCUS", draw="W3DCommandBarForegroundDraw"),
                 small("ButtonGeneral", (154, Y + 112, 176, Y + 134)),
                 T("MoneyDisplay", (300, Y + 10, 440, Y + 28)),
                 U("PowerWindow", (450, Y + 14, 556, Y + 24), input="GameWinBlockInput", draw="W3DPowerDraw"),
                 small("ButtonSmall", (778, Y - 18, 798, Y - 2), "ENABLED+HIDDEN+IMAGE+NOFOCUS"),
                 small("ButtonLarge", (778, Y - 18, 798, Y - 2)),
                 small("ButtonMedium", (778, Y - 18, 798, Y - 2), "ENABLED+HIDDEN+IMAGE+NOFOCUS"),
                 U("WinUAttack", (154, Y + 138, 176, Y + 154), "ENABLED+IMAGE"),
                 U("OnTopDraw", (0, Y, 800, 600), "ENABLED+NOINPUT+NOFOCUS", draw="W3DCommandBarTopDraw")])
    return layout(root)


def replay_control():
    R = "ReplayControl.wnd:"
    bw = lambda n, x, t: Win("PUSHBUTTON", R + n, (x, 8, x + 60, 32), status="ENABLED+IMAGE+SEE_THRU", text=t, font=("Arial", 11, 1))
    root = Win("USER", R + "ParentReplayControl", (500, 4, 796, 60), status="DRAGABLE+ENABLED+HIDDEN+BORDER+SEE_THRU",
               system="ReplayControlSystem", input="ReplayControlInput", draw="W3DGameWinDefaultDraw",
               enabled=[("NoImage", (12, 18, 24, 220), PALETTE["panel_border"])],
               children=[bw("ButtonSlower", 506, "GUI:SA_Slower"), bw("ButtonFaster", 570, "GUI:SA_Faster"),
                         bw("ButtonPause", 634, "GUI:SA_Pause"), bw("ButtonNextFrame", 698, "GUI:SA_Step"),
                         Win("ENTRYFIELD", R + "TextReplaySpeed", (506, 36, 790, 56),
                             status="ENABLED+IMAGE+NOINPUT+NOFOCUS+BORDER+SEE_THRU",
                             extra=["TEXTENTRYDATA = MAXLEN: 32, SECRETTEXT: 0, NUMERICALONLY: 0, ALPHANUMERICALONLY: 0, ASCIIONLY: 0"])])
    return layout(root)


def scheme():
    Y = BAR_Y
    out = ["; Steel Accord - command bar schemes (original, tools/gen_hud.py)"]
    for side in SIDES:
        out += [f"ControlBarScheme SA_{side}", "  ScreenCreationRes X:800 Y:600", f"  Side {side}",
                "  QueueButtonImage SAQueueSlot", "  RightHUDImage SAHudEmblem",
                "  CommandBarBorderColor R:96 G:132 B:150 A:255", "  BuildUpClockColor R:0 G:0 B:0 A:150",
                "  ButtonBorderBuildColor R:110 G:160 B:182 A:255", "  ButtonBorderActionColor R:90 G:200 B:120 A:255",
                "  ButtonBorderUpgradeColor R:255 G:176 B:64 A:255", "  ButtonBorderSystemColor R:232 G:236 B:240 A:255",
                "  GenBarButtonIn SABtnGenBarN", "  GenBarButtonOn SABtnGenBarH",
                "  ToggleButtonUpIn SABtnMinMaxUN", "  ToggleButtonUpOn SABtnMinMaxUH", "  ToggleButtonUpPushed SABtnMinMaxUP",
                "  ToggleButtonDownIn SABtnMinMaxN", "  ToggleButtonDownOn SABtnMinMaxH", "  ToggleButtonDownPushed SABtnMinMaxP"]
        for key, name in (("Options", "Options"), ("IdleWorker", "Worker"), ("Buddy", "Chat"), ("Beacon", "Beacon"),
                          ("General", "General")):
            out += [f"  {key}ButtonEnable SABtn{name}N", f"  {key}ButtonHightlited SABtn{name}H",
                    f"  {key}ButtonPushed SABtn{name}P", f"  {key}ButtonDisabled SABtn{name}N"]
        out += ["  UAttackButtonEnable SABtnUAttackN", "  UAttackButtonHightlited SABtnUAttackH", "  UAttackButtonPushed SABtnUAttackP",
                "  MinMaxButtonEnable SABtnMinMaxN", "  MinMaxButtonHightlited SABtnMinMaxH", "  MinMaxButtonPushed SABtnMinMaxP",
                f"  MinMaxUL X:778 Y:{Y - 18}", f"  MinMaxLR X:798 Y:{Y - 2}",
                f"  GeneralUL X:154 Y:{Y + 112}", f"  GeneralLR X:176 Y:{Y + 134}",
                f"  UAttackUL X:154 Y:{Y + 138}", f"  UAttackLR X:176 Y:{Y + 154}",
                f"  OptionsUL X:154 Y:{Y + 8}", f"  OptionsLR X:176 Y:{Y + 30}",
                f"  WorkerUL X:154 Y:{Y + 34}", f"  WorkerLR X:176 Y:{Y + 56}",
                f"  ChatUL X:154 Y:{Y + 86}", f"  ChatLR X:176 Y:{Y + 108}",
                f"  BeaconUL X:154 Y:{Y + 60}", f"  BeaconLR X:176 Y:{Y + 82}",
                f"  PowerBarUL X:450 Y:{Y + 14}", f"  PowerBarLR X:556 Y:{Y + 24}",
                f"  MoneyUL X:300 Y:{Y + 10}", f"  MoneyLR X:440 Y:{Y + 28}",
                "  CommandMarkerImage SACommandMarker", "  ExpBarForegroundImage SAExpBar", "  PowerPurchaseImage SAPowerPurchase",
                "  ImagePart", f"    Position X:0 Y:{Y}", "    Size X:800 Y:160", "    ImageName SAHudBar", "    Layer 5", "  End",
                "End", ""]
    open(os.path.join(BASE, "Data", "INI", "ControlBarScheme.ini"), "w").write("\n".join(out))


SYSTEM_BUTTONS = [  # engine-required command buttons (ControlBar.cpp looks these up by name)
    ("Command_CancelConstruction", "DOZER_CONSTRUCT_CANCEL", "SAGlyphCancel", "Cancel construction", ""),
    ("Command_CancelUnitCreate", "CANCEL_UNIT_BUILD", "SAGlyphCancel", "Cancel production", ""),
    ("Command_CancelUpgradeCreate", "CANCEL_UPGRADE", "SAGlyphCancel", "Cancel upgrade", ""),
    ("Command_Evacuate", "EVACUATE", "SAGlyphEvacuate", "Evacuate", "Options = OK_FOR_MULTI_SELECT"),
    ("Command_PlaceBeacon", "PLACE_BEACON", "SAGlyphBeacon", "Place beacon", "Options = NEED_TARGET_POS\n  CursorName = SAPlaceBeacon\n  InvalidCursorName = SAInvalid"),
    ("Command_Sell", "SELL", "SAGlyphSell", "Sell", ""),
    ("Command_SetRallyPoint", "SET_RALLY_POINT", "SAGlyphRally", "Rally point", "Options = NEED_TARGET_POS\n  CursorName = SARallyPoint"),
    ("Command_Stop", "STOP", "SAGlyphStop", "Stop", "Options = OK_FOR_MULTI_SELECT"),
    ("Command_StructureExit", "EXIT_CONTAINER", "SAGlyphExit", "Exit structure", ""),
    ("Command_TransportExit", "EXIT_CONTAINER", "SAGlyphExit", "Exit transport", ""),
]
NON_COMMANDS = [("NonCommand_Beacon", "Beacon"), ("NonCommand_BriefingHistory", "Briefing history"),
                ("NonCommand_Communicator", "Chat"), ("NonCommand_GeneralsExperience", "Commander ranks"),
                ("NonCommand_IdleWorker", "Idle builder"), ("NonCommand_Options", "Options"),
                ("NonCommand_UpDown", "Show / hide command bar")]


def system_buttons():
    out = ["; Steel Accord - engine-required system command buttons (original text/images, tools/gen_hud.py)"]
    for name, cmd, image, text, opts in SYSTEM_BUTTONS:
        lab = "CONTROLBAR:SA_" + name
        HUD_STRINGS[lab] = text; HUD_STRINGS[lab + "_Tip"] = text
        out += [f"CommandButton {name}", f"  Command = {cmd}"] + ([f"  {opts}"] if opts else []) + [
            f"  TextLabel = {lab}", f"  ButtonImage = {image}", "  ButtonBorderType = SYSTEM", f"  DescriptLabel = {lab}_Tip", "End", ""]
    for name, text in NON_COMMANDS:
        lab = "CONTROLBAR:SA_" + name
        HUD_STRINGS[lab] = text
        out += [f"CommandButton {name}", f"  TextLabel = {lab}", f"  DescriptLabel = {lab}", "End", ""]
    p = os.path.join(BASE, "Data", "INI", "CommandButton", "SA_SystemButtons.ini")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write("\n".join(out).replace("\\n", "\n"))


def write(rel, text):
    p = os.path.join(BASE, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", newline="\n").write(text)


def main():
    os.makedirs(PREV, exist_ok=True)
    hud_art()
    write("Window/ControlBar.wnd", control_bar())
    write("Window/ReplayControl.wnd", replay_control())
    scheme()
    system_buttons()
    print("hud: images", len(IMAGES))


if __name__ == "__main__":
    main()

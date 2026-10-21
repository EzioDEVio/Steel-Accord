#!/usr/bin/env python3
"""Auto-generate functional Steel Accord window layouts for engine screens not yet custom-designed.

For each required screen, the interface contract (window names, types, status flags,
callbacks, gadget configuration) is read from a reference layout via pzlib.wndcontract; all
geometry is computed here (simple flow layout), and all visuals use the Steel Accord palette.
Text uses our own string labels (GUI:SA_Auto_<control>), generated as readable English from the
control name, so no reference text is reused. Custom-designed screens (MainMenu, ControlBar,
ReplayControl, IME windows) are never overwritten.

usage: gen_autolayouts.py <contract_dir> <screen.wnd> [...]   (paths relative to Window/)
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import wndcontract as C
from pzlib.wnd import Win, layout, PALETTE

BASE = os.path.join(ROOT, "content", "base")
CUSTOM = {"Menus/MainMenu.wnd", "ControlBar.wnd", "ReplayControl.wnd", "IMECandidateWindow.wnd", "IMEStatusWindow.wnd"}
STR_FILE = os.path.join(ROOT, "content", "base_src", "auto_layout_strings.str")
ROW = {"PUSHBUTTON": 28, "STATICTEXT": 18, "LISTBOX": 120, "COMBOBOX": 22, "CHECKBOX": 18, "RADIOBUTTON": 18,
       "HORZSLIDER": 18, "VERTSLIDER": 80, "ENTRYFIELD": 22, "PROGRESSBAR": 14, "USER": 40, "TABCONTROL": 24}
STRINGS = {}


def label_for(name):
    short = name.split(":")[-1]
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", re.sub(r"^(Button|StaticText|Text|Label|Static|Check|Combo|Slider|Win)", "", short))
    text = words.strip() or short
    key = "GUI:SA_Auto_" + re.sub(r"\W", "", short)
    STRINGS[key] = text
    return key


def build(w, rect, depth=0):
    f = w["fields"]
    wtype = f.get("WINDOWTYPE", "USER")
    name = f.get("NAME", '""').strip('"')
    status = f.get("STATUS", "ENABLED")
    cb = {k: f.get(k, '"[None]"').strip('"') for k in ("SYSTEMCALLBACK", "INPUTCALLBACK", "TOOLTIPCALLBACK", "DRAWCALLBACK")}
    cb = {k: (None if v == "[None]" else v) for k, v in cb.items()}
    extra = [f"{k} = {v}" for k, v in f.items() if k.endswith("DATA")]
    text = None
    if wtype in ("PUSHBUTTON", "CHECKBOX", "RADIOBUTTON") or (wtype == "STATICTEXT" and "HIDDEN" not in status):
        text = label_for(name) if name else None
    P = PALETTE
    enabled = None
    if wtype == "USER" and depth == 0:
        enabled = [("SAShellBackdrop", (120, 128, 136, 255), (0, 0, 0, 0))] if rect == (0, 0, 800, 600) else \
                  [("NoImage", P["panel"], P["panel_border"])]
    elif wtype == "USER" and w["children"]:
        enabled = [("NoImage", (14, 20, 26, 160), P["panel_border"])]
    elif wtype in ("LISTBOX", "ENTRYFIELD", "COMBOBOX", "PROGRESSBAR"):
        enabled = [("NoImage", (8, 12, 16, 235), P["btn_border"])] * 3
    kids = []
    if w["children"]:
        x0, y0, x1, y1 = rect
        pad = 8 if depth else 24
        cx, cy, colw = x0 + pad, y0 + pad + (16 if depth == 0 else 0), max(60, (x1 - x0 - 3 * pad) // 2)
        col = 0
        for ch in w["children"]:
            ct = ch["fields"].get("WINDOWTYPE", "USER")
            hidden = "HIDDEN" in ch["fields"].get("STATUS", "")
            h = 10 if hidden else ROW.get(ct, 24)
            if ch["children"] and not hidden:
                h = min(y1 - y0 - 2 * pad, 40 + 26 * len(ch["children"]))
            if cy + h > y1 - pad and col == 0:
                col, cy = 1, y0 + pad + (16 if depth == 0 else 0)
            cxx = cx + col * (colw + pad)
            r = (cxx, cy, min(x1 - pad, cxx + colw), min(y1 - pad, cy + h))
            kids.append(build(ch, r, depth + 1))
            cy += h + 4
    return Win(wtype, name, rect, status=status, text=text, children=kids, extra=extra, enabled=enabled,
               system=cb["SYSTEMCALLBACK"], input=cb["INPUTCALLBACK"], draw=cb["DRAWCALLBACK"], tooltip=cb["TOOLTIPCALLBACK"],
               font=("Arial", 13 if depth == 0 else 11, 1 if wtype == "PUSHBUTTON" else 0))


def root_rect(name):
    # popups and in-game dialogs get a centred panel, full-screen menus the whole screen
    small = ("Popup", "MessageBox", "Quit", "Diplomacy", "InGame", "GeneralsExp", "Disconnect", "Observer",
             "CRCMismatch", "IMEStatus", "ReplayControl", "Beacon", "Chat", "Control", "Tool")
    return (160, 110, 640, 490) if any(s in name for s in small) else (0, 0, 800, 600)


def main(contract_dir, screens):
    made = []
    for rel in screens:
        if rel in CUSTOM:
            continue
        src = os.path.join(contract_dir, rel)
        lay, root = C.parse(src)
        w = build(root, root_rect(rel))
        text = layout(w, init=lay.get("LAYOUTINIT", "[None]").strip(), update=lay.get("LAYOUTUPDATE", "[None]").strip(),
                      shutdown=lay.get("LAYOUTSHUTDOWN", "[None]").strip())
        out = os.path.join(BASE, "Window", rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", newline="\n").write(text)
        made.append(rel)
    old = {}
    if os.path.exists(STR_FILE):
        for blk in open(STR_FILE).read().split("\nEND\n"):
            ls = [l for l in blk.strip().splitlines() if l and not l.startswith("//")]
            if len(ls) >= 2: old[ls[0]] = ls[1].strip('"')
    old.update(STRINGS)
    with open(STR_FILE, "w") as fo:
        for k in sorted(old):
            fo.write(f'{k}\n"{old[k]}"\nEND\n')
    print("auto layouts:", ", ".join(made))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

"""Writer for the engine's text window-layout format (.wnd, FILE_VERSION = 2).

Grammar follows the parser in Core/GameEngine/Source/GameClient/GUI/GameWindowManagerScript.cpp.
Steel Accord layouts are authored as Python specs (tools/gen_shell.py): names, window types and
callbacks are the engine's interface contract; geometry, colours, images, fonts and text are ours.
Original Steel Accord tooling.
"""

PALETTE = dict(
    text=(232, 236, 240, 255), text_border=(10, 14, 18, 255),
    text_dis=(110, 118, 126, 255), text_dis_border=(20, 22, 24, 255),
    text_hi=(255, 196, 92, 255), text_hi_border=(10, 14, 18, 255),
    panel=(18, 26, 34, 220), panel_border=(96, 132, 150, 255),
    btn=(30, 44, 56, 235), btn_border=(110, 160, 182, 255),
    btn_hi=(52, 76, 92, 245), btn_hi_border=(255, 196, 92, 255),
    btn_dis=(26, 30, 34, 200), btn_dis_border=(60, 66, 72, 255),
    clear=(0, 0, 0, 0),
)


def _c(c): return " ".join(str(int(v)) for v in c)


def drawdata(entries):
    """9 entries of (image, color, border)."""
    entries = list(entries) + [("NoImage", PALETTE["clear"], PALETTE["clear"])] * (9 - len(entries))
    return (",\n" + " " * 20).join(f"IMAGE: {i}, COLOR: {_c(c)}, BORDERCOLOR: {_c(b)}" for i, c, b in entries[:9])


class Win:
    def __init__(self, wtype, name, rect, status="ENABLED", style=None, text=None, children=(),
                 system=None, input=None, draw=None, tooltip=None, font=("Arial", 12, 0), header=None,
                 enabled=None, disabled=None, hilite=None, extra=(), tooltiptext=None):
        self.wtype, self.name, self.rect = wtype, name, rect   # rect = (x0, y0, x1, y1) in 800x600 space
        self.status = status
        self.style = style or {"USER": "USER", "STATICTEXT": "STATICTEXT"}.get(wtype, wtype + "+MOUSETRACK")
        self.text, self.children = text, list(children)
        self.cb = dict(SYSTEMCALLBACK=system, INPUTCALLBACK=input, TOOLTIPCALLBACK=tooltip, DRAWCALLBACK=draw)
        self.font, self.header, self.extra, self.tooltiptext = font, header, list(extra), tooltiptext
        P = PALETTE
        if wtype == "PUSHBUTTON":
            self.enabled = enabled or [("NoImage", P["btn"], P["btn_border"])]
            self.disabled = disabled or [("NoImage", P["btn_dis"], P["btn_dis_border"])]
            self.hilite = hilite or [("NoImage", P["btn_hi"], P["btn_hi_border"]), ("NoImage", P["btn_hi"], P["btn_hi_border"])]
        else:
            self.enabled = enabled or [("NoImage", P["clear"], P["clear"])]
            self.disabled = disabled or [("NoImage", P["clear"], P["clear"])]
            self.hilite = hilite or [("NoImage", P["clear"], P["clear"])]

    def emit(self, ind=0):
        sp = " " * ind
        x0, y0, x1, y1 = self.rect
        P = PALETTE
        L = [f"{sp}WINDOW",
             f"{sp}  WINDOWTYPE = {self.wtype};",
             f"{sp}  SCREENRECT = UPPERLEFT: {x0} {y0},",
             f"{sp}               BOTTOMRIGHT: {x1} {y1},",
             f"{sp}               CREATIONRESOLUTION: 800 600;",
             f'{sp}  NAME = "{self.name}";',
             f"{sp}  STATUS = {self.status};",
             f"{sp}  STYLE = {self.style};"]
        for k, v in self.cb.items():
            L.append(f'{sp}  {k} = "{v or "[None]"}";')
        f = self.font
        L.append(f'{sp}  FONT = NAME: "{f[0]}", SIZE: {f[1]}, BOLD: {f[2]};')
        L.append(f'{sp}  HEADERTEMPLATE = "{self.header or "[NONE]"}";')
        L.append(f"{sp}  TOOLTIPDELAY = -1;")
        if self.tooltiptext:
            L.append(f'{sp}  TOOLTIPTEXT = "{self.tooltiptext}";')
        if self.text:
            L.append(f'{sp}  TEXT = "{self.text}";')
        L.append(f"{sp}  TEXTCOLOR = ENABLED:  {_c(P['text'])}, ENABLEDBORDER:  {_c(P['text_border'])},")
        L.append(f"{sp}              DISABLED: {_c(P['text_dis'])}, DISABLEDBORDER: {_c(P['text_dis_border'])},")
        L.append(f"{sp}              HILITE:   {_c(P['text_hi'])}, HILITEBORDER:   {_c(P['text_hi_border'])};")
        for key, dd in (("ENABLEDDRAWDATA", self.enabled), ("DISABLEDDRAWDATA", self.disabled), ("HILITEDRAWDATA", self.hilite)):
            L.append(f"{sp}  {key} = " + drawdata(dd).replace("\n" + " " * 20, "\n" + sp + " " * 20) + ";")
        for e in self.extra:
            L.append(f"{sp}  {e};")
        for ch in self.children:
            L.append(f"{sp}  CHILD")
            L.append(ch.emit(ind + 2))
        if self.children:
            L.append(f"{sp}  ENDALLCHILDREN")
        L.append(f"{sp}END")
        return "\n".join(L)


def layout(root, init=None, update=None, shutdown=None):
    head = ["FILE_VERSION = 2;", "STARTLAYOUTBLOCK",
            f"  LAYOUTINIT = {init or '[None]'};", f"  LAYOUTUPDATE = {update or '[None]'};",
            f"  LAYOUTSHUTDOWN = {shutdown or '[None]'};", "ENDLAYOUTBLOCK"]
    return "\n".join(head) + "\n" + root.emit(0) + "\n"

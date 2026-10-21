"""Extract the *interface contract* of an engine window layout: the tree of window names, window
types, status/style flags, callbacks and gadget configuration keys that the engine code depends on.

Used only as a reference for which named controls our own layouts must provide. Geometry,
images, colours, fonts and text are deliberately NOT extracted — Steel Accord layouts author
their own (tools/gen_shell.py). Original Steel Accord tooling.
"""
import re

KEEP = ("WINDOWTYPE", "NAME", "STATUS", "STYLE", "SYSTEMCALLBACK", "INPUTCALLBACK", "TOOLTIPCALLBACK",
        "DRAWCALLBACK", "LISTBOXDATA", "COMBOBOXDATA", "SLIDERDATA", "RADIOBUTTONDATA", "TEXTENTRYDATA",
        "STATICTEXTDATA", "TABCONTROLDATA")


def parse(path):
    s = open(path, encoding="latin-1").read()
    layout = dict(re.findall(r"(LAYOUTINIT|LAYOUTUPDATE|LAYOUTSHUTDOWN)\s*=\s*([^;]*);", s))
    body = s[s.index("ENDLAYOUTBLOCK") + len("ENDLAYOUTBLOCK"):]
    toks = re.findall(r"\bWINDOW\b|\bENDALLCHILDREN\b|\bCHILD\b|\bEND\b|[A-Z]+DATA\s*=[^;]*;|[A-Z]+\s*=[^;]*;", body)
    root, stack = None, []
    for t in toks:
        if t == "WINDOW":
            w = dict(children=[], fields={})
            if stack:
                stack[-1]["children"].append(w)
            else:
                root = w
            stack.append(w)
        elif t == "END":
            stack.pop()
        elif t in ("CHILD", "ENDALLCHILDREN"):
            continue
        else:
            k, v = t.split("=", 1)
            k = k.strip()
            if k in KEEP and stack:
                stack[-1]["fields"][k] = " ".join(v.strip().rstrip(";").split())
    return layout, root


def walk(w, depth=0):
    yield depth, w
    for c in w["children"]:
        yield from walk(c, depth + 1)

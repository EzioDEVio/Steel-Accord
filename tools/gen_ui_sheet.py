#!/usr/bin/env python3
"""Compose the original dev UI sheet content/dev/Art/Textures/pzui_dev.tga (256x256).

Layout (pixels, inclusive coords used in PZDev_Images.ini):
  Kestrel unit button   (0,0)-(119,95)      Field Depot button  (0,128)-(119,223)
  glyphs 60x48: attack-move (128,0) guard (192,0) stop (128,48) rally (192,48) sell (128,96)
Icons are renders of our own exported W3D models (gen_kestrel.py, gen_fielddepot.py).
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga

OUT = os.path.join(ROOT, "content", "dev", "Art", "Textures", "pzui_dev.tga")
EDGE = (120, 190, 220)


def unit_icon(npy, tag):
    ic = Image.fromarray(np.load(npy)).resize((120, 96), Image.LANCZOS)
    d = ImageDraw.Draw(ic)
    d.rectangle([0, 0, 119, 95], outline=EDGE, width=2)
    d.rectangle([3, 3, 22, 12], fill=tag)
    return ic


def glyph(kind):
    g = Image.new("RGBA", (60, 48), (24, 40, 52, 255)); d = ImageDraw.Draw(g)
    d.rectangle([0, 0, 59, 47], outline=EDGE, width=2)
    W = (235, 235, 235)
    if kind == "attackmove":
        d.polygon([(50, 22), (32, 7), (32, 16), (12, 16), (12, 28), (32, 28), (32, 37)], fill=(235, 120, 60))
        d.line([(8, 40), (20, 40)], fill=W, width=3)
    elif kind == "guard":
        d.polygon([(30, 8), (46, 14), (44, 30), (30, 41), (16, 30), (14, 14)], outline=W, fill=(60, 120, 170))
        d.line([(30, 14), (30, 34)], fill=W, width=3)
    elif kind == "stop":
        d.regular_polygon((30, 24, 16), 8, rotation=22.5, fill=(200, 60, 50), outline=W)
        d.rectangle([20, 21, 40, 27], fill=W)
    elif kind == "rally":
        d.line([(22, 8), (22, 40)], fill=W, width=3)
        d.polygon([(23, 9), (44, 15), (23, 22)], fill=(90, 200, 120))
        d.ellipse([14, 36, 30, 44], outline=W, width=2)
    elif kind == "sell":
        d.ellipse([16, 8, 44, 40], outline=(230, 200, 80), width=3)
        d.line([(30, 13), (30, 35)], fill=(230, 200, 80), width=3)
        d.arc([22, 14, 38, 24], 90, 360, fill=(230, 200, 80), width=3)
        d.arc([22, 23, 38, 33], 270, 180, fill=(230, 200, 80), width=3)
    return g


def main():
    sheet = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    sheet.paste(unit_icon(os.path.join(ROOT, "build", "kestrel_icon.npy"), EDGE), (0, 0))
    sheet.paste(unit_icon(os.path.join(ROOT, "build", "fielddepot_icon.npy"), (230, 170, 60)), (0, 128))
    for (x, y), k in (((128, 0), "attackmove"), ((192, 0), "guard"), ((128, 48), "stop"),
                      ((192, 48), "rally"), ((128, 96), "sell")):
        sheet.paste(glyph(k), (x, y))
    tga.save(OUT, np.asarray(sheet))
    sheet.resize((512, 512), Image.NEAREST).save(os.path.join(ROOT, "build", "previews", "pzui_sheet_2x.png"))


if __name__ == "__main__":
    main()

"""Steel Accord - B3 support-power icons for the bomber squadrons (bpy 5.x + Pillow). Original work.

Renders each HD bomber (godot/assets/units3d/<b52|b1|b2>_hd/*.glb) once from a high three-quarter view with a
transparent background (Cycles CPU, 512 x 320), then composites formation icons at 256 x 160 RGBA (the size of the
existing power icons):
  godot/assets/ui/powers/stealth_squadron.png        three flying wings in echelon
  godot/assets/ui/powers/stealth_squadron_heavy.png  five flying wings in echelon
  godot/assets/ui/powers/strike_package.png          flying wing lead, swing-wing pair, two eight-engine bombers trailing
Run:  python3 -I tools/art/icons_bomber_powers.py
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airkit as K  # noqa: E402

L = K.L
import bpy  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402

OUT = os.path.join(K.REPO, "godot", "assets", "ui", "powers")
SIZE = (256, 160)


def render(aid, tmp):
    L.reset_scene()
    bpy.ops.import_scene.gltf(filepath=os.path.join(K.OUT3D, f"{aid}_hd", f"{aid}_hd.glb"))
    cam = L.setup_preview_scene(ground=False)
    sc = bpy.context.scene
    sc.cycles.samples = 12
    sc.render.film_transparent = True
    L.aim(cam, (0, 0, 3.0), -150, 58, 260, ortho=60)       # tail-on high view: nose towards the top-right
    p = os.path.join(tmp, f"{aid}.png")
    sc.render.resolution_x, sc.render.resolution_y = 640, 640
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    im = Image.open(p).convert("RGBA")
    return im.crop(im.getbbox())


def place(canvas, im, cx, cy, w):
    h = int(im.height * w / im.width)
    s = im.resize((int(w), max(1, h)), Image.LANCZOS)
    sh = Image.new("RGBA", s.size, (0, 0, 0, 0))
    a = s.split()[3].point(lambda v: int(v * 0.45))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(2)))
    canvas.alpha_composite(sh, (int(cx - s.width / 2 + 3), int(cy - s.height / 2 + 4)))
    canvas.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="icons_b3_")
    ims = {a: render(a, tmp) for a in ("b2", "b1", "b52")}
    # stealth squadron: three in echelon (lead top right)
    c = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    for i in range(3)[::-1]:
        place(c, ims["b2"], 186 - i * 58, 42 + i * 38, 112)
    c.save(os.path.join(OUT, "stealth_squadron.png"))
    c = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    for i in range(5)[::-1]:
        place(c, ims["b2"], 214 - i * 44, 26 + i * 27, 84)
    c.save(os.path.join(OUT, "stealth_squadron_heavy.png"))
    c = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    for cx, cy, w, a in ((70, 118, 104, "b52"), (150, 136, 104, "b52"), (96, 68, 72, "b1"), (172, 88, 72, "b1"), (196, 32, 84, "b2")):
        place(c, ims[a], cx, cy, w)
    c.save(os.path.join(OUT, "strike_package.png"))
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    print("icons ->", OUT)


if __name__ == "__main__":
    main()

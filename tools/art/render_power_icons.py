"""Steel Accord - B3 support-power icons rendered from the game's own 3D aircraft models (bpy 5.x, Cycles CPU).

Run:  python3 -I tools/art/render_power_icons.py [id ...]
Out:  godot/assets/ui/powers/<power id>.png  (256 x 160 RGBA, transparent background, like the other power icons)

Each icon is the aircraft model (godot/assets/units3d/<model>/<model>.glb, original kit geometry) seen from a
3/4 view above, with a small 2D glyph drawn on top with Pillow: parachute canopies for the airdrops, gun tracers
for the gunship, an open nose and a tank silhouette for the airlift. Original work; no external imagery.
"""
import math
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "godot", "assets", "ui", "powers")
U3D = os.path.join(REPO, "godot", "assets", "units3d")

# power id: (model id, azimuth deg, elevation deg, glyph, NoseDoor angle deg)
ICONS = {
    "gunship": ("ac130", -125, 30, "tracers", 0),
    "airborne_armor": ("c17", -130, 28, "chutes", 0),
    "airlift": ("c5", -50, 22, "tank", 62),
    "ir_airborne_armor": ("ir_c130", -130, 28, "chutes", 0),
}
W, H = 512, 320


def scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 20
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    w = bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.6, 0.65, 0.72, 1); bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.4
    sun.rotation_euler = Euler((math.radians(40), 0, math.radians(-30)))
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam); sc.camera = cam
    return sc, cam


def render_model(mid, az, el, nose_deg, path):
    sc, cam = scene()
    bpy.ops.import_scene.gltf(filepath=os.path.join(U3D, mid, f"{mid}.glb"))
    objs = [o for o in sc.objects if o.type == "MESH"]
    for o in objs:
        if o.name.startswith("NoseDoor") and nose_deg:
            o.rotation_mode = "XYZ"
            o.rotation_euler.x += math.radians(nose_deg)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    size = (hi - lo).length
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size * 0.86
    cam.location = c + d * size * 3
    cam.rotation_euler = (c - cam.location).normalized().to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = size * 10
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def glyph(im, kind):
    d = ImageDraw.Draw(im)
    if kind == "chutes":
        for k, (x, y) in enumerate(((60, 52), (102, 36), (144, 52))):
            r = 30
            d.pieslice((x - r, y - r, x + r, y + r), 180, 360, fill=(222, 214, 170, 255), outline=(40, 40, 34, 255), width=4)
            for t in (-1, 0, 1):
                d.line((x + t * r * 0.9, y, 102, 128), fill=(40, 40, 34, 230), width=2)
        d.rectangle((78, 126, 126, 142), fill=(200, 160, 70, 255), outline=(30, 30, 26, 255), width=3)
    elif kind == "tracers":
        for k in range(5):
            x0, y0 = 300 + k * 16, 168 + k * 6
            d.line((x0, y0, x0 + 120, y0 + 120), fill=(255, 196, 80, 235), width=5)
        d.ellipse((392, 268, 452, 300), fill=(255, 150, 60, 200))
    elif kind == "tank":
        x, y = 40, 236
        d.rounded_rectangle((x, y + 22, x + 120, y + 52), 10, fill=(200, 160, 70, 255), outline=(30, 30, 26, 255), width=4)
        d.rectangle((x + 30, y + 4, x + 86, y + 26), fill=(200, 160, 70, 255), outline=(30, 30, 26, 255), width=4)
        d.line((x + 86, y + 14, x + 150, y + 10), fill=(30, 30, 26, 255), width=7)
        d.line((x + 86, y + 14, x + 148, y + 10), fill=(200, 160, 70, 255), width=3)
        d.polygon([(x + 170, y + 40), (x + 200, y + 28), (x + 200, y + 52)], fill=(232, 238, 240, 255))


def main():
    ids = sys.argv[1:] or list(ICONS)
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="sa_icons_")
    for pid in ids:
        mid, az, el, kind, nose = ICONS[pid]
        raw = os.path.join(tmp, pid + ".png")
        render_model(mid, az, el, nose, raw)
        im = Image.open(raw).convert("RGBA")
        # dark outline so the silhouette reads on the dark power buttons
        a = im.split()[3].filter(ImageFilter.MaxFilter(7))
        base = Image.new("RGBA", im.size, (14, 20, 24, 0)); base.putalpha(a.point(lambda v: min(v, 200)))
        base.alpha_composite(im)
        glyph(base, kind)
        base.resize((256, 160), Image.LANCZOS).save(os.path.join(OUT, pid + ".png"))
        print("ICON", pid, os.path.join(OUT, pid + ".png"))


if __name__ == "__main__":
    main()

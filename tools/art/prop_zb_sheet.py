"""Steel Accord - contact sheet of the Zagros Basin map props (composited from each generator's RTS preview render).

Run:  python3 -I prop_zb_sheet.py <previews_dir> <props_dir> <out.png>
      previews_dir must hold prop_<name>_rts.png (from `prop_<name>.py <out> --previews <dir> --only rts`).
Labels list node names, triangle counts and size measured from the exported GLBs (Blender import).
"""
import os, sys, math
import bpy
from PIL import Image, ImageDraw, ImageFont

PREV, PROPS, OUT = sys.argv[1:4]
NAMES = ["oil_derrick", "village_house", "ruin", "rock_cluster", "date_palm", "scrub", "pylon"]
info = {}
for n in NAMES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(PROPS, n + ".glb"))
    tris = 0; lo = [1e9] * 3; hi = [-1e9] * 3; nodes = []
    for o in bpy.context.scene.objects:
        nodes.append(o.name)
        if o.type != "MESH":
            continue
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for k in range(3):
                lo[k] = min(lo[k], w[k]); hi[k] = max(hi[k], w[k])
    info[n] = (tris, [hi[k] - lo[k] for k in range(3)], sorted(nodes), os.path.getsize(os.path.join(PROPS, n + ".glb")))
W, H = 640, 400
cols = 4
rows = math.ceil(len(NAMES) / cols)
sheet = Image.new("RGB", (cols * W, rows * (H + 70) + 60), (24, 24, 26))
dr = ImageDraw.Draw(sheet)
try:
    f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", 20); f2 = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    f1 = f2 = ImageFont.load_default()
dr.text((14, 16), "Steel Accord - Zagros Basin map props (original, procedurally modelled + baked in Blender; RTS 52 deg preview renders)",
        fill=(235, 235, 235), font=f1)
for i, n in enumerate(NAMES):
    x, y = (i % cols) * W, 60 + (i // cols) * (H + 70)
    im = Image.open(os.path.join(PREV, f"prop_{n}_rts.png")).convert("RGB").resize((W, H))
    sheet.paste(im, (x, y))
    tris, dim, nodes, size = info[n]
    dr.text((x + 10, y + H + 6), f"{n}.glb", fill=(250, 220, 120), font=f1)
    dr.text((x + 10, y + H + 32), f"{tris} tris  |  {dim[0]:.1f} x {dim[1]:.1f} x {dim[2]:.1f} m  |  {size // 1024} KB",
            fill=(220, 220, 220), font=f2)
    dr.text((x + 10, y + H + 50), "nodes: " + ", ".join(nodes)[:84], fill=(170, 170, 170), font=f2)
sheet.save(OUT)
print("sheet", OUT, {k: v[0] for k, v in info.items()})

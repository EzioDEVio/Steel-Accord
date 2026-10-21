#!/usr/bin/env python3
"""Original replacements for engine-hardcoded 'system' assets (file names the engine code loads directly).

The engine references these by fixed file name (see RECON: grep of .tga/.w3d literals in
GameEngineDevice). The name is the interface; every pixel/vertex here is procedurally authored.
Output: content/base/Art/Textures/*.tga, content/base/Art/W3D/SCMNODE.W3D
"""
import os, sys, math
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pzlib import tga
from pzlib.meshbuild import Mesh
from gen_kestrel import noise, export_model

TEX = os.path.join(ROOT, "content", "base", "Art", "Textures")
W3D = os.path.join(ROOT, "content", "base", "Art", "W3D")
os.makedirs(TEX, exist_ok=True); os.makedirs(W3D, exist_ok=True)


def save(name, arr): tga.save(os.path.join(TEX, name), np.clip(arr, 0, 255).astype(np.uint8))


def rgba(h, w, rgb, a): return np.dstack([np.broadcast_to(np.array(rgb, float), (h, w, 3)), a])


def main():
    y, x = np.mgrid[0:64, 0:64] / 63.0
    edge = np.minimum.reduce([x, y, 1 - x, 1 - y])
    frame = np.clip(1 - edge * 14, 0, 1) * 200 + 40
    save("TBBib.tga", rgba(64, 64, (90, 230, 120), frame))          # placement footprint: valid
    save("TBRedBib.tga", rgba(64, 64, (240, 70, 60), frame))        # placement footprint: blocked
    yy, xx = np.mgrid[0:16, 0:64] / np.array([15.0, 63.0])[:, None, None]
    core = np.exp(-((yy[0] - 0.5) / 0.18) ** 2)
    save("EXLaser.tga", np.dstack([core * 255, core * 230 + 20, core * 160 + 60, core * 255]))
    save("missing.tga", np.dstack([((x * 8).astype(int) + (y * 8).astype(int)) % 2 * 200 + 40] * 3 + [np.full((64, 64), 255.0)]))
    n = noise(128, 128, 8, seed=401) * 255
    save("Noise0000.tga", np.dstack([n, n, n]))
    save("TSNoiseUrb.tga", np.dstack([n * 0.6 + 60] * 3))
    c = noise(256, 256, 4, seed=402)
    save("cloudmap.tga", np.dstack([np.full((256, 256), 255.0)] * 3 + [np.clip((c - 0.45) * 600, 0, 140)]))
    save("TSCloudMed.tga", np.dstack([np.clip(c * 255 + 40, 0, 255)] * 3))
    ry, rx = np.mgrid[0:64, 0:64] / 63.0
    r = np.hypot(rx - 0.5, ry - 0.5) * 2
    save("shadow.tga", np.dstack([np.zeros((64, 64))] * 3 + [np.clip(1 - r, 0, 1) * 200]))
    save("TWAlphaEdge.tga", np.dstack([np.full((64, 64), 255.0)] * 3 + [rx * 255]))
    save("EdgingTemplate.tga", np.dstack([np.full((64, 64), 255.0)] * 3 + [np.clip(1 - edge * 6, 0, 1) * 255]))
    save("alphaclip.tga", np.dstack([np.full((64, 64), 255.0)] * 3 + [(ry > 0.5) * 255.0]))
    w = (np.sin(rx * math.tau * 4) * 0.5 + 0.5) * 255
    for nm in ("wave1.tga", "wave2.tga"):
        save(nm, np.dstack([w * 0.4, w * 0.6 + 40, w * 0.8 + 60, w]))
    wv = noise(256, 256, 6, seed=403) * 255
    save("wave256.tga", np.dstack([wv * 0.3 + 20, wv * 0.5 + 50, wv * 0.6 + 80]))
    save("WaterSurfaceBubbles.tga", np.dstack([np.full((64, 64), 255.0)] * 3 + [(noise(64, 64, 16, seed=404) > 0.7) * 120.0]))
    save("EXScorch01.tga", np.dstack([np.zeros((64, 64))] * 3 + [np.clip(1 - r, 0, 1) ** 0.7 * 220]))
    save("shroud1024.tga", np.dstack([np.full((64, 64), 255.0)] * 3))
    # waypoint node marker (path display): small octahedron, team-tintable
    m = Mesh(64); top, bot, R = (0, 0, 6), (0, 0, 0), 2.5
    ring = [(R * math.cos(k * math.pi / 2), R * math.sin(k * math.pi / 2), 3) for k in range(4)]
    for k in range(4):
        a, b = ring[k], ring[(k + 1) % 4]
        m.tri(a, b, top, (0, 0, 64, 64)); m.tri(b, a, bot, (0, 0, 64, 64))
    save("sawaypoint.tga", rgba(64, 64, (120, 230, 140), np.full((64, 64), 255.0))[:, :, :3])
    export_model(os.path.join(W3D, "SCMNODE.W3D"), "SCMNODE", [("BODY", m)], "sawaypoint.tga")
    # water surface + sky reflection (Water.ini)
    wn = noise(256, 256, 8, seed=405); wf = noise(256, 256, 24, seed=406)
    v = 0.6 * wn + 0.4 * wf
    save("sa_water.tga", np.dstack([v * 40 + 20, v * 70 + 60, v * 80 + 85]))
    sk = noise(256, 256, 3, seed=407)
    save("sa_sky.tga", np.dstack([sk * 60 + 150, sk * 60 + 170, sk * 40 + 200]))
    save("sa_snowflake.tga", np.dstack([np.full((64, 64), 255.0)] * 3 + [np.clip(1 - r, 0, 1) ** 2 * 255]))
    print("system assets written")


if __name__ == "__main__":
    main()

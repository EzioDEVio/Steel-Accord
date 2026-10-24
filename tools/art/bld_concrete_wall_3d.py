"""Steel Accord - B3 structure: precast CONCRETE T-WALL segment (tileable end to end along X) + END POST.

Run:  python3 -I bld_concrete_wall_3d.py <out_dir> [--icon <png>] [--previews <dir>]
Out:  <out_dir>/concrete_wall.glb       nodes: Building (T-wall panel on a jersey-profile foot, lifting loops, team band)
      <out_dir>/concrete_wall_post.glb  nodes: Post (square cast column with a cap; caps the free ends of a wall line)
Segment footprint 6 (X) x 2 (depth) m, origin = footprint centre at ground, front = Blender -Y = Godot +Z.
Panel ends exactly at x = +-3 so consecutive segments butt together without a gap. Original design, code-placed
primitives with procedural textures (bldkit_b): no scans, photos or AI imagery.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bldkit_b as K

A = K.Args(sys.argv[1:])
L = 3.0            # half length (m)
H = 3.6            # panel height (m)


def profile():
    """Cross-section (y = depth, z = height): wide sloped jersey foot, then the tall slab (slight batter)."""
    return [(-0.95, 0.0), (-0.95, 0.22), (-0.32, 0.85), (-0.17, H), (0.17, H), (0.32, 0.85), (0.95, 0.22), (0.95, 0.0)]


def build_wall():
    kit = K.Kit("concrete_wall", "CW", atlas=1024, ao_res=512, ao_dist=2.0)
    B = kit.part("Building")
    # the slab is split into three pours so the joints read at RTS distance (seams at x = +-1)
    for x0, x1 in ((-L, -1.02), (-0.98, 0.98), (1.02, L)):
        B.prism("gconc", profile(), "x", x0, x1, arc_uv=True)
    # thin dark joint fillers between pours
    for x in (-1.0, 1.0):
        B.prism("dark", [(y * 0.97, z) for y, z in profile()], "x", x - 0.02, x + 0.02)
    # lifting loops on top (steel rebar arcs)
    for x in (-1.6, 1.6):
        pts = [(x - 0.22, 0.0, H), (x - 0.18, 0.0, H + 0.18), (x, 0.0, H + 0.26), (x + 0.18, 0.0, H + 0.18), (x + 0.22, 0.0, H)]
        for a, b in zip(pts[:-1], pts[1:]):
            B.strut("steel", a, b, 0.03, seg=5)
    # team-colour band painted across the front of the slab + stencil plate
    B.quad("team", [(-L + 0.05, -0.215, 2.55), (L - 0.05, -0.215, 2.55), (L - 0.05, -0.195, 2.85), (-L + 0.05, -0.195, 2.85)])
    B.span("white", -0.35, 0.35, -0.37, -0.33, 1.25, 1.55)
    # drainage notch shadow at the foot (two dark slots through the base)
    for x in (-2.0, 2.0):
        B.span("dark", x - 0.25, x + 0.25, -0.97, 0.97, 0.0, 0.12, bottom=True)
    B.build()
    return kit.finish(A.out, "concrete_wall.glb", ground_size=24)


def build_post():
    kit = K.Kit("concrete_wall_post", "CP", atlas=512, ao_res=256, ao_dist=1.5)
    B = kit.part("Post")
    B.span("gconc", -0.55, 0.55, -0.55, 0.55, 0.0, H + 0.25)
    B.span("gconc", -0.65, 0.65, -0.65, 0.65, H + 0.25, H + 0.45, bottom=True)      # cap
    B.span("gconc", -0.75, 0.75, -1.05, 1.05, 0.0, 0.3)                              # footing (matches the foot)
    B.span("team", -0.56, 0.56, -0.56, 0.56, 2.55, 2.85)                              # team band
    B.build()
    return kit.finish(A.out, "concrete_wall_post.glb", ground_size=8)


def main():
    icon = None
    if "--icon" in sys.argv:
        icon = sys.argv[sys.argv.index("--icon") + 1]
    if not A.skip_build:
        build_wall()
        build_post()
    if icon:
        import env_civic_3d as C
        os.makedirs(os.path.dirname(icon), exist_ok=True)
        C.render_icon(os.path.join(A.out, "concrete_wall.glb"), "concrete_wall", icon, fill=0.9, az=-30.0, el=24.0)
    if A.previews:
        K.previews(os.path.join(A.out, "concrete_wall.glb"), A.previews, "b3_concrete_wall", K.std_shots(7.0, 2.0), only=A.only)


main()

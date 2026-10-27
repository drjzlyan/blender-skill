"""Live end-to-end test of the stylized-character colour pipeline (needs Blender and the TRELLIS venv).

Builds a synthetic figure mesh and synthetic front/back/side art, runs trellis_prep_refs.py and
trellis_project_colour.py, then checks the saved .blend: shader links, packed canonical images,
blend weights that sum to 1, and that the front image carries the art's colours at the right place.

  BLENDER_BIN=/path/to/blender python3 tests/live_project_colour.py
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = os.environ.get("BLENDER_BIN") or shutil.which("blender")
VENV_PY = os.environ.get("TRELLIS_PYTHON") or str(Path.home() / ".local/share/blender-skill/venvs/trellis/bin/python")
assert BLENDER, "set BLENDER_BIN"
assert Path(VENV_PY).is_file(), "set TRELLIS_PYTHON (needs numpy + opencv)"

ART = r'''
import cv2, numpy as np, sys
out = sys.argv[1]
def figure(path, torso_bgr, head_bgr, wide):
    im = np.full((1024, 1024, 3), 255, np.uint8)
    cv2.rectangle(im, (512 - wide, 400), (512 + wide, 800), torso_bgr, -1)          # body
    cv2.circle(im, (512, 280), 120, head_bgr, -1)                                     # head
    cv2.rectangle(im, (512 - wide // 2, 800), (512 + wide // 2, 960), (90, 60, 40), -1)  # legs
    cv2.imwrite(path, im)
figure(out + "/front.png", (40, 40, 220), (80, 160, 230), 170)   # red torso, skin head
figure(out + "/back.png", (40, 40, 220), (30, 60, 90), 170)
figure(out + "/side.png", (40, 40, 220), (80, 160, 230), 120)
'''

MESH = r'''
import bpy, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)
o = bpy.context.object
o.scale = (0.17, 0.12, 0.5); o.location = (0, 0, 0.5)        # a 1 m tall capsule-ish body, faces -Y
bpy.ops.object.transform_apply(location=True, scale=True)
bpy.ops.export_scene.gltf(filepath=sys.argv[sys.argv.index("--") + 1], export_format="GLB")
'''

CHECK = r'''
import bpy, sys, numpy as np
bpy.ops.wm.open_mainfile(filepath=sys.argv[sys.argv.index("--") + 1])
m = bpy.data.materials["MAT-character"]
types = {n.type for n in m.node_tree.nodes}
assert {"TEX_IMAGE", "ATTRIBUTE", "EMISSION"} <= types, types
imgs = {i.name: i for i in bpy.data.images}
assert {"kid-front", "kid-back", "kid-side"} <= set(imgs), list(imgs)
assert all(i.packed_file for i in imgs.values()), "images must be packed"
ob = bpy.data.objects["GEO-character"]
w = np.empty(len(ob.data.vertices) * 4, np.float32); ob.data.color_attributes["ProjW"].data.foreach_get("color", w)
w = w.reshape(-1, 4)[:, :3]
assert np.allclose(w.sum(axis=1), 1.0, atol=1e-3), "blend weights must sum to 1"
f = imgs["kid-front"]; px = np.array(f.pixels[:], np.float32).reshape(f.size[1], f.size[0], 4)
# canonical image is bottom-row-first with v = height: the torso (red) sits low, the head (skin) high
low = px[int(0.45 * f.size[1]), f.size[0] // 2, :3]      # zn ~ 0.45 -> torso
high = px[int(0.80 * f.size[1]), f.size[0] // 2, :3]     # zn ~ 0.80 -> head
print("torso", low.round(2), "head", high.round(2))
assert low[0] > low[2] + 0.3, "torso should be red"
assert high[0] > high[2] and high[1] > low[1], "head should be the lighter skin colour"
print("OK")
'''


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, **kw)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-2000:]); raise SystemExit(f"failed: {cmd[:3]}")
    return r.stdout


with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    (t / "art.py").write_text(ART); (t / "mesh.py").write_text(MESH); (t / "check.py").write_text(CHECK)
    run([VENV_PY, str(t / "art.py"), str(t)])
    refs = t / "refs"; refs.mkdir()
    run([VENV_PY, str(ROOT / "scripts/trellis_prep_refs.py"), str(refs), "--prefix", "kid",
         "--front", f"{t}/front.png:960", "--back", f"{t}/back.png:960", "--side", f"{t}/side.png:960"])
    run([BLENDER, "-b", "--python", str(t / "mesh.py"), "--", str(t / "mesh.glb")])
    out = run([BLENDER, "-b", "--python", str(ROOT / "scripts/trellis_project_colour.py"), "--",
               "--glb", str(t / "mesh.glb"), "--dir", str(refs), "--prefix", "kid", "--out", str(t / "out.blend"), "--size", "512"])
    assert "SAVED" in out, out[-1500:]
    res = run([BLENDER, "-b", "--python", str(t / "check.py"), "--", str(t / "out.blend")])
    print([l for l in res.splitlines() if l.startswith(("torso", "OK"))])
    assert "OK" in res
print("live_project_colour: PASS")

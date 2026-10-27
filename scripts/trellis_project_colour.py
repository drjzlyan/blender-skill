"""Colour a TRELLIS.2 character mesh from its approved reference art, at texture resolution.

TRELLIS's own PBR bake is unreliable for flat storybook colour, and per-vertex colour is too coarse
for faces (eyebrows and bindis smear at ~2 mm vertex spacing). So the mesh is geometry only and colour
is projected per pixel in the shader:

  1. each reference art (front, back, side) is warped into a canonical orthographic image registered
     to the mesh silhouette row by row (trellis_colour_lib.canonical_view)
  2. a material samples those images with the mesh's rest-pose Generated coordinates, so colour does
     not swim when the character is posed
  3. per-vertex blend weights (stored as an attribute, stable under deformation) choose the front,
     back or side image by facing direction, with zones that keep bad regions out (e.g. a hallucinated
     torso on the side art)
  4. soft toon shading with a warm rim; the images are packed into the .blend

  blender -b --python trellis_project_colour.py -- --glb kid.glb --dir REFDIR --prefix kid --out kid.blend

REFDIR holds PREFIX-<view>-filled.png, -extent.png (or -mask.png) and proj-meta.json from
trellis_prep_refs.py.
"""
import argparse, json, math, sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trellis_colour_lib as lib  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--glb", required=True)
ap.add_argument("--dir", required=True)
ap.add_argument("--prefix", default="kid")
ap.add_argument("--out", required=True)
ap.add_argument("--render", default="")
ap.add_argument("--size", type=int, default=2048, help="canonical image size")
ap.add_argument("--torso-x", type=float, default=0.16, help="half-width of the torso where the back art is trusted")
ap.add_argument("--back-low", type=float, default=0.46, help="lowest height where the back art is trusted (hands-on-hips art would smear below)")
ap.add_argument("--sharp", type=float, default=3.0, help="blend sharpness between views")
ap.add_argument("--no-toon", action="store_true")
ap.add_argument("--rim", type=float, default=0.0, help="warm rim-light strength (0 = off)")
a = ap.parse_args(argv)
D = Path(a.dir)
meta = json.loads((D / "proj-meta.json").read_text())


def load_rgb(path):
    img = bpy.data.images.load(str(path))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]  # top row first
    bpy.data.images.remove(img)
    return px


def load_mask(path):
    return load_rgb(path)[:, :, 0] > 0.5


views = [v for v in ("front", "back", "side") if v in meta and (D / f"{a.prefix}-{v}-filled.png").exists()]
arts = {v: load_rgb(D / f"{a.prefix}-{v}-filled.png") for v in views}
masks = {v: load_mask(D / (f"{a.prefix}-{v}-extent.png" if (D / f"{a.prefix}-{v}-extent.png").exists() else f"{a.prefix}-{v}-mask.png")) for v in views}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.glb)
ob = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bpy.context.view_layer.objects.active = ob
me = ob.data
n = len(me.vertices)
co = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("co", co); co = co.reshape(n, 3)
mw = np.array(ob.matrix_world)
co = co @ mw[:3, :3].T + mw[:3, 3]
nm = np.empty(n * 3, dtype=np.float32); me.vertices.foreach_get("normal", nm)
nm = nm.reshape(n, 3) @ mw[:3, :3].T
nm /= np.linalg.norm(nm, axis=1, keepdims=True) + 1e-9
lo, hi = co.min(axis=0), co.max(axis=0)
height = float(hi[2] - lo[2])
x, y, z = co[:, 0], co[:, 1], co[:, 2]
zn = (z - lo[2]) / height

# ---- canonical, mesh-registered images --------------------------------------------------------
LANDMARKS = {  # mesh height (0 soles .. 1 top of buns) -> art row, per view
    "front": lambda m: (lambda zz: m["y0"] + (1 - zz) * (m["y1"] - m["y0"])),
    "back": lambda m: (lambda zz: np.interp(zz, [0.0, 0.33, 0.58, 1.0], [m["y1"], m.get("waist", m["y0"] + 0.68 * (m["y1"] - m["y0"])), m.get("neck", m["y0"] + 0.29 * (m["y1"] - m["y0"])), m["y0"]])),
    "side": lambda m: (lambda zz: np.interp(zz, [0.0, 0.146, 0.35, 0.58, 1.0], [m["y1"], m.get("hem", m["y0"] + 0.83 * (m["y1"] - m["y0"])), m.get("waist", m["y0"] + 0.70 * (m["y1"] - m["y0"])), m.get("neck", m["y0"] + 0.47 * (m["y1"] - m["y0"])), m["y0"]])),
}
AXIS = {"front": (x, False), "back": (x, True), "side": (y, False)}
SPAN = {"front": 0.9, "back": 0.9, "side": 0.8}
canon = {}
for v in views:
    coord, flip = AXIS[v]
    centres, m_lo, m_hi = lib.mesh_row_extents(coord, zn)
    canon[v] = lib.canonical_view(arts[v], masks[v], centres, m_lo, m_hi, LANDMARKS[v](meta[v]),
                                  SPAN[v], a.size, a.size, flip=flip)
    print("CANON", v, canon[v].shape)

# ---- per-vertex blend weights ----------------------------------------------------------------
head = zn > 0.60
torso = (zn <= 0.60) & (zn > a.back_low) & (np.abs(x) < a.torso_x)
f = np.clip(-nm[:, 1], 0, 1) ** a.sharp
b = np.clip(nm[:, 1], 0, 1) ** a.sharp * (head | torso) * ("back" in views)
s = np.clip(np.abs(nm[:, 0]), 0, 1) ** a.sharp * (head | (zn < 0.37)) * ("side" in views)
f = f + 0.02 * ((nm[:, 1] <= 0) | ~(head | torso))  # never leave a vertex with no view
tot = f + b + s
W = np.stack([f, b, s], axis=1) / np.maximum(tot, 1e-6)[:, None]
attr = me.color_attributes.new("ProjW", "FLOAT_COLOR", "POINT")
attr.data.foreach_set("color", np.concatenate([W, np.ones((n, 1), np.float32)], axis=1).reshape(-1))


def make_image(name, rgb_top_first):
    h, w = rgb_top_first.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = "sRGB"
    px = np.concatenate([np.clip(rgb_top_first[::-1], 0, 1), np.ones((h, w, 1), np.float32)], axis=2)
    img.pixels.foreach_set(px.reshape(-1))
    img.pack()
    return img


# ---- material ---------------------------------------------------------------------------------
mat = bpy.data.materials.new("MAT-character")
mat.use_nodes = True
nt = mat.node_tree
nodes, links = nt.nodes, nt.links
bsdf = nodes["Principled BSDF"]
tc = nodes.new("ShaderNodeTexCoord")
gen = nodes.new("ShaderNodeSeparateXYZ"); links.new(tc.outputs["Generated"], gen.inputs["Vector"])
wattr = nodes.new("ShaderNodeAttribute"); wattr.attribute_type = "GEOMETRY"; wattr.attribute_name = "ProjW"
wsep = nodes.new("ShaderNodeSeparateColor"); links.new(wattr.outputs["Color"], wsep.inputs["Color"])


def madd(a_sock, mul, add):
    m = nodes.new("ShaderNodeMath"); m.operation = "MULTIPLY_ADD"
    links.new(a_sock, m.inputs[0]); m.inputs[1].default_value = mul; m.inputs[2].default_value = add
    return m.outputs["Value"]


def tex(view):
    coord, _ = AXIS[view]
    gx = gen.outputs["X"] if coord is x else gen.outputs["Y"]
    c_lo, c_hi = float(coord.min()), float(coord.max())
    u = madd(gx, (c_hi - c_lo) / SPAN[view], c_lo / SPAN[view] + 0.5)  # coord = lo + g*(hi-lo); u = coord/span + 0.5
    uv = nodes.new("ShaderNodeCombineXYZ")
    links.new(u, uv.inputs["X"]); links.new(gen.outputs["Z"], uv.inputs["Y"])
    t = nodes.new("ShaderNodeTexImage"); t.image = make_image(f"{a.prefix}-{view}", canon[view])
    t.interpolation = "Linear"; t.extension = "EXTEND"
    links.new(uv.outputs["Vector"], t.inputs["Vector"])
    return t.outputs["Color"]


def scaled(col, w_sock):
    vm = nodes.new("ShaderNodeVectorMath"); vm.operation = "SCALE"
    links.new(col, vm.inputs[0]); links.new(w_sock, vm.inputs["Scale"])
    return vm.outputs["Vector"]


acc = None
for view, wname in (("front", "Red"), ("back", "Green"), ("side", "Blue")):
    if view not in canon:
        continue
    term = scaled(tex(view), wsep.outputs[wname])
    if acc is None:
        acc = term
    else:
        add = nodes.new("ShaderNodeVectorMath"); add.operation = "ADD"
        links.new(acc, add.inputs[0]); links.new(term, add.inputs[1]); acc = add.outputs["Vector"]
base = acc

if a.no_toon:
    links.new(base, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.62
else:
    out = nodes["Material Output"]
    diff = nodes.new("ShaderNodeBsdfDiffuse")
    s2r = nodes.new("ShaderNodeShaderToRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "B_SPLINE"
    cr.elements[0].position, cr.elements[0].color = 0.04, (0.80, 0.76, 0.86, 1)
    cr.elements[1].position, cr.elements[1].color = 0.70, (1.0, 0.99, 0.97, 1)
    mid = cr.elements.new(0.35); mid.color = (0.93, 0.90, 0.94, 1)
    mix = nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    fres = nodes.new("ShaderNodeLayerWeight"); fres.inputs["Blend"].default_value = 0.30
    rimr = nodes.new("ShaderNodeMapRange")
    rimr.inputs["From Min"].default_value = 0.55; rimr.inputs["From Max"].default_value = 0.95
    rimr.inputs["To Max"].default_value = a.rim
    tint = nodes.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "ADD"
    tint.inputs[7].default_value = (1.0, 0.72, 0.45, 1)
    emit = nodes.new("ShaderNodeEmission")
    links.new(base, diff.inputs["Color"])
    links.new(diff.outputs["BSDF"], s2r.inputs["Shader"])
    links.new(s2r.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs[6]); links.new(base, mix.inputs[7])
    links.new(fres.outputs["Facing"], rimr.inputs["Value"])
    links.new(mix.outputs[2], tint.inputs[6])
    links.new(rimr.outputs["Result"], tint.inputs["Factor"])
    links.new(tint.outputs[2], emit.inputs["Color"])
    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    nodes.remove(bsdf)

me.materials.clear(); me.materials.append(mat)
for p_ in me.polygons: p_.use_smooth = True
ob.name = "GEO-character"
for img in list(bpy.data.images):
    if img.name.startswith("Image_") or (img.users == 0 and not img.packed_file): bpy.data.images.remove(img)
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.out).resolve()))
print("SAVED", a.out, "verts", n, "views", views)

if a.render:
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 700; sc.render.resolution_y = 900
    sc.eevee.taa_render_samples = 32; sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.80, 0.74, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    c = Vector(((lo + hi) / 2).tolist()); size = float(max(hi - lo))
    for loc, e, col_ in (((2, -3, 3), 400, (1, .93, .84)), ((-3, -2, 2), 150, (.85, .9, 1)), ((0, 3, 3), 220, (1, .8, .6))):
        d = bpy.data.lights.new("L", "AREA"); d.energy = e; d.size = 3; d.color = col_
        o = bpy.data.objects.new("L", d); sc.collection.objects.link(o); o.location = c + Vector(loc) * size / 1.8
        o.rotation_euler = (c - o.location).to_track_quat("-Z", "Y").to_euler()
    Path(a.render).mkdir(parents=True, exist_ok=True)
    for name, ang, lens in (("front", 0, 70), ("three", 35, 70), ("side", 90, 70), ("back", 180, 70), ("face", 12, 190)):
        r = math.radians(ang)
        cd = bpy.data.cameras.new(name); cd.lens = lens
        cam = bpy.data.objects.new(name, cd); sc.collection.objects.link(cam)
        tgt = c + Vector((0, 0, size * 0.33)) if name == "face" else c
        cam.location = tgt + Vector((math.sin(r) * size * 2.0, -math.cos(r) * size * 2.0, 0))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.camera = cam; sc.render.filepath = f"{a.render}/{name}.png"
        bpy.ops.render.render(write_still=True)

"""Orthographic front-silhouette IoU of a GLB against a reference figure mask (run in Blender).
blender -b --python silhouette_iou.py -- model.glb ref_mask.png out_prefix
The mesh is rotated/oriented as imported (character faces -Y after glTF import); the silhouette is fitted to
the mask's bounding box by uniform scale + translation only, so proportions are judged, not placement."""
import sys, json, math
import bpy, numpy as np
from mathutils import Vector
args_ = sys.argv[sys.argv.index("--") + 1:]
glb, maskp, out = args_[:3]
FLIPZ = len(args_) > 3 and args_[3] == "flip"   # model faces +Y: rotate 180 deg about Z before rendering
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if FLIPZ:
    for o in bpy.context.scene.objects:
        if o.parent is None: o.rotation_euler[2] += 3.14159265
    bpy.context.view_layer.update()
pts = np.array([(o.matrix_world @ Vector(c))[:] for o in objs for c in o.bound_box])
lo, hi = pts.min(0), pts.max(0); c = (lo + hi) / 2; size = hi - lo
H, W = 1536, 1024
mimg = bpy.data.images.load(maskp); mw, mh = mimg.size
mask = np.array(mimg.pixels[:], np.float32).reshape(mh, mw, 4)[::-1, :, 0] > 0.5
ys, xs = np.where(mask); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
for o in objs:   # emission-white material so the render is a clean silhouette
    m = bpy.data.materials.new("sil"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission"); o_ = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o_.inputs[0]); o.data.materials.clear(); o.data.materials.append(m)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x, sc.render.resolution_y = mw, mh
sc.render.film_transparent = True; sc.view_settings.view_transform = "Standard"
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); sc.camera = cam
fig_h = size[2]; fig_w = size[0]
# scale so the mesh height maps onto the mask height (pixels): ortho_scale covers mh pixels
cd.ortho_scale = fig_h * mh / (y1 - y0 + 1)
cx_px = (x0 + x1) / 2; cy_px = (y0 + y1) / 2
px = cd.ortho_scale / mh
cam.location = Vector((c[0] + (cx_px - mw / 2) * -px * -1, c[1] - 10, c[2] - (cy_px - mh / 2) * -px * -1 * -1))
cam.location.x = c[0] - (cx_px - mw / 2) * px
cam.location.z = c[2] + (cy_px - mh / 2) * px
cam.rotation_euler = (math.radians(90), 0, 0)
sc.render.filepath = out + "_sil.png"; bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(out + "_sil.png"); w, h = img.size
a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, 3] > 0.5
inter = (a & mask).sum(); union = (a | mask).sum()
print("IOU", json.dumps({"iou": round(float(inter / union), 4), "mesh_h_m": round(float(fig_h), 3), "mesh_w_m": round(float(fig_w), 3)}))

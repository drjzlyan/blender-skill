"""Run Hunyuan3D-2.1 (shape then paint, GPU freed in between) and report time / peak VRAM / peak RAM.
  run_hunyuan.py --image in_rgba.png --out_dir DIR [--views 6] [--res 512]"""
import argparse, gc, json, os, resource, sys, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
REPO = os.path.expanduser("~/.local/share/blender-skill/experiments/hunyuan3d21")
MODEL = os.path.expanduser("~/.local/share/blender-skill/models/Hunyuan3D-2.1")
sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/hy3dshape"); sys.path.insert(0, REPO + "/hy3dpaint"); os.chdir(REPO)
import torch
from PIL import Image
ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True); ap.add_argument("--out_dir", required=True)
ap.add_argument("--views", type=int, default=6); ap.add_argument("--res", type=int, default=512)
ap.add_argument("--seed", type=int, default=42); ap.add_argument("--skip_paint", action="store_true"); ap.add_argument("--reuse_shape", action="store_true")
a = ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
report = {"model": "Hunyuan3D-2.1"}

shape_glb = os.path.join(a.out_dir, "shape.glb")
t0 = time.time()
if not (a.reuse_shape and os.path.exists(shape_glb)):
    from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
    torch.cuda.reset_peak_memory_stats()
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(MODEL)
    image = Image.open(a.image).convert("RGBA")
    mesh = pipe(image=image, generator=torch.Generator("cuda").manual_seed(a.seed))[0]
    mesh.export(shape_glb)
    report["shape"] = {"seconds": round(time.time() - t0, 1), "peak_vram_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                       "peak_vram_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
                       "faces": int(len(mesh.faces)), "verts": int(len(mesh.vertices))}
    print("SHAPE", json.dumps(report["shape"]), flush=True)
    del pipe, mesh; gc.collect(); torch.cuda.empty_cache()
else:
    print("SHAPE reused", shape_glb, flush=True)
try:
    from torchvision_fix import apply_fix   # basicsr imports torchvision.transforms.functional_tensor (removed upstream)
    apply_fix()
except Exception as e:
    print("torchvision_fix failed:", e)

if not a.skip_paint:
    from textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
    torch.cuda.reset_peak_memory_stats(); t1 = time.time()
    conf = Hunyuan3DPaintConfig(a.views, a.res)
    conf.multiview_pretrained_path = MODEL
    conf.realesrgan_ckpt_path = REPO + "/hy3dpaint/ckpt/RealESRGAN_x4plus.pth"
    conf.multiview_cfg_path = REPO + "/hy3dpaint/cfgs/hunyuan-paint-pbr.yaml"
    conf.custom_pipeline = REPO + "/hy3dpaint/hunyuanpaintpbr"
    paint = Hunyuan3DPaintPipeline(conf)
    out_obj = os.path.join(a.out_dir, "textured.obj")
    paint(mesh_path=shape_glb, image_path=a.image, output_mesh_path=out_obj, save_glb=False)
    report["paint"] = {"seconds": round(time.time() - t1, 1), "peak_vram_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                       "peak_vram_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2), "views": a.views, "res": a.res}
report["total_seconds"] = round(time.time() - t0, 1)
report["peak_rss_gib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2)
print("BENCH", json.dumps(report))

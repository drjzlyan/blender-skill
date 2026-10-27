"""Run Pixal3D once and report time / peak VRAM / peak RAM.
  run_pixal3d.py --image in.png --output out.glb [--low_vram] [--resolution 1024] [--fov RAD] [--seed N]"""
import argparse, json, os, resource, sys, time
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("ATTN_BACKEND", "xformers")   # flash_attn is not installed
REPO = os.path.expanduser("~/.local/share/blender-skill/experiments/pixal3d")
sys.path.insert(0, REPO); os.chdir(REPO)
import torch
import inference as P

ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True); ap.add_argument("--output", required=True)
ap.add_argument("--seed", type=int, default=42); ap.add_argument("--low_vram", action="store_true")
ap.add_argument("--resolution", type=int, default=-1); ap.add_argument("--fov", type=float, default=-1.0)
ap.add_argument("--model_path", default=os.path.expanduser("~/.local/share/blender-skill/models/Pixal3D"))
a = ap.parse_args()
torch.cuda.reset_peak_memory_stats()
t0 = time.time()
P.run_inference(a.image, a.output, seed=a.seed, model_path=a.model_path, manual_fov=a.fov,
                low_vram=a.low_vram, resolution=a.resolution)
dt = time.time() - t0
print("BENCH", json.dumps({
    "model": "Pixal3D", "seconds": round(dt, 1), "low_vram": a.low_vram, "resolution": a.resolution, "fov": a.fov,
    "peak_vram_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
    "peak_vram_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
    "peak_rss_gib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2),
    "output": a.output, "output_mb": round(os.path.getsize(a.output) / 2**20, 1)}))

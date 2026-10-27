import os
os.environ["HF_HUB_DISABLE_XET"] = "1"   # the xet backend stalled at ~0 B/s here; plain LFS HTTP gave ~7 MB/s
from huggingface_hub import snapshot_download
p = snapshot_download("TencentARC/Pixal3D", local_dir=os.path.expanduser("~/.local/share/blender-skill/models/Pixal3D"),
                      ignore_patterns=["*_mv.safetensors", "*_mv.json", "pipeline_mv.json", "assets/*"], max_workers=4)
print("DOWNLOADED", p)

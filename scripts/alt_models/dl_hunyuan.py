import os
os.environ["HF_HUB_DISABLE_XET"] = "1"
from huggingface_hub import snapshot_download
p = snapshot_download("tencent/Hunyuan3D-2.1", local_dir=os.path.expanduser("~/.local/share/blender-skill/models/Hunyuan3D-2.1"), max_workers=4)
print("DOWNLOADED", p)

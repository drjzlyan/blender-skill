#!/usr/bin/env bash
# Isolated Hunyuan3D-2.1 env that actually works on a 24 GB RTX 4090 (Linux, Python 3.10, CUDA 12.4 toolchain).
# Reuses torch 2.6 + numpy 1.26 from the TRELLIS venv via a fallback .pth (saves ~6 GB; authors tested 2.5.1),
# and installs only what differs with --no-deps. Every step below fixed a real failure; see
# references/trellis2/model-comparison.md.
set -euo pipefail
export UV_HTTP_TIMEOUT=300 HF_HUB_DISABLE_XET=1
BASE=${BLENDER_SKILL_HOME:-$HOME/.local/share/blender-skill}
V=$BASE/venvs/hunyuan21; T=$BASE/venvs/trellis; R=$BASE/experiments/hunyuan3d21
mkdir -p "$BASE/experiments/wheels"
[ -d "$R" ] || git clone --depth 1 https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git "$R"
uv venv "$V" --python 3.10; PY="$V/bin/python"
SP=$("$PY" -c "import site;print(site.getsitepackages()[0])")
"$T/bin/python" -c "import site;print(site.getsitepackages()[0])" > "$SP/zz_trellis_fallback.pth"
export PATH="$V/bin:$PATH" CUDA_HOME=/usr
I="uv pip install --python $PY --no-deps"
$I "transformers==4.46.0" "tokenizers>=0.20,<0.21" "diffusers==0.30.0" "accelerate==1.1.1" "huggingface-hub==0.30.2" \
   "safetensors==0.4.4" "pytorch-lightning==1.9.5" torchmetrics lightning-utilities einops==0.8.0 omegaconf==2.3.0 \
   "antlr4-python3-runtime==4.9.3" trimesh==4.4.7 pymeshlab==2022.2.post3 pygltflib==1.16.3 xatlas==0.0.9 \
   "scikit-image==0.24.0" pybind11 ninja cmake wheel cython regex requests pyyaml psutil filelock fsspec aiohttp \
   importlib_metadata zipp packaging typing_extensions tqdm timm tensorboard urllib3 idna certifi charset-normalizer lazy_loader \
   numba llvmlite scikit-learn joblib threadpoolctl cloudpickle pandas python-dateutil pytz tzdata six
$I "setuptools==69.5.1"                 # pytorch-lightning 1.9 needs pkg_resources (removed from newer setuptools)
$I rembg==2.0.65 "onnxruntime==1.20.1"  # 1.16.3 fails to load on newer kernels (executable-stack shared object)
$I pooch jsonschema pymatting platformdirs referencing rpds-py attrs jsonschema-specifications flatbuffers coloredlogs humanfriendly sympy mpmath protobuf
$I addict future lmdb yapf "basicsr==1.4.2" "realesrgan==0.3.0"
# open3d (400 MB) is far faster with curl than with uv's downloader; its import also needs the plotly/dash chain
URL=$(python3 -c "import json,urllib.request;d=json.load(urllib.request.urlopen('https://pypi.org/pypi/open3d/0.18.0/json'));print([f['url'] for f in d['urls'] if f['filename'].endswith('manylinux_2_27_x86_64.whl') and 'cp310' in f['filename']][0])")
curl -sL --retry 3 -C - -o "$BASE/experiments/wheels/open3d.whl" "$URL"
$I "$BASE/experiments/wheels/open3d.whl" plotly dash pydantic pydantic_core typing_inspection annotated_types narwhals janus werkzeug
# bpy is imported at module top but only used when save_glb=True: stub it and convert OBJ -> GLB in real Blender
mkdir -p "$SP/bpy" && printf 'data = context = ops = None\n' > "$SP/bpy/__init__.py"
# local patch: let the paint stage use an already-downloaded model directory instead of re-downloading 14 GB
python3 - "$R" <<'PYEOF'
import sys
p = sys.argv[1] + "/hy3dpaint/utils/multiview_utils.py"; s = open(p).read()
old = 'model_path = huggingface_hub.snapshot_download(\n            repo_id=config.multiview_pretrained_path,\n            allow_patterns=["hunyuan3d-paintpbr-v2-1/*"],\n        )'
new = 'model_path = config.multiview_pretrained_path if os.path.isdir(config.multiview_pretrained_path) else huggingface_hub.snapshot_download(\n            repo_id=config.multiview_pretrained_path,\n            allow_patterns=["hunyuan3d-paintpbr-v2-1/*"],\n        )'
if old in s: open(p, "w").write(s.replace(old, new))
PYEOF
# native pieces. compile_mesh_painter.sh names the .so after the SYSTEM python (cpython-314); build it with the venv's
( cd "$R/hy3dpaint/custom_rasterizer" && TORCH_CUDA_ARCH_LIST="8.9" uv pip install --python "$PY" --no-deps --no-build-isolation -e . )
( cd "$R/hy3dpaint/DifferentiableRenderer" && rm -f mesh_inpaint_processor.cpython-31[1-9]*.so \
  && c++ -O3 -Wall -shared -std=c++11 -fPIC $("$PY" -m pybind11 --includes) mesh_inpaint_processor.cpp \
     -o mesh_inpaint_processor$("$PY" -c "import sysconfig;print(sysconfig.get_config_var('EXT_SUFFIX'))") )
mkdir -p "$R/hy3dpaint/ckpt"
curl -sL --retry 3 -o "$R/hy3dpaint/ckpt/RealESRGAN_x4plus.pth" https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth
"$PY" -c "import torch, diffusers, transformers, custom_rasterizer, open3d; print('HY ENV OK', torch.__version__, torch.cuda.is_available())"

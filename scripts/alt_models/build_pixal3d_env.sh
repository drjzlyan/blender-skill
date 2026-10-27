#!/usr/bin/env bash
# Isolated Pixal3D env. Falls back to the TRELLIS site-packages for torch 2.6 and the compiled CUDA extensions,
# and installs ONLY what differs, with --no-deps so uv never pulls a second torch.
set -euo pipefail
V=~/.local/share/blender-skill/venvs/pixal3d
T=~/.local/share/blender-skill/venvs/trellis
uv venv "$V" --python 3.10
SP=$("$V/bin/python" -c "import site;print(site.getsitepackages()[0])")
TSP=$("$T/bin/python" -c "import site;print(site.getsitepackages()[0])")
echo "$TSP" > "$SP/zz_trellis_fallback.pth"   # appended after this venv's own packages, so overrides win
export CUDA_HOME=${CUDA_HOME:-/usr}
I="uv pip install --python $V/bin/python --no-deps"
$I "transformers==4.57.3" "tokenizers>=0.22,<0.23" "huggingface_hub>=0.34,<1.0" "diffusers==0.37.1" "accelerate==1.13.0" \
   "pillow==12.0.0" lpips pandas regex requests pyyaml psutil filelock importlib_metadata zipp packaging charset_normalizer idna urllib3 certifi \
   python-dateutil pytz tzdata six
$I "git+https://github.com/microsoft/MoGe.git"
$I https://github.com/LDYang694/Storages/releases/download/20260430/utils3d-0.0.2-py3-none-any.whl
$I "git+https://github.com/EasternJournalist/utils3d-moge.git@62f09d58509485564e24d5d9f6aac9ee9ebc0c37" einops
uv pip install --python "$V/bin/python" cmake ninja   # natten builds with CMake
NATTEN_CUDA_ARCH="8.9" NATTEN_N_WORKERS=4 uv pip install --python "$V/bin/python" --no-deps --no-build-isolation "natten==0.21.0"
"$V/bin/python" -c "import torch, natten, moge, transformers, huggingface_hub; print('ENV OK', torch.__version__, transformers.__version__, huggingface_hub.__version__, torch.cuda.is_available())"

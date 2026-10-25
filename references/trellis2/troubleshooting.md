# TRELLIS.2 troubleshooting

## Doctor fails

```bash
python3 scripts/blender_skill.py trellis doctor
```

Read `errors` first, then `warnings`. Do not start a GPU job until `ok` is true.

### `cuda_available: false`

- Check `nvidia-smi`.
- The driver must support the CUDA 12.4 runtime used by torch 2.6.
- In a container, pass the GPU device and driver mounts.

### `cumesh`, `flex_gemm`, `nvdiffrast`, `o_voxel` missing

Re-run:

```bash
python3 scripts/blender_skill.py setup --with-trellis
```

These are compiled CUDA extensions. They need a matching `nvcc`, Python headers,
and torch in the venv. If the venv was created from a Python without headers,
recreate it with a managed Python:

```bash
uv python install 3.10
rm -rf "$BLENDER_SKILL_HOME/venvs/trellis"
python3 scripts/blender_skill.py setup --with-trellis
```

### Sparse attention / `flash_attn` missing

Sparse attention supports `xformers` and `flash_attn`, not `sdpa`. Setup installs
`xformers==0.0.29.post2` by default. If it is missing:

```bash
python3 scripts/blender_skill.py setup --with-trellis
```

Or use the optional faster backend:

```bash
python3 scripts/blender_skill.py setup --with-trellis --with-flash-attn
```

### `flash_attn` missing

Use SDPA instead:

```bash
ATTN_BACKEND=sdpa python3 scripts/blender_skill.py trellis generate ...
```

Or install flash-attn during setup with `--with-flash-attn`. SDPA is a valid
fallback and avoids compiler-specific build failures.

### CUDA version mismatch

Torch 2.6 is built with CUDA 12.4. Compiling extensions with another CUDA 12.x
toolkit usually works through minor-version compatibility; the safest setup is
CUDA 12.4:

```bash
export CUDA_HOME=/usr/local/cuda-12.4
export PATH="$CUDA_HOME/bin:$PATH"
```

Set `TORCH_CUDA_ARCH_LIST` to the GPU architecture (for example `8.9`) to speed
up builds and avoid building for every architecture.

## Doctor passes but generation fails

Read the sidecar and log. Common causes:

### Out of memory

- Use `--pipeline-type 512` or `1024`.
- Keep `--low-vram` on.
- Lower `--decimation-target` (for example `150000`).
- Lower `--texture-size` (for example `1024`).
- Close other GPU processes; run one job at a time.
- The bridge sets `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.

### Gated model (403)

DINOv3 and RMBG-2.0 are gated. Accept the licenses on Hugging Face with the
account that owns `HF_TOKEN`, then re-run:

```bash
python3 scripts/blender_skill.py trellis download
```

Confirm with:

```bash
"$BLENDER_SKILL_HOME/venvs/trellis/bin/python" -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('facebook/dinov3-vitl16-pretrain-lvd1689m','config.json'))"
```

### Model download stalls or fails

```bash
python3 scripts/blender_skill.py trellis download --resume
```

Check `HF_HOME`, free disk (about 16 GB for weights plus outputs), and access to
`huggingface.co`. A logged-in token helps with rate limits. The download is
resumable; re-run the same command.

### `mesh.simplify` or GLB extraction fails

- The nvdiffrast render limit is 16,777,216 vertices; the bridge simplifies to
  that by default.
- Try `--no-remesh` to keep original topology.
- Raise `--decimation-target` only if VRAM allows.
- Reduce `--texture-size`.

## Add-on issues

### Panel not visible

- Enable **TRELLIS.2 Bridge** in Preferences → Add-ons.
- Press `N` in the 3D Viewport and look for the **TRELLIS.2** tab.
- Restart Blender after installing the extension.
- Check `blender --command extension list`.

### "Python executable not found"

Set the full path to the guide TRELLIS venv Python in the add-on preferences. The
venv must exist and contain torch.

### Job starts then fails immediately

Open **Open Last Log**. Typical causes: wrong vendor path, missing bridge script,
an image path with unsupported characters, or a model cache permission problem.

### Import succeeds but the object is invisible

- Frame selected.
- Check collection visibility and whether `COL_TRELLIS2` is excluded.
- The asset may be tiny after a custom import scale; check dimensions.

### Material is black or has no texture

- Confirm the base-color texture loaded (packed in the GLB).
- Set the base-color image color space to `sRGB`.
- Do not use `--no-webp` into a viewer that cannot read the embedded format.
- For alpha cutouts, connect texture alpha and use DITHERED/BLEND.

### Textured result is in the wrong place or scale

The texturing pipeline normalizes to a unit AABB. Use **Fit To Original** or
re-place manually. For exact placement, texture an already-normalized mesh.

## CLI issues

### `ModuleNotFoundError: trellis2`

The bridge adds `--vendor-dir` (default `trellis/vendor`) to `sys.path`. Run the
wrapper, or pass the correct `--vendor-dir`.

### `No module named torch`

You are using the wrong Python. Use the guide TRELLIS venv, not Blender's Python
and not the system Python.

### Progress freezes at 25%

The flow models are running. On a 24 GB card a 1024 cascade job can take tens of
seconds; check GPU utilization with `nvidia-smi`.

### Multiple concurrent jobs

The add-on prevents this. CLI users must serialize jobs manually; two 4B models
do not fit in 24 GB.

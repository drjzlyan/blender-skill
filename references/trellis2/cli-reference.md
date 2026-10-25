# TRELLIS.2 CLI reference

The bridge is at `trellis/bridge/trellis2_bridge.py` and runs with the guide's
TRELLIS venv (`$BLENDER_SKILL_HOME/venvs/trellis/bin/python`). The wrapper
`python3 scripts/blender_skill.py trellis ...` sets all paths for you.

Global options must appear before the subcommand:

| Option | Default | Purpose |
|---|---|---|
| `--vendor-dir` | `trellis/vendor` | Directory added to `sys.path` |
| `--model` | local weights dir, else `microsoft/TRELLIS.2-4B` | Local model directory or Hugging Face id |

## doctor

```bash
python3 scripts/blender_skill.py trellis doctor
```

Returns a `TRELLIS2_RESULT` JSON object. Key fields:

- `ok` — all required checks passed
- `checks.cuda` — torch, CUDA availability, device, VRAM
- `checks.cumesh`, `checks.flex_gemm`, `checks.nvdiffrast`, `checks.o_voxel`
- `checks.flash_attn`, `checks.xformers`
- `checks.model_dir` — resolved weights directory
- `warnings`, `errors`

Exit code is `0` only when `ok` is true. Doctor imports torch but does not load
the 4B model.

## generate

```bash
python3 scripts/blender_skill.py trellis generate \
  --image ref.png \
  --output outputs/asset.glb \
  --pipeline-type 1024_cascade \
  --seed 42
```

| Flag | Default | Notes |
|---|---|---|
| `--image` | required | PNG/WebP/JPG; alpha preferred |
| `--output` | required | `.glb` file or directory |
| `--seed` | `42` | Reproducible variation |
| `--num-samples` | `1` | Writes `_00`, `_01`, ... when > 1 |
| `--pipeline-type` | `1024_cascade` | `512`, `1024`, `1024_cascade`, `1536_cascade` |
| `--decimation-target` | `250000` | Vertex target for UV/remesh extraction |
| `--texture-size` | `2048` | 1024–4096 |
| `--simplify-limit` | `16777216` | nvdiffrast render limit; `0` disables |
| `--remesh` / `--no-remesh` | remesh | Rebuild topology before UVs |
| `--remesh-band` | `1.0` | Narrow-band width |
| `--remesh-project` | `0.0` | Projection to source surface |
| `--alpha-mode` | `opaque` | `blend` or `mask` writes glTF alpha mode |
| `--no-webp` | off | Embed PNG instead of WebP |
| `--low-vram` / `--no-low-vram` | config | Stage offloading override |

### Output behavior

- One sample with `--output asset.glb` writes exactly that file.
- Multiple samples write `asset_00.glb`, `asset_01.glb`, ...
- A directory output creates a timestamped filename.
- Each GLB gets a `<glb>.glb.json` sidecar. With multiple samples every sidecar
  contains the full output list.

### Sidecar schema

```json
{
  "ok": true,
  "task": "generate",
  "model": "microsoft/TRELLIS.2-4B",
  "image": "/abs/ref.png",
  "seed": 42,
  "num_samples": 1,
  "pipeline_type": "1024_cascade",
  "decimation_target": 250000,
  "texture_size": 2048,
  "remesh": true,
  "alpha_mode": "opaque",
  "outputs": [
    {"path": "/abs/asset.glb", "vertices": 250000, "faces": 499998}
  ],
  "created": "2026-01-01T12:00:00",
  "elapsed_sec": 31.4
}
```

Failure adds `error` and `traceback` and leaves `ok` false. Exit code is `1`.

### Progress protocol

Stdout contains:

```text
TRELLIS2_PROGRESS 10 Loading generate pipeline
...
TRELLIS2_PROGRESS 100 Done
TRELLIS2_RESULT {"ok": true, ...}
```

The add-on and MCP parse progress lines; agents can parse the final result line
or read the sidecar.

## texture

```bash
python3 scripts/blender_skill.py trellis texture \
  --mesh shape.glb \
  --image ref.png \
  --output outputs/textured.glb \
  --resolution 1024 \
  --texture-size 2048
```

| Flag | Default | Notes |
|---|---|---|
| `--mesh` | required | GLB/GLTF/OBJ/PLY; scenes are concatenated |
| `--image` | required | Texture reference |
| `--output` | required | `.glb` file or directory |
| `--seed` | `42` | |
| `--resolution` | `1024` | `512` or `1024` shape latent |
| `--texture-size` | `2048` | Baked texture resolution |
| `--no-webp` | off | |
| `--low-vram` / `--no-low-vram` | config | |

The shape is normalized to a unit AABB and the output is re-centered. Fit it to
the original bounds in Blender when placement matters.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Doctor OK or job OK |
| `1` | Validation or job failure; read the sidecar/JSON |
| `2` | Argument error |

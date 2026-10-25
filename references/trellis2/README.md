# TRELLIS.2 in this guide

TRELLIS.2 is vendored inference code plus downloaded weights. It runs in an
isolated Python environment; Blender only launches it and imports the resulting
GLB. **Never import `torch` or the CUDA extensions into Blender.**

## What is vendored

| Path | Contents |
|---|---|
| `trellis/vendor/trellis2/` | Microsoft's MIT inference package |
| `trellis/vendor/o-voxel/` | MIT O-Voxel meshing/export package |
| `trellis/vendor/configs/` | Pipeline configuration |
| `trellis/bridge/trellis2_bridge.py` | CLI bridge (`doctor`, `generate`, `texture`) |
| `trellis/addon/` | Optional Blender UI add-on |

The TRELLIS environment installs `xformers` by default because sparse attention
needs it. `--with-flash-attn` is an optional faster backend. Dense-only `sdpa`
is not enough for generation.

Weights are **not** vendored. Setup downloads 16.24 GB from
`microsoft/TRELLIS.2-4B` into the guide data directory. You can point at
existing weights instead:

```bash
python3 scripts/blender_skill.py setup --model-dir /path/to/TRELLIS.2-4B
```

## Commands

```bash
# environment and weights check
python3 scripts/blender_skill.py trellis doctor

# image -> GLB
python3 scripts/blender_skill.py trellis generate \
  --image reference.png \
  --output outputs/asset.glb \
  --pipeline-type 1024_cascade \
  --seed 42 \
  --decimation-target 250000 \
  --texture-size 2048

# PBR texture an existing mesh
python3 scripts/blender_skill.py trellis texture \
  --mesh shape.glb \
  --image reference.png \
  --output outputs/textured.glb \
  --resolution 1024 \
  --texture-size 2048
```

The wrapper resolves the TRELLIS venv, vendored code, and model directory from
the guide config. Direct bridge invocation is also supported:

```bash
"$BLENDER_SKILL_HOME/venvs/trellis/bin/python" \
  trellis/bridge/trellis2_bridge.py doctor
```

## Quality ladder

| `--pipeline-type` | Approx. VRAM | Use |
|---|---|---|
| `512` | lower | ideation, low VRAM |
| `1024` | medium | balanced single stage |
| `1024_cascade` | ~24 GB | default production balance |
| `1536_cascade` | high | hero detail |

Use `--low-vram` below 24 GB. Use `--num-samples 4` for a seed sweep; outputs are
suffixed `_00`–`_03`.

## Workflow

```text
1. PREFLIGHT   doctor; GPU, extensions, weights
2. PREPARE     one subject, clean background, 1024 px long edge
3. GENERATE    explicit seed, quality, decimation, texture size
4. VALIDATE    read the .glb.json sidecar; check files and face counts
5. IMPORT      MCP trellis2_import into COL_TRELLIS2
6. POST        alpha, scale, cleanup, decimate/retopo, UV + material audit
7. REPORT      seed, quality, face counts, limitations, next step
```

## Constraints

- One GPU job at a time. Two 4B models do not fit in 24 GB.
- Always pass an explicit seed.
- Always write outputs outside the repository.
- Never overwrite an input image or mesh.
- Raw output is a base asset, not shipping topology.
- Verify reference fidelity with a screenshot; do not claim it from the prompt.

## Limits

- GLB alpha is exported `OPAQUE`; wire base-color alpha after import.
- No normal map is generated.
- No multi-view conditioning; one strong view per generation.
- Remesh output is dense uniform topology.
- Texturing normalizes the mesh to a unit AABB.

## Files

| Reference | Topic |
|---|---|
| `cli-reference.md` | Every flag, sidecar schema, progress protocol |
| `Import.md` | Import, alpha, scale, cleanup, validation |
| `addon.md` | Interactive Blender UI |
| `troubleshooting.md` | Doctor and job failures |

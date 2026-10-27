# Changelog

## Unreleased

- GPU detection falls back to the TRELLIS venv's torch when `nvidia-smi` is not on PATH; the doctor
  no longer reports "No NVIDIA GPU" on machines where CUDA works.
- Stylized-character colour pipeline for TRELLIS.2 meshes (`references/trellis2/stylized-characters.md`):
  `scripts/trellis_prep_refs.py` prepares front/back/side reference art, `scripts/trellis_colour_lib.py`
  warps each art into a canonical view registered to the mesh silhouette, and
  `scripts/trellis_project_colour.py` builds a packed, pose-stable, texture-resolution toon material.
  Documents the `1024_cascade` black-bake failure and why per-vertex colour is not enough.
- Landmark-derived height marks (neck/waist/hem from the front art), `--side-start`, and a guide section on
  getting consistent reference art from a model sheet plus same-chat per-view images.
- Tests: unit tests for the colour library and GPU detection, and a live end-to-end test.

## 1.0.0

- Single installable `blender-skill` with one `SKILL.md` and an internal,
  non-installable knowledge library.
- Independent MIT Blender MCP server and Blender add-on: live code execution,
  scene/data-block summaries, screenshots, viewport navigation, renders, and
  live Python API documentation.
- TRELLIS.2 vendored inference stack with weights-only download, no
  `microsoft/TRELLIS.2` clone.
- Auxiliary model handling for the non-gated sparse-structure decoder and the
  gated DINOv3/RMBG models, with explicit license guidance.
- CUDA-extension builds work on CUDA 12.0+ after a Thrust-based patch to the
  vendored CuMesh cleanup path.
- DINOv3 feature extraction supports both older `model.layer` and Transformers
  5.x `model.model.layer` layouts.
- `xformers` is installed by default for sparse attention; `--with-flash-attn`
  remains optional.
- Installer/doctor for Blender 4.5+, Python 3.10+, GPU/VRAM profiling, ports,
  harness configuration (opencode, Claude Code, Codex, Cursor, generic).
- Workspaces: production pipeline gates, ownership/version policy, examples,
  packaging tests, live MCP test, and a TRELLIS generation test.

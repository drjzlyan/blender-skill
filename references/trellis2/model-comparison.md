# Image-to-3D model comparison for stylised characters (24 GB GPU)

Measured 2026-10-27 on an RTX 4090 (24 GB), 61 GB RAM, Linux, one character (a 6-year-old girl in a flat
storybook style), one reference image (front A-pose cutout), one seed. **One character, one seed, one image:
treat this as evidence, not a leaderboard.** Reproduce with `scripts/alt_models/`.

| | TRELLIS.2 (1024_cascade) | Pixal3D (`--low_vram`, 1024) | Hunyuan3D 2.1 (shape + paint) |
|---|---|---|---|
| Fits a 24 GB card | yes | yes, **only** in low-VRAM mode (1536 / standard OOMs) | yes, as two sequential stages |
| Time | ~87 s | 169 s | 54 s shape + 46 s paint |
| Peak VRAM | fits comfortably | 14.2 GiB alloc / 15.3 reserved | shape 7.6; paint 13.4 alloc / 20.4 reserved |
| Peak RAM | n/a | 24 GiB (single-view weights only) | 12 GiB |
| Weights on disk | 18 GB | 23 GB (single-view subset of a 43 GB repo) | 14 GB + 4.5 GB `dinov2-giant` |
| Mesh | 241k faces, 83 pieces, 9,981 UV islands | 996k faces, 99 pieces, 30,864 UV islands | shape 547k faces / 22 pieces; textured **40k faces, watertight, 8 pieces**, 643 UV islands |
| Own texture | broken for flat-colour art at 1024_cascade | 4096² PBR, good | 2048² PBR + metallic + roughness, good, painterly |
| Silhouette IoU vs front art (bbox-fitted) | 0.921 | 0.909 | 0.896 |
| Face after our colour projection | good; pale crescent at eye corners | best registered; very detailed | crisp; smooth face suits flat colour |
| Side / back after projection | ghosting on torso | strongest ghosting (inner shells visible) | mildest |
| Licence | MIT | MIT (+ BiRefNet MIT; DINOv3 and MoGe weights: verify) | Tencent Hunyuan 3D 2.1 Community Licence: **does not apply in the EU, UK or South Korea**; licence needed above 1M monthly users; no using outputs to train other models |

IoU barely separates the models; the visual difference after the same projection pipeline matters more.

## What the evidence says

- **Cleanest, rig-ready mesh:** Hunyuan (40k faces, watertight, few pieces) and most consistent across views.
- **Most detail:** Pixal3D (sculpted face, hair strands), but ~1M faces with inner shells; needs decimation and
  cleanup before rigging. Its claimed pixel alignment did register the front face best.
- **Least friction:** TRELLIS.2 (already installed, MIT).
- **Face animation:** a smooth, blank face (Hunyuan shape) is easier to drive with swapped expression colour
  sets than a sculpted one.
- **Licence is the deciding risk for Hunyuan** on a globally published channel. Get it checked.

Pixal3D's pixel alignment relies on a camera estimated by MoGe, which is also a CUDA-only dependency.

## Install gotchas (each one cost time)

General: `HF_HUB_DISABLE_XET=1` (the xet backend stalled at ~0 B/s, plain HTTP gave 7-12 MB/s); run model jobs
under `systemd-run --user --scope -p MemoryMax=50G` (an out-of-memory event killed the terminal once); never run
two big downloads or a compile with a download at once; `uv pip install` of a 400 MB wheel can be slower than
`curl`. Use `--no-deps` with a fallback `.pth` to the TRELLIS venv so `uv` never pulls a second torch.

Pixal3D: needs `cmake` + `ninja` before building `natten`; its own `utils3d` wheel plus `utils3d_moge` (MoGe 3);
`einops` for the NAF upsampler; `ATTN_BACKEND=xformers` when `flash_attn` is absent. Its background remover is
BiRefNet (MIT) and is skipped for RGBA input.

Hunyuan3D 2.1: `bpy` is imported at module top but only used for OBJ->GLB (stub it, convert in real Blender and
call the paint stage with `save_glb=False`); `setuptools==69.5.1` for `pkg_resources`; `onnxruntime>=1.20`
(1.16 fails to load on newer kernels); apply `torchvision_fix.apply_fix()` before importing basicsr; build the
mesh painter with the venv's python (the stock script names the `.so` after the system python); `open3d` for
decimation (it needs the plotly/dash chain just to import); the paint stage also downloads
`facebook/dinov2-giant` (~4.5 GB) and calls `snapshot_download` on the repo id, so patch it to accept a local
directory. `scripts/alt_models/build_hunyuan_env.sh` applies all of this.

## What the Hugging Face Space does differently (read from its `app.py`, 2026-10-27)

- **Same model.** The Space loads `TencentARC/Pixal3D-T`; all 11 weight files are byte-identical (SHA-256) to
  `TencentARC/Pixal3D`. Same sampler defaults (12 steps; guidance 7.5 / 7.5 / 1.0) and the same MoGe camera estimate.
- **Same export.** `extract_glb_api` calls `o_voxel.postprocess.to_glb(remesh=True, remesh_band=1, remesh_project=0)`,
  the same rotation, and `extension_webp=True`, exactly like the local `inference.py` and this skill's TRELLIS bridge.
  There is no hidden export improvement, and Blender plays no part in it. Exporting through this skill gives the same
  mesh and texture for the same latents.
- **Standard mode on a big GPU.** `low_vram = False` (everything resident) on ZeroGPU, with a UI-chosen cascade
  resolution (the CLI defaults to 1536 in standard mode). On 24 GB, `--low_vram --resolution 1536` works: 148 s,
  18.7 GiB VRAM. It changed little for a flat cartoon character (980k faces vs 996k; main piece 97.5% vs 93.4%).
- **Generate once, export many times.** It stores the shape and texture latents, then re-decodes and re-exports with
  a chosen `decimation_target` and `texture_size`. Worth copying: save the latents, then export a ~150k-face mesh
  for rigging and a 1M-face one for a hero shot without regenerating.
- **Manual FOV override** (degrees or radians) when MoGe's estimate is poor; MoGe is trained on photos, so
  check its estimate on illustrations.
- **Presentation.** Its previews are PBR renders with HDRI lighting (forest, sunset, courtyard) and normal / clay /
  base-colour modes, rendered after `mesh.simplify(16777216)`. Part of the polished look is lighting, which this
  skill can reproduce in Blender.

Not fixed by any of that: ghosting at side angles (doubled skirt hem, see-through legs) is in the generated geometry,
and it survived the 1536 run. Cleaning inner shells and hidden faces is a Blender-side job this skill can do.

## Using them with the colour pipeline

`trellis_project_colour.py` accepts GLB or OBJ. Use `--flip-z` for models that face +Y (Pixal3D). It now bakes all
object transforms into the mesh before projecting: the shader samples rest-pose Generated coordinates, which
live in local space, so a leftover import rotation (OBJ) or flip folded the texture.

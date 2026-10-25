---
name: blender-skill
description: Self-contained Blender 4.5+ production skill. Detects prerequisites, installs an MIT Blender MCP bridge and a local TRELLIS.2 image-to-3D/PBR pipeline, and carries the full modeling, sculpting, retopo, UV, materials, lighting, animation, simulation, rendering, export, and art-direction corpus inside one skill. Use for any Blender task, AI-assisted 3D generation, or first-run machine setup.
license: MIT
metadata:
  version: "1.0.0"
  domain: blender
  role: all-in-one
  blender_min: "4.5"
  python_min: "3.10"
  mcp_server: blender-skill-mcp
  ai_backend: microsoft/TRELLIS.2-4B
  triggers: blender, bpy, bmesh, 3d model, sculpt, retopo, uv unwrap, pbr material, lighting, render, animation, rig, export fbx, export gltf, unreal, unity, godot, trellis, trellis2, image to 3d, ai 3d, generate mesh, pbr texture, blender mcp, blender setup
---

# Blender Skill

A single installable skill that owns the whole Blender production loop:

- **Machine setup** — detects Blender, Python, GPU, CUDA, VRAM, disk and network.
- **Blender MCP** — an independent MIT MCP server plus its Blender add-on, with
  live code execution, scene inspection, screenshots, renders, viewport
  navigation, and Python API documentation lookup.
- **TRELLIS.2** — a vendored MIT inference stack. Setup downloads only the
  16.24 GB model weights; no `microsoft/TRELLIS.2` repository clone is needed.
- **Knowledge** — 140+ production guides (modeling, art direction,
  pipelines, QA) that live inside `references/`. They are **not** separate
  skills. Read them directly, in place.

Never ask the user to install a pile of separate skills. Installing this one
skill is the whole setup.

---

## 0. What this skill owns

This repository owns the complete integration, not just a link list:

| Layer | Owned here |
|---|---|
| Runtime prompt | `SKILL.md`, `references/OWNERSHIP.md`, `references/PIPELINE.md` |
| Blender MCP | `mcp/` (independent MIT server) and `blender_addon/` (independent MIT add-on) |
| TRELLIS.2 | `trellis/bridge/`, `trellis/addon/`, vendored MIT inference code, weights-only download |
| Installer | `scripts/blender_skill.py`, `install.sh`, `install.ps1` |
| Knowledge | vendored MIT guides in `references/`, used in place |

The vendored guides are **source material**. They are not installable skills and
must never be "activated" or installed separately. Read the file path directly.

When a guide disagrees with another, resolve it in this order: running Blender
version → target engine → `references/PIPELINE.md` → measured evidence → ask the
user.

### Version policy

- Baseline: Blender **4.5 LTS**.
- Blender **5.x** material (slotted actions, new EEVEE settings, extension
  manifests) applies only when the running Blender is 5.x.
- If a guide assumes a feature the running Blender lacks, use the 4.x fallback
  or tell the user an upgrade is required. Never blindly apply 5.x API.

## 0.1 AI-first production, the intended use

The primary workflow is:

```text
AI base  →  production-grade  →  build on top
```

1. **AI base** — TRELLIS.2 turns one strong reference image into a dense PBR
   base mesh. This is stage 1, not a deliverable.
2. **Production-grade** — use the bundled knowledge to retopologize/decimate,
   repair UVs, rebuild materials, validate scale, rig, optimize, QA, and export.
3. **Build on top** — kitbash secondary shapes, create variants, add sockets,
   modular pieces, damage states, LODs, and scene integration without breaking
   the asset's budget, UVs, rig, or export contract.

Every stage has an explicit gate in `references/PIPELINE.md`. Do not advance a
stage because time passed; advance it because the gate passed.

---

## 1. First run: detect, then set up

Run the doctor before the first Blender task in a session:

```bash
python3 scripts/blender_skill.py doctor
```

If it reports missing pieces, run setup:

```bash
python3 scripts/blender_skill.py setup --harness auto
```

Useful forms:

```bash
# only the MCP + Blender add-on (no TRELLIS install)
python3 scripts/blender_skill.py setup --harness opencode --without-trellis

# use weights you already have instead of downloading 16.24 GB
python3 scripts/blender_skill.py setup --harness auto --model-dir /path/to/TRELLIS.2-4B

# reuse an existing working TRELLIS environment (skips a long CUDA build)
python3 scripts/blender_skill.py setup --harness auto --trellis-python /path/to/venv/bin/python

# install the skill payload into a harness without touching MCP config
python3 scripts/blender_skill.py install --harness claude

# every harness at once
python3 scripts/blender_skill.py install --harness all
```

Supported harness targets: `opencode`, `claude`, `codex`, `cursor`, `agents`,
`generic`, `all`, `auto`. `auto` detects what is present.

Setup is idempotent. It prints a JSON report and exits non-zero only when a
hard requirement is missing.

### Hard requirements

| Requirement | Rule |
|---|---|
| Blender | `>= 4.5` (override with `BLENDER_BIN`) |
| Python | `>= 3.10` for the skill scripts |
| OS | Linux or macOS; Windows through WSL for TRELLIS |
| Git | needed only when building CuMesh/FlexGEMM |
| Disk | ~25 GB free for a fresh TRELLIS setup (16.24 GB weights + venvs) |

### Soft requirements — warn, never block

TRELLIS.2 is CUDA-only. The installer detects the GPU and records the expected
behavior, but **never refuses to continue**:

| GPU / VRAM | Expected behavior |
|---|---|
| No NVIDIA GPU / no CUDA | MCP and manual Blender work function; TRELLIS generation unavailable |
| 8–15 GB VRAM | `512` pipeline only, low-VRAM mode, small textures; may OOM |
| 16–23 GB VRAM | `512` or `1024`, low-VRAM mode; slower; may OOM at 2048 textures |
| 24 GB+ VRAM | `1024_cascade` default; `1536_cascade` possible with care |
| 48 GB+ VRAM | `1536_cascade` and 4K textures comfortable |

State the detected profile to the user before a long job. If the profile is
below the requested job, warn and suggest lower settings; proceed only if the
user confirms. Never claim a job will succeed on undersized hardware.

### Downloads and paths

All runtime state is outside the repository:

| Item | Default | Override |
|---|---|---|
| Home | `~/.local/share/blender-skill` | `BLENDER_SKILL_HOME` |
| Config | `~/.config/blender-skill/config.json` | `BLENDER_SKILL_CONFIG` |
| Model weights | `<home>/models/TRELLIS.2-4B` | `--model-dir`, `TRELLIS2_MODEL` |
| TRELLIS venv | `<home>/venvs/trellis` | `--trellis-python` |
| MCP venv | `<home>/venvs/mcp` | — |
| MCP executable | `<home>/venvs/mcp/bin/blender-skill-mcp` | — |
| Outputs | `<home>/outputs` | `TRELLIS2_OUTPUT` |

No machine-specific path, username, or personal configuration belongs in this
repository. Runtime paths are resolved from environment variables and the
platform's standard config/data directories.

---

## 2. MCP and Blender add-on

The MCP server (`mcp/blender_skill_mcp`) talks to the add-on
(`blender_addon/blender_skill_mcp`) over a localhost, null-byte-delimited JSON
socket. Defaults: `127.0.0.1:9876`. The server is an independent MIT
implementation; it does not vendor Blender Lab's GPL code.

Start Blender, enable **Blender Skill MCP** in the 3D View sidebar, and press
**Start Server**. The add-on auto-starts on load by default.

### Tools

| Tool | Purpose |
|---|---|
| `execute_blender_code` | Run `bpy`/`bmesh` code in the open Blender session |
| `get_objects_summary` | Collection hierarchy and object inventory |
| `get_object_detail_summary` | Transforms, modifiers, constraints, materials, visibility |
| `get_blendfile_summary_datablocks` | Data-block counts, workspace, render engine |
| `get_blendfile_summary_path_info` | Blend path, save state, backups |
| `get_blendfile_summary_missing_files` | Missing external references |
| `get_blendfile_summary_of_linked_libraries` | Linked-library tree |
| `get_blendfile_summary_usage_guess` | Best-guess use cases with confidence |
| `get_screenshot_of_window_as_image` | Full Blender window PNG |
| `get_screenshot_of_area_as_image` | One editor area PNG |
| `get_screenshot_of_window_as_json` | Window layout, areas, active object |
| `jump_to_tab_by_name` | Switch workspace |
| `jump_to_tab_by_space_type` | Switch to a workspace by area type |
| `jump_to_view3d_object_by_name` | Frame an object in the viewport |
| `jump_to_view3d_object_data_by_name` | Frame by data-block name |
| `render_viewport_to_path` | Render with current settings |
| `render_thumbnail_to_path` | Fast low-quality preview |
| `get_python_api_docs` | API docs from the **running** Blender version |
| `search_api_docs` | Full-text search over live `bpy` docstrings |
| `search_manual_docs` | Search the bundled workflow corpus and optional manual cache |
| `trellis2_doctor` | Check the local TRELLIS environment |
| `trellis2_generate` | Image-to-3D GLB generation |
| `trellis2_texture` | PBR-texture an existing mesh |
| `trellis2_import` | Import a GLB into `COL_TRELLIS2` with provenance |
| `blender_skill_status` | Versions, paths, GPU profile, connection state |

The API-doc tools introspect the Blender that is actually running, so they
never describe a different version than the one executing the code.

### Connection discipline

- Verify the add-on is connected before the first call (`blender_skill_status`).
- If the socket refuses, tell the user to enable the add-on; do not silently
  spawn background Blender for a task that edits an open scene.
- One long-running job at a time. TRELLIS generation is GPU-bound; never run
  concurrent generations or a heavy render during generation.
- Keep code idempotent: check for existing collections/objects before creating.

### Scene preflight: detect existing work first

Before the first scene edit, TRELLIS import, or generated model in a session,
inspect the open file. `blender_skill_status` already returns `blender.objects`
and `blender.filepath`; for names, dirty state, and scenes run:

```python
import bpy

scene = bpy.context.scene
names = [o.name for o in scene.objects]
default_names = {"Cube", "Camera", "Light"}
result = {
    "file": bpy.data.filepath,
    "dirty": bool(bpy.data.is_dirty),
    "scene": scene.name,
    "objects": len(names),
    "non_default": [n for n in names if n not in default_names],
    "names": names[:25],
    "scenes": [s.name for s in bpy.data.scenes],
}
```

Treat the session as **occupied** when any of these is true:

- `bpy.data.filepath` is non-empty, or
- an object is not one of the default startup objects (`Cube`, `Camera`, `Light`), or
- more than those three objects exist, or
- another scene or a non-default collection contains user content.

When occupied, **stop and ask the user before changing anything**. Report the
file name, object count, and unsaved state, then offer:

| Choice | Action |
|---|---|
| Keep and add | Keep the scene; import/generate into a new collection with unique names |
| New scene | Create and switch to an empty scene, leaving the old scene intact |
| Save, then reset | Save the current `.blend`, then load an empty file |
| Close and reopen | Save, then the user quits and relaunches Blender; reconnect the add-on after |
| Cancel | Do not modify the scene |

Do not delete, purge, rename, or overwrite existing data until the user picks.
Do not quit Blender yourself: closing it kills the MCP server and can lose
unsaved work. The **Close and reopen** choice must be performed by the user.
After relaunch, re-enable the add-on and re-run `blender_skill_status` before
continuing.

**New scene — non-destructive, default when the user has unsaved work:**

```python
import bpy

name = "SCENE_<asset>"
scene = bpy.data.scenes.get(name) or bpy.data.scenes.new(name)
if bpy.context.window:
    bpy.context.window.scene = scene
result = {"scene": scene.name, "scenes": [s.name for s in bpy.data.scenes]}
```

Every existing object stays untouched. `trellis2_import` links its collection
into the active scene, so switch the window scene first.

**Save, then reset — destructive, only after explicit confirmation:**

```python
import bpy

if not bpy.data.filepath:
    raise RuntimeError("Save the current file to an explicit path first")
bpy.ops.wm.save_mainfile()
bpy.ops.wm.read_homefile(use_empty=True)
```

`read_homefile(use_empty=True)` loads a truly empty file; without `use_empty`
it reloads the startup scene instead. If the file has never been saved, use
`bpy.ops.wm.save_as_mainfile(filepath=<user-chosen-path>)` first. Never run this
on unsaved work.

---

## 3. TRELLIS.2 image-to-3D

TRELLIS.2 needs three model groups:

| Model | Gated | Purpose |
|---|---|---|
| `microsoft/TRELLIS.2-4B` | No | Main 4B geometry + PBR weights (16.24 GB) |
| `microsoft/TRELLIS-image-large` | No | Sparse-structure decoder |
| `facebook/dinov3-vitl16-pretrain-lvd1689m` | **Yes** | Image conditioner; accept the DINOv3 license |
| `briaai/RMBG-2.0` | **Yes** | Background removal; optional (public BiRefNet fallback or alpha input) |

The gated models are **not** bundled or redistributed. The user accepts their
licenses on Hugging Face, sets `HF_TOKEN`, and runs `trellis download`. Without
DINOv3, generation cannot run; without RMBG, supply an image with alpha or use
the fallback.

TRELLIS.2 is a **base-asset generator**, not a finished-asset pipeline. Generated
GLBs are dense, single-atlas, and frequently need cleanup, retopology or
decimation, UV validation, material repair, and QA.

### Preflight

```bash
python3 scripts/blender_skill.py trellis doctor
```

Require `ok: true`, CUDA available, CUDA extensions importable, a working sparse
attention backend (`xformers` by default, or `flash_attn`), and the model
directory present. Fix the environment before generating.

### Generate

```bash
python3 scripts/blender_skill.py trellis generate \
  --image reference.png \
  --output out/hero_prop.glb \
  --pipeline-type 1024_cascade \
  --seed 42 \
  --decimation-target 250000 \
  --texture-size 2048
```

Quality ladder:

| `--pipeline-type` | Approx. VRAM | Use |
|---|---|---|
| `512` | lower | ideation, low VRAM |
| `1024` | medium | balanced |
| `1024_cascade` | ~24 GB | default production balance |
| `1536_cascade` | high | hero detail |

Always pass `--seed` explicitly. Use `--num-samples 4` for a seed sweep;
outputs are suffixed `_00`–`_03`. Every output gets a JSON sidecar with the
seed, settings, face counts, timings, and errors.

### Parallel generation: one job at a time

**Default answer: one TRELLIS job at a time.** Each `trellis2_generate` or
`trellis2_texture` call starts a separate Python process that loads the full
model onto the default CUDA device. The MCP TRELLIS path and CLI have no shared
job queue or GPU lock. The optional TRELLIS panel rejects a second job, but that
does not protect MCP or CLI calls. Two `1024_cascade` jobs on a 24 GB card
contend for VRAM and typically OOM or crawl. GLB imports also serialize on
Blender's main thread.

To produce multiple models safely:

1. **Batch variants in one job** — `--num-samples 4` (or a seed sweep) loads the
   model once and writes outputs suffixed `_00`–`_03`. This is far faster than
   four separate calls.
2. **Queue jobs sequentially** — start the next job only after the previous
   result returns. A loop over reference images is fine.
3. **Use the wait productively** — read references, plan cleanup, inspect
   existing assets, or write scripts. Do not render, sculpt, or import while a
   generation process is running.
4. **Multiple GPUs are not supported out of the box.** Inference uses the default
   CUDA device and the MCP tool exposes no device flag. One job per GPU requires
   manual isolation (for example separate CLI processes with
   `CUDA_VISIBLE_DEVICES=0` and `=1`) plus enough VRAM per job. Verify it before
   recommending it.

If a second generation request arrives while one is active, refuse it, report
the active job, and queue it. Never rely on the client or the MCP server to
serialize calls.

### Texture an approved mesh

```bash
python3 scripts/blender_skill.py trellis texture \
  --mesh shape.glb --image reference.png \
  --output out/shape_textured.glb \
  --resolution 1024 --texture-size 2048
```

### Import and finish

Use the MCP `trellis2_import` tool (or `bpy.ops.import_scene.gltf` followed by
collection cleanup). Then:

1. Wire base-color alpha when the asset has cutouts.
2. Verify real-world scale and bounds; generated assets arrive unit-scaled.
3. Merge, recalculate normals, remove loose/interior geometry.
4. Decimate for props; retopologize characters and creatures.
5. Audit the baked UV atlas and texel density.
6. Consolidate to the project's Principled material.
7. Render a hero-angle screenshot and compare it to the reference.
8. Report seed, quality, face counts, limitations, and the next pipeline step.

Read `references/trellis2/` for CLI details, import protocol, add-on usage, and
troubleshooting.

### Reference image rules

One clear subject, centered; transparent or clean background; 1024 px on the
long edge; 3/4 or front view with a readable silhouette; even neutral light;
preserve alpha for hair, cloth, and leaves. Avoid collages, fine text, and
blown highlights.

### TRELLIS constraints

- Never import `torch`, `cumesh`, `o_voxel`, or `flex_gemm` into Blender's Python.
- Never `pip install` into Blender.
- Never ship raw TRELLIS output as final game topology.
- Never overwrite an input image or mesh.
- Never run multiple GPU jobs concurrently on one GPU.
- Never quit Blender, delete the scene, or reset the file without explicit
  confirmation.
- Never claim reference fidelity without a screenshot comparison.

---

## 4. Knowledge routing

The bundled corpus is plain Markdown under `references/`. It is intentionally
**not** a set of installable skills. Read the files directly.

Start with `references/index.md`, which lists every document, its source, and
its triggers. Then open only what the task needs.

| Task | Start here |
|---|---|
| Canonical stage order and gates | `references/PIPELINE.md` |
| Prompt rules, version policy, maintenance | `references/OWNERSHIP.md` |
| Plan a production or route a mixed task | `references/library/core/direction/` |
| Blockout, modifiers, scene organization | `references/library/core/modeling/` |
| Organic detail, wrinkles, damage | `references/library/core/sculpting/` |
| Animation-ready topology | `references/library/core/retopology/` |
| Seams, packing, texel density, UDIM | `references/library/core/uv/` |
| PBR, procedural shaders, reuse | `references/library/core/materials/`, `references/library/core/texturing/` |
| Lighting and look development | `references/library/core/lighting/`, `references/library/core/lookdev/` |
| Render, passes, color management | `references/library/core/rendering/`, `references/library/core/compositing/` |
| Rig, skin, constraints | `references/library/core/rigging/`, `references/library/core/animation/` |
| Cloth, rigid bodies, destruction | `references/library/core/cloth/`, `references/library/core/simulation/` |
| Vegetation, procedural scatter | `references/library/core/vegetation/`, `references/library/core/geometry-nodes/` |
| Game export and optimization | `references/library/core/export/`, `references/library/core/optimization/`, `references/library/core/lod/` |
| Engine-specific export | `references/library/core/unreal-export/`, `references/library/core/unity-export/`, `references/library/core/godot-export/` |
| Characters and creatures | `references/library/core/characters/`, `references/library/core/creatures/` |
| Props, hard surface, vehicles | `references/library/core/props/`, `references/library/core/hard-surface/`, `references/library/core/vehicles/` |
| Environment and architecture | `references/library/core/environment/`, `references/library/core/archviz/` |
| Art direction and mood | `references/library/core/*-style/`, `references/library/core/*-mood/`, `references/library/core/*-worlds/` |
| Genre-specific spaces | `references/library/core/genre-*/` |
| QA and shipping | `references/library/core/qa/` |
| Reference-to-3D, multi-view fitting | `references/library/roble3/guides/` |
| Pipeline automation, facial shape keys, time of day, weather (Blender 5.2+) | `references/library/el4cteo/guides/` |
| Gated image-to-game-asset process | `references/library/majid/guides/` |
| TRELLIS.2 operation | `references/trellis2/` |

### How to use the corpus

1. Read the routing entry, not the whole corpus.
2. Open only the reference files the entry points to.
3. Prefer measured evidence: viewport screenshots, render checks, polycounts,
   naming audits. Never claim success without checking.
4. When two references conflict, prefer the one matching the installed Blender
   version and the user's target engine.

---

## 5. Production loop

```text
1. INTAKE     brief with asset class, engine, budget, animation, style
2. DETECT     doctor; scene preflight; report Blender, GPU, VRAM, TRELLIS, missing pieces
              if the scene has existing items, ask: keep/add vs new scene vs save+reset
3. BASE       TRELLIS image-to-3D or manual blockout; record provenance
4. PROPORTION match landmarks; three-angle silhouette check
5. DETAIL     sculpt, hard-surface, hair, cloth, simulation as needed
6. RETOPO/UV  animation-ready topology; seams, packing, texel density
7. SHADE      PBR materials, lookdev, lighting
8. ANIMATE    rig, skin, animation, constraints (if required)
9. OPTIMIZE   decimate, LODs, collision proxies, material audit
10. VALIDATE  screenshots, polycounts, naming, scale, missing files, exports
11. DELIVER   render and/or engine export; report limitations
12. EXTEND    kitbash, variants, sockets, modularity, scene integration
```

Each stage has a numeric gate in `references/PIPELINE.md`. Do not skip
validation. Every deliverable needs at least one screenshot from the hero angle
and a numeric check (faces, materials, UVs, scale).

---

## 6. Constraints

### MUST DO

- Run `doctor` before the first task in a session.
- Run the scene preflight and get the user's choice when Blender already has
  content; prefer a new scene or collection over deleting work.
- Report the detected hardware profile before a long TRELLIS job.
- Keep runtime state outside the repository.
- Use the MCP for live scene edits; use the CLI for background/batch work.
- Keep provenance on generated objects (`trellis2_source`, seed, pipeline).
- Save renders and screenshots to explicit paths.
- Tell the user what was verified and what remains unverified.

### MUST NOT DO

- Bundle or require other installable skills; use `references/` in place.
- Hardcode a machine path, username, token, or personal config in this repo.
- Commit model weights, venvs, outputs, or downloaded documentation.
- Claim TRELLIS fidelity without a side-by-side screenshot check.
- Run destructive scene operations without confirmation.
- Run two TRELLIS generation or texture jobs concurrently on one GPU.
- Close, quit, or reset Blender or its open file without explicit confirmation.
- Install Python packages into Blender's interpreter.

---

## 7. Troubleshooting

| Symptom | Action |
|---|---|
| `doctor` says Blender missing | Install Blender 4.5+ or set `BLENDER_BIN` |
| MCP socket refused | Enable the add-on, press Start Server, check host/port |
| Add-on not listed | Re-run setup; check Blender version and extension path |
| `trellis doctor` CUDA error | Update NVIDIA driver; confirm `nvidia-smi` works |
| CUDA extension import error | Re-run `setup`; check compiler and torch version |
| OOM during generation | Use `512`, `--low-vram`, lower texture size, close other GPU apps |
| Two TRELLIS jobs OOM or stall | They are running concurrently; kill one and run jobs serially |
| Existing scene changed unexpectedly | Stop; re-run preflight, use a new scene/collection, and restore from backup |
| User asks for a fresh Blender session | Save first; quitting Blender ends the MCP connection, so reconnect after relaunch |
| Gated model `403` | Accept DINOv3/RMBG licenses, set `HF_TOKEN`, run `trellis download` |
| Model download interrupted | Re-run setup; Hugging Face resumes partial files |
| Weights path wrong | Pass `--model-dir` or set `TRELLIS2_MODEL` |
| API docs empty | Confirm the add-on is connected; docs come from the running Blender's RNA |

---

## 8. Examples

See `examples/`:

- `examples/01_hero_prop.md` — reference image → TRELLIS base → cleanup → PBR → hero render.
- `examples/02_creature.md` — creature blockout, retopo, rig-ready mesh, export.
- `examples/03_archviz.md` — measured interior, lighting, render passes, delivery.
- `examples/04_mcp_smoke.md` — minimal MCP connection and scene check.

---

## 9. Attribution

Bundled knowledge: arjun988/blender-skills (MIT), EL4CTEO/blender-skills (MIT),
RobLe3/cc-blender-skill (MIT), majidmanzarpour/blender-game-skills (MIT).
TRELLIS.2 code: Microsoft (MIT). See `THIRD_PARTY_NOTICES.md`.

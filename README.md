# blender-skill

**One installable agent skill for the entire Blender pipeline — including a
bundled Blender MCP and a local TRELLIS.2 image-to-3D / PBR stack.**

`blender-skill` is not a tutorial and not a bundle of separate skills.
It is a single skill that:

1. detects the machine's prerequisites,
2. installs an MIT Blender MCP server and its Blender add-on,
3. installs a local TRELLIS.2 inference environment and downloads only the
   model weights (no `microsoft/TRELLIS.2` clone),
4. carries the production knowledge (modeling, sculpting, retopo, UV, PBR,
   lighting, animation, simulation, rendering, export, QA, art direction)
   **inside itself**, and
5. drives Blender through the MCP.

```
                    ┌──────────────────────────────┐
                    │        blender-skill         │
                    │         (SKILL.md)           │
                    └──────────────┬───────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐        ┌────────▼────────┐        ┌────────▼────────┐
│  references/   │        │   MCP server    │        │    TRELLIS.2    │
│ 140+ guides    │        │  (MIT, Python)  │        │  vendored code  │
│ bodies in one  │        │        │        │        │  + 16.24 GB     │
│ corpus         │        │  localhost TCP  │        │  weights        │
└────────────────┘        │        │        │        └────────┬────────┘
                          │ ┌──────▼──────┐ │                 │
                          │ │ Blender     │ │                 │
                          │ │ add-on      │ │                 │
                          │ └──────┬──────┘ │                 │
                          └────────┼────────┘                 │
                                   │                          │
                            ┌──────▼──────────────────────────▼──────┐
                            │              Blender 4.5+              │
                            └────────────────────────────────────────┘
```

## Requirements

| | Requirement |
|---|---|
| **Blender** | 4.5 LTS or newer (`BLENDER_BIN` to override) |
| **Python** | 3.10+ for the skill scripts |
| **OS** | Linux or macOS; Windows through WSL for TRELLIS.2 |
| **GPU (TRELLIS.2)** | NVIDIA with CUDA. 24 GB+ VRAM recommended for the default quality |
| **Attention** | `xformers` is installed automatically; `--with-flash-attn` is optional |
| **Disk** | ~28 GB free for a fresh TRELLIS.2 setup (16.24 GB main weights + ~2.5 GB auxiliary models + venvs) |
| **Hugging Face** | A read token with access to the two gated auxiliary models below |

GPU and VRAM are **detected, never blocking**. Below the recommended profile the
skill warns that jobs will be slower or may run out of memory and offers reduced
settings. Without a CUDA GPU, MCP and manual Blender work still function;
TRELLIS.2 generation is unavailable.

## Install

```bash
git clone https://github.com/drjzlyan/blender-skill.git
cd blender-skill

# detect the harness, install the skill, MCP, add-on, and TRELLIS
python3 scripts/blender_skill.py setup --harness auto

# only the skill + MCP, no TRELLIS build
python3 scripts/blender_skill.py setup --harness auto --without-trellis

# also install the optional interactive TRELLIS.2 panel
python3 scripts/blender_skill.py setup --harness auto --with-trellis-addon
```

Harnesses: `opencode`, `claude`, `codex`, `cursor`, `agents`, `generic`, `all`,
`auto`.

The installer writes harness MCP configuration idempotently and prints what it
changed. It never commits secrets or machine-specific paths to the repository.

### Gated auxiliary models

TRELLIS.2 also loads two gated models that this repository does **not** bundle or
redistribute:

| Model | Required | License |
|---|---|---|
| `facebook/dinov3-vitl16-pretrain-lvd1689m` | Yes — image conditioner | DINOv3 License (non-commercial) |
| `briaai/RMBG-2.0` | No — background remover | BRIA RMBG License (non-commercial) |

Accept both on Hugging Face with the account that owns your token:

1. https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m
2. https://huggingface.co/briaai/RMBG-2.0

Then:

```bash
export HF_TOKEN=hf_...
python3 scripts/blender_skill.py trellis download
```

Without DINOv3, generation cannot run. Without RMBG, use an image with alpha or
let the bridge fall back to the public BiRefNet. The non-gated sparse-structure
decoder (`microsoft/TRELLIS-image-large`) downloads automatically.

### Using existing TRELLIS assets

```bash
# use weights you already downloaded
python3 scripts/blender_skill.py setup --harness auto --model-dir /data/models/TRELLIS.2-4B

# reuse a working TRELLIS Python environment
python3 scripts/blender_skill.py setup --harness auto --trellis-python /data/venvs/trellis/bin/python
```

## First-run behavior

`python3 scripts/blender_skill.py doctor` reports:

- Blender version and executable
- Python version
- NVIDIA GPU, driver, VRAM, and the inferred TRELLIS quality profile
- MCP venv/executable and add-on install state
- TRELLIS venv, CUDA extensions, and model weights
- free disk
- harness config presence

Setup order:

1. validate Blender and Python;
2. create the MCP venv and install `blender-skill-mcp`;
3. install and enable the Blender add-on;
4. write harness MCP config;
5. create the TRELLIS venv, install PyTorch, xformers, and the vendored CUDA extensions;
6. download `microsoft/TRELLIS.2-4B` plus the sparse-structure decoder;
7. download the gated DINOv3/RMBG auxiliary models when the token is authorized;
8. run the doctor and a short smoke test.

Every step is idempotent and can be run alone.

## MCP tools

The server exposes live-scene tools rather than a script generator:

| Area | Tools |
|---|---|
| Execution | `execute_blender_code` |
| Scene | `get_objects_summary`, `get_object_detail_summary`, `get_blendfile_summary_*` |
| Visual | `get_screenshot_of_window_as_image`, `get_screenshot_of_area_as_image`, `get_screenshot_of_window_as_json` |
| Navigation | `jump_to_tab_by_name`, `jump_to_tab_by_space_type`, `jump_to_view3d_object_by_name`, `jump_to_view3d_object_data_by_name` |
| Render | `render_viewport_to_path`, `render_thumbnail_to_path` |
| Docs | `get_python_api_docs`, `search_api_docs`, `search_manual_docs` |
| TRELLIS.2 | `trellis2_doctor`, `trellis2_generate`, `trellis2_texture`, `trellis2_import` |
| Diagnostics | `blender_skill_status` |

API documentation is read from the **running** Blender, so it always matches the
version executing the code. No 27 MB GPL documentation copy is vendored.

## TRELLIS.2

TRELLIS.2 runs in an isolated Python environment. Blender only imports the
resulting GLB. The inference code is vendored under `trellis/vendor/` (MIT);
only the model weights are downloaded.

```bash
# environment check
python3 scripts/blender_skill.py trellis doctor

# image -> GLB
python3 scripts/blender_skill.py trellis generate \
  --image reference.png \
  --output outputs/hero_prop.glb \
  --pipeline-type 1024_cascade \
  --seed 42 \
  --decimation-target 250000 \
  --texture-size 2048

# PBR texture an existing mesh
python3 scripts/blender_skill.py trellis texture \
  --mesh shape.glb --image reference.png \
  --output outputs/shape_textured.glb
```

Quality/resolution guidance and post-processing rules are in
`references/trellis2/`.

## Production philosophy

The intended workflow is **AI base → production-grade → build on top**:

1. **AI base** — TRELLIS.2 generates a dense PBR base mesh from a single strong
   reference.
2. **Production-grade** — the bundled corpus drives retopology/decimation, UV
   repair, material rebuild, scale validation, rigging, optimization and export.
3. **Build on top** — kitbash, variants, sockets, modularity, damage states and
   scene integration without breaking the budget, UVs, rig or export contract.

Every stage has an explicit gate in `references/PIPELINE.md`. Prompt rules,
version policy, and conflict resolution live in `references/OWNERSHIP.md`.

## What you can build

The corpus covers the whole production surface. Representative outputs:

- **Game props** — hard-surface weapon or tool from a concept image: TRELLIS
  base, cleanup, UV repair, PBR, LODs, Unreal/Unity/Godot export.
- **Characters and creatures** — blockout or image-to-3D base, retopology,
  sculpt detail, rig-ready topology, hair cards, clothing, facial shape keys.
- **Environments** — modular kits, terrain, vegetation scatter with Geometry
  Nodes, set dressing, lighting, and streaming-friendly scene assembly.
- **Archviz** — measured interiors/exteriors, PBR material libraries, HDRI and
  three-point lighting, render passes, compositing, still or animation delivery.
- **Vehicles and mechs** — proportion-driven hard surface, panel flow, greebles,
  LODs, collision proxies.
- **Stylized and genre work** — anime, cartoon, low-poly, PSX, voxel, noir,
  horror, sci-fi/punk, fantasy, historical, and genre-specific spaces.
- **Animation and simulation** — walk/run/idle cycles, mechanical rigs, cloth,
  rigid bodies, destruction, VFX, camera animation.
- **Full QA** — polycount, topology, UV efficiency, material count, naming,
  missing files, export validation, ship/no-ship verdicts.

## Examples

| Example | Shows |
|---|---|
| [`examples/01_hero_prop.md`](examples/01_hero_prop.md) | Reference image → TRELLIS → cleanup → PBR → hero render |
| [`examples/02_creature.md`](examples/02_creature.md) | Creature base, retopo, rig-ready deliverable |
| [`examples/03_archviz.md`](examples/03_archviz.md) | Measured interior, lighting, passes, delivery |
| [`examples/04_mcp_smoke.md`](examples/04_mcp_smoke.md) | Minimal MCP connection and scene validation |

## Tests

```bash
# fast, no GPU
python3 scripts/blender_skill.py test fast

# live MCP against a running Blender with the add-on enabled
python3 scripts/blender_skill.py test mcp

# one small TRELLIS generation, import, and render
python3 scripts/blender_skill.py test trellis --pipeline-type 512

# everything
python3 scripts/blender_skill.py test all
```

The test suite covers:

1. **Installer/prereq** — version parsing, GPU profile inference, dry-run.
2. **Packaging** — single-skill manifest, no nested installable skills, no
   machine paths, attribution present.
3. **MCP unit** — protocol framing, tool registration, docs index.
4. **MCP live** — connect to the add-on, create an object, read the scene,
   capture a screenshot, render a thumbnail.
5. **TRELLIS** — doctor, one 512 generation, sidecar validation, GLB import,
   face-count and material checks.

A release is only tagged when 1–4 pass and 5 passes on a CUDA machine with the
recommended VRAM profile.

## Repository layout

```
SKILL.md                    single installable skill
README.md
LICENSE                     MIT
THIRD_PARTY_NOTICES.md
install.sh / install.ps1    thin wrappers
scripts/                    installer, doctor, tests, adapters
mcp/                        MIT MCP server package
blender_addon/              Blender add-on (socket server, panel, prefs)
trellis/                    bridge, add-on, vendored inference code
references/
  index.md                  full corpus index
  OWNERSHIP.md              prompt rules, version policy, maintenance
  PIPELINE.md               canonical stage order and gates
  library/                  internal guides: core/ + el4cteo/ + roble3/ + majid/
  trellis2/                 TRELLIS.2 operating references
examples/                   worked end-to-end recipes
tests/                      unit + integration tests
```

## Known limitations

- **TRELLIS.2 output is a base asset**, not shipping topology. It must be
  retopologized/decimated, UV-audited, and material-checked.
- **No normal map** is generated by TRELLIS.2; author one if required.
- **No multi-view conditioning**; one strong reference view per generation.
- **Texturing normalizes to a unit AABB**; fit it back to the original bounds.
- **Gated auxiliary models** require license acceptance and a Hugging Face token.
- **One GPU job at a time** on 24 GB cards.
- **Windows** needs WSL for the TRELLIS environment; Blender/MCP run natively.
- **Blender 5.x-only features** in the 5.2 supplement are gated at runtime; the
  baseline is 4.5 LTS.

## Security

- The MCP executes arbitrary Python in the Blender process. It is a local
  developer tool: bind to `127.0.0.1`, never expose the port.
- No telemetry.
- No credentials are stored in the repository. Hugging Face tokens, if needed,
  are read from the user's environment.
- Model weights and downloaded documentation are excluded from git.

## Credits

Knowledge corpus: [arjun988/blender-skills](https://github.com/arjun988/blender-skills),
[EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills),
[RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill),
[majidmanzarpour/blender-game-skills](https://github.com/majidmanzarpour/blender-game-skills).
TRELLIS.2: [Microsoft](https://github.com/microsoft/TRELLIS.2).
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

MIT. Bundled third-party material keeps its own license; see the notices.

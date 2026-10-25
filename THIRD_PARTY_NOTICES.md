# Third-party notices

This repository is MIT licensed. It bundles or derives from the following
projects. Each upstream license is reproduced or referenced below; the full
text ships with the vendored material where required.

## Knowledge corpus

| Upstream | Version / commit | License | What is bundled |
|---|---|---|---|
| [arjun988/blender-skills](https://github.com/arjun988/blender-skills) | 1.3.0 | MIT | 94 production guides, flattened into `references/library/core/` |
| [EL4CTEO/blender-skills](https://github.com/EL4CTEO/blender-skills) | current | MIT | Non-duplicate Blender 5.2 pipeline guides in `references/library/el4cteo/` |
| [RobLe3/cc-blender-skill](https://github.com/RobLe3/cc-blender-skill) | 1.4.0 | MIT | Non-duplicate reference-to-3D, fitting, and validation guides in `references/library/roble3/` |
| [majidmanzarpour/blender-game-skills](https://github.com/majidmanzarpour/blender-game-skills) | current | MIT | Image-to-3D production gates in `references/library/majid/` |
| [microsoft/TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | `75fbf01` | MIT | `trellis/vendor/trellis2/`, `trellis/vendor/o-voxel/`, `trellis/vendor/configs/`, bridge and add-on in `trellis/`; example reference image in `examples/assets/` |
| [JeffreyXiang/CuMesh](https://github.com/JeffreyXiang/CuMesh) | `12289e1` | MIT | `trellis/vendor/CuMesh/` (Thrust sort patch for CUDA 12.0+) |
| [JeffreyXiang/FlexGEMM](https://github.com/JeffreyXiang/FlexGEMM) | `6dd94a8` | MIT | `trellis/vendor/FlexGEMM/` |
| [Eigen](https://gitlab.com/libeigen/eigen) | vendored | MPL-2.0 | `trellis/vendor/o-voxel/third_party/eigen/`, unmodified |

Upstream MIT copyright lines:

```
Copyright (c) 2026 blender-skills contributors
Copyright (c) 2026 EL4CTEO
Copyright (c) 2026 RobLe3
Copyright (c) 2026 Majid Manzarpour
Copyright (c) Microsoft Corporation
```

## Installed at setup, not redistributed

| Component | License | Why it is not in this repository |
|---|---|---|
| [Blender](https://www.blender.org/) | GPL-3.0-or-later | Installed by the user |
| [Blender Lab MCP](https://www.blender.org/lab/mcp-server/) | GPL-3.0-or-later | Reference only; this repo ships an independent MIT MCP implementation |
| `mcp` Python SDK | MIT | Installed from PyPI |
| PyTorch | BSD-3-Clause | Installed from PyTorch indexes |
| [nvdiffrast](https://github.com/NVlabs/nvdiffrast) | NVIDIA Source Code License (1-way commercial) | Built from a pinned upstream revision; review the upstream license before use |
| TRELLIS.2-4B weights | MIT | Downloaded (16.24 GB) from Hugging Face at setup, never committed |
| [microsoft/TRELLIS-image-large](https://huggingface.co/microsoft/TRELLIS-image-large) | MIT | Sparse-structure decoder, downloaded at setup |
| [facebook/dinov3-vitl16-pretrain-lvd1689m](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m) | DINOv3 License (gated, non-commercial) | User must accept the license before download |
| [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0) | BRIA RMBG License (gated, non-commercial) | Optional; the bridge falls back to public BiRefNet or alpha input |

## Documentation

The Blender Python API reference and user manual are **not** vendored. API
documentation is queried live from the running Blender through its RNA
descriptions, so it always matches the installed version. Manual search covers
the MIT-licensed workflow guides in `references/library/`. No GPL documentation
is redistributed by this repository.

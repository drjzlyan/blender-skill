# Ownership, prompt rules, and maintenance

This repository **owns** the integration. The vendored knowledge is source
material, not a set of instructions to install or activate other skills.

## What we own

| Layer | Owner | Notes |
|---|---|---|
| `SKILL.md` and `references/OWNERSHIP.md`, `PIPELINE.md` | this repo | Runtime prompt and production contract |
| `mcp/` | this repo | Independent MIT MCP server |
| `blender_addon/` | this repo | Independent MIT add-on |
| `trellis/bridge/`, `trellis/addon/` | this repo | Adapted bridge and UI |
| `trellis/vendor/` | Microsoft/JeffreyXiang (MIT), Eigen (MPL-2.0) | Inference code; CuMesh carries a documented CUDA 12.0 sort patch |
| `references/library/` | upstream (MIT) | Knowledge, used in place |

## Prompt rules for the agent

1. **Never install or activate another skill.** Read the internal guide at the
   path given by `references/index.md` or the routing table in `SKILL.md`.
2. **Read only what the task needs.** Do not dump the corpus into context.
3. **Prefer measured evidence.** Screenshots, renders, polycounts, UV checks,
   missing-file scans, engine round-trips.
4. **State the Blender version before applying version-specific advice.**
   - Baseline: Blender 4.5 LTS.
   - 5.x-only material (slotted actions, new EEVEE settings, extension
     manifests) applies only when the running Blender is 5.x.
   - If a guide assumes a feature the running Blender lacks, use the 4.x
     fallback or tell the user the upgrade is required.
5. **Do not claim reference fidelity** without a side-by-side screenshot.
6. **Do not present AI-generated geometry as finished.** TRELLIS.2 output is a
   base asset.
7. **No machine-specific paths.** Use the resolved skill paths and environment
   variables.
8. **One GPU job at a time.**

## Conflict resolution

When two guides disagree:

1. The running Blender version wins over a guide's assumed version.
2. The target engine's export/import rules win over generic advice.
3. `references/PIPELINE.md` wins on stage order and gates.
4. Measured evidence wins over prose.
5. If still ambiguous, ask the user; do not silently pick.

## Maintenance

1. Update a vendored pack from its upstream, keeping the license.
2. Rename every `SKILL.md` to `guide.md` so it is not installable on its own.
3. Regenerate `references/index.md`.
4. Run `python3 scripts/blender_skill.py test fast`.
5. Run a live MCP and one TRELLIS job if the change touches those layers.
6. Bump `metadata.version` in `SKILL.md` and `README.md`.

## Attribution

See `THIRD_PARTY_NOTICES.md`. Bundled MIT text keeps its upstream copyright.
Our original integration code is MIT.

---
title: "Mascot Logo Reconstruction"
summary: "Orchestrate a fail-gated, source-locked Blender reconstruction of mascots, logos, brand avatars, and stylized flat characters from wireframes, texture packs, and orthographic views. Use when the user requires a 1:1 brand/model match rather than a plausible stylized interpretation."
applies_to: "Blender 4.5+"
---
# Mascot Logo Reconstruction

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

## MCP backend

Use when: Brand mascot/logo 3D reconstruction, exact part counts, texture-driven model matching, repeated “does not match reference” feedback, or full pipeline coordination across analysis, contour mesh, registration, UV fitting, validation, animation, and export.

Before the first Blender call, read [../text-to-blender/references/mcp-backends.md](../text-to-blender/references/mcp-backends.md). Prefer official MCP for shared capabilities; preserve the selected backend for the whole task. Tool names in recipes are client/legacy examples: map them through that reference and its agent-host guide.
# Mascot / Logo Reconstruction

This is the top-level guide for 1:1 brand mascot reconstruction. It chains the internal guides and enforces stop/go gates.

## Harmonization requirement

For mascot/logo work, use `Guide Harmonizer` first when multiple source types or validation failures are present. It sets canonical source policy and prevents conflicts between reconstruction, UV, fit-repair, lighting, export, and animation guides.

## Guide chain

1. `reference-analysis-validator` — source inventory, manifest, part counts, masks.
2. `orthographic-registration` — shared front/side/back/top coordinate contract.
3. `contour-to-mesh` — structural meshes from measured silhouettes.
4. `atlas-uv-fitting` — per-part texture/UV fitting.
5. `Materials` / `Lighting` — only after geometry and UVs pass.
6. `reference-analysis-validator` again — overlay gates before export.
7. `Export` — export only after gates pass.
8. `Animation` — only after static model is accepted.

## Non-negotiable order

Static reference fidelity comes before animation and beauty rendering.

```
measure → manifest → contour meshes → depth registration → UV fit → overlay validation → export → animation
```

## Hard gates

- expected structural part count equals Blender scene/export structural part count.
- front silhouette overlay passes threshold.
- face/features landmarks pass tolerance.
- side/back/top renders match their registered envelopes.
- texture atlas regions are mapped per part.
- optional aura/background is separated from base structural GLB.

## Modeling guidance

- Treat mascots/logos as designed symbols, not natural objects. Symmetry is not guaranteed.
- Do not infer hidden leaves/petals from radial math.
- Avoid primitive-first construction when a silhouette exists.
- Use semantic object names and validation prints.

## Source-manifest structural part invariant

Create exactly the structural parts declared by the source manifest. Extra background arcs, glow, aura, shadows, guide marks, and decorative rings are context/decor unless the manifest explicitly promotes them to structural geometry.

## Front-plane rotation rule

In this Blender coordinate convention, the front camera looks along the Y axis and the reference silhouette lives in the X/Z plane. Therefore 2D rotations inside the front view are rotations around the **Y axis**, not around Z. Use `rotation_euler = (0, angle, 0)` for 2D component orientation in the front projection. Z rotation spins objects into/out of screen-space incorrectly for X/Z-plane meshes.

## Output contract

Every final reconstruction folder should include:

- `reference_manifest.json`
- `registration_report.json`
- `atlas_regions.json`
- `validation/front_mask_validation.json`
- `validation/front_overlay_reference.png`
- named `.blend`
- base `.glb`
- optional aura/context `.glb`
- `BUILD_NOTES.md` with pass/fail gates

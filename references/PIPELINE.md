# Production pipeline and gates

This is the canonical order for every asset in this skill. A stage is not
"done" until its gate passes. AI generation is stage 1, never the finish line.

## Stage 0 — Intake

Record:

- asset class (prop, weapon, character, creature, vehicle, environment, kit,
  architecture, VFX)
- target engine and platform (Unreal, Unity, Godot, web, cinematic)
- budget: triangles/vertices, texture sizes, material count, LODs
- animation requirement and rig type
- art direction (style, mood, genre, reference images)
- delivery format and naming convention

**Gate:** a written brief with numbers. No modeling before this.

## Stage 1 — Base asset

Choose one:

- **TRELLIS.2 image-to-3D** when a single strong reference exists and speed
  matters.
- **Manual blockout** when proportions, multi-view accuracy, or mechanical
  fit matters.
- **Hybrid** when TRELLIS gives a silhouette and manual modeling adds the
  structure.

TRELLIS rules: explicit seed; `512` for ideation, `1024_cascade` for production
balance; validate the sidecar; one job at a time. Read
`references/trellis2/README.md`.

**Gate:** silhouette reads from three angles; scale is plausible; provenance is
recorded.

## Stage 2 — Proportion and blockout

- Match the largest landmarks first.
- Keep modifiers non-destructive.
- Check the silhouette at thumbnail size.
- Compare against the reference with a matched camera.

**Gate:** front/side/3-4 screenshots pass; no unresolved proportion notes.

## Stage 3 — Detail and sculpt

- Secondary forms before tertiary detail.
- Detail only where the camera or gameplay sees it.
- Use alphas for scales, wrinkles, damage; keep them readable at final distance.
- Remesh for sculpting, not for delivery.

**Gate:** detail holds at the hero angle; no floating geometry; no unreadable
noise.

## Stage 4 — Retopology and UV

- Quad-dominant deformation mesh for characters/creatures; clean triangulated
  optimized mesh for props.
- Edge loops follow joints.
- Seams in hidden areas; consistent texel density; no overlapping UVs except
  intentional symmetry.
- Bake high-to-low maps before discarding the high-poly.

**Gate:** animation test pose (if rigged); UV checker render; texel density
report; no missing bake maps.

## Stage 5 — Materials and look development

- One Principled material per logical surface group.
- Correct color spaces: sRGB base color, Non-Color data maps.
- PBR values, not guesses.
- Lookdev with the final lighting and camera.

**Gate:** three-angle material check; no black/white clipping; alpha tested on a
light background.

## Stage 6 — Rig and animation (if required)

- Armature at rest, clean weights, tested extreme poses.
- IK/FK only where needed.
- Animation curves checked in the Graph Editor for pops and interpolation.
- Game-ready clips named and exported with the correct frame range.

**Gate:** deformation test render; clip list; no unweighted vertices; root
motion verified.

## Stage 7 — Optimization, LOD, collision

- Decimate or retopologize to budget.
- Generate LOD1/LOD2 with preserved silhouette.
- Author UCX/UHX or simple collision proxies.
- Audit material slots and texture memory.

**Gate:** triangle counts within budget at every LOD; collision behaves in the
engine; no material bloat.

## Stage 8 — Export and QA

- Export with the engine-specific skill.
- Verify scale (meters/centimeters), pivot, rotation, normals, tangents,
  materials, animation, and collision after import.
- Scan for missing files and broken references.
- Render a final hero screenshot.

**Gate:** engine round-trip passes; QA checklist signed off; limitations
reported.

## Stage 9 — Build on top

After the base asset ships, extend it deliberately:

- **Kitbash**: add secondary shapes and hard-surface details.
- **Variants**: material swaps, faction skins, damage states, colorways.
- **Modularity**: snap points, tiling pieces, sockets, decals.
- **Systems**: sockets for VFX, attachment points, animation notifies.
- **Scene integration**: set dressing, lighting, LOD streaming.

**Gate:** the extension does not break the original budget, UVs, rig, or export
contract. Re-run the relevant gates.

## Evidence format

Every deliverable reports:

```json
{
  "asset": "name",
  "blender": "5.2.2",
  "engine": "unreal",
  "source": "trellis2 | manual | hybrid",
  "seed": 42,
  "pipeline": "1024_cascade",
  "triangles": {"lod0": 48000, "lod1": 12000, "lod2": 3000},
  "textures": ["2048 basecolor", "2048 normal", "1024 orm"],
  "materials": 3,
  "uv": "non-overlapping, texel density 10.24 px/cm",
  "collision": "UCX_ 12 convex hulls",
  "screenshots": ["hero.png", "side.png"],
  "limitations": ["normal map authored, not generated"]
}
```

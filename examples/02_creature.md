# Example 2 — Creature from concept to rig-ready mesh

**Goal:** produce a creature that is believable in silhouette, has animation
topology, and exports cleanly.

**Skills used:** `references/library/core/creatures`, `character-archetypes`,
`sculpting`, `retopology`, `rigging`, `materials`, `qa-review`.

## 1. Decide the source

| Source | Use when |
|---|---|
| TRELLIS.2 image-to-3D | one strong concept image, fast silhouette exploration |
| Manual blockout | multi-view references, exact proportions, mechanical parts |

For TRELLIS, follow `references/trellis2/` and generate at `1024_cascade` with a
seed sweep (`--num-samples 4`). Pick the best silhouette, not the best texture.

## 2. Blockout or import

Manual blockout:

- Build primary masses with primitives and a Mirror modifier.
- Match the reference's largest landmarks first: shoulder width, hip width,
  head size, limb length.
- Keep the blockout non-destructive until proportions are approved.

TRELLIS import:

```json
{"tool": "trellis2_import", "glb": "…/creature_base.glb"}
```

Treat it as a **sculpt base**, not a rig-ready mesh.

## 3. Sculpt and detail

Follow `references/library/core/sculpting/`:

1. Voxel remesh at a resolution that preserves the silhouette.
2. Block secondary forms (muscle groups, brow, jaw, joints).
3. Add tertiary detail only after the form reads from three angles.
4. Use alpha stamps for scales, wrinkles, and damage; keep them subtle.

Take viewport screenshots at front, 3/4, and side after each major pass.

## 4. Retopology

Follow `references/library/core/retopology/`:

- Quad-dominant, edge loops around eyes, mouth, shoulders, hips, knees.
- Deformation loops follow the joint, not the surface detail.
- Target density from the engine budget, not from the sculpt.
- Transfer detail to a normal map; do not ship the multires mesh.

## 5. UV and materials

Follow `references/library/core/uv/` and `materials/`:

- Seams in hidden areas; pack to a consistent texel density.
- One material set per logical surface group.
- Bake AO, curvature, and normals; keep base color/roughness/metallic readable.

## 6. Rig and validate

Follow `references/library/core/rigging/`:

- Build the armature at rest, then skin with clean weight groups.
- Test extreme poses for shoulders, hips, jaw, and tail.
- Add IK/FK only where the animation needs it.
- Re-check deformation with a simple pose render.

## 7. Deliver

Export the rigged mesh with `references/library/core/export/` (or the target
engine skill). Validate the skeleton, skin weights, material slots, and scale in
the destination engine. Report topology budget, texture sizes, and any remaining
deformation issues.

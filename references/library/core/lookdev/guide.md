---
title: "Lookdev"
summary: "Look development loop for Blender assets combining materials, lighting, camera, and screenshot comparison until shading reads correctly via MCP."
applies_to: "Blender 4.5+"
---

# Lookdev

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

Material + light + camera loop. Screenshot compare. Stop when it reads.

## When to Use

- Finalizing asset shading before export/portfolio
- Turntable / grey shader checks
- Matching material references
- Bridging `materials` and `lighting` intentionally

## Workflow

```
Clay/grey pass → Base materials → Neutral light rig
  → Beauty light → Screenshot → Gap list → Iterate (≤3–5)
  → Optional grade → QA
```

## Generated Asset Lookdev (TRELLIS.2)

TRELLIS.2 materials already contain baked color and wear. Do not stack heavy
procedural detail on top before auditing them:

- Grey/clay pass first to judge generated silhouette and topology.
- Neutral 3-point light before HDRI; generated textures can hide form issues.
- Compare against the source reference at the hero angle.
- Check alpha edges against a light background for cutouts/foliage.
- If the generated material reads flat, verify texture color spaces and
  metallic/roughness channels before adding new nodes.

## Standard Rigs

| Rig | Use |
|-----|-----|
| Neutral 3-point | Evaluate materials fairly |
| HDRI studio | Product / character |
| In-situ scene lights | Final context |

Keep a reusable `COL_Lookdev_Lights` + `CAM_Lookdev_*`.

## Checklist

- [ ] Values read in grayscale
- [ ] Specular roughness believable
- [ ] Edges catch light (bevels/normals)
- [ ] Emissive under control
- [ ] No pure black / pure white traps unless stylized
- [ ] Matches reference palette if provided

## Iteration Rule

Each pass: change one major variable (material OR light OR camera), then screenshot.

## Constraints

### MUST DO
- Grey pass before fancy textures when forms unsure
- Capture screenshots each iteration
- Hand off to `QA` before ship

### MUST NOT DO
- Fix modeling problems only with roughness maps
- Infinite tweak loops without gap list

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|----------|
| Lookdev Rig | `references/lookdev-rig.md` | When needed |
| Lookdev Checklist | `references/lookdev-checklist.md` | When needed |

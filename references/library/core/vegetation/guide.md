---
title: "Vegetation"
summary: "Vegetation and foliage authoring for Blender including trees, plants, grass cards, canopy LODs, and game-friendly leaf atlases via MCP."
applies_to: "Blender 4.5+"
---

# Vegetation

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

Believable plants. Card efficiency. Wind-ready pivots. Canopy LODs.

## When to Use

- Trees, bushes, grass, ivy, flowers
- Forest kits and hero trees
- Grass card / leaf atlas workflows

## Path Decision

```
Hero tree close-up → Branch hierarchy + leaf cards
Background forest → Billboards / GN instances + heavy LOD
Grass field → Cards + GN scatter
```

## Workflow

```
Trunk/branch blockout → Branch levels → Leaf/card placement
  → Atlas materials → Wind vertex colors → LODs → Scatter
```

## AI-Generated Plant Base (TRELLIS.2)

Use `TRELLIS.2 reference` for a hero plant or organic set piece from a reference
image. Preserve alpha in the reference and use `--alpha-mode blend`.

- Generated foliage is usually a solid mesh, not a card/atlas setup.
- Convert leaf masses to cards/atlases for game use.
- Retopo trunks and branches; rebuild wind-ready pivots.
- Do not use generated topology for grass scatter.

## Game Plant Structure

| Part | Notes |
|------|-------|
| Trunk | Opaque; solid materials |
| Branches | Merge small twigs early on LODs |
| Leaves | Alpha cards; atlas |
| Impostor | Billboard or baked card for far LOD |

## Atlas Rules

- Pack leaf variants in one atlas
- Consistent pivot at card base
- Alpha tested or dithered for engines

## Wind Prep

- Vertex colors: `VC_Wind` (trunk=0 → tips=1)
- Pivot at ground plant base
- Optional GN wind for cinematic only

## Constraints

### MUST DO
- Plan LODs with canopy silhouette
- Keep leaf alpha cheap
- Ground pivot correct for scatter

### MUST NOT DO
- Unique leaf mesh per leaf on game trees
- Skip impostor for dense forests

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|----------|
| AI plant base | `../../trellis2/README.md` | Reference image to hero plant |
| Leaf Atlas | `references/leaf-atlas.md` | When needed |
| Tree Lod | `references/tree-lod.md` | When needed |
| Wind Vertex Colors | `references/wind-vertex-colors.md` | When needed |

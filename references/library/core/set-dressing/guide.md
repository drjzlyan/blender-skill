---
title: "Set Dressing"
summary: "Set dressing and environmental storytelling placement for interiors and exteriors using prop density, narrative clusters, and readability rules via MCP."
applies_to: "Blender 4.5+"
---

# Set Dressing

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

Story through placement. Controlled clutter. Readable clusters.

## When to Use

- Interior/exterior dressing passes
- Narrative prop clusters
- Avoiding empty or overstuffed spaces
- After modular layout is locked

## Workflow

```
Layout locked → Hero narrative props → Secondary clusters
  → Background filler → Decals/wear → Lighting check → QA
```

## Generated Clutter (TRELLIS.2)

Use `TRELLIS.2 reference` to generate unique background/clutter props from images:

- Optimize/decimate before placing; raw generated meshes are too heavy for
  scatter.
- Keep a shared low-poly variant for repeated use.
- Vary rotation/scale/seed, not topology, when populating a set.
- Match color/value to the scene; generated palettes may be too saturated.

## Density Rules

| Zone | Density |
|------|---------|
| Hero interact zone | High intent, low noise |
| Midground | Supporting story clusters |
| Background | Sparse; silhouette only |
| Traversal path | Clearance for player/camera |

## Cluster Method

1. Pick a story beat (meal abandoned, workbench used, escape rushed)
2. Place 3–7 props that sell the beat
3. Add 1–2 wear/decal cues
4. Stop — do not fill every surface

## Prop Sources

- `props` for unique pieces
- Kitbash / modular libraries for filler
- Instance repeats; vary rotation/scale slightly

## Horror / Sparse Styles

- Fewer props, more meaning
- Negative space intentional
- Coordinate with `horror-style` / `psx-horror-style`

## Constraints

### MUST DO
- Dress after greybox navigation works
- Keep player/camera paths clear
- Instance repeated meshes

### MUST NOT DO
- Uniform clutter wallpaper
- Block doors/windows without story reason

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|----------|
| Story Clusters | `references/story-clusters.md` | When needed |
| Density Map | `references/density-map.md` | When needed |

---
title: "Props"
summary: "Everyday and hero prop modeling for furniture, tools, household objects, kitbash parts, and readable game props. Use when hard-surface is too sci-fi/mechanical and the asset is a grounded prop."
applies_to: "Blender 4.5+"
---

# Props

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

Grounded, readable props. Silhouette first. Real-world scale. Kitbash-friendly parts.

## When to Use

- Furniture, tools, containers, electronics, household objects
- Hero interactive props and background set dressing pieces
- Kitbash libraries (handles, brackets, panels, fasteners)
- When hard-surface sci-fi language would feel wrong

## Design Principles

1. **Real-world scale** — Measure against human (door 2.0–2.1m, chair seat ~0.45m)
2. **Silhouette readability** — Reads at game camera distance
3. **Wear hierarchy** — Contact edges dirty; protected faces cleaner
4. **Part logic** — Separate meshes where materials or LODs differ
5. **Pivot correctness** — Floor contact, grip, hinge, or socket as needed

## Workflow

```
Reference → Scale blockout → Primary volumes → Secondary forms
  → Edge bevels → Wear/damage → UVs → Materials → Optimize → Export
```

## AI-Generated Prop Base (TRELLIS.2)

For a concept image or a fast silhouette study, `TRELLIS.2 reference` can produce a
textured base prop:

```
Reference → TRELLIS.2 base → real-world scale → cleanup/decimate
  → UV audit → material conversion → pivot fix → optimize
```

- Generated props often have uneven topology and baked wear; refine bevels and
  construction seams manually.
- Set the correct pivot (floor, grip, hinge) after import; generated assets arrive
  centered in a unit AABB.
- Keep generated material as a texture source, then convert to project masters.

## Prop Tiers

| Tier | Tris (guide) | Detail | Use |
|------|--------------|--------|-----|
| Hero | 2k–8k | Full bevels, unique wear | Interactables, close-ups |
| Standard | 500–2k | Clean forms, shared mats | Midground |
| Background | 100–500 | Block forms, atlas mats | Far / dense dressing |

## Kitbash Rules

- Name parts `SM_KB_[Category]_[Part]`
- Keep origins at logical attach points
- Prefer modular dimensions (0.05 / 0.1 / 0.25m grid)
- Collection: `COL_Kitbash_[Set]`

## Material Guidance

- Limit unique materials; atlas where possible
- Separate glass / emissive / opaque when needed for engine
- Wear via roughness/AO, not only albedo dirt

## Handoff

- UVs → `UV`
- Look → `materials` / `lookdev`
- Placement → `set-dressing`
- Ship → `optimization` → `export` or engine export guide

## Constraints

### MUST DO
- Set real-world scale before detailing
- Place pivot intentionally
- Match prop tier to camera distance

### MUST NOT DO
- Over-greeble everyday objects
- Use sci-fi panel language on mundane props
- Skip collision planning for interactables

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|----------|
| Prop Tiers | `references/prop-tiers.md` | When needed |
| Kitbash Library | `references/kitbash-library.md` | When needed |
| Everyday Prop Checklist | `references/everyday-prop-checklist.md` | When needed |
| AI prop base | `../../trellis2/README.md` | Reference image to prop base |

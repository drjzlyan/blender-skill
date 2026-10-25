# Example 3 — Measured archviz interior

**Goal:** a believable interior still with correct scale, controlled light, and
a composited delivery.

**Skills used:** `references/library/core/archviz`, `materials`, `lighting`,
`rendering`, `compositing`, `set-dressing`, `qa-review`.

## 1. Establish real scale

- Set the scene unit system to metric, unit scale 1.0.
- Model from measurements, not from eyeballing. A door is ~2.1 m, a ceiling
  ~2.7–3.0 m, a kitchen counter ~0.9 m.
- Build walls as separate objects with thickness; do not use zero-thickness
  planes for final geometry.

## 2. Blockout and camera

1. Block the room, openings, and major furniture.
2. Choose the hero camera first. Use a 24–35 mm lens for interiors.
3. Keep verticals vertical (camera at eye height or use a shift lens).
4. Set the camera's clipping range to cover the room.

## 3. Materials

Follow `references/library/core/materials/`:

- Use PBR values, not guesses: painted wall roughness 0.6–0.9, varnished wood
  0.3–0.5, polished stone 0.1–0.25.
- Add subtle variation with procedural masks or scanned textures.
- Avoid pure white and pure black; they break the light response.

## 4. Lighting

Follow `references/library/core/lighting/`:

- Start with an HDRI for ambient direction.
- Add window portals or area lights at openings.
- Add practicals only where they motivate the shot.
- Check the exposure at the final camera, not in the viewport.

## 5. Set dressing

Follow `references/library/core/set-dressing/`:

- Dress in narrative clusters: entry, work surface, rest area.
- Keep the hero camera's foreground clear unless it frames the subject.
- Use repetition with variation; avoid perfect grids.

## 6. Render passes

Follow `references/library/core/rendering/`:

- Render beauty, AO, depth, mist, and object/material passes if compositing.
- Use denoising; raise samples only where noise survives.
- Check the render at 100% in the darkest and brightest regions.

## 7. Composite and deliver

Follow `references/library/core/compositing/`:

- Balance the exposure and white point first.
- Add glare only to motivated highlights.
- Use depth/mist to separate planes; do not fake atmosphere over the whole image.
- Deliver a still plus a short camera move only if the animation adds value.

Validate scale against a human-height reference object before delivery.

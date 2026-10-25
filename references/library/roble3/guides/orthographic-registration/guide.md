---
title: "Orthographic Registration"
summary: "Register front, side, back, and top orthographic reference views into a shared Blender coordinate contract. Use when a 3D model must match multi-view wireframes/templates, when side/back/top silhouettes are off, or before adding depth to a front-locked contour model."
applies_to: "Blender 4.5+"
---

# Orthographic Registration

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

## MCP backend

Use when: Multi-view mascot/object reconstruction, depth fitting from side/back/top views, orthographic blueprint alignment, reference planes/cameras with shared scale and centerline.

Before the first Blender call, read [../text-to-blender/references/mcp-backends.md](../text-to-blender/references/mcp-backends.md). Prefer official MCP for shared capabilities; preserve the selected backend for the whole task. Tool names in recipes are client/legacy examples: map them through that reference and its agent-host guide.
# Orthographic Registration

This guide prevents the common failure where the front view looks plausible but the side/back/top views are wrong.

## Coordinate contract

- Front view defines `X/Z` silhouette.
- Side view defines `Y/Z` depth envelope.
- Top view defines `X/Y` spread.
- Back view defines rear silhouette/material only; it must not rewrite the front silhouette.

## Workflow

1. Run `scripts/register_views.py` on the available view images.
2. Create orthographic reference planes/image empties with a single shared scale.
3. Align centerline and bbox centers before modeling.
4. Lock front X/Z boundary vertices.
5. Add Y depth from side/top envelopes using modifiers/displacement or vertex groups.
6. Validate all four cameras before export.

## Failure policy

If views disagree, front brand read wins. Document the conflict in `registration_report.json`.

## Front-plane rotation rule

In this Blender coordinate convention, the front camera looks along the Y axis and the reference silhouette lives in the X/Z plane. Therefore 2D rotations inside the front view are rotations around the **Y axis**, not around Z. Use `rotation_euler = (0, angle, 0)` for 2D component orientation in the front projection. Z rotation spins objects into/out of screen-space incorrectly for X/Z-plane meshes.

## Sources distilled

- Blender Image Empty/reference image controls for orthographic blueprints.
- OpenCV homography/alignment and geometric transforms for view registration.

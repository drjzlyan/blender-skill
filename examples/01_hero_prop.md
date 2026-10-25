# Example 1 — Hero prop from a reference image

**Goal:** turn one reference image into a production-grade game prop with a
hero render and engine export.

**Skills used:** `references/library/core/props`, `hard-surface`,
`asset-optimization`, `uv-workflow`, `materials`, `lookdev`, `rendering`,
`qa-review`, `references/trellis2`.

## 0. Preflight

```bash
python3 scripts/blender_skill.py doctor
python3 scripts/blender_skill.py trellis doctor
```

Start Blender, enable **Blender Skill MCP**, press **Start Server**. Confirm:

```json
{"tool": "blender_skill_status"}
```

## 1. Prepare the reference

One subject, centered, clean background, 1024 px long edge, readable
silhouette. For cloth or leaves, keep alpha. Do not use a collage.

## 2. Generate the base

```bash
python3 scripts/blender_skill.py trellis generate \
  --image examples/assets/angel_statue.webp \
  --output "$BLENDER_SKILL_HOME/outputs/angel_base.glb" \
  --pipeline-type 1024_cascade \
  --seed 42 \
  --decimation-target 250000 \
  --texture-size 2048
```

Read the sidecar (`angel_base.glb.json`). Require `ok: true` and a face count in
the expected range before importing.

## 3. Import and audit

```json
{"tool": "trellis2_import", "glb": "…/angel_base.glb", "collection": "COL_TRELLIS2"}
```

Then inspect:

```json
{"tool": "get_object_detail_summary", "name": "GEN_Trellis2_00"}
```

Check dimensions, materials, alpha, and provenance properties. Screenshot the
viewport from the hero angle and compare with the reference.

## 4. Make it production-grade

Apply `references/trellis2/blender-import.md`, then:

1. Merge by distance, recalculate normals, remove loose/interior geometry.
2. Decimate props to the budget; retopologize only if the silhouette demands it.
3. Audit the baked UV atlas, fix overlaps, and raise texel density where needed.
4. Consolidate to one Principled material; set base color to sRGB and
   metallic/roughness to Non-Color.
5. Add a normal map only if you author one; TRELLIS.2 does not generate it.
6. Build LOD1/LOD2 from the cleaned mesh, not from the raw remesh.

Use `references/library/core/optimization/` and
`references/library/core/lod/` for budgets and naming.

## 5. Build on top

At this point the generated mesh is only the starting point:

- Kitbash secondary shapes and hard-surface details.
- Add bevels/weighted normals where the silhouette needs crisp edges.
- Add a simple collision proxy (`references/library/core/collision/`).
- Create a material variant for a second skin or faction.

## 6. Look development and delivery

Use `references/library/core/lookdev/` for a three-angle check and
`references/library/core/rendering/` for the final render.

```json
{"tool": "render_thumbnail_to_path", "path": "…/outputs/angel_thumb.png"}
{"tool": "render_viewport_to_path", "path": "…/outputs/angel_hero.png", "width": 1920, "height": 1080}
```

Export with `references/library/core/export/` or the engine-specific skill
(`unreal-export`, `unity-export`, `godot-export`). Validate scale, pivot,
rotation, normals, materials, and collision.

## 7. Report

State the seed, pipeline, face count, texture size, poly budget, validation
results, and remaining limitations. Never claim reference fidelity without the
side-by-side screenshot.

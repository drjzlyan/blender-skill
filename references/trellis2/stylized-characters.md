# Stylized storybook characters with TRELLIS.2

Verified end to end on 2026-10-27 (RTX 4090, Blender 5.2, `1024_cascade`, ~97 s per mesh).

## Getting good reference art (this matters more than anything downstream)

Art that is generated one view at a time drifts between views, and the mesh and colour inherit that.
What worked (verified with ChatGPT image generation in the owner's signed-in Chrome, driven with
Claude in Chrome; check your plan's terms before commercial use):

1. Ask for ONE model sheet first: "character model sheet (orthographic turnaround): FRONT, LEFT SIDE
   PROFILE (facing left), BACK; same size and height, feet on one baseline; strict neutral A-pose;
   identical design in every view; flat orthographic view, no perspective, no ground shadow, no text".
   Describe the design in detail once (face, hair, outfit, palette). This locks one design.
2. In the same chat, ask for each view again as its own large portrait image ("generate ONLY the FRONT
   view of this exact same character, portrait, full body from the top of the hair to the soles,
   centred, plain white background"), then BACK, then LEFT SIDE ("true 90-degree side view, arms hang
   straight down"). Same-chat context keeps the design identical, and each view is 1024x1536, so the
   face is large enough for crisp colour.
3. Use the FRONT image for TRELLIS geometry. Read the neck, waist and hem rows off the front, back and
   side images and pass them as `--landmarks-<view>` to `trellis_prep_refs.py`.

Compared with generating each view separately from a short prompt, this removed the trousers-vs-skirt
and hands-on-hips drift entirely, so the back and side art can be trusted everywhere.

## Pipeline

```text
approved reference art (front, back, side)  ->  TRELLIS.2 geometry  ->  mesh-registered colour projection
        ->  retopo / rig (stage 4 and 6 in PIPELINE.md)  ->  animate
```

1. **Reference art.** One clean full-body character per view, neutral A-pose, arms and legs apart,
   plain white background, no ground shadow. Generate the front first; then back and side views of
   the *same* design (they drift, see below). Seated or cross-legged poses generate seated meshes.
2. **Geometry.** `trellis generate --image front.png --pipeline-type 1024_cascade --seed N`.
   Judge the silhouette from front, 3/4, side and back before anything else. A flat-colour cartoon
   reference gives a sculpted, clean chibi mesh (~250k faces).
3. **Prepare the art.** With the TRELLIS venv python (it ships numpy and OpenCV):

   ```bash
   $BLENDER_SKILL_HOME/venvs/trellis/bin/python scripts/trellis_prep_refs.py REFDIR --prefix kid \
     --front front.png:907 --back back.png:955 --side side.png:968 \
     --landmarks-back neck=318,waist=615 --landmarks-side neck=485,waist=680,hem=800
   ```

   `NAME.png:ROW` gives the row of the soles. Landmarks are art rows of the neck base, waist and
   hem; read them off the images once per character.
4. **Colour.** Run in Blender (any 4.5+):

   ```bash
   blender -b --python scripts/trellis_project_colour.py -- --glb kid.glb --dir REFDIR --prefix kid \
     --out kid-coloured.blend --render PREVIEW_DIR
   ```

   Each art is warped into a canonical orthographic image registered to the mesh silhouette row by
   row (`trellis_colour_lib.canonical_view`), packed into the `.blend`, and sampled per pixel by a
   toon material using rest-pose Generated coordinates, so colour does not swim when posed.
   Per-vertex blend weights (a `ProjW` attribute, stable under deformation) pick front, back or side
   by facing direction. The side art only takes over on near-profile surfaces (`--side-start`), so thin
   sideways features such as cheek curls keep the front/back colour. Mesh heights for the neck, waist
   and hem come from the front art's landmarks.

## Why not TRELLIS's own colour, or vertex colour

- `1024_cascade` generate bakes a near-black base colour for flat-colour cartoon input (mean RGB
  ~0.02, metallic map ~0.69) while the 512 pipeline on the same image is fine. `trellis texture`
  gives colour but leaves ~40% black voids between hundreds of UV islands. Check numerically: load
  the GLB and average `Image_0`; a mean under 0.05 is a failed bake.
- Per-vertex colour (even cleaned with palette labels and majority filtering) is too coarse for
  faces: at ~2 mm vertex spacing eyebrows, bindis and lashes smear. Colour must be texture resolution.

## Known limits (read before promising "production")

- **Feature registration.** The silhouette warp aligns bodies, not features. Generated eyes, brows
  and mouths do not sit exactly where the art draws them, so you can see a pale crescent at an outer
  eye corner. Fix with landmark-based warping (eyes, brows, nose, mouth) of the canonical front
  image; not implemented yet.
- **Back and side art drift.** Generators change the design between views (trousers vs skirt, hands
  on hips, a hallucinated bag instead of a sash). The script only trusts the back art above
  `--back-low` and inside the torso width, and the side art only for the head and below the hips.
- **Static mesh.** TRELLIS meshes have no eyeballs, lids or mouth shapes, and no rig. Animate the
  face by swapping projected expression colour sets, or add deliberate overlay meshes.

## Tests

`tests/test_trellis_colour_lib.py` (run with the TRELLIS venv python), `tests/test_gpu_detection.py`,
and `tests/live_project_colour.py` (end-to-end on a synthetic character; needs Blender and the venv).

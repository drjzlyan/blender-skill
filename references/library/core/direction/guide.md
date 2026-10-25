---
title: "Direction"
summary: "Use when starting any Blender asset task, planning a production pipeline, coordinating multiple disciplines, or matching a reference photo/concept art. Use for game-ready assets, hard surface, environment, character, creature, export, or any multi-guide Blender workflow."
applies_to: "Blender 4.5+"
---
# Direction

> Internal knowledge for **blender-skill**. Read in place; this is not an installable guide.

Senior Technical Director orchestrating AAA Blender production.

## Role Definition

A 15-year veteran Technical Art Director who has shipped AAA games on PC, console, and mobile. Specializes in pipeline architecture, cross-discipline coordination, production planning, and driving all Blender operations through MCP rather than manual UI. Acts as the single orchestrator and reads specialist guides in place.

## When to Use

- Any new Blender asset request (props, environments, characters, creatures)
- Multi-discipline tasks spanning modeling, UVs, materials, rigging, export
- Ambiguous requests needing workflow analysis
- Production planning, polycount targets, export format decisions
- Coordinating style direction (horror, lowpoly, stylized, realistic)
- **Reference image / photo match** — user attaches image and wants similar result

## Core Philosophy

Every asset follows the universal pipeline in `../references/asset-pipeline.md`. Never skip planning. Prefer MCP execution over UI instructions. Avoid destructive workflows. Deliver game-ready, validated assets.

**When a reference image is attached:** follow `../references/reference-image-match.md` end-to-end. Write Reference Analysis first (`../references/reference-analysis-template.md`). Match camera before micro-detail. Run screenshot comparison loop. Validate with `../references/visual-match-checklist.md`.

## Director Workflow

```
1. ANALYZE    → Parse request, identify asset type, target platform, art direction
2. PLAN       → Select internal guides, define polycount/texture budgets, export format
3. BRIEF      → Output structured production brief before any Blender operations
4. DELEGATE   → Read the matching internal guides in pipeline order
5. EXECUTE    → Drive work via Blender MCP (see ../references/mcp-integration.md)
6. VALIDATE   → Run checklist (../references/validation-checklist.md)
7. DELIVER    → Export + validation report
```

## Analysis Framework

Before any work, determine:

| Question | Options | Impact |
|----------|---------|--------|
| Asset purpose | Hero / Standard / Background | Polycount, texture res |
| Target | Game / Cinematic / Portfolio | Optimization level |
| Platform | Mobile / Console / PC | Budget constraints |
| Style | Horror / Lowpoly / Stylized / Realistic | Style guide activation |
| Animation | Static / Rigged / Animated | Retopo, rigging, animation guides |
| Export | FBX / GLTF / USD / Alembic | Export-pipeline config |

## Topic routing

| Request Signal | Primary guide | Supporting guides |
|----------------|---------------|-------------------|
| Image-to-3D, AI base mesh, reference-to-asset | TRELLIS.2 reference | modeling, retopology, UV, materials, optimization |
| Sci-fi, weapons, machinery, industrial HS | hard-surface | modeling, materials, optimization |
| Everyday / hero props, kitbash, furniture | props | materials, UV, set-dressing, optimization |
| Cars, ships, aircraft, mechs, transit | vehicles | hard-surface, LOD, collision, materials |
| Buildings, terrain, modular kits | environment | geometry-nodes, procedural-modeling, UV, scene-assembly |
| Trees, plants, grass, foliage | vegetation | geometry-nodes, environment, LOD |
| Human characters, clothing base mesh | characters | retopology, rigging, UV, hair, cloth |
| Hair, fur, hair cards, groom | hair | characters, materials, texturing |
| Cloth sim, garments, capes, bake | cloth | characters, simulation, animation |
| Monsters, aliens, fantasy creatures | creatures | sculpting, retopology, rigging |
| Organic detail, wrinkles, damage | sculpting | retopology, texturing |
| Clean animation mesh | retopology | characters, creatures |
| UV seams, texel density, UDIM | UV | texturing, materials |
| PBR, procedural shaders | materials | texturing, lookdev |
| Baking, normal maps, atlases | texturing | UV, materials |
| Lookdev / shading review loop | lookdev | materials, lighting, cinematography, QA |
| Scatter, procedural systems | geometry-nodes | procedural-modeling, environment |
| Mood, cinematic lighting | lighting | rendering, lookdev, horror-style |
| Camera, lenses, framing, camera moves | cinematography | rendering, lighting, animation, compositing |
| Final renders, passes | rendering | lighting, materials, compositing |
| Compositor, grade, beauty stack | compositing | rendering, lookdev, vfx-fx |
| Smoke, fire, particles, cinematic FX | vfx-fx | geometry-nodes, simulation, materials, compositing |
| Rigid/soft body, destruction | simulation | vfx-fx, collision, animation |
| Walk cycles, mechanical motion | animation | rigging |
| Bones, IK, weight paint | rigging | animation, characters |
| Rocks, roads, cables, buildings (procedural) | procedural-modeling | geometry-nodes |
| Large scene layout, linking, overrides | scene-assembly | environment, set-dressing, lighting |
| Prop placement, narrative clutter | set-dressing | props, scene-assembly, environment |
| Archviz interiors/exteriors | archviz | materials, lighting, cinematography, rendering |
| Polycount, cleanup | optimization | LOD, export, QA |
| LOD generation / validation | LOD | optimization, unity-export, unreal-export |
| UCX / convex / collider proxies | collision | LOD, unreal-export, unity-export, simulation |
| Generic FBX/GLTF/USD export | export | optimization, QA |
| Unity-specific export | unity-export | export, LOD, collision |
| Unreal-specific export | unreal-export | export, LOD, collision |
| Godot-specific export | godot-export | export, LOD, collision |
| QA gate, screenshot review, ship check | QA | optimization, lookdev, direction |
| Psychological horror aesthetic | horror-style | lighting, environment, set-dressing |
| Cosmic / Lovecraftian / eldritch | cosmic-eldritch-horror | horror-style, creatures, vfx-fx |
| Body horror / mutation | body-horror-style | horror-style, creatures, sculpting |
| Analog / VHS / found footage | analog-found-footage-horror | compositing, cinematography, horror-style |
| Liminal / Backrooms / empty mall | liminal-space-style | environment, horror-style, lighting |
| Folk horror / rural ritual | folk-horror-style | horror-style, vegetation, set-dressing |
| Mascot / puppet horror | mascot-puppet-horror | horror-style, stop-motion-craft-style, characters |
| Dreamcore / weirdcore | dream-weirdcore-style | liminal-space-style, compositing |
| Indie horror refs (SH / FtF / Puppet Combo) | indie-horror-aesthetics | horror-style, psx-horror-style, lighting |
| PSX/PS1 horror crunch | psx-horror-style | horror-style, lowpoly-style, lighting, compositing |
| PS1/PS2, Lethal Company style | lowpoly-style | environment, materials, visual-console-eras |
| Anime / cel / hard color breaks | anime-style | stylized-style, materials, rendering, characters |
| Manga value / screentone language | manga-style | anime-style, comic-book-style, compositing |
| Cartoon graphic shapes | cartoon-style | stylized-style, characters |
| Comic book / ink / halftone | comic-book-style | stylized-style, compositing |
| Pixel / texel-locked | pixel-art-style | retro-8bit-style, retro-16bit-style, hd-2d-style |
| HD-2D hybrid | hd-2d-style | pixel-art-style, environment, lighting |
| Hand-painted textures | hand-painted-style | stylized-style, texturing |
| Watercolor / oil painterly | painterly-style | hand-painted-style, compositing |
| Claymation / paper craft / stop-mo | stop-motion-craft-style | materials, characters |
| Chibi / SD proportions | chibi-style | anime-style, cartoon-style, characters |
| Noir / neo-noir | noir-style | lighting, cinematography, compositing |
| Minimalist / abstract reduce | minimalist-style | stylized-style, lookdev |
| Vector-flat graphic | vector-style | minimalist-style, cartoon-style |
| Voxel / Minecraft-adjacent | voxel-style | lowpoly-style, environment, geometry-nodes |
| Isometric / strategy / diorama | isometric-style | cinematography, environment, genre-strategy-sim |
| Frutiger Aero glossy 2000s | frutiger-aero-style | materials, lookdev, neon-retrofuturism |
| Neon / vaporwave / synthwave | neon-retrofuturism | sci-fi-punk-worlds, lighting, compositing |
| Cozy / cute / wholesome | cozy-wholesome-mood | stylized-style, lighting, set-dressing |
| Dark / gritty / decayed / industrial | dark-gritty-mood | horror-style, materials, environment |
| Dreamlike / surreal / mystical | dream-surreal-mood | dream-weirdcore-style, lighting, vfx-fx |
| Brutalist concrete mood | brutalist-mood | archviz, environment, materials |
| Fantasy / medieval / dark fantasy | fantasy-worlds | environment, props, creatures |
| Sci-fi / cyberpunk / steampunk / punks | sci-fi-punk-worlds | hard-surface, environment, vehicles |
| Historical / western / samurai / WW | historical-worlds | environment, props, characters |
| Post-apoc / dystopia / zombie | apocalypse-worlds | environment, props, vehicles |
| Underwater / desert / arctic / jungle | biome-worlds | environment, vegetation, lighting |
| Character race/role archetypes | character-archetypes | characters, creatures |
| PS1–PS5 / CRT / VHS / DOS eras | visual-console-eras | lowpoly-style, compositing, realistic |
| Action / brawler / fighting arenas | genre-action-combat | environment, vfx-fx |
| FPS / TPS / BR / extraction | genre-shooter | environment, hard-surface, collision |
| RPG / JRPG / CRPG / ARPG / MMO | genre-rpg | fantasy-worlds, environment, characters |
| Survival / survival-horror gameplay | genre-survival | environment, props, horror-style |
| Stealth spaces | genre-stealth | environment, lighting |
| Puzzle / platformer | genre-puzzle-platformer | environment, props |
| Metroidvania / roguelike / roguelite | genre-metroidvania-roguelike | environment, scene-assembly |
| Soulslike monumental dread | genre-soulslike | dark-gritty-mood, fantasy-worlds, lighting |
| Strategy / sim / city / colony / MOBA | genre-strategy-sim | isometric-style, environment |
| Racing / sports | genre-racing-sports | vehicles, environment |
| VN / walking sim / interactive movie | genre-narrative-vn | cinematography, lighting, set-dressing |
| Card / party / idle / rhythm / edu | genre-card-party-idle | props, cinematography |
| Open world / sandbox | genre-open-world-sandbox | biome-worlds, environment, LOD |
| Exaggerated, NPR, hand-painted broad | stylized-style | materials, rendering, anime-style |
| Photoreal, scan cleanup, AAA PBR | realistic | texturing, rendering, lookdev |
| **Reference photo / concept art attached** | **reference-image-match** | direction → discipline guide → style → materials → lighting → rendering |

## Reference Image Workflow (Mandatory)

When user provides a photo or render to match:

```
1. REFERENCE ANALYSIS  → reference-analysis-template.md (written, before MCP)
2. BASELINE SCREENSHOT → get_viewport_screenshot
3. CAMERA MATCH        → CAM_* + EMPTY_CamTarget_* before detailing
4. GEOMETRY TIERS      → silhouette → panel breaks → greebles
5. MATERIALS           → palette from reference; per-object emissive lights only
6. LIGHTING + WORLD    → key direction, rim, space/env mood
7. GRADING             → AgX exposure/look; EEVEE for animation preview
8. COMPARE LOOP        → screenshot → gap list → fix (×3 max)
9. VALIDATE            → visual-match-checklist.md
```

See `../references/reference-image-match.md` for full protocol and failure fixes.

## Production Brief Template

Output this before executing:

```markdown
## Production Brief: [Asset Name]

**Type:** [prop/environment/character/creature]
**Target:** [game engine / cinematic / portfolio]
**Style:** [horror/lowpoly/stylized/realistic]
**Poly Budget:** [triangles] (ref: polycount-budgets.md)
**Texture Budget:** [resolution]
**Export:** [format + settings]
**Pivot:** [floor/grip/hinge/center]
**Animation:** [none/rigged/animated]

### Active Guides
1. [guide] — [role in pipeline]
2. [guide] — [role in pipeline]

### Pipeline Phases
- [ ] Reference & Planning
- [ ] Blockout & Silhouette
- [ ] Modeling
- [ ] Cleanup & Topology
- [ ] UVs
- [ ] Materials/Textures
- [ ] Optimization
- [ ] Rig/Animate (if needed)
- [ ] Export & Validation

### MCP Execution Plan
[Ordered list of MCP operations]
```

## Multi-Guide Workflows

### Hero Prop (Hard Surface)
```
direction → hard-surface → materials → UV → optimization → export
```

### AI Base Asset (TRELLIS.2)
```
direction → TRELLIS.2 reference → modeling → retopology|optimization
  → UV → materials → lookdev → QA → export
```
Use when a reference image should become a base asset quickly. TRELLIS.2 output is
raw generated geometry: always retopologize/decimate, audit UVs and materials,
and compare against the reference before calling it production-ready.

### Everyday / Hero Prop
```
direction → props → UV → materials → lookdev → optimization → export
```

### Vehicle (Game)
```
direction → vehicles → LOD → collision → materials → unreal-export|unity-export
```

### Environment Modular Kit
```
direction → environment → geometry-nodes → UV → optimization → export
```

### Game Character
```
direction → characters → sculpting → retopology → hair → cloth
  → UV → materials → rigging → animation → export
```

### Horror Scene
```
direction → horror-style → environment → set-dressing → lighting → optimization → export
```

### PSX Horror Scene
```
direction → psx-horror-style → environment → lowpoly-style → lighting → compositing
```

### Procedural Scatter System
```
direction → geometry-nodes → procedural-modeling → optimization
```

### Cinematic Shot
```
direction → [discipline] → lookdev → cinematography → lighting → rendering → compositing → QA
```

### Engine Delivery
```
direction → optimization → LOD → collision → unity-export|unreal-export|godot-export → QA
```

## MCP Integration

1. Check Blender MCP availability before Phase 1 execution
2. Create collection hierarchy via MCP immediately
3. Query scene state after each pipeline phase
4. Never describe UI steps when MCP can execute
5. See `../references/mcp-integration.md`

## Constraints

### MUST DO
- Output production brief before modeling
- **If reference image attached:** complete Reference Analysis and camera match before geometry detail
- **Screenshot compare** after materials, lighting, and each refinement pass
- Activate appropriate style guide for art direction
- Set polycount/texture budgets explicitly
- Organize collections with `COL_` prefix from start
- Validate before declaring complete
- Coordinate guides; don't try to do everything in one pass

### MUST NOT DO
- Skip planning phase
- Skip reference analysis when user attached an image
- Keyframe emission on shared hull/structural materials
- Add micro-greebles before silhouette and panel-break tiers
- Declare "done" without visual-match checklist when reference was provided
- Start modeling without scale reference
- Mix styles without explicit direction
- Export without validation
- Explain Blender UI when MCP is available
- Apply destructive operations without backup

## Reference Guide

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Universal Pipeline | `../references/asset-pipeline.md` | Every task |
| MCP Integration | `../references/mcp-integration.md` | Before execution |
| Naming | `../references/naming-conventions.md` | Scene setup |
| Validation | `../references/validation-checklist.md` | Before delivery |
| Polycount Budgets | `../references/polycount-budgets.md` | Planning phase |
| Topic routing | `references/guide-routing.md` | Complex multi-guide tasks |
| MCP Tools | `../references/mcp-tools.md` | Before MCP execution |
| Reference Image Match | `../references/reference-image-match.md` | Photo/concept attached |
| TRELLIS.2 image-to-3D | `../../trellis2/README.md` | User wants an AI-generated base asset from an image |
| Reference Analysis | `../references/reference-analysis-template.md` | Before first MCP call |
| Visual Match Validation | `../references/visual-match-checklist.md` | Before delivery |

## Decision Trees

### Reference Image Provided?
```
User attached photo / concept / "match this"?
├── YES → reference-image-match.md (full workflow)
│         → Analyze → Camera → Geometry tiers → Materials → Lighting → Compare loop
└── NO  → Standard pipeline below
```

### Start from an Image?
```
User supplied a reference image and wants speed?
├── YES → TRELLIS.2 reference (generate base)
│         → modeling / retopology / optimization
│         → UV → materials → lookdev → QA
└── NO  → Standard pipeline below
```

### New Asset Request
```
Is style specified?
├── Horror → horror-style (+ psx-horror-style if PS1 crunch)
├── Lowpoly → lowpoly-style + relevant modeling guide
├── Anime/cel → anime-style + relevant modeling guide
├── Voxel → voxel-style + relevant modeling guide
├── Isometric → isometric-style + cinematography
├── Stylized → stylized-style + relevant modeling guide
├── Realistic → realistic + relevant modeling guide
├── Archviz → archviz + lookdev
└── Unspecified → Ask or infer from context

What is the asset?
├── Vehicle / mech → vehicles
├── Everyday / hero prop → props
├── Sci-fi / weapon / industrial HS → hard-surface
├── Human → characters (+ hair / cloth as needed)
├── Creature → creatures
├── Vegetation → vegetation
├── Environment / level → environment + scene-assembly
└── FX / sim → vfx-fx / simulation / cloth

Engine delivery?
├── Unity → unity-export
├── Unreal → unreal-export
├── Godot → godot-export
└── Generic → export

Does it need animation?
├── Yes → Add retopology, rigging, animation
└── No → Static pipeline
```

## Knowledge Reference

AAA, Blender, MCP, game-ready, technical art, pipeline, production brief, hard surface, prop artist, vehicle artist, environment art, character art, creature art, vegetation, set dressing, hair groom, cloth sim, VFX, physics, camera cinematography, compositing, lookdev, archviz, sculpting, retopology, UV unwrapping, PBR materials, texture baking, geometry nodes, procedural modeling, lighting, Cycles, Eevee, AgX, animation, rigging, LOD, collision proxy, scene assembly, QA review, export, FBX, GLTF, USD, Unity, Unreal, Godot, horror, PSX horror, lowpoly, anime, voxel, isometric, stylized, realistic, reference image match, photo match, silhouette, panel breaks, greebles, Mcp, TRELLIS.2, image-to-3D, AI base mesh, generated asset, PBR generation, COL_TRELLIS2, COL_, SM_, MAT_, LGT_, CAM_, ARM_, AN_, UCX_

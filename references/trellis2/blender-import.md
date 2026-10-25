# Blender import and cleanup

## Preferred: MCP `trellis2_import`

```json
{"glb": "/path/to/asset.glb", "collection": "COL_TRELLIS2"}
```

The tool imports the GLB, moves every new object into the target collection,
names them `GEN_Trellis2_NN`, stores `trellis2_source` and seed/pipeline
provenance when a sidecar is present, and selects the result.

## Manual import

```python
import bpy
from pathlib import Path

glb = Path("/path/to/asset.glb")
if not glb.is_file():
    raise FileNotFoundError(glb)

collection = bpy.data.collections.get("COL_TRELLIS2")
if collection is None:
    collection = bpy.data.collections.new("COL_TRELLIS2")
    bpy.context.scene.collection.children.link(collection)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(glb))
new_objects = [obj for obj in bpy.data.objects if obj not in before]

for index, obj in enumerate(new_objects):
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    collection.objects.link(obj)
    obj.name = f"GEN_Trellis2_{index:02d}"
    if obj.data:
        obj.data.name = obj.name
    obj["trellis2_source"] = str(glb)

bpy.ops.object.select_all(action="DESELECT")
for obj in new_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = new_objects[0]
```

## Alpha / opacity

TRELLIS.2 writes alpha into the base-color texture but exports the GLB as
`OPAQUE`. Enable transparency for cutouts, cloth, hair cards, or leaves.

```python
def enable_alpha(material):
    if not material or not material.use_nodes:
        return False
    nodes = material.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return False
    alpha = bsdf.inputs.get("Alpha")
    base = bsdf.inputs.get("Base Color")
    if alpha is None or base is None or not base.links:
        return False
    tex = base.links[0].from_node
    if tex.type != "TEX_IMAGE" or tex.image is None:
        return False
    if not alpha.links:
        material.node_tree.links.new(tex.outputs["Alpha"], alpha)
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    if hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
    return True

for obj in bpy.context.selected_objects:
    for slot in obj.material_slots:
        enable_alpha(slot.material)
```

Use `DITHERED` for leaves/hair to avoid sorting artifacts; use `BLEND` only when
smooth transparency is required.

## Scale and orientation

The GLB is centered in a unit AABB. Blender's importer converts glTF Y-up to
Z-up. Verify:

```python
obj = bpy.context.active_object
print(obj.dimensions)  # <= 1 on the largest axis before scaling
```

Scale to real-world size with a numeric value, then apply scale before further
modeling or export. For texture results, fit to the original object's bounds:

```python
from mathutils import Matrix, Vector

def world_bounds(objects):
    points = [o.matrix_world @ Vector(c) for o in objects if o.type == "MESH" for c in o.bound_box]
    if not points:
        return None
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi

def fit_to(imported, target_bounds):
    current = world_bounds(imported)
    if current is None or target_bounds is None:
        return
    c_lo, c_hi = current
    t_lo, t_hi = target_bounds
    c_size, t_size = c_hi - c_lo, t_hi - t_lo
    factors = [t_size[i] / c_size[i] for i in range(3) if c_size[i] > 1e-9]
    if not factors:
        return
    factor = max(factors)
    matrix = (
        Matrix.Translation((t_lo + t_hi) * 0.5)
        @ Matrix.Scale(factor, 4)
        @ Matrix.Translation(-(c_lo + c_hi) * 0.5)
    )
    roots = [o for o in imported if o.parent not in imported]
    for obj in roots:
        obj.matrix_world = matrix @ obj.matrix_world
```

## Material audit

Generated assets normally arrive with one material:

- Principled BSDF
- Base-color texture with alpha in A
- Metallic/roughness texture (roughness in G, metallic in B)
- `doubleSided` may be on

Check and fix:

- Alpha connected only when needed
- Normal map absent (TRELLIS.2 does not generate one)
- Color space (`sRGB` for base color, `Non-Color` for metallic/roughness)
- Material naming (`MAT_TRELLIS2_...`) before adding to the project library

## Geometry cleanup

1. Merge by distance (small threshold relative to scale).
2. Recalculate outside normals.
3. Remove loose geometry and interior faces.
4. Fill or repair holes if the asset must be watertight.
5. Check non-manifold edges; generated cloth/open surfaces may be intentionally
   open.
6. Decimate or retopologize. Remesh output is uniform triangles, not animation
   topology.

## Validation

- Triangle count vs budget
- UV atlas present and non-overlapping (except intentional symmetry)
- No black seams at UV borders
- Material renders correctly in EEVEE and Cycles
- Alpha test under a light background
- Screenshot from the hero angle and compare to the reference
- Object is in `COL_TRELLIS2` and provenance properties exist

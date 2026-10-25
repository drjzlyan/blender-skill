"""Python snippets executed inside Blender.

Each snippet assigns a JSON-serialisable dict to ``result``. Keeping them here
makes the MCP tools thin and auditable.
"""

from __future__ import annotations

import json
from typing import Any

OBJECTS_SUMMARY = r'''
import bpy

def _v(v):
    try:
        return [round(float(x), 5) for x in v]
    except Exception:
        return None

def _obj(o):
    return {
        "name": o.name,
        "type": o.type,
        "data": getattr(o.data, "name", None),
        "parent": o.parent.name if o.parent else None,
        "selected": bool(o.select_get()),
        "hide_viewport": bool(o.hide_viewport),
        "hide_render": bool(o.hide_render),
        "collections": [c.name for c in o.users_collection],
        "location": _v(o.location),
        "dimensions": _v(o.dimensions),
    }

def _coll(c):
    return {
        "name": c.name,
        "objects": [_obj(o) for o in c.objects],
        "children": [_coll(ch) for ch in c.children],
    }

scene = bpy.context.scene
result = {"scene": scene.name if scene else None, "collections": [], "orphan_objects": [], "active": None}
if scene:
    result["collections"] = [_coll(c) for c in scene.collection.children]
    in_scene = {o.name for o in scene.objects}
    result["orphan_objects"] = [_obj(o) for o in bpy.data.objects if o.name not in in_scene]
active = bpy.context.view_layer.objects.active
result["active"] = active.name if active else None
'''

OBJECT_DETAIL = r'''
import bpy

name = {name}
o = bpy.data.objects.get(name)
if o is None:
    result = {{"error": "object not found", "name": name, "available": [x.name for x in bpy.data.objects][:200]}}
else:
    def _v(v):
        try:
            return [round(float(x), 6) for x in v]
        except Exception:
            return None
    result = {{
        "name": o.name,
        "type": o.type,
        "data": getattr(o.data, "name", None),
        "data_type": type(o.data).__name__ if o.data else None,
        "parent": o.parent.name if o.parent else None,
        "children": [c.name for c in o.children],
        "collections": [c.name for c in o.users_collection],
        "location": _v(o.location),
        "rotation_mode": o.rotation_mode,
        "rotation_euler": _v(o.rotation_euler),
        "scale": _v(o.scale),
        "dimensions": _v(o.dimensions),
        "hide_viewport": bool(o.hide_viewport),
        "hide_render": bool(o.hide_render),
        "hide_get": bool(o.hide_get()),
        "visible_get": bool(o.visible_get()),
        "modifiers": [{{"name": m.name, "type": m.type, "show_viewport": m.show_viewport, "show_render": m.show_render}} for m in o.modifiers],
        "constraints": [{{"name": c.name, "type": c.type, "enabled": c.enabled}} for c in o.constraints],
        "materials": [{{"slot": i, "material": s.material.name if s.material else None}} for i, s in enumerate(o.material_slots)],
        "vertex_groups": [g.name for g in o.vertex_groups],
        "custom_properties": {{k: str(o[k]) for k in o.keys() if k != "_RNA_UI"}},
        "bound_box_world": (lambda pts: {"min": _v([min(p[i] for p in pts) for i in range(3)]), "max": _v([max(p[i] for p in pts) for i in range(3)])})([o.matrix_world @ __import__("mathutils").Vector(c) for c in o.bound_box]) if o.type == "MESH" else None,
    }}
'''

DATABLOCKS = r'''
import bpy

attrs = ["objects", "meshes", "materials", "images", "collections", "node_groups", "armatures",
         "actions", "cameras", "lights", "worlds", "scenes", "textures", "curves", "fonts",
         "sounds", "movieclips", "libraries", "cache_files", "volumes", "grease_pencils"]
counts = {}
for attr in attrs:
    try:
        counts[attr] = len(getattr(bpy.data, attr))
    except Exception:
        counts[attr] = None
window = getattr(bpy.context, "window", None)
scene = bpy.context.scene
result = {
    "counts": counts,
    "active_workspace": window.workspace.name if window else None,
    "render_engine": scene.render.engine if scene else None,
    "scene": scene.name if scene else None,
    "filepath": bpy.data.filepath,
    "version": bpy.app.version_string,
    "is_dirty": bpy.data.is_dirty,
}
'''

PATH_INFO = r'''
import bpy, os, datetime

p = bpy.data.filepath
st = os.stat(p) if p and os.path.isfile(p) else None
backups = []
for suffix in (".blend1", ".blend2", ".blend3"):
    q = p + suffix if p else None
    if q and os.path.isfile(q):
        s = os.stat(q)
        backups.append({"path": q, "size_bytes": s.st_size, "modified": datetime.datetime.fromtimestamp(s.st_mtime).isoformat()})
result = {
    "filepath": p,
    "saved": bool(p) and os.path.isfile(p),
    "dirty": bool(bpy.data.is_dirty),
    "size_bytes": st.st_size if st else None,
    "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat() if st else None,
    "backups": backups,
    "version": bpy.app.version_string,
}
'''

MISSING_FILES = r'''
import bpy, os

missing = []
def check(kind, block):
    fp = getattr(block, "filepath", "")
    if not fp:
        return
    if getattr(block, "packed_file", None):
        return
    resolved = bpy.path.abspath(fp)
    if not os.path.exists(resolved):
        missing.append({
            "kind": kind,
            "name": getattr(block, "name", None),
            "path": fp,
            "resolved": resolved,
        })

collections = [
    ("image", getattr(bpy.data, "images", [])),
    ("library", getattr(bpy.data, "libraries", [])),
    ("font", getattr(bpy.data, "fonts", [])),
    ("sound", getattr(bpy.data, "sounds", [])),
    ("movieclip", getattr(bpy.data, "movieclips", [])),
    ("cachefile", getattr(bpy.data, "cache_files", [])),
    ("volume", getattr(bpy.data, "volumes", [])),
]
for kind, blocks in collections:
    for block in blocks:
        check(kind, block)
result = {"missing": missing, "count": len(missing)}
'''

LINKED_LIBRARIES = r'''
import bpy, os

libraries = []
for lib in bpy.data.libraries:
    resolved = bpy.path.abspath(lib.filepath)
    libraries.append({
        "name": lib.name,
        "filepath": lib.filepath,
        "resolved": resolved,
        "exists": os.path.exists(resolved),
        "parent": getattr(getattr(lib, "parent", None), "name", None),
    })
result = {"libraries": libraries, "count": len(libraries)}
'''

USAGE_GUESS = r'''
import bpy

objects = list(bpy.data.objects)
meshes = [o for o in objects if o.type == "MESH"]
lights = [o for o in objects if o.type == "LIGHT"]
cameras = [o for o in objects if o.type == "CAMERA"]
armatures = [o for o in objects if o.type == "ARMATURE"]
volumes = [o for o in objects if o.type == "VOLUME"]
actions = list(bpy.data.actions)
images = list(bpy.data.images)
node_groups = list(bpy.data.node_groups)

scores = {
    "archviz": 0,
    "game_asset": 0,
    "character": 0,
    "animation": 0,
    "simulation": 0,
    "product_render": 0,
    "environment": 0,
    "vfx": 0,
}
evidence = []
if any(o.modifiers for o in meshes):
    scores["game_asset"] += 15
if any(o.type == "MESH" and len(o.data.polygons) > 200000 for o in meshes):
    scores["archviz"] += 10
if armatures:
    scores["character"] += 30
    scores["animation"] += 25
    evidence.append(f"{len(armatures)} armature(s)")
if actions:
    scores["animation"] += min(40, len(actions) * 5)
    evidence.append(f"{len(actions)} action(s)")
if cameras and lights:
    scores["product_render"] += 15
    scores["archviz"] += 10
if len(lights) >= 3:
    scores["archviz"] += 10
    evidence.append(f"{len(lights)} lights")
if any(o.modifiers and any(m.type in {"FLUID", "CLOTH", "SOFT_BODY"} for m in o.modifiers) for o in meshes):
    scores["simulation"] += 35
if any(o.rigid_body for o in objects if hasattr(o, "rigid_body")):
    scores["simulation"] += 20
if volumes:
    scores["vfx"] += 30
    evidence.append(f"{len(volumes)} volume(s)")
if any(g.bl_idname == "GeometryNodeTree" for g in node_groups):
    scores["environment"] += 15
    scores["game_asset"] += 5
if any(o.type == "MESH" and o.modifiers and any(m.type == "NODES" for m in o.modifiers) for o in meshes):
    scores["environment"] += 15
if len(objects) > 500:
    scores["environment"] += 20
    evidence.append(f"{len(objects)} objects")
if any("scene" in (o.name or "").lower() for o in objects):
    scores["environment"] += 5
if len(images) > 10:
    scores["game_asset"] += 5
ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
result = {
    "scores": scores,
    "top": [{"use": k, "score": v} for k, v in ranked[:4]],
    "evidence": evidence,
    "stats": {
        "objects": len(objects),
        "meshes": len(meshes),
        "lights": len(lights),
        "cameras": len(cameras),
        "armatures": len(armatures),
        "actions": len(actions),
        "images": len(images),
        "node_groups": len(node_groups),
    },
}
'''

WINDOW_JSON = r'''
import bpy

windows = []
for w in bpy.context.window_manager.windows:
    areas = []
    for a in w.screen.areas:
        areas.append({
            "type": a.type,
            "width": a.width,
            "height": a.height,
            "regions": [r.type for r in a.regions],
        })
    windows.append({"width": w.width, "height": w.height, "workspace": w.workspace.name, "areas": areas})
active = bpy.context.view_layer.objects.active
result = {
    "windows": windows,
    "workspaces": [ws.name for ws in bpy.data.workspaces],
    "active_object": active.name if active else None,
    "selected": [o.name for o in bpy.context.selected_objects],
    "mode": bpy.context.mode,
    "filepath": bpy.data.filepath,
    "version": bpy.app.version_string,
    "engine": bpy.context.scene.render.engine if bpy.context.scene else None,
}
'''


def screenshot_code(area_type: str | None) -> str:
    area = json.dumps(area_type)
    return f'''
import bpy, os, tempfile, base64

area_type = {area}
if bpy.app.background:
    raise RuntimeError("Screenshots require Blender's graphical interface")
window = getattr(bpy.context, "window", None)
if window is None:
    raise RuntimeError("No active Blender window")
fd, path = tempfile.mkstemp(prefix="blender_skill_", suffix=".png")
os.close(fd)
try:
    if area_type is None:
        bpy.ops.screen.screenshot(filepath=path)
    else:
        area = next((a for a in window.screen.areas if a.type == area_type), None)
        if area is None:
            raise RuntimeError(f"No {{area_type}} area in the active window")
        with bpy.context.temp_override(window=window, screen=window.screen, area=area):
            bpy.ops.screen.screenshot_area(filepath=path)
    with open(path, "rb") as handle:
        data = handle.read()
    result = {{"area": area_type or "WINDOW", "bytes": len(data), "base64": base64.b64encode(data).decode("ascii")}}
finally:
    try:
        os.unlink(path)
    except OSError:
        pass
'''


def jump_workspace_name(name: str) -> str:
    return f'''
import bpy
name = {json.dumps(name)}
ws = bpy.data.workspaces.get(name)
window = getattr(bpy.context, "window", None)
if ws is None:
    result = {{"error": "workspace not found", "requested": name, "available": [w.name for w in bpy.data.workspaces]}}
elif window is None:
    result = {{"error": "no active window"}}
else:
    window.workspace = ws
    result = {{"workspace": ws.name}}
'''


def jump_workspace_space(space_type: str) -> str:
    return f'''
import bpy
target = {json.dumps(space_type)}
window = getattr(bpy.context, "window", None)
if window is None:
    result = {{"error": "no active window"}}
else:
    found = None
    for ws in bpy.data.workspaces:
        for screen in ws.screens:
            if any(area.type == target for area in screen.areas):
                found = ws
                break
        if found:
            break
    if found is None:
        result = {{"error": "no workspace with that area type", "requested": target}}
    else:
        window.workspace = found
        result = {{"workspace": found.name, "area_type": target}}
'''


def jump_object(name: str, by_data: bool) -> str:
    return f'''
import bpy
name = {json.dumps(name)}
by_data = {str(bool(by_data))}
obj = None
if by_data:
    obj = next((o for o in bpy.data.objects if o.data is not None and o.data.name == name), None)
else:
    obj = bpy.data.objects.get(name)
if obj is None:
    result = {{"error": "object not found", "requested": name, "by_data": by_data}}
else:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    framed = False
    window = getattr(bpy.context, "window", None)
    if window is not None:
        area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
        if area is not None:
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            with bpy.context.temp_override(window=window, screen=window.screen, area=area, region=region):
                bpy.ops.view3d.view_selected(use_all_regions=False)
            framed = True
    result = {{"object": obj.name, "data": getattr(obj.data, "name", None), "framed": framed, "dimensions": [round(float(x), 5) for x in obj.dimensions]}}
'''


def render_code(path: str, thumbnail: bool, width: int | None, height: int | None) -> str:
    width_code = json.dumps(width) if width is not None else "None"
    height_code = json.dumps(height) if height is not None else "None"
    return f'''
import bpy, os, time

path = os.path.abspath(os.path.expanduser({json.dumps(path)}))
os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
scene = bpy.context.scene
render = scene.render
old = {{
    "filepath": render.filepath,
    "format": render.image_settings.file_format,
    "resolution_percentage": render.resolution_percentage,
    "resolution_x": render.resolution_x,
    "resolution_y": render.resolution_y,
    "samples": None,
    "eevee_samples": None,
}}
try:
    if {str(thumbnail)}:
        render.resolution_percentage = 25
        try:
            old["samples"] = scene.cycles.samples
            scene.cycles.samples = 8
        except Exception:
            pass
        try:
            old["eevee_samples"] = scene.eevee.taa_render_samples
            scene.eevee.taa_render_samples = 8
        except Exception:
            pass
    if {width_code}:
        render.resolution_x = int({width_code})
    if {height_code}:
        render.resolution_y = int({height_code})
    render.filepath = path
    render.image_settings.file_format = "PNG"
    started = time.time()
    bpy.ops.render.render(write_still=True)
    result = {{
        "path": path,
        "engine": render.engine,
        "width": render.resolution_x,
        "height": render.resolution_y,
        "percentage": render.resolution_percentage,
        "elapsed_sec": round(time.time() - started, 3),
        "exists": os.path.isfile(path),
        "bytes": os.path.getsize(path) if os.path.isfile(path) else None,
    }}
finally:
    render.filepath = old["filepath"]
    render.image_settings.file_format = old["format"]
    render.resolution_percentage = old["resolution_percentage"]
    render.resolution_x = old["resolution_x"]
    render.resolution_y = old["resolution_y"]
    if old["samples"] is not None:
        try:
            scene.cycles.samples = old["samples"]
        except Exception:
            pass
    if old["eevee_samples"] is not None:
        try:
            scene.eevee.taa_render_samples = old["eevee_samples"]
        except Exception:
            pass
'''


def import_code(glb: str, collection: str, prefix: str, apply_alpha: bool) -> str:
    return f'''
import bpy, json, os

glb = os.path.abspath(os.path.expanduser({json.dumps(glb)}))
collection_name = {json.dumps(collection)}
prefix = {json.dumps(prefix)}
if not os.path.isfile(glb):
    raise FileNotFoundError(glb)

sidecar = {{}}
sidecar_path = glb + ".json"
if os.path.isfile(sidecar_path):
    try:
        with open(sidecar_path, encoding="utf-8") as handle:
            sidecar = json.load(handle)
    except Exception:
        sidecar = {{}}

coll = bpy.data.collections.get(collection_name)
if coll is None:
    coll = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(coll)

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
new_objects = [o for o in bpy.data.objects if o not in before]

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

for index, obj in enumerate(new_objects):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    obj.name = f"{{prefix}}_{{index:02d}}"
    if obj.data:
        obj.data.name = obj.name
    obj["trellis2_source"] = glb
    if sidecar:
        obj["trellis2_seed"] = int(sidecar.get("seed", 0) or 0)
        obj["trellis2_pipeline"] = str(sidecar.get("pipeline_type", ""))
        obj["trellis2_texture_size"] = int(sidecar.get("texture_size", 0) or 0)
    if {str(bool(apply_alpha))}:
        for slot in obj.material_slots:
            enable_alpha(slot.material)

bpy.ops.object.select_all(action="DESELECT")
for obj in new_objects:
    obj.select_set(True)
if new_objects:
    bpy.context.view_layer.objects.active = new_objects[0]

result = {{
    "glb": glb,
    "collection": coll.name,
    "objects": [
        {{
            "name": o.name,
            "type": o.type,
            "vertices": len(o.data.vertices) if o.type == "MESH" else None,
            "polygons": len(o.data.polygons) if o.type == "MESH" else None,
            "materials": [s.material.name if s.material else None for s in o.material_slots],
        }}
        for o in new_objects
    ],
    "sidecar": sidecar,
}}
'''


def api_doc_code(identifier: str) -> str:
    return "import bpy, inspect\nidentifier = " + json.dumps(identifier) + "\n" + r'''
roots = {"bpy": bpy}
try:
    import bmesh
    roots["bmesh"] = bmesh
except Exception:
    pass
try:
    import mathutils
    roots["mathutils"] = mathutils
except Exception:
    pass

def prop_payload(rna, name):
    prop = rna.properties.get(name)
    if prop is None:
        return None
    payload = {
        "doc": prop.description or "",
        "signature": "",
        "type": prop.type,
        "kind": "property",
        "owner": rna.identifier,
        "subtype": getattr(prop, "subtype", ""),
        "units": getattr(prop, "unit", ""),
        "read_only": bool(getattr(prop, "is_readonly", False)),
    }
    try:
        payload["default"] = str(prop.default)
    except Exception:
        pass
    if prop.type == "ENUM":
        payload["enum_items"] = [item.identifier for item in prop.enum_items]
    return payload

parts = identifier.split(".")
result = None

# bpy.types.Class.property / function
if len(parts) >= 4 and parts[0] == "bpy" and parts[1] == "types":
    cls = getattr(bpy.types, parts[2], None)
    rna = getattr(cls, "bl_rna", None) if cls is not None else None
    if rna is not None:
        if len(parts) == 4:
            payload = prop_payload(rna, parts[3])
            if payload is not None:
                result = {"identifier": identifier, "found": True, **payload}
            else:
                fn = next((f for f in rna.functions if f.identifier == parts[3]), None)
                if fn is not None:
                    result = {
                        "identifier": identifier,
                        "found": True,
                        "doc": fn.description or "",
                        "signature": f"{fn.identifier}({', '.join(p.identifier for p in fn.parameters)})",
                        "type": "function",
                        "kind": "function",
                        "owner": rna.identifier,
                    }

if result is None:
    obj = roots.get(parts[0])
    path = [parts[0]]
    if obj is None:
        obj = bpy
        path = []
    for part in (parts[1:] if path else parts):
        try:
            obj = getattr(obj, part)
            path.append(part)
        except AttributeError:
            obj = None
            break

    if obj is None:
        result = {"identifier": identifier, "found": False, "error": "identifier not found"}
    else:
        doc = inspect.getdoc(obj) or ""
        rna = getattr(obj, "bl_rna", None)
        if rna is not None and not doc:
            doc = rna.description or ""
        try:
            rna2 = obj.get_rna_type()
        except Exception:
            rna2 = None
        if rna2 is not None and not doc:
            doc = rna2.description or ""
        try:
            signature = str(inspect.signature(obj))
        except Exception:
            signature = ""
        payload = {
            "identifier": ".".join(path) or identifier,
            "found": True,
            "doc": doc,
            "signature": signature,
            "type": type(obj).__name__,
            "kind": "class" if isinstance(obj, type) else "object",
        }
        active_rna = rna or rna2
        if active_rna is not None:
            payload["rna_identifier"] = active_rna.identifier
            try:
                payload["properties"] = [
                    {"name": p.identifier, "type": p.type, "description": p.description}
                    for p in active_rna.properties if p.identifier != "rna_type"
                ][:250]
            except Exception:
                pass
            try:
                payload["functions"] = [
                    {"name": f.identifier, "description": f.description}
                    for f in active_rna.functions
                ][:200]
            except Exception:
                pass
        result = payload
'''

API_INDEX = r'''
import bpy, inspect

entries = []
def describe(obj):
    try:
        doc = inspect.getdoc(obj) or ""
    except Exception:
        doc = ""
    if not doc:
        rna = getattr(obj, "bl_rna", None)
        if rna is not None:
            doc = getattr(rna, "description", "") or ""
    if not doc:
        try:
            doc = obj.get_rna_type().description or ""
        except Exception:
            doc = ""
    return doc

def add(identifier, obj, kind=None, doc=None):
    text = doc if doc is not None else describe(obj)
    if not text or not text.strip():
        return
    entries.append({"id": identifier, "doc": text[:1800], "kind": kind or type(obj).__name__})

def add_class(prefix, cls):
    rna = getattr(cls, "bl_rna", None)
    if rna is None:
        add(prefix, cls)
        return
    add(prefix, cls, "class", rna.description or describe(cls))
    for prop in rna.properties:
        if prop.identifier == "rna_type" or not prop.description:
            continue
        add(f"{prefix}.{prop.identifier}", prop, "property", prop.description)
    for fn in rna.functions:
        if not fn.description:
            continue
        add(f"{prefix}.{fn.identifier}", fn, "function", fn.description)

for name in dir(bpy.types):
    if name.startswith("_"):
        continue
    try:
        add_class("bpy.types." + name, getattr(bpy.types, name))
    except Exception:
        pass

for module_name in dir(bpy.ops):
    if module_name.startswith("_"):
        continue
    try:
        module = getattr(bpy.ops, module_name)
    except Exception:
        continue
    for op_name in dir(module):
        if op_name.startswith("_"):
            continue
        op = getattr(module, op_name)
        try:
            add(f"bpy.ops.{module_name}.{op_name}", op, "operator")
            rna = op.get_rna_type()
            for prop in rna.properties:
                if prop.identifier == "rna_type" or not prop.description:
                    continue
                add(f"bpy.ops.{module_name}.{op_name}.{prop.identifier}", prop, "property", prop.description)
        except Exception:
            pass

for name in dir(bpy.data):
    if name.startswith("_"):
        continue
    try:
        add("bpy.data." + name, getattr(bpy.data, name))
    except Exception:
        pass

try:
    import bmesh
    for name in dir(bmesh.ops):
        if name.startswith("_"):
            continue
        try:
            add("bmesh.ops." + name, getattr(bmesh.ops, name), "function")
        except Exception:
            pass
except Exception:
    pass

try:
    import mathutils
    for name in dir(mathutils):
        if name.startswith("_"):
            continue
        try:
            add_class("mathutils." + name, getattr(mathutils, name)) if isinstance(getattr(mathutils, name), type) else add("mathutils." + name, getattr(mathutils, name))
        except Exception:
            pass
except Exception:
    pass

result = {"version": bpy.app.version_string, "entries": entries[:40000]}
'''

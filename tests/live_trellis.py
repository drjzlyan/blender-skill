#!/usr/bin/env python3
"""Live TRELLIS.2 generation and Blender import test."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from blender_skill_mcp import paths  # noqa: E402


def request(kind: str, code: str | None = None, timeout: float = 120.0) -> dict:
    payload = {"id": uuid.uuid4().hex, "type": kind}
    token = paths.mcp_token()
    if token:
        payload["token"] = token
    if code is not None:
        payload["code"] = code
        payload["strict_json"] = True
    with socket.create_connection((paths.mcp_host(), paths.mcp_port()), timeout=10) as sock:
        sock.settimeout(timeout)
        sock.sendall(json.dumps(payload).encode() + b"\x00")
        buffer = b""
        while b"\x00" not in buffer:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError("Blender closed the connection")
            buffer += chunk
        raw = buffer.partition(b"\x00")[0]
    response = json.loads(raw.decode())
    if not response.get("ok"):
        raise RuntimeError(response.get("error") or "unknown error")
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default=str(ROOT / "examples" / "assets" / "angel_statue.webp"))
    parser.add_argument("--pipeline-type", default="512")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    image = Path(args.image).expanduser().resolve()
    if not image.is_file():
        print(json.dumps({"ok": False, "error": f"reference image not found: {image}"}))
        return 2
    outputs = paths.outputs_dir() / "tests"
    outputs.mkdir(parents=True, exist_ok=True)
    output = outputs / f"skill_test_{int(time.time())}.glb"

    command = [
        sys.executable,
        str(ROOT / "scripts" / "blender_skill.py"),
        "trellis", "generate",
        "--image", str(image),
        "--output", str(output),
        "--pipeline-type", args.pipeline_type,
        "--seed", str(args.seed),
        "--decimation-target", "20000",
        "--texture-size", "512",
        "--low-vram",
    ]
    print(json.dumps({"stage": "generate", "command": command}), flush=True)
    proc = subprocess.run(command, text=True, capture_output=True, timeout=7200)
    result: dict = {
        "ok": False,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
        "output": str(output),
    }
    sidecar = Path(str(output) + ".json")
    if sidecar.is_file():
        result["sidecar"] = json.loads(sidecar.read_text(encoding="utf-8"))
    if proc.returncode != 0 or not output.is_file():
        print(json.dumps(result, indent=2))
        return 1
    result["ok"] = True
    result["bytes"] = output.stat().st_size

    # Optional live import. Skipped when Blender is not reachable.
    try:
        import_code = f'''
import bpy, json, os
glb = {str(output)!r}
sidecar_path = glb + ".json"
sidecar = json.load(open(sidecar_path)) if os.path.isfile(sidecar_path) else {{}}
coll = bpy.data.collections.get("COL_SKILL_TEST_TRELLIS")
if coll is None:
    coll = bpy.data.collections.new("COL_SKILL_TEST_TRELLIS")
    bpy.context.scene.collection.children.link(coll)
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=glb)
new = [o for o in bpy.data.objects if o not in before]
for index, obj in enumerate(new):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    obj.name = f"SKILL_TEST_TRELLIS_{{index:02d}}"
    if obj.data:
        obj.data.name = obj.name
    obj["trellis2_source"] = glb
    obj["trellis2_seed"] = int(sidecar.get("seed", 0) or 0)
meshes = [o for o in new if o.type == "MESH"]
result = {{
    "objects": [{{"name": o.name, "type": o.type, "vertices": len(o.data.vertices) if o.type == "MESH" else None,
                 "polygons": len(o.data.polygons) if o.type == "MESH" else None,
                 "materials": [s.material.name if s.material else None for s in o.material_slots]}} for o in new],
    "meshes": len(meshes),
    "triangles": sum(len(o.data.polygons) for o in meshes),
}}
'''
        result["import"] = request("execute", import_code, timeout=300)["result"]
    except Exception as exc:  # noqa: BLE001
        result["import"] = {"skipped": str(exc)}


    # Render the imported asset with a temporary camera so the test exercises
    # generation -> import -> render end to end.
    render_path = output.with_name(output.stem + "_render.png")
    render_code = f'''
import bpy, os
from mathutils import Vector
path = {str(render_path)!r}
objs = [o for o in bpy.data.objects if o.name.startswith("SKILL_TEST_TRELLIS_") and o.type == "MESH"]
if not objs:
    result = {{"skipped": "no imported mesh"}}
else:
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    test_names = {{o.name for o in objs}}
    center = (lo + hi) * 0.5
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z, 0.1)
    cam_data = bpy.data.cameras.new("SKILL_TEST_CAM")
    cam = bpy.data.objects.new("SKILL_TEST_CAM", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = center + Vector((size * 2.0, -size * 2.4, size * 1.6))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sun_data = bpy.data.lights.new("SKILL_TEST_SUN", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("SKILL_TEST_SUN", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = (0.7, 0.2, 0.5)
    scene = bpy.context.scene
    old_camera = scene.camera
    old_path = scene.render.filepath
    old_x = scene.render.resolution_x
    old_y = scene.render.resolution_y
    hidden = []
    for other in list(scene.objects):
        if other.name not in test_names and other not in (cam, sun) and not other.hide_render:
            other.hide_render = True
            hidden.append(other)
    try:
        scene.camera = cam
        scene.render.filepath = path
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        scene.render.resolution_percentage = 100
        bpy.ops.render.render(write_still=True)
        result = {{"path": path, "exists": os.path.isfile(path),
                   "bytes": os.path.getsize(path) if os.path.isfile(path) else 0}}
    finally:
        scene.camera = old_camera
        scene.render.filepath = old_path
        scene.render.resolution_x = old_x
        scene.render.resolution_y = old_y
        for other in hidden:
            try:
                other.hide_render = False
            except Exception:
                pass
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.objects.remove(sun, do_unlink=True)
'''
    try:
        result["render"] = request("execute", render_code, timeout=600)["result"]
    except Exception as exc:  # noqa: BLE001
        result["render"] = {"error": str(exc)}

    if not args.keep:
        cleanup = r'''
import bpy
for obj in [o for o in bpy.data.objects if o.name.startswith("SKILL_TEST_TRELLIS_")]:
    bpy.data.objects.remove(obj, do_unlink=True)
coll = bpy.data.collections.get("COL_SKILL_TEST_TRELLIS")
if coll is not None and not coll.objects and not coll.children:
    bpy.data.collections.remove(coll)
result = {"cleaned": True}
'''
        try:
            result["cleanup"] = request("execute", cleanup)["result"]
        except Exception as exc:  # noqa: BLE001
            result["cleanup"] = {"skipped": str(exc)}

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

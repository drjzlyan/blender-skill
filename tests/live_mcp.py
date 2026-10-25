#!/usr/bin/env python3
"""Live MCP smoke test. Requires Blender running with the add-on enabled."""

from __future__ import annotations

import base64
import json
import socket
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from blender_skill_mcp import paths  # noqa: E402


def request(kind: str, code: str | None = None, timeout: float = 60.0) -> dict:
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
    try:
        state = request("state")["result"]
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "stage": "connect", "error": str(exc)}))
        return 2

    result: dict = {"ok": True, "state": state}
    create = r'''
import bpy
coll = bpy.data.collections.get("COL_SKILL_TEST")
if coll is None:
    coll = bpy.data.collections.new("COL_SKILL_TEST")
    bpy.context.scene.collection.children.link(coll)
existing = bpy.data.objects.get("SKILL_TEST_CUBE")
if existing is not None:
    bpy.data.objects.remove(existing, do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
cube = bpy.context.active_object
cube.name = "SKILL_TEST_CUBE"
for c in list(cube.users_collection):
    c.objects.unlink(cube)
coll.objects.link(cube)
result = {"name": cube.name, "collection": coll.name, "objects": len(bpy.data.objects), "vertices": len(cube.data.vertices)}
'''
    try:
        result["create"] = request("execute", create)["result"]
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "stage": "create", "error": str(exc)}))
        return 1

    check = r'''
import bpy
cube = bpy.data.objects.get("SKILL_TEST_CUBE")
result = {
    "exists": cube is not None,
    "collections": [c.name for c in cube.users_collection] if cube else [],
    "active": bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
    "mode": bpy.context.mode,
}
'''
    result["check"] = request("execute", check)["result"]
    if not result["check"].get("exists"):
        print(json.dumps({"ok": False, "stage": "check", "result": result}))
        return 1

    # Screenshot only when a graphical interface is available.
    shot = r'''
import bpy, base64, os, tempfile
if bpy.app.background:
    result = {"skipped": "background"}
else:
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        bpy.ops.screen.screenshot(filepath=path)
        with open(path, "rb") as handle:
            data = handle.read()
        result = {"bytes": len(data), "png": data[:8] == b"\x89PNG\r\n\x1a\n", "base64": base64.b64encode(data).decode("ascii")}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
'''
    try:
        shot_result = request("execute", shot)["result"]
        if isinstance(shot_result, dict) and "base64" in shot_result:
            shot_result["base64_bytes"] = len(shot_result.pop("base64"))
        result["screenshot"] = shot_result
    except Exception as exc:  # noqa: BLE001
        result["screenshot"] = {"error": str(exc)}

    render = r'''
import bpy, os, tempfile
scene = bpy.context.scene
camera = scene.camera or next((o for o in scene.objects if o.type == "CAMERA"), None)
if camera is None:
    result = {"skipped": "no camera"}
else:
    scene.camera = camera
    path = os.path.join(tempfile.gettempdir(), "blender_skill_test_render.png")
    scene.render.filepath = path
    scene.render.resolution_percentage = 25
    bpy.ops.render.render(write_still=True)
    result = {"path": path, "exists": os.path.isfile(path), "bytes": os.path.getsize(path) if os.path.isfile(path) else 0}
'''
    try:
        result["render"] = request("execute", render, timeout=300)["result"]
    except Exception as exc:  # noqa: BLE001
        result["render"] = {"error": str(exc)}

    cleanup = r'''
import bpy
cube = bpy.data.objects.get("SKILL_TEST_CUBE")
if cube is not None:
    bpy.data.objects.remove(cube, do_unlink=True)
coll = bpy.data.collections.get("COL_SKILL_TEST")
if coll is not None and not coll.objects and not coll.children:
    bpy.data.collections.remove(coll)
result = {"cleaned": True}
'''
    try:
        result["cleanup"] = request("execute", cleanup)["result"]
    except Exception as exc:  # noqa: BLE001
        result["cleanup"] = {"error": str(exc)}

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

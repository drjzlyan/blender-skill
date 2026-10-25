"""Local socket bridge that runs inside Blender.

Protocol: newline-independent, null-byte-delimited UTF-8 JSON messages.
Request:  {"id": "...", "type": "execute"|"ping"|"state", "token": "...", ...}
Response: {"id": "...", "ok": true, "result": ..., "stdout": "", "stderr": ""}

The server is non-blocking and executes code on Blender's main thread from a
``bpy.app.timers`` callback. It never imports project-specific packages.
"""

from __future__ import annotations

import base64
import io
import json
import os
import select
import socket
import sys
import tempfile
import time
import traceback
from typing import Any

import bpy

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
_TICK_ACTIVE = 0.05
_TICK_IDLE = 0.5
_MAX_MESSAGE = 32 * 1024 * 1024


def _json_safe(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return repr(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        return {str(k): _json_safe(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v, depth + 1) for v in value]
    for attr in ("to_list", "to_tuple"):
        fn = getattr(value, attr, None)
        if callable(fn):
            try:
                return _json_safe(fn(), depth + 1)
            except Exception:
                pass
    if hasattr(value, "__len__") and hasattr(value, "__getitem__"):
        try:
            return [_json_safe(value[i], depth + 1) for i in range(min(len(value), 1000))]
        except Exception:
            pass
    return repr(value)


class _Client:
    __slots__ = ("sock", "buffer", "out", "closed")

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buffer = bytearray()
        self.out = bytearray()
        self.closed = False


class BridgeServer:
    def __init__(self) -> None:
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.token = ""
        self._socket: socket.socket | None = None
        self._clients: list[_Client] = []
        self._running = False
        self._last_request = 0.0
        self._error = ""

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str:
        return self._error

    def start(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, token: str = "") -> tuple[bool, str]:
        self.stop()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, int(port)))
            sock.listen(8)
            sock.setblocking(False)
        except Exception as exc:  # noqa: BLE001
            self._error = f"{host}:{port}: {exc}"
            return False, self._error
        self._socket = sock
        self.host = host
        self.port = int(port)
        self.token = token or ""
        self._running = True
        self._error = ""
        if not bpy.app.timers.is_registered(self._tick):
            bpy.app.timers.register(self._tick, first_interval=_TICK_ACTIVE, persistent=True)
        return True, f"listening on {host}:{port}"

    def stop(self) -> None:
        self._running = False
        for client in list(self._clients):
            self._close(client)
        self._clients.clear()
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        if bpy.app.timers.is_registered(self._tick):
            try:
                bpy.app.timers.unregister(self._tick)
            except Exception:
                pass

    def _close(self, client: _Client) -> None:
        client.closed = True
        try:
            client.sock.close()
        except Exception:
            pass

    def _tick(self) -> float | None:
        if not self._running or self._socket is None:
            return None
        self._accept()
        did_work = self._pump()
        now = time.time()
        if did_work:
            self._last_request = now
            return _TICK_ACTIVE
        return _TICK_IDLE

    def _accept(self) -> None:
        if self._socket is None:
            return
        while True:
            try:
                conn, _ = self._socket.accept()
            except BlockingIOError:
                return
            except Exception:
                return
            conn.setblocking(False)
            self._clients.append(_Client(conn))

    def _pump(self) -> bool:
        did_work = False
        for client in list(self._clients):
            if client.closed:
                self._clients.remove(client)
                continue
            # flush pending output
            if client.out:
                try:
                    sent = client.sock.send(client.out)
                    del client.out[:sent]
                except BlockingIOError:
                    pass
                except Exception:
                    self._close(client)
                    self._clients.remove(client)
                    continue
            # read
            while True:
                try:
                    chunk = client.sock.recv(65536)
                except BlockingIOError:
                    break
                except Exception:
                    self._close(client)
                    break
                if not chunk:
                    self._close(client)
                    break
                client.buffer.extend(chunk)
                if len(client.buffer) > _MAX_MESSAGE:
                    self._send(client, {"ok": False, "error": "request too large"})
                    client.buffer.clear()
            if client.closed:
                if client in self._clients:
                    self._clients.remove(client)
                continue
            while b"\x00" in client.buffer:
                raw, _, rest = client.buffer.partition(b"\x00")
                client.buffer = bytearray(rest)
                did_work = True
                try:
                    request = json.loads(raw.decode("utf-8"))
                except Exception as exc:  # noqa: BLE001
                    self._send(client, {"ok": False, "error": f"invalid JSON: {exc}"})
                    continue
                self._send(client, self._handle(request))
        return did_work

    def _send(self, client: _Client, payload: dict[str, Any]) -> None:
        try:
            data = json.dumps(payload, default=str).encode("utf-8") + b"\x00"
        except Exception as exc:  # noqa: BLE001
            data = json.dumps({"ok": False, "error": f"encode failed: {exc}"}).encode("utf-8") + b"\x00"
        client.out.extend(data)
        try:
            sent = client.sock.send(client.out)
            del client.out[:sent]
        except BlockingIOError:
            pass
        except Exception:
            self._close(client)

    def _handle(self, request: dict[str, Any]) -> dict[str, Any]:
        req_id = request.get("id")
        if self.token and request.get("token") != self.token:
            return {"id": req_id, "ok": False, "error": "invalid token"}
        kind = request.get("type", "execute")
        if kind == "ping":
            return {"id": req_id, "ok": True, "result": {"pong": True, "version": bpy.app.version_string}}
        if kind == "state":
            return {"id": req_id, "ok": True, "result": _state()}
        if kind != "execute":
            return {"id": req_id, "ok": False, "error": f"unknown request type: {kind}"}
        code = request.get("code", "")
        if not isinstance(code, str) or not code.strip():
            return {"id": req_id, "ok": False, "error": "empty code"}
        strict = bool(request.get("strict_json", True))
        return {"id": req_id, **_execute(code, strict)}


def _execute(code: str, strict: bool) -> dict[str, Any]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    namespace: dict[str, Any] = {
        "__name__": "__blender_skill__",
        "bpy": bpy,
    }
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    started = time.time()
    try:
        exec(compile(code, "<blender-skill>", "exec"), namespace, namespace)
        result = namespace.get("result")
        ok = True
        error = None
    except Exception:  # noqa: BLE001
        result = None
        ok = False
        error = traceback.format_exc()
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    if strict:
        try:
            json.dumps(result)
        except Exception:
            result = _json_safe(result)
    else:
        result = _json_safe(result)
    return {
        "ok": ok,
        "result": result,
        "stdout": stdout.getvalue()[-20000:],
        "stderr": stderr.getvalue()[-20000:],
        "error": error,
        "elapsed_sec": round(time.time() - started, 3),
    }


def _state() -> dict[str, Any]:
    scene = getattr(bpy.context, "scene", None)
    window = getattr(bpy.context, "window", None)
    return {
        "blender": bpy.app.version_string,
        "background": bool(bpy.app.background),
        "filepath": bpy.data.filepath,
        "scene": getattr(scene, "name", None),
        "engine": getattr(getattr(scene, "render", None), "engine", None),
        "mode": getattr(getattr(bpy.context, "mode", None), "name", None) or str(getattr(bpy.context, "mode", "")),
        "window": getattr(window, "width", None) and getattr(window, "height", None),
        "objects": len(bpy.data.objects),
    }


def _screenshot(path: str, area_type: str | None = None) -> dict[str, Any]:
    if bpy.app.background:
        raise RuntimeError("screenshots require Blender's graphical interface")
    window = getattr(bpy.context, "window", None)
    if window is None:
        raise RuntimeError("no active Blender window")
    if area_type is None:
        bpy.ops.screen.screenshot(filepath=path)
        return {"path": path, "area": "WINDOW"}
    area = next((a for a in window.screen.areas if a.type == area_type), None)
    if area is None:
        raise RuntimeError(f"no {area_type} area in the active window")
    with bpy.context.temp_override(window=window, screen=window.screen, area=area):
        bpy.ops.screen.screenshot_area(filepath=path)
    return {"path": path, "area": area_type}


def capture_screenshot(area_type: str | None = None) -> dict[str, Any]:
    fd, path = tempfile.mkstemp(prefix="blender_skill_", suffix=".png")
    os.close(fd)
    try:
        info = _screenshot(path, area_type)
        with open(path, "rb") as handle:
            data = handle.read()
        info["bytes"] = len(data)
        info["base64"] = base64.b64encode(data).decode("ascii")
        return info
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


SERVER = BridgeServer()

"""Client for the Blender Skill MCP add-on socket."""

from __future__ import annotations

import json
import socket
import threading
import uuid
from typing import Any

from . import paths


class BridgeError(RuntimeError):
    pass


class BlenderBridge:
    def __init__(self, host: str | None = None, port: int | None = None, token: str | None = None) -> None:
        self.host = host or paths.mcp_host()
        self.port = int(port if port is not None else paths.mcp_port())
        self.token = token if token is not None else paths.mcp_token()
        self._socket: socket.socket | None = None
        self._buffer = bytearray()
        self._lock = threading.Lock()

    def _connect(self, timeout: float) -> None:
        try:
            self._socket = socket.create_connection((self.host, self.port), timeout=timeout)
            self._socket.settimeout(timeout)
            self._buffer.clear()
        except OSError as exc:
            self._socket = None
            raise BridgeError(
                f"Cannot connect to Blender at {self.host}:{self.port}. "
                "Enable the Blender Skill MCP add-on and press Start Server. "
                f"({exc})"
            ) from exc

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def request(
        self,
        kind: str,
        *,
        code: str | None = None,
        strict_json: bool = True,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        with self._lock:
            if self._socket is None:
                self._connect(timeout)
            payload: dict[str, Any] = {"id": uuid.uuid4().hex, "type": kind}
            if self.token:
                payload["token"] = self.token
            if code is not None:
                payload["code"] = code
                payload["strict_json"] = strict_json
            try:
                assert self._socket is not None
                self._socket.settimeout(timeout)
                self._socket.sendall(json.dumps(payload).encode("utf-8") + b"\x00")
                raw = self._read_message()
            except (OSError, TimeoutError) as exc:
                self.close()
                raise BridgeError(f"Lost connection to Blender: {exc}") from exc
            try:
                response = json.loads(raw.decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise BridgeError(f"Invalid response from Blender: {exc}") from exc
            if not response.get("ok"):
                detail = response.get("error") or "unknown error"
                raise BridgeError(str(detail))
            return response

    def _read_message(self) -> bytes:
        assert self._socket is not None
        while b"\x00" not in self._buffer:
            chunk = self._socket.recv(65536)
            if not chunk:
                raise BridgeError("Blender closed the connection")
            self._buffer.extend(chunk)
            if len(self._buffer) > 64 * 1024 * 1024:
                raise BridgeError("Response exceeded 64 MB")
        raw, _, rest = self._buffer.partition(b"\x00")
        self._buffer = bytearray(rest)
        return raw

    def ping(self) -> dict[str, Any]:
        return self.request("ping", timeout=5.0).get("result") or {}

    def state(self) -> dict[str, Any]:
        return self.request("state", timeout=5.0).get("result") or {}

    def execute(self, code: str, *, strict_json: bool = True, timeout: float = 60.0) -> dict[str, Any]:
        response = self.request("execute", code=code, strict_json=strict_json, timeout=timeout)
        return {
            "ok": True,
            "result": response.get("result"),
            "stdout": response.get("stdout", ""),
            "stderr": response.get("stderr", ""),
            "elapsed_sec": response.get("elapsed_sec"),
        }

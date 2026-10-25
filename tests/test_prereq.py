import importlib.util
import socket
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    path = ROOT / "scripts" / "blender_skill.py"
    spec = importlib.util.spec_from_file_location("blender_skill_installer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PrereqTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer = load_installer()

    def test_version_parsing(self):
        self.assertEqual(self.installer.parse_version("Blender 5.2.2 LTS"), (5, 2, 2))
        self.assertEqual(self.installer.parse_version("Blender 4.5"), (4, 5, 0))
        self.assertEqual(self.installer.parse_version("no version"), (0, 0, 0))

    def test_minimums(self):
        self.assertGreaterEqual(self.installer.MIN_BLENDER, (4, 5, 0))
        self.assertGreaterEqual(self.installer.MIN_PYTHON, (3, 10))

    def test_gpu_profile_shape(self):
        gpu = self.installer.gpu_info()
        self.assertIn("profile", gpu)
        self.assertIn(gpu["profile"], {"high", "recommended", "medium", "low", "minimal", "mcp_only"})

    def test_doctor_shape(self):
        report = self.installer.doctor()
        for key in ("ok", "blender", "python", "gpu", "disk", "paths", "addon", "warnings", "errors"):
            self.assertIn(key, report)
        self.assertIn("trellis_ok", report)

    def test_port_pick(self):
        port = self.installer.pick_port("127.0.0.1", 9876)
        self.assertGreaterEqual(port, 9876)
        self.assertTrue(self.installer.port_available("127.0.0.1", port))


class ProtocolTests(unittest.TestCase):
    def test_null_delimited_json(self):
        sys.path.insert(0, str(ROOT / "mcp"))
        try:
            from blender_skill_mcp.bridge import BlenderBridge
        finally:
            sys.path.pop(0)

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def handle():
            conn, _ = server.accept()
            buffer = b""
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buffer += chunk
                while b"\x00" in buffer:
                    raw, _, buffer = buffer.partition(b"\x00")
                    import json
                    req = json.loads(raw.decode())
                    if req.get("type") == "ping":
                        payload = {"id": req.get("id"), "ok": True, "result": {"pong": True}}
                    elif req.get("code") == "raise":
                        payload = {"id": req.get("id"), "ok": False, "error": "boom"}
                    else:
                        payload = {"id": req.get("id"), "ok": True, "result": {"echo": req.get("code")},
                                   "stdout": "", "stderr": "", "elapsed_sec": 0.01}
                    conn.sendall(json.dumps(payload).encode() + b"\x00")
            conn.close()

        thread = threading.Thread(target=handle, daemon=True)
        thread.start()
        try:
            bridge = BlenderBridge(host="127.0.0.1", port=port, token="")
            self.assertTrue(bridge.ping()["pong"])
            result = bridge.execute("result = 1 + 1")
            self.assertEqual(result["result"]["echo"], "result = 1 + 1")
            with self.assertRaises(Exception):
                bridge.execute("raise")
        finally:
            bridge.close()
            server.close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

import sys, types, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import blender_skill as bs  # noqa: E402


def proc(code=0, out=""):
    return types.SimpleNamespace(returncode=code, stdout=out, stderr="")


class GpuDetectionTests(unittest.TestCase):
    def test_nvidia_smi_wins_when_present(self):
        with mock.patch.object(bs.shutil, "which", return_value="/usr/bin/nvidia-smi"), \
             mock.patch.object(bs, "run", return_value=proc(0, "NVIDIA GeForce RTX 4090, 24564, 550.00\n")):
            g = bs.gpu_info()
        self.assertTrue(g["cuda"])
        self.assertEqual(g["source"], "nvidia-smi")
        self.assertEqual(g["profile"], "recommended")

    def test_falls_back_to_torch_when_smi_is_off_path(self):
        torch_out = '{"ok": true, "name": "NVIDIA GeForce RTX 4090", "vram": 23.5}\n'
        with mock.patch.object(bs.shutil, "which", return_value=None), \
             mock.patch.object(bs, "load_config", return_value={"trellis_python": __file__}), \
             mock.patch.object(bs, "run", return_value=proc(0, torch_out)):
            g = bs.gpu_info()
        self.assertTrue(g["cuda"])
        self.assertEqual(g["source"], "torch")
        self.assertEqual(g["vram_gb"], 23.5)
        self.assertIn(g["profile"], {"medium", "recommended"})

    def test_reports_no_gpu_when_neither_probe_finds_cuda(self):
        with mock.patch.object(bs.shutil, "which", return_value=None), \
             mock.patch.object(bs, "load_config", return_value={"trellis_python": __file__}), \
             mock.patch.object(bs, "run", return_value=proc(0, '{"ok": false, "name": null, "vram": 0}\n')):
            g = bs.gpu_info()
        self.assertFalse(g["cuda"])
        self.assertEqual(g["profile"], "mcp_only")

    def test_missing_trellis_venv_is_not_an_error(self):
        with mock.patch.object(bs.shutil, "which", return_value=None), \
             mock.patch.object(bs, "load_config", return_value={"trellis_python": "/nonexistent/python"}):
            self.assertFalse(bs.gpu_info()["cuda"])


if __name__ == "__main__":
    unittest.main()

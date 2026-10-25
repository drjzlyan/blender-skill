import importlib.util
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    spec = importlib.util.spec_from_file_location("blender_skill_installer", ROOT / "scripts" / "blender_skill.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer = load_installer()

    def test_aux_models_declared(self):
        names = set(self.installer.AUX_MODELS)
        self.assertEqual(names, {"TRELLIS-image-large", "dinov3-vitl16", "RMBG-2.0"})
        self.assertFalse(self.installer.AUX_MODELS["TRELLIS-image-large"]["gated"])
        self.assertTrue(self.installer.AUX_MODELS["dinov3-vitl16"]["gated"])

    def test_pipeline_rewrite_targets(self):
        self.assertTrue((ROOT / "trellis" / "vendor" / "trellis2").is_dir())
        self.assertTrue((ROOT / "trellis" / "vendor" / "CuMesh" / "src" / "clean_up.cu").is_file())
        text = (ROOT / "trellis" / "vendor" / "CuMesh" / "src" / "clean_up.cu").read_text(encoding="utf-8")
        self.assertIn("thrust::sort_by_key", text, "CUDA 12.0 compatibility patch missing")

    @unittest.skipUnless(shutil.which("blender") or __import__("os").environ.get("BLENDER_BIN"), "Blender not installed")
    def test_dry_run(self):
        import argparse
        args = argparse.Namespace(
            harness="auto", project=None, force=False, dry_run=True, without_trellis=True,
            skip_trellis_build=False, with_flash_attn=False, trellis_python=None, model_dir=None,
            aux_dir=None, skip_mcp=False, skip_addon=False, skip_weights=False, mcp_port=None,
            no_token=False, with_trellis_addon=False,
        )
        report = self.installer.setup(args)
        self.assertIn("dry_run", report)
        self.assertIn("blender", report["plan"])


if __name__ == "__main__":
    unittest.main()
